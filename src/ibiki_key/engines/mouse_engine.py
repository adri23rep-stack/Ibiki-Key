from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable

from ..errors import IbikiError
from ..models import Mapping, Profile
from ..services import mouse_backend as mouse
from ..services.windows import (
    SystemMouseSettings,
    capture_mouse_settings,
    foreground_window,
    restore_mouse_settings,
    set_cursor_speed,
    set_double_click_time,
    set_scroll_lines,
)
from .action_executor import ActionExecutor
from .monitor import InputMonitor

log = logging.getLogger(__name__)


class MouseEngine:
    def __init__(
        self,
        executor: ActionExecutor,
        monitor: InputMonitor,
        notify: Callable[[str, str], None] | None = None,
    ):
        self.executor = executor
        self.monitor = monitor
        self.notify = notify
        self.profile: Profile | None = None
        self.running = False
        self.paused = False
        self._hook: object | None = None
        self._last_fired: dict[str, float] = {}
        self._ignore_until = 0.0
        self._gesture_start: tuple[float, float] | None = None
        self._gesture_last: tuple[float, float] | None = None
        self._gesture_button = "right"
        self._lock = threading.RLock()
        self._allow_cache: tuple[float, bool] = (0.0, True)
        self._original_settings: SystemMouseSettings | None = None

    def start(self, profile: Profile) -> None:
        self._close_hook()
        if self._original_settings is None:
            self._original_settings = capture_mouse_settings()
        self.profile = profile
        self.paused = False
        self._last_fired.clear()
        self._allow_cache = (0.0, True)
        try:
            if self._original_settings is None:
                log.warning(
                    "No se pudieron leer los ajustes originales del mouse; no se modificarán"
                )
            else:
                self.apply_profile_settings()
            self._hook = mouse.hook(self._on_event)
        except Exception:
            self._hook = None
            restore_mouse_settings(self._original_settings)
            self._original_settings = None
            self.profile = None
            self.running = False
            raise
        self.running = True
        log.info("Motor de mouse activo: %s", profile.name)

    def stop(self) -> None:
        self._close_hook()
        restore_mouse_settings(self._original_settings)
        self._original_settings = None
        self.paused = False
        self.profile = None
        log.info("Motor de mouse detenido")

    def _close_hook(self) -> None:
        if self._hook is not None:
            try:
                mouse.unhook(self._hook)
            except Exception:
                pass
        self._hook = None
        self.running = False

    def apply_profile_settings(self) -> None:
        if not self.profile:
            return
        results = (
            set_cursor_speed(self.profile.mouse.cursor_speed),
            set_double_click_time(self.profile.mouse.double_click_ms),
            set_scroll_lines(self.profile.mouse.scroll_lines),
        )
        if not all(results):
            log.warning("Windows no confirmó todos los ajustes del mouse")

    def set_pause_state(self, *, automation_paused: bool, capture_paused: bool = False) -> None:
        self.paused = bool(automation_paused or capture_paused)
        if not self.running:
            return
        if automation_paused:
            restore_mouse_settings(self._original_settings)
        else:
            self.apply_profile_settings()

    def apply_profile(self, profile: Profile) -> None:
        if self.running:
            self.start(profile)
        else:
            self.profile = profile

    def suspend_for(self, seconds: float) -> None:
        with self._lock:
            self._ignore_until = max(self._ignore_until, time.monotonic() + max(0.0, seconds))

    def _on_event(self, event: object) -> None:
        name = type(event).__name__
        if name == "MoveEvent":
            x = float(getattr(event, "x", 0))
            y = float(getattr(event, "y", 0))
            if self._gesture_start:
                self._gesture_last = (x, y)
            return
        if name == "WheelEvent":
            delta = int(getattr(event, "delta", 0))
            horizontal = bool(getattr(event, "horizontal", False))
            if horizontal:
                source = "wheel_right" if delta > 0 else "wheel_left"
            else:
                source = "wheel_up" if delta > 0 else "wheel_down"
            self.monitor.record("mouse", source, "scroll")
            self._match_and_fire(source, "press")
            return
        button = str(getattr(event, "button", "unknown"))
        event_type = str(getattr(event, "event_type", "down"))
        self.monitor.record("mouse", button, event_type)
        if self.profile and self.profile.mouse.gestures_enabled and button == self._gesture_button:
            if event_type == "down":
                try:
                    pos = mouse.get_position()
                    self._gesture_start = (float(pos[0]), float(pos[1]))
                    self._gesture_last = self._gesture_start
                except Exception:
                    self._gesture_start = None
            elif event_type == "up":
                gesture = self._gesture_direction()
                self._gesture_start = None
                self._gesture_last = None
                if gesture:
                    self._match_and_fire(f"gesture:{gesture}", "press")
        phase = "press" if event_type in {"down", "double"} else "release"
        self._match_and_fire(button, phase)

    def _match_and_fire(self, source: str, phase: str) -> None:
        if (
            self.paused
            or not self.profile
            or (phase != "release" and not self._profile_allows_input())
            or (phase != "release" and time.monotonic() < self._ignore_until)
        ):
            return
        active_layer = self.profile.active_layer
        for mapping in self.profile.mouse_mappings:
            if not mapping.enabled or mapping.layer != active_layer or mapping.source != source:
                continue
            if mapping.trigger not in {phase, "hold"} and not (
                mapping.trigger == "double_tap" and phase == "press"
            ):
                continue
            now = time.monotonic()
            if mapping.debounce_ms:
                previous = self._last_fired.get(mapping.id, 0.0)
                if (now - previous) * 1000 < mapping.debounce_ms:
                    continue
            if mapping.trigger == "double_tap":
                previous = self._last_fired.get(f"tap:{mapping.id}", 0.0)
                self._last_fired[f"tap:{mapping.id}"] = now
                if (now - previous) * 1000 > int(mapping.action.options.get("tap_ms", 300)):
                    continue
            self._last_fired[mapping.id] = now
            self._ignore_until = now + (0.015 if self.profile.settings.get("low_latency", False) else 0.035)
            threading.Thread(
                target=self._execute,
                args=(mapping, phase),
                name="MouseMapping",
                daemon=True,
            ).start()

    def _execute(self, mapping: Mapping, phase: str) -> None:
        try:
            from ..models import Action

            action = Action(mapping.action.type, mapping.action.value, dict(mapping.action.options))
            action.options["_mapping_id"] = mapping.id
            if mapping.trigger == "hold" and action.type in {"key", "mouse_button"}:
                action.options["hold"] = True
            if action.type == "macro":
                action.options.setdefault("source_key", f"mouse:{mapping.source}")
                if mapping.trigger == "hold":
                    action.options["stop_on_release"] = True
            self.executor.execute(action, phase=phase)
        except IbikiError:
            log.debug("Acción de mouse rechazada para %s", mapping.source)
        except Exception:
            log.exception("Falló el remapeo del botón %s", mapping.source)

    def _gesture_direction(self) -> str | None:
        if not self._gesture_start or not self._gesture_last:
            return None
        dx = self._gesture_last[0] - self._gesture_start[0]
        dy = self._gesture_last[1] - self._gesture_start[1]
        if math.hypot(dx, dy) < 45:
            return None
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        return "down" if dy > 0 else "up"

    def _profile_allows_input(self) -> bool:
        profile = self.profile
        if not profile or not profile.settings.get("whitelist_enabled", False):
            return True
        now = time.monotonic()
        if now - self._allow_cache[0] < 0.25:
            return self._allow_cache[1]
        process, _ = foreground_window()
        allowed = process in set(profile.settings.get("whitelist_programs", []))
        self._allow_cache = (now, allowed)
        return allowed

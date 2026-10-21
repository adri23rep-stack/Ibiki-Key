from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from ..errors import EngineUnavailable
from ..errors import IbikiError
from ..models import Mapping, Profile
from ..services.windows import foreground_window
from .action_executor import ActionExecutor
from .monitor import InputMonitor

log = logging.getLogger(__name__)


class KeyboardEngine:
    """Global keyboard mappings backed by the Windows `keyboard` hook."""

    def __init__(
        self,
        executor: ActionExecutor,
        monitor: InputMonitor,
        notify: Callable[[str, str], None] | None = None,
    ):
        self.executor = executor
        self.monitor = monitor
        self.notify = notify
        self.pause_callback: Callable[[], None] | None = None
        self.profile: Profile | None = None
        self.active_layer = "Base"
        self.running = False
        self.paused = False
        self._removers: list[object] = []
        self._control_handles: list[object] = []
        self._monitor_remover: object | None = None
        self._lock = threading.RLock()
        self._ignore_until = 0.0
        self._last_fired: dict[str, float] = {}
        self._last_tap: dict[str, float] = {}
        self._layer_stack: list[str] = []
        self._allow_cache: tuple[float, bool] = (0.0, True)

    def start(self, profile: Profile) -> None:
        try:
            import keyboard
        except ImportError as exc:
            raise EngineUnavailable("Falta instalar el paquete 'keyboard'") from exc
        with self._lock:
            self._clear_hooks()
            self.profile = profile
            self.active_layer = profile.active_layer if profile.active_layer in profile.layers else "Base"
            self._layer_stack.clear()
            self._last_fired.clear()
            self._last_tap.clear()
            self._allow_cache = (0.0, True)
            self.running = True
            self.paused = False
            self._monitor_remover = keyboard.hook(self._on_monitor_event, suppress=False)
            self._bind_active_layer()
            pause_remove = keyboard.add_hotkey(
                "ctrl+alt+f12", self._pause_requested, suppress=False, trigger_on_release=True
            )
            self._control_handles.append(pause_remove)
        log.info("Motor de teclado activo: %s / %s", profile.name, self.active_layer)

    def stop(self) -> None:
        with self._lock:
            self.running = False
            self._clear_hooks()
            self.profile = None
        log.info("Motor de teclado detenido")

    def apply_profile(self, profile: Profile) -> None:
        if not self.running:
            self.profile = profile
            return
        self.start(profile)

    def toggle_pause(self) -> None:
        with self._lock:
            self.paused = not self.paused
            paused = self.paused
        if self.notify:
            self.notify(
                "warning" if paused else "success",
                "Remapeo y macros pausados" if paused else "Remapeo y macros reanudados",
            )

    def _pause_requested(self) -> None:
        if self.pause_callback:
            self.pause_callback()
        else:
            self.toggle_pause()

    def suspend_for(self, seconds: float) -> None:
        with self._lock:
            self._ignore_until = max(self._ignore_until, time.monotonic() + max(0.0, seconds))

    def set_layer(self, layer: str, restore: bool = False) -> None:
        profile = self.profile
        if not profile or layer not in profile.layers:
            if self.notify:
                self.notify("warning", f"La capa '{layer}' no existe")
            return
        with self._lock:
            if restore:
                new_layer = self._layer_stack.pop() if self._layer_stack else "Base"
            else:
                if layer == self.active_layer:
                    new_layer = "Base"
                    self._layer_stack.clear()
                else:
                    self._layer_stack.append(self.active_layer)
                    new_layer = layer
            if new_layer == self.active_layer:
                return
            self.active_layer = new_layer
            profile.active_layer = new_layer
        threading.Timer(0.01, self._rebind_for_layer).start()
        if self.notify:
            self.notify("info", f"Capa activa: {new_layer}")

    def _rebind_for_layer(self) -> None:
        with self._lock:
            if not self.running:
                return
            self._remove_mapping_hooks()
            self._bind_active_layer()

    def _bind_active_layer(self) -> None:
        import keyboard

        if not self.profile:
            return
        candidates = [
            mapping
            for mapping in self.profile.mappings
            if mapping.enabled
            and (
                mapping.layer == self.active_layer
                or mapping.action.type in {"layer_momentary", "layer_toggle"}
            )
        ]
        candidates.sort(key=lambda item: item.layer != self.active_layer)
        mappings: list[Mapping] = []
        layer_sources: set[str] = set()
        for mapping in candidates:
            if mapping.action.type in {"layer_momentary", "layer_toggle"}:
                if mapping.source in layer_sources:
                    continue
                layer_sources.add(mapping.source)
            mappings.append(mapping)
        for mapping in mappings:
            try:
                if "+" in mapping.source:
                    remover = keyboard.add_hotkey(
                        mapping.source,
                        lambda item=mapping: self._fire_combo(item),
                        suppress=mapping.suppress,
                        trigger_on_release=mapping.trigger == "release",
                    )
                else:
                    remover = keyboard.hook_key(
                        mapping.source,
                        lambda event, item=mapping: self._on_mapping_event(item, event),
                        suppress=mapping.suppress,
                    )
                self._removers.append(remover)
            except Exception as exc:
                log.warning("No se pudo enlazar %s: %s", mapping.source, exc)
                if self.notify:
                    self.notify("warning", f"No se pudo activar '{mapping.source}': {exc}")

    def _on_mapping_event(self, mapping: Mapping, event: object) -> None:
        event_type = getattr(event, "event_type", "down")
        phase = "press" if event_type == "down" else "release"
        if (
            self.paused
            or (phase != "release" and not self._profile_allows_input())
            or (phase != "release" and time.monotonic() < self._ignore_until)
        ):
            return
        should_fire = (
            mapping.trigger == phase
            or mapping.trigger == "hold"
            or (mapping.trigger == "double_tap" and phase == "press")
            or mapping.action.type == "layer_momentary"
        )
        if not should_fire:
            return
        now = time.monotonic()
        if phase == "press" and mapping.debounce_ms:
            previous = self._last_fired.get(mapping.id, 0.0)
            if (now - previous) * 1000 < mapping.debounce_ms:
                return
        if mapping.trigger == "double_tap":
            if phase != "press":
                return
            previous = self._last_tap.get(mapping.id, 0.0)
            self._last_tap[mapping.id] = now
            if (now - previous) * 1000 > int(mapping.action.options.get("tap_ms", 300)):
                return
        self._last_fired[mapping.id] = now
        self._dispatch(mapping, phase)

    def _fire_combo(self, mapping: Mapping) -> None:
        if self.paused or not self._profile_allows_input() or time.monotonic() < self._ignore_until:
            return
        now = time.monotonic()
        if mapping.debounce_ms:
            previous = self._last_fired.get(mapping.id, 0.0)
            if (now - previous) * 1000 < mapping.debounce_ms:
                return
        if mapping.trigger == "double_tap":
            previous = self._last_tap.get(mapping.id, 0.0)
            self._last_tap[mapping.id] = now
            if (now - previous) * 1000 > int(mapping.action.options.get("tap_ms", 300)):
                return
        self._last_fired[mapping.id] = now
        self._dispatch(mapping, "press")

    def _dispatch(self, mapping: Mapping, phase: str) -> None:
        low_latency = bool(self.profile and self.profile.settings.get("low_latency", False))
        self._ignore_until = time.monotonic() + (0.015 if low_latency else 0.035)
        try:
            from ..models import Action

            action = Action(mapping.action.type, mapping.action.value, dict(mapping.action.options))
            action.options["_mapping_id"] = mapping.id
            if mapping.trigger == "hold" and action.type in {"key", "mouse_button"}:
                action.options["hold"] = True
            if action.type == "macro":
                action.options.setdefault("source_key", mapping.source)
                if mapping.trigger == "hold":
                    action.options["stop_on_release"] = True
            self.executor.execute(action, phase=phase)
        except IbikiError:
            log.debug("Acción rechazada para el remapeo de %s", mapping.source)
        except Exception:
            log.exception("Falló el remapeo de %s", mapping.source)

    def _on_monitor_event(self, event: object) -> None:
        name = str(getattr(event, "name", "?"))
        event_type = str(getattr(event, "event_type", "down"))
        self.monitor.record("keyboard", name, event_type)

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

    def _remove_mapping_hooks(self) -> None:
        handles = self._removers
        self._removers = []
        for handle in handles:
            self._remove_handle(handle)

    def _clear_hooks(self) -> None:
        self._remove_mapping_hooks()
        for handle in self._control_handles:
            self._remove_handle(handle)
        self._control_handles = []
        if self._monitor_remover:
            self._remove_handle(self._monitor_remover)
            self._monitor_remover = None

    @staticmethod
    def _remove_handle(handle: object) -> None:
        try:
            import keyboard

            try:
                keyboard.remove_hotkey(handle)
                return
            except Exception:
                pass
            try:
                keyboard.unhook(handle)
                return
            except Exception:
                pass
            if callable(handle):
                handle()
        except Exception:
            pass

from __future__ import annotations

import threading
import time
from typing import Any

from PySide6.QtCore import QObject, Signal

from ..models import Action, MacroStep
from ..services import mouse_backend as mouse
from ..services.mouse_recording import MouseRecordingBuilder


class MacroRecorder(QObject):
    count_changed = Signal(int)
    failed = Signal(str)
    stop_requested = Signal()

    def __init__(self, controller: object, *, mode: str = "all"):
        super().__init__()
        if mode not in {"all", "mouse"}:
            raise ValueError(f"Modo de grabación no compatible: {mode}")
        self.controller = controller
        self.mode = mode
        self.events: list[dict[str, Any]] = []
        self._mouse_builder = MouseRecordingBuilder()
        self._lock = threading.RLock()
        self._keyboard_handle: object | None = None
        self._stop_hotkey_handle: object | None = None
        self._mouse_handle: object | None = None
        self.running = False
        self._owns_capture = False

    def start(
        self,
        *,
        record_mouse_moves: bool | None = None,
        move_interval_ms: int | None = None,
    ) -> None:
        if self.running:
            return
        if not self.controller.begin_input_capture(self):
            self.failed.emit("Ya hay otra grabación de entradas en curso.")
            return
        self._owns_capture = True
        try:
            import keyboard

            with self._lock:
                self.events.clear()
            self._mouse_builder = MouseRecordingBuilder(
                record_moves=True if record_mouse_moves is None else record_mouse_moves,
                move_interval_ms=30 if move_interval_ms is None else move_interval_ms,
            )
            try:
                start_position = mouse.get_position()
            except Exception:
                start_position = None
            self._mouse_builder.reset(start_position)

            if self.mode == "all":
                self._keyboard_handle = keyboard.hook(self._on_keyboard, suppress=False)
            else:
                # Este atajo no se agrega a la macro: permite detener sin contaminar
                # la grabación con el clic sobre la interfaz.
                self._stop_hotkey_handle = keyboard.add_hotkey(
                    "ctrl+alt+f11",
                    lambda: self.stop_requested.emit(),
                    suppress=False,
                    trigger_on_release=False,
                )
            self._mouse_handle = mouse.hook(self._on_mouse)
            self.running = True
        except Exception as exc:
            self._unhook_all()
            self._release_capture()
            self.failed.emit(f"No se pudo iniciar la grabación: {exc}")

    def stop(self) -> list[MacroStep]:
        if not self.running:
            return []
        self.running = False
        self._unhook_all()
        self._release_capture()
        self._mouse_builder.remove_recent_stop_click()
        return self._to_steps()

    def _unhook_all(self) -> None:
        try:
            import keyboard

            if self._keyboard_handle is not None:
                keyboard.unhook(self._keyboard_handle)
            if self._stop_hotkey_handle is not None:
                keyboard.remove_hotkey(self._stop_hotkey_handle)
        except Exception:
            pass
        try:
            if self._mouse_handle is not None:
                mouse.unhook(self._mouse_handle)
        except Exception:
            pass
        self._keyboard_handle = None
        self._stop_hotkey_handle = None
        self._mouse_handle = None

    def _release_capture(self) -> None:
        if self._owns_capture:
            self.controller.end_input_capture(self)
            self._owns_capture = False

    def _on_keyboard(self, event: object) -> None:
        name = str(getattr(event, "name", ""))
        event_type = str(getattr(event, "event_type", ""))
        if not name or event_type not in {"down", "up"}:
            return
        self._append(
            {
                "time": float(getattr(event, "time", time.time())),
                "action": Action("key", name, {"event": event_type}),
            }
        )

    def _on_mouse(self, event: object) -> None:
        if self._event_count() >= 10_000:
            self.stop_requested.emit()
            return
        if self._mouse_builder.feed(event):
            self.count_changed.emit(self._event_count())
        if self._mouse_builder.full:
            self.stop_requested.emit()

    def _append(self, event: dict[str, Any]) -> None:
        with self._lock:
            if len(self.events) + self._mouse_builder.count >= 10_000:
                self.stop_requested.emit()
                return
            self.events.append(event)
        self.count_changed.emit(self._event_count())

    def _event_count(self) -> int:
        with self._lock:
            return len(self.events) + self._mouse_builder.count

    def _to_steps(self) -> list[MacroStep]:
        mouse_steps = self._mouse_builder.to_steps()
        if self.mode == "mouse":
            return mouse_steps
        with self._lock:
            keyboard_events = list(self.events)
        # Reconstruimos una sola línea temporal para conservar los retrasos entre
        # teclado y mouse en la grabación general.
        mouse_events = self._mouse_builder.snapshot_events()
        events = sorted([*keyboard_events, *mouse_events], key=lambda item: float(item["time"]))
        steps: list[MacroStep] = []
        for index, item in enumerate(events):
            delay = 0
            if index + 1 < len(events):
                delay = min(
                    round(max(0.0, float(events[index + 1]["time"]) - float(item["time"])) * 1000),
                    60_000,
                )
            steps.append(MacroStep(action=item["action"], delay_after_ms=delay))
        return steps

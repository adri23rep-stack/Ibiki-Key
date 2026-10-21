from __future__ import annotations

import threading
import time
from typing import Any

from ..models import Action, MacroStep


class MouseRecordingBuilder:
    """Convierte eventos nativos del mouse en pasos de macro editables.

    Los movimientos se guardan como desplazamientos relativos y se muestrean para
    evitar crear miles de pasos por segundo. La clase no depende de Qt ni de
    Windows, por lo que la conversión puede probarse de forma aislada.
    """

    def __init__(
        self,
        *,
        record_moves: bool = True,
        move_interval_ms: int = 30,
        max_events: int = 10_000,
    ):
        self.record_moves = bool(record_moves)
        self.move_interval_ms = max(8, min(1000, int(move_interval_ms)))
        self.max_events = max(1, int(max_events))
        self._events: list[dict[str, Any]] = []
        self._last_position: tuple[int, int] | None = None
        self._last_move_time = 0.0
        self._lock = threading.RLock()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._events)

    @property
    def full(self) -> bool:
        return self.count >= self.max_events

    def snapshot_events(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)

    def reset(self, start_position: tuple[int, int] | None = None) -> None:
        with self._lock:
            self._events.clear()
            self._last_position = (
                (int(start_position[0]), int(start_position[1])) if start_position else None
            )
            self._last_move_time = 0.0

    def feed(self, event: object) -> bool:
        """Agrega un evento. Devuelve True solamente si produjo un paso."""
        event_name = type(event).__name__
        timestamp = float(getattr(event, "time", time.time()))
        if event_name == "MoveEvent":
            return self._feed_move(event, timestamp)
        if event_name == "WheelEvent":
            delta = int(getattr(event, "delta", 0))
            if not delta:
                return False
            if bool(getattr(event, "horizontal", False)):
                value: Any = {"vertical": 0, "horizontal": delta}
            else:
                value = delta
            return self._append(timestamp, Action("scroll", value))

        event_type = str(getattr(event, "event_type", ""))
        if event_type not in {"down", "up"}:
            return False
        button = str(getattr(event, "button", "left")).strip().lower()
        return self._append(
            timestamp,
            Action("mouse_button", button, {"event": event_type}),
        )

    def to_steps(self) -> list[MacroStep]:
        with self._lock:
            events = sorted(self._events, key=lambda item: float(item["time"]))
        steps: list[MacroStep] = []
        for index, item in enumerate(events):
            if index + 1 < len(events):
                elapsed = max(0.0, float(events[index + 1]["time"]) - float(item["time"]))
                delay = min(round(elapsed * 1000), 60_000)
            else:
                delay = 0
            steps.append(MacroStep(action=item["action"], delay_after_ms=delay))
        return steps

    def remove_recent_stop_click(self, *, now: float | None = None, window: float = 1.25) -> bool:
        """Quita el clic izquierdo reciente usado para detener desde la interfaz."""
        cutoff = float(time.time() if now is None else now) - max(0.1, float(window))
        with self._lock:
            if len(self._events) < 2:
                return False
            up_index = self._last_recent_left_index("up", cutoff)
            if up_index is None:
                return False
            down_index = self._last_recent_left_index("down", cutoff, before=up_index)
            if down_index is None:
                return False
            # Solo se eliminan movimientos posteriores al clic. Los movimientos
            # anteriores pueden ser parte real de la macro y se conservan.
            removable = {down_index, up_index}
            for index in range(down_index + 1, len(self._events)):
                action = self._events[index]["action"]
                if action.type == "mouse_move" and float(self._events[index]["time"]) >= cutoff:
                    removable.add(index)
            self._events = [item for index, item in enumerate(self._events) if index not in removable]
            return True

    def _feed_move(self, event: object, timestamp: float) -> bool:
        position = (int(getattr(event, "x", 0)), int(getattr(event, "y", 0)))
        with self._lock:
            if self._last_position is None:
                self._last_position = position
                self._last_move_time = timestamp
                return False
            if not self.record_moves:
                self._last_position = position
                return False
            interval = self.move_interval_ms / 1000
            if self._last_move_time and timestamp - self._last_move_time < interval:
                return False
            previous = self._last_position
            delta_x = position[0] - previous[0]
            delta_y = position[1] - previous[1]
            if not delta_x and not delta_y:
                self._last_move_time = timestamp
                return False
            if len(self._events) >= self.max_events:
                return False
            self._events.append(
                {
                    "time": timestamp,
                    "action": Action(
                        "mouse_move",
                        {"x": delta_x, "y": delta_y, "absolute": False},
                    ),
                }
            )
            self._last_position = position
            self._last_move_time = timestamp
            return True

    def _append(self, timestamp: float, action: Action) -> bool:
        with self._lock:
            if len(self._events) >= self.max_events:
                return False
            self._events.append({"time": timestamp, "action": action})
            return True

    def _last_recent_left_index(
        self,
        event_type: str,
        cutoff: float,
        *,
        before: int | None = None,
    ) -> int | None:
        stop = len(self._events) if before is None else before
        for index in range(stop - 1, -1, -1):
            item = self._events[index]
            if float(item["time"]) < cutoff:
                return None
            action = item["action"]
            if (
                action.type == "mouse_button"
                and action.value == "left"
                and action.options.get("event") == event_type
            ):
                return index
        return None

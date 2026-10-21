from __future__ import annotations

import threading
import time
from collections import Counter, deque
from typing import Any, Callable


class InputMonitor:
    def __init__(self, callback: Callable[[dict[str, Any]], None] | None = None):
        self.callback = callback
        self._lock = threading.RLock()
        self._events: deque[dict[str, Any]] = deque(maxlen=1000)
        self._press_times: deque[float] = deque(maxlen=5000)
        self._heatmap: Counter[str] = Counter()
        self._device_presses: Counter[str] = Counter()
        self._started_at = time.monotonic()
        self._last_press: float | None = None
        self._interval_sum_ms = 0.0
        self._interval_count = 0
        self._min_interval_ms: float | None = None
        self._max_interval_ms: float | None = None
        self._peak_cps = 0

    def record(self, device: str, name: str, event_type: str) -> dict[str, Any]:
        now = time.monotonic()
        event: dict[str, Any] = {
            "device": device,
            "name": name,
            "event_type": event_type,
            "time": time.time(),
            "delta_ms": None,
        }
        with self._lock:
            if event_type in {"down", "press", "double", "scroll"}:
                if self._last_press is not None:
                    event["delta_ms"] = round((now - self._last_press) * 1000, 1)
                    interval = float(event["delta_ms"])
                    self._interval_sum_ms += interval
                    self._interval_count += 1
                    self._min_interval_ms = (
                        interval
                        if self._min_interval_ms is None
                        else min(self._min_interval_ms, interval)
                    )
                    self._max_interval_ms = (
                        interval
                        if self._max_interval_ms is None
                        else max(self._max_interval_ms, interval)
                    )
                self._last_press = now
                self._press_times.append(now)
                self._heatmap[f"{device}:{name}"] += 1
                self._device_presses[device] += 1
                self._peak_cps = max(
                    self._peak_cps,
                    sum(1 for value in self._press_times if value >= now - 1),
                )
            self._events.append(event)
            stats = self.snapshot()
        if self.callback:
            self.callback({"event": event, "stats": stats})
        return event

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            while self._press_times and self._press_times[0] < now - 60:
                self._press_times.popleft()
            cps = sum(1 for value in self._press_times if value >= now - 1)
            apm = len(self._press_times)
            average = (
                round(self._interval_sum_ms / self._interval_count, 1)
                if self._interval_count
                else None
            )
            return {
                "cps": cps,
                "apm": apm,
                "peak_cps": self._peak_cps,
                "total": sum(self._heatmap.values()),
                "session_seconds": round(now - self._started_at, 1),
                "average_interval_ms": average,
                "min_interval_ms": self._min_interval_ms,
                "max_interval_ms": self._max_interval_ms,
                "device_counts": dict(self._device_presses),
                "heatmap": dict(self._heatmap),
                "history": list(self._events)[-250:],
            }

    def history(self, limit: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            events = list(self._events)
            if limit is None:
                return events
            limit = max(0, int(limit))
            return events[-limit:] if limit else []

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._press_times.clear()
            self._heatmap.clear()
            self._device_presses.clear()
            self._started_at = time.monotonic()
            self._last_press = None
            self._interval_sum_ms = 0.0
            self._interval_count = 0
            self._min_interval_ms = None
            self._max_interval_ms = None
            self._peak_cps = 0

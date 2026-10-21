from __future__ import annotations

import logging
import random
import threading
from collections.abc import Callable

from ..errors import IbikiError
from ..models import Macro, Profile
from ..services import mouse_backend as mouse
from .action_executor import ActionExecutor

log = logging.getLogger(__name__)


class MacroEngine:
    def __init__(
        self,
        executor: ActionExecutor,
        get_profile: Callable[[], Profile],
        notify: Callable[[str, str], None] | None = None,
    ):
        self.executor = executor
        self.get_profile = get_profile
        self.notify = notify
        self._running: dict[str, tuple[threading.Thread, threading.Event]] = {}
        self._lock = threading.RLock()
        self._paused = threading.Event()

    def run(self, macro_id: str, source_key: str | None = None) -> None:
        if self._paused.is_set():
            if self.notify:
                self.notify("warning", "Pánico activo: las macros están desactivadas")
            return
        profile = self.get_profile()
        macro = next((x for x in profile.macros if x.id == macro_id), None)
        if not macro or not macro.enabled:
            if self.notify:
                self.notify("warning", "La macro no existe o está desactivada")
            return
        if not profile.settings.get("macros_enabled", True):
            if self.notify:
                self.notify("warning", "Las macros están pausadas en este perfil")
            return
        macro.validate()

        with self._lock:
            existing = self._running.get(macro.id)
            if existing and existing[0].is_alive():
                if macro.mode == "toggle":
                    existing[1].set()
                return
            stop = threading.Event()
            thread = threading.Thread(
                target=self._worker,
                args=(macro, stop, source_key),
                name=f"Macro-{macro.name}",
                daemon=True,
            )
            self._running[macro.id] = (thread, stop)
            thread.start()

    def stop(self, macro_id: str) -> None:
        with self._lock:
            item = self._running.get(macro_id)
            if item:
                item[1].set()

    def stop_all(self) -> None:
        with self._lock:
            for _, stop in self._running.values():
                stop.set()

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._paused.set()
            self.stop_all()
        else:
            self._paused.clear()

    def running_ids(self) -> set[str]:
        with self._lock:
            return {key for key, item in self._running.items() if item[0].is_alive()}

    def _worker(self, macro: Macro, stop: threading.Event, source_key: str | None) -> None:
        try:
            loops = self._loop_count(macro)
            index = 0
            while not stop.is_set() and not self._paused.is_set() and (loops is None or index < loops):
                if macro.mode == "while_held" and source_key and not self._is_pressed(source_key):
                    break
                for step in macro.steps:
                    if stop.is_set() or self._paused.is_set():
                        break
                    if not step.enabled:
                        continue
                    try:
                        self.executor.execute(step.action)
                    except Exception:
                        if macro.stop_on_error:
                            raise
                    delay = step.delay_after_ms
                    if step.random_delay_ms:
                        delay += random.randint(0, step.random_delay_ms)
                    if self._wait(stop, delay / 1000):
                        break
                index += 1
                if self._wait(stop, max(0, macro.interval_ms) / 1000):
                    break
        except IbikiError as exc:
            log.warning("Macro %s detenida: %s", macro.name, exc)
            if self.notify and not getattr(exc, "ibiki_reported", False):
                self.notify("warning", f"Macro '{macro.name}': {exc}")
        except Exception as exc:
            log.exception("Macro %s falló", macro.name)
            if self.notify and not getattr(exc, "ibiki_reported", False):
                self.notify("error", f"Macro '{macro.name}': {exc}")
        finally:
            with self._lock:
                current = self._running.get(macro.id)
                if current and current[1] is stop:
                    self._running.pop(macro.id, None)

    @staticmethod
    def _loop_count(macro: Macro) -> int | None:
        if macro.mode in {"toggle", "while_held", "infinite"}:
            return None
        if macro.mode == "count":
            return macro.repeat_count
        return 1

    @staticmethod
    def _wait(stop: threading.Event, seconds: float) -> bool:
        return stop.wait(max(0.0, seconds))

    @staticmethod
    def _is_pressed(key: str) -> bool:
        try:
            if key.startswith("mouse:"):
                return mouse.is_pressed(key.split(":", 1)[1])
            import keyboard

            return bool(keyboard.is_pressed(key))
        except Exception:
            return False

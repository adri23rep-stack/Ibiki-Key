from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from ..models import Profile
from ..services.windows import foreground_window

log = logging.getLogger(__name__)


class ProfileWatcher:
    def __init__(
        self,
        get_profiles: Callable[[], list[Profile]],
        get_active_id: Callable[[], str],
        activate: Callable[[str, str], None],
    ):
        self.get_profiles = get_profiles
        self.get_active_id = get_active_id
        self.activate = activate
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_signature: tuple[str, str] = ("", "")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="ProfileWatcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _loop(self) -> None:
        while not self._stop.wait(0.75):
            try:
                process, title = foreground_window()
                signature = (process, title)
                if not process or signature == self._last_signature:
                    continue
                self._last_signature = signature
                profiles = self.get_profiles()
                matching = next(
                    (
                        p
                        for p in profiles
                        if p.settings.get("auto_switch", True)
                        and (
                            process in p.app_rules
                            or any(rule.lower() in title.lower() for rule in p.window_rules if rule)
                        )
                    ),
                    None,
                )
                if matching and matching.id != self.get_active_id():
                    self.activate(matching.id, f"Aplicación detectada: {process}")
            except Exception:
                log.exception("Error observando la ventana activa")

from __future__ import annotations

import logging
import os
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Callable

from ..errors import ActionBlocked, IbikiError
from ..models import Action, Profile
from ..services import mouse_backend as mouse
from ..services import windows

log = logging.getLogger(__name__)


class ActionExecutor:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.get_profile: Callable[[], Profile] | None = None
        self.run_macro: Callable[[str, str | None], None] | None = None
        self.stop_macro: Callable[[str], None] | None = None
        self.run_graph: Callable[[str], None] | None = None
        self.change_profile: Callable[[str], None] | None = None
        self.change_layer: Callable[[str, bool], None] | None = None
        self.set_variable: Callable[[str, Any, bool], None] | None = None
        self.get_variable: Callable[[str], Any] | None = None
        self.toast: Callable[[str, str], None] | None = None
        self.plugin_actions: dict[str, Callable[[Any, dict[str, Any], str, Profile | None], None]] = {}
        self.suspend_input: Callable[[float], None] | None = None
        self._local = threading.local()
        self._turbo: dict[str, threading.Event] = {}
        self._mod_tap: dict[str, dict[str, Any]] = {}
        self._held_keys: set[str] = set()
        self._held_mouse_buttons: set[str] = set()
        self._mouse_cancel = threading.Event()
        self._automation_paused = threading.Event()
        self._state_lock = threading.RLock()

    def execute(self, action: Action, *, phase: str = "press") -> None:
        if self._automation_paused.is_set():
            return
        action.validate()
        if action.type == "noop":
            return
        profile = self.get_profile() if self.get_profile else None
        try:
            self._execute(action, profile, phase)
        except IbikiError as exc:
            log.warning("Acción %s no disponible: %s", action.type, exc)
            if self.toast:
                self.toast("warning", str(exc))
            setattr(exc, "ibiki_reported", True)
            raise
        except Exception as exc:
            log.exception("Falló la acción %s", action.type)
            if self.toast:
                self.toast("error", f"No se pudo ejecutar {action.type}: {exc}")
            setattr(exc, "ibiki_reported", True)
            raise

    def _execute(self, action: Action, profile: Profile | None, phase: str) -> None:
        kind = action.type
        value = action.value
        options = action.options

        if kind in self.plugin_actions:
            self.plugin_actions[kind](value, options, phase, profile)
            return

        if kind == "paste_text":
            import keyboard
            import pyperclip

            pyperclip.copy(str(value))
            self._suspend(0.12)
            keyboard.send("ctrl+v")
            return

        if kind in {"key", "hotkey", "text", "media", "volume"}:
            import keyboard

            if kind == "text":
                interval = max(0.0, float(options.get("interval", 0.01)))
                self._suspend(max(0.08, len(str(value)) * interval + 0.08))
            else:
                self._suspend(0.06)

            if kind == "text":
                keyboard.write(str(value), delay=float(options.get("interval", 0.01)))
            elif kind == "key":
                key = str(value)
                recorded_event = options.get("event")
                if recorded_event == "down":
                    keyboard.press(key)
                    with self._state_lock:
                        self._held_keys.add(key)
                elif recorded_event == "up":
                    keyboard.release(key)
                    with self._state_lock:
                        self._held_keys.discard(key)
                elif options.get("hold"):
                    if phase == "press":
                        keyboard.press(key)
                        with self._state_lock:
                            self._held_keys.add(key)
                    else:
                        keyboard.release(key)
                        with self._state_lock:
                            self._held_keys.discard(key)
                else:
                    keyboard.send(key)
            elif kind == "hotkey":
                keyboard.send(str(value))
            elif kind == "media":
                aliases = {
                    "play_pause": "play/pause media",
                    "next": "next track",
                    "previous": "previous track",
                    "stop": "stop media",
                    "mute": "volume mute",
                }
                keyboard.send(aliases.get(str(value), str(value)))
            else:
                volume_keys = {
                    "up": "volume up",
                    "down": "volume down",
                    "mute": "volume mute",
                }
                if isinstance(value, (int, float)):
                    key = "volume up" if value > 0 else "volume down"
                    for _ in range(max(1, abs(int(value)) // 2)):
                        keyboard.send(key)
                else:
                    keyboard.send(volume_keys.get(str(value), str(value)))
            return

        if kind in {"mouse_button", "double_click", "scroll", "mouse_move"}:
            if self._mouse_cancel.is_set():
                return
            self._suspend(0.06)

            if kind == "mouse_button":
                button = str(value)
                recorded_event = options.get("event")
                if recorded_event == "down":
                    mouse.press(button)
                    with self._state_lock:
                        self._held_mouse_buttons.add(button)
                elif recorded_event == "up":
                    mouse.release(button)
                    with self._state_lock:
                        self._held_mouse_buttons.discard(button)
                elif options.get("hold"):
                    if phase == "press":
                        mouse.press(button)
                        with self._state_lock:
                            self._held_mouse_buttons.add(button)
                    else:
                        mouse.release(button)
                        with self._state_lock:
                            self._held_mouse_buttons.discard(button)
                else:
                    mouse.click(button)
            elif kind == "double_click":
                mouse.double_click(str(value or "left"), cancel=self._mouse_cancel)
            elif kind == "scroll":
                if isinstance(value, dict):
                    vertical = int(value.get("vertical", 0))
                    horizontal = int(value.get("horizontal", 0))
                    if vertical:
                        mouse.wheel(vertical)
                    if horizontal:
                        self._horizontal_scroll(horizontal)
                else:
                    mouse.wheel(int(value))
            else:
                if isinstance(value, dict):
                    mouse.move(
                        int(value.get("x", 0)),
                        int(value.get("y", 0)),
                        absolute=bool(value.get("absolute", False)),
                        duration=float(value.get("duration", 0)),
                        cancel=self._mouse_cancel,
                    )
            return

        if kind == "turbo":
            self._turbo_action(str(value), options, phase)
            return
        if kind == "mod_tap":
            self._mod_tap_action(value, options, phase)
            return

        if kind == "macro" and phase == "release" and options.get("stop_on_release"):
            if self.stop_macro:
                self.stop_macro(str(value))
            return
        if kind == "macro" and self.run_macro:
            self.run_macro(str(value), options.get("source_key"))
            return
        if kind == "logic_graph" and self.run_graph:
            self.run_graph(str(value))
            return
        if kind == "profile" and self.change_profile:
            self.change_profile(str(value))
            return
        if kind in {"layer_toggle", "layer_momentary"} and self.change_layer:
            momentary = kind == "layer_momentary"
            self.change_layer(str(value), momentary and phase == "release")
            return

        if kind == "wait":
            time.sleep(max(0, float(value)) / 1000)
            return
        if kind in {"set_variable", "toggle_variable"} and profile:
            name = str(value if kind == "toggle_variable" else options.get("name", value))
            if self.set_variable:
                self.set_variable(name, options.get("value"), kind == "toggle_variable")
            elif kind == "toggle_variable":
                profile.variables[name] = not bool(profile.variables.get(name, False))
            else:
                profile.variables[name] = options.get("value")
            return

        if kind == "open_program":
            self._require_trusted_external_actions(profile)
            target = os.path.expandvars(str(value))
            args = [target, *[str(x) for x in options.get("args", [])]]
            import subprocess

            subprocess.Popen(args, cwd=options.get("cwd") or None)
            return
        if kind == "open_folder":
            self._require_trusted_external_actions(profile)
            windows.open_target(os.path.expandvars(str(value)))
            return
        if kind == "open_url":
            self._require_trusted_external_actions(profile)
            webbrowser.open(str(value))
            return
        if kind in {"command", "powershell"}:
            self._require_trusted_external_actions(profile)
            if not profile or not profile.settings.get("scripts_allowed", False):
                raise ActionBlocked(
                    "CMD y PowerShell están bloqueados. Ve a Perfiles > Editar y activa "
                    "'Permitir CMD y PowerShell', o prueba la macro desde su editor para autorizarla."
                )
            windows.run_command(
                str(value),
                powershell=kind == "powershell",
                hidden=bool(options.get("hidden", True)),
            )
            return
        if kind == "brightness":
            windows.set_brightness(int(value))
            return
        if kind == "screenshot":
            import keyboard

            self._suspend(0.08)
            keyboard.send("print screen")
            return
        raise ValueError(f"La acción {kind} todavía no tiene ejecutor")

    @staticmethod
    def _require_trusted_external_actions(profile: Profile | None) -> None:
        if profile and not profile.settings.get("trusted_actions", True):
            raise ActionBlocked(
                "Este perfil importado no tiene permiso para abrir programas o enlaces. "
                "Revísalo y habilita 'Acciones externas' en Perfiles."
            )

    def _suspend(self, seconds: float) -> None:
        if self.suspend_input:
            self.suspend_input(seconds)

    def _turbo_action(self, key: str, options: dict[str, Any], phase: str) -> None:
        identifier = str(options.get("_mapping_id", key))
        with self._state_lock:
            if phase == "release":
                stop = self._turbo.pop(identifier, None)
                if stop:
                    stop.set()
                return
            if identifier in self._turbo:
                return
            stop = threading.Event()
            self._turbo[identifier] = stop
        rate = max(1.0, min(30.0, float(options.get("rate_hz", 10))))

        def worker() -> None:
            try:
                import keyboard

                while not stop.is_set():
                    self._suspend(max(0.055, 1.0 / rate))
                    keyboard.send(key)
                    stop.wait(1.0 / rate)
            finally:
                with self._state_lock:
                    if self._turbo.get(identifier) is stop:
                        self._turbo.pop(identifier, None)

        threading.Thread(target=worker, name=f"Turbo-{key}", daemon=True).start()

    def _mod_tap_action(self, value: Any, options: dict[str, Any], phase: str) -> None:
        if not isinstance(value, dict):
            raise ValueError("Mod-Tap necesita toque, mantener y tiempo")
        identifier = str(options.get("_mapping_id", value))
        tap = str(value.get("tap", "escape"))
        hold = str(value.get("hold", "left ctrl"))
        threshold = max(80, min(1000, int(value.get("threshold_ms", 180)))) / 1000
        if phase == "press":
            with self._state_lock:
                if identifier in self._mod_tap:
                    return
                cancel = threading.Event()
                state = {"cancel": cancel, "held": False, "hold": hold, "tap": tap}
                self._mod_tap[identifier] = state

            def hold_worker() -> None:
                if not cancel.wait(threshold):
                    import keyboard

                    with self._state_lock:
                        if self._mod_tap.get(identifier) is not state or cancel.is_set():
                            return
                        state["held"] = True
                        self._suspend(0.08)
                        keyboard.press(hold)

            threading.Thread(target=hold_worker, name="ModTap", daemon=True).start()
            return
        with self._state_lock:
            state = self._mod_tap.pop(identifier, None)
        if not state:
            return
        state["cancel"].set()
        import keyboard

        self._suspend(0.08)
        if state["held"]:
            keyboard.release(state["hold"])
        else:
            keyboard.send(state["tap"])

    def stop_dynamic_actions(self) -> None:
        self._mouse_cancel.set()
        with self._state_lock:
            turbo_stops = list(self._turbo.values())
            self._turbo.clear()
            mod_taps = list(self._mod_tap.values())
            self._mod_tap.clear()
            held_keys = list(self._held_keys)
            self._held_keys.clear()
            held_mouse = list(self._held_mouse_buttons)
            self._held_mouse_buttons.clear()
        for stop in turbo_stops:
            stop.set()
        for state in mod_taps:
            state["cancel"].set()
            if state.get("held"):
                try:
                    import keyboard

                    self._suspend(0.08)
                    keyboard.release(str(state["hold"]))
                except Exception:
                    log.exception("No se pudo liberar una tecla de Mod-Tap")
        if held_keys:
            try:
                import keyboard

                self._suspend(0.1)
                for key in held_keys:
                    keyboard.release(key)
            except Exception:
                log.exception("No se pudieron liberar todas las teclas mantenidas")
        if held_mouse:
            try:
                self._suspend(0.1)
                for button in held_mouse:
                    mouse.release(button)
            except Exception:
                log.exception("No se pudieron liberar todos los botones mantenidos")

    def resume_dynamic_actions(self) -> None:
        self._mouse_cancel.clear()

    def set_automation_paused(self, paused: bool) -> None:
        if paused:
            self._automation_paused.set()
            self._mouse_cancel.set()
        else:
            self._automation_paused.clear()
            self._mouse_cancel.clear()

    @staticmethod
    def _horizontal_scroll(amount: int) -> None:
        mouse.horizontal_wheel(amount)

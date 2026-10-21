from __future__ import annotations

import logging
import secrets
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from .constants import VERSION
from .engines.action_executor import ActionExecutor
from .engines.api_server import LocalApiServer
from .engines.keyboard_engine import KeyboardEngine
from .engines.logic_engine import LogicEngine
from .engines.macro_engine import MacroEngine
from .engines.monitor import InputMonitor
from .engines.mouse_engine import MouseEngine
from .engines.profile_watcher import ProfileWatcher
from .engines.plugin_manager import PluginManager
from .errors import EngineUnavailable, IbikiError
from .events import EventBus
from .models import AppState, Profile
from .storage import Storage

log = logging.getLogger(__name__)


class AppController(QObject):
    profile_activation_requested = Signal(str, str)
    variable_operation_requested = Signal(str, object, bool)
    macro_run_requested = Signal(str, object)

    def __init__(self, project_root: Path, storage: Storage, state: AppState, bus: EventBus):
        super().__init__()
        self.project_root = project_root
        self.storage = storage
        self.state = state
        self.bus = bus
        self.engine_running = False
        self.automation_paused = False
        self._input_capture_owner: object | None = None
        self._last_engine_warning = ""
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.save_now)
        self._restart_timer = QTimer(self)
        self._restart_timer.setSingleShot(True)
        self._restart_timer.timeout.connect(self.restart_engines)
        self.profile_activation_requested.connect(self.activate_profile)
        self.variable_operation_requested.connect(self._apply_variable_operation)
        self.macro_run_requested.connect(self._run_macro_requested)

        self.monitor = InputMonitor(self._on_monitor_payload)
        self.executor = ActionExecutor(project_root)
        self.plugin_manager = PluginManager(
            storage.data_dir / "plugins",
            self.executor,
            self.state.settings,
            self.notify,
        )
        self.plugin_manager.load_enabled()
        self.macro_engine = MacroEngine(self.executor, self.active_profile, self.notify)
        self.logic_engine = LogicEngine(self.executor, self.active_profile, self.notify)
        self.keyboard_engine = KeyboardEngine(self.executor, self.monitor, self.notify)
        self.mouse_engine = MouseEngine(self.executor, self.monitor, self.notify)

        self.executor.get_profile = self.active_profile
        self.executor.run_macro = self.macro_engine.run
        self.executor.stop_macro = self.macro_engine.stop
        self.executor.run_graph = self.logic_engine.run
        self.executor.change_profile = lambda value: self.profile_activation_requested.emit(value, "Acción")
        self.executor.change_layer = self.keyboard_engine.set_layer
        self.executor.set_variable = lambda name, value, toggle: self.variable_operation_requested.emit(
            name, value, toggle
        )
        self.executor.get_variable = self.get_variable
        self.executor.toast = self.notify
        self.executor.suspend_input = self._suspend_input
        self.keyboard_engine.pause_callback = self.toggle_automation_pause

        self.watcher = ProfileWatcher(
            lambda: list(self.state.profiles),
            lambda: self.state.active_profile_id,
            lambda profile_id, reason: self.profile_activation_requested.emit(profile_id, reason),
        )
        self.api = LocalApiServer(
            self.api_status,
            lambda profile_id, reason: self.profile_activation_requested.emit(profile_id, reason),
            lambda macro_id, source: self.macro_run_requested.emit(macro_id, source),
            lambda: dict(self.state.global_variables),
            lambda name, value: self.variable_operation_requested.emit(name, value, False),
        )

    def active_profile(self) -> Profile:
        return self.state.active_profile()

    def notify(self, level: str, message: str) -> None:
        logger = {
            "error": log.error,
            "warning": log.warning,
            "success": log.info,
            "info": log.info,
        }.get(level, log.info)
        logger("Actividad: %s", message)
        self.bus.toast_requested.emit(level, message)
        self.bus.log_event.emit(level, message)

    def start_engines(self) -> None:
        if self.engine_running:
            return
        profile = self.active_profile()
        self.executor.set_automation_paused(self.automation_paused)
        self.macro_engine.set_paused(self.automation_paused)
        self.logic_engine.set_paused(self.automation_paused)
        if not self.automation_paused:
            self.executor.resume_dynamic_actions()
        errors: list[str] = []
        try:
            self.keyboard_engine.start(profile)
        except EngineUnavailable as exc:
            errors.append(f"Teclado: {exc}")
            log.warning("No inició el teclado: %s", exc)
        except Exception as exc:
            errors.append(f"Teclado: {exc}")
            log.exception("No inició el teclado")
        try:
            self.mouse_engine.start(profile)
        except EngineUnavailable as exc:
            errors.append(f"Mouse: {exc}")
            log.warning("No inició el mouse: %s", exc)
        except Exception as exc:
            errors.append(f"Mouse: {exc}")
            log.exception("No inició el mouse")
        if profile.settings.get("auto_switch", True):
            self.watcher.start()
        self._apply_input_pause_state()
        self._apply_api_settings()
        self.engine_running = (
            self.keyboard_engine.running or self.mouse_engine.running or self.api.server is not None
        )
        detail = "Motores activos" if not errors else "; ".join(errors)
        self.bus.engine_state_changed.emit(self.engine_running, detail)
        if errors:
            if detail != self._last_engine_warning:
                self.notify("warning", detail)
            self._last_engine_warning = detail
        else:
            self._last_engine_warning = ""
            self.notify("success", detail)

    def stop_engines(self) -> None:
        self.macro_engine.stop_all()
        self.executor.stop_dynamic_actions()
        self.keyboard_engine.stop()
        self.mouse_engine.stop()
        self.watcher.stop()
        self.api.stop()
        self.engine_running = False
        self.bus.engine_state_changed.emit(False, "Motores detenidos")
        self.notify("info", "Remapeo y automatizaciones detenidos")

    def restart_engines(self) -> None:
        was_running = self.engine_running
        if was_running:
            self.stop_engines()
            self.start_engines()

    def activate_profile(self, profile_id_or_name: str, reason: str = "Manual") -> None:
        profile = next(
            (
                p
                for p in self.state.profiles
                if p.id == profile_id_or_name or p.name.lower() == profile_id_or_name.lower()
            ),
            None,
        )
        if not profile:
            raise IbikiError(f"No existe el perfil: {profile_id_or_name}")
        if self.state.active_profile_id == profile.id:
            return
        self.state.active_profile_id = profile.id
        self.schedule_save()
        if self.engine_running:
            self.macro_engine.stop_all()
            self.keyboard_engine.apply_profile(profile)
            self.mouse_engine.apply_profile(profile)
            self._apply_input_pause_state()
        self.bus.active_profile_changed.emit(profile.id, reason)
        self.bus.mappings_changed.emit()
        self.bus.macros_changed.emit()
        self.bus.graph_changed.emit()
        self.notify("success", f"Perfil activo: {profile.name}")

    def schedule_save(self, delay_ms: int = 350) -> None:
        self._save_timer.start(delay_ms)

    def save_now(self) -> None:
        try:
            self.storage.save(self.state)
        except Exception as exc:
            log.exception("No se pudo guardar")
            self.notify("error", f"No se pudo guardar: {exc}")

    def profile_changed(self, restart: bool = True) -> None:
        self.schedule_save()
        self.bus.mappings_changed.emit()
        self.bus.macros_changed.emit()
        self.bus.graph_changed.emit()
        if restart and self.engine_running:
            self._restart_timer.start(400)

    def set_variable(self, name: str, value: Any) -> None:
        self.state.global_variables[name] = value
        self.schedule_save()

    def get_variable(self, name: str) -> Any:
        if name in self.state.global_variables:
            return self.state.global_variables[name]
        return self.active_profile().variables.get(name)

    def _apply_variable_operation(self, name: str, value: Any, toggle: bool) -> None:
        if toggle:
            value = not bool(self.get_variable(name))
        self.set_variable(name, value)

    def _run_macro_requested(self, macro_id: str, source: object) -> None:
        self.macro_engine.run(macro_id, str(source) if source else None)

    def toggle_automation_pause(self) -> None:
        paused = not self.automation_paused
        self.automation_paused = paused
        self._apply_input_pause_state()
        self.executor.set_automation_paused(paused)
        self.macro_engine.set_paused(paused)
        self.logic_engine.set_paused(paused)
        if paused:
            self.macro_engine.stop_all()
            self.executor.stop_dynamic_actions()
        else:
            self.executor.resume_dynamic_actions()
        self.bus.automation_pause_changed.emit(paused)
        self.notify(
            "warning" if paused else "success",
            "PÁNICO: teclado, macros y cambios del mouse desactivados"
            if paused
            else "Automatización reanudada y ajustes del mouse reaplicados",
        )

    def begin_input_capture(self, owner: object) -> bool:
        if self._input_capture_owner is not None and self._input_capture_owner is not owner:
            return False
        self._input_capture_owner = owner
        self._apply_input_pause_state()
        return True

    def end_input_capture(self, owner: object) -> None:
        if self._input_capture_owner is owner:
            self._input_capture_owner = None
            self._apply_input_pause_state()

    def _apply_input_pause_state(self) -> None:
        capture_paused = self._input_capture_owner is not None
        self.keyboard_engine.paused = bool(self.automation_paused or capture_paused)
        self.mouse_engine.set_pause_state(
            automation_paused=self.automation_paused,
            capture_paused=capture_paused,
        )

    def _on_monitor_payload(self, payload: dict[str, Any]) -> None:
        event = payload.get("event", {})
        stats = payload.get("stats", {})
        self.bus.input_event.emit(event)
        self.bus.stats_changed.emit(stats)

    def _suspend_input(self, seconds: float) -> None:
        self.keyboard_engine.suspend_for(seconds)
        self.mouse_engine.suspend_for(seconds)

    def api_status(self) -> dict[str, Any]:
        profile = self.active_profile()
        return {
            "ok": True,
            "app": "Ibiki Key",
            "version": VERSION,
            "engine_running": self.engine_running,
            "automation_paused": self.automation_paused,
            "active_profile": {"id": profile.id, "name": profile.name},
            "profiles": [{"id": p.id, "name": p.name} for p in self.state.profiles],
            "macros": [
                {"id": m.id, "name": m.name, "scope": m.scope}
                for m in profile.macros
            ],
        }

    def _apply_api_settings(self) -> None:
        settings = self.state.settings
        if not settings.get("api_enabled", False):
            return
        token = str(settings.get("api_token") or "")
        if not token:
            token = secrets.token_urlsafe(24)
            settings["api_token"] = token
            self.schedule_save()
        try:
            self.api.start(int(settings.get("api_port", 8765)), token)
        except OSError as exc:
            self.notify("error", f"No se pudo iniciar la API local: {exc}")

    def shutdown(self) -> None:
        self.stop_engines()
        self.plugin_manager.unload_all()
        self.save_now()

    def reload_plugins(self) -> None:
        plugins = self.plugin_manager.load_enabled()
        loaded = sum(1 for item in plugins if item.loaded)
        self.notify("success", f"Plugins recargados: {loaded} activos")

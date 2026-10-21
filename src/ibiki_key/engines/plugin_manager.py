from __future__ import annotations

import importlib.util
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from ..models import Profile
from .action_executor import ActionExecutor

log = logging.getLogger(__name__)


@dataclass(slots=True)
class PluginInfo:
    id: str
    name: str
    version: str
    path: Path
    entry: str
    description: str = ""
    loaded: bool = False
    error: str = ""


class PluginContext:
    def __init__(
        self,
        plugin: PluginInfo,
        executor: ActionExecutor,
        labels: dict[str, str],
        notify: Callable[[str, str], None],
    ):
        self.plugin = plugin
        self.executor = executor
        self.labels = labels
        self.notify = notify

    def register_action(
        self,
        name: str,
        label: str,
        callback: Callable[[Any, dict[str, Any], str, Profile | None], None],
    ) -> str:
        if not re.fullmatch(r"[a-z0-9_]+", name):
            raise ValueError("El nombre de una acción solo admite a-z, 0-9 y guion bajo")
        action_type = f"plugin.{self.plugin.id}.{name}"
        self.executor.plugin_actions[action_type] = callback
        self.labels[action_type] = label
        return action_type


class PluginManager:
    def __init__(
        self,
        directory: Path,
        executor: ActionExecutor,
        settings: dict[str, Any],
        notify: Callable[[str, str], None],
    ):
        self.directory = directory
        self.executor = executor
        self.settings = settings
        self.notify = notify
        self.action_labels: dict[str, str] = {}
        self.loaded_modules: dict[str, ModuleType] = {}
        directory.mkdir(parents=True, exist_ok=True)

    def discover(self) -> list[PluginInfo]:
        found: list[PluginInfo] = []
        for manifest in sorted(self.directory.glob("*/plugin.json")):
            try:
                raw = json.loads(manifest.read_text(encoding="utf-8"))
                plugin_id = str(raw.get("id", ""))
                if not re.fullmatch(r"[a-z0-9_]+", plugin_id):
                    raise ValueError("id inválido")
                found.append(
                    PluginInfo(
                        id=plugin_id,
                        name=str(raw.get("name") or plugin_id),
                        version=str(raw.get("version") or "0.0.0"),
                        path=manifest.parent,
                        entry=str(raw.get("entry") or "plugin.py"),
                        description=str(raw.get("description") or ""),
                    )
                )
            except Exception as exc:
                log.warning("Plugin inválido en %s: %s", manifest, exc)
        return found

    def load_enabled(self) -> list[PluginInfo]:
        self.unload_all()
        enabled = set(self.settings.get("enabled_plugins", []))
        plugins = self.discover()
        for plugin in plugins:
            if plugin.id not in enabled:
                continue
            try:
                entry = (plugin.path / plugin.entry).resolve()
                if plugin.path.resolve() not in entry.parents or not entry.is_file():
                    raise ValueError("El archivo de entrada está fuera de la carpeta del plugin")
                module_name = f"ibiki_user_plugin_{plugin.id}"
                spec = importlib.util.spec_from_file_location(module_name, entry)
                if not spec or not spec.loader:
                    raise ImportError("No se pudo preparar el módulo")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                register = getattr(module, "register", None)
                if not callable(register):
                    raise ValueError("El plugin necesita una función register(context)")
                context = PluginContext(plugin, self.executor, self.action_labels, self.notify)
                register(context)
                self.loaded_modules[plugin.id] = module
                plugin.loaded = True
                log.info("Plugin cargado: %s %s", plugin.name, plugin.version)
            except Exception as exc:
                plugin.error = str(exc)
                log.exception("No se pudo cargar el plugin %s", plugin.id)
                self.notify("error", f"Plugin '{plugin.name}': {exc}")
        return plugins

    def unload_all(self) -> None:
        for module in self.loaded_modules.values():
            shutdown = getattr(module, "shutdown", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception:
                    log.exception("Falló el cierre de un plugin")
        self.loaded_modules.clear()
        self.executor.plugin_actions.clear()
        self.action_labels.clear()

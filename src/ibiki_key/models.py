from __future__ import annotations

import copy
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .constants import SCHEMA_VERSION
from .errors import ValidationError


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_process_name(value: str) -> str:
    value = value.strip().lower().replace("\\", "/").rsplit("/", 1)[-1]
    if value and "." not in value:
        value += ".exe"
    return value


ACTION_TYPES = {
    "key",
    "hotkey",
    "text",
    "paste_text",
    "mouse_button",
    "mouse_move",
    "scroll",
    "double_click",
    "macro",
    "open_program",
    "open_folder",
    "open_url",
    "command",
    "powershell",
    "media",
    "volume",
    "brightness",
    "screenshot",
    "profile",
    "layer_momentary",
    "layer_toggle",
    "logic_graph",
    "wait",
    "set_variable",
    "toggle_variable",
    "turbo",
    "mod_tap",
    "noop",
}


@dataclass(slots=True)
class Action:
    type: str = "key"
    value: Any = "a"
    options: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.type not in ACTION_TYPES and not self.type.startswith("plugin."):
            raise ValidationError(f"Acción desconocida: {self.type}")
        if self.type not in {"noop", "screenshot"} and self.value is None:
            raise ValidationError(f"La acción {self.type} necesita un valor")

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "Action":
        raw = raw or {}
        return cls(
            type=str(raw.get("type", "key")),
            value=raw.get("value", "a"),
            options=dict(raw.get("options") or {}),
        )


@dataclass(slots=True)
class Mapping:
    id: str = field(default_factory=lambda: new_id("map"))
    source: str = "f13"
    trigger: str = "press"
    action: Action = field(default_factory=Action)
    layer: str = "Base"
    enabled: bool = True
    suppress: bool = True
    debounce_ms: int = 0
    note: str = ""

    def validate(self) -> None:
        if not self.source.strip():
            raise ValidationError("La tecla de origen está vacía")
        if self.trigger not in {"press", "release", "hold", "double_tap"}:
            raise ValidationError(f"Disparador no válido: {self.trigger}")
        if not self.layer.strip():
            raise ValidationError("La capa está vacía")
        if not 0 <= int(self.debounce_ms) <= 5000:
            raise ValidationError("El anti rebote debe estar entre 0 y 5000 ms")
        self.action.validate()
        if self.action.type in {"turbo", "mod_tap"} and self.trigger != "hold":
            raise ValidationError(
                f"La acción {self.action.type} necesita el disparador 'Mientras se mantiene'"
            )
        if "+" in self.source and (
            self.trigger == "hold" or self.action.type in {"turbo", "mod_tap", "layer_momentary"}
        ):
            raise ValidationError(
                "Las acciones que necesitan pulsar y soltar deben usar una tecla física, no una combinación"
            )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Mapping":
        return cls(
            id=str(raw.get("id") or new_id("map")),
            source=str(raw.get("source", "f13")),
            trigger=str(raw.get("trigger", "press")),
            action=Action.from_dict(raw.get("action")),
            layer=str(raw.get("layer", "Base")),
            enabled=bool(raw.get("enabled", True)),
            suppress=bool(raw.get("suppress", True)),
            debounce_ms=int(raw.get("debounce_ms", 0)),
            note=str(raw.get("note", "")),
        )


@dataclass(slots=True)
class MacroStep:
    id: str = field(default_factory=lambda: new_id("step"))
    action: Action = field(default_factory=lambda: Action("wait", 100))
    delay_after_ms: int = 0
    random_delay_ms: int = 0
    enabled: bool = True

    def validate(self) -> None:
        self.action.validate()
        if not 0 <= self.delay_after_ms <= 3_600_000:
            raise ValidationError("El retraso debe estar entre 0 y 3,600,000 ms")
        if not 0 <= self.random_delay_ms <= 60_000:
            raise ValidationError("El retraso aleatorio debe ser menor a 60 segundos")

    def clone(self) -> "MacroStep":
        cloned = copy.deepcopy(self)
        cloned.id = new_id("step")
        return cloned

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "MacroStep":
        return cls(
            id=str(raw.get("id") or new_id("step")),
            action=Action.from_dict(raw.get("action")),
            delay_after_ms=int(raw.get("delay_after_ms", 0)),
            random_delay_ms=int(raw.get("random_delay_ms", 0)),
            enabled=bool(raw.get("enabled", True)),
        )


@dataclass(slots=True)
class Macro:
    id: str = field(default_factory=lambda: new_id("macro"))
    name: str = "Nueva macro"
    scope: str = "general"
    steps: list[MacroStep] = field(default_factory=list)
    mode: str = "once"
    repeat_count: int = 1
    interval_ms: int = 0
    enabled: bool = True
    stop_on_error: bool = True

    def validate(self) -> None:
        if not self.name.strip():
            raise ValidationError("La macro necesita un nombre")
        if self.scope not in {"general", "mouse"}:
            raise ValidationError(f"Tipo de macro no válido: {self.scope}")
        if self.mode not in {"once", "count", "toggle", "while_held", "infinite"}:
            raise ValidationError(f"Modo de macro no válido: {self.mode}")
        if not 1 <= self.repeat_count <= 1_000_000:
            raise ValidationError("Las repeticiones deben ser mayores a cero")
        for step in self.steps:
            step.validate()

    def clone(self, name: str | None = None) -> "Macro":
        cloned = copy.deepcopy(self)
        old_id = cloned.id
        cloned.id = new_id("macro")
        cloned.name = name or f"{self.name} - copia"
        for step in cloned.steps:
            step.id = new_id("step")
            if step.action.type == "macro" and str(step.action.value) == old_id:
                step.action.value = cloned.id
        return cloned

    def duration_bounds_ms(self) -> tuple[int, int] | None:
        """Devuelve la duración mínima/máxima estimada o None si no tiene fin fijo."""
        if self.mode in {"toggle", "while_held", "infinite"}:
            return None
        minimum = 0
        maximum = 0
        for step in self.steps:
            if not step.enabled:
                continue
            action_wait = 0
            if step.action.type == "wait":
                try:
                    action_wait = max(0, int(float(step.action.value)))
                except (TypeError, ValueError):
                    action_wait = 0
            minimum += action_wait + max(0, int(step.delay_after_ms))
            maximum += action_wait + max(0, int(step.delay_after_ms)) + max(
                0, int(step.random_delay_ms)
            )
        repeats = self.repeat_count if self.mode == "count" else 1
        interval_total = max(0, repeats - 1) * max(0, int(self.interval_ms))
        return minimum * repeats + interval_total, maximum * repeats + interval_total

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Macro":
        return cls(
            id=str(raw.get("id") or new_id("macro")),
            name=str(raw.get("name", "Nueva macro")),
            scope=str(raw.get("scope", "general")),
            steps=[MacroStep.from_dict(x) for x in raw.get("steps", [])],
            mode=str(raw.get("mode", "once")),
            repeat_count=int(raw.get("repeat_count", 1)),
            interval_ms=int(raw.get("interval_ms", 0)),
            enabled=bool(raw.get("enabled", True)),
            stop_on_error=bool(raw.get("stop_on_error", True)),
        )


@dataclass(slots=True)
class LogicNode:
    id: str = field(default_factory=lambda: new_id("node"))
    kind: str = "trigger_key"
    title: str = "Tecla"
    x: float = 0.0
    y: float = 0.0
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LogicNode":
        return cls(
            id=str(raw.get("id") or new_id("node")),
            kind=str(raw.get("kind", "trigger_key")),
            title=str(raw.get("title", "Nodo")),
            x=float(raw.get("x", 0)),
            y=float(raw.get("y", 0)),
            config=dict(raw.get("config") or {}),
        )


@dataclass(slots=True)
class LogicEdge:
    source: str = ""
    target: str = ""
    branch: str = "next"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LogicEdge":
        return cls(
            source=str(raw.get("source", "")),
            target=str(raw.get("target", "")),
            branch=str(raw.get("branch", "next")),
        )


@dataclass(slots=True)
class LogicGraph:
    id: str = field(default_factory=lambda: new_id("graph"))
    name: str = "Nueva lógica"
    nodes: list[LogicNode] = field(default_factory=list)
    edges: list[LogicEdge] = field(default_factory=list)
    enabled: bool = True

    def validate(self) -> None:
        ids = {node.id for node in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValidationError("Hay nodos duplicados")
        for edge in self.edges:
            if edge.source not in ids or edge.target not in ids:
                raise ValidationError("Hay una conexión que apunta a un nodo inexistente")
            if edge.source == edge.target:
                raise ValidationError("Un nodo no puede conectarse consigo mismo")
            if edge.branch not in {"next", "yes", "no", "timeout", "always"}:
                raise ValidationError(f"Salida de conexión no válida: {edge.branch}")

    def clone(self, name: str | None = None) -> "LogicGraph":
        cloned = copy.deepcopy(self)
        old_graph_id = cloned.id
        cloned.id = new_id("graph")
        cloned.name = name or f"{self.name} - copia"
        id_map: dict[str, str] = {}
        for node in cloned.nodes:
            old_id = node.id
            node.id = new_id("node")
            id_map[old_id] = node.id
        for edge in cloned.edges:
            edge.source = id_map.get(edge.source, edge.source)
            edge.target = id_map.get(edge.target, edge.target)
        for node in cloned.nodes:
            action = node.config.get("action") if node.kind == "action" else None
            if isinstance(action, dict) and action.get("type") == "logic_graph":
                if str(action.get("value")) == old_graph_id:
                    action["value"] = cloned.id
        return cloned

    def diagnostics(self) -> list[tuple[str, str]]:
        """Analiza el flujo sin impedir patrones avanzados como los ciclos controlados."""
        issues: list[tuple[str, str]] = []
        try:
            self.validate()
        except ValidationError as exc:
            issues.append(("error", str(exc)))
            return issues
        if not self.nodes:
            return [("error", "El flujo no contiene nodos")]

        ids = {node.id for node in self.nodes}
        incoming = {edge.target for edge in self.edges}
        starts = {
            node.id
            for node in self.nodes
            if node.kind.startswith("trigger_") or node.id not in incoming
        }
        if not starts:
            issues.append(("error", "No hay un nodo inicial; el flujo es un ciclo cerrado"))

        adjacency: dict[str, list[str]] = {node_id: [] for node_id in ids}
        edge_keys: set[tuple[str, str, str]] = set()
        for edge in self.edges:
            adjacency[edge.source].append(edge.target)
            key = (edge.source, edge.target, edge.branch)
            if key in edge_keys:
                issues.append(
                    ("warning", "Hay conexiones duplicadas que ejecutarán la misma rama dos veces")
                )
            edge_keys.add(key)

        reachable: set[str] = set()
        pending = list(starts)
        while pending:
            node_id = pending.pop()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            pending.extend(adjacency.get(node_id, []))
        unreachable = ids - reachable
        if unreachable:
            issues.append(("warning", f"Hay {len(unreachable)} nodo(s) inaccesible(s)"))

        condition_kinds = {"timer"}
        for node in self.nodes:
            branches = {edge.branch for edge in self.edges if edge.source == node.id}
            if node.kind.startswith("condition_") or node.kind in condition_kinds:
                missing = [branch for branch in ("yes", "no") if branch not in branches]
                if missing:
                    issues.append(
                        (
                            "warning",
                            f"'{node.title}' no tiene salida(s): {', '.join(missing)}",
                        )
                    )
            elif node.kind == "wait_event" and "timeout" not in branches:
                issues.append(("warning", f"'{node.title}' no controla la salida timeout"))

        visiting: set[str] = set()
        visited: set[str] = set()

        def has_cycle(node_id: str) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False
            visiting.add(node_id)
            for target in adjacency.get(node_id, []):
                if has_cycle(target):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        if any(has_cycle(node_id) for node_id in ids if node_id not in visited):
            issues.append(
                (
                    "warning",
                    "El flujo contiene un ciclo; la ejecución se detendrá al alcanzar 250 pasos",
                )
            )
        return issues

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LogicGraph":
        return cls(
            id=str(raw.get("id") or new_id("graph")),
            name=str(raw.get("name", "Nueva lógica")),
            nodes=[LogicNode.from_dict(x) for x in raw.get("nodes", [])],
            edges=[LogicEdge.from_dict(x) for x in raw.get("edges", [])],
            enabled=bool(raw.get("enabled", True)),
        )


@dataclass(slots=True)
class MouseSettings:
    cursor_speed: int = 10
    double_click_ms: int = 500
    scroll_lines: int = 3
    gestures_enabled: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "MouseSettings":
        raw = raw or {}
        return cls(
            cursor_speed=max(1, min(20, int(raw.get("cursor_speed", 10)))),
            double_click_ms=max(100, min(2000, int(raw.get("double_click_ms", 500)))),
            scroll_lines=max(1, min(100, int(raw.get("scroll_lines", 3)))),
            gestures_enabled=bool(raw.get("gestures_enabled", False)),
        )


@dataclass(slots=True)
class Profile:
    id: str = field(default_factory=lambda: new_id("profile"))
    name: str = "Perfil nuevo"
    color: str = "#8B5CF6"
    app_rules: list[str] = field(default_factory=list)
    window_rules: list[str] = field(default_factory=list)
    mappings: list[Mapping] = field(default_factory=list)
    mouse_mappings: list[Mapping] = field(default_factory=list)
    macros: list[Macro] = field(default_factory=list)
    logic_graphs: list[LogicGraph] = field(default_factory=list)
    layers: list[str] = field(default_factory=lambda: ["Base"])
    active_layer: str = "Base"
    mouse: MouseSettings = field(default_factory=MouseSettings)
    variables: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def validate(self) -> None:
        if not self.name.strip():
            raise ValidationError("El perfil necesita un nombre")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", self.color):
            raise ValidationError("El color del perfil no es válido")
        self.layers = list(dict.fromkeys(x.strip() for x in self.layers if x.strip()))
        if "Base" not in self.layers:
            self.layers.insert(0, "Base")
        if self.active_layer not in self.layers:
            self.active_layer = "Base"
        self.app_rules = list(
            dict.fromkeys(filter(None, (normalize_process_name(x) for x in self.app_rules)))
        )
        whitelist = self.settings.get("whitelist_programs", [])
        self.settings["whitelist_programs"] = list(
            dict.fromkeys(filter(None, (normalize_process_name(str(x)) for x in whitelist)))
        )
        for mapping in [*self.mappings, *self.mouse_mappings]:
            mapping.validate()
            if mapping.layer not in self.layers:
                raise ValidationError(
                    f"La asignación {mapping.source} usa una capa inexistente: {mapping.layer}"
                )
        for macro in self.macros:
            macro.validate()
        for graph in self.logic_graphs:
            graph.validate()

    def clone(self, name: str | None = None) -> "Profile":
        cloned = copy.deepcopy(self)
        cloned.id = new_id("profile")
        cloned.name = name or f"{self.name} - copia"
        cloned.created_at = utc_now()
        cloned.updated_at = cloned.created_at
        return cloned

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Profile":
        profile = cls(
            id=str(raw.get("id") or new_id("profile")),
            name=str(raw.get("name", "Perfil nuevo")),
            color=str(raw.get("color", "#8B5CF6")),
            app_rules=[str(x) for x in raw.get("app_rules", [])],
            window_rules=[str(x) for x in raw.get("window_rules", [])],
            mappings=[Mapping.from_dict(x) for x in raw.get("mappings", [])],
            mouse_mappings=[Mapping.from_dict(x) for x in raw.get("mouse_mappings", [])],
            macros=[Macro.from_dict(x) for x in raw.get("macros", [])],
            logic_graphs=[LogicGraph.from_dict(x) for x in raw.get("logic_graphs", [])],
            layers=[str(x) for x in raw.get("layers", ["Base"])],
            active_layer=str(raw.get("active_layer", "Base")),
            mouse=MouseSettings.from_dict(raw.get("mouse")),
            variables=dict(raw.get("variables") or {}),
            settings=dict(raw.get("settings") or {}),
            created_at=str(raw.get("created_at") or utc_now()),
            updated_at=str(raw.get("updated_at") or utc_now()),
        )
        profile.validate()
        return profile

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AppState:
    schema_version: int = SCHEMA_VERSION
    active_profile_id: str = ""
    profiles: list[Profile] = field(default_factory=list)
    global_variables: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AppState":
        profiles = [Profile.from_dict(x) for x in raw.get("profiles", [])]
        active = str(raw.get("active_profile_id", ""))
        if not profiles:
            profiles = [default_profile()]
        if active not in {p.id for p in profiles}:
            active = profiles[0].id
        return cls(
            schema_version=int(raw.get("schema_version", SCHEMA_VERSION)),
            active_profile_id=active,
            profiles=profiles,
            global_variables=dict(raw.get("global_variables") or {}),
            settings=dict(raw.get("settings") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def active_profile(self) -> Profile:
        for profile in self.profiles:
            if profile.id == self.active_profile_id:
                return profile
        self.active_profile_id = self.profiles[0].id
        return self.profiles[0]


def default_profile() -> Profile:
    return Profile(
        name="Escritorio",
        color="#8B5CF6",
        mappings=[],
        macros=[
            Macro(
                name="Abrir Administrador de tareas",
                steps=[MacroStep(action=Action("hotkey", "ctrl+shift+esc"))],
            )
        ],
        logic_graphs=[],
        settings={
            "auto_switch": True,
            "debounce_ms": 0,
            "low_latency": False,
            "macros_enabled": True,
            "scripts_allowed": False,
            "trusted_actions": True,
        },
    )

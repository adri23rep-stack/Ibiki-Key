from __future__ import annotations

from typing import Any


ACTION_LABELS: dict[str, str] = {
    "key": "Enviar una tecla",
    "hotkey": "Combinación de teclas",
    "text": "Escribir texto",
    "paste_text": "Pegar texto",
    "mouse_button": "Botón del mouse",
    "mouse_move": "Mover cursor",
    "scroll": "Scroll",
    "double_click": "Doble clic",
    "macro": "Ejecutar macro",
    "open_program": "Abrir programa",
    "open_folder": "Abrir carpeta",
    "open_url": "Abrir enlace",
    "command": "Ejecutar CMD",
    "powershell": "Ejecutar PowerShell",
    "media": "Control multimedia",
    "volume": "Cambiar volumen",
    "brightness": "Cambiar brillo",
    "screenshot": "Captura de pantalla",
    "profile": "Cambiar perfil",
    "layer_momentary": "Capa mientras se mantiene",
    "layer_toggle": "Alternar capa",
    "logic_graph": "Ejecutar lógica visual",
    "wait": "Esperar",
    "set_variable": "Asignar variable",
    "toggle_variable": "Alternar variable",
    "turbo": "Turbo mientras se mantiene",
    "mod_tap": "Mod-Tap (toque / mantener)",
    "noop": "Desactivar tecla / no hacer nada",
}

TRIGGER_LABELS = {
    "press": "Al presionar",
    "release": "Al soltar",
    "hold": "Mientras se mantiene",
    "double_tap": "Doble toque",
}

MOUSE_SOURCES = [
    ("left", "Clic izquierdo"),
    ("right", "Clic derecho"),
    ("middle", "Botón central"),
    ("x", "Lateral 1"),
    ("x2", "Lateral 2"),
    ("wheel_up", "Rueda arriba"),
    ("wheel_down", "Rueda abajo"),
    ("wheel_left", "Rueda horizontal izquierda"),
    ("wheel_right", "Rueda horizontal derecha"),
    ("gesture:up", "Gesto arriba"),
    ("gesture:down", "Gesto abajo"),
    ("gesture:left", "Gesto izquierda"),
    ("gesture:right", "Gesto derecha"),
]

NODE_CATALOG: dict[str, tuple[str, str, dict[str, Any]]] = {
    "trigger_key": ("Disparador · Tecla", "trigger", {"key": "f13"}),
    "trigger_mouse": ("Disparador · Mouse", "trigger", {"button": "x"}),
    "condition_process": ("Condición · Programa abierto", "condition", {"process": "chrome.exe"}),
    "condition_active_process": (
        "Condición · Programa activo",
        "condition",
        {"process": "chrome.exe"},
    ),
    "condition_window": ("Condición · Título de ventana", "condition", {"contains": ""}),
    "condition_time": ("Condición · Horario", "condition", {"start": "08:00", "end": "22:00"}),
    "condition_capslock": ("Condición · Bloq Mayús", "condition", {}),
    "condition_idle": ("Condición · Usuario inactivo", "condition", {"seconds": 60}),
    "condition_variable": ("Condición · Variable", "condition", {"name": "modo", "equals": True}),
    "condition_key": ("Condición · Tecla presionada", "condition", {"key": "shift"}),
    "timer": ("Condición · Temporizador", "condition", {"name": "timer", "seconds": 1}),
    "delay": ("Esperar", "utility", {"milliseconds": 250}),
    "wait_event": (
        "Esperar evento",
        "utility",
        {"event": "process", "value": "notepad.exe", "timeout": 30},
    ),
    "set_variable": ("Asignar variable", "utility", {"name": "modo", "value": True}),
    "action": ("Ejecutar acción", "action", {"action": {"type": "hotkey", "value": "ctrl+t", "options": {}}}),
}

CATEGORY_COLORS = {
    "trigger": "#22D3EE",
    "condition": "#F59E0B",
    "action": "#A78BFA",
    "utility": "#60A5FA",
}

CATEGORY_LABELS = {
    "trigger": "INICIO · DISPARADOR",
    "condition": "DECISIÓN · CONDICIÓN",
    "action": "EJECUTAR · ACCIÓN",
    "utility": "FLUJO · CONTROL",
}

CATEGORY_PREFIXES = {
    "trigger": "TRG",
    "condition": "CON",
    "action": "ACT",
    "utility": "FLW",
}


def action_summary(kind: str, value: Any) -> str:
    label = ACTION_LABELS.get(kind, kind)
    if kind in {"noop", "screenshot"}:
        return label
    if isinstance(value, dict):
        shown = ", ".join(f"{k}={v}" for k, v in value.items())
    else:
        shown = str(value)
    return f"{label}: {shown}"


def node_display_id(kind: str, node_id: str) -> str:
    category = NODE_CATALOG.get(kind, ("Nodo", "utility", {}))[1]
    suffix = node_id.rsplit("_", 1)[-1][-6:].upper()
    return f"{CATEGORY_PREFIXES.get(category, 'NOD')}-{suffix or 'NUEVO'}"


def node_summary(kind: str, config: dict[str, Any]) -> str:
    if kind == "action":
        action = config.get("action") or {}
        return action_summary(str(action.get("type", "noop")), action.get("value", ""))
    if kind == "trigger_key":
        return f"Tecla: {config.get('key', 'sin asignar')}"
    if kind == "trigger_mouse":
        return f"Botón: {config.get('button', 'sin asignar')}"
    if kind == "condition_process":
        return f"Programa abierto: {config.get('process', 'sin configurar')}"
    if kind == "condition_active_process":
        return f"Programa activo: {config.get('process', 'sin configurar')}"
    if kind == "condition_window":
        return f"Título contiene: {config.get('contains', 'sin configurar')}"
    if kind == "condition_time":
        return f"Horario: {config.get('start', '00:00')}–{config.get('end', '23:59')}"
    if kind == "condition_capslock":
        return "¿Bloq Mayús está activo?"
    if kind == "condition_idle":
        return f"Inactividad mínima: {config.get('seconds', 60)} s"
    if kind == "condition_variable":
        return f"{config.get('name', 'variable')} = {config.get('equals', True)}"
    if kind == "condition_key":
        return f"¿Está presionada: {config.get('key', 'shift')}?"
    if kind == "timer":
        return f"Temporizador {config.get('name', 'timer')}: {config.get('seconds', 1)} s"
    if kind == "delay":
        return f"Pausa: {config.get('milliseconds', 250)} ms"
    if kind == "wait_event":
        return (
            f"Evento {config.get('event', 'process')}: {config.get('value', '')} "
            f"(máx. {config.get('timeout', 30)} s)"
        )
    if kind == "set_variable":
        return f"{config.get('name', 'variable')} ← {config.get('value', True)}"
    if not config:
        return "Sin configuración"
    return " · ".join(f"{key}: {value}" for key, value in config.items())[:110]


def node_output_hint(kind: str) -> str:
    if kind.startswith("condition_") or kind == "timer":
        return "SALIDAS  ·  SÍ  /  NO"
    if kind == "wait_event":
        return "SALIDAS  ·  SIGUIENTE  /  TIEMPO"
    return "SALIDA  ·  SIGUIENTE"

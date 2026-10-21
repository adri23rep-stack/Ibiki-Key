from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable

from ..errors import IbikiError
from ..models import Action, LogicGraph, LogicNode, Profile
from ..services import windows
from .action_executor import ActionExecutor

log = logging.getLogger(__name__)


class LogicEngine:
    MAX_STEPS = 250

    def __init__(
        self,
        executor: ActionExecutor,
        get_profile: Callable[[], Profile],
        notify: Callable[[str, str], None] | None = None,
    ):
        self.executor = executor
        self.get_profile = get_profile
        self.notify = notify
        self._timers: dict[str, float] = {}
        self._paused = threading.Event()

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._paused.set()
        else:
            self._paused.clear()

    def run(self, graph_id: str) -> None:
        if self._paused.is_set():
            if self.notify:
                self.notify("warning", "Pánico activo: la lógica visual está desactivada")
            return
        profile = self.get_profile()
        graph = next((x for x in profile.logic_graphs if x.id == graph_id), None)
        if not graph or not graph.enabled:
            if self.notify:
                self.notify("warning", "La lógica no existe o está desactivada")
            return
        graph.validate()
        thread = threading.Thread(
            target=self._execute_graph,
            args=(graph,),
            name=f"Logic-{graph.name}",
            daemon=True,
        )
        thread.start()

    def test(self, graph: LogicGraph, start_id: str | None = None) -> None:
        if self._paused.is_set():
            if self.notify:
                self.notify("warning", "Pánico activo: la lógica visual está desactivada")
            return
        graph.validate()
        thread = threading.Thread(
            target=self._execute_graph,
            args=(graph, start_id),
            name=f"LogicTest-{graph.name}",
            daemon=True,
        )
        thread.start()

    def _execute_graph(self, graph: LogicGraph, start_id: str | None = None) -> None:
        try:
            nodes = {node.id: node for node in graph.nodes}
            incoming = {edge.target for edge in graph.edges}
            starts = [
                node
                for node in graph.nodes
                if node.id == start_id
                or (start_id is None and (node.kind.startswith("trigger_") or node.id not in incoming))
            ]
            if start_id:
                starts = [nodes[start_id]] if start_id in nodes else []
            if not starts:
                raise ValueError("La lógica no tiene un nodo inicial")
            queue = [node.id for node in starts]
            steps = 0
            while queue and not self._paused.is_set():
                steps += 1
                if steps > self.MAX_STEPS:
                    raise RuntimeError("La lógica superó 250 pasos; revisa si tiene un ciclo infinito")
                node_id = queue.pop(0)
                node = nodes.get(node_id)
                if not node:
                    continue
                branch = self._run_node(node)
                next_ids = [
                    edge.target
                    for edge in graph.edges
                    if edge.source == node_id and edge.branch in {"next", branch, "always"}
                ]
                queue[0:0] = next_ids
        except IbikiError as exc:
            log.warning("Lógica %s detenida: %s", graph.name, exc)
            if self.notify and not getattr(exc, "ibiki_reported", False):
                self.notify("warning", f"Lógica '{graph.name}': {exc}")
        except Exception as exc:
            log.exception("La lógica %s falló", graph.name)
            if self.notify and not getattr(exc, "ibiki_reported", False):
                self.notify("error", f"Lógica '{graph.name}': {exc}")

    def _run_node(self, node: LogicNode) -> str:
        config = node.config
        kind = node.kind
        profile = self.get_profile()

        if kind.startswith("trigger_"):
            return "next"
        if kind == "condition_process":
            return "yes" if windows.process_running(str(config.get("process", ""))) else "no"
        if kind == "condition_active_process":
            process, _ = windows.foreground_window()
            expected = str(config.get("process", "")).strip().lower()
            return "yes" if process == expected else "no"
        if kind == "condition_window":
            _, title = windows.foreground_window()
            expected = str(config.get("contains", "")).lower()
            return "yes" if expected in title.lower() else "no"
        if kind == "condition_time":
            now = datetime.now().strftime("%H:%M")
            start = str(config.get("start", "00:00"))
            end = str(config.get("end", "23:59"))
            inside = start <= now <= end if start <= end else now >= start or now <= end
            return "yes" if inside else "no"
        if kind == "condition_capslock":
            return "yes" if windows.caps_lock_active() else "no"
        if kind == "condition_idle":
            seconds = float(config.get("seconds", 60))
            return "yes" if windows.idle_seconds() >= seconds else "no"
        if kind == "condition_variable":
            name = str(config.get("name", "variable"))
            expected = config.get("equals", True)
            getter = getattr(self.executor, "get_variable", None)
            current = getter(name) if getter else profile.variables.get(name)
            return "yes" if current == expected else "no"
        if kind == "condition_key":
            import keyboard

            return "yes" if keyboard.is_pressed(str(config.get("key", "shift"))) else "no"
        if kind == "delay":
            self._paused.wait(max(0, float(config.get("milliseconds", 100))) / 1000)
            return "next"
        if kind == "wait_event":
            timeout = max(0.0, min(86_400.0, float(config.get("timeout", 30))))
            deadline = time.monotonic() + timeout
            while time.monotonic() <= deadline and not self._paused.is_set():
                if self._event_ready(str(config.get("event", "process")), config.get("value")):
                    return "next"
                time.sleep(0.05)
            return "timeout"
        if kind == "timer":
            name = str(config.get("name", node.id))
            seconds = max(0, float(config.get("seconds", 1)))
            last = self._timers.get(name, 0.0)
            ready = time.monotonic() - last >= seconds
            if ready:
                self._timers[name] = time.monotonic()
            return "yes" if ready else "no"
        if kind == "set_variable":
            name = str(config.get("name", "variable"))
            setter = getattr(self.executor, "set_variable", None)
            if setter:
                setter(name, config.get("value"), False)
            else:
                profile.variables[name] = config.get("value")
            return "next"
        if kind == "action":
            self.executor.execute(Action.from_dict(config.get("action")))
            return "next"
        raise ValueError(f"Nodo no compatible: {kind}")

    def _event_ready(self, event: str, value: Any) -> bool:
        event = event.strip().lower()
        if event == "process":
            return windows.process_running(str(value))
        if event == "window":
            _, title = windows.foreground_window()
            return str(value).lower() in title.lower()
        if event == "key":
            import keyboard

            return bool(keyboard.is_pressed(str(value)))
        if event == "variable":
            getter = getattr(self.executor, "get_variable", None)
            return bool(getter(str(value))) if getter else bool(self.get_profile().variables.get(str(value)))
        if event == "idle":
            return windows.idle_seconds() >= float(value)
        raise ValueError(f"Evento no compatible: {event}")

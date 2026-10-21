from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ibiki_key.engines.monitor import InputMonitor
from ibiki_key.models import Action, LogicEdge, LogicGraph, LogicNode, Macro, MacroStep
from ibiki_key.services.logic_history import LogicHistory
from ibiki_key.storage import Storage


class WorkflowStudioTests(unittest.TestCase):
    def test_macro_clone_replaces_all_identities(self) -> None:
        macro = Macro(name="Original", steps=[MacroStep(action=Action("key", "a"))])
        cloned = macro.clone()
        self.assertNotEqual(cloned.id, macro.id)
        self.assertNotEqual(cloned.steps[0].id, macro.steps[0].id)
        self.assertEqual(cloned.steps[0].action.value, "a")

    def test_macro_clone_remaps_self_reference(self) -> None:
        macro = Macro(name="Recursiva")
        macro.steps = [MacroStep(action=Action("macro", macro.id))]
        cloned = macro.clone()
        self.assertEqual(cloned.steps[0].action.value, cloned.id)

    def test_macro_duration_includes_random_repeat_and_interval(self) -> None:
        macro = Macro(
            steps=[
                MacroStep(
                    action=Action("wait", 100),
                    delay_after_ms=50,
                    random_delay_ms=20,
                )
            ],
            mode="count",
            repeat_count=3,
            interval_ms=25,
        )
        self.assertEqual(macro.duration_bounds_ms(), (500, 560))
        macro.mode = "infinite"
        self.assertIsNone(macro.duration_bounds_ms())

    def test_graph_clone_remaps_nodes_and_edges(self) -> None:
        first = LogicNode(kind="trigger_key")
        second = LogicNode(kind="action")
        graph = LogicGraph(nodes=[first, second], edges=[LogicEdge(first.id, second.id)])
        cloned = graph.clone()
        original_ids = {first.id, second.id}
        cloned_ids = {node.id for node in cloned.nodes}
        self.assertTrue(original_ids.isdisjoint(cloned_ids))
        self.assertIn(cloned.edges[0].source, cloned_ids)
        self.assertIn(cloned.edges[0].target, cloned_ids)

    def test_graph_clone_remaps_self_reference(self) -> None:
        graph = LogicGraph()
        graph.nodes = [
            LogicNode(
                kind="action",
                config={
                    "action": {"type": "logic_graph", "value": graph.id, "options": {}}
                },
            )
        ]
        cloned = graph.clone()
        self.assertEqual(cloned.nodes[0].config["action"]["value"], cloned.id)

    def test_graph_diagnostics_detect_closed_cycle(self) -> None:
        first = LogicNode(kind="action", title="Uno")
        second = LogicNode(kind="action", title="Dos")
        graph = LogicGraph(
            nodes=[first, second],
            edges=[LogicEdge(first.id, second.id), LogicEdge(second.id, first.id)],
        )
        diagnostics = graph.diagnostics()
        self.assertTrue(any(level == "error" and "nodo inicial" in text for level, text in diagnostics))
        self.assertTrue(any(level == "warning" and "ciclo" in text for level, text in diagnostics))

    def test_history_restores_in_place_and_supports_redo(self) -> None:
        node = LogicNode(x=10, y=20)
        graph = LogicGraph(name="Flujo", nodes=[node])
        history = LogicHistory()
        history.remember(graph)
        graph.nodes[0].x = 90
        self.assertTrue(history.undo(graph))
        self.assertEqual(graph.nodes[0].x, 10)
        self.assertTrue(history.redo(graph))
        self.assertEqual(graph.nodes[0].x, 90)

    def test_history_keeps_redo_after_a_noop_gesture(self) -> None:
        graph = LogicGraph(nodes=[LogicNode(x=10)])
        history = LogicHistory()
        history.remember(graph)
        graph.nodes[0].x = 20
        history.commit()
        self.assertTrue(history.undo(graph))
        history.remember(graph)
        history.discard_noop(graph)
        self.assertTrue(history.can_redo)

    def test_macro_export_import_is_safe_and_portable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            storage = Storage(Path(temp) / "data")
            macro = Macro(name="Compartida", steps=[MacroStep(action=Action("hotkey", "ctrl+t"))])
            exported = storage.export_macro(macro, Path(temp) / "sample")
            imported = storage.import_macro(exported)
            self.assertEqual(exported.suffix, ".ibikimacro")
            self.assertEqual(imported.name, "Compartida")
            self.assertNotEqual(imported.id, macro.id)
            self.assertNotEqual(imported.steps[0].id, macro.steps[0].id)

    def test_monitor_exposes_interval_peak_and_full_history(self) -> None:
        monitor = InputMonitor()
        monitor.record("keyboard", "a", "down")
        monitor.record("keyboard", "b", "down")
        snapshot = monitor.snapshot()
        self.assertEqual(snapshot["total"], 2)
        self.assertEqual(snapshot["peak_cps"], 2)
        self.assertIsNotNone(snapshot["average_interval_ms"])
        self.assertEqual(len(monitor.history()), 2)
        self.assertEqual(monitor.history(0), [])
        monitor.record("mouse", "wheel_up", "scroll")
        self.assertEqual(monitor.snapshot()["total"], 3)


if __name__ == "__main__":
    unittest.main()

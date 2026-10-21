from __future__ import annotations

import unittest

from ibiki_key.engines.logic_engine import LogicEngine
from ibiki_key.models import LogicEdge, LogicGraph, LogicNode, default_profile


class FakeExecutor:
    def __init__(self) -> None:
        self.values: list[str] = []

    def execute(self, action) -> None:
        self.values.append(str(action.value))


class LogicTests(unittest.TestCase):
    def test_yes_branch(self) -> None:
        profile = default_profile()
        profile.variables["game"] = True
        executor = FakeExecutor()
        engine = LogicEngine(executor, lambda: profile)  # type: ignore[arg-type]
        trigger = LogicNode(kind="trigger_key", config={"key": "f13"})
        condition = LogicNode(kind="condition_variable", config={"name": "game", "equals": True})
        yes = LogicNode(kind="action", config={"action": {"type": "text", "value": "yes"}})
        no = LogicNode(kind="action", config={"action": {"type": "text", "value": "no"}})
        graph = LogicGraph(
            nodes=[trigger, condition, yes, no],
            edges=[
                LogicEdge(trigger.id, condition.id, "next"),
                LogicEdge(condition.id, yes.id, "yes"),
                LogicEdge(condition.id, no.id, "no"),
            ],
        )
        engine._execute_graph(graph)
        self.assertEqual(executor.values, ["yes"])

    def test_wait_for_existing_variable_event(self) -> None:
        profile = default_profile()
        profile.variables["ready"] = True
        executor = FakeExecutor()
        engine = LogicEngine(executor, lambda: profile)  # type: ignore[arg-type]
        wait = LogicNode(
            kind="wait_event",
            config={"event": "variable", "value": "ready", "timeout": 0.1},
        )
        action = LogicNode(kind="action", config={"action": {"type": "text", "value": "done"}})
        graph = LogicGraph(
            nodes=[wait, action],
            edges=[LogicEdge(wait.id, action.id, "next")],
        )
        engine._execute_graph(graph)
        self.assertEqual(executor.values, ["done"])


if __name__ == "__main__":
    unittest.main()

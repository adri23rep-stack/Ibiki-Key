from __future__ import annotations

import unittest

from ibiki_key.engines.keyboard_engine import KeyboardEngine
from ibiki_key.engines.monitor import InputMonitor
from ibiki_key.errors import ValidationError
from ibiki_key.models import Action, Mapping


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[Action, str]] = []

    def execute(self, action: Action, *, phase: str = "press") -> None:
        self.calls.append((action, phase))


class Event:
    def __init__(self, event_type: str):
        self.event_type = event_type


class KeyboardEngineTests(unittest.TestCase):
    def test_double_tap_only_fires_on_second_press(self) -> None:
        executor = FakeExecutor()
        engine = KeyboardEngine(executor, InputMonitor())  # type: ignore[arg-type]
        mapping = Mapping(trigger="double_tap", action=Action("key", "a"))
        engine._on_mapping_event(mapping, Event("down"))
        self.assertEqual(executor.calls, [])
        engine._on_mapping_event(mapping, Event("down"))
        self.assertEqual(len(executor.calls), 1)

    def test_hold_marks_key_action_as_held(self) -> None:
        executor = FakeExecutor()
        engine = KeyboardEngine(executor, InputMonitor())  # type: ignore[arg-type]
        mapping = Mapping(trigger="hold", action=Action("key", "left ctrl"))
        engine._on_mapping_event(mapping, Event("down"))
        engine._on_mapping_event(mapping, Event("up"))
        self.assertEqual([phase for _, phase in executor.calls], ["press", "release"])
        self.assertTrue(all(action.options["hold"] for action, _ in executor.calls))

    def test_turbo_requires_hold_and_physical_key(self) -> None:
        with self.assertRaises(ValidationError):
            Mapping(trigger="press", action=Action("turbo", "space")).validate()
        with self.assertRaises(ValidationError):
            Mapping(source="ctrl+k", trigger="hold", action=Action("turbo", "space")).validate()


if __name__ == "__main__":
    unittest.main()

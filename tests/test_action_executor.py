from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ibiki_key.engines.action_executor import ActionExecutor
from ibiki_key.errors import ActionBlocked
from ibiki_key.models import Action, default_profile


class FakeKeyboard:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def send(self, key: str) -> None:
        self.events.append(("send", key))

    def press(self, key: str) -> None:
        self.events.append(("press", key))

    def release(self, key: str) -> None:
        self.events.append(("release", key))

    def module(self) -> SimpleNamespace:
        return SimpleNamespace(send=self.send, press=self.press, release=self.release)


class ActionExecutorTests(unittest.TestCase):
    def test_command_permission_is_a_clear_user_facing_block(self) -> None:
        executor = ActionExecutor(Path.cwd())
        profile = default_profile()
        profile.settings["scripts_allowed"] = False
        executor.get_profile = lambda: profile
        messages: list[tuple[str, str]] = []
        executor.toast = lambda level, text: messages.append((level, text))

        with self.assertRaises(ActionBlocked) as raised:
            executor.execute(Action("command", "echo hello"))

        self.assertIn("Perfiles > Editar", str(raised.exception))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0][0], "warning")

    def test_quick_mod_tap_sends_tap(self) -> None:
        fake = FakeKeyboard()
        executor = ActionExecutor(Path.cwd())
        action = Action(
            "mod_tap",
            {"tap": "escape", "hold": "left ctrl", "threshold_ms": 80},
            {"_mapping_id": "one"},
        )
        with patch.dict(sys.modules, {"keyboard": fake.module()}):
            executor.execute(action, phase="press")
            executor.execute(action, phase="release")
            time.sleep(0.1)
        self.assertIn(("send", "escape"), fake.events)
        self.assertNotIn(("press", "left ctrl"), fake.events)

    def test_held_mod_tap_releases_modifier(self) -> None:
        fake = FakeKeyboard()
        executor = ActionExecutor(Path.cwd())
        action = Action(
            "mod_tap",
            {"tap": "escape", "hold": "left ctrl", "threshold_ms": 80},
            {"_mapping_id": "two"},
        )
        with patch.dict(sys.modules, {"keyboard": fake.module()}):
            executor.execute(action, phase="press")
            time.sleep(0.1)
            executor.execute(action, phase="release")
        self.assertIn(("press", "left ctrl"), fake.events)
        self.assertIn(("release", "left ctrl"), fake.events)

    def test_held_macro_stops_immediately_on_source_release(self) -> None:
        executor = ActionExecutor(Path.cwd())
        runs: list[tuple[str, str | None]] = []
        stops: list[str] = []
        executor.run_macro = lambda macro_id, source: runs.append((macro_id, source))
        executor.stop_macro = stops.append
        action = Action(
            "macro",
            "macro_mouse",
            {"source_key": "mouse:x", "stop_on_release": True},
        )
        executor.execute(action, phase="press")
        executor.execute(action, phase="release")
        self.assertEqual(runs, [("macro_mouse", "mouse:x")])
        self.assertEqual(stops, ["macro_mouse"])


if __name__ == "__main__":
    unittest.main()

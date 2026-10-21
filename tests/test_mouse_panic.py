from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ibiki_key.engines.action_executor import ActionExecutor
from ibiki_key.engines.logic_engine import LogicEngine
from ibiki_key.engines.macro_engine import MacroEngine
from ibiki_key.engines.mouse_engine import MouseEngine
from ibiki_key.models import Action, LogicGraph, LogicNode, Macro, MacroStep, default_profile
from ibiki_key.services.windows import SystemMouseSettings


class MousePanicTests(unittest.TestCase):
    def test_mouse_engine_restores_windows_settings_on_panic_and_stop(self) -> None:
        profile = default_profile()
        profile.mouse.cursor_speed = 17
        profile.mouse.double_click_ms = 640
        profile.mouse.scroll_lines = 8
        snapshot = SystemMouseSettings(9, 500, 3)
        executor = Mock()
        monitor = Mock()
        engine = MouseEngine(executor, monitor)

        with (
            patch("ibiki_key.engines.mouse_engine.capture_mouse_settings", return_value=snapshot),
            patch("ibiki_key.engines.mouse_engine.restore_mouse_settings", return_value=True) as restore,
            patch("ibiki_key.engines.mouse_engine.set_cursor_speed", return_value=True) as speed,
            patch("ibiki_key.engines.mouse_engine.set_double_click_time", return_value=True) as double,
            patch("ibiki_key.engines.mouse_engine.set_scroll_lines", return_value=True) as scroll,
            patch("ibiki_key.engines.mouse_engine.mouse.hook", return_value=object()),
            patch("ibiki_key.engines.mouse_engine.mouse.unhook"),
        ):
            engine.start(profile)
            speed.assert_called_with(17)
            double.assert_called_with(640)
            scroll.assert_called_with(8)

            engine.set_pause_state(automation_paused=True)
            self.assertTrue(engine.paused)
            restore.assert_called_with(snapshot)

            previous_speed_calls = speed.call_count
            engine.set_pause_state(automation_paused=False)
            self.assertFalse(engine.paused)
            self.assertGreater(speed.call_count, previous_speed_calls)

            engine.stop()
            self.assertGreaterEqual(restore.call_count, 2)

    def test_executor_rejects_mouse_actions_while_panic_is_active(self) -> None:
        executor = ActionExecutor(Path.cwd())
        with patch("ibiki_key.engines.action_executor.mouse.click") as click:
            executor.set_automation_paused(True)
            executor.execute(Action("mouse_button", "left"))
            click.assert_not_called()
            executor.set_automation_paused(False)
            executor.execute(Action("mouse_button", "left"))
            click.assert_called_once_with("left")

    def test_while_held_macro_can_use_a_mouse_button(self) -> None:
        profile = default_profile()
        macro = Macro(
            name="Mientras lateral",
            scope="mouse",
            mode="while_held",
            steps=[MacroStep(action=Action("noop", ""))],
        )
        profile.macros.append(macro)
        engine = MacroEngine(Mock(), lambda: profile)
        with patch("ibiki_key.engines.macro_engine.mouse.is_pressed", return_value=True) as pressed:
            self.assertTrue(engine._is_pressed("mouse:x"))  # noqa: SLF001
            pressed.assert_called_once_with("x")

    def test_panic_blocks_new_macro_and_logic_runs(self) -> None:
        profile = default_profile()
        macro = Macro(name="Bloqueada", steps=[MacroStep(action=Action("key", "a"))])
        graph = LogicGraph(name="Bloqueada", nodes=[LogicNode(kind="trigger_key")])
        profile.macros.append(macro)
        profile.logic_graphs.append(graph)
        executor = Mock()
        macro_engine = MacroEngine(executor, lambda: profile)
        logic_engine = LogicEngine(executor, lambda: profile)

        macro_engine.set_paused(True)
        logic_engine.set_paused(True)
        macro_engine.run(macro.id)
        logic_engine.run(graph.id)

        self.assertEqual(macro_engine.running_ids(), set())
        executor.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()

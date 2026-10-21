from __future__ import annotations

import unittest

from ibiki_key.services.mouse_backend import ButtonEvent, MoveEvent, WheelEvent
from ibiki_key.services.mouse_recording import MouseRecordingBuilder


class MouseRecordingTests(unittest.TestCase):
    def test_records_sampled_relative_moves_clicks_and_both_wheels(self) -> None:
        builder = MouseRecordingBuilder(record_moves=True, move_interval_ms=30)
        builder.reset((100, 100))

        self.assertTrue(builder.feed(MoveEvent(105, 102, 1.00)))
        self.assertFalse(builder.feed(MoveEvent(110, 104, 1.01)))
        self.assertTrue(builder.feed(MoveEvent(120, 108, 1.04)))
        self.assertTrue(builder.feed(ButtonEvent("down", "x", 1.10)))
        self.assertTrue(builder.feed(ButtonEvent("up", "x", 1.13)))
        self.assertTrue(builder.feed(WheelEvent(-1, 1.20)))
        self.assertTrue(builder.feed(WheelEvent(1, 1.25, horizontal=True)))

        steps = builder.to_steps()
        self.assertEqual(len(steps), 6)
        self.assertEqual(steps[0].action.type, "mouse_move")
        self.assertEqual(steps[0].action.value, {"x": 5, "y": 2, "absolute": False})
        self.assertEqual(steps[1].action.value, {"x": 15, "y": 6, "absolute": False})
        self.assertEqual(steps[2].action.options["event"], "down")
        self.assertEqual(steps[4].action.value, -1)
        self.assertEqual(steps[5].action.value, {"vertical": 0, "horizontal": 1})
        self.assertEqual(steps[0].delay_after_ms, 40)

    def test_can_record_clicks_without_cursor_noise(self) -> None:
        builder = MouseRecordingBuilder(record_moves=False)
        builder.reset((0, 0))
        self.assertFalse(builder.feed(MoveEvent(50, 20, 1.0)))
        self.assertTrue(builder.feed(ButtonEvent("down", "left", 1.1)))
        self.assertEqual([step.action.type for step in builder.to_steps()], ["mouse_button"])

    def test_removes_only_recent_gui_stop_click(self) -> None:
        builder = MouseRecordingBuilder(record_moves=True)
        builder.reset((0, 0))
        builder.feed(ButtonEvent("down", "right", 1.0))
        builder.feed(ButtonEvent("up", "right", 1.1))
        builder.feed(ButtonEvent("down", "left", 2.0))
        builder.feed(ButtonEvent("up", "left", 2.1))

        self.assertTrue(builder.remove_recent_stop_click(now=2.2))
        steps = builder.to_steps()
        self.assertEqual(len(steps), 2)
        self.assertTrue(all(step.action.value == "right" for step in steps))


if __name__ == "__main__":
    unittest.main()

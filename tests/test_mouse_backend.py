from __future__ import annotations

import unittest

from ibiki_key.services import mouse_backend


class MouseBackendTests(unittest.TestCase):
    def test_native_messages_have_compatible_event_names(self) -> None:
        data = mouse_backend._LowLevelMouseData()  # noqa: SLF001
        data.pt.x = 30
        data.pt.y = 40
        move = mouse_backend.NativeMouseHook._translate(0x0200, data)  # noqa: SLF001
        down = mouse_backend.NativeMouseHook._translate(0x0201, data)  # noqa: SLF001
        self.assertIsInstance(move, mouse_backend.MoveEvent)
        self.assertEqual((move.x, move.y), (30, 40))
        self.assertIsInstance(down, mouse_backend.ButtonEvent)
        self.assertEqual((down.event_type, down.button), ("down", "left"))

    def test_xbutton_two_maps_to_x2(self) -> None:
        data = mouse_backend._LowLevelMouseData()  # noqa: SLF001
        data.mouseData = 2 << 16
        event = mouse_backend.NativeMouseHook._translate(0x020B, data)  # noqa: SLF001
        self.assertIsInstance(event, mouse_backend.ButtonEvent)
        self.assertEqual(event.button, "x2")

    def test_horizontal_wheel_is_identified(self) -> None:
        data = mouse_backend._LowLevelMouseData()  # noqa: SLF001
        data.mouseData = 120 << 16
        event = mouse_backend.NativeMouseHook._translate(0x020E, data)  # noqa: SLF001
        self.assertIsInstance(event, mouse_backend.WheelEvent)
        self.assertTrue(event.horizontal)
        self.assertEqual(event.delta, 1)


if __name__ == "__main__":
    unittest.main()

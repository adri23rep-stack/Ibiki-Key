from __future__ import annotations

import unittest

from ibiki_key.models import Action, Mapping
from ibiki_key.ui.keyboard_widget import KEY_SPECS, normalize_key_name
from ibiki_key.ui.pages.dashboard import DashboardPage


class LiveDashboardTests(unittest.TestCase):
    def test_keyboard_contains_navigation_arrows_and_numpad(self) -> None:
        keys = {item.key for item in KEY_SPECS}
        self.assertGreaterEqual(len(KEY_SPECS), 100)
        self.assertTrue(
            {
                "f12",
                "insert",
                "delete",
                "page up",
                "left",
                "right",
                "num lock",
                "num 0",
                "num enter",
            }.issubset(keys)
        )

    def test_keyboard_normalizes_common_hook_names(self) -> None:
        self.assertEqual(normalize_key_name("escape"), "esc")
        self.assertEqual(normalize_key_name("print_screen"), "print screen")
        self.assertEqual(normalize_key_name("numpad 7"), "num 7")

    def test_dashboard_summarizes_macro_bindings(self) -> None:
        mappings = [
            Mapping(source="f13", action=Action("macro", "macro_demo")),
            Mapping(source="f14", action=Action("macro", "macro_demo")),
            Mapping(source="f15", action=Action("macro", "macro_demo")),
        ]
        self.assertEqual(
            DashboardPage._macro_bindings(mappings),  # noqa: SLF001
            {"macro_demo": "F13, F14"},
        )

    def test_dashboard_uses_readable_mouse_binding_names(self) -> None:
        mappings = [Mapping(source="x", action=Action("macro", "macro_mouse"))]
        self.assertEqual(
            DashboardPage._macro_bindings(mappings, mouse=True),  # noqa: SLF001
            {"macro_mouse": "Lateral 1"},
        )


if __name__ == "__main__":
    unittest.main()

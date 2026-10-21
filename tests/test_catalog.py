from __future__ import annotations

import unittest

from ibiki_key.ui.catalog import node_display_id, node_output_hint, node_summary


class CatalogTests(unittest.TestCase):
    def test_node_ids_are_readable_and_stable(self) -> None:
        self.assertEqual(node_display_id("trigger_key", "node_123456abcdef"), "TRG-ABCDEF")
        self.assertEqual(node_display_id("condition_process", "node_123456abcdef"), "CON-ABCDEF")
        self.assertEqual(node_display_id("action", "node_123456abcdef"), "ACT-ABCDEF")

    def test_node_summary_explains_the_configuration(self) -> None:
        self.assertEqual(
            node_summary("condition_process", {"process": "chrome.exe"}),
            "Programa abierto: chrome.exe",
        )
        self.assertIn(
            "Combinación de teclas",
            node_summary(
                "action",
                {"action": {"type": "hotkey", "value": "ctrl+t", "options": {}}},
            ),
        )

    def test_condition_outputs_are_named(self) -> None:
        self.assertEqual(node_output_hint("condition_window"), "SALIDAS  ·  SÍ  /  NO")
        self.assertEqual(node_output_hint("action"), "SALIDA  ·  SIGUIENTE")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ibiki_key.engines.action_executor import ActionExecutor
from ibiki_key.engines.plugin_manager import PluginManager


class PluginTests(unittest.TestCase):
    def test_disabled_by_default_and_explicit_load(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plugin_dir = root / "hello"
            plugin_dir.mkdir()
            (plugin_dir / "plugin.json").write_text(
                json.dumps(
                    {
                        "id": "hello",
                        "name": "Hello",
                        "version": "1.0.0",
                        "entry": "plugin.py",
                    }
                ),
                encoding="utf-8",
            )
            (plugin_dir / "plugin.py").write_text(
                "def register(context):\n"
                "    context.register_action('run', 'Run', lambda value, options, phase, profile: None)\n",
                encoding="utf-8",
            )
            executor = ActionExecutor(root)
            settings: dict[str, object] = {}
            manager = PluginManager(root, executor, settings, lambda level, text: None)
            manager.load_enabled()
            self.assertFalse(executor.plugin_actions)
            settings["enabled_plugins"] = ["hello"]
            loaded = manager.load_enabled()
            self.assertTrue(loaded[0].loaded)
            self.assertIn("plugin.hello.run", executor.plugin_actions)


if __name__ == "__main__":
    unittest.main()

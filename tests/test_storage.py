from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ibiki_key.models import AppState, default_profile
from ibiki_key.storage import Storage


class StorageTests(unittest.TestCase):
    def test_save_load_backup_export_import(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            storage = Storage(Path(temp))
            profile = default_profile()
            state = AppState(active_profile_id=profile.id, profiles=[profile])
            storage.save(state, make_backup=False)
            loaded = storage.load()
            self.assertEqual(loaded.active_profile().name, "Escritorio")

            storage.save(loaded)
            self.assertTrue(list(storage.backup_dir.glob("*.json")))

            exported = storage.export_profile(profile, Path(temp) / "sample.ibiki")
            raw = json.loads(exported.read_text(encoding="utf-8"))
            self.assertEqual(raw["format"], "ibiki-profile")
            imported = storage.import_profile(exported)
            self.assertNotEqual(imported.id, profile.id)
            self.assertFalse(imported.settings["auto_switch"])
            self.assertFalse(imported.settings["scripts_allowed"])
            self.assertFalse(imported.settings["trusted_actions"])


if __name__ == "__main__":
    unittest.main()

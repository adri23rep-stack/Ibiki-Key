from __future__ import annotations

import unittest

from ibiki_key.models import Action, AppState, Macro, Mapping, Profile, default_profile


class ModelTests(unittest.TestCase):
    def test_profile_roundtrip(self) -> None:
        profile = default_profile()
        profile.layers.append("Fn")
        profile.mappings.append(Mapping(source="f13", action=Action("hotkey", "ctrl+t"), layer="Fn"))
        rebuilt = Profile.from_dict(profile.to_dict())
        self.assertEqual(rebuilt.name, profile.name)
        self.assertEqual(rebuilt.mappings[0].action.value, "ctrl+t")
        self.assertEqual(rebuilt.layers, ["Base", "Fn"])

    def test_clone_has_new_identity(self) -> None:
        profile = default_profile()
        cloned = profile.clone()
        self.assertNotEqual(cloned.id, profile.id)
        self.assertNotEqual(cloned.name, profile.name)

    def test_app_state_repairs_active_profile(self) -> None:
        state = AppState.from_dict(
            {
                "profiles": [default_profile().to_dict()],
                "active_profile_id": "missing",
                "global_variables": {"modo": True},
            }
        )
        self.assertEqual(state.active_profile_id, state.profiles[0].id)
        self.assertTrue(state.global_variables["modo"])

    def test_mouse_macro_scope_roundtrip_and_legacy_default(self) -> None:
        macro = Macro(name="Mouse", scope="mouse")
        rebuilt = Macro.from_dict(
            {
                "id": macro.id,
                "name": macro.name,
                "scope": macro.scope,
                "steps": [],
            }
        )
        self.assertEqual(rebuilt.scope, "mouse")
        self.assertEqual(Macro.from_dict({"name": "Anterior"}).scope, "general")


if __name__ == "__main__":
    unittest.main()

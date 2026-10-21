from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ibiki_key.models import (  # noqa: E402
    Action,
    AppState,
    LogicEdge,
    LogicGraph,
    LogicNode,
    Macro,
    MacroStep,
    Mapping,
    default_profile,
)
from ibiki_key.storage import Storage  # noqa: E402


def main() -> int:
    profile = default_profile()
    profile.mappings.append(Mapping(source="f13", action=Action("hotkey", "ctrl+t")))
    profile.validate()
    with tempfile.TemporaryDirectory() as temp:
        storage = Storage(Path(temp))
        state = AppState(active_profile_id=profile.id, profiles=[profile])
        storage.save(state, make_backup=False)
        rebuilt = storage.load()
        assert rebuilt.active_profile().mappings[0].source == "f13"
        macro = Macro(
            name="Prueba mouse",
            scope="mouse",
            steps=[MacroStep(action=Action("mouse_move", {"x": 5, "y": -2, "absolute": False}))],
        )
        macro_file = storage.export_macro(macro, Path(temp) / "macro")
        imported_macro = storage.import_macro(macro_file)
        assert imported_macro.scope == "mouse"
        assert imported_macro.steps[0].action.value["x"] == 5
    trigger = LogicNode(kind="trigger_key")
    action = LogicNode(kind="action")
    graph = LogicGraph(
        nodes=[trigger, action],
        edges=[LogicEdge(trigger.id, action.id, "next")],
    )
    assert graph.diagnostics() == []
    print("Ibiki Key core: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

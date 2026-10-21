from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    engine_state_changed = Signal(bool, str)
    automation_pause_changed = Signal(bool)
    active_profile_changed = Signal(str, str)
    input_event = Signal(dict)
    stats_changed = Signal(dict)
    toast_requested = Signal(str, str)
    profiles_changed = Signal()
    macros_changed = Signal()
    mappings_changed = Signal()
    graph_changed = Signal()
    theme_changed = Signal(str)
    log_event = Signal(str, str)

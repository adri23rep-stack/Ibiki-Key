from __future__ import annotations

import copy
from dataclasses import asdict

from ..models import LogicGraph


class LogicHistory:
    """Historial acotado de un flujo; restaura el objeto para no romper referencias de la UI."""

    def __init__(self, limit: int = 60):
        self.limit = max(1, int(limit))
        self._undo: list[LogicGraph] = []
        self._redo: list[LogicGraph] = []
        self._pending_snapshot: LogicGraph | None = None
        self._pending_added = False
        self._redo_backup: list[LogicGraph] | None = None

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def remember(self, graph: LogicGraph) -> None:
        snapshot = copy.deepcopy(graph)
        self._pending_snapshot = snapshot
        self._pending_added = False
        self._redo_backup = copy.deepcopy(self._redo)
        if self._undo and asdict(self._undo[-1]) == asdict(snapshot):
            self._redo.clear()
            return
        self._undo.append(snapshot)
        self._pending_added = True
        del self._undo[:-self.limit]
        self._redo.clear()

    def discard_noop(self, graph: LogicGraph) -> None:
        if self._pending_snapshot is None:
            return
        if asdict(self._pending_snapshot) != asdict(graph):
            self.commit()
            return
        if self._pending_added and self._undo and asdict(self._undo[-1]) == asdict(graph):
            self._undo.pop()
        if self._redo_backup is not None:
            self._redo = self._redo_backup
        self.commit()

    def commit(self) -> None:
        self._pending_snapshot = None
        self._pending_added = False
        self._redo_backup = None

    def undo(self, graph: LogicGraph) -> bool:
        self.commit()
        if not self._undo:
            return False
        self._redo.append(copy.deepcopy(graph))
        self._restore(graph, self._undo.pop())
        return True

    def redo(self, graph: LogicGraph) -> bool:
        self.commit()
        if not self._redo:
            return False
        self._undo.append(copy.deepcopy(graph))
        self._restore(graph, self._redo.pop())
        return True

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
        self.commit()

    @staticmethod
    def _restore(target: LogicGraph, snapshot: LogicGraph) -> None:
        target.name = snapshot.name
        target.nodes = copy.deepcopy(snapshot.nodes)
        target.edges = copy.deepcopy(snapshot.edges)
        target.enabled = snapshot.enabled

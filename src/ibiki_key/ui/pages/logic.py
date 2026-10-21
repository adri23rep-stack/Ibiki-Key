from __future__ import annotations

import copy
import re
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QAction, QBrush, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...models import Action, LogicEdge, LogicGraph, LogicNode, Mapping, new_id
from ...services.logic_history import LogicHistory
from ..catalog import CATEGORY_COLORS, NODE_CATALOG, node_display_id
from ..common import Card, PageHeader, confirm, danger_button, primary_button, section_title
from ..dialogs import LogicNodeDialog, MappingDialog
from ..logic_canvas import LogicCanvas, NodePalette


class LogicPage(QWidget):
    def __init__(self, controller: object, bus: object):
        super().__init__()
        self.controller = controller
        self.bus = bus
        self._histories: dict[str, LogicHistory] = {}
        self._pending_graph_id = ""
        self._shown_graph_id = ""
        self._shortcuts: list[QShortcut] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 26)
        root.setSpacing(12)
        root.addWidget(
            PageHeader(
                "Lógica visual",
                "Arrastra, conecta, valida y prueba automatizaciones sin escribir código.",
            )
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = Card()
        left.setMinimumWidth(245)
        left.setMaximumWidth(330)
        tabs = QTabWidget()
        left.box.addWidget(tabs, 1)

        flows_tab = QWidget()
        flows = QVBoxLayout(flows_tab)
        flows.setContentsMargins(8, 10, 8, 8)
        flows.setSpacing(8)
        head = QHBoxLayout()
        head.addWidget(section_title("Flujos"))
        head.addStretch(1)
        head.addWidget(primary_button("+", self.add_graph))
        flows.addLayout(head)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(lambda *_: self._show_graph())
        flows.addWidget(self.list, 1)
        flows.addWidget(QPushButton("Plantilla F13 + Chrome", clicked=self.add_template))
        flow_row = QHBoxLayout()
        flow_row.addWidget(QPushButton("Duplicar", clicked=self.duplicate_graph))
        flow_row.addWidget(QPushButton("Renombrar", clicked=self.rename_graph))
        flows.addLayout(flow_row)
        self.toggle_graph_button = QPushButton("Desactivar flujo", clicked=self.toggle_graph)
        flows.addWidget(self.toggle_graph_button)
        flows.addWidget(danger_button("Eliminar flujo", self.delete_graph))
        tabs.addTab(flows_tab, "Flujos")

        nodes_tab = QWidget()
        nodes = QVBoxLayout(nodes_tab)
        nodes.setContentsMargins(8, 10, 8, 8)
        nodes.setSpacing(8)
        nodes.addWidget(section_title("Biblioteca de nodos"))
        self.node_search = QLineEdit()
        self.node_search.setPlaceholderText("Buscar condición, acción…")
        self.node_search.setClearButtonEnabled(True)
        self.node_search.textChanged.connect(self._populate_palette)
        nodes.addWidget(self.node_search)
        self.palette = NodePalette()
        self.palette.node_activated.connect(self.add_node)
        nodes.addWidget(self.palette, 1)
        palette_hint = QLabel("Doble clic o arrastra un nodo al lienzo")
        palette_hint.setObjectName("Muted")
        palette_hint.setWordWrap(True)
        nodes.addWidget(palette_hint)
        tabs.addTab(nodes_tab, "Nodos")
        splitter.addWidget(left)

        workspace = Card(padding=10)
        edit_toolbar = QHBoxLayout()
        self.add_node_button = primary_button("+ Nodo")
        self.add_node_button.clicked.connect(self._show_node_menu)
        self.edit_button = QPushButton("Editar", clicked=self.edit_selected_node)
        self.connect_button = QPushButton("Conectar", clicked=self.connect_nodes)
        self.duplicate_button = QPushButton("Duplicar", clicked=self.duplicate_selection)
        self.delete_button = danger_button("Eliminar", self.delete_selection)
        for button in (
            self.add_node_button,
            self.edit_button,
            self.connect_button,
            self.duplicate_button,
            self.delete_button,
        ):
            edit_toolbar.addWidget(button)
        edit_toolbar.addStretch(1)
        edit_toolbar.addWidget(QPushButton("Validar", clicked=self.validate_graph))
        edit_toolbar.addWidget(primary_button("▶ Probar", self.test_graph))
        workspace.box.addLayout(edit_toolbar)

        view_toolbar = QHBoxLayout()
        self.undo_button = QPushButton("↶ Deshacer", clicked=self.undo)
        self.redo_button = QPushButton("↷ Rehacer", clicked=self.redo)
        view_toolbar.addWidget(self.undo_button)
        view_toolbar.addWidget(self.redo_button)
        view_toolbar.addWidget(QPushButton("Asignar tecla", clicked=self.bind_graph))
        view_toolbar.addWidget(QPushButton("Exportar PNG", clicked=self.export_graph))
        view_toolbar.addStretch(1)
        view_toolbar.addWidget(QPushButton("−", clicked=lambda: self.canvas.zoom_out()))
        self.zoom_label = QLabel("100 %")
        self.zoom_label.setMinimumWidth(52)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        view_toolbar.addWidget(self.zoom_label)
        view_toolbar.addWidget(QPushButton("+", clicked=lambda: self.canvas.zoom_in()))
        view_toolbar.addWidget(QPushButton("Ajustar", clicked=lambda: self.canvas.fit_graph()))
        workspace.box.addLayout(view_toolbar)

        legend = QHBoxLayout()
        for label, category in (
            ("Disparador", "trigger"),
            ("Condición", "condition"),
            ("Acción", "action"),
            ("Control", "utility"),
        ):
            item = QLabel(f"● {label}")
            item.setStyleSheet(f"color:{CATEGORY_COLORS[category]};font-weight:650;")
            legend.addWidget(item)
        legend.addSpacing(10)
        hint = QLabel("ID estable · Ctrl+clic conecta · Ctrl+D duplica · Supr elimina")
        hint.setObjectName("Muted")
        legend.addWidget(hint)
        legend.addStretch(1)
        workspace.box.addLayout(legend)

        self.canvas = LogicCanvas(
            self.edit_node,
            self._node_moved,
            self._remember_current,
            self._finish_canvas_change,
        )
        self.canvas.node_dropped.connect(self.add_node)
        self.canvas.zoom_changed.connect(lambda value: self.zoom_label.setText(f"{value} %"))
        self.canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self._canvas_menu)
        workspace.box.addWidget(self.canvas, 1)
        splitter.addWidget(workspace)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self._setup_shortcuts()
        self._populate_palette()
        bus.graph_changed.connect(self.refresh)
        bus.active_profile_changed.connect(lambda *_: self.refresh())
        self.refresh()

    def current_graph(self) -> LogicGraph | None:
        item = self.list.currentItem()
        if not item:
            return None
        graph_id = item.data(Qt.ItemDataRole.UserRole)
        return next(
            (x for x in self.controller.active_profile().logic_graphs if x.id == graph_id),
            None,
        )

    def refresh(self) -> None:
        current = self.current_graph()
        selected = self._pending_graph_id or (current.id if current else "")
        self._pending_graph_id = ""
        self.list.blockSignals(True)
        self.list.clear()
        for graph in self.controller.active_profile().logic_graphs:
            state = "●" if graph.enabled else "○"
            item = QListWidgetItem(f"{state} {graph.name}  ·  {len(graph.nodes)} nodos")
            item.setData(Qt.ItemDataRole.UserRole, graph.id)
            if not graph.enabled:
                item.setForeground(QBrush(QColor("#7E879D")))
            self.list.addItem(item)
            if graph.id == selected:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)
        self._show_graph()

    def _show_graph(self) -> None:
        graph = self.current_graph()
        changed_graph = bool(graph and graph.id != self._shown_graph_id)
        self._shown_graph_id = graph.id if graph else ""
        self.canvas.set_graph(graph)
        self.canvas.set_editable(not self._is_locked())
        if changed_graph:
            self.canvas.fit_graph()
        self.toggle_graph_button.setText(
            "Desactivar flujo" if not graph or graph.enabled else "Activar flujo"
        )
        self._update_history_buttons()
        self._update_edit_controls()

    def add_graph(self) -> None:
        if self._locked():
            return
        name, ok = QInputDialog.getText(self, "Nuevo flujo", "Nombre:")
        if ok and name.strip():
            graph = LogicGraph(name=name.strip())
            self.controller.active_profile().logic_graphs.append(graph)
            self._pending_graph_id = graph.id
            self.controller.profile_changed(restart=False)

    def duplicate_graph(self) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        if not graph:
            return
        cloned = graph.clone()
        self.controller.active_profile().logic_graphs.append(cloned)
        self._pending_graph_id = cloned.id
        self.controller.profile_changed(restart=False)
        self.controller.notify("success", f"Flujo duplicado: {cloned.name}")

    def rename_graph(self) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        if not graph:
            return
        name, ok = QInputDialog.getText(self, "Renombrar flujo", "Nombre:", text=graph.name)
        if ok and name.strip() and name.strip() != graph.name:
            graph.name = name.strip()
            self._pending_graph_id = graph.id
            self.controller.profile_changed(restart=False)

    def toggle_graph(self) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        if not graph:
            return
        graph.enabled = not graph.enabled
        self._pending_graph_id = graph.id
        self.controller.profile_changed(restart=False)

    def delete_graph(self) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        if not graph:
            return
        profile = self.controller.active_profile()
        direct = [
            mapping
            for mapping in [*profile.mappings, *profile.mouse_mappings]
            if mapping.action.type == "logic_graph" and str(mapping.action.value) == graph.id
        ]
        macro_steps = [
            step
            for macro in profile.macros
            for step in macro.steps
            if step.action.type == "logic_graph" and str(step.action.value) == graph.id
        ]
        graph_nodes = [
            node
            for owner in profile.logic_graphs
            if owner is not graph
            for node in owner.nodes
            if node.kind == "action"
            and isinstance(node.config.get("action"), dict)
            and node.config["action"].get("type") == "logic_graph"
            and str(node.config["action"].get("value")) == graph.id
        ]
        references = len(direct) + len(macro_steps) + len(graph_nodes)
        detail = (
            f"\n\nTambién se limpiarán {references} referencia(s) para evitar acciones rotas."
            if references
            else ""
        )
        if confirm(self, "Eliminar flujo", f"¿Eliminar '{graph.name}'?{detail}"):
            profile.logic_graphs.remove(graph)
            profile.mappings = [mapping for mapping in profile.mappings if mapping not in direct]
            profile.mouse_mappings = [
                mapping for mapping in profile.mouse_mappings if mapping not in direct
            ]
            for step in macro_steps:
                step.enabled = False
            for node in graph_nodes:
                node.config["action"] = {"type": "noop", "value": None, "options": {}}
                node.title = f"{node.title} · referencia eliminada"
            self._histories.pop(self._history_key(graph), None)
            self._shown_graph_id = ""
            self.controller.profile_changed(restart=False)
            if references:
                self.controller.notify("warning", "Se limpiaron referencias al flujo eliminado")

    def _populate_palette(self) -> None:
        query = self.node_search.text().strip().casefold() if hasattr(self, "node_search") else ""
        self.palette.clear()
        order = {"trigger": 0, "condition": 1, "action": 2, "utility": 3}
        entries = sorted(NODE_CATALOG.items(), key=lambda value: (order.get(value[1][1], 9), value[1][0]))
        for kind, (title, category, _defaults) in entries:
            searchable = f"{kind} {title} {category}".casefold()
            if query and query not in searchable:
                continue
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, kind)
            item.setForeground(QBrush(QColor(CATEGORY_COLORS.get(category, "#60A5FA"))))
            item.setToolTip(f"{title}\nArrastra al lienzo o haz doble clic")
            self.palette.addItem(item)

    def _show_node_menu(self) -> None:
        if self._locked():
            return
        menu = QMenu(self)
        categories = {
            "Disparadores": [key for key in NODE_CATALOG if key.startswith("trigger_")],
            "Condiciones": [
                key for key in NODE_CATALOG if key.startswith("condition_") or key == "timer"
            ],
            "Acciones y control": ["action", "set_variable", "delay", "wait_event"],
        }
        for category, keys in categories.items():
            submenu = menu.addMenu(category)
            for key in keys:
                action = QAction(NODE_CATALOG[key][0], submenu)
                action.triggered.connect(lambda checked=False, value=key: self.add_node(value))
                submenu.addAction(action)
        menu.exec(self.add_node_button.mapToGlobal(self.add_node_button.rect().bottomLeft()))

    def add_node(self, kind: str, position: object | None = None) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        if not graph:
            QMessageBox.information(self, "Falta un flujo", "Crea o selecciona un flujo primero.")
            return
        if kind not in NODE_CATALOG:
            return
        dialog = LogicNodeDialog(self.controller, kind=kind, parent=self)
        if not dialog.exec():
            return
        node = dialog.result_node()
        point = position if isinstance(position, QPointF) else self.canvas.mapToScene(
            self.canvas.viewport().rect().center()
        )
        node.x, node.y = point.x() - 135, point.y() - 66
        self._remember_current()
        graph.nodes.append(node)
        self._apply_graph_change([node.id])

    def edit_selected_node(self) -> None:
        nodes = self.canvas.selected_nodes()
        if nodes:
            self.edit_node(nodes[0])

    def edit_node(self, node: LogicNode) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        if not graph or node not in graph.nodes:
            return
        dialog = LogicNodeDialog(self.controller, node=node, parent=self)
        if dialog.exec():
            new = dialog.result_node()
            self._remember_current()
            graph.nodes[graph.nodes.index(node)] = new
            for edge in graph.edges:
                if edge.source == node.id:
                    edge.source = new.id
                if edge.target == node.id:
                    edge.target = new.id
            self._apply_graph_change([new.id])

    def connect_nodes(self) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        nodes = self.canvas.selected_nodes()
        if not graph or len(nodes) != 2:
            QMessageBox.information(
                self,
                "Selecciona dos nodos",
                "Selecciona el nodo de salida y el de destino usando Ctrl + clic.",
            )
            return
        labels = [f"{node.title} · {node_display_id(node.kind, node.id)}" for node in nodes]
        source_name, ok = QInputDialog.getItem(
            self, "Dirección de la conexión", "Nodo de salida:", labels, 0, False
        )
        if not ok:
            return
        source_index = labels.index(source_name)
        source = nodes[source_index]
        target = nodes[1 - source_index]
        branch_options = {
            "Siguiente": "next",
            "Sí": "yes",
            "No": "no",
            "Tiempo agotado": "timeout",
            "Siempre": "always",
        }
        branch_label, ok = QInputDialog.getItem(
            self,
            "Tipo de conexión",
            "Salida:",
            list(branch_options),
            0,
            False,
        )
        if not ok:
            return
        branch = branch_options[branch_label]
        if any(
            edge.source == source.id and edge.target == target.id and edge.branch == branch
            for edge in graph.edges
        ):
            self.controller.notify("info", "Esa conexión ya existe")
            return
        self._remember_current()
        graph.edges.append(LogicEdge(source.id, target.id, branch))
        try:
            graph.validate()
        except Exception as exc:
            graph.edges.pop()
            self._history().discard_noop(graph)
            QMessageBox.warning(self, "Conexión inválida", str(exc))
            return
        self._apply_graph_change([source.id, target.id])

    def duplicate_selection(self) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        selected = self.canvas.selected_nodes()
        if not graph or not selected:
            QMessageBox.information(self, "Nada que duplicar", "Selecciona uno o más nodos.")
            return
        self._remember_current()
        id_map: dict[str, str] = {}
        copies: list[LogicNode] = []
        for node in selected:
            cloned = copy.deepcopy(node)
            cloned.id = new_id("node")
            cloned.x += 38
            cloned.y += 38
            id_map[node.id] = cloned.id
            copies.append(cloned)
        edges = [
            LogicEdge(id_map[edge.source], id_map[edge.target], edge.branch)
            for edge in graph.edges
            if edge.source in id_map and edge.target in id_map
        ]
        graph.nodes.extend(copies)
        graph.edges.extend(edges)
        self._apply_graph_change([node.id for node in copies])

    def delete_selection(self) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        if not graph:
            return
        self._remember_current()
        if self.canvas.delete_selected():
            self._history().commit()
            self.controller.schedule_save()
            self._update_history_buttons()
        else:
            self._history().discard_noop(graph)

    def validate_graph(self) -> bool:
        graph = self.current_graph()
        if not graph:
            return False
        issues = graph.diagnostics()
        if not issues:
            QMessageBox.information(
                self,
                "Flujo válido",
                f"'{graph.name}' no presenta errores ni advertencias.",
            )
            return True
        lines = []
        for level, message in issues:
            lines.append(f"{'ERROR' if level == 'error' else 'AVISO'} · {message}")
        text = "\n".join(lines)
        if any(level == "error" for level, _ in issues):
            QMessageBox.critical(self, "El flujo necesita correcciones", text)
            return False
        QMessageBox.warning(self, "Flujo válido con avisos", text)
        return True

    def test_graph(self) -> None:
        graph = self.current_graph()
        if not graph:
            return
        errors = [message for level, message in graph.diagnostics() if level == "error"]
        if errors:
            QMessageBox.critical(self, "No se puede probar", "\n".join(errors))
            return
        self.controller.logic_engine.test(graph)
        self.controller.notify("info", f"Prueba iniciada: {graph.name}")

    def undo(self) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        if graph and self._history().undo(graph):
            self._apply_graph_change()

    def redo(self) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        if graph and self._history().redo(graph):
            self._apply_graph_change()

    def export_graph(self) -> None:
        graph = self.current_graph()
        if not graph or not graph.nodes:
            QMessageBox.information(self, "Nada que exportar", "El flujo no contiene nodos.")
            return
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", graph.name).strip("_") or "flujo"
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar flujo como imagen",
            str(Path.home() / f"{safe_name}.png"),
            "Imagen PNG (*.png)",
        )
        if not destination:
            return
        if not destination.lower().endswith(".png"):
            destination += ".png"
        if self.canvas.export_png(destination):
            self.controller.notify("success", f"Imagen exportada: {destination}")
        else:
            QMessageBox.warning(self, "No se pudo exportar", "No fue posible crear la imagen PNG.")

    def bind_graph(self) -> None:
        if self._locked():
            return
        graph = self.current_graph()
        if not graph:
            return
        trigger = next((node for node in graph.nodes if node.kind == "trigger_key"), None)
        source = str(trigger.config.get("key", "f13")) if trigger else "f13"
        mapping = Mapping(source=source, action=Action("logic_graph", graph.id), suppress=True)
        dialog = MappingDialog(self.controller, mapping=mapping, parent=self)
        if dialog.exec():
            self.controller.active_profile().mappings.append(dialog.result_mapping())
            self.controller.profile_changed()
            self.controller.notify("success", "La lógica quedó asignada a una tecla")

    def add_template(self) -> None:
        if self._locked():
            return
        graph = LogicGraph(name="F13 · Chrome")
        trigger = LogicNode(kind="trigger_key", title="F13", x=0, y=60, config={"key": "f13"})
        condition = LogicNode(
            kind="condition_active_process",
            title="¿Chrome activo?",
            x=330,
            y=60,
            config={"process": "chrome.exe"},
        )
        yes = LogicNode(
            kind="action",
            title="Nueva pestaña",
            x=680,
            y=-40,
            config={"action": {"type": "hotkey", "value": "ctrl+t", "options": {}}},
        )
        no = LogicNode(
            kind="action",
            title="Abrir Chrome",
            x=680,
            y=190,
            config={
                "action": {
                    "type": "open_program",
                    "value": r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
                    "options": {},
                }
            },
        )
        graph.nodes = [trigger, condition, yes, no]
        graph.edges = [
            LogicEdge(trigger.id, condition.id, "next"),
            LogicEdge(condition.id, yes.id, "yes"),
            LogicEdge(condition.id, no.id, "no"),
        ]
        profile = self.controller.active_profile()
        profile.logic_graphs.append(graph)
        profile.mappings.append(Mapping(source="f13", action=Action("logic_graph", graph.id), suppress=True))
        self._pending_graph_id = graph.id
        self.controller.profile_changed()
        self.controller.notify("success", "Plantilla creada y asignada a F13")

    def _node_moved(self) -> None:
        self.controller.schedule_save()

    def _remember_current(self) -> None:
        graph = self.current_graph()
        if graph and not self._is_locked():
            self._history(graph).remember(graph)
            self._update_history_buttons()

    def _finish_canvas_change(self) -> None:
        graph = self.current_graph()
        if graph:
            self._history(graph).discard_noop(graph)
            self.controller.schedule_save()
            self._update_history_buttons()

    def _apply_graph_change(self, selected_ids: list[str] | None = None) -> None:
        graph = self.current_graph()
        if not graph:
            return
        self.controller.schedule_save()
        self._history(graph).commit()
        self.canvas.set_graph(graph)
        self.canvas.set_editable(not self._is_locked())
        if selected_ids:
            self.canvas.select_nodes(selected_ids)
        self._update_history_buttons()

    def _history_key(self, graph: LogicGraph) -> str:
        return f"{self.controller.active_profile().id}:{graph.id}"

    def _history(self, graph: LogicGraph | None = None) -> LogicHistory:
        graph = graph or self.current_graph()
        if not graph:
            return LogicHistory()
        return self._histories.setdefault(self._history_key(graph), LogicHistory())

    def _update_history_buttons(self) -> None:
        graph = self.current_graph()
        history = self._history(graph) if graph else None
        editable = bool(graph) and not self._is_locked()
        self.undo_button.setEnabled(bool(editable and history and history.can_undo))
        self.redo_button.setEnabled(bool(editable and history and history.can_redo))

    def _update_edit_controls(self) -> None:
        enabled = bool(self.current_graph()) and not self._is_locked()
        for button in (
            self.add_node_button,
            self.edit_button,
            self.connect_button,
            self.duplicate_button,
            self.delete_button,
        ):
            button.setEnabled(enabled)

    def _canvas_menu(self, position: object) -> None:
        self.canvas.select_item_at(position)
        menu = QMenu(self)
        if self.canvas.selected_nodes():
            menu.addAction("Editar nodo", self.edit_selected_node)
            menu.addAction("Duplicar selección", self.duplicate_selection)
        if self.canvas.scene().selectedItems():
            menu.addAction("Eliminar selección", self.delete_selection)
        if menu.actions():
            menu.addSeparator()
        menu.addAction("Validar flujo", self.validate_graph)
        menu.addAction("Ajustar vista", self.canvas.fit_graph)
        menu.exec(self.canvas.viewport().mapToGlobal(position))

    def _setup_shortcuts(self) -> None:
        shortcuts = {
            "Delete": self.delete_selection,
            "Ctrl+D": self.duplicate_selection,
            "Ctrl+Z": self.undo,
            "Ctrl+Y": self.redo,
            "Ctrl+0": self.canvas.fit_graph,
        }
        for sequence, callback in shortcuts.items():
            shortcut = QShortcut(QKeySequence(sequence), self.canvas)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def _is_locked(self) -> bool:
        return bool(self.controller.active_profile().settings.get("locked", False))

    def _locked(self) -> bool:
        if self._is_locked():
            QMessageBox.information(
                self,
                "Perfil bloqueado",
                "Desbloquea el perfil desde Perfiles para editarlo.",
            )
            return True
        return False

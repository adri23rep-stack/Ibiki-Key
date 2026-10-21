from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...models import Action, Macro, MacroStep, Mapping
from ..catalog import action_summary
from ..common import Card, PageHeader, confirm, danger_button, primary_button, section_title
from ..dialogs import MacroPropertiesDialog, MacroStepDialog, MappingDialog
from ..recorder import MacroRecorder

SCRIPT_ACTIONS = {"command", "powershell"}


class MacrosPage(QWidget):
    def __init__(
        self,
        controller: object,
        bus: object,
        *,
        scope: str = "general",
        page_title: str = "Macros",
        page_subtitle: str = "Graba, duplica, importa y edita secuencias con tiempos reproducibles.",
    ):
        super().__init__()
        if scope not in {"general", "mouse"}:
            raise ValueError(f"Tipo de macro no compatible: {scope}")
        self.controller = controller
        self.bus = bus
        self.scope = scope
        self._pending_macro_id = ""
        self._recording_macro_id = ""
        self._step_clipboard: MacroStep | None = None
        self._shortcuts: list[QShortcut] = []
        self.recorder = MacroRecorder(controller, mode="mouse" if scope == "mouse" else "all")
        self.recorder.count_changed.connect(self._record_count)
        self.recorder.failed.connect(lambda text: QMessageBox.warning(self, "No se pudo grabar", text))
        self.recorder.stop_requested.connect(lambda: self._stop_recording(save=True))

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 26)
        root.setSpacing(14)
        root.addWidget(PageHeader(page_title, page_subtitle))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = Card()
        left.setMinimumWidth(250)
        left.setMaximumWidth(350)
        title_row = QHBoxLayout()
        title_row.addWidget(section_title(page_title))
        title_row.addStretch(1)
        title_row.addWidget(primary_button("+", self.add_macro))
        left.box.addLayout(title_row)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar macro…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        left.box.addWidget(self.search)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(lambda *_: self.refresh_steps())
        left.box.addWidget(self.list, 1)
        macro_row = QHBoxLayout()
        macro_row.addWidget(QPushButton("Duplicar", clicked=self.duplicate_macro))
        macro_row.addWidget(QPushButton("Propiedades", clicked=self.edit_macro))
        left.box.addLayout(macro_row)
        file_row = QHBoxLayout()
        file_row.addWidget(QPushButton("Importar", clicked=self.import_macro))
        file_row.addWidget(QPushButton("Exportar", clicked=self.export_macro))
        left.box.addLayout(file_row)
        left.box.addWidget(danger_button("Eliminar macro", self.delete_macro))
        splitter.addWidget(left)

        right = Card()
        top = QHBoxLayout()
        self.title = section_title("Selecciona una macro")
        top.addWidget(self.title)
        top.addStretch(1)
        self.record_button = QPushButton("● Grabar en vivo", clicked=self.toggle_recording)
        self.run_button = primary_button("▶ Probar", self.run_macro)
        self.stop_button = QPushButton("■ Detener", clicked=self.stop_macro)
        self.bind_button = QPushButton("Asignar a botón", clicked=self.bind_mouse_button)
        top.addWidget(self.record_button)
        if self.scope == "mouse":
            top.addWidget(self.bind_button)
        top.addWidget(self.run_button)
        top.addWidget(self.stop_button)
        right.box.addLayout(top)
        self.mode = QLabel("")
        self.mode.setObjectName("Muted")
        self.mode.setWordWrap(True)
        right.box.addWidget(self.mode)
        self.record_options = QWidget()
        record_options_layout = QHBoxLayout(self.record_options)
        record_options_layout.setContentsMargins(0, 0, 0, 0)
        self.record_moves = QCheckBox("Grabar movimiento del cursor")
        self.record_moves.setChecked(True)
        self.move_interval = QSpinBox()
        self.move_interval.setRange(8, 250)
        self.move_interval.setValue(30)
        self.move_interval.setSuffix(" ms")
        record_options_layout.addWidget(self.record_moves)
        record_options_layout.addWidget(QLabel("Muestreo"))
        record_options_layout.addWidget(self.move_interval)
        record_options_layout.addSpacing(12)
        stop_hint = QLabel("Ctrl+Alt+F11 detiene sin grabar un clic")
        stop_hint.setObjectName("Muted")
        record_options_layout.addWidget(stop_hint)
        record_options_layout.addStretch(1)
        self.record_options.setVisible(self.scope == "mouse")
        right.box.addWidget(self.record_options)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "Acción", "Retraso", "Aleatorio", "Estado"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.edit_step)
        right.box.addWidget(self.table, 1)

        controls = QHBoxLayout()
        controls.addWidget(primary_button("+ Añadir paso", self.add_step))
        controls.addWidget(QPushButton("Editar", clicked=self.edit_step))
        controls.addWidget(QPushButton("Duplicar", clicked=self.duplicate_step))
        controls.addWidget(QPushButton("Activar / desactivar", clicked=self.toggle_step))
        controls.addWidget(danger_button("Eliminar", self.delete_step))
        controls.addStretch(1)
        right.box.addLayout(controls)
        utility = QHBoxLayout()
        utility.addWidget(QPushButton("Copiar", clicked=self.copy_step))
        utility.addWidget(QPushButton("Pegar", clicked=self.paste_step))
        utility.addWidget(QPushButton("↑ Subir", clicked=lambda: self.move_step(-1)))
        utility.addWidget(QPushButton("↓ Bajar", clicked=lambda: self.move_step(1)))
        self.clipboard_status = QLabel("")
        self.clipboard_status.setObjectName("Muted")
        utility.addWidget(self.clipboard_status)
        utility.addStretch(1)
        right.box.addLayout(utility)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self._setup_shortcuts()
        bus.macros_changed.connect(self.refresh)
        bus.active_profile_changed.connect(self._active_profile_changed)
        self.refresh()

    def refresh(self) -> None:
        current = self.current_macro()
        selected_id = self._pending_macro_id or (current.id if current else "")
        self._pending_macro_id = ""
        query = self.search.text().strip().casefold()
        self.list.blockSignals(True)
        self.list.clear()
        for macro in self.controller.active_profile().macros:
            if macro.scope != self.scope:
                continue
            if query and query not in macro.name.casefold():
                continue
            running = "  ●" if macro.id in self.controller.macro_engine.running_ids() else ""
            state = "" if macro.enabled else "  ○ desactivada"
            item = QListWidgetItem(f"{macro.name}{running}{state}")
            item.setData(Qt.ItemDataRole.UserRole, macro.id)
            if not macro.enabled:
                item.setForeground(QBrush(QColor("#7E879D")))
            self.list.addItem(item)
            if macro.id == selected_id:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)
        self.refresh_steps()

    def refresh_steps(self) -> None:
        selected_step = self._selected_step()
        selected_step_id = selected_step.id if selected_step else ""
        macro = self.current_macro()
        self.table.setRowCount(0)
        if not macro:
            self.title.setText("Selecciona una macro")
            self.mode.setText("")
            return
        self.title.setText(macro.name)
        mode_labels = {
            "once": "Una vez",
            "count": "Repeticiones",
            "toggle": "Alternar",
            "while_held": "Mientras se mantiene",
            "infinite": "Infinita",
        }
        duration = self._duration_text(macro)
        enabled_steps = sum(1 for step in macro.steps if step.enabled)
        self.mode.setText(
            f"Modo: {mode_labels.get(macro.mode, macro.mode)} · "
            f"{enabled_steps}/{len(macro.steps)} pasos activos · {duration}"
        )
        if self.scope == "mouse":
            bindings = [
                item
                for item in self.controller.active_profile().mouse_mappings
                if item.action.type == "macro" and str(item.action.value) == macro.id
            ]
            if bindings:
                sources = ", ".join(sorted({item.source for item in bindings}))
                self.mode.setText(self.mode.text() + f" · Botón: {sources}")
            else:
                self.mode.setText(self.mode.text() + " · Sin botón asignado")
        scripts_allowed = bool(self.controller.active_profile().settings.get("scripts_allowed", False))
        if self._uses_scripts(macro) and not scripts_allowed:
            self.mode.setText(self.mode.text() + " · 🔒 CMD/PowerShell requiere autorización")
        for index, step in enumerate(macro.steps):
            row = self.table.rowCount()
            self.table.insertRow(row)
            blocked_script = step.action.type in SCRIPT_ACTIONS and not scripts_allowed
            values = [
                str(index + 1),
                action_summary(step.action.type, step.action.value),
                f"{step.delay_after_ms} ms",
                f"0–{step.random_delay_ms} ms" if step.random_delay_ms else "—",
                "🔒 Permiso requerido" if blocked_script else ("Activo" if step.enabled else "Desactivado"),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, step.id)
                if blocked_script:
                    item.setToolTip("Autoriza CMD/PowerShell al probar la macro o desde Perfiles > Editar.")
                if not step.enabled:
                    item.setForeground(QBrush(QColor("#7E879D")))
                self.table.setItem(row, column, item)
            if step.id == selected_step_id:
                self.table.selectRow(row)

    def current_macro(self) -> Macro | None:
        item = self.list.currentItem()
        if not item:
            return None
        macro_id = item.data(Qt.ItemDataRole.UserRole)
        return next(
            (x for x in self.controller.active_profile().macros if x.id == macro_id),
            None,
        )

    def add_macro(self) -> None:
        if self._locked():
            return
        macro = Macro(scope=self.scope)
        dialog = MacroPropertiesDialog(macro, self)
        if dialog.exec():
            dialog.apply(macro)
            self.controller.active_profile().macros.append(macro)
            self._pending_macro_id = macro.id
            self.search.clear()
            self.controller.profile_changed(restart=False)

    def duplicate_macro(self) -> None:
        if self._locked():
            return
        macro = self.current_macro()
        if not macro:
            return
        cloned = macro.clone()
        self.controller.active_profile().macros.append(cloned)
        self._pending_macro_id = cloned.id
        self.search.clear()
        self.controller.profile_changed(restart=False)
        self.controller.notify("success", f"Macro duplicada: {cloned.name}")

    def edit_macro(self) -> None:
        if self._locked():
            return
        macro = self.current_macro()
        if not macro:
            return
        dialog = MacroPropertiesDialog(macro, self)
        if dialog.exec():
            dialog.apply(macro)
            self._pending_macro_id = macro.id
            self.controller.profile_changed(restart=False)

    def delete_macro(self) -> None:
        if self._locked():
            return
        macro = self.current_macro()
        if not macro:
            return
        profile = self.controller.active_profile()
        direct = [
            mapping
            for mapping in [*profile.mappings, *profile.mouse_mappings]
            if mapping.action.type == "macro" and str(mapping.action.value) == macro.id
        ]
        macro_steps = [
            step
            for owner in profile.macros
            if owner is not macro
            for step in owner.steps
            if step.action.type == "macro" and str(step.action.value) == macro.id
        ]
        graph_nodes = [
            node
            for graph in profile.logic_graphs
            for node in graph.nodes
            if node.kind == "action"
            and isinstance(node.config.get("action"), dict)
            and node.config["action"].get("type") == "macro"
            and str(node.config["action"].get("value")) == macro.id
        ]
        references = len(direct) + len(macro_steps) + len(graph_nodes)
        detail = (
            f"\n\nTambién se limpiarán {references} referencia(s) para evitar acciones rotas."
            if references
            else ""
        )
        if confirm(self, "Eliminar macro", f"¿Eliminar '{macro.name}'?{detail}"):
            if self._recording_macro_id == macro.id:
                self._stop_recording(save=False)
            self.controller.macro_engine.stop(macro.id)
            profile.macros.remove(macro)
            profile.mappings = [mapping for mapping in profile.mappings if mapping not in direct]
            profile.mouse_mappings = [mapping for mapping in profile.mouse_mappings if mapping not in direct]
            for step in macro_steps:
                step.enabled = False
            for node in graph_nodes:
                node.config["action"] = {"type": "noop", "value": None, "options": {}}
                node.title = f"{node.title} · referencia eliminada"
            self.controller.profile_changed(restart=False)
            if references:
                self.controller.notify("warning", "Se limpiaron referencias a la macro eliminada")

    def export_macro(self) -> None:
        macro = self.current_macro()
        if not macro:
            return
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", macro.name).strip("_") or "macro"
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar macro",
            str(self.controller.storage.exports_dir / f"{safe_name}.ibikimacro"),
            "Macro de Ibiki Key (*.ibikimacro)",
        )
        if not destination:
            return
        try:
            saved = self.controller.storage.export_macro(macro, Path(destination))
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo exportar", str(exc))
            return
        self.controller.notify("success", f"Macro exportada: {saved}")

    def import_macro(self) -> None:
        if self._locked():
            return
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Importar macro",
            str(self.controller.storage.exports_dir),
            "Macro de Ibiki Key (*.ibikimacro)",
        )
        if not source:
            return
        try:
            macro = self.controller.storage.import_macro(Path(source))
        except Exception as exc:
            QMessageBox.critical(self, "Macro no válida", str(exc))
            return
        macro.scope = self.scope
        self.controller.active_profile().macros.append(macro)
        self._pending_macro_id = macro.id
        self.search.clear()
        self.controller.profile_changed(restart=False)
        self.controller.notify("success", f"Macro importada: {macro.name}")

    def add_step(self) -> None:
        if self._locked():
            return
        macro = self.current_macro()
        if not macro:
            QMessageBox.information(self, "Falta una macro", "Crea o selecciona una macro.")
            return
        dialog = MacroStepDialog(self.controller, parent=self)
        if dialog.exec():
            step = dialog.result_step()
            macro.steps.append(step)
            self.controller.profile_changed(restart=False)
            self._select_step(step.id)

    def edit_step(self) -> None:
        if self._locked():
            return
        macro = self.current_macro()
        step = self._selected_step()
        if not macro or not step:
            return
        dialog = MacroStepDialog(self.controller, step, self)
        if dialog.exec():
            replacement = dialog.result_step()
            macro.steps[macro.steps.index(step)] = replacement
            self.controller.profile_changed(restart=False)
            self._select_step(replacement.id)

    def duplicate_step(self) -> None:
        if self._locked():
            return
        macro = self.current_macro()
        step = self._selected_step()
        if not macro or not step:
            return
        cloned = step.clone()
        index = macro.steps.index(step) + 1
        macro.steps.insert(index, cloned)
        self.controller.profile_changed(restart=False)
        self._select_step(cloned.id)

    def toggle_step(self) -> None:
        if self._locked():
            return
        step = self._selected_step()
        if not step:
            return
        step.enabled = not step.enabled
        self.controller.profile_changed(restart=False)
        self._select_step(step.id)

    def delete_step(self) -> None:
        if self._locked():
            return
        macro = self.current_macro()
        step = self._selected_step()
        if macro and step:
            row = macro.steps.index(step)
            macro.steps.remove(step)
            self.controller.profile_changed(restart=False)
            if macro.steps:
                self.table.selectRow(min(row, len(macro.steps) - 1))

    def move_step(self, delta: int) -> None:
        if self._locked():
            return
        macro = self.current_macro()
        step = self._selected_step()
        if not macro or not step:
            return
        old = macro.steps.index(step)
        new = max(0, min(len(macro.steps) - 1, old + delta))
        if new != old:
            macro.steps.insert(new, macro.steps.pop(old))
            self.controller.profile_changed(restart=False)
            self._select_step(step.id)

    def copy_step(self) -> None:
        step = self._selected_step()
        if not step:
            return
        self._step_clipboard = step.clone()
        self.clipboard_status.setText("Paso copiado")

    def paste_step(self) -> None:
        if self._locked():
            return
        macro = self.current_macro()
        if not macro or not self._step_clipboard:
            return
        pasted = self._step_clipboard.clone()
        selected = self._selected_step()
        index = macro.steps.index(selected) + 1 if selected in macro.steps else len(macro.steps)
        macro.steps.insert(index, pasted)
        self.controller.profile_changed(restart=False)
        self._select_step(pasted.id)

    def run_macro(self) -> None:
        if self.recorder.running:
            QMessageBox.information(
                self,
                "Grabación en curso",
                "Detén la grabación antes de reproducir una macro.",
            )
            return
        macro = self.current_macro()
        if not macro:
            return
        if not macro.enabled:
            QMessageBox.information(self, "Macro desactivada", "Actívala desde Propiedades para probarla.")
            return
        profile = self.controller.active_profile()
        if self._uses_scripts(macro) and not profile.settings.get("scripts_allowed", False):
            if profile.settings.get("locked", False):
                QMessageBox.information(
                    self,
                    "Perfil bloqueado",
                    "Esta macro contiene CMD o PowerShell. Desbloquea el perfil para autorizar scripts.",
                )
                return
            answer = QMessageBox.question(
                self,
                "Autorizar CMD y PowerShell",
                f"La macro '{macro.name}' contiene comandos que pueden modificar el equipo.\n\n"
                f"¿Permitir CMD y PowerShell en el perfil '{profile.name}' y ejecutar la macro?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            profile.settings["scripts_allowed"] = True
            profile.settings["trusted_actions"] = True
            self.controller.profile_changed(restart=False)
            self.controller.notify(
                "warning",
                f"CMD y PowerShell habilitados en el perfil '{profile.name}'",
            )
            self.refresh_steps()
        self.controller.macro_engine.run(macro.id)

    def stop_macro(self) -> None:
        macro = self.current_macro()
        if macro:
            self.controller.macro_engine.stop(macro.id)

    def toggle_recording(self) -> None:
        if self.recorder.running:
            self._stop_recording(save=True)
            return
        if self._locked():
            return
        macro = self.current_macro()
        if not macro:
            QMessageBox.information(
                self,
                "Falta una macro",
                "Crea o selecciona una macro antes de grabar.",
            )
            return
        self.controller.macro_engine.stop_all()
        self.recorder.start(
            record_mouse_moves=self.record_moves.isChecked() if self.scope == "mouse" else False,
            move_interval_ms=self.move_interval.value(),
        )
        if self.recorder.running:
            self._recording_macro_id = macro.id
            self.list.setEnabled(False)
            self.run_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.bind_button.setEnabled(False)
            self.record_button.setText("■ Detener grabación (0)")
            self.record_button.setProperty("danger", True)
            self._polish_record_button()

    def _stop_recording(self, *, save: bool) -> None:
        steps = self.recorder.stop() if self.recorder.running else []
        macro_id = self._recording_macro_id
        self._recording_macro_id = ""
        self.list.setEnabled(True)
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.bind_button.setEnabled(True)
        self.record_button.setText("● Grabar en vivo")
        self.record_button.setProperty("danger", False)
        self._polish_record_button()
        if not save or not steps:
            if steps and not save:
                self.controller.notify("info", "Grabación descartada")
            return
        macro = next(
            (item for item in self.controller.active_profile().macros if item.id == macro_id),
            None,
        )
        if not macro:
            self.controller.notify("warning", "La macro de destino ya no existe; grabación descartada")
            return
        macro.steps.extend(steps)
        self._pending_macro_id = macro.id
        self.controller.profile_changed(restart=False)
        self.controller.notify("success", f"Se añadieron {len(steps)} eventos grabados")

    def _record_count(self, count: int) -> None:
        if self.recorder.running:
            self.record_button.setText(f"■ Detener grabación ({count})")

    def bind_mouse_button(self) -> None:
        if self.scope != "mouse" or self._locked():
            return
        macro = self.current_macro()
        if not macro:
            QMessageBox.information(self, "Falta una macro", "Crea o selecciona una macro de mouse.")
            return
        profile = self.controller.active_profile()
        mapping = Mapping(
            source="x",
            trigger="hold" if macro.mode == "while_held" else "press",
            action=Action("macro", macro.id),
            layer=profile.active_layer,
            suppress=False,
            note=f"Macro de mouse: {macro.name}",
        )
        dialog = MappingDialog(self.controller, mapping=mapping, mouse_mode=True, parent=self)
        dialog.setWindowTitle(f"Asignar '{macro.name}' a un botón")
        dialog.action_editor.setEnabled(False)
        if dialog.exec():
            result = dialog.result_mapping()
            result.action = Action("macro", macro.id)
            profile.mouse_mappings.append(result)
            self.controller.profile_changed()
            self.controller.notify("success", f"Macro asignada al botón {result.source}")
            self.refresh_steps()

    def _active_profile_changed(self, *_args: object) -> None:
        if self.recorder.running:
            self._stop_recording(save=False)
        self.refresh()

    def _selected_step(self) -> MacroStep | None:
        macro = self.current_macro()
        row = self.table.currentRow()
        if not macro or row < 0 or not self.table.item(row, 0):
            return None
        step_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((x for x in macro.steps if x.id == step_id), None)

    def _select_step(self, step_id: str) -> None:
        self.refresh_steps()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == step_id:
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                break

    def _setup_shortcuts(self) -> None:
        shortcuts = {
            "Delete": self.delete_step,
            "Ctrl+D": self.duplicate_step,
            "Ctrl+C": self.copy_step,
            "Ctrl+V": self.paste_step,
            "Space": self.toggle_step,
        }
        for sequence, callback in shortcuts.items():
            shortcut = QShortcut(QKeySequence(sequence), self.table)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    @staticmethod
    def _uses_scripts(macro: Macro) -> bool:
        return any(step.enabled and step.action.type in SCRIPT_ACTIONS for step in macro.steps)

    @classmethod
    def _duration_text(cls, macro: Macro) -> str:
        bounds = macro.duration_bounds_ms()
        if bounds is None:
            return "duración sin límite fijo"
        minimum, maximum = bounds
        if minimum == maximum:
            return f"duración estimada {cls._format_ms(minimum)}"
        return f"duración estimada {cls._format_ms(minimum)}–{cls._format_ms(maximum)}"

    @staticmethod
    def _format_ms(value: int) -> str:
        if value < 1000:
            return f"{value} ms"
        seconds = value / 1000
        if seconds < 60:
            return f"{seconds:.1f} s"
        return f"{int(seconds) // 60}:{int(seconds) % 60:02d} min"

    def _polish_record_button(self) -> None:
        self.record_button.style().unpolish(self.record_button)
        self.record_button.style().polish(self.record_button)

    def _locked(self) -> bool:
        if self.recorder.running:
            QMessageBox.information(
                self,
                "Grabación en curso",
                "Termina o descarta la grabación antes de modificar la macro.",
            )
            return True
        if self.controller.active_profile().settings.get("locked", False):
            QMessageBox.information(
                self,
                "Perfil bloqueado",
                "Desbloquea el perfil desde Perfiles para editarlo.",
            )
            return True
        return False

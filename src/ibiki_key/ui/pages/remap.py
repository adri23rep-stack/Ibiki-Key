from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...models import Action, Mapping
from ..catalog import TRIGGER_LABELS, action_summary
from ..common import Card, PageHeader, confirm, danger_button, primary_button
from ..dialogs import MappingDialog
from ..keyboard_widget import KeyboardWidget


class RemapPage(QWidget):
    def __init__(self, controller: object, bus: object):
        super().__init__()
        self.controller = controller
        self.bus = bus
        self.selected_key = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 26)
        root.setSpacing(14)
        root.addWidget(
            PageHeader("Remapeo", "Haz clic en una tecla, elige una acción y decide en qué capa funciona.")
        )

        top = QHBoxLayout()
        top.setSpacing(12)
        keyboard_card = Card()
        self.keyboard = KeyboardWidget()
        self.keyboard.key_selected.connect(self._key_selected)
        keyboard_card.box.addWidget(self.keyboard)
        self.selection_label = QLabel("Selecciona una tecla del teclado")
        self.selection_label.setObjectName("Muted")
        keyboard_card.box.addWidget(self.selection_label)
        top.addWidget(keyboard_card, 4)

        tools = Card()
        tools.setMaximumWidth(270)
        tools.box.addWidget(QLabel("Capa visible"))
        self.layer = QComboBox()
        self.layer.currentTextChanged.connect(self.refresh)
        tools.box.addWidget(self.layer)
        tools.box.addWidget(primary_button("+ Asignar tecla", self.add_mapping))
        tools.box.addWidget(QPushButton("⇄ Intercambiar dos teclas", clicked=self.swap_keys))
        tools.box.addWidget(QPushButton("⊘ Desactivar seleccionada", clicked=self.disable_key))
        tools.box.addSpacing(8)
        tools.box.addWidget(QLabel("Capas"))
        tools.box.addWidget(QPushButton("Nueva capa", clicked=self.add_layer))
        tools.box.addWidget(QPushButton("Eliminar capa", clicked=self.remove_layer))
        tools.box.addStretch(1)
        top.addWidget(tools, 1)
        root.addLayout(top, 3)

        list_card = Card()
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar tecla, acción o nota…")
        self.search.textChanged.connect(self._filter)
        bar.addWidget(self.search, 1)
        bar.addWidget(QPushButton("Editar", clicked=self.edit_mapping))
        bar.addWidget(danger_button("Eliminar", self.delete_mapping))
        list_card.box.addLayout(bar)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Origen", "Capa", "Disparador", "Acción", "Bloquea", "Nota"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.edit_mapping)
        list_card.box.addWidget(self.table)
        root.addWidget(list_card, 2)
        bus.mappings_changed.connect(self.refresh)
        bus.active_profile_changed.connect(lambda *_: self.refresh())
        self.refresh()

    def _locked(self) -> bool:
        if self.controller.active_profile().settings.get("locked", False):
            QMessageBox.information(
                self, "Perfil bloqueado", "Desbloquea el perfil desde Perfiles para editarlo."
            )
            return True
        return False

    def refresh(self, *_: object) -> None:
        profile = self.controller.active_profile()
        current_layer = self.layer.currentText() or profile.active_layer
        self.layer.blockSignals(True)
        self.layer.clear()
        self.layer.addItems(profile.layers)
        self.layer.setCurrentText(current_layer if current_layer in profile.layers else "Base")
        self.layer.blockSignals(False)
        self.table.setRowCount(0)
        for mapping in profile.mappings:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                mapping.source,
                mapping.layer,
                TRIGGER_LABELS.get(mapping.trigger, mapping.trigger),
                action_summary(mapping.action.type, mapping.action.value),
                "Sí" if mapping.suppress else "No",
                mapping.note,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, mapping.id)
                if not mapping.enabled:
                    item.setForeground(Qt.GlobalColor.gray)
                self.table.setItem(row, column, item)
        self.keyboard.set_mapped(
            {x.source for x in profile.mappings if x.layer == self.layer.currentText() and x.enabled}
        )
        self._filter()

    def _key_selected(self, key: str) -> None:
        self.selected_key = key
        self.selection_label.setText(f"Seleccionada: {key}")

    def select_key(self, key: str) -> None:
        """Selecciona una tecla desde otra vista, por ejemplo el Dashboard."""
        self.selected_key = key
        self.keyboard.select_key(key)
        self.selection_label.setText(f"Seleccionada: {key} · lista para editar")

    def add_mapping(self) -> None:
        if self._locked():
            return
        dialog = MappingDialog(self.controller, source=self.selected_key, parent=self)
        if dialog.exec():
            mapping = dialog.result_mapping()
            mapping.layer = self.layer.currentText()
            self.controller.active_profile().mappings.append(mapping)
            self.controller.profile_changed()

    def edit_mapping(self) -> None:
        if self._locked():
            return
        mapping = self._selected_mapping()
        if not mapping:
            return
        dialog = MappingDialog(self.controller, mapping=mapping, parent=self)
        if dialog.exec():
            new = dialog.result_mapping()
            index = self.controller.active_profile().mappings.index(mapping)
            self.controller.active_profile().mappings[index] = new
            self.controller.profile_changed()

    def delete_mapping(self) -> None:
        if self._locked():
            return
        mapping = self._selected_mapping()
        if mapping and confirm(self, "Eliminar asignación", f"¿Eliminar el remapeo de {mapping.source}?"):
            self.controller.active_profile().mappings.remove(mapping)
            self.controller.profile_changed()

    def disable_key(self) -> None:
        if self._locked():
            return
        if not self.selected_key:
            QMessageBox.information(self, "Falta una tecla", "Selecciona una tecla en el teclado visual.")
            return
        self.controller.active_profile().mappings.append(
            Mapping(
                source=self.selected_key,
                action=Action("noop", ""),
                layer=self.layer.currentText(),
                suppress=True,
            )
        )
        self.controller.profile_changed()

    def swap_keys(self) -> None:
        if self._locked():
            return
        first, ok = QInputDialog.getText(
            self, "Intercambiar teclas", "Primera tecla:", text=self.selected_key
        )
        if not ok or not first.strip():
            return
        second, ok = QInputDialog.getText(self, "Intercambiar teclas", "Segunda tecla:")
        if not ok or not second.strip():
            return
        layer = self.layer.currentText()
        profile = self.controller.active_profile()
        profile.mappings.extend(
            [
                Mapping(
                    source=first.strip().lower(), action=Action("key", second.strip().lower()), layer=layer
                ),
                Mapping(
                    source=second.strip().lower(), action=Action("key", first.strip().lower()), layer=layer
                ),
            ]
        )
        self.controller.profile_changed()

    def add_layer(self) -> None:
        if self._locked():
            return
        name, ok = QInputDialog.getText(self, "Nueva capa", "Nombre de la capa:")
        if ok and name.strip() and name.strip() not in self.controller.active_profile().layers:
            self.controller.active_profile().layers.append(name.strip())
            self.controller.profile_changed()

    def remove_layer(self) -> None:
        if self._locked():
            return
        name = self.layer.currentText()
        if name == "Base":
            QMessageBox.information(self, "Capa principal", "La capa Base no se puede eliminar.")
            return
        if confirm(self, "Eliminar capa", f"Las asignaciones de '{name}' pasarán a Base. ¿Continuar?"):
            profile = self.controller.active_profile()
            for mapping in [*profile.mappings, *profile.mouse_mappings]:
                if mapping.layer == name:
                    mapping.layer = "Base"
            profile.layers.remove(name)
            profile.active_layer = "Base"
            self.controller.profile_changed()

    def _selected_mapping(self) -> Mapping | None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selecciona una asignación", "Elige una fila de la tabla.")
            return None
        mapping_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((x for x in self.controller.active_profile().mappings if x.id == mapping_id), None)

    def _filter(self, *_: object) -> None:
        query = self.search.text().strip().lower()
        for row in range(self.table.rowCount()):
            text = " ".join(
                self.table.item(row, col).text().lower() for col in range(self.table.columnCount())
            )
            self.table.setRowHidden(row, bool(query and query not in text))

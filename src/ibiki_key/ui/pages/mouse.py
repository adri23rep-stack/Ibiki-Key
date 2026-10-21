from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..catalog import TRIGGER_LABELS, action_summary
from ..common import Card, PageHeader, confirm, danger_button, primary_button
from ..dialogs import MappingDialog
from ..keyboard_widget import MouseWidget


class MousePage(QWidget):
    def __init__(self, controller: object, bus: object):
        super().__init__()
        self.controller = controller
        self.bus = bus
        self.selected_button = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 26)
        root.setSpacing(14)
        root.addWidget(PageHeader("Mouse", "Botones, velocidad, scroll, doble clic y gestos por perfil."))
        self.panic_banner = QLabel()
        self.panic_banner.setWordWrap(True)
        root.addWidget(self.panic_banner)
        top = QHBoxLayout()
        visual_card = Card()
        self.mouse = MouseWidget()
        self.mouse.button_selected.connect(self._selected)
        visual_card.box.addWidget(self.mouse)
        self.selection = QLabel("Selecciona un botón")
        self.selection.setObjectName("Muted")
        visual_card.box.addWidget(self.selection)
        visual_card.box.addWidget(primary_button("+ Asignar botón", self.add_mapping))
        top.addWidget(visual_card, 1)

        settings = Card()
        form = QFormLayout()
        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setRange(1, 20)
        self.speed.valueChanged.connect(self._settings_changed)
        self.speed_value = QLabel()
        speed_row = QHBoxLayout()
        speed_row.addWidget(self.speed, 1)
        speed_row.addWidget(self.speed_value)
        self.double_click = QSpinBox()
        self.double_click.setRange(100, 2000)
        self.double_click.setSuffix(" ms")
        self.double_click.valueChanged.connect(self._settings_changed)
        self.scroll_lines = QSpinBox()
        self.scroll_lines.setRange(1, 100)
        self.scroll_lines.valueChanged.connect(self._settings_changed)
        self.gestures = QCheckBox("Activar gestos manteniendo clic derecho")
        self.gestures.toggled.connect(self._settings_changed)
        form.addRow("Velocidad del cursor", speed_row)
        form.addRow("Intervalo de doble clic", self.double_click)
        form.addRow("Líneas por rueda", self.scroll_lines)
        form.addRow("Gestos", self.gestures)
        settings.box.addLayout(form)
        warning = QLabel(
            "El remapeo avanzado puede detectar botones laterales. La supresión total por botón llegará con el controlador de entrada dedicado."
        )
        warning.setObjectName("Muted")
        warning.setWordWrap(True)
        settings.box.addWidget(warning)
        settings.box.addStretch(1)
        top.addWidget(settings, 2)
        root.addLayout(top, 2)

        table_card = Card()
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(QPushButton("Editar", clicked=self.edit_mapping))
        actions.addWidget(danger_button("Eliminar", self.delete_mapping))
        table_card.box.addLayout(actions)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Origen", "Capa", "Disparador", "Acción", "Nota"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_mapping)
        table_card.box.addWidget(self.table)
        root.addWidget(table_card, 2)
        bus.mappings_changed.connect(self.refresh)
        bus.active_profile_changed.connect(lambda *_: self.refresh())
        bus.automation_pause_changed.connect(self._panic_changed)
        self.refresh()
        self._panic_changed(controller.automation_paused)

    def refresh(self) -> None:
        profile = self.controller.active_profile()
        self.speed.blockSignals(True)
        self.double_click.blockSignals(True)
        self.scroll_lines.blockSignals(True)
        self.gestures.blockSignals(True)
        self.speed.setValue(profile.mouse.cursor_speed)
        self.speed_value.setText(str(profile.mouse.cursor_speed))
        self.double_click.setValue(profile.mouse.double_click_ms)
        self.scroll_lines.setValue(profile.mouse.scroll_lines)
        self.gestures.setChecked(profile.mouse.gestures_enabled)
        self.speed.blockSignals(False)
        self.double_click.blockSignals(False)
        self.scroll_lines.blockSignals(False)
        self.gestures.blockSignals(False)
        self.table.setRowCount(0)
        for mapping in profile.mouse_mappings:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                mapping.source,
                mapping.layer,
                TRIGGER_LABELS.get(mapping.trigger, mapping.trigger),
                action_summary(mapping.action.type, mapping.action.value),
                mapping.note,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, mapping.id)
                self.table.setItem(row, column, item)
        self.mouse.set_mapped({x.source for x in profile.mouse_mappings if x.enabled})

    def _selected(self, button: str) -> None:
        self.selected_button = button
        self.selection.setText(f"Seleccionado: {button}")

    def add_mapping(self) -> None:
        if self._locked():
            return
        dialog = MappingDialog(self.controller, source=self.selected_button, mouse_mode=True, parent=self)
        if dialog.exec():
            self.controller.active_profile().mouse_mappings.append(dialog.result_mapping())
            self.controller.profile_changed()

    def edit_mapping(self) -> None:
        if self._locked():
            return
        item = self._selected_mapping()
        if not item:
            return
        dialog = MappingDialog(self.controller, mapping=item, mouse_mode=True, parent=self)
        if dialog.exec():
            index = self.controller.active_profile().mouse_mappings.index(item)
            self.controller.active_profile().mouse_mappings[index] = dialog.result_mapping()
            self.controller.profile_changed()

    def delete_mapping(self) -> None:
        if self._locked():
            return
        item = self._selected_mapping()
        if item and confirm(self, "Eliminar asignación", f"¿Eliminar {item.source}?"):
            self.controller.active_profile().mouse_mappings.remove(item)
            self.controller.profile_changed()

    def _selected_mapping(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selecciona una asignación", "Elige una fila de la tabla.")
            return None
        item_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((x for x in self.controller.active_profile().mouse_mappings if x.id == item_id), None)

    def _settings_changed(self) -> None:
        profile = self.controller.active_profile()
        profile.mouse.cursor_speed = self.speed.value()
        profile.mouse.double_click_ms = self.double_click.value()
        profile.mouse.scroll_lines = self.scroll_lines.value()
        profile.mouse.gestures_enabled = self.gestures.isChecked()
        self.speed_value.setText(str(self.speed.value()))
        self.controller.profile_changed()

    def _panic_changed(self, paused: bool) -> None:
        if paused:
            self.panic_banner.setText(
                "⚠ MODO PÁNICO ACTIVO · Los remapeos, gestos, macros y movimientos del mouse "
                "están detenidos. Windows recuperó su velocidad, doble clic y scroll originales."
            )
            self.panic_banner.setStyleSheet(
                "background:#3B2112;color:#FDBA74;border:1px solid #9A5A24;"
                "border-radius:8px;padding:9px;font-weight:650;"
            )
        else:
            self.panic_banner.setText(
                "Ctrl+Alt+F12 activa el pánico: detiene toda automatización del mouse y "
                "restaura temporalmente sus ajustes originales de Windows."
            )
            self.panic_banner.setStyleSheet(
                "background:#122B2A;color:#5EEAD4;border:1px solid #235E59;"
                "border-radius:8px;padding:9px;"
            )

    def _locked(self) -> bool:
        if self.controller.active_profile().settings.get("locked", False):
            QMessageBox.information(
                self, "Perfil bloqueado", "Desbloquea el perfil desde Perfiles para editarlo."
            )
            return True
        return False

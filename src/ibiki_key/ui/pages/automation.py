from __future__ import annotations

import json
import secrets

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..common import Card, PageHeader, danger_button, primary_button, section_title


class AutomationPage(QWidget):
    def __init__(self, controller: object, bus: object):
        super().__init__()
        self.controller = controller
        self.bus = bus
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 26)
        root.setSpacing(14)
        root.addWidget(
            PageHeader(
                "Automatización", "Variables globales, acciones de Windows, API local e integraciones."
            )
        )
        top = QHBoxLayout()
        variables = Card()
        head = QHBoxLayout()
        head.addWidget(section_title("Variables globales"))
        head.addStretch(1)
        head.addWidget(primary_button("+ Variable", self.add_variable))
        variables.box.addLayout(head)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Nombre", "Valor JSON"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_variable)
        variables.box.addWidget(self.table)
        variable_buttons = QHBoxLayout()
        variable_buttons.addWidget(QPushButton("Editar", clicked=self.edit_variable))
        variable_buttons.addWidget(danger_button("Eliminar", self.delete_variable))
        variable_buttons.addStretch(1)
        variables.box.addLayout(variable_buttons)
        top.addWidget(variables, 2)

        api = Card()
        api.box.addWidget(section_title("API pública local"))
        form = QFormLayout()
        self.api_enabled = QCheckBox("Escuchar solo en 127.0.0.1")
        self.api_enabled.toggled.connect(self.save_api)
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.valueChanged.connect(self.save_api)
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.token.editingFinished.connect(self.save_api)
        form.addRow("Estado", self.api_enabled)
        form.addRow("Puerto", self.port)
        form.addRow("Token", self.token)
        api.box.addLayout(form)
        api.box.addWidget(QPushButton("Generar token nuevo", clicked=self.new_token))
        self.api_status = QLabel("La API se aplica al reiniciar los motores.")
        self.api_status.setObjectName("Muted")
        self.api_status.setWordWrap(True)
        api.box.addWidget(self.api_status)
        top.addWidget(api, 2)
        root.addLayout(top, 2)

        integrations = Card()
        integrations.box.addWidget(section_title("Integraciones"))
        rows = [
            ("API local", "Funcional", "#2DD4BF"),
            ("OBS", "Funciona mediante atajos, WebSocket llegará como plugin", "#F59E0B"),
            ("Discord / Spotify / Stream Deck", "Planeado para plugins", "#9299B2"),
            ("Philips Hue / MQTT", "Planeado para plugins", "#9299B2"),
        ]
        for name, status, color in rows:
            line = QHBoxLayout()
            line.addWidget(QLabel(name))
            line.addStretch(1)
            label = QLabel(status)
            label.setStyleSheet(f"color:{color};")
            line.addWidget(label)
            integrations.box.addLayout(line)
        note = QLabel(
            "Abrir programas, carpetas y enlaces; escribir texto; multimedia; volumen; brillo; captura; CMD y PowerShell ya están disponibles como acciones."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        integrations.box.addWidget(note)
        root.addWidget(integrations, 1)
        bus.active_profile_changed.connect(lambda *_: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        self.table.setRowCount(0)
        for name, value in sorted(self.controller.state.global_variables.items()):
            row = self.table.rowCount()
            self.table.insertRow(row)
            first = QTableWidgetItem(name)
            first.setData(Qt.ItemDataRole.UserRole, name)
            self.table.setItem(row, 0, first)
            self.table.setItem(row, 1, QTableWidgetItem(json.dumps(value, ensure_ascii=False)))
        settings = self.controller.state.settings
        self.api_enabled.blockSignals(True)
        self.port.blockSignals(True)
        self.token.blockSignals(True)
        self.api_enabled.setChecked(bool(settings.get("api_enabled", False)))
        self.port.setValue(int(settings.get("api_port", 8765)))
        self.token.setText(str(settings.get("api_token", "")))
        self.api_enabled.blockSignals(False)
        self.port.blockSignals(False)
        self.token.blockSignals(False)

    def add_variable(self) -> None:
        name, ok = QInputDialog.getText(self, "Nueva variable", "Nombre:")
        if not ok or not name.strip():
            return
        value, ok = QInputDialog.getText(self, "Nueva variable", "Valor JSON:", text="true")
        if not ok:
            return
        try:
            self.controller.set_variable(name.strip(), json.loads(value))
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "Valor inválido", str(exc))

    def edit_variable(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        name = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        old = self.controller.state.global_variables.get(name)
        value, ok = QInputDialog.getText(
            self, "Editar variable", f"{name}:", text=json.dumps(old, ensure_ascii=False)
        )
        if ok:
            try:
                self.controller.set_variable(name, json.loads(value))
                self.refresh()
            except Exception as exc:
                QMessageBox.warning(self, "Valor inválido", str(exc))

    def delete_variable(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            name = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.controller.state.global_variables.pop(name, None)
            self.controller.schedule_save()
            self.refresh()

    def save_api(self) -> None:
        settings = self.controller.state.settings
        settings["api_enabled"] = self.api_enabled.isChecked()
        settings["api_port"] = self.port.value()
        settings["api_token"] = self.token.text().strip()
        self.controller.schedule_save()
        self.api_status.setText("Cambios guardados. Reinicia los motores para aplicarlos.")

    def new_token(self) -> None:
        self.token.setText(secrets.token_urlsafe(24))
        self.save_api()

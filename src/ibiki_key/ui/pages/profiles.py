from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...models import Profile
from ..common import Card, PageHeader, confirm, danger_button, primary_button
from ..dialogs import ProfileDialog


class ProfilesPage(QWidget):
    def __init__(self, controller: object, bus: object):
        super().__init__()
        self.controller = controller
        self.bus = bus
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 26)
        root.setSpacing(14)
        root.addWidget(
            PageHeader("Perfiles", "Configuraciones ilimitadas con cambio manual o automático por programa.")
        )
        card = Card()
        toolbar = QHBoxLayout()
        toolbar.addWidget(primary_button("+ Crear perfil", self.add_profile))
        toolbar.addWidget(QPushButton("Editar", clicked=self.edit_profile))
        toolbar.addWidget(QPushButton("Duplicar", clicked=self.clone_profile))
        toolbar.addWidget(QPushButton("Activar", clicked=self.activate_profile))
        toolbar.addWidget(QPushButton("Bloquear / desbloquear", clicked=self.toggle_lock))
        toolbar.addStretch(1)
        toolbar.addWidget(QPushButton("Importar .ibiki", clicked=self.import_profile))
        toolbar.addWidget(QPushButton("Exportar", clicked=self.export_profile))
        toolbar.addWidget(danger_button("Eliminar", self.delete_profile))
        card.box.addLayout(toolbar)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Perfil", "Estado", "Programas", "Teclado", "Mouse", "Macros", "Seguridad"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.activate_profile)
        card.box.addWidget(self.table, 1)
        root.addWidget(card, 1)
        bus.profiles_changed.connect(self.refresh)
        bus.active_profile_changed.connect(lambda *_: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        self.table.setRowCount(0)
        for profile in self.controller.state.profiles:
            row = self.table.rowCount()
            self.table.insertRow(row)
            active = profile.id == self.controller.state.active_profile_id
            values = [
                profile.name,
                "● Activo" if active else "Disponible",
                ", ".join(profile.app_rules) or "Manual",
                str(len(profile.mappings)),
                str(len(profile.mouse_mappings)),
                str(len(profile.macros)),
                "🔒 Bloqueado" if profile.settings.get("locked", False) else "Editable",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, profile.id)
                if column == 0:
                    item.setForeground(Qt.GlobalColor.white)
                    item.setBackground(QColor(profile.color))
                elif active and column == 1:
                    item.setForeground(Qt.GlobalColor.cyan)
                self.table.setItem(row, column, item)
        active_row = next(
            (
                i
                for i, p in enumerate(self.controller.state.profiles)
                if p.id == self.controller.state.active_profile_id
            ),
            0,
        )
        if self.table.rowCount():
            self.table.selectRow(active_row)

    def selected_profile(self) -> Profile | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        profile_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((x for x in self.controller.state.profiles if x.id == profile_id), None)

    def add_profile(self) -> None:
        profile = Profile()
        dialog = ProfileDialog(profile, self)
        if dialog.exec():
            try:
                dialog.apply(profile)
            except Exception as exc:
                QMessageBox.warning(self, "Perfil inválido", str(exc))
                return
            self.controller.state.profiles.append(profile)
            self.controller.schedule_save()
            self.bus.profiles_changed.emit()

    def edit_profile(self) -> None:
        profile = self.selected_profile()
        if not profile:
            return
        if profile.settings.get("locked", False):
            QMessageBox.information(
                self, "Perfil bloqueado", "Usa 'Bloquear / desbloquear' antes de editarlo."
            )
            return
        dialog = ProfileDialog(profile, self)
        if dialog.exec():
            try:
                dialog.apply(profile)
            except Exception as exc:
                QMessageBox.warning(self, "Perfil inválido", str(exc))
                return
            self.controller.profile_changed()
            self.bus.profiles_changed.emit()

    def clone_profile(self) -> None:
        profile = self.selected_profile()
        if profile:
            self.controller.state.profiles.append(profile.clone())
            self.controller.schedule_save()
            self.bus.profiles_changed.emit()

    def activate_profile(self) -> None:
        profile = self.selected_profile()
        if profile:
            self.controller.activate_profile(profile.id, "Cambio manual")

    def toggle_lock(self) -> None:
        profile = self.selected_profile()
        if profile:
            profile.settings["locked"] = not profile.settings.get("locked", False)
            self.controller.schedule_save()
            self.bus.profiles_changed.emit()

    def delete_profile(self) -> None:
        profile = self.selected_profile()
        if not profile:
            return
        if len(self.controller.state.profiles) == 1:
            QMessageBox.information(self, "Perfil necesario", "Ibiki Key necesita al menos un perfil.")
            return
        if profile.settings.get("locked", False):
            QMessageBox.information(self, "Perfil bloqueado", "Desbloquéalo antes de eliminarlo.")
            return
        if confirm(self, "Eliminar perfil", f"¿Eliminar '{profile.name}' y todas sus macros?"):
            was_active = profile.id == self.controller.state.active_profile_id
            self.controller.state.profiles.remove(profile)
            if was_active:
                self.controller.state.active_profile_id = self.controller.state.profiles[0].id
                if self.controller.engine_running:
                    self.controller.restart_engines()
            self.controller.schedule_save()
            self.bus.profiles_changed.emit()
            self.bus.active_profile_changed.emit(self.controller.state.active_profile_id, "Perfil eliminado")

    def export_profile(self) -> None:
        profile = self.selected_profile()
        if not profile:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar perfil", f"{profile.name}.ibiki", "Perfil Ibiki (*.ibiki)"
        )
        if path:
            try:
                saved = self.controller.storage.export_profile(profile, Path(path))
                self.controller.notify("success", f"Perfil exportado: {saved.name}")
            except Exception as exc:
                QMessageBox.warning(self, "No se pudo exportar", str(exc))

    def import_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Importar perfil", "", "Perfil Ibiki (*.ibiki)")
        if path:
            try:
                profile = self.controller.storage.import_profile(Path(path))
                self.controller.state.profiles.append(profile)
                self.controller.schedule_save()
                self.bus.profiles_changed.emit()
                self.controller.notify("success", f"Perfil importado: {profile.name}")
            except Exception as exc:
                QMessageBox.warning(self, "No se pudo importar", str(exc))

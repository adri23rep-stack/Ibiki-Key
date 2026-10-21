from __future__ import annotations


from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...services import windows
from ..common import Card, PageHeader, primary_button, section_title


class SettingsPage(QWidget):
    def __init__(self, controller: object, bus: object, portable: bool):
        super().__init__()
        self.controller = controller
        self.bus = bus
        self.portable = portable
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 26)
        root.setSpacing(14)
        root.addWidget(PageHeader("Ajustes", "Inicio, seguridad, apariencia, respaldo y diagnóstico."))
        row = QHBoxLayout()
        general = Card()
        general.box.addWidget(section_title("General"))
        form = QFormLayout()
        self.start_engines = QCheckBox("Iniciar remapeo al abrir Ibiki Key")
        self.start_engines.toggled.connect(self.save)
        self.start_windows = QCheckBox("Iniciar con Windows")
        self.start_windows.toggled.connect(self._startup_changed)
        self.theme = QComboBox()
        self.theme.addItems(["Oscuro Ibiki", "Alto contraste"])
        self.theme.currentTextChanged.connect(self.save)
        form.addRow("Motores", self.start_engines)
        form.addRow("Windows", self.start_windows)
        form.addRow("Tema", self.theme)
        general.box.addLayout(form)
        mode = QLabel("Modo portátil" if portable else "Modo instalado / AppData")
        mode.setObjectName("Accent")
        general.box.addWidget(mode)
        general.box.addStretch(1)
        row.addWidget(general, 1)

        security = Card()
        security.box.addWidget(section_title("Seguridad"))
        admin = QLabel(
            "Ejecutándose como administrador" if windows.is_admin() else "Sin permisos de administrador"
        )
        admin.setObjectName("Accent" if windows.is_admin() else "Muted")
        security.box.addWidget(admin)
        explanation = QLabel(
            "Los permisos elevados solo son necesarios para bloquear entradas dentro de programas que también usan administrador."
        )
        explanation.setObjectName("Muted")
        explanation.setWordWrap(True)
        security.box.addWidget(explanation)
        if not windows.is_admin():
            security.box.addWidget(primary_button("Reiniciar como administrador", self.relaunch_admin))
        emergency = QLabel(
            "Pánico: Ctrl + Alt + F12\nDetener grabación de mouse: Ctrl + Alt + F11"
        )
        emergency.setObjectName("Accent")
        security.box.addWidget(emergency)
        security.box.addStretch(1)
        row.addWidget(security, 1)
        root.addLayout(row)

        maintenance = Card()
        maintenance.box.addWidget(section_title("Respaldo y diagnóstico"))
        buttons = QHBoxLayout()
        buttons.addWidget(QPushButton("Crear copia ahora", clicked=self.backup))
        buttons.addWidget(
            QPushButton(
                "Abrir carpeta de datos",
                clicked=lambda: windows.open_target(str(controller.storage.data_dir)),
            )
        )
        buttons.addWidget(
            QPushButton(
                "Abrir registros", clicked=lambda: windows.open_target(str(controller.storage.logs_dir))
            )
        )
        buttons.addWidget(QPushButton("Abrir carpeta de plugins", clicked=self.open_plugins))
        buttons.addStretch(1)
        maintenance.box.addLayout(buttons)
        info = QLabel(
            "Se conservan las 20 copias más recientes. Actualizaciones automáticas, nube y traducciones adicionales quedan preparadas para versiones posteriores."
        )
        info.setObjectName("Muted")
        info.setWordWrap(True)
        maintenance.box.addWidget(info)
        root.addWidget(maintenance)

        plugins = Card()
        plugins.box.addWidget(section_title("Plugins locales"))
        plugin_note = QLabel("Los plugins ejecutan código en tu PC. Activa únicamente archivos de confianza.")
        plugin_note.setObjectName("Muted")
        plugin_note.setWordWrap(True)
        plugins.box.addWidget(plugin_note)
        self.plugin_list = QListWidget()
        self.plugin_list.setMaximumHeight(130)
        plugins.box.addWidget(self.plugin_list)
        plugin_buttons = QHBoxLayout()
        plugin_buttons.addWidget(QPushButton("Actualizar lista", clicked=self.refresh_plugins))
        plugin_buttons.addWidget(primary_button("Aplicar y recargar", self.apply_plugins))
        plugin_buttons.addStretch(1)
        plugins.box.addLayout(plugin_buttons)
        root.addWidget(plugins)
        root.addStretch(1)
        self.refresh()

    def refresh(self) -> None:
        settings = self.controller.state.settings
        self.start_engines.blockSignals(True)
        self.start_windows.blockSignals(True)
        self.theme.blockSignals(True)
        self.start_engines.setChecked(bool(settings.get("start_engines", True)))
        self.start_windows.setChecked(bool(settings.get("start_with_windows", False)))
        self.theme.setCurrentText(str(settings.get("theme", "Oscuro Ibiki")))
        self.start_engines.blockSignals(False)
        self.start_windows.blockSignals(False)
        self.theme.blockSignals(False)
        self.refresh_plugins()

    def save(self) -> None:
        settings = self.controller.state.settings
        settings["start_engines"] = self.start_engines.isChecked()
        settings["start_with_windows"] = self.start_windows.isChecked()
        settings["theme"] = self.theme.currentText()
        self.controller.schedule_save()
        self.bus.theme_changed.emit(self.theme.currentText())

    def _startup_changed(self, enabled: bool) -> None:
        try:
            windows.set_start_with_windows(enabled, windows.startup_command(self.controller.project_root))
            self.save()
        except Exception as exc:
            self.start_windows.blockSignals(True)
            self.start_windows.setChecked(not enabled)
            self.start_windows.blockSignals(False)
            QMessageBox.warning(self, "No se pudo cambiar el inicio", str(exc))

    def relaunch_admin(self) -> None:
        if windows.relaunch_as_admin():
            self.controller.save_now()
            self.window().close()
        else:
            QMessageBox.warning(self, "No se pudo elevar", "Windows rechazó el reinicio como administrador.")

    def backup(self) -> None:
        self.controller.save_now()
        path = self.controller.storage.create_backup()
        if path:
            self.controller.notify("success", f"Copia creada: {path.name}")

    def open_plugins(self) -> None:
        path = self.controller.storage.data_dir / "plugins"
        path.mkdir(parents=True, exist_ok=True)
        windows.open_target(str(path))

    def refresh_plugins(self) -> None:
        self.plugin_list.clear()
        enabled = set(self.controller.state.settings.get("enabled_plugins", []))
        for plugin in self.controller.plugin_manager.discover():
            item = QListWidgetItem(f"{plugin.name}  ·  {plugin.version}")
            item.setData(0x0100, plugin.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if plugin.id in enabled else Qt.CheckState.Unchecked)
            item.setToolTip(plugin.description)
            self.plugin_list.addItem(item)
        if self.plugin_list.count() == 0:
            item = QListWidgetItem("No hay plugins instalados")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.plugin_list.addItem(item)

    def apply_plugins(self) -> None:
        enabled: list[str] = []
        for index in range(self.plugin_list.count()):
            item = self.plugin_list.item(index)
            plugin_id = item.data(0x0100)
            if plugin_id and item.checkState() == Qt.CheckState.Checked:
                enabled.append(str(plugin_id))
        self.controller.state.settings["enabled_plugins"] = enabled
        self.controller.schedule_save()
        self.controller.reload_plugins()
        self.refresh_plugins()

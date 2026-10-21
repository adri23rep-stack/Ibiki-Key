from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..constants import APP_NAME, VERSION
from .common import Toast
from .pages.automation import AutomationPage
from .pages.dashboard import DashboardPage
from .pages.logic import LogicPage
from .pages.macros import MacrosPage
from .pages.monitor import MonitorPage
from .pages.mouse import MousePage
from .pages.mouse_macros import MouseMacrosPage
from .pages.profiles import ProfilesPage
from .pages.remap import RemapPage
from .pages.settings import SettingsPage
from .style import APP_STYLE


class MainWindow(QMainWindow):
    def __init__(self, controller: object, bus: object, *, portable: bool):
        super().__init__()
        self.controller = controller
        self.bus = bus
        self.portable = portable
        self.setWindowTitle(f"{APP_NAME} · {VERSION}")
        self.setMinimumSize(1120, 720)
        self.resize(1440, 900)
        self.setStyleSheet(APP_STYLE + self._theme_extra())
        icon_path = controller.project_root / "assets" / "ibiki-key.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self._force_quit = False

        root_widget = QWidget()
        root_widget.setObjectName("AppRoot")
        root = QHBoxLayout(root_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(root_widget)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(218)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 18, 12, 14)
        sidebar_layout.setSpacing(5)
        brand = QHBoxLayout()
        mark = QLabel("IK")
        mark.setFixedSize(42, 42)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet("background:#7C3AED;border-radius:12px;font-size:16px;font-weight:800;")
        name_box = QVBoxLayout()
        self.brand_title = QLabel("Ibiki Key")
        self.brand_title.setObjectName("AppTitle")
        self.brand_beta = QLabel("ALPHA · LIVE DASHBOARD 0.4")
        self.brand_beta.setStyleSheet("color:#A78BFA;font-size:9px;font-weight:700;")
        name_box.addWidget(self.brand_title)
        name_box.addWidget(self.brand_beta)
        brand.addWidget(mark)
        brand.addLayout(name_box)
        brand.addStretch(1)
        sidebar_layout.addLayout(brand)
        sidebar_layout.addSpacing(15)

        self.stack = QStackedWidget()
        self.pages = [
            DashboardPage(controller, bus),
            RemapPage(controller, bus),
            MousePage(controller, bus),
            MouseMacrosPage(controller, bus),
            MacrosPage(controller, bus),
            LogicPage(controller, bus),
            ProfilesPage(controller, bus),
            MonitorPage(controller, bus),
            AutomationPage(controller, bus),
            SettingsPage(controller, bus, portable),
        ]
        self.nav = [
            ("⌂", "Dashboard", 0),
            ("⌨", "Remapeo", 1),
            ("●", "Mouse", 2),
            ("⇝", "Macros mouse", 3),
            ("⚡", "Macros teclado", 4),
            ("◇", "Lógica visual", 5),
            ("▣", "Perfiles", 6),
            ("▥", "Monitor", 7),
            ("◎", "Automatización", 8),
            ("⚙", "Ajustes", 9),
        ]
        self.nav_buttons: list[QPushButton] = []
        for icon, label, index in self.nav:
            button = QPushButton(f"{icon}  {label}")
            button.setProperty("nav", True)
            button.setCheckable(True)
            button.setToolTip(label)
            button.clicked.connect(lambda checked=False, value=index: self.show_page(value))
            self.nav_buttons.append(button)
            sidebar_layout.addWidget(button)
            self.stack.addWidget(self.pages[index])
        sidebar_layout.addStretch(1)
        self.sidebar_shortcut = QLabel("Ctrl + Alt + F12\nPausa de emergencia")
        self.sidebar_shortcut.setObjectName("Muted")
        self.sidebar_shortcut.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.sidebar_shortcut)
        self.sidebar_version = QLabel(VERSION)
        self.sidebar_version.setObjectName("Muted")
        self.sidebar_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.sidebar_version)
        root.addWidget(self.sidebar)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        topbar = QFrame()
        topbar.setObjectName("TopBar")
        topbar.setFixedHeight(58)
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(20, 0, 20, 0)
        self.sidebar_toggle = QPushButton("☰")
        self.sidebar_toggle.setProperty("topIcon", True)
        self.sidebar_toggle.setToolTip("Contraer o ampliar la barra lateral")
        self.sidebar_toggle.clicked.connect(self._toggle_sidebar)
        top_layout.addWidget(self.sidebar_toggle)
        self.page_name = QLabel("Dashboard")
        self.page_name.setObjectName("SectionTitle")
        top_layout.addWidget(self.page_name)
        top_layout.addStretch(1)
        self.profile_label = QLabel()
        self.profile_label.setObjectName("Accent")
        top_layout.addWidget(self.profile_label)
        self.engine_status = QLabel("● Detenido")
        self.engine_status.setStyleSheet("color:#FB7185;font-weight:650;")
        top_layout.addWidget(self.engine_status)
        self.panic_toggle = QPushButton("⚠ Pánico")
        self.panic_toggle.setToolTip(
            "Detiene macros, remapeos y movimientos; restaura los ajustes del mouse de Windows."
        )
        self.panic_toggle.clicked.connect(self.controller.toggle_automation_pause)
        top_layout.addWidget(self.panic_toggle)
        self.engine_toggle = QPushButton("Iniciar")
        self.engine_toggle.clicked.connect(self._toggle_engine)
        top_layout.addWidget(self.engine_toggle)
        body_layout.addWidget(topbar)
        body_layout.addWidget(self.stack, 1)
        root.addWidget(body, 1)

        self.toast = Toast(root_widget)
        bus.toast_requested.connect(self.toast.show_message)
        bus.engine_state_changed.connect(self._engine_state)
        bus.automation_pause_changed.connect(self._automation_pause_state)
        bus.active_profile_changed.connect(lambda *_: self._profile_changed())
        bus.profiles_changed.connect(self._profile_changed)
        bus.theme_changed.connect(self._apply_theme)
        self.pages[0].navigate_requested.connect(self.show_page)
        self.pages[0].remap_key_requested.connect(self._remap_from_dashboard)
        self._setup_shortcuts()
        self._setup_tray(icon_path)
        self.show_page(0)
        self._profile_changed()
        self._engine_state(controller.engine_running, "")
        self._automation_pause_state(controller.automation_paused)
        self._set_sidebar_collapsed(bool(controller.state.settings.get("sidebar_collapsed", False)))

    def show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for position, button in enumerate(self.nav_buttons):
            button.setChecked(position == index)
        names = [
            "Dashboard",
            "Remapeo",
            "Mouse",
            "Macros del mouse",
            "Macros de teclado",
            "Lógica visual",
            "Perfiles",
            "Monitor",
            "Automatización",
            "Ajustes",
        ]
        self.page_name.setText(names[index])
        page = self.pages[index]
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()

    def _toggle_sidebar(self) -> None:
        collapsed = self.sidebar.width() > 100
        self._set_sidebar_collapsed(collapsed)
        self.controller.state.settings["sidebar_collapsed"] = collapsed
        self.controller.schedule_save()

    def _set_sidebar_collapsed(self, collapsed: bool) -> None:
        self.sidebar.setFixedWidth(74 if collapsed else 218)
        self.brand_title.setVisible(not collapsed)
        self.brand_beta.setVisible(not collapsed)
        self.sidebar_shortcut.setVisible(not collapsed)
        self.sidebar_version.setVisible(not collapsed)
        self.sidebar_toggle.setText("☰" if not collapsed else "☷")
        for button, (icon, label, _index) in zip(self.nav_buttons, self.nav, strict=True):
            button.setText(icon if collapsed else f"{icon}  {label}")
            button.setProperty("compact", collapsed)
            button.style().unpolish(button)
            button.style().polish(button)

    def _remap_from_dashboard(self, key: str) -> None:
        page = self.pages[1]
        select_key = getattr(page, "select_key", None)
        if callable(select_key):
            select_key(key)
        self.show_page(1)

    def _toggle_engine(self) -> None:
        if self.controller.engine_running:
            self.controller.stop_engines()
        else:
            self.controller.start_engines()

    def _engine_state(self, running: bool, detail: str) -> None:
        self.engine_status.setText("● Activo" if running else "● Detenido")
        self.engine_status.setStyleSheet(f"color:{'#2DD4BF' if running else '#FB7185'};font-weight:650;")
        self.engine_toggle.setText("Detener" if running else "Iniciar")
        self.engine_toggle.setProperty("danger", running)
        self.engine_toggle.style().unpolish(self.engine_toggle)
        self.engine_toggle.style().polish(self.engine_toggle)
        if self.controller.automation_paused:
            self.engine_status.setText("● PÁNICO")
            self.engine_status.setStyleSheet("color:#F59E0B;font-weight:750;")

    def _automation_pause_state(self, paused: bool) -> None:
        self.panic_toggle.setText("▶ Reanudar" if paused else "⚠ Pánico")
        self.panic_toggle.setProperty("danger", not paused)
        self.panic_toggle.style().unpolish(self.panic_toggle)
        self.panic_toggle.style().polish(self.panic_toggle)
        if paused:
            self.engine_status.setText("● PÁNICO")
            self.engine_status.setStyleSheet("color:#F59E0B;font-weight:750;")
        else:
            self._engine_state(self.controller.engine_running, "")

    def _profile_changed(self) -> None:
        self.profile_label.setText(
            f"{self.controller.active_profile().name}  ·  {self.controller.active_profile().active_layer}"
        )

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self.show_page(0))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self.show_page(1))
        QShortcut(QKeySequence("Ctrl+3"), self, activated=lambda: self.show_page(2))
        QShortcut(QKeySequence("Ctrl+4"), self, activated=lambda: self.show_page(3))
        QShortcut(QKeySequence("Ctrl+5"), self, activated=lambda: self.show_page(4))

    def _setup_tray(self, icon_path: object) -> None:
        self.tray: QSystemTrayIcon | None = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(QIcon(str(icon_path)), self)
        menu = QMenu()
        show_action = QAction("Mostrar Ibiki Key", self)
        show_action.triggered.connect(self._show_from_tray)
        toggle_action = QAction("Iniciar / detener motores", self)
        toggle_action.triggered.connect(self._toggle_engine)
        panic_action = QAction("Pánico / reanudar", self)
        panic_action.triggered.connect(self.controller.toggle_automation_pause)
        quit_action = QAction("Salir", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(show_action)
        menu.addAction(toggle_action)
        menu.addAction(panic_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: (
                self._show_from_tray() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
            )
        )
        self.tray.show()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit(self) -> None:
        self._force_quit = True
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.controller.state.settings.get("close_to_tray", False) and self.tray and not self._force_quit:
            self.hide()
            self.tray.showMessage(
                "Ibiki Key", "Sigue activo en segundo plano.", QSystemTrayIcon.MessageIcon.Information, 2500
            )
            event.ignore()
            return
        event.accept()

    def resizeEvent(self, event: object) -> None:  # noqa: N802
        super().resizeEvent(event)  # type: ignore[arg-type]
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast.move(max(10, self.centralWidget().width() - self.toast.width() - 24), 76)

    def _apply_theme(self, theme: str) -> None:
        self.setStyleSheet(APP_STYLE + self._theme_extra(theme))

    def _theme_extra(self, theme: str | None = None) -> str:
        if (theme or self.controller.state.settings.get("theme")) == "Alto contraste":
            return "\n* { color:#FFFFFF; } QFrame#Card { border:2px solid #59627D; } QPushButton { border:2px solid #59627D; }"
        return ""

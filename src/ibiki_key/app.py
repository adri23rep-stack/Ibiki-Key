from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .constants import APP_NAME, ORGANIZATION, VERSION
from .controller import AppController
from .events import EventBus
from .logging_setup import configure_logging
from .storage import Storage, resolve_data_dir

log = logging.getLogger(__name__)


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def run() -> int:
    root = project_root()
    data_dir, portable = resolve_data_dir(root)
    storage = Storage(data_dir)
    configure_logging(storage.logs_dir)
    log.info("Iniciando %s %s (portátil=%s)", APP_NAME, VERSION, portable)

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName(ORGANIZATION)
    icon_path = root / "assets" / "ibiki-key.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    try:
        state = storage.load()
        bus = EventBus()
        controller = AppController(root, storage, state, bus)
        from .ui.main_window import MainWindow

        window = MainWindow(controller, bus, portable=portable)
        app.aboutToQuit.connect(controller.shutdown)
        window.show()
        if "--minimized" in sys.argv:
            window.showMinimized()
        if state.settings.get("start_engines", True):
            controller.start_engines()
        return app.exec()
    except Exception as exc:
        log.exception("Error fatal al iniciar")
        QMessageBox.critical(
            None,
            "Ibiki Key no pudo iniciar",
            f"Ocurrió un error inesperado:\n\n{exc}\n\nRevisa el archivo de registro en:\n{storage.logs_dir}",
        )
        return 1

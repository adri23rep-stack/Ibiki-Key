from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def clear_layout(layout: QVBoxLayout | QHBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()
        child = item.layout()
        if child:
            clear_layout(child)  # type: ignore[arg-type]


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, padding: int = 16):
        super().__init__(parent)
        self.setObjectName("Card")
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(padding, padding, padding, padding)
        self.box.setSpacing(10)


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(3)
        label = QLabel(title)
        label.setObjectName("PageTitle")
        sub = QLabel(subtitle)
        sub.setObjectName("Muted")
        sub.setWordWrap(True)
        layout.addWidget(label)
        layout.addWidget(sub)


class MetricCard(Card):
    def __init__(self, label: str, value: str = "0", accent: str = "#8B5CF6"):
        super().__init__()
        top = QLabel(label)
        top.setObjectName("Muted")
        self.value = QLabel(value)
        self.value.setObjectName("Metric")
        self.value.setStyleSheet(f"color: {accent};")
        self.box.addWidget(top)
        self.box.addWidget(self.value)


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("SectionTitle")
    return label


def primary_button(text: str, callback: Callable[[], None] | None = None) -> QPushButton:
    button = QPushButton(text)
    button.setProperty("primary", True)
    if callback:
        button.clicked.connect(callback)
    return button


def danger_button(text: str, callback: Callable[[], None] | None = None) -> QPushButton:
    button = QPushButton(text)
    button.setProperty("danger", True)
    if callback:
        button.clicked.connect(callback)
    return button


def confirm(parent: QWidget, title: str, text: str) -> bool:
    return (
        QMessageBox.question(
            parent,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        == QMessageBox.StandardButton.Yes
    )


class Toast(QFrame):
    COLORS = {
        "success": ("#0D2F2C", "#2DD4BF"),
        "warning": ("#382811", "#F59E0B"),
        "error": ("#3B1B28", "#FB7185"),
        "info": ("#1D2544", "#60A5FA"),
    }

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(340)
        self.setMaximumWidth(520)
        self.box = QHBoxLayout(self)
        self.box.setContentsMargins(14, 12, 14, 12)
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.box.addWidget(self.label)
        self.hide()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_message(self, level: str, message: str) -> None:
        background, border = self.COLORS.get(level, self.COLORS["info"])
        self.setStyleSheet(
            f"QFrame {{ background:{background}; border:1px solid {border}; border-radius:10px; }}"
            "QLabel { border:0; background:transparent; color:#FFFFFF; }"
        )
        self.label.setText(message)
        self.adjustSize()
        parent = self.parentWidget()
        if parent:
            self.move(max(10, parent.width() - self.width() - 24), 76)
        self.show()
        self.raise_()
        self.timer.start(4300)

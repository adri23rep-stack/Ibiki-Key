from __future__ import annotations

import time
from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


@dataclass(frozen=True, slots=True)
class KeySpec:
    key: str
    label: str
    x: float
    y: float
    width: float = 1.0
    height: float = 1.0


def _row(y: float, values: list[tuple[str, str, float]], *, x: float = 0.0) -> list[KeySpec]:
    result: list[KeySpec] = []
    cursor = x
    for key, label, width in values:
        result.append(KeySpec(key, label, cursor, y, width))
        cursor += width + 0.09
    return result


# Distribución ISO completa. Las coordenadas están expresadas en unidades de tecla,
# por lo que conserva su proporción al redimensionar la ventana.
KEY_SPECS: list[KeySpec] = [
    KeySpec("esc", "Esc", 0.0, 0.0),
    KeySpec("f1", "F1", 2.0, 0.0),
    KeySpec("f2", "F2", 3.09, 0.0),
    KeySpec("f3", "F3", 4.18, 0.0),
    KeySpec("f4", "F4", 5.27, 0.0),
    KeySpec("f5", "F5", 6.68, 0.0),
    KeySpec("f6", "F6", 7.77, 0.0),
    KeySpec("f7", "F7", 8.86, 0.0),
    KeySpec("f8", "F8", 9.95, 0.0),
    KeySpec("f9", "F9", 11.36, 0.0),
    KeySpec("f10", "F10", 12.45, 0.0),
    KeySpec("f11", "F11", 13.54, 0.0),
    KeySpec("f12", "F12", 14.63, 0.0),
    KeySpec("print screen", "Impr", 16.28, 0.0),
    KeySpec("scroll lock", "Bloq\nDespl", 17.37, 0.0),
    KeySpec("pause", "Pausa", 18.46, 0.0),
]

KEY_SPECS += _row(
    1.28,
    [
        ("`", "º", 1),
        ("1", "1", 1),
        ("2", "2", 1),
        ("3", "3", 1),
        ("4", "4", 1),
        ("5", "5", 1),
        ("6", "6", 1),
        ("7", "7", 1),
        ("8", "8", 1),
        ("9", "9", 1),
        ("0", "0", 1),
        ("-", "-", 1),
        ("=", "+", 1),
        ("backspace", "Retroceso", 2),
    ],
)
KEY_SPECS += _row(
    2.37,
    [
        ("tab", "Tab", 1.5),
        ("q", "Q", 1),
        ("w", "W", 1),
        ("e", "E", 1),
        ("r", "R", 1),
        ("t", "T", 1),
        ("y", "Y", 1),
        ("u", "U", 1),
        ("i", "I", 1),
        ("o", "O", 1),
        ("p", "P", 1),
        ("[", "´", 1),
        ("]", "Ç", 1),
        ("enter", "Enter", 1.5),
    ],
)
KEY_SPECS += _row(
    3.46,
    [
        ("caps lock", "Bloq Mayús", 1.8),
        ("a", "A", 1),
        ("s", "S", 1),
        ("d", "D", 1),
        ("f", "F", 1),
        ("g", "G", 1),
        ("h", "H", 1),
        ("j", "J", 1),
        ("k", "K", 1),
        ("l", "L", 1),
        (";", "Ñ", 1),
        ("'", "¨", 1),
        ("\\", "\\", 1),
        ("enter", "Enter", 1.2),
    ],
)
KEY_SPECS += _row(
    4.55,
    [
        ("left shift", "Shift", 2.2),
        ("z", "Z", 1),
        ("x", "X", 1),
        ("c", "C", 1),
        ("v", "V", 1),
        ("b", "B", 1),
        ("n", "N", 1),
        ("m", "M", 1),
        (",", ",", 1),
        (".", ".", 1),
        ("/", "-", 1),
        ("right shift", "Shift", 2.4),
    ],
)
KEY_SPECS += _row(
    5.64,
    [
        ("left ctrl", "Ctrl", 1.4),
        ("left windows", "Win", 1.2),
        ("left alt", "Alt", 1.2),
        ("space", "Espacio", 6),
        ("right alt", "Alt Gr", 1.2),
        ("right windows", "Win", 1.2),
        ("menu", "Menú", 1.2),
        ("right ctrl", "Ctrl", 1.4),
    ],
)

# Navegación, cursores y teclado numérico.
KEY_SPECS += [
    KeySpec("insert", "Insert", 16.28, 1.28),
    KeySpec("home", "Inicio", 17.37, 1.28),
    KeySpec("page up", "Re Pág", 18.46, 1.28),
    KeySpec("delete", "Supr", 16.28, 2.37),
    KeySpec("end", "Fin", 17.37, 2.37),
    KeySpec("page down", "Av Pág", 18.46, 2.37),
    KeySpec("up", "▲", 17.37, 4.55),
    KeySpec("left", "◀", 16.28, 5.64),
    KeySpec("down", "▼", 17.37, 5.64),
    KeySpec("right", "▶", 18.46, 5.64),
    KeySpec("num lock", "Bloq\nNum", 20.05, 1.28),
    KeySpec("num divide", "/", 21.14, 1.28),
    KeySpec("num multiply", "×", 22.23, 1.28),
    KeySpec("num subtract", "−", 23.32, 1.28),
    KeySpec("num 7", "7", 20.05, 2.37),
    KeySpec("num 8", "8", 21.14, 2.37),
    KeySpec("num 9", "9", 22.23, 2.37),
    KeySpec("num add", "+", 23.32, 2.37, 1.0, 2.09),
    KeySpec("num 4", "4", 20.05, 3.46),
    KeySpec("num 5", "5", 21.14, 3.46),
    KeySpec("num 6", "6", 22.23, 3.46),
    KeySpec("num 1", "1", 20.05, 4.55),
    KeySpec("num 2", "2", 21.14, 4.55),
    KeySpec("num 3", "3", 22.23, 4.55),
    KeySpec("num enter", "Enter", 23.32, 4.55, 1.0, 2.09),
    KeySpec("num 0", "0", 20.05, 5.64, 2.09),
    KeySpec("num decimal", ",", 22.23, 5.64),
]

KEYBOARD_WIDTH_UNITS = 24.32
KEYBOARD_HEIGHT_UNITS = 6.64

_ALIASES = {
    "escape": "esc",
    "return": "enter",
    "intro": "enter",
    "control": "left ctrl",
    "ctrl": "left ctrl",
    "shift": "left shift",
    "alt": "left alt",
    "windows": "left windows",
    "windows key": "left windows",
    "win": "left windows",
    "cmd": "left windows",
    "spacebar": "space",
    "del": "delete",
    "pgup": "page up",
    "pgdn": "page down",
    "print_screen": "print screen",
    "printscreen": "print screen",
    "decimal": "num decimal",
    "divide": "num divide",
    "multiply": "num multiply",
    "subtract": "num subtract",
    "add": "num add",
}


def normalize_key_name(value: str) -> str:
    key = str(value).strip().lower().replace("_", " ")
    if key.startswith("key "):
        key = key[4:]
    if key.startswith("numpad "):
        key = "num " + key[7:]
    return _ALIASES.get(key, key)


def _mix(first: QColor, second: QColor, amount: float) -> QColor:
    amount = max(0.0, min(1.0, amount))
    return QColor(
        round(first.red() + (second.red() - first.red()) * amount),
        round(first.green() + (second.green() - first.green()) * amount),
        round(first.blue() + (second.blue() - first.blue()) * amount),
    )


class KeyboardWidget(QWidget):
    key_selected = Signal(str)
    key_context_requested = Signal(str)

    CATEGORY_COLORS = {
        "mapped": ("#162E37", "#22D3EE"),
        "macro": ("#261D45", "#8B5CF6"),
        "blocked": ("#371A26", "#FB7185"),
        "layer": ("#382811", "#F59E0B"),
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.selected = ""
        self.mapped: set[str] = set()
        self.categories: dict[str, str] = {}
        self.details: dict[str, str] = {}
        self.heatmap: dict[str, int] = {}
        self._pressed: set[str] = set()
        self._pulse_until: dict[str, float] = {}
        self._rects: list[tuple[QRectF, str]] = []
        self._hovered = ""
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(16)
        self._animation_timer.timeout.connect(self._animate)

    def set_mapped(self, keys: set[str]) -> None:
        self.mapped = {normalize_key_name(x) for x in keys if "+" not in x}
        self.update()

    def set_key_categories(self, values: dict[str, str]) -> None:
        self.categories = {
            normalize_key_name(key): str(category) for key, category in values.items() if "+" not in key
        }
        self.mapped = set(self.categories)
        self.update()

    def set_key_details(self, values: dict[str, str]) -> None:
        self.details = {normalize_key_name(key): str(text) for key, text in values.items()}
        self.update()

    def set_heatmap(self, values: dict[str, int]) -> None:
        self.heatmap = {
            normalize_key_name(key.split(":", 1)[-1]): value
            for key, value in values.items()
            if key.startswith("keyboard:")
        }
        self.update()

    def set_key_state(self, key: str, pressed: bool) -> None:
        normalized = normalize_key_name(key)
        if not normalized:
            return
        now = time.monotonic()
        self._pulse_until[normalized] = now + (0.30 if pressed else 0.22)
        if pressed:
            self._pressed.add(normalized)
        else:
            self._pressed.discard(normalized)
        if not self._animation_timer.isActive():
            self._animation_timer.start()
        self.update()

    def clear_pressed(self) -> None:
        self._pressed.clear()
        self._pulse_until.clear()
        self._animation_timer.stop()
        self.update()

    def select_key(self, key: str) -> None:
        self.selected = normalize_key_name(key)
        self.update()

    def paintEvent(self, event: object) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#0C0F18"))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 13, 13)

        margin = 13.0
        available_width = max(1.0, self.width() - margin * 2)
        available_height = max(1.0, self.height() - margin * 2)
        unit = min(
            available_width / KEYBOARD_WIDTH_UNITS,
            available_height / KEYBOARD_HEIGHT_UNITS,
        )
        draw_width = KEYBOARD_WIDTH_UNITS * unit
        draw_height = KEYBOARD_HEIGHT_UNITS * unit
        origin_x = (self.width() - draw_width) / 2
        origin_y = (self.height() - draw_height) / 2
        key_gap = max(2.0, unit * 0.085)
        max_heat = max(self.heatmap.values(), default=1)
        self._rects.clear()
        font = QFont("Segoe UI", max(6, min(11, int(unit * 0.25))))
        painter.setFont(font)

        now = time.monotonic()
        for spec in KEY_SPECS:
            rect = QRectF(
                origin_x + spec.x * unit,
                origin_y + spec.y * unit,
                max(4.0, spec.width * unit - key_gap),
                max(4.0, spec.height * unit - key_gap),
            )
            self._rects.append((rect, spec.key))
            normalized = normalize_key_name(spec.key)
            fill, border = self._key_colors(normalized, max_heat)
            pulse_left = self._pulse_until.get(normalized, 0.0) - now
            if normalized in self._pressed:
                fill = _mix(fill, QColor("#7B4DFF"), 0.86)
                border = QColor("#D8CCFF")
            elif pulse_left > 0:
                pulse = min(1.0, pulse_left / 0.30)
                fill = _mix(fill, QColor("#7B4DFF"), pulse * 0.72)
                border = _mix(border, QColor("#C4B5FD"), pulse)

            offset = 1.5 if normalized in self._pressed else 0.0
            painted = rect.translated(0, offset)
            painter.setPen(QPen(border, 1.5 if normalized in self._pressed else 1.0))
            painter.setBrush(fill)
            painter.drawRoundedRect(painted, max(4.0, unit * 0.13), max(4.0, unit * 0.13))

            painter.setPen(QColor("#F5F3FF" if normalized in self._pressed else "#DDE1F1"))
            painter.drawText(painted.adjusted(2, 1, -2, -1), Qt.AlignmentFlag.AlignCenter, spec.label)

            if normalized in self.categories and normalized not in self._pressed:
                dot_color = QColor(self.CATEGORY_COLORS.get(self.categories[normalized], ("", "#22D3EE"))[1])
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(dot_color)
                radius = max(2.0, min(3.5, unit * 0.07))
                painter.drawEllipse(
                    QRectF(
                        painted.right() - radius * 2.8, painted.top() + radius * 0.8, radius * 2, radius * 2
                    )
                )

    def _key_colors(self, key: str, max_heat: int) -> tuple[QColor, QColor]:
        if key == normalize_key_name(self.selected):
            return QColor("#32205D"), QColor("#A78BFA")
        if key in self.heatmap:
            ratio = min(1.0, self.heatmap[key] / max_heat)
            return (
                _mix(QColor("#1A1F2F"), QColor("#6D28D9"), ratio * 0.75),
                _mix(QColor("#343B54"), QColor("#A78BFA"), ratio),
            )
        category = self.categories.get(key, "mapped" if key in self.mapped else "")
        if category:
            colors = self.CATEGORY_COLORS.get(category, self.CATEGORY_COLORS["mapped"])
            return QColor(colors[0]), QColor(colors[1])
        return QColor("#181C2A"), QColor("#30364B")

    def _animate(self) -> None:
        now = time.monotonic()
        self._pulse_until = {key: end for key, end in self._pulse_until.items() if end > now}
        if not self._pulse_until:
            self._animation_timer.stop()
        self.update()

    def mousePressEvent(self, event: object) -> None:  # noqa: N802
        position = event.position()  # type: ignore[attr-defined]
        for rect, key in self._rects:
            if rect.contains(position):
                normalized = normalize_key_name(key)
                self.selected = normalized
                self.set_key_state(normalized, True)
                QTimer.singleShot(120, lambda value=normalized: self.set_key_state(value, False))
                self.key_selected.emit(normalized)
                if event.button() == Qt.MouseButton.RightButton:  # type: ignore[attr-defined]
                    self.key_context_requested.emit(normalized)
                return

    def mouseMoveEvent(self, event: object) -> None:  # noqa: N802
        position = event.position()  # type: ignore[attr-defined]
        hovered = ""
        for rect, key in self._rects:
            if rect.contains(position):
                hovered = normalize_key_name(key)
                break
        if hovered != self._hovered:
            self._hovered = hovered
            detail = self.details.get(hovered, "")
            self.setToolTip(detail or (f"{hovered.title()} · clic para seleccionar" if hovered else ""))
        super().mouseMoveEvent(event)  # type: ignore[arg-type]

    def leaveEvent(self, event: object) -> None:  # noqa: N802
        self._hovered = ""
        self.setToolTip("")
        super().leaveEvent(event)  # type: ignore[arg-type]


class MouseWidget(QWidget):
    button_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(250, 310)
        self.selected = ""
        self.mapped: set[str] = set()
        self._rects: list[tuple[QRectF, str]] = []

    def set_mapped(self, buttons: set[str]) -> None:
        self.mapped = buttons
        self.update()

    def paintEvent(self, event: object) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0D101A"))
        cx = self.width() / 2
        width = min(170.0, self.width() - 42.0)
        height = min(265.0, self.height() - 35.0)
        body = QRectF(cx - width / 2, 16, width, height)
        painter.setPen(QPen(QColor("#47506B"), 2))
        painter.setBrush(QColor("#181D2C"))
        painter.drawRoundedRect(body, 55, 55)

        left = QRectF(body.left() + 8, body.top() + 8, width / 2 - 12, 83)
        right = QRectF(cx + 4, body.top() + 8, width / 2 - 12, 83)
        middle = QRectF(cx - 13, body.top() + 26, 26, 52)
        side1 = QRectF(body.left() - 5, body.top() + 105, 24, 42)
        side2 = QRectF(body.left() - 5, body.top() + 153, 24, 42)
        self._rects = [
            (left, "left"),
            (right, "right"),
            (middle, "middle"),
            (side1, "x"),
            (side2, "x2"),
        ]
        for rect, name in self._rects:
            if name == self.selected:
                fill, border = QColor("#7C3AED"), QColor("#C4B5FD")
            elif name in self.mapped:
                fill, border = QColor("#17333C"), QColor("#22D3EE")
            else:
                fill, border = QColor("#22283B"), QColor("#414A66")
            painter.setPen(QPen(border, 1))
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QColor("#9299B2"))
        painter.drawText(body.adjusted(15, 205, -15, -15), Qt.AlignmentFlag.AlignCenter, "IBIKI")

    def mousePressEvent(self, event: object) -> None:  # noqa: N802
        position = event.position()  # type: ignore[attr-defined]
        for rect, button in self._rects:
            if rect.contains(position):
                self.selected = button
                self.update()
                self.button_selected.emit(button)
                return

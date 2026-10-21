from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...models import Macro, Mapping, Profile
from ...services.windows import foreground_window
from ..catalog import MOUSE_SOURCES, action_summary
from ..common import Card, PageHeader, clear_layout, section_title
from ..keyboard_widget import KeyboardWidget, normalize_key_name


MACRO_MODE_LABELS = {
    "once": "Una vez",
    "count": "Repeticiones",
    "toggle": "Alternar",
    "while_held": "Mantener",
    "infinite": "Infinita",
}


class MacroPanel(Card):
    run_requested = Signal(str)
    toggle_requested = Signal(str, bool)
    open_requested = Signal()

    def __init__(self, title: str, icon: str, accent: str, parent: QWidget | None = None):
        super().__init__(parent, padding=13)
        self.box.setSpacing(7)
        self.setProperty("dashboardPanel", True)
        self.accent = accent
        self._signature: tuple[object, ...] = ()

        header = QHBoxLayout()
        mark = QLabel(icon)
        mark.setObjectName("PanelIcon")
        mark.setStyleSheet(f"color:{accent};")
        header.addWidget(mark)
        header.addWidget(section_title(title))
        header.addStretch(1)
        self.count = QLabel("0")
        self.count.setObjectName("CountBadge")
        header.addWidget(self.count)
        self.box.addLayout(header)

        self.rows_host = QWidget()
        self.rows = QVBoxLayout(self.rows_host)
        self.rows.setContentsMargins(0, 0, 0, 0)
        self.rows.setSpacing(7)
        self.box.addWidget(self.rows_host, 1)

        self.open_button = QPushButton("Ver todas")
        self.open_button.setProperty("dashboardLink", True)
        self.open_button.clicked.connect(lambda: self.open_requested.emit())
        self.box.addWidget(self.open_button)

    def refresh(
        self,
        macros: Iterable[Macro],
        bindings: dict[str, str],
        running: set[str],
        *,
        paused: bool,
        locked: bool,
    ) -> None:
        values = list(macros)
        signature = (
            tuple(
                (item.id, item.name, item.enabled, item.mode, bindings.get(item.id, ""))
                for item in values[:4]
            ),
            tuple(sorted(running)),
            tuple((item.id, item.enabled) for item in values),
            paused,
            locked,
            len(values),
        )
        if signature == self._signature:
            return
        self._signature = signature
        self.count.setText(str(sum(1 for item in values if item.enabled)))
        self.count.setToolTip(f"{sum(1 for item in values if item.enabled)} activas de {len(values)}")
        clear_layout(self.rows)

        if not values:
            empty = QLabel("Todavía no hay macros\nen este perfil")
            empty.setObjectName("DashboardEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.rows.addWidget(empty, 1)
        else:
            for macro in values[:4]:
                row = QFrame()
                row.setObjectName("MacroQuickRow")
                row.setProperty("running", macro.id in running)
                layout = QHBoxLayout(row)
                layout.setContentsMargins(10, 7, 7, 7)
                layout.setSpacing(7)

                text = QVBoxLayout()
                text.setSpacing(1)
                name = QLabel(macro.name)
                name.setObjectName("MacroName")
                name.setToolTip(macro.name)
                name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                meta = QLabel(
                    f"{bindings.get(macro.id, 'Sin disparador')} · "
                    f"{MACRO_MODE_LABELS.get(macro.mode, macro.mode)}"
                )
                meta.setObjectName("MacroMeta")
                meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                text.addWidget(name)
                text.addWidget(meta)
                layout.addLayout(text, 1)

                toggle = QPushButton("ON" if macro.enabled else "OFF")
                toggle.setCheckable(True)
                toggle.setChecked(macro.enabled)
                toggle.setProperty("miniToggle", True)
                toggle.setProperty("active", macro.enabled)
                toggle.setToolTip("Activar o desactivar esta macro")
                toggle.setEnabled(not locked)
                toggle.clicked.connect(
                    lambda checked=False, macro_id=macro.id: self.toggle_requested.emit(
                        macro_id, bool(checked)
                    )
                )
                layout.addWidget(toggle)

                play = QPushButton("■" if macro.id in running else "▶")
                play.setProperty("iconButton", True)
                play.setProperty("running", macro.id in running)
                play.setToolTip("Detener macro" if macro.id in running else "Probar macro")
                play.setEnabled(macro.enabled and (not paused or macro.id in running))
                play.clicked.connect(
                    lambda checked=False, macro_id=macro.id: self.run_requested.emit(macro_id)
                )
                layout.addWidget(play)
                self.rows.addWidget(row)
            self.rows.addStretch(1)

        suffix = f" ({len(values)})" if values else ""
        self.open_button.setText(f"Ver todas{suffix}")


class DashboardPage(QWidget):
    navigate_requested = Signal(int)
    remap_key_requested = Signal(str)

    def __init__(self, controller: object, bus: object):
        super().__init__()
        self.controller = controller
        self.bus = bus
        self._last_process: str | None = None
        self._last_title: str | None = None
        self._shown_layer = ""
        self._engine_detail = "Motores detenidos"
        self._last_input_text = "Esperando una pulsación…"
        self._last_action_text = "El teclado mostrará aquí la acción resultante."

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 18)
        root.setSpacing(10)
        root.addWidget(
            PageHeader(
                "Dashboard",
                "Tus macros, el contexto activo y cada pulsación en un solo lugar.",
            )
        )

        top = QHBoxLayout()
        top.setSpacing(12)
        self.keyboard_macros = MacroPanel("Macros de teclado", "⌨", "#A78BFA")
        self.mouse_macros = MacroPanel("Macros del mouse", "●", "#22D3EE")
        self.keyboard_macros.run_requested.connect(self._run_macro)
        self.mouse_macros.run_requested.connect(self._run_macro)
        self.keyboard_macros.toggle_requested.connect(self._toggle_macro)
        self.mouse_macros.toggle_requested.connect(self._toggle_macro)
        self.keyboard_macros.open_requested.connect(lambda: self.navigate_requested.emit(4))
        self.mouse_macros.open_requested.connect(lambda: self.navigate_requested.emit(3))
        top.addWidget(self.keyboard_macros, 27)

        self.now_card = self._build_now_card()
        top.addWidget(self.now_card, 46)
        top.addWidget(self.mouse_macros, 27)
        root.addLayout(top, 5)

        keyboard_card = Card(padding=12)
        keyboard_card.box.setSpacing(7)
        keyboard_card.setProperty("keyboardCard", True)
        keyboard_header = QHBoxLayout()
        keyboard_header.addWidget(section_title("Teclado en vivo"))
        self.keyboard_hint = QLabel("Presiona una tecla o haz clic para inspeccionarla")
        self.keyboard_hint.setObjectName("Muted")
        self.keyboard_hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        keyboard_header.addWidget(self.keyboard_hint)
        keyboard_header.addStretch(1)
        keyboard_header.addWidget(self._legend("Remapeo", "#22D3EE"))
        keyboard_header.addWidget(self._legend("Macro", "#8B5CF6"))
        keyboard_header.addWidget(self._legend("Bloqueada", "#FB7185"))
        keyboard_card.box.addLayout(keyboard_header)
        self.keyboard = KeyboardWidget()
        self.keyboard.setMinimumHeight(220)
        self.keyboard.key_selected.connect(self._keyboard_selected)
        self.keyboard.key_context_requested.connect(self.remap_key_requested)
        keyboard_card.box.addWidget(self.keyboard, 1)
        root.addWidget(keyboard_card, 6)

        bus.engine_state_changed.connect(self._engine_state)
        bus.automation_pause_changed.connect(self._panic_state)
        bus.active_profile_changed.connect(lambda *_: self.refresh())
        bus.mappings_changed.connect(self.refresh)
        bus.macros_changed.connect(self.refresh)
        bus.graph_changed.connect(self.refresh)
        bus.profiles_changed.connect(self.refresh)
        bus.input_event.connect(self._input_event)
        bus.stats_changed.connect(self._stats_changed)

        self.runtime_timer = QTimer(self)
        self.runtime_timer.setInterval(500)
        self.runtime_timer.timeout.connect(self._refresh_runtime)
        self.runtime_timer.start()
        self.window_timer = QTimer(self)
        self.window_timer.setInterval(1200)
        self.window_timer.timeout.connect(self._refresh_foreground)
        self.window_timer.start()
        self.refresh()
        self._refresh_foreground()

    def _build_now_card(self) -> Card:
        card = Card(padding=14)
        card.setObjectName("NowCard")
        card.box.setSpacing(7)
        header = QHBoxLayout()
        eyebrow = QLabel("AHORA")
        eyebrow.setObjectName("Eyebrow")
        header.addWidget(eyebrow)
        header.addStretch(1)
        self.now_status = QLabel("● Motores detenidos")
        self.now_status.setObjectName("NowStatus")
        header.addWidget(self.now_status)
        card.box.addLayout(header)

        profile_row = QHBoxLayout()
        profile_caption = QLabel("Perfil")
        profile_caption.setObjectName("Muted")
        profile_row.addWidget(profile_caption)
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._profile_selected)
        profile_row.addWidget(self.profile_combo, 1)
        self.layer_badge = QLabel("Base")
        self.layer_badge.setObjectName("LayerBadge")
        profile_row.addWidget(self.layer_badge)
        card.box.addLayout(profile_row)

        app_surface = QFrame()
        app_surface.setObjectName("NowSurface")
        app_layout = QHBoxLayout(app_surface)
        app_layout.setContentsMargins(11, 9, 11, 9)
        app_mark = QLabel("▣")
        app_mark.setObjectName("AppMark")
        app_layout.addWidget(app_mark)
        app_text = QVBoxLayout()
        app_text.setSpacing(0)
        self.app_name = QLabel("Escritorio de Windows")
        self.app_name.setObjectName("NowApp")
        self.app_name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.app_title = QLabel("Detectando la ventana activa…")
        self.app_title.setObjectName("MacroMeta")
        self.app_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.app_title.setToolTip("Aplicación y título de la ventana actualmente enfocada")
        app_text.addWidget(self.app_name)
        app_text.addWidget(self.app_title)
        app_layout.addLayout(app_text, 1)
        card.box.addWidget(app_surface)

        stats = QHBoxLayout()
        stats.setSpacing(7)
        self.macro_stat = self._mini_stat("0", "macros")
        self.logic_stat = self._mini_stat("0", "flujos")
        self.cps_stat = self._mini_stat("0", "CPS")
        self.apm_stat = self._mini_stat("0", "APM")
        for item in (self.macro_stat, self.logic_stat, self.cps_stat, self.apm_stat):
            stats.addWidget(item)
        card.box.addLayout(stats)

        activity = QFrame()
        activity.setObjectName("ActivitySurface")
        activity_layout = QVBoxLayout(activity)
        activity_layout.setContentsMargins(11, 7, 11, 7)
        activity_layout.setSpacing(0)
        self.last_input = QLabel(self._last_input_text)
        self.last_input.setObjectName("ActivityInput")
        self.last_action = QLabel(self._last_action_text)
        self.last_action.setObjectName("MacroMeta")
        self.last_action.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.last_action.setToolTip(self._last_action_text)
        activity_layout.addWidget(self.last_input)
        activity_layout.addWidget(self.last_action)
        card.box.addWidget(activity)

        quick = QHBoxLayout()
        quick.setSpacing(7)
        for label, page in (
            ("＋ Remapear", 1),
            ("● Grabar", 3),
            ("◇ Lógica", 5),
        ):
            button = QPushButton(label)
            button.setProperty("quickAction", True)
            button.clicked.connect(lambda checked=False, index=page: self.navigate_requested.emit(index))
            quick.addWidget(button)
        card.box.addLayout(quick)
        return card

    @staticmethod
    def _legend(text: str, color: str) -> QLabel:
        label = QLabel(f"● {text}")
        label.setStyleSheet(f"color:{color};font-size:11px;")
        return label

    @staticmethod
    def _mini_stat(value: str, caption: str) -> QFrame:
        item = QFrame()
        item.setObjectName("MiniStat")
        layout = QVBoxLayout(item)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)
        number = QLabel(value)
        number.setObjectName("MiniStatValue")
        number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number.setProperty("valueLabel", True)
        text = QLabel(caption)
        text.setObjectName("MiniStatCaption")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(number)
        layout.addWidget(text)
        return item

    @staticmethod
    def _set_stat(widget: QFrame, value: object) -> None:
        layout = widget.layout()
        item = layout.itemAt(0) if layout else None
        label = item.widget() if item else None
        if isinstance(label, QLabel):
            label.setText(str(value))

    def refresh(self) -> None:
        profile = self.controller.active_profile()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for item in self.controller.state.profiles:
            self.profile_combo.addItem(item.name, item.id)
        self.profile_combo.setCurrentIndex(
            max(0, self.profile_combo.findData(self.controller.state.active_profile_id))
        )
        self.profile_combo.blockSignals(False)
        self.layer_badge.setText(f"Capa · {profile.active_layer}")

        categories: dict[str, str] = {}
        details: dict[str, str] = {}
        for mapping in profile.mappings:
            if not mapping.enabled or mapping.layer != profile.active_layer or "+" in mapping.source:
                continue
            category = (
                "blocked"
                if mapping.action.type == "noop"
                else "macro"
                if mapping.action.type == "macro"
                else "layer"
                if mapping.action.type in {"layer_momentary", "layer_toggle"}
                else "mapped"
            )
            categories[mapping.source] = category
            details[mapping.source] = self._mapping_description(mapping)
        self.keyboard.set_key_categories(categories)
        self.keyboard.set_key_details(details)
        self._shown_layer = profile.active_layer
        self._refresh_macro_panels(profile)
        self._engine_state(
            self.controller.engine_running,
            "Motores activos" if self.controller.engine_running else "Motores detenidos",
        )

    def _refresh_macro_panels(self, profile: Profile) -> None:
        running = self.controller.macro_engine.running_ids()
        keyboard_bindings = self._macro_bindings(profile.mappings)
        mouse_bindings = self._macro_bindings(profile.mouse_mappings, mouse=True)
        locked = bool(profile.settings.get("locked", False))
        paused = bool(self.controller.automation_paused)
        self.keyboard_macros.refresh(
            (macro for macro in profile.macros if macro.scope == "general"),
            keyboard_bindings,
            running,
            paused=paused,
            locked=locked,
        )
        self.mouse_macros.refresh(
            (macro for macro in profile.macros if macro.scope == "mouse"),
            mouse_bindings,
            running,
            paused=paused,
            locked=locked,
        )
        self._set_stat(self.macro_stat, sum(1 for macro in profile.macros if macro.enabled))
        self._set_stat(self.logic_stat, sum(1 for graph in profile.logic_graphs if graph.enabled))

    def _refresh_runtime(self) -> None:
        profile = self.controller.active_profile()
        current_layer = (
            self.controller.keyboard_engine.active_layer
            if self.controller.keyboard_engine.profile is not None
            else profile.active_layer
        )
        if current_layer != profile.active_layer:
            profile.active_layer = current_layer
        self.layer_badge.setText(f"Capa · {current_layer}")
        if current_layer != self._shown_layer:
            self.refresh()
        else:
            self._refresh_macro_panels(profile)
            self._engine_state(self.controller.engine_running, "")

    def _refresh_foreground(self) -> None:
        process, title = foreground_window()
        if (process, title) == (self._last_process, self._last_title):
            return
        self._last_process, self._last_title = process, title
        if process:
            shown = process.rsplit(".", 1)[0].replace("_", " ").title()
            self.app_name.setText(shown)
            self.app_title.setText(title or process)
            self.app_title.setToolTip(title or process)
        else:
            self.app_name.setText("Escritorio de Windows")
            self.app_title.setText("Sin una aplicación vinculada")
            self.app_title.setToolTip("")

    def _input_event(self, event: dict) -> None:
        device = str(event.get("device", "")).casefold()
        name = str(event.get("name", "?"))
        event_type = str(event.get("event_type", "")).casefold()
        pressed = event_type in {"down", "press", "double", "scroll"}
        released = event_type in {"up", "release"}
        if "key" in device or "tecl" in device:
            if pressed or released:
                self.keyboard.set_key_state(name, pressed)
        if not pressed:
            return

        profile = self.controller.active_profile()
        is_mouse = "mouse" in device or "rat" in device
        mappings = profile.mouse_mappings if is_mouse else profile.mappings
        source = name.casefold() if is_mouse else normalize_key_name(name)
        mapping = next(
            (
                item
                for item in mappings
                if item.enabled
                and item.layer == profile.active_layer
                and (
                    item.source.casefold() == source
                    if is_mouse
                    else normalize_key_name(item.source) == source
                )
            ),
            None,
        )
        prefix = "Mouse" if is_mouse else "Teclado"
        shown_source = self._mouse_source_label(name) if is_mouse else name.upper()
        self._last_input_text = f"{prefix} · {shown_source}"
        self._last_action_text = (
            self._mapping_description(mapping) if mapping else "Entrada normal · sin remapeo en esta capa"
        )
        self.last_input.setText(self._last_input_text)
        self.last_action.setText(self._last_action_text)
        self.last_action.setToolTip(self._last_action_text)
        self.keyboard_hint.setText(f"Última entrada: {shown_source}")

    def _stats_changed(self, stats: dict) -> None:
        self._set_stat(self.cps_stat, stats.get("cps", 0))
        self._set_stat(self.apm_stat, stats.get("apm", 0))

    def _keyboard_selected(self, key: str) -> None:
        detail = self.keyboard.details.get(normalize_key_name(key), "Sin remapeo en la capa actual")
        self.keyboard_hint.setText(f"{key.title()} · {detail} · clic derecho para editar")

    def _toggle_macro(self, macro_id: str, enabled: bool) -> None:
        profile = self.controller.active_profile()
        if profile.settings.get("locked", False):
            self.controller.notify("warning", "El perfil está bloqueado")
            return
        macro = next((item for item in profile.macros if item.id == macro_id), None)
        if not macro:
            return
        macro.enabled = enabled
        if not enabled:
            self.controller.macro_engine.stop(macro.id)
        self.controller.profile_changed(restart=False)
        self.controller.notify(
            "success" if enabled else "info",
            f"Macro {'activada' if enabled else 'desactivada'}: {macro.name}",
        )

    def _run_macro(self, macro_id: str) -> None:
        running = self.controller.macro_engine.running_ids()
        if macro_id in running:
            self.controller.macro_engine.stop(macro_id)
        else:
            self.controller.macro_engine.run(macro_id, "Dashboard")
        QTimer.singleShot(60, self.refresh)

    def _profile_selected(self) -> None:
        profile_id = self.profile_combo.currentData()
        if profile_id and profile_id != self.controller.state.active_profile_id:
            self.controller.activate_profile(str(profile_id), "Dashboard")

    def _engine_state(self, running: bool, detail: str) -> None:
        if detail:
            self._engine_detail = detail
        paused = bool(self.controller.automation_paused)
        if paused:
            text, color = "● PÁNICO ACTIVO", "#F59E0B"
        elif running:
            keyboard = self.controller.keyboard_engine.running
            mouse = self.controller.mouse_engine.running
            if keyboard and mouse:
                text, color = "● Ibiki activo", "#2DD4BF"
            elif keyboard or mouse:
                text, color = "● Activo parcial", "#F59E0B"
            else:
                text, color = "● Servicios activos", "#60A5FA"
        else:
            text, color = "● Motores detenidos", "#FB7185"
        self.now_status.setText(text)
        self.now_status.setStyleSheet(f"color:{color};")
        self.now_status.setToolTip(self._engine_detail)

    def _panic_state(self, paused: bool) -> None:
        self.keyboard.clear_pressed()
        self._engine_state(self.controller.engine_running, "Automatización pausada" if paused else "")
        self.refresh()

    def _mapping_description(self, mapping: Mapping) -> str:
        if mapping.action.type == "macro":
            macro = next(
                (
                    item
                    for item in self.controller.active_profile().macros
                    if item.id == str(mapping.action.value)
                ),
                None,
            )
            return f"Ejecutar macro · {macro.name if macro else 'macro no encontrada'}"
        return action_summary(mapping.action.type, mapping.action.value)

    @staticmethod
    def _macro_bindings(mappings: Iterable[Mapping], *, mouse: bool = False) -> dict[str, str]:
        labels = dict(MOUSE_SOURCES)
        result: dict[str, list[str]] = {}
        for mapping in mappings:
            if not mapping.enabled or mapping.action.type != "macro":
                continue
            shown = labels.get(mapping.source, mapping.source) if mouse else mapping.source.upper()
            result.setdefault(str(mapping.action.value), []).append(shown)
        return {macro_id: ", ".join(list(dict.fromkeys(values))[:2]) for macro_id, values in result.items()}

    @staticmethod
    def _mouse_source_label(value: str) -> str:
        return dict(MOUSE_SOURCES).get(value, value.replace("_", " ").title())

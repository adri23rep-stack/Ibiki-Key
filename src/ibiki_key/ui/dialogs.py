from __future__ import annotations

import json
from typing import Any

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..models import Action, LogicNode, Macro, MacroStep, Mapping, Profile
from .catalog import ACTION_LABELS, MOUSE_SOURCES, NODE_CATALOG, TRIGGER_LABELS


class ActionEditor(QWidget):
    def __init__(self, controller: object, action: Action | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.controller = controller
        self.kind = QComboBox()
        self._action_choices = list(ACTION_LABELS.items()) + [
            (value, f"Plugin · {label}") for value, label in controller.plugin_manager.action_labels.items()
        ]
        for value, label in self._action_choices:
            self.kind.addItem(label, value)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar una función…")
        self.value = QComboBox()
        self.value.setEditable(True)
        self.value.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.hint = QLabel()
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        browse = QPushButton("Buscar…")
        browse.clicked.connect(self._browse)
        target_row = QHBoxLayout()
        target_row.setContentsMargins(0, 0, 0, 0)
        target_row.addWidget(self.value, 1)
        target_row.addWidget(browse)
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addRow("Buscar", self.search)
        layout.addRow("Tipo de acción", self.kind)
        layout.addRow("Valor", target_row)
        layout.addRow("", self.hint)
        self.kind.currentIndexChanged.connect(self._populate)
        self.search.textChanged.connect(self._filter_actions)
        if action:
            index = self.kind.findData(action.type)
            self.kind.setCurrentIndex(max(0, index))
            self._populate()
            match = self.value.findData(action.value)
            if match >= 0:
                self.value.setCurrentIndex(match)
            else:
                if action.type == "turbo":
                    self.value.setEditText(f"{action.value},{action.options.get('rate_hz', 10)}")
                elif action.type == "set_variable":
                    self.value.setEditText(
                        f"{action.options.get('name', action.value)},"
                        f"{json.dumps(action.options.get('value'), ensure_ascii=False)}"
                    )
                else:
                    self.value.setEditText(self._serialize_value(action.value))
        else:
            self._populate()

    def _populate(self) -> None:
        kind = str(self.kind.currentData())
        current = self.value.currentText()
        self.value.clear()
        hints = {
            "key": "Ejemplo: a, f13, volume up",
            "hotkey": "Usa + entre teclas. Ejemplo: ctrl+shift+s",
            "text": "El texto se escribirá en la ventana activa.",
            "paste_text": "Copia el texto al portapapeles y ejecuta Ctrl+V.",
            "scroll": "Vertical: 3 o -3. Vertical y horizontal: 3,2.",
            "brightness": "Valor de 0 a 100. Depende del monitor.",
            "wait": "Tiempo en milisegundos.",
            "command": "Por seguridad, primero habilita CMD/PowerShell en el perfil.",
            "powershell": "Por seguridad, primero habilita CMD/PowerShell en el perfil.",
            "set_variable": "Escribe nombre,valor JSON. Ejemplo: modo_juego,true",
            "toggle_variable": "Escribe el nombre de una variable booleana.",
            "turbo": "Escribe tecla,veces_por_segundo. Ejemplo: space,12. Usa el disparador 'Mientras se mantiene'.",
            "mod_tap": "Escribe toque,mantener,milisegundos. Ejemplo: escape,left ctrl,180. Usa 'Mientras se mantiene'.",
            "noop": "La tecla queda bloqueada si activas 'Bloquear tecla original'.",
        }
        self.hint.setText(hints.get(kind, ""))
        profile = self.controller.active_profile()
        if kind == "macro":
            for item in profile.macros:
                self.value.addItem(item.name, item.id)
        elif kind == "profile":
            for item in self.controller.state.profiles:
                self.value.addItem(item.name, item.id)
        elif kind in {"layer_toggle", "layer_momentary"}:
            for item in profile.layers:
                self.value.addItem(item, item)
        elif kind == "logic_graph":
            for item in profile.logic_graphs:
                self.value.addItem(item.name, item.id)
        elif kind in {"mouse_button", "double_click"}:
            for value, label in MOUSE_SOURCES[:5]:
                self.value.addItem(label, value)
        elif kind == "media":
            for value, label in [
                ("play_pause", "Reproducir / pausar"),
                ("next", "Siguiente"),
                ("previous", "Anterior"),
                ("stop", "Detener"),
                ("mute", "Silenciar"),
            ]:
                self.value.addItem(label, value)
        elif kind == "volume":
            for value, label in [("up", "Subir"), ("down", "Bajar"), ("mute", "Silenciar")]:
                self.value.addItem(label, value)
        elif kind in {"noop", "screenshot"}:
            self.value.addItem("—", "")
            self.value.setEnabled(False)
            return
        self.value.setEnabled(True)
        if self.value.count() == 0:
            self.value.setEditText(current)

    def _filter_actions(self, query: str) -> None:
        current = self.kind.currentData()
        query = query.strip().lower()
        self.kind.blockSignals(True)
        self.kind.clear()
        for value, label in self._action_choices:
            if not query or query in label.lower() or query in value.lower():
                self.kind.addItem(label, value)
        index = self.kind.findData(current)
        self.kind.setCurrentIndex(index if index >= 0 else 0)
        self.kind.blockSignals(False)
        self._populate()

    def action(self) -> Action:
        kind = str(self.kind.currentData())
        data = self.value.currentData()
        text = self.value.currentText().strip()
        value: Any = data if data not in {None, ""} and self.value.findText(text) >= 0 else text
        if kind in {"noop", "screenshot"}:
            value = ""
        elif kind == "scroll":
            try:
                if "," in text:
                    vertical, horizontal = [int(x.strip()) for x in text.split(",", 1)]
                    value = {"vertical": vertical, "horizontal": horizontal}
                else:
                    value = int(text)
            except ValueError as exc:
                raise ValueError("Usa un número o vertical,horizontal; ejemplo: -3,2") from exc
        elif kind in {"wait", "brightness"}:
            try:
                value = int(text)
            except ValueError as exc:
                raise ValueError("Esta acción necesita un número") from exc
        elif kind == "mouse_move":
            try:
                parts = [int(x.strip()) for x in text.split(",")]
                value = {"x": parts[0], "y": parts[1], "absolute": False}
            except Exception as exc:
                raise ValueError("Usa X,Y; por ejemplo: 20,-10") from exc
        elif kind == "turbo":
            try:
                key, rate = [x.strip() for x in text.split(",", 1)]
                value = key
                return Action(kind, value, {"rate_hz": max(1.0, min(30.0, float(rate)))})
            except Exception as exc:
                raise ValueError("Usa tecla,velocidad; por ejemplo: space,12") from exc
        elif kind == "mod_tap":
            try:
                tap, hold, threshold = [x.strip() for x in text.split(",", 2)]
                value = {"tap": tap, "hold": hold, "threshold_ms": max(80, min(1000, int(threshold)))}
            except Exception as exc:
                raise ValueError("Usa toque,mantener,milisegundos; ejemplo: escape,left ctrl,180") from exc
        elif kind == "set_variable":
            try:
                name, raw_value = [x.strip() for x in text.split(",", 1)]
                value = name
                return Action(kind, value, {"name": name, "value": json.loads(raw_value)})
            except Exception as exc:
                raise ValueError("Usa nombre,valor JSON; ejemplo: modo_juego,true") from exc
        return Action(kind, value)

    def _browse(self) -> None:
        kind = str(self.kind.currentData())
        if kind == "open_program":
            path, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar programa", "", "Programas (*.exe);;Todos (*.*)"
            )
        elif kind == "open_folder":
            path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        else:
            return
        if path:
            self.value.setEditText(path)

    @staticmethod
    def _serialize_value(value: Any) -> str:
        if isinstance(value, dict):
            if {"tap", "hold", "threshold_ms"}.issubset(value):
                return f"{value['tap']},{value['hold']},{value['threshold_ms']}"
            if {"vertical", "horizontal"}.issubset(value):
                return f"{value['vertical']},{value['horizontal']}"
            if {"x", "y"}.issubset(value):
                return f"{value['x']},{value['y']}"
            return json.dumps(value, ensure_ascii=False)
        return str(value if value is not None else "")


class MappingDialog(QDialog):
    def __init__(
        self,
        controller: object,
        mapping: Mapping | None = None,
        *,
        source: str = "",
        mouse_mode: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.controller = controller
        self.original = mapping
        self.mouse_mode = mouse_mode
        self.setWindowTitle("Asignación de mouse" if mouse_mode else "Asignación de teclado")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.source = QComboBox()
        self.source.setEditable(True)
        if mouse_mode:
            for value, label in MOUSE_SOURCES:
                self.source.addItem(label, value)
        else:
            for value in ["f13", "f14", "f15", "ctrl+alt+k", "caps lock", "menu"]:
                self.source.addItem(value, value)
        self.trigger = QComboBox()
        for value, label in TRIGGER_LABELS.items():
            self.trigger.addItem(label, value)
        self.layer = QComboBox()
        self.layer.addItems(controller.active_profile().layers)
        self.enabled = QCheckBox("Activa")
        self.enabled.setChecked(True)
        self.suppress = QCheckBox("Bloquear la tecla o botón original")
        self.suppress.setChecked(not mouse_mode)
        if mouse_mode:
            self.suppress.setEnabled(False)
            self.suppress.setToolTip(
                "El bloqueo selectivo de botones estará disponible con el controlador avanzado."
            )
        self.debounce = QSpinBox()
        self.debounce.setRange(0, 5000)
        self.debounce.setSuffix(" ms")
        self.double_tap = QSpinBox()
        self.double_tap.setRange(100, 1000)
        self.double_tap.setValue(300)
        self.double_tap.setSuffix(" ms")
        self.note = QLineEdit()
        form.addRow("Origen", self.source)
        form.addRow("Disparador", self.trigger)
        form.addRow("Capa", self.layer)
        form.addRow("Estado", self.enabled)
        form.addRow("Supresión", self.suppress)
        form.addRow("Anti rebote", self.debounce)
        form.addRow("Ventana de doble toque", self.double_tap)
        form.addRow("Nota", self.note)
        layout.addLayout(form)
        layout.addWidget(QLabel("Acción"))
        self.action_editor = ActionEditor(controller, mapping.action if mapping else None)
        self.action_editor.kind.currentIndexChanged.connect(self._action_kind_changed)
        layout.addWidget(self.action_editor)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if mapping:
            self._set_combo(self.source, mapping.source)
            self._set_combo(self.trigger, mapping.trigger)
            self.layer.setCurrentText(mapping.layer)
            self.enabled.setChecked(mapping.enabled)
            self.suppress.setChecked(mapping.suppress)
            self.debounce.setValue(mapping.debounce_ms)
            self.double_tap.setValue(int(mapping.action.options.get("tap_ms", 300)))
            self.note.setText(mapping.note)
        elif source:
            self._set_combo(self.source, source)

    def _action_kind_changed(self, *_: object) -> None:
        if self.action_editor.kind.currentData() in {"turbo", "mod_tap", "layer_momentary"}:
            self.trigger.setCurrentIndex(max(0, self.trigger.findData("hold")))

    def result_mapping(self) -> Mapping:
        data = self.source.currentData()
        shown = self.source.currentText().strip()
        source = str(data if data and self.source.findText(shown) >= 0 else shown).lower()
        action = self.action_editor.action()
        if self.trigger.currentData() == "double_tap":
            action.options["tap_ms"] = self.double_tap.value()
        return Mapping(
            id=self.original.id if self.original else Mapping().id,
            source=source,
            trigger=str(self.trigger.currentData()),
            action=action,
            layer=self.layer.currentText(),
            enabled=self.enabled.isChecked(),
            suppress=self.suppress.isChecked(),
            debounce_ms=self.debounce.value(),
            note=self.note.text().strip(),
        )

    def _accept(self) -> None:
        try:
            candidate = self.result_mapping()
            if self.mouse_mode and candidate.trigger == "hold" and (
                candidate.source.startswith("wheel_") or candidate.source.startswith("gesture:")
            ):
                raise ValueError(
                    "La rueda y los gestos no tienen un estado mantenido; usa 'Al presionar'."
                )
            candidate.validate()
        except Exception as exc:
            QMessageBox.warning(self, "Asignación incompleta", str(exc))
            return
        self.accept()

    @staticmethod
    def _set_combo(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.setEditText(value)


class MacroPropertiesDialog(QDialog):
    def __init__(self, macro: Macro | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.macro = macro
        self.setWindowTitle("Propiedades de macro")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(macro.name if macro else "Nueva macro")
        self.mode = QComboBox()
        for value, label in [
            ("once", "Ejecutar una vez"),
            ("count", "Número de repeticiones"),
            ("toggle", "Alternar hasta detener"),
            ("while_held", "Mientras se mantiene la tecla"),
            ("infinite", "Secuencia infinita"),
        ]:
            self.mode.addItem(label, value)
        self.repeats = QSpinBox()
        self.repeats.setRange(1, 1_000_000)
        self.interval = QSpinBox()
        self.interval.setRange(0, 3_600_000)
        self.interval.setSuffix(" ms")
        self.enabled = QCheckBox("Activa")
        self.enabled.setChecked(True)
        self.stop_error = QCheckBox("Detener si una acción falla")
        self.stop_error.setChecked(True)
        if macro:
            self.mode.setCurrentIndex(max(0, self.mode.findData(macro.mode)))
            self.repeats.setValue(macro.repeat_count)
            self.interval.setValue(macro.interval_ms)
            self.enabled.setChecked(macro.enabled)
            self.stop_error.setChecked(macro.stop_on_error)
        form.addRow("Nombre", self.name)
        form.addRow("Modo", self.mode)
        form.addRow("Repeticiones", self.repeats)
        form.addRow("Pausa entre ciclos", self.interval)
        form.addRow("Estado", self.enabled)
        form.addRow("Errores", self.stop_error)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply(self, macro: Macro) -> None:
        macro.name = self.name.text().strip() or "Macro sin nombre"
        macro.mode = str(self.mode.currentData())
        macro.repeat_count = self.repeats.value()
        macro.interval_ms = self.interval.value()
        macro.enabled = self.enabled.isChecked()
        macro.stop_on_error = self.stop_error.isChecked()


class MacroStepDialog(QDialog):
    def __init__(self, controller: object, step: MacroStep | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.original = step
        self.setWindowTitle("Paso de macro")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        self.action_editor = ActionEditor(controller, step.action if step else None)
        layout.addWidget(self.action_editor)
        form = QFormLayout()
        self.delay = QSpinBox()
        self.delay.setRange(0, 3_600_000)
        self.delay.setSuffix(" ms")
        self.random = QSpinBox()
        self.random.setRange(0, 60_000)
        self.random.setSuffix(" ms")
        self.enabled = QCheckBox("Activo")
        self.enabled.setChecked(True)
        if step:
            self.delay.setValue(step.delay_after_ms)
            self.random.setValue(step.random_delay_ms)
            self.enabled.setChecked(step.enabled)
        form.addRow("Retraso después", self.delay)
        form.addRow("Retraso aleatorio extra", self.random)
        form.addRow("Estado", self.enabled)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_step(self) -> MacroStep:
        return MacroStep(
            id=self.original.id if self.original else MacroStep().id,
            action=self.action_editor.action(),
            delay_after_ms=self.delay.value(),
            random_delay_ms=self.random.value(),
            enabled=self.enabled.isChecked(),
        )

    def _accept(self) -> None:
        try:
            self.result_step().validate()
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Paso incompleto", str(exc))


class ProfileDialog(QDialog):
    def __init__(self, profile: Profile | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle("Editar perfil" if profile else "Crear perfil")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(profile.name if profile else "Perfil nuevo")
        color_row = QHBoxLayout()
        self.color = QLineEdit(profile.color if profile else "#8B5CF6")
        color_button = QPushButton("Elegir…")
        color_button.clicked.connect(self._choose_color)
        color_row.addWidget(self.color, 1)
        color_row.addWidget(color_button)
        self.apps = QTextEdit("\n".join(profile.app_rules) if profile else "")
        self.apps.setPlaceholderText("valorant.exe\nchrome.exe")
        self.apps.setMaximumHeight(92)
        self.windows = QTextEdit("\n".join(profile.window_rules) if profile else "")
        self.windows.setPlaceholderText("Texto que debe contener el título de la ventana")
        self.windows.setMaximumHeight(76)
        self.auto_switch = QCheckBox("Cambiar a este perfil automáticamente")
        self.auto_switch.setChecked(bool(profile.settings.get("auto_switch", True)) if profile else True)
        self.macros = QCheckBox("Permitir macros")
        self.macros.setChecked(bool(profile.settings.get("macros_enabled", True)) if profile else True)
        self.scripts = QCheckBox("Permitir CMD y PowerShell (pueden modificar el equipo)")
        self.scripts.setChecked(bool(profile.settings.get("scripts_allowed", False)) if profile else False)
        self.scripts.setToolTip(
            "Déjalo desactivado salvo que confíes en todos los comandos y scripts de este perfil."
        )
        self.external_actions = QCheckBox("Permitir abrir programas, carpetas y enlaces")
        self.external_actions.setChecked(
            bool(profile.settings.get("trusted_actions", True)) if profile else True
        )
        self.locked = QCheckBox("Bloquear edición del perfil")
        self.locked.setChecked(bool(profile.settings.get("locked", False)) if profile else False)
        self.low_latency = QCheckBox("Reducir filtros para menor latencia")
        self.low_latency.setChecked(bool(profile.settings.get("low_latency", False)) if profile else False)
        self.whitelist_enabled = QCheckBox("Solo funcionar en programas permitidos")
        self.whitelist_enabled.setChecked(
            bool(profile.settings.get("whitelist_enabled", False)) if profile else False
        )
        self.whitelist_apps = QTextEdit(
            "\n".join(profile.settings.get("whitelist_programs", [])) if profile else ""
        )
        self.whitelist_apps.setPlaceholderText("juego.exe\neditor.exe")
        self.whitelist_apps.setMaximumHeight(72)
        form.addRow("Nombre", self.name)
        form.addRow("Color", color_row)
        form.addRow("Programas vinculados", self.apps)
        form.addRow("Títulos de ventana", self.windows)
        form.addRow("Cambio automático", self.auto_switch)
        form.addRow("Macros", self.macros)
        form.addRow("Scripts", self.scripts)
        form.addRow("Acciones externas", self.external_actions)
        form.addRow("Gaming", self.low_latency)
        form.addRow("Lista blanca", self.whitelist_enabled)
        form.addRow("Programas permitidos", self.whitelist_apps)
        form.addRow("Seguridad", self.locked)
        layout.addLayout(form)
        note = QLabel(
            "Un perfil bloqueado puede usarse y exportarse, pero primero hay que desbloquearlo para editarlo. "
            "CMD y PowerShell permanecen desactivados hasta que los autorices aquí o al probar una macro."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply(self, profile: Profile) -> None:
        profile.name = self.name.text().strip() or "Perfil sin nombre"
        profile.color = self.color.text().strip()
        profile.app_rules = self._lines(self.apps.toPlainText())
        profile.window_rules = self._lines(self.windows.toPlainText())
        profile.settings["auto_switch"] = self.auto_switch.isChecked()
        profile.settings["macros_enabled"] = self.macros.isChecked()
        profile.settings["scripts_allowed"] = self.scripts.isChecked()
        profile.settings["trusted_actions"] = self.external_actions.isChecked()
        profile.settings["low_latency"] = self.low_latency.isChecked()
        profile.settings["whitelist_enabled"] = self.whitelist_enabled.isChecked()
        profile.settings["whitelist_programs"] = self._lines(self.whitelist_apps.toPlainText())
        profile.settings["locked"] = self.locked.isChecked()
        profile.validate()

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.color.text()), self, "Color del perfil")
        if color.isValid():
            self.color.setText(color.name())

    @staticmethod
    def _lines(text: str) -> list[str]:
        return [line.strip() for line in text.replace(",", "\n").splitlines() if line.strip()]


class LogicNodeDialog(QDialog):
    def __init__(
        self,
        controller: object,
        node: LogicNode | None = None,
        kind: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.controller = controller
        self.original = node
        self.kind = node.kind if node else str(kind or "action")
        self.config = dict(node.config) if node else dict(NODE_CATALOG[self.kind][2])
        self.setWindowTitle(NODE_CATALOG.get(self.kind, ("Nodo", "", {}))[0])
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        self.form = QFormLayout()
        self.title = QLineEdit(node.title if node else NODE_CATALOG[self.kind][0])
        self.form.addRow("Nombre visible", self.title)
        self.fields: dict[str, QWidget] = {}
        self.action_editor: ActionEditor | None = None
        self._build_fields()
        layout.addLayout(self.form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_fields(self) -> None:
        kind = self.kind
        if kind == "action":
            self.action_editor = ActionEditor(self.controller, Action.from_dict(self.config.get("action")))
            self.form.addRow("Acción", self.action_editor)
            return
        specs: list[tuple[str, str, str]] = []
        if kind == "trigger_key":
            specs = [("key", "Tecla", "text")]
        elif kind == "trigger_mouse":
            specs = [("button", "Botón", "text")]
        elif kind in {"condition_process", "condition_active_process"}:
            specs = [("process", "Proceso", "text")]
        elif kind == "condition_window":
            specs = [("contains", "El título contiene", "text")]
        elif kind == "condition_time":
            specs = [("start", "Desde (HH:MM)", "text"), ("end", "Hasta (HH:MM)", "text")]
        elif kind == "condition_idle":
            specs = [("seconds", "Segundos inactivo", "number")]
        elif kind == "condition_variable":
            specs = [("name", "Variable", "text"), ("equals", "Es igual a (JSON)", "json")]
        elif kind == "condition_key":
            specs = [("key", "Tecla", "text")]
        elif kind == "timer":
            specs = [("name", "Temporizador", "text"), ("seconds", "Cada segundos", "number")]
        elif kind == "delay":
            specs = [("milliseconds", "Milisegundos", "integer")]
        elif kind == "wait_event":
            specs = [
                ("event", "Evento (process/window/key/variable/idle)", "text"),
                ("value", "Valor esperado", "text"),
                ("timeout", "Tiempo máximo en segundos", "number"),
            ]
        elif kind == "set_variable":
            specs = [("name", "Variable", "text"), ("value", "Valor (JSON)", "json")]
        for key, label, data_type in specs:
            edit = QLineEdit(self._format(self.config.get(key, "")))
            edit.setProperty("data_type", data_type)
            self.fields[key] = edit
            self.form.addRow(label, edit)

    def result_node(self) -> LogicNode:
        config = dict(self.config)
        if self.action_editor:
            config["action"] = {
                "type": self.action_editor.action().type,
                "value": self.action_editor.action().value,
                "options": self.action_editor.action().options,
            }
        for key, widget in self.fields.items():
            text = widget.text().strip()  # type: ignore[attr-defined]
            data_type = widget.property("data_type")
            if data_type == "integer":
                value: Any = int(text)
            elif data_type == "number":
                value = float(text)
            elif data_type == "json":
                value = json.loads(text)
            else:
                value = text
            config[key] = value
        return LogicNode(
            id=self.original.id if self.original else LogicNode().id,
            kind=self.kind,
            title=self.title.text().strip() or NODE_CATALOG[self.kind][0],
            x=self.original.x if self.original else 0,
            y=self.original.y if self.original else 0,
            config=config,
        )

    def _accept(self) -> None:
        try:
            self.result_node()
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Nodo incompleto", str(exc))

    @staticmethod
    def _format(value: Any) -> str:
        if isinstance(value, (dict, list, bool)) or value is None:
            return json.dumps(value, ensure_ascii=False)
        return str(value)

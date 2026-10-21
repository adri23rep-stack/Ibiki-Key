from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..common import Card, MetricCard, PageHeader, section_title
from ..keyboard_widget import KeyboardWidget


class MonitorPage(QWidget):
    MAX_VISIBLE_ROWS = 250

    def __init__(self, controller: object, bus: object):
        super().__init__()
        self.controller = controller
        self.bus = bus
        self.events: list[dict] = list(controller.monitor.history())
        self.paused = False

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 26)
        root.setSpacing(14)
        root.addWidget(
            PageHeader(
                "Monitor",
                "Analiza pulsaciones, intervalos y uso; filtra o exporta el historial.",
            )
        )
        grid = QGridLayout()
        grid.setSpacing(12)
        self.cps = MetricCard("CPS actual", "0", "#22D3EE")
        self.apm = MetricCard("APM", "0", "#A78BFA")
        self.peak = MetricCard("Pico CPS", "0", "#FB7185")
        self.total = MetricCard("Pulsaciones", "0", "#2DD4BF")
        self.interval = MetricCard("Intervalo medio", "—", "#60A5FA")
        self.session = MetricCard("Sesión", "0:00", "#F59E0B")
        metrics = [self.cps, self.apm, self.peak, self.total, self.interval, self.session]
        for index, metric in enumerate(metrics):
            grid.addWidget(metric, index // 3, index % 3)
        root.addLayout(grid)

        lower = QSplitter()
        heat = Card()
        heat.box.addWidget(section_title("Mapa de uso"))
        self.device_summary = QLabel("Teclado: 0 · Mouse: 0")
        self.device_summary.setObjectName("Muted")
        heat.box.addWidget(self.device_summary)
        self.keyboard = KeyboardWidget()
        heat.box.addWidget(self.keyboard, 1)
        lower.addWidget(heat)

        history = Card()
        top = QHBoxLayout()
        top.addWidget(section_title("Historial"))
        top.addStretch(1)
        self.pause_button = QPushButton("Pausar vista", clicked=self.toggle_pause)
        top.addWidget(self.pause_button)
        top.addWidget(QPushButton("Copiar", clicked=self.copy_rows))
        top.addWidget(QPushButton("Exportar CSV", clicked=self.export_csv))
        top.addWidget(QPushButton("Reiniciar", clicked=self.reset))
        history.box.addLayout(top)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar tecla o botón…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._rebuild_table)
        filters.addWidget(self.search, 2)
        self.device_filter = QComboBox()
        self.device_filter.addItem("Todos los dispositivos", "")
        self.device_filter.addItem("Teclado", "keyboard")
        self.device_filter.addItem("Mouse", "mouse")
        self.device_filter.currentIndexChanged.connect(self._rebuild_table)
        filters.addWidget(self.device_filter)
        self.event_filter = QComboBox()
        self.event_filter.addItem("Todos los eventos", "")
        self.event_filter.addItem("Pulsaciones", "press")
        self.event_filter.addItem("Liberaciones", "release")
        self.event_filter.currentIndexChanged.connect(self._rebuild_table)
        filters.addWidget(self.event_filter)
        self.filter_status = QLabel("")
        self.filter_status.setObjectName("Muted")
        filters.addWidget(self.filter_status)
        history.box.addLayout(filters)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Hora", "Dispositivo", "Entrada", "Evento", "Intervalo"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        history.box.addWidget(self.table, 1)
        lower.addWidget(history)
        lower.setStretchFactor(0, 3)
        lower.setStretchFactor(1, 5)
        root.addWidget(lower, 1)

        bus.input_event.connect(self.add_event)
        bus.stats_changed.connect(self.update_stats)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(lambda: self.update_stats(self.controller.monitor.snapshot()))
        self.refresh_timer.start()
        self._rebuild_table()
        self.update_stats(controller.monitor.snapshot())

    def add_event(self, event: dict) -> None:
        self.events.append(dict(event))
        del self.events[:-1000]
        if not self.paused and self._matches(event):
            self._insert_event(0, event)
            while self.table.rowCount() > self.MAX_VISIBLE_ROWS:
                self.table.removeRow(self.table.rowCount() - 1)
        self._update_filter_status()

    def update_stats(self, stats: dict) -> None:
        self.cps.value.setText(str(stats.get("cps", 0)))
        self.apm.value.setText(str(stats.get("apm", 0)))
        self.peak.value.setText(str(stats.get("peak_cps", 0)))
        self.total.value.setText(str(stats.get("total", 0)))
        average = stats.get("average_interval_ms")
        self.interval.value.setText(f"{average} ms" if average is not None else "—")
        minimum = stats.get("min_interval_ms")
        maximum = stats.get("max_interval_ms")
        self.interval.setToolTip(
            f"Mínimo: {minimum if minimum is not None else '—'} ms\n"
            f"Máximo: {maximum if maximum is not None else '—'} ms"
        )
        seconds = int(float(stats.get("session_seconds", 0)))
        self.session.value.setText(f"{seconds // 60}:{seconds % 60:02d}")
        counts = {str(key).casefold(): value for key, value in stats.get("device_counts", {}).items()}
        keyboard_count = sum(value for key, value in counts.items() if "key" in key or "tecl" in key)
        mouse_count = sum(value for key, value in counts.items() if "mouse" in key or "rat" in key)
        self.device_summary.setText(f"Teclado: {keyboard_count} · Mouse: {mouse_count}")
        self.keyboard.set_heatmap(stats.get("heatmap", {}))

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_button.setText("Reanudar vista" if self.paused else "Pausar vista")
        self.filter_status.setText("Vista pausada" if self.paused else "")
        if not self.paused:
            self._rebuild_table()

    def copy_rows(self) -> None:
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        if not rows:
            rows = list(range(self.table.rowCount()))
        if not rows:
            return
        lines = ["Hora\tDispositivo\tEntrada\tEvento\tIntervalo"]
        for row in rows:
            lines.append(
                "\t".join(
                    self.table.item(row, column).text() if self.table.item(row, column) else ""
                    for column in range(self.table.columnCount())
                )
            )
        QApplication.clipboard().setText("\n".join(lines))
        self.controller.notify("success", f"{len(rows)} fila(s) copiadas")

    def export_csv(self) -> None:
        events = self._filtered_events()
        if not events:
            QMessageBox.information(self, "Sin datos", "No hay eventos que coincidan con los filtros.")
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar historial",
            str(self.controller.storage.exports_dir / f"ibiki-monitor-{stamp}.csv"),
            "Archivo CSV (*.csv)",
        )
        if not destination:
            return
        path = Path(destination)
        if path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")
        try:
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerow(["fecha_hora", "dispositivo", "entrada", "evento", "intervalo_ms"])
                for event in events:
                    writer.writerow(
                        [
                            self._format_time(event, include_date=True),
                            event.get("device", ""),
                            event.get("name", ""),
                            event.get("event_type", ""),
                            event.get("delta_ms", ""),
                        ]
                    )
        except OSError as exc:
            QMessageBox.critical(self, "No se pudo exportar", str(exc))
            return
        self.controller.notify("success", f"Historial exportado: {path}")

    def reset(self) -> None:
        answer = QMessageBox.question(
            self,
            "Reiniciar monitor",
            "¿Borrar el historial y todas las estadísticas de esta sesión?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.controller.monitor.reset()
        self.events.clear()
        self.table.setRowCount(0)
        self._update_filter_status()
        self.update_stats(self.controller.monitor.snapshot())

    def _rebuild_table(self, *_args: object) -> None:
        events = self._filtered_events()
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        for event in reversed(events[-self.MAX_VISIBLE_ROWS :]):
            self._insert_event(self.table.rowCount(), event)
        self.table.setUpdatesEnabled(True)
        self._update_filter_status(len(events))

    def _insert_event(self, row: int, event: dict) -> None:
        self.table.insertRow(row)
        values = [
            self._format_time(event),
            str(event.get("device", "")),
            str(event.get("name", "")),
            self._event_label(str(event.get("event_type", ""))),
            f"{event.get('delta_ms')} ms" if event.get("delta_ms") is not None else "—",
        ]
        for column, value in enumerate(values):
            self.table.setItem(row, column, QTableWidgetItem(value))

    def _filtered_events(self) -> list[dict]:
        return [event for event in self.events if self._matches(event)]

    def _matches(self, event: dict) -> bool:
        query = self.search.text().strip().casefold()
        if query:
            haystack = " ".join(
                str(event.get(key, "")) for key in ("device", "name", "event_type")
            ).casefold()
            if query not in haystack:
                return False
        device = str(self.device_filter.currentData() or "").casefold()
        actual_device = str(event.get("device", "")).casefold()
        if device == "keyboard" and not ("key" in actual_device or "tecl" in actual_device):
            return False
        if device == "mouse" and not ("mouse" in actual_device or "rat" in actual_device):
            return False
        event_filter = str(self.event_filter.currentData() or "")
        event_type = str(event.get("event_type", "")).casefold()
        if event_filter == "press" and event_type not in {"down", "press", "double", "scroll"}:
            return False
        if event_filter == "release" and event_type not in {"up", "release"}:
            return False
        return True

    def _update_filter_status(self, filtered_count: int | None = None) -> None:
        if self.paused:
            self.filter_status.setText(f"Vista pausada · {len(self.events)} eventos")
            return
        count = len(self._filtered_events()) if filtered_count is None else filtered_count
        visible = min(count, self.MAX_VISIBLE_ROWS)
        self.filter_status.setText(f"{visible} de {count}")

    @staticmethod
    def _format_time(event: dict, *, include_date: bool = False) -> str:
        try:
            value = datetime.fromtimestamp(float(event.get("time", 0)))
        except (TypeError, ValueError, OSError):
            return "—"
        pattern = "%Y-%m-%d %H:%M:%S.%f" if include_date else "%H:%M:%S.%f"
        return value.strftime(pattern)[:-3]

    @staticmethod
    def _event_label(value: str) -> str:
        return {
            "down": "Pulsación",
            "press": "Pulsación",
            "double": "Doble",
            "scroll": "Rueda",
            "up": "Liberación",
            "release": "Liberación",
        }.get(value.casefold(), value)

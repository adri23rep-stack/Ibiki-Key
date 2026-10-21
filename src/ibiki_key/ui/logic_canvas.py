from __future__ import annotations

import textwrap
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QListWidget,
    QStyleOptionGraphicsItem,
    QWidget,
)

from ..models import LogicEdge, LogicGraph, LogicNode
from .catalog import (
    CATEGORY_COLORS,
    CATEGORY_LABELS,
    NODE_CATALOG,
    node_display_id,
    node_output_hint,
    node_summary,
)

NODE_MIME_TYPE = "application/x-ibiki-logic-node"


class NodePalette(QListWidget):
    """Lista de nodos que admite doble clic y arrastre hacia el lienzo."""

    node_activated = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAlternatingRowColors(True)
        self.itemDoubleClicked.connect(self._activate_item)

    def _activate_item(self, item: object, _column: int = 0) -> None:
        self.node_activated.emit(str(item.data(Qt.ItemDataRole.UserRole)))  # type: ignore[attr-defined]

    def startDrag(self, supported_actions: Qt.DropAction) -> None:  # noqa: N802
        item = self.currentItem()
        if not item:
            return
        kind = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not kind:
            return
        mime = QMimeData()
        mime.setData(NODE_MIME_TYPE, kind.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class LogicNodeItem(QGraphicsRectItem):
    WIDTH = 270
    HEIGHT = 132

    def __init__(
        self,
        node: LogicNode,
        moved: Callable[[], None],
        edit: Callable[[LogicNode], None],
        move_started: Callable[[], None] | None = None,
        move_finished: Callable[[], None] | None = None,
    ):
        super().__init__(0, 0, self.WIDTH, self.HEIGHT)
        self.node = node
        self.moved_callback = moved
        self.edit_callback = edit
        self.move_started_callback = move_started
        self.move_finished_callback = move_finished
        self._press_pos: QPointF | None = None
        self.setPos(node.x, node.y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(2)
        _, category, _ = NODE_CATALOG.get(node.kind, ("Nodo", "utility", {}))
        color = CATEGORY_COLORS.get(category, "#60A5FA")
        self.category_color = QColor(color)
        body_color = self.category_color.darker(520)
        self.setBrush(body_color)
        self.setPen(QPen(self.category_color, 1.5))

        category_text = QGraphicsSimpleTextItem(CATEGORY_LABELS.get(category, "NODO"), self)
        category_text.setBrush(self.category_color)
        category_text.setFont(self._font(8, bold=True))
        category_text.setPos(18, 11)

        identifier = QGraphicsSimpleTextItem(node_display_id(node.kind, node.id), self)
        identifier.setBrush(QColor("#DCE7FF"))
        identifier.setFont(self._font(8, bold=True))
        identifier.setPos(self.WIDTH - identifier.boundingRect().width() - 16, 11)

        shown_title = node.title if len(node.title) <= 34 else f"{node.title[:31]}…"
        title = QGraphicsSimpleTextItem(shown_title, self)
        title.setBrush(QColor("#FFFFFF"))
        title.setPos(18, 38)
        title.setFont(self._font(11, bold=True))

        summary_text = self._summary()
        summary_lines = textwrap.wrap(
            summary_text,
            width=42,
            break_long_words=True,
            break_on_hyphens=False,
        )[:2] or ["Sin configuración"]
        for index, line in enumerate(summary_lines):
            summary = QGraphicsSimpleTextItem(line, self)
            summary.setBrush(QColor("#C7D2E8"))
            summary.setPos(18, 68 + index * 17)
            summary.setFont(self._font(9))

        output = QGraphicsSimpleTextItem(node_output_hint(node.kind), self)
        output.setBrush(QColor("#93A4C5"))
        output.setFont(self._font(7, bold=True))
        output.setPos(18, 108)

        for x in (-5.5, self.WIDTH - 5.5):
            port = QGraphicsEllipseItem(x, self.HEIGHT / 2 - 5.5, 11, 11, self)
            port.setBrush(self.category_color)
            port.setPen(QPen(body_color, 2))

        catalog_title = NODE_CATALOG.get(node.kind, ("Nodo", "utility", {}))[0]
        self.setToolTip(
            f"{catalog_title}\nID: {node_display_id(node.kind, node.id)}\n"
            f"{summary_text}\n\nDoble clic para editar"
        )

    def _summary(self) -> str:
        return node_summary(self.node.kind, self.node.config)

    @staticmethod
    def _font(size: int, *, bold: bool = False) -> QFont:
        font = QFont("Segoe UI", size)
        if bold:
            font.setWeight(QFont.Weight.DemiBold)
        return font

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: object) -> object:  # noqa: N802
        result = super().itemChange(change, value)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            position = self.pos()
            self.node.x = position.x()
            self.node.y = position.y()
            self.moved_callback()
        return result

    def mouseDoubleClickEvent(self, event: object) -> None:  # noqa: N802
        self.edit_callback(self.node)
        event.accept()  # type: ignore[attr-defined]

    def mousePressEvent(self, event: object) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:  # type: ignore[attr-defined]
            self._press_pos = QPointF(self.pos())
            if self.move_started_callback:
                self.move_started_callback()
        super().mousePressEvent(event)  # type: ignore[arg-type]

    def mouseReleaseEvent(self, event: object) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)  # type: ignore[arg-type]
        if self._press_pos is not None and self.move_finished_callback:
            self.move_finished_callback()
        self._press_pos = None

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(
            QPen(QColor("#FFFFFF"), 2.6)
            if self.isSelected()
            else QPen(self.category_color, 1.5)
        )
        painter.setBrush(self.brush())
        painter.drawRoundedRect(self.rect(), 12, 12)
        accent = QPen(self.category_color, 6)
        accent.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(accent)
        painter.drawLine(QPointF(7, 18), QPointF(7, self.HEIGHT - 18))


class LogicEdgeItem(QGraphicsPathItem):
    def __init__(self, edge: LogicEdge, source: LogicNodeItem, target: LogicNodeItem):
        super().__init__()
        self.edge = edge
        self.source = source
        self.target = target
        self.setZValue(1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        color = {
            "yes": "#2DD4BF",
            "no": "#FB7185",
            "timeout": "#F59E0B",
            "always": "#60A5FA",
        }.get(edge.branch, "#8B5CF6")
        self.base_color = QColor(color)
        self.label = QGraphicsSimpleTextItem(
            {
                "yes": "Sí",
                "no": "No",
                "timeout": "Tiempo",
                "next": "",
                "always": "Siempre",
            }.get(edge.branch, edge.branch),
            self,
        )
        self.label.setBrush(self.base_color)
        self.label.setFont(LogicNodeItem._font(8, bold=True))
        self.update_path()

    def update_path(self) -> None:
        start = self.source.scenePos() + QPointF(LogicNodeItem.WIDTH, LogicNodeItem.HEIGHT / 2)
        end = self.target.scenePos() + QPointF(0, LogicNodeItem.HEIGHT / 2)
        span = max(70.0, abs(end.x() - start.x()) * 0.5)
        path = QPainterPath(start)
        path.cubicTo(start + QPointF(span, 0), end - QPointF(span, 0), end)
        self.setPath(path)
        self.setPen(QPen(QColor("#FFFFFF") if self.isSelected() else self.base_color, 2.5))
        mid = path.pointAtPercent(0.5)
        self.label.setPos(mid + QPointF(4, -16))


class LogicCanvas(QGraphicsView):
    node_dropped = Signal(str, object)
    zoom_changed = Signal(int)

    def __init__(
        self,
        edit_node: Callable[[LogicNode], None],
        moved: Callable[[], None] | None = None,
        change_started: Callable[[], None] | None = None,
        change_finished: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.edit_node_callback = edit_node
        self.moved_callback = moved
        self.change_started_callback = change_started
        self.change_finished_callback = change_finished
        self.graph: LogicGraph | None = None
        self.scene_model = QGraphicsScene(self)
        self.setScene(self.scene_model)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setSceneRect(-2000, -1500, 4000, 3000)
        self.setAcceptDrops(True)
        self.node_items: dict[str, LogicNodeItem] = {}
        self.edge_items: list[LogicEdgeItem] = []

    def set_graph(self, graph: LogicGraph | None) -> None:
        self.graph = graph
        self.scene_model.clear()
        self.node_items.clear()
        self.edge_items.clear()
        if not graph:
            self.zoom_changed.emit(self.zoom_percent())
            return
        for node in graph.nodes:
            item = LogicNodeItem(
                node,
                self._node_moved,
                self.edit_node_callback,
                self._change_started,
                self._change_finished,
            )
            self.scene_model.addItem(item)
            self.node_items[node.id] = item
        for edge in graph.edges:
            source = self.node_items.get(edge.source)
            target = self.node_items.get(edge.target)
            if source and target:
                item = LogicEdgeItem(edge, source, target)
                self.scene_model.addItem(item)
                self.edge_items.append(item)
        self.refresh_edges()

    def refresh_edges(self) -> None:
        for edge in self.edge_items:
            edge.update_path()

    def _node_moved(self) -> None:
        self.refresh_edges()
        if self.moved_callback:
            self.moved_callback()

    def _change_started(self) -> None:
        if self.change_started_callback:
            self.change_started_callback()

    def _change_finished(self) -> None:
        if self.change_finished_callback:
            self.change_finished_callback()

    def selected_nodes(self) -> list[LogicNode]:
        return [item.node for item in self.scene_model.selectedItems() if isinstance(item, LogicNodeItem)]

    def delete_selected(self) -> bool:
        if not self.graph:
            return False
        selected_nodes = {
            item.node.id for item in self.scene_model.selectedItems() if isinstance(item, LogicNodeItem)
        }
        selected_edges = {
            id(item.edge) for item in self.scene_model.selectedItems() if isinstance(item, LogicEdgeItem)
        }
        if not selected_nodes and not selected_edges:
            return False
        self.graph.nodes = [node for node in self.graph.nodes if node.id not in selected_nodes]
        self.graph.edges = [
            edge
            for edge in self.graph.edges
            if edge.source not in selected_nodes
            and edge.target not in selected_nodes
            and id(edge) not in selected_edges
        ]
        self.set_graph(self.graph)
        return True

    def select_nodes(self, node_ids: list[str]) -> None:
        wanted = set(node_ids)
        for node_id, item in self.node_items.items():
            item.setSelected(node_id in wanted)

    def select_item_at(self, position: object) -> None:
        item = self.itemAt(position)  # type: ignore[arg-type]
        while item and not isinstance(item, (LogicNodeItem, LogicEdgeItem)):
            item = item.parentItem()
        if not item:
            return
        if not item.isSelected():
            self.scene_model.clearSelection()
            item.setSelected(True)

    def set_editable(self, editable: bool) -> None:
        for item in self.node_items.values():
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, editable)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:  # noqa: N802
        painter.fillRect(rect, QColor("#0C0F18"))
        minor = 24
        left = int(rect.left()) - (int(rect.left()) % minor)
        top = int(rect.top()) - (int(rect.top()) % minor)
        painter.setPen(QPen(QColor("#171B29"), 1))
        x = left
        while x < rect.right():
            painter.drawLine(x, rect.top(), x, rect.bottom())
            x += minor
        y = top
        while y < rect.bottom():
            painter.drawLine(rect.left(), y, rect.right(), y)
            y += minor

    def wheelEvent(self, event: object) -> None:  # noqa: N802
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15  # type: ignore[attr-defined]
        self._scale_bounded(factor)
        event.accept()  # type: ignore[attr-defined]

    def zoom_percent(self) -> int:
        return int(round(self.transform().m11() * 100))

    def zoom_in(self) -> None:
        self._scale_bounded(1.2)

    def zoom_out(self) -> None:
        self._scale_bounded(1 / 1.2)

    def reset_zoom(self) -> None:
        self.resetTransform()
        self.zoom_changed.emit(100)

    def _scale_bounded(self, factor: float) -> None:
        current = self.transform().m11()
        target = current * factor
        if target < 0.25:
            factor = 0.25 / current
        elif target > 2.5:
            factor = 2.5 / current
        self.scale(factor, factor)
        self.zoom_changed.emit(self.zoom_percent())

    def fit_graph(self) -> None:
        bounds = self.scene_model.itemsBoundingRect()
        if not bounds.isEmpty():
            self.fitInView(bounds.adjusted(-60, -60, 60, 60), Qt.AspectRatioMode.KeepAspectRatio)
            current = self.transform().m11()
            if current < 0.25:
                self.scale(0.25 / current, 0.25 / current)
            elif current > 2.5:
                self.scale(2.5 / current, 2.5 / current)
            self.centerOn(bounds.center())
            self.zoom_changed.emit(self.zoom_percent())

    def dragEnterEvent(self, event: object) -> None:  # noqa: N802
        if event.mimeData().hasFormat(NODE_MIME_TYPE):  # type: ignore[attr-defined]
            event.acceptProposedAction()  # type: ignore[attr-defined]
            return
        super().dragEnterEvent(event)  # type: ignore[arg-type]

    def dragMoveEvent(self, event: object) -> None:  # noqa: N802
        if event.mimeData().hasFormat(NODE_MIME_TYPE):  # type: ignore[attr-defined]
            event.acceptProposedAction()  # type: ignore[attr-defined]
            return
        super().dragMoveEvent(event)  # type: ignore[arg-type]

    def dropEvent(self, event: object) -> None:  # noqa: N802
        mime = event.mimeData()  # type: ignore[attr-defined]
        if mime.hasFormat(NODE_MIME_TYPE):
            kind = bytes(mime.data(NODE_MIME_TYPE)).decode("utf-8", errors="ignore")
            position = self.mapToScene(event.position().toPoint())  # type: ignore[attr-defined]
            self.node_dropped.emit(kind, position)
            event.acceptProposedAction()  # type: ignore[attr-defined]
            return
        super().dropEvent(event)  # type: ignore[arg-type]

    def export_png(self, destination: str | Path) -> bool:
        bounds = self.scene_model.itemsBoundingRect()
        if bounds.isEmpty():
            return False
        source = bounds.adjusted(-48, -48, 48, 48)
        scale = min(2.0, 12000 / max(source.width(), source.height(), 1.0))
        width = max(1, int(source.width() * scale))
        height = max(1, int(source.height() * scale))
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("#0C0F18"))
        selected = list(self.scene_model.selectedItems())
        self.scene_model.clearSelection()
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene_model.render(painter, QRectF(0, 0, width, height), source)
        painter.end()
        for item in selected:
            item.setSelected(True)
        return image.save(str(destination), "PNG")

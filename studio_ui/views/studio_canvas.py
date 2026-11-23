"""Interactive 1080p Studio Canvas for Whiteboard Studio.

Part of Phase 8 & 9: Interactive Canvas, Timeline & Studio Editor.
Provides 1920x1080 virtual coordinate space, asset manipulation, camera frustum
visualization, snap guides, and selection handling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from studio_ui.qt import (
    QBrush,
    QColor,
    QFont,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QPainter,
    QPen,
    QPixmap,
    QPointF,
    QRectF,
    Qt,
    Signal,
    Slot,
)


class CanvasElementItem(QGraphicsPixmapItem):
    """Interactive visual element item on the 1080p canvas."""

    def __init__(
        self,
        element_id: str,
        pixmap: QPixmap,
        initial_x: float = 100.0,
        initial_y: float = 100.0,
        scale_factor: float = 1.0,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(pixmap, parent)
        self.element_id = element_id
        self.scale_factor = scale_factor
        self.start_time = 0.0
        self.animation_style = "Outside-In Pen"
        self.anchor_word = ""
        self.draw_duration = 0.8
        self.hold_duration = 2.0

        self.setPos(initial_x, initial_y)
        self.setScale(scale_factor)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def set_playhead_time(self, time_sec: float, is_playing: bool = False) -> None:
        """Dynamically updates element visibility and inking progress matching the playhead."""
        draw_start = self.start_time
        draw_end = self.start_time + self.draw_duration
        hold_end = draw_end + self.hold_duration

        if time_sec < draw_start:
            # Not yet reached
            self.setOpacity(0.0 if is_playing else 0.35)
        elif draw_start <= time_sec < draw_end:
            # Currently drawing
            progress = (time_sec - draw_start) / max(0.05, self.draw_duration)
            self.setOpacity(min(1.0, 0.25 + 0.75 * progress))
        else:
            # Drawn and holding
            self.setOpacity(1.0)

    def paint(self, painter: QPainter, option: Any, widget: Any = None) -> None:
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.save()
            pen = QPen(QColor("#4F46E5"), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = self.boundingRect()
            painter.drawRect(r)

            # Draw small corner selection handles
            handle_size = 6
            painter.setBrush(QBrush(QColor("#4F46E5")))
            painter.drawRect(QRectF(r.left(), r.top(), handle_size, handle_size))
            painter.drawRect(QRectF(r.right() - handle_size, r.top(), handle_size, handle_size))
            painter.drawRect(QRectF(r.left(), r.bottom() - handle_size, handle_size, handle_size))
            painter.drawRect(QRectF(r.right() - handle_size, r.bottom() - handle_size, handle_size, handle_size))
            painter.restore()

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            scene = self.scene()
            if scene and hasattr(scene, "on_element_geometry_changed"):
                scene.on_element_geometry_changed(self)
        return super().itemChange(change, value)


class CanvasTextItem(QGraphicsTextItem):
    """Interactive text overlay item on the 1080p canvas with RTL support."""

    def __init__(
        self,
        text_id: str,
        text: str,
        initial_x: float = 200.0,
        initial_y: float = 200.0,
        font_size: int = 36,
        color_hex: str = "#ffffff",
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(text, parent)
        self.text_id = text_id
        self.setPos(initial_x, initial_y)

        font = QFont("Arial", font_size, QFont.Weight.Bold)
        self.setFont(font)
        self.setDefaultTextColor(QColor(color_hex))
        self.setTextWidth(-1)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

    def paint(self, painter: QPainter, option: Any, widget: Any = None) -> None:
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.save()
            pen = QPen(QColor("#4F46E5"), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect())
            painter.restore()


class CameraFrustumItem(QGraphicsRectItem):
    """16:9 Viewport Frustum indicating the active camera shot framing."""

    def __init__(
        self,
        camera_name: str = "Camera 01",
        rect: QRectF = QRectF(0, 0, 1920, 1080),
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(rect, parent)
        self.camera_name = camera_name
        self.zoom = 1.0

        # Border styling: amber dashed bounding box
        pen = QPen(QColor("#D97706"), 2, Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setBrush(QBrush(QColor(245, 158, 11, 15)))  # faint transparent amber fill
        self.setZValue(100)  # Render on top of assets

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

    def paint(self, painter: QPainter, option: Any, widget: Any = None) -> None:
        super().paint(painter, option, widget)
        # Draw camera label badge in top-left
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#D97706")))
        r = self.rect()
        badge_rect = QRectF(r.left() + 8, r.top() + 8, 140, 24)
        painter.drawRoundedRect(badge_rect, 4, 4)

        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, f"🎥 {self.camera_name}")
        painter.restore()


class StudioCanvasScene(QGraphicsScene):
    """1920x1080 virtual resolution canvas scene."""

    element_selected = Signal(str)  # element_id
    element_geometry_changed = Signal(str, float, float, float)  # (id, x, y, scale)
    selection_cleared = Signal()

    CANVAS_WIDTH = 1920
    CANVAS_HEIGHT = 1080

    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(0, 0, self.CANVAS_WIDTH, self.CANVAS_HEIGHT, parent)
        self.setBackgroundBrush(QBrush(QColor("#FFFFFF")))
        self.show_safe_zones = True
        self.selectionChanged.connect(self._on_selection_changed)

    def update_playhead(self, time_sec: float, is_playing: bool = False) -> None:
        """Propagate current playhead time to all animated canvas items."""
        for item in self.items():
            if isinstance(item, CanvasElementItem):
                item.set_playhead_time(time_sec, is_playing)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        # Base background fill
        painter.fillRect(rect, QColor("#F5F6F8"))

        # 1920x1080 Canvas Boundary
        canvas_rect = QRectF(0, 0, self.CANVAS_WIDTH, self.CANVAS_HEIGHT)
        painter.fillRect(canvas_rect, QColor("#FFFFFF"))

        # Canvas Border
        pen = QPen(QColor("#E4E7EC"), 2)
        painter.setPen(pen)
        painter.drawRect(canvas_rect)

        # 1080p Grid (240px intervals)
        grid_pen = QPen(QColor("#FAFBFC"), 1, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        for x in range(240, self.CANVAS_WIDTH, 240):
            painter.drawLine(x, 0, x, self.CANVAS_HEIGHT)
        for y in range(180, self.CANVAS_HEIGHT, 180):
            painter.drawLine(0, y, self.CANVAS_WIDTH, y)

        # Safe Area Guides (Action Safe 90%, Title Safe 80%)
        if self.show_safe_zones:
            # Action safe: 90% (54px margin on top/bottom, 96px on sides)
            as_pen = QPen(QColor(56, 189, 248, 60), 1, Qt.PenStyle.DashLine)
            painter.setPen(as_pen)
            action_safe = QRectF(96, 54, 1920 - 192, 1080 - 108)
            painter.drawRect(action_safe)

            # Title safe: 80% (108px margin on top/bottom, 192px on sides)
            ts_pen = QPen(QColor(245, 158, 11, 50), 1, Qt.PenStyle.DashLine)
            painter.setPen(ts_pen)
            title_safe = QRectF(192, 108, 1920 - 384, 1080 - 216)
            painter.drawRect(title_safe)

    def _on_selection_changed(self) -> None:
        items = self.selectedItems()
        if not items:
            self.selection_cleared.emit()
            return
        selected = items[0]
        if isinstance(selected, CanvasElementItem):
            self.element_selected.emit(selected.element_id)
        elif isinstance(selected, CanvasTextItem):
            self.element_selected.emit(selected.text_id)
        elif isinstance(selected, CameraFrustumItem):
            self.element_selected.emit(selected.camera_name)

    def on_element_geometry_changed(self, item: CanvasElementItem) -> None:
        pos = item.pos()
        self.element_geometry_changed.emit(item.element_id, pos.x(), pos.y(), item.scale())


class StudioCanvasView(QGraphicsView):
    """Viewport supporting zoom, pan, and interactive canvas manipulation."""

    def __init__(self, scene: StudioCanvasScene, parent: Optional[Any] = None) -> None:
        super().__init__(scene, parent)
        self.canvas_scene = scene

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setStyleSheet("border: none; background-color: #F5F6F8;")

    def zoom_in(self) -> None:
        self.scale(1.2, 1.2)

    def zoom_out(self) -> None:
        self.scale(1.0 / 1.2, 1.0 / 1.2)

    def reset_zoom(self) -> None:
        self.resetTransform()

    def fit_1080p(self) -> None:
        """Fit the entire 1920x1080 canvas scene within the view viewport."""
        self.fitInView(0, 0, 1920, 1080, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

"""Camera Render View -- Render-Accurate Multi-Camera Preview Panel.

Provides a horizontal strip of camera views that exactly match the render engine's
world-to-screen projection:
    scr_x = WIDTH/2 + (world_x - cam_x) * cam_zoom
    scr_y = HEIGHT/2 + (world_y - cam_y) * cam_zoom

Features:
- White canvas background (matching actual whiteboard render output)
- Render-accurate projection of world-coordinate elements into each camera frame
- Timeline-synced element visibility (only elements active at playhead are shown)
- Horizontal multi-camera strip (N cameras side-by-side)
- Interactive element manipulation (move, scale, reorder) within each camera frame
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from PySide6.QtWidgets import QSizePolicy
except ImportError:
    from PyQt6.QtWidgets import QSizePolicy

from studio_ui.qt import (
    QBrush,
    QColor,
    QFont,
    QHBoxLayout,
    QLabel,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QPoint,
    QPointF,
    QRectF,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    Qt,
    Signal,
)

RENDER_WIDTH = 1920
RENDER_HEIGHT = 1080


def world_to_screen(world_x, world_y, cam_x, cam_y, cam_zoom):
    scr_x = RENDER_WIDTH / 2.0 + (world_x - cam_x) * cam_zoom
    scr_y = RENDER_HEIGHT / 2.0 + (world_y - cam_y) * cam_zoom
    return scr_x, scr_y


def screen_to_world(scr_x, scr_y, cam_x, cam_y, cam_zoom):
    world_x = cam_x + (scr_x - RENDER_WIDTH / 2.0) / cam_zoom
    world_y = cam_y + (scr_y - RENDER_HEIGHT / 2.0) / cam_zoom
    return world_x, world_y


class SingleCameraRenderWidget(QWidget):
    """A single camera render-accurate white-canvas preview."""

    element_moved = Signal(str, float, float)
    element_scaled = Signal(str, float)
    element_selected = Signal(str)
    camera_selected = Signal(str)

    def __init__(self, camera_name: str, camera_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.camera_name = camera_name
        self.camera_data = dict(camera_data)
        self.elements: Dict[str, Dict[str, Any]] = {}
        self.pixmaps: Dict[str, QPixmap] = {}
        self.playhead_time: float = 0.0
        self.selected_element_id: Optional[str] = None
        self.z_order: List[str] = []

        self._dragging_id: Optional[str] = None
        self._drag_offset_x: float = 0.0
        self._drag_offset_y: float = 0.0
        self._drag_start_world_x: float = 0.0
        self._drag_start_world_y: float = 0.0
        self._panning: bool = False
        self._pan_start: Optional[QPoint] = None
        self._view_zoom: float = 1.0
        self._view_pan_x: float = 0.0
        self._view_pan_y: float = 0.0

        self.setMinimumSize(380, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_camera_data(self, camera_data: Dict[str, Any]):
        self.camera_data = dict(camera_data)
        self.update()

    def set_elements(self, elements: Dict[str, Dict[str, Any]], pixmaps: Dict[str, QPixmap]):
        self.elements = dict(elements)
        self.pixmaps = dict(pixmaps)
        new_ids = set(elements.keys())
        self.z_order = [eid for eid in self.z_order if eid in new_ids]
        for eid in elements:
            if eid not in self.z_order:
                self.z_order.append(eid)
        self.update()

    def set_playhead_time(self, time_sec: float):
        self.playhead_time = time_sec
        self.update()

    def set_selected_element(self, element_id: Optional[str]):
        self.selected_element_id = element_id
        self.update()

    def move_element_up(self, element_id: str):
        if element_id in self.z_order:
            idx = self.z_order.index(element_id)
            if idx < len(self.z_order) - 1:
                self.z_order[idx], self.z_order[idx + 1] = self.z_order[idx + 1], self.z_order[idx]
                self.update()

    def move_element_down(self, element_id: str):
        if element_id in self.z_order:
            idx = self.z_order.index(element_id)
            if idx > 0:
                self.z_order[idx], self.z_order[idx - 1] = self.z_order[idx - 1], self.z_order[idx]
                self.update()

    def _cam_props(self):
        cam_x = float(self.camera_data.get("center_x", RENDER_WIDTH / 2))
        cam_y = float(self.camera_data.get("center_y", RENDER_HEIGHT / 2))
        cam_zoom = float(self.camera_data.get("zoom", 1.0))
        return cam_x, cam_y, cam_zoom

    def _view_scale(self) -> float:
        w = max(1, self.width())
        h = max(1, self.height())
        return min(w / RENDER_WIDTH, h / RENDER_HEIGHT) * self._view_zoom

    def _render_rect_in_view(self) -> QRectF:
        scale = self._view_scale()
        rw = RENDER_WIDTH * scale
        rh = RENDER_HEIGHT * scale
        ox = (self.width() - rw) / 2.0 + self._view_pan_x
        oy = (self.height() - rh) / 2.0 + self._view_pan_y
        return QRectF(ox, oy, rw, rh)

    def _view_to_world(self, vx: float, vy: float):
        rr = self._render_rect_in_view()
        scale = self._view_scale()
        render_x = (vx - rr.left()) / scale
        render_y = (vy - rr.top()) / scale
        cam_x, cam_y, cam_zoom = self._cam_props()
        return screen_to_world(render_x, render_y, cam_x, cam_y, cam_zoom)

    def _is_element_visible(self, eid: str) -> bool:
        edata = self.elements.get(eid, {})
        start = float(edata.get("start_time", 0.0))
        draw_dur = float(edata.get("draw_duration", 0.8))
        hold_dur = float(edata.get("hold_duration", 2.0))
        return start <= self.playhead_time <= start + draw_dur + hold_dur

    def _hit_test(self, pt: QPoint) -> Optional[str]:
        rr = self._render_rect_in_view()
        s = self._view_scale()
        cam_x, cam_y, cam_zoom = self._cam_props()
        for eid in reversed(self.z_order):
            if not self._is_element_visible(eid):
                continue
            edata = self.elements.get(eid, {})
            world_x = float(edata.get("x", edata.get("cx", 0)))
            world_y = float(edata.get("y", edata.get("cy", 0)))
            world_w = float(edata.get("w", edata.get("width", 200)))
            world_h = float(edata.get("h", edata.get("height", 150)))
            scale_f = float(edata.get("scale", 1.0))
            rx, ry = world_to_screen(world_x, world_y, cam_x, cam_y, cam_zoom)
            vx = rr.left() + rx * s
            vy = rr.top() + ry * s
            vw = world_w * scale_f * cam_zoom * s
            vh = world_h * scale_f * cam_zoom * s
            if QRectF(vx, vy, vw, vh).contains(float(pt.x()), float(pt.y())):
                return eid
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Dark surround
        painter.fillRect(self.rect(), QColor("#0d0d14"))

        rr = self._render_rect_in_view()
        s = self._view_scale()

        # White canvas
        painter.fillRect(rr, QColor("#ffffff"))

        # Light grid
        painter.save()
        painter.setClipRect(rr)
        grid_pen = QPen(QColor(180, 180, 180, 70), 0.5, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        grid_x = 240 * s
        gx = rr.left() + grid_x
        while gx < rr.right():
            painter.drawLine(QPointF(gx, rr.top()), QPointF(gx, rr.bottom()))
            gx += grid_x
        grid_y_step = 180 * s
        gy = rr.top() + grid_y_step
        while gy < rr.bottom():
            painter.drawLine(QPointF(rr.left(), gy), QPointF(rr.right(), gy))
            gy += grid_y_step
        painter.restore()

        cam_x, cam_y, cam_zoom = self._cam_props()

        # Draw elements in z-order
        painter.setClipRect(rr)
        for eid in self.z_order:
            edata = self.elements.get(eid)
            if not edata:
                continue
            is_visible = self._is_element_visible(eid)
            start = float(edata.get("start_time", 0.0))
            draw_dur = float(edata.get("draw_duration", 0.8))

            if not is_visible:
                opacity = 0.12
            elif self.playhead_time < start + draw_dur:
                progress = (self.playhead_time - start) / max(0.05, draw_dur)
                opacity = min(1.0, 0.2 + 0.8 * progress)
            else:
                opacity = 1.0

            world_x = float(edata.get("x", edata.get("cx", 0)))
            world_y = float(edata.get("y", edata.get("cy", 0)))
            world_w = float(edata.get("w", edata.get("width", 200)))
            world_h = float(edata.get("h", edata.get("height", 150)))
            scale_f = float(edata.get("scale", 1.0))

            rx, ry = world_to_screen(world_x, world_y, cam_x, cam_y, cam_zoom)
            rw = world_w * scale_f * cam_zoom
            rh = world_h * scale_f * cam_zoom

            vx = rr.left() + rx * s
            vy = rr.top() + ry * s
            vw = rw * s
            vh = rh * s
            elem_rect = QRectF(vx, vy, vw, vh)

            pix = self.pixmaps.get(eid)
            painter.setOpacity(opacity)
            if pix and not pix.isNull():
                painter.drawPixmap(elem_rect.toRect(), pix)
            else:
                fill_c = QColor("#E0E7FF") if is_visible else QColor("#344054")
                painter.fillRect(elem_rect, fill_c)
                painter.setPen(QPen(QColor("#4F46E5"), 1.0))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(elem_rect)
            painter.setOpacity(1.0)

            # Selection ring
            if eid == self.selected_element_id:
                sel_pen = QPen(QColor("#D97706"), 2.5)
                painter.setPen(sel_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(elem_rect)
                hs = 7.0
                painter.setBrush(QBrush(QColor("#D97706")))
                for hx, hy in [
                    (elem_rect.left(), elem_rect.top()),
                    (elem_rect.right() - hs, elem_rect.top()),
                    (elem_rect.left(), elem_rect.bottom() - hs),
                    (elem_rect.right() - hs, elem_rect.bottom() - hs),
                ]:
                    painter.drawRect(QRectF(hx, hy, hs, hs))

            # Element label
            if opacity > 0.25 and vw > 20:
                painter.setOpacity(opacity)
                painter.setPen(QColor("#101828"))
                f = QFont("Arial", max(6, int(8 * s)))
                painter.setFont(f)
                short = eid[-14:] if len(eid) > 14 else eid
                painter.drawText(QRectF(vx + 2, vy + 2, vw - 4, 14), Qt.AlignmentFlag.AlignLeft, short)
                painter.setOpacity(1.0)

        painter.setClipping(False)

        # Camera frame border
        border_color = QColor("#D97706") if self.hasFocus() else QColor("#475467")
        painter.setPen(QPen(border_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rr)

        # Camera name badge
        badge_h = max(22, int(26 * s))
        badge_rect = QRectF(rr.left() + 6, rr.top() + 5, 165, badge_h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#D97706")))
        painter.drawRoundedRect(badge_rect, 5, 5)
        painter.setPen(QColor("#FFFFFF"))
        badge_font = QFont("Arial", max(8, int(10 * s)), QFont.Weight.Bold)
        painter.setFont(badge_font)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, f"Camera: {self.camera_name}")

        # Info line
        cam_x_v, cam_y_v, cam_zoom_v = self._cam_props()
        info = f"zoom={cam_zoom_v:.2f}  cx={int(cam_x_v)}  cy={int(cam_y_v)}"
        painter.setPen(QColor("#667085"))
        painter.setFont(QFont("Arial", max(6, int(8 * s))))
        painter.drawText(
            QRectF(rr.left() + 5, rr.bottom() - 18, 300, 16),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            info,
        )
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus()
        self.camera_selected.emit(self.camera_name)
        pt = event.pos()
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = pt
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            hit = self._hit_test(pt)
            if hit:
                self.selected_element_id = hit
                self.element_selected.emit(hit)
                edata = self.elements[hit]
                world_x = float(edata.get("x", 0))
                world_y = float(edata.get("y", 0))
                wx, wy = self._view_to_world(float(pt.x()), float(pt.y()))
                self._dragging_id = hit
                self._drag_offset_x = wx - world_x
                self._drag_offset_y = wy - world_y
                self._drag_start_world_x = world_x
                self._drag_start_world_y = world_y
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.selected_element_id = None
                self._dragging_id = None
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pt = event.pos()
        if self._panning and self._pan_start:
            dx = pt.x() - self._pan_start.x()
            dy = pt.y() - self._pan_start.y()
            self._view_pan_x += dx
            self._view_pan_y += dy
            self._pan_start = pt
            self.update()
            return
        if self._dragging_id:
            wx, wy = self._view_to_world(float(pt.x()), float(pt.y()))
            new_x = wx - self._drag_offset_x
            new_y = wy - self._drag_offset_y
            if self._dragging_id in self.elements:
                self.elements[self._dragging_id]["x"] = new_x
                self.elements[self._dragging_id]["y"] = new_y
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        if event.button() == Qt.MouseButton.LeftButton and self._dragging_id:
            eid = self._dragging_id
            self._dragging_id = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if eid in self.elements:
                new_x = float(self.elements[eid].get("x", 0))
                new_y = float(self.elements[eid].get("y", 0))
                if (new_x, new_y) != (self._drag_start_world_x, self._drag_start_world_y):
                    self.element_moved.emit(eid, new_x, new_y)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if delta > 0 else 1.0 / 1.15
            self._view_zoom = max(0.15, min(8.0, self._view_zoom * factor))
            self.update()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        if self.selected_element_id:
            if key == Qt.Key.Key_BracketRight:
                self.move_element_up(self.selected_element_id)
            elif key == Qt.Key.Key_BracketLeft:
                self.move_element_down(self.selected_element_id)
        super().keyPressEvent(event)


class MultiCameraRenderStrip(QWidget):
    """Horizontal strip of camera render views -- one per camera."""

    element_moved = Signal(str, float, float)
    element_selected = Signal(str)
    camera_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: #FFFFFF; border-bottom: 1px solid #FAFBFC;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        title_lbl = QLabel("Camera Render Views  --  White Canvas (Render-Accurate Projection)")
        title_lbl.setStyleSheet("color: #D97706; font-weight: bold; font-size: 12px;")
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        hint_lbl = QLabel("Drag: move element  |  Ctrl+Wheel: zoom  |  Middle-drag: pan  |  [  /  ]: z-order")
        hint_lbl.setStyleSheet("color: #D0D5DD; font-size: 12px;")
        title_layout.addWidget(hint_lbl)
        root_layout.addWidget(title_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #F5F6F8; }")

        self.cameras_container = QWidget()
        self.cameras_container.setStyleSheet("background-color: #F5F6F8;")
        self.cameras_layout = QHBoxLayout(self.cameras_container)
        self.cameras_layout.setContentsMargins(8, 8, 8, 8)
        self.cameras_layout.setSpacing(8)

        self.scroll_area.setWidget(self.cameras_container)
        root_layout.addWidget(self.scroll_area)

        self._camera_widgets: Dict[str, SingleCameraRenderWidget] = {}

    def rebuild_cameras(
        self,
        cameras_data: Dict[str, Dict[str, Any]],
        elements_data: Dict[str, Dict[str, Any]],
        pixmaps: Dict[str, QPixmap],
        playhead_time: float = 0.0,
    ):
        for w in self._camera_widgets.values():
            self.cameras_layout.removeWidget(w)
            w.deleteLater()
        self._camera_widgets.clear()

        for cam_name, cam_data in cameras_data.items():
            cam_widget = SingleCameraRenderWidget(camera_name=cam_name, camera_data=cam_data)
            cam_widget.set_elements(elements_data, pixmaps)
            cam_widget.set_playhead_time(playhead_time)
            cam_widget.element_moved.connect(self.element_moved)
            cam_widget.element_selected.connect(self.element_selected)
            cam_widget.camera_selected.connect(self.camera_selected)
            self.cameras_layout.addWidget(cam_widget)
            self._camera_widgets[cam_name] = cam_widget

        self.cameras_layout.addStretch()

    def update_playhead(self, time_sec: float):
        for w in self._camera_widgets.values():
            w.set_playhead_time(time_sec)

    def update_elements(self, elements_data: Dict[str, Dict[str, Any]], pixmaps: Dict[str, QPixmap]):
        for w in self._camera_widgets.values():
            w.set_elements(elements_data, pixmaps)

    def set_elements_data(self, elements_data: Dict[str, Dict[str, Any]]):
        """Update elements data across all camera preview widgets."""
        for w in self._camera_widgets.values():
            w.elements = dict(elements_data)
            w.update()

    def update_camera(self, camera_name: str, camera_data: Dict[str, Any]):
        if camera_name in self._camera_widgets:
            self._camera_widgets[camera_name].set_camera_data(camera_data)

    def set_selected_element(self, element_id: Optional[str]):
        for w in self._camera_widgets.values():
            w.set_selected_element(element_id)

    def get_z_order(self, camera_name: str) -> List[str]:
        if camera_name in self._camera_widgets:
            return list(self._camera_widgets[camera_name].z_order)
        return []

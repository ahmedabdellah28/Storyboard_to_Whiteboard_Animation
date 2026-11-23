"""Interactive Storyboard Review & Bounding Box Canvas for Whiteboard Studio.

Allows visual inspection and manual selection of extracted elements directly over storyboard.png.
Clean, uncluttered, caption-free drawing with fluid multi-element sequential creation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from studio_ui.responsive import font_size, spacing

from studio_ui.qt import (
    QAction,
    QBrush,
    QColor,
    QCursor,
    QFont,
    QImage,
    QMenu,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QResizeEvent,
    Qt,
    QWidget,
    Signal,
)


def _rect_contains(rect: QRectF, pt: QPoint | QPointF) -> bool:
    """Safely tests if point is inside QRectF across PyQt6 and PySide6."""
    return rect.contains(float(pt.x()), float(pt.y()))


class StoryboardReviewCanvas(QWidget):
    """Interactive canvas for drawing, selecting, and adjusting element bounding boxes on storyboard.png."""

    asset_selected = Signal(str)        # asset_id
    box_modified = Signal(str, list)    # asset_id, [x, y, w, h] in image coords
    new_box_created = Signal(list)      # [x, y, w, h] in image coords
    delete_requested = Signal(str)      # asset_id
    split_requested = Signal(str, str)  # asset_id, "lr" | "tb" | "3parts"
    exclude_toggle_requested = Signal(str)  # asset_id
    redraw_requested = Signal(str)      # asset_id

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(spacing(360), spacing(260))

        self.image_path: Optional[Path] = None
        self.pixmap: Optional[QPixmap] = None
        self.img_w: int = 1920
        self.img_h: int = 1080

        # Boxes dictionary: asset_id -> {"orig_box": [x, y, w, h], "excluded": bool, ...}
        self.boxes: Dict[str, Dict[str, Any]] = {}
        self.selected_asset_id: Optional[str] = None
        self.multi_selected_ids: List[str] = []
        self.target_redraw_aid: Optional[str] = None

        # Modes: "select", "draw", or "manual_box"
        self.mode: str = "select"
        self.continuous_draw: bool = False

        # Mouse interaction state
        self._is_dragging: bool = False
        self._drag_start: Optional[QPoint] = None
        self._drag_current: Optional[QPoint] = None
        self._active_handle: Optional[str] = None  # None, "move", "tl", "tr", "bl", "br", "draw"
        self._dragged_box_orig: Optional[List[int]] = None

    def set_storyboard_image(self, img_path: Path | str) -> None:
        """Loads and caches the storyboard image."""
        self.image_path = Path(img_path).resolve()
        if self.image_path.exists():
            self.pixmap = QPixmap(str(self.image_path))
            if not self.pixmap.isNull():
                self.img_w = self.pixmap.width()
                self.img_h = self.pixmap.height()
        else:
            self.pixmap = None
        self.update()

    def get_cropped_pixmap(self, box: List[int]) -> Optional[QPixmap]:
        """Return cropped QPixmap for box [x, y, w, h]."""
        if self.pixmap and not self.pixmap.isNull() and len(box) >= 4:
            x, y, w, h = box
            x = max(0, min(self.img_w - 1, int(x)))
            y = max(0, min(self.img_h - 1, int(y)))
            w = max(1, min(self.img_w - x, int(w)))
            h = max(1, min(self.img_h - y, int(h)))
            return self.pixmap.copy(QRect(x, y, w, h))
        return None

    def set_boxes(self, boxes: Dict[str, Dict[str, Any]]) -> None:
        """Sets bounding box definitions {aid: {'orig_box': [x,y,w,h], 'excluded': bool, ...}}."""
        self.boxes = dict(boxes)
        if self.selected_asset_id and self.selected_asset_id not in self.boxes:
            self.selected_asset_id = None
        self.update()

    def set_selected_asset(self, asset_id: Optional[str]) -> None:
        """Selects an asset and highlights its bounding box."""
        if self.selected_asset_id != asset_id:
            self.selected_asset_id = asset_id
            self.update()

    def set_redraw_target(self, aid: Optional[str]) -> None:
        """Explicitly set a specific element to be redrawn on next drag."""
        self.target_redraw_aid = aid
        self.selected_asset_id = aid
        self.mode = "draw"
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.update()

    def set_mode(self, mode: str) -> None:
        """Sets interaction mode: 'select', 'draw', or 'manual_box'."""
        self.mode = mode
        if mode in ("draw", "manual_box"):
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.target_redraw_aid = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_continuous_draw(self, enabled: bool) -> None:
        self.continuous_draw = enabled

    # -------------------------------------------------------------------------
    # Coordinate Transforms
    # -------------------------------------------------------------------------

    def _get_transform_metrics(self) -> Tuple[float, float, float]:
        """Returns (scale, offset_x, offset_y) for aspect-fit image rendering."""
        w = max(1, self.width())
        h = max(1, self.height())
        iw = max(1, self.img_w)
        ih = max(1, self.img_h)

        scale = min(w / iw, h / ih)
        ox = (w - iw * scale) / 2.0
        oy = (h - ih * scale) / 2.0
        return scale, ox, oy

    def _img_to_screen_rect(self, box: List[int]) -> QRectF:
        scale, ox, oy = self._get_transform_metrics()
        bx, by, bw, bh = box
        return QRectF(ox + bx * scale, oy + by * scale, bw * scale, bh * scale)

    def _screen_to_img_point(self, pt: QPoint) -> Tuple[int, int]:
        scale, ox, oy = self._get_transform_metrics()
        ix = int((pt.x() - ox) / scale)
        iy = int((pt.y() - oy) / scale)
        ix = max(0, min(self.img_w, ix))
        iy = max(0, min(self.img_h, iy))
        return ix, iy

    # -------------------------------------------------------------------------
    # Keyboard & Context Menu
    # -------------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.selected_asset_id:
                self.delete_requested.emit(self.selected_asset_id)
                event.accept()
                return
        elif key == Qt.Key.Key_Escape:
            self.set_mode("select")
            self.target_redraw_aid = None
            self.selected_asset_id = None
            self.update()
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event) -> None:
        pt = event.pos()
        target_aid = None
        for aid, data in reversed(list(self.boxes.items())):
            box = data.get("orig_box") or data.get("bbox") or data.get("box") or [0, 0, 0, 0]
            s_rect = self._img_to_screen_rect(box)
            if _rect_contains(s_rect, pt):
                target_aid = aid
                break

        if not target_aid:
            return

        self.set_selected_asset(target_aid)
        self.asset_selected.emit(target_aid)

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #FAFBFC; color: #101828; border: 1px solid #E4E7EC; padding: 4px; border-radius: 6px; font-size: 12px; }
            QMenu::item { padding: 5px 20px 5px 10px; }
            QMenu::item:selected { background-color: #4F46E5; }
            QMenu::separator { height: 1px; background-color: #E4E7EC; margin: 4px 6px; }
        """)

        act_redraw = menu.addAction(f"🎯 إعادة تحديد يدوي بالماوس ({target_aid})")
        menu.addSeparator()
        split_menu = menu.addMenu("✂️ تقسيم العنصر...")
        act_split_lr = split_menu.addAction("✂️ تقسيم أفقي (يسار / يمين)")
        act_split_tb = split_menu.addAction("✂️ تقسيم رأسي (أعلى / أسفل)")
        act_split_3 = split_menu.addAction("✂️ تقسيم إلى 3 أجزاء")
        menu.addSeparator()
        act_exclude = menu.addAction("🚫 استبعاد / تفعيل هذا العنصر")
        menu.addSeparator()
        act_del = menu.addAction("🗑️ حذف هذا العنصر (Delete)")

        chosen = menu.exec(self.mapToGlobal(pt))
        if chosen == act_redraw:
            self.set_redraw_target(target_aid)
            self.redraw_requested.emit(target_aid)
        elif chosen == act_split_3:
            self.split_requested.emit(target_aid, "3parts")
        elif chosen == act_split_lr:
            self.split_requested.emit(target_aid, "lr")
        elif chosen == act_split_tb:
            self.split_requested.emit(target_aid, "tb")
        elif chosen == act_exclude:
            self.exclude_toggle_requested.emit(target_aid)
        elif chosen == act_del:
            self.delete_requested.emit(target_aid)

    # -------------------------------------------------------------------------
    # Paint Event
    # -------------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#FFFFFF"))

        scale, ox, oy = self._get_transform_metrics()

        # Draw Storyboard Pixmap
        if self.pixmap and not self.pixmap.isNull():
            target_rect = QRectF(ox, oy, self.img_w * scale, self.img_h * scale)
            painter.drawPixmap(target_rect.toRect(), self.pixmap)
        else:
            painter.setPen(QColor("#667085"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Storyboard Image Loaded")

        # Draw Bounding Boxes
        font = QFont("Segoe UI", font_size(12), QFont.Weight.Bold)
        painter.setFont(font)

        for aid, data in self.boxes.items():
            box = data.get("orig_box") or data.get("bbox") or data.get("box") or [0, 0, 50, 50]
            s_rect = self._img_to_screen_rect(box)
            is_sel = (aid == self.selected_asset_id) or (aid in self.multi_selected_ids)
            is_ex = data.get("excluded", False)

            if is_sel:
                pen = QPen(QColor("#D97706"), 2.5)
                fill = QColor(245, 158, 11, 40)
            elif is_ex:
                pen = QPen(QColor("#DC2626"), 1.5, Qt.PenStyle.DashLine)
                fill = QColor(239, 68, 68, 20)
            else:
                pen = QPen(QColor("#4F46E5"), 1.5)
                fill = QColor(56, 189, 248, 20)

            painter.setPen(pen)
            painter.setBrush(QBrush(fill))
            painter.drawRect(s_rect)

            # Clean, compact badge label above box
            label_text = f"{aid} [EX]" if is_ex else aid
            bg_color = QColor("#DC2626") if is_ex else (QColor("#D97706") if is_sel else QColor("#4F46E5"))
            text_w = max(45.0, len(label_text) * 7.0)
            text_rect = QRectF(s_rect.x(), max(0.0, s_rect.y() - 17), text_w, 16)
            painter.fillRect(text_rect, bg_color)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label_text)

            # Resize Handles for selected box
            if is_sel:
                painter.setBrush(QBrush(QColor("#ffffff")))
                painter.setPen(QPen(QColor("#D97706"), 1.5))
                handle_size = 6.0
                corners = [
                    s_rect.topLeft(),
                    s_rect.topRight(),
                    s_rect.bottomLeft(),
                    s_rect.bottomRight(),
                ]
                for c in corners:
                    painter.drawRect(QRectF(c.x() - handle_size / 2, c.y() - handle_size / 2, handle_size, handle_size))

        # Draw Active Drag Rectangle (Clean line, NO TEXT CAPTION OVERLAYS)
        if self._is_dragging and self._drag_start and self._drag_current:
            drag_rect = QRect(self._drag_start, self._drag_current).normalized()
            if self.target_redraw_aid:
                painter.setPen(QPen(QColor("#ec4899"), 2, Qt.PenStyle.DashDotLine))
                painter.setBrush(QBrush(QColor(236, 72, 153, 50)))
            else:
                painter.setPen(QPen(QColor("#16A34A"), 2, Qt.PenStyle.DashDotLine))
                painter.setBrush(QBrush(QColor(16, 185, 129, 50)))
            painter.drawRect(drag_rect)

    # -------------------------------------------------------------------------
    # Mouse Events
    # -------------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pt = event.pos()
            self._drag_start = pt
            self._drag_current = pt
            self._is_dragging = True

            # If user explicitly requested redraw for target element or is in draw mode:
            if self.target_redraw_aid or self.mode in ("draw", "manual_box"):
                self._active_handle = "draw"
                return

            # Check handle hit for selected box
            if self.selected_asset_id and self.selected_asset_id in self.boxes:
                box = self.boxes[self.selected_asset_id].get("orig_box") or self.boxes[self.selected_asset_id].get("bbox", [0, 0, 0, 0])
                s_rect = self._img_to_screen_rect(box)
                handle = self._hit_test_handle(s_rect, pt)
                if handle:
                    self._active_handle = handle
                    self._dragged_box_orig = list(box)
                    return

            # Hit test boxes from topmost to bottom
            clicked_aid = None
            for aid, data in reversed(list(self.boxes.items())):
                box = data.get("orig_box") or data.get("bbox") or data.get("box") or [0, 0, 0, 0]
                s_rect = self._img_to_screen_rect(box)
                if _rect_contains(s_rect, pt):
                    clicked_aid = aid
                    break

            if clicked_aid:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if clicked_aid in self.multi_selected_ids:
                        self.multi_selected_ids.remove(clicked_aid)
                    else:
                        self.multi_selected_ids.append(clicked_aid)
                else:
                    self.multi_selected_ids = [clicked_aid]

                self.selected_asset_id = clicked_aid
                self._active_handle = "move"
                self._dragged_box_orig = list(self.boxes[clicked_aid].get("orig_box") or self.boxes[clicked_aid].get("bbox", [0, 0, 0, 0]))
                self.asset_selected.emit(clicked_aid)
            else:
                self.selected_asset_id = None
                self.multi_selected_ids.clear()
                self._active_handle = None

            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pt = event.pos()
        self._drag_current = pt

        if self._is_dragging:
            if self._active_handle == "draw" or self.target_redraw_aid or self.mode in ("draw", "manual_box"):
                self.update()
                return

            if self._active_handle and self.selected_asset_id and self._dragged_box_orig and self._drag_start:
                scale, _, _ = self._get_transform_metrics()
                dx = int((pt.x() - self._drag_start.x()) / scale)
                dy = int((pt.y() - self._drag_start.y()) / scale)

                ox, oy, ow, oh = self._dragged_box_orig
                if self._active_handle == "move":
                    nx = max(0, min(self.img_w - ow, ox + dx))
                    ny = max(0, min(self.img_h - oh, oy + dy))
                    new_box = [nx, ny, ow, oh]
                elif self._active_handle == "br":
                    nw = max(20, min(self.img_w - ox, ow + dx))
                    nh = max(20, min(self.img_h - oy, oh + dy))
                    new_box = [ox, oy, nw, nh]
                elif self._active_handle == "tl":
                    nx = max(0, min(ox + ow - 20, ox + dx))
                    ny = max(0, min(oy + oh - 20, oy + dy))
                    nw = ow - (nx - ox)
                    nh = oh - (ny - oy)
                    new_box = [nx, ny, nw, nh]
                elif self._active_handle == "tr":
                    ny = max(0, min(oy + oh - 20, oy + dy))
                    nw = max(20, min(self.img_w - ox, ow + dx))
                    nh = oh - (ny - oy)
                    new_box = [ox, ny, nw, nh]
                elif self._active_handle == "bl":
                    nx = max(0, min(ox + ow - 20, ox + dx))
                    nw = ow - (nx - ox)
                    nh = max(20, min(self.img_h - oy, oh + dy))
                    new_box = [nx, oy, nw, nh]
                else:
                    new_box = [ox, oy, ow, oh]

                self.boxes[self.selected_asset_id]["orig_box"] = new_box
                self.boxes[self.selected_asset_id]["bbox"] = new_box
                self.update()
        else:
            if self.target_redraw_aid or self.mode in ("draw", "manual_box"):
                self.setCursor(Qt.CursorShape.CrossCursor)
            elif self.selected_asset_id and self.selected_asset_id in self.boxes:
                box = self.boxes[self.selected_asset_id].get("orig_box") or self.boxes[self.selected_asset_id].get("bbox", [0, 0, 0, 0])
                s_rect = self._img_to_screen_rect(box)
                h = self._hit_test_handle(s_rect, pt)
                if h in ("tl", "br"):
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif h in ("tr", "bl"):
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                elif _rect_contains(s_rect, pt):
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False

            if (self._active_handle == "draw" or self.target_redraw_aid or self.mode in ("draw", "manual_box")) and self._drag_start and self._drag_current:
                p1 = self._screen_to_img_point(self._drag_start)
                p2 = self._screen_to_img_point(self._drag_current)
                x1, x2 = min(p1[0], p2[0]), max(p1[0], p2[0])
                y1, y2 = min(p1[1], p2[1]), max(p1[1], p2[1])
                w = x2 - x1
                h = y2 - y1

                if w >= 12 and h >= 12:
                    new_box = [x1, y1, w, h]
                    if self.target_redraw_aid and self.target_redraw_aid in self.boxes:
                        # Specific element re-selection
                        aid = self.target_redraw_aid
                        self.boxes[aid]["orig_box"] = new_box
                        self.boxes[aid]["bbox"] = new_box
                        self.box_modified.emit(aid, new_box)
                        self.target_redraw_aid = None
                    else:
                        # Draw a brand new element box
                        self.new_box_created.emit(new_box)

            elif self._active_handle and self.selected_asset_id and self._dragged_box_orig:
                box = self.boxes[self.selected_asset_id].get("orig_box") or self.boxes[self.selected_asset_id].get("bbox")
                if box and box != self._dragged_box_orig:
                    self.box_modified.emit(self.selected_asset_id, box)

            self._active_handle = None
            self._drag_start = None
            self._drag_current = None
            self.update()

    def _hit_test_handle(self, s_rect: QRectF, pt: QPoint) -> Optional[str]:
        """Tests whether point is within resize handles of selected box."""
        margin = 8.0
        tl = s_rect.topLeft()
        tr = s_rect.topRight()
        bl = s_rect.bottomLeft()
        br = s_rect.bottomRight()

        if _rect_contains(QRectF(tl.x() - margin, tl.y() - margin, margin * 2, margin * 2), pt):
            return "tl"
        if _rect_contains(QRectF(tr.x() - margin, tr.y() - margin, margin * 2, margin * 2), pt):
            return "tr"
        if _rect_contains(QRectF(bl.x() - margin, bl.y() - margin, margin * 2, margin * 2), pt):
            return "bl"
        if _rect_contains(QRectF(br.x() - margin, br.y() - margin, margin * 2, margin * 2), pt):
            return "br"
        return None

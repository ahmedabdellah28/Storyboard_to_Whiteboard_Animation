"""
Add Box Creation Tool — Rubberband Drawing that directly creates first-class SceneObjects.
"""
import uuid
import numpy as np
from .base_tool import BaseCanvasTool
from engine.core.scene import SceneObject


class AddBoxTool(BaseCanvasTool):
    def __init__(self, canvas_view):
        super().__init__(canvas_view)
        self._touch_start_pos = (0, 0)
        self._touch_start_img = (0, 0)
        self._touch_curr_img = (0, 0)
        self._is_dragging = False

    def on_touch_down(self, touch, img_pt) -> bool:
        if not img_pt:
            return True
        ix, iy = img_pt
        self._touch_start_pos = (touch.x, touch.y)
        self._touch_start_img = (ix, iy)
        self._touch_curr_img = (ix, iy)
        self._is_dragging = False
        touch.grab(self.canvas_view)
        return True

    def on_touch_move(self, touch, img_pt) -> bool:
        if touch.grab_current is not self.canvas_view:
            return False

        dx = touch.x - self._touch_start_pos[0]
        dy = touch.y - self._touch_start_pos[1]
        if not self._is_dragging and np.hypot(dx, dy) >= 8.0:
            self._is_dragging = True

        if img_pt:
            self._touch_curr_img = img_pt
            if self._is_dragging:
                self._draw_in_progress_box()
        return True

    def on_touch_up(self, touch, img_pt) -> bool:
        if touch.grab_current is not self.canvas_view:
            return False

        touch.ungrab(self.canvas_view)
        self.canvas_view.in_progress_group.clear()

        if self._is_dragging:
            p1_x, p1_y = self._touch_start_img
            p2_x, p2_y = self._touch_curr_img
            bx = int(round(min(p1_x, p2_x)))
            by = int(round(min(p1_y, p2_y)))
            bw = int(round(abs(p2_x - p1_x)))
            bh = int(round(abs(p2_y - p1_y)))

            if bw >= 16 and bh >= 16:
                src_img = getattr(self.canvas_view.state, "source_image", None)
                ih, iw = (src_img.shape[:2]) if src_img is not None else (1080, 1920)
                bx = max(0, min(iw - 4, bx))
                by = max(0, min(ih - 4, by))
                bw = max(4, min(iw - bx, bw))
                bh = max(4, min(ih - by, bh))

                crop_img = None
                if src_img is not None:
                    crop_img = src_img[by:by+bh, bx:bx+bw].copy()

                panel_id = 1
                if self.canvas_view.state.project and getattr(self.canvas_view.state.project, "panels", None):
                    for p in self.canvas_view.state.project.panels:
                        px, py, pw, ph = getattr(p, "interior_bbox", None) or getattr(p, "bbox", (0,0,0,0))
                        if px <= bx + bw / 2.0 <= px + pw and py <= by + bh / 2.0 <= py + ph:
                            panel_id = p.id
                            break

                obj_count = len(self.canvas_view.state.objects) + 1
                is_storyboard = bool(self.canvas_view.state.project and getattr(self.canvas_view.state.project, "panels", None))
                name = f"Panel {panel_id} - Custom {obj_count}" if is_storyboard else f"Element {obj_count}"

                new_obj = SceneObject(
                    id=str(uuid.uuid4())[:8],
                    name=name,
                    bbox=(bx, by, bw, bh),
                    global_bbox=(bx, by, bw, bh),
                    panel_id=panel_id,
                    width=bw,
                    height=bh,
                    area=bw * bh,
                    crop=crop_img,
                    visibility=True
                )
                new_obj.scene_source_image = src_img

                self.canvas_view.state.add_object(new_obj, record_undo=True)
                self.canvas_view.set_tool("SELECT")

        self._is_dragging = False
        self.canvas_view.redraw_overlays()
        return True

    def _draw_in_progress_box(self):
        from kivy.graphics import Color, Line
        self.canvas_view.in_progress_group.clear()
        p1_x, p1_y = self._touch_start_img
        p2_x, p2_y = self._touch_curr_img
        bx = min(p1_x, p2_x)
        by = min(p1_y, p2_y)
        bw = abs(p2_x - p1_x)
        bh = abs(p2_y - p1_y)

        rect = self.canvas_view.image_to_widget_coords(bx, by, bw, bh)
        if rect:
            sx, sy, sw, sh = rect
            self.canvas_view.in_progress_group.add(Color(rgba=[0.0, 0.9, 1.0, 0.85]))
            self.canvas_view.in_progress_group.add(Line(rectangle=(sx, sy, sw, sh), width=2.0))

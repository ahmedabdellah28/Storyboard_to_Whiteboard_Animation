"""
Select & Direct Manipulation Tool — Handles Hit Testing, Corner Resize Handles, and Body Movement with Undo.
"""
import numpy as np
from kivy.metrics import dp
from .base_tool import BaseCanvasTool
from ui.state.commands import MoveOrResizeCommand


class SelectTool(BaseCanvasTool):
    def __init__(self, canvas_view):
        super().__init__(canvas_view)
        self._touch_start_pos = (0, 0)
        self._touch_start_img = (0, 0)
        self._touch_curr_img = (0, 0)
        self._is_dragging = False
        self._active_handle = None   # "TL", "TR", "BR", "BL" or None
        self._is_moving_body = False
        self._initial_bbox = None
        self._candidate_select_id = None

    def on_touch_down(self, touch, img_pt) -> bool:
        if not img_pt:
            if self.canvas_view.state:
                self.canvas_view.state.set_active_id(None)
            self.canvas_view.redraw_overlays()
            return True

        ix, iy = img_pt
        self._touch_start_pos = (touch.x, touch.y)
        self._touch_start_img = (ix, iy)
        self._touch_curr_img = (ix, iy)
        self._is_dragging = False
        self._active_handle = None
        self._is_moving_body = False
        self._candidate_select_id = None

        active_obj = self.canvas_view.state.active_object if self.canvas_view.state else None

        # 1. Check if touch hit any corner handle of active object
        if active_obj:
            bbox = active_obj.global_bbox or active_obj.bbox
            if bbox:
                rect = self.canvas_view.image_to_widget_coords(*bbox)
                if rect:
                    sx, sy, sw, sh = rect
                    handle_size = dp(14)
                    handles = {
                        "BL": (sx - handle_size/2, sy - handle_size/2),
                        "BR": (sx + sw - handle_size/2, sy - handle_size/2),
                        "TL": (sx - handle_size/2, sy + sh - handle_size/2),
                        "TR": (sx + sw - handle_size/2, sy + sh - handle_size/2)
                    }
                    for h_name, (hx, hy) in handles.items():
                        if hx <= touch.x <= hx + handle_size and hy <= touch.y <= hy + handle_size:
                            self._active_handle = h_name
                            self._initial_bbox = bbox
                            touch.grab(self.canvas_view)
                            return True

                # 2. Check if touch hit inside body of active object
                bx, by, bw, bh = bbox
                if bx <= ix <= bx + bw and by <= iy <= by + bh:
                    self._is_moving_body = True
                    self._initial_bbox = bbox
                    touch.grab(self.canvas_view)
                    return True

        # 3. Check if touch hit any other object
        objects = self.canvas_view.state.objects if self.canvas_view.state else []
        for obj in reversed(objects):
            bx, by, bw, bh = obj.global_bbox or obj.bbox
            if bx <= ix <= bx + bw and by <= iy <= by + bh:
                self._candidate_select_id = obj.id
                break

        touch.grab(self.canvas_view)
        return True

    def on_touch_move(self, touch, img_pt) -> bool:
        if touch.grab_current is not self.canvas_view:
            return False

        dx = touch.x - self._touch_start_pos[0]
        dy = touch.y - self._touch_start_pos[1]
        dist = np.hypot(dx, dy)

        if not self._is_dragging and dist >= 8.0:
            self._is_dragging = True

        if not img_pt:
            return True
        self._touch_curr_img = img_pt

        if self._is_dragging and self._active_handle and self._initial_bbox:
            # Resize active object
            p_orig_x, p_orig_y, p_orig_w, p_orig_h = self._initial_bbox
            d_img_x = self._touch_curr_img[0] - self._touch_start_img[0]
            d_img_y = self._touch_curr_img[1] - self._touch_start_img[1]

            nbx, nby, nbw, nbh = p_orig_x, p_orig_y, p_orig_w, p_orig_h
            if self._active_handle == "BR":
                nbw = max(16, p_orig_w + d_img_x)
                nbh = max(16, p_orig_h + d_img_y)
            elif self._active_handle == "BL":
                nbx = p_orig_x + d_img_x
                nbw = max(16, p_orig_w - d_img_x)
                nbh = max(16, p_orig_h + d_img_y)
            elif self._active_handle == "TR":
                nby = p_orig_y + d_img_y
                nbw = max(16, p_orig_w + d_img_x)
                nbh = max(16, p_orig_h - d_img_y)
            elif self._active_handle == "TL":
                nbx = p_orig_x + d_img_x
                nby = p_orig_y + d_img_y
                nbw = max(16, p_orig_w - d_img_x)
                nbh = max(16, p_orig_h - d_img_y)

            new_bbox = (int(round(nbx)), int(round(nby)), int(round(nbw)), int(round(nbh)))
            if self.canvas_view.state and self.canvas_view.state.active_object_id:
                self.canvas_view.state.update_object_bbox(self.canvas_view.state.active_object_id, new_bbox, record_undo=False)
            self.canvas_view.redraw_overlays()
            return True

        elif self._is_dragging and self._is_moving_body and self._initial_bbox:
            # Move active object
            p_orig_x, p_orig_y, p_orig_w, p_orig_h = self._initial_bbox
            d_img_x = self._touch_curr_img[0] - self._touch_start_img[0]
            d_img_y = self._touch_curr_img[1] - self._touch_start_img[1]

            new_bbox = (
                int(round(p_orig_x + d_img_x)),
                int(round(p_orig_y + d_img_y)),
                p_orig_w, p_orig_h
            )
            if self.canvas_view.state and self.canvas_view.state.active_object_id:
                self.canvas_view.state.update_object_bbox(self.canvas_view.state.active_object_id, new_bbox, record_undo=False)
            self.canvas_view.redraw_overlays()
            return True

        return True

    def on_touch_up(self, touch, img_pt) -> bool:
        if touch.grab_current is not self.canvas_view:
            return False

        touch.ungrab(self.canvas_view)

        # Case 1: Pure Click
        if not self._is_dragging:
            if self._candidate_select_id:
                self.canvas_view.state.set_active_id(self._candidate_select_id)
            elif not self._is_moving_body and not self._active_handle:
                self.canvas_view.state.set_active_id(None)
            self.canvas_view.redraw_overlays()
            return True

        # Case 2: Finalize Move / Resize with Undo
        if self._is_dragging and self._initial_bbox and self.canvas_view.state and self.canvas_view.state.active_object:
            final_bbox = self.canvas_view.state.active_object.global_bbox or self.canvas_view.state.active_object.bbox
            if final_bbox != self._initial_bbox:
                self.canvas_view.state.command_history.push(
                    MoveOrResizeCommand(self.canvas_view.state, self.canvas_view.state.active_object_id, self._initial_bbox, final_bbox)
                )

        self._is_dragging = False
        self._active_handle = None
        self._is_moving_body = False
        self._initial_bbox = None
        self.canvas_view.redraw_overlays()
        return True

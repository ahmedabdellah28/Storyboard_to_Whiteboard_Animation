"""
Select & Direct Manipulation Tool — Handles Hit Testing, Corner Resize Handles, Direction Arrow Toggle, and Body Movement.
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
        self._transient_bbox = None

    def _get_effective_bbox(self, obj):
        if not obj:
            return None
        if self.canvas_view.view_mode == "PANEL":
            return obj.bbox
        return obj.global_bbox or obj.bbox

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
        self._transient_bbox = None

        active_obj = self.canvas_view.state.active_object if self.canvas_view.state else None
        objects = self.canvas_view.state.objects if self.canvas_view.state else []
        current_panel_id = getattr(self.canvas_view.state, "active_panel_id", self.canvas_view.focused_panel_id)

        # 0. Check if touch hit Direction Arrow Badge of ANY visible text object (Active or Inactive)
        check_list = []
        if active_obj and getattr(active_obj, "visibility", True) and (self.canvas_view.view_mode != "PANEL" or getattr(active_obj, "panel_id", 1) == current_panel_id):
            check_list.append(active_obj)
        for o in reversed(objects):
            if o != active_obj and getattr(o, "visibility", True) and (self.canvas_view.view_mode != "PANEL" or getattr(o, "panel_id", 1) == current_panel_id):
                check_list.append(o)

        for obj in check_list:
            bbox = self._get_effective_bbox(obj)
            if not bbox:
                continue
            rect = self.canvas_view.image_to_widget_coords(*bbox)
            if not rect:
                continue
            sx, sy, sw, sh = rect
            is_act = (active_obj and obj.id == active_obj.id)

            # A. Check Priority Circle Badge on top-left (Direct Click to Toggle Sequence)
            badge_r = dp(10) if is_act else dp(8)
            badge_cx = sx + badge_r + dp(2)
            badge_cy = sy + sh - badge_r - dp(2)
            p_margin = dp(6)
            if (badge_cx - badge_r - p_margin) <= touch.x <= (badge_cx + badge_r + p_margin) and (badge_cy - badge_r - p_margin) <= touch.y <= (badge_cy + badge_r + p_margin):
                pid = getattr(obj, "panel_id", 1)
                is_assigned, new_p = self.canvas_view.state.toggle_panel_object_priority(pid, obj.id)
                if self.canvas_view.app and hasattr(self.canvas_view.app, "_show_toast"):
                    if is_assigned:
                        self.canvas_view.app._show_toast(f"Priority Assigned: #{new_p}")
                    else:
                        self.canvas_view.app._show_toast("Priority Cleared & Sequence Adjusted")
                self.canvas_view.redraw_overlays()
                return True

            # B. Check Direction Arrow Badge
            elem_type = getattr(obj, "element_type", "TEXT")
            direction = getattr(obj, "direction", "RTL")
            if elem_type in ("TEXT", "UNDERLINE") and direction in ("RTL", "LTR"):
                arr_w = dp(22) if is_act else dp(18)
                arr_h = dp(22) if is_act else dp(18)
                arr_x = sx + sw - arr_w - dp(2)
                arr_y = sy + sh - arr_h - dp(2)

                margin = dp(6)
                if (arr_x - margin) <= touch.x <= (arr_x + arr_w + margin) and (arr_y - margin) <= touch.y <= (arr_y + arr_h + margin):
                    # Direct Arrow Toggle: RTL <-> LTR
                    new_dir = "LTR" if direction == "RTL" else "RTL"
                    obj.direction = new_dir
                    self.canvas_view.state.set_active_id(obj.id)
                    if hasattr(self.canvas_view.state, "_notify_objects_changed"):
                        self.canvas_view.state._notify_objects_changed()
                    if self.canvas_view.app and hasattr(self.canvas_view.app, "_show_toast"):
                        dir_str = "RTL ⮜ (من اليمين لليسار)" if new_dir == "RTL" else "LTR ⮞ (من اليسار لليمين)"
                        self.canvas_view.app._show_toast(f"Writing Direction: {dir_str}")
                    self.canvas_view.redraw_overlays()
                    return True

        # 1. Check if touch hit corner handle of active object
        if active_obj and getattr(active_obj, "visibility", True):
            bbox = self._get_effective_bbox(active_obj)
            if bbox:
                rect = self.canvas_view.image_to_widget_coords(*bbox)
                if rect:
                    sx, sy, sw, sh = rect
                    handle_size = dp(16)
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

        # 3. Check if touch hit any candidate object
        for obj in reversed(objects):
            if not getattr(obj, "visibility", True):
                continue
            if self.canvas_view.view_mode == "PANEL" and getattr(obj, "panel_id", 1) != current_panel_id:
                continue
            bbox = self._get_effective_bbox(obj)
            if not bbox:
                continue
            bx, by, bw, bh = bbox
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

        if not self._is_dragging and dist >= 6.0:
            self._is_dragging = True

        if not img_pt:
            return True
        self._touch_curr_img = img_pt

        if self._is_dragging and self._active_handle and self._initial_bbox:
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
            self._transient_bbox = new_bbox
            self.canvas_view.redraw_overlays(transient_bbox=new_bbox)
            return True

        elif self._is_dragging and self._is_moving_body and self._initial_bbox:
            p_orig_x, p_orig_y, p_orig_w, p_orig_h = self._initial_bbox
            d_img_x = self._touch_curr_img[0] - self._touch_start_img[0]
            d_img_y = self._touch_curr_img[1] - self._touch_start_img[1]

            new_bbox = (
                int(round(p_orig_x + d_img_x)),
                int(round(p_orig_y + d_img_y)),
                p_orig_w, p_orig_h
            )
            self._transient_bbox = new_bbox
            self.canvas_view.redraw_overlays(transient_bbox=new_bbox)
            return True

        return True

    def on_touch_up(self, touch, img_pt) -> bool:
        if touch.grab_current is not self.canvas_view:
            return False

        touch.ungrab(self.canvas_view)

        # Case 1: Pure Click (Selection or Direction Toggle)
        if not self._is_dragging:
            if self._candidate_select_id:
                # If clicking on already-selected text object, toggle its writing direction (RTL <-> LTR)
                if self.canvas_view.state and self.canvas_view.state.active_object_id == self._candidate_select_id:
                    cand_obj = self.canvas_view.state.get_object_by_id(self._candidate_select_id)
                    if cand_obj and getattr(cand_obj, "element_type", "TEXT") in ("TEXT", "UNDERLINE"):
                        cur_dir = getattr(cand_obj, "direction", "RTL")
                        cand_obj.direction = "LTR" if cur_dir == "RTL" else "RTL"
                        if hasattr(self.canvas_view.state, "_notify_objects_changed"):
                            self.canvas_view.state._notify_objects_changed()
                        if self.canvas_view.app and hasattr(self.canvas_view.app, "_show_toast"):
                            dir_str = "RTL ⮜ (Right to Left)" if cand_obj.direction == "RTL" else "LTR ⮞ (Left to Right)"
                            self.canvas_view.app._show_toast(f"Text Direction: {dir_str}")
                else:
                    self.canvas_view.state.set_active_id(self._candidate_select_id)
            elif not self._is_moving_body and not self._active_handle:
                self.canvas_view.state.set_active_id(None)
            self.canvas_view.redraw_overlays()
            return True

        # Case 2: Finalize Move / Resize with Undo
        if self._is_dragging and self._transient_bbox and self._initial_bbox and self.canvas_view.state and self.canvas_view.state.active_object_id:
            if self._transient_bbox != self._initial_bbox:
                self.canvas_view.state.update_object_bbox(
                    self.canvas_view.state.active_object_id,
                    self._transient_bbox,
                    record_undo=True
                )

        self._is_dragging = False
        self._active_handle = None
        self._is_moving_body = False
        self._initial_bbox = None
        self._transient_bbox = None
        self.canvas_view.redraw_overlays()
        return True

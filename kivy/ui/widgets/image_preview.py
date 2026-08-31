"""
Interactive Studio Canvas (ImagePreview) — Direct Manipulation, Visual Handles & Toolbox.
Supports:
1. First-class Toolbox: Select [ ↖ ], Add Box [ ⛶ ], Pan [ ✋ ].
2. Direct Transform Handles (4 Corner Handles) on Active Object.
3. Strict Drag Threshold (8px) preventing Click vs Drag conflict.
4. Smooth Pan & Zoom Viewport.
5. In-App Video Playback Texture Engine.
"""
import os
import uuid
import cv2
import numpy as np
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle, InstructionGroup
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDRoundFlatButton, MDFillRoundFlatIconButton, MDFlatButton
from engine.core.scene import SceneObject
from ..theme import Theme


class ImagePreview(FloatLayout):
    """Studio Interactive Canvas with direct object manipulation and toolbox."""

    def __init__(self, app_ref=None, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.size_hint = (1, 1)

        # Pan & Zoom viewport state
        self.zoom_level = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0

        # Touch & Interaction state machine
        self._touch_start_pos = (0, 0)
        self._touch_start_img = (0, 0)
        self._touch_curr_img = (0, 0)
        self._is_dragging = False
        self._active_handle = None   # "TL", "TR", "BR", "BL" or None
        self._is_moving_body = False
        self._initial_bbox = None
        self._candidate_select_id = None

        # Video playback engine
        self._cap = None
        self._video_path = None
        self._video_clock = None
        self._is_playing = False
        self._total_frames = 0
        self._current_frame_idx = 0
        self._fps = 30.0
        self.on_video_frame_cb = None

        # Canvas Image Display
        self.img_widget = Image(
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0}
        )
        self.add_widget(self.img_widget)

        # Canvas Graphic Instruction Groups
        with self.canvas.after:
            self.overlay_group = InstructionGroup()
            self.in_progress_group = InstructionGroup()

        self.bind(pos=self._on_geometry_change, size=self._on_geometry_change)

        # ── Studio Canvas Floating Toolbox ──
        self.toolbox = MDBoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            size=(dp(290), dp(40)),
            pos_hint={"center_x": 0.5, "top": 0.98},
            padding=[dp(6), dp(4), dp(6), dp(4)],
            spacing=dp(6)
        )
        with self.toolbox.canvas.before:
            Color(rgba=[0.08, 0.10, 0.14, 0.92])
            self._tb_bg = RoundedRectangle(pos=self.toolbox.pos, size=self.toolbox.size, radius=[dp(20)])
            Color(rgba=Theme.BORDER)
            self._tb_border = Line(rounded_rectangle=(self.toolbox.x, self.toolbox.y, self.toolbox.width, self.toolbox.height, dp(20)), width=1.0)
        self.toolbox.bind(pos=self._update_toolbox_bg, size=self._update_toolbox_bg)

        # Tool 1: SELECT
        self.tool_select_btn = MDIconButton(
            icon="cursor-default",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_ACCENT,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._set_tool("SELECT")
        )
        self.toolbox.add_widget(self.tool_select_btn)

        # Tool 2: ADD BOX
        self.tool_add_btn = MDIconButton(
            icon="vector-rectangle",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._set_tool("ADD_BOX")
        )
        self.toolbox.add_widget(self.tool_add_btn)

        # Tool 3: PAN
        self.tool_pan_btn = MDIconButton(
            icon="hand-back-right-outline",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._set_tool("PAN")
        )
        self.toolbox.add_widget(self.tool_pan_btn)

        # Divider
        div = Widget(size_hint=(None, 1), width=dp(1))
        with div.canvas:
            Color(rgba=Theme.BORDER)
            self._div_rect = Rectangle(pos=div.pos, size=(dp(1), dp(24)))
        div.bind(pos=lambda *a: setattr(self._div_rect, 'pos', (div.x, div.y + dp(4))))
        self.toolbox.add_widget(div)

        # Zoom Fit button
        self.fit_btn = MDIconButton(
            icon="fit-to-screen-outline",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.reset_zoom()
        )
        self.toolbox.add_widget(self.fit_btn)

        # Zoom In / Out
        self.zoom_in_btn = MDIconButton(
            icon="magnify-plus-outline",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.adjust_zoom(1.2)
        )
        self.toolbox.add_widget(self.zoom_in_btn)

        self.zoom_out_btn = MDIconButton(
            icon="magnify-minus-outline",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.adjust_zoom(0.8)
        )
        self.toolbox.add_widget(self.zoom_out_btn)

        self.add_widget(self.toolbox)

    def _update_toolbox_bg(self, *args):
        self._tb_bg.pos = self.toolbox.pos
        self._tb_bg.size = self.toolbox.size
        self._tb_border.rounded_rectangle = (self.toolbox.x, self.toolbox.y, self.toolbox.width, self.toolbox.height, dp(20))

    def _set_tool(self, tool: str):
        if self.app and hasattr(self.app, "state"):
            self.app.state.set_active_tool(tool)
        self._update_tool_buttons(tool)

    def _update_tool_buttons(self, tool: str):
        self.tool_select_btn.icon_color = Theme.TEXT_ACCENT if tool == "SELECT" else Theme.TEXT_SECONDARY
        self.tool_add_btn.icon_color = Theme.TEXT_ACCENT if tool == "ADD_BOX" else Theme.TEXT_SECONDARY
        self.tool_pan_btn.icon_color = Theme.TEXT_ACCENT if tool == "PAN" else Theme.TEXT_SECONDARY

    def _on_geometry_change(self, *args):
        self.redraw_overlays()

    def set_image(self, img_path: str):
        self.stop_video()
        if os.path.exists(img_path):
            self.img_widget.source = img_path
            self.img_widget.reload()
            self.redraw_overlays()

    # ═════════════════════════════════════════════════════════════════════════
    #  Coordinate Transformation Math (Image Pixels <-> Screen Coordinates)
    # ═════════════════════════════════════════════════════════════════════════

    def _get_image_render_geometry(self):
        tex = self.img_widget.texture
        if not tex:
            return None

        if self.app and hasattr(self.app, "state") and self.app.state.source_image is not None and not self._is_playing and not self._cap:
            img_w = float(self.app.state.source_image.shape[1])
            img_h = float(self.app.state.source_image.shape[0])
        else:
            img_w = float(tex.width)
            img_h = float(tex.height)

        ww, wh = self.img_widget.size
        wx, wy = self.img_widget.pos

        base_scale = min(ww / max(1.0, img_w), wh / max(1.0, img_h))
        scale = base_scale * self.zoom_level
        disp_w = img_w * scale
        disp_h = img_h * scale

        off_x = wx + (ww - disp_w) / 2.0 + self.pan_offset_x
        off_y = wy + (wh - disp_h) / 2.0 + self.pan_offset_y

        return img_w, img_h, scale, off_x, off_y, disp_w, disp_h

    def widget_to_image_coords(self, wx: float, wy: float):
        geom = self._get_image_render_geometry()
        if not geom:
            return None
        img_w, img_h, scale, off_x, off_y, disp_w, disp_h = geom

        if off_x <= wx <= off_x + disp_w and off_y <= wy <= off_y + disp_h:
            ix = (wx - off_x) / scale
            iy = img_h - (wy - off_y) / scale
            return max(0.0, min(img_w, ix)), max(0.0, min(img_h, iy))
        return None

    def image_to_widget_coords(self, bx: float, by: float, bw: float, bh: float):
        geom = self._get_image_render_geometry()
        if not geom:
            return None
        img_w, img_h, scale, off_x, off_y, disp_w, disp_h = geom

        sx = off_x + bx * scale
        sy = off_y + (img_h - by - bh) * scale
        sw = max(2.0, bw * scale)
        sh = max(2.0, bh * scale)
        return sx, sy, sw, sh

    # ═════════════════════════════════════════════════════════════════════════
    #  Touch State Machine & Direct Manipulation
    # ═════════════════════════════════════════════════════════════════════════

    def on_touch_down(self, touch):
        if self.toolbox.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        img_pt = self.widget_to_image_coords(touch.x, touch.y)
        if not img_pt:
            # Clicked outside image bounds
            if self.app and hasattr(self.app, "state"):
                self.app.state.set_active_id(None)
            self.redraw_overlays()
            return True

        ix, iy = img_pt
        self._touch_start_pos = (touch.x, touch.y)
        self._touch_start_img = (ix, iy)
        self._touch_curr_img = (ix, iy)
        self._is_dragging = False
        self._active_handle = None
        self._is_moving_body = False
        self._candidate_select_id = None

        tool = self.app.state.active_tool if self.app and hasattr(self.app, "state") else "SELECT"

        if tool == "PAN":
            touch.grab(self)
            return True

        if tool == "ADD_BOX":
            touch.grab(self)
            return True

        # Tool is SELECT: Check handles & hit testing
        active_obj = self.app.state.active_object if self.app and hasattr(self.app, "state") else None

        # 1. Check if touch hit any corner handle of active object
        if active_obj:
            bbox = active_obj.global_bbox or active_obj.bbox
            if bbox:
                rect = self.image_to_widget_coords(*bbox)
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
                            touch.grab(self)
                            return True

                # 2. Check if touch hit inside body of active object
                bx, by, bw, bh = bbox
                if bx <= ix <= bx + bw and by <= iy <= by + bh:
                    self._is_moving_body = True
                    self._initial_bbox = bbox
                    touch.grab(self)
                    return True

        # 3. Check if touch hit any other object
        objects = self.app.state.objects if self.app and hasattr(self.app, "state") else []
        for obj in reversed(objects):
            bx, by, bw, bh = obj.global_bbox or obj.bbox
            if bx <= ix <= bx + bw and by <= iy <= by + bh:
                self._candidate_select_id = obj.id
                break

        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        dx = touch.x - self._touch_start_pos[0]
        dy = touch.y - self._touch_start_pos[1]
        dist = np.hypot(dx, dy)

        if not self._is_dragging and dist >= 8.0:
            self._is_dragging = True

        tool = self.app.state.active_tool if self.app and hasattr(self.app, "state") else "SELECT"

        if tool == "PAN":
            if self._is_dragging:
                self.pan_offset_x += touch.dx
                self.pan_offset_y += touch.dy
                self.redraw_overlays()
            return True

        img_pt = self.widget_to_image_coords(touch.x, touch.y)
        if not img_pt:
            return True
        self._touch_curr_img = img_pt

        if tool == "ADD_BOX":
            if self._is_dragging:
                self._draw_in_progress_box()
            return True

        # Tool == SELECT
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
            if self.app and hasattr(self.app, "state") and self.app.state.active_object_id:
                self.app.state.update_object_bbox(self.app.state.active_object_id, new_bbox, record_undo=False)
            self.redraw_overlays()
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
            if self.app and hasattr(self.app, "state") and self.app.state.active_object_id:
                self.app.state.update_object_bbox(self.app.state.active_object_id, new_bbox, record_undo=False)
            self.redraw_overlays()
            return True

        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)

        touch.ungrab(self)
        self.in_progress_group.clear()

        tool = self.app.state.active_tool if self.app and hasattr(self.app, "state") else "SELECT"

        # Case 1: Pure Click (Movement was below 8px threshold)
        if not self._is_dragging:
            if self._candidate_select_id:
                self.app.state.set_active_id(self._candidate_select_id)
            elif not self._is_moving_body and not self._active_handle:
                # Clicked blank area
                self.app.state.set_active_id(None)
            self.redraw_overlays()
            return True

        # Case 2: Dragging Add Box Tool Finished
        if tool == "ADD_BOX" and self._is_dragging:
            p1_x, p1_y = self._touch_start_img
            p2_x, p2_y = self._touch_curr_img
            bx = int(round(min(p1_x, p2_x)))
            by = int(round(min(p1_y, p2_y)))
            bw = int(round(abs(p2_x - p1_x)))
            bh = int(round(abs(p2_y - p1_y)))

            if bw >= 16 and bh >= 16:
                src_img = getattr(self.app.state, "source_image", None)
                ih, iw = (src_img.shape[:2]) if src_img is not None else (1080, 1920)
                bx = max(0, min(iw - 4, bx))
                by = max(0, min(ih - 4, by))
                bw = max(4, min(iw - bx, bw))
                bh = max(4, min(ih - by, bh))

                crop_img = None
                if src_img is not None:
                    crop_img = src_img[by:by+bh, bx:bx+bw].copy()

                panel_id = 1
                if self.app.state.project and getattr(self.app.state.project, "panels", None):
                    for p in self.app.state.project.panels:
                        px, py, pw, ph = getattr(p, "interior_bbox", None) or getattr(p, "bbox", (0,0,0,0))
                        if px <= bx + bw / 2.0 <= px + pw and py <= by + bh / 2.0 <= py + ph:
                            panel_id = p.id
                            break

                obj_count = len(self.app.state.objects) + 1
                is_storyboard = bool(self.app.state.project and getattr(self.app.state.project, "panels", None))
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

                self.app.state.add_object(new_obj, record_undo=True)
                self._set_tool("SELECT")

            self._is_dragging = False
            self.redraw_overlays()
            return True

        # Case 3: Finalize Move / Resize with Undo record
        if self._is_dragging and self._initial_bbox and self.app and hasattr(self.app, "state") and self.app.state.active_object:
            final_bbox = self.app.state.active_object.global_bbox or self.app.state.active_object.bbox
            if final_bbox != self._initial_bbox:
                from ..state.project_state import MoveOrResizeCommand
                self.app.state.command_history.push(
                    MoveOrResizeCommand(self.app.state, self.app.state.active_object_id, self._initial_bbox, final_bbox)
                )

        self._is_dragging = False
        self._active_handle = None
        self._is_moving_body = False
        self._initial_bbox = None
        self.redraw_overlays()
        return True

    def _draw_in_progress_box(self):
        self.in_progress_group.clear()
        p1_x, p1_y = self._touch_start_img
        p2_x, p2_y = self._touch_curr_img
        bx = min(p1_x, p2_x)
        by = min(p1_y, p2_y)
        bw = abs(p2_x - p1_x)
        bh = abs(p2_y - p1_y)

        rect = self.image_to_widget_coords(bx, by, bw, bh)
        if rect:
            sx, sy, sw, sh = rect
            self.in_progress_group.add(Color(rgba=[0.0, 0.9, 1.0, 0.85]))
            self.in_progress_group.add(Line(rectangle=(sx, sy, sw, sh), width=2.0))

    # ═════════════════════════════════════════════════════════════════════════
    #  Overlay Rendering (Active Transform Handles & Inactive Elements)
    # ═════════════════════════════════════════════════════════════════════════

    def redraw_overlays(self):
        self.overlay_group.clear()

        # Do not draw edit overlays during video preview
        if getattr(self, "_is_playing", False) or self._cap is not None:
            return

        if not self.app or not hasattr(self.app, "state"):
            return

        objects = self.app.state.objects
        active_id = self.app.state.active_object_id

        # 1. Draw Inactive Bounding Boxes
        for idx, obj in enumerate(objects):
            if obj.id == active_id:
                continue

            bbox = obj.global_bbox or obj.bbox
            if not bbox:
                continue
            rect = self.image_to_widget_coords(*bbox)
            if not rect:
                continue
            sx, sy, sw, sh = rect

            # Subtle outline
            self.overlay_group.add(Color(rgba=[0.486, 0.302, 1.0, 0.65]))
            self.overlay_group.add(Line(rectangle=(sx, sy, sw, sh), width=1.2))

            # Number badge
            badge_w, badge_h = dp(20), dp(18)
            badge_x = sx + dp(2)
            badge_y = sy + sh - badge_h - dp(2)
            self.overlay_group.add(Color(rgba=[0.10, 0.12, 0.18, 0.9]))
            self.overlay_group.add(RoundedRectangle(pos=(badge_x, badge_y), size=(badge_w, badge_h), radius=[dp(3)]))
            self.overlay_group.add(Color(rgba=Theme.TEXT_SECONDARY))
            self.overlay_group.add(Line(rounded_rectangle=(badge_x, badge_y, badge_w, badge_h, dp(3)), width=1.0))

        # 2. Draw Active Object Bounding Box + 4 Corner Transform Handles
        active_obj = self.app.state.get_object_by_id(active_id)
        if active_obj:
            bbox = active_obj.global_bbox or active_obj.bbox
            if bbox:
                rect = self.image_to_widget_coords(*bbox)
                if rect:
                    sx, sy, sw, sh = rect

                    # Prominent Accent Outline
                    self.overlay_group.add(Color(rgba=Theme.ACCENT_CYAN))
                    self.overlay_group.add(Line(rectangle=(sx, sy, sw, sh), width=2.4))

                    # 4 Corner Handles (8x8 dp squares)
                    handle_size = dp(10)
                    corners = [
                        (sx - handle_size/2, sy - handle_size/2),                    # BL
                        (sx + sw - handle_size/2, sy - handle_size/2),               # BR
                        (sx - handle_size/2, sy + sh - handle_size/2),              # TL
                        (sx + sw - handle_size/2, sy + sh - handle_size/2)           # TR
                    ]
                    for cx, cy in corners:
                        self.overlay_group.add(Color(rgba=[1.0, 1.0, 1.0, 1.0]))
                        self.overlay_group.add(Rectangle(pos=(cx, cy), size=(handle_size, handle_size)))
                        self.overlay_group.add(Color(rgba=Theme.ACCENT_CYAN))
                        self.overlay_group.add(Line(rectangle=(cx, cy, handle_size, handle_size), width=1.5))

                    # Top Badge Label
                    badge_w, badge_h = dp(24), dp(20)
                    badge_x = sx + dp(4)
                    badge_y = sy + sh - badge_h - dp(4)
                    self.overlay_group.add(Color(rgba=[0.0, 0.898, 1.0, 0.95]))
                    self.overlay_group.add(RoundedRectangle(pos=(badge_x, badge_y), size=(badge_w, badge_h), radius=[dp(4)]))

    # ═════════════════════════════════════════════════════════════════════════
    #  Pan & Zoom Controls
    # ═════════════════════════════════════════════════════════════════════════

    def adjust_zoom(self, factor: float):
        self.zoom_level = max(0.25, min(4.0, self.zoom_level * factor))
        self.redraw_overlays()

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.redraw_overlays()

    # ═════════════════════════════════════════════════════════════════════════
    #  In-App Video Playback Texture Engine
    # ═════════════════════════════════════════════════════════════════════════

    def play_video(self, video_path: str):
        if not os.path.exists(video_path):
            return
        self.stop_video()
        self._video_path = video_path
        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            return

        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._fps = float(self._cap.get(cv2.CAP_PROP_FPS)) or 30.0
        self._current_frame_idx = 0
        self._is_playing = True

        self.overlay_group.clear()
        self._video_clock = Clock.schedule_interval(self._tick_video_frame, 1.0 / self._fps)

    def _tick_video_frame(self, dt):
        if not self._cap or not self._is_playing:
            return

        ret, frame = self._cap.read()
        if not ret:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self._cap.read()
            if not ret:
                return

        self._current_frame_idx += 1
        h, w = frame.shape[:2]
        buf = cv2.flip(frame, 0).tobytes()
        tex = Texture.create(size=(w, h), colorfmt='bgr')
        tex.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.img_widget.texture = tex

        if self.on_video_frame_cb:
            pct = (self._current_frame_idx / float(max(1, self._total_frames)))
            self.on_video_frame_cb(pct, self._current_frame_idx, self._total_frames)

    def toggle_play_pause(self):
        self._is_playing = not self._is_playing

    def replay_video(self):
        if self._cap:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._current_frame_idx = 0
            self._is_playing = True

    def stop_video(self):
        if self._video_clock:
            self._video_clock.cancel()
            self._video_clock = None
        if self._cap:
            self._cap.release()
            self._cap = None
        self._is_playing = False

        if self.app and hasattr(self.app, "state") and self.app.state.source_image_path and os.path.exists(self.app.state.source_image_path):
            self.img_widget.source = self.app.state.source_image_path
            self.img_widget.reload()
        self.redraw_overlays()

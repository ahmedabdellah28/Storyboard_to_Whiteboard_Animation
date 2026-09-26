"""
Canvas View — Interactive Studio Canvas Presentation Widget.
Features:
1. Single-Panel Focused View vs Full Storyboard Sheet Toggle.
2. Interactive RTL / LTR Writing Direction Toggle Arrows.
3. Numbered & Color-Coded Priority Badges on Canvas Overlays.
4. Smooth Viewport Pan/Zoom and Direct Manipulation.
"""
import os
from typing import Optional, Tuple, Dict, Any
import cv2
import numpy as np

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle, Ellipse, InstructionGroup
# pyrefly: ignore [missing-import]
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton

from .viewport_controller import ViewportController
from .coordinate_transform import CoordinateTransformer
from .video_player import CanvasVideoPlayer
from .tools import SelectTool, AddBoxTool, PanTool, BaseCanvasTool
from ui.theme import Theme


class CanvasView(FloatLayout):
    def __init__(self, app_ref=None, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.size_hint = (1, 1)

        # 1. Viewport & Video Player Subsystems
        self.viewport = ViewportController()
        self.video_player = CanvasVideoPlayer(on_frame_update_cb=self._on_video_texture_update)
        self.view_mode = "PANEL" # "PANEL" (Single Panel Focus) or "FULL" (Full Storyboard Sheet)
        self.focused_panel_id = 1
        self._panel_texture = None

        # 2. Tools Subsystem
        self._tools = {
            "SELECT": SelectTool(self),
            "ADD_BOX": AddBoxTool(self),
            "PAN": PanTool(self)
        }

        # 3. Canvas Image Widget
        self.img_widget = Image(
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0}
        )
        self.add_widget(self.img_widget)

        # 4. Canvas Graphic Instruction Groups
        with self.canvas.after:
            self.overlay_group = InstructionGroup()
            self.in_progress_group = InstructionGroup()

        self.bind(pos=self._on_geometry_change, size=self._on_geometry_change)

        # 5. Floating Toolbox
        self._build_floating_toolbox()

    @property
    def state(self):
        return self.app.state if self.app and hasattr(self.app, "state") else None

    @property
    def zoom_level(self) -> float:
        return self.viewport.zoom_level

    @property
    def active_tool_instance(self) -> BaseCanvasTool:
        tool_name = self.state.active_tool if self.state else "SELECT"
        return self._tools.get(tool_name, self._tools["SELECT"])

    # ── Geometry & Coordinates ──

    def _get_geometry(self):
        tex = self.img_widget.texture
        if not tex:
            return None

        # Determine source image dimensions based on view mode
        src_shape = None
        if self.state and not self.video_player.has_video:
            if self.view_mode == "PANEL" and self.state.project and self.state.project.panels:
                p = self._get_current_panel()
                if p and getattr(p, "clean_crop", None) is not None:
                    src_shape = p.clean_crop.shape[:2]
            if src_shape is None and getattr(self.state, "source_image", None) is not None:
                src_shape = self.state.source_image.shape[:2]

        return CoordinateTransformer.get_image_render_geometry(
            tex_w=float(tex.width),
            tex_h=float(tex.height),
            widget_pos=self.img_widget.pos,
            widget_size=self.img_widget.size,
            zoom_level=self.viewport.zoom_level,
            pan_offset_x=self.viewport.pan_offset_x,
            pan_offset_y=self.viewport.pan_offset_y,
            source_image_shape=src_shape
        )

    def widget_to_image_coords(self, wx: float, wy: float) -> Optional[Tuple[float, float]]:
        return CoordinateTransformer.widget_to_image_coords(wx, wy, self._get_geometry())

    def image_to_widget_coords(self, bx: float, by: float, bw: float, bh: float) -> Optional[Tuple[float, float, float, float]]:
        return CoordinateTransformer.image_to_widget_coords(bx, by, bw, bh, self._get_geometry())

    def _on_geometry_change(self, *args):
        self.redraw_overlays()

    def _get_current_panel(self):
        if not self.state or not self.state.project or not self.state.project.panels:
            return None
        pid = getattr(self.state, "active_panel_id", self.focused_panel_id)
        for p in self.state.project.panels:
            if p.id == pid:
                return p
        return self.state.project.panels[0]

    def set_image(self, img_path: str):
        self.video_player.stop_video()
        if self.view_mode == "PANEL" and self.state and self.state.project and self.state.project.panels:
            self.set_focused_panel(getattr(self.state, "active_panel_id", 1))
        else:
            if os.path.exists(img_path):
                self.img_widget.source = img_path
                self.img_widget.reload()
                self.redraw_overlays()

    def set_focused_panel(self, panel_id: int):
        self.focused_panel_id = panel_id
        if self.state:
            self.state.active_panel_id = panel_id

        if self.view_mode == "PANEL" and self.state and self.state.project and self.state.project.panels:
            p = self._get_current_panel()
            if p:
                c_crop = getattr(p, "clean_crop", None)
                s_crop = getattr(p, "source_image", None)
                crop = c_crop if c_crop is not None else s_crop
                if crop is not None and crop.size > 0:
                    h, w = crop.shape[:2]
                    rgba_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGBA)
                    buf = np.ascontiguousarray(cv2.flip(rgba_crop, 0)).tobytes()
                    tex = Texture.create(size=(w, h), colorfmt='rgba')
                    tex.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
                    self.img_widget.source = ""
                    self.img_widget.texture = tex
                    self._panel_texture = tex
                    self.reset_zoom()
                    self.redraw_overlays()
                    return

        # Fallback to full image
        if self.state and self.state.source_image_path and os.path.exists(self.state.source_image_path):
            self.img_widget.source = self.state.source_image_path
            self.img_widget.reload()
        self.reset_zoom()
        self.redraw_overlays()

    def toggle_view_mode(self):
        """Toggle between Focused Panel and Full Sheet mode."""
        if self.view_mode == "PANEL":
            self.view_mode = "FULL"
            self.mode_btn.icon = "image-frame"
            if self.state and self.state.source_image_path and os.path.exists(self.state.source_image_path):
                self.img_widget.source = self.state.source_image_path
                self.img_widget.reload()
        else:
            self.view_mode = "PANEL"
            self.mode_btn.icon = "crop-free"
            self.set_focused_panel(getattr(self.state, "active_panel_id", 1))

        self.reset_zoom()
        self.redraw_overlays()
        mode_name = "Single Panel Focus" if self.view_mode == "PANEL" else "Full Storyboard Sheet"
        if self.app and hasattr(self.app, "_show_toast"):
            self.app._show_toast(f"View Mode: {mode_name}")

    # ── Zoom Controls ──

    def adjust_zoom(self, factor: float):
        self.viewport.adjust_zoom(factor)
        self.redraw_overlays()

    def reset_zoom(self):
        self.viewport.reset_zoom()
        self.redraw_overlays()

    # ── Video Playback Facade ──

    def play_video(self, video_path: str):
        self.overlay_group.clear()
        self.video_player.play_video(video_path)

    def stop_video(self):
        self.video_player.stop_video()
        if self.view_mode == "PANEL":
            self.set_focused_panel(getattr(self.state, "active_panel_id", 1))
        else:
            if self.state and self.state.source_image_path and os.path.exists(self.state.source_image_path):
                self.img_widget.source = self.state.source_image_path
                self.img_widget.reload()
        self.redraw_overlays()

    def toggle_play_pause(self):
        self.video_player.toggle_play_pause()

    def replay_video(self):
        self.video_player.replay_video()

    def _on_video_texture_update(self, texture):
        self.img_widget.texture = texture

    @property
    def _is_playing(self) -> bool:
        return self.video_player.is_playing

    @property
    def _cap(self):
        return self.video_player._cap

    @property
    def on_video_frame_cb(self):
        return self.video_player.on_progress_cb

    @on_video_frame_cb.setter
    def on_video_frame_cb(self, cb):
        self.video_player.on_progress_cb = cb

    # ── Touch Routing ──

    def on_touch_down(self, touch):
        if self.toolbox.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        img_pt = self.widget_to_image_coords(touch.x, touch.y)
        return self.active_tool_instance.on_touch_down(touch, img_pt)

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        img_pt = self.widget_to_image_coords(touch.x, touch.y)
        return self.active_tool_instance.on_touch_move(touch, img_pt)

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)

        img_pt = self.widget_to_image_coords(touch.x, touch.y)
        return self.active_tool_instance.on_touch_up(touch, img_pt)

    # ── Overlay Graphics Drawing ──

    def redraw_overlays(self, transient_bbox=None):
        self.overlay_group.clear()

        if self.video_player.has_video or not self.state:
            return

        all_objects = self.state.objects
        active_id = self.state.active_object_id
        current_panel_id = getattr(self.state, "active_panel_id", self.focused_panel_id)

        # Filter objects in Panel Focus mode
        if self.view_mode == "PANEL":
            objects_to_render = [o for o in all_objects if getattr(o, "panel_id", 1) == current_panel_id]
        else:
            objects_to_render = all_objects

        # 1. Inactive Elements (Boxes, Priority Badges, Direction Arrows)
        for idx, obj in enumerate(objects_to_render):
            if obj.id == active_id:
                continue

            if not getattr(obj, "visibility", True):
                continue

            bbox = obj.bbox if self.view_mode == "PANEL" else (obj.global_bbox or obj.bbox)
            if not bbox:
                continue
            rect = self.image_to_widget_coords(*bbox)
            if not rect:
                continue
            sx, sy, sw, sh = rect

            elem_type = getattr(obj, "element_type", "TEXT")
            direction = getattr(obj, "direction", "RTL")
            p_order = getattr(obj, "priority_order", idx + 1)
            p_color = Theme.get_priority_color(p_order)

            # Bounding Box Line
            self.overlay_group.add(Color(rgba=p_color))
            self.overlay_group.add(Line(rectangle=(sx, sy, sw, sh), width=1.2))

            # Numbered Priority Badge on Top-Left
            badge_r = dp(8)
            badge_cx = sx + badge_r + dp(2)
            badge_cy = sy + sh - badge_r - dp(2)
            self.overlay_group.add(Color(rgba=p_color))
            self.overlay_group.add(Ellipse(pos=(badge_cx - badge_r, badge_cy - badge_r), size=(badge_r * 2, badge_r * 2)))
            self.overlay_group.add(Color(rgba=[1.0, 1.0, 1.0, 0.6]))
            self.overlay_group.add(Line(circle=(badge_cx, badge_cy, badge_r), width=1.0))

            # Direction Arrow Badge for text elements
            if elem_type in ("TEXT", "UNDERLINE") and direction in ("RTL", "LTR"):
                arr_w, arr_h = dp(16), dp(16)
                arr_x = sx + sw - arr_w - dp(2)
                arr_y = sy + sh - arr_h - dp(2)

                self.overlay_group.add(Color(rgba=[0.08, 0.10, 0.15, 0.90]))
                self.overlay_group.add(RoundedRectangle(pos=(arr_x, arr_y), size=(arr_w, arr_h), radius=[dp(3)]))
                self.overlay_group.add(Color(rgba=p_color))
                self.overlay_group.add(Line(rounded_rectangle=(arr_x, arr_y, arr_w, arr_h, dp(3)), width=1.0))

                mid_y = arr_y + arr_h / 2.0
                if direction == "RTL":
                    # Left-pointing arrow ⮜
                    self.overlay_group.add(Line(points=[arr_x + arr_w - dp(3), mid_y, arr_x + dp(3), mid_y], width=1.4))
                    self.overlay_group.add(Line(points=[arr_x + dp(7), mid_y + dp(3), arr_x + dp(3), mid_y, arr_x + dp(7), mid_y - dp(3)], width=1.4))
                else:
                    # Right-pointing arrow ⮞
                    self.overlay_group.add(Line(points=[arr_x + dp(3), mid_y, arr_x + arr_w - dp(3), mid_y], width=1.4))
                    self.overlay_group.add(Line(points=[arr_x + arr_w - dp(7), mid_y + dp(3), arr_x + arr_w - dp(3), mid_y, arr_x + arr_w - dp(7), mid_y - dp(3)], width=1.4))

        # 2. Active Object
        active_obj = self.state.get_object_by_id(active_id)
        if active_obj and getattr(active_obj, "visibility", True):
            # Only draw active if in current view mode
            if self.view_mode != "PANEL" or getattr(active_obj, "panel_id", 1) == current_panel_id:
                if transient_bbox is not None:
                    bbox = transient_bbox
                else:
                    bbox = active_obj.bbox if self.view_mode == "PANEL" else (active_obj.global_bbox or active_obj.bbox)
                if bbox:
                    rect = self.image_to_widget_coords(*bbox)
                    if rect:
                        sx, sy, sw, sh = rect

                        # Cyan active selection outline
                        self.overlay_group.add(Color(rgba=Theme.ACCENT_CYAN))
                        self.overlay_group.add(Line(rectangle=(sx, sy, sw, sh), width=2.4))

                        # Active Corner Resize Handles
                        handle_size = dp(10)
                        corners = [
                            (sx - handle_size/2, sy - handle_size/2),
                            (sx + sw - handle_size/2, sy - handle_size/2),
                            (sx - handle_size/2, sy + sh - handle_size/2),
                            (sx + sw - handle_size/2, sy + sh - handle_size/2)
                        ]
                        for cx, cy in corners:
                            self.overlay_group.add(Color(rgba=[1.0, 1.0, 1.0, 1.0]))
                            self.overlay_group.add(Rectangle(pos=(cx, cy), size=(handle_size, handle_size)))
                            self.overlay_group.add(Color(rgba=Theme.ACCENT_CYAN))
                            self.overlay_group.add(Line(rectangle=(cx, cy, handle_size, handle_size), width=1.5))

                        # Active Numbered Priority Badge on Top-Left
                        p_order = getattr(active_obj, "priority_order", 1)
                        p_color = Theme.get_priority_color(p_order)
                        badge_r = dp(10)
                        badge_cx = sx + badge_r + dp(2)
                        badge_cy = sy + sh - badge_r - dp(2)
                        self.overlay_group.add(Color(rgba=p_color))
                        self.overlay_group.add(Ellipse(pos=(badge_cx - badge_r, badge_cy - badge_r), size=(badge_r * 2, badge_r * 2)))
                        self.overlay_group.add(Color(rgba=[1.0, 1.0, 1.0, 1.0]))
                        self.overlay_group.add(Line(circle=(badge_cx, badge_cy, badge_r), width=1.5))

                        # Active Direction Toggle Badge on Top-Right
                        elem_type = getattr(active_obj, "element_type", "TEXT")
                        direction = getattr(active_obj, "direction", "RTL")
                        if elem_type in ("TEXT", "UNDERLINE") and direction in ("RTL", "LTR"):
                            arr_w, arr_h = dp(20), dp(20)
                            arr_x = sx + sw - arr_w - dp(2)
                            arr_y = sy + sh - arr_h - dp(2)

                            self.overlay_group.add(Color(rgba=[0.0, 0.898, 1.0, 0.95]))
                            self.overlay_group.add(RoundedRectangle(pos=(arr_x, arr_y), size=(arr_w, arr_h), radius=[dp(4)]))
                            self.overlay_group.add(Color(rgba=[0.05, 0.05, 0.08, 1.0]))
                            mid_y = arr_y + arr_h / 2.0
                            if direction == "RTL":
                                self.overlay_group.add(Line(points=[arr_x + arr_w - dp(4), mid_y, arr_x + dp(4), mid_y], width=2.0))
                                self.overlay_group.add(Line(points=[arr_x + dp(9), mid_y + dp(4), arr_x + dp(4), mid_y, arr_x + dp(9), mid_y - dp(4)], width=2.0))
                            else:
                                self.overlay_group.add(Line(points=[arr_x + dp(4), mid_y, arr_x + arr_w - dp(4), mid_y], width=2.0))
                                self.overlay_group.add(Line(points=[arr_x + arr_w - dp(9), mid_y + dp(4), arr_x + arr_w - dp(4), mid_y, arr_x + arr_w - dp(9), mid_y - dp(4)], width=2.0))

    # ── Floating Toolbox UI ──

    def _build_floating_toolbox(self):
        self.toolbox = MDBoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            size=(dp(340), dp(40)),
            pos_hint={"center_x": 0.5, "top": 0.98},
            padding=[dp(6), dp(4), dp(6), dp(4)],
            spacing=dp(4)
        )
        with self.toolbox.canvas.before:
            Color(rgba=[0.08, 0.10, 0.14, 0.94])
            self._tb_bg = RoundedRectangle(pos=self.toolbox.pos, size=self.toolbox.size, radius=[dp(20)])
            Color(rgba=Theme.BORDER)
            self._tb_border = Line(width=1.0)
        self.toolbox.bind(pos=self._update_toolbox_bg, size=self._update_toolbox_bg)

        # Select Tool
        self.tool_select_btn = MDIconButton(
            icon="cursor-default",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_ACCENT,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.set_tool("SELECT")
        )
        self.toolbox.add_widget(self.tool_select_btn)

        # Add Box Tool
        self.tool_add_btn = MDIconButton(
            icon="vector-rectangle",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.set_tool("ADD_BOX")
        )
        self.toolbox.add_widget(self.tool_add_btn)

        # Pan Tool
        self.tool_pan_btn = MDIconButton(
            icon="hand-back-right-outline",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.set_tool("PAN")
        )
        self.toolbox.add_widget(self.tool_pan_btn)

        # Separator 1
        self.toolbox.add_widget(self._create_tool_sep())

        # Focus / Full Sheet Mode Toggle Button
        self.mode_btn = MDIconButton(
            icon="crop-free",
            theme_icon_color="Custom",
            icon_color=Theme.HEX_CYAN,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.toggle_view_mode()
        )
        self.toolbox.add_widget(self.mode_btn)

        # Separator 2
        self.toolbox.add_widget(self._create_tool_sep())

        # Zoom Fit
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

    def _create_tool_sep(self):
        div = Widget(size_hint=(None, 1), width=dp(1))
        with div.canvas:
            Color(rgba=Theme.BORDER)
            div_rect = Rectangle(pos=div.pos, size=(dp(1), dp(22)))
        div.bind(pos=lambda *a: setattr(div_rect, 'pos', (div.x, div.y + dp(5))))
        return div

    def _update_toolbox_bg(self, *args):
        self._tb_bg.pos = self.toolbox.pos
        self._tb_bg.size = self.toolbox.size
        if self.toolbox.width > dp(20) and self.toolbox.height > dp(20):
            self._tb_border.rounded_rectangle = (self.toolbox.x, self.toolbox.y, self.toolbox.width, self.toolbox.height, dp(20))

    def set_tool(self, tool: str):
        if self.state:
            self.state.set_active_tool(tool)
        self.tool_select_btn.icon_color = Theme.TEXT_ACCENT if tool == "SELECT" else Theme.TEXT_SECONDARY
        self.tool_add_btn.icon_color = Theme.TEXT_ACCENT if tool == "ADD_BOX" else Theme.TEXT_SECONDARY
        self.tool_pan_btn.icon_color = Theme.TEXT_ACCENT if tool == "PAN" else Theme.TEXT_SECONDARY

"""
Canvas View — Interactive Studio Canvas Presentation Widget.
"""
import os
from typing import Optional, Tuple
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle, InstructionGroup
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
        src_shape = getattr(self.state, "source_image", None).shape[:2] if (self.state and getattr(self.state, "source_image", None) is not None and not self.video_player.has_video) else None
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

    def set_image(self, img_path: str):
        self.video_player.stop_video()
        if os.path.exists(img_path):
            self.img_widget.source = img_path
            self.img_widget.reload()
            self.redraw_overlays()

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

    def redraw_overlays(self):
        self.overlay_group.clear()

        if self.video_player.has_video or not self.state:
            return

        objects = self.state.objects
        active_id = self.state.active_object_id

        # 1. Inactive Bounding Boxes
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

            self.overlay_group.add(Color(rgba=[0.486, 0.302, 1.0, 0.65]))
            self.overlay_group.add(Line(rectangle=(sx, sy, sw, sh), width=1.2))

            badge_w, badge_h = dp(20), dp(18)
            badge_x = sx + dp(2)
            badge_y = sy + sh - badge_h - dp(2)
            self.overlay_group.add(Color(rgba=[0.10, 0.12, 0.18, 0.9]))
            self.overlay_group.add(RoundedRectangle(pos=(badge_x, badge_y), size=(badge_w, badge_h), radius=[dp(3)]))
            self.overlay_group.add(Color(rgba=Theme.TEXT_SECONDARY))
            self.overlay_group.add(Line(rounded_rectangle=(badge_x, badge_y, badge_w, badge_h, dp(3)), width=1.0))

        # 2. Active Object + 4 Corner Handles
        active_obj = self.state.get_object_by_id(active_id)
        if active_obj:
            bbox = active_obj.global_bbox or active_obj.bbox
            if bbox:
                rect = self.image_to_widget_coords(*bbox)
                if rect:
                    sx, sy, sw, sh = rect

                    self.overlay_group.add(Color(rgba=Theme.ACCENT_CYAN))
                    self.overlay_group.add(Line(rectangle=(sx, sy, sw, sh), width=2.4))

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

                    badge_w, badge_h = dp(24), dp(20)
                    badge_x = sx + dp(4)
                    badge_y = sy + sh - badge_h - dp(4)
                    self.overlay_group.add(Color(rgba=[0.0, 0.898, 1.0, 0.95]))
                    self.overlay_group.add(RoundedRectangle(pos=(badge_x, badge_y), size=(badge_w, badge_h), radius=[dp(4)]))

    # ── Floating Toolbox UI ──

    def _build_floating_toolbox(self):
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

        div = Widget(size_hint=(None, 1), width=dp(1))
        with div.canvas:
            Color(rgba=Theme.BORDER)
            self._div_rect = Rectangle(pos=div.pos, size=(dp(1), dp(24)))
        div.bind(pos=lambda *a: setattr(self._div_rect, 'pos', (div.x, div.y + dp(4))))
        self.toolbox.add_widget(div)

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

    def _update_toolbox_bg(self, *args):
        self._tb_bg.pos = self.toolbox.pos
        self._tb_bg.size = self.toolbox.size
        self._tb_border.rounded_rectangle = (self.toolbox.x, self.toolbox.y, self.toolbox.width, self.toolbox.height, dp(20))

    def set_tool(self, tool: str):
        if self.state:
            self.state.set_active_tool(tool)
        self.tool_select_btn.icon_color = Theme.TEXT_ACCENT if tool == "SELECT" else Theme.TEXT_SECONDARY
        self.tool_add_btn.icon_color = Theme.TEXT_ACCENT if tool == "ADD_BOX" else Theme.TEXT_SECONDARY
        self.tool_pan_btn.icon_color = Theme.TEXT_ACCENT if tool == "PAN" else Theme.TEXT_SECONDARY

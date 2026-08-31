import os
import cv2
import numpy as np
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.slider import Slider
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDRoundFlatIconButton, MDFillRoundFlatIconButton
from kivymd.uix.label import MDLabel
from ..theme import StudioTheme


class ViewportCanvas(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.show_bboxes = True
        self.show_camera_frame = True
        self.show_safe_area = False
        self.selected_object = None
        self.current_camera_shot = None
        self.native_w = 1920
        self.native_h = 1080

        self.img_display = Image(
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1)
        )
        self.add_widget(self.img_display)

        with self.canvas.after:
            self.overlay_color = Color(rgba=[0, 0, 0, 0])
            self.bbox_line = Line(rectangle=(0, 0, 0, 0), width=2)
            self.cam_color = Color(rgba=[0, 0, 0, 0])
            self.cam_line = Line(rectangle=(0, 0, 0, 0), width=2)
            self.safe_color = Color(rgba=[0, 0, 0, 0])
            self.safe_line = Line(rectangle=(0, 0, 0, 0), width=1, dash_offset=5, dash_length=5)

        self.bind(pos=self._redraw_overlays, size=self._redraw_overlays)

    def set_image(self, img_path: str):
        if os.path.exists(img_path):
            self.img_display.source = img_path
            self.img_display.reload()
            self._redraw_overlays()

    def set_frame_texture(self, frame_bgr: np.ndarray):
        h, w = frame_bgr.shape[:2]
        buf = cv2.flip(frame_bgr, 0).tobytes()
        tex = Texture.create(size=(w, h), colorfmt='bgr')
        tex.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.img_display.texture = tex
        self._redraw_overlays()

    def set_selection(self, obj):
        self.selected_object = obj
        self._redraw_overlays()

    def set_camera_shot(self, shot):
        self.current_camera_shot = shot
        self._redraw_overlays()

    def _redraw_overlays(self, *args):
        if not self.img_display.texture:
            self.overlay_color.rgba = [0, 0, 0, 0]
            self.cam_color.rgba = [0, 0, 0, 0]
            self.safe_color.rgba = [0, 0, 0, 0]
            return

        tex_w, tex_h = self.img_display.texture_size
        view_w, view_h = self.size
        scale = min(view_w / max(1, tex_w), view_h / max(1, tex_h))

        draw_w = tex_w * scale
        draw_h = tex_h * scale
        draw_x = self.x + (view_w - draw_w) / 2.0
        draw_y = self.y + (view_h - draw_h) / 2.0

        # 1. Bounding Box Overlay
        if self.show_bboxes and self.selected_object and not self.selected_object.is_frame:
            bx, by, bw, bh = self.selected_object.bbox
            sx = draw_x + (bx / float(self.native_w)) * draw_w
            sy = draw_y + ((self.native_h - (by + bh)) / float(self.native_h)) * draw_h
            sw = (bw / float(self.native_w)) * draw_w
            sh = (bh / float(self.native_h)) * draw_h

            self.overlay_color.rgba = [0.49, 0.30, 1.0, 0.9]
            self.bbox_line.rectangle = (sx, sy, sw, sh)
        else:
            self.overlay_color.rgba = [0, 0, 0, 0]

        # 2. Camera Frame Overlay
        if self.show_camera_frame and self.current_camera_shot:
            cx, cy = self.current_camera_shot.target_center
            zoom = max(1.0, self.current_camera_shot.zoom)
            vp_w = self.native_w / zoom
            vp_h = self.native_h / zoom
            vx = cx - vp_w / 2.0
            vy = cy - vp_h / 2.0

            sx = draw_x + (vx / float(self.native_w)) * draw_w
            sy = draw_y + ((self.native_h - (vy + vp_h)) / float(self.native_h)) * draw_h
            sw = (vp_w / float(self.native_w)) * draw_w
            sh = (vp_h / float(self.native_h)) * draw_h

            self.cam_color.rgba = [0.0, 0.90, 1.0, 0.75]
            self.cam_line.rectangle = (sx, sy, sw, sh)
        else:
            self.cam_color.rgba = [0, 0, 0, 0]

        # 3. Safe Area Overlay
        if self.show_safe_area:
            margin = 0.10
            sx = draw_x + draw_w * margin
            sy = draw_y + draw_h * margin
            sw = draw_w * (1.0 - 2.0 * margin)
            sh = draw_h * (1.0 - 2.0 * margin)
            self.safe_color.rgba = [1.0, 0.70, 0.0, 0.5]
            self.safe_line.rectangle = (sx, sy, sw, sh)
        else:
            self.safe_color.rgba = [0, 0, 0, 0]


class PreviewViewport(MDBoxLayout):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.orientation = "vertical"
        self.padding = [dp(8), dp(8), dp(8), dp(8)]
        self.spacing = dp(8)
        self.md_bg_color = StudioTheme.BG_ROOT

        self.is_playing = False
        self.current_time = 0.0
        self.total_duration = 12.0

        self._build_ui()

    def _build_ui(self):
        # 1. Overlay Controls Header Toolbar
        top_bar = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            padding=[dp(8), dp(4), dp(8), dp(4)],
            spacing=dp(8)
        )

        self.btn_bbox = MDRoundFlatIconButton(
            text="BBoxes",
            icon="crop",
            font_size=sp(12),
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            theme_icon_color="Custom",
            icon_color=StudioTheme.ACCENT_PRIMARY,
            line_color=StudioTheme.BORDER_FOCUSED,
            on_release=self._toggle_bboxes
        )
        self.btn_cam = MDRoundFlatIconButton(
            text="Camera Frame",
            icon="video-outline",
            font_size=sp(12),
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            theme_icon_color="Custom",
            icon_color=StudioTheme.ACCENT_SECONDARY,
            line_color=StudioTheme.BORDER_CAMERA,
            on_release=self._toggle_camera_frame
        )
        self.btn_safe = MDRoundFlatIconButton(
            text="Safe Area",
            icon="aspect-ratio",
            font_size=sp(12),
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_SECONDARY,
            theme_icon_color="Custom",
            icon_color=StudioTheme.TEXT_SECONDARY,
            line_color=StudioTheme.BORDER_SUBTLE,
            on_release=self._toggle_safe_area
        )

        top_bar.add_widget(self.btn_bbox)
        top_bar.add_widget(self.btn_cam)
        top_bar.add_widget(self.btn_safe)
        top_bar.add_widget(BoxLayout()) # spacer

        self.res_lbl = MDLabel(
            text="1920×1080 • 30 FPS",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_MUTED,
            adaptive_width=True
        )
        top_bar.add_widget(self.res_lbl)
        self.add_widget(top_bar)

        # 2. Main Viewport Canvas
        self.viewport_canvas = ViewportCanvas(size_hint=(1, 1))
        self.add_widget(self.viewport_canvas)

        # 3. Transport Controls Bar
        transport_box = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            padding=[dp(12), dp(6), dp(12), dp(6)],
            spacing=dp(10),
            md_bg_color=StudioTheme.BG_PANEL
        )

        # Jump Start
        btn_start = MDIconButton(
            icon="skip-backward",
            theme_icon_color="Custom",
            icon_color=StudioTheme.TEXT_SECONDARY,
            on_release=lambda x: self.seek_to(0.0)
        )
        # Step back 1s
        btn_back = MDIconButton(
            icon="rewind-5",
            theme_icon_color="Custom",
            icon_color=StudioTheme.TEXT_SECONDARY,
            on_release=lambda x: self.seek_by(-1.0)
        )
        # Play / Pause
        self.btn_play = MDIconButton(
            icon="play-circle",
            theme_icon_color="Custom",
            icon_color=StudioTheme.ACCENT_PRIMARY,
            icon_size=sp(32),
            on_release=self._toggle_play
        )
        # Step forward 1s
        btn_fwd = MDIconButton(
            icon="fast-forward-5",
            theme_icon_color="Custom",
            icon_color=StudioTheme.TEXT_SECONDARY,
            on_release=lambda x: self.seek_by(1.0)
        )
        # Jump End
        btn_end = MDIconButton(
            icon="skip-forward",
            theme_icon_color="Custom",
            icon_color=StudioTheme.TEXT_SECONDARY,
            on_release=lambda x: self.seek_to(self.total_duration)
        )

        transport_box.add_widget(btn_start)
        transport_box.add_widget(btn_back)
        transport_box.add_widget(self.btn_play)
        transport_box.add_widget(btn_fwd)
        transport_box.add_widget(btn_end)

        # Timeline Scrubber Slider
        self.scrubber = Slider(
            min=0.0,
            max=12.0,
            value=0.0,
            step=0.05,
            size_hint_x=1.0,
            value_track=True,
            value_track_color=[0.49, 0.30, 1.0, 1.0]
        )
        self.scrubber.bind(value=self._on_scrub)
        transport_box.add_widget(self.scrubber)

        # Timestamp Counter
        self.time_lbl = MDLabel(
            text="00:00.0 / 00:12.0",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            adaptive_width=True,
            bold=True
        )
        transport_box.add_widget(self.time_lbl)

        self.add_widget(transport_box)

    def _toggle_bboxes(self, *args):
        self.viewport_canvas.show_bboxes = not self.viewport_canvas.show_bboxes
        self.btn_bbox.line_color = StudioTheme.BORDER_FOCUSED if self.viewport_canvas.show_bboxes else StudioTheme.BORDER_SUBTLE
        self.viewport_canvas._redraw_overlays()

    def _toggle_camera_frame(self, *args):
        self.viewport_canvas.show_camera_frame = not self.viewport_canvas.show_camera_frame
        self.btn_cam.line_color = StudioTheme.BORDER_CAMERA if self.viewport_canvas.show_camera_frame else StudioTheme.BORDER_SUBTLE
        self.viewport_canvas._redraw_overlays()

    def _toggle_safe_area(self, *args):
        self.viewport_canvas.show_safe_area = not self.viewport_canvas.show_safe_area
        self.btn_safe.line_color = StudioTheme.ACCENT_WARNING if self.viewport_canvas.show_safe_area else StudioTheme.BORDER_SUBTLE
        self.viewport_canvas._redraw_overlays()

    def _toggle_play(self, *args):
        self.is_playing = not self.is_playing
        self.btn_play.icon = "pause-circle" if self.is_playing else "play-circle"
        if self.app:
            self.app.on_playback_toggle(self.is_playing)

    def _on_scrub(self, instance, value):
        self.current_time = float(value)
        mins = int(self.current_time // 60)
        secs = self.current_time % 60
        tot_mins = int(self.total_duration // 60)
        tot_secs = self.total_duration % 60
        self.time_lbl.text = f"{mins:02d}:{secs:04.1f} / {tot_mins:02d}:{tot_secs:04.1f}"
        if self.app:
            self.app.on_timeline_seek(self.current_time)

    def seek_to(self, t: float):
        self.scrubber.value = max(0.0, min(self.total_duration, t))

    def seek_by(self, delta: float):
        self.seek_to(self.current_time + delta)

    def set_duration(self, dur: float):
        self.total_duration = max(1.0, dur)
        self.scrubber.max = self.total_duration
        self._on_scrub(None, self.scrubber.value)

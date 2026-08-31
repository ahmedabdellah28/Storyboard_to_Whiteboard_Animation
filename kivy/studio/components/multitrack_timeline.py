from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp, sp
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from ..theme import StudioTheme


class TimelineCanvas(Widget):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.total_duration = 12.4
        self.current_time = 0.0
        self.shots = []
        self.objects = []

        self.bind(pos=self.redraw, size=self.redraw)

    def set_data(self, shots, objects, total_dur):
        self.shots = shots
        self.objects = [o for o in objects if not o.is_frame]
        self.total_duration = max(1.0, total_dur)
        self.redraw()

    def set_playhead(self, t: float):
        self.current_time = max(0.0, min(self.total_duration, t))
        self.redraw()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._handle_scrub(touch.x)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self._handle_scrub(touch.x)
            return True
        return super().on_touch_move(touch)

    def _handle_scrub(self, touch_x):
        track_left = self.x + dp(80)
        track_w = self.width - dp(90)
        if track_w <= 0:
            return
        t_norm = max(0.0, min(1.0, (touch_x - track_left) / track_w))
        target_t = t_norm * self.total_duration
        self.set_playhead(target_t)
        if self.app:
            self.app.on_timeline_seek(target_t)

    def redraw(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return

        with self.canvas:
            # 1. Background
            Color(rgba=[0.086, 0.098, 0.125, 1])
            Rectangle(pos=self.pos, size=self.size)

            track_left = self.x + dp(80)
            track_w = max(10.0, self.width - dp(90))
            dur = max(1.0, self.total_duration)

            # Track heights
            row_h = dp(24)
            spacing = dp(6)
            y_ruler = self.top - dp(22)
            y_cam = y_ruler - row_h - spacing
            y_obj = y_cam - row_h - spacing
            y_elm = y_obj - row_h - spacing

            # 2. Time Ruler
            Color(rgba=[0.38, 0.41, 0.47, 0.8])
            step = 1.0 if dur <= 15.0 else 2.0
            t_curr = 0.0
            while t_curr <= dur:
                x_pos = track_left + (t_curr / dur) * track_w
                Line(points=[x_pos, y_ruler - dp(4), x_pos, y_ruler + dp(8)], width=1)
                t_curr += step

            # 3. Track 1: Camera Shots
            Color(rgba=[0.10, 0.18, 0.23, 1])
            RoundedRectangle(pos=(track_left, y_cam), size=(track_w, row_h), radius=[dp(4)])
            for idx, shot in enumerate(self.shots):
                x1 = track_left + (shot.start_time / dur) * track_w
                x2 = track_left + (shot.end_time / dur) * track_w
                w = max(dp(2), x2 - x1)
                if "FOCUS" in shot.shot_name:
                    Color(rgba=[0.0, 0.69, 1.0, 0.85]) # Cyan
                elif "TRANSITION" in shot.shot_name:
                    Color(rgba=[0.0, 0.45, 0.75, 0.6])
                else:
                    Color(rgba=[0.2, 0.35, 0.45, 0.8])
                RoundedRectangle(pos=(x1, y_cam), size=(w, row_h), radius=[dp(3)])

            # 4. Track 2: Major Objects
            Color(rgba=[0.17, 0.12, 0.23, 1])
            RoundedRectangle(pos=(track_left, y_obj), size=(track_w, row_h), radius=[dp(4)])
            for idx, obj in enumerate(self.objects):
                x1 = track_left + (obj.animation_start / dur) * track_w
                x2 = track_left + (obj.animation_end / dur) * track_w
                w = max(dp(2), x2 - x1)
                Color(rgba=[0.49, 0.30, 1.0, 0.85]) # Violet
                RoundedRectangle(pos=(x1, y_obj), size=(w, row_h), radius=[dp(3)])

            # 5. Track 3: Fills & Elements
            Color(rgba=[0.12, 0.18, 0.15, 1])
            RoundedRectangle(pos=(track_left, y_elm), size=(track_w, row_h), radius=[dp(4)])
            for idx, obj in enumerate(self.objects):
                fill_start = obj.animation_start + obj.duration * 0.55
                fill_end = obj.animation_start + obj.duration * 0.90
                x1 = track_left + (fill_start / dur) * track_w
                x2 = track_left + (fill_end / dur) * track_w
                w = max(dp(2), x2 - x1)
                Color(rgba=[0.0, 0.90, 0.46, 0.85]) # Neon Green
                RoundedRectangle(pos=(x1, y_elm), size=(w, row_h), radius=[dp(3)])

            # 6. Playhead Scrubber Cursor
            playhead_x = track_left + (self.current_time / dur) * track_w
            Color(rgba=[1.0, 0.32, 0.32, 1.0]) # Red Playhead
            Line(points=[playhead_x, self.y + dp(4), playhead_x, self.top - dp(4)], width=2)
            # Playhead head icon
            RoundedRectangle(pos=(playhead_x - dp(4), self.top - dp(14)), size=(dp(8), dp(10)), radius=[dp(2)])


class MultiTrackTimeline(MDBoxLayout):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(StudioTheme.TIMELINE_HEIGHT)
        self.padding = [dp(8), dp(6), dp(8), dp(6)]
        self.spacing = dp(6)
        self.md_bg_color = StudioTheme.BG_PANEL

        with self.canvas.before:
            Color(rgba=[0.086, 0.098, 0.125, 1])
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(rgba=[0.15, 0.17, 0.22, 1])
            self.border_top = Rectangle(pos=(self.x, self.top - dp(1)), size=(self.width, dp(1)))

        self.bind(pos=self._update_canvas, size=self._update_canvas)

        self._build_ui()

    def _update_canvas(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_top.pos = (self.x, self.top - dp(1))
        self.border_top.size = (self.width, dp(1))

    def _build_ui(self):
        # Left Track Headers Box
        labels_box = MDBoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(74),
            spacing=dp(6),
            padding=[dp(4), dp(18), dp(4), dp(4)]
        )
        lbl_cam = MDLabel(
            text="CAM",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_SECONDARY,
            bold=True,
            adaptive_height=True
        )
        lbl_obj = MDLabel(
            text="OBJECTS",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_PRIMARY,
            bold=True,
            adaptive_height=True
        )
        lbl_elm = MDLabel(
            text="FILLS",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_SUCCESS,
            bold=True,
            adaptive_height=True
        )
        labels_box.add_widget(lbl_cam)
        labels_box.add_widget(lbl_obj)
        labels_box.add_widget(lbl_elm)
        self.add_widget(labels_box)

        # Timeline Canvas
        self.timeline_canvas = TimelineCanvas(self.app, size_hint=(1, 1))
        self.add_widget(self.timeline_canvas)

    def update_timeline_data(self, shots, objects, total_dur):
        self.timeline_canvas.set_data(shots, objects, total_dur)

    def set_playhead(self, t: float):
        self.timeline_canvas.set_playhead(t)

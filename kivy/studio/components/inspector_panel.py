from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.switch import Switch
from kivy.metrics import dp, sp
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRoundFlatIconButton, MDIconButton, MDRoundFlatButton, MDFillRoundFlatIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from ..theme import StudioTheme


class CameraShotItem(MDCard):
    def __init__(self, shot, index, on_click_cb, **kwargs):
        super().__init__(**kwargs)
        self.shot = shot
        self.index = index
        self.on_click_cb = on_click_cb
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(46)
        self.padding = [dp(10), dp(4), dp(10), dp(4)]
        self.spacing = dp(8)
        self.radius = [dp(6)]
        self.md_bg_color = StudioTheme.BG_CARD
        self.line_color = StudioTheme.BORDER_SUBTLE

        self._build_ui()

    def _build_ui(self):
        icon_name = "video-outline"
        if "FOCUS" in self.shot.shot_name:
            icon_name = "target"
        elif "TRANSITION" in self.shot.shot_name:
            icon_name = "ray-start-arrow"
        elif "WIDE" in self.shot.shot_name:
            icon_name = "panorama-horizontal"

        icon = MDIconButton(
            icon=icon_name,
            theme_icon_color="Custom",
            icon_color=StudioTheme.ACCENT_SECONDARY,
            icon_size=sp(18),
            size_hint=(None, None),
            size=(dp(24), dp(24))
        )
        self.add_widget(icon)

        # Label & Time
        text_box = MDBoxLayout(orientation="vertical", spacing=dp(1))
        shot_title = self.shot.shot_name.replace("TRANSITION_TO_", "→ ").replace("FOCUS_", "● ")
        lbl_title = MDLabel(
            text=f"{self.index+1:02d}  {shot_title[:20]}",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            bold=True,
            adaptive_height=True
        )
        dur = self.shot.end_time - self.shot.start_time
        lbl_time = MDLabel(
            text=f"{self.shot.start_time:.1f}s – {self.shot.end_time:.1f}s ({dur:.1f}s) • Z:{self.shot.zoom:.2f}",
            font_style="Overline",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_SECONDARY,
            adaptive_height=True
        )
        text_box.add_widget(lbl_title)
        text_box.add_widget(lbl_time)
        self.add_widget(text_box)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.on_click_cb(self.shot)
            return True
        return super().on_touch_down(touch)


class InspectorPanel(MDBoxLayout):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.orientation = "vertical"
        self.size_hint_x = None
        self.width = dp(StudioTheme.SIDE_PANEL_WIDTH + 20)
        self.padding = [dp(12), dp(12), dp(12), dp(12)]
        self.spacing = dp(10)
        self.md_bg_color = StudioTheme.BG_PANEL

        with self.canvas.before:
            Color(rgba=[0.086, 0.098, 0.125, 1])
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(rgba=[0.15, 0.17, 0.22, 1])
            self.border_left = Rectangle(pos=self.pos, size=(dp(1), self.height))

        self.bind(pos=self._update_canvas, size=self._update_canvas)

        self.selected_object = None
        self.current_shots = []
        self.active_tab = "OBJECT"
        self.current_zoom = 1.40

        self._build_ui()

    def _update_canvas(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_left.pos = self.pos
        self.border_left.size = (dp(1), self.height)

    def _build_ui(self):
        # 1. Primary Action: Animate Selected Button
        self.btn_animate_selected = MDFillRoundFlatIconButton(
            text="Animate Selected Scene",
            icon="play-circle-outline",
            theme_text_color="Custom",
            text_color="#FFFFFF",
            theme_icon_color="Custom",
            icon_color="#FFFFFF",
            md_bg_color=StudioTheme.ACCENT_PRIMARY,
            font_size=sp(13),
            size_hint_x=1.0,
            on_release=self._on_animate_selected_clicked
        )
        self.add_widget(self.btn_animate_selected)

        # 2. Tab Switcher (Object / Camera)
        tab_bar = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(6)
        )
        self.btn_tab_obj = MDRoundFlatButton(
            text="OBJECT",
            size_hint_x=0.5,
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            line_color=StudioTheme.BORDER_FOCUSED,
            on_release=lambda x: self._switch_tab("OBJECT")
        )
        self.btn_tab_cam = MDRoundFlatButton(
            text="CAMERA & ZOOM",
            size_hint_x=0.5,
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_SECONDARY,
            line_color=StudioTheme.BORDER_SUBTLE,
            on_release=lambda x: self._switch_tab("CAMERA")
        )
        tab_bar.add_widget(self.btn_tab_obj)
        tab_bar.add_widget(self.btn_tab_cam)
        self.add_widget(tab_bar)

        # 3. Scrollable Body
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.content_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            adaptive_height=True
        )
        self.scroll.add_widget(self.content_box)
        self.add_widget(self.scroll)

        self._render_object_tab()

    def _on_animate_selected_clicked(self, *args):
        if self.app:
            self.app.animate_selected_scene(self.selected_object)

    def _switch_tab(self, tab_name: str):
        self.active_tab = tab_name
        if tab_name == "OBJECT":
            self.btn_tab_obj.line_color = StudioTheme.BORDER_FOCUSED
            self.btn_tab_obj.text_color = StudioTheme.TEXT_PRIMARY
            self.btn_tab_cam.line_color = StudioTheme.BORDER_SUBTLE
            self.btn_tab_cam.text_color = StudioTheme.TEXT_SECONDARY
            self._render_object_tab()
        else:
            self.btn_tab_cam.line_color = StudioTheme.BORDER_CAMERA
            self.btn_tab_cam.text_color = StudioTheme.TEXT_PRIMARY
            self.btn_tab_obj.line_color = StudioTheme.BORDER_SUBTLE
            self.btn_tab_obj.text_color = StudioTheme.TEXT_SECONDARY
            self._render_camera_tab()

    def _render_object_tab(self):
        self.content_box.clear_widgets()

        if not self.selected_object:
            empty_lbl = MDLabel(
                text="Select an object from the Assets panel to inspect and customize its animation.",
                font_style="Caption",
                theme_text_color="Custom",
                text_color=StudioTheme.TEXT_MUTED,
                halign="center",
                adaptive_height=True,
                padding=[dp(8), dp(20)]
            )
            self.content_box.add_widget(empty_lbl)
            return

        # Object Header
        name_card = MDCard(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(4),
            adaptive_height=True,
            radius=[dp(6)],
            md_bg_color=StudioTheme.BG_CARD
        )
        lbl_name = MDLabel(
            text=self.selected_object.name,
            font_style="Subtitle1",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            bold=True,
            adaptive_height=True
        )
        lbl_info = MDLabel(
            text=f"BBox: {self.selected_object.bbox} • Area: {self.selected_object.area:,}px",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_SECONDARY,
            adaptive_height=True
        )
        name_card.add_widget(lbl_name)
        name_card.add_widget(lbl_info)
        self.content_box.add_widget(name_card)

        # Duration Control
        dur_box = MDBoxLayout(orientation="vertical", spacing=dp(4), adaptive_height=True)
        dur_hdr = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        dur_lbl = MDLabel(
            text="Duration Budget",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            adaptive_width=True
        )
        self.dur_val_lbl = MDLabel(
            text=f"{self.selected_object.duration:.1f}s",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_PRIMARY,
            halign="right",
            adaptive_height=True,
            bold=True
        )
        dur_hdr.add_widget(dur_lbl)
        dur_hdr.add_widget(self.dur_val_lbl)
        dur_box.add_widget(dur_hdr)

        dur_slider = Slider(
            min=1.0,
            max=8.0,
            value=self.selected_object.duration,
            step=0.1,
            size_hint_x=1.0,
            value_track=True,
            value_track_color=[0.49, 0.30, 1.0, 1.0]
        )
        dur_slider.bind(value=self._on_dur_change)
        dur_box.add_widget(dur_slider)
        self.content_box.add_widget(dur_box)

        # Component Layer Toggles
        toggles_card = MDCard(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8),
            adaptive_height=True,
            radius=[dp(6)],
            md_bg_color=StudioTheme.BG_CARD
        )
        toggles_card.add_widget(MDLabel(
            text="ANIMATION LAYERS",
            font_style="Overline",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_MUTED,
            adaptive_height=True,
            bold=True
        ))

        toggles_card.add_widget(self._build_toggle_row("Outlines", len(self.selected_object.strokes) > 0))
        toggles_card.add_widget(self._build_toggle_row("TrueColor Fills", len(self.selected_object.fills) > 0))
        toggles_card.add_widget(self._build_toggle_row("Micro Details", len(self.selected_object.details) > 0))

        self.content_box.add_widget(toggles_card)

    def _build_toggle_row(self, title: str, active: bool) -> MDBoxLayout:
        row = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        lbl = MDLabel(
            text=title,
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            adaptive_width=True
        )
        sw = Switch(active=active, size_hint=(None, None), size=(dp(40), dp(24)))
        row.add_widget(lbl)
        row.add_widget(BoxLayout())
        row.add_widget(sw)
        return row

    def _render_camera_tab(self):
        self.content_box.clear_widgets()

        # 1. Interactive Camera Zoom Control
        zoom_card = MDCard(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(6),
            adaptive_height=True,
            radius=[dp(6)],
            md_bg_color=StudioTheme.BG_CARD
        )
        zoom_hdr = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        zoom_hdr.add_widget(MDLabel(
            text="Camera Zoom Level",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            bold=True,
            adaptive_width=True
        ))
        self.zoom_val_lbl = MDLabel(
            text=f"{self.current_zoom:.2f}x",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_SECONDARY,
            halign="right",
            adaptive_height=True,
            bold=True
        )
        zoom_hdr.add_widget(self.zoom_val_lbl)
        zoom_card.add_widget(zoom_hdr)

        self.zoom_slider = Slider(
            min=1.0,
            max=3.2,
            value=self.current_zoom,
            step=0.05,
            size_hint_x=1.0,
            value_track=True,
            value_track_color=[0.0, 0.90, 1.0, 1.0]
        )
        self.zoom_slider.bind(value=self._on_zoom_slider_change)
        zoom_card.add_widget(self.zoom_slider)

        # Zoom Preset Buttons
        presets_row = MDBoxLayout(orientation="horizontal", spacing=dp(4), adaptive_height=True)
        presets = [("1.0x Full", 1.0), ("1.4x Mid", 1.4), ("1.8x Close", 1.8), ("2.4x Deep", 2.4)]
        for text, val in presets:
            btn = MDRoundFlatButton(
                text=text,
                font_size=sp(11),
                theme_text_color="Custom",
                text_color=StudioTheme.TEXT_SECONDARY,
                line_color=StudioTheme.BORDER_SUBTLE,
                on_release=lambda x, v=val: self._set_zoom_preset(v)
            )
            presets_row.add_widget(btn)
        zoom_card.add_widget(presets_row)
        self.content_box.add_widget(zoom_card)

        # 2. Camera Shots Storyboard
        shots_hdr = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        shots_hdr.add_widget(MDLabel(
            text="CAMERA SHOTS STORYBOARD",
            font_style="Overline",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_MUTED,
            adaptive_height=True,
            bold=True
        ))
        shots_count = MDLabel(
            text=str(len(self.current_shots)),
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_SECONDARY,
            halign="right",
            adaptive_height=True,
            bold=True
        )
        shots_hdr.add_widget(shots_count)
        self.content_box.add_widget(shots_hdr)

        # Shots List
        for idx, shot in enumerate(self.current_shots):
            item = CameraShotItem(shot, idx, self._on_shot_click)
            self.content_box.add_widget(item)

    def _on_zoom_slider_change(self, instance, val):
        self.current_zoom = float(val)
        self.zoom_val_lbl.text = f"{self.current_zoom:.2f}x"
        if self.app:
            self.app.on_zoom_changed(self.current_zoom)

    def _set_zoom_preset(self, val: float):
        self.zoom_slider.value = val

    def _on_dur_change(self, instance, val):
        if self.selected_object:
            self.selected_object.duration = float(val)
            self.dur_val_lbl.text = f"{val:.1f}s"
            if self.app:
                self.app.replan_timeline()

    def _on_shot_click(self, shot):
        if self.app:
            self.app.on_camera_shot_selected(shot)

    def inspect_object(self, obj):
        self.selected_object = obj
        if self.active_tab == "OBJECT":
            self._render_object_tab()

    def update_shots(self, shots):
        self.current_shots = shots
        if self.active_tab == "CAMERA":
            self._render_camera_tab()

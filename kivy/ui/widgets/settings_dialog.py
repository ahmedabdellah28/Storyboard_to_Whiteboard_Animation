"""
Comprehensive Animation & Export Settings Dialog
Features full customizable control with editable inputs, clear English descriptions, and categories.
"""
from typing import Any
import json
import os
from kivy.uix.spinner import Spinner
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.scrollview import MDScrollView
from engine.core.scene import SceneConfig
from ..theme import Theme


class SectionHeader(MDBoxLayout):
    """Visual header separating setting categories."""
    def __init__(self, title: str, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.adaptive_height = True
        self.spacing = dp(2)
        self.padding = [0, dp(14), 0, dp(4)]

        lbl = MDLabel(
            text=title.upper(),
            font_style="Subtitle2",
            theme_text_color="Custom",
            text_color=Theme.ACCENT_CYAN,
            bold=True,
            adaptive_height=True
        )
        self.add_widget(lbl)


class SettingRow(MDBoxLayout):
    """A row containing a label, an editable input widget, and an explanatory description."""
    def __init__(self, title: str, description: str, widget, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.adaptive_height = True
        self.spacing = dp(2)
        self.padding = [0, dp(4), 0, dp(6)]

        top_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(12))
        lbl_title = MDLabel(
            text=title,
            font_style="Body2",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            adaptive_height=True,
            bold=True
        )
        top_row.add_widget(lbl_title)
        top_row.add_widget(widget)
        self.add_widget(top_row)

        if description:
            lbl_desc = MDLabel(
                text=description,
                font_style="Caption",
                theme_text_color="Custom",
                text_color=Theme.TEXT_SECONDARY,
                adaptive_height=True
            )
            self.add_widget(lbl_desc)


def _clean_float(val: Any, default: float) -> float:
    """Safely parse float values supporting Arabic-Indic digits, commas, and prefixes."""
    if val is None:
        return default
    s = str(val).strip()
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for i, d in enumerate(arabic_digits):
        s = s.replace(d, str(i))
    s = s.replace(",", ".").replace("x", "").replace("X", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def create_input_field(default_value: str, width_dp: int = 140) -> MDTextField:
    """Helper to create a sleek editable text field for numeric/text settings."""
    field = MDTextField(
        text=str(default_value),
        size_hint=(None, None),
        size=(dp(width_dp), dp(36)),
        mode="rectangle",
        text_color_normal=Theme.TEXT,
        text_color_focus=Theme.ACCENT,
        line_color_normal=Theme.BORDER,
        line_color_focus=Theme.ACCENT,
        font_size="13sp",
        multiline=False
    )
    return field


class SettingsDialogContent(MDBoxLayout):
    """Main scrollable container with all categorized settings."""
    def __init__(self, config: SceneConfig, dialog_ref=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = dp(520)
        self.config = config
        self.dialog_ref = dialog_ref

        # Scrollview for settings options
        self.scroll = MDScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.inner_layout = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(6),
            padding=[dp(8), dp(4), dp(8), dp(8)]
        )

        # ── 0. Deep Storyboard Engine (AI Organic) ──
        self.inner_layout.add_widget(SectionHeader("0. Deep Storyboard Engine (AI Organic)"))

        self.deep_mode_spinner = Spinner(
            text="ON" if getattr(config, "deep_mode", True) else "OFF",
            values=("ON", "OFF"),
            size_hint=(None, None), size=(dp(120), dp(34)),
            background_color=Theme.BG_CARD, color=Theme.TEXT
        )
        self.inner_layout.add_widget(SettingRow(
            "Deep Mode (Dynamic Organic):",
            "Enable 6-Stage Dynamic Organic Pipeline (Marker-controlled watershed decomposition, auto panel detection, and cinematic zoom).",
            self.deep_mode_spinner
        ))

        self.suppress_borders_spinner = Spinner(
            text="ON" if getattr(config, "suppress_borders", True) else "OFF",
            values=("ON", "OFF"),
            size_hint=(None, None), size=(dp(120), dp(34)),
            background_color=Theme.BG_CARD, color=Theme.TEXT
        )
        self.inner_layout.add_widget(SettingRow(
            "Suppress Panel Box Borders:",
            "Automatically removes outer rectangular panel frames so the hand draws only characters and artwork.",
            self.suppress_borders_spinner
        ))

        # ── 1. Video & Canvas Output ──
        self.inner_layout.add_widget(SectionHeader("1. Video & Canvas Output"))

        # Dedicated Quality / Resolution Tier Selector
        cur_w_val = getattr(config, "width", 1280)
        cur_h_val = getattr(config, "height", 720)
        if cur_w_val >= 3840 or cur_h_val >= 2160:
            init_quality = "4K Ultra HD (3840x2160)"
        elif cur_w_val >= 1920 or cur_h_val >= 1080:
            init_quality = "1080p Full HD (1920x1080)"
        else:
            init_quality = "720p HD (1280x720 - الافتراضية)"

        self.quality_spinner = Spinner(
            text=init_quality,
            values=(
                "720p HD (1280x720 - الافتراضية)",
                "1080p Full HD (1920x1080 - جودة فائقة)",
                "4K Ultra HD (3840x2160 - سينمائية)"
            ),
            size_hint=(None, None), size=(dp(240), dp(34)),
            background_color=Theme.BG_CARD, color=Theme.HEX_CYAN
        )
        self.quality_spinner.bind(text=self._on_quality_selected)
        self.inner_layout.add_widget(SettingRow(
            "Video Quality / Resolution (جودة الفيديو):",
            "Select default 720p HD for fast rendering, or upgrade to 1080p Full HD / 4K.",
            self.quality_spinner
        ))

        self.platform_preset_spinner = Spinner(
            text="Choose Platform Preset...",
            values=(
                "16:9 📺 YouTube HD (1280x720) [Default]",
                "16:9 📺 YouTube Full HD (1920x1080)",
                "9:16 📱 TikTok / Reels (720x1280)",
                "9:16 📱 TikTok / Reels FHD (1080x1920)",
                "1:1 ⏹️ Instagram Square (720x720)",
                "1:1 ⏹️ Instagram Square FHD (1080x1080)",
                "4:5 📸 Portrait Feed (720x900)",
                "4:5 📸 Portrait Feed FHD (1080x1350)",
                "4:3 🖥️ Tablet / Classic (960x720)",
                "4:3 🖥️ Tablet / Classic FHD (1440x1080)",
                "4K 🎬 Cinema Ultra HD (3840x2160)"
            ),
            size_hint=(None, None), size=(dp(240), dp(34)),
            background_color=Theme.BG_CARD, color=Theme.ACCENT_CYAN
        )
        self.platform_preset_spinner.bind(text=self._on_preset_selected)
        self.inner_layout.add_widget(SettingRow(
            "Platform & Aspect Ratio Preset:",
            "Quickly sets resolution to fit YouTube, TikTok, Instagram Reels, Feed, or 4K Cinema.",
            self.platform_preset_spinner
        ))

        self.width_field = create_input_field(str(config.width), 120)
        self.inner_layout.add_widget(SettingRow(
            "Canvas Width (pixels):",
            "Output video horizontal resolution (e.g. 1920 for Full HD, 3840 for 4K).",
            self.width_field
        ))

        self.height_field = create_input_field(str(config.height), 120)
        self.inner_layout.add_widget(SettingRow(
            "Canvas Height (pixels):",
            "Output video vertical resolution (e.g. 1080 for Full HD, 2160 for 4K).",
            self.height_field
        ))

        self.fps_field = create_input_field(str(config.fps), 120)
        self.inner_layout.add_widget(SettingRow(
            "Frame Rate (FPS):",
            "Frames rendered per second (e.g. 24 for cinematic, 30 for standard, 60 for ultra-smooth).",
            self.fps_field
        ))

        # ── 2. Drawing Engine & Speed ──
        self.inner_layout.add_widget(SectionHeader("2. Drawing Engine & Speed"))

        self.speed_field = create_input_field(str(config.drawing_speed), 120)
        self._syncing_speed = False
        self.speed_field.bind(text=self._on_general_speed_changed)
        self.inner_layout.add_widget(SettingRow(
            "General Speed Multiplier",
            "Master baseline speed factor for marker strokes and pencil motion (e.g. 1.0, 1.5, 2.5).",
            self.speed_field
        ))

        cur_char_spd = getattr(config, "character_drawing_speed", getattr(config, "drawing_speed", 1.5))
        self.char_speed_field = create_input_field(str(cur_char_spd), 120)
        self.inner_layout.add_widget(SettingRow(
            "Character & Artwork Speed",
            "Speed multiplier for characters, artwork, and concentric shading (e.g. 1.0 = slower/smooth, 1.5 = default, 2.5 = fast).",
            self.char_speed_field
        ))

        cur_txt_spd = getattr(config, "text_drawing_speed", getattr(config, "drawing_speed", 1.5))
        self.text_speed_field = create_input_field(str(cur_txt_spd), 120)
        self.inner_layout.add_widget(SettingRow(
            "Text & Typography Speed",
            "Speed multiplier for handwriting Arabic/English text lines, titles, and underlines (e.g. 1.0 = steady writing, 1.5 = default, 2.5 = fast).",
            self.text_speed_field
        ))

        cur_dir = getattr(config, "drawing_direction", "OUTSIDE_IN")
        display_dir = "Outside -> In" if cur_dir == "OUTSIDE_IN" else "Inside -> Out"
        self.dir_spinner = Spinner(
            text=display_dir,
            values=("Outside -> In", "Inside -> Out"),
            size_hint=(None, None), size=(dp(140), dp(34)),
            background_color=Theme.BG_CARD, color=Theme.TEXT
        )
        self.inner_layout.add_widget(SettingRow(
            "Drawing Flow Direction:",
            "Outside->In draws outer borders first then spirals in. Inside->Out starts at core center and expands out.",
            self.dir_spinner
        ))

        self.ring_step_field = create_input_field(str(getattr(config, "ring_step", 5)), 120)
        self.inner_layout.add_widget(SettingRow(
            "Ring Step / Density (px):",
            "Distance in pixels between concentric orbital rings. Smaller values create denser lines.",
            self.ring_step_field
        ))

        self.brush_radius_field = create_input_field(str(getattr(config, "brush_radius", 8)), 120)
        self.inner_layout.add_widget(SettingRow(
            "Brush Tip Radius (px):",
            "Marker / pencil reveal stroke thickness in pixels.",
            self.brush_radius_field
        ))

        self.sample_interval_field = create_input_field(str(getattr(config, "sample_interval", 3.0)), 120)
        self.inner_layout.add_widget(SettingRow(
            "Sampling Interval (px):",
            "Point interpolation distance along strokes for smooth hand trajectory.",
            self.sample_interval_field
        ))

        # ── 3. Virtual Camera & Zoom ──
        self.inner_layout.add_widget(SectionHeader("3. Virtual Camera & Zoom"))

        self.zoom_field = create_input_field(str(getattr(config, "camera_zoom_scale", 1.40)), 120)
        self.inner_layout.add_widget(SettingRow(
            "Camera Zoom Magnification:",
            "Close-up magnification factor when focusing on each character (1.0 = Full Overview, 2.0 = Normal Focus, 3.5 = Deep Close-up).",
            self.zoom_field
        ))

        self.transition_field = create_input_field(str(config.transition_duration), 120)
        self.inner_layout.add_widget(SettingRow(
            "Camera Transition Duration (s):",
            "Smooth panning transition time in seconds when moving between elements.",
            self.transition_field
        ))

        self.end_hold_field = create_input_field(str(getattr(config, "end_hold_seconds", 1.5)), 120)
        self.inner_layout.add_widget(SettingRow(
            "Final Composition Hold (s):",
            "Duration in seconds to showcase the finished whiteboard at the end of the video.",
            self.end_hold_field
        ))

        # ── 4. Realistic Drawing Hand ──
        self.inner_layout.add_widget(SectionHeader("4. Realistic Hand Overlay"))

        self.hand_spinner = Spinner(
            text="ON" if getattr(config, "show_hand", True) else "OFF",
            values=("ON", "OFF"),
            size_hint=(None, None), size=(dp(120), dp(34)),
            background_color=Theme.BG_CARD, color=Theme.TEXT
        )
        self.inner_layout.add_widget(SettingRow(
            "Drawing Hand Overlay:",
            "Enable or disable realistic drawing hand and whiteboard marker overlay.",
            self.hand_spinner
        ))

        self.hand_scale_field = create_input_field(str(getattr(config, "hand_scale", 0.95)), 120)
        self.inner_layout.add_widget(SettingRow(
            "Hand Size Scale Factor:",
            "Scale multiplier for the hand sprite size (e.g. 0.7 for small, 0.95 for standard, 1.2 for large).",
            self.hand_scale_field
        ))

        # ── 5. Storyboard Layout & Styling ──
        self.inner_layout.add_widget(SectionHeader("5. Layout & Styling"))

        self.spacing_field = create_input_field(str(getattr(config, "element_spacing", 24)), 120)
        self.inner_layout.add_widget(SettingRow(
            "Element Spacing Gap (px):",
            "Horizontal spacing gap in pixels between adjacent panels on the widescreen canvas.",
            self.spacing_field
        ))

        self.color_palette_field = create_input_field(str(config.color_palette_size), 120)
        self.inner_layout.add_widget(SettingRow(
            "Color Palette Clusters:",
            "Number of color clusters for vector extraction and region quantization (16 to 256).",
            self.color_palette_field
        ))

        self.scroll.add_widget(self.inner_layout)
        self.add_widget(self.scroll)

        # ── Bottom Action Buttons ──
        btn_bar = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(10),
            padding=[0, dp(12), 0, 0]
        )

        self.cancel_btn = MDFlatButton(
            text="CANCEL",
            theme_text_color="Custom",
            text_color=Theme.TEXT_SECONDARY,
            size_hint_x=0.3
        )
        self.reset_btn = MDFlatButton(
            text="RESET DEFAULTS",
            theme_text_color="Custom",
            text_color=Theme.ACCENT_CYAN,
            size_hint_x=0.35
        )
        self.save_btn = MDRaisedButton(
            text="SAVE SETTINGS",
            md_bg_color=Theme.ACCENT,
            text_color=(1, 1, 1, 1),
            size_hint_x=0.35
        )

        btn_bar.add_widget(self.cancel_btn)
        btn_bar.add_widget(self.reset_btn)
        btn_bar.add_widget(self.save_btn)
        self.add_widget(btn_bar)

    def _on_quality_selected(self, spinner, text):
        if "1080p" in text:
            # Scale active ratio to 1080p height (or 1080p width for vertical)
            cur_w = int(self.width_field.text or "1280")
            cur_h = int(self.height_field.text or "720")
            if cur_h > cur_w: # Vertical e.g. 9:16
                self.width_field.text = "1080"
                self.height_field.text = "1920"
            elif cur_w == cur_h: # Square 1:1
                self.width_field.text = "1080"
                self.height_field.text = "1080"
            else: # Landscape 16:9
                self.width_field.text = "1920"
                self.height_field.text = "1080"
        elif "4K" in text:
            self.width_field.text = "3840"
            self.height_field.text = "2160"
        else: # 720p HD Default
            cur_w = int(self.width_field.text or "1280")
            cur_h = int(self.height_field.text or "720")
            if cur_h > cur_w: # Vertical 9:16
                self.width_field.text = "720"
                self.height_field.text = "1280"
            elif cur_w == cur_h: # Square 1:1
                self.width_field.text = "720"
                self.height_field.text = "720"
            else: # 16:9
                self.width_field.text = "1280"
                self.height_field.text = "720"

    def _on_preset_selected(self, spinner, text):
        if "16:9" in text:
            if "Full HD" in text or "1920" in text:
                self.width_field.text = "1920"
                self.height_field.text = "1080"
                self.quality_spinner.text = "1080p Full HD (1920x1080 "
            else:
                self.width_field.text = "1280"
                self.height_field.text = "720"
                self.quality_spinner.text = "720p HD (1280x720 )"
        elif "9:16" in text:
            if "FHD" in text or "1080" in text:
                self.width_field.text = "1080"
                self.height_field.text = "1920"
                self.quality_spinner.text = "1080p Full HD (1920x1080 "
            else:
                self.width_field.text = "720"
                self.height_field.text = "1280"
                self.quality_spinner.text = "720p HD (1280x720 )"
        elif "1:1" in text:
            if "FHD" in text or "1080" in text:
                self.width_field.text = "1080"
                self.height_field.text = "1080"
                self.quality_spinner.text = "1080p Full HD (1920x1080 "
            else:
                self.width_field.text = "720"
                self.height_field.text = "720"
                self.quality_spinner.text = "720p HD (1280x720 )"
        elif "4:5" in text:
            if "FHD" in text or "1350" in text:
                self.width_field.text = "1080"
                self.height_field.text = "1350"
                self.quality_spinner.text = "1080p Full HD (1920x1080 "
            else:
                self.width_field.text = "720"
                self.height_field.text = "900"
                self.quality_spinner.text = "720p HD (1280x720 )"
        elif "4:3" in text:
            if "FHD" in text or "1440" in text:
                self.width_field.text = "1440"
                self.height_field.text = "1080"
                self.quality_spinner.text = "1080p Full HD (1920x1080 "
            else:
                self.width_field.text = "960"
                self.height_field.text = "720"
                self.quality_spinner.text = "720p HD (1280x720 )"
        elif "4K" in text:
            self.width_field.text = "3840"
            self.height_field.text = "2160"
            self.quality_spinner.text = "4K Ultra HD (3840x2160 )"

    def _on_general_speed_changed(self, instance, text):
        """Automatically synchronizes character and text speed fields with general speed when general speed is updated."""
        if getattr(self, "_syncing_speed", False):
            return
        val = _clean_float(text, None)
        if val is not None and 0.1 <= val <= 20.0:
            self._syncing_speed = True
            try:
                self.char_speed_field.text = f"{val:g}"
                self.text_speed_field.text = f"{val:g}"
            finally:
                self._syncing_speed = False

    def reset_defaults(self):
        """Reset all input fields to recommended defaults."""
        self._syncing_speed = True
        try:
            self.quality_spinner.text = "720p HD (1280x720 )"
            self.platform_preset_spinner.text = "Choose Platform Preset..."
            self.deep_mode_spinner.text = "ON"
            self.suppress_borders_spinner.text = "ON"
            self.width_field.text = "1280"
            self.height_field.text = "720"
            self.fps_field.text = "30"
            self.speed_field.text = "1.5"
            self.char_speed_field.text = "1.5"
            self.text_speed_field.text = "1.5"
            self.dir_spinner.text = "Outside -> In"
            self.ring_step_field.text = "5"
            self.brush_radius_field.text = "8"
            self.sample_interval_field.text = "3.0"
            self.zoom_field.text = "2.10"
            self.transition_field.text = "0.5"
            self.end_hold_seconds_field = getattr(self, "end_hold_field", None)
            if self.end_hold_seconds_field:
                self.end_hold_seconds_field.text = "1.5"
            self.hand_spinner.text = "ON"
            self.hand_scale_field.text = "0.95"
            self.spacing_field.text = "24"
            self.color_palette_field.text = "28"
        finally:
            self._syncing_speed = False


class SettingsDialog:
    """Controller dialog for configuring export and animation settings."""
    def __init__(self, config: SceneConfig, on_save_callback=None):
        self.on_save_callback = on_save_callback
        self.content = SettingsDialogContent(config, dialog_ref=self)

        self.content.cancel_btn.bind(on_release=self.dismiss)
        self.content.reset_btn.bind(on_release=lambda *args: self.content.reset_defaults())
        self.content.save_btn.bind(on_release=self.save)

        self.dialog = MDDialog(
            title="Storyboard to Whiteboard Settings",
            type="custom",
            content_cls=self.content,
            md_bg_color=Theme.BG_PANEL,
            auto_dismiss=True
        )

    def open(self):
        self.dialog.open()

    def dismiss(self, *args):
        try:
            self.dialog.dismiss(force=True)
        except Exception:
            pass

    def save(self, *args):
        c = self.content.config
        try:
            # Parse Deep Mode
            c.deep_mode = (self.content.deep_mode_spinner.text.strip() == "ON")
            c.suppress_borders = (self.content.suppress_borders_spinner.text.strip() == "ON")
            # Parse Resolution
            c.width = max(320, int(_clean_float(self.content.width_field.text, c.width)))
            c.height = max(240, int(_clean_float(self.content.height_field.text, c.height)))
            # Parse FPS
            c.fps = max(1, min(120, int(_clean_float(self.content.fps_field.text, c.fps))))
            # Parse Speed with robust fallback
            gen_spd = max(0.1, min(20.0, _clean_float(self.content.speed_field.text, c.drawing_speed)))
            char_spd = max(0.1, min(20.0, _clean_float(self.content.char_speed_field.text, gen_spd)))
            txt_spd = max(0.1, min(20.0, _clean_float(self.content.text_speed_field.text, gen_spd)))

            c.drawing_speed = gen_spd
            c.character_drawing_speed = char_spd
            c.text_drawing_speed = txt_spd

            # Parse Direction
            dir_val = self.content.dir_spinner.text.strip()
            c.drawing_direction = "INSIDE_OUT" if "Inside" in dir_val else "OUTSIDE_IN"
            # Parse Ring Step
            c.ring_step = max(1, min(50, int(_clean_float(self.content.ring_step_field.text, c.ring_step))))
            # Parse Brush Radius
            c.brush_radius = max(2, min(50, int(_clean_float(self.content.brush_radius_field.text, c.brush_radius))))
            # Parse Sampling
            c.sample_interval = max(1.0, min(20.0, _clean_float(self.content.sample_interval_field.text, c.sample_interval)))
            # Parse Zoom
            c.camera_zoom_scale = max(1.0, min(5.0, _clean_float(self.content.zoom_field.text, c.camera_zoom_scale)))
            # Parse Transitions
            c.transition_duration = max(0.0, min(10.0, _clean_float(self.content.transition_field.text, c.transition_duration)))
            c.end_hold_seconds = max(0.0, min(10.0, _clean_float(self.content.end_hold_field.text, c.end_hold_seconds)))
            # Parse Hand
            c.show_hand = (self.content.hand_spinner.text.strip() == "ON")
            c.hand_scale = max(0.2, min(3.0, _clean_float(self.content.hand_scale_field.text, c.hand_scale)))
            # Parse Spacing & Palette
            c.element_spacing = max(0, min(200, int(_clean_float(self.content.spacing_field.text, c.element_spacing))))
            c.color_palette_size = max(8, min(256, int(_clean_float(self.content.color_palette_field.text, c.color_palette_size))))
        except Exception as e:
            print(f"[SettingsDialog] Parse error: {e}")

        self.dismiss()

        if self.on_save_callback:
            try:
                self.on_save_callback(c)
            except Exception as e:
                print(f"[SettingsDialog] Error invoking on_save_callback: {e}")
        else:
            app = MDApp.get_running_app()
            if hasattr(app, "save_settings"):
                app.save_settings(c)

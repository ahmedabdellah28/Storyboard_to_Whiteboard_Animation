import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRoundFlatButton, MDFillRoundFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from ...theme import StudioTheme


class DebugGalleryContent(MDBoxLayout):
    STAGES = [
        ("01_original.png", "01. Original Image"),
        ("02_resized_padded.png", "02. Normalized 1080p Canvas"),
        ("03_color_quantized.png", "03. LAB Quantization & Palette"),
        ("04_edges_raw.png", "04. Multi-Scale Edges"),
        ("05_strokes_classified.png", "05. Classified Stroke Paths"),
        ("06_color_regions.png", "06. Connected Color Regions"),
        ("07_major_objects_detected.png", "07. Major Object Grouping"),
        ("08_camera_shots_storyboard.png", "08. Camera Shots & Viewports"),
        ("09_full_composition_preview.png", "09. Final Composition"),
    ]

    def __init__(self, app_ref, dialog_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.dialog_ref = dialog_ref
        self.orientation = "horizontal"
        self.spacing = dp(12)
        self.size_hint_y = None
        self.height = dp(440)
        self.padding = [dp(12), dp(8), dp(12), dp(8)]

        self.active_stage_idx = 6 # Default to Major Objects
        self.buttons = []

        self._build_ui()

    def _build_ui(self):
        # 1. Left Stages Selector List
        scroll = ScrollView(size_hint_x=0.35, do_scroll_x=False)
        stages_box = MDBoxLayout(orientation="vertical", spacing=dp(4), adaptive_height=True)

        for idx, (fname, label) in enumerate(self.STAGES):
            btn = MDRoundFlatButton(
                text=label,
                size_hint_x=1.0,
                font_size=sp(11),
                line_color=StudioTheme.BORDER_FOCUSED if idx == self.active_stage_idx else StudioTheme.BORDER_SUBTLE,
                theme_text_color="Custom",
                text_color=StudioTheme.TEXT_PRIMARY if idx == self.active_stage_idx else StudioTheme.TEXT_SECONDARY,
                on_release=lambda x, i=idx: self._select_stage(i)
            )
            self.buttons.append(btn)
            stages_box.add_widget(btn)

        scroll.add_widget(stages_box)
        self.add_widget(scroll)

        # 2. Right Image Viewer
        viewer_box = MDBoxLayout(orientation="vertical", spacing=dp(6), size_hint_x=0.65)
        self.stage_img = Image(
            source="",
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 0.90)
        )
        self.stage_lbl = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_PRIMARY,
            halign="center",
            adaptive_height=True,
            bold=True
        )
        viewer_box.add_widget(self.stage_img)
        viewer_box.add_widget(self.stage_lbl)

        # Close button
        btn_close = MDRoundFlatButton(
            text="Close Gallery",
            line_color=StudioTheme.BORDER_SUBTLE,
            pos_hint={"center_x": 0.5},
            on_release=lambda x: self.dialog_ref.dismiss()
        )
        viewer_box.add_widget(btn_close)

        self.add_widget(viewer_box)
        self._update_display()

    def _select_stage(self, idx: int):
        self.active_stage_idx = idx
        for i, btn in enumerate(self.buttons):
            if i == idx:
                btn.line_color = StudioTheme.BORDER_FOCUSED
                btn.text_color = StudioTheme.TEXT_PRIMARY
            else:
                btn.line_color = StudioTheme.BORDER_SUBTLE
                btn.text_color = StudioTheme.TEXT_SECONDARY
        self._update_display()

    def _update_display(self):
        fname, label = self.STAGES[self.active_stage_idx]
        target_path = os.path.join("debug_output", fname)
        if os.path.exists(target_path):
            self.stage_img.source = target_path
            self.stage_img.reload()
            self.stage_lbl.text = label
        else:
            self.stage_lbl.text = f"{label} (Not generated yet)"


class DebugGalleryDialog:
    @staticmethod
    def show(app_ref):
        content = DebugGalleryContent(app_ref, None)
        dialog = MDDialog(
            title="PROCESSING PIPELINE DEBUG GALLERY",
            type="custom",
            content_cls=content,
            size_hint=(0.85, None),
            radius=[dp(12), dp(12), dp(12), dp(12)]
        )
        content.dialog_ref = dialog
        dialog.open()
        return dialog

import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.progressbar import ProgressBar
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFillRoundFlatIconButton, MDRoundFlatButton, MDFillRoundFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from ...theme import StudioTheme


class ExportStudioContent(MDBoxLayout):
    def __init__(self, app_ref, dialog_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.dialog_ref = dialog_ref
        self.orientation = "vertical"
        self.spacing = dp(12)
        self.adaptive_height = True
        self.padding = [dp(16), dp(10), dp(16), dp(10)]

        self.selected_res = "1080p"
        self.selected_fps = 30
        self.is_exporting = False

        self._build_ui()

    def _build_ui(self):
        # Header Info
        self.add_widget(MDLabel(
            text="Configure your output video parameters and render with NVENC hardware acceleration.",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_SECONDARY,
            adaptive_height=True
        ))

        # Resolution Selection
        res_card = MDCard(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(6),
            adaptive_height=True,
            radius=[dp(6)],
            md_bg_color=StudioTheme.BG_CARD
        )
        res_card.add_widget(MDLabel(
            text="RESOLUTION",
            font_style="Overline",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_MUTED,
            adaptive_height=True,
            bold=True
        ))
        res_btn_box = MDBoxLayout(orientation="horizontal", spacing=dp(8), adaptive_height=True)
        self.btn_1080p = MDFillRoundFlatButton(
            text="1080p (1920×1080)",
            md_bg_color=StudioTheme.ACCENT_PRIMARY,
            on_release=lambda x: self._set_res("1080p")
        )
        self.btn_720p = MDRoundFlatButton(
            text="720p (1280×720)",
            line_color=StudioTheme.BORDER_SUBTLE,
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_SECONDARY,
            on_release=lambda x: self._set_res("720p")
        )
        res_btn_box.add_widget(self.btn_1080p)
        res_btn_box.add_widget(self.btn_720p)
        res_card.add_widget(res_btn_box)
        self.add_widget(res_card)

        # FPS Selection
        fps_card = MDCard(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(6),
            adaptive_height=True,
            radius=[dp(6)],
            md_bg_color=StudioTheme.BG_CARD
        )
        fps_card.add_widget(MDLabel(
            text="FRAME RATE",
            font_style="Overline",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_MUTED,
            adaptive_height=True,
            bold=True
        ))
        fps_btn_box = MDBoxLayout(orientation="horizontal", spacing=dp(8), adaptive_height=True)
        self.btn_30fps = MDFillRoundFlatButton(
            text="30 FPS (Standard)",
            md_bg_color=StudioTheme.ACCENT_PRIMARY,
            on_release=lambda x: self._set_fps(30)
        )
        self.btn_60fps = MDRoundFlatButton(
            text="60 FPS (Smooth)",
            line_color=StudioTheme.BORDER_SUBTLE,
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_SECONDARY,
            on_release=lambda x: self._set_fps(60)
        )
        fps_btn_box.add_widget(self.btn_30fps)
        fps_btn_box.add_widget(self.btn_60fps)
        fps_card.add_widget(fps_btn_box)
        self.add_widget(fps_card)

        # Export Progress Bar
        self.progress_box = MDBoxLayout(orientation="vertical", spacing=dp(4), adaptive_height=True)
        self.export_status_lbl = MDLabel(
            text="Ready to export",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            adaptive_height=True
        )
        self.export_bar = ProgressBar(max=100.0, value=0.0, size_hint_y=None, height=dp(10))
        self.progress_box.add_widget(self.export_status_lbl)
        self.progress_box.add_widget(self.export_bar)
        self.add_widget(self.progress_box)

        # Action Buttons
        btn_box = MDBoxLayout(orientation="horizontal", spacing=dp(10), adaptive_height=True, padding=[0, dp(10), 0, 0])
        btn_cancel = MDRoundFlatButton(
            text="Cancel",
            line_color=StudioTheme.BORDER_SUBTLE,
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_SECONDARY,
            on_release=lambda x: self.dialog_ref.dismiss()
        )
        self.btn_start_export = MDFillRoundFlatIconButton(
            text="START EXPORT",
            icon="movie-play",
            md_bg_color=StudioTheme.ACCENT_PRIMARY,
            on_release=self._start_export
        )
        btn_box.add_widget(BoxLayout()) # spacer
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(self.btn_start_export)
        self.add_widget(btn_box)

    def _set_res(self, res_mode: str):
        self.selected_res = res_mode
        if res_mode == "1080p":
            self.btn_1080p.md_bg_color = StudioTheme.ACCENT_PRIMARY
            self.btn_1080p.text_color = "#FFFFFF"
            self.btn_720p.line_color = StudioTheme.BORDER_SUBTLE
            self.btn_720p.text_color = StudioTheme.TEXT_SECONDARY
        else:
            self.btn_720p.md_bg_color = StudioTheme.ACCENT_PRIMARY
            self.btn_720p.text_color = "#FFFFFF"
            self.btn_1080p.line_color = StudioTheme.BORDER_SUBTLE
            self.btn_1080p.text_color = StudioTheme.TEXT_SECONDARY

    def _set_fps(self, fps: int):
        self.selected_fps = fps
        if fps == 30:
            self.btn_30fps.md_bg_color = StudioTheme.ACCENT_PRIMARY
            self.btn_30fps.text_color = "#FFFFFF"
            self.btn_60fps.line_color = StudioTheme.BORDER_SUBTLE
            self.btn_60fps.text_color = StudioTheme.TEXT_SECONDARY
        else:
            self.btn_60fps.md_bg_color = StudioTheme.ACCENT_PRIMARY
            self.btn_60fps.text_color = "#FFFFFF"
            self.btn_30fps.line_color = StudioTheme.BORDER_SUBTLE
            self.btn_30fps.text_color = StudioTheme.TEXT_SECONDARY

    def _start_export(self, *args):
        if self.is_exporting:
            return
        self.is_exporting = True
        self.btn_start_export.disabled = True
        self.export_status_lbl.text = "Rendering frames with NVENC..."
        if self.app:
            self.app.trigger_studio_export(
                res=self.selected_res,
                fps=self.selected_fps,
                progress_cb=self._on_export_progress
            )

    def _on_export_progress(self, pct: float, msg: str = ""):
        self.export_bar.value = pct
        self.export_status_lbl.text = f"{msg} ({pct:.1f}%)" if msg else f"Exporting: {pct:.1f}%"
        if pct >= 100.0:
            self.export_status_lbl.text = "✓ Video Export Completed Successfully!"
            self.btn_start_export.disabled = False
            self.is_exporting = False


class ExportStudioDialog:
    @staticmethod
    def show(app_ref):
        content = ExportStudioContent(app_ref, None)
        dialog = MDDialog(
            title="EXPORT ANIMATION VIDEO",
            type="custom",
            content_cls=content,
            size_hint=(0.7, None),
            radius=[dp(12), dp(12), dp(12), dp(12)]
        )
        content.dialog_ref = dialog
        dialog.open()
        return dialog

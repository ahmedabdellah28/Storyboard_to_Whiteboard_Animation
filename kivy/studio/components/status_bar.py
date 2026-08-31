from kivy.uix.boxlayout import BoxLayout
from kivy.uix.progressbar import ProgressBar
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from ..theme import StudioTheme


class StudioStatusBar(MDBoxLayout):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(StudioTheme.BOTTOM_BAR_HEIGHT)
        self.padding = [dp(14), dp(2), dp(14), dp(2)]
        self.spacing = dp(10)
        self.md_bg_color = StudioTheme.BG_PANEL_HEADER

        self._build_ui()

    def _build_ui(self):
        # Status text with bullet
        self.status_lbl = MDLabel(
            text="● Ready",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_SUCCESS,
            adaptive_width=True,
            bold=True
        )
        self.add_widget(self.status_lbl)

        # Progress bar
        self.progress_bar = ProgressBar(
            max=100.0,
            value=0.0,
            size_hint_x=0.35,
            size_hint_y=None,
            height=dp(8)
        )
        self.add_widget(self.progress_bar)

        # Spacer
        self.add_widget(BoxLayout())

        # Hardware & Engine info
        self.info_lbl = MDLabel(
            text="Single-Pass PyAV • NVENC Hardware Accelerated",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_MUTED,
            adaptive_width=True
        )
        self.add_widget(self.info_lbl)

    def set_status(self, text: str, progress: float = 0.0, is_busy: bool = False):
        bullet_color = StudioTheme.ACCENT_PRIMARY if is_busy else StudioTheme.ACCENT_SUCCESS
        self.status_lbl.text = f"● {text}"
        self.status_lbl.text_color = bullet_color
        self.progress_bar.value = max(0.0, min(100.0, progress))

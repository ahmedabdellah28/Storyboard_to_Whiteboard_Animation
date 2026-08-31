"""
Loading Screen — Real progress tied to actual processing stages.
No fake progress. No "Rendering" label (we haven't started rendering).
"""
import os
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.metrics import dp, sp
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from ..theme import Theme


class LoadingScreen(MDScreen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.name = "loading"
        self.app = app_ref
        self.md_bg_color = Theme.BG_ROOT

        root = MDBoxLayout(orientation="vertical")

        # Top spacer
        root.add_widget(Widget(size_hint_y=0.25))

        # Center content
        center = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(16),
            padding=[dp(60), 0, dp(60), 0]
        )

        # Logo
        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "images", "favicon.png")
        if os.path.exists(logo_path):
            logo_img = Image(
                source=logo_path,
                size_hint=(None, None),
                size=(dp(64), dp(64)),
                pos_hint={"center_x": 0.5}
            )
            center.add_widget(logo_img)

        # Stage label
        self.stage_label = MDLabel(
            text="Preparing...",
            font_style="H6",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            halign="center",
            adaptive_height=True
        )
        center.add_widget(self.stage_label)

        # Progress bar
        self.progress_bar = MDProgressBar(
            value=0,
            max=100,
            size_hint_y=None,
            height=dp(6),
            color=Theme.ACCENT[:3] + [1.0]
        )
        center.add_widget(self.progress_bar)

        # Percentage label
        self.pct_label = MDLabel(
            text="0%",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            halign="center",
            adaptive_height=True
        )
        center.add_widget(self.pct_label)

        root.add_widget(center)

        # Bottom spacer
        root.add_widget(Widget(size_hint_y=0.5))

        self.add_widget(root)

    def set_progress(self, progress: float, stage: str):
        """Called from main thread via Clock.schedule_once"""
        self.progress_bar.value = progress
        self.stage_label.text = stage
        self.pct_label.text = f"{int(progress)}%"

"""
Home Screen — Clean drop/import landing page.
No Timeline, no Camera, no Settings. Just import.
"""
import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.metrics import dp, sp
from kivy.graphics import Color, Line, RoundedRectangle, Rectangle
from kivy.core.window import Window
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFillRoundFlatIconButton, MDFlatButton
from ..theme import Theme


class DropZone(MDBoxLayout):
    """Dashed-border drop area that accepts image files."""

    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.orientation = "vertical"
        self.size_hint = (None, None)
        self.size = (dp(420), dp(270))
        self.pos_hint = {"center_x": 0.5}
        self.padding = [dp(24), dp(24), dp(24), dp(24)]
        self.spacing = dp(12)
        self.md_bg_color = Theme.BG_DROP_ZONE

        with self.canvas.before:
            Color(rgba=Theme.BORDER_DASHED)
            self._border = Line(
                rounded_rectangle=(0, 0, 0, 0, dp(12)),
                width=1.5,
                dash_offset=8,
                dash_length=6
            )

        self.bind(pos=self._redraw, size=self._redraw)

        # Icon / Logo
        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "images", "icon_fg.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "images", "favicon.png")

        if os.path.exists(logo_path):
            icon_img = Image(
                source=logo_path,
                size_hint=(None, None),
                size=(dp(48), dp(48)),
                pos_hint={"center_x": 0.5}
            )
            self.add_widget(icon_img)
        else:
            icon_lbl = MDLabel(
                text="[size=48]" + chr(0xF0552) + "[/size]",
                markup=True,
                font_style="H4",
                theme_text_color="Custom",
                text_color=Theme.TEXT_DIM,
                halign="center",
                adaptive_height=True
            )
            self.add_widget(icon_lbl)

        # Title
        title = MDLabel(
            text="Drop image here",
            font_style="H6",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            halign="center",
            adaptive_height=True
        )
        self.add_widget(title)

        # Or divider
        or_label = MDLabel(
            text="or",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            halign="center",
            adaptive_height=True
        )
        self.add_widget(or_label)

        # Import button
        import_btn = MDFillRoundFlatIconButton(
            text="Import Image",
            icon="image-plus",
            theme_text_color="Custom",
            text_color=Theme.HEX_TEXT,
            theme_icon_color="Custom",
            icon_color=Theme.HEX_TEXT,
            md_bg_color=Theme.HEX_ACCENT,
            font_size=sp(14),
            pos_hint={"center_x": 0.5},
            on_release=lambda x: self.app.open_file_chooser()
        )
        self.add_widget(import_btn)

        # Supported formats
        fmt_lbl = MDLabel(
            text="PNG  .  JPG  .  JPEG  .  WEBP",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            halign="center",
            adaptive_height=True
        )
        self.add_widget(fmt_lbl)

        # Register window drop callback
        Window.bind(on_drop_file=self._on_file_drop)

    def _on_file_drop(self, window, file_path, x, y, *args):
        path = file_path.decode("utf-8") if isinstance(file_path, bytes) else file_path
        if path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            self.app.on_image_selected(path)

    def _redraw(self, *args):
        x, y = self.pos
        w, h = self.size
        self._border.rounded_rectangle = (x, y, w, h, dp(12))


class HomeScreen(MDScreen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.name = "home"
        self.app = app_ref
        self.md_bg_color = Theme.BG_ROOT

        root = MDBoxLayout(orientation="vertical")

        # Top spacer
        root.add_widget(Widget(size_hint_y=0.15))

        # Logo & Title block
        title_box = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(8),
            padding=[dp(20), 0, dp(20), 0]
        )

        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "images", "favicon.png")
        if os.path.exists(logo_path):
            logo_img = Image(
                source=logo_path,
                size_hint=(None, None),
                size=(dp(84), dp(84)),
                pos_hint={"center_x": 0.5}
            )
            title_box.add_widget(logo_img)

        app_title = MDLabel(
            text="STORYBOARD TO WHITEBOARD",
            font_style="H4",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            halign="center",
            adaptive_height=True,
            bold=True
        )
        app_subtitle = MDLabel(
            text="Transform storyboards and images into stunning whiteboard animations",
            font_style="Subtitle1",
            theme_text_color="Custom",
            text_color=Theme.TEXT_SECONDARY,
            halign="center",
            adaptive_height=True
        )
        title_box.add_widget(app_title)
        title_box.add_widget(app_subtitle)
        root.add_widget(title_box)

        # Spacer
        root.add_widget(Widget(size_hint_y=0.06))

        # Drop zone (centered)
        drop_container = MDBoxLayout(
            adaptive_height=True,
            padding=[dp(40), 0, dp(40), 0]
        )
        drop_container.add_widget(Widget())  # left spacer
        self.drop_zone = DropZone(self.app)
        drop_container.add_widget(self.drop_zone)
        drop_container.add_widget(Widget())  # right spacer
        root.add_widget(drop_container)

        # Bottom spacer
        root.add_widget(Widget(size_hint_y=0.3))

        # Version
        ver_lbl = MDLabel(
            text="Sketch Animation Studio v0.7.0",
            font_style="Overline",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            halign="center",
            adaptive_height=True,
            padding=[0, 0, 0, dp(12)]
        )
        root.add_widget(ver_lbl)

        self.add_widget(root)

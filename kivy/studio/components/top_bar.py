from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp, sp
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFillRoundFlatIconButton, MDIconButton, MDRoundFlatIconButton
from kivymd.uix.label import MDLabel
from ..theme import StudioTheme


class StudioTopBar(MDBoxLayout):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(StudioTheme.TOP_BAR_HEIGHT)
        self.padding = [dp(16), dp(8), dp(16), dp(8)]
        self.spacing = dp(12)
        self.md_bg_color = StudioTheme.BG_PANEL_HEADER

        with self.canvas.before:
            Color(rgba=[0.11, 0.13, 0.17, 1])
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(rgba=[0.15, 0.17, 0.22, 1])
            self.border_bottom = Rectangle(pos=self.pos, size=(self.width, dp(1)))

        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self._build_ui()

    def _update_canvas(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_bottom.pos = self.pos
        self.border_bottom.size = (self.width, dp(1))

    def _build_ui(self):
        # 1. Logo & App Title
        brand_box = MDBoxLayout(
            orientation="horizontal",
            adaptive_width=True,
            spacing=dp(8)
        )
        logo_btn = MDIconButton(
            icon="movie-edit",
            theme_icon_color="Custom",
            icon_color=StudioTheme.ACCENT_PRIMARY,
            icon_size=sp(26)
        )
        app_title = MDLabel(
            text="Sketch Animation Studio",
            font_style="Subtitle1",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            adaptive_width=True,
            bold=True
        )
        version_lbl = MDLabel(
            text="v2.1",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_SECONDARY,
            adaptive_width=True
        )
        brand_box.add_widget(logo_btn)
        brand_box.add_widget(app_title)
        brand_box.add_widget(version_lbl)
        self.add_widget(brand_box)

        # Spacer
        self.add_widget(BoxLayout(size_hint_x=0.08))

        # 2. Quick Action Buttons
        actions_box = MDBoxLayout(
            orientation="horizontal",
            adaptive_width=True,
            spacing=dp(8)
        )

        import_btn = MDRoundFlatIconButton(
            text="Import Image",
            icon="image-plus",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            theme_icon_color="Custom",
            icon_color=StudioTheme.ACCENT_PRIMARY,
            line_color=StudioTheme.BORDER_SUBTLE,
            on_release=lambda x: self.app.open_img_file_manager()
        )
        batch_btn = MDRoundFlatIconButton(
            text="Batch",
            icon="folder-multiple-image",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_SECONDARY,
            theme_icon_color="Custom",
            icon_color=StudioTheme.TEXT_SECONDARY,
            line_color=StudioTheme.BORDER_SUBTLE,
            on_release=lambda x: self.app.open_img_fldr_manager()
        )
        debug_btn = MDRoundFlatIconButton(
            text="Debug View",
            icon="layers-search",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_SECONDARY,
            theme_icon_color="Custom",
            icon_color=StudioTheme.ACCENT_SECONDARY,
            line_color=StudioTheme.BORDER_SUBTLE,
            on_release=lambda x: self.app.open_debug_gallery()
        )
        settings_btn = MDIconButton(
            icon="cog-outline",
            theme_icon_color="Custom",
            icon_color=StudioTheme.TEXT_SECONDARY,
            on_release=lambda x: self.app.open_settings_dialog()
        )

        actions_box.add_widget(import_btn)
        actions_box.add_widget(batch_btn)
        actions_box.add_widget(debug_btn)
        actions_box.add_widget(settings_btn)
        self.add_widget(actions_box)

        # Flexible spacer
        self.add_widget(BoxLayout())

        # 3. Animate All & Export CTA Buttons
        animate_all_btn = MDRoundFlatIconButton(
            text="Animate All Scenes",
            icon="play-box-multiple-outline",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_SECONDARY,
            theme_icon_color="Custom",
            icon_color=StudioTheme.ACCENT_SECONDARY,
            line_color=StudioTheme.BORDER_CAMERA,
            font_size=sp(13),
            on_release=lambda x: self.app.animate_all_scenes()
        )
        self.add_widget(animate_all_btn)

        export_btn = MDFillRoundFlatIconButton(
            text="Export Video",
            icon="export-variant",
            theme_text_color="Custom",
            text_color="#FFFFFF",
            theme_icon_color="Custom",
            icon_color="#FFFFFF",
            md_bg_color=StudioTheme.ACCENT_PRIMARY,
            font_size=sp(14),
            on_release=lambda x: self.app.open_export_dialog()
        )
        self.add_widget(export_btn)

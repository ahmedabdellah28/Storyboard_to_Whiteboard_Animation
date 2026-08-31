from kivy.uix.boxlayout import BoxLayout
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRoundFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from ...theme import StudioTheme


class SettingsContent(MDBoxLayout):
    def __init__(self, app_ref, dialog_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.dialog_ref = dialog_ref
        self.orientation = "vertical"
        self.spacing = dp(12)
        self.adaptive_height = True
        self.padding = [dp(16), dp(10), dp(16), dp(10)]

        self._build_ui()

    def _build_ui(self):
        # Setting 1: Max 1080p Resolution
        card1 = MDCard(
            orientation="horizontal",
            padding=dp(10),
            adaptive_height=True,
            radius=[dp(6)],
            md_bg_color=StudioTheme.BG_CARD
        )
        card1.add_widget(MDLabel(
            text="Cap Output to 1080p Full HD",
            font_style="Subtitle2",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            adaptive_width=True
        ))
        card1.add_widget(BoxLayout()) # spacer
        sw_1080p = Switch(active=True, size_hint=(None, None), size=(dp(40), dp(24)))
        card1.add_widget(sw_1080p)
        self.add_widget(card1)

        # Setting 2: End Hold Duration
        card2 = MDCard(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(4),
            adaptive_height=True,
            radius=[dp(6)],
            md_bg_color=StudioTheme.BG_CARD
        )
        hdr2 = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        hdr2.add_widget(MDLabel(
            text="Final Composition Hold Duration",
            font_style="Subtitle2",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            adaptive_width=True
        ))
        lbl_hold = MDLabel(
            text="1.5s",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_PRIMARY,
            halign="right",
            adaptive_height=True,
            bold=True
        )
        hdr2.add_widget(lbl_hold)
        card2.add_widget(hdr2)
        sl_hold = Slider(min=0.5, max=5.0, value=1.5, step=0.5, size_hint_x=1.0)
        sl_hold.bind(value=lambda inst, v: setattr(lbl_hold, "text", f"{v:.1f}s"))
        card2.add_widget(sl_hold)
        self.add_widget(card2)

        # Setting 3: Hand on Video
        card3 = MDCard(
            orientation="horizontal",
            padding=dp(10),
            adaptive_height=True,
            radius=[dp(6)],
            md_bg_color=StudioTheme.BG_CARD
        )
        card3.add_widget(MDLabel(
            text="Hand / Pen Cursor Overlay",
            font_style="Subtitle2",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            adaptive_width=True
        ))
        card3.add_widget(BoxLayout()) # spacer
        sw_hand = Switch(active=False, size_hint=(None, None), size=(dp(40), dp(24)))
        card3.add_widget(sw_hand)
        self.add_widget(card3)

        # Close Button
        btn_box = MDBoxLayout(orientation="horizontal", adaptive_height=True, padding=[0, dp(10), 0, 0])
        btn_close = MDRoundFlatButton(
            text="Close",
            line_color=StudioTheme.BORDER_SUBTLE,
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            on_release=lambda x: self.dialog_ref.dismiss()
        )
        btn_box.add_widget(BoxLayout())
        btn_box.add_widget(btn_close)
        self.add_widget(btn_box)


class SettingsStudioDialog:
    @staticmethod
    def show(app_ref):
        content = SettingsContent(app_ref, None)
        dialog = MDDialog(
            title="STUDIO PREFERENCES",
            type="custom",
            content_cls=content,
            size_hint=(0.65, None),
            radius=[dp(12), dp(12), dp(12), dp(12)]
        )
        content.dialog_ref = dialog
        dialog.open()
        return dialog

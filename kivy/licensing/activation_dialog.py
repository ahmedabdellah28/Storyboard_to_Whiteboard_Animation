"""
Activation Dialog for KivyMD (Program B - Sketch Animation Studio).
Simple, clean, and direct online activation matching Program A's user experience.
Asks only for the License Key (Format: SKCH-XXXX-XXXX-XXXX-XXXX) and validates via Supabase.
"""

import sys
import threading
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton

from licensing.license_guard import LicenseGuard


class ActivationContent(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(14)
        self.padding = [dp(12), dp(8), dp(12), dp(8)]
        self.size_hint_y = None
        self.height = dp(160)

        # Instructions
        self.add_widget(MDLabel(
            text="Please enter your License Key to activate Sketch Animation Studio.",
            theme_text_color="Secondary",
            font_style="Body2",
            size_hint_y=None,
            height=dp(30)
        ))

        # License Key Input Field
        self.key_field = MDTextField(
            hint_text="License Key (e.g. SKCH-XXXX-XXXX-XXXX-XXXX)",
            helper_text="Format: SKCH-XXXX-XXXX-XXXX-XXXX (Online connection required)",
            helper_text_mode="on_focus",
            mode="rectangle",
            size_hint_y=None,
            height=dp(60)
        )
        self.add_widget(self.key_field)

        # Status / Feedback Message
        self.status_label = MDLabel(
            text="",
            theme_text_color="Error",
            font_style="Caption",
            size_hint_y=None,
            height=dp(25)
        )
        self.add_widget(self.status_label)


class ActivationDialog:
    def __init__(self, on_success_callback=None):
        self.on_success = on_success_callback
        self.content = ActivationContent()

        self.activate_btn = MDRaisedButton(
            text="ACTIVATE",
            md_bg_color=(0.5, 0.2, 0.8, 1),
            on_release=self._on_activate_clicked
        )

        self.dialog = MDDialog(
            title="Software Activation Required",
            type="custom",
            content_cls=self.content,
            auto_dismiss=False,
            buttons=[
                MDFlatButton(
                    text="EXIT",
                    theme_text_color="Custom",
                    text_color=(0.7, 0.3, 0.3, 1),
                    on_release=self._on_exit
                ),
                self.activate_btn,
            ],
        )

    def show(self):
        self.dialog.open()

    def _on_exit(self, *args):
        sys.exit(0)

    def _on_activate_clicked(self, *args):
        entered_key = self.content.key_field.text.strip().upper()
        if not entered_key:
            self.content.status_label.theme_text_color = "Error"
            self.content.status_label.text = "Please enter your license key."
            return

        self.activate_btn.disabled = True
        self.content.status_label.theme_text_color = "Custom"
        self.content.status_label.text_color = (0.9, 0.7, 0.2, 1)
        self.content.status_label.text = "Connecting to Supabase License Gateway..."

        # Run online activation in background thread
        threading.Thread(target=self._run_activation, args=(entered_key,), daemon=True).start()

    def _run_activation(self, key: str):
        success, message = LicenseGuard.activate_online(key)
        Clock.schedule_once(lambda dt: self._handle_result(success, message))

    def _handle_result(self, success: bool, message: str):
        self.activate_btn.disabled = False
        if success:
            self.content.status_label.theme_text_color = "Custom"
            self.content.status_label.text_color = (0.2, 0.8, 0.4, 1)
            self.content.status_label.text = message
            
            # Dismiss dialog and unlock application
            self.dialog.dismiss()
            if self.on_success:
                self.on_success()
        else:
            self.content.status_label.theme_text_color = "Error"
            self.content.status_label.text = message

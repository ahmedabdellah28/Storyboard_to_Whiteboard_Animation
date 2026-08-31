"""
Test ActivationDialog initialization.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kivy"))

from kivymd.app import MDApp
from licensing.activation_dialog import ActivationDialog, ActivationContent


class TestActivationDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = MDApp.get_running_app() or MDApp()

    def test_activation_content_creation(self):
        content = ActivationContent()
        self.assertIsNotNone(content)
        self.assertIsNotNone(content.key_field)

    def test_activation_dialog_creation(self):
        dlg = ActivationDialog()
        self.assertIsNotNone(dlg.dialog)
        self.assertIn("Software Activation Required", dlg.dialog.title)


if __name__ == "__main__":
    unittest.main()

"""
Native Dialog Service for File Selection (Plyer with Tkinter Fallback).
"""
import os
from typing import Callable, Optional
from plyer import filechooser


class NativeDialogService:
    @staticmethod
    def open_image_chooser(on_selected_callback: Callable[[str], None]):
        """Open native image file chooser dialog."""
        def _on_selection(selection):
            if selection and len(selection) > 0:
                selected_path = selection[0]
                if selected_path and os.path.exists(selected_path):
                    on_selected_callback(selected_path)

        try:
            filechooser.open_file(
                title="Select Artwork or Storyboard",
                filters=[("Images", "*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp")],
                on_selection=_on_selection
            )
        except Exception as e:
            print(f"[DialogService] Plyer error: {e}, falling back to Tkinter...")
            NativeDialogService._fallback_tkinter_chooser(on_selected_callback)

    @staticmethod
    def _fallback_tkinter_chooser(on_selected_callback: Callable[[str], None]):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.askopenfilename(
                title="Select Artwork or Storyboard",
                filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
            )
            root.destroy()
            if file_path and os.path.exists(file_path):
                on_selected_callback(file_path)
        except Exception as e:
            print(f"[DialogService] Tkinter FileChooser error: {e}")

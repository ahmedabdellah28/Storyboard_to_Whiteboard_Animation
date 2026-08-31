"""
Sketch Animation Studio — main.py
Clean, fast, user-controlled. No automatic animation or rendering.
"""
from engine.core.project import StructureType
import os
import sys

# PyInstaller / Frozen Resource Path Handling
if getattr(sys, 'frozen', False):
    bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
    from kivy.resources import resource_add_path
    resource_add_path(bundle_dir)
    resource_add_path(os.path.join(bundle_dir, 'data'))
    resource_add_path(os.path.join(bundle_dir, 'data', 'images'))

os.environ['KIVY_GL_BACKEND'] = 'sdl2'
import datetime
from threading import Thread

import cv2
import numpy as np

import json

from kivymd.app import MDApp
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, FadeTransition

from plyer import filechooser

# Licensing imports
from licensing.license_guard import LicenseGuard
from licensing.activation_dialog import ActivationDialog

# Engine imports
from engine.core.scene import SceneConfig
from engine.processing.image_processor import ImageProcessor
from engine.planning.sequence_planner import SequencePlanner
from engine.planning.shot_planner import ShotPlanner
from engine.camera.camera import Camera
from engine.camera.camera_animator import CameraAnimator
from engine.render.renderer import Renderer
from engine.video.encoder import VideoEncoder

# UI imports
from ui.state.project_state import ProjectState, AppPhase
from ui.screens.home_screen import HomeScreen
from ui.screens.loading_screen import LoadingScreen
from ui.screens.scene_screen import SceneScreen
from ui.theme import Theme

__version__ = "0.7.0"


def read_image_unicode(img_path):
    """Read image supporting unicode paths."""
    if isinstance(img_path, np.ndarray):
        return img_path
    bytes_data = np.fromfile(str(img_path), dtype=np.uint8)
    img = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)
    return img


class SketchAnimationApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_keyboard=self._on_keyboard)
        Window.title = "Storyboard to Whiteboard Animation"
        self.state = ProjectState()

        # Paths
        home_dir = os.path.expanduser("~")
        self.video_dir = os.path.join(home_dir, "Documents", "image_to_animation")
        self.settings_file = os.path.join(home_dir, ".image_to_animation", "settings.json")
        os.makedirs(self.video_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)

    def load_settings(self):
        """Load user settings from JSON."""
        defaults = {
            "width": 1920, "height": 1080, "fps": 30,
            "detail_level": "HIGH", "color_palette_size": 28,
            "drawing_speed": 1.5, "camera_zoom_scale": 2.0, "transition_duration": 0.5,
            "show_hand": True, "hand_scale": 0.75, "element_spacing": 24,
            "drawing_direction": "OUTSIDE_IN",
            "ring_step": 5, "brush_radius": 8, "sample_interval": 3.0,
            "end_hold_seconds": 1.5
        }
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults.update(data)
            except Exception as e:
                print(f"Could not load settings: {e}")
        return defaults

    def save_settings(self, config: SceneConfig):
        """Save user settings to JSON."""
        data = {
            "width": config.width,
            "height": config.height,
            "fps": config.fps,
            "detail_level": config.detail_level,
            "color_palette_size": config.color_palette_size,
            "drawing_speed": config.drawing_speed,
            "camera_zoom_scale": getattr(config, "camera_zoom_scale", 2.0),
            "transition_duration": config.transition_duration,
            "show_hand": getattr(config, "show_hand", True),
            "hand_scale": getattr(config, "hand_scale", 0.75),
            "element_spacing": getattr(config, "element_spacing", 24),
            "drawing_direction": getattr(config, "drawing_direction", "OUTSIDE_IN"),
            "ring_step": getattr(config, "ring_step", 5),
            "brush_radius": getattr(config, "brush_radius", 8),
            "sample_interval": getattr(config, "sample_interval", 3.0),
            "end_hold_seconds": getattr(config, "end_hold_seconds", 1.5)
        }
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Could not save settings: {e}")

        # Propagate to active scenes
        if self.state.scene:
            self.state.scene.config = config
        if self.state.project and self.state.project.scenes:
            for sc in self.state.project.scenes:
                sc.config = config

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.accent_palette = "Cyan"

        logo_path = os.path.join(os.path.dirname(__file__), "data", "images", "favicon.png")
        if os.path.exists(logo_path):
            self.icon = logo_path
            try:
                Window.set_icon(logo_path)
            except Exception:
                pass

        self.sm = ScreenManager(transition=FadeTransition(duration=0.15))

        self.home_screen = HomeScreen(self)
        self.loading_screen = LoadingScreen(self)
        self.scene_screen = SceneScreen(self)

        self.sm.add_widget(self.home_screen)
        self.sm.add_widget(self.loading_screen)
        self.sm.add_widget(self.scene_screen)

        self.state._on_selection_changed = self._on_selection_changed

        return self.sm

    def on_start(self):
        """Verify software license online on startup."""
        from licensing.license_guard import LicenseGuard
        from licensing.activation_dialog import ActivationDialog

        # Verify online in background thread to keep UI smooth
        def _check_bg():
            is_valid, msg, token = LicenseGuard.verify_startup_online()
            if not is_valid:
                Clock.schedule_once(lambda dt: self._show_activation_dialog(msg), 0.1)

        Thread(target=_check_bg, daemon=True).start()

    def _show_activation_dialog(self, error_msg: str = ""):
        from licensing.activation_dialog import ActivationDialog
        self.activation_dialog = ActivationDialog(on_success_callback=self._on_license_activated)
        self.activation_dialog.show()
        if error_msg and "no license key" not in error_msg.lower():
            self.activation_dialog.content.status_label.text = error_msg

    def _on_license_activated(self):
        self._show_toast("Software Activated & Verified Online!")

    # ════════════════════════════════════════════════
    #  Navigation
    # ════════════════════════════════════════════════

    def go_home(self):
        self.state.set_phase(AppPhase.EMPTY)
        self.sm.current = "home"

    # ════════════════════════════════════════════════
    #  Image Selection
    # ════════════════════════════════════════════════

    def open_file_chooser(self):
        """Open native file dialog via Plyer."""
        try:
            filechooser.open_file(
                title="Select Artwork or Storyboard",
                filters=[("Images", "*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp")],
                on_selection=self._on_file_selected
            )
        except Exception as e:
            print(f"[FileChooser Error]: {e}")
            self._fallback_desktop_chooser()

    def _fallback_desktop_chooser(self):
        """Fallback tkinter file chooser if plyer fails."""
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
            if file_path:
                self.on_image_selected(file_path)
        except Exception as e:
            print(f"[Tkinter FileChooser Error]: {e}")

    def _on_file_selected(self, selection):
        if selection and len(selection) > 0:
            Clock.schedule_once(lambda dt: self.on_image_selected(selection[0]))

    def on_image_selected(self, path: str):
        """Called when user picks an image."""
        if not path or not os.path.exists(path):
            return

        from licensing.license_guard import LicenseGuard
        if not LicenseGuard.is_session_active():
            self._show_activation_dialog("Active License Session Required.")
            return

        self.state.source_image_path = path
        self.state.set_phase(AppPhase.ANALYZING)

        # Switch to loading screen
        self.sm.current = "loading"
        self.loading_screen.set_progress(0, "Analyzing composition...")

        # Start analysis in background thread
        Thread(target=self._analyze_worker, args=(path,), daemon=True).start()

    # ════════════════════════════════════════════════
    #  Analysis (Background Thread)
    # ════════════════════════════════════════════════

    def _analyze_worker(self, path: str):
        """Runs in background thread. Only does analysis — NO animation, NO rendering."""
        try:
            img = read_image_unicode(path)
            if img is None:
                raise ValueError(f"Could not load image: {path}")

            self.state.source_image = img

            s = self.load_settings()
            config = SceneConfig(
                width=s.get("width", 1280),
                height=s.get("height", 720),
                fps=s.get("fps", 30),
                detail_level=s.get("detail_level", "MEDIUM"),
                color_palette_size=min(32, s.get("color_palette_size", 24)),
                drawing_speed=s.get("drawing_speed", 1.5),
                transition_duration=s.get("transition_duration", 0.5),
                min_region_area=24,
                show_hand=s.get("show_hand", True),
                hand_scale=s.get("hand_scale", 0.75),
            )

            last_report = [0.0]

            def _progress_from_thread(pct, stage):
                # Throttle progress callback to avoid flooding Kivy event queue
                import time
                now = time.perf_counter()
                if now - last_report[0] > 0.05 or pct >= 99.0:
                    last_report[0] = now
                    Clock.schedule_once(lambda dt: self._update_loading(pct, stage))

            project = ImageProcessor.process(img, config, progress_cb=_progress_from_thread)

            Clock.schedule_once(lambda dt: self._on_analysis_complete(path, project))

        except Exception as e:
            import traceback
            err_msg = str(e)
            print(f"[Analysis Error]: {err_msg}")
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self._on_analysis_error(err_msg))

    def _update_loading(self, pct, stage):
        self.loading_screen.set_progress(pct, stage)
        self.state.set_progress(pct, stage)

    def _on_analysis_complete(self, path, project):
        """Called on main thread after analysis finishes."""
        self.state.set_project(project)
        self.state.set_phase(AppPhase.READY)
        self.scene_screen.load_project(path, project)
        self.sm.current = "scene"

    def _on_analysis_error(self, err_msg):
        self.loading_screen.set_progress(0, f"Error: {err_msg}")
        Clock.schedule_once(lambda dt: setattr(self.sm, 'current', 'home'), 3.0)

    # ════════════════════════════════════════════════
    #  Object Selection
    # ════════════════════════════════════════════════

    def on_object_selected(self, target):
        """Called when user taps an object card or canvas element."""
        if isinstance(target, str):
            self.state.set_active_id(target)
        elif isinstance(target, int):
            self.state.select(target)

    def _on_selection_changed(self, obj):
        """State callback — sync active object across canvas, inspector, and layers."""
        if hasattr(self, "scene_screen"):
            self.scene_screen._on_active_sync(obj)

    # ════════════════════════════════════════════════
    #  Animation (User-Triggered Only)
    # ════════════════════════════════════════════════

    def animate_single_object(self, obj):
        """Animate one object only and play live canvas preview."""
        if not self.state.project and not self.state.source_image and not self.state.source_image_path:
            return
        
        self.sm.current = "loading"
        self.loading_screen.set_progress(0, f"Preparing {obj.name}...")
        self.state.set_phase(AppPhase.ANIMATING)

        Thread(target=self._animate_single_worker, args=(obj, False), daemon=True).start()

    def export_single_object(self, obj):
        """Export video for one object and open destination folder."""
        if not self.state.project and not self.state.source_image and not self.state.source_image_path:
            return
        
        self.sm.current = "loading"
        self.loading_screen.set_progress(0, f"Exporting {obj.name}...")
        self.state.set_phase(AppPhase.EXPORTING)

        Thread(target=self._animate_single_worker, args=(obj, True), daemon=True).start()

    def animate_all_objects(self):
        """Animate all objects in current project. Called by ANIMATE ALL button."""
        if not self.state.project:
            return
        
        # Switch to loading screen
        self.sm.current = "loading"
        self.loading_screen.set_progress(0, "Preparing Animation...")
        self.state.set_phase(AppPhase.ANIMATING)

        Thread(target=self._animate_all_worker, daemon=True).start()

    def _animate_all_worker(self):
        try:
            now = datetime.datetime.now()
            filename = f"sketch_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
            out_path = os.path.join(self.video_dir, filename)

            from sketchApi import render_concentric_orbital_whiteboard

            s = self.load_settings()
            drawing_speed = float(s.get("drawing_speed", 1.5))
            camera_zoom_scale = float(s.get("camera_zoom_scale", 2.0))
            fps = int(s.get("fps", 30))
            element_spacing = int(s.get("element_spacing", 24))
            drawing_direction = str(s.get("drawing_direction", "OUTSIDE_IN"))
            ring_step = int(s.get("ring_step", 5))
            brush_radius = int(s.get("brush_radius", 8))
            sample_interval = float(s.get("sample_interval", 3.0))
            show_hand = bool(s.get("show_hand", True))
            hand_scale = float(s.get("hand_scale", 0.75))
            end_hold_seconds = float(s.get("end_hold_seconds", 1.5))

            def _progress_cb(pct, stage="Rendering Animation..."):
                Clock.schedule_once(lambda dt: self._update_loading(pct, stage))

            src_img = self.state.source_image
            if src_img is None and self.state.source_image_path:
                src_img = read_image_unicode(self.state.source_image_path)
                self.state.source_image = src_img

            if src_img is None:
                raise ValueError("No source image loaded.")

            render_concentric_orbital_whiteboard(
                image_input=src_img,
                output_path=out_path,
                fps=fps,
                drawing_speed=drawing_speed,
                camera_zoom_scale=camera_zoom_scale,
                element_spacing=element_spacing,
                drawing_direction=drawing_direction,
                ring_step=ring_step,
                brush_radius=brush_radius,
                sample_interval=sample_interval,
                show_hand=show_hand,
                hand_scale=hand_scale,
                end_hold_seconds=end_hold_seconds,
                custom_objects=self.state.objects,
                progress_callback=_progress_cb
            )

            Clock.schedule_once(lambda dt: self._on_export_complete(out_path))

        except Exception as e:
            import traceback
            err = str(e)
            print(f"[Export Error]: {err}")
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self._on_analysis_error(err))

    def move_object(self, from_idx: int, to_idx: int):
        """Reorders objects and updates project state."""
        self.state.reorder(from_idx, to_idx)

    def delete_object(self, index: int):
        """Deletes object at index from state."""
        self.state.remove_object(index)
        self._show_toast("تم حذف العنصر بنجاح.")

    def apply_manual_boxes(self, manual_boxes):
        """Called when user applies custom bounding boxes in SceneScreen."""
        if not manual_boxes:
            self._show_toast("لم يتم تحديد أي عناصر.")
            return

        try:
            src_img = self.state.source_image
            if src_img is None and self.state.source_image_path:
                src_img = read_image_unicode(self.state.source_image_path)
                self.state.source_image = src_img

            if src_img is None:
                return

            s = self.load_settings()
            config = SceneConfig(
                width=int(s.get("width", 1280)),
                height=int(s.get("height", 720)),
                fps=int(s.get("fps", 30)),
                drawing_speed=float(s.get("drawing_speed", 1.5))
            )

            project = ImageProcessor.process_custom_bboxes(src_img, manual_boxes, config)
            self.state.set_project(project)
            self.scene_screen.load_project(self.state.source_image_path, project)
            self._show_toast(f"تم تطبيق {len(manual_boxes)} عنصر محدد بنجاح!")
        except Exception as e:
            print(f"[Apply Manual Boxes Error]: {e}")
            self._show_toast(f"خطأ في تطبيق العناصر: {e}")

    def _animate_single_worker(self, obj, open_folder: bool = False):
        """Background worker to render a single object animation with the 360° concentric engine."""
        try:
            now = datetime.datetime.now()
            safe_name = obj.name.replace(" ", "_").lower()
            filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{safe_name}.mp4"
            out_path = os.path.join(self.video_dir, filename)

            from sketchApi import render_concentric_orbital_whiteboard

            s = self.load_settings()
            drawing_speed = float(s.get("drawing_speed", 1.5))
            camera_zoom_scale = float(s.get("camera_zoom_scale", 2.0))
            fps = int(s.get("fps", 30))
            element_spacing = int(s.get("element_spacing", 24))
            drawing_direction = str(s.get("drawing_direction", "OUTSIDE_IN"))
            ring_step = int(s.get("ring_step", 5))
            brush_radius = int(s.get("brush_radius", 8))
            sample_interval = float(s.get("sample_interval", 3.0))
            show_hand = bool(s.get("show_hand", True))
            hand_scale = float(s.get("hand_scale", 0.75))
            end_hold_seconds = float(s.get("end_hold_seconds", 1.5))

            def _progress_cb(pct, stage="Rendering..."):
                Clock.schedule_once(lambda dt: self._update_loading(pct, f"Rendering {obj.name}..."))

            src_img = self.state.source_image
            if src_img is None and self.state.source_image_path:
                src_img = read_image_unicode(self.state.source_image_path)
                self.state.source_image = src_img

            if src_img is None:
                raise ValueError("No source image loaded.")

            render_concentric_orbital_whiteboard(
                image_input=src_img,
                output_path=out_path,
                fps=fps,
                drawing_speed=drawing_speed,
                camera_zoom_scale=camera_zoom_scale,
                element_spacing=element_spacing,
                drawing_direction=drawing_direction,
                ring_step=ring_step,
                brush_radius=brush_radius,
                sample_interval=sample_interval,
                show_hand=show_hand,
                hand_scale=hand_scale,
                end_hold_seconds=end_hold_seconds,
                custom_objects=[obj],
                progress_callback=_progress_cb
            )

            Clock.schedule_once(lambda dt: self._on_export_complete(out_path, open_folder=open_folder))

        except Exception as e:
            import traceback
            err = str(e)
            print(f"[Animate Single Error]: {err}")
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self._on_analysis_error(err))

    def _on_export_complete(self, out_path: str, open_folder: bool = False):
        self._show_toast(f"Render Complete: {os.path.basename(out_path)}")
        self.sm.current = "scene"
        self.state.set_phase(AppPhase.READY)

        # 1. Automatically start video preview directly inside the app!
        try:
            self.scene_screen.play_video_preview(out_path)
        except Exception as e:
            print(f"Error starting in-app video preview: {e}")

        # 2. Only open the folder if the user clicked an explicit EXPORT action
        if open_folder:
            try:
                folder_path = os.path.dirname(out_path)
                if os.name == 'nt':
                    os.startfile(folder_path)
            except Exception as e:
                print(f"Could not open export directory: {e}")

    def open_export_folder(self):
        """Called when user clicks the EXPORT folder button in the Top Bar."""
        try:
            if os.path.exists(self.video_dir) and os.name == 'nt':
                os.startfile(self.video_dir)
        except Exception as e:
            print(f"Could not open export folder: {e}")

    def _show_toast(self, msg):
        from kivymd.toast import toast
        try:
            toast(msg)
        except Exception:
            print(f"[Toast]: {msg}")

    def undo(self):
        """Revert the last user action."""
        if self.state.undo():
            self._show_toast("Undo")

    def redo(self):
        """Reapply the last undone action."""
        if self.state.redo():
            self._show_toast("Redo")

    def _on_keyboard(self, instance, keyboard, keycode, text, modifiers):
        # Escape: deselect or return home
        if keyboard == 27:
            if self.state.active_object_id:
                self.state.set_active_id(None)
                return True
            elif self.sm.current != "home":
                self.go_home()
                return True

        # Ctrl+Z: Undo
        if (keyboard == 122 or keycode == 'z') and "ctrl" in modifiers:
            if "shift" in modifiers:
                self.redo()
            else:
                self.undo()
            return True

        # Ctrl+Y: Redo
        if (keyboard == 121 or keycode == 'y') and "ctrl" in modifiers:
            self.redo()
            return True

        # Ctrl+D: Duplicate Active Object
        if (keyboard == 100 or keycode == 'd') and "ctrl" in modifiers:
            if self.state.active_object_id:
                self.state.duplicate_object(self.state.active_object_id)
                self._show_toast("Element Duplicated")
                return True

        # Delete / Backspace: Delete Active Object
        if keyboard in (127, 8):  # Delete or Backspace
            if self.state.active_object_id:
                self.state.remove_object_by_id(self.state.active_object_id)
                self._show_toast("Element Deleted")
                return True

        return False


if __name__ == '__main__':
    SketchAnimationApp().run()

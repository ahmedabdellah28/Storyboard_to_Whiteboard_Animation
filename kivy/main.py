import os
import sys

# Configure UTF-8 encoding for Windows Console / PowerShell (cp1256 compatibility)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

# PyInstaller / Frozen Resource Path Handling
if getattr(sys, 'frozen', False):
    bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
    from kivy.resources import resource_add_path
    resource_add_path(bundle_dir)
    resource_add_path(os.path.join(bundle_dir, 'data'))
    resource_add_path(os.path.join(bundle_dir, 'data', 'images'))

os.environ['KIVY_GL_BACKEND'] = 'sdl2'
from threading import Thread

from kivymd.app import MDApp
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, NoTransition

# Licensing imports
from licensing.license_guard import LicenseGuard
from licensing.activation_dialog import ActivationDialog

# Domain & State imports
from engine.core.scene import SceneConfig
from engine.core.project import StructureType
from ui.state.project_state import ProjectState, AppPhase

# UI Services
from ui.services import (
    SettingsRepository,
    NativeDialogService,
    AnalysisWorkflowService,
    RenderWorkflowService,
    read_image_unicode
)

# Presentation Screens
from ui.screens.home_screen import HomeScreen
from ui.screens.loading_screen import LoadingScreen
from ui.screens.grid_setup_screen import GridSetupScreen
from ui.screens.scene_screen import SceneScreen
from ui.theme import Theme

__version__ = "0.7.0"


class SketchAnimationApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_keyboard=self._on_keyboard)
        Window.title = "Storyboard to Whiteboard Animation"
        Window.minimum_width = 1024
        Window.minimum_height = 650
        try:
            Window.maximize()
        except Exception:
            pass

        self.state = ProjectState()

        # Paths & Application Services
        home_dir = os.path.expanduser("~")
        self.video_dir = os.path.join(home_dir, "Documents", "image_to_animation")
        self.settings_file = os.path.join(home_dir, ".image_to_animation", "settings.json")
        os.makedirs(self.video_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)

        self.settings_repo = SettingsRepository(self.settings_file)
        self.analysis_service = AnalysisWorkflowService()
        self.render_service = RenderWorkflowService(self.video_dir)

    def load_settings(self):
        """Load user settings from settings repository."""
        return self.settings_repo.load_settings()

    def save_settings(self, config: SceneConfig):
        """Save user settings and propagate to active scenes."""
        self.settings_repo.save_settings(config)
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

        self.sm = ScreenManager(transition=NoTransition())

        self.home_screen = HomeScreen(self)
        self.grid_setup_screen = GridSetupScreen(self)
        self.loading_screen = LoadingScreen(self)
        self.scene_screen = SceneScreen(self)

        self.sm.add_widget(self.home_screen)
        self.sm.add_widget(self.grid_setup_screen)
        self.sm.add_widget(self.loading_screen)
        self.sm.add_widget(self.scene_screen)

        self.state._on_active_object_changed = self._on_selection_changed

        return self.sm

    def on_start(self):
        """Lifecycle on_start handler."""
        try:
            Window.maximize()
        except Exception:
            pass

    def _show_activation_dialog(self, error_msg: str = ""):
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

    def go_to_grid_setup(self):
        if self.state.source_image_path and os.path.exists(self.state.source_image_path):
            self.sm.current = "grid_setup"

    # ════════════════════════════════════════════════
    #  Image Selection & Workflow
    # ════════════════════════════════════════════════

    def open_file_chooser(self):
        """Open native file dialog via dialog service."""
        NativeDialogService.open_image_chooser(self.on_image_selected)

    def on_image_selected(self, path: str):
        """Called when user picks an image."""
        if not path or not os.path.exists(path):
            return

        if not LicenseGuard.is_session_active():
            is_valid, msg, token = LicenseGuard.verify_startup_online()
            if not is_valid:
                self._show_activation_dialog(msg)
                return

        self.state.source_image_path = path
        # Seamlessly load into interactive Grid Setup / Panel Review screen
        self.grid_setup_screen.load_image_for_setup(path)
        self.sm.current = "grid_setup"

    def start_extraction_workflow(self, path: str, custom_panels=None):
        """Called when user confirms panels in GridSetupScreen or triggers extraction."""
        self.state.source_image_path = path
        self.state.set_phase(AppPhase.ANALYZING)

        self.sm.current = "loading"
        self.loading_screen.set_progress(0, "Analyzing composition & extracting layers...")

        s = self.load_settings()
        config = SceneConfig(
            width=s.get("width", 1920),
            height=s.get("height", 1080),
            fps=s.get("fps", 30),
            detail_level=s.get("detail_level", "HIGH"),
            color_palette_size=min(32, s.get("color_palette_size", 28)),
            drawing_speed=s.get("drawing_speed", 1.5),
            character_drawing_speed=s.get("character_drawing_speed", s.get("drawing_speed", 1.5)),
            text_drawing_speed=s.get("text_drawing_speed", s.get("drawing_speed", 1.5)),
            camera_zoom_scale=s.get("camera_zoom_scale", 1.40),
            transition_duration=s.get("transition_duration", 0.5),
            min_region_area=24,
            show_hand=s.get("show_hand", True),
            hand_scale=s.get("hand_scale", 0.75),
            deep_mode=bool(s.get("deep_mode", True)),
            suppress_borders=bool(s.get("suppress_borders", True)),
        )

        def _on_progress(pct, stage):
            Clock.schedule_once(lambda dt: self._update_loading(pct, stage))

        def _on_success(img_path, img_bgr, project):
            self.state.source_image = img_bgr
            Clock.schedule_once(lambda dt: self._on_analysis_complete(img_path, project))

        def _on_error(err_msg):
            Clock.schedule_once(lambda dt: self._on_analysis_error(err_msg))

        self.analysis_service.start_analysis_job(
            image_path=path,
            config=config,
            progress_callback=_on_progress,
            on_success_callback=_on_success,
            on_error_callback=_on_error,
            custom_panels=custom_panels
        )

    def _update_loading(self, pct, stage):
        self.loading_screen.set_progress(pct, stage)
        self.state.set_progress(pct, stage)

    def _on_analysis_complete(self, path, project):
        """Called on main thread after analysis finishes."""
        try:
            self.state.set_project(project)
            self.state.set_phase(AppPhase.READY)
            self.scene_screen.load_project(path, project)
            self.sm.current = "scene"
            print("  [SUCCESS] Transition to SceneScreen successful!", flush=True)
        except Exception as e:
            import traceback
            print(f"[CRITICAL ERROR in _on_analysis_complete]: {e}", flush=True)
            traceback.print_exc()

    def _on_analysis_error(self, err_msg):
        self.loading_screen.set_progress(0, f"Error: {err_msg}")
        Clock.schedule_once(lambda dt: setattr(self.sm, 'current', 'home'), 3.0)

    # ════════════════════════════════════════════════
    #  Object Selection Sync
    # ════════════════════════════════════════════════

    def on_object_selected(self, target):
        """Called when user taps an object card or canvas element."""
        if isinstance(target, str):
            self.state.set_active_id(target)
        elif isinstance(target, int):
            if 0 <= target < len(self.state.objects):
                self.state.set_active_id(self.state.objects[target].id)
            else:
                self.state.set_active_id(None)

    def _on_selection_changed(self, obj):
        """State callback — sync active object across canvas, inspector, and layers."""
        if hasattr(self, "scene_screen"):
            self.scene_screen._on_active_sync(obj)

    # ════════════════════════════════════════════════
    #  Animation & Video Rendering Workflows
    # ════════════════════════════════════════════════

    def animate_single_object(self, obj):
        """Animate one object only and play live canvas preview."""
        self._start_render_job_for_objects([obj], open_folder=False, progress_title=f"Preparing {obj.name}...")

    def animate_single_panel(self, panel_id: int):
        """Animate only the specified open panel."""
        if not self.state.project:
            return
        p_objs = [o for o in self.state.objects if getattr(o, "panel_id", 1) == panel_id and getattr(o, "visibility", True)]
        if not p_objs:
            if hasattr(self, "_show_toast"):
                self._show_toast(f"No objects in Panel {panel_id:02d}")
            return
        self._start_render_job_for_objects(p_objs, open_folder=False, progress_title=f"Preparing Panel {panel_id:02d} Animation...")

    def export_single_object(self, obj):
        """Export video for one object and open destination folder."""
        self._start_render_job_for_objects([obj], open_folder=True, progress_title=f"Exporting {obj.name}...")

    def animate_all_objects(self):
        """Animate all objects in current project across all panels. Called by ANIMATE ALL hero button."""
        if not self.state.project:
            return
        self._start_render_job_for_objects(self.state.objects, open_folder=False, progress_title="Preparing All Panels Animation...")

    def _start_render_job_for_objects(self, objects, open_folder: bool = False, progress_title: str = "Rendering..."):
        if not self.state.project and not self.state.source_image and not self.state.source_image_path:
            return

        self.sm.current = "loading"
        self.loading_screen.set_progress(0, progress_title)
        self.state.set_phase(AppPhase.ANIMATING)

        src_img = self.state.source_image
        if src_img is None and self.state.source_image_path:
            src_img = read_image_unicode(self.state.source_image_path)
            self.state.source_image = src_img

        if src_img is None:
            self._on_analysis_error("No source image loaded.")
            return

        settings = self.load_settings()
        if self.state.scene and self.state.scene.config:
            cfg = self.state.scene.config
            settings["drawing_speed"] = getattr(cfg, "drawing_speed", settings.get("drawing_speed", 1.5))
            settings["character_drawing_speed"] = getattr(cfg, "character_drawing_speed", settings.get("character_drawing_speed", 1.5))
            settings["text_drawing_speed"] = getattr(cfg, "text_drawing_speed", settings.get("text_drawing_speed", 1.5))
            settings["deep_mode"] = getattr(cfg, "deep_mode", settings.get("deep_mode", True))
        if self.state.project and self.state.project.panels:
            settings["custom_panels"] = self.state.project.panels

        def _on_progress(pct, stage):
            Clock.schedule_once(lambda dt: self._update_loading(pct, stage))

        def _on_complete(out_path):
            Clock.schedule_once(lambda dt: self._on_export_complete(out_path, open_folder=open_folder))

        def _on_error(err_msg):
            Clock.schedule_once(lambda dt: self._on_analysis_error(err_msg))

        self.render_service.start_render_job(
            source_image=src_img,
            settings=settings,
            objects_to_render=objects,
            progress_callback=_on_progress,
            on_complete_callback=_on_complete,
            on_error_callback=_on_error,
            job_prefix=objects[0].name.replace(" ", "_").lower() if len(objects) == 1 else "sketch"
        )

    def _on_export_complete(self, out_path: str, open_folder: bool = False):
        self._show_toast(f"Render Complete: {os.path.basename(out_path)}")
        self.sm.current = "scene"
        self.state.set_phase(AppPhase.READY)

        # 1. Automatically start video preview directly inside the app
        try:
            self.scene_screen.play_video_preview(out_path)
        except Exception as e:
            print(f"Error starting in-app video preview: {e}")

        # 2. Only open folder if user triggered an explicit export
        if open_folder:
            try:
                folder_path = os.path.dirname(out_path)
                if os.name == 'nt':
                    os.startfile(folder_path)
            except Exception as e:
                print(f"Could not open export directory: {e}")

    def open_export_folder(self):
        """Open export directory in system file explorer."""
        try:
            if os.path.exists(self.video_dir) and os.name == 'nt':
                os.startfile(self.video_dir)
        except Exception as e:
            print(f"Could not open export folder: {e}")

    def focus_panel(self, panel_id: int):
        """Focuses and zooms the studio canvas viewport onto a specific panel."""
        if self.state and self.state.project and self.state.project.panels:
            panel = next((p for p in self.state.project.panels if p.id == panel_id), None)
            if panel and self.state.source_image is not None:
                px, py, pw, ph = panel.bbox
                # Select first object in this panel
                p_objs = [o for o in self.state.objects if getattr(o, "panel_id", 1) == panel_id]
                if p_objs:
                    self.state.set_active_id(p_objs[0].id)
                if hasattr(self, "scene_screen") and hasattr(self.scene_screen, "image_preview"):
                    self.scene_screen.image_preview.set_focused_panel(panel_id)
                self._show_toast(f"Switched to Panel {panel_id}")

    def _show_toast(self, msg):
        from kivymd.toast import toast
        try:
            toast(msg)
        except Exception:
            print(f"[Toast]: {msg}")

    # ════════════════════════════════════════════════
    #  Undo / Redo / Shortcuts
    # ════════════════════════════════════════════════

    def undo(self):
        if self.state.undo():
            self._show_toast("Undo")

    def redo(self):
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
        if keyboard in (127, 8):
            if self.state.active_object_id:
                self.state.remove_object_by_id(self.state.active_object_id)
                self._show_toast("Element Deleted")
                return True

        return False


if __name__ == '__main__':
    def _uncaught_excepthook(exctype, value, tb):
        import traceback
        print("[UNCAUGHT SYSTEM EXCEPTION]:", file=sys.stderr)
        traceback.print_exception(exctype, value, tb)

    sys.excepthook = _uncaught_excepthook

    try:
        SketchAnimationApp().run()
    except Exception as e:
        import traceback
        print(f"[FATAL APP CRASH]: {e}", file=sys.stderr)
        traceback.print_exc()


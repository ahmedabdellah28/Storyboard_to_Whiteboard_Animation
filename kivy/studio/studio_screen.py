from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from .theme import StudioTheme
from .components.top_bar import StudioTopBar
from .components.assets_panel import AssetsScenePanel
from .components.preview_viewport import PreviewViewport
from .components.inspector_panel import InspectorPanel
from .components.multitrack_timeline import MultiTrackTimeline
from .components.status_bar import StudioStatusBar


class StudioScreen(MDScreen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.md_bg_color = StudioTheme.BG_ROOT

        # Master Container
        master_box = MDBoxLayout(
            orientation="vertical",
            spacing=0,
            padding=0
        )

        # 1. Top Bar
        self.top_bar = StudioTopBar(self.app)
        master_box.add_widget(self.top_bar)

        # 2. Main Middle Workspace (3 Columns: Assets | Preview | Inspector)
        self.workspace = MDBoxLayout(
            orientation="horizontal",
            spacing=0,
            padding=0,
            size_hint=(1, 1)
        )
        self.assets_panel = AssetsScenePanel(self.app)
        self.preview_viewport = PreviewViewport(self.app)
        self.inspector_panel = InspectorPanel(self.app)

        self.workspace.add_widget(self.assets_panel)
        self.workspace.add_widget(self.preview_viewport)
        self.workspace.add_widget(self.inspector_panel)
        master_box.add_widget(self.workspace)

        # 3. Bottom Multi-Track Timeline
        self.timeline = MultiTrackTimeline(self.app)
        master_box.add_widget(self.timeline)

        # 4. Status Bar
        self.status_bar = StudioStatusBar(self.app)
        master_box.add_widget(self.status_bar)

        self.add_widget(master_box)

    def load_scene_data(self, img_path: str, scene, timeline_obj, shots):
        # Update Assets Panel
        self.assets_panel.update_source_image(img_path, scene.canvas_width, scene.canvas_height)
        self.assets_panel.populate_objects(scene.objects, self.on_object_selected)

        # Update Preview
        self.preview_viewport.viewport_canvas.set_image(img_path)
        self.preview_viewport.set_duration(timeline_obj.duration)

        # Update Inspector
        self.inspector_panel.update_shots(shots)
        if scene.objects:
            first_obj = next((o for o in scene.objects if not o.is_frame), scene.objects[0])
            self.on_object_selected(first_obj)

        # Update Timeline
        self.timeline.update_timeline_data(shots, scene.objects, timeline_obj.duration)

    def on_object_selected(self, obj, toggle_vis=False):
        if not toggle_vis:
            self.assets_panel.select_object(obj)
            self.inspector_panel.inspect_object(obj)
            self.preview_viewport.viewport_canvas.set_selection(obj)

    def on_camera_shot_selected(self, shot):
        self.preview_viewport.viewport_canvas.set_camera_shot(shot)
        self.preview_viewport.seek_to(shot.start_time)
        self.inspector_panel.current_zoom = float(shot.zoom)
        if hasattr(self.inspector_panel, "zoom_slider"):
            self.inspector_panel.zoom_slider.value = shot.zoom
        if hasattr(self.inspector_panel, "zoom_val_lbl"):
            self.inspector_panel.zoom_val_lbl.text = f"{shot.zoom:.2f}x"

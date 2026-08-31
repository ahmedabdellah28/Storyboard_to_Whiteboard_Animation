"""
Scene Screen — Studio 3-Column Workspace with Docked Bottom Transport Bar.
Left: Layers Panel (ObjectList)
Center: Interactive Canvas Viewport (ImagePreview)
Right: Dynamic Property Inspector (InspectorPanel)
Bottom: Permanent Docked Transport & Playback Bar (No overlay clutter)
"""
import os
from engine.core.scene import SceneConfig
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.metrics import dp, sp
from kivy.graphics import Color, Rectangle, Line
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import (
    MDFillRoundFlatIconButton,
    MDRoundFlatIconButton,
    MDIconButton,
    MDFlatButton
)
from kivymd.uix.progressbar import MDProgressBar
from ..theme import Theme
from ..widgets.image_preview import ImagePreview
from ..widgets.object_list import ObjectList
from ..widgets.inspector_panel import InspectorPanel
from ..widgets.settings_dialog import SettingsDialog


class SceneScreen(MDScreen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.name = "scene"
        self.app = app_ref
        self.md_bg_color = Theme.BG_ROOT

        root = MDBoxLayout(orientation="vertical", spacing=0)

        # ═════════════════════════════════════════════════════════════════════
        #  1. Top Studio Header Bar
        # ═════════════════════════════════════════════════════════════════════
        top_bar = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(Theme.TOP_BAR_HEIGHT),
            padding=[dp(12), dp(6), dp(12), dp(6)],
            spacing=dp(8),
            md_bg_color=Theme.BG_PANEL
        )
        with top_bar.canvas.before:
            Color(rgba=Theme.BG_PANEL)
            self._tb_bg = Rectangle(pos=top_bar.pos, size=top_bar.size)
            Color(rgba=Theme.BORDER)
            self._tb_border = Line(points=[top_bar.x, top_bar.y, top_bar.x + top_bar.width, top_bar.y], width=1.0)
        top_bar.bind(pos=self._update_top_bar_bg, size=self._update_top_bar_bg)

        # Back Navigation
        back_btn = MDIconButton(
            icon="arrow-left",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.app.go_home()
        )
        top_bar.add_widget(back_btn)

        # Logo & App Title
        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "images", "favicon.png")
        if os.path.exists(logo_path):
            from kivy.uix.image import Image
            logo_img = Image(
                source=logo_path,
                size_hint=(None, None),
                size=(dp(24), dp(24)),
                pos_hint={"center_y": 0.5}
            )
            top_bar.add_widget(logo_img)

        title = MDLabel(
            text="STORYBOARD STUDIO",
            font_style="Subtitle1",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            bold=True,
            size_hint_x=None,
            width=dp(180)
        )
        top_bar.add_widget(title)

        # Artwork Filename info
        self.file_info_lbl = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            adaptive_height=True,
            pos_hint={"center_y": 0.5}
        )
        top_bar.add_widget(self.file_info_lbl)

        # Undo & Redo buttons in center-left
        undo_btn = MDIconButton(
            icon="undo-variant",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.app.undo()
        )
        redo_btn = MDIconButton(
            icon="redo-variant",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.app.redo()
        )
        top_bar.add_widget(undo_btn)
        top_bar.add_widget(redo_btn)

        # Spacer
        top_bar.add_widget(Widget())

        # Settings Dialog Button
        self.settings_btn = MDIconButton(
            icon="cog-outline",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.open_settings()
        )
        top_bar.add_widget(self.settings_btn)

        # Export Folder Button
        self.export_btn = MDRoundFlatIconButton(
            text="EXPORTS",
            icon="folder-open-outline",
            theme_text_color="Custom",
            text_color=Theme.HEX_TEXT,
            theme_icon_color="Custom",
            icon_color=Theme.HEX_TEXT,
            line_color=Theme.BORDER,
            font_size=sp(12),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.app.open_export_folder()
        )
        top_bar.add_widget(self.export_btn)

        # Hero Action: ANIMATE ALL
        self.animate_all_btn = MDFillRoundFlatIconButton(
            text="ANIMATE ALL",
            icon="play-box-multiple",
            theme_text_color="Custom",
            text_color=Theme.HEX_TEXT,
            theme_icon_color="Custom",
            icon_color=Theme.HEX_TEXT,
            md_bg_color=Theme.HEX_ACCENT,
            font_size=sp(13),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.app.animate_all_objects()
        )
        top_bar.add_widget(self.animate_all_btn)

        root.add_widget(top_bar)

        # ═════════════════════════════════════════════════════════════════════
        #  2. Middle 3-Column Studio Workspace (Layers + Canvas + Inspector)
        # ═════════════════════════════════════════════════════════════════════
        workspace = MDBoxLayout(orientation="horizontal", spacing=0, size_hint=(1, 1))

        # Column 1: Left Layers Panel
        self.object_list = ObjectList(self.app, size_hint=(None, 1), width=dp(260))
        workspace.add_widget(self.object_list)

        # Thin separator
        workspace.add_widget(self._create_v_separator())

        # Column 2: Center Interactive Canvas
        self.image_preview = ImagePreview(app_ref=self.app, size_hint=(1, 1))
        workspace.add_widget(self.image_preview)

        # Thin separator
        workspace.add_widget(self._create_v_separator())

        # Column 3: Right Inspector Panel
        self.inspector_panel = InspectorPanel(self.app, size_hint=(None, 1), width=dp(280))
        workspace.add_widget(self.inspector_panel)

        root.add_widget(workspace)

        # ═════════════════════════════════════════════════════════════════════
        #  3. Bottom Docked Transport & Playback Bar
        # ═════════════════════════════════════════════════════════════════════
        self.transport_bar = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(46),
            padding=[dp(16), dp(4), dp(16), dp(4)],
            spacing=dp(10),
            md_bg_color=Theme.BG_PANEL
        )
        with self.transport_bar.canvas.before:
            Color(rgba=Theme.BG_PANEL)
            self._tp_bg = Rectangle(pos=self.transport_bar.pos, size=self.transport_bar.size)
            Color(rgba=Theme.BORDER)
            self._tp_border = Line(points=[self.transport_bar.x, self.transport_bar.y + self.transport_bar.height, self.transport_bar.x + self.transport_bar.width, self.transport_bar.y + self.transport_bar.height], width=1.0)
        self.transport_bar.bind(pos=self._update_tp_bg, size=self._update_tp_bg)

        # Play / Pause button
        self.play_pause_btn = MDIconButton(
            icon="play",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_ACCENT,
            size_hint=(None, None),
            size=(dp(34), dp(34)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._toggle_play_pause()
        )
        self.transport_bar.add_widget(self.play_pause_btn)

        # Replay button
        self.replay_btn = MDIconButton(
            icon="replay",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(34), dp(34)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._replay_video()
        )
        self.transport_bar.add_widget(self.replay_btn)

        # Stop / Return to Canvas Edit button
        self.stop_btn = MDIconButton(
            icon="stop",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(34), dp(34)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._stop_video_preview()
        )
        self.transport_bar.add_widget(self.stop_btn)

        # Progress bar
        self.playback_progress = MDProgressBar(
            value=0,
            max=100,
            size_hint_x=1,
            pos_hint={"center_y": 0.5},
            color=Theme.ACCENT[:3] + [1.0]
        )
        self.transport_bar.add_widget(self.playback_progress)

        # Timecode
        self.timecode_lbl = MDLabel(
            text="00:00 / 00:00",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            size_hint_x=None,
            width=dp(100),
            halign="right",
            pos_hint={"center_y": 0.5}
        )
        self.transport_bar.add_widget(self.timecode_lbl)

        # Frame callback from image_preview
        self.image_preview.on_video_frame_cb = self._on_video_frame

        root.add_widget(self.transport_bar)
        self.add_widget(root)

    def _create_v_separator(self):
        sep = Widget(size_hint=(None, 1), width=dp(1))
        with sep.canvas:
            Color(rgba=Theme.BORDER)
            sep_rect = Rectangle(pos=sep.pos, size=(dp(1), sep.height))
        sep.bind(pos=lambda *a: setattr(sep_rect, 'pos', sep.pos),
                 size=lambda *a: setattr(sep_rect, 'size', (dp(1), sep.height)))
        return sep

    def _update_top_bar_bg(self, *args):
        self._tb_bg.pos = self.children[0].children[-1].pos
        self._tb_bg.size = self.children[0].children[-1].size
        self._tb_border.points = [self._tb_bg.pos[0], self._tb_bg.pos[1], self._tb_bg.pos[0] + self._tb_bg.size[0], self._tb_bg.pos[1]]

    def _update_tp_bg(self, *args):
        self._tp_bg.pos = self.transport_bar.pos
        self._tp_bg.size = self.transport_bar.size
        self._tp_border.points = [self.transport_bar.x, self.transport_bar.y + self.transport_bar.height, self.transport_bar.x + self.transport_bar.width, self.transport_bar.y + self.transport_bar.height]

    def load_project(self, image_path, project):
        """Called after image analysis completes."""
        self.image_preview.set_image(image_path)
        base_name = os.path.basename(image_path)
        self.file_info_lbl.text = f"•  {base_name}"

        all_objects = []
        if project and project.scenes:
            for scene in project.scenes:
                for o in scene.objects:
                    if not o.is_frame:
                        if getattr(o, "scene_source_image", None) is None:
                            o.scene_source_image = self.app.state.source_image
                        all_objects.append(o)

            structure_type = project.structure_type.value if project.structure_type else "SINGLE_SCENE"
            self.object_list.populate(all_objects, self.app.state.source_image,
                                      structure_type=structure_type, project=project)

        # Wire active object sync and objects list sync between layers, inspector, and canvas
        self.app.state._on_active_object_changed = self._on_active_sync
        self.app.state._on_objects_changed = self._on_objects_sync
        self.inspector_panel.refresh()
        self.image_preview.redraw_overlays()

    def _on_active_sync(self, active_obj):
        # When selecting an object while video is playing/loaded, return to canvas edit mode
        if active_obj and (getattr(self.image_preview, "_is_playing", False) or self.image_preview._cap is not None):
            self.image_preview.stop_video()
            self.play_pause_btn.icon = "play"

        self.object_list.update_active_selection(active_obj)
        self.inspector_panel.refresh()
        self.image_preview.redraw_overlays()

    def _on_objects_sync(self, objects):
        structure_type = "SINGLE_SCENE"
        if self.app.state.project and self.app.state.project.structure_type:
            structure_type = self.app.state.project.structure_type.value

        self.object_list.populate(
            objects,
            self.app.state.source_image,
            structure_type=structure_type,
            project=self.app.state.project
        )
        self.inspector_panel.refresh()
        self.image_preview.redraw_overlays()

    def play_video_preview(self, video_path: str):
        self.image_preview.play_video(video_path)
        self.play_pause_btn.icon = "pause"

    def _toggle_play_pause(self):
        self.image_preview.toggle_play_pause()
        self.play_pause_btn.icon = "pause" if self.image_preview._is_playing else "play"

    def _replay_video(self):
        self.image_preview.replay_video()
        self.play_pause_btn.icon = "pause"

    def _stop_video_preview(self):
        self.image_preview.stop_video()
        self.play_pause_btn.icon = "play"
        self.playback_progress.value = 0
        self.timecode_lbl.text = "00:00 / 00:00"

    def _on_video_frame(self, pct, cur_f, tot_f):
        self.playback_progress.value = int(pct * 100)
        fps = getattr(self.image_preview, "_fps", 30.0) or 30.0
        cur_sec = int(cur_f / fps)
        tot_sec = int(tot_f / fps)
        self.timecode_lbl.text = f"{cur_sec//60:02d}:{cur_sec%60:02d} / {tot_sec//60:02d}:{tot_sec%60:02d}"

    def open_settings(self):
        s = self.app.load_settings()
        cfg = SceneConfig(
            width=int(s.get("width", 1920)),
            height=int(s.get("height", 1080)),
            fps=int(s.get("fps", 30)),
            detail_level=s.get("detail_level", "HIGH"),
            color_palette_size=max(8, int(s.get("color_palette_size", 28))),
            drawing_speed=float(s.get("drawing_speed", 1.5)),
            camera_zoom_scale=float(s.get("camera_zoom_scale", 2.0)),
            transition_duration=float(s.get("transition_duration", 0.5)),
            min_region_area=24,
            show_hand=bool(s.get("show_hand", True)),
            hand_scale=float(s.get("hand_scale", 0.75)),
            element_spacing=int(s.get("element_spacing", 24)),
            drawing_direction=str(s.get("drawing_direction", "OUTSIDE_IN")),
            ring_step=int(s.get("ring_step", 5)),
            brush_radius=int(s.get("brush_radius", 8)),
            sample_interval=float(s.get("sample_interval", 3.0)),
            end_hold_seconds=float(s.get("end_hold_seconds", 1.5))
        )

        def _on_save(updated_cfg):
            self.app.save_settings(updated_cfg)
            self.app._show_toast("Settings saved successfully!")

        dialog = SettingsDialog(cfg, on_save_callback=_on_save)
        dialog.open()

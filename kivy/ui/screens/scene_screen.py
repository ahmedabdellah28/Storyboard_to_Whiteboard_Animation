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
        self.top_bar = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(Theme.TOP_BAR_HEIGHT),
            padding=[dp(12), dp(6), dp(12), dp(6)],
            spacing=dp(8),
            md_bg_color=Theme.BG_PANEL
        )
        with self.top_bar.canvas.before:
            Color(rgba=Theme.BG_PANEL)
            self._tb_bg = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
            Color(rgba=Theme.BORDER)
            self._tb_border = Rectangle(pos=(self.top_bar.x, self.top_bar.y), size=(self.top_bar.width, dp(1)))
        self.top_bar.bind(pos=self._update_top_bar_bg, size=self._update_top_bar_bg)

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
        self.top_bar.add_widget(back_btn)

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
            self.top_bar.add_widget(logo_img)

        title = MDLabel(
            text="STORYBOARD STUDIO",
            font_style="Subtitle1",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            bold=True,
            size_hint_x=None,
            width=dp(180)
        )
        self.top_bar.add_widget(title)

        # Artwork Filename info
        self.file_info_lbl = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            adaptive_height=True,
            pos_hint={"center_y": 0.5}
        )
        self.top_bar.add_widget(self.file_info_lbl)

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
        self.top_bar.add_widget(undo_btn)
        self.top_bar.add_widget(redo_btn)

        # Spacer
        self.top_bar.add_widget(Widget())

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
        self.top_bar.add_widget(self.settings_btn)

        # Edit Grid / Panels Button
        self.grid_btn = MDRoundFlatIconButton(
            text="PANELS",
            icon="grid-large",
            theme_text_color="Custom",
            text_color=Theme.HEX_CYAN,
            theme_icon_color="Custom",
            icon_color=Theme.HEX_CYAN,
            line_color=Theme.BORDER,
            font_size=sp(12),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.app.go_to_grid_setup()
        )
        self.top_bar.add_widget(self.grid_btn)

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
        self.top_bar.add_widget(self.export_btn)

        # Quality / Resolution Tier Selector (720p Default vs 1080p Full HD vs 4K)
        s_init = self.app.load_settings()
        cur_w = int(s_init.get("width", 1280))
        cur_h = int(s_init.get("height", 720))

        if cur_w >= 3840 or cur_h >= 2160:
            init_qual = "4K Cinema"
        elif cur_w >= 1920 or cur_h >= 1080:
            init_qual = "1080p FHD"
        else:
            init_qual = "720p HD"

        if cur_h > cur_w * 1.15:
            init_ratio = "9:16 (TikTok/Reels)"
        elif 0.85 <= cur_w / float(cur_h) <= 1.15:
            init_ratio = "1:1 (Instagram)"
        elif cur_w == 1440 or cur_w == 960:
            init_ratio = "4:3 (Classic)"
        elif (cur_w == 1080 and cur_h == 1350) or (cur_w == 720 and cur_h == 900):
            init_ratio = "4:5 (Feed)"
        else:
            init_ratio = "16:9 (YouTube)"

        from kivy.uix.spinner import Spinner

        # 1. Quality Spinner
        self.quality_spinner = Spinner(
            text=init_qual,
            values=(
                "720p HD",
                "1080p FHD",
                "4K Cinema"
            ),
            size_hint=(None, None),
            size=(dp(105), dp(34)),
            background_color=Theme.BG_CARD,
            color=Theme.HEX_CYAN,
            pos_hint={"center_y": 0.5}
        )
        self.quality_spinner.bind(text=self._on_quality_selected)
        self.top_bar.add_widget(self.quality_spinner)

        # 2. Aspect Ratio Preset Selector
        self.ratio_spinner = Spinner(
            text=init_ratio,
            values=(
                "16:9 (YouTube)",
                "9:16 (TikTok/Reels)",
                "1:1 (Instagram)",
                "4:5 (Feed)",
                "4:3 (Classic)"
            ),
            size_hint=(None, None),
            size=(dp(155), dp(34)),
            background_color=Theme.BG_CARD,
            color=Theme.TEXT,
            pos_hint={"center_y": 0.5}
        )
        self.ratio_spinner.bind(text=self._on_ratio_preset_selected)
        self.top_bar.add_widget(self.ratio_spinner)

        # Deep Mode Toggle Action Button
        self.is_deep_active = bool(s_init.get("deep_mode", True))
        self.deep_mode_btn = MDRoundFlatIconButton(
            text=f"DEEP MODE: {'ON' if self.is_deep_active else 'OFF'}",
            icon="creation" if self.is_deep_active else "creation-outline",
            theme_text_color="Custom",
            text_color=Theme.ACCENT_CYAN if self.is_deep_active else Theme.TEXT_SECONDARY,
            theme_icon_color="Custom",
            icon_color=Theme.ACCENT_CYAN if self.is_deep_active else Theme.TEXT_SECONDARY,
            line_color=Theme.ACCENT_CYAN if self.is_deep_active else Theme.BORDER,
            font_size=sp(12),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._toggle_deep_mode()
        )
        self.top_bar.add_widget(self.deep_mode_btn)

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
        self.top_bar.add_widget(self.animate_all_btn)

        root.add_widget(self.top_bar)

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
            self._tp_border = Rectangle(pos=(self.transport_bar.x, self.transport_bar.y + self.transport_bar.height - dp(1)), size=(self.transport_bar.width, dp(1)))
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
        if hasattr(self, "top_bar") and hasattr(self, "_tb_bg"):
            self._tb_bg.pos = self.top_bar.pos
            self._tb_bg.size = self.top_bar.size
            self._tb_border.pos = (self.top_bar.x, self.top_bar.y)
            self._tb_border.size = (self.top_bar.width, dp(1))

    def _update_tp_bg(self, *args):
        if hasattr(self, "transport_bar") and hasattr(self, "_tp_bg"):
            self._tp_bg.pos = self.transport_bar.pos
            self._tp_bg.size = self.transport_bar.size
            self._tp_border.pos = (self.transport_bar.x, self.transport_bar.y + self.transport_bar.height - dp(1))
            self._tp_border.size = (self.transport_bar.width, dp(1))

    def load_project(self, image_path, project):
        """Called after image analysis completes."""
        print("  [load_project] 1. Setting filename...", flush=True)
        base_name = os.path.basename(image_path)
        self.file_info_lbl.text = f"•  {base_name}"

        all_objects = []
        if project and project.scenes:
            print(f"  [load_project] 2. Extracting objects from {len(project.scenes)} scenes...", flush=True)
            for scene in project.scenes:
                for o in scene.objects:
                    if not o.is_frame:
                        if getattr(o, "scene_source_image", None) is None:
                            o.scene_source_image = self.app.state.source_image
                        all_objects.append(o)

            structure_type = project.structure_type.value if project.structure_type else "SINGLE_SCENE"
            print(f"  [load_project] 3. Populating object_list with {len(all_objects)} objects...", flush=True)
            self.object_list.populate(all_objects, self.app.state.source_image,
                                      structure_type=structure_type, project=project)
            print("  [load_project] 3b. object_list populated successfully!", flush=True)

        print("  [load_project] 4. Setting image_preview...", flush=True)
        self.image_preview.set_image(image_path)
        print("  [load_project] 4b. image_preview set successfully!", flush=True)

        # Wire active object sync and objects list sync between layers, inspector, and canvas
        self.app.state._on_active_object_changed = self._on_active_sync
        self.app.state._on_objects_changed = self._on_objects_sync
        print("  [load_project] 5. Refreshing inspector...", flush=True)
        self.inspector_panel.refresh()
        print("  [load_project] 6. Redrawing overlays...", flush=True)
        self.image_preview.redraw_overlays()
        print("  [load_project] 7. load_project complete!", flush=True)

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

    def _on_quality_selected(self, spinner, text):
        s = self.app.load_settings()
        cur_ratio = self.ratio_spinner.text if hasattr(self, "ratio_spinner") else "16:9"

        if "1080p" in text:
            qual_label = "1080p Full HD"
            if "9:16" in cur_ratio:
                w, h = 1080, 1920
            elif "1:1" in cur_ratio:
                w, h = 1080, 1080
            elif "4:5" in cur_ratio:
                w, h = 1080, 1350
            elif "4:3" in cur_ratio:
                w, h = 1440, 1080
            else: # 16:9
                w, h = 1920, 1080
        elif "4K" in text:
            qual_label = "4K Cinema"
            if "9:16" in cur_ratio:
                w, h = 2160, 3840
            elif "1:1" in cur_ratio:
                w, h = 2160, 2160
            elif "4:5" in cur_ratio:
                w, h = 2160, 2700
            elif "4:3" in cur_ratio:
                w, h = 2880, 2160
            else: # 16:9
                w, h = 3840, 2160
        else: # 720p HD Default
            qual_label = "720p HD (Default)"
            if "9:16" in cur_ratio:
                w, h = 720, 1280
            elif "1:1" in cur_ratio:
                w, h = 720, 720
            elif "4:5" in cur_ratio:
                w, h = 720, 900
            elif "4:3" in cur_ratio:
                w, h = 960, 720
            else: # 16:9
                w, h = 1280, 720

        s["width"] = w
        s["height"] = h

        if self.app.state.scene and self.app.state.scene.config:
            self.app.state.scene.config.width = w
            self.app.state.scene.config.height = h
            self.app.save_settings(self.app.state.scene.config)
        else:
            cfg = SceneConfig(**{k: v for k, v in s.items() if hasattr(SceneConfig, k)})
            cfg.width = w
            cfg.height = h
            self.app.save_settings(cfg)

        self.app._show_toast(f"Video Quality: {qual_label} ({w}x{h})")

    def _on_ratio_preset_selected(self, spinner, text):
        s = self.app.load_settings()
        qual_text = self.quality_spinner.text if hasattr(self, "quality_spinner") else "720p HD"
        is_1080p = "1080p" in qual_text
        is_4k = "4K" in qual_text

        if is_4k:
            if "9:16" in text:
                w, h = 2160, 3840
                label = "9:16 TikTok / Reels (2160x3840)"
            elif "1:1" in text:
                w, h = 2160, 2160
                label = "1:1 Instagram Square (2160x2160)"
            elif "4:5" in text:
                w, h = 2160, 2700
                label = "4:5 Portrait Feed (2160x2700)"
            elif "4:3" in text:
                w, h = 2880, 2160
                label = "4:3 Classic (2880x2160)"
            else:
                w, h = 3840, 2160
                label = "16:9 Cinema 4K (3840x2160)"
        elif is_1080p:
            if "9:16" in text:
                w, h = 1080, 1920
                label = "9:16 TikTok / Reels FHD (1080x1920)"
            elif "1:1" in text:
                w, h = 1080, 1080
                label = "1:1 Instagram Square FHD (1080x1080)"
            elif "4:5" in text:
                w, h = 1080, 1350
                label = "4:5 Portrait Feed FHD (1080x1350)"
            elif "4:3" in text:
                w, h = 1440, 1080
                label = "4:3 Classic FHD (1440x1080)"
            else:
                w, h = 1920, 1080
                label = "16:9 YouTube Full HD (1920x1080)"
        else: # 720p HD Default
            if "9:16" in text:
                w, h = 720, 1280
                label = "9:16 TikTok / Reels (720x1280)"
            elif "1:1" in text:
                w, h = 720, 720
                label = "1:1 Instagram Square (720x720)"
            elif "4:5" in text:
                w, h = 720, 900
                label = "4:5 Portrait Feed (720x900)"
            elif "4:3" in text:
                w, h = 960, 720
                label = "4:3 Classic (960x720)"
            else:
                w, h = 1280, 720
                label = "16:9 YouTube HD (1280x720)"

        s["width"] = w
        s["height"] = h

        if self.app.state.scene and self.app.state.scene.config:
            self.app.state.scene.config.width = w
            self.app.state.scene.config.height = h
            self.app.save_settings(self.app.state.scene.config)
        else:
            cfg = SceneConfig(**{k: v for k, v in s.items() if hasattr(SceneConfig, k)})
            cfg.width = w
            cfg.height = h
            self.app.save_settings(cfg)

        self.app._show_toast(f"Platform Aspect Ratio: {label}")

    def _toggle_deep_mode(self):
        s = self.app.load_settings()
        cur = bool(s.get("deep_mode", True))
        new_val = not cur
        s["deep_mode"] = new_val

        if self.app.state.scene and self.app.state.scene.config:
            self.app.state.scene.config.deep_mode = new_val
            self.app.save_settings(self.app.state.scene.config)
        else:
            cfg = SceneConfig(**{k: v for k, v in s.items() if hasattr(SceneConfig, k)})
            cfg.deep_mode = new_val
            self.app.save_settings(cfg)

        self.is_deep_active = new_val
        self._update_deep_mode_btn_ui()
        status_str = "ENABLED (Dynamic 6-Stage Organic Pipeline)" if new_val else "DISABLED (Classic Orbital Engine)"
        self.app._show_toast(f"Deep Mode {status_str}")

    def _update_deep_mode_btn_ui(self):
        self.deep_mode_btn.text = f"DEEP MODE: {'ON' if self.is_deep_active else 'OFF'}"
        self.deep_mode_btn.icon = "creation" if self.is_deep_active else "creation-outline"
        self.deep_mode_btn.text_color = Theme.ACCENT_CYAN if self.is_deep_active else Theme.TEXT_SECONDARY
        self.deep_mode_btn.icon_color = Theme.ACCENT_CYAN if self.is_deep_active else Theme.TEXT_SECONDARY
        self.deep_mode_btn.line_color = Theme.ACCENT_CYAN if self.is_deep_active else Theme.BORDER

    def open_settings(self):
        s = self.app.load_settings()
        active_cfg = getattr(self.app.state.scene, "config", None) if self.app.state.scene else None

        cfg = SceneConfig(
            width=int(getattr(active_cfg, "width", s.get("width", 1920))),
            height=int(getattr(active_cfg, "height", s.get("height", 1080))),
            fps=int(getattr(active_cfg, "fps", s.get("fps", 30))),
            detail_level=getattr(active_cfg, "detail_level", s.get("detail_level", "HIGH")),
            color_palette_size=max(8, int(getattr(active_cfg, "color_palette_size", s.get("color_palette_size", 28)))),
            drawing_speed=float(getattr(active_cfg, "drawing_speed", s.get("drawing_speed", 1.5))),
            character_drawing_speed=float(getattr(active_cfg, "character_drawing_speed", s.get("character_drawing_speed", s.get("drawing_speed", 1.5)))),
            text_drawing_speed=float(getattr(active_cfg, "text_drawing_speed", s.get("text_drawing_speed", s.get("drawing_speed", 1.5)))),
            camera_zoom_scale=float(getattr(active_cfg, "camera_zoom_scale", s.get("camera_zoom_scale", 1.40))),
            transition_duration=float(getattr(active_cfg, "transition_duration", s.get("transition_duration", 0.5))),
            min_region_area=24,
            show_hand=bool(getattr(active_cfg, "show_hand", s.get("show_hand", True))),
            hand_scale=float(getattr(active_cfg, "hand_scale", s.get("hand_scale", 0.75))),
            element_spacing=int(getattr(active_cfg, "element_spacing", s.get("element_spacing", 24))),
            drawing_direction=str(getattr(active_cfg, "drawing_direction", s.get("drawing_direction", "OUTSIDE_IN"))),
            ring_step=int(getattr(active_cfg, "ring_step", s.get("ring_step", 5))),
            brush_radius=int(getattr(active_cfg, "brush_radius", s.get("brush_radius", 8))),
            sample_interval=float(getattr(active_cfg, "sample_interval", s.get("sample_interval", 3.0))),
            end_hold_seconds=float(getattr(active_cfg, "end_hold_seconds", s.get("end_hold_seconds", 1.5))),
            deep_mode=bool(getattr(active_cfg, "deep_mode", s.get("deep_mode", True))),
            suppress_borders=bool(getattr(active_cfg, "suppress_borders", s.get("suppress_borders", True)))
        )

        def _on_save(updated_cfg):
            self.app.save_settings(updated_cfg)
            self.is_deep_active = updated_cfg.deep_mode
            self._update_deep_mode_btn_ui()
            self.app._show_toast(f"Speed: Chars {updated_cfg.character_drawing_speed:g}x | Text {updated_cfg.text_drawing_speed:g}x")

        dialog = SettingsDialog(cfg, on_save_callback=_on_save)
        dialog.open()

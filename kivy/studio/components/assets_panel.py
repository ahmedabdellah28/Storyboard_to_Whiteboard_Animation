import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from ..theme import StudioTheme


class SceneObjectCard(MDCard):
    def __init__(self, obj, index, total_count, on_select_cb, on_reorder_cb, **kwargs):
        super().__init__(**kwargs)
        self.obj = obj
        self.index = index
        self.total_count = total_count
        self.on_select_cb = on_select_cb
        self.on_reorder_cb = on_reorder_cb
        self.is_selected = False
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = dp(68)
        self.padding = [dp(8), dp(6), dp(8), dp(6)]
        self.spacing = dp(4)
        self.radius = [dp(6)]
        self.elevation = 0
        self.md_bg_color = StudioTheme.BG_CARD
        self.line_color = StudioTheme.BORDER_SUBTLE

        self._build_content()

    def _build_content(self):
        row = MDBoxLayout(orientation="horizontal", spacing=dp(6), adaptive_height=True)

        # 1. Reorder buttons (Move Up / Down)
        reorder_box = MDBoxLayout(orientation="vertical", size_hint=(None, None), size=(dp(22), dp(52)), spacing=0)
        btn_up = MDIconButton(
            icon="chevron-up",
            theme_icon_color="Custom",
            icon_color=StudioTheme.TEXT_SECONDARY if self.index > 0 else StudioTheme.TEXT_MUTED,
            icon_size=sp(16),
            size_hint=(None, None),
            size=(dp(22), dp(24)),
            disabled=(self.index == 0),
            on_release=lambda x: self.on_reorder_cb(self.index, -1)
        )
        btn_down = MDIconButton(
            icon="chevron-down",
            theme_icon_color="Custom",
            icon_color=StudioTheme.TEXT_SECONDARY if self.index < self.total_count - 1 else StudioTheme.TEXT_MUTED,
            icon_size=sp(16),
            size_hint=(None, None),
            size=(dp(22), dp(24)),
            disabled=(self.index >= self.total_count - 1),
            on_release=lambda x: self.on_reorder_cb(self.index, 1)
        )
        reorder_box.add_widget(btn_up)
        reorder_box.add_widget(btn_down)
        row.add_widget(reorder_box)

        # 2. Icon based on object name
        icon_name = "account-outline"
        name_lower = self.obj.name.lower()
        if "lock" in name_lower:
            icon_name = "lock-outline"
        elif "frame" in name_lower:
            icon_name = "crop-landscape"
        elif "pedestal" in name_lower or "stone" in name_lower:
            icon_name = "podium"

        icon = MDIconButton(
            icon=icon_name,
            theme_icon_color="Custom",
            icon_color=StudioTheme.ACCENT_PRIMARY if not self.obj.is_frame else StudioTheme.TEXT_MUTED,
            icon_size=sp(20),
            size_hint=(None, None),
            size=(dp(26), dp(26))
        )
        row.add_widget(icon)

        # 3. Details text
        text_box = MDBoxLayout(orientation="vertical", spacing=dp(1))
        lbl_name = MDLabel(
            text=f"#{self.index+1}  {self.obj.name}",
            font_style="Subtitle2",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_PRIMARY,
            bold=True,
            adaptive_height=True
        )
        total_strokes = len(self.obj.strokes) + len(self.obj.details)
        total_fills = len(self.obj.fills)
        lbl_info = MDLabel(
            text=f"{self.obj.duration:.1f}s • {total_strokes} strokes • {total_fills} fills",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_SECONDARY,
            adaptive_height=True
        )
        text_box.add_widget(lbl_name)
        text_box.add_widget(lbl_info)
        row.add_widget(text_box)

        # 4. Visibility button
        vis_btn = MDIconButton(
            icon="eye" if self.obj.visibility else "eye-off",
            theme_icon_color="Custom",
            icon_color=StudioTheme.TEXT_SECONDARY,
            icon_size=sp(18),
            size_hint=(None, None),
            size=(dp(26), dp(26)),
            on_release=self._toggle_visibility
        )
        row.add_widget(vis_btn)

        self.add_widget(row)

    def _toggle_visibility(self, *args):
        self.obj.visibility = not self.obj.visibility
        self.on_select_cb(self.obj, toggle_vis=True)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.on_select_cb(self.obj)
            return True
        return super().on_touch_down(touch)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.md_bg_color = StudioTheme.BG_CARD_HOVER
            self.line_color = StudioTheme.BORDER_FOCUSED
        else:
            self.md_bg_color = StudioTheme.BG_CARD
            self.line_color = StudioTheme.BORDER_SUBTLE


class AssetsScenePanel(MDBoxLayout):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.orientation = "vertical"
        self.size_hint_x = None
        self.width = dp(StudioTheme.SIDE_PANEL_WIDTH + 15)
        self.padding = [dp(10), dp(10), dp(10), dp(10)]
        self.spacing = dp(10)
        self.md_bg_color = StudioTheme.BG_PANEL

        with self.canvas.before:
            Color(rgba=[0.086, 0.098, 0.125, 1])
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(rgba=[0.15, 0.17, 0.22, 1])
            self.border_right = Rectangle(pos=(self.right - dp(1), self.y), size=(dp(1), self.height))

        self.bind(pos=self._update_canvas, size=self._update_canvas)

        self.object_cards = []
        self.current_content_objs = []
        self._build_ui()

    def _update_canvas(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_right.pos = (self.right - dp(1), self.y)
        self.border_right.size = (dp(1), self.height)

    def _build_ui(self):
        # 1. Header
        header = MDLabel(
            text="PROJECT ASSETS",
            font_style="Overline",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_MUTED,
            adaptive_height=True,
            bold=True
        )
        self.add_widget(header)

        # 2. Source Image Card
        self.source_card = MDCard(
            orientation="vertical",
            size_hint_y=None,
            height=dp(130),
            padding=dp(6),
            spacing=dp(4),
            radius=[dp(8)],
            md_bg_color=StudioTheme.BG_CARD,
            line_color=StudioTheme.BORDER_SUBTLE
        )
        self.source_thumb = Image(
            source="",
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 0.75)
        )
        self.source_info_lbl = MDLabel(
            text="No image imported",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_SECONDARY,
            halign="center",
            adaptive_height=True
        )
        self.source_card.add_widget(self.source_thumb)
        self.source_card.add_widget(self.source_info_lbl)
        self.add_widget(self.source_card)

        # 3. Scene Objects Header
        objects_hdr_box = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        objects_hdr = MDLabel(
            text="SCENE ORDER (▲/▼ REORDER)",
            font_style="Overline",
            theme_text_color="Custom",
            text_color=StudioTheme.TEXT_MUTED,
            adaptive_height=True,
            bold=True
        )
        self.count_badge = MDLabel(
            text="0",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=StudioTheme.ACCENT_PRIMARY,
            halign="right",
            adaptive_height=True,
            bold=True
        )
        objects_hdr_box.add_widget(objects_hdr)
        objects_hdr_box.add_widget(self.count_badge)
        self.add_widget(objects_hdr_box)

        # 4. Scrollable Scene Objects List
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.objects_list_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(6),
            adaptive_height=True
        )
        self.scroll.add_widget(self.objects_list_box)
        self.add_widget(self.scroll)

    def update_source_image(self, img_path: str, width: int = 1920, height: int = 1080):
        if os.path.exists(img_path):
            self.source_thumb.source = img_path
            self.source_thumb.reload()
            fname = os.path.basename(img_path)
            self.source_info_lbl.text = f"{width}×{height} • {fname[:20]}"

    def populate_objects(self, scene_objects, on_select_cb):
        self.on_select_cb = on_select_cb
        self.current_content_objs = [o for o in scene_objects if not o.is_frame]
        self.count_badge.text = str(len(self.current_content_objs))
        self._refresh_cards()

    def _refresh_cards(self):
        self.objects_list_box.clear_widgets()
        self.object_cards.clear()
        total = len(self.current_content_objs)

        for idx, obj in enumerate(self.current_content_objs):
            card = SceneObjectCard(obj, idx, total, self.on_select_cb, self._on_reorder)
            self.object_cards.append(card)
            self.objects_list_box.add_widget(card)

    def _on_reorder(self, index: int, delta: int):
        new_idx = index + delta
        if 0 <= new_idx < len(self.current_content_objs):
            # Swap items in list
            self.current_content_objs[index], self.current_content_objs[new_idx] = (
                self.current_content_objs[new_idx],
                self.current_content_objs[index]
            )
            self._refresh_cards()
            if self.app:
                self.app.on_scene_objects_reordered(self.current_content_objs)

    def select_object(self, target_obj):
        for card in self.object_cards:
            card.set_selected(card.obj == target_obj)

"""
Inspector Panel — Dynamic studio property inspector.
Displays and edits the properties of the single Active Object.
Provides Empty State when nothing is selected.
"""
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import (
    MDFillRoundFlatIconButton,
    MDRoundFlatIconButton,
    MDIconButton,
    MDFlatButton
)
from kivymd.uix.menu import MDDropdownMenu
from ..theme import Theme


class InspectorPanel(MDBoxLayout):
    """Dynamic properties inspector for the active SceneObject."""

    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.orientation = "vertical"
        self.size_hint = (None, 1)
        self.width = dp(280)
        self.padding = [dp(12), dp(10), dp(12), dp(10)]
        self.spacing = dp(8)
        self.md_bg_color = Theme.BG_PANEL

        with self.canvas.before:
            Color(rgba=Theme.BG_PANEL)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(rgba=Theme.BORDER)
            self._left_border = Rectangle(pos=(self.x, self.y), size=(dp(1), self.height))

        self.bind(pos=self._update_bg, size=self._update_bg)

        # Header Title
        hdr = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(6))
        hdr_icon = MDIconButton(
            icon="tune-variant",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_ACCENT,
            icon_size=sp(18),
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={"center_y": 0.5}
        )
        self.hdr_label = MDLabel(
            text="INSPECTOR",
            font_style="Subtitle2",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            bold=True,
            adaptive_height=True
        )
        hdr.add_widget(hdr_icon)
        hdr.add_widget(self.hdr_label)
        self.add_widget(hdr)

        # Scrollable container for dynamic content
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.content_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            adaptive_height=True,
            padding=[0, dp(4), 0, dp(12)]
        )
        self.scroll.add_widget(self.content_box)
        self.add_widget(self.scroll)

        # Listen to state active object changes
        if self.app and hasattr(self.app, "state"):
            self.app.state._on_active_object_changed = self._on_active_changed
            self.app.state._on_objects_changed = lambda objs: self.refresh()

        self.refresh()

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._left_border.pos = (self.x, self.y)
        self._left_border.size = (dp(1), self.height)

    def _on_active_changed(self, active_obj):
        self.refresh()

    def refresh(self):
        """Redraws or in-place updates the inspector content based on current active_object."""
        active_obj = self.app.state.active_object if self.app and hasattr(self.app, "state") else None
        active_id = active_obj.id if active_obj else None

        # Check if in-place update is possible
        if active_id and active_id == getattr(self, "_active_obj_id", None) and hasattr(self, "_pos_lbl"):
            self._sync_active_state_in_place(active_obj)
            return

        self._active_obj_id = active_id
        self.content_box.clear_widgets()

        if not active_obj:
            self._build_empty_state()
        else:
            self._build_active_state(active_obj)

    def _sync_active_state_in_place(self, obj):
        """Ultra-fast in-place synchronization of inspector fields."""
        # 1. Update Name Input (if not actively being typed into)
        if hasattr(self, "_name_input") and not self._name_input.focus:
            name_txt = obj.name.replace("_", " ")
            if self._name_input.text != name_txt:
                self._name_input.text = name_txt

        # 2. Update BBox Labels
        bbox = obj.global_bbox or obj.bbox or (0, 0, 0, 0)
        bx, by, bw, bh = bbox
        if hasattr(self, "_pos_lbl"):
            self._pos_lbl.text = f"X: {bx} px    Y: {by} px"
        if hasattr(self, "_size_lbl"):
            self._size_lbl.text = f"W: {bw} px    H: {bh} px"

        # 3. Update Speed Button
        if hasattr(self, "_spd_btn"):
            cur_spd = getattr(obj, "speed_multiplier", 1.0)
            self._spd_btn.text = f"{cur_spd:.1f}x"

        # 4. Update Reorder Buttons
        if hasattr(self, "_up_btn") and hasattr(self, "_down_btn"):
            idx = self.app.state.get_object_index(obj.id)
            total_objs = len(self.app.state.objects) if self.app and hasattr(self.app, "state") else 0
            self._up_btn.disabled = (idx <= 0)
            self._down_btn.disabled = (idx >= total_objs - 1)

    def _build_empty_state(self):
        """Empty state displayed when no object is selected."""
        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(8), dp(40), dp(8), dp(20)],
            adaptive_height=True
        )
        icon = MDLabel(
            text="[size=36]--[/size]",
            markup=True,
            font_style="H4",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            halign="center",
            adaptive_height=True
        )
        title = MDLabel(
            text="No Element Selected",
            font_style="Subtitle1",
            theme_text_color="Custom",
            text_color=Theme.TEXT_SECONDARY,
            halign="center",
            adaptive_height=True,
            bold=True
        )
        hint = MDLabel(
            text="Click any element on canvas or in layers list to view and tune its properties.",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            halign="center",
            adaptive_height=True
        )
        box.add_widget(icon)
        box.add_widget(title)
        box.add_widget(hint)
        self.content_box.add_widget(box)

        # Overview stats
        if self.app and hasattr(self.app, "state") and self.app.state.objects:
            stats_box = MDBoxLayout(
                orientation="vertical",
                spacing=dp(6),
                padding=[dp(12), dp(12), dp(12), dp(12)],
                adaptive_height=True
            )
            with stats_box.canvas.before:
                Color(rgba=Theme.BG_CARD)
                self._st_bg = RoundedRectangle(pos=stats_box.pos, size=stats_box.size, radius=[dp(6)])
            stats_box.bind(pos=lambda *a: setattr(self._st_bg, 'pos', stats_box.pos),
                           size=lambda *a: setattr(self._st_bg, 'size', stats_box.size))

            st_title = MDLabel(
                text="STORYBOARD OVERVIEW",
                font_style="Overline",
                theme_text_color="Custom",
                text_color=Theme.TEXT_ACCENT,
                adaptive_height=True,
                bold=True
            )
            count_lbl = MDLabel(
                text=f"Total Elements: {len(self.app.state.objects)}",
                font_style="Body2",
                theme_text_color="Custom",
                text_color=Theme.TEXT,
                adaptive_height=True
            )
            stats_box.add_widget(st_title)
            stats_box.add_widget(count_lbl)
            self.content_box.add_widget(stats_box)

    def _build_active_state(self, obj):
        """Active properties editor for selected object."""
        # 1. Name Editor
        name_card = MDBoxLayout(orientation="vertical", spacing=dp(4), adaptive_height=True)
        name_lbl = MDLabel(
            text="ELEMENT NAME",
            font_style="Overline",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            adaptive_height=True,
            bold=True
        )
        self._name_input = TextInput(
            text=obj.name.replace("_", " "),
            multiline=False,
            size_hint_y=None,
            height=dp(36),
            background_color=Theme.BG_INPUT,
            foreground_color=Theme.TEXT,
            cursor_color=Theme.ACCENT,
            font_size=sp(13),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        self._name_input.bind(text=lambda w, txt: self.app.state.update_object_name(obj.id, txt, record_undo=False))
        name_card.add_widget(name_lbl)
        name_card.add_widget(self._name_input)
        self.content_box.add_widget(name_card)

        # 2. Position & Size (Bounding Box in Pixels)
        bbox = obj.global_bbox or obj.bbox or (0, 0, 0, 0)
        bx, by, bw, bh = bbox

        trans_card = MDBoxLayout(
            orientation="vertical",
            spacing=dp(6),
            padding=[dp(10), dp(10), dp(10), dp(10)],
            adaptive_height=True
        )
        with trans_card.canvas.before:
            Color(rgba=Theme.BG_CARD)
            self._tc_bg = RoundedRectangle(pos=trans_card.pos, size=trans_card.size, radius=[dp(6)])
        trans_card.bind(pos=lambda *a: setattr(self._tc_bg, 'pos', trans_card.pos),
                        size=lambda *a: setattr(self._tc_bg, 'size', trans_card.size))

        trans_title = MDLabel(
            text="BOUNDING BOX (PIXELS)",
            font_style="Overline",
            theme_text_color="Custom",
            text_color=Theme.TEXT_ACCENT,
            adaptive_height=True,
            bold=True
        )
        trans_card.add_widget(trans_title)

        pos_row = MDBoxLayout(orientation="horizontal", spacing=dp(8), adaptive_height=True)
        self._pos_lbl = MDLabel(
            text=f"X: {bx} px    Y: {by} px",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            adaptive_height=True
        )
        pos_row.add_widget(self._pos_lbl)
        trans_card.add_widget(pos_row)

        size_row = MDBoxLayout(orientation="horizontal", spacing=dp(8), adaptive_height=True)
        self._size_lbl = MDLabel(
            text=f"W: {bw} px    H: {bh} px",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            adaptive_height=True
        )
        size_row.add_widget(self._size_lbl)
        trans_card.add_widget(size_row)

        self.content_box.add_widget(trans_card)

        # 3. Animation Tuning
        anim_card = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=[dp(10), dp(10), dp(10), dp(10)],
            adaptive_height=True
        )
        with anim_card.canvas.before:
            Color(rgba=Theme.BG_CARD)
            self._ac_bg = RoundedRectangle(pos=anim_card.pos, size=anim_card.size, radius=[dp(6)])
        anim_card.bind(pos=lambda *a: setattr(self._ac_bg, 'pos', anim_card.pos),
                       size=lambda *a: setattr(self._ac_bg, 'size', anim_card.size))

        anim_title = MDLabel(
            text="ANIMATION CONTROLS",
            font_style="Overline",
            theme_text_color="Custom",
            text_color=Theme.TEXT_ACCENT,
            adaptive_height=True,
            bold=True
        )
        anim_card.add_widget(anim_title)

        # Speed selector
        cur_spd = getattr(obj, "speed_multiplier", 1.0)
        spd_row = MDBoxLayout(orientation="horizontal", spacing=dp(6), adaptive_height=True)
        spd_lbl = MDLabel(
            text="Speed:",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_SECONDARY,
            size_hint_x=0.4
        )
        self._spd_btn = MDFlatButton(
            text=f"{cur_spd:.1f}x",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            font_size=sp(12),
            size_hint_x=0.6,
            on_release=lambda x: self._open_speed_menu(x, obj)
        )
        spd_row.add_widget(spd_lbl)
        spd_row.add_widget(self._spd_btn)
        anim_card.add_widget(spd_row)

        self.content_box.add_widget(anim_card)

        # 4. Order Buttons
        order_box = MDBoxLayout(orientation="horizontal", spacing=dp(8), adaptive_height=True)
        idx = self.app.state.get_object_index(obj.id)
        total_objs = len(self.app.state.objects) if self.app and hasattr(self.app, "state") else 0
        
        self._up_btn = MDRoundFlatIconButton(
            text="UP",
            icon="arrow-up",
            theme_text_color="Custom",
            text_color=Theme.HEX_TEXT,
            theme_icon_color="Custom",
            icon_color=Theme.HEX_TEXT,
            size_hint_x=0.5,
            disabled=(idx <= 0),
            on_release=lambda x: self._move_up(idx)
        )
        self._down_btn = MDRoundFlatIconButton(
            text="DOWN",
            icon="arrow-down",
            theme_text_color="Custom",
            text_color=Theme.HEX_TEXT,
            theme_icon_color="Custom",
            icon_color=Theme.HEX_TEXT,
            size_hint_x=0.5,
            disabled=(idx >= total_objs - 1),
            on_release=lambda x: self._move_down(idx)
        )
        order_box.add_widget(self._up_btn)
        order_box.add_widget(self._down_btn)
        self.content_box.add_widget(order_box)

        # 5. Action Buttons (Duplicate, Delete, Animate Single)
        actions_box = MDBoxLayout(orientation="vertical", spacing=dp(8), adaptive_height=True)

        dup_btn = MDRoundFlatIconButton(
            text="Duplicate Element",
            icon="content-copy",
            theme_text_color="Custom",
            text_color=Theme.HEX_TEXT,
            theme_icon_color="Custom",
            icon_color=Theme.HEX_TEXT,
            size_hint_x=1,
            on_release=lambda x: self.app.state.duplicate_object(obj.id)
        )
        del_btn = MDRoundFlatIconButton(
            text="Delete Element",
            icon="trash-can-outline",
            theme_text_color="Custom",
            text_color=Theme.HEX_DANGER,
            theme_icon_color="Custom",
            icon_color=Theme.HEX_DANGER,
            line_color=Theme.ACCENT_DANGER,
            size_hint_x=1,
            on_release=lambda x: self.app.state.remove_object_by_id(obj.id)
        )
        anim_single_btn = MDFillRoundFlatIconButton(
            text="Animate Element",
            icon="play-circle-outline",
            theme_text_color="Custom",
            text_color=Theme.HEX_TEXT,
            theme_icon_color="Custom",
            icon_color=Theme.HEX_TEXT,
            md_bg_color=Theme.HEX_ACCENT,
            size_hint_x=1,
            on_release=lambda x: self.app.animate_single_object(obj)
        )

        actions_box.add_widget(dup_btn)
        actions_box.add_widget(del_btn)
        actions_box.add_widget(anim_single_btn)
        self.content_box.add_widget(actions_box)

    def _open_speed_menu(self, caller, obj):
        speeds = [0.5, 1.0, 1.5, 2.0, 3.0]
        items = [
            {
                "viewclass": "OneLineListItem",
                "text": f"{s:.1f}x",
                "on_release": lambda v=s: self._set_speed(obj, v),
            } for s in speeds
        ]
        self._speed_menu = MDDropdownMenu(
            caller=caller,
            items=items,
            width_mult=2,
        )
        self._speed_menu.open()

    def _set_speed(self, obj, val):
        if hasattr(self, "_speed_menu"):
            self._speed_menu.dismiss()
        self.app.state.update_object_property(obj.id, "speed_multiplier", val)

    def _move_up(self, idx):
        if idx > 0:
            self.app.state.reorder(idx, idx - 1)

    def _move_down(self, idx):
        if idx < len(self.app.state.objects) - 1:
            self.app.state.reorder(idx, idx + 1)

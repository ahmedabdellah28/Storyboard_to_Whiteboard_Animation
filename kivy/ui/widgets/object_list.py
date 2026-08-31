"""
Object List — Clean, responsive studio layers panel.
Shows objects grouped by panel with collapsible headers.
Supports smooth, in-place drag-and-drop reordering without widget-tree destruction.
"""
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.metrics import dp, sp
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDFlatButton
from .object_card import ObjectCard
from ..theme import Theme


class InsertIndicator(Widget):
    """Visual drop target indicator line."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, None)
        self.height = dp(3)
        with self.canvas:
            Color(rgba=Theme.ACCENT)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class PanelHeader(MDBoxLayout):
    """Collapsible panel header widget."""

    def __init__(self, panel_id, panel_info, on_toggle, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.adaptive_height = True
        self.padding = [dp(8), dp(4), dp(8), dp(4)]
        self.spacing = dp(6)
        self.panel_id = panel_id
        self._collapsed = False
        self._on_toggle = on_toggle

        with self.canvas.before:
            Color(rgba=(0.14, 0.16, 0.22, 1.0))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])
        self.bind(pos=self._update_bg, size=self._update_bg)

        self._toggle_btn = MDIconButton(
            icon="chevron-down",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_ACCENT,
            icon_size=sp(18),
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._toggle()
        )
        self.add_widget(self._toggle_btn)

        label_text = f"Panel {panel_id}"
        if panel_info:
            label_text += f" • {panel_info}"
        self._label = MDLabel(
            text=label_text,
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_ACCENT,
            adaptive_height=True,
            bold=True
        )
        self.add_widget(self._label)

    def _update_bg(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._toggle_btn.icon = "chevron-right" if self._collapsed else "chevron-down"
        if self._on_toggle:
            self._on_toggle(self.panel_id, self._collapsed)


class ObjectList(MDBoxLayout):
    """Studio Layers List with smooth drag-and-drop and Active Object state synchronization."""

    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.orientation = "vertical"
        self.spacing = dp(4)
        self.padding = [dp(8), dp(6), dp(8), dp(6)]
        self.size_hint = (1, 1)

        self.cards = []
        self.source_image = None
        self._panel_card_groups = {}
        self._panel_headers = {}
        self._structure_type = "SINGLE_SCENE"

        # Header
        hdr = MDBoxLayout(orientation="horizontal", adaptive_height=True, padding=[dp(4), dp(2), dp(4), dp(4)])
        self.hdr_label = MDLabel(
            text="LAYERS",
            font_style="Subtitle2",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            adaptive_height=True,
            bold=True
        )
        self.count_label = MDLabel(
            text="0 elements",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            halign="right",
            adaptive_height=True
        )
        hdr.add_widget(self.hdr_label)
        hdr.add_widget(self.count_label)
        self.add_widget(hdr)

        # Scrollable container
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.card_container = MDBoxLayout(
            orientation="vertical",
            spacing=dp(Theme.CARD_SPACING),
            adaptive_height=True,
            padding=[0, 0, 0, dp(12)]
        )
        self.scroll.add_widget(self.card_container)
        self.add_widget(self.scroll)

        # Drag state
        self._dragging = False
        self._drag_from = -1
        self._insert_indicator = InsertIndicator()

    def populate(self, objects, source_image, structure_type="SINGLE_SCENE", project=None):
        """Builds layer cards and groups them by panel."""
        self.source_image = source_image
        self._structure_type = structure_type
        self.card_container.clear_widgets()
        self.cards.clear()
        self._panel_card_groups.clear()
        self._panel_headers.clear()
        self.count_label.text = f"{len(objects)} elements"

        callbacks = {
            "on_select": self._on_card_selected,
            "on_drag_start": self._on_drag_start,
            "on_toggle_visibility": self._on_toggle_visibility
        }

        active_id = self.app.state.active_object_id if self.app and hasattr(self.app, "state") else None

        if structure_type == "STORYBOARD":
            panels_map = {}
            for obj in objects:
                pid = getattr(obj, 'panel_id', 1)
                if pid not in panels_map:
                    panels_map[pid] = []
                panels_map[pid].append(obj)

            global_idx = 0
            for panel_id in sorted(panels_map.keys()):
                panel_objs = panels_map[panel_id]
                info = f"{len(panel_objs)} items"

                header = PanelHeader(
                    panel_id=panel_id,
                    panel_info=info,
                    on_toggle=self._on_panel_toggle
                )
                self._panel_headers[panel_id] = header
                self.card_container.add_widget(header)

                panel_cards = []
                for obj in panel_objs:
                    card = ObjectCard(obj, global_idx, source_image, callbacks)
                    card.set_selected(obj.id == active_id)
                    self.cards.append(card)
                    panel_cards.append(card)
                    self.card_container.add_widget(card)
                    global_idx += 1

                self._panel_card_groups[panel_id] = panel_cards
        else:
            for idx, obj in enumerate(objects):
                card = ObjectCard(obj, idx, source_image, callbacks)
                card.set_selected(obj.id == active_id)
                self.cards.append(card)
                self.card_container.add_widget(card)

    def update_active_selection(self, active_obj):
        """Highlights the active card matching active_obj.id."""
        active_id = active_obj.id if active_obj else None
        for card in self.cards:
            card.set_selected(card.obj.id == active_id)

    def _on_card_selected(self, target):
        if self.app and hasattr(self.app, "state"):
            if isinstance(target, str):
                self.app.state.set_active_id(target)
            elif isinstance(target, int) and 0 <= target < len(self.cards):
                self.app.state.set_active_id(self.cards[target].obj.id)

    def _on_toggle_visibility(self, obj):
        if self.app and hasattr(self.app, "state"):
            self.app.state._notify_active_changed()

    def _on_panel_toggle(self, panel_id, collapsed):
        if panel_id in self._panel_card_groups:
            for card in self._panel_card_groups[panel_id]:
                if collapsed:
                    if card.parent:
                        self.card_container.remove_widget(card)
                else:
                    header = self._panel_headers.get(panel_id)
                    if header and header.parent:
                        idx = self.card_container.children.index(header)
                        for c in self._panel_card_groups[panel_id]:
                            self.card_container.add_widget(c, index=idx)

    def _on_drag_start(self, index, touch):
        self._dragging = True
        self._drag_from = index
        if index < len(self.cards):
            self.cards[index]._bg_color.rgba = [Theme.BG_CARD[0], Theme.BG_CARD[1], Theme.BG_CARD[2], 0.4]
        touch.grab(self)

    def on_touch_move(self, touch):
        if not self._dragging or touch.grab_current is not self:
            return super().on_touch_move(touch)

        target_idx = self._find_insert_index(touch.y)
        if self._insert_indicator.parent:
            self._insert_indicator.parent.remove_widget(self._insert_indicator)

        if 0 <= target_idx <= len(self.cards):
            self.card_container.add_widget(self._insert_indicator, index=len(self.cards) - target_idx)
        return True

    def on_touch_up(self, touch):
        if not self._dragging or touch.grab_current is not self:
            return super().on_touch_up(touch)

        touch.ungrab(self)
        if self._insert_indicator.parent:
            self._insert_indicator.parent.remove_widget(self._insert_indicator)

        target_idx = self._find_insert_index(touch.y)

        if self._drag_from < len(self.cards):
            active_id = self.app.state.active_object_id if self.app else None
            is_sel = (self.cards[self._drag_from].obj.id == active_id)
            self.cards[self._drag_from].set_selected(is_sel)

        if target_idx != self._drag_from and 0 <= target_idx <= len(self.cards):
            if self.app:
                to_idx = target_idx if target_idx < self._drag_from else max(0, target_idx - 1)
                self.app.state.reorder(self._drag_from, to_idx)
                # In-place card list reorder
                card = self.cards.pop(self._drag_from)
                self.cards.insert(to_idx, card)
                for idx, c in enumerate(self.cards):
                    c.update_index(idx)

        self._dragging = False
        self._drag_from = -1
        return True

    def _find_insert_index(self, touch_y):
        for i, card in enumerate(self.cards):
            card_win_y = card.to_window(card.x, card.y)[1]
            card_mid = card_win_y + card.height / 2.0
            if touch_y > card_mid:
                return i
        return len(self.cards)

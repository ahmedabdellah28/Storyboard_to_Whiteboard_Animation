"""
Object List — Studio Layers Panel with Collapsible Panel Accordions.
Features:
1. Panel Accordion Headers: Shows Panel ID, thumbnail, item count, and focus trigger.
2. Expands to reveal member layer cards with priority badges.
3. Supports priority order reordering (Up/Down and Drag).
"""
import cv2
import numpy as np
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
# pyrefly: ignore [missing-import]
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton
from .object_card import ObjectCard
from ..theme import Theme


_PANEL_THUMB_CACHE = {}


class PanelAccordionHeader(MDBoxLayout):
    """Clean collapsible panel header with thumbnail, title, badge, focus, reordering, and single-panel animate actions."""

    def __init__(self, panel_id: int, panel_crop: np.ndarray, item_count: int, on_toggle, on_focus=None, on_clear=None, on_auto_order=None, on_animate=None, **kwargs):
        super().__init__(**kwargs)
        self.panel_id = panel_id
        self.item_count = item_count
        self._collapsed = True  # Collapsed by default for clean panel order view
        self._on_toggle = on_toggle
        self._on_focus = on_focus
        self._on_clear = on_clear
        self._on_auto_order = on_auto_order
        self._on_animate = on_animate

        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(44)
        self.padding = [dp(6), dp(4), dp(8), dp(4)]
        self.spacing = dp(4)

        with self.canvas.before:
            self._bg_col = Color(rgba=[0.12, 0.14, 0.19, 1.0])
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])

        self.bind(pos=self._update_geom, size=self._update_geom)
        self._build(panel_crop)

    def _update_geom(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def update_count(self, new_count: int):
        self.item_count = new_count
        self.count_badge.text = f"({new_count})"

    def _build(self, panel_crop):
        # 1. Expand / Collapse Chevron Button
        self.toggle_btn = MDIconButton(
            icon="chevron-right" if self._collapsed else "chevron-down",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_ACCENT,
            icon_size=sp(18),
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.toggle()
        )
        self.add_widget(self.toggle_btn)

        # 2. Mini Thumbnail
        self.thumb = Image(
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(None, None),
            size=(dp(34), dp(34)),
            pos_hint={"center_y": 0.5}
        )
        self._set_thumbnail(self.thumb, panel_crop)
        self.add_widget(self.thumb)

        # 3. Title & Items count
        lbl_box = MDBoxLayout(orientation="horizontal", spacing=dp(4), pos_hint={"center_y": 0.5}, size_hint_x=1)
        self.title_lbl = MDLabel(
            text=f"Panel {self.panel_id:02d}",
            font_style="Subtitle2",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            bold=True,
            adaptive_height=True
        )
        self.count_badge = MDLabel(
            text=f"({self.item_count})",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            adaptive_height=True
        )
        lbl_box.add_widget(self.title_lbl)
        lbl_box.add_widget(self.count_badge)
        self.add_widget(lbl_box)

        # 4. Clear/Reset Sequence Orders Button (تفريغ الترتيب)
        self.clear_btn = MDIconButton(
            icon="restore",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_DIM,
            icon_size=sp(16),
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._trigger_clear()
        )
        self.add_widget(self.clear_btn)

        # 5. Auto 1..N Sequence Orders Button (ترتيب تلقائي)
        self.auto_btn = MDIconButton(
            icon="sort-numeric-ascending",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_DIM,
            icon_size=sp(16),
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._trigger_auto()
        )
        self.add_widget(self.auto_btn)

        # 6. Focus Panel Button (Focus canvas onto this panel)
        self.focus_btn = MDIconButton(
            icon="crosshairs-gps",
            theme_icon_color="Custom",
            icon_color=Theme.HEX_CYAN,
            icon_size=sp(16),
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._trigger_focus()
        )
        self.add_widget(self.focus_btn)

        # 7. Single Panel Animate Button (تحريك هذا البانل فقط)
        self.anim_btn = MDIconButton(
            icon="play-circle",
            theme_icon_color="Custom",
            icon_color=Theme.HEX_SUCCESS,
            icon_size=sp(20),
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._trigger_animate()
        )
        self.add_widget(self.anim_btn)

    def _set_thumbnail(self, widget, crop):
        if crop is None or crop.size == 0:
            return
        if self.panel_id in _PANEL_THUMB_CACHE:
            widget.texture = _PANEL_THUMB_CACHE[self.panel_id]
            return
        try:
            th, tw = 36, 36
            ch, cw = crop.shape[:2]
            scale = min(tw / float(max(1, cw)), th / float(max(1, ch)))
            nw = max(1, int(round(cw * scale)))
            nh = max(1, int(round(ch * scale)))
            resized = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_AREA)

            thumb = np.full((th, tw, 3), 255, dtype=np.uint8)
            ox = (tw - nw) // 2
            oy = (th - nh) // 2
            thumb[oy:oy+nh, ox:ox+nw] = resized
            thumb_rgba = cv2.cvtColor(thumb, cv2.COLOR_BGR2RGBA)
            buf = np.ascontiguousarray(cv2.flip(thumb_rgba, 0)).tobytes()
            tex = Texture.create(size=(tw, th), colorfmt='rgba')
            tex.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
            widget.texture = tex
            _PANEL_THUMB_CACHE[self.panel_id] = tex
        except Exception:
            pass

    def toggle(self):
        self._collapsed = not self._collapsed
        self.toggle_btn.icon = "chevron-right" if self._collapsed else "chevron-down"
        self._bg_col.rgba = [0.16, 0.18, 0.25, 1.0] if not self._collapsed else [0.12, 0.14, 0.19, 1.0]
        if self._on_toggle:
            self._on_toggle(self.panel_id, self._collapsed)

    def _trigger_focus(self):
        if self._on_focus:
            self._on_focus(self.panel_id)

    def _trigger_clear(self):
        if self._on_clear:
            self._on_clear(self.panel_id)

    def _trigger_auto(self):
        if self._on_auto_order:
            self._on_auto_order(self.panel_id)

    def _trigger_animate(self):
        if self._on_animate:
            self._on_animate(self.panel_id)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if (self.toggle_btn.collide_point(*touch.pos) or 
                self.focus_btn.collide_point(*touch.pos) or
                self.clear_btn.collide_point(*touch.pos) or
                self.auto_btn.collide_point(*touch.pos) or
                self.anim_btn.collide_point(*touch.pos)):
                return super().on_touch_down(touch)
            self.toggle()
            self._trigger_focus()
            return True
        return super().on_touch_down(touch)


class ObjectList(MDBoxLayout):
    """Studio Layers List with Collapsible Accordion Panels and Priority Sync."""

    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.orientation = "vertical"
        self.spacing = dp(4)
        self.padding = [dp(8), dp(6), dp(8), dp(6)]
        self.size_hint = (1, 1)

        self.cards = []
        self.source_image = None
        self._panel_headers = {}
        self._panel_card_boxes = {}
        self._panel_card_groups = {}
        self._structure_type = "SINGLE_SCENE"

        # Top Header
        hdr = MDBoxLayout(orientation="horizontal", adaptive_height=True, padding=[dp(4), dp(2), dp(4), dp(4)])
        self.hdr_label = MDLabel(
            text="STORYBOARD PANELS",
            font_style="Subtitle2",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            adaptive_height=True,
            bold=True
        )
        self.count_label = MDLabel(
            text="0 panels",
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
            spacing=dp(6),
            adaptive_height=True,
            padding=[0, 0, 0, dp(16)]
        )
        self.scroll.add_widget(self.card_container)
        self.add_widget(self.scroll)

    def populate(self, objects, source_image, structure_type="SINGLE_SCENE", project=None):
        self.source_image = source_image
        callbacks = {
            "on_select": self._on_card_selected,
            "on_move_order": self._on_move_order,
            "on_drag_drop": self._on_drag_drop,
            "on_toggle_visibility": self._on_toggle_visibility,
            "on_toggle_priority": self._on_toggle_priority
        }
        self._callbacks = callbacks

        active_id = self.app.state.active_object_id if self.app and hasattr(self.app, "state") else None
        active_panel = getattr(self.app.state, "active_panel_id", 1) if self.app and hasattr(self.app, "state") else 1

        # Check if in-place synchronization is possible without rebuilding DOM
        if (self._structure_type == structure_type and 
            structure_type == "STORYBOARD" and 
            project and project.panels and 
            set(self._panel_headers.keys()) == {p.id for p in project.panels}):
            
            # 1. Update panels map
            self._panels_map = {p.id: [] for p in project.panels}
            for obj in objects:
                pid = getattr(obj, 'panel_id', 1)
                if pid in self._panels_map:
                    self._panels_map[pid].append(obj)

            # 2. Update panel counts and existing cards in-place
            for p in project.panels:
                pid = p.id
                p_objs = self._panels_map.get(pid, [])
                if pid in self._panel_headers:
                    self._panel_headers[pid].update_count(len(p_objs))

                cards = self._panel_card_groups.get(pid, [])
                cards_box = self._panel_card_boxes.get(pid)

                if cards and cards_box and len(cards) == len(p_objs):
                    # In-place sync existing cards
                    for o_idx, (card, obj) in enumerate(zip(cards, p_objs)):
                        card.sync_from_object(obj, o_idx, source_image)
                        card.set_selected(obj.id == active_id)
                elif cards_box and not self._panel_headers[pid]._collapsed:
                    # Panel is expanded but count changed: fast refresh
                    self.refresh_panel_cards(pid)

            return

        if (self._structure_type == structure_type and 
            structure_type != "STORYBOARD" and 
            len(self.cards) == len(objects) and len(self.cards) > 0):
            # In-place sync flat cards list
            for o_idx, (card, obj) in enumerate(zip(self.cards, objects)):
                card.sync_from_object(obj, o_idx, source_image)
                card.set_selected(obj.id == active_id)
            return

        # Full initial structure creation
        global _PANEL_THUMB_CACHE
        _PANEL_THUMB_CACHE.clear()
        self._structure_type = structure_type
        self.card_container.clear_widgets()
        self.cards.clear()
        self._panel_headers.clear()
        self._panel_card_boxes.clear()
        self._panel_card_groups.clear()
        self._panels_map = {}

        if structure_type == "STORYBOARD" and project and project.panels:
            self.count_label.text = f"{len(project.panels)} panels"
            
            # Map objects by panel
            for p in project.panels:
                self._panels_map[p.id] = []

            for obj in objects:
                pid = getattr(obj, 'panel_id', 1)
                if pid not in self._panels_map:
                    self._panels_map[pid] = []
                self._panels_map[pid].append(obj)

            for p in project.panels:
                pid = p.id
                p_objs = self._panels_map.get(pid, [])
                c_crop = getattr(p, "clean_crop", None)
                s_crop = getattr(p, "source_image", None)
                p_crop = c_crop if c_crop is not None else s_crop

                # Dedicated Panel Box containing Header + Cards Container
                panel_box = MDBoxLayout(
                    orientation="vertical",
                    spacing=dp(4),
                    adaptive_height=True
                )

                header = PanelAccordionHeader(
                    panel_id=pid,
                    panel_crop=p_crop,
                    item_count=len(p_objs),
                    on_toggle=self._on_panel_toggle,
                    on_focus=self._on_panel_focus,
                    on_clear=self._on_clear_panel_priority,
                    on_auto_order=self._on_auto_sequence_panel,
                    on_animate=self._on_animate_panel
                )
                self._panel_headers[pid] = header
                panel_box.add_widget(header)

                cards_sub_box = MDBoxLayout(
                    orientation="vertical",
                    spacing=dp(4),
                    adaptive_height=True,
                    padding=[dp(6), 0, 0, dp(4)]
                )
                panel_box.add_widget(cards_sub_box)
                self._panel_card_boxes[pid] = cards_sub_box
                self._panel_card_groups[pid] = []

                self.card_container.add_widget(panel_box)

                # Open active panel or Panel 1 by default
                if pid == active_panel:
                    header.toggle()

        else:
            self.count_label.text = f"{len(objects)} layers"
            for idx, obj in enumerate(objects):
                card = ObjectCard(obj, idx, source_image, callbacks)
                card.set_selected(obj.id == active_id)
                self.cards.append(card)
                self.card_container.add_widget(card)

    def _get_or_create_panel_cards(self, panel_id):
        existing = self._panel_card_groups.get(panel_id)
        if existing and len(existing) > 0:
            return existing

        p_objs = self._panels_map.get(panel_id, [])
        active_id = self.app.state.active_object_id if self.app and hasattr(self.app, "state") else None
        
        cards = []
        for o_idx, obj in enumerate(p_objs):
            card = ObjectCard(obj, o_idx, self.source_image, self._callbacks)
            card.set_selected(obj.id == active_id)
            self.cards.append(card)
            cards.append(card)

        self._panel_card_groups[panel_id] = cards
        return cards

    def _on_panel_toggle(self, panel_id, collapsed):
        cards_box = self._panel_card_boxes.get(panel_id)
        if not cards_box:
            return

        cards_box.clear_widgets()
        if not collapsed:
            cards = self._get_or_create_panel_cards(panel_id)
            for c in cards:
                cards_box.add_widget(c)

    def _on_panel_focus(self, panel_id):
        if self.app and hasattr(self.app, "focus_panel"):
            self.app.focus_panel(panel_id)
        elif self.app and hasattr(self.app, "state"):
            self.app.state.active_panel_id = panel_id
            self.app.scene_screen.image_preview.set_focused_panel(panel_id)

    def _on_move_order(self, obj_id: str, delta: int):
        """Move object up (delta=-1, towards top) or down (delta=+1, towards bottom)."""
        if not self.app or not hasattr(self.app, "state"):
            return
        
        target_obj = self.app.state.get_object_by_id(obj_id)
        if not target_obj:
            return

        pid = getattr(target_obj, "panel_id", 1)
        p_objs = [o for o in self.app.state.objects if getattr(o, "panel_id", 1) == pid]

        cur_p_idx = None
        for i, o in enumerate(p_objs):
            if o.id == obj_id:
                cur_p_idx = i
                break

        if cur_p_idx is None:
            return

        new_p_idx = cur_p_idx + delta
        if 0 <= new_p_idx < len(p_objs):
            self.app.state.reorder_panel_object(pid, cur_p_idx, new_p_idx)
            self.refresh_panel_cards(pid)

    def _on_drag_drop(self, dragged_obj_id: str, drop_x: float, drop_y: float, panel_id: int):
        """Move dragged object to target position based on drop coordinates within its panel."""
        if not self.app or not hasattr(self.app, "state"):
            return

        panel_cards = self._panel_card_groups.get(panel_id, [])
        if len(panel_cards) <= 1:
            return

        cards_box = self._panel_card_boxes.get(panel_id)
        if drop_y is not None:
            if cards_box:
                local_x, local_y = cards_box.to_widget(drop_x, drop_y)
            else:
                local_x, local_y = drop_x, drop_y

            # Target slot is the card whose vertical center is closest to drop position
            target_idx = 0
            min_dist = float('inf')
            for idx, card in enumerate(panel_cards):
                card_center_y = card.y + card.height / 2.0
                dist = abs(local_y - card_center_y)
                if dist < min_dist:
                    min_dist = dist
                    target_idx = idx
        else:
            target_idx = int(drop_x)

        dragged_idx = None
        for idx, card in enumerate(panel_cards):
            if card.obj.id == dragged_obj_id:
                dragged_idx = idx
                break

        if dragged_idx is None or dragged_idx == target_idx:
            return

        moving = self.app.state.reorder_panel_object(panel_id, dragged_idx, target_idx)
        if moving and self.app and hasattr(self.app, "_show_toast"):
            self.app._show_toast(f"Reordered: {moving.name} -> Priority #{target_idx+1}")

    def _on_toggle_priority(self, obj_id: str, panel_id: int):
        """Toggle priority assignment for an object and adjust sequence order."""
        if not self.app or not hasattr(self.app, "state"):
            return

        is_assigned, new_p = self.app.state.toggle_panel_object_priority(panel_id, obj_id)
        if self.app and hasattr(self.app, "_show_toast"):
            if is_assigned:
                self.app._show_toast(f"تم تحديد الترتيب: رقم #{new_p}")
            else:
                self.app._show_toast("تم إلغاء التحديد وتحديث ترتيب باقي العناصر")

        self.refresh_panel_cards(panel_id)

    def _on_clear_panel_priority(self, panel_id: int):
        """Clear all priority assignments in panel for sequential click-ordering."""
        if not self.app or not hasattr(self.app, "state"):
            return
        
        self.app.state.clear_panel_priority(panel_id)
        self.refresh_panel_cards(panel_id)
        if self.app and hasattr(self.app, "_show_toast"):
            self.app._show_toast("تم تفريغ ترتيب البانل. اضغط على العناصر بالترتيب الذي تريده!")

    def _on_auto_sequence_panel(self, panel_id: int):
        """Auto sequence all objects in panel 1..N."""
        if not self.app or not hasattr(self.app, "state"):
            return

        self.app.state.reset_panel_priority_auto(panel_id)
        self.refresh_panel_cards(panel_id)
        if self.app and hasattr(self.app, "_show_toast"):
            self.app._show_toast("تم الترقيم التسلسلي التلقائي 1..N لجميع العناصر")

    def _on_animate_panel(self, panel_id: int):
        """Trigger animation for only the specified open panel."""
        if self.app and hasattr(self.app, "animate_single_panel"):
            self.app.animate_single_panel(panel_id)

    def refresh_panel_cards(self, panel_id: int):
        """Refresh card representations for a specific panel in-place."""
        if not self.app or not hasattr(self.app, "state"):
            return
        
        cards_box = self._panel_card_boxes.get(panel_id)
        if not cards_box:
            return

        p_objs = [o for o in self.app.state.objects if getattr(o, "panel_id", 1) == panel_id]
        active_id = self.app.state.active_object_id

        # Update card widgets for this panel
        existing_cards = self._panel_card_groups.get(panel_id, [])
        existing_by_id = {c.obj.id: c for c in existing_cards if hasattr(c, "obj")}

        cards_box.clear_widgets()
        new_cards = []
        for o_idx, obj in enumerate(p_objs):
            if obj.id in existing_by_id:
                card = existing_by_id[obj.id]
                card.sync_from_object(obj, o_idx, self.source_image)
                card.set_selected(obj.id == active_id)
            else:
                card = ObjectCard(obj, o_idx, self.source_image, self._callbacks)
                card.set_selected(obj.id == active_id)
                self.cards.append(card)
            new_cards.append(card)
            cards_box.add_widget(card)

        self._panel_card_groups[panel_id] = new_cards

        # Update flat cards list
        self.cards = [c for c in self.cards if getattr(c.obj, "panel_id", 1) != panel_id] + new_cards

    def update_active_selection(self, active_obj):
        active_id = active_obj.id if active_obj else None
        for card in self.cards:
            card.set_selected(card.obj.id == active_id)

        if active_obj and getattr(active_obj, 'panel_id', None):
            pid = active_obj.panel_id
            header = self._panel_headers.get(pid)
            if header and header._collapsed:
                header.toggle()

    def _on_card_selected(self, target):
        if self.app and hasattr(self.app, "state"):
            if isinstance(target, str):
                self.app.state.set_active_id(target)
            elif isinstance(target, int) and 0 <= target < len(self.cards):
                self.app.state.set_active_id(self.cards[target].obj.id)

    def _on_toggle_visibility(self, obj):
        if self.app and hasattr(self.app, "state"):
            self.app.state._notify_active_changed()
            self.app.state._notify_objects_changed()
        if self.app and hasattr(self.app, "scene_screen") and hasattr(self.app.scene_screen, "image_preview"):
            self.app.scene_screen.image_preview.redraw_overlays()

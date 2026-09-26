"""
Object Card — Studio Layer Card with Numbered & Color-Coded Priority Badges.
Contains: Drag grip, Numbered Priority Circle Badge, Type Badge, Crisp Thumbnail, Label, and Quick Reorder Buttons.
"""
import cv2
import numpy as np
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse
# pyrefly: ignore [missing-import]
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton
from ..theme import Theme


from kivy.uix.label import Label


_CARD_THUMBNAIL_CACHE = {}


class PriorityBadge(MDLabel):
    """Circular colored priority badge with centered number or unassigned indicator."""
    def __init__(self, number = 1, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(24), dp(24))
        self.number = number
        self.halign = "center"
        self.font_style = "Caption"
        self.bold = True
        self.theme_text_color = "Custom"

        with self.canvas.before:
            self._bg_col = Color(rgba=[0.25, 0.28, 0.35, 0.7])
            self._circle = Ellipse(pos=self.pos, size=self.size)

        self.bind(pos=self._update_geom, size=self._update_geom)
        self.set_priority(number)

    def _update_geom(self, *args):
        self._circle.pos = self.pos
        self._circle.size = self.size

    def set_priority(self, new_num):
        self.number = new_num
        if new_num is None or new_num == 0 or str(new_num).strip() in ("", "0", "None"):
            self.text = "—"
            self._bg_col.rgba = [0.22, 0.25, 0.32, 0.6]
            self.text_color = [0.65, 0.68, 0.75, 1.0]
        else:
            try:
                num_int = int(new_num)
                self.text = str(num_int)
                self._bg_col.rgba = Theme.get_priority_color(num_int)
                self.text_color = [0.05, 0.05, 0.08, 1.0]
            except Exception:
                self.text = str(new_num)
                self._bg_col.rgba = [0.3, 0.5, 0.8, 1.0]
                self.text_color = [1.0, 1.0, 1.0, 1.0]


class ObjectCard(MDBoxLayout):
    """Studio layer card for a SceneObject with color-coded priority badge and reordering."""

    def __init__(self, obj, index, source_image, callbacks, **kwargs):
        super().__init__(**kwargs)
        self.obj = obj
        self.index = index
        self.callbacks = callbacks
        self.is_selected = False
        self.is_dragging = False

        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(58)
        self.padding = [dp(6), dp(4), dp(6), dp(4)]
        self.spacing = dp(6)

        with self.canvas.before:
            self._bg_color = Color(rgba=Theme.BG_CARD)
            self._bg_rect = RoundedRectangle(
                pos=self.pos, size=self.size,
                radius=[dp(Theme.CARD_RADIUS)]
            )

        self.bind(pos=self._update_graphics, size=self._update_graphics)
        self._build(source_image)

    def _update_graphics(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _build(self, source_image):
        # 0. Drag Grip Handle
        self.drag_grip = MDIconButton(
            icon="drag-vertical",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_DIM,
            icon_size=sp(20),
            size_hint=(None, None),
            size=(dp(22), dp(28)),
            pos_hint={"center_y": 0.5}
        )
        self.add_widget(self.drag_grip)

        # 1. Circular Priority Badge (1, 2, 3...)
        p_num = getattr(self.obj, "priority_order", self.index + 1)
        self.priority_badge = PriorityBadge(number=p_num, pos_hint={"center_y": 0.5})
        self.add_widget(self.priority_badge)

        # 2. Thumbnail (Crisp Aspect Ratio Preview)
        self.thumb_widget = Image(
            size_hint=(None, None),
            size=(dp(54), dp(36)),
            pos_hint={"center_y": 0.5}
        )
        self._set_thumbnail(self.thumb_widget, source_image)
        self.add_widget(self.thumb_widget)

        # 3. Text & Tag Box
        self.text_box = MDBoxLayout(orientation="vertical", spacing=dp(2), pos_hint={"center_y": 0.5}, size_hint_x=1)
        
        self.name_label = MDLabel(
            text=str(self.obj.name).replace("_", " "),
            font_style="Body2",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            shorten=True,
            shorten_from="right",
            size_hint_y=None,
            height=dp(20)
        )
        
        # Tag label (e.g. TEXT RTL, CHARACTER, UNDERLINE)
        elem_type = getattr(self.obj, "element_type", "TEXT")
        direction = getattr(self.obj, "direction", "RTL")
        tag_str = f"{elem_type}"
        if elem_type == "TEXT":
            tag_str = f"TEXT - {direction} ({'RTL' if direction == 'RTL' else 'LTR'})"
        
        self.tag_label = MDLabel(
            text=tag_str,
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            size_hint_y=None,
            height=dp(16)
        )
        
        self.text_box.add_widget(self.name_label)
        self.text_box.add_widget(self.tag_label)
        self.add_widget(self.text_box)

        # 4. Quick Up / Down Reorder Actions (Enlarged)
        self.reorder_box = MDBoxLayout(orientation="vertical", size_hint=(None, 1), width=dp(30), spacing=dp(1))
        
        self.btn_up = MDIconButton(
            icon="chevron-up",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT,
            icon_size=sp(22),
            size_hint=(None, None),
            size=(dp(28), dp(26)),
            pos_hint={"center_x": 0.5},
            on_release=lambda x: self._on_move_up()
        )
        self.btn_down = MDIconButton(
            icon="chevron-down",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT,
            icon_size=sp(22),
            size_hint=(None, None),
            size=(dp(28), dp(26)),
            pos_hint={"center_x": 0.5},
            on_release=lambda x: self._on_move_down()
        )
        self.reorder_box.add_widget(self.btn_down)
        self.reorder_box.add_widget(self.btn_up)
        self.add_widget(self.reorder_box)

        # 5. Visibility toggle icon (Enlarged)
        is_vis = getattr(self.obj, "visibility", True)
        self.vis_btn = MDIconButton(
            icon="eye-outline" if is_vis else "eye-off-outline",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY if is_vis else Theme.TEXT_DIM,
            icon_size=sp(22),
            size_hint=(None, None),
            size=(dp(32), dp(32)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._toggle_visibility()
        )
        self.add_widget(self.vis_btn)

    def _set_thumbnail(self, widget, source_image, force=False):
        try:
            obj_id = getattr(self.obj, "id", None)
            bbox = getattr(self.obj, "global_bbox", None) or getattr(self.obj, "bbox", None)
            cache_key = (obj_id, bbox) if (obj_id and bbox) else None

            if not force and cache_key and cache_key in _CARD_THUMBNAIL_CACHE:
                widget.texture = _CARD_THUMBNAIL_CACHE[cache_key]
                return

            crop = getattr(self.obj, "crop", None)
            mask = getattr(self.obj, "mask", None)
            elem_type = str(getattr(self.obj, "element_type", "TEXT")).upper()
            name = str(getattr(self.obj, "name", "")).lower()

            if (crop is None or getattr(crop, "size", 0) == 0) and source_image is not None:
                bx, by, bw, bh = bbox or (0, 0, 0, 0)
                ih, iw = source_image.shape[:2]
                pad_x = max(2, int(bw * 0.05))
                pad_y = max(2, int(bh * 0.05))
                x1 = max(0, bx - pad_x)
                y1 = max(0, by - pad_y)
                x2 = min(iw, bx + bw + pad_x)
                y2 = min(ih, by + bh + pad_y)
                if x2 > x1 and y2 > y1:
                    crop = source_image[y1:y2, x1:x2].copy()

            th, tw = 36, 54
            canvas = np.full((th, tw, 3), 248, dtype=np.uint8)

            if crop is not None and getattr(crop, "size", 0) > 0:
                if mask is not None and mask.shape[:2] == crop.shape[:2] and cv2.countNonZero(mask) > 0:
                    ys, xs = np.where(mask > 0)
                    y1 = max(0, int(ys.min()) - 1)
                    y2 = min(crop.shape[0], int(ys.max()) + 2)
                    x1 = max(0, int(xs.min()) - 1)
                    x2 = min(crop.shape[1], int(xs.max()) + 2)
                    tight_crop = crop[y1:y2, x1:x2].copy()
                    tight_mask = mask[y1:y2, x1:x2]
                    isolated = np.full_like(tight_crop, 255)
                    isolated[tight_mask > 0] = tight_crop[tight_mask > 0]
                else:
                    isolated = crop.copy()

                ch, cw = isolated.shape[:2]
                pad = 2
                max_w = max(4, tw - pad * 2)
                max_h = max(4, th - pad * 2)
                scale = min(max_w / float(max(1, cw)), max_h / float(max(1, ch)))
                nw = max(1, min(max_w, int(round(cw * scale))))
                nh = max(1, min(max_h, int(round(ch * scale))))

                resized = cv2.resize(isolated, (nw, nh), interpolation=cv2.INTER_AREA)

                # High contrast ink boost for small text and icons
                if elem_type in ("TEXT", "TITLE", "UNDERLINE", "ICON", "ACCENT") or "text" in name or "title" in name:
                    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                    ink_pts = gray < 215
                    resized[ink_pts] = np.clip(resized[ink_pts].astype(np.float32) * 0.70, 0, 255).astype(np.uint8)

                ox = pad + (max_w - nw) // 2
                oy = pad + (max_h - nh) // 2
                canvas[oy:oy+nh, ox:ox+nw] = resized
                cv2.rectangle(canvas, (0, 0), (tw - 1, th - 1), (215, 220, 230), 1)

            canvas_rgba = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGBA)
            buf = np.ascontiguousarray(cv2.flip(canvas_rgba, 0)).tobytes()
            tex = Texture.create(size=(tw, th), colorfmt='rgba')
            tex.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
            widget.texture = tex
            if cache_key:
                _CARD_THUMBNAIL_CACHE[cache_key] = tex
        except Exception:
            pass

    def _on_move_up(self):
        cb = self.callbacks.get("on_move_order")
        if cb:
            cb(self.obj.id, -1)

    def _on_move_down(self):
        cb = self.callbacks.get("on_move_order")
        if cb:
            cb(self.obj.id, 1)

    def _toggle_visibility(self):
        cur = getattr(self.obj, "visibility", True)
        self.obj.visibility = not cur
        self.vis_btn.icon = "eye-outline" if self.obj.visibility else "eye-off-outline"
        self.vis_btn.icon_color = Theme.TEXT_SECONDARY if self.obj.visibility else Theme.TEXT_DIM
        cb = self.callbacks.get("on_toggle_visibility")
        if cb:
            cb(self.obj)

    def sync_from_object(self, obj, index=None, source_image=None):
        """Ultra-fast in-place synchronization of card properties without widget recreation."""
        self.obj = obj
        if index is not None:
            self.index = index
        
        # 1. Update Name
        name_txt = str(self.obj.name).replace("_", " ")
        if self.name_label.text != name_txt:
            self.name_label.text = name_txt

        # 2. Update Direction & Tag
        elem_type = getattr(self.obj, "element_type", "TEXT")
        direction = getattr(self.obj, "direction", "RTL")
        tag_str = f"{elem_type}"
        if elem_type == "TEXT":
            tag_str = f"TEXT - {direction} ({'RTL' if direction == 'RTL' else 'LTR'})"
        if self.tag_label.text != tag_str:
            self.tag_label.text = tag_str

        # 3. Update Priority Badge
        p_num = getattr(self.obj, "priority_order", self.index + 1)
        if self.priority_badge.number != p_num:
            self.priority_badge.set_priority(p_num)

        # 4. Update Visibility Icon
        is_vis = getattr(self.obj, "visibility", True)
        self.vis_btn.icon = "eye-outline" if is_vis else "eye-off-outline"
        self.vis_btn.icon_color = Theme.TEXT_SECONDARY if is_vis else Theme.TEXT_DIM

        # 5. Check if thumbnail needs refresh
        if source_image is not None:
            self._set_thumbnail(self.thumb_widget, source_image)

    def _on_toggle_priority(self):
        cb = self.callbacks.get("on_toggle_priority")
        if cb:
            pid = getattr(self.obj, "panel_id", 1)
            cb(self.obj.id, pid)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self._bg_color.rgba = Theme.BG_CARD_SELECTED
            self.name_label.bold = True
            self.name_label.text_color = Theme.TEXT
        else:
            self._bg_color.rgba = Theme.BG_CARD
            self.name_label.bold = False
            self.name_label.text_color = Theme.TEXT_SECONDARY

    def update_priority(self, new_num):
        self.obj.priority_order = new_num
        self.priority_badge.set_priority(new_num)

    def update_direction_tag(self, new_dir: str):
        self.obj.direction = new_dir
        elem_type = getattr(self.obj, "element_type", "TEXT")
        tag_str = f"{elem_type}"
        if elem_type == "TEXT":
            tag_str = f"TEXT - {new_dir} ({'RTL' if new_dir == 'RTL' else 'LTR'})"
        self.tag_label.text = tag_str

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # 1. Direct Priority Badge click -> Toggle priority sequence
            if self.priority_badge.collide_point(*touch.pos):
                self._on_toggle_priority()
                return True

            # 2. Child action buttons
            if self.vis_btn.collide_point(*touch.pos) or self.btn_up.collide_point(*touch.pos) or self.btn_down.collide_point(*touch.pos):
                return super().on_touch_down(touch)

            # 3. Drag Handle click -> enable drag
            if self.drag_grip.collide_point(*touch.pos):
                self._touch_down_pos = (touch.x, touch.y)
                self._is_dragging = False
                touch.grab(self)
                return True

            # 4. Normal Card click -> Select active object without blocking ScrollView scroll
            cb = self.callbacks.get("on_select")
            if cb:
                cb(self.obj.id if hasattr(self.obj, "id") else self.index)
            return super().on_touch_down(touch)

        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if hasattr(self, "_touch_down_pos"):
                dy = abs(touch.y - self._touch_down_pos[1])
                dx = abs(touch.x - self._touch_down_pos[0])
                if dy > dp(6) or dx > dp(6):
                    self._is_dragging = True
                    self._bg_color.rgba = [0.20, 0.28, 0.42, 0.95]
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            was_dragging = getattr(self, "_is_dragging", False)
            self._is_dragging = False
            self._bg_color.rgba = Theme.BG_CARD_SELECTED if self.is_selected else Theme.BG_CARD

            if was_dragging:
                cb = self.callbacks.get("on_drag_drop")
                if cb:
                    pid = getattr(self.obj, "panel_id", 1)
                    cb(self.obj.id, touch.x, touch.y, pid)
                return True
            return True
        return super().on_touch_up(touch)

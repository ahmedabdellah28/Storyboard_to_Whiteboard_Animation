"""
Object Card — Minimal, modern studio layer card.
Contains: Drag grip, crisp 44x44 thumbnail, order index, name label, and visibility toggle.
All secondary editing actions are cleanly delegated to the Inspector Panel.
"""
import cv2
import numpy as np
from kivy.uix.image import Image
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton
from ..theme import Theme


class ObjectCard(MDBoxLayout):
    """Clean studio layer card for a single detected or manually added SceneObject."""

    def __init__(self, obj, index, source_image, callbacks, **kwargs):
        """
        Args:
            obj: SceneObject
            index: display order (0-based)
            source_image: np.ndarray (BGR)
            callbacks: dict with keys: on_select, on_drag_start, on_toggle_visibility
        """
        super().__init__(**kwargs)
        self.obj = obj
        self.index = index
        self.callbacks = callbacks
        self.is_selected = False
        self.is_dragging = False

        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(52)
        self.padding = [dp(6), dp(4), dp(8), dp(4)]
        self.spacing = dp(8)

        with self.canvas.before:
            self._bg_color = Color(rgba=Theme.BG_CARD)
            self._bg_rect = RoundedRectangle(
                pos=self.pos, size=self.size,
                radius=[dp(Theme.CARD_RADIUS)]
            )
            self._border_color = Color(rgba=[0, 0, 0, 0])
            self._border_line = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(Theme.CARD_RADIUS)),
                width=1.5
            )

        self.bind(pos=self._update_graphics, size=self._update_graphics)
        self._build(source_image)

    def _update_graphics(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._border_line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(Theme.CARD_RADIUS))

    def _build(self, source_image):
        # 1. Drag grip handle
        self.drag_handle = MDIconButton(
            icon="drag-vertical",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_DIM,
            icon_size=sp(18),
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={"center_y": 0.5}
        )
        self.drag_handle.bind(on_touch_down=self._handle_drag_touch)
        self.add_widget(self.drag_handle)

        # 2. Thumbnail
        self.thumb_widget = Image(
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(None, None),
            size=(dp(42), dp(42)),
            pos_hint={"center_y": 0.5}
        )
        self._set_thumbnail(self.thumb_widget, source_image)
        self.add_widget(self.thumb_widget)

        # 3. Text block (Index + Name)
        self.text_box = MDBoxLayout(orientation="horizontal", spacing=dp(6), pos_hint={"center_y": 0.5})
        self.order_label = MDLabel(
            text=f"{self.index + 1:02d}",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_ACCENT,
            size_hint_x=None,
            width=dp(22),
            bold=True
        )
        self.name_label = MDLabel(
            text=self.obj.name.replace("_", " "),
            font_style="Body2",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            shorten=True,
            shorten_from="right"
        )
        self.text_box.add_widget(self.order_label)
        self.text_box.add_widget(self.name_label)
        self.add_widget(self.text_box)

        # 4. Visibility toggle icon
        is_vis = getattr(self.obj, "visibility", True)
        self.vis_btn = MDIconButton(
            icon="eye-outline" if is_vis else "eye-off-outline",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY if is_vis else Theme.TEXT_DIM,
            icon_size=sp(18),
            size_hint=(None, None),
            size=(dp(28), dp(28)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._toggle_visibility()
        )
        self.add_widget(self.vis_btn)

    def _set_thumbnail(self, widget, source_image):
        """Crop object from source image and set as crisp texture."""
        try:
            crop = getattr(self.obj, "crop", None)
            if crop is None or getattr(crop, "size", 0) == 0:
                img = getattr(self.obj, "scene_source_image", None) or source_image
                if img is None:
                    return

                bx, by, bw, bh = getattr(self.obj, "global_bbox", None) or getattr(self.obj, "bbox", (0, 0, 0, 0))
                ih, iw = img.shape[:2]
                pad_x = max(2, int(bw * 0.08))
                pad_y = max(2, int(bh * 0.08))
                x1 = max(0, bx - pad_x)
                y1 = max(0, by - pad_y)
                x2 = min(iw, bx + bw + pad_x)
                y2 = min(ih, by + bh + pad_y)
                if x2 <= x1 or y2 <= y1:
                    return
                crop = img[y1:y2, x1:x2].copy()

            th, tw = 48, 48
            ch, cw = crop.shape[:2]
            scale = min(tw / float(max(1, cw)), th / float(max(1, ch)))
            nw = max(1, int(round(cw * scale)))
            nh = max(1, int(round(ch * scale)))
            resized = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_AREA)

            square_thumb = np.full((th, tw, 3), 255, dtype=np.uint8)
            ox = (tw - nw) // 2
            oy = (th - nh) // 2
            square_thumb[oy:oy+nh, ox:ox+nw] = resized

            buf = cv2.flip(square_thumb, 0).tobytes()
            tex = Texture.create(size=(tw, th), colorfmt='bgr')
            tex.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            widget.texture = tex
        except Exception:
            pass

    def _handle_drag_touch(self, widget, touch):
        if widget.collide_point(*touch.pos):
            cb = self.callbacks.get("on_drag_start")
            if cb:
                cb(self.index, touch)
            return True
        return False

    def _toggle_visibility(self):
        cur = getattr(self.obj, "visibility", True)
        self.obj.visibility = not cur
        self.vis_btn.icon = "eye-outline" if self.obj.visibility else "eye-off-outline"
        self.vis_btn.icon_color = Theme.TEXT_SECONDARY if self.obj.visibility else Theme.TEXT_DIM
        cb = self.callbacks.get("on_toggle_visibility")
        if cb:
            cb(self.obj)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self._bg_color.rgba = Theme.BG_CARD_SELECTED
            self._border_color.rgba = Theme.BORDER_FOCUS
            self.name_label.bold = True
            self.name_label.text_color = Theme.TEXT
        else:
            self._bg_color.rgba = Theme.BG_CARD
            self._border_color.rgba = [0, 0, 0, 0]
            self.name_label.bold = False
            self.name_label.text_color = Theme.TEXT_SECONDARY

    def update_index(self, new_index: int):
        self.index = new_index
        self.order_label.text = f"{self.index + 1:02d}"

    def update_name(self, new_name: str):
        self.name_label.text = new_name.replace("_", " ")

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # If touch is on drag handle or visibility button, let child handle it
            if self.drag_handle.collide_point(*touch.pos) or self.vis_btn.collide_point(*touch.pos):
                return super().on_touch_down(touch)

            # Direct selection of this card
            cb = self.callbacks.get("on_select")
            if cb:
                cb(self.obj.id if hasattr(self.obj, "id") else self.index)
            return True
        return super().on_touch_down(touch)

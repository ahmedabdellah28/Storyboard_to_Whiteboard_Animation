"""
Grid Setup Screen — Interactive Dynamic Panel Detection & Manual Annotation View.
Allows users to:
1. Preview dynamically detected storyboard panels (1..N) with sequential numbered badges.
2. Move, resize, delete, and add custom panel boxes directly on the canvas.
3. Confirm with 'NEXT: EXTRACT & ANIMATE' to run the deep layer extraction pipeline.
"""
import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.metrics import dp, sp
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle, Ellipse, InstructionGroup
from kivy.core.window import Window

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import (
    MDFillRoundFlatIconButton,
    MDRoundFlatIconButton,
    MDIconButton,
    MDFlatButton
)

from ..theme import Theme
from engine.processing.whiteboard_processor import WhiteboardProcessor
from engine.core.image_io import read_image_unicode


class InteractiveGridCanvas(FloatLayout):
    """Interactive canvas widget to view image and manipulate panel bounding boxes."""

    def __init__(self, setup_screen_ref, **kwargs):
        super().__init__(**kwargs)
        self.setup_screen = setup_screen_ref
        self.size_hint = (1, 1)

        self.img_widget = Image(
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0}
        )
        self.add_widget(self.img_widget)

        with self.canvas.after:
            self.overlay_group = InstructionGroup()
            self.drag_preview_group = InstructionGroup()

        self.boxes: List[Dict[str, Any]] = []
        self.selected_idx: Optional[int] = None
        self.is_add_mode: bool = False

        self._touch_mode = None  # "MOVE", "RESIZE_TL", "RESIZE_TR", "RESIZE_BL", "RESIZE_BR", "DRAW"
        self._touch_start_img = (0, 0)
        self._touch_curr_img = (0, 0)
        self._orig_box = None

        self.bind(pos=self._on_geometry_change, size=self._on_geometry_change)

    def set_image_and_boxes(self, img_path: str, boxes: List[Dict[str, Any]]):
        self.img_widget.source = img_path
        self.img_widget.reload()
        self.boxes = [dict(b) for b in boxes]
        self._reindex_boxes()
        self.selected_idx = None
        self.is_add_mode = False
        self.redraw_overlays()

    def _reindex_boxes(self):
        """Sorts boxes top-to-bottom, left-to-right and re-indexes 1..N."""
        if not self.boxes:
            return
        # Sort primarily by row, secondarily by x
        img = self.setup_screen.source_image
        h = img.shape[0] if img is not None else 1080
        row_h = max(20.0, np.mean([b["bbox"][3] for b in self.boxes]) * 0.7 if self.boxes else h * 0.25)
        self.boxes.sort(key=lambda b: (round(b["bbox"][1] / row_h), b["bbox"][0]))
        for idx, b in enumerate(self.boxes):
            b["id"] = idx + 1
            b["center"] = (b["bbox"][0] + b["bbox"][2] / 2.0, b["bbox"][1] + b["bbox"][3] / 2.0)

    def _get_geometry(self):
        tex = self.img_widget.texture
        if not tex:
            return None
        tex_w, tex_h = float(tex.width), float(tex.height)
        wx, wy = self.img_widget.pos
        ww, wh = self.img_widget.size
        if ww <= 0 or wh <= 0:
            return None

        scale = min(ww / tex_w, wh / tex_h)
        disp_w = tex_w * scale
        disp_h = tex_h * scale
        disp_x = wx + (ww - disp_w) / 2.0
        disp_y = wy + (wh - disp_h) / 2.0

        return {
            "scale": scale,
            "disp_x": disp_x,
            "disp_y": disp_y,
            "disp_w": disp_w,
            "disp_h": disp_h,
            "tex_w": tex_w,
            "tex_h": tex_h
        }

    def img_to_widget(self, ix: float, iy: float) -> Optional[Tuple[float, float]]:
        geom = self._get_geometry()
        if not geom:
            return None
        scale = geom["scale"]
        disp_x = geom["disp_x"]
        disp_y = geom["disp_y"]
        tex_h = geom["tex_h"]
        wx = disp_x + ix * scale
        wy = disp_y + (tex_h - iy) * scale
        return (wx, wy)

    def widget_to_img(self, wx: float, wy: float) -> Optional[Tuple[float, float]]:
        geom = self._get_geometry()
        if not geom:
            return None
        scale = geom["scale"]
        if scale <= 0:
            return None
        disp_x = geom["disp_x"]
        disp_y = geom["disp_y"]
        tex_w = geom["tex_w"]
        tex_h = geom["tex_h"]

        ix = (wx - disp_x) / scale
        iy = tex_h - (wy - disp_y) / scale
        ix = max(0, min(tex_w - 1, ix))
        iy = max(0, min(tex_h - 1, iy))
        return (ix, iy)

    def _on_geometry_change(self, *args):
        self.redraw_overlays()

    def redraw_overlays(self):
        self.overlay_group.clear()
        geom = self._get_geometry()
        if not geom:
            return

        for idx, b in enumerate(self.boxes):
            bx, by, bw, bh = b["bbox"]
            p_id = b.get("id", idx + 1)
            is_sel = (idx == self.selected_idx)

            p_tl = self.img_to_widget(bx, by)
            p_br = self.img_to_widget(bx + bw, by + bh)
            if not p_tl or not p_br:
                continue

            wx1, wy1 = min(p_tl[0], p_br[0]), min(p_tl[1], p_br[1])
            ww = abs(p_br[0] - p_tl[0])
            wh = abs(p_br[1] - p_tl[1])

            # Box fill background tint
            fill_col = [0.0, 0.85, 1.0, 0.12] if is_sel else [0.2, 0.4, 0.9, 0.06]
            self.overlay_group.add(Color(rgba=fill_col))
            self.overlay_group.add(RoundedRectangle(pos=(wx1, wy1), size=(ww, wh), radius=[dp(4)]))

            # Box Border
            border_col = [0.0, 0.95, 1.0, 0.95] if is_sel else [0.35, 0.65, 1.0, 0.70]
            border_w = 2.5 if is_sel else 1.5
            self.overlay_group.add(Color(rgba=border_col))
            self.overlay_group.add(Line(rounded_rectangle=(wx1, wy1, ww, wh, dp(4)), width=border_w))

            # Number badge at Top-Left
            badge_w = dp(32)
            badge_h = dp(20)
            badge_x = wx1 + dp(4)
            badge_y = wy1 + wh - badge_h - dp(4)

            badge_bg = [0.0, 0.75, 0.95, 0.95] if is_sel else [0.15, 0.20, 0.35, 0.85]
            self.overlay_group.add(Color(rgba=badge_bg))
            self.overlay_group.add(RoundedRectangle(pos=(badge_x, badge_y), size=(badge_w, badge_h), radius=[dp(4)]))

            # If selected, draw corner resize handles
            if is_sel:
                handle_size = dp(10)
                hs2 = handle_size / 2.0
                corners = [
                    (wx1 - hs2, wy1 - hs2),
                    (wx1 + ww - hs2, wy1 - hs2),
                    (wx1 - hs2, wy1 + wh - hs2),
                    (wx1 + ww - hs2, wy1 + wh - hs2)
                ]
                self.overlay_group.add(Color(rgba=[1.0, 1.0, 1.0, 1.0]))
                for cx, cy in corners:
                    self.overlay_group.add(Ellipse(pos=(cx, cy), size=(handle_size, handle_size)))
                self.overlay_group.add(Color(rgba=[0.0, 0.8, 1.0, 1.0]))
                for cx, cy in corners:
                    self.overlay_group.add(Line(ellipse=(cx, cy, handle_size, handle_size), width=1.5))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        img_pt = self.widget_to_img(touch.x, touch.y)
        if not img_pt:
            return True

        ix, iy = img_pt
        self._touch_start_img = (ix, iy)
        self._touch_curr_img = (ix, iy)

        if self.is_add_mode:
            self._touch_mode = "DRAW"
            touch.grab(self)
            return True

        # Check if clicked on resize handle of selected box
        if self.selected_idx is not None and 0 <= self.selected_idx < len(self.boxes):
            b = self.boxes[self.selected_idx]
            bx, by, bw, bh = b["bbox"]
            p_tl = self.img_to_widget(bx, by)
            p_br = self.img_to_widget(bx + bw, by + bh)
            if p_tl and p_br:
                wx1, wy1 = min(p_tl[0], p_br[0]), min(p_tl[1], p_br[1])
                ww = abs(p_br[0] - p_tl[0])
                wh = abs(p_br[1] - p_tl[1])
                hr = dp(14)
                if np.hypot(touch.x - wx1, touch.y - wy1) <= hr:
                    self._touch_mode = "RESIZE_BL"
                    self._orig_box = dict(b["bbox"])
                    touch.grab(self)
                    return True
                elif np.hypot(touch.x - (wx1 + ww), touch.y - wy1) <= hr:
                    self._touch_mode = "RESIZE_BR"
                    self._orig_box = dict(b["bbox"])
                    touch.grab(self)
                    return True
                elif np.hypot(touch.x - wx1, touch.y - (wy1 + wh)) <= hr:
                    self._touch_mode = "RESIZE_TL"
                    self._orig_box = dict(b["bbox"])
                    touch.grab(self)
                    return True
                elif np.hypot(touch.x - (wx1 + ww), touch.y - (wy1 + wh)) <= hr:
                    self._touch_mode = "RESIZE_TR"
                    self._orig_box = dict(b["bbox"])
                    touch.grab(self)
                    return True

        # Check if clicked inside any box to select / move
        hit_idx = None
        for idx, b in reversed(list(enumerate(self.boxes))):
            bx, by, bw, bh = b["bbox"]
            if bx <= ix <= bx + bw and by <= iy <= by + bh:
                hit_idx = idx
                break

        if hit_idx is not None:
            self.selected_idx = hit_idx
            self._touch_mode = "MOVE"
            self._orig_box = list(self.boxes[hit_idx]["bbox"])
            self.setup_screen.update_status_ui()
            self.redraw_overlays()
            touch.grab(self)
            return True
        else:
            self.selected_idx = None
            self.setup_screen.update_status_ui()
            self.redraw_overlays()

        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        img_pt = self.widget_to_img(touch.x, touch.y)
        if not img_pt:
            return True

        ix, iy = img_pt
        self._touch_curr_img = (ix, iy)
        dx = ix - self._touch_start_img[0]
        dy = iy - self._touch_start_img[1]

        if self._touch_mode == "DRAW":
            self._draw_rubberband_preview()
        elif self._touch_mode == "MOVE" and self.selected_idx is not None and self._orig_box:
            ox, oy, ow, oh = self._orig_box
            img = self.setup_screen.source_image
            max_w = img.shape[1] if img is not None else 4000
            max_h = img.shape[0] if img is not None else 4000
            nx = max(0, min(max_w - ow, int(round(ox + dx))))
            ny = max(0, min(max_h - oh, int(round(oy + dy))))
            self.boxes[self.selected_idx]["bbox"] = (nx, ny, ow, oh)
            self.redraw_overlays()
        elif self._touch_mode and self._touch_mode.startswith("RESIZE_") and self.selected_idx is not None and self._orig_box:
            ox, oy, ow, oh = self._orig_box
            if self._touch_mode == "RESIZE_BR":
                nw = max(20, int(round(ow + dx)))
                nh = max(20, int(round(oh + dy)))
                self.boxes[self.selected_idx]["bbox"] = (ox, oy, nw, nh)
            elif self._touch_mode == "RESIZE_BL":
                nx = int(round(ox + dx))
                nw = max(20, int(round(ow - dx)))
                nh = max(20, int(round(oh + dy)))
                self.boxes[self.selected_idx]["bbox"] = (nx, oy, nw, nh)
            elif self._touch_mode == "RESIZE_TL":
                nx = int(round(ox + dx))
                ny = int(round(oy + dy))
                nw = max(20, int(round(ow - dx)))
                nh = max(20, int(round(oh - dy)))
                self.boxes[self.selected_idx]["bbox"] = (nx, ny, nw, nh)
            elif self._touch_mode == "RESIZE_TR":
                ny = int(round(oy + dy))
                nw = max(20, int(round(ow + dx)))
                nh = max(20, int(round(oh - dy)))
                self.boxes[self.selected_idx]["bbox"] = (ox, ny, nw, nh)
            self.redraw_overlays()

        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)

        touch.ungrab(self)
        self.drag_preview_group.clear()

        if self._touch_mode == "DRAW":
            p1_x, p1_y = self._touch_start_img
            p2_x, p2_y = self._touch_curr_img
            bx = int(round(min(p1_x, p2_x)))
            by = int(round(min(p1_y, p2_y)))
            bw = int(round(abs(p2_x - p1_x)))
            bh = int(round(abs(p2_y - p1_y)))
            if bw >= 24 and bh >= 24:
                new_box = {
                    "id": len(self.boxes) + 1,
                    "bbox": (bx, by, bw, bh),
                    "center": (bx + bw / 2.0, by + bh / 2.0)
                }
                self.boxes.append(new_box)
                self._reindex_boxes()
                self.selected_idx = next((i for i, b in enumerate(self.boxes) if b["bbox"] == (bx, by, bw, bh)), len(self.boxes) - 1)
                self.is_add_mode = False
                self.setup_screen.update_status_ui()
                self.redraw_overlays()

        self._touch_mode = None
        self._orig_box = None
        return True

    def _draw_rubberband_preview(self):
        self.drag_preview_group.clear()
        p1_x, p1_y = self._touch_start_img
        p2_x, p2_y = self._touch_curr_img
        bx = min(p1_x, p2_x)
        by = min(p1_y, p2_y)
        bw = abs(p2_x - p1_x)
        bh = abs(p2_y - p1_y)

        p_tl = self.img_to_widget(bx, by)
        p_br = self.img_to_widget(bx + bw, by + bh)
        if p_tl and p_br:
            wx = min(p_tl[0], p_br[0])
            wy = min(p_tl[1], p_br[1])
            ww = abs(p_br[0] - p_tl[0])
            wh = abs(p_br[1] - p_tl[1])
            self.drag_preview_group.add(Color(rgba=[0.0, 1.0, 0.7, 0.20]))
            self.drag_preview_group.add(RoundedRectangle(pos=(wx, wy), size=(ww, wh), radius=[dp(4)]))
            self.drag_preview_group.add(Color(rgba=[0.0, 1.0, 0.7, 0.95]))
            self.drag_preview_group.add(Line(rounded_rectangle=(wx, wy, ww, wh, dp(4)), width=2.0))


class GridSetupScreen(MDScreen):
    """Studio Panel Setup & Manual Annotation Wizard Screen."""

    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.name = "grid_setup"
        self.app = app_ref
        self.md_bg_color = Theme.BG_ROOT

        self.image_path: Optional[str] = None
        self.source_image: Optional[np.ndarray] = None
        self.detected_default_boxes: List[Dict[str, Any]] = []

        root = MDBoxLayout(orientation="vertical", spacing=0)

        # ── 1. Top Setup Header Bar ──
        self.top_bar = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(52),
            padding=[dp(12), dp(6), dp(16), dp(6)],
            spacing=dp(8),
            md_bg_color=Theme.BG_PANEL
        )
        with self.top_bar.canvas.before:
            Color(rgba=Theme.BG_PANEL)
            self._tb_bg = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
            Color(rgba=Theme.BORDER)
            self._tb_border = Rectangle(pos=(self.top_bar.x, self.top_bar.y), size=(self.top_bar.width, dp(1)))
        self.top_bar.bind(pos=self._update_top_bar_bg, size=self._update_top_bar_bg)

        # Back Navigation to Home
        back_btn = MDIconButton(
            icon="arrow-left",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(34), dp(34)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self.app.go_home()
        )
        self.top_bar.add_widget(back_btn)

        # Screen Title
        title_box = MDBoxLayout(orientation="vertical", adaptive_height=True, pos_hint={"center_y": 0.5})
        title_lbl = MDLabel(
            text="PANEL GRID & COMPOSITION SETUP",
            font_style="Subtitle1",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            bold=True,
            adaptive_height=True
        )
        self.file_info_lbl = MDLabel(
            text="Review detected panels or adjust boundaries manually",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            adaptive_height=True
        )
        title_box.add_widget(title_lbl)
        title_box.add_widget(self.file_info_lbl)
        self.top_bar.add_widget(title_box)

        # Spacer
        self.top_bar.add_widget(Widget())

        # + Add Box Toggle Button
        self.add_box_btn = MDRoundFlatIconButton(
            text="ADD BOX",
            icon="plus-box-outline",
            theme_text_color="Custom",
            text_color=Theme.TEXT_SECONDARY,
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            line_color=Theme.BORDER,
            font_size=sp(12),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._toggle_add_mode()
        )
        self.top_bar.add_widget(self.add_box_btn)

        # Delete Box Button
        self.del_box_btn = MDRoundFlatIconButton(
            text="DELETE BOX",
            icon="delete-outline",
            theme_text_color="Custom",
            text_color=Theme.TEXT_DIM,
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_DIM,
            line_color=Theme.BORDER,
            font_size=sp(12),
            pos_hint={"center_y": 0.5},
            disabled=True,
            on_release=lambda x: self._delete_selected_box()
        )
        self.top_bar.add_widget(self.del_box_btn)

        # Auto-Detect / Re-scan Button
        self.autodetect_btn = MDRoundFlatIconButton(
            text="AUTO-DETECT",
            icon="auto-fix",
            theme_text_color="Custom",
            text_color=Theme.HEX_CYAN,
            theme_icon_color="Custom",
            icon_color=Theme.HEX_CYAN,
            line_color=Theme.ACCENT_CYAN,
            font_size=sp(12),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._run_auto_detect()
        )
        self.top_bar.add_widget(self.autodetect_btn)

        # Reset Button
        reset_btn = MDIconButton(
            icon="restore",
            theme_icon_color="Custom",
            icon_color=Theme.TEXT_SECONDARY,
            size_hint=(None, None),
            size=(dp(34), dp(34)),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._reset_to_default()
        )
        self.top_bar.add_widget(reset_btn)

        root.add_widget(self.top_bar)

        # ── 2. Center Interactive Grid Viewport ──
        self.canvas_view = InteractiveGridCanvas(setup_screen_ref=self)
        root.add_widget(self.canvas_view)

        # ── 3. Bottom Action Bar (Proceed to Next Step) ──
        self.bottom_bar = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(54),
            padding=[dp(20), dp(8), dp(20), dp(8)],
            spacing=dp(12),
            md_bg_color=Theme.BG_PANEL
        )
        with self.bottom_bar.canvas.before:
            Color(rgba=Theme.BG_PANEL)
            self._bb_bg = Rectangle(pos=self.bottom_bar.pos, size=self.bottom_bar.size)
            Color(rgba=Theme.BORDER)
            self._bb_border = Rectangle(pos=(self.bottom_bar.x, self.bottom_bar.y + self.bottom_bar.height - dp(1)), size=(self.bottom_bar.width, dp(1)))
        self.bottom_bar.bind(pos=self._update_bb_bg, size=self._update_bb_bg)

        self.summary_badge = MDLabel(
            text="16 Panels Detected",
            font_style="Subtitle2",
            theme_text_color="Custom",
            text_color=Theme.TEXT,
            bold=True,
            adaptive_height=True,
            pos_hint={"center_y": 0.5}
        )
        self.bottom_bar.add_widget(self.summary_badge)

        self.bottom_bar.add_widget(Widget())

        # Hero Action Button: NEXT -> EXTRACT & ANIMATE
        self.next_btn = MDFillRoundFlatIconButton(
            text="NEXT: EXTRACT & ANIMATE  →",
            icon="lightning-bolt",
            theme_text_color="Custom",
            text_color=Theme.HEX_TEXT,
            theme_icon_color="Custom",
            icon_color=Theme.HEX_TEXT,
            md_bg_color=Theme.HEX_ACCENT,
            font_size=sp(14),
            pos_hint={"center_y": 0.5},
            on_release=lambda x: self._on_confirm_next()
        )
        self.bottom_bar.add_widget(self.next_btn)

        root.add_widget(self.bottom_bar)
        self.add_widget(root)

    def _update_top_bar_bg(self, *args):
        if hasattr(self, "top_bar") and hasattr(self, "_tb_bg"):
            self._tb_bg.pos = self.top_bar.pos
            self._tb_bg.size = self.top_bar.size
            self._tb_border.pos = (self.top_bar.x, self.top_bar.y)
            self._tb_border.size = (self.top_bar.width, dp(1))

    def _update_bb_bg(self, *args):
        if hasattr(self, "bottom_bar") and hasattr(self, "_bb_bg"):
            self._bb_bg.pos = self.bottom_bar.pos
            self._bb_bg.size = self.bottom_bar.size
            self._bb_border.pos = (self.bottom_bar.x, self.bottom_bar.y + self.bottom_bar.height - dp(1))
            self._bb_border.size = (self.bottom_bar.width, dp(1))

    def load_image_for_setup(self, image_path: str):
        """Loads image and performs initial dynamic panel discovery."""
        self.image_path = image_path
        self.source_image = read_image_unicode(image_path)
        if self.source_image is None:
            return

        base_name = os.path.basename(image_path)
        self.file_info_lbl.text = f"{base_name}  •  {self.source_image.shape[1]}x{self.source_image.shape[0]}px"

        # Instant dynamic discovery
        discovered = WhiteboardProcessor.discover_panels(self.source_image)
        self.detected_default_boxes = [dict(b) for b in discovered]
        self.canvas_view.set_image_and_boxes(image_path, self.detected_default_boxes)
        self.update_status_ui()

    def update_status_ui(self):
        count = len(self.canvas_view.boxes)
        self.summary_badge.text = f"{count} Panel{'s' if count != 1 else ''} Configured"

        has_sel = (self.canvas_view.selected_idx is not None)
        self.del_box_btn.disabled = not has_sel
        self.del_box_btn.text_color = Theme.HEX_DANGER if has_sel else Theme.TEXT_DIM
        self.del_box_btn.icon_color = Theme.HEX_DANGER if has_sel else Theme.TEXT_DIM
        self.del_box_btn.line_color = Theme.HEX_DANGER if has_sel else Theme.BORDER

        is_add = getattr(self.canvas_view, "is_add_mode", False)
        self.add_box_btn.text = "DRAWING BOX..." if is_add else "ADD BOX"
        self.add_box_btn.text_color = Theme.HEX_ACCENT if is_add else Theme.TEXT_SECONDARY
        self.add_box_btn.icon_color = Theme.HEX_ACCENT if is_add else Theme.TEXT_SECONDARY
        self.add_box_btn.line_color = Theme.HEX_ACCENT if is_add else Theme.BORDER

    def _toggle_add_mode(self):
        self.canvas_view.is_add_mode = not self.canvas_view.is_add_mode
        self.canvas_view.selected_idx = None
        self.update_status_ui()
        self.canvas_view.redraw_overlays()

    def _delete_selected_box(self):
        if self.canvas_view.selected_idx is not None and 0 <= self.canvas_view.selected_idx < len(self.canvas_view.boxes):
            del self.canvas_view.boxes[self.canvas_view.selected_idx]
            self.canvas_view._reindex_boxes()
            self.canvas_view.selected_idx = None
            self.update_status_ui()
            self.canvas_view.redraw_overlays()

    def _run_auto_detect(self):
        if self.source_image is not None:
            discovered = WhiteboardProcessor.discover_panels(self.source_image)
            self.canvas_view.boxes = [dict(b) for b in discovered]
            self.canvas_view._reindex_boxes()
            self.canvas_view.selected_idx = None
            self.update_status_ui()
            self.canvas_view.redraw_overlays()

    def _reset_to_default(self):
        if self.detected_default_boxes:
            self.canvas_view.boxes = [dict(b) for b in self.detected_default_boxes]
            self.canvas_view._reindex_boxes()
            self.canvas_view.selected_idx = None
            self.update_status_ui()
            self.canvas_view.redraw_overlays()

    def _on_confirm_next(self):
        """Passes confirmed boxes to app extraction workflow."""
        if not self.image_path:
            return
        boxes_to_pass = list(self.canvas_view.boxes)
        self.app.start_extraction_workflow(self.image_path, custom_panels=boxes_to_pass)

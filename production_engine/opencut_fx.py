"""OpenCut-Derived Visual Effects & Motion Graphics Engine.

Ports visual assets, easing curves, feathered masks, and post-processing shaders
from OpenCut Classic into a high-performance Python/NumPy/OpenCV pipeline.
"""

import os
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Tuple, List, Optional, Dict, Any

# Root directory configuration
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(ROOT_DIR, "assets", "fonts")
SHAPES_DIR = os.path.join(ROOT_DIR, "assets", "shapes")
DEFAULT_CAIRO_FONT = os.path.join(FONTS_DIR, "Cairo-Bold-Presentation.ttf")



# ==============================================================================
# 1. OpenCut Bezier Easing System
# ==============================================================================

class CubicBezier:
    """Exact cubic bezier timing curve solver with 20-step Newton/Bisection solver."""

    def __init__(self, p1x: float, p1y: float, p2x: float, p2y: float):
        self.p1x = float(p1x)
        self.p1y = float(p1y)
        self.p2x = float(p2x)
        self.p2y = float(p2y)

    def _sample_curve_x(self, t: float) -> float:
        # P0 = (0,0), P3 = (1,1)
        return 3.0 * (1.0 - t) ** 2 * t * self.p1x + 3.0 * (1.0 - t) * t ** 2 * self.p2x + t ** 3

    def _sample_curve_y(self, t: float) -> float:
        return 3.0 * (1.0 - t) ** 2 * t * self.p1y + 3.0 * (1.0 - t) * t ** 2 * self.p2y + t ** 3

    def _sample_curve_derivative_x(self, t: float) -> float:
        return (
            3.0 * (1.0 - t) ** 2 * self.p1x
            + 6.0 * (1.0 - t) * t * (self.p2x - self.p1x)
            + 3.0 * t ** 2 * (1.0 - self.p2x)
        )

    def solve_t_for_x(self, x: float, iterations: int = 20) -> float:
        x = float(np.clip(x, 0.0, 1.0))
        # Newton-Raphson initial guess
        t = x
        for _ in range(iterations):
            cx = self._sample_curve_x(t) - x
            if abs(cx) < 1e-5:
                return t
            dx = self._sample_curve_derivative_x(t)
            if abs(dx) < 1e-6:
                break
            t -= cx / dx
            t = np.clip(t, 0.0, 1.0)

        # Bisection fallback
        t0, t1 = 0.0, 1.0
        t = x
        for _ in range(iterations):
            cx = self._sample_curve_x(t)
            if abs(cx - x) < 1e-5:
                return t
            if x > cx:
                t0 = t
            else:
                t1 = t
            t = (t0 + t1) * 0.5
        return t

    def evaluate(self, progress: float) -> float:
        progress = float(np.clip(progress, 0.0, 1.0))
        if progress <= 0.0:
            return 0.0
        if progress >= 1.0:
            return 1.0
        t = self.solve_t_for_x(progress)
        return float(self._sample_curve_y(t))


# Standard Motion Graphics Bezier Curve Presets
BEZIER_PRESETS = {
    # Snappy overshoot pop-in (great for badges, stickers, and cards)
    "ease_out_back": CubicBezier(0.175, 0.885, 0.32, 1.275),
    # Deep acceleration to deep deceleration
    "ease_in_out_cubic": CubicBezier(0.645, 0.045, 0.355, 1.0),
    # Swift deceleration (cinematic glide)
    "ease_out_cubic": CubicBezier(0.215, 0.61, 0.355, 1.0),
    # Fast punchy entrance
    "ease_out_expo": CubicBezier(0.19, 1.0, 0.22, 1.0),
    # Anticipation wind-up then shoot forward
    "anticipate": CubicBezier(0.36, 0.0, 0.66, -0.56),
    # Smooth natural flow
    "flow": CubicBezier(0.25, 0.1, 0.25, 1.0),
}


def ease(progress: float, preset_name: str = "ease_out_cubic") -> float:
    """Evaluates easing progress [0.0, 1.0] using OpenCut Bezier curve."""
    p = float(np.clip(progress, 0.0, 1.0))
    if preset_name in BEZIER_PRESETS:
        return BEZIER_PRESETS[preset_name].evaluate(p)
    elif preset_name == "smootherstep":
        return p * p * p * (p * (p * 6.0 - 15.0) + 10.0)
    elif preset_name == "linear":
        return p
    return p


# ==============================================================================
# 2. OpenCut Feathered Mask Suite (SDF Blending)
# ==============================================================================

class OpenCutMaskEngine:
    """Generates continuous feathered masks for transitions and reveals."""

    @staticmethod
    def apply_feather(mask: np.ndarray, feather_px: int) -> np.ndarray:
        """Applies smooth Gaussian distance feathering to a binary/grayscale mask."""
        if feather_px <= 1:
            return mask
        ksize = int(round(feather_px * 2)) | 1
        return cv2.GaussianBlur(mask, (ksize, ksize), feather_px * 0.5)

    @classmethod
    def split_wipe_mask(
        cls,
        width: int,
        height: int,
        progress: float,
        angle_deg: float = 15.0,
        feather_px: int = 50,
        invert: bool = False,
    ) -> np.ndarray:
        """Generates an angled split wipe transition mask with soft feathered leading edge."""
        progress = float(np.clip(progress, 0.0, 1.0))
        if progress <= 0.0:
            return np.zeros((height, width), dtype=np.float32) if not invert else np.ones((height, width), dtype=np.float32)
        if progress >= 1.0:
            return np.ones((height, width), dtype=np.float32) if not invert else np.zeros((height, width), dtype=np.float32)

        rad = math.radians(angle_deg)
        nx = math.cos(rad)
        ny = math.sin(rad)

        # Coordinate grid
        y_coords, x_coords = np.mgrid[0:height, 0:width]

        # Project corners to find total projection span
        corners = [(0, 0), (width, 0), (0, height), (width, height)]
        projections = [x * nx + y * ny for x, y in corners]
        min_p, max_p = min(projections), max(projections)

        # Expand span slightly to allow feather to clear edges completely
        span = max_p - min_p + feather_px * 2
        cutoff = (min_p - feather_px) + progress * span

        projected = x_coords * nx + y_coords * ny
        dist = cutoff - projected

        # Smoothstep sigmoid feather
        half_f = max(1.0, float(feather_px))
        mask = np.clip((dist / half_f + 1.0) * 0.5, 0.0, 1.0).astype(np.float32)

        return (1.0 - mask) if invert else mask

    @classmethod
    def ellipse_reveal_mask(
        cls,
        width: int,
        height: int,
        progress: float,
        center: Tuple[float, float] = (0.5, 0.5),
        aspect_ratio: float = 1.0,
        feather_px: int = 60,
    ) -> np.ndarray:
        """Generates an expanding ellipse/circle spotlight reveal mask."""
        progress = float(np.clip(progress, 0.0, 1.0))
        if progress <= 0.0:
            return np.zeros((height, width), dtype=np.float32)

        cx = center[0] * width
        cy = center[1] * height
        max_r = math.hypot(max(cx, width - cx), max(cy, height - cy)) + feather_px

        cur_rx = max(1.0, progress * max_r)
        cur_ry = max(1.0, cur_rx / aspect_ratio)

        y_coords, x_coords = np.mgrid[0:height, 0:width]
        dist_sq = ((x_coords - cx) / cur_rx) ** 2 + ((y_coords - cy) / cur_ry) ** 2
        dist = np.sqrt(dist_sq)

        # Feather border
        f_norm = feather_px / max(1.0, cur_rx)
        edge_lo = max(0.0, 1.0 - f_norm)
        mask = np.clip((1.0 - dist) / max(0.001, 1.0 - edge_lo), 0.0, 1.0).astype(np.float32)
        return mask

    @classmethod
    def rectangle_reveal_mask(
        cls,
        width: int,
        height: int,
        progress: float,
        center: Tuple[float, float] = (0.5, 0.5),
        corner_radius: int = 24,
        feather_px: int = 30,
    ) -> np.ndarray:
        """Generates a rounded rectangular card reveal with feathered borders."""
        progress = float(np.clip(progress, 0.0, 1.0))
        if progress <= 0.0:
            return np.zeros((height, width), dtype=np.float32)

        rw = int(round(width * progress))
        rh = int(round(height * progress))
        cx = int(round(center[0] * width))
        cy = int(round(center[1] * height))

        x1 = max(0, cx - rw // 2)
        y1 = max(0, cy - rh // 2)
        x2 = min(width, cx + rw // 2)
        y2 = min(height, cy + rh // 2)

        mask_img = np.zeros((height, width), dtype=np.uint8)
        rad = min(corner_radius, min(rw, rh) // 2)

        # Draw rounded rectangle in uint8
        if x2 > x1 and y2 > y1:
            cv2.rectangle(mask_img, (x1 + rad, y1), (x2 - rad, y2), 255, -1)
            cv2.rectangle(mask_img, (x1, y1 + rad), (x2, y2 - rad), 255, -1)
            if rad > 0:
                cv2.circle(mask_img, (x1 + rad, y1 + rad), rad, 255, -1)
                cv2.circle(mask_img, (x2 - rad, y1 + rad), rad, 255, -1)
                cv2.circle(mask_img, (x1 + rad, y2 - rad), rad, 255, -1)
                cv2.circle(mask_img, (x2 - rad, y2 - rad), rad, 255, -1)

        f_mask = cls.apply_feather(mask_img, feather_px).astype(np.float32) / 255.0
        return np.clip(f_mask, 0.0, 1.0)


# ==============================================================================
# 3. OpenCut Visual Enhancers (Drop Shadow, Ambient Glow, Glass Card)
# ==============================================================================

class OpenCutVisualFX:
    """Studio-grade post-processing passes for motion graphics assets."""

    @staticmethod
    def apply_drop_shadow(
        img_bgra: np.ndarray,
        offset: Tuple[int, int] = (6, 12),
        blur_radius: int = 18,
        opacity: float = 0.45,
        shadow_color: Tuple[int, int, int] = (15, 18, 25),
    ) -> np.ndarray:
        """Generates a realistic, soft diffused drop shadow beneath a transparent sprite."""
        if img_bgra is None or img_bgra.size == 0:
            return img_bgra
        h, w = img_bgra.shape[:2]
        ox, oy = offset
        pad_x = abs(ox) + blur_radius * 2 + 10
        pad_y = abs(oy) + blur_radius * 2 + 10

        new_h = h + pad_y * 2
        new_w = w + pad_x * 2

        # Extract source alpha
        src_alpha = img_bgra[:, :, 3]

        # Canvas for shadow alpha
        shadow_canvas = np.zeros((new_h, new_w), dtype=np.uint8)
        sy = pad_y + oy
        sx = pad_x + ox
        shadow_canvas[sy : sy + h, sx : sx + w] = (src_alpha.astype(np.float32) * opacity).astype(np.uint8)

        # Gaussian blur shadow
        k = blur_radius * 2 + 1
        blurred_shadow = cv2.GaussianBlur(shadow_canvas, (k, k), blur_radius * 0.5)

        # Assemble full result
        result = np.zeros((new_h, new_w, 4), dtype=np.uint8)
        result[:, :, 0] = shadow_color[0]
        result[:, :, 1] = shadow_color[1]
        result[:, :, 2] = shadow_color[2]
        result[:, :, 3] = blurred_shadow

        # Composite original sprite over shadow
        oy_orig = pad_y
        ox_orig = pad_x

        # Alpha blend original over shadow in overlapping region
        orig_patch = img_bgra
        dest_patch = result[oy_orig : oy_orig + h, ox_orig : ox_orig + w]

        a_src = orig_patch[:, :, 3:4].astype(np.float32) / 255.0
        a_dst = dest_patch[:, :, 3:4].astype(np.float32) / 255.0

        out_a = a_src + a_dst * (1.0 - a_src)
        out_rgb = (orig_patch[:, :, :3] * a_src + dest_patch[:, :, :3] * a_dst * (1.0 - a_src)) / np.maximum(out_a, 1e-6)

        dest_patch[:, :, :3] = np.clip(out_rgb, 0, 255).astype(np.uint8)
        dest_patch[:, :, 3] = np.clip(out_a[:, :, 0] * 255.0, 0, 255).astype(np.uint8)

        return result

    @staticmethod
    def apply_ambient_glow(
        img_bgra: np.ndarray,
        radius: int = 22,
        intensity: float = 0.65,
        glow_color: Tuple[int, int, int] = (0, 215, 255),
    ) -> np.ndarray:
        """Applies a neon / active ambient glow halo around element contours."""
        if img_bgra is None or img_bgra.size == 0:
            return img_bgra
        h, w = img_bgra.shape[:2]
        pad = radius * 2 + 8
        new_h, new_w = h + pad * 2, w + pad * 2

        alpha = img_bgra[:, :, 3]
        glow_canvas = np.zeros((new_h, new_w), dtype=np.uint8)
        glow_canvas[pad : pad + h, pad : pad + w] = alpha

        k = radius * 2 + 1
        blurred = cv2.GaussianBlur(glow_canvas, (k, k), radius * 0.4)
        glow_alpha = np.clip(blurred.astype(np.float32) * intensity, 0, 255).astype(np.uint8)

        result = np.zeros((new_h, new_w, 4), dtype=np.uint8)
        result[:, :, 0] = glow_color[0]
        result[:, :, 1] = glow_color[1]
        result[:, :, 2] = glow_color[2]
        result[:, :, 3] = glow_alpha

        # Blend original over glow
        dest_patch = result[pad : pad + h, pad : pad + w]
        a_src = img_bgra[:, :, 3:4].astype(np.float32) / 255.0
        a_dst = dest_patch[:, :, 3:4].astype(np.float32) / 255.0
        out_a = a_src + a_dst * (1.0 - a_src)
        out_rgb = (img_bgra[:, :, :3] * a_src + dest_patch[:, :, :3] * a_dst * (1.0 - a_src)) / np.maximum(out_a, 1e-6)

        dest_patch[:, :, :3] = np.clip(out_rgb, 0, 255).astype(np.uint8)
        dest_patch[:, :, 3] = np.clip(out_a[:, :, 0] * 255.0, 0, 255).astype(np.uint8)
        return result

    @staticmethod
    def create_glass_card(
        width: int,
        height: int,
        corner_radius: int = 16,
        bg_color: Tuple[int, int, int, int] = (255, 255, 255, 235),
        border_color: Tuple[int, int, int, int] = (220, 228, 245, 255),
        border_width: int = 2,
        add_shadow: bool = True,
    ) -> np.ndarray:
        """Creates a modern Glassmorphism / neumorphic backdrop card with smooth borders."""
        card = np.zeros((height, width, 4), dtype=np.uint8)
        pil_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pil_img)

        # Draw card body
        draw.rounded_rectangle(
            [(border_width, border_width), (width - border_width, height - border_width)],
            radius=corner_radius,
            fill=bg_color,
            outline=border_color,
            width=border_width,
        )

        arr = np.array(pil_img)
        # Convert RGBA to BGRA
        card[:, :, :3] = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
        card[:, :, 3] = arr[:, :, 3]

        if add_shadow:
            card = OpenCutVisualFX.apply_drop_shadow(card, offset=(4, 8), blur_radius=12, opacity=0.35)

        return card


# ==============================================================================
# 4. OpenCut Vector Shapes Engine (Circle, Star, Diamond, Hexagon, etc.)
# ==============================================================================

class OpenCutShapeRenderer:
    """Renders high-quality vector shapes with anti-aliasing directly to BGRA."""

    @staticmethod
    def render(
        shape_name: str,
        size: int = 100,
        fill_color: Tuple[int, int, int, int] = (45, 55, 72, 255),
        stroke_color: Optional[Tuple[int, int, int, int]] = None,
        stroke_width: int = 0,
    ) -> np.ndarray:
        """Renders geometric shapes (circle, square, triangle, diamond, hexagon, star)."""
        scale_super = 4
        ss = size * scale_super
        img = np.zeros((ss, ss, 4), dtype=np.uint8)

        bgr = (fill_color[0], fill_color[1], fill_color[2])
        alpha = fill_color[3]

        if shape_name == "circle":
            center = (ss // 2, ss // 2)
            rad = ss // 2 - stroke_width * scale_super
            cv2.circle(img, center, rad, (*bgr, alpha), -1, cv2.LINE_AA)

        elif shape_name == "square":
            pad = stroke_width * scale_super
            cv2.rectangle(img, (pad, pad), (ss - pad, ss - pad), (*bgr, alpha), -1, cv2.LINE_AA)

        elif shape_name == "triangle":
            pts = np.array([[ss // 2, 0], [ss, ss], [0, ss]], dtype=np.int32)
            cv2.fillPoly(img, [pts], (*bgr, alpha), cv2.LINE_AA)

        elif shape_name == "diamond":
            pts = np.array([[ss // 2, 0], [ss, ss // 2], [ss // 2, ss], [0, ss // 2]], dtype=np.int32)
            cv2.fillPoly(img, [pts], (*bgr, alpha), cv2.LINE_AA)

        elif shape_name == "hexagon":
            pad = ss // 4
            pts = np.array([
                [pad, 0],
                [ss - pad, 0],
                [ss, ss // 2],
                [ss - pad, ss],
                [pad, ss],
                [0, ss // 2],
            ], dtype=np.int32)
            cv2.fillPoly(img, [pts], (*bgr, alpha), cv2.LINE_AA)

        elif shape_name == "star":
            outer_r = ss // 2 - stroke_width * scale_super
            inner_r = outer_r * 0.42
            cx, cy = ss // 2, ss // 2
            pts = []
            for i in range(10):
                r = outer_r if i % 2 == 0 else inner_r
                theta = i * math.pi / 5.0 - math.pi / 2.0
                pts.append([int(cx + r * math.cos(theta)), int(cy + r * math.sin(theta))])
            cv2.fillPoly(img, [np.array(pts, dtype=np.int32)], (*bgr, alpha), cv2.LINE_AA)

        if stroke_color and stroke_width > 0:
            sbgr = (stroke_color[0], stroke_color[1], stroke_color[2], stroke_color[3])
            sw = stroke_width * scale_super
            if shape_name == "circle":
                cv2.circle(img, center, rad, sbgr, sw, cv2.LINE_AA)
            elif shape_name in ("triangle", "diamond", "hexagon", "star"):
                cv2.polylines(img, [np.array(pts, dtype=np.int32)], True, sbgr, sw, cv2.LINE_AA)

        # Downscale with high-quality anti-aliasing
        out = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
        return out


# ==============================================================================
# 5. OpenCut Kinetic Text Engine (Cairo Font + Arabic Typing + Glassplate)
# ==============================================================================

class OpenCutKineticText:
    """Renders high-definition Arabic motion typography with typewriter animation and glass cards."""

    def __init__(self, font_path: str = DEFAULT_CAIRO_FONT):
        self.font_path = font_path if os.path.exists(font_path) else "arial.ttf"
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            self.reshaper = arabic_reshaper
            self.get_display = get_display
            self.has_arabic_support = True
        except ImportError:
            self.has_arabic_support = False

    def reshape_text(self, text: str) -> str:
        if not self.has_arabic_support:
            return text
        try:
            reshaped = self.reshaper.reshape(text)
            return self.get_display(reshaped)
        except Exception:
            return text

    def render_typing_badge(
        self,
        full_text: str,
        typing_progress: float,
        font_size: int = 38,
        text_color: Tuple[int, int, int] = (25, 30, 45),
        accent_color: Tuple[int, int, int] = (0, 150, 255),
        show_cursor: bool = True,
        cursor_blink: bool = True,
        show_card_backdrop: bool = True,
    ) -> np.ndarray:
        """
        Renders Arabic text with real-time typewriter character reveal,
        blinking cursor, and an optional sleek frosted glass card background.
        """
        typing_progress = float(np.clip(typing_progress, 0.0, 1.0))
        total_len = len(full_text)
        visible_chars = int(round(typing_progress * total_len))
        sub_text = full_text[:visible_chars]

        # Load Cairo Font
        try:
            font = ImageFont.truetype(self.font_path, font_size)
        except Exception:
            font = ImageFont.load_default()

        # Reshape for Arabic
        bidi_sub = self.reshape_text(sub_text)
        bidi_full = self.reshape_text(full_text)

        # Measure dimensions with safety margin
        dummy_img = Image.new("RGBA", (100, 100))
        d_dummy = ImageDraw.Draw(dummy_img)

        # Measure bounding box of full text for layout stability
        bbox_full = d_dummy.textbbox((0, 0), bidi_full if bidi_full else "ا", font=font)
        text_w = bbox_full[2] - bbox_full[0]
        text_h = bbox_full[3] - bbox_full[1]

        pad_x = 50
        pad_y = 26
        card_w = text_w + pad_x * 2 + 40
        card_h = text_h + pad_y * 2 + 16

        # Create PIL Image
        pil_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pil_img)

        if show_card_backdrop:
            # Draw Glassmorphism card
            draw.rounded_rectangle(
                [(6, 6), (card_w - 6, card_h - 6)],
                radius=20,
                fill=(255, 255, 255, 248),
                outline=(210, 222, 240, 255),
                width=2,
            )

        # Render visible Arabic text
        if bidi_sub.strip():
            bbox_sub = d_dummy.textbbox((0, 0), bidi_sub, font=font)
            sub_w = bbox_sub[2] - bbox_sub[0]
            # Anchor right edge of Arabic text to card_w - pad_x
            tx = card_w - pad_x - sub_w - bbox_sub[0]
            ty = pad_y - bbox_sub[1]

            # Crisp anti-aliased text
            draw.text((tx, ty), bidi_sub, font=font, fill=(*text_color, 255))

            # Cursor to the left of the typed text
            if show_cursor and (typing_progress < 1.0 or cursor_blink):
                cursor_x = tx + bbox_sub[0] - 10
                cursor_h = text_h + 8
                cursor_y = pad_y
                draw.rounded_rectangle(
                    [(cursor_x - 3, cursor_y), (cursor_x + 1, cursor_y + cursor_h)],
                    radius=2,
                    fill=(*accent_color, 255),
                )

        # Convert PIL RGBA to OpenCV BGRA
        arr = np.array(pil_img)
        bgra = np.zeros_like(arr)
        bgra[:, :, :3] = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
        bgra[:, :, 3] = arr[:, :, 3]

        # Apply soft drop shadow
        if show_card_backdrop:
            bgra = OpenCutVisualFX.apply_drop_shadow(bgra, offset=(4, 10), blur_radius=15, opacity=0.32)

        return bgra


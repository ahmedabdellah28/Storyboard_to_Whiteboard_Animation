"""Master Staged Motion Director Engine (V6 - Dynamic Stage Alternation & Handwriting Typewriter).

Directorial features based on user requirements:
1. Pure white studio background (#FFFFFF).
2. Selective elevation physics: Grounded elements are flat on canvas; aerial elements have flight shadows.
3. Left/Right stage alternation:
   - Scenes alternate elements on the RIGHT (text on LEFT/TOP) and elements on the LEFT (text on RIGHT).
4. Audio synchronization:
   - Text appears strictly AFTER / WITH the spoken voice based on word-by-word timestamps.
5. Diverse positions from all sides (Right, Left, Top-center, Top-left, Bottom-left).
6. Authentic RTL handwriting / typewriter animation (`write_rtl`) with glowing cursor dot, alongside pop-overshoot, slide-in, and impact slams.
7. Fixed camera with micro-shake impact on hammer strike (t=39.5s).
"""

import os
import sys
import json
import math
import subprocess
import time
import numpy as np
import cv2
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Any, Tuple, Optional

# Path setup
ROOT_DIR = str(Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.opencut_fx import (
    ease,
    OpenCutMaskEngine,
    OpenCutVisualFX,
    DEFAULT_CAIRO_FONT,
)

# Resolution & Frame Rate
WIDTH = 1920
HEIGHT = 1080
FPS = 30


# ==============================================================================
# 1. Selective Elevation Configuration
# ==============================================================================

ELEVATED_ASSETS = {
    "r1_04_bee_flying_to_flower",       # Flying bee
    "r2_05_exploding_seed_pod",         # Bursting airborne seeds
    "r3_04_wasp_comparison_callout",    # Floating callout UI card
    "r4_01_wasp_in_love",               # Flying wasp in love
    "r4_02_orchid_hammer_strike",       # Swinging hammer mechanism
    "r4_03_wasp_pollinated_shocked",    # Airborne knocked wasp
    "r4_04_wasp_foolish_flight",        # Flying wasp
}


# ==============================================================================
# 2. Rich Color Palettes
# ==============================================================================

POPUP_THEMES = {
    "emerald": {
        "card_bg": (16, 105, 75, 255),       # Deep Emerald Green
        "border": (52, 211, 153, 255),        # Vibrant Mint Border
        "badge_bg": (52, 211, 153, 255),      # Neon Mint Pill
        "badge_text": (6, 78, 59, 255),       # Dark Forest
        "title_text": (255, 255, 255, 255),   # Pure White
        "accent": (52, 211, 153, 255),
    },
    "crimson": {
        "card_bg": (153, 27, 27, 255),        # Deep Crimson Red
        "border": (248, 113, 113, 255),       # Bright Coral Border
        "badge_bg": (248, 113, 113, 255),     # Coral Pill
        "badge_text": (127, 29, 29, 255),     # Blood Red
        "title_text": (255, 255, 255, 255),   # Pure White
        "accent": (248, 113, 113, 255),
    },
    "amber": {
        "card_bg": (180, 83, 9, 255),         # Deep Warm Amber
        "border": (251, 191, 36, 255),        # Electric Gold Border
        "badge_bg": (251, 191, 36, 255),      # Gold Pill
        "badge_text": (120, 53, 15, 255),     # Bronze
        "title_text": (255, 255, 255, 255),   # Pure White
        "accent": (251, 191, 36, 255),
    },
    "cyan": {
        "card_bg": (14, 116, 144, 255),       # Deep Marine Cyan
        "border": (34, 211, 238, 255),        # Neon Cyan Border
        "badge_bg": (34, 211, 238, 255),      # Cyan Pill
        "badge_text": (22, 78, 99, 255),      # Marine Blue
        "title_text": (255, 255, 255, 255),   # Pure White
        "accent": (34, 211, 238, 255),
    },
    "purple": {
        "card_bg": (109, 40, 217, 255),       # Royal Violet
        "border": (192, 132, 252, 255),       # Electric Lavender Border
        "badge_bg": (192, 132, 252, 255),     # Lavender Pill
        "badge_text": (76, 29, 149, 255),     # Dark Violet
        "title_text": (255, 255, 255, 255),   # Pure White
        "accent": (192, 132, 252, 255),
    },
    "indigo": {
        "card_bg": (67, 56, 202, 255),        # Deep Indigo
        "border": (129, 140, 248, 255),       # Sky Indigo Border
        "badge_bg": (129, 140, 248, 255),     # Indigo Pill
        "badge_text": (49, 46, 129, 255),     # Midnight Navy
        "title_text": (255, 255, 255, 255),   # Pure White
        "accent": (129, 140, 248, 255),
    },
    "navy_gold": {
        "card_bg": (15, 23, 42, 255),         # Deep Midnight Slate
        "border": (245, 158, 11, 255),        # Brilliant Metallic Gold
        "badge_bg": (245, 158, 11, 255),      # Gold Pill
        "badge_text": (15, 23, 42, 255),      # Midnight Slate
        "title_text": (255, 255, 255, 255),   # Pure White
        "accent": (245, 158, 11, 255),
    },
}


# ==============================================================================
# 3. Multi-Style Kinetic Typography Engine (with RTL Handwriting)
# ==============================================================================

class DiverseTypographyEngine:
    """Renders multiple distinct motion graphics text styles with Cairo-Bold."""

    def __init__(self, font_path: str = DEFAULT_CAIRO_FONT):
        self.font_path = font_path if os.path.exists(font_path) else "arial.ttf"
        import arabic_reshaper
        from bidi.algorithm import get_display
        self.reshaper = arabic_reshaper
        self.get_display = get_display

    def shape(self, text: str) -> str:
        try:
            return self.get_display(self.reshaper.reshape(text))
        except Exception:
            return text

    def render_element_text(
        self,
        style_type: str,
        badge: str,
        word: str,
        theme_name: str = "cyan",
        write_progress: float = 1.0,
    ) -> np.ndarray:
        """Dispatches to the appropriate graphic style generator."""
        if style_type == "top_banner":
            return self._render_top_banner(badge, word, theme_name)
        elif style_type == "clean_line_type":
            return self._render_clean_line_type(badge, word, theme_name, write_progress)
        elif style_type == "impact_slam":
            return self._render_impact_slam(badge, word, theme_name)
        elif style_type == "pointer_tag":
            return self._render_pointer_tag(badge, word, theme_name)
        elif style_type == "gold_hero":
            return self._render_gold_hero(badge, word)
        else:
            return self._render_card_badge(badge, word, theme_name, write_progress)

    # Style 1: Card Badge (Classic vibrant rounded card with optional RTL handwriting)
    def _render_card_badge(self, badge: str, word: str, theme_name: str, write_p: float = 1.0) -> np.ndarray:
        theme = POPUP_THEMES.get(theme_name, POPUP_THEMES["cyan"])
        s_badge = self.shape(badge)
        s_word = self.shape(word)

        font_badge = ImageFont.truetype(self.font_path, 26)
        font_word = ImageFont.truetype(self.font_path, 70)

        dummy = Image.new("RGBA", (10, 10))
        d_dummy = ImageDraw.Draw(dummy)

        bb_b = d_dummy.textbbox((0, 0), s_badge, font=font_badge)
        bw, bh = bb_b[2] - bb_b[0], bb_b[3] - bb_b[1]
        bb_w = d_dummy.textbbox((0, 0), s_word, font=font_word)
        ww, wh = bb_w[2] - bb_w[0], bb_w[3] - bb_w[1]

        card_w = max(ww + 120, bw + 140, 400)
        card_h = bh + wh + 110

        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle(
            [(3, 3), (card_w - 3, card_h - 3)],
            radius=28,
            fill=theme["card_bg"],
            outline=theme["border"],
            width=5,
        )

        badge_w = bw + 36
        badge_h = bh + 14
        badge_x = (card_w - badge_w) // 2
        badge_y = 20
        draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)], radius=12, fill=theme["badge_bg"])
        bx_txt = (card_w - bw) // 2 - bb_b[0]
        by_txt = badge_y + 7 - bb_b[1]
        draw.text((bx_txt, by_txt), s_badge, font=font_badge, fill=theme["badge_text"])

        # Word layer with RTL mask
        word_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        d_word = ImageDraw.Draw(word_img)
        tx = (card_w - ww) // 2 - bb_w[0]
        ty = badge_y + badge_h + 18 - bb_w[1]
        d_word.text((tx, ty), s_word, font=font_word, fill=theme["title_text"])

        w_arr = np.array(word_img)
        if write_p < 0.999:
            # Mask from right to left
            text_x_start = (card_w - ww) // 2
            text_x_end = text_x_start + ww
            cutoff = int(round(text_x_end - ww * write_p))
            w_arr[:, :cutoff, 3] = 0

            # Draw glowing pen/cursor nib at current writing position
            if 0.05 < write_p < 0.98:
                nib_x = np.clip(cutoff, 0, card_w - 1)
                nib_y = ty + wh // 2
                cv2.circle(w_arr, (nib_x, nib_y), 6, theme["border"], -1)

        # Composite word layer on card base
        base_arr = np.array(img)
        wa = (w_arr[:, :, 3].astype(np.float32) / 255.0)
        wa3 = np.dstack([wa, wa, wa])
        blended = w_arr[:, :, :3].astype(np.float32) * wa3 + base_arr[:, :, :3].astype(np.float32) * (1.0 - wa3)
        base_arr[:, :, :3] = np.clip(blended, 0, 255).astype(np.uint8)
        base_arr[:, :, 3] = np.maximum(base_arr[:, :, 3], w_arr[:, :, 3])

        return self._to_bgra_shadow(Image.fromarray(base_arr), offset=(8, 18), blur=24, opacity=0.40)

    # Style 2: Top Banner (Wide broadcast ribbon across top)
    def _render_top_banner(self, badge: str, word: str, theme_name: str) -> np.ndarray:
        theme = POPUP_THEMES.get(theme_name, POPUP_THEMES["crimson"])
        s_badge = self.shape(badge)
        s_word = self.shape(word)

        font_badge = ImageFont.truetype(self.font_path, 28)
        font_word = ImageFont.truetype(self.font_path, 68)

        dummy = Image.new("RGBA", (10, 10))
        d_dummy = ImageDraw.Draw(dummy)

        bb_b = d_dummy.textbbox((0, 0), s_badge, font=font_badge)
        bw, bh = bb_b[2] - bb_b[0], bb_b[3] - bb_b[1]
        bb_w = d_dummy.textbbox((0, 0), s_word, font=font_word)
        ww, wh = bb_w[2] - bb_w[0], bb_w[3] - bb_w[1]

        banner_w = max(ww + bw + 180, 720)
        banner_h = max(wh, bh) + 60

        img = Image.new("RGBA", (banner_w, banner_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle(
            [(3, 3), (banner_w - 3, banner_h - 3)],
            radius=30,
            fill=theme["card_bg"],
            outline=theme["border"],
            width=5,
        )

        badge_w = bw + 34
        badge_h = bh + 14
        badge_x = banner_w - badge_w - 30
        badge_y = (banner_h - badge_h) // 2
        draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)], radius=14, fill=theme["badge_bg"])
        bx_txt = badge_x + 17 - bb_b[0]
        by_txt = badge_y + 7 - bb_b[1]
        draw.text((bx_txt, by_txt), s_badge, font=font_badge, fill=theme["badge_text"])

        tx = 40 - bb_w[0]
        ty = (banner_h - wh) // 2 - bb_w[1]
        draw.text((tx, ty), s_word, font=font_word, fill=theme["title_text"])

        return self._to_bgra_shadow(img, offset=(6, 16), blur=24, opacity=0.40)

    # Style 3: Clean Line Type (Modern box-less typography with animated accent line)
    def _render_clean_line_type(self, badge: str, word: str, theme_name: str, write_p: float = 1.0) -> np.ndarray:
        theme = POPUP_THEMES.get(theme_name, POPUP_THEMES["purple"])
        s_badge = self.shape(badge)
        s_word = self.shape(word)

        font_badge = ImageFont.truetype(self.font_path, 24)
        font_word = ImageFont.truetype(self.font_path, 76)

        dummy = Image.new("RGBA", (10, 10))
        d_dummy = ImageDraw.Draw(dummy)

        bb_b = d_dummy.textbbox((0, 0), s_badge, font=font_badge)
        bw, bh = bb_b[2] - bb_b[0], bb_b[3] - bb_b[1]
        bb_w = d_dummy.textbbox((0, 0), s_word, font=font_word)
        ww, wh = bb_w[2] - bb_w[0], bb_w[3] - bb_w[1]

        total_w = max(ww, bw) + 80
        total_h = bh + wh + 60

        img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bx_txt = (total_w - bw) // 2 - bb_b[0]
        draw.text((bx_txt, 10 - bb_b[1]), s_badge, font=font_badge, fill=theme["border"])

        tx = (total_w - ww) // 2 - bb_w[0]
        ty = bh + 24 - bb_w[1]
        draw.text((tx, ty), s_word, font=font_word, fill=theme["card_bg"])

        line_w = int(ww * 0.9 * write_p)
        lx1 = (total_w - int(ww * 0.9)) // 2
        ly = ty + wh + 12
        if line_w > 4:
            draw.rounded_rectangle([(lx1, ly), (lx1 + line_w, ly + 5)], radius=3, fill=theme["border"])

        arr = np.array(img)
        if write_p < 0.999:
            # Mask text from right to left
            text_x_start = (total_w - ww) // 2
            text_x_end = text_x_start + ww
            cutoff = int(round(text_x_end - ww * write_p))
            arr[:, :cutoff, 3] = 0

        bgra = np.zeros_like(arr)
        bgra[:, :, :3] = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
        bgra[:, :, 3] = arr[:, :, 3]
        return bgra

    # Style 4: Impact Slam (Bold heavy warning stamp)
    def _render_impact_slam(self, badge: str, word: str, theme_name: str) -> np.ndarray:
        theme = POPUP_THEMES.get(theme_name, POPUP_THEMES["crimson"])
        s_badge = self.shape(badge)
        s_word = self.shape(word)

        font_badge = ImageFont.truetype(self.font_path, 28)
        font_word = ImageFont.truetype(self.font_path, 80)

        dummy = Image.new("RGBA", (10, 10))
        d_dummy = ImageDraw.Draw(dummy)

        bb_b = d_dummy.textbbox((0, 0), s_badge, font=font_badge)
        bw, bh = bb_b[2] - bb_b[0], bb_b[3] - bb_b[1]
        bb_w = d_dummy.textbbox((0, 0), s_word, font=font_word)
        ww, wh = bb_w[2] - bb_w[0], bb_w[3] - bb_w[1]

        card_w = max(ww + 140, bw + 160, 440)
        card_h = bh + wh + 115

        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle(
            [(4, 4), (card_w - 4, card_h - 4)],
            radius=24,
            fill=theme["card_bg"],
            outline=theme["border"],
            width=7,
        )

        badge_w = bw + 38
        badge_h = bh + 14
        badge_x = (card_w - badge_w) // 2
        badge_y = 18
        draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)], radius=10, fill=theme["badge_bg"])
        bx_txt = (card_w - bw) // 2 - bb_b[0]
        by_txt = badge_y + 7 - bb_b[1]
        draw.text((bx_txt, by_txt), s_badge, font=font_badge, fill=theme["badge_text"])

        tx = (card_w - ww) // 2 - bb_w[0]
        ty = badge_y + badge_h + 16 - bb_w[1]
        draw.text((tx, ty), s_word, font=font_word, fill=theme["title_text"])

        return self._to_bgra_shadow(img, offset=(10, 22), blur=28, opacity=0.45)

    # Style 5: Pointer Tag (Horizontal tag with directional indicator)
    def _render_pointer_tag(self, badge: str, word: str, theme_name: str) -> np.ndarray:
        theme = POPUP_THEMES.get(theme_name, POPUP_THEMES["cyan"])
        s_badge = self.shape(badge)
        s_word = self.shape(word)

        font_badge = ImageFont.truetype(self.font_path, 24)
        font_word = ImageFont.truetype(self.font_path, 64)

        dummy = Image.new("RGBA", (10, 10))
        d_dummy = ImageDraw.Draw(dummy)

        bb_b = d_dummy.textbbox((0, 0), s_badge, font=font_badge)
        bw, bh = bb_b[2] - bb_b[0], bb_b[3] - bb_b[1]
        bb_w = d_dummy.textbbox((0, 0), s_word, font=font_word)
        ww, wh = bb_w[2] - bb_w[0], bb_w[3] - bb_w[1]

        tag_w = max(ww + 110, 380)
        tag_h = bh + wh + 90

        img = Image.new("RGBA", (tag_w, tag_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle(
            [(3, 3), (tag_w - 3, tag_h - 3)],
            radius=22,
            fill=theme["card_bg"],
            outline=theme["border"],
            width=4,
        )

        dot_r = 8
        dot_cx = tag_w - 24
        dot_cy = tag_h // 2
        draw.ellipse([(dot_cx - dot_r, dot_cy - dot_r), (dot_cx + dot_r, dot_cy + dot_r)], fill=theme["border"])

        badge_w = bw + 28
        badge_h = bh + 10
        badge_x = (tag_w - 40 - badge_w) // 2 + 10
        badge_y = 16
        draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)], radius=10, fill=theme["badge_bg"])
        bx_txt = badge_x + 14 - bb_b[0]
        by_txt = badge_y + 5 - bb_b[1]
        draw.text((bx_txt, by_txt), s_badge, font=font_badge, fill=theme["badge_text"])

        tx = (tag_w - 40 - ww) // 2 + 10 - bb_w[0]
        ty = badge_y + badge_h + 14 - bb_w[1]
        draw.text((tx, ty), s_word, font=font_word, fill=theme["title_text"])

        return self._to_bgra_shadow(img, offset=(6, 14), blur=20, opacity=0.35)

    # Style 6: Gold Hero (Deep obsidian & metallic gold badge for grand finale)
    def _render_gold_hero(self, badge: str, word: str) -> np.ndarray:
        theme = POPUP_THEMES["navy_gold"]
        s_badge = self.shape(badge)
        s_word = self.shape(word)

        font_badge = ImageFont.truetype(self.font_path, 28)
        font_word = ImageFont.truetype(self.font_path, 80)

        dummy = Image.new("RGBA", (10, 10))
        d_dummy = ImageDraw.Draw(dummy)

        bb_b = d_dummy.textbbox((0, 0), s_badge, font=font_badge)
        bw, bh = bb_b[2] - bb_b[0], bb_b[3] - bb_b[1]
        bb_w = d_dummy.textbbox((0, 0), s_word, font=font_word)
        ww, wh = bb_w[2] - bb_w[0], bb_w[3] - bb_w[1]

        card_w = max(ww + 150, bw + 170, 480)
        card_h = bh + wh + 120

        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle(
            [(4, 4), (card_w - 4, card_h - 4)],
            radius=30,
            fill=theme["card_bg"],
            outline=theme["border"],
            width=6,
        )

        badge_w = bw + 40
        badge_h = bh + 16
        badge_x = (card_w - badge_w) // 2
        badge_y = 20
        draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)], radius=12, fill=theme["badge_bg"])
        bx_txt = (card_w - bw) // 2 - bb_b[0]
        by_txt = badge_y + 8 - bb_b[1]
        draw.text((bx_txt, by_txt), s_badge, font=font_badge, fill=theme["badge_text"])

        tx = (card_w - ww) // 2 - bb_w[0]
        ty = badge_y + badge_h + 18 - bb_w[1]
        draw.text((tx, ty), s_word, font=font_word, fill=theme["title_text"])

        return self._to_bgra_shadow(img, offset=(10, 24), blur=30, opacity=0.48)

    @staticmethod
    def _to_bgra_shadow(img: Image.Image, offset=(8, 18), blur=24, opacity=0.40) -> np.ndarray:
        arr = np.array(img)
        bgra = np.zeros_like(arr)
        bgra[:, :, :3] = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
        bgra[:, :, 3] = arr[:, :, 3]
        return OpenCutVisualFX.apply_drop_shadow(bgra, offset=offset, blur_radius=blur, opacity=opacity)


# ==============================================================================
# 4. Cinematic Scenes Architecture (Alternating Sides, Audio-Sync, Handwriting)
# ==============================================================================

SCENES = [
    # Scene 1: Innocent Narrator (Elements on RIGHT, Text on LEFT)
    # Audio: "مسالمة" spoken at 2.42s -> 3.06s; "وبريئة" spoken at 3.06s -> 3.76s
    {
        "id": "scene_01",
        "start": 0.0,
        "end": 3.76,
        "elements": [
            {
                "asset_key": "r1_01_narrator_thinking",
                "start": 0.0,
                "end": 3.76,
                "pos": (1300, 540),
                "target_size": 620,
            }
        ],
        "words": [
            {
                "start": 2.45,
                "end": 3.10,
                "style_type": "card_badge",
                "anim_type": "pop_overshoot",
                "badge": "تساؤل",
                "word": "مسالمة؟",
                "theme": "emerald",
                "pos": (580, 540),
            },
            {
                "start": 3.10,
                "end": 3.76,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "ظن بريء",
                "word": "بريئة؟",
                "theme": "emerald",
                "pos": (580, 540),
            },
        ],
    },

    # Scene 2: Sweet Flower & Bee Arriving (ALTERNATION: Elements on LEFT, Text on RIGHT)
    # Audio: "وردة حلوة" spoken at 5.14s -> 5.76s; "نحلة تمر عشان تلقحها" at 7.32s -> 9.32s
    {
        "id": "scene_02",
        "start": 3.76,
        "end": 9.32,
        "elements": [
            {
                "asset_key": "r1_03_sweet_pink_flower",
                "start": 3.76,
                "end": 9.32,
                "pos": (520, 540),
                "target_size": 580,
            },
            {
                "asset_key": "r1_04_bee_flying_to_flower",
                "start": 7.00,
                "end": 9.32,
                "pos": (880, 490),
                "target_size": 580,
            },
        ],
        "words": [
            {
                "start": 5.20,
                "end": 7.30,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "طبيعة",
                "word": "وردة حلوة",
                "theme": "emerald",
                "pos": (1380, 460),
            },
            {
                "start": 7.35,
                "end": 9.32,
                "style_type": "pointer_tag",
                "anim_type": "slide_in_left",
                "badge": "انتظار",
                "word": "نحلة تلقحها",
                "theme": "cyan",
                "pos": (1380, 620),
            },
        ],
    },

    # Scene 3: The Shocking Twist! (Elements on RIGHT, Text in TOP-CENTER)
    # Audio: "بس الحقيقة؟" spoken at 9.32s -> 10.38s
    {
        "id": "scene_03",
        "start": 9.32,
        "end": 10.38,
        "elements": [
            {
                "asset_key": "r2_01_narrator_shocked",
                "start": 9.32,
                "end": 10.38,
                "pos": (1300, 560),
                "target_size": 620,
            }
        ],
        "words": [
            {
                "start": 9.40,
                "end": 10.38,
                "style_type": "top_banner",
                "anim_type": "slide_in_top",
                "badge": "صدمة كبرى",
                "word": "بس الحقيقة؟",
                "theme": "crimson",
                "pos": (960, 220),
            }
        ],
    },

    # Scene 4: Carnivorous Trio & Seeds (ALTERNATION: Elements on LEFT, Text on RIGHT)
    # Audio: "بايعتها" spoken at 12.08s -> 13.32s; "الخطف" at 13.98s -> 14.54s; "التفجير" at 15.72s -> 16.20s
    {
        "id": "scene_04",
        "start": 10.38,
        "end": 17.36,
        "elements": [
            {
                "asset_key": "r2_02_carnivorous_trio",
                "start": 10.38,
                "end": 17.36,
                "pos": (520, 540),
                "target_size": 620,
            },
            {
                "asset_key": "r2_05_exploding_seed_pod",
                "start": 14.50,
                "end": 17.36,
                "pos": (920, 520),
                "target_size": 540,
            },
        ],
        "words": [
            {
                "start": 12.10,
                "end": 13.95,
                "style_type": "impact_slam",
                "anim_type": "impact_slam",
                "badge": "شراسة",
                "word": "بـايـعـتـهـا!",
                "theme": "crimson",
                "pos": (1420, 380),
            },
            {
                "start": 14.00,
                "end": 15.70,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "افتراس",
                "word": "خـطـف!",
                "theme": "amber",
                "pos": (1420, 520),
            },
            {
                "start": 15.75,
                "end": 17.36,
                "style_type": "impact_slam",
                "anim_type": "impact_slam",
                "badge": "قوة ميكانيكية",
                "word": "تـفـجـيـر!",
                "theme": "purple",
                "pos": (1420, 660),
            },
        ],
    },

    # Scene 5: Hammer Orchid & Australia Map (ALTERNATION: Elements on RIGHT, Text on LEFT)
    # Audio: "أوركيد المطرقة" spoken at 18.14s -> 19.14s; "أستراليا" at 19.30s -> 20.10s; "تدلع" at 22.02s -> 23.10s
    {
        "id": "scene_05",
        "start": 17.36,
        "end": 23.92,
        "elements": [
            {
                "asset_key": "r3_01_hammer_orchid_plant",
                "start": 17.36,
                "end": 23.92,
                "pos": (1400, 540),
                "target_size": 600,
            },
            {
                "asset_key": "r3_02_australia_map",
                "start": 19.30,
                "end": 23.92,
                "pos": (980, 520),
                "target_size": 560,
            },
        ],
        "words": [
            {
                "start": 18.15,
                "end": 19.30,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "البطل",
                "word": "أوركيد المطرقة",
                "theme": "cyan",
                "pos": (480, 420),
            },
            {
                "start": 19.35,
                "end": 22.00,
                "style_type": "card_badge",
                "anim_type": "pop_overshoot",
                "badge": "الموطن",
                "word": "أستراليا",
                "theme": "cyan",
                "pos": (480, 540),
            },
            {
                "start": 22.10,
                "end": 23.92,
                "style_type": "pointer_tag",
                "anim_type": "slide_in_left",
                "badge": "بدون رحيق",
                "word": "ما تدلع!",
                "theme": "amber",
                "pos": (480, 660),
            },
        ],
    },

    # Scene 6: Orchid Mimic & Callout (ALTERNATION: Elements on LEFT, Text on RIGHT)
    # Audio: "نسخة طبق الأصل" spoken at 28.40s -> 29.54s; "أنثى دبور" at 29.54s -> 31.26s
    {
        "id": "scene_06",
        "start": 23.92,
        "end": 31.26,
        "elements": [
            {
                "asset_key": "r3_03_orchid_mimic_flower",
                "start": 23.92,
                "end": 31.26,
                "pos": (520, 540),
                "target_size": 600,
            },
            {
                "asset_key": "r3_04_wasp_comparison_callout",
                "start": 27.00,
                "end": 31.26,
                "pos": (940, 520),
                "target_size": 580,
            },
        ],
        "words": [
            {
                "start": 28.45,
                "end": 29.55,
                "style_type": "clean_line_type",
                "anim_type": "mask_reveal_up",
                "badge": "تطابق تام",
                "word": "نسخة طبق الأصل!",
                "theme": "purple",
                "pos": (1400, 480),
            },
            {
                "start": 29.60,
                "end": 31.26,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "خداع عبقري",
                "word": "أنثى دبور!",
                "theme": "indigo",
                "pos": (1400, 620),
            },
        ],
    },

    # Scene 7: Male Wasp Flying in Love (Elements on RIGHT, Text on BOTTOM-LEFT)
    # Audio: "طاير ومتحمس" spoken at 32.20s -> 33.50s; "شريكة حياته" at 34.20s -> 35.76s
    {
        "id": "scene_07",
        "start": 31.26,
        "end": 35.76,
        "elements": [
            {
                "asset_key": "r4_01_wasp_in_love",
                "start": 31.26,
                "end": 35.76,
                "pos": (1300, 540),
                "target_size": 620,
            }
        ],
        "words": [
            {
                "start": 32.25,
                "end": 34.20,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "حب أعمى",
                "word": "عـاشـق!",
                "theme": "amber",
                "pos": (580, 640),
            },
            {
                "start": 34.25,
                "end": 35.76,
                "style_type": "card_badge",
                "anim_type": "pop_overshoot",
                "badge": "فخ عاطفي",
                "word": "شريكة حياته!",
                "theme": "amber",
                "pos": (580, 640),
            },
        ],
    },

    # Scene 8: The Hammer Strike Slam! (Element CENTER-RIGHT, Text TOP-LEFT, Shake at 39.5s)
    # Audio: "المطرقة تضربه" spoken at 39.50s -> 40.52s; "كيس لقاح أصفر" at 41.00s -> 44.62s
    {
        "id": "scene_08",
        "start": 35.76,
        "end": 44.62,
        "elements": [
            {
                "asset_key": "r4_02_orchid_hammer_strike",
                "start": 35.76,
                "end": 44.62,
                "pos": (1180, 520),
                "target_size": 720,
                "shake_at": 39.50,
            }
        ],
        "words": [
            {
                "start": 39.50,
                "end": 41.15,
                "style_type": "impact_slam",
                "anim_type": "impact_slam",
                "badge": "اصطدام عنيف",
                "word": "طـاخ!",
                "theme": "crimson",
                "pos": (480, 360),
            },
            {
                "start": 41.20,
                "end": 44.62,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "كيس أصفر",
                "word": "كيس لقاح أصفر",
                "theme": "amber",
                "pos": (480, 520),
            },
        ],
    },

    # Scene 9: Shocked Wasp & 2nd Flower (ALTERNATION: Elements on LEFT, Text on RIGHT)
    # Audio: "مصدوم ومحبط" spoken at 45.30s -> 46.80s; "نفس الخدعة" at 48.00s -> 50.00s; "نقل اللقاح" at 50.76s -> 52.50s
    {
        "id": "scene_09",
        "start": 44.62,
        "end": 52.50,
        "elements": [
            {
                "asset_key": "r4_03_wasp_pollinated_shocked",
                "start": 44.62,
                "end": 52.50,
                "pos": (520, 540),
                "target_size": 600,
            },
            {
                "asset_key": "r4_05_second_orchid_pollination",
                "start": 48.50,
                "end": 52.50,
                "pos": (940, 520),
                "target_size": 580,
            },
        ],
        "words": [
            {
                "start": 45.35,
                "end": 48.05,
                "style_type": "clean_line_type",
                "anim_type": "mask_reveal_up",
                "badge": "ذهول",
                "word": "مـصـدوم!",
                "theme": "purple",
                "pos": (1420, 420),
            },
            {
                "start": 48.10,
                "end": 50.75,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "تكرار السذاجة",
                "word": "سـذاجـة!",
                "theme": "purple",
                "pos": (1420, 540),
            },
            {
                "start": 50.80,
                "end": 52.50,
                "style_type": "pointer_tag",
                "anim_type": "slide_in_left",
                "badge": "الهدف تحقق",
                "word": "نـقـل اللقاح!",
                "theme": "cyan",
                "pos": (1420, 660),
            },
        ],
    },

    # Scene 10: Grand Finale (Elements on RIGHT, Text on LEFT)
    # Audio: "كات فيش" spoken at 53.20s -> 54.40s; "ببلاش" at 55.00s -> 56.28s
    {
        "id": "scene_10",
        "start": 52.50,
        "end": 56.28,
        "elements": [
            {
                "asset_key": "r4_03_wasp_pollinated_shocked",
                "start": 52.50,
                "end": 56.28,
                "pos": (1300, 540),
                "target_size": 620,
            }
        ],
        "words": [
            {
                "start": 53.25,
                "end": 55.00,
                "style_type": "gold_hero",
                "anim_type": "pop_overshoot",
                "badge": "احتيال كاسح",
                "word": "كـات فـيـش!",
                "theme": "navy_gold",
                "pos": (580, 540),
            },
            {
                "start": 55.05,
                "end": 56.28,
                "style_type": "gold_hero",
                "anim_type": "pop_overshoot",
                "badge": "استغلال تام",
                "word": "بـبـلاش!",
                "theme": "navy_gold",
                "pos": (580, 540),
            },
        ],
    },
]


# ==============================================================================
# 5. Master Engine Implementation (V6)
# ==============================================================================

class MasterStagedMotionDirector:
    """Master motion graphics engine with stage alternation, audio sync, and RTL handwriting."""

    def __init__(
        self,
        storyboard_path: str,
        audio_path: str,
        assets_metadata_path: str,
        assets_dir: str,
        output_mp4_path: str,
        width: int = WIDTH,
        height: int = HEIGHT,
        fps: int = FPS,
    ):
        self.storyboard_path = storyboard_path
        self.audio_path = audio_path
        self.assets_metadata_path = assets_metadata_path
        self.assets_dir = assets_dir
        self.output_mp4_path = Path(output_mp4_path)
        self.width = width
        self.height = height
        self.fps = fps

        # Multi-style typography engine
        self.typo = DiverseTypographyEngine(DEFAULT_CAIRO_FONT)

        # Preload visual assets with selective elevation physics
        self.assets = self._preload_assets()

        # Storyboard image for opening transition
        self.storyboard_img = None
        if os.path.exists(storyboard_path):
            raw = cv2.imdecode(np.fromfile(storyboard_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if raw is not None:
                self.storyboard_img = cv2.resize(raw, (self.width, self.height), interpolation=cv2.INTER_AREA)

        self.duration_sec = 56.28
        self.total_frames = int(round(self.duration_sec * self.fps))

    def _preload_assets(self) -> Dict[str, np.ndarray]:
        """Preloads assets: elevated elements get shadows, grounded elements remain flat."""
        loaded = {}
        if not os.path.exists(self.assets_metadata_path):
            return loaded

        with open(self.assets_metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        all_entries = {**data.get("primary_assets", {}), **data.get("sub_elements", {})}
        for k, v in all_entries.items():
            fname = v.get("filename", "")
            fpath = os.path.join(self.assets_dir, fname)
            if os.path.exists(fpath):
                raw = cv2.imdecode(np.fromfile(fpath, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                if raw is not None:
                    if k in ELEVATED_ASSETS:
                        processed = OpenCutVisualFX.apply_drop_shadow(raw, offset=(10, 22), blur_radius=24, opacity=0.38)
                    else:
                        processed = OpenCutVisualFX.apply_drop_shadow(raw, offset=(1, 3), blur_radius=4, opacity=0.10)
                    loaded[k] = processed
        print(f"Preloaded {len(loaded)} visual assets with selective elevation physics.")
        return loaded

    def render_frame(self, t: float) -> np.ndarray:
        """Renders the master frame at timestamp t."""
        # Clean white studio background (255 pure canvas)
        canvas = np.full((self.height, self.width, 3), 255, dtype=np.uint8)

        # 1. Opening Storyboard Split-Wipe Transition (0.0s -> 1.0s)
        storyboard_hold = 0.3
        storyboard_wipe = 0.7
        if self.storyboard_img is not None and t < (storyboard_hold + storyboard_wipe):
            if t <= storyboard_hold:
                canvas = self.storyboard_img.copy()
            else:
                wipe_p = (t - storyboard_hold) / storyboard_wipe
                eased_w = ease(wipe_p, "ease_out_cubic")
                mask = OpenCutMaskEngine.split_wipe_mask(self.width, self.height, eased_w, angle_deg=22.0, feather_px=65)
                m3 = np.dstack([mask, mask, mask])
                canvas = (canvas.astype(np.float32) * m3 + self.storyboard_img.astype(np.float32) * (1.0 - m3)).astype(np.uint8)

        # 2. Find Active Scene
        active_scene = None
        for sc in SCENES:
            if sc["start"] <= t <= sc["end"]:
                active_scene = sc
                break

        if active_scene is None:
            return canvas

        # Micro-shake logic (for hammer strike)
        shake_x, shake_y = 0, 0
        for el in active_scene.get("elements", []):
            if "shake_at" in el:
                dt_shake = t - el["shake_at"]
                if 0.0 <= dt_shake <= 0.35:
                    decay = 1.0 - dt_shake / 0.35
                    shake_mag = decay * 14.0
                    shake_x = int(math.sin(dt_shake * 80.0) * shake_mag)
                    shake_y = int(math.cos(dt_shake * 90.0) * shake_mag)

        # ======================================================================
        # LAYER 1: ROCK-SOLID ELEMENTS (Alternating Left / Right across scenes)
        # ======================================================================
        for el in active_scene.get("elements", []):
            if el["start"] <= t <= el["end"]:
                asset_key = el["asset_key"]
                if asset_key in self.assets:
                    img = self.assets[asset_key]
                    sh, sw = img.shape[:2]

                    el_age = t - el["start"]
                    el_left = el["end"] - t

                    in_dur = 0.35
                    out_dur = 0.25
                    p_in = min(1.0, el_age / in_dur)
                    p_out = min(1.0, el_left / out_dur)
                    el_alpha = min(p_in, p_out)

                    # Snappy entrance scale pop with overshoot
                    scale_in = ease(p_in, "ease_out_back")
                    scale_out = ease(p_out, "ease_out_cubic")
                    final_scale_mult = scale_in * scale_out

                    target_box = float(el.get("target_size", 600))
                    base_scale = min(target_box / float(max(sw, sh)), 1.5)
                    draw_scale = base_scale * final_scale_mult

                    dw = max(4, int(round(sw * draw_scale)))
                    dh = max(4, int(round(sh * draw_scale)))

                    # Rock-solid fixed center position (NO idle float!)
                    cx, cy = el["pos"]
                    pos_x = int(round(cx - dw / 2.0)) + shake_x
                    pos_y = int(round(cy - dh / 2.0)) + shake_y

                    resized = cv2.resize(img, (dw, dh), interpolation=cv2.INTER_AREA)
                    self._composite(canvas, resized, pos_x, pos_y, alpha=el_alpha)

        # ======================================================================
        # LAYER 2: DIVERSE KINETIC TYPOGRAPHY (Audio-Synced & Diverse Placements)
        # ======================================================================
        for wd in active_scene.get("words", []):
            if wd["start"] <= t <= wd["end"]:
                w_age = t - wd["start"]
                w_left = wd["end"] - t

                w_in_dur = 0.26
                w_out_dur = 0.22
                p_in = min(1.0, w_age / w_in_dur)
                p_out = min(1.0, w_left / w_out_dur)
                w_alpha = min(p_in, p_out)

                if w_alpha > 0.01:
                    badge = wd.get("badge", "ملاحظة")
                    word = wd["word"]
                    theme = wd.get("theme", "cyan")
                    style_type = wd.get("style_type", "card_badge")
                    anim_type = wd.get("anim_type", "pop_overshoot")

                    # Handwriting progress calculation (types out over 0.40s)
                    write_prog = min(1.0, w_age / 0.40) if anim_type == "write_rtl" else 1.0

                    text_sprite = self.typo.render_element_text(
                        style_type=style_type,
                        badge=badge,
                        word=word,
                        theme_name=theme,
                        write_progress=write_prog,
                    )

                    cw, ch = text_sprite.shape[1], text_sprite.shape[0]

                    offset_x, offset_y = 0, 0
                    draw_scale = 1.0

                    if anim_type == "pop_overshoot":
                        draw_scale = (0.70 + 0.30 * ease(p_in, "ease_out_back")) * (0.80 + 0.20 * ease(p_out, "ease_out_cubic"))

                    elif anim_type == "write_rtl":
                        # Stable scale with smooth exit
                        draw_scale = 1.0 * (0.85 + 0.15 * ease(p_out, "ease_out_cubic"))

                    elif anim_type == "slide_in_left":
                        eased_in = ease(p_in, "ease_out_cubic")
                        offset_x = int(round((1.0 - eased_in) * -120.0))
                        draw_scale = (0.85 + 0.15 * eased_in) * (0.85 + 0.15 * ease(p_out, "ease_out_cubic"))

                    elif anim_type == "slide_in_top":
                        eased_in = ease(p_in, "ease_out_cubic")
                        offset_y = int(round((1.0 - eased_in) * -90.0))
                        draw_scale = (0.90 + 0.10 * eased_in) * (0.90 + 0.10 * ease(p_out, "ease_out_cubic"))

                    elif anim_type == "impact_slam":
                        eased_in = ease(p_in, "ease_out_cubic")
                        slam_scale = 1.6 - 0.6 * eased_in
                        draw_scale = slam_scale * (0.85 + 0.15 * ease(p_out, "ease_out_cubic"))

                    elif anim_type == "mask_reveal_up":
                        eased_in = ease(p_in, "ease_out_cubic")
                        offset_y = int(round((1.0 - eased_in) * 35.0))
                        draw_scale = (0.92 + 0.08 * eased_in) * (0.92 + 0.08 * ease(p_out, "ease_out_cubic"))

                    scaled_w = max(4, int(round(cw * draw_scale)))
                    scaled_h = max(4, int(round(ch * draw_scale)))

                    sprite_resized = cv2.resize(text_sprite, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)

                    cx, cy = wd.get("pos", (550, 540))
                    target_x = int(round(cx - scaled_w / 2.0)) + offset_x + shake_x
                    target_y = int(round(cy - scaled_h / 2.0)) + offset_y + shake_y

                    self._composite(canvas, sprite_resized, target_x, target_y, alpha=w_alpha)

        return canvas

    @staticmethod
    def _composite(canvas: np.ndarray, sprite_bgra: np.ndarray, x: int, y: int, alpha: float = 1.0) -> None:
        """Fast alpha blending directly with numpy slicing."""
        if sprite_bgra is None or sprite_bgra.size == 0 or alpha <= 0.0:
            return
        ch, cw = canvas.shape[:2]
        sh, sw = sprite_bgra.shape[:2]

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(cw, x + sw)
        y2 = min(ch, y + sh)

        if x1 >= x2 or y1 >= y2:
            return

        sx1 = x1 - x
        sy1 = y1 - y
        sx2 = sx1 + (x2 - x1)
        sy2 = sy1 + (y2 - y1)

        src = sprite_bgra[sy1:sy2, sx1:sx2]
        dst = canvas[y1:y2, x1:x2]

        a = (src[:, :, 3].astype(np.float32) / 255.0) * float(np.clip(alpha, 0.0, 1.0))
        a3 = np.dstack([a, a, a])

        blended = src[:, :, :3].astype(np.float32) * a3 + dst.astype(np.float32) * (1.0 - a3)
        canvas[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)

    def render_master_video(self, limit_seconds: Optional[float] = None) -> str:
        """Renders the master documentary video with full audio sync."""
        self.output_mp4_path.parent.mkdir(parents=True, exist_ok=True)
        temp_video = self.output_mp4_path.parent / "temp_master_track.mp4"

        render_duration = self.duration_sec if limit_seconds is None else min(limit_seconds, self.duration_sec)
        total_frames = int(round(render_duration * self.fps))

        print("==================================================")
        print("MASTER DYNAMIC STAGE ALTERNATION RENDERER (V6)")
        print(f"Resolution: {self.width}x{self.height} @ {self.fps} FPS")
        print(f"Duration:   {render_duration:.2f}s ({total_frames} frames)")
        print(f"Output:     {self.output_mp4_path}")
        print("==================================================")

        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}", "-pix_fmt", "bgr24", "-r", str(self.fps),
            "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", str(temp_video)
        ]

        pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        t0 = time.time()

        for f_idx in range(total_frames):
            t = f_idx / float(self.fps)
            frame = self.render_frame(t)
            pipe.stdin.write(frame.tobytes())

            if (f_idx + 1) % 90 == 0 or (f_idx + 1) == total_frames:
                elapsed = time.time() - t0
                fps_rate = (f_idx + 1) / max(0.001, elapsed)
                pct = (f_idx + 1) / float(total_frames) * 100.0
                print(f"   [FRAME {f_idx + 1}/{total_frames}] {pct:.1f}% ({fps_rate:.1f} FPS, Time: {t:.2f}s)")

        pipe.stdin.close()
        pipe.wait()

        # Audio multiplexing
        print("[AUDIO] Muxing synchronized master audio track...")
        mux_cmd = [
            "ffmpeg", "-y",
            "-i", str(temp_video),
            "-i", self.audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(render_duration),
            "-shortest",
            "-movflags", "+faststart",
            str(self.output_mp4_path),
        ]
        subprocess.run(mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        if temp_video.exists():
            try:
                temp_video.unlink()
            except Exception:
                pass

        total_time = time.time() - t0
        print(f"[DONE] Master Video V6 Rendered successfully in {total_time:.1f}s!")
        print(f"       Saved to: {self.output_mp4_path}")
        return str(self.output_mp4_path)

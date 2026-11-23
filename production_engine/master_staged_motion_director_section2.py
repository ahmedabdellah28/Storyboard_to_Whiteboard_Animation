"""Master Staged Motion Director Engine for Section 02 (Bucket Orchid / Coryanthes).

Directorial features based on user V6 requirements:
1. Pure white studio background (#FFFFFF).
2. Selective elevation physics: Grounded elements are flat on canvas; aerial elements (flying bees, floating Saw bubble, lightbulb) have 3D flight drop shadows.
3. Left/Right stage alternation:
   - Scenes strictly alternate elements on the RIGHT (text on LEFT) and elements on the LEFT (text on RIGHT).
4. Audio synchronization:
   - Text appears strictly AFTER / WITH the spoken voice based on section_02_word_by_word.srt.
5. Diverse positions from all sides (Right, Left, Top-center, Top-left, Bottom-left).
6. Varied typography animations: authentic RTL handwriting (`write_rtl`) with glowing pen cursor dot, impact slams (`slam_bounce`), overshoot pops (`pop_overshoot`), and slide-ins.
7. Fixed camera with rock-solid stationary element holds.
"""

import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

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
    "r1_02_bee_flying_alert",
    "sub_r1_06_saw_mask_bubble",
    "r2_02_bee_attracted_flying",
    "sub_r2_02_bee_flying",
    "sub_r2_03_scent_waves",
    "r3_06_bee_exhausted_covered_pollen",
    "sub_r3_06_exhausted_bee",
    "r4_01_bee_flying_second_bucket",
    "sub_r4_05_lightbulb_glow",
}

# ==============================================================================
# 2. Rich Color Palettes
# ==============================================================================

POPUP_THEMES = {
    "emerald": {
        "card_bg": (16, 105, 75, 255),
        "border": (52, 211, 153, 255),
        "badge_bg": (52, 211, 153, 255),
        "badge_text": (6, 78, 59, 255),
        "title_text": (255, 255, 255, 255),
        "accent": (52, 211, 153, 255),
    },
    "crimson": {
        "card_bg": (153, 27, 27, 255),
        "border": (248, 113, 113, 255),
        "badge_bg": (248, 113, 113, 255),
        "badge_text": (127, 29, 29, 255),
        "title_text": (255, 255, 255, 255),
        "accent": (248, 113, 113, 255),
    },
    "amber": {
        "card_bg": (180, 83, 9, 255),
        "border": (251, 191, 36, 255),
        "badge_bg": (251, 191, 36, 255),
        "badge_text": (120, 53, 15, 255),
        "title_text": (255, 255, 255, 255),
        "accent": (251, 191, 36, 255),
    },
    "cyan": {
        "card_bg": (14, 116, 144, 255),
        "border": (34, 211, 238, 255),
        "badge_bg": (34, 211, 238, 255),
        "badge_text": (22, 78, 99, 255),
        "title_text": (255, 255, 255, 255),
        "accent": (34, 211, 238, 255),
    },
    "purple": {
        "card_bg": (109, 40, 217, 255),
        "border": (192, 132, 252, 255),
        "badge_bg": (192, 132, 252, 255),
        "badge_text": (59, 7, 100, 255),
        "title_text": (255, 255, 255, 255),
        "accent": (192, 132, 252, 255),
    },
}

# ==============================================================================
# 3. Typography & Card Drawing Helpers
# ==============================================================================

def get_arabic_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    font_candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\seguiemj.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        DEFAULT_CAIRO_FONT,
    ]
    for p in font_candidates:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def reshape_arabic(text: str) -> str:
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text

def render_arabic_text_as_rgba(text: str, font_size: int, text_color: Tuple[int, int, int, int], bold: bool = True) -> np.ndarray:
    display_text = reshape_arabic(text)
    font = get_arabic_font(font_size, bold=bold)
    
    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), display_text, font=font)
    tw = max(1, bbox[2] - bbox[0] + 16)
    th = max(1, bbox[3] - bbox[1] + 16)
    
    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((8 - bbox[0], 8 - bbox[1]), display_text, font=font, fill=text_color)
    return np.array(img)

def create_staged_popup_card(
    title: str,
    badge: Optional[str] = None,
    theme_name: str = "cyan",
    style_type: str = "card_badge",
    width: Optional[int] = None
) -> np.ndarray:
    theme = POPUP_THEMES.get(theme_name, POPUP_THEMES["cyan"])
    card_bg = theme["card_bg"]
    border_col = theme["border"]
    badge_bg = theme["badge_bg"]
    badge_text_col = theme["badge_text"]
    title_text_col = theme["title_text"]

    title_rgba = render_arabic_text_as_rgba(title, font_size=42, text_color=title_text_col, bold=True)
    th, tw = title_rgba.shape[:2]

    badge_rgba = None
    bw, bh = 0, 0
    if badge:
        badge_rgba = render_arabic_text_as_rgba(badge, font_size=24, text_color=badge_text_col, bold=True)
        bh, bw = badge_rgba.shape[:2]

    pad_h = 32
    pad_v = 22
    content_w = max(tw, bw + 20)
    card_w = max(width or 0, content_w + pad_h * 2)

    if badge:
        card_h = bh + 14 + th + pad_v * 2
    else:
        card_h = th + pad_v * 2

    canvas = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    radius = 18 if style_type != "top_banner" else 8
    draw.rounded_rectangle([(0, 0), (card_w - 1, card_h - 1)], radius=radius, fill=card_bg, outline=border_col, width=3)

    canvas_arr = np.array(canvas)

    curr_y = pad_v
    if badge and badge_rgba is not None:
        pill_w = bw + 28
        pill_h = bh + 8
        pill_x = (card_w - pill_w) // 2
        pill_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        pill_draw = ImageDraw.Draw(pill_img)
        pill_draw.rounded_rectangle([(pill_x, curr_y), (pill_x + pill_w, curr_y + pill_h)], radius=12, fill=badge_bg)
        pill_arr = np.array(pill_img)
        
        alpha_pill = pill_arr[:, :, 3] / 255.0
        for c in range(3):
            canvas_arr[:, :, c] = (alpha_pill * pill_arr[:, :, c] + (1 - alpha_pill) * canvas_arr[:, :, c]).astype(np.uint8)
        canvas_arr[:, :, 3] = np.maximum(canvas_arr[:, :, 3], pill_arr[:, :, 3])

        bx = pill_x + 14
        by = curr_y + 4
        sub_alpha = badge_rgba[:, :, 3] / 255.0
        for c in range(3):
            canvas_arr[by:by+bh, bx:bx+bw, c] = (sub_alpha * badge_rgba[:, :, c] + (1 - sub_alpha) * canvas_arr[by:by+bh, bx:bx+bw, c]).astype(np.uint8)
        canvas_arr[by:by+bh, bx:bx+bw, 3] = np.maximum(canvas_arr[by:by+bh, bx:bx+bw, 3], badge_rgba[:, :, 3])

        curr_y += pill_h + 10

    tx = (card_w - tw) // 2
    ty = curr_y
    t_alpha = title_rgba[:, :, 3] / 255.0
    for c in range(3):
        canvas_arr[ty:ty+th, tx:tx+tw, c] = (t_alpha * title_rgba[:, :, c] + (1 - t_alpha) * canvas_arr[ty:ty+th, tx:tx+tw, c]).astype(np.uint8)
    canvas_arr[ty:ty+th, tx:tx+tw, 3] = np.maximum(canvas_arr[ty:ty+th, tx:tx+tw, 3], title_rgba[:, :, 3])

    bgra = cv2.cvtColor(canvas_arr, cv2.COLOR_RGBA2BGRA)
    return OpenCutVisualFX.apply_drop_shadow(bgra, offset=(0, 10), blur_radius=18, opacity=0.35)

def apply_selective_elevation_shadow(asset_key: str, asset_rgba: np.ndarray) -> np.ndarray:
    is_elevated = asset_key in ELEVATED_ASSETS
    arr = asset_rgba.copy()

    if is_elevated:
        offset = (10, 22)
        blur = 24
        opacity = 0.38
    else:
        offset = (1, 3)
        blur = 4
        opacity = 0.10

    bgra = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
    bgra[:, :, 3] = arr[:, :, 3]
    return OpenCutVisualFX.apply_drop_shadow(bgra, offset=offset, blur_radius=blur, opacity=opacity)

# ==============================================================================
# 4. Cinematic Scenes Architecture for Section 02
# ==============================================================================

SCENES = [
    # Scene 1: Innocent Start -> The Harsh Reality
    # Elements on RIGHT, Text on LEFT
    # Spoken audio: "قاسي" at 2.12s, "أوركيد الدلو" at 3.40s
    {
        "id": "scene_01",
        "start": 0.0,
        "end": 4.26,
        "elements": [
            {
                "asset_key": "r1_01_stickman_thinking_bee",
                "start": 0.0,
                "end": 4.26,
                "pos": (1320, 540),
                "target_size": 580,
            },
            {
                "asset_key": "r1_02_bee_flying_alert",
                "start": 1.00,
                "end": 4.26,
                "pos": (950, 480),
                "target_size": 400,
            }
        ],
        "words": [
            {
                "start": 2.15,
                "end": 3.35,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "صدمة",
                "word": "استغلال قاسي!",
                "theme": "amber",
                "pos": (540, 540),
            },
            {
                "start": 3.40,
                "end": 4.26,
                "style_type": "card_badge",
                "anim_type": "pop_overshoot",
                "badge": "الهدف القادم",
                "word": "أوركيد الدلو",
                "theme": "emerald",
                "pos": (540, 540),
            },
        ],
    },

    # Scene 2: The SAW Movie Trap
    # ALTERNATION: Elements on LEFT, Text on RIGHT
    # Spoken audio: "الخداع لحاله ما يكفي" at 4.60s, "فخ على طريقة أفلام سو" at 6.80s - 7.50s
    {
        "id": "scene_02",
        "start": 4.26,
        "end": 8.46,
        "elements": [
            {
                "asset_key": "r1_06_stickman_thinking_saw_jigsaw",
                "start": 4.26,
                "end": 8.46,
                "pos": (580, 540),
                "target_size": 620,
            },
        ],
        "words": [
            {
                "start": 4.60,
                "end": 6.50,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "تخطيط النبتة",
                "word": "الخداع لا يكفي!",
                "theme": "cyan",
                "pos": (1380, 460),
            },
            {
                "start": 6.80,
                "end": 8.46,
                "style_type": "card_badge",
                "anim_type": "slam_bounce",
                "badge": "أفلام SAW",
                "word": "فخ مرعب!",
                "theme": "crimson",
                "pos": (1380, 620),
            },
        ],
    },

    # Scene 3: The Bucket Shape & Intoxicating Scent
    # ALTERNATION: Elements on RIGHT, Text on LEFT
    # Spoken audio: "شكلها زي السطل" at 9.68s, "سائل ريحته تدوخ" at 11.54s
    {
        "id": "scene_03",
        "start": 8.46,
        "end": 12.52,
        "elements": [
            {
                "asset_key": "r2_03_bucket_emitting_scent_bee_tasting",
                "start": 8.46,
                "end": 12.52,
                "pos": (1300, 540),
                "target_size": 640,
            },
        ],
        "words": [
            {
                "start": 8.90,
                "end": 10.60,
                "style_type": "pointer_tag",
                "anim_type": "slide_in_left",
                "badge": "تشريح النبتة",
                "word": "شكلها سطل!",
                "theme": "amber",
                "pos": (540, 460),
            },
            {
                "start": 10.80,
                "end": 12.52,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "سائل مسكر",
                "word": "ريحة تدوخ النحل!",
                "theme": "purple",
                "pos": (540, 620),
            },
        ],
    },

    # Scene 4: The Fatal Slip & Fall into Sticky Liquid
    # ALTERNATION: Elements on LEFT, Text on RIGHT
    # Spoken audio: "تزلق وتطيح" at 14.02s - 14.60s, "موية لزجة" at 16.46s
    {
        "id": "scene_04",
        "start": 12.52,
        "end": 17.50,
        "elements": [
            {
                "asset_key": "r2_04_bee_slipping_rim",
                "start": 12.52,
                "end": 17.50,
                "pos": (500, 520),
                "target_size": 560,
            },
            {
                "asset_key": "r2_05_cutaway_bee_falling_liquid",
                "start": 14.80,
                "end": 17.50,
                "pos": (900, 520),
                "target_size": 560,
            },
        ],
        "words": [
            {
                "start": 13.90,
                "end": 15.60,
                "style_type": "card_badge",
                "anim_type": "pop_overshoot",
                "badge": "لحظة الغفلة",
                "word": "انزلاق وسقوط!",
                "theme": "amber",
                "pos": (1380, 480),
            },
            {
                "start": 15.80,
                "end": 17.50,
                "style_type": "card_badge",
                "anim_type": "slam_bounce",
                "badge": "الهاوية",
                "word": "سائل لزج!",
                "theme": "cyan",
                "pos": (1380, 640),
            },
        ],
    },

    # Scene 5: Drowning Struggle & Impossible Smooth Walls
    # ALTERNATION: Elements on RIGHT, Text on LEFT
    # Spoken audio: "تغرق وتصارع" at 17.34s, "جدران السطل ملساء جداً" at 19.66s
    {
        "id": "scene_05",
        "start": 17.50,
        "end": 23.10,
        "elements": [
            {
                "asset_key": "r2_06_cutaway_bee_struggling_liquid",
                "start": 17.50,
                "end": 23.10,
                "pos": (1340, 540),
                "target_size": 580,
            },
            {
                "asset_key": "r3_02_slippery_wall_sliding_2",
                "start": 19.20,
                "end": 23.10,
                "pos": (880, 540),
                "target_size": 540,
            },
        ],
        "words": [
            {
                "start": 17.60,
                "end": 19.80,
                "style_type": "card_badge",
                "anim_type": "shake_bounce",
                "badge": "صراع البقاء",
                "word": "تغرق وتصارع!",
                "theme": "crimson",
                "pos": (540, 460),
            },
            {
                "start": 20.00,
                "end": 23.10,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "مستحيل الهروب",
                "word": "جدران ملساء!",
                "theme": "amber",
                "pos": (540, 620),
            },
        ],
    },

    # Scene 6: The Only Exit - The Narrow Tunnel
    # ALTERNATION: Elements on LEFT, Text on RIGHT
    # Spoken audio: "مخرج واحد بس" at 22.82s, "نفق ضيق جداً" at 23.74s
    {
        "id": "scene_06",
        "start": 23.10,
        "end": 26.80,
        "elements": [
            {
                "asset_key": "r3_03_bee_trapped_looking_up",
                "start": 23.10,
                "end": 26.80,
                "pos": (520, 540),
                "target_size": 560,
            },
            {
                "asset_key": "r3_04_bee_entering_narrow_tunnel",
                "start": 24.50,
                "end": 26.80,
                "pos": (920, 540),
                "target_size": 540,
            },
        ],
        "words": [
            {
                "start": 23.30,
                "end": 24.80,
                "style_type": "card_badge",
                "anim_type": "pop_overshoot",
                "badge": "بصيص أمل",
                "word": "مخرج واحد بس!",
                "theme": "emerald",
                "pos": (1380, 480),
            },
            {
                "start": 24.90,
                "end": 26.80,
                "style_type": "card_badge",
                "anim_type": "slide_in_right",
                "badge": "الممر الإجباري",
                "word": "نفق ضيق جداً",
                "theme": "cyan",
                "pos": (1380, 640),
            },
        ],
    },

    # Scene 7: Squeezed in Tunnel & Glued with Heavy Pollen
    # ALTERNATION: Elements on RIGHT, Text on LEFT
    # Spoken audio: "تحشر نفسها" at 26.48s, "سائل صمغي" at 32.06s, "كيس لقاح ثقيل" at 34.44s
    {
        "id": "scene_07",
        "start": 26.80,
        "end": 35.00,
        "elements": [
            {
                "asset_key": "r3_05_bee_tunnel_pollen_glued",
                "start": 26.80,
                "end": 35.00,
                "pos": (1300, 540),
                "target_size": 660,
            },
        ],
        "words": [
            {
                "start": 27.00,
                "end": 30.00,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "معاناة الزحف",
                "word": "حشر وزحف!",
                "theme": "amber",
                "pos": (540, 440),
            },
            {
                "start": 31.80,
                "end": 33.80,
                "style_type": "card_badge",
                "anim_type": "pop_overshoot",
                "badge": "تثبيت النبتة",
                "word": "سائل صمغي",
                "theme": "purple",
                "pos": (540, 580),
            },
            {
                "start": 34.00,
                "end": 35.00,
                "style_type": "card_badge",
                "anim_type": "slam_bounce",
                "badge": "الحمولة الإجبارية",
                "word": "كيس ثقيل!",
                "theme": "amber",
                "pos": (540, 720),
            },
        ],
    },

    # Scene 8: The Exhausted Survivor & Falling into Second Bucket!
    # ALTERNATION: Elements on LEFT, Text on RIGHT
    # Spoken audio: "معركة" at 36.96s, "تتوب ... سطل ثاني" at 38.04s - 40.50s
    {
        "id": "scene_08",
        "start": 35.00,
        "end": 40.80,
        "elements": [
            {
                "asset_key": "r3_06_bee_exhausted_covered_pollen",
                "start": 35.00,
                "end": 40.80,
                "pos": (520, 520),
                "target_size": 540,
            },
            {
                "asset_key": "r4_01_bee_flying_second_bucket",
                "start": 37.80,
                "end": 40.80,
                "pos": (940, 540),
                "target_size": 560,
            },
        ],
        "words": [
            {
                "start": 36.60,
                "end": 38.20,
                "style_type": "card_badge",
                "anim_type": "pop_overshoot",
                "badge": "إنهاك تام",
                "word": "طالعة من معركة!",
                "theme": "crimson",
                "pos": (1380, 480),
            },
            {
                "start": 38.40,
                "end": 40.80,
                "style_type": "card_badge",
                "anim_type": "write_rtl",
                "badge": "بدل ما تتوب",
                "word": "تطيح في سطل ثاني!",
                "theme": "cyan",
                "pos": (1380, 640),
            },
        ],
    },

    # Scene 9: The Grand Moral - The Plant Forces You!
    # ALTERNATION: Elements on RIGHT, Text on LEFT
    # Spoken audio: "النبتة ما تطلب المساعدة" at 41.50s, "تجبرك عليها" at 42.70s
    {
        "id": "scene_09",
        "start": 40.80,
        "end": 43.76,
        "elements": [
            {
                "asset_key": "r4_05_stickman_narrator_lightbulb",
                "start": 40.80,
                "end": 43.76,
                "pos": (1300, 540),
                "target_size": 640,
            },
        ],
        "words": [
            {
                "start": 41.20,
                "end": 42.40,
                "style_type": "pointer_tag",
                "anim_type": "slide_in_left",
                "badge": "قانون الطبيعة",
                "word": "لا تطلب المساعدة",
                "theme": "emerald",
                "pos": (540, 480),
            },
            {
                "start": 42.50,
                "end": 43.76,
                "style_type": "card_badge",
                "anim_type": "slam_bounce",
                "badge": "حقيقة مؤكدة",
                "word": "تجبرك عليها!",
                "theme": "crimson",
                "pos": (540, 640),
            },
        ],
    },
]

# ==============================================================================
# 5. Master Director Engine Class
# ==============================================================================

class MasterStagedMotionDirectorSection2:
    def __init__(self, assets_dir: Path):
        self.assets_dir = Path(assets_dir)
        self.meta_path = self.assets_dir / "metadata.json"
        with open(self.meta_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        self.loaded_assets: Dict[str, np.ndarray] = {}
        self._load_all_assets()
        self.total_duration = 43.76
        self.total_frames = int(self.total_duration * FPS)

    def _load_all_assets(self):
        all_entries = {**self.metadata.get("primary_assets", {}), **self.metadata.get("sub_elements", {})}
        for key, info in all_entries.items():
            fn = info["filename"]
            p = self.assets_dir / fn
            if p.exists():
                img = Image.open(p).convert("RGBA")
                self.loaded_assets[key] = np.array(img)

    def render_element(self, asset_key: str, t: float, start_t: float, target_pos: Tuple[int, int], target_size: int) -> Tuple[np.ndarray, Tuple[int, int]]:
        raw = self.loaded_assets.get(asset_key)
        if raw is None:
            return np.zeros((10, 10, 4), dtype=np.uint8), (0, 0)

        elapsed = max(0.0, t - start_t)
        intro_dur = 0.40

        if elapsed < intro_dur:
            p = elapsed / intro_dur
            s = ease(p, "out_back")
            scale_factor = 0.3 + 0.7 * s
            alpha_mult = min(1.0, elapsed / 0.15)
        else:
            scale_factor = 1.0
            alpha_mult = 1.0

        h, w = raw.shape[:2]
        base_scale = target_size / max(h, w)
        final_scale = base_scale * scale_factor

        new_w = max(4, int(w * final_scale))
        new_h = max(4, int(h * final_scale))

        scaled = cv2.resize(raw, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        if alpha_mult < 1.0:
            scaled[:, :, 3] = (scaled[:, :, 3].astype(float) * alpha_mult).astype(np.uint8)

        with_shadow = apply_selective_elevation_shadow(asset_key, scaled)

        sh, sw = with_shadow.shape[:2]
        center_x, center_y = target_pos
        top_left_x = center_x - sw // 2
        top_left_y = center_y - sh // 2

        return with_shadow, (top_left_x, top_left_y)

    def render_word_card(self, word_cfg: Dict[str, Any], t: float) -> Optional[Tuple[np.ndarray, Tuple[int, int]]]:
        st = word_cfg["start"]
        en = word_cfg["end"]
        if t < st or t > en:
            return None

        badge = word_cfg.get("badge")
        word = word_cfg["word"]
        theme = word_cfg.get("theme", "cyan")
        style = word_cfg.get("style_type", "card_badge")
        anim = word_cfg.get("anim_type", "pop_overshoot")
        center_pos = word_cfg["pos"]

        card_raw = create_staged_popup_card(title=word, badge=badge, theme_name=theme, style_type=style)
        elapsed = t - st
        intro_dur = 0.35

        if anim == "write_rtl":
            write_dur = 0.55
            progress = min(1.0, elapsed / write_dur)
            p = ease(progress, "out_cubic")
            
            card_arr = card_raw.copy()
            ch, cw = card_arr.shape[:2]
            
            cutoff = int(cw * (1.0 - p))
            if cutoff > 0:
                card_arr[:, :cutoff, 3] = 0
            
            if 0 < cutoff < cw:
                nib_x = cutoff
                nib_rad = 5
                y_min = max(0, ch // 2 - 25)
                y_max = min(ch, ch // 2 + 25)
                cv2.circle(card_arr, (nib_x, ch // 2), nib_rad, (255, 255, 255, 255), -1)
                cv2.circle(card_arr, (nib_x, ch // 2), nib_rad + 3, (52, 211, 153, 180), 2)
            
            scale = 1.0
            offset_y = 0
            alpha = min(1.0, elapsed / 0.12)
            res = card_arr

        elif anim == "slam_bounce":
            intro_dur = 0.28
            if elapsed < intro_dur:
                p = elapsed / intro_dur
                s = ease(p, "out_bounce")
                scale = 1.4 - 0.4 * s
                offset_y = int(-40 * (1.0 - s))
                alpha = min(1.0, elapsed / 0.08)
            else:
                scale = 1.0
                offset_y = 0
                alpha = 1.0
            res = card_raw

        elif anim == "shake_bounce":
            intro_dur = 0.35
            if elapsed < intro_dur:
                p = elapsed / intro_dur
                s = ease(p, "out_back")
                scale = 0.4 + 0.6 * s
                offset_y = int(math.sin(elapsed * 35.0) * 8 * (1.0 - p))
                alpha = min(1.0, elapsed / 0.10)
            else:
                scale = 1.0
                offset_y = 0
                alpha = 1.0
            res = card_raw

        elif anim == "slide_in_left":
            if elapsed < intro_dur:
                p = ease(elapsed / intro_dur, "out_cubic")
                scale = 1.0
                offset_y = 0
                offset_x = int(-120 * (1.0 - p))
                center_pos = (center_pos[0] + offset_x, center_pos[1])
                alpha = min(1.0, elapsed / 0.10)
            else:
                scale = 1.0
                offset_y = 0
                alpha = 1.0
            res = card_raw

        elif anim == "slide_in_right":
            if elapsed < intro_dur:
                p = ease(elapsed / intro_dur, "out_cubic")
                scale = 1.0
                offset_y = 0
                offset_x = int(120 * (1.0 - p))
                center_pos = (center_pos[0] + offset_x, center_pos[1])
                alpha = min(1.0, elapsed / 0.10)
            else:
                scale = 1.0
                offset_y = 0
                alpha = 1.0
            res = card_raw

        else: # pop_overshoot
            if elapsed < intro_dur:
                p = elapsed / intro_dur
                s = ease(p, "out_back")
                scale = 0.3 + 0.7 * s
                offset_y = int(25 * (1.0 - s))
                alpha = min(1.0, elapsed / 0.12)
            else:
                scale = 1.0
                offset_y = 0
                alpha = 1.0
            res = card_raw

        if scale != 1.0:
            ch, cw = res.shape[:2]
            nw = max(4, int(cw * scale))
            nh = max(4, int(ch * scale))
            res = cv2.resize(res, (nw, nh), interpolation=cv2.INTER_LANCZOS4)

        if alpha < 1.0:
            res[:, :, 3] = (res[:, :, 3].astype(float) * alpha).astype(np.uint8)

        rh, rw = res.shape[:2]
        cx, cy = center_pos
        top_x = cx - rw // 2
        top_y = cy - rh // 2 + offset_y

        return res, (top_x, top_y)

    def render_frame(self, t: float) -> np.ndarray:
        # Pure White Canvas
        frame = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)

        current_scene = None
        for s in SCENES:
            if s["start"] <= t < s["end"]:
                current_scene = s
                break
        if current_scene is None and t >= SCENES[-1]["end"]:
            current_scene = SCENES[-1]

        if not current_scene:
            return frame

        # Render Scene Elements
        for elem in current_scene.get("elements", []):
            if elem["start"] <= t <= elem["end"]:
                layer_bgra, (lx, ly) = self.render_element(
                    elem["asset_key"],
                    t,
                    elem["start"],
                    elem["pos"],
                    elem["target_size"]
                )
                self._alpha_blend(frame, layer_bgra, lx, ly)

        # Render Scene Words / Cards
        for w_cfg in current_scene.get("words", []):
            card_res = self.render_word_card(w_cfg, t)
            if card_res is not None:
                card_bgra, (cx, cy) = card_res
                self._alpha_blend(frame, card_bgra, cx, cy)

        return frame

    def _alpha_blend(self, base_bgr: np.ndarray, overlay_bgra: np.ndarray, x: int, y: int):
        oh, ow = overlay_bgra.shape[:2]
        bh, bw = base_bgr.shape[:2]

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(bw, x + ow)
        y2 = min(bh, y + oh)

        if x1 >= x2 or y1 >= y2:
            return

        ox1 = x1 - x
        oy1 = y1 - y
        ox2 = ox1 + (x2 - x1)
        oy2 = oy1 + (y2 - y1)

        src_roi = overlay_bgra[oy1:oy2, ox1:ox2]
        alpha = (src_roi[:, :, 3].astype(float) / 255.0)[:, :, np.newaxis]

        dst_roi = base_bgr[y1:y2, x1:x2].astype(float)
        src_bgr = src_roi[:, :, :3].astype(float)

        blended = alpha * src_bgr + (1.0 - alpha) * dst_roi
        base_bgr[y1:y2, x1:x2] = blended.astype(np.uint8)

    def render_video(self, output_mp4: str, audio_wav: str):
        out_path = Path(output_mp4)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_video = str(out_path.with_name(f"temp_{out_path.name}"))

        print("=" * 70)
        print("🎬 RENDERING SECTION 02 MASTER STAGED MOTION GRAPHICS VIDEO (V6)")
        print("=" * 70)
        print(f"• Output MP4   : {output_mp4}")
        print(f"• Audio Track  : {audio_wav}")
        print(f"• Resolution   : {WIDTH}x{HEIGHT} @ {FPS}fps")
        print(f"• Total Frames : {self.total_frames} ({self.total_duration:.2f}s)")
        print(f"• Scenes Count : {len(SCENES)}")
        print("=" * 70)

        # Pipe frames directly to FFmpeg
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{WIDTH}x{HEIGHT}",
            "-pix_fmt", "bgr24",
            "-r", str(FPS),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            temp_video
        ]

        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

        t_start = time.time()
        for f_idx in range(self.total_frames):
            cur_t = f_idx / float(FPS)
            frame = self.render_frame(cur_t)
            proc.stdin.write(frame.tobytes())

            if (f_idx + 1) % 150 == 0 or (f_idx + 1) == self.total_frames:
                pct = (f_idx + 1) / self.total_frames * 100.0
                elapsed = time.time() - t_start
                fps_render = (f_idx + 1) / elapsed
                print(f"  Frame {f_idx+1}/{self.total_frames} ({pct:.1f}%) - {fps_render:.1f} fps", flush=True)

        proc.stdin.close()
        proc.wait()

        print("\n🔊 Muxing Audio Track...")
        mux_cmd = [
            "ffmpeg", "-y",
            "-i", temp_video,
            "-i", audio_wav,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_mp4
        ]
        res = subprocess.run(mux_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print("❌ Mux Error:", res.stderr)
            raise RuntimeError("Audio muxing failed.")

        if os.path.exists(temp_video):
            os.remove(temp_video)

        total_render_time = time.time() - t_start
        print("=" * 70)
        print(f"🎉 RENDER COMPLETE in {total_render_time:.1f}s!")
        print(f"• Master Video File: {output_mp4}")
        print("=" * 70)

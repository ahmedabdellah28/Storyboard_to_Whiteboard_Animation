"""EffectCraft Professional Motion Graphics Engine.
Translates director manifests, assets, and voiceover into professional,
hardware-accelerated EffectCraft compositions (.ecproj) and renders 1080p masters.

Features:
- Full implementation of Style 1 Grounded Typography Lifecycle:
  1. Traveling Dot (0.00s -> 0.28s): Arched Bezier flight from visual element to card center.
  2. Card Bloom (0.28s -> 0.44s): Snappy out_back expansion with drop shadow and border outline.
  3. Rapid RTL Handwriting (0.44s -> 0.70s): Linear Wipe reveal with glowing Pen Nib cursor.
  4. Grounded Stability (> 0.70s): 100% stable until end-of-word graceful fadeout.
- Native subpixel transformations and bezier keyframes.
- Studio Whiteboard standards: Ground Line (Y = 840), Pure White (#FFFFFF).
- Headless ultra-fast rendering via effectcraft-cli (Rust engine).
"""

import os
import sys
import time
import json
import math
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
CLI_CANDIDATES = [
    ROOT_DIR / "craftApp" / "effectcraft" / "target" / "release" / "effectcraft-cli.exe",
    ROOT_DIR / "effectcraft" / "target" / "release" / "effectcraft-cli.exe",
]
CLI_PATH = next((p for p in CLI_CANDIDATES if p.exists()), CLI_CANDIDATES[0])

# Reconfigure console encoding for safe printing
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

# Import font and visual FX configuration
try:
    from production_engine.opencut_fx import DEFAULT_CAIRO_FONT, OpenCutVisualFX
except Exception:
    DEFAULT_CAIRO_FONT = ROOT_DIR / "assets" / "fonts" / "Cairo-Bold-Presentation.ttf"
    OpenCutVisualFX = None

import cv2
import numpy as np
import arabic_reshaper
from bidi.algorithm import get_display
from core_engine.effectcraft_motion_studio import CARD_THEMES
from core_engine.director_effects_suite import DirectorEffectsSuite

POPUP_THEMES = {
    "emerald": {
        "bg": [0.063, 0.412, 0.294, 1.0],      # #10694B
        "border": [0.204, 0.827, 0.600, 1.0],  # #34D399
        "text": [1.0, 1.0, 1.0, 1.0],
    },
    "crimson": {
        "bg": [0.600, 0.106, 0.106, 1.0],      # #991B1B
        "border": [0.973, 0.443, 0.443, 1.0],  # #F87171
        "text": [1.0, 1.0, 1.0, 1.0],
    },
    "amber": {
        "bg": [0.706, 0.325, 0.035, 1.0],      # #B45309
        "border": [0.984, 0.749, 0.141, 1.0],  # #FBBF24
        "text": [1.0, 1.0, 1.0, 1.0],
    },
    "royal": {
        "bg": [0.059, 0.298, 0.361, 1.0],      # #0F4C5C
        "border": [0.176, 0.831, 0.749, 1.0],  # #2DD4BF
        "text": [1.0, 1.0, 1.0, 1.0],
    },
    "teal": {
        "bg": [0.059, 0.298, 0.361, 1.0],
        "border": [0.176, 0.831, 0.749, 1.0],
        "text": [1.0, 1.0, 1.0, 1.0],
    },
    "cyan": {
        "bg": [0.059, 0.298, 0.361, 1.0],
        "border": [0.176, 0.831, 0.749, 1.0],
        "text": [1.0, 1.0, 1.0, 1.0],
    }
}

COLOR_PALETTE = {
    "red": (0.88, 0.12, 0.18),
    "crimson": (0.88, 0.12, 0.18),
    "cyan": (0.133, 0.827, 0.933),
    "blue": (0.133, 0.827, 0.933),
    "gold": (0.984, 0.749, 0.141),
    "amber": (0.984, 0.749, 0.141),
    "emerald": (0.204, 0.827, 0.600),
    "green": (0.204, 0.827, 0.600),
    "purple": (0.68, 0.35, 0.95),
    "white": (1.0, 1.0, 1.0),
}

def measure_arabic_text(text: str, font_size: int = 64) -> Tuple[int, int]:
    """Measures precise bounding box for Arabic text using Cairo font."""
    try:
        font_path = str(DEFAULT_CAIRO_FONT)
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
        dummy = Image.new("RGBA", (10, 10))
        d = ImageDraw.Draw(dummy)
        bbox = d.textbbox((0, 0), text, font=font)
        ww = max(40, bbox[2] - bbox[0])
        wh = max(30, bbox[3] - bbox[1])
        return ww, wh
    except Exception:
        # Fallback approximation
        return max(180, len(text) * 36), 64

class EffectCraftMotionEngine:
    def __init__(self, section_dir: Path, output_dir: Optional[Path] = None):
        self.section_dir = Path(section_dir)
        self.output_dir = Path(output_dir) if output_dir else ROOT_DIR / "exports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.manifest_path = self.section_dir / "manifest.json"

        # Mandatory Pre-Render Quality Assurance & Scene Retention Audit
        try:
            from core_engine.director_qa_auditor import DirectorQAAuditor
            audit_passed, audit_log = DirectorQAAuditor.audit_and_optimize_manifest(self.manifest_path, auto_fix=True)
            for msg in audit_log:
                print(msg)
        except Exception as e:
            print(f"[!] Warning during Director QA Audit: {e}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)
            
        self.fps = self.manifest.get("fps", 30)
        self.duration = float(self.manifest.get("total_duration", 30.0))
        self.width = self.manifest.get("resolution", [1920, 1080])[0]
        self.height = self.manifest.get("resolution", [1920, 1080])[1]
        self.section_id = self.manifest.get("section_id", self.section_dir.name)
        
        # Audio check
        self.audio_path = self.section_dir / "voice" / f"{self.section_id}.wav"
        if not self.audio_path.exists():
            wavs = [w for w in (self.section_dir / "voice").glob("*.wav") if "_sfx" not in w.name]
            if wavs:
                self.audio_path = wavs[0]

        # SFX Audio Mix integration
        sfx_enabled = self.manifest.get("enable_sfx", True)
        if sfx_enabled and self.audio_path.exists():
            try:
                from core_engine.sfx_director import SFXDirector
                sfx_mixed_wav = self.section_dir / "voice" / f"{self.section_id}_master_sfx.wav"
                sfx_dir = SFXDirector()
                sfx_dir.create_synchronized_audio(self.manifest, self.audio_path, sfx_mixed_wav)
                if sfx_mixed_wav.exists():
                    self.audio_path = sfx_mixed_wav
            except Exception as e:
                print(f"[!] Warning mixing SFX: {e}")

    def render_compact_card_components(
        self,
        word_text: str,
        theme_name: str = "emerald",
        font_size: int = 44,
        corner_radius: int = 20,
        border_width: int = 4,
        card_id: str = "1"
    ) -> Tuple[Path, Path, int, int, int]:
        """Renders separate aligned BG and Text PNG components for EffectCraft hardware wipe."""
        theme = CARD_THEMES.get(theme_name, CARD_THEMES["emerald"])
        has_arabic = any('\u0600' <= c <= '\u06FF' for c in word_text)
        if has_arabic:
            font_path = str(DEFAULT_CAIRO_FONT)
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()
            configuration = {
                'delete_harakat': False,
                'support_ligatures': True,
            }
            reshaper = arabic_reshaper.ArabicReshaper(configuration=configuration)
            reshaped_text = reshaper.reshape(word_text)
            display_text = get_display(reshaped_text)
        else:
            font = None
            for en_fp in [
                "C:/Windows/Fonts/segoeuib.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                str(DEFAULT_CAIRO_FONT),
            ]:
                if os.path.exists(en_fp):
                    font = ImageFont.truetype(en_fp, font_size)
                    break
            if font is None:
                font = ImageFont.load_default()
            display_text = word_text
        
        dummy = Image.new("RGBA", (10, 10))
        d = ImageDraw.Draw(dummy)
        bbox = d.textbbox((0, 0), display_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        
        pad_h = 48
        pad_v = 24
        card_w = max(tw + pad_h * 2, 240)
        card_h = max(th + pad_v * 2, 82)
        
        # 1. Base rounded rectangle card background (EMPTY - no text)
        base = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(base)
        draw.rounded_rectangle(
            [(2, 2), (card_w - 2, card_h - 2)],
            radius=corner_radius,
            fill=theme["bg_rgba"],
            outline=theme["border_rgba"],
            width=border_width
        )
        
        arr = cv2.cvtColor(np.array(base), cv2.COLOR_RGBA2BGRA)
        shadowed = OpenCutVisualFX.apply_drop_shadow(arr, offset=(4, 10), blur_radius=16, opacity=0.35)
        bg_img = Image.fromarray(cv2.cvtColor(shadowed, cv2.COLOR_BGRA2RGBA))
        sw, sh = bg_img.size
        
        # 2. Text layer on transparent canvas with identical (sw, sh) dimensions
        txt_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        draw_txt = ImageDraw.Draw(txt_img)
        cx = sw // 2
        cy = (sh // 2) - 2  # Optical micro-tune
        draw_txt.text((cx, cy), display_text, font=font, fill=(255, 255, 255, 255), anchor="mm")
        
        cache_dir = self.output_dir / "cache_assets"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        slug = f"word_{card_id}_{theme_name}"
        bg_path = cache_dir / f"card_bg_{slug}.png"
        txt_path = cache_dir / f"card_txt_{slug}.png"
        
        bg_img.save(bg_path)
        txt_img.save(txt_path)
        
        return bg_path, txt_path, tw, sw, sh

    def _build_style1_card_script(
        self,
        word_cfg: Dict[str, Any],
        idx: int,
        current_scene_element_pos: Optional[List[int]] = None,
        scene_start: float = 0.0
    ) -> List[str]:
        """Builds ExtendScript layers for Style 1 Grounded Typography Lifecycle with exact audio sync and linear wipe reveal."""
        word_text = word_cfg.get("word", word_cfg.get("text", ""))
        st = float(word_cfg.get("start", 0.0))  # EXACT Spoken timestamp from audio
        en = float(word_cfg.get("end", st + 2.5))
        target_pos = word_cfg.get("pos", [540, 540])
        theme_name = word_cfg.get("theme", "emerald")
        theme_border = POPUP_THEMES.get(theme_name, POPUP_THEMES["emerald"])["border"]
        
        # Origin for Traveling Dot
        if "from_pos" in word_cfg:
            from_pos = word_cfg["from_pos"]
        elif current_scene_element_pos:
            from_pos = current_scene_element_pos
        else:
            from_pos = [target_pos[0] + 380, target_pos[1]]
            
        bg_path, txt_path, tw, sw, sh = self.render_compact_card_components(word_text, theme_name=theme_name, card_id=str(idx))
        bg_posix = bg_path.resolve().as_posix()
        txt_posix = txt_path.resolve().as_posix()
        
        # Audio-synchronized timing:
        # Phase 1: Traveling dot launches right as the narrator speaks at st
        t_travel_start = st
        t_travel_end = st + 0.16
        
        # Phase 2: Card background blooms open on dot impact
        t_bloom_start = t_travel_end
        t_bloom_end = t_bloom_start + 0.12
        
        t_write_start = t_bloom_end
        phrase_dur = max(0.40, en - st)
        write_dur = min(0.28, max(0.20, phrase_dur * 0.20))
        t_write_end = min(t_write_start + write_dur, en - 0.15)
        if t_write_end <= t_write_start:
            t_write_end = t_write_start + 0.25
            
        t_fade_start = max(t_write_end + 0.30, en - 0.20)
        safe_word = word_text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")
        
        lines = [
            f"// --- Style 1 Rounded Word Card {idx}: '{safe_word}' ---",
            f"// Target: [{target_pos[0]}, {target_pos[1]}], Theme: {theme_name}, Spoken at: {st:.2f}s -> {en:.2f}s",
            "",
            f"// Phase 1: Traveling Dot ({t_travel_start:.2f}s -> {t_travel_end:.2f}s)",
            f"var dot_{idx} = comp.layers.addSolid([{theme_border[0]}, {theme_border[1]}, {theme_border[2]}], 'Dot_{idx}', 22, 22, 1);",
            f"dot_{idx}.inPoint = {t_travel_start:.2f};",
            f"dot_{idx}.outPoint = {t_travel_end:.2f};",
            f"dot_{idx}.property('Effects').addProperty('Gaussian Blur').property('Blurriness').setValue(3);",
            f"var dotPos_{idx} = dot_{idx}.property('Transform').property('Position');",
            f"var mx_{idx} = ({from_pos[0]} + {target_pos[0]}) / 2.0;",
            f"var my_{idx} = Math.min({from_pos[1]}, {target_pos[1]}) - 40.0;",
            f"dotPos_{idx}.setValueAtTime({t_travel_start:.2f}, [{from_pos[0]}, {from_pos[1]}, 0]);",
            f"dotPos_{idx}.setValueAtTime({(t_travel_start + t_travel_end) / 2.0:.2f}, [mx_{idx}, my_{idx}, 0]);",
            f"dotPos_{idx}.setValueAtTime({t_travel_end:.2f}, [{target_pos[0]}, {target_pos[1]}, 0]);",
            "",
            f"// Phase 2: Card Background Bloom ({t_bloom_start:.2f}s -> {en:.2f}s)",
            f"var bgIO_{idx} = new ImportOptions(new File('{bg_posix}'));",
            f"var bgItem_{idx} = app.project.importFile(bgIO_{idx});",
            f"var bgLayer_{idx} = comp.layers.add(bgItem_{idx});",
            f"bgLayer_{idx}.name = 'CardBG_{idx}_{safe_word}';",
            f"bgLayer_{idx}.inPoint = {t_bloom_start:.2f};",
            f"bgLayer_{idx}.outPoint = {en:.2f};",
            f"bgLayer_{idx}.property('Transform').property('Position').setValue([{target_pos[0]}, {target_pos[1]}, 0]);",
            f"var bgScale_{idx} = bgLayer_{idx}.property('Transform').property('Scale');",
            f"bgScale_{idx}.setValueAtTime({t_bloom_start:.2f}, [0, 0, 100]);",
            f"bgScale_{idx}.setValueAtTime({t_bloom_start + 0.10:.2f}, [110, 110, 100]);",
            f"bgScale_{idx}.setValueAtTime({t_bloom_end:.2f}, [100, 100, 100]);",
            f"var bgOp_{idx} = bgLayer_{idx}.property('Transform').property('Opacity');",
            f"bgOp_{idx}.setValueAtTime({t_bloom_start:.2f}, 100);",
            f"bgOp_{idx}.setValueAtTime({t_fade_start:.2f}, 100);",
            f"bgOp_{idx}.setValueAtTime({en:.2f}, 0);",
            "",
            f"// Phase 3: Synchronized RTL Handwriting Text Reveal ({t_write_start:.2f}s -> {en:.2f}s)",
            f"var txtIO_{idx} = new ImportOptions(new File('{txt_posix}'));",
            f"var txtItem_{idx} = app.project.importFile(txtIO_{idx});",
            f"var txtLayer_{idx} = comp.layers.add(txtItem_{idx});",
            f"txtLayer_{idx}.name = 'CardTXT_{idx}_{safe_word}';",
            f"txtLayer_{idx}.inPoint = {t_write_start:.2f};",
            f"txtLayer_{idx}.outPoint = {en:.2f};",
            f"txtLayer_{idx}.property('Transform').property('Position').setValue([{target_pos[0]}, {target_pos[1]}, 0]);",
            f"var wipe_{idx} = txtLayer_{idx}.property('Effects').addProperty('Linear Wipe');",
            f"wipe_{idx}.property('Wipe Angle').setValue(90.0);",
            f"var wipeProp_{idx} = wipe_{idx}.property('Transition Completion');",
            f"wipeProp_{idx}.setValueAtTime({t_write_start:.2f}, 100.0);",
            f"wipeProp_{idx}.setValueAtTime({t_write_end:.2f}, 0.0);",
            f"var txtOp_{idx} = txtLayer_{idx}.property('Transform').property('Opacity');",
            f"txtOp_{idx}.setValueAtTime({t_write_start:.2f}, 100);",
            f"txtOp_{idx}.setValueAtTime({t_fade_start:.2f}, 100);",
            f"txtOp_{idx}.setValueAtTime({en:.2f}, 0);",
            "",
            f"// Phase 4: Active Glowing Pen Nib Cursor during Handwriting ({t_write_start:.2f}s -> {t_write_end:.2f}s)",
            f"var nib_{idx} = comp.layers.addSolid([1.0, 1.0, 1.0], 'Nib_{idx}', 14, 14, 1);",
            f"nib_{idx}.inPoint = {t_write_start:.2f};",
            f"nib_{idx}.outPoint = {t_write_end:.2f};",
            f"nib_{idx}.property('Effects').addProperty('Gaussian Blur').property('Blurriness').setValue(2);",
            f"var nibPos_{idx} = nib_{idx}.property('Transform').property('Position');",
            f"var nibStartX_{idx} = {target_pos[0]} + {int(tw / 2)};",
            f"var nibEndX_{idx} = {target_pos[0]} - {int(tw / 2)};",
            f"nibPos_{idx}.setValueAtTime({t_write_start:.2f}, [nibStartX_{idx}, {target_pos[1]}, 0]);",
            f"nibPos_{idx}.setValueAtTime({t_write_end:.2f}, [nibEndX_{idx}, {target_pos[1]}, 0]);",
            ""
        ]
        return lines

    def generate_jsx_script(self) -> str:
        """Generates ExtendScript code to construct the EffectCraft project."""
        scenes = self.manifest.get("scenes", [])
        assets_dir = (self.section_dir / "assets").resolve().as_posix()
        audio_posix = self.audio_path.resolve().as_posix() if self.audio_path.exists() else None

        # Theme extraction and flexible background support
        theme_cfg = self.manifest.get("theme", {})
        if isinstance(theme_cfg, str):
            theme_name = theme_cfg
            theme_dict = {}
        else:
            theme_name = theme_cfg.get("name", "whiteboard")
            theme_dict = theme_cfg

        THEME_PRESETS = {
            "eye_comfort_paper": {
                "bg": [0.925, 0.910, 0.880],  # #EDE8E0 Soft Eye-Comfort Matte Canvas (anti-glare)
                "ground": [0.78, 0.74, 0.69],
                "name": "Eye_Comfort_Matte_Paper_BG"
            },
            "warm_paper": {
                "bg": [0.925, 0.910, 0.880],  # Calibrated to eye-comfort #EDE8E0
                "ground": [0.78, 0.74, 0.69],
                "name": "Eye_Comfort_Matte_Paper_BG"
            },
            "parchment": {
                "bg": [0.956, 0.933, 0.886],  # #F4EEDF
                "ground": [0.80, 0.76, 0.70],
                "name": "Parchment_Canvas_BG"
            },
            "slate_dark": {
                "bg": [0.08, 0.10, 0.14],      # #141A24
                "ground": [0.20, 0.24, 0.30],
                "name": "Slate_Dark_Canvas_BG"
            },
            "studio_neutral": {
                "bg": [0.93, 0.94, 0.96],      # #ECEFF4
                "ground": [0.80, 0.82, 0.85],
                "name": "Studio_Neutral_BG"
            },
            "whiteboard": {
                "bg": [0.925, 0.910, 0.880],  # Upgraded from blinding white to eye comfort
                "ground": [0.78, 0.74, 0.69],
                "name": "Eye_Comfort_Matte_Paper_BG"
            }
        }
        active_theme = THEME_PRESETS.get(theme_name, THEME_PRESETS["eye_comfort_paper"])
        bg_rgb = theme_dict.get("bg_color", active_theme["bg"])
        ground_rgb = theme_dict.get("ground_color", active_theme["ground"])
        bg_label = active_theme["name"]

        lines = [
            f"// EffectCraft Master Script for {self.section_id}",
            f"var comp = app.project.items.addComp('{self.section_id}_Master', {self.width}, {self.height}, 1, {self.duration}, {self.fps});",
            "",
            f"// 1. Studio Canvas Background ({theme_name})",
            f"var bg = comp.layers.addSolid([{bg_rgb[0]:.3f}, {bg_rgb[1]:.3f}, {bg_rgb[2]:.3f}], '{bg_label}', {self.width}, {self.height}, 1);",
            "",
        ]

        if audio_posix:
            lines.extend([
                "// 2. Audio Voiceover Track",
                f"var audioIO = new ImportOptions(new File('{audio_posix}'));",
                "var audioItem = app.project.importFile(audioIO);",
                "var audioLayer = comp.layers.add(audioItem);",
                f"audioLayer.inPoint = 0.0;",
                f"audioLayer.outPoint = {self.duration};",
                "",
            ])

        # Studio Ground Line (Responsive to Canvas Dimensions)
        ground_w = int(self.width * 0.92)
        ground_x = int(self.width / 2.0)
        default_ground_y = 840 if self.width >= self.height else int(self.height * 0.78)
        self.ground_y = self.manifest.get("ground_y", default_ground_y)
        lines.extend([
            f"// 3. Studio Ground Line (Y = {self.ground_y})",
            f"var groundLine = comp.layers.addSolid([{ground_rgb[0]:.3f}, {ground_rgb[1]:.3f}, {ground_rgb[2]:.3f}], 'Stage_Ground_Line', {ground_w}, 3, 1);",
            f"groundLine.property('Transform').property('Position').setValue([{ground_x}, {self.ground_y}]);",
            "",
        ])

        # Add Scene Visual Elements
        elem_idx = 1
        scene_lead_pos: Dict[str, List[int]] = {}

        for sc in scenes:
            sc_id = sc.get("id", "")
            sc_start = float(sc.get("start", 0.0))
            sc_end = float(sc.get("end", self.duration))
            
            elements = sc.get("elements", [])
            if elements:
                scene_lead_pos[sc_id] = elements[0].get("pos", [960, 540])
            
            for elem in elements:
                asset_key = elem.get("asset_key", "")
                pos = elem.get("pos", [960, 540])
                target_size = elem.get("target_size", 540)
                st = float(elem.get("start", sc_start))
                et = float(elem.get("end", sc_end))
                anim_type = elem.get("anim_type", "pop_overshoot")
                
                png_file = f"{assets_dir}/{asset_key}.png"
                # Determine if element should be grounded to stage line
                is_grounded = elem.get("grounded", False) or (pos[1] >= (self.ground_y - 40))
                
                max_dim = 450
                im_w = 400
                im_h = 400
                anchor_x = 200.0
                anchor_y = 200.0
                if Path(png_file).exists():
                    try:
                        im_meta = cv2.imread(png_file, cv2.IMREAD_UNCHANGED)
                        if im_meta is not None:
                            im_h, im_w = im_meta.shape[:2]
                            max_dim = max(im_h, im_w, 1)
                            if is_grounded and im_meta.shape[2] == 4:
                                alpha = im_meta[:, :, 3]
                                y_idx, x_idx = np.where(alpha > 15)
                                if len(y_idx) > 0:
                                    anchor_y = float(y_idx.max())
                                    anchor_x = float((x_idx.min() + x_idx.max()) / 2.0)
                                else:
                                    anchor_y = float(im_h)
                                    anchor_x = float(im_w / 2.0)
                            else:
                                anchor_x = float(im_w / 2.0)
                                anchor_y = float(im_h / 2.0)
                    except Exception:
                        pass
                
                actual_y = self.ground_y if is_grounded else pos[1]
                effective_pos = [pos[0], actual_y]

                lines.extend([
                    f"// Visual Element {elem_idx}: {asset_key}",
                    f"var fIO_{elem_idx} = new ImportOptions(new File('{png_file}'));",
                    f"var fItem_{elem_idx} = app.project.importFile(fIO_{elem_idx});",
                    f"var fLayer_{elem_idx} = comp.layers.add(fItem_{elem_idx});",
                    f"fLayer_{elem_idx}.name = '{asset_key}';",
                    f"fLayer_{elem_idx}.inPoint = {st:.2f};",
                    f"fLayer_{elem_idx}.outPoint = {et:.2f};",
                    f"fLayer_{elem_idx}.property('Transform').property('Anchor Point').setValue([{anchor_x:.1f}, {anchor_y:.1f}, 0]);",
                    f"fLayer_{elem_idx}.property('Transform').property('Position').setValue([{effective_pos[0]}, {effective_pos[1]}, 0]);",
                ])
                
                s_base = max(10, int((target_size / float(max_dim)) * 100))
                s_pop = int(s_base * 1.18)
                
                # Standardized Entrances (Integrated with 20 Motion Templates)
                entrance = elem.get("entrance", elem.get("anim_type", "pop_bounce"))
                if entrance in ["squash_drop", "gravity_drop"]:
                    lines.extend(DirectorEffectsSuite.apply_squash_and_stretch_drop(f"fLayer_{elem_idx}", st, effective_pos, s_base))
                elif entrance in ["whip_motion", "whip_pan", "whip_in"]:
                    from_right = effective_pos[0] >= (self.width / 2.0)
                    lines.extend(DirectorEffectsSuite.apply_whip_motion_entrance(f"fLayer_{elem_idx}", st, effective_pos, s_base, duration=float(elem.get("duration", 0.28)), from_right=from_right))
                elif entrance in ["rotation_spin", "spin_reveal", "spin_in"]:
                    lines.extend(DirectorEffectsSuite.apply_rotation_spin_reveal(f"fLayer_{elem_idx}", st, effective_pos, s_base, duration=float(elem.get("duration", 0.42))))
                elif entrance in ["elastic_overshoot", "spring_overshoot"]:
                    lines.extend(DirectorEffectsSuite.apply_elastic_overshoot(f"fLayer_{elem_idx}", st, s_base, duration=float(elem.get("duration", 0.55))))
                elif entrance in ["card_stack", "card_stack_reveal", "stack_deck"]:
                    lines.extend(DirectorEffectsSuite.apply_card_stack_entrance(f"fLayer_{elem_idx}", st, effective_pos, s_base, duration=float(elem.get("duration", 0.40))))
                elif entrance in ["speed_blur", "blur_speed", "blur_in"]:
                    lines.extend(DirectorEffectsSuite.apply_speed_blur_transition(f"fLayer_{elem_idx}", st, duration=float(elem.get("duration", 0.35))))
                elif entrance in ["mask_wipe", "mask_reveal_wipe", "wipe_in"]:
                    lines.extend([
                        f"var sProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Scale');",
                        f"sProp_{elem_idx}.setValueAtTime({st:.2f}, [{s_base}, {s_base}, 100]);",
                    ])
                    lines.extend(DirectorEffectsSuite.apply_mask_reveal_wipe(f"fLayer_{elem_idx}", st, duration=float(elem.get("duration", 0.45)), wipe_angle=float(elem.get("wipe_angle", 180.0))))
                elif entrance in ["slide_in", "directional_slide", "directional_flow"]:
                    dx = -260 if effective_pos[0] > 960 else 260
                    lines.extend([
                        f"var sProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Scale');",
                        f"sProp_{elem_idx}.setValueAtTime({st:.2f}, [85, 85, 100]);",
                        f"sProp_{elem_idx}.setValueAtTime({st + 0.45:.2f}, [{s_base}, {s_base}, 100]);",
                        f"var pProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Position');",
                        f"pProp_{elem_idx}.setValueAtTime({st:.2f}, [{effective_pos[0] + dx}, {effective_pos[1]}, 0]);",
                        f"pProp_{elem_idx}.setValueAtTime({st + 0.45:.2f}, [{effective_pos[0]}, {effective_pos[1]}, 0]);",
                        f"var fxBlur_{elem_idx} = fLayer_{elem_idx}.property('Effects').addProperty('Directional Blur');",
                        f"fxBlur_{elem_idx}.property('Direction').setValue({'0.0' if dx > 0 else '180.0'});",
                        f"var blLen_{elem_idx} = fxBlur_{elem_idx}.property('Blur Length');",
                        f"blLen_{elem_idx}.setValueAtTime({st:.2f}, 35);",
                        f"blLen_{elem_idx}.setValueAtTime({st + 0.45:.2f}, 0);",
                    ])
                elif entrance in ["zoom_in", "fade_zoom"]:
                    lines.extend([
                        f"var sProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Scale');",
                        f"sProp_{elem_idx}.setValueAtTime({st:.2f}, [30, 30, 100]);",
                        f"sProp_{elem_idx}.setValueAtTime({st + 0.40:.2f}, [{s_base}, {s_base}, 100]);",
                        f"var opProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Opacity');",
                        f"opProp_{elem_idx}.setValueAtTime({st:.2f}, 0);",
                        f"opProp_{elem_idx}.setValueAtTime({st + 0.35:.2f}, 100);",
                    ])
                else: # pop_bounce / elastic_pop / pop_overshoot
                    lines.extend([
                        f"var sProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Scale');",
                        f"sProp_{elem_idx}.setValueAtTime({st:.2f}, [0, 0, 100]);",
                        f"sProp_{elem_idx}.setValueAtTime({st + 0.32:.2f}, [{s_pop}, {s_pop}, 100]);",
                        f"sProp_{elem_idx}.setValueAtTime({st + 0.48:.2f}, [{s_base}, {s_base}, 100]);",
                    ])

                # Scene Camera Creeping Push-in Multiplier
                cam_cfg = sc.get("camera", {})
                z_start = float(cam_cfg.get("zoom_start", 1.0))
                z_end = float(cam_cfg.get("zoom_end", 1.05))
                cam_ratio = max(1.0, min(1.12, z_end / max(z_start, 0.1)))
                s_hold_end = int(round(s_base * cam_ratio))

                # Standardized Idle / Movement
                idle_motion = elem.get("idle", None)
                if idle_motion in ["floating", "idle_floating", "breathe"] and not is_grounded:
                    lines.extend(DirectorEffectsSuite.apply_idle_floating(f"fLayer_{elem_idx}", st + 0.50, et - 0.45, (effective_pos[0], effective_pos[1]), s_base, bob_px=7))
                elif idle_motion == "orbit_arc" or elem.get("anim_type") == "orbit_arc":
                    lines.extend([
                        f"var pProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Position');",
                        f"pProp_{elem_idx}.setValueAtTime({st:.2f}, [{effective_pos[0] - 140}, {effective_pos[1] + 60}, 0]);",
                        f"pProp_{elem_idx}.setValueAtTime({st + 0.35:.2f}, [{effective_pos[0] - 30}, {effective_pos[1] - 40}, 0]);",
                        f"pProp_{elem_idx}.setValueAtTime({st + 0.70:.2f}, [{effective_pos[0]}, {effective_pos[1]}, 0]);",
                    ])

                # Ensure active mid-hold choreography (Scale Punches & Micro-Life between Entrance and Exit)
                raw_punches = list(elem.get("scale_punches", []))
                hold_span = (et - 0.45) - (st + 0.55)
                if not raw_punches and hold_span >= 2.2:
                    # Auto-inject a mid-hold emphasis beat so element is never static
                    raw_punches.append({"time": round(st + 0.55 + hold_span * 0.45, 2)})

                valid_punches = sorted(
                    [float(p.get("time", st + 1.2)) for p in raw_punches if (st + 0.50) <= float(p.get("time", 0.0)) <= (et - 0.42)]
                )

                for pt in valid_punches:
                    prog = max(0.0, min(1.0, (pt - st) / max(0.1, et - st)))
                    s_cur = int(round(s_base + (s_hold_end - s_base) * prog))
                    s_punch = int(round(s_cur * 1.18))
                    lines.extend([
                        f"// Active Mid-Hold Scale Punch & Micro-Impact at {pt:.2f}s",
                        f"var sProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Scale');",
                        f"sProp_{elem_idx}.setValueAtTime({pt - 0.04:.2f}, [{s_cur}, {s_cur}, 100]);",
                        f"sProp_{elem_idx}.setValueAtTime({pt + 0.09:.2f}, [{s_punch}, {s_punch}, 100]);",
                        f"sProp_{elem_idx}.setValueAtTime({pt + 0.24:.2f}, [{s_cur}, {s_cur}, 100]);",
                        f"var pProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Position');",
                        f"pProp_{elem_idx}.setValueAtTime({pt - 0.02:.2f}, [{effective_pos[0]}, {effective_pos[1]}, 0]);",
                        f"pProp_{elem_idx}.setValueAtTime({pt + 0.05:.2f}, [{effective_pos[0] + 12}, {effective_pos[1] - (8 if not is_grounded else 0)}, 0]);",
                        f"pProp_{elem_idx}.setValueAtTime({pt + 0.12:.2f}, [{effective_pos[0] - 10}, {effective_pos[1]}, 0]);",
                        f"pProp_{elem_idx}.setValueAtTime({pt + 0.22:.2f}, [{effective_pos[0]}, {effective_pos[1]}, 0]);",
                    ])

                # Standardized Exits (Written AFTER mid-hold punches in strict chronological order)
                exit_motion = elem.get("exit", "shrink_out")
                if exit_motion == "fly_away":
                    lines.extend(DirectorEffectsSuite.apply_fly_away_exit(f"fLayer_{elem_idx}", start_t=et - 0.45, current_pos=(effective_pos[0], effective_pos[1]), duration=0.45))
                elif exit_motion in ["shrink_out", "pop_shrink"]:
                    lines.extend([
                        f"var sProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Scale');",
                        f"sProp_{elem_idx}.setValueAtTime({et - 0.38:.2f}, [{s_hold_end}, {s_hold_end}, 100]);",
                        f"sProp_{elem_idx}.setValueAtTime({et - 0.24:.2f}, [{int(s_hold_end * 1.14)}, {int(s_hold_end * 1.14)}, 100]);",
                        f"sProp_{elem_idx}.setValueAtTime({et:.2f}, [0, 0, 100]);",
                        f"var opProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Opacity');",
                        f"opProp_{elem_idx}.setValueAtTime({et - 0.24:.2f}, 100);",
                        f"opProp_{elem_idx}.setValueAtTime({et:.2f}, 0);",
                    ])
                elif exit_motion in ["slide_out", "directional_slide_out"]:
                    out_dx = 280 if effective_pos[0] > 960 else -280
                    lines.extend([
                        f"var sProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Scale');",
                        f"sProp_{elem_idx}.setValueAtTime({et - 0.42:.2f}, [{s_hold_end}, {s_hold_end}, 100]);",
                        f"var pProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Position');",
                        f"pProp_{elem_idx}.setValueAtTime({et - 0.42:.2f}, [{effective_pos[0]}, {effective_pos[1]}, 0]);",
                        f"pProp_{elem_idx}.setValueAtTime({et:.2f}, [{effective_pos[0] + out_dx}, {effective_pos[1]}, 0]);",
                        f"var fxBlurOut_{elem_idx} = fLayer_{elem_idx}.property('Effects').addProperty('Directional Blur');",
                        f"fxBlurOut_{elem_idx}.property('Direction').setValue({'0.0' if out_dx > 0 else '180.0'});",
                        f"var blLenOut_{elem_idx} = fxBlurOut_{elem_idx}.property('Blur Length');",
                        f"blLenOut_{elem_idx}.setValueAtTime({et - 0.42:.2f}, 0);",
                        f"blLenOut_{elem_idx}.setValueAtTime({et:.2f}, 35);",
                        f"var opProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Opacity');",
                        f"opProp_{elem_idx}.setValueAtTime({et - 0.20:.2f}, 100);",
                        f"opProp_{elem_idx}.setValueAtTime({et:.2f}, 0);",
                    ])
                elif exit_motion in ["fade_out", "smooth_fade"]:
                    lines.extend([
                        f"var sProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Scale');",
                        f"sProp_{elem_idx}.setValueAtTime({et - 0.35:.2f}, [{s_hold_end}, {s_hold_end}, 100]);",
                        f"var opProp_{elem_idx} = fLayer_{elem_idx}.property('Transform').property('Opacity');",
                        f"opProp_{elem_idx}.setValueAtTime({et - 0.35:.2f}, 100);",
                        f"opProp_{elem_idx}.setValueAtTime({et:.2f}, 0);",
                    ])

                # Merge legacy light_sweeps and radio_waves into unified effects list
                combined_effects = list(elem.get("effects", []))
                for ls in elem.get("light_sweeps", []):
                    combined_effects.append({
                        "type": "light_sweep",
                        "time": ls.get("time", st + 1.0),
                        "duration": ls.get("duration", 0.45),
                        "intensity": ls.get("intensity", 20.0),
                        "width": ls.get("width", 24),
                        "color": ls.get("color", "gold")
                    })
                for rw in elem.get("radio_waves", []):
                    combined_effects.append({
                        "type": "radio_waves",
                        "time": rw.get("time", st + 0.8),
                        "end": rw.get("end", et),
                        "color": rw.get("color", "cyan")
                    })

                # Handle Standardized Director Effects on Elements
                for fx in combined_effects:
                    fx_type = fx.get("type", "")
                    fx_t = float(fx.get("time", fx.get("start", st)))

                    if fx_type in ["tint_flash", "color_tint_flash"]:
                        col_val = fx.get("color", "cyan")
                        col_rgb = COLOR_PALETTE.get(col_val, (0.133, 0.827, 0.933)) if isinstance(col_val, str) else tuple(col_val)
                        lines.extend(DirectorEffectsSuite.apply_color_tint_flash(f"fLayer_{elem_idx}", flash_time=fx_t, color_rgb=col_rgb, duration=float(fx.get("duration", 0.22))))
                    elif fx_type in ["white_strobe", "strobe_flash", "strobe"]:
                        lines.extend(DirectorEffectsSuite.apply_white_strobe_flash(f"fLayer_{elem_idx}", flash_time=fx_t, duration=float(fx.get("duration", 0.22))))
                    elif fx_type in ["wiggle", "wiggle_attention", "attention_wiggle"]:
                        lines.extend(DirectorEffectsSuite.apply_wiggle_attention(f"fLayer_{elem_idx}", wiggle_time=fx_t, duration=float(fx.get("duration", 0.45))))
                    elif fx_type in ["light_sweep", "sweep"]:
                        sw_intensity = float(fx.get("intensity", 20.0))
                        sw_width = int(fx.get("width", 24))
                        sw_angle = float(fx.get("angle", -35.0))
                        col_val = fx.get("color", None)
                        col_rgb = COLOR_PALETTE.get(col_val, (0.90, 0.92, 0.95)) if isinstance(col_val, str) else col_val
                        lines.extend(DirectorEffectsSuite.apply_light_sweep(
                            f"fLayer_{elem_idx}",
                            start_t=fx_t,
                            duration=float(fx.get("duration", 0.45)),
                            angle=sw_angle,
                            width=sw_width,
                            intensity=sw_intensity,
                            color_rgb=col_rgb
                        ))
                    elif fx_type in ["mask_wipe", "mask_reveal_wipe"]:
                        lines.extend(DirectorEffectsSuite.apply_mask_reveal_wipe(
                            f"fLayer_{elem_idx}",
                            start_t=fx_t,
                            duration=float(fx.get("duration", 0.45)),
                            wipe_angle=float(fx.get("angle", 90.0))
                        ))
                    elif fx_type in ["speed_blur", "blur_speed"]:
                        lines.extend(DirectorEffectsSuite.apply_speed_blur_transition(
                            f"fLayer_{elem_idx}",
                            start_t=fx_t,
                            duration=float(fx.get("duration", 0.35)),
                            max_blur=float(fx.get("blur", 40.0))
                        ))
                    elif fx_type in ["neon_glow", "glow"]:
                        col_val = fx.get("color", "cyan")
                        col_rgb = COLOR_PALETTE.get(col_val, (0.176, 0.831, 0.749)) if isinstance(col_val, str) else tuple(col_val)
                        lines.extend(DirectorEffectsSuite.apply_neon_glow(f"fLayer_{elem_idx}", color_rgb=col_rgb, radius=fx.get("radius", 24)))
                    elif fx_type in ["light_burst", "light_burst_flash"]:
                        lines.extend(DirectorEffectsSuite.apply_light_burst_flash(f"fLayer_{elem_idx}", burst_time=fx_t, duration=float(fx.get("duration", 0.35))))
                    elif fx_type == "radio_waves":
                        col_val = fx.get("color", "cyan")
                        col_rgb = COLOR_PALETTE.get(col_val, (0.2, 0.8, 1.0)) if isinstance(col_val, str) else tuple(col_val)
                        lines.extend(DirectorEffectsSuite.apply_radio_waves(f"fLayer_{elem_idx}", start_t=fx_t, end_t=float(fx.get("end", et)), wave_color=col_rgb))
                    elif fx_type == "radial_blur":
                        lines.extend(DirectorEffectsSuite.apply_radial_fast_blur(f"fLayer_{elem_idx}", start_t=fx_t, end_t=float(fx.get("end", fx_t + 0.35)), max_amount=fx.get("amount", 35.0)))
                    elif fx_type in ["lightning", "lightning_flash", "electric_arc"]:
                        lines.extend(DirectorEffectsSuite.apply_lightning_flash(f"fLayer_{elem_idx}", start_t=fx_t, duration=float(fx.get("duration", 0.40))))
                    elif fx_type in ["border_flash", "danger_flash", "edge_flash"]:
                        v_type = fx.get("color", "red")
                        p_op = float(fx.get("opacity", 45.0))
                        p_pulses = int(fx.get("pulses", 2))
                        lines.extend(DirectorEffectsSuite.apply_camera_border_flash("comp", flash_time=fx_t, vignette_type=v_type, duration=float(fx.get("duration", 0.60)), peak_opacity=p_op, pulses=p_pulses))

                lines.append("")
                elem_idx += 1

            # Camera / Scene Level Effects (3D Dolly/Pan + Rectangular Border Flash / Danger Glow)
            cam_cfg = sc.get("camera", {})
            if cam_cfg and (cam_cfg.get("dolly", False) or "center_start" in cam_cfg or "center_end" in cam_cfg):
                c_start = tuple(cam_cfg.get("center_start", [960, 540]))
                c_end = tuple(cam_cfg.get("center_end", c_start))
                z_s = float(cam_cfg.get("zoom_start", 1.0))
                z_e = float(cam_cfg.get("zoom_end", 1.06))
                lines.extend(DirectorEffectsSuite.apply_camera_dolly_pan("comp", sc_start, sc_end, zoom_start=z_s, zoom_end=z_e, center_start=c_start, center_end=c_end))

            for s_fx in sc.get("camera_effects", []):
                sfx_type = s_fx.get("type", "")
                sfx_t = float(s_fx.get("time", s_fx.get("start", sc_start)))
                if sfx_type in ["border_flash", "danger_flash", "edge_flash"]:
                    v_type = s_fx.get("color", "red")
                    p_op = float(s_fx.get("opacity", 45.0))
                    p_pulses = int(s_fx.get("pulses", 2))
                    lines.extend(DirectorEffectsSuite.apply_camera_border_flash("comp", flash_time=sfx_t, vignette_type=v_type, duration=float(s_fx.get("duration", 0.60)), peak_opacity=p_op, pulses=p_pulses))


                lines.append("")
                elem_idx += 1

        # Add Style 1 Arabic Word Cards using dedicated component
        word_idx = 1
        for sc in scenes:
            sc_id = sc.get("id", "")
            sc_start = float(sc.get("start", 0.0))
            lead_pos = scene_lead_pos.get(sc_id, [960, 540])
            words_list = sc.get("words", []) or sc.get("word_cards", [])
            for w in words_list:
                card_lines = self._build_style1_card_script(w, word_idx, current_scene_element_pos=lead_pos, scene_start=sc_start)
                lines.extend(card_lines)
                word_idx += 1

        return "\n".join(lines)

    def compile_project(self) -> Path:
        """Builds and compiles the project into an .ecproj file with styled text."""
        jsx_script = self.generate_jsx_script()
        jsx_file = self.output_dir / f"{self.section_id}_build.jsx"
        ecproj_file = self.output_dir / f"{self.section_id}_effectcraft.ecproj"
        
        with open(jsx_file, "w", encoding="utf-8") as f:
            f.write(jsx_script)
            
        print(f"[*] Compiling {self.section_id} via EffectCraft CLI...")
        cmd = [
            str(CLI_PATH),
            "--empty",
            "--save-as", str(ecproj_file),
            "script", str(jsx_file)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
        if res.returncode != 0:
            print(f"[!] Compilation warning/error: {res.stderr}")

        # Post-process .ecproj to style typography with Cairo font and crisp white color
        self._style_typography_in_project(ecproj_file)
        print(f"[+] Project successfully compiled: {ecproj_file}")
        return ecproj_file

    def _style_typography_in_project(self, ecproj_file: Path):
        """Enforces Cairo-Bold font styling and pure white text in the project JSON."""
        if not ecproj_file.exists():
            return
            
        with open(ecproj_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("items", {}).values():
            if item.get("kind", {}).get("type") == "Comp":
                for layer in item.get("kind", {}).get("layers", []):
                    if layer.get("source", {}).get("type") == "Text":
                        for group in layer.get("props", {}).get("children", []):
                            if group.get("match") == "text":
                                for prop in group.get("children", []):
                                    if prop.get("match") == "sourceText":
                                        val = prop.get("value", {}).get("v", {})
                                        val["font"] = "Cairo"
                                        val["style"] = "Bold"
                                        val["size"] = 64.0
                                        val["fill"] = [1.0, 1.0, 1.0, 1.0]

        with open(ecproj_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def render(self, out_mp4: Optional[Path] = None, start: float = 0.0, end: Optional[float] = None) -> Path:
        """Renders the master 1080p MP4 using EffectCraft's pure Rust engine."""
        ecproj_file = self.compile_project()
        if not out_mp4:
            out_mp4 = self.output_dir / f"{self.section_id}_effectcraft_master.mp4"
            
        render_end = end if end is not None else self.duration
        comp_name = f"{self.section_id}_Master"
        
        print(f"[*] Rendering {comp_name} ({start}s -> {render_end}s) to {out_mp4.name}...")
        cmd = [
            str(CLI_PATH),
            "--project", str(ecproj_file),
            "render",
            "--comp", comp_name,
            "--out", str(out_mp4),
            "--fps", str(self.fps),
            "--start", str(start),
            "--end", str(render_end),
            "--audio", "on",
            "--bitrate", "16000"
        ]
        
        start_time = time.time()
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
        elapsed = time.time() - start_time
        
        if res.returncode == 0:
            print(f"[+] Render finished successfully in {elapsed:.2f}s: {out_mp4}")
        else:
            print(f"[!] Render failed: {res.stderr}\n{res.stdout}")
            
        return out_mp4

if __name__ == "__main__":
    section_dir = ROOT_DIR / "sections" / "section_01"
    engine = EffectCraftMotionEngine(section_dir)
    engine.compile_project()

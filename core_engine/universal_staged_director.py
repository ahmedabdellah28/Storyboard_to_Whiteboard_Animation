"""Universal Staged Motion Director Engine (V6 Template).

A completely parameterized, manifest-driven engine that renders any section
from its manifest.json without modifying code.
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

# Safe UTF-8 console output
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

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from production_engine.opencut_fx import ease, OpenCutVisualFX, DEFAULT_CAIRO_FONT

POPUP_THEMES = {
    "emerald": {
        "card_bg": (16, 105, 75, 255),
        "border": (52, 211, 153, 255),
        "badge_bg": (52, 211, 153, 255),
        "badge_text": (6, 78, 59, 255),
        "title_text": (255, 255, 255, 255),
    },
    "crimson": {
        "card_bg": (153, 27, 27, 255),
        "border": (248, 113, 113, 255),
        "badge_bg": (248, 113, 113, 255),
        "badge_text": (127, 29, 29, 255),
        "title_text": (255, 255, 255, 255),
    },
    "amber": {
        "card_bg": (180, 83, 9, 255),
        "border": (251, 191, 36, 255),
        "badge_bg": (251, 191, 36, 255),
        "badge_text": (120, 53, 15, 255),
        "title_text": (255, 255, 255, 255),
    },
    "cyan": {
        "card_bg": (14, 116, 144, 255),
        "border": (34, 211, 238, 255),
        "badge_bg": (34, 211, 238, 255),
        "badge_text": (22, 78, 99, 255),
        "title_text": (255, 255, 255, 255),
    },
    "teal": {
        "card_bg": (13, 148, 136, 255),
        "border": (45, 212, 191, 255),
        "badge_bg": (45, 212, 191, 255),
        "badge_text": (19, 78, 74, 255),
        "title_text": (255, 255, 255, 255),
    },
    "forest": {
        "card_bg": (20, 83, 45, 255),
        "border": (74, 222, 128, 255),
        "badge_bg": (74, 222, 128, 255),
        "badge_text": (5, 46, 22, 255),
        "title_text": (255, 255, 255, 255),
    },
    "purple": {
        "card_bg": (109, 40, 217, 255),
        "border": (192, 132, 252, 255),
        "badge_bg": (192, 132, 252, 255),
        "badge_text": (59, 7, 100, 255),
        "title_text": (255, 255, 255, 255),
    },
}

def get_arabic_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for p in [DEFAULT_CAIRO_FONT, r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\tahoma.ttf"]:
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
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text

def create_staged_popup_card(title: str, badge: Optional[str] = None, theme_name: str = "cyan", style_type: str = "card_badge", write_p: float = 1.0) -> np.ndarray:
    theme = POPUP_THEMES.get(theme_name, POPUP_THEMES["cyan"])
    
    # Scale Upgrade: 64pt title with Cairo-Bold (Style 1: Clean single title card, no upper badge)
    font_word = get_arabic_font(64, bold=True)
    s_title = reshape_arabic(title)
    
    dummy = Image.new("RGBA", (10, 10))
    d_dummy = ImageDraw.Draw(dummy)
    
    bb_w = d_dummy.textbbox((0, 0), s_title, font=font_word)
    ww, wh = bb_w[2] - bb_w[0], bb_w[3] - bb_w[1]
    
    card_w = max(ww + 110, 360)
    card_h = wh + 74
    
    # 1. Base card (Stable, grounded, sharp outline, no upper badge)
    base_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base_img)
    draw.rounded_rectangle([(3, 3), (card_w - 3, card_h - 3)], radius=24, fill=theme["card_bg"], outline=theme["border"], width=5)
    
    curr_y = (card_h - wh) // 2
        
    # 2. Word Layer with Style 1 RTL Handwriting & Cursor
    word_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    d_word = ImageDraw.Draw(word_img)
    tx = (card_w - ww) // 2 - bb_w[0]
    ty = curr_y - bb_w[1]
    d_word.text((tx, ty), s_title, font=font_word, fill=theme["title_text"])
    
    w_arr = np.array(word_img)
    if write_p < 0.999:
        text_x_start = (card_w - ww) // 2
        text_x_end = text_x_start + ww
        cutoff = int(round(text_x_end - ww * write_p))
        w_arr[:, :cutoff, 3] = 0
        if 0.05 < write_p < 0.98:
            nib_x = np.clip(cutoff, 0, card_w - 1)
            nib_y = curr_y + wh // 2
            cv2.circle(w_arr, (nib_x, nib_y), 6, theme["border"], -1)
            cv2.circle(w_arr, (nib_x, nib_y), 9, (255, 255, 255, 180), 2)
            
    # 3. Composite Word Layer on Base Card
    base_arr = np.array(base_img)
    wa = w_arr[:, :, 3].astype(np.float32) / 255.0
    wa3 = np.dstack([wa, wa, wa])
    blended = w_arr[:, :, :3].astype(np.float32) * wa3 + base_arr[:, :, :3].astype(np.float32) * (1.0 - wa3)
    base_arr[:, :, :3] = np.clip(blended, 0, 255).astype(np.uint8)
    base_arr[:, :, 3] = np.maximum(base_arr[:, :, 3], w_arr[:, :, 3])
    
    bgra = cv2.cvtColor(base_arr, cv2.COLOR_RGBA2BGRA)
    return OpenCutVisualFX.apply_drop_shadow(bgra, offset=(6, 16), blur_radius=22, opacity=0.38)

class UniversalStagedDirector:
    """Renders any section from its manifest.json dynamically."""
    def __init__(self, manifest_path: Path | str):
        self.manifest_path = Path(manifest_path).resolve()
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)
            
        self.sec_dir = self.manifest_path.parent
        self.assets_dir = self.sec_dir / "assets"
        self.meta_path = self.assets_dir / "metadata.json"
        
        self.fps = self.manifest.get("fps", 30)
        self.width, self.height = self.manifest.get("resolution", [1920, 1080])
        self.duration = self.manifest["total_duration"]
        self.total_frames = int(self.duration * self.fps)
        self.scenes = self.manifest["scenes"]
        
        self.loaded_assets: Dict[str, np.ndarray] = {}
        self._load_assets()
        
    def _load_assets(self):
        # 1. Load from metadata.json if available
        if self.meta_path.exists():
            with open(self.meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            
            # Check if flat dict or nested under primary_assets/sub_elements
            if "primary_assets" in meta or "sub_elements" in meta:
                entries = {**meta.get("primary_assets", {}), **meta.get("sub_elements", {})}
            else:
                entries = meta
                
            for k, info in entries.items():
                fname = info.get("filename", info.get("file", f"{k}.png")) if isinstance(info, dict) else f"{k}.png"
                p = self.assets_dir / fname
                if p.exists():
                    self.loaded_assets[k] = np.array(Image.open(p).convert("RGBA"))
                    
        # 2. Fallback: load any existing pngs in assets_dir
        for p in self.assets_dir.glob("*.png"):
            k = p.stem
            if k not in self.loaded_assets and k not in ("contact_sheet", "connectivity_and_separation_map"):
                self.loaded_assets[k] = np.array(Image.open(p).convert("RGBA"))
                    
    def render_element(self, asset_key: str, t: float, start_t: float, target_pos: Tuple[int, int], target_size: int, is_elevated: bool = False) -> Tuple[np.ndarray, Tuple[int, int]]:
        raw = self.loaded_assets.get(asset_key)
        if raw is None:
            return np.zeros((10, 10, 4), dtype=np.uint8), (0, 0)
            
        elapsed = max(0.0, t - start_t)
        intro_dur = 0.40
        if elapsed < intro_dur:
            s = ease(elapsed / intro_dur, "out_back")
            scale = 0.3 + 0.7 * s
            alpha = min(1.0, elapsed / 0.15)
        else:
            scale, alpha = 1.0, 1.0
            
        h, w = raw.shape[:2]
        f_scale = (target_size / max(h, w)) * scale
        nw, nh = max(4, int(w * f_scale)), max(4, int(h * f_scale))
        scaled = cv2.resize(raw, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
        if alpha < 1.0:
            scaled[:, :, 3] = (scaled[:, :, 3].astype(float) * alpha).astype(np.uint8)
            
        offset = (10, 22) if is_elevated else (1, 3)
        blur = 24 if is_elevated else 4
        op = 0.38 if is_elevated else 0.10
        
        bgra = cv2.cvtColor(scaled, cv2.COLOR_RGBA2BGRA)
        with_shadow = OpenCutVisualFX.apply_drop_shadow(bgra, offset=offset, blur_radius=blur, opacity=op)
        sh, sw = with_shadow.shape[:2]
        return with_shadow, (target_pos[0] - sw // 2, target_pos[1] - sh // 2)

    def render_word_card(self, word_cfg: Dict[str, Any], t: float) -> Optional[Tuple[np.ndarray, Tuple[int, int]]]:
        st, en = word_cfg["start"], word_cfg["end"]
        if t < st or t > en:
            return None
        elapsed = t - st
        dur = en - st
        
        # Style 1: Stable card base, handwriting typewriter reveal on the word layer only
        write_dur = min(0.65, max(0.35, dur * 0.45))
        write_p = ease(min(1.0, elapsed / write_dur), "out_cubic")
        
        card_with_shadow = create_staged_popup_card(
            word_cfg["word"],
            None,  # No upper text (badge removed per user directive)
            theme_name=word_cfg.get("theme", "cyan"),
            style_type=word_cfg.get("style_type", "card_badge"),
            write_p=write_p
        )
        
        # Subtle fade in (0.10s) and fade out (0.12s)
        alpha = 1.0
        if elapsed < 0.10:
            alpha = elapsed / 0.10
        elif t > en - 0.12:
            alpha = max(0.0, (en - t) / 0.12)
            
        if alpha < 0.999:
            card_with_shadow = card_with_shadow.copy()
            card_with_shadow[:, :, 3] = (card_with_shadow[:, :, 3].astype(float) * alpha).astype(np.uint8)
            
        center_pos = word_cfg["pos"]
        sh, sw = card_with_shadow.shape[:2]
        return card_with_shadow, (center_pos[0] - sw // 2, center_pos[1] - sh // 2)

    def render_frame(self, t: float) -> np.ndarray:
        frame = np.full((self.height, self.width, 3), 255, dtype=np.uint8)
        current_scene = None
        for s in self.scenes:
            if s["start"] <= t < s["end"]:
                current_scene = s
                break
        if not current_scene and t >= self.scenes[-1]["end"]:
            current_scene = self.scenes[-1]
        if not current_scene:
            return frame
            
        for el in current_scene.get("elements", []):
            if el["start"] <= t <= el["end"]:
                layer, (lx, ly) = self.render_element(el["asset_key"], t, el["start"], el["pos"], el["target_size"], el.get("is_elevated", False))
                self._blend(frame, layer, lx, ly)
                
        for w in current_scene.get("words", []):
            res = self.render_word_card(w, t)
            if res:
                self._blend(frame, res[0], res[1][0], res[1][1])
        return frame

    def _blend(self, base: np.ndarray, over: np.ndarray, x: int, y: int):
        oh, ow = over.shape[:2]
        bh, bw = base.shape[:2]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(bw, x + ow), min(bh, y + oh)
        if x1 >= x2 or y1 >= y2: return
        src = over[y1 - y:y2 - y, x1 - x:x2 - x]
        alpha = (src[:, :, 3].astype(float) / 255.0)[:, :, np.newaxis]
        base[y1:y2, x1:x2] = (alpha * src[:, :, :3].astype(float) + (1.0 - alpha) * base[y1:y2, x1:x2].astype(float)).astype(np.uint8)

    def export_video(self, output_mp4: str, audio_wav: str):
        out_p = Path(output_mp4)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        temp_v = str(out_p.with_name(f"temp_{out_p.name}"))
        
        cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-s", f"{self.width}x{self.height}",
               "-pix_fmt", "bgr24", "-r", str(self.fps), "-i", "-", "-c:v", "libx264", "-preset", "fast",
               "-crf", "18", "-pix_fmt", "yuv420p", temp_v]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        t0 = time.time()
        for f in range(self.total_frames):
            frame = self.render_frame(f / float(self.fps))
            proc.stdin.write(frame.tobytes())
            if (f + 1) % 150 == 0 or (f + 1) == self.total_frames:
                print(f"  Frame {f+1}/{self.total_frames} ({(f+1)/self.total_frames*100:.1f}%) - {(f+1)/(time.time()-t0):.1f} fps", flush=True)
        proc.stdin.close()
        proc.wait()
        
        mux = ["ffmpeg", "-y", "-i", temp_v, "-i", str(audio_wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_mp4]
        subprocess.run(mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(temp_v): os.remove(temp_v)
        print(f"✅ Video exported successfully: {output_mp4}")

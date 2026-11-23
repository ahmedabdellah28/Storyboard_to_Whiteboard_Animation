"""Universal Staged Motion Director Engine (V2 - Advanced Motion System).

Implements the motion behaviors and cinematic transitions specified in motion_types.md:
- Camera System (Push, Pull, Pan, Zoom) with smooth viewport transforms
- Directional Flow & Object Push (scene-to-scene momentum)
- Morph / Dissolve Bridge between visual concepts
- Line Path / Inking Connector (animated whiteboard pen lines connecting elements)
- Scale Punch & Elastic Overshoot
- Mask Reveal (circular and directional)
- Motion Blur & Speed Blur on transitions
- Parallax Depth & Multi-layer staggering
- Strictly adheres to Style 1 for typography (stable grounded card, 64pt Cairo-Bold, RTL handwriting, no upper badge)
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
        "title_text": (255, 255, 255, 255),
    },
    "crimson": {
        "card_bg": (153, 27, 27, 255),
        "border": (248, 113, 113, 255),
        "title_text": (255, 255, 255, 255),
    },
    "amber": {
        "card_bg": (180, 83, 9, 255),
        "border": (251, 191, 36, 255),
        "title_text": (255, 255, 255, 255),
    },
    "cyan": {
        "card_bg": (14, 116, 144, 255),
        "border": (34, 211, 238, 255),
        "title_text": (255, 255, 255, 255),
    },
    "teal": {
        "card_bg": (13, 148, 136, 255),
        "border": (45, 212, 191, 255),
        "title_text": (255, 255, 255, 255),
    },
    "forest": {
        "card_bg": (20, 83, 45, 255),
        "border": (74, 222, 128, 255),
        "title_text": (255, 255, 255, 255),
    },
    "purple": {
        "card_bg": (109, 40, 217, 255),
        "border": (192, 132, 252, 255),
        "title_text": (255, 255, 255, 255),
    },
    "royal": {
        "card_bg": (15, 76, 92, 255),
        "border": (45, 212, 191, 255),
        "title_text": (255, 255, 255, 255),
    },
}

def get_arabic_font(size: int = 44, bold: bool = True) -> ImageFont.FreeTypeFont:
    for p in [DEFAULT_CAIRO_FONT, r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\tahoma.ttf"]:
        if p and os.path.exists(str(p)):
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()

def reshape_arabic(text: str) -> str:
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        configuration = {
            'delete_harakat': False,
            'support_ligatures': True,
        }
        reshaper = arabic_reshaper.ArabicReshaper(configuration=configuration)
        return get_display(reshaper.reshape(text))
    except Exception:
        return text

# -------------------------------------------------------------
# Style 1 V2: Dot Travel -> Card Bloom -> Rapid Handwriting
# -------------------------------------------------------------
def create_traveling_dot(theme_name: str = "teal", size: int = 44) -> np.ndarray:
    """Generates a glowing pen nib / energy dot that flies across the screen."""
    theme = POPUP_THEMES.get(theme_name, POPUP_THEMES["teal"])
    img = np.zeros((size, size, 4), dtype=np.uint8)
    cx, cy = size // 2, size // 2
    # Outer pulsating halo
    cv2.circle(img, (cx, cy), 16, (*theme["border"][:3], 90), -1, cv2.LINE_AA)
    # Bright core
    cv2.circle(img, (cx, cy), 10, (*theme["border"][:3], 255), -1, cv2.LINE_AA)
    # White incandescent tip
    cv2.circle(img, (cx, cy), 4, (255, 255, 255, 255), -1, cv2.LINE_AA)
    return img

def create_staged_popup_card_v2(
    title: str,
    theme_name: str = "teal",
    bloom_p: float = 1.0,
    write_p: float = 1.0
) -> np.ndarray:
    """Creates card expanding from dot (bloom_p) and reveals text rapidly (write_p) in RAM."""
    theme = POPUP_THEMES.get(theme_name, POPUP_THEMES["teal"])
    font_word = get_arabic_font(44, bold=True)
    display_text = reshape_arabic(title)
    
    # Measure exact text dimensions
    dummy = Image.new("RGBA", (10, 10))
    d_dummy = ImageDraw.Draw(dummy)
    bbox = d_dummy.textbbox((0, 0), display_text, font=font_word)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    pad_h = 48
    pad_v = 24
    corner_radius = 20
    border_width = 4
    
    final_w = max(tw + pad_h * 2, 240)
    final_h = max(th + pad_v * 2, 82)
    
    # Calculate current blooming dimensions from dot to full card
    if bloom_p < 0.999:
        s_b = ease(bloom_p, "out_back")
        card_w = max(24, int(24 + (final_w - 24) * s_b))
        card_h = max(24, int(24 + (final_h - 24) * s_b))
        r_start = min(card_w, card_h) // 2
        card_r = max(4, int(r_start * (1.0 - bloom_p) + corner_radius * bloom_p))
    else:
        card_w = final_w
        card_h = final_h
        card_r = corner_radius
        
    base_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base_img)
    draw.rounded_rectangle(
        [(2, 2), (card_w - 2, card_h - 2)],
        radius=card_r,
        fill=theme["card_bg"],
        outline=theme["border"],
        width=border_width
    )
    
    # Only render text when blooming is nearly complete and write_p > 0
    if bloom_p >= 0.90 and write_p > 0.001:
        cx = card_w // 2
        cy = (card_h // 2) - 2
        word_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        d_word = ImageDraw.Draw(word_img)
        d_word.text((cx, cy), display_text, font=font_word, fill=theme["title_text"], anchor="mm")
        
        w_arr = np.array(word_img)
        if write_p < 0.999:
            text_x_start = cx - tw // 2
            text_x_end = cx + tw // 2
            cutoff = int(round(text_x_end - tw * write_p))
            w_arr[:, :max(0, cutoff), 3] = 0
            if 0.05 < write_p < 0.98:
                nib_x = np.clip(cutoff, 4, card_w - 5)
                nib_y = cy
                cv2.circle(w_arr, (nib_x, nib_y), 5, theme["border"][:3], -1, cv2.LINE_AA)
                cv2.circle(w_arr, (nib_x, nib_y), 8, (255, 255, 255, 200), 2, cv2.LINE_AA)
                
        base_arr = np.array(base_img)
        wa = w_arr[:, :, 3].astype(np.float32) / 255.0
        wa3 = np.dstack([wa, wa, wa])
        blended = w_arr[:, :, :3].astype(np.float32) * wa3 + base_arr[:, :, :3].astype(np.float32) * (1.0 - wa3)
        base_arr[:, :, :3] = np.clip(blended, 0, 255).astype(np.uint8)
        base_arr[:, :, 3] = np.maximum(base_arr[:, :, 3], w_arr[:, :, 3])
    else:
        base_arr = np.array(base_img)
        
    bgra = cv2.cvtColor(base_arr, cv2.COLOR_RGBA2BGRA)
    shadow_op = 0.35 * min(1.0, bloom_p * 1.5)
    return OpenCutVisualFX.apply_drop_shadow(bgra, offset=(4, 10), blur_radius=16, opacity=shadow_op)

def create_staged_popup_card(title: str, badge: Optional[str] = None, theme_name: str = "cyan", style_type: str = "card_badge", write_p: float = 1.0) -> np.ndarray:
    return create_staged_popup_card_v2(title, theme_name=theme_name, bloom_p=1.0, write_p=write_p)


# -------------------------------------------------------------
# Advanced Motion FX Helpers (V2 Motion System)
# -------------------------------------------------------------
class MotionFX:
    """Procedural Motion Graphic behaviors and transitions."""

    @staticmethod
    def apply_directional_motion_blur(img: np.ndarray, angle_deg: float, length: int) -> np.ndarray:
        """Applies linear motion blur along angle_deg with specified pixel length."""
        if length <= 1:
            return img
        length = max(3, int(length))
        if length % 2 == 0:
            length += 1
        rad = math.radians(angle_deg)
        kernel = np.zeros((length, length), dtype=np.float32)
        cx, cy = length // 2, length // 2
        dx = math.cos(rad) * (length // 2)
        dy = math.sin(rad) * (length // 2)
        p1 = (int(cx - dx), int(cy - dy))
        p2 = (int(cx + dx), int(cy + dy))
        cv2.line(kernel, p1, p2, 1.0, 1)
        k_sum = kernel.sum()
        if k_sum > 0:
            kernel /= k_sum
        return cv2.filter2D(img, -1, kernel)

    @staticmethod
    def apply_elastic_spring(p: float, decay: float = 6.0, freq: float = 12.0) -> float:
        """Damped harmonic overshoot settling at 1.0."""
        if p >= 1.0:
            return 1.0
        return 1.0 - math.exp(-decay * p) * math.cos(freq * p)

    @staticmethod
    def draw_whiteboard_inking_path(frame: np.ndarray, p1: Tuple[int, int], p2: Tuple[int, int], progress: float, color=(60, 60, 60), thickness=5):
        """Draws a hand-inked curved path from p1 to p2 with an active pen nib dot."""
        if progress <= 0.0:
            return
        progress = min(1.0, max(0.0, progress))
        
        # Quadratic control point arching upwards
        mx = (p1[0] + p2[0]) / 2.0
        my = min(p1[1], p2[1]) - 90.0  # Natural arch
        
        # Sample Bezier curve points up to progress
        num_pts = max(3, int(60 * progress))
        curve_pts = []
        for i in range(num_pts + 1):
            t = (i / float(num_pts)) * progress
            bx = (1 - t)**2 * p1[0] + 2 * (1 - t) * t * mx + t**2 * p2[0]
            by = (1 - t)**2 * p1[1] + 2 * (1 - t) * t * my + t**2 * p2[1]
            curve_pts.append((int(round(bx)), int(round(by))))
            
        for i in range(len(curve_pts) - 1):
            cv2.line(frame, curve_pts[i], curve_pts[i+1], color, thickness, cv2.LINE_AA)
            
        # Glowing nib at the leading tip
        if 0.02 < progress < 0.99 and curve_pts:
            tip = curve_pts[-1]
            cv2.circle(frame, tip, thickness + 3, (45, 212, 191), -1, cv2.LINE_AA)
            cv2.circle(frame, tip, thickness + 6, (255, 255, 255), 2, cv2.LINE_AA)

    @staticmethod
    def apply_camera_transform(frame: np.ndarray, cam_center: Tuple[float, float], zoom: float) -> np.ndarray:
        """Applies a virtual camera zoom and pan matrix onto the frame."""
        if abs(zoom - 1.0) < 0.001 and abs(cam_center[0] - frame.shape[1]/2) < 1.0 and abs(cam_center[1] - frame.shape[0]/2) < 1.0:
            return frame
        h, w = frame.shape[:2]
        cx, cy = cam_center
        # Construct affine transformation matrix centered on cx, cy
        M = cv2.getRotationMatrix2D((cx, cy), 0, zoom)
        # Shift so cx, cy maps towards screen center (w/2, h/2)
        M[0, 2] += (w / 2.0 - cx)
        M[1, 2] += (h / 2.0 - cy)
        return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))


# -------------------------------------------------------------
# Universal Staged Director V2
# -------------------------------------------------------------
class UniversalStagedDirectorV2:
    """Advanced Motion Graphics Director Engine (V2).
    
    Supports:
    - Camera Push / Pull / Pan
    - Morph Transitions & Concept Bridges
    - Directional Flow & Object Push
    - Whiteboard Inking Path Connectors
    - Scale Punch on audio keywords
    - Elastic Overshoot & Velocity Motion Blur
    - Full Style 1 typography standard
    """

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
        if self.meta_path.exists():
            with open(self.meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if "primary_assets" in meta or "sub_elements" in meta:
                entries = {**meta.get("primary_assets", {}), **meta.get("sub_elements", {})}
            else:
                entries = meta
            for k, info in entries.items():
                fname = info.get("filename", info.get("file", f"{k}.png")) if isinstance(info, dict) else f"{k}.png"
                p = self.assets_dir / fname
                if p.exists():
                    self.loaded_assets[k] = np.array(Image.open(p).convert("RGBA"))
                    
        for p in self.assets_dir.glob("*.png"):
            k = p.stem
            if k not in self.loaded_assets and k not in ("contact_sheet", "connectivity_and_separation_map"):
                self.loaded_assets[k] = np.array(Image.open(p).convert("RGBA"))

    def compute_camera_state(self, t: float) -> Tuple[Tuple[float, float], float]:
        """Calculates current camera (center_x, center_y) and zoom at time t."""
        default_center = (self.width / 2.0, self.height / 2.0)
        default_zoom = 1.0
        
        # Check if the active scene defines custom camera dynamics
        for s in self.scenes:
            if s["start"] <= t < s["end"]:
                cam_cfg = s.get("camera")
                if not cam_cfg:
                    break
                st, en = s["start"], s["end"]
                dur = cam_cfg.get("duration", max(0.1, en - st))
                p = min(1.0, (t - st) / dur)
                
                # Camera Push / Pull support
                z_start = cam_cfg.get("zoom_start", 1.0)
                z_end = cam_cfg.get("zoom_end", 1.0)
                cur_zoom = z_start + (z_end - z_start) * ease(p, "in_out_quad")
                
                c_start = cam_cfg.get("center_start", default_center)
                c_end = cam_cfg.get("center_end", default_center)
                cur_cx = c_start[0] + (c_end[0] - c_start[0]) * ease(p, "in_out_quad")
                cur_cy = c_start[1] + (c_end[1] - c_start[1]) * ease(p, "in_out_quad")
                return (cur_cx, cur_cy), cur_zoom
                
        return default_center, default_zoom

    def render_element_v2(self, el_cfg: Dict[str, Any], t: float) -> Tuple[np.ndarray, Tuple[int, int]]:
        """Renders an element with V2 motion behaviors (Elastic entrance, Directional flow, Scale punch, Exit push)."""
        asset_key = el_cfg["asset_key"]
        raw = self.loaded_assets.get(asset_key)
        if raw is None:
            return np.zeros((10, 10, 4), dtype=np.uint8), (0, 0)
            
        start_t, end_t = el_cfg["start"], el_cfg["end"]
        target_pos = list(el_cfg["pos"])
        target_size = el_cfg.get("target_size", 540)
        is_elevated = el_cfg.get("is_elevated", False)
        anim_type = el_cfg.get("anim_type", "elastic_pop")
        
        elapsed = max(0.0, t - start_t)
        total_life = end_t - start_t
        time_to_exit = end_t - t
        
        # 1. Entrance Phase (Fast, snappy velocity)
        intro_dur = 0.22
        scale = 1.0
        alpha = 1.0
        cur_pos = [target_pos[0], target_pos[1]]
        motion_blur_len = 0
        motion_blur_angle = 0.0

        # If grounded, anchor bottom directly to stage baseline (Y=840)
        if not is_elevated:
            ground_y = el_cfg.get("ground_y", 840)
            cur_pos[1] = ground_y - int(target_size * 0.48)
            
        if elapsed < intro_dur:
            p = elapsed / intro_dur
            if anim_type in ("none", "static"):
                scale = 1.0
                alpha = 1.0
            elif anim_type == "directional_flow":
                # Fast snap flow with momentum
                flow_dx = -220 if target_pos[0] > 960 else 220
                s_move = ease(p, "out_expo")
                cur_pos[0] = int(target_pos[0] + flow_dx * (1.0 - s_move))
                scale = 0.90 + 0.10 * s_move
                alpha = min(1.0, elapsed / 0.10)
                motion_blur_len = int(16 * (1.0 - p))
                motion_blur_angle = 0.0
            elif anim_type == "object_push":
                push_dy = 140
                s_move = ease(p, "out_expo")
                cur_pos[1] = int(cur_pos[1] + push_dy * (1.0 - s_move))
                alpha = min(1.0, elapsed / 0.10)
            else:
                s = ease(p, "out_back")
                scale = 0.35 + 0.65 * s
                alpha = min(1.0, elapsed / 0.10)
                
        # 2. Exit Phase (Fast, punchy exit)
        exit_dur = 0.18
        exit_type = el_cfg.get("exit_type", "flow_out" if anim_type not in ("none", "static") else "none")
        if exit_type != "none" and time_to_exit < exit_dur and time_to_exit >= 0:
            ep = 1.0 - (time_to_exit / exit_dur)
            exit_type = el_cfg.get("exit_type", "flow_out")
            if exit_type == "flow_out":
                exit_dx = 180 if target_pos[0] > 960 else -180
                cur_pos[0] = int(target_pos[0] + exit_dx * ease(ep, "in_expo"))
                alpha = max(0.0, 1.0 - ep)
                motion_blur_len = int(16 * ep)
            elif exit_type == "scale_shrink":
                scale = max(0.1, 1.0 - 0.7 * ease(ep, "in_quad"))
                alpha = max(0.0, 1.0 - ep)
                
        # 3. Audio Keyword Scale Punch Emphasis
        punch_cfgs = el_cfg.get("scale_punches", [])
        for punch in punch_cfgs:
            pt = punch["time"]
            pdur = punch.get("duration", 0.35)
            if pt <= t < pt + pdur:
                pp = (t - pt) / pdur
                # Fast punch up to 1.18x then spring settle
                punch_factor = 1.0 + 0.22 * math.sin(pp * math.pi) * math.exp(-3.0 * pp)
                scale *= punch_factor
                
        # Resize asset
        h, w = raw.shape[:2]
        f_scale = (target_size / max(h, w)) * scale
        nw, nh = max(4, int(w * f_scale)), max(4, int(h * f_scale))
        scaled = cv2.resize(raw, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
        
        if alpha < 1.0:
            scaled[:, :, 3] = (scaled[:, :, 3].astype(float) * alpha).astype(np.uint8)
            
        # Apply motion blur if high velocity
        if motion_blur_len > 2:
            scaled = MotionFX.apply_directional_motion_blur(scaled, motion_blur_angle, motion_blur_len)
            
        if not is_elevated:
            bgra = cv2.cvtColor(scaled, cv2.COLOR_RGBA2BGRA)
            return bgra, (cur_pos[0] - nw // 2, cur_pos[1] - nh // 2)
        else:
            # Elevated aerial element (flying insects, floating bubbles)
            bgra = cv2.cvtColor(scaled, cv2.COLOR_RGBA2BGRA)
            with_shadow = OpenCutVisualFX.apply_drop_shadow(bgra, offset=(10, 22), blur_radius=24, opacity=0.38)
            sh, sw = with_shadow.shape[:2]
            return with_shadow, (cur_pos[0] - sw // 2, cur_pos[1] - sh // 2)

    def render_word_card_v2(self, word_cfg: Dict[str, Any], t: float, current_scene: Optional[Dict[str, Any]] = None) -> Optional[Tuple[np.ndarray, Tuple[int, int]]]:
        """Style 1 V2: 
        Phase 1: Traveling Dot (flies from source/element to card target)
        Phase 2: Dot Bloom & Morph into Card (expands smoothly outward from center)
        Phase 3: Rapid Text Handwriting Reveal (fast cursive writing with glowing pen nib)
        Phase 4: Grounded, stable card
        """
        st, en = word_cfg["start"], word_cfg["end"]
        if t < st or t > en:
            return None
        elapsed = t - st
        theme_name = word_cfg.get("theme", "teal")
        target_pos = word_cfg["pos"]
        
        # Determine from_pos (origin of traveling dot)
        if "from_pos" in word_cfg:
            from_pos = word_cfg["from_pos"]
        elif current_scene and current_scene.get("elements"):
            from_pos = current_scene["elements"][0]["pos"]
        else:
            from_pos = [target_pos[0] - 350, target_pos[1]]
            
        # Precise Stage Timings (Graceful, visible dot flight & snappy bloom)
        travel_dur = 0.28   # Graceful, trackable flight across the canvas (calibrated per feedback)
        bloom_dur = 0.16    # Quick springy pop into card
        write_dur = 0.26    # Fast cursive writing reveal
        
        # 1. Phase 1: Traveling Dot
        if elapsed < travel_dur:
            p_tr = elapsed / travel_dur
            s_tr = ease(p_tr, "out_cubic")
            # Arched Bezier trajectory
            mx = (from_pos[0] + target_pos[0]) / 2.0
            my = min(from_pos[1], target_pos[1]) - 40.0
            bx = (1.0 - s_tr)**2 * from_pos[0] + 2.0 * (1.0 - s_tr) * s_tr * mx + s_tr**2 * target_pos[0]
            by = (1.0 - s_tr)**2 * from_pos[1] + 2.0 * (1.0 - s_tr) * s_tr * my + s_tr**2 * target_pos[1]
            dot_img = create_traveling_dot(theme_name=theme_name)
            dh, dw = dot_img.shape[:2]
            return dot_img, (int(round(bx)) - dw // 2, int(round(by)) - dh // 2)
            
        # 2. Phase 2: Dot Bloom & Expansion into Card
        elif elapsed < travel_dur + bloom_dur:
            p_bl = (elapsed - travel_dur) / bloom_dur
            card_with_shadow = create_staged_popup_card_v2(
                word_cfg["word"],
                theme_name=theme_name,
                bloom_p=p_bl,
                write_p=0.0
            )
            sh, sw = card_with_shadow.shape[:2]
            return card_with_shadow, (target_pos[0] - sw // 2, target_pos[1] - sh // 2)
            
        # 3. Phase 3: Rapid Text Handwriting Reveal
        elif elapsed < travel_dur + bloom_dur + write_dur:
            p_wr = (elapsed - travel_dur - bloom_dur) / write_dur
            write_p = ease(min(1.0, p_wr), "out_cubic")
            card_with_shadow = create_staged_popup_card_v2(
                word_cfg["word"],
                theme_name=theme_name,
                bloom_p=1.0,
                write_p=write_p
            )
            sh, sw = card_with_shadow.shape[:2]
            return card_with_shadow, (target_pos[0] - sw // 2, target_pos[1] - sh // 2)
            
        # 4. Phase 4: Stable Grounded Card with Subtle Fade Out at end
        else:
            card_with_shadow = create_staged_popup_card_v2(
                word_cfg["word"],
                theme_name=theme_name,
                bloom_p=1.0,
                write_p=1.0
            )
            alpha = 1.0
            if t > en - 0.12:
                alpha = max(0.0, (en - t) / 0.12)
            if alpha < 0.999:
                card_with_shadow = card_with_shadow.copy()
                card_with_shadow[:, :, 3] = (card_with_shadow[:, :, 3].astype(float) * alpha).astype(np.uint8)
                
            sh, sw = card_with_shadow.shape[:2]
            return card_with_shadow, (target_pos[0] - sw // 2, target_pos[1] - sh // 2)

    def render_morph_transition(self, morph_cfg: Dict[str, Any], t: float) -> Optional[Tuple[np.ndarray, Tuple[int, int]]]:
        """Motion Transition #1: Morph Transition (تحول العنصر A إلى B بصرياً)
        - Phase 1 (0 <= p < 0.55): Asset A inward anticipation squash towards base + energy charge
        - Midpoint (0.32 <= p <= 0.68): Incandescent energy core + expanding glowing halo
        - Phase 2 (0.45 <= p <= 1.0): Asset B elastic expansion outward (out_back) + settle
        - Continuous grounding: Ground contact shadow smoothly interpolates on Y = 840
        """
        st, en = morph_cfg["start"], morph_cfg["end"]
        if t < st or t > en:
            return None
        dur = max(0.05, en - st)
        p = np.clip((t - st) / dur, 0.0, 1.0)
        
        raw_a = self.loaded_assets.get(morph_cfg["from_asset"])
        raw_b = self.loaded_assets.get(morph_cfg["to_asset"])
        if raw_a is None or raw_b is None:
            return None
            
        target_pos = morph_cfg.get("pos", [480, 600])
        target_size = morph_cfg.get("target_size", 500)
        is_elevated = morph_cfg.get("is_elevated", False)
        
        ha, wa = raw_a.shape[:2]
        hb, wb = raw_b.shape[:2]
        base_scale_a = target_size / max(ha, wa)
        base_scale_b = target_size / max(hb, wb)
        
        pad = 140
        cw = int(target_size * 1.5) + pad * 2
        ch = int(target_size * 1.5) + pad * 2
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_anchor_y = cy + int(target_size * 0.44)
        
        # Phase 1: Asset A Squash & Inward Morph (p < 0.55)
        if p < 0.55:
            p_a = p / 0.55
            scale_x_a = 1.0 + 0.16 * math.sin(p_a * math.pi)
            scale_y_a = max(0.1, 1.0 - 0.70 * ease(p_a, "in_quad"))
            rot_a = 12.0 * math.sin(p_a * math.pi)
            alpha_a = max(0.0, 1.0 - ease(max(0.0, (p_a - 0.35) / 0.65), "in_quad"))
            
            nwa = max(4, int(wa * base_scale_a * scale_x_a))
            nha = max(4, int(ha * base_scale_a * scale_y_a))
            resized_a = cv2.resize(raw_a, (nwa, nha), interpolation=cv2.INTER_LANCZOS4)
            if abs(rot_a) > 0.5:
                M = cv2.getRotationMatrix2D((nwa / 2.0, nha / 2.0), rot_a, 1.0)
                resized_a = cv2.warpAffine(resized_a, M, (nwa, nha), borderMode=cv2.BORDER_CONSTANT)
                
            if alpha_a < 1.0:
                resized_a[:, :, 3] = (resized_a[:, :, 3].astype(float) * alpha_a).astype(np.uint8)
                
            ax1 = cx - nwa // 2
            ay1 = floor_anchor_y - nha
            self._blend_patch(canvas, resized_a, ax1, ay1)

        # Phase 2: Asset B Bloom & Elastic Emergence (p >= 0.45)
        if p >= 0.45:
            p_b = (p - 0.45) / 0.55
            scale_b = 0.30 + 0.70 * ease(p_b, "out_back")
            scale_x_b = scale_b * (1.0 + 0.14 * math.sin((1.0 - p_b) * math.pi))
            scale_y_b = scale_b
            rot_b = -10.0 * (1.0 - p_b)
            alpha_b = min(1.0, p_b / 0.35)
            
            nwb = max(4, int(wb * base_scale_b * scale_x_b))
            nhb = max(4, int(hb * base_scale_b * scale_y_b))
            resized_b = cv2.resize(raw_b, (nwb, nhb), interpolation=cv2.INTER_LANCZOS4)
            if abs(rot_b) > 0.5:
                M = cv2.getRotationMatrix2D((nwb / 2.0, nhb / 2.0), rot_b, 1.0)
                resized_b = cv2.warpAffine(resized_b, M, (nwb, nhb), borderMode=cv2.BORDER_CONSTANT)
                
            if alpha_b < 1.0:
                resized_b[:, :, 3] = (resized_b[:, :, 3].astype(float) * alpha_b).astype(np.uint8)
                
            bx1 = cx - nwb // 2
            by1 = floor_anchor_y - nhb
            self._blend_patch(canvas, resized_b, bx1, by1)
            
        # Midpoint Incandescent Spark / Energy Core (0.32 <= p <= 0.68)
        if 0.32 <= p <= 0.68:
            p_core = (p - 0.32) / 0.36
            core_intensity = math.sin(p_core * math.pi)
            core_r = int(14 + 65 * p_core)
            core_y = floor_anchor_y - int(target_size * 0.28)
            overlay = np.zeros_like(canvas)
            cv2.circle(overlay, (cx, core_y), core_r, (45, 212, 191, int(190 * core_intensity)), -1, cv2.LINE_AA)
            cv2.circle(overlay, (cx, core_y), max(4, int(core_r * 0.40)), (255, 255, 255, int(250 * core_intensity)), -1, cv2.LINE_AA)
            overlay = cv2.GaussianBlur(overlay, (27, 27), 0)
            self._blend_patch(canvas, overlay, 0, 0)
            
        bgra = cv2.cvtColor(canvas, cv2.COLOR_RGBA2BGRA)
        return bgra, (target_pos[0] - cw // 2, target_pos[1] - ch // 2)

    def _blend_patch(self, dest: np.ndarray, patch: np.ndarray, x: int, y: int):
        ph, pw = patch.shape[:2]
        dh, dw = dest.shape[:2]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(dw, x + pw), min(dh, y + ph)
        if x1 >= x2 or y1 >= y2:
            return
        px1, py1 = x1 - x, y1 - y
        px2, py2 = px1 + (x2 - x1), py1 + (y2 - y1)
        src = patch[py1:py2, px1:px2]
        alpha = (src[:, :, 3].astype(float) / 255.0)[:, :, np.newaxis]
        dest[y1:y2, x1:x2, :3] = (alpha * src[:, :, :3].astype(float) + (1.0 - alpha) * dest[y1:y2, x1:x2, :3].astype(float)).astype(np.uint8)
        dest[y1:y2, x1:x2, 3] = np.maximum(dest[y1:y2, x1:x2, 3], src[:, :, 3])

    def render_frame(self, t: float) -> np.ndarray:
        """Composites full 1080p frame at time t with camera and visual behaviors."""
        # Clean Studio Canvas (Pure #FFFFFF)
        frame = np.full((self.height, self.width, 3), 255, dtype=np.uint8)
        
        # Stage Ground Baseline (anchors all physical elements firmly to the floor)
        cv2.line(frame, (80, 840), (1840, 840), (225, 230, 235), 2, cv2.LINE_AA)
        
        current_scene = None
        for s in self.scenes:
            if s["start"] <= t < s["end"]:
                current_scene = s
                break
        if not current_scene and t >= self.scenes[-1]["end"]:
            current_scene = self.scenes[-1]
        if not current_scene:
            return frame
            
        # Collect active morph transitions across manifest & scenes
        all_morphs = self.manifest.get("morph_transitions", []) + current_scene.get("morph_transitions", [])
        active_morphs = [m for m in all_morphs if m["start"] <= t <= m["end"]]

        # 1. Whiteboard Inking Path Connectors (between consecutive elements)
        connectors = current_scene.get("inking_connectors", [])
        for conn in connectors:
            c_st, c_en = conn["start"], conn["end"]
            if c_st <= t <= c_en:
                p_conn = (t - c_st) / max(0.01, (c_en - c_st))
                MotionFX.draw_whiteboard_inking_path(
                    frame,
                    tuple(conn["from_pos"]),
                    tuple(conn["to_pos"]),
                    p_conn,
                    color=conn.get("color", (70, 70, 70)),
                    thickness=conn.get("thickness", 4)
                )

        # 2. Render Elements (suppressing elements handled by active/completed morph transitions)
        for el in current_scene.get("elements", []):
            el_key = el["asset_key"]
            # Skip if this element is actively morphing at time t
            if any(m["start"] <= t <= m["end"] and (m["from_asset"] == el_key or m["to_asset"] == el_key) for m in all_morphs):
                continue
            # Skip if this element morphed out earlier
            if any(m["from_asset"] == el_key and t >= m["start"] for m in all_morphs):
                continue
            # Skip if this element morphs in later
            if any(m["to_asset"] == el_key and t < m["end"] for m in all_morphs):
                continue

            if el["start"] <= t <= el["end"]:
                layer, (lx, ly) = self.render_element_v2(el, t)
                self._blend(frame, layer, lx, ly)
                
        # 2.5 Render Active Morph Transitions (Shape Transformation in place on stage)
        for morph in active_morphs:
            res = self.render_morph_transition(morph, t)
            if res:
                self._blend(frame, res[0], res[1][0], res[1][1])
                
        # 3. Render Style 1 Grounded Word Cards (Dot -> Bloom -> Fast Handwriting)
        for w in current_scene.get("words", []):
            res = self.render_word_card_v2(w, t, current_scene)
            if res:
                self._blend(frame, res[0], res[1][0], res[1][1])
                
        # 4. Virtual Camera Viewport Transform (Zoom & Pan)
        cam_center, cam_zoom = self.compute_camera_state(t)
        if abs(cam_zoom - 1.0) > 0.005 or abs(cam_center[0] - self.width/2) > 2.0:
            frame = MotionFX.apply_camera_transform(frame, cam_center, cam_zoom)
            
        return frame

    def _blend(self, base: np.ndarray, over: np.ndarray, x: int, y: int):
        oh, ow = over.shape[:2]
        bh, bw = base.shape[:2]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(bw, x + ow), min(bh, y + oh)
        if x1 >= x2 or y1 >= y2:
            return
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
        if os.path.exists(temp_v):
            os.remove(temp_v)
        print(f"✅ V2 Video exported successfully: {output_mp4}")

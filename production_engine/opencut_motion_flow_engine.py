"""OpenCut Motion Flow Engine.

Implements the user's vision:
1. Smooth storyboard fade-out via feathered split wipe mask.
2. Organic element flow with OpenCut Bezier easing (ease_out_back / flow).
3. Professional drop shadows & ambient glow.
4. Kinetic typing typography using the Cairo Arabic font in sleek glassmorphism cards.
5. Perfect synchronization with audio and SRT sentence timing.
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
from typing import Dict, List, Any, Tuple, Optional

# Path setup
ROOT_DIR = str(Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.opencut_fx import (
    ease,
    OpenCutMaskEngine,
    OpenCutVisualFX,
    OpenCutShapeRenderer,
    OpenCutKineticText,
    DEFAULT_CAIRO_FONT,
)

# Resolution & Frame rate
WIDTH = 1920
HEIGHT = 1080
FPS = 30


class OpenCutMotionFlowEngine:
    def __init__(
        self,
        storyboard_path: str,
        audio_path: str,
        sentences_srt_path: str,
        assets_metadata_path: str,
        assets_dir: str,
        output_mp4_path: str,
        width: int = WIDTH,
        height: int = HEIGHT,
        fps: int = FPS,
    ):
        self.storyboard_path = storyboard_path
        self.audio_path = audio_path
        self.sentences_srt_path = sentences_srt_path
        self.assets_metadata_path = assets_metadata_path
        self.assets_dir = assets_dir
        self.output_mp4_path = Path(output_mp4_path)
        self.width = width
        self.height = height
        self.fps = fps

        # Initialize Typography
        self.kinetic_text = OpenCutKineticText(DEFAULT_CAIRO_FONT)

        # Load Storyboard Image
        self.storyboard_img = None
        if os.path.exists(storyboard_path):
            raw = cv2.imdecode(np.fromfile(storyboard_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if raw is not None:
                self.storyboard_img = cv2.resize(raw, (self.width, self.height), interpolation=cv2.INTER_AREA)

        # Load Sentences from SRT
        self.sentences = self._load_srt(sentences_srt_path)

        # Load Assets Metadata & Pre-load images
        self.asset_defs = self._load_assets(assets_metadata_path, assets_dir)

        # Determine total duration from audio or last sentence
        self.duration_sec = self._get_duration()
        self.total_frames = int(round(self.duration_sec * self.fps))

    def _load_srt(self, srt_path: str) -> List[Dict[str, Any]]:
        """Parses SRT subtitle entries with precise start/end in seconds."""
        if not os.path.exists(srt_path):
            return []
        entries = []
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = content.strip().split("\n\n")
        for b in blocks:
            lines = [l.strip() for l in b.split("\n") if l.strip()]
            if len(lines) >= 3:
                time_line = lines[1]
                text = " ".join(lines[2:])
                if "-->" in time_line:
                    t_start_str, t_end_str = [t.strip() for t in time_line.split("-->")]
                    s_sec = self._parse_srt_timestamp(t_start_str)
                    e_sec = self._parse_srt_timestamp(t_end_str)
                    entries.append({"start": s_sec, "end": e_sec, "text": text})
        return entries

    @staticmethod
    def _parse_srt_timestamp(ts: str) -> float:
        parts = ts.replace(",", ".").split(":")
        h = float(parts[0])
        m = float(parts[1])
        s = float(parts[2])
        return h * 3600.0 + m * 60.0 + s

    def _load_assets(self, metadata_path: str, assets_dir: str) -> List[Dict[str, Any]]:
        if not os.path.exists(metadata_path):
            return []
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_assets = data.get("primary_assets", {})
        loaded = []

        for asset_id, item in raw_assets.items():
            fname = item.get("filename", "")
            fpath = os.path.join(assets_dir, fname)
            img_bgra = None
            if os.path.exists(fpath):
                raw = cv2.imdecode(np.fromfile(fpath, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                if raw is not None:
                    # Apply soft drop shadow to the sprite for 3D depth
                    img_bgra = OpenCutVisualFX.apply_drop_shadow(raw, offset=(6, 12), blur_radius=14, opacity=0.35)

            timing = item.get("anchor_timing", [0.0, 5.0])
            bbox = item.get("global_bbox", [100, 100, 200, 200])

            loaded.append({
                "id": asset_id,
                "title": item.get("title", ""),
                "start": float(timing[0]),
                "end": float(timing[1]),
                "recommended_anim": item.get("recommended_anim", "ease_out_back"),
                "img": img_bgra,
                "orig_bbox": bbox,
            })

        # Sort assets by start time
        loaded.sort(key=lambda x: x["start"])
        return loaded

    def _get_duration(self) -> float:
        """Gets exact duration from audio file using ffprobe, or fallback to sentences."""
        if os.path.exists(self.audio_path):
            cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", self.audio_path
            ]
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                return float(res.stdout.strip())
            except Exception:
                pass
        if self.sentences:
            return self.sentences[-1]["end"] + 1.5
        return 30.0

    def render_frame(self, t: float) -> np.ndarray:
        """Renders a single frame at timestamp t with full OpenCut aesthetic compositing."""
        # 1. Base Whiteboard Canvas (Ultra-clean off-white gradient for eye comfort)
        canvas = np.full((self.height, self.width, 3), 252, dtype=np.uint8)

        # Subtle vignette / ambient shading on corners
        # 2. Storyboard Wipe Transition (Vanishes over [0.8s, 2.4s])
        storyboard_show_duration = 0.8
        storyboard_wipe_duration = 1.4

        if self.storyboard_img is not None and t < (storyboard_show_duration + storyboard_wipe_duration):
            if t <= storyboard_show_duration:
                # Fully visible storyboard
                canvas = self.storyboard_img.copy()
            else:
                # Wiping out with feathered split wipe
                wipe_prog = (t - storyboard_show_duration) / storyboard_wipe_duration
                eased_wipe = ease(wipe_prog, "ease_out_cubic")
                # Mask where 1.0 is canvas, 0.0 is storyboard
                mask = OpenCutMaskEngine.split_wipe_mask(
                    self.width, self.height, eased_wipe, angle_deg=25.0, feather_px=65, invert=False
                )
                m3 = np.dstack([mask, mask, mask])
                canvas = (canvas.astype(np.float32) * m3 + self.storyboard_img.astype(np.float32) * (1.0 - m3)).astype(np.uint8)

        # 3. Dynamic Elements Flow
        # Filter assets active or persistent around timestamp t
        for asset in self.asset_defs:
            t_start = asset["start"]
            # Allow asset to appear slightly before voice cue for anticipation
            t_intro = max(0.0, t_start - 0.25)
            if t < t_intro:
                continue

            # Elements remain visible once introduced until end of section
            age = t - t_intro
            entrance_dur = 0.8
            p_raw = min(1.0, age / entrance_dur)
            p_eased = ease(p_raw, "ease_out_back")

            img = asset["img"]
            if img is None:
                continue

            ah, aw = img.shape[:2]
            orig_bbox = asset["orig_bbox"]  # [x, y, w, h] in original storyboard coordinate

            # Normalized target position
            # Storyboard original resolution is ~1280x720 or similar; map to 1920x1080
            # Center of element in canvas
            center_x = (orig_bbox[0] + orig_bbox[2] / 2.0) * (self.width / 1280.0)
            center_y = (orig_bbox[1] + orig_bbox[3] / 2.0) * (self.height / 720.0)

            # Eased Scale & Flow
            scale = 0.3 + 0.7 * p_eased
            alpha_fade = min(1.0, age / 0.35)

            # Slight subtle breathing / floating animation after entrance
            if age > entrance_dur:
                breath = math.sin((age - entrance_dur) * 2.2) * 4.0
                center_y += breath

            # Target bounds
            cur_w = max(4, int(round(aw * scale)))
            cur_h = max(4, int(round(ah * scale)))
            pos_x = int(round(center_x - cur_w / 2.0))
            pos_y = int(round(center_y - cur_h / 2.0))

            resized = cv2.resize(img, (cur_w, cur_h), interpolation=cv2.INTER_AREA)

            # Alpha composite onto canvas
            self._composite_sprite(canvas, resized, pos_x, pos_y, alpha_mult=alpha_fade)

        # 4. Kinetic Typography (Sentence-by-Sentence with Cairo Font)
        current_sentence = None
        for s in self.sentences:
            if s["start"] <= t <= (s["end"] + 0.3):
                current_sentence = s
                break

        if current_sentence is not None:
            s_start = current_sentence["start"]
            s_end = current_sentence["end"]
            s_dur = max(0.5, s_end - s_start)
            s_age = t - s_start

            # Typing completes over 65% of the sentence, then holds
            type_dur = s_dur * 0.75
            typing_prog = min(1.0, s_age / type_dur)

            # Render typing badge with Cairo font
            badge_bgra = self.kinetic_text.render_typing_badge(
                full_text=current_sentence["text"],
                typing_progress=typing_prog,
                font_size=42,
                text_color=(20, 28, 48),
                accent_color=(0, 160, 245),
                show_cursor=True,
                cursor_blink=True,
                show_card_backdrop=True,
            )

            # Position badge at lower-center
            bw, bh = badge_bgra.shape[1], badge_bgra.shape[0]
            bx = (self.width - bw) // 2
            by = self.height - bh - 60

            # Subtle entrance bounce for the card
            card_intro_p = ease(min(1.0, s_age / 0.4), "ease_out_cubic")
            if card_intro_p < 1.0:
                by = int(round(by + (1.0 - card_intro_p) * 40))

            self._composite_sprite(canvas, badge_bgra, bx, by, alpha_mult=min(1.0, s_age / 0.2))

        return canvas

    @staticmethod
    def _composite_sprite(
        canvas: np.ndarray,
        sprite_bgra: np.ndarray,
        x: int,
        y: int,
        alpha_mult: float = 1.0,
    ) -> None:
        """High-performance alpha-blending with canvas boundaries clipping."""
        if sprite_bgra is None or sprite_bgra.size == 0 or alpha_mult <= 0.0:
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

        src_crop = sprite_bgra[sy1:sy2, sx1:sx2]
        dst_crop = canvas[y1:y2, x1:x2]

        src_alpha = (src_crop[:, :, 3].astype(np.float32) / 255.0) * float(np.clip(alpha_mult, 0.0, 1.0))
        src_rgb = src_crop[:, :, :3].astype(np.float32)
        dst_rgb = dst_crop.astype(np.float32)

        alpha_3d = np.dstack([src_alpha, src_alpha, src_alpha])
        blended = src_rgb * alpha_3d + dst_rgb * (1.0 - alpha_3d)

        canvas[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)

    def render_full_video(self, limit_seconds: Optional[float] = None) -> str:
        """Pipes rendered frames to FFmpeg and multiplexes synchronized master audio."""
        self.output_mp4_path.parent.mkdir(parents=True, exist_ok=True)
        temp_video = self.output_mp4_path.parent / "temp_video_track.mp4"

        render_duration = self.duration_sec if limit_seconds is None else min(limit_seconds, self.duration_sec)
        frames_to_render = int(round(render_duration * self.fps))

        print("==================================================")
        print("Starting OpenCut Motion Flow Render:")
        print(f"   Resolution: {self.width}x{self.height} @ {self.fps} FPS")
        print(f"   Duration: {render_duration:.2f}s ({frames_to_render} frames)")
        print(f"   Output: {self.output_mp4_path}")
        print("==================================================")

        # Video encoding command
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}", "-pix_fmt", "bgr24", "-r", str(self.fps),
            "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", str(temp_video)
        ]

        pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        t0 = time.time()

        for f_idx in range(frames_to_render):
            t = f_idx / float(self.fps)
            frame = self.render_frame(t)
            pipe.stdin.write(frame.tobytes())

            if (f_idx + 1) % 60 == 0 or (f_idx + 1) == frames_to_render:
                elapsed = time.time() - t0
                fps_rate = (f_idx + 1) / max(0.001, elapsed)
                pct = (f_idx + 1) / float(frames_to_render) * 100.0
                print(f"   Rendered {f_idx + 1}/{frames_to_render} ({pct:.1f}%) [{fps_rate:.1f} FPS, Time: {t:.2f}s]")

        pipe.stdin.close()
        pipe.wait()

        # Mux master audio
        print("[AUDIO] Muxing synchronized audio...")
        mux_cmd = [
            "ffmpeg", "-y",
            "-i", str(temp_video),
            "-i", self.audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(render_duration),
            "-shortest",
            str(self.output_mp4_path),
        ]
        subprocess.run(mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        if temp_video.exists():
            try:
                temp_video.unlink()
            except Exception:
                pass

        total_time = time.time() - t0
        print(f"[DONE] Render Completed successfully in {total_time:.1f}s!")
        print(f"   Saved to: {self.output_mp4_path}")
        return str(self.output_mp4_path)

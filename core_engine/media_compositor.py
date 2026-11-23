#!/usr/bin/env python3
"""Media Compositor Engine: Micro-Retention GIF Overlays & Clean Narration Integration.

STRICT ZERO-BGM MANDATE:
Whiteboard explainer style mandates 100% clean voice narration.
Musical background tracks (BGM) are strictly prohibited across all productions.
This preserves utmost clarity, eliminates distraction, and maximizes viewer retention.

Features:
1. Pure Pristine Voice Narration (Zero-BGM Policy).
2. Micro-Retention GIF Overlays:
   - Chroma-keyed transparent GIF overlays placed in upper negative space.
   - Strict Anti-Freeze execution: uses eof_action=pass and eliminates shortest=1 inside overlay.
   - Exact audio duration clamping via ffprobe down to milliseconds (-t exact_audio_dur).
3. Clean Pre-Cut Sweeps:
   - Elements and overlays fade out at least 0.35s before the scene cut.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

# Safe UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
GIFS_DIR = ROOT_DIR / "assets" / "gifs"
MEDIA_LIB_PATH = ROOT_DIR / "assets" / "media_library.json"

# Strict policy flag: BGM is completely banned
ZERO_BGM_POLICY = True


def get_audio_duration_seconds(audio_path: Path) -> float:
    """Probes exact audio duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def get_video_duration_seconds(video_path: Path) -> float:
    """Probes exact video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


class MediaCompositor:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = Path(root_dir or ROOT_DIR)
        self.gifs_dir = self.root_dir / "assets" / "gifs"
        self.media_lib = self._load_media_library()

    def _load_media_library(self) -> Dict[str, Any]:
        if MEDIA_LIB_PATH.exists():
            try:
                return json.loads(MEDIA_LIB_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"gifs": []}

    def process_clean_voice(self, voice_wav: Path, output_wav: Path) -> Path:
        """Processes voice track ensuring 100% clean narration with ZERO BGM."""
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        exact_dur = get_audio_duration_seconds(voice_wav)
        print(f"[🛡️ ZERO-BGM POLICY] Keeping pure narration voice track: {output_wav.name} ({exact_dur:.2f}s)")
        if voice_wav.resolve() != output_wav.resolve():
            shutil.copyfile(voice_wav, output_wav)
        return output_wav

    def composite_gif_overlays(
        self,
        base_video_path: Path,
        clean_audio_path: Path,
        output_video_path: Path,
        overlays: List[Dict[str, Any]]
    ) -> Path:
        """Overlays micro-retention transparent GIFs onto the rendered whiteboard video
        and muxes with the clean voice track (NO BGM).
        
        Strict Anti-Freeze Directives:
        1. Uses eof_action=pass on all overlay filters.
        2. NEVER uses shortest=1 inside the overlay filter.
        3. Probes exact audio duration and sets -t {exact_audio_dur:.3f} on the output.
        """
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
        exact_audio_dur = get_audio_duration_seconds(clean_audio_path)

        # Build FFmpeg command
        cmd = ["ffmpeg", "-y", "-i", str(base_video_path)]
        valid_overlays = []

        # Add GIF inputs
        for ov in overlays:
            gif_filename = ov.get("gif", "")
            gif_file = self.gifs_dir / gif_filename
            if not gif_file.exists():
                matches = list(self.gifs_dir.glob(f"*{gif_filename}*"))
                if matches:
                    gif_file = matches[0]
            if gif_file.exists():
                cmd.extend(["-ignore_loop", "0", "-i", str(gif_file)])
                valid_overlays.append((gif_file, ov))
            else:
                print(f"[-] Warning: GIF asset not found: {gif_filename}")

        # Add clean audio input
        audio_input_idx = len(valid_overlays) + 1
        cmd.extend(["-i", str(clean_audio_path)])

        if not valid_overlays:
            # No overlays: simply remux video with clean audio clamped to exact duration
            cmd = [
                "ffmpeg", "-y",
                "-i", str(base_video_path),
                "-i", str(clean_audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                "-t", f"{exact_audio_dur:.3f}",
                str(output_video_path)
            ]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"[+] Muxed clean video without overlays clamped to {exact_audio_dur:.2f}s")
            return output_video_path

        # Construct complex filter
        filter_parts = []
        for idx, (g_path, ov) in enumerate(valid_overlays, start=1):
            scale_w = ov.get("scale_w", 180)
            filter_parts.append(f"[{idx}:v]scale={scale_w}:-1[g{idx}]")

        current_layer = "0:v"
        for idx, (g_path, ov) in enumerate(valid_overlays, start=1):
            next_layer = f"v{idx}" if idx < len(valid_overlays) else "vout"
            px, py = ov.get("pos", [960, 340])
            st = ov.get("start", 0.0)
            en = ov.get("end", st + 5.0)
            # Make sure en does not exceed exact_audio_dur - 0.35
            en = min(en, max(st + 1.0, exact_audio_dur - 0.35))
            
            # CRITICAL: eof_action=pass, NO shortest=1 inside overlay
            filter_parts.append(
                f"[{current_layer}][g{idx}]overlay={px}:{py}:eof_action=pass:enable='between(t,{st:.2f},{en:.2f})'[{next_layer}]"
            )
            current_layer = next_layer

        filter_complex_str = "; ".join(filter_parts)

        cmd.extend([
            "-filter_complex", filter_complex_str,
            "-map", "[vout]", "-map", f"{audio_input_idx}:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "256k",
            "-t", f"{exact_audio_dur:.3f}",
            str(output_video_path)
        ])

        print(f"[*] Running FFmpeg media composite: {len(valid_overlays)} overlays, clamp={exact_audio_dur:.2f}s (Pure Voice, NO BGM)")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[!] FFmpeg overlay failed: {res.stderr[:300]}")
            # Fallback to direct remux
            remux_cmd = [
                "ffmpeg", "-y",
                "-i", str(base_video_path),
                "-i", str(clean_audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                "-t", f"{exact_audio_dur:.3f}",
                str(output_video_path)
            ]
            subprocess.run(remux_cmd, capture_output=True, text=True, check=True)
        else:
            final_dur = get_video_duration_seconds(output_video_path)
            print(f"[+] Output verified: {output_video_path.name} ({final_dur:.2f}s, diff={abs(final_dur - exact_audio_dur):.3f}s)")

        return output_video_path


def enhance_section(
    project_dir: Path,
    sec_id: str,
    custom_overlays: Optional[List[Dict[str, Any]]] = None
) -> Optional[Path]:
    """Enhances a rendered section with micro-retention GIFs and clean narration (NO BGM)."""
    sec_dir = project_dir / "sections" / sec_id
    exports_dir = project_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Locate base video (raw render in section dir or legacy v6)
    v6_video = sec_dir / f"{sec_id}_raw_render.mp4"
    if not v6_video.exists():
        v6_video = exports_dir / f"{sec_id}_master_v6.mp4"
    if not v6_video.exists():
        v6_video = exports_dir / f"{sec_id}_master.mp4"
    if not v6_video.exists():
        v6_video = sec_dir / "final_whiteboard_1080p.mp4"
    if not v6_video.exists():
        print(f"[-] Base video not found for {sec_id} in {sec_dir} or {exports_dir}")
        return None

    # 2. Locate clean voice track & ensure synchronized Motion SFX are mixed (Zero BGM, 100% Motion SFX)
    raw_voice_wav = sec_dir / "voice" / f"{sec_id}.wav"
    if not raw_voice_wav.exists():
        raw_voice_wav = sec_dir / "voice" / "section.wav"
    if not raw_voice_wav.exists():
        print(f"[-] Voice track not found for {sec_id}")
        return None

    manifest_file = sec_dir / "manifest.json"
    m_data: Dict[str, Any] = {}
    if manifest_file.exists():
        try:
            m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    sfx_voice_wav = sec_dir / "voice" / f"{sec_id}_master_sfx.wav"
    if m_data and m_data.get("enable_sfx", True):
        try:
            from core_engine.sfx_director import SFXDirector
            sfx_dir = SFXDirector()
            sfx_dir.create_synchronized_audio(m_data, raw_voice_wav, sfx_voice_wav)
        except Exception as e:
            print(f"[!] SFX mix notice in enhance_section: {e}")

    voice_wav = sfx_voice_wav if sfx_voice_wav.exists() else raw_voice_wav

    # 3. Read manifest overlays
    manifest_overlays = m_data.get("overlays", [])
    selected_overlays = custom_overlays or manifest_overlays

    compositor = MediaCompositor()
    clean_audio_wav = sec_dir / "voice" / f"{sec_id}_clean_voice_master.wav"
    compositor.process_clean_voice(voice_wav, clean_audio_wav)

    out_master_v7 = exports_dir / f"{sec_id}_master_v7.mp4"
    compositor.composite_gif_overlays(v6_video, clean_audio_wav, out_master_v7, selected_overlays)

    # Clean up temporary raw render or legacy v6 so ONLY v7 remains in exports
    if out_master_v7.exists():
        raw_temp = sec_dir / f"{sec_id}_raw_render.mp4"
        legacy_v6 = exports_dir / f"{sec_id}_master_v6.mp4"
        for tmp_vid in (raw_temp, legacy_v6):
            if tmp_vid.exists():
                try:
                    tmp_vid.unlink()
                except Exception:
                    pass

    return out_master_v7

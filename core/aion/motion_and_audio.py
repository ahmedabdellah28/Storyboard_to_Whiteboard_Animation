"""Stages 8 & 9: Shared Motion Derivative Builder & RMS-Ducked SFX Audio Mixer.

Consolidated cleanly from golden production adapters so any project (Arabic/English)
reuses one canonical implementation with zero duplication.
"""
from __future__ import annotations

import json
import math
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import signal as scipy_signal

from core.aion.audio_mastering import MASTER_SAMPLE_RATE, resample_audio_hq

ROOT_DIR = Path(__file__).resolve().parents[2]
SFX_BASIC_DIR = ROOT_DIR / "assets" / "sfx"
SFX_PRO_DIR = ROOT_DIR / "creative_v3" / "studio_pro_sfx_and_audio_stems_v3"

CARD_STYLES: Dict[str, Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]] = {
    "warm": ((248, 244, 236, 248), (195, 184, 166, 255)),
    "dark_crimson": ((46, 22, 26, 248), (185, 75, 85, 255)),
    "arctic": ((24, 34, 52, 248), (95, 165, 220, 255)),
    "amber": ((42, 31, 22, 248), (215, 162, 72, 255)),
}


def build_soft_bottom_derivative(src_png: Path, out_png: Path, fade_frac: float = 0.14) -> Path:
    im = Image.open(src_png).convert("RGBA")
    arr = np.array(im, dtype=np.float32)
    h, _w = arr.shape[:2]
    fade_h = max(12, int(h * fade_frac))
    ramp = np.linspace(1.0, 0.0, fade_h, dtype=np.float32)[:, None]
    arr[h - fade_h:h, :, 3] *= ramp
    out_png.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(out_png)
    return out_png


def build_exhibit_card_derivative(
    src_png: Path,
    out_png: Path,
    card_bg: Tuple[int, int, int, int] = (248, 244, 236, 245),
    border_col: Tuple[int, int, int, int] = (195, 184, 166, 255),
    padding: int = 24,
    radius: int = 28,
) -> Path:
    im = Image.open(src_png).convert("RGBA")
    iw, ih = im.size
    cw, ch = iw + padding * 2, ih + padding + int(padding * 0.6)

    card = Image.new("RGBA", (cw + 24, ch + 28), (0, 0, 0, 0))
    shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([(12, 16), (12 + cw, 16 + ch)], radius=radius, fill=(20, 18, 15, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    card.alpha_composite(shadow)

    body = Image.new("RGBA", card.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    bd.rounded_rectangle([(12, 8), (12 + cw, 8 + ch)], radius=radius, fill=card_bg, outline=border_col, width=4)
    card.alpha_composite(body)

    card.alpha_composite(im, (12 + padding, 8 + ch - ih - 6))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    card.save(out_png)
    return out_png


def build_editorial_panel_matte(
    src_png: Path,
    out_png: Path,
    radius: int = 30,
) -> Path:
    """Rounds sharp rectangular comic/card panels, trims uniform white rims, and adds soft studio shadow."""
    im = Image.open(src_png).convert("RGBA")
    arr = np.array(im)
    h, w = arr.shape[:2]

    # Trim thin outer white/off-white scanner rim (up to 6px per side) when panel has solid corners
    if w > 40 and h > 40:
        is_rim = (arr[:, :, 3] > 200) & (arr[:, :, 0] > 236) & (arr[:, :, 1] > 236) & (arr[:, :, 2] > 236)
        top = 0
        while top < 6 and top < h - 20 and float(is_rim[top, :].mean()) > 0.85:
            top += 1
        bot = h
        while h - bot < 6 and bot - top > 20 and float(is_rim[bot - 1, :].mean()) > 0.85:
            bot -= 1
        left = 0
        while left < 6 and left < w - 20 and float(is_rim[top:bot, left].mean()) > 0.85:
            left += 1
        right = w
        while w - right < 6 and right - left > 20 and float(is_rim[top:bot, right - 1].mean()) > 0.85:
            right -= 1
        if (top, left, bot, right) != (0, 0, h, w):
            im = im.crop((left, top, right, bot))
            w, h = im.size

    eff_r = max(12, min(radius, min(w, h) // 7))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([(0, 0), (w - 1, h - 1)], radius=eff_r, fill=255)
    im.putalpha(mask)

    pad = 16
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2 + 6), (0, 0, 0, 0))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([(pad, pad + 6), (pad + w - 1, pad + 6 + h - 1)], radius=eff_r, fill=(8, 12, 20, 95))
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(im, (pad, pad))

    # Subtle 1.5px studio hairline border for crisp separation on both warm and dark stages
    bd = ImageDraw.Draw(canvas)
    bd.rounded_rectangle([(pad, pad), (pad + w - 1, pad + h - 1)], radius=eff_r, outline=(255, 255, 255, 42), width=2)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_png)
    return out_png


def _is_boxed_rectangular_panel(src_png: Path) -> bool:
    with Image.open(src_png) as im:
        rgba = im.convert("RGBA")
        arr = np.array(rgba)
    h, w = arr.shape[:2]
    if w < 48 or h < 48:
        return False
    ins_y, ins_x = max(2, int(h * 0.04)), max(2, int(w * 0.04))
    corners = [
        arr[ins_y, ins_x, 3],
        arr[ins_y, w - 1 - ins_x, 3],
        arr[h - 1 - ins_y, ins_x, 3],
        arr[h - 1 - ins_y, w - 1 - ins_x, 3],
    ]
    return sum(1 for a in corners if a > 190) >= 3


def prepare_asset_derivative(asset_cfg: Dict[str, Any], raw_assets_dir: Path, derived_dir: Path) -> Tuple[Path, int, int]:
    aid = asset_cfg["id"]
    src = raw_assets_dir / f"{aid}.png"
    if not src.exists():
        cand = raw_assets_dir / f"{aid}_composite.png"
        if cand.exists():
            src = cand
        else:
            raise FileNotFoundError(f"Asset PNG missing for {aid}: {src}")

    prep = asset_cfg.get("preprocess", [])
    final_path = src
    if "soft_bottom" in prep:
        out = derived_dir / f"{aid}_soft_bottom.png"
        final_path = build_soft_bottom_derivative(src, out, fade_frac=float(asset_cfg.get("fade_frac", 0.16)))
    elif "exhibit_card" in prep:
        style = asset_cfg.get("card_style", "warm")
        card_bg, border_col = CARD_STYLES.get(style, CARD_STYLES["warm"])
        out = derived_dir / f"{aid}_card_{style}.png"
        final_path = build_exhibit_card_derivative(src, out, card_bg=card_bg, border_col=border_col)
    elif _is_boxed_rectangular_panel(src):
        out = derived_dir / f"{aid}_editorial_matte.png"
        final_path = build_editorial_panel_matte(src, out)

    with Image.open(final_path) as im:
        return final_path, im.width, im.height


def run_motion_stage(
    proj_dir: Path,
    sec_id: str,
    work_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Stage 8: Generates clean preprocessed asset derivatives (`exhibit_card` / `soft_bottom`)."""
    sg_path = proj_dir / "director" / sec_id / "scene_graph.json"
    if not sg_path.is_file():
        raise FileNotFoundError(f"Scene graph not found: {sg_path}. Run 'direct' first.")
    sg = json.loads(sg_path.read_text(encoding="utf-8"))

    raw_assets_dir = proj_dir / "sections" / sec_id / "assets"
    wdir = work_dir or (proj_dir / "work" / sec_id)
    derived_dir = wdir / "derived_assets"
    prepared: List[Dict[str, Any]] = []
    for sc in sg.get("scenes", []):
        for acfg in sc.get("assets", []):
            path, w, h = prepare_asset_derivative(acfg, raw_assets_dir, derived_dir)
            prepared.append({"id": acfg["id"], "file": str(path), "width": w, "height": h})

    motion_plan = wdir / "motion_plan.json"
    motion_plan.parent.mkdir(parents=True, exist_ok=True)
    motion_plan.write_text(
        json.dumps({"section_id": sec_id, "prepared_assets": prepared}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"motion_plan": str(motion_plan), "assets_prepared": len(prepared)}


def _read_wav_float_stereo(path: Path, target_sr: int = MASTER_SAMPLE_RATE) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        n_ch, sampwidth, sr, n_frames = wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()
        raw = wf.readframes(n_frames)
    if sampwidth == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sampwidth == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        signed = b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16)
        signed = np.where(signed >= 0x800000, signed - 0x1000000, signed)
        data = signed.astype(np.float32) / 8388608.0
    else:
        raise ValueError(f"Unsupported sample width {sampwidth} in {path}")
    stereo = np.stack([data, data], axis=1) if n_ch == 1 else data.reshape(-1, n_ch)[:, :2]
    if sr != target_sr and len(stereo) > 1:
        stereo = resample_audio_hq(stereo, sr, target_sr)
    return stereo


def _compute_attack_release_duck_curve(
    voice_stereo: np.ndarray,
    sr: int,
    *,
    threshold_rms: float = 0.025,
    max_duck_db: float = -8.5,
    attack_ms: float = 15.0,
    release_ms: float = 220.0,
) -> np.ndarray:
    """Causal attack/release envelope follower returning per-sample linear ducking gain in [min_gain, 1.0]."""
    n = len(voice_stereo)
    if n == 0:
        return np.ones((0, 1), dtype=np.float32)

    hop = max(1, int(sr * 0.005))  # 5ms control rate (200Hz)
    n_blocks = max(1, (n + hop - 1) // hop)
    v_mono = np.mean(np.abs(voice_stereo), axis=1)

    pad_len = n_blocks * hop - n
    if pad_len > 0:
        v_pad = np.pad(v_mono, (0, pad_len), mode="constant")
    else:
        v_pad = v_mono
    block_rms = np.sqrt(np.mean(v_pad.reshape(n_blocks, hop) ** 2, axis=1) + 1e-12)

    dt = hop / float(sr)
    a_att = math.exp(-dt / max(1e-4, attack_ms / 1000.0))
    a_rel = math.exp(-dt / max(1e-4, release_ms / 1000.0))

    min_gain = 10.0 ** (max_duck_db / 20.0)
    # Smooth proportional target gain instead of harsh binary switch
    over = np.clip((block_rms - threshold_rms) / max(1e-5, threshold_rms * 3.0), 0.0, 1.0)
    target_gain = 1.0 - over * (1.0 - min_gain)

    ctrl = np.empty(n_blocks, dtype=np.float32)
    g = 1.0
    for i in range(n_blocks):
        tg = float(target_gain[i])
        coeff = a_att if tg < g else a_rel
        g = coeff * g + (1.0 - coeff) * tg
        ctrl[i] = g

    x_blocks = np.linspace(0.0, float(n - 1), n_blocks, dtype=np.float32)
    x_samples = np.arange(n, dtype=np.float32)
    smooth = np.interp(x_samples, x_blocks, ctrl).astype(np.float32)
    return smooth[:, None]


def _apply_transparent_limiter(stereo: np.ndarray, sr: int, ceiling_db: float = -1.0) -> np.ndarray:
    """Transparent lookahead peak limiter (unity gain below ceiling — zero harmonic distortion on normal speech)."""
    ceiling = 10.0 ** (ceiling_db / 20.0)
    peak_env = np.max(np.abs(stereo), axis=1)
    if float(np.max(peak_env)) <= ceiling:
        return stereo

    # Short 5ms lookahead maximum filter + smooth 60ms release
    win = max(1, int(sr * 0.005))
    hop = max(1, win // 2)
    n = len(peak_env)
    n_blocks = max(1, (n + hop - 1) // hop)
    pad_len = n_blocks * hop - n
    p_pad = np.pad(peak_env, (0, pad_len), mode="constant") if pad_len > 0 else peak_env
    blk_peak = np.max(p_pad.reshape(n_blocks, hop), axis=1)

    req_gain = np.minimum(1.0, ceiling / np.maximum(blk_peak, 1e-8)).astype(np.float32)
    dt = hop / float(sr)
    a_rel = math.exp(-dt / 0.060)
    ctrl = np.empty(n_blocks, dtype=np.float32)
    g = 1.0
    for i in range(n_blocks):
        tg = float(req_gain[i])
        g = tg if tg < g else (a_rel * g + (1.0 - a_rel) * tg)
        ctrl[i] = g

    x_blocks = np.linspace(0.0, float(n - 1), n_blocks, dtype=np.float32)
    gain_curve = np.interp(np.arange(n, dtype=np.float32), x_blocks, ctrl).astype(np.float32)[:, None]
    return np.clip(stereo * gain_curve, -ceiling, ceiling)


def resolve_sfx_path(cue_ref: str) -> Optional[Path]:
    p = Path(cue_ref)
    if p.is_absolute() and p.is_file():
        return p
    for base in (SFX_BASIC_DIR, SFX_PRO_DIR, ROOT_DIR / "production_engine" / "sfx", ROOT_DIR):
        for cand in (base / cue_ref, base / f"{cue_ref}.wav"):
            if cand.is_file():
                return cand
    if SFX_PRO_DIR.is_dir():
        matches = list(SFX_PRO_DIR.rglob(f"*{cue_ref}*"))
        if matches:
            return matches[0]
    return None


def mix_scene_graph_audio(
    narration_wav: Path,
    sfx_cues: List[Dict[str, Any]],
    out_wav: Path,
    target_sr: int = MASTER_SAMPLE_RATE,
) -> Dict[str, Any]:
    """Mixes narration WAV + scheduled SFX at 48kHz with envelope-follower ducking, vocal-band carve & true-peak limiting."""
    voice = _read_wav_float_stereo(narration_wav, target_sr=target_sr)
    total_samples = len(voice)
    duration_sec = total_samples / float(target_sr)

    # Preserve mastered voice loudness (only protect against unexpected clipping > -1 dBFS)
    v_peak = float(np.max(np.abs(voice))) if total_samples > 0 else 0.0
    if v_peak > 0.90:
        voice = voice * (0.891 / v_peak)

    sfx_bed = np.zeros_like(voice, dtype=np.float32)
    placed_cues, missing_cues = [], []
    last_cue_name = ""
    pitch_offsets = (1.0, 1.024, 0.976, 1.015, 0.985)

    for cue_idx, cue in enumerate(sfx_cues):
        ref = cue.get("file", "")
        resolved = resolve_sfx_path(ref)
        if not resolved:
            missing_cues.append(ref)
            continue
        st_sec = float(cue.get("time", 0.0))
        gain_db = float(cue.get("gain_db", -12.0))
        max_dur = cue.get("max_duration")
        fade_out_sec = float(cue.get("fade_out", 0.25))
        pan = float(cue.get("pan", 0.0))

        clip = _read_wav_float_stereo(resolved, target_sr=target_sr)

        # Subtle deterministic pitch micro-variation (+/- 2.4%) when same SFX repeats consecutively
        if resolved.name == last_cue_name and len(clip) > 128:
            ratio = pitch_offsets[cue_idx % len(pitch_offsets)]
            if abs(ratio - 1.0) > 0.001:
                clip = resample_audio_hq(clip, int(round(target_sr * ratio)), target_sr)
        last_cue_name = resolved.name

        if max_dur is not None:
            clip = clip[:min(len(clip), int(float(max_dur) * target_sr))].copy()
            fo_n = min(len(clip), int(fade_out_sec * target_sr))
            if fo_n > 0:
                ramp = np.linspace(1.0, 0.0, fo_n, dtype=np.float32)[:, None]
                clip[-fo_n:, :] *= ramp

        # Equal-power stereo panning
        pan_c = max(-1.0, min(1.0, pan))
        gain_lin = 10.0 ** (gain_db / 20.0)
        clip[:, 0] *= gain_lin * math.sqrt(0.5 * (1.0 - pan_c)) * 1.4142
        clip[:, 1] *= gain_lin * math.sqrt(0.5 * (1.0 + pan_c)) * 1.4142

        s0 = max(0, int(st_sec * target_sr))
        e0 = min(total_samples, s0 + len(clip))
        if e0 > s0:
            sfx_bed[s0:e0] += clip[: e0 - s0]
            placed_cues.append({"file": resolved.name, "time": st_sec, "gain_db": gain_db})

    # Causal attack/release envelope ducking + vocal-band sidechain carve (1.2-3.8 kHz)
    duck_curve = _compute_attack_release_duck_curve(
        voice, target_sr, threshold_rms=0.025, max_duck_db=-8.5, attack_ms=15.0, release_ms=220.0
    )
    if placed_cues and total_samples > 64 and target_sr >= 16000:
        nyq = 0.5 * target_sr
        sos_vox = scipy_signal.butter(2, [1200.0 / nyq, min(3800.0 / nyq, 0.95)], btype="bandpass", output="sos")
        sfx_vox_band = scipy_signal.sosfilt(sos_vox, sfx_bed, axis=0).astype(np.float32)
        # During speech, carve an extra ~3.5 dB from the vocal presence band of SFX while keeping sub-bass/air intact
        speech_amt = np.clip((1.0 - duck_curve) / max(1e-5, 1.0 - 10.0 ** (-8.5 / 20.0)), 0.0, 1.0)
        sfx_carved = sfx_bed - 0.35 * speech_amt * sfx_vox_band
    else:
        sfx_carved = sfx_bed

    mixed = _apply_transparent_limiter(voice + sfx_carved * duck_curve, target_sr, ceiling_db=-1.0)
    pcm16 = np.clip(np.round(mixed * 32767.0), -32768, 32767).astype(np.int16)

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    tmp_wav = out_wav.with_name(f"{out_wav.name}.tmp.wav")
    with wave.open(str(tmp_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(target_sr)
        wf.writeframes(pcm16.tobytes())
    tmp_wav.replace(out_wav)

    return {
        "duration_sec": round(duration_sec, 3),
        "sample_rate": target_sr,
        "placed_cues_count": len(placed_cues),
        "missing_cues": missing_cues,
        "out_wav": str(out_wav),
    }


def run_sfx_stage(
    proj_dir: Path,
    sec_id: str,
    work_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Stage 9: Mixes narration + scene_graph SFX cues cleanly."""
    sg_path = proj_dir / "director" / sec_id / "scene_graph.json"
    if not sg_path.is_file():
        raise FileNotFoundError(f"Scene graph not found: {sg_path}. Run 'direct' first.")
    sg = json.loads(sg_path.read_text(encoding="utf-8"))

    narr_rel = sg.get("source_timeline", {}).get("audio_file") or f"sections/{sec_id}/voice/{sec_id}.wav"
    narr_wav = proj_dir / narr_rel
    if not narr_wav.is_file():
        raise FileNotFoundError(f"Narration WAV missing: {narr_wav}")

    wdir = work_dir or (proj_dir / "work" / sec_id)
    out_wav = wdir / f"{sec_id}_aion_mix.wav"
    return mix_scene_graph_audio(narr_wav, sg.get("sfx_cues", []), out_wav)

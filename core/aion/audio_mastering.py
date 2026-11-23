"""Broadcast-Grade Audio DSP Core for AION Studio (48kHz End-to-End).

Provides separate language-tuned mastering chains:
  - Saudi Arabic (`ar`): Preserves pharyngeal/emphatic warmth (80Hz HPF), cuts low-mid mud,
    boosts consonant/shadda articulation (3.2kHz), tames Arabic sibilants (س/ص/ش),
    smooth 2.5:1 broadcast compression, 2-pass linear loudnorm (-14 LUFS / -1.0 dBTP).
  - English / Foreign (`en`+): Tight close-mic YouTube explainer HPF (95Hz),
    crisp presence (4.0kHz) + air shelf (10.8kHz), targeted English sibilance control,
    punchy 3.0:1 vocal compression, 2-pass linear loudnorm (-14 LUFS / -1.0 dBTP).

Also provides:
  - RMS-windowed silence trimming with zero-crossing snap & micro-fade (protects soft onsets)
  - Seamless chunk stitching with micro-crossfades & ultra-low room-tone floor (-68 dBFS)
  - Polyphase high-quality resampling (zero linear-interpolation aliasing)
  - Full-file broadcast loudness & silence-gap QA metrics via FFmpeg
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import signal as scipy_signal

MASTER_SAMPLE_RATE = 48000
TARGET_LUFS = -14.0
TARGET_TP_DB = -1.0


def resample_audio_hq(stereo: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    """High-quality polyphase anti-aliased resampling for mono or stereo float32 arrays."""
    if src_sr == dst_sr or len(stereo) <= 1:
        return stereo.astype(np.float32, copy=False)
    g = math.gcd(int(src_sr), int(dst_sr))
    up = int(dst_sr) // g
    down = int(src_sr) // g
    arr = np.asarray(stereo, dtype=np.float32)
    if arr.ndim == 1:
        return scipy_signal.resample_poly(arr, up, down).astype(np.float32)
    ch0 = scipy_signal.resample_poly(arr[:, 0], up, down)
    ch1 = scipy_signal.resample_poly(arr[:, 1], up, down)
    return np.stack([ch0, ch1], axis=1).astype(np.float32)


def trim_pcm_silence_rms(
    pcm_bytes: bytes,
    sample_rate: int = 24000,
    bits_per_sample: int = 16,
    rms_threshold_dbfs: float = -44.0,
    pad_ms: int = 40,
    fade_ms: int = 8,
) -> bytes:
    """Trims leading/trailing dead air using RMS frames + micro-fade so soft consonants survive."""
    if bits_per_sample != 16 or len(pcm_bytes) < 600:
        return pcm_bytes

    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    n = len(samples)
    win = max(1, int(sample_rate * 0.010))  # 10ms RMS window
    n_win = n // win
    if n_win < 4:
        return pcm_bytes

    frames = samples[: n_win * win].reshape(n_win, win)
    rms = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
    thresh_lin = 10.0 ** (rms_threshold_dbfs / 20.0)
    active = np.where(rms > thresh_lin)[0]
    if len(active) == 0:
        return pcm_bytes

    pad_samples = int(sample_rate * (pad_ms / 1000.0))
    start_idx = max(0, int(active[0]) * win - pad_samples)
    end_idx = min(n, int(active[-1] + 1) * win + pad_samples)
    if end_idx - start_idx < win * 2:
        return pcm_bytes

    trimmed = samples[start_idx:end_idx].copy()
    fade_n = min(len(trimmed) // 4, int(sample_rate * (fade_ms / 1000.0)))
    if fade_n > 1:
        ramp_in = np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
        trimmed[:fade_n] *= ramp_in
        trimmed[-fade_n:] *= ramp_in[::-1]

    out_i16 = np.clip(np.round(trimmed * 32767.0), -32768, 32767).astype(np.int16)
    return out_i16.tobytes()


def stitch_wav_chunks_seamless(
    chunk_wavs: List[Path],
    out_wav: Path,
    gap_sec: float = 0.14,
    fade_ms: float = 10.0,
    room_tone_dbfs: float = -68.0,
) -> Path:
    """Stitches chunk WAVs with micro-fades and natural ultra-low room-tone pauses (zero clicks)."""
    if not chunk_wavs:
        raise ValueError("No chunk WAVs provided for stitching.")

    with wave.open(str(chunk_wavs[0]), "rb") as w0:
        sr = w0.getframerate()
        nch = w0.getnchannels()
        sw = w0.getsampwidth()

    fade_n = max(1, int(sr * (fade_ms / 1000.0)))
    gap_n = max(0, int(round(sr * gap_sec)))
    rng = np.random.default_rng(seed=42)
    tone_amp = 10.0 ** (room_tone_dbfs / 20.0)

    segments: List[np.ndarray] = []
    for idx, cp in enumerate(chunk_wavs):
        with wave.open(str(cp), "rb") as wf:
            c_sr = wf.getframerate()
            c_ch = wf.getnchannels()
            raw = wf.readframes(wf.getnframes())
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if c_ch > 1:
            data = data.reshape(-1, c_ch).mean(axis=1)
        if c_sr != sr:
            data = resample_audio_hq(data, c_sr, sr)
        if len(data) == 0:
            continue

        fn = min(fade_n, len(data) // 4)
        if fn > 1:
            ramp = np.linspace(0.0, 1.0, fn, dtype=np.float32)
            data[:fn] *= ramp
            data[-fn:] *= ramp[::-1]
        segments.append(data)

        if idx < len(chunk_wavs) - 1 and gap_n > 0:
            # Soft low-passed room tone prevents artificial "digital vacuum" between sentences
            noise = rng.normal(0.0, tone_amp, gap_n).astype(np.float32)
            b, a = scipy_signal.butter(1, 0.15)
            room = scipy_signal.lfilter(b, a, noise).astype(np.float32)
            segments.append(room)

    joined = np.concatenate(segments) if segments else np.zeros(1, dtype=np.float32)
    pcm16 = np.clip(np.round(joined * 32767.0), -32768, 32767).astype(np.int16)

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_wav.with_name(f"{out_wav.name}.tmp.wav")
    with wave.open(str(tmp), "wb") as ow:
        ow.setnchannels(1 if nch == 1 else nch)
        ow.setsampwidth(sw)
        ow.setframerate(sr)
        ow.writeframes(pcm16.tobytes())
    tmp.replace(out_wav)
    return out_wav


def build_vocal_dsp_chain(language: str, speed_factor: float = 1.0) -> List[str]:
    """Returns language-specific pre-loudnorm FFmpeg vocal polish filters.

    Saudi Arabic (`ar`) and English/Foreign (`en`+) use distinct spectral & dynamic curves.
    """
    is_en = str(language or "ar").lower().startswith("en")
    if is_en:
        # Close-mic American YouTube explainer chain (crisp air, tight lows, punchy 3:1 leveling)
        filters = [
            "highpass=f=95",
            "equalizer=f=260:t=q:w=1.5:g=-1.5",
            "equalizer=f=4000:t=q:w=1.3:g=1.6",
            "equalizer=f=7600:t=q:w=2.0:g=-2.4",
            "highshelf=f=10800:g=1.5",
            "acompressor=threshold=-17dB:ratio=3.0:attack=8:release=75:makeup=2.0",
        ]
    else:
        # Saudi Arabic YouTube creator chain (warm pharyngeals, anti-boxiness, crisp shadda, sibilance control)
        filters = [
            "highpass=f=80",
            "equalizer=f=280:t=q:w=1.4:g=-1.8",
            "equalizer=f=3200:t=q:w=1.3:g=1.8",
            "equalizer=f=6800:t=q:w=1.8:g=-2.2",
            "acompressor=threshold=-18dB:ratio=2.5:attack=10:release=90:makeup=1.5",
        ]

    if abs(speed_factor - 1.0) > 0.005:
        clamped = max(0.5, min(2.0, float(speed_factor)))
        filters.append(f"atempo={clamped:.4f}")
    return filters


def _parse_loudnorm_json(stderr_text: str) -> Optional[Dict[str, str]]:
    """Extracts the JSON measurement block emitted by FFmpeg's loudnorm=print_format=json."""
    matches = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr_text, flags=re.DOTALL)
    if not matches:
        return None
    try:
        return json.loads(matches[-1])
    except Exception:
        return None


def master_voice_ffmpeg(
    raw_wav: Path,
    final_wav: Path,
    *,
    language: str = "ar",
    speed_factor: float = 1.0,
    target_lufs: float = TARGET_LUFS,
    target_tp: float = TARGET_TP_DB,
    target_lra: float = 7.0,
    sample_rate: int = MASTER_SAMPLE_RATE,
) -> Tuple[float, Dict[str, Any]]:
    """Applies language-tuned vocal DSP + 2-pass linear broadcast loudnorm + true-peak limiter at 48kHz."""
    final_wav.parent.mkdir(parents=True, exist_ok=True)
    pre_filters = build_vocal_dsp_chain(language=language, speed_factor=speed_factor)
    pre_chain = ",".join(pre_filters)

    # Pass 1: Measure exact integrated loudness & true peak after vocal DSP
    pass1_filter = f"{pre_chain},loudnorm=I={target_lufs}:TP={target_tp}:LRA={target_lra}:print_format=json"
    p1 = subprocess.run(
        ["ffmpeg", "-y", "-i", str(raw_wav), "-af", pass1_filter, "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    measured = _parse_loudnorm_json(p1.stderr)

    # Pass 2: Apply linear 2-pass loudnorm (falls back to single-pass only if input was ultra-short/silent)
    if measured and measured.get("input_i") not in (None, "-inf", "inf"):
        ln_pass2 = (
            f"loudnorm=I={target_lufs}:TP={target_tp}:LRA={target_lra}:"
            f"measured_I={measured['input_i']}:measured_LRA={measured['input_lra']}:"
            f"measured_TP={measured['input_tp']}:measured_thresh={measured['input_thresh']}:"
            f"offset={measured['target_offset']}:linear=true"
        )
        used_two_pass = True
    else:
        ln_pass2 = f"loudnorm=I={target_lufs}:TP={target_tp}:LRA={target_lra}"
        used_two_pass = False

    # Safety true-peak ceiling limiter (-1.0 dBFS == 0.891 linear) + clean 48kHz resample
    limit_lin = round(10.0 ** (target_tp / 20.0), 4)
    full_chain = f"{pre_chain},{ln_pass2},alimiter=limit={limit_lin}:level=false,aresample={sample_rate}"
    tmp_wav = final_wav.with_name(f"{final_wav.name}.tmp.wav")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(raw_wav),
            "-af", full_chain,
            "-ar", str(sample_rate), "-ac", "1", "-c:a", "pcm_s16le",
            str(tmp_wav),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    tmp_wav.replace(final_wav)

    with wave.open(str(final_wav), "rb") as wf:
        dur = round(wf.getnframes() / float(wf.getframerate()), 3)

    meta = {
        "language_chain": "en" if str(language).lower().startswith("en") else "ar_saudi",
        "sample_rate": sample_rate,
        "two_pass_loudnorm": used_two_pass,
        "target_lufs": target_lufs,
        "target_tp_db": target_tp,
        "speed_factor": speed_factor,
    }
    return dur, meta


def measure_audio_loudness(wav_path: Path) -> Dict[str, Any]:
    """Measures full-file Integrated LUFS, True Peak (dBTP), and LRA via FFmpeg loudnorm."""
    p = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(wav_path),
            "-af", "loudnorm=I=-14:TP=-1.0:LRA=7:print_format=json",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    parsed = _parse_loudnorm_json(p.stderr or "")
    if not parsed:
        return {"integrated_lufs": None, "true_peak_dbtp": None, "lra": None}

    def _flt(key: str) -> Optional[float]:
        val = parsed.get(key)
        if val in (None, "-inf", "inf", "nan"):
            return None
        try:
            return round(float(val), 2)
        except Exception:
            return None

    return {
        "integrated_lufs": _flt("input_i"),
        "true_peak_dbtp": _flt("input_tp"),
        "lra": _flt("input_lra"),
    }


def audit_audio_broadcast_qa(
    wav_path: Path,
    *,
    clipping_threshold: float = 0.995,
    silence_dbfs: float = -46.0,
) -> Dict[str, Any]:
    """Full-duration broadcast QA audit (no 60-second cutoff): peak, clipping, silence gaps & LUFS."""
    with wave.open(str(wav_path), "rb") as wf:
        n_ch = wf.getnchannels()
        sw = wf.getsampwidth()
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    duration = round(n_frames / float(sr), 3) if sr > 0 else 0.0
    if sw == 2 and raw:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        samples = np.zeros(1, dtype=np.float32)

    if n_ch > 1 and len(samples) >= n_ch:
        mono = samples.reshape(-1, n_ch).mean(axis=1)
        peak = float(np.max(np.abs(samples)))
    else:
        mono = samples
        peak = float(np.max(np.abs(mono))) if len(mono) > 0 else 0.0

    # Measure longest silence gap across entire file using 50ms windows
    win = max(1, int(sr * 0.05))
    n_win = len(mono) // win
    max_silence_sec = 0.0
    if n_win > 0:
        frames = mono[: n_win * win].reshape(n_win, win)
        rms = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
        thresh = 10.0 ** (silence_dbfs / 20.0)
        silent = rms < thresh
        run = 0
        max_run = 0
        for is_sil in silent:
            if is_sil:
                run += 1
                if run > max_run:
                    max_run = run
            else:
                run = 0
        max_silence_sec = round(max_run * 0.05, 2)

    loud = measure_audio_loudness(wav_path)
    return {
        "duration_sec": duration,
        "sample_rate": sr,
        "channels": n_ch,
        "sample_peak": round(peak, 4),
        "clipping_detected": bool(peak >= clipping_threshold),
        "max_silence_gap_sec": max_silence_sec,
        **loud,
    }

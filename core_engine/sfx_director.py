"""Audio SFX Library and Synchronizer for Whiteboard Motion Graphics.
Procedurally generates pristine studio sound effects and synchronizes them
with visual manifest keyframes (Pop, Whoosh, Card Snap, Glint, Thud).
Mixes an SFX track ducked at -14dB beneath voiceover.
"""

import math
import struct
import wave
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
SFX_DIR = ROOT_DIR / "assets" / "sfx"
SFX_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_RATE = 44100

def _write_wav(filename: Path, samples: np.ndarray, sample_rate: int = SAMPLE_RATE):
    """Writes a 16-bit mono WAV file."""
    # Normalize and clip
    max_val = np.max(np.abs(samples))
    if max_val > 1.0:
        samples = samples / max_val
    int_samples = (samples * 32767).astype(np.int16)
    with wave.open(str(filename), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int_samples.tobytes())

def generate_default_sfx_library():
    """Generates clean procedural SFX if not present."""
    # 1. Pop (Clean rounded bubble/pop)
    pop_file = SFX_DIR / "pop.wav"
    if not pop_file.exists():
        dur = 0.09
        t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
        # Frequency drops from 680Hz to 180Hz
        freq = np.linspace(680, 180, len(t))
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.exp(-t * 45) * np.sin(np.pi * t / dur)
        samples = np.sin(phase) * env * 0.8
        _write_wav(pop_file, samples)

    # 2. Whoosh (Gentle airy whoosh)
    whoosh_file = SFX_DIR / "whoosh.wav"
    if not whoosh_file.exists():
        dur = 0.28
        t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
        # Noise shaped with bell envelope
        noise = np.random.uniform(-1, 1, len(t))
        # Simple IIR low-pass filter
        filtered = np.zeros_like(noise)
        alpha = 0.22
        for i in range(1, len(noise)):
            filtered[i] = alpha * noise[i] + (1 - alpha) * filtered[i-1]
        env = (np.sin(np.pi * t / dur) ** 2) * 0.55
        samples = filtered * env
        _write_wav(whoosh_file, samples)

    # 3. Card Snap (Tactile paper snap)
    snap_file = SFX_DIR / "card_snap.wav"
    if not snap_file.exists():
        dur = 0.08
        t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
        # Fast click + body resonance (1200Hz & 380Hz)
        click = np.sin(2 * np.pi * 1200 * t) * np.exp(-t * 90) * 0.5
        body = np.sin(2 * np.pi * 380 * t) * np.exp(-t * 40) * 0.4
        samples = (click + body) * 0.75
        _write_wav(snap_file, samples)

    # 4. Glint / Shimmer (High crystal chime for light sweeps)
    glint_file = SFX_DIR / "glint.wav"
    if not glint_file.exists():
        dur = 0.38
        t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
        chime1 = np.sin(2 * np.pi * 2349.32 * t) * np.exp(-t * 12)  # D7
        chime2 = np.sin(2 * np.pi * 3520.00 * t) * np.exp(-t * 14)  # A7
        chime3 = np.sin(2 * np.pi * 4698.63 * t) * np.exp(-t * 18)  # D8
        samples = (chime1 * 0.4 + chime2 * 0.35 + chime3 * 0.25) * 0.45
        _write_wav(glint_file, samples)

    # 5. Thud / Impact (Subtle low punch)
    thud_file = SFX_DIR / "thud.wav"
    if not thud_file.exists():
        dur = 0.16
        t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
        freq = np.linspace(130, 45, len(t))
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.exp(-t * 26)
        samples = np.sin(phase) * env * 0.7
        _write_wav(thud_file, samples)

    # 6. Sword Slash / Metallic Blade Swish (For assassinations, battles, blades)
    slash_file = SFX_DIR / "sword_slash.wav"
    if not slash_file.exists():
        dur = 0.22
        t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
        # High metallic frequency sweep + airy hiss
        freq1 = np.linspace(3800, 950, len(t))
        freq2 = np.linspace(6200, 1800, len(t))
        p1 = 2 * np.pi * np.cumsum(freq1) / SAMPLE_RATE
        p2 = 2 * np.pi * np.cumsum(freq2) / SAMPLE_RATE
        noise = np.random.uniform(-1, 1, len(t))
        env = np.exp(-t * 22) * (np.sin(np.pi * t / dur) ** 0.7)
        samples = (np.sin(p1) * 0.45 + np.sin(p2) * 0.30 + noise * 0.25) * env * 0.75
        _write_wav(slash_file, samples)

    # 7. Heartbeat Pulse (Deep double lub-dub for suspense, revenge, shock, heart extraction)
    hb_file = SFX_DIR / "heartbeat.wav"
    if not hb_file.exists():
        dur = 0.52
        t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
        # First beat (lub) at 0.02s, Second beat (dub) at 0.22s
        lub = np.sin(2 * np.pi * 62 * t) * np.exp(-((t - 0.06) ** 2) / 0.0018)
        dub = np.sin(2 * np.pi * 52 * t) * np.exp(-((t - 0.24) ** 2) / 0.0022) * 0.85
        samples = (lub + dub) * 0.85
        _write_wav(hb_file, samples)

    # 8.Suspense Riser / Shock Stinger (For "وهنا كانت الصدمة" / sudden twists)
    riser_file = SFX_DIR / "suspense_riser.wav"
    if not riser_file.exists():
        dur = 0.55
        t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
        freq = np.linspace(140, 880, len(t))
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = (t / dur) ** 1.8 * np.exp(-(dur - t) * 4)
        samples = (np.sin(phase) * 0.65 + np.sin(phase * 1.5) * 0.35) * env * 0.65
        _write_wav(riser_file, samples)

class SFXDirector:
    """Extracts animation cues from manifest and renders synchronized audio mix."""

    def __init__(self):
        generate_default_sfx_library()
        self.sfx_samples = {}
        for sfx_name in ["pop", "whoosh", "card_snap", "glint", "thud", "sword_slash", "heartbeat", "suspense_riser"]:
            wav_p = SFX_DIR / f"{sfx_name}.wav"
            if wav_p.exists():
                with wave.open(str(wav_p), 'r') as wf:
                    n_frames = wf.getnframes()
                    raw = wf.readframes(n_frames)
                    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0
                    self.sfx_samples[sfx_name] = (data, wf.getframerate())

    def create_synchronized_audio(self, manifest: Dict[str, Any], voice_wav_path: Path, out_wav_path: Path) -> Path:
        """Mixes voiceover audio with precisely timed sound effects."""
        if not voice_wav_path.exists():
            print(f"[SFXDirector] Voice wav not found: {voice_wav_path}")
            return voice_wav_path

        # Read base voiceover
        with wave.open(str(voice_wav_path), 'r') as wf:
            v_sr = wf.getframerate()
            v_channels = wf.getnchannels()
            v_frames = wf.getnframes()
            v_raw = wf.readframes(v_frames)
            v_data = np.frombuffer(v_raw, dtype=np.int16).astype(np.float32) / 32767.0
            if v_channels > 1:
                v_data = v_data.reshape(-1, v_channels)[:, 0]

        total_duration = v_frames / float(v_sr)
        sfx_track = np.zeros_like(v_data)

        # Helper to overlay an sfx sample
        def overlay(sfx_key: str, timestamp_sec: float, gain: float = 0.22):
            if sfx_key not in self.sfx_samples:
                return
            s_data, s_sr = self.sfx_samples[sfx_key]
            # Resample if sample rate differs
            if s_sr != v_sr:
                indices = np.round(np.arange(0, len(s_data), s_sr / float(v_sr))).astype(int)
                indices = indices[indices < len(s_data)]
                s_data = s_data[indices]

            start_idx = max(0, int(timestamp_sec * v_sr))
            end_idx = min(len(sfx_track), start_idx + len(s_data))
            chunk_len = end_idx - start_idx
            if chunk_len > 0:
                sfx_track[start_idx:end_idx] += s_data[:chunk_len] * gain

        # Scan manifest scenes for triggers
        for sc in manifest.get("scenes", []):
            sc_start = float(sc.get("start", 0.0))
            sc_end = float(sc.get("end", total_duration))

            # Scene-level camera effects (e.g. border_flash danger pulse)
            for cam_fx in sc.get("camera_effects", []):
                cfx_t = float(cam_fx.get("time", cam_fx.get("start", sc_start)))
                overlay("thud", cfx_t, gain=0.38)

            for elem in sc.get("elements", []):
                st = float(elem.get("start", sc_start))
                et = float(elem.get("end", sc_end))
                anim = elem.get("entrance", elem.get("anim_type", "pop_bounce"))
                exit_anim = elem.get("exit", "shrink_out")
                
                # 1. Element Entrance SFX
                if anim in ["whip_motion", "whip_pan", "whip_in", "directional_slide", "slide_in", "directional_flow", "mask_wipe", "mask_reveal_wipe", "wipe_in", "speed_blur"]:
                    overlay("whoosh", st, gain=0.38)
                elif anim in ["card_stack", "stack_deck"]:
                    overlay("card_snap", st, gain=0.40)
                elif anim in ["squash_drop", "gravity_drop"]:
                    overlay("whoosh", st, gain=0.30)
                    overlay("thud", st + 0.24, gain=0.42)
                elif anim in ["zoom_in", "fade_zoom"]:
                    overlay("whoosh", st, gain=0.32)
                    overlay("pop", st + 0.28, gain=0.34)
                else:
                    # pop_bounce, elastic_overshoot, rotation_spin, etc.
                    overlay("pop", st + 0.05, gain=0.38)

                # 2. Scale Punches & Mid-Hold Impact Beats
                for punch in elem.get("scale_punches", []):
                    pt = float(punch.get("time", st))
                    overlay("thud", pt, gain=0.40)
                    overlay("pop", pt + 0.04, gain=0.28)

                # 3. Legacy Light Sweeps array
                for sweep in elem.get("light_sweeps", []):
                    sw_t = float(sweep.get("time", st))
                    overlay("glint", sw_t, gain=0.32)

                # 4. Standardized Effects array (light_sweep, tint_flash, wiggle, radio_waves, border_flash, lightning, radial_blur)
                for fx in elem.get("effects", []):
                    fx_type = fx.get("type", "")
                    fx_t = float(fx.get("time", fx.get("start", st)))
                    fx_sfx = fx.get("sfx", "")
                    if fx_sfx and fx_sfx in self.sfx_samples:
                        overlay(fx_sfx, fx_t, gain=float(fx.get("gain", 0.38)))
                    elif fx_type in ["light_sweep", "sweep", "light_burst", "radio_waves", "neon_glow"]:
                        overlay("glint", fx_t, gain=0.34)
                    elif fx_type in ["lightning", "lightning_flash", "electric_arc"]:
                        overlay("sword_slash", fx_t, gain=0.38)
                        overlay("thud", fx_t + 0.05, gain=0.34)
                    elif fx_type in ["radial_blur"]:
                        overlay("suspense_riser", max(0.0, fx_t - 0.15), gain=0.34)
                        overlay("thud", fx_t + 0.10, gain=0.38)
                    elif fx_type in ["tint_flash", "color_tint_flash", "white_strobe", "border_flash"]:
                        overlay("heartbeat", fx_t, gain=0.38)
                        overlay("thud", fx_t, gain=0.34)
                    elif fx_type in ["wiggle", "wiggle_attention", "attention_wiggle"]:
                        overlay("pop", fx_t, gain=0.32)
                    elif fx_type in ["mask_wipe", "speed_blur"]:
                        overlay("whoosh", fx_t, gain=0.34)

                # 5. Element Exit SFX
                if et < total_duration - 0.15:
                    if exit_anim in ["slide_out", "directional_slide_out", "fly_away"]:
                        overlay("whoosh", max(0.0, et - 0.35), gain=0.26)
                    elif exit_anim in ["shrink_out", "pop_shrink"]:
                        overlay("pop", max(0.0, et - 0.28), gain=0.24)

            # 6. Word Cards (Style 1 Traveling Dot Whoosh + Card Bloom Snap)
            card_list = sc.get("words", sc.get("word_cards", []))
            for wc in card_list:
                card_t = float(wc.get("start", sc_start))
                overlay("whoosh", card_t, gain=0.24)
                overlay("card_snap", card_t + 0.26, gain=0.36)

        # Mix voiceover + ducked SFX (-14dB relative)
        # SFX gain is controlled above (~0.18 to 0.25).
        mixed = v_data + sfx_track
        
        # Soft limiter / ceiling at 0.96 to prevent clipping
        max_peak = np.max(np.abs(mixed))
        if max_peak > 0.96:
            mixed = (mixed / max_peak) * 0.96

        # Write output wav
        out_wav_path.parent.mkdir(parents=True, exist_ok=True)
        int_out = (mixed * 32767).astype(np.int16)
        with wave.open(str(out_wav_path), 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(v_sr)
            wf.writeframes(int_out.tobytes())

        print(f"🎵 Synchronized SFX mixed: {out_wav_path.name} (Duration: {total_duration:.2f}s)")
        return out_wav_path

if __name__ == "__main__":
    generate_default_sfx_library()
    print("Default SFX library created successfully.")

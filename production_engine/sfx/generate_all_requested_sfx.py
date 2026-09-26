"""
Script to generate all 18 requested whiteboard sound effects in pristine 48kHz WAV format.
Uses physics-based DSP synthesis: harmonic modeling, filtered friction noise, frequency sweeps,
and exponential envelopes tailored specifically for whiteboard animations.
"""
import os
import wave
import numpy as np

import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
SR = 48000

def save_wav(name, audio_data, volume=0.85):
    """Normalize and write 16-bit mono 48kHz WAV file."""
    peak = np.max(np.abs(audio_data))
    if peak > 0:
        audio_data = (audio_data / peak) * volume
    pcm = (audio_data * 32767.0).astype(np.int16)
    out_path = os.path.join(OUTPUT_DIR, f"{name}.wav")
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    dur = len(audio_data) / SR
    print(f"[OK] Created: {name}.wav ({dur:.2f}s)")
    return out_path

# ==========================================
# 1. PENCIL WRITE (0.5–2s) — ✏️ رسم القلم
# ==========================================
def gen_pencil_write():
    dur = 1.4
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    # Rhythmic writing friction with multiple micro-strokes
    noise = np.random.normal(0, 1, len(t))
    # Filter emulation via highpass/bandpass weighting
    stroke_env = (np.abs(np.sin(2 * np.pi * 5.2 * t)) ** 1.8) * (0.4 + 0.6 * np.cos(2 * np.pi * 1.5 * t) ** 2)
    # Micro jitter
    jitter = 0.8 + 0.4 * np.random.uniform(0, 1, len(t))
    signal = noise * stroke_env * jitter
    # Envelope fade in/out
    env = np.sin(np.pi * (t / dur)) ** 0.5
    return save_wav("pencil_write", signal * env, 0.70)

# ==========================================
# 2. MARKER SCRIBBLE (0.3–1.5s) — ✏️ رسم سريع
# ==========================================
def gen_marker_scribble():
    dur = 0.85
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    noise = np.random.normal(0, 1, len(t))
    # Rapid back and forth marker friction (8 strokes/sec)
    hatch = np.abs(np.sin(2 * np.pi * 8.5 * t)) ** 2.2
    # Formant squeak
    squeak = np.sin(2 * np.pi * 1350 * t) * 0.12 * hatch
    signal = (noise * hatch * 0.7) + squeak
    env = np.sin(np.pi * (t / dur)) ** 0.6
    return save_wav("marker_scribble", signal * env, 0.75)

# ==========================================
# 3. PENCIL STROKE (0.2–1s) — ✏️ خط أو تفصيلة
# ==========================================
def gen_pencil_stroke():
    dur = 0.45
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    noise = np.random.normal(0, 1, len(t))
    # Single smooth stroke envelope
    env = np.sin(np.pi * (t / dur)) ** 2.0
    mod = np.sin(2 * np.pi * 3200 * t) * 0.1
    signal = noise * env * (1.0 + mod)
    return save_wav("pencil_stroke", signal, 0.70)

# ==========================================
# 4. MARKER STROKE (0.3–1.5s) — ✏️ كتابة / تحديد
# ==========================================
def gen_marker_stroke():
    dur = 0.65
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    noise = np.random.normal(0, 1, len(t))
    # Felt-tip squeak transient at start, then friction
    squeak = np.sin(2 * np.pi * 1180 * t) * np.exp(-t * 22.0) * 0.35
    env = (np.sin(np.pi * (t / dur)) ** 1.5)
    signal = noise * env * 0.65 + squeak
    return save_wav("marker_stroke", signal, 0.75)

# ==========================================
# 5. SOFT WHOOSH (0.2–0.8s) — 💨 انتقال اليد/العنصر
# ==========================================
def gen_soft_whoosh():
    dur = 0.42
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    noise = np.random.normal(0, 1, len(t))
    env = np.sin(np.pi * (t / dur)) ** 3.0
    # Pitch sweep down
    f_sweep = np.linspace(800, 350, len(t))
    swirl = np.sin(2 * np.pi * f_sweep * t * 0.4)
    signal = noise * env * (0.6 + 0.4 * swirl)
    return save_wav("soft_whoosh", signal, 0.75)

# ==========================================
# 6. LIGHT WHOOSH (0.2–0.7s) — 💨 ظهور عنصر جديد
# ==========================================
def gen_light_whoosh():
    dur = 0.28
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    noise = np.random.normal(0, 1, len(t))
    # Very light, quick air sweep
    env = np.sin(np.pi * (t / dur)) ** 4.0
    f_sweep = np.linspace(1200, 600, len(t))
    tone = np.sin(2 * np.pi * f_sweep * t * 0.3)
    signal = noise * env * 0.7 + tone * env * 0.3
    return save_wav("light_whoosh", signal, 0.70)

# ==========================================
# 7. SOFT POP (0.1–0.4s) — 👆 ظهور صورة / عنصر
# ==========================================
def gen_soft_pop():
    dur = 0.16
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    # Frequency chirp from 550Hz down to 160Hz
    f = np.linspace(550, 160, len(t))
    pop = np.sin(2 * np.pi * f * t) * np.exp(-t * 38.0)
    # Soft click impulse
    click = np.sin(2 * np.pi * 1400 * t) * np.exp(-t * 90.0) * 0.25
    signal = pop + click
    return save_wav("soft_pop", signal, 0.85)

# ==========================================
# 8. PLUCK POP (0.2–0.6s) — 👆 إبراز عنصر
# ==========================================
def gen_pluck_pop():
    dur = 0.32
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    # Springy pitch dip then rise
    f = 320.0 + 120.0 * np.sin(np.pi * (t / 0.12)) * (t < 0.12)
    harm1 = np.sin(2 * np.pi * f * t) * np.exp(-t * 18.0)
    harm2 = np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 26.0) * 0.4
    harm3 = np.sin(2 * np.pi * f * 3.0 * t) * np.exp(-t * 35.0) * 0.2
    signal = harm1 + harm2 + harm3
    return save_wav("pluck_pop", signal, 0.80)

# ==========================================
# 9. SOFT DING (0.2–0.8s) — 🔔 معلومة مهمة
# ==========================================
def gen_soft_ding():
    dur = 0.65
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    f0 = 1318.51  # E6
    # Pure crystal bell with natural overtones
    b1 = np.sin(2 * np.pi * f0 * t) * np.exp(-t * 6.5)
    b2 = np.sin(2 * np.pi * f0 * 2.756 * t) * np.exp(-t * 9.5) * 0.35
    b3 = np.sin(2 * np.pi * f0 * 5.404 * t) * np.exp(-t * 14.0) * 0.15
    signal = b1 + b2 + b3
    return save_wav("soft_ding", signal, 0.80)

# ==========================================
# 10. BRIGHT PING (0.1–0.5s) — 🔔 نقطة مهمة جدًا
# ==========================================
def gen_bright_ping():
    dur = 0.35
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    f0 = 2637.02  # E7 (high register, clean focus)
    p1 = np.sin(2 * np.pi * f0 * t) * np.exp(-t * 14.0)
    p2 = np.sin(2 * np.pi * f0 * 2.0 * t) * np.exp(-t * 22.0) * 0.3
    signal = p1 + p2
    return save_wav("bright_ping", signal, 0.80)

# ==========================================
# 11. SOFT IMPACT (0.2–0.7s) — 💥 نهاية جملة قوية
# ==========================================
def gen_soft_impact():
    dur = 0.45
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    # Low warm sub thump (90Hz -> 45Hz)
    f_sub = np.linspace(90, 45, len(t))
    thump = np.sin(2 * np.pi * f_sub * t) * np.exp(-t * 14.0)
    # Muffled tactile touch
    body = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 24.0) * 0.4
    noise = np.random.normal(0, 1, len(t)) * np.exp(-t * 40.0) * 0.2
    signal = thump + body + noise
    return save_wav("soft_impact", signal, 0.80)

# ==========================================
# 12. LIGHT HIT (0.1–0.5s) — 💥 تأكيد بصري
# ==========================================
def gen_light_hit():
    dur = 0.22
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    # Tight snap transient
    snap = np.sin(2 * np.pi * 1600 * t) * np.exp(-t * 60.0) * 0.4
    tap = np.sin(2 * np.pi * 240 * t) * np.exp(-t * 28.0) * 0.7
    noise = np.random.normal(0, 0.5, len(t)) * np.exp(-t * 70.0) * 0.3
    signal = snap + tap + noise
    return save_wav("light_hit", signal, 0.75)

# ==========================================
# 13. REVEAL WHOOSH (0.4–1.2s) — 🔍 كشف معلومة
# ==========================================
def gen_reveal_whoosh():
    dur = 0.85
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    noise = np.random.normal(0, 1, len(t))
    # Swell up to peak at 60% of duration, then smooth decay
    env = np.where(t < 0.55, np.sin(np.pi * (t / 1.1)) ** 2.5, np.cos(np.pi * (t - 0.55) / 0.6) ** 2.0)
    # Chime shimmer at peak
    t_chime = np.maximum(0, t - 0.45)
    shimmer = np.sin(2 * np.pi * 1760 * t_chime) * np.exp(-t_chime * 8.0) * 0.25
    signal = noise * env * 0.65 + shimmer
    return save_wav("reveal_whoosh", signal, 0.78)

# ==========================================
# 14. SHORT STINGER (0.5–1.5s) — ⚡ معلومة مفاجئة
# ==========================================
def gen_short_stinger():
    dur = 1.1
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    # Mystery minor chord: A minor (A3, C4, E4, A4)
    c_a3 = np.sin(2 * np.pi * 220.00 * t) * np.exp(-t * 3.5)
    c_c4 = np.sin(2 * np.pi * 261.63 * t) * np.exp(-t * 4.0) * 0.8
    c_e4 = np.sin(2 * np.pi * 329.63 * t) * np.exp(-t * 4.5) * 0.8
    c_a4 = np.sin(2 * np.pi * 440.00 * t) * np.exp(-t * 5.0) * 0.6
    chord = (c_a3 + c_c4 + c_e4 + c_a4) * 0.25
    # Soft dramatic sub boom
    sub = np.sin(2 * np.pi * 65 * t) * np.exp(-t * 6.0) * 0.4
    signal = chord + sub
    return save_wav("short_stinger", signal, 0.80)

# ==========================================
# 15. SOFT ERROR BEEP (0.1–0.5s) — ❌ تصحيح معلومة
# ==========================================
def gen_soft_error_beep():
    dur = 0.32
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    # Gentle double tone (not harsh buzzer)
    t1 = t[t < 0.14]
    b1 = np.sin(2 * np.pi * 320 * t1) * np.sin(np.pi * (t1 / 0.14)) ** 1.5
    t2 = t[t >= 0.16] - 0.16
    b2 = np.sin(2 * np.pi * 260 * t2) * np.sin(np.pi * (t2 / 0.16)) ** 1.5
    signal = np.zeros(len(t))
    signal[:len(b1)] += b1
    signal[len(t) - len(b2):] += b2
    return save_wav("soft_error_beep", signal, 0.70)

# ==========================================
# 16. SUCCESS DING (0.2–0.7s) — ✅ إجابة / نتيجة
# ==========================================
def gen_success_ding():
    dur = 0.60
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    # Two-tone uplifting major interval (C6 -> G6)
    t_c = t
    n1 = np.sin(2 * np.pi * 1046.50 * t_c) * np.exp(-t_c * 8.0) * 0.7
    t_g = np.maximum(0, t - 0.12)
    n2 = np.sin(2 * np.pi * 1567.98 * t_g) * np.exp(-t_g * 6.0) * (t >= 0.12) * 0.8
    signal = n1 + n2
    return save_wav("success_ding", signal, 0.80)

# ==========================================
# 17. ZOOM WHOOSH (0.3–1s) — 🔎 Camera Zoom
# ==========================================
def gen_zoom_whoosh():
    dur = 0.58
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    noise = np.random.normal(0, 1, len(t))
    # Wide dynamic sweep with low-mid resonance
    env = np.sin(np.pi * (t / dur)) ** 2.2
    f_res = np.linspace(250, 950, len(t))
    tone = np.sin(2 * np.pi * f_res * t * 0.4)
    signal = noise * env * 0.6 + tone * env * 0.4
    return save_wav("zoom_whoosh", signal, 0.75)

# ==========================================
# 18. MAGIC SPARKLE (0.3–1s) — ✨ معلومة مميزة
# ==========================================
def gen_magic_sparkle():
    dur = 0.75
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    # Fast celestial pentatonic arpeggio (C6, E6, G6, B6, D7)
    notes = [1046.50, 1318.51, 1567.98, 1975.53, 2349.32]
    signal = np.zeros(len(t))
    step = 0.08
    for idx, f in enumerate(notes):
        offset = int(idx * step * SR)
        if offset < len(t):
            t_sub = t[offset:] - t[offset]
            sig = np.sin(2 * np.pi * f * t_sub) * np.exp(-t_sub * 7.5) * 0.28
            signal[offset:] += sig
    return save_wav("magic_sparkle", signal, 0.85)

if __name__ == "__main__":
    print(f"Generating all 18 whiteboard sound effects in {OUTPUT_DIR}...")
    gen_pencil_write()
    gen_marker_scribble()
    gen_pencil_stroke()
    gen_marker_stroke()
    gen_soft_whoosh()
    gen_light_whoosh()
    gen_soft_pop()
    gen_pluck_pop()
    gen_soft_ding()
    gen_bright_ping()
    gen_soft_impact()
    gen_light_hit()
    gen_reveal_whoosh()
    gen_short_stinger()
    gen_soft_error_beep()
    gen_success_ding()
    gen_zoom_whoosh()
    gen_magic_sparkle()
    print("All 18 sound effects successfully generated!")

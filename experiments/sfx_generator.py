"""
Procedural Sound Effects (SFX) Synthesizer & Video Audio Sync Engine.
Generates:
1. pop.wav: Cartoon / UI bubble pop sound (Elastic overshoot sync)
2. whoosh.wav: Smooth aerodynamic air whoosh (Slide-in sync)
3. chime.wav: Crystal shimmer / gentle bell (Fade dissolve sync)
4. marker.wav: Realistic whiteboard marker friction (Hand drawing sync)
"""
import os
import math
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

os.makedirs("experiments/sfx", exist_ok=True)
SAMPLE_RATE = 44100


def butter_bandpass_filter(data, lowcut, highcut, fs, order=3):
    nyq = 0.5 * fs
    low = max(0.01, min(0.99, lowcut / nyq))
    high = max(0.01, min(0.99, highcut / nyq))
    b, a = butter(order, [low, high], btype='band')
    return lfilter(b, a, data)


def generate_pop_bubble_sfx(filepath="experiments/sfx/pop_bubble.wav"):
    """Snappy, resonant cartoon bubble pop sound."""
    dur = 0.14  # 140ms
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    
    # Rapid pitch drop after an initial pluck upward
    # Frequency: 400Hz -> 850Hz -> 180Hz
    freq = 400.0 + 450.0 * np.exp(-t * 45.0) - 200.0 * (t / dur)
    phase = 2.0 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    
    # Fast attack, exponential decay
    envelope = np.sin(np.pi * np.clip(t / 0.015, 0, 1) * 0.5) * np.exp(-t * 28.0)
    
    # Add a slight second harmonic for "watery" body
    wave = np.sin(phase) + 0.35 * np.sin(2.0 * phase)
    audio = wave * envelope
    
    # Normalize to 16-bit
    audio = audio / np.max(np.abs(audio) + 1e-6) * 0.85
    wavfile.write(filepath, SAMPLE_RATE, (audio * 32767).astype(np.int16))
    print(f"Generated: {filepath}")
    return filepath


def generate_whoosh_sfx(filepath="experiments/sfx/whoosh.wav"):
    """Smooth, modern UI / motion swipe air whoosh."""
    dur = 0.35  # 350ms
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    
    # Noise generator
    noise = np.random.normal(0, 1, len(t))
    
    # Bell-shaped amplitude envelope
    envelope = np.sin(np.pi * t / dur) ** 2
    
    # Filter sweeping upwards then down
    filtered = butter_bandpass_filter(noise, 250, 2200, SAMPLE_RATE, order=2)
    
    audio = filtered * envelope
    # Soft sine pitch underlay for body
    sub_freq = 150.0 + 120.0 * np.sin(np.pi * t / dur)
    sub_phase = 2.0 * np.pi * np.cumsum(sub_freq) / SAMPLE_RATE
    sub = np.sin(sub_phase) * envelope * 0.4
    
    combined = audio + sub
    combined = combined / np.max(np.abs(combined) + 1e-6) * 0.75
    wavfile.write(filepath, SAMPLE_RATE, (combined * 32767).astype(np.int16))
    print(f"Generated: {filepath}")
    return filepath


def generate_chime_sfx(filepath="experiments/sfx/chime_sparkle.wav"):
    """Gentle crystalline chime shimmer for fade-in dissolve."""
    dur = 0.65  # 650ms
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    
    # Bell harmonics: C6 (1046 Hz), E6 (1318 Hz), G6 (1567 Hz), C7 (2093 Hz)
    freqs = [1046.5, 1318.5, 1567.9, 2093.0]
    weights = [0.4, 0.3, 0.25, 0.15]
    decays = [5.0, 6.0, 7.0, 9.0]
    
    audio = np.zeros_like(t)
    for f, w, d in zip(freqs, weights, decays):
        envelope = np.exp(-t * d)
        audio += w * np.sin(2.0 * np.pi * f * t) * envelope
        
    audio = audio / np.max(np.abs(audio) + 1e-6) * 0.70
    wavfile.write(filepath, SAMPLE_RATE, (audio * 32767).astype(np.int16))
    print(f"Generated: {filepath}")
    return filepath


def generate_marker_friction_sfx(filepath="experiments/sfx/marker_draw.wav", duration=2.0):
    """Realistic marker on whiteboard drawing sound with periodic stroke friction."""
    dur = duration
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    
    noise = np.random.normal(0, 1, len(t))
    # Filter between 800Hz and 4500Hz for plastic nib squeak/scratch
    filtered = butter_bandpass_filter(noise, 800, 4200, SAMPLE_RATE, order=2)
    
    # Modulation representing zig-zag hand movement (3-4 strokes per second)
    stroke_mod = 0.5 + 0.5 * (np.sin(2.0 * np.pi * 3.5 * t) ** 4)
    envelope = np.clip(t / 0.1, 0, 1) * np.clip((dur - t) / 0.1, 0, 1)
    
    audio = filtered * stroke_mod * envelope
    audio = audio / np.max(np.abs(audio) + 1e-6) * 0.55
    wavfile.write(filepath, SAMPLE_RATE, (audio * 32767).astype(np.int16))
    print(f"Generated: {filepath}")
    return filepath


if __name__ == "__main__":
    generate_pop_bubble_sfx()
    generate_whoosh_sfx()
    generate_chime_sfx()
    generate_marker_friction_sfx()

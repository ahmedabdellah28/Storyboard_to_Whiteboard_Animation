import os
import wave
import numpy as np
from scipy.signal import resample

SR = 48000

def load_wav(path, target_sr=SR):
    with wave.open(path, 'rb') as wf:
        orig_sr = wf.getframerate()
        n_frames = wf.getnframes()
        channels = wf.getnchannels()
        raw = wf.readframes(n_frames)
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if channels == 2:
            data = data.reshape(-1, 2).mean(axis=1)
        if orig_sr != target_sr:
            new_len = int(len(data) * target_sr / orig_sr)
            data = resample(data, new_len)
        return data

# 1. Load Voiceover (Paced 79.64s)
vo_path = "project_content/audio/kiwi_voiceover_paced.wav"
vo_audio = load_wav(vo_path, SR)
total_samples = len(vo_audio)
total_dur = total_samples / SR
print(f"Loaded paced voiceover: {total_dur:.2f}s ({total_samples} samples at {SR}Hz)")

# Peak normalize voiceover to -0.5 dB (~0.94)
vo_peak = np.max(np.abs(vo_audio))
if vo_peak > 0:
    vo_audio = vo_audio * (0.94 / vo_peak)

# 2. Load SFX
sfx_marker = load_wav("experiments/sfx/marker_draw.wav", SR)
sfx_whoosh = load_wav("experiments/sfx/whoosh.wav", SR)
sfx_pop = load_wav("experiments/sfx/pop_bubble.wav", SR)
sfx_chime = load_wav("experiments/sfx/chime_sparkle.wav", SR)

# 3. Build SFX Track (Cut by 50% for subtle ambient background elegance: 0.05 - 0.07)
sfx_track = np.zeros(total_samples, dtype=np.float32)

def add_sfx(time_s, clip, gain):
    idx = int(time_s * SR)
    end = min(total_samples, idx + len(clip))
    dur = end - idx
    if dur > 0:
        sfx_track[idx:end] += clip[:dur] * gain

# SFX Cues matched to the 79.64s timeline
# === ROW 1: Origins, China, Gooseberry & Medicine (0.0s - 13.0s) ===
add_sfx(0.2, sfx_marker, 0.06)   # Marker drawing giant kiwi
add_sfx(2.5, sfx_whoosh, 0.06)   # Branch & leaves
add_sfx(3.5, sfx_marker, 0.06)   # Chinese sage
add_sfx(6.0, sfx_pop, 0.065)     # Chinese gooseberry plant
add_sfx(7.8, sfx_pop, 0.06)      # Bowl of wild berries
add_sfx(10.5, sfx_whoosh, 0.065) # Mortar & pestle medicine herbs

# === ROW 2: New Zealand, Seeds & Size Evolution (14.2s - 33.8s) ===
add_sfx(14.5, sfx_marker, 0.06)  # Marker drawing NZ farmer
add_sfx(17.5, sfx_pop, 0.06)     # NZ Map with flag
add_sfx(19.0, sfx_pop, 0.065)    # Seeds sack & open hand
add_sfx(21.5, sfx_pop, 0.06)     # Seedling sprout
add_sfx(23.0, sfx_pop, 0.06)     # Bigger seedling
add_sfx(25.0, sfx_whoosh, 0.065) # Pergola trellis tree with kiwis
# 5 Size evolution sequential pops
add_sfx(27.5, sfx_pop, 0.06)     # Size 1
add_sfx(28.3, sfx_pop, 0.06)     # Size 2
add_sfx(29.1, sfx_pop, 0.06)     # Size 3
add_sfx(30.0, sfx_pop, 0.065)    # Size 4
add_sfx(31.0, sfx_pop, 0.07)     # Size 5 (giant sliced kiwi)

# === ROW 3: Kiwi Bird & Global Shipping (35.0s - 41.4s) ===
add_sfx(35.2, sfx_pop, 0.07)     # Kiwi bird reveal
add_sfx(36.5, sfx_whoosh, 0.065) # Wooden shipping crate
add_sfx(37.8, sfx_whoosh, 0.07)  # Cargo ship across ocean waves
add_sfx(39.2, sfx_pop, 0.065)    # Globe international marketing
add_sfx(40.2, sfx_pop, 0.065)    # Classic green kiwis

# === ROW 4: Scientific Berry, Skin Fiber & Varieties (42.6s - 55.0s) ===
add_sfx(42.8, sfx_pop, 0.065)    # Berry comparison
add_sfx(44.5, sfx_pop, 0.065)    # Microscope on skin fibers
add_sfx(46.5, sfx_whoosh, 0.06)  # Dietary fiber strands
add_sfx(48.0, sfx_pop, 0.06)     # Digestive stomach & intestines
add_sfx(50.0, sfx_pop, 0.065)    # Green kiwi pair
add_sfx(52.0, sfx_pop, 0.07)     # Golden kiwi
add_sfx(53.5, sfx_pop, 0.07)     # Ruby red kiwi

# === ROW 5: Nutrition, Protein Enzymes & Vitamin C (56.2s - 79.64s) ===
add_sfx(56.5, sfx_marker, 0.06)  # Marker drawing man tasting kiwi
add_sfx(59.5, sfx_whoosh, 0.065) # Trio heap of varieties
add_sfx(61.5, sfx_pop, 0.07)     # Artistic red cross section
add_sfx(64.5, sfx_pop, 0.065)    # Protein enzyme splitting molecules
add_sfx(68.5, sfx_chime, 0.07)   # Vitamin C golden burst
add_sfx(72.0, sfx_pop, 0.07)     # Complete nutrition composition finale
add_sfx(75.5, sfx_whoosh, 0.06)  # Camera pullout to full whiteboard

# 4. Ducking and Master Stereo Mixing
vo_envelope = np.abs(vo_audio)
win_len = int(0.12 * SR)
if win_len > 0:
    kernel = np.ones(win_len, dtype=np.float32) / float(win_len)
    vo_envelope = np.convolve(vo_envelope, kernel, mode='same')

duck_gain = np.clip(1.0 - (vo_envelope * 0.45), 0.55, 1.0)
sfx_ducked = sfx_track * duck_gain

left_channel = vo_audio * 0.95 + sfx_ducked * 0.90
right_channel = vo_audio * 0.95 + sfx_ducked * 1.10

stereo_master = np.vstack([left_channel, right_channel]).T

peak = np.max(np.abs(stereo_master))
if peak > 0.96:
    stereo_master = stereo_master * (0.96 / peak)

out_audio_path = "project_content/audio/kiwi_master_ducked_audio_paced.wav"
stereo_int16 = (stereo_master * 32767.0).astype(np.int16)

with wave.open(out_audio_path, 'wb') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(stereo_int16.tobytes())

print(f"SUCCESS: Paced master stereo audio saved to: {out_audio_path}")
print(f"Duration: {total_dur:.2f}s, Peak: {np.max(np.abs(stereo_master)):.3f}")

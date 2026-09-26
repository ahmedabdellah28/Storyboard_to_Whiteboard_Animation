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

# 1. Load Voiceover (58.24s Sweetspot)
vo_path = "project_content/audio/kiwi_voiceover_sweetspot.wav"
vo_audio = load_wav(vo_path, SR)
total_samples = len(vo_audio)
total_dur = total_samples / SR
print(f"Loaded voiceover: {total_dur:.2f}s ({total_samples} samples at {SR}Hz)")

# Peak normalize voiceover to -0.5 dB (~0.94)
vo_peak = np.max(np.abs(vo_audio))
if vo_peak > 0:
    vo_audio = vo_audio * (0.94 / vo_peak)

# 2. Load SFX (marker sound cut by 50% per user request)
sfx_marker = load_wav("production_engine/sfx/marker_draw.wav", SR) * 0.50
sfx_whoosh = load_wav("production_engine/sfx/whoosh.wav", SR)
sfx_pop = load_wav("production_engine/sfx/pop_bubble.wav", SR)
sfx_chime = load_wav("production_engine/sfx/chime_sparkle.wav", SR)

# 3. Build SFX Track (Cut by 50% for subtle ambient background elegance: 0.05 - 0.07)
sfx_track = np.zeros(total_samples, dtype=np.float32)

def add_sfx(time_s, clip, gain):
    idx = int(time_s * SR)
    end = min(total_samples, idx + len(clip))
    dur = end - idx
    if dur > 0:
        sfx_track[idx:end] += clip[:dur] * gain

# SFX Cues matched to the verified sequential timeline
# === PARAGRAPH 1: Origins, China, Gooseberry & Medicine (0.0s - 10.5s) ===
add_sfx(0.0, sfx_marker, 0.06)   # Marker drawing giant kiwi
add_sfx(1.0, sfx_whoosh, 0.06)   # Leaves appear after kiwi is finished
add_sfx(1.5, sfx_marker, 0.06)   # Marker drawing Chinese sage
add_sfx(3.5, sfx_pop, 0.065)     # Chinese gooseberry plant after sage is finished
add_sfx(4.5, sfx_pop, 0.06)      # Bowl of wild berries
add_sfx(7.2, sfx_whoosh, 0.065)  # Mortar & pestle medicine herbs

# === PARAGRAPH 2: New Zealand, Seeds & Size Evolution (10.5s - 18.0s) ===
add_sfx(10.6, sfx_marker, 0.06)  # Marker drawing NZ farmer
add_sfx(12.8, sfx_pop, 0.06)     # NZ Map with flag after farmer is finished
add_sfx(13.5, sfx_pop, 0.065)    # Seeds sack
add_sfx(14.0, sfx_pop, 0.065)    # Hand with seeds
add_sfx(15.1, sfx_pop, 0.06)     # Seedling sprout
add_sfx(15.5, sfx_pop, 0.06)     # Bigger seedling
add_sfx(16.0, sfx_whoosh, 0.065) # Pergola trellis tree (يطورون)
add_sfx(16.8, sfx_pop, 0.07)     # 5 Size evolution cascade

# === PARAGRAPH 3: Kiwi Bird & Global Shipping (18.0s - 25.5s) ===
add_sfx(18.2, sfx_pop, 0.07)     # Kiwi bird reveal (نسبة لطائر الكيوي)
add_sfx(20.0, sfx_whoosh, 0.065) # Wooden shipping crate
add_sfx(20.8, sfx_whoosh, 0.07)  # Cargo ship across ocean waves
add_sfx(22.0, sfx_pop, 0.065)    # Globe international marketing
add_sfx(23.5, sfx_pop, 0.065)    # Classic green kiwis

# === PARAGRAPH 4: Scientific Berry, Skin Fiber & Varieties (25.5s - 48.0s) ===
add_sfx(25.8, sfx_pop, 0.065)    # Berry comparison
add_sfx(29.8, sfx_pop, 0.065)    # Microscope on skin fibers
add_sfx(31.0, sfx_whoosh, 0.06)  # Dietary fiber strands
add_sfx(32.0, sfx_pop, 0.065)    # Digestive gut
add_sfx(34.0, sfx_pop, 0.065)    # Green kiwi pair
add_sfx(40.5, sfx_pop, 0.07)     # Golden kiwi
add_sfx(44.0, sfx_pop, 0.07)     # Ruby red kiwi

# === PARAGRAPH 5: Nutrition, Protein Enzymes & Vitamin C (48.0s - 58.5s) ===
add_sfx(48.2, sfx_marker, 0.06)  # Marker drawing man tasting kiwi
add_sfx(50.4, sfx_whoosh, 0.065) # Trio heap of varieties after man is finished
add_sfx(51.0, sfx_pop, 0.07)     # Artistic red cross section
add_sfx(51.8, sfx_pop, 0.065)    # Protein enzyme splitting molecules
add_sfx(52.8, sfx_chime, 0.07)   # Vitamin C golden burst
add_sfx(54.5, sfx_pop, 0.07)     # Complete nutrition composition finale

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

out_audio_path = "project_content/audio/kiwi_master_ducked_audio_sweetspot.wav"
stereo_int16 = (stereo_master * 32767.0).astype(np.int16)

with wave.open(out_audio_path, 'wb') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(stereo_int16.tobytes())

# Also save to sections/02_kiwi/master_audio.wav
import shutil
shutil.copy(out_audio_path, "sections/02_kiwi/master_audio.wav")

print(f"SUCCESS: Sweetspot master stereo audio saved to: {out_audio_path} and sections/02_kiwi/master_audio.wav")
print(f"Duration: {total_dur:.2f}s, Peak: {np.max(np.abs(stereo_master)):.3f}")

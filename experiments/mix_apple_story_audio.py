import os
import wave
import numpy as np
from scipy.signal import resample

# Output sample rate: 48000Hz (Broadcast Standard)
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

# 1. Load Voiceover
vo_path = "project_content/audio/apple_voiceover.wav"
vo_audio = load_wav(vo_path, SR)
total_samples = len(vo_audio)
total_duration = total_samples / SR
print(f"Loaded voiceover: {total_duration:.2f}s ({total_samples} samples at {SR}Hz)")

# Normalize voiceover to -1.5 dB (approx 0.841 amplitude)
vo_peak = np.max(np.abs(vo_audio))
if vo_peak > 0:
    vo_audio = vo_audio * (0.841 / vo_peak)

# 2. Compute Voice Envelope for Dynamic Sidechain Ducking
# 100ms window smoothing
window_size = int(0.1 * SR)
vo_energy = np.abs(vo_audio)
kernel = np.ones(window_size) / window_size
vo_envelope = np.convolve(vo_energy, kernel, mode='same')
vo_active = np.clip(vo_envelope / 0.05, 0.0, 1.0) # 1.0 when speaking, 0.0 when quiet

# 3. Load SFX
sfx_marker = load_wav("experiments/sfx/marker_draw.wav", SR)
sfx_whoosh = load_wav("experiments/sfx/whoosh.wav", SR)
sfx_pop = load_wav("experiments/sfx/pop_bubble.wav", SR)
sfx_chime = load_wav("experiments/sfx/chime_sparkle.wav", SR)

# SFX Cue Sheet matching the 5 Acts
sfx_cues = [
    # Act 1: Origins & Wild Apples (0 - 15s)
    (0.4, sfx_marker, 0.8),    # Giant red apple drawing
    (3.8, sfx_pop, 0.7),       # Wild sour apple pop
    (5.2, sfx_whoosh, 0.6),    # Wild branch whoosh
    (7.0, sfx_pop, 0.5),       # Apple blossom
    (8.5, sfx_whoosh, 0.7),    # Snowy mountains slide in
    (11.2, sfx_pop, 0.6),      # Central Asia map

    # Act 2: Roman Era & Cultivation (15 - 32s)
    (15.5, sfx_marker, 0.8),   # Roman soldier drawing
    (17.5, sfx_whoosh, 0.6),   # Europe map slide
    (19.8, sfx_whoosh, 0.7),   # Horse cart moving across
    (24.2, sfx_marker, 0.8),   # Farmer planting
    (27.0, sfx_pop, 0.6),      # Tree stage 1
    (28.0, sfx_pop, 0.6),      # Tree stage 2
    (29.0, sfx_pop, 0.6),      # Tree stage 3
    (30.2, sfx_pop, 0.7),      # Tree stage 4 (mature)

    # Act 3: Evolution & Diversity (32 - 46s)
    (33.0, sfx_pop, 0.6),      # Evolution scale 1
    (34.0, sfx_pop, 0.6),      # Evolution scale 2
    (35.2, sfx_pop, 0.7),      # Evolution scale 3
    (38.0, sfx_whoosh, 0.6),   # Hand reaching for apple
    (39.0, sfx_chime, 0.6),    # Apple picked
    (41.2, sfx_pop, 0.5),      # Red apple variety
    (41.8, sfx_pop, 0.5),      # Green apple variety
    (42.4, sfx_pop, 0.5),      # Yellow apple variety
    (43.0, sfx_pop, 0.5),      # Dark apple variety
    (43.6, sfx_pop, 0.6),      # Striped apple variety

    # Act 4: Harvest & Juice (46 - 54s)
    (46.2, sfx_whoosh, 0.6),   # Harvest crate
    (47.5, sfx_chime, 0.8),    # Sliced apple & golden juice splash
    (49.5, sfx_pop, 0.6),      # Farmer inspecting
    (50.8, sfx_pop, 0.6),      # Checkbox 1 (green check)
    (51.4, sfx_pop, 0.6),      # Checkbox 2 (green check)
    (52.0, sfx_pop, 0.6),      # Checkbox 3 (green check)
    (52.6, sfx_pop, 0.5),      # Checkbox 4 (red X)

    # Act 5: Health & Grand Outro (54 - 60.88s)
    (54.2, sfx_whoosh, 0.6),   # Digestive gut
    (55.0, sfx_pop, 0.6),      # Vitamins bubbles
    (55.8, sfx_pop, 0.7),      # Heart pulse
    (56.8, sfx_whoosh, 0.8),   # Modern refrigerator reveal
    (58.2, sfx_chime, 0.9),    # Grand Outro reveal
]

sfx_track = np.zeros(total_samples, dtype=np.float32)

for time_sec, sfx_clip, gain in sfx_cues:
    start_sample = int(time_sec * SR)
    end_sample = min(total_samples, start_sample + len(sfx_clip))
    clip_len = end_sample - start_sample
    if clip_len > 0:
        sfx_track[start_sample:end_sample] += sfx_clip[:clip_len] * gain

# Apply Dynamic Sidechain Ducking:
# Base SFX level: -18 dB (gain ~ 0.126)
# When voice is active, duck by additional -4 dB (total -22 dB, gain ~ 0.079)
base_gain = 0.126
ducked_gain = 0.079
dynamic_sfx_gain = base_gain * (1.0 - vo_active) + ducked_gain * vo_active

ducked_sfx = sfx_track * dynamic_sfx_gain

# Master Mix (Voiceover + Ducked SFX)
master_mix = vo_audio + ducked_sfx
# Hard clip protection
master_mix = np.clip(master_mix, -0.99, 0.99)

out_audio_path = "project_content/audio/apple_master_ducked_audio.wav"
os.makedirs("project_content/audio", exist_ok=True)

# Save as 16-bit 48kHz WAV
int_audio = (master_mix * 32767.0).astype(np.int16)
with wave.open(out_audio_path, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(int_audio.tobytes())

print(f"Successfully generated master ducked audio: {out_audio_path} ({total_duration:.2f}s)")

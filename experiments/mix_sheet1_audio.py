import os
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

ROOT_DIR = r"E:\image_to_animate"
audio_path = os.path.join(ROOT_DIR, "project_content", "audio", "sheet1_master_audio.wav")
sfx_dir = os.path.join(ROOT_DIR, "experiments", "sfx")

# Load voiceover master
sr_orig, speech_raw = wavfile.read(audio_path)
print(f"Loaded voiceover: sr={sr_orig}, len={len(speech_raw)} samples ({len(speech_raw)/sr_orig:.2f}s)")

# Target standard 44100Hz stereo
target_sr = 44100
total_len_sec = len(speech_raw) / float(sr_orig)
total_samples = int(round(total_len_sec * target_sr))

# Resample speech to target_sr
from scipy.signal import resample
num_target_speech = int(round(len(speech_raw) * (target_sr / float(sr_orig))))
speech_44k = resample(speech_raw.astype(np.float32), num_target_speech)

# Convert to stereo
if speech_44k.ndim == 1:
    speech_stereo = np.column_stack([speech_44k, speech_44k])
else:
    speech_stereo = speech_44k

# Peak normalize speech to -1.5dB (0.841)
peak = np.max(np.abs(speech_stereo))
if peak > 0:
    speech_stereo = speech_stereo * (0.841 / peak)

# Load SFX library
def load_sfx(filename):
    p = os.path.join(sfx_dir, filename)
    sr, data = wavfile.read(p)
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    # resample if needed
    if sr != target_sr:
        num_s = int(round(len(data) * (target_sr / float(sr))))
        data = resample(data, num_s)
    if data.ndim == 1:
        data = np.column_stack([data, data])
    return data

sfx_whoosh = load_sfx("whoosh.wav")
sfx_pop = load_sfx("pop_bubble.wav")
sfx_chime = load_sfx("chime_sparkle.wav")
sfx_marker = load_sfx("marker_draw.wav")

# Master SFX Track
sfx_track = np.zeros((total_samples, 2), dtype=np.float32)

def add_sfx(clip, start_sec, volume=1.0):
    start_sample = int(round(start_sec * target_sr))
    end_sample = min(total_samples, start_sample + len(clip))
    clip_len = end_sample - start_sample
    if clip_len > 0:
        sfx_track[start_sample:end_sample] += clip[:clip_len] * volume

# DIRECTORIAL SFX SCHEDULE (Exact synchronized beats):
# Panel 1:
add_sfx(sfx_marker, 0.5, volume=0.45)
add_sfx(sfx_whoosh, 4.8, volume=0.60)
add_sfx(sfx_pop, 8.2, volume=0.75)
add_sfx(sfx_chime, 9.5, volume=0.70)
# Pan P1->P2
add_sfx(sfx_whoosh, 14.2, volume=0.50)

# Panel 2:
add_sfx(sfx_marker, 15.4, volume=0.45)
add_sfx(sfx_whoosh, 20.8, volume=0.60)
add_sfx(sfx_whoosh, 23.0, volume=0.55)
add_sfx(sfx_whoosh, 25.5, volume=0.60)
add_sfx(sfx_pop, 28.5, volume=0.80)
add_sfx(sfx_chime, 28.6, volume=0.70)
# Pan P2->P3
add_sfx(sfx_whoosh, 33.5, volume=0.50)

# Panel 3:
add_sfx(sfx_marker, 34.8, volume=0.45)
add_sfx(sfx_marker, 40.5, volume=0.45)
add_sfx(sfx_chime, 44.5, volume=0.65)
add_sfx(sfx_chime, 45.5, volume=0.65)
# S-Curve Crane Swoop P3->P4
add_sfx(sfx_whoosh, 47.0, volume=0.70)

# Panel 4:
add_sfx(sfx_marker, 49.0, volume=0.45)
add_sfx(sfx_whoosh, 58.0, volume=0.60)
# Pan P4->P5
add_sfx(sfx_whoosh, 70.0, volume=0.50)

# Panel 5:
add_sfx(sfx_marker, 71.2, volume=0.45)
add_sfx(sfx_pop, 75.6, volume=0.75)
add_sfx(sfx_pop, 76.2, volume=0.75)
add_sfx(sfx_pop, 76.8, volume=0.75)
add_sfx(sfx_pop, 77.4, volume=0.75)
add_sfx(sfx_pop, 78.0, volume=0.75)
add_sfx(sfx_pop, 78.6, volume=0.75)
# Pan P5->P6
add_sfx(sfx_whoosh, 80.0, volume=0.50)

# Panel 6:
add_sfx(sfx_marker, 81.2, volume=0.45)
add_sfx(sfx_chime, 84.8, volume=0.70)
# Grand Outro Reveal Zoom-out:
add_sfx(sfx_whoosh, 85.8, volume=0.65)

# High-Pass Filter on SFX (120Hz)
b, a = butter(2, 120.0 / (target_sr / 2.0), btype='high')
sfx_track[:, 0] = lfilter(b, a, sfx_track[:, 0])
sfx_track[:, 1] = lfilter(b, a, sfx_track[:, 1])

# Dynamic Sidechain Ducking (-18dB baseline + -4dB during speech)
base_sfx_gain = 0.125  # ~ -18dB
speech_mono = np.abs(speech_stereo[:, 0])
win_size = int(0.08 * target_sr)  # 80ms smoothing window
kernel = np.ones(win_size, dtype=np.float32) / win_size
speech_env = np.convolve(speech_mono, kernel, mode='same')
duck_factor = np.where(speech_env > 0.05, 0.63, 1.0)  # additional -4dB when speech active
duck_factor = np.column_stack([duck_factor, duck_factor])

sfx_ducked = sfx_track * base_sfx_gain * duck_factor

# Final Master Mix
final_mix = speech_stereo[:total_samples] + sfx_ducked

# Prevent any digital clipping
max_val = np.max(np.abs(final_mix))
if max_val > 0.95:
    final_mix = final_mix * (0.95 / max_val)

out_wav = os.path.join(sfx_dir, "sheet_01_master_audio_mixed.wav")
wavfile.write(out_wav, target_sr, (final_mix * 32767).astype(np.int16))
print(f"Successfully generated Master Audio Mix: {out_wav} ({total_len_sec:.2f}s, 44.1kHz stereo)")

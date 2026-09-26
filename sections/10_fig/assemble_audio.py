import os
import sys
import wave
import numpy as np
from scipy.signal import resample

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.mix_section_audio import mix_section_audio

SR = 48000
TARGET_DURATION = 68.0

def load_wav_as_mono(path, target_sr=SR):
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

audio_dir = r"sections/10_fig/scratch/row_audio"
row_files = [
    (0.5, os.path.join(audio_dir, "row_1.wav")),
    (19.3, os.path.join(audio_dir, "row_2.wav")),
    (36.6, os.path.join(audio_dir, "row_3.wav")),
    (52.4, os.path.join(audio_dir, "row_4.wav")),
]

total_samples = int(TARGET_DURATION * SR)
master_vo = np.zeros(total_samples, dtype=np.float32)

for start_time, r_path in row_files:
    clip = load_wav_as_mono(r_path, SR)
    st_idx = int(start_time * SR)
    end_idx = min(total_samples, st_idx + len(clip))
    dur = end_idx - st_idx
    if dur > 0:
        master_vo[st_idx:end_idx] = clip[:dur]
        print(f"Placed {os.path.basename(r_path)} at {start_time:.2f}s -> {start_time + len(clip)/SR:.2f}s")

# Save voiceover.wav
vo_path = r"sections/10_fig/voiceover.wav"
vo_int16 = (np.clip(master_vo, -0.98, 0.98) * 32767.0).astype(np.int16)
with wave.open(vo_path, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(vo_int16.tobytes())

print(f"\nVoiceover generated: {vo_path} ({TARGET_DURATION:.2f}s)")

# Define SFX cues
sfx_cues = [
    # Inking markers
    (0.5, "marker", 0.45),
    (12.0, "marker", 0.45),
    (19.3, "marker", 0.45),
    (31.5, "marker", 0.45),
    (38.2, "marker", 0.45),
    (52.4, "marker", 0.45),
    (60.0, "marker", 0.45),

    # Whoosh pans
    (8.5, "whoosh", 0.65),
    (18.2, "whoosh", 0.70),
    (26.5, "whoosh", 0.65),
    (35.5, "whoosh", 0.70),
    (43.0, "whoosh", 0.65),
    (51.3, "whoosh", 0.70),
    (59.0, "whoosh", 0.65),

    # Pop & chime cues
    (4.2, "pop", 0.40),
    (6.0, "chime", 0.35),
    (9.5, "pop", 0.40),
    (23.0, "chime", 0.35),
    (27.5, "pop", 0.40),
    (29.5, "pop", 0.40),
    (36.6, "pop", 0.40),
    (44.0, "pop", 0.40),
    (45.8, "chime", 0.35),
    (47.8, "pop", 0.40),
    (56.5, "chime", 0.35),
    (64.2, "chime", 0.35),
]

master_audio_path = r"sections/10_fig/master_audio.wav"
mix_section_audio(
    voiceover_path=vo_path,
    sfx_cues=sfx_cues,
    output_audio_path=master_audio_path,
    target_duration_s=TARGET_DURATION
)
print("Section 10 Fig audio mixed successfully!")

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

# 1. Load Voiceover
vo_path = "project_content/audio/kiwi_voiceover.wav"
vo_audio = load_wav(vo_path, SR)
total_samples = len(vo_audio)
total_dur = total_samples / SR
print(f"Loaded voiceover: {total_dur:.2f}s ({total_samples} samples at {SR}Hz)")

# Peak normalize voiceover to -0.5 dB (~0.94)
vo_peak = np.max(np.abs(vo_audio))
if vo_peak > 0:
    vo_audio = vo_audio * (0.94 / vo_peak)

# 2. Load SFX
sfx_marker = load_wav("experiments/sfx/marker_draw.wav", SR)
sfx_whoosh = load_wav("experiments/sfx/whoosh.wav", SR)
sfx_pop = load_wav("experiments/sfx/pop_bubble.wav", SR)
sfx_chime = load_wav("experiments/sfx/chime_sparkle.wav", SR)

# 3. Build SFX Track (Cut by 50% for subtle ambient background elegance)
sfx_track = np.zeros(total_samples, dtype=np.float32)

def add_sfx(time_s, clip, gain):
    idx = int(time_s * SR)
    end = min(total_samples, idx + len(clip))
    dur = end - idx
    if dur > 0:
        sfx_track[idx:end] += clip[:dur] * gain

# SFX Cues matched WORD-FOR-WORD to the Kiwi narrative
# Row 1: Origins, China, Gooseberry & Medicine (0.0s - 6.5s)
add_sfx(0.2, sfx_marker, 0.06)   # Marker drawing giant kiwi ("الكيوي")
add_sfx(1.2, sfx_whoosh, 0.06)   # Whoosh branch & leaves
add_sfx(1.8, sfx_marker, 0.06)   # Drawing Chinese sage ("أصله من الصين")
add_sfx(2.6, sfx_pop, 0.065)     # Pop Chinese gooseberry plant ("عنب الثعلب الصيني")
add_sfx(3.3, sfx_pop, 0.06)      # Pop bowl of wild berries
add_sfx(4.8, sfx_whoosh, 0.065)  # Whoosh mortar & pestle herbs ("غذاء وحتى كدواء")

# Row 2: New Zealand, Seeds & Size Evolution (6.5s - 11.8s)
add_sfx(8.1, sfx_marker, 0.06)   # Marker drawing NZ farmer ("المزارعين في نيوزيلندا")
add_sfx(8.8, sfx_pop, 0.06)      # NZ Map with flag
add_sfx(9.3, sfx_pop, 0.065)     # Seeds sack & open hand ("حصلوا على بذوره")
add_sfx(10.1, sfx_pop, 0.06)     # Seedling growth stages
add_sfx(10.7, sfx_whoosh, 0.065) # Pergola trellis tree with kiwis
# 5 Size evolution sequential pops ("يطورون النوع اللي نعرفه اليوم")
add_sfx(11.1, sfx_pop, 0.06)     # Size 1
add_sfx(11.3, sfx_pop, 0.06)     # Size 2
add_sfx(11.5, sfx_pop, 0.06)     # Size 3
add_sfx(11.7, sfx_pop, 0.065)    # Size 4
add_sfx(11.9, sfx_pop, 0.07)     # Size 5 (giant sliced kiwi)

# Row 3: Kiwi Bird, Renaming & Global Export (11.8s - 17.0s)
add_sfx(12.0, sfx_pop, 0.07)     # Kiwi bird reveal ("نسبة لطائر الكيوي النيوزيلندي")
add_sfx(13.5, sfx_whoosh, 0.065) # Wooden shipping crate
add_sfx(14.2, sfx_whoosh, 0.07)  # Cargo ship across ocean waves ("تسويقه أسهل حول العالم")
add_sfx(15.2, sfx_pop, 0.065)    # Globe orbit arrows
add_sfx(16.0, sfx_pop, 0.07)     # Classic green kiwis cluster

# Row 4: Scientific Berry, Skin Fiber & Varieties (17.0s - 27.8s)
add_sfx(18.0, sfx_pop, 0.065)    # Berries comparison ("علمياً يعتبر نوعاً من التوت")
add_sfx(20.5, sfx_pop, 0.065)    # Magnifying glass on hairy skin ("وحتى القشرة تقدر تأكلها")
add_sfx(21.9, sfx_whoosh, 0.065) # Dietary fiber & digestive gut ("لأنها مليانة ألياف")
add_sfx(23.6, sfx_pop, 0.065)    # Green kiwi pair ("الكيوي الأخضر")
add_sfx(25.3, sfx_pop, 0.07)     # Golden kiwi pair ("الكيوي الذهبي")
add_sfx(26.5, sfx_pop, 0.07)     # Red kiwi pair ("والأحمر")

# Row 5: Nutrition, Protein Enzymes & Vitamin C (27.8s - 41.18s)
add_sfx(28.0, sfx_marker, 0.06)  # Marker drawing man tasting kiwi ("طعمه أحلى")
add_sfx(30.0, sfx_pop, 0.065)    # Trio kiwi heap
add_sfx(31.3, sfx_chime, 0.08)   # Ruby red artistic cross-section ("تصميم فني")
add_sfx(33.6, sfx_whoosh, 0.07)  # Enzyme breaking protein molecules ("تكسير البروتين")
add_sfx(36.5, sfx_chime, 0.08)   # Glowing golden Vitamin C burst ("غني بفيتامين سي")
add_sfx(38.5, sfx_pop, 0.07)     # Complete nutrition grand finale cluster ("تركيبه الغذائي مختلف")
add_sfx(40.5, sfx_chime, 0.08)   # Grand Outro reveal pullout

# 4. Master Stereo Mix (2 Channels)
left_ch = vo_audio * 1.0 + sfx_track * 0.95
right_ch = vo_audio * 1.0 + sfx_track * 1.05

stereo = np.column_stack([left_ch, right_ch])
max_val = np.max(np.abs(stereo))
if max_val > 0.98:
    stereo = stereo * (0.98 / max_val)

out_audio_path = "project_content/audio/kiwi_master_ducked_audio.wav"
int_audio = (stereo * 32767.0).astype(np.int16)

with wave.open(out_audio_path, 'wb') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(int_audio.tobytes())

print(f"Generated pristine STEREO audio mix: {out_audio_path}")
print(f"Duration: {total_dur:.2f}s, Max Peak: {np.max(np.abs(stereo)):.2f}, Channels: 2")

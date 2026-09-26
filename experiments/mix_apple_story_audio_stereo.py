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
vo_path = "project_content/audio/apple_voiceover.wav"
vo_audio = load_wav(vo_path, SR)
total_samples = len(vo_audio)
total_dur = total_samples / SR

# Peak normalize voiceover to -0.5 dB (~0.94)
vo_peak = np.max(np.abs(vo_audio))
if vo_peak > 0:
    vo_audio = vo_audio * (0.94 / vo_peak)

# 2. Load SFX
sfx_marker = load_wav("experiments/sfx/marker_draw.wav", SR)
sfx_whoosh = load_wav("experiments/sfx/whoosh.wav", SR)
sfx_pop = load_wav("experiments/sfx/pop_bubble.wav", SR)
sfx_chime = load_wav("experiments/sfx/chime_sparkle.wav", SR)

# 3. Build SFX Track with subtle, gentle ambient volume levels (Cut by 50% as requested)
sfx_track = np.zeros(total_samples, dtype=np.float32)

def add_sfx(time_s, clip, gain):
    idx = int(time_s * SR)
    end = min(total_samples, idx + len(clip))
    dur = end - idx
    if dur > 0:
        sfx_track[idx:end] += clip[:dur] * gain

# SFX Cues matched WORD-FOR-WORD to the narrative
# Act 1: Origins & Wild Fruits
add_sfx(0.25, sfx_marker, 0.06)  # Marker drawing giant apple ("التفاح")
add_sfx(1.8, sfx_pop, 0.065)     # Pop wild apple ("أشهر فاكهة في العالم")
add_sfx(3.2, sfx_whoosh, 0.06)   # Whoosh branch ("خصوصاً في المناطق الباردة")
add_sfx(4.8, sfx_pop, 0.06)      # Pop flower ("لكن الغريب إن التفاح")
add_sfx(6.9, sfx_pop, 0.065)     # Blooming apple tree ("من الغابات البرية")
add_sfx(9.5, sfx_whoosh, 0.065)  # Whoosh snowy mountains ("قريب من جبال القوقاز")
add_sfx(11.0, sfx_pop, 0.065)    # Pop Central Asia map ("في آسيا الوسطى")

# Act 2: Roman Era & Cultivation
add_sfx(14.3, sfx_marker, 0.065) # Marker drawing Roman soldier ("للإمبراطورية الرومانية")
add_sfx(18.2, sfx_whoosh, 0.06)  # Whoosh Europe map ("أخذوا الفاكهة معهم لأوروبا")
add_sfx(19.0, sfx_whoosh, 0.065) # Horse cart journey across map
add_sfx(20.6, sfx_marker, 0.06)  # Marker drawing farmer planting ("بدأ المزارعين يزرعونها")
# 4 Tree stages sequential pops ("ويحسنون جودتها جيل بعد جيل")
add_sfx(22.5, sfx_pop, 0.06)     # Tree stage 1 (sprout)
add_sfx(23.0, sfx_pop, 0.06)     # Tree stage 2 (young tree)
add_sfx(23.6, sfx_pop, 0.065)    # Tree stage 3 (bushy tree)
add_sfx(24.2, sfx_pop, 0.07)     # Tree stage 4 (mature full tree)

# Act 3: 180-Degree Evolution & Diversity
# 3 Evolution scale stages ("يختلف تقريباً 180 درجة عن النسخ القديمة")
add_sfx(25.3, sfx_pop, 0.06)     # Evolution 1 (sour ancient apple)
add_sfx(27.0, sfx_pop, 0.065)    # Evolution 2 (growth arrow)
add_sfx(28.5, sfx_pop, 0.07)     # Evolution 3 (giant honeycrisp)
add_sfx(36.0, sfx_whoosh, 0.06)  # Hand reach ("استمر آلاف السنين")
add_sfx(38.0, sfx_chime, 0.07)   # Picking apple ("يختارون أفضل الثمار")
# 5 Varieties sequential pops ("لين طلع لنا آلاف الأنواع الحديثة")
add_sfx(40.9, sfx_pop, 0.06)     # Apple variety 1
add_sfx(41.5, sfx_pop, 0.06)     # Apple variety 2
add_sfx(42.1, sfx_pop, 0.06)     # Apple variety 3
add_sfx(42.7, sfx_pop, 0.06)     # Apple variety 4
add_sfx(43.3, sfx_pop, 0.065)    # Apple variety 5

# Act 4: Harvest Crate, Sliced Apples & Quality
add_sfx(45.1, sfx_whoosh, 0.06)  # Seedling cycle ("ومن ناحية الفوائد")
add_sfx(46.2, sfx_whoosh, 0.065) # Harvest crate
add_sfx(48.0, sfx_chime, 0.08)   # Sliced apple & golden juice burst ("غني بالألياف")
add_sfx(49.3, sfx_pop, 0.065)    # Farmer inspecting ("تساعد على الهضم")
# 4 Checkmarks sequential pops
add_sfx(50.2, sfx_pop, 0.065)    # Checkmark 1
add_sfx(50.5, sfx_pop, 0.065)    # Checkmark 2
add_sfx(50.8, sfx_pop, 0.065)    # Checkmark 3
add_sfx(51.1, sfx_pop, 0.06)     # Red X checkmark

# Act 5: Health Benefits & Modern Refrigerator
add_sfx(51.6, sfx_whoosh, 0.065) # Digestive system ("فيتامينات")
add_sfx(52.4, sfx_pop, 0.065)    # Vitamins bubbles
add_sfx(53.2, sfx_pop, 0.07)     # Heartbeat ("عناصر غذائية")
add_sfx(54.8, sfx_whoosh, 0.065) # Wheat fiber ("باختصار")
add_sfx(55.5, sfx_pop, 0.065)    # Harvest pile
add_sfx(56.5, sfx_whoosh, 0.07)  # Refrigerator open ("في الثلاجة اليوم")
add_sfx(58.5, sfx_chime, 0.08)   # Grand Outro reveal ("رحلة عمرها آلاف السنين")

# 4. Master Stereo Mix (2 Channels)
# Voiceover is full volume in center, subtle SFX widened in stereo
left_ch = vo_audio * 1.0 + sfx_track * 0.95
right_ch = vo_audio * 1.0 + sfx_track * 1.05

# Peak limiter to avoid any clipping
stereo = np.column_stack([left_ch, right_ch])
max_val = np.max(np.abs(stereo))
if max_val > 0.98:
    stereo = stereo * (0.98 / max_val)

out_audio_path = "project_content/audio/apple_master_ducked_audio.wav"
int_audio = (stereo * 32767.0).astype(np.int16)

with wave.open(out_audio_path, 'wb') as wf:
    wf.setnchannels(2) # STEREO
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(int_audio.tobytes())

print(f"Generated pristine STEREO audio mix: {out_audio_path}")
print(f"Duration: {total_dur:.2f}s, Max Peak: {np.max(np.abs(stereo)):.2f}, Channels: 2")

import os
import sys
import wave
import cv2
import numpy as np
import subprocess
import time

# Safe console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("=====================================================================================")
print("  🎬 SEAMLESS WHITEBOARD MASTER ENGINE 2026 — MULTI-SECTION DISSOLVE MERGER 🎬")
print("=====================================================================================")

WIDTH, HEIGHT = 1920, 1080
FPS = 30
SR = 48000

# Sequence of sections to merge
sections = [
    {
        'id': '01_apple',
        'title': 'Apple (التفاح)',
        'video': 'sections/01_apple/final_whiteboard_1080p.mp4',
        'audio': 'sections/01_apple/master_audio.wav'
    },
    {
        'id': '02_kiwi',
        'title': 'Kiwi (الكيوي)',
        'video': 'sections/02_kiwi/final_whiteboard_1080p.mp4',
        'audio': 'sections/02_kiwi/master_audio.wav'
    },
    {
        'id': '03_lemon',
        'title': 'Lemon (الليمون)',
        'video': 'sections/03_lemon/final_whiteboard_1080p.mp4',
        'audio': 'sections/03_lemon/master_audio.wav'
    },
    {
        'id': '04_pineapple',
        'title': 'Pineapple (الأناناس)',
        'video': 'sections/04_pineapple/final_whiteboard_1080p.mp4',
        'audio': 'sections/04_pineapple/master_audio.wav'
    },
    {
        'id': '05_pomegranate',
        'title': 'Pomegranate (الرمان)',
        'video': 'sections/05_pomegranate/final_whiteboard_1080p.mp4',
        'audio': 'sections/05_pomegranate/master_audio.wav'
    },
    {
        'id': '06_mango',
        'title': 'Mango (المانجو)',
        'video': 'sections/06_mango/final_whiteboard_1080p.mp4',
        'audio': 'sections/06_mango/master_audio.wav'
    },
    {
        'id': '07_dates',
        'title': 'Dates (التمر)',
        'video': 'sections/07_dates/final_whiteboard_1080p.mp4',
        'audio': 'sections/07_dates/master_audio.wav'
    },
    {
        'id': '08_miracle_fruit',
        'title': 'Miracle Fruit (الفاكهة المعجزة)',
        'video': 'sections/08_miracle_fruit/final_whiteboard_1080p.mp4',
        'audio': 'sections/08_miracle_fruit/master_audio.wav'
    },
    {
        'id': '09_dragon_fruit',
        'title': 'Dragon Fruit (فاكهة التنين)',
        'video': 'sections/09_dragon_fruit/final_whiteboard_1080p.mp4',
        'audio': 'sections/09_dragon_fruit/master_audio.wav'
    },
    {
        'id': '10_fig',
        'title': 'Fig (التين)',
        'video': 'sections/10_fig/final_whiteboard_1080p.mp4',
        'audio': 'sections/10_fig/master_audio.wav'
    },
    {
        'id': '11_jabuticaba',
        'title': 'Jabuticaba (الجابوتيكابا)',
        'video': 'sections/11_jabuticaba/final_whiteboard_1080p.mp4',
        'audio': 'sections/11_jabuticaba/master_audio.wav',
        'deliverable_name': '11_Jabuticaba_Whiteboard_1080p.mp4'
    },
    {
        'id': '12_outro',
        'title': 'Outro (الخاتمة)',
        'video': 'sections/12_outro/final_whiteboard_1080p.mp4',
        'audio': 'sections/12_outro/master_audio.wav',
        'deliverable_name': '12_Outro_Whiteboard_1080p.mp4'
    }
]

# Set semantic deliverable names for earlier sections if missing
for sec in sections:
    if 'deliverable_name' not in sec:
        clean_name = sec['title'].split('(')[0].strip().replace(' ', '_')
        sec['deliverable_name'] = f"{sec['id'][:2]}_{clean_name}_Whiteboard_1080p.mp4"

# Project Identity & Semantic Naming
PROJECT_SLUG = "12_strangest_fruits_documentary"
PROJECT_TITLE = "12_Strangest_Fruits_Whiteboard_Master_1080p"
PROJECT_ARABIC_NAME = "أغرب 11 فاكهة في العالم + الخاتمة"

whoosh_path = "production_engine/sfx/whoosh.wav"

BASE_OUT_DIR = os.path.join("output_animations", PROJECT_SLUG)
DELIVERABLES_DIR = os.path.join(BASE_OUT_DIR, "deliverables")
SECTIONS_DELIVERABLES_DIR = os.path.join(DELIVERABLES_DIR, "sections")
SCRATCH_DIR = os.path.join(BASE_OUT_DIR, "scratch")

os.makedirs(DELIVERABLES_DIR, exist_ok=True)
os.makedirs(SECTIONS_DELIVERABLES_DIR, exist_ok=True)
os.makedirs(SCRATCH_DIR, exist_ok=True)

# Temporary buffers strictly inside scratch/
temp_raw_mp4 = os.path.join(SCRATCH_DIR, "temp_raw_video.mp4")
temp_audio_wav = os.path.join(SCRATCH_DIR, "temp_merged_audio.wav")

# Final Deliverables
final_output_mp4 = os.path.join(DELIVERABLES_DIR, f"{PROJECT_TITLE}.mp4")
final_master_audio_wav = os.path.join(DELIVERABLES_DIR, f"{PROJECT_TITLE.replace('_1080p', '')}_Master_Audio.wav")
legacy_output_mp4 = "output_animations/master_whiteboard_continuous_2026.mp4"

def load_stereo_wav(path, target_sr=SR):
    with wave.open(path, 'rb') as wf:
        orig_sr = wf.getframerate()
        n_frames = wf.getnframes()
        channels = wf.getnchannels()
        raw = wf.readframes(n_frames)
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if channels == 1:
            data = np.column_stack([data, data])
        elif channels == 2:
            data = data.reshape(-1, 2)
        elif channels > 2:
            data = data.reshape(-1, channels)[:, :2]
        return data

# 1. Build Multi-Section Audio with Micro-Pause and Whoosh
print(f"\n1. Building seamless continuous audio track across {len(sections)} sections...")
whoosh = load_stereo_wav(whoosh_path)
pause_samples = int(0.20 * SR) # 0.2s pure pause between sections
pause_silence = np.zeros((pause_samples, 2), dtype=np.float32)

audio_segments = []
for idx, sec in enumerate(sections):
    aud = load_stereo_wav(sec['audio'])
    audio_segments.append(aud)
    if idx < len(sections) - 1:
        audio_segments.append(pause_silence)

combined_audio = np.vstack(audio_segments)

# Insert whoosh sound at each transition point
cur_sample = 0
for idx in range(len(sections) - 1):
    sec_audio_len = len(load_stereo_wav(sections[idx]['audio']))
    cur_sample += sec_audio_len
    # Place whoosh 0.35s before section end across the dissolve
    w_start = cur_sample - int(0.35 * SR)
    w_end = min(len(combined_audio), w_start + len(whoosh))
    dur = w_end - w_start
    if dur > 0:
        combined_audio[w_start:w_end] += whoosh[:dur] * 0.08
    cur_sample += pause_samples

# Peak normalize to -0.2 dB
peak = np.max(np.abs(combined_audio))
if peak > 0.98:
    combined_audio = combined_audio * (0.98 / peak)

trans_int16 = (combined_audio * 32767.0).astype(np.int16)
with wave.open(temp_audio_wav, 'wb') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(trans_int16.tobytes())

total_audio_sec = len(combined_audio) / float(SR)
print(f"Master continuous audio created: {temp_audio_wav} ({total_audio_sec:.2f}s)")

# 2. Setup Video Streaming with Dissolve Through White
print("\n2. Streaming video frames with smooth dissolve-through-white transitions...")
nvenc_cmd = [
    "ffmpeg", "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-s", f"{WIDTH}x{HEIGHT}",
    "-pix_fmt", "bgr24",
    "-r", str(FPS),
    "-i", "-",
    "-c:v", "h264_nvenc",
    "-preset", "p7",
    "-cq", "18",
    "-bf", "2",
    "-pix_fmt", "yuv420p",
    "-profile:v", "high",
    "-level:v", "4.1",
    "-g", "60",
    "-keyint_min", "30",
    "-colorspace", "bt709",
    "-color_trc", "bt709",
    "-color_primaries", "bt709",
    temp_raw_mp4
]

libx264_fallback = [
    "ffmpeg", "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-s", f"{WIDTH}x{HEIGHT}",
    "-pix_fmt", "bgr24",
    "-r", str(FPS),
    "-i", "-",
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-crf", "18",
    "-pix_fmt", "yuv420p",
    temp_raw_mp4
]

try:
    pipe = subprocess.Popen(nvenc_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    use_nvenc = True
    print("Using hardware-accelerated NVIDIA NVENC encoder (p7 high-quality).")
except Exception:
    pipe = subprocess.Popen(libx264_fallback, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    use_nvenc = False
    print("Using CPU libx264 ultrafast encoder.")

DISSOLVE_FRAMES = 15 # 0.5s fade to/from pure white
PAUSE_FRAMES = 6      # 0.2s pause holding pure white

t_start_merge = time.time()
total_frames_written = 0
white_frame = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)

for sec_idx, sec in enumerate(sections):
    v_path = sec['video']
    print(f"Processing Section {sec_idx + 1}/{len(sections)}: {sec['title']} ({v_path})...")
    cap = cv2.VideoCapture(v_path)
    total_sec_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Read all frames of current section
    sec_frames = []
    while True:
        ret, f = cap.read()
        if not ret:
            break
        sec_frames.append(f)
    cap.release()
    
    n_frames = len(sec_frames)
    print(f"  Loaded {n_frames} frames ({n_frames/FPS:.2f}s). Applying cinematic transitions...")
    
    is_first = (sec_idx == 0)
    is_last = (sec_idx == len(sections) - 1)
    
    for f_idx in range(n_frames):
        cur_f = sec_frames[f_idx]
        
        # Dissolve in from white (if not the very first section)
        if not is_first and f_idx < DISSOLVE_FRAMES:
            t = float(f_idx) / float(DISSOLVE_FRAMES)
            p = t * t * (3.0 - 2.0 * t) # smoothstep
            cur_f = (cur_f.astype(np.float32) * p + white_frame.astype(np.float32) * (1.0 - p)).astype(np.uint8)
            
        # Dissolve out to white (if not the very last section)
        if not is_last and f_idx >= n_frames - DISSOLVE_FRAMES:
            rem = (n_frames - 1) - f_idx
            t = float(rem) / float(DISSOLVE_FRAMES)
            p = t * t * (3.0 - 2.0 * t)
            cur_f = (cur_f.astype(np.float32) * p + white_frame.astype(np.float32) * (1.0 - p)).astype(np.uint8)
            
        pipe.stdin.write(cur_f.tobytes())
        total_frames_written += 1
        
    # Insert pure white pause between sections
    if not is_last:
        for _ in range(PAUSE_FRAMES):
            pipe.stdin.write(white_frame.tobytes())
            total_frames_written += 1

pipe.stdin.close()
pipe.wait()

merge_dur = time.time() - t_start_merge
print(f"\nRaw merged video written in {merge_dur:.2f}s ({total_frames_written} frames, {total_frames_written/FPS:.2f}s)")

# 3. Final Multiplex with Audio
mux_cmd = [
    "ffmpeg", "-y",
    "-i", temp_raw_mp4,
    "-i", temp_audio_wav,
    "-c:v", "copy",
    "-c:a", "aac",
    "-ac", "2",
    "-b:a", "256k",
    "-movflags", "+faststart",
    "-shortest",
    final_output_mp4
]

print(f"\nMultiplexing into master continuous video: {final_output_mp4}...")
mux_res = subprocess.run(mux_cmd, capture_output=True, text=True)

if mux_res.returncode != 0:
    print(f"Error multiplexing: {mux_res.stderr}")
else:
    size_mb = os.path.getsize(final_output_mp4) / (1024 * 1024)
    print(f"\n=====================================================================================")
    print(f"  🏆 MASTER WHITEBOARD DELIVERABLE READY: {final_output_mp4} ({size_mb:.2f} MB) 🏆")
    print(f"=====================================================================================")

    # 4. Save Master Audio Deliverable
    import shutil
    import json
    if os.path.exists(temp_audio_wav):
        shutil.copy2(temp_audio_wav, final_master_audio_wav)
        print(f"  Master Audio Deliverable saved: {final_master_audio_wav}")

    # 5. Populate Section Deliverables with Clean Semantic Names
    print("\nArchiving individual section deliverables...")
    manifest_sections = []
    for sec in sections:
        src_v = sec['video']
        dst_v = os.path.join(SECTIONS_DELIVERABLES_DIR, sec['deliverable_name'])
        if os.path.exists(src_v):
            shutil.copy2(src_v, dst_v)
            sec_size_mb = os.path.getsize(dst_v) / (1024 * 1024)
            print(f"  Saved section: {sec['deliverable_name']} ({sec_size_mb:.1f} MB)")
            manifest_sections.append({
                'id': sec['id'],
                'title': sec['title'],
                'file': f"sections/{sec['deliverable_name']}",
                'size_mb': round(sec_size_mb, 2)
            })

    # 6. Generate Project Manifest
    manifest = {
        'project_title': PROJECT_ARABIC_NAME,
        'project_slug': PROJECT_SLUG,
        'master_video': f"{PROJECT_TITLE}.mp4",
        'master_audio': f"{PROJECT_TITLE.replace('_1080p', '')}_Master_Audio.wav",
        'resolution': f"{WIDTH}x{HEIGHT}",
        'fps': FPS,
        'total_duration_sec': round(total_audio_sec, 2),
        'sections_count': len(sections),
        'sections': manifest_sections
    }
    manifest_path = os.path.join(DELIVERABLES_DIR, "project_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\n  Project Manifest generated: {manifest_path}")

    # Backward compatibility copy
    try:
        shutil.copy2(final_output_mp4, legacy_output_mp4)
    except Exception:
        pass

# 7. Cleanup Scratch Temp Buffers
print("\nPurging temporary scratch buffers...")
if os.path.exists(temp_raw_mp4):
    os.remove(temp_raw_mp4)
if os.path.exists(temp_audio_wav):
    os.remove(temp_audio_wav)
print("Scratch cleaned. All deliverables organized under: " + DELIVERABLES_DIR)

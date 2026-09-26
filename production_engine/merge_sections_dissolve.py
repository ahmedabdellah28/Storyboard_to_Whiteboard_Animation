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
print("  🎬 SEAMLESS WHITEBOARD SECTION MERGER — SMOOTH DISSOLVE THROUGH WHITE 🎬")
print("=====================================================================================")

WIDTH, HEIGHT = 1920, 1080
FPS = 30
SR = 48000

video1_path = "sections/01_apple/final_whiteboard_1080p.mp4"
video2_path = "sections/02_kiwi/final_whiteboard_1080p.mp4"

audio1_path = "sections/01_apple/master_audio.wav"
audio2_path = "sections/02_kiwi/master_audio.wav"

whoosh_path = "production_engine/sfx/whoosh.wav"

temp_raw_mp4 = "output_animations/temp_raw_merged.mp4"
temp_audio_wav = "output_animations/temp_merged_audio.wav"
final_output_mp4 = "output_animations/master_whiteboard_apple_and_kiwi_2026.mp4"

# 1. Build Seamless Audio Track
print("\n1. Building seamless audio track with transition whoosh...")
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

a1 = load_stereo_wav(audio1_path)
a2 = load_stereo_wav(audio2_path)
whoosh = load_stereo_wav(whoosh_path)

# Micro pause between scenes (0.2s = 9600 samples)
pause_samples = int(0.20 * SR)
pause_silence = np.zeros((pause_samples, 2), dtype=np.float32)

# Transition point (right where a1 ends and enters pause)
# Add subtle whoosh across the transition (gain = 0.08)
t_trans_start = len(a1) - int(0.35 * SR)
trans_audio = np.vstack([a1, pause_silence, a2])

whoosh_len = min(len(trans_audio) - t_trans_start, len(whoosh))
if whoosh_len > 0:
    trans_audio[t_trans_start:t_trans_start + whoosh_len] += whoosh[:whoosh_len] * 0.08

# Peak limit
peak = np.max(np.abs(trans_audio))
if peak > 0.98:
    trans_audio = trans_audio * (0.98 / peak)

trans_int16 = (trans_audio * 32767.0).astype(np.int16)
with wave.open(temp_audio_wav, 'wb') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(trans_int16.tobytes())

total_audio_sec = len(trans_audio) / float(SR)
print(f"Master merged audio created: {temp_audio_wav} ({total_audio_sec:.2f}s)")

# 2. Setup NVENC Fast Video Merge Pipe
print("\n2. Streaming video frames with smooth dissolve-through-white transition...")
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
    temp_raw_mp4
]

ffmpeg_log = open("output_animations/ffmpeg_merge.log", "w", encoding="utf-8")
pipe = subprocess.Popen(nvenc_cmd, stdin=subprocess.PIPE, stdout=ffmpeg_log, stderr=ffmpeg_log)

cap1 = cv2.VideoCapture(video1_path)
total_f1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
fps1 = cap1.get(cv2.CAP_PROP_FPS)

cap2 = cv2.VideoCapture(video2_path)
total_f2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
fps2 = cap2.get(cv2.CAP_PROP_FPS)

print(f"Video 1 (Apple): {total_f1} frames")
print(f"Video 2 (Kiwi) : {total_f2} frames")

t_start = time.time()
frame_count = 0

# Stream Video 1 (Fade out last 15 frames to pure white)
DISSOLVE_FRAMES = 15
fade_start_idx = total_f1 - DISSOLVE_FRAMES

while True:
    ret, frame = cap1.read()
    if not ret:
        break
    
    if frame_count >= fade_start_idx:
        p = (frame_count - fade_start_idx + 1) / float(DISSOLVE_FRAMES)
        # Smoother dissolve towards pure white (255, 255, 255)
        p_smooth = p * p * (3.0 - 2.0 * p)
        white = np.full_like(frame, 255)
        frame = cv2.addWeighted(frame, 1.0 - p_smooth, white, p_smooth, 0.0)
        
    pipe.stdin.write(frame.tobytes())
    frame_count += 1

cap1.release()
print(f"Streamed Section 01 Apple with smooth fade-out ({frame_count} frames)")

# Stream 6 frames (0.2s) of pure clean white board
pure_white = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)
for _ in range(6):
    pipe.stdin.write(pure_white.tobytes())
    frame_count += 1
print(f"Inserted pure clean whiteboard pause (6 frames)")

# Stream Video 2 (Kiwi - starts clean with hand entering)
f2_count = 0
while True:
    ret, frame = cap2.read()
    if not ret:
        break
    pipe.stdin.write(frame.tobytes())
    frame_count += 1
    f2_count += 1

cap2.release()
pipe.stdin.close()
pipe.wait()
ffmpeg_log.close()

elapsed = time.time() - t_start
print(f"Streamed Section 02 Kiwi ({f2_count} frames)")
print(f"Total video frames encoded: {frame_count} in {elapsed:.2f}s (Speed: {frame_count / elapsed:.1f} FPS)")

# 3. Multiplex Final Master Video
print("\n3. Multiplexing final continuous video with master stereo audio...")
final_mux_cmd = [
    "ffmpeg", "-y",
    "-i", temp_raw_mp4,
    "-i", temp_audio_wav,
    "-c:v", "copy",
    "-c:a", "aac",
    "-ac", "2",
    "-b:a", "256k",
    "-shortest",
    final_output_mp4
]

mux_proc = subprocess.run(final_mux_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if mux_proc.returncode == 0:
    print(f"\n🎉 MASTERPIECE COMPLETED!")
    print(f"Combined Master Video saved to: {final_output_mp4}")
    total_dur_s = frame_count / float(FPS)
    mins = int(total_dur_s // 60)
    secs = int(total_dur_s % 60)
    print(f"Duration: {total_dur_s:.2f}s ({mins}m {secs}s)")
else:
    print(f"Multiplex error: {mux_proc.stderr.decode('utf-8', errors='ignore')}")

# Clean temporary files
if os.path.exists(temp_raw_mp4):
    os.remove(temp_raw_mp4)
if os.path.exists(temp_audio_wav):
    os.remove(temp_audio_wav)
print("Cleaned temporary raw merge files.")

"""
Master Documentary Concatenator
Stitches all 11 produced whiteboard sections into the final Master Documentary Film.
- 1920x1080 @ 30 FPS Full Feature Video
- Master Audio with ducked SFX and synchronized voiceover
- Generates YouTube / Player Chapter Markers
"""
import os
import sys
import json
import subprocess
import wave

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SECTIONS_DIR = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables", "sections")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables")

SECTIONS_ORDER = [
    ("00_Hook", "المقدمة (The Hook)", "00_Hook_Whiteboard_1080p.mp4", "00_Hook_Master_Audio.wav"),
    ("01_Homeless", "بلا مأوى (Homeless)", "01_Homeless_Whiteboard_1080p.mp4", "01_Homeless_Master_Audio.wav"),
    ("02_Extreme_Poverty", "الفقر المدقع (Extreme Poverty)", "02_Extreme_Poverty_Whiteboard_1080p.mp4", "02_Extreme_Poverty_Master_Audio.wav"),
    ("03_Working_Poor", "الفقر العامل (Working Poor)", "03_Working_Poor_Whiteboard_1080p.mp4", "03_Working_Poor_Master_Audio.wav"),
    ("04_Lower_Middle_Class", "الطبقة المتوسطة الدنيا (Lower Middle Class)", "04_Lower_Middle_Class_Whiteboard_1080p.mp4", "04_Lower_Middle_Class_Master_Audio.wav"),
    ("05_Middle_Class", "الطبقة المتوسطة (Middle Class)", "05_Middle_Class_Whiteboard_1080p.mp4", "05_Middle_Class_Master_Audio.wav"),
    ("06_Upper_Middle_Class", "الطبقة المتوسطة العليا (Upper Middle Class)", "06_Upper_Middle_Class_Whiteboard_1080p.mp4", "06_Upper_Middle_Class_Master_Audio.wav"),
    ("07_Comfortable_Rich", "الغني المرتاح (Comfortable Rich)", "07_Comfortable_Rich_Whiteboard_1080p.mp4", "07_Comfortable_Rich_Master_Audio.wav"),
    ("08_Ultra_Wealthy", "فاحش الثراء (Ultra Wealthy)", "08_Ultra_Wealthy_Whiteboard_1080p.mp4", "08_Ultra_Wealthy_Master_Audio.wav"),
    ("10_Islamic_Perspective", "المنظور الإسلامي (Islamic Perspective)", "10_Islamic_Perspective_Whiteboard_1080p.mp4", "10_Islamic_Perspective_Master_Audio.wav"),
    ("11_Outro", "الخاتمة (Outro)", "11_Outro_Whiteboard_1080p.mp4", "11_Outro_Master_Audio.wav"),
]

def format_timestamp(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

print("=" * 80)
print("🎬 COMPILING MASTER DOCUMENTARY FEATURE FILM")
print("=" * 80)

# Check all files exist
for tag, title, vid, aud in SECTIONS_ORDER:
    v_path = os.path.join(SECTIONS_DIR, vid)
    a_path = os.path.join(SECTIONS_DIR, aud)
    if not os.path.exists(v_path):
        raise FileNotFoundError(f"Missing video: {v_path}")
    if not os.path.exists(a_path):
        raise FileNotFoundError(f"Missing audio: {a_path}")

# 1. Calculate Chapter Timestamps
chapters = []
cumulative_time = 0.0

for tag, title, vid, aud in SECTIONS_ORDER:
    v_path = os.path.join(SECTIONS_DIR, vid)
    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', v_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    dur = float(json.loads(res.stdout)['format']['duration'])
    
    chapters.append({
        "tag": tag,
        "title": title,
        "start_sec": cumulative_time,
        "start_str": format_timestamp(cumulative_time),
        "duration": dur
    })
    cumulative_time += dur

print(f"\n📑 Chapter Marks ({len(chapters)} Chapters | Total: {format_timestamp(cumulative_time)}):")
for ch in chapters:
    print(f"  {ch['start_str']} - {ch['title']} ({ch['duration']:.1f}s)")

# Save chapters to text file
chapters_file = os.path.join(OUTPUT_DIR, "documentary_chapters.txt")
with open(chapters_file, "w", encoding="utf-8") as f:
    f.write("# رحلة عبر الطبقات المادية: من بلا مأوى إلى الملياردير\n")
    f.write(f"# Total Runtime: {format_timestamp(cumulative_time)} ({cumulative_time:.2f}s)\n\n")
    f.write("## فصول الفيديو (YouTube Chapters):\n")
    for ch in chapters:
        f.write(f"{ch['start_str']} {ch['title']}\n")

# 2. Concat Videos using FFmpeg concat filter / demuxer
concat_list_file = os.path.join(OUTPUT_DIR, "concat_video_list.txt")
with open(concat_list_file, "w", encoding="utf-8") as f:
    for _, _, vid, _ in SECTIONS_ORDER:
        v_path = os.path.join(SECTIONS_DIR, vid).replace("\\", "/")
        f.write(f"file '{v_path}'\n")

final_video_path = os.path.join(OUTPUT_DIR, "Full_Wealth_Classes_Documentary_1080p.mp4")
print(f"\n🎥 Stitching 11 Video Sections -> {final_video_path}...")

# Lossless stream copy concat
cmd_concat_v = [
    'ffmpeg', '-y',
    '-f', 'concat',
    '-safe', '0',
    '-i', concat_list_file,
    '-c', 'copy',
    final_video_path
]
res_v = subprocess.run(cmd_concat_v, capture_output=True, text=True)
if res_v.returncode != 0:
    print("Warning: Stream copy failed, re-encoding with NVENC...", flush=True)
    cmd_fallback = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_list_file,
        '-c:v', 'h264_nvenc', '-preset', 'p7', '-b:v', '5000k',
        '-c:a', 'aac', '-b:a', '192k',
        final_video_path
    ]
    subprocess.run(cmd_fallback, check=True)

# 3. Concat Master Audio files
concat_audio_list_file = os.path.join(OUTPUT_DIR, "concat_audio_list.txt")
with open(concat_audio_list_file, "w", encoding="utf-8") as f:
    for _, _, _, aud in SECTIONS_ORDER:
        a_path = os.path.join(SECTIONS_DIR, aud).replace("\\", "/")
        f.write(f"file '{a_path}'\n")

final_audio_path = os.path.join(OUTPUT_DIR, "Full_Wealth_Classes_Documentary_Master_Audio.wav")
print(f"\n🎵 Stitching 11 Audio Sections -> {final_audio_path}...")

cmd_concat_a = [
    'ffmpeg', '-y',
    '-f', 'concat',
    '-safe', '0',
    '-i', concat_audio_list_file,
    '-c', 'pcm_s16le',
    final_audio_path
]
subprocess.run(cmd_concat_a, check=True)

# 4. Verify Final Deliverable
cmd_probe = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', final_video_path]
probe_data = json.loads(subprocess.run(cmd_probe, capture_output=True, text=True).stdout)
final_dur = float(probe_data['format']['duration'])
final_size_mb = os.path.getsize(final_video_path) / (1024*1024)

print("\n" + "=" * 80)
print("🎉 MASTER FEATURE DOCUMENTARY SUCCESSFULLY GENERATED!")
print(f"  • Full Video : {final_video_path}")
print(f"  • Master Audio: {final_audio_path}")
print(f"  • Chapters   : {chapters_file}")
print(f"  • Total Time : {format_timestamp(final_dur)} ({final_dur:.2f}s)")
print(f"  • File Size  : {final_size_mb:.1f} MB")
print("=" * 80)

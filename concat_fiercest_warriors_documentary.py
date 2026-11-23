"""Master Documentary Concatenator for Fiercest Warriors (أشرس المحاربين في التاريخ).

Stitches all 8 produced whiteboard sections into the final Master Documentary Film:
- 1920x1080 @ 30 FPS Full Feature Video
- Master Audio with ducked SFX and synchronized voiceover
- Generates YouTube / Player Chapter Markers
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(r"E:\image_to_animate")
SECTIONS_SRC_DIR = ROOT_DIR / "sections" / "fiercest_warriors_documentary"
DELIVERABLES_DIR = ROOT_DIR / "output_animations" / "fiercest_warriors_documentary" / "deliverables"
SECTIONS_DELIV_DIR = DELIVERABLES_DIR / "sections"

DELIVERABLES_DIR.mkdir(parents=True, exist_ok=True)
SECTIONS_DELIV_DIR.mkdir(parents=True, exist_ok=True)

# 1. Update Guan Yu in deliverables from the successful TCM v2 run
src_guan_yu_vid = SECTIONS_SRC_DIR / "07_guan_yu" / "final_whiteboard_tcm_v2_1080p.mp4"
dst_guan_yu_vid = SECTIONS_DELIV_DIR / "07_guan_yu_Whiteboard_1080p.mp4"
if src_guan_yu_vid.exists():
    print(f"Updating deliverables with latest Guan Yu TCM v2 video ({src_guan_yu_vid.stat().st_size / (1024*1024):.2f} MB)...")
    shutil.copyfile(src_guan_yu_vid, dst_guan_yu_vid)

src_guan_yu_aud = SECTIONS_SRC_DIR / "07_guan_yu" / "master_audio.wav"
dst_guan_yu_aud = SECTIONS_DELIV_DIR / "07_guan_yu_Master_Audio.wav"
if src_guan_yu_aud.exists():
    shutil.copyfile(src_guan_yu_aud, dst_guan_yu_aud)

# Ensure Hamza has canonical naming
src_hamza_vid = SECTIONS_SRC_DIR / "03_hamza_ibn_abd_al_muttalib" / "final_whiteboard_1080p.mp4"
dst_hamza_vid = SECTIONS_DELIV_DIR / "03_Hamza_Ibn_Abd_Al_Muttalib_Whiteboard_1080p.mp4"
if src_hamza_vid.exists():
    shutil.copyfile(src_hamza_vid, dst_hamza_vid)

SECTIONS_ORDER = [
    ("00_Hook", "المقدمة (The Hook)", "00_Hook_Whiteboard_1080p.mp4", "00_Hook_Master_Audio.wav"),
    ("01_El_Cid", "إل سيد (El Cid - بطل قشتالة)", "01_El_Cid_Whiteboard_1080p.mp4", "01_El_Cid_Master_Audio.wav"),
    ("02_Khalid", "خالد بن الوليد (سيف الله المسلول)", "02_Khalid_Ibn_Al_Walid_Whiteboard_1080p.mp4", "02_Khalid_Ibn_Al_Walid_Master_Audio.wav"),
    ("03_Hamza", "حمزة بن عبد المطلب (أسد الله)", "03_Hamza_Ibn_Abd_Al_Muttalib_Whiteboard_1080p.mp4", "03_Hamza_Ibn_Abd_Al_Muttalib_Master_Audio.wav"),
    ("04_Spartacus", "سبارتاكوس (قائد ثورة المصارعين)", "04_Spartacus_Whiteboard_1080p.mp4", "04_Spartacus_Master_Audio.wav"),
    ("05_Tlahuicole", "تلاهويكول (أسطورة شعب التلاكسكالا)", "05_Tlahuicole_Whiteboard_1080p.mp4", "05_Tlahuicole_Master_Audio.wav"),
    ("06_Omar_Mukhtar", "عمر المختار (شيخ الشهداء وأسد الصحراء)", "06_Omar_Al_Mukhtar_Whiteboard_1080p.mp4", "06_Omar_Al_Mukhtar_Master_Audio.wav"),
    ("07_Guan_Yu", "غوان يو (إله الحرب ورمز الوفاء)", "07_guan_yu_Whiteboard_1080p.mp4", "07_guan_yu_Master_Audio.wav"),
    ("08_Lu_Bu", "لوبو (الجنرال الطائر وأقوى محاربي سلالة هان)", "08_lu_bu_Whiteboard_1080p.mp4", "08_lu_bu_Master_Audio.wav"),
    ("09_Al_Baraa", "البراء بن مالك (فارس حديقة الموت وبطل اليمامة)", "09_al_baraa_ibn_malik_Whiteboard_1080p.mp4", "09_al_baraa_ibn_malik_Master_Audio.wav"),
    ("15_Outro", "الخاتمة (Outro - خلاصة عن معنى الشجاعة)", "15_outro_Whiteboard_1080p.mp4", "15_outro_Master_Audio.wav"),
]

def format_timestamp(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

print("=" * 80)
print("🎬 COMPILING MASTER DOCUMENTARY: FIERCEST WARRIORS (أشرس المحاربين في التاريخ)")
print("=" * 80)

# Check all files exist
for tag, title, vid, aud in SECTIONS_ORDER:
    v_path = SECTIONS_DELIV_DIR / vid
    a_path = SECTIONS_DELIV_DIR / aud
    if not v_path.exists():
        raise FileNotFoundError(f"Missing video: {v_path}")
    if not a_path.exists():
        raise FileNotFoundError(f"Missing audio: {a_path}")

# 1. Calculate Chapter Timestamps
chapters = []
cumulative_time = 0.0

for tag, title, vid, aud in SECTIONS_ORDER:
    v_path = SECTIONS_DELIV_DIR / vid
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(v_path)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    dur = float(json.loads(res.stdout)["format"]["duration"])
    
    chapters.append({
        "tag": tag,
        "title": title,
        "start_sec": cumulative_time,
        "start_str": format_timestamp(cumulative_time),
        "duration": dur,
    })
    cumulative_time += dur

print(f"\n📑 Chapter Marks ({len(chapters)} Chapters | Total: {format_timestamp(cumulative_time)}):")
for ch in chapters:
    print(f"  {ch['start_str']} - {ch['title']} ({ch['duration']:.1f}s)")

# Save chapters to text file
chapters_file = DELIVERABLES_DIR / "documentary_chapters.txt"
with open(chapters_file, "w", encoding="utf-8") as f:
    f.write("# وثائقي أشرس وأعظم المحاربين في تاريخ البشرية\n")
    f.write(f"# Total Runtime: {format_timestamp(cumulative_time)} ({cumulative_time:.2f}s)\n\n")
    f.write("## فصول الفيديو (YouTube Chapters):\n")
    for ch in chapters:
        f.write(f"{ch['start_str']} {ch['title']}\n")

# 2. Concat Videos using FFmpeg concat demuxer
concat_list_file = DELIVERABLES_DIR / "concat_video_list.txt"
with open(concat_list_file, "w", encoding="utf-8") as f:
    for _, _, vid, _ in SECTIONS_ORDER:
        v_path = str(SECTIONS_DELIV_DIR / vid).replace("\\", "/")
        f.write(f"file '{v_path}'\n")

final_video_path = DELIVERABLES_DIR / "Full_Fiercest_Warriors_Documentary_1080p.mp4"
print(f"\n🎥 Stitching 8 Video Sections -> {final_video_path}...")

# Lossless stream copy concat
cmd_concat_v = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", str(concat_list_file),
    "-c", "copy",
    str(final_video_path),
]
res_v = subprocess.run(cmd_concat_v, capture_output=True, text=True)
if res_v.returncode != 0:
    print("Warning: Stream copy failed, re-encoding with NVENC...", flush=True)
    cmd_fallback = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c:v", "h264_nvenc", "-preset", "p7", "-b:v", "5000k",
        "-c:a", "aac", "-b:a", "192k",
        str(final_video_path),
    ]
    subprocess.run(cmd_fallback, check=True)

# 3. Concat Master Audio files
concat_audio_list_file = DELIVERABLES_DIR / "concat_audio_list.txt"
with open(concat_audio_list_file, "w", encoding="utf-8") as f:
    for _, _, _, aud in SECTIONS_ORDER:
        a_path = str(SECTIONS_DELIV_DIR / aud).replace("\\", "/")
        f.write(f"file '{a_path}'\n")

final_audio_path = DELIVERABLES_DIR / "Full_Fiercest_Warriors_Documentary_Master_Audio.wav"
print(f"\n🎵 Stitching 8 Audio Sections -> {final_audio_path}...")

cmd_concat_a = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", str(concat_audio_list_file),
    "-c", "pcm_s16le",
    str(final_audio_path),
]
subprocess.run(cmd_concat_a, check=True)

# 4. Verify Final Deliverable
cmd_probe = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(final_video_path)]
probe_data = json.loads(subprocess.run(cmd_probe, capture_output=True, text=True).stdout)
final_dur = float(probe_data["format"]["duration"])
final_size_mb = final_video_path.stat().st_size / (1024 * 1024)

print("\n" + "=" * 80)
print("🎉 MASTER FEATURE DOCUMENTARY SUCCESSFULLY GENERATED!")
print(f"  • Full Video : {final_video_path}")
print(f"  • Master Audio: {final_audio_path}")
print(f"  • Chapters   : {chapters_file}")
print(f"  • Total Time : {format_timestamp(final_dur)} ({final_dur:.2f}s)")
print(f"  • File Size  : {final_size_mb:.1f} MB")
print("=" * 80)

"""
Arabic Master Audio Exporter
Concatenates all Arabic section master audio files into a single
professional-quality Arabic dubbing track that matches the documentary timeline.
"""
import os
import sys
import wave
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SECTIONS_DIR = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables", "sections")
OUTPUT_DIR   = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables")
SCRATCH_DIR  = os.path.join(ROOT_DIR, "scratch", "arabic_dub_work")
os.makedirs(SCRATCH_DIR, exist_ok=True)

SECTIONS = [
    {"id": "00_Hook",               "aud": "00_Hook_Master_Audio.wav"},
    {"id": "01_Homeless",           "aud": "01_Homeless_Master_Audio.wav"},
    {"id": "02_Extreme_Poverty",    "aud": "02_Extreme_Poverty_Master_Audio.wav"},
    {"id": "03_Working_Poor",       "aud": "03_Working_Poor_Master_Audio.wav"},
    {"id": "04_Lower_Middle_Class", "aud": "04_Lower_Middle_Class_Master_Audio.wav"},
    {"id": "05_Middle_Class",       "aud": "05_Middle_Class_Master_Audio.wav"},
    {"id": "06_Upper_Middle_Class", "aud": "06_Upper_Middle_Class_Master_Audio.wav"},
    {"id": "07_Comfortable_Rich",   "aud": "07_Comfortable_Rich_Master_Audio.wav"},
    {"id": "08_Ultra_Wealthy",      "aud": "08_Ultra_Wealthy_Master_Audio.wav"},
    {"id": "10_Islamic_Perspective","aud": "10_Islamic_Perspective_Master_Audio.wav"},
    {"id": "11_Outro",              "aud": "11_Outro_Master_Audio.wav"},
]

def get_duration_wav(path: str) -> float:
    with wave.open(path, 'rb') as wf:
        return wf.getnframes() / float(wf.getframerate())

def normalize_section(src: str, sec_id: str) -> str:
    """Normalize sample rate & channels to 48kHz stereo PCM."""
    norm_path = os.path.join(SCRATCH_DIR, f"{sec_id}_norm.wav")
    cmd = [
        'ffmpeg', '-y', '-i', src,
        '-ar', '48000', '-ac', '2',
        '-c:a', 'pcm_s16le',
        norm_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"  WARNING ffmpeg error for {sec_id}:")
        print(result.stderr.decode('utf-8', errors='replace')[-500:])
        raise RuntimeError(f"Normalization failed for {sec_id}")
    return norm_path

def main():
    print("=" * 70)
    print("  ARABIC DUBBING MASTER EXPORT — Wealth Classes Documentary")
    print("=" * 70)

    normalized_files = []
    total_dur = 0.0

    print("\n  Step 1: Verify & Normalize All Arabic Section Audio\n")
    for sec in SECTIONS:
        src = os.path.join(SECTIONS_DIR, sec["aud"])
        if not os.path.exists(src):
            print(f"  MISSING: {src}")
            sys.exit(1)

        dur = get_duration_wav(src)
        print(f"  OK [{sec['id']:25s}]  {dur:7.2f}s  <- {sec['aud']}")
        total_dur += dur

        norm_path = normalize_section(src, sec["id"])
        normalized_files.append(norm_path)

    m = int(total_dur // 60)
    s = int(total_dur % 60)
    print(f"\n  Total combined duration: {m:02d}:{s:02d} ({total_dur:.2f}s)")

    # Step 2: Write concat list
    print("\n  Step 2: Concatenating into Full Arabic Master Track...")
    list_path = os.path.join(SCRATCH_DIR, "concat_arabic_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for p in normalized_files:
            safe = p.replace("\\", "/")
            f.write(f"file '{safe}'\n")

    # Step 3: Concatenate to WAV
    out_wav = os.path.join(OUTPUT_DIR, "Full_Wealth_Classes_Documentary_Arabic_Master.wav")
    cmd_concat = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', list_path,
        '-c:a', 'pcm_s16le',
        out_wav
    ]
    result = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print("  Concatenation failed:")
        print(result.stderr.decode('utf-8', errors='replace')[-800:])
        sys.exit(1)

    size_mb = os.path.getsize(out_wav) / (1024 * 1024)
    final_dur = get_duration_wav(out_wav)
    fm = int(final_dur // 60)
    fs = int(final_dur % 60)

    print(f"  Arabic Master WAV: {out_wav}")
    print(f"  Size    : {size_mb:.1f} MB")
    print(f"  Duration: {fm:02d}:{fs:02d} ({final_dur:.2f}s)")

    # Step 4: Export as MP3
    print("\n  Step 3: Exporting Arabic Master MP3 (320kbps)...")
    out_mp3 = os.path.join(OUTPUT_DIR, "Full_Wealth_Classes_Documentary_Arabic_Master.mp3")
    cmd_mp3 = [
        'ffmpeg', '-y',
        '-i', out_wav,
        '-c:a', 'libmp3lame', '-b:a', '320k',
        '-id3v2_version', '3',
        '-metadata', 'title=Wealth Classes Documentary - Arabic Edition',
        '-metadata', 'artist=Documentary Production',
        '-metadata', 'album=Wealth Classes: From Homeless to Billionaire',
        out_mp3
    ]
    result_mp3 = subprocess.run(cmd_mp3, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    mp3_ok = result_mp3.returncode == 0
    if mp3_ok:
        mp3_mb = os.path.getsize(out_mp3) / (1024 * 1024)
        print(f"  Arabic Master MP3: {out_mp3}  ({mp3_mb:.1f} MB)")
    else:
        print("  MP3 export skipped (libmp3lame not available)")

    print("\n" + "=" * 70)
    print("  ARABIC DUBBING EXPORT COMPLETE!")
    print(f"  WAV  -> {out_wav}")
    if mp3_ok:
        print(f"  MP3  -> {out_mp3}")
    print(f"  Runtime: {fm:02d}:{fs:02d} ({final_dur:.2f}s)")
    print("=" * 70)


if __name__ == "__main__":
    main()

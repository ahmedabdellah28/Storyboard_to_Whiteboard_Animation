import os
import sys
import wave
import subprocess
import shutil

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine
from voice_studio.profiles import AUDIO_PROFILES, DIRECTOR_NOTES

def generate_complete_audio():
    sec_dir = os.path.join(ROOT_DIR, "sections", "00_hook")
    script_file = os.path.join(sec_dir, "script.txt")
    final_wav = os.path.join(sec_dir, "voiceover.wav")
    chunks_dir = os.path.join(sec_dir, "audio_chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    with open(script_file, "r", encoding="utf-8") as f:
        full_transcript = f.read().strip()

    # Part 1 and Part 2 (split at natural transition point: "يدير تفاصيل يومك.")
    split_marker = "يدير تفاصيل يومك."
    if split_marker in full_transcript:
        parts_raw = full_transcript.split(split_marker)
        part1 = parts_raw[0].strip() + " " + split_marker
        part2 = parts_raw[1].strip()
    else:
        # Fallback to paragraph splitting
        paras = [p.strip() for p in full_transcript.split("\n\n") if p.strip()]
        mid = len(paras) // 2
        part1 = "\n\n".join(paras[:mid])
        part2 = "\n\n".join(paras[mid:])

    chunks = [
        ("part_01", part1),
        ("part_02", part2)
    ]

    print("=" * 70)
    print("🎙️ GENERATING FULL SECTION 00 VOICEOVER (HIGH_ENERGY_YOUTUBE @ 1.1x)")
    print("=" * 70)
    print(f"Total Words: {len(full_transcript.split())}")
    print(f"Part 1 words: {len(part1.split())}")
    print(f"Part 2 words: {len(part2.split())}\n")

    engine = VoiceStudioEngine(model="gemini-3.1-flash-tts-preview")
    profile = AUDIO_PROFILES["SAUDI_YOUTH_CREATOR"]
    director_note = DIRECTOR_NOTES["HIGH_ENERGY_YOUTUBE"]

    chunk_files = []
    for cid, ctext in chunks:
        out_chunk = os.path.join(chunks_dir, f"{cid}.wav")
        chunk_files.append(out_chunk)
        print(f"  • Synthesizing {cid} ({len(ctext.split())} words)...")
        prompt = engine.build_prompt(ctext, profile, director_note)
        
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=engine.api_key)
        
        res = engine._synthesize_single_chunk(
            client=client,
            types=types,
            full_prompt=prompt,
            output_wav_path=out_chunk,
            voice_name="Fenrir",
            temperature=1.0,
            retries=3
        )
        print(f"    ✅ Done: {res['duration']:.2f}s audio duration.")

    # Stitch the chunks with 0.15s natural pause
    print("\n🔗 Seamlessly stitching parts into unified section master...")
    raw_concat = os.path.join(sec_dir, "raw_voiceover_concat.wav")
    sample_rate = 24000
    num_channels = 1
    sampwidth = 2
    pause_sec = 0.15
    silence_bytes = b'\x00' * int(sample_rate * num_channels * sampwidth * pause_sec)

    with wave.open(raw_concat, 'wb') as outfile:
        outfile.setnchannels(num_channels)
        outfile.setsampwidth(sampwidth)
        outfile.setframerate(sample_rate)
        for idx, cp in enumerate(chunk_files):
            with wave.open(cp, 'rb') as infile:
                outfile.writeframes(infile.readframes(infile.getnframes()))
            if idx < len(chunk_files) - 1:
                outfile.writeframes(silence_bytes)

    # Apply 1.20x speed multiplier via FFmpeg atempo
    print("⚡ Applying speed multiplier 1.20x (high-energy YouTube delivery)...")
    cmd = [
        "ffmpeg", "-y", "-i", raw_concat,
        "-af", "atempo=1.20",
        final_wav
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if os.path.exists(raw_concat):
        os.remove(raw_concat)

    # Inspect final file
    with wave.open(final_wav, 'rb') as wf:
        n_frames = wf.getnframes()
        sr = wf.getframerate()
        duration = n_frames / float(sr)

    print("=" * 70)
    print(f"🎉 100% COMPLETE SECTION 00 VOICEOVER CREATED!")
    print(f"  • File Path   : {final_wav}")
    print(f"  • Duration    : {duration:.2f} seconds")
    print(f"  • Sample Rate : {sr} Hz")
    print(f"  • Pacing Mode : HIGH_ENERGY_YOUTUBE (1.1x)")
    print("=" * 70)
    return duration

if __name__ == "__main__":
    generate_complete_audio()

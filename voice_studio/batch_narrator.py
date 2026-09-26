"""
Voice Studio Batch Narrator
Iterates over all script sections in sequence with a configurable sleep delay (10-15s)
to respect API rate limits and produce a unified, master multi-chapter voiceover.
"""
import os
import sys
import time
import re
import wave
import shutil
from typing import Optional

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine, split_transcript_into_sections
from voice_studio.profiles import AUDIO_PROFILES, DIRECTOR_NOTES


def run_batch_narrator(
    script_path: str = "project_content/transcript_to_speech.txt",
    output_master_wav: str = "project_content/audio/خلنا نبدأ من أول مستوى المستوى التأسيسي.wav",
    model: str = "gemini-2.5-flash-preview-tts",
    voice_name: str = "Fenrir",
    delay_between_sections: float = 12.0,
    pause_between_sections: float = 0.25,
    chunks_dir: str = "project_content/audio/chunks",
    artifact_dir: Optional[str] = r"C:\Users\loper\.gemini\antigravity-ide\brain\158728a5-a939-4410-9555-755847fa7279"
):
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError("google-genai is required.")

    if not os.path.isabs(script_path):
        script_path = os.path.join(ROOT_DIR, script_path)
    if not os.path.isabs(output_master_wav):
        output_master_wav = os.path.join(ROOT_DIR, output_master_wav)
    if not os.path.isabs(chunks_dir):
        chunks_dir = os.path.join(ROOT_DIR, chunks_dir)

    os.makedirs(chunks_dir, exist_ok=True)
    os.makedirs(os.path.dirname(output_master_wav), exist_ok=True)

    with open(script_path, "r", encoding="utf-8") as f:
        transcript = f.read()

    sections = split_transcript_into_sections(transcript)
    total_sections = len(sections)

    engine = VoiceStudioEngine(model=model)
    # Prioritize GEMINI_API_KEY2 since Key 1 exhausted its 10 requests daily limit
    if len(engine.api_keys) > 1:
        for k in engine.api_keys:
            if k.startswith("AQ.Ab8RN6L6v") or k != engine.api_keys[0]:
                engine.api_key = k
                break

    client = genai.Client(api_key=engine.api_key)
    profile = AUDIO_PROFILES["SAUDI_YOUTH_CREATOR"]
    director_note = DIRECTOR_NOTES["HIGH_ENERGY_YOUTUBE"]

    print("=" * 85)
    print("      🎙️ VOICE STUDIO — AUTOMATED MULTI-SECTION BATCH NARRATOR 🎙️")
    print("=" * 85)
    print(f"Total Sections   : {total_sections}")
    print(f"Model / Voice    : {model} / {voice_name}")
    print(f"Delay Between    : {delay_between_sections}s (Rate-Limiter Protection)")
    print(f"Natural Pause    : {pause_between_sections}s")
    print(f"Master Target    : {output_master_wav}")
    print(f"Chunks Directory : {chunks_dir}\n")

    chunk_files = []

    for i, sec in enumerate(sections, 1):
        tag_label = sec["tag"] if sec["tag"] else "[neutral]"
        clean_tag = re.sub(r'[^a-zA-Z0-9_]', '_', tag_label.strip('[]'))
        chunk_name = f"sec_{i:02d}_{clean_tag}.wav"
        chunk_path = os.path.join(chunks_dir, chunk_name)
        chunk_files.append(chunk_path)

        section_export = os.path.join(ROOT_DIR, "project_content", "audio", f"section_{i:02d}_speed_1.0x.wav")
        first_snippet = " ".join(re.sub(r'\[.*?\]', '', sec["text"]).replace('\n', ' ').split()[:7])

        # Check existing chunk
        if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 2000:
            with wave.open(chunk_path, 'rb') as wf:
                sec_dur = wf.getnframes() / float(wf.getframerate())
            print(f"[{i:02d}/{total_sections:02d}] ⚡ CACHED: {tag_label} ({sec['words']} words) -> {sec_dur:.2f}s")
            if not os.path.exists(section_export):
                shutil.copyfile(chunk_path, section_export)
            continue

        print(f"[{i:02d}/{total_sections:02d}] 🎙️ GENERATING: {tag_label} ({sec['words']} words)")
        print(f"        Snippet: \"{first_snippet}...\"")

        full_prompt = engine.build_prompt(sec["text"], profile, director_note)
        
        # Retry with exponential backoff and delay parsing
        success = False
        for attempt in range(1, 5):
            try:
                res = engine._synthesize_single_chunk(
                    client=client,
                    types=types,
                    full_prompt=full_prompt,
                    output_wav_path=chunk_path,
                    voice_name=voice_name,
                    temperature=1.0,
                    retries=1
                )
                sec_dur = res["duration"]
                print(f"        ✅ Succeeded: {sec_dur:.2f}s audio duration.")
                shutil.copyfile(chunk_path, section_export)
                if artifact_dir and os.path.exists(artifact_dir):
                    try:
                        shutil.copyfile(chunk_path, os.path.join(artifact_dir, f"section_{i:02d}_speed_1.0x.wav"))
                    except Exception:
                        pass
                success = True
                break
            except Exception as e:
                err_str = str(e)
                print(f"        ⚠️ Attempt {attempt}/4 encountered error: {err_str[:120]}...")
                wait_sec = 20.0
                if "retry in" in err_str:
                    m = re.search(r'retry in\s+([\d\.]+)\s*s', err_str)
                    if m:
                        wait_sec = float(m.group(1)) + 3.0
                elif "retryDelay" in err_str:
                    m = re.search(r"'retryDelay':\s*'(\d+)s'", err_str)
                    if m:
                        wait_sec = float(m.group(1)) + 3.0
                print(f"        ⏳ Waiting {wait_sec:.1f}s before retrying...")
                time.sleep(wait_sec)
                # Rotate key if another key is available
                engine.rotate_key()
                client = genai.Client(api_key=engine.api_key)

        if not success:
            print(f"❌ Failed to synthesize Section {i}. Stopping batch.")
            sys.exit(1)

        # Sleep between sections as requested (10-15s)
        if i < total_sections and delay_between_sections > 0:
            print(f"        💤 Sleeping {delay_between_sections}s before next section...")
            time.sleep(delay_between_sections)

    # All sections completed! Now concatenate into master file
    print("\n" + "=" * 85)
    print(f"🔗 CONCATENATING ALL {total_sections} SECTIONS INTO MASTER AUDIO...")
    print("=" * 85)

    sample_rate = 24000
    num_channels = 1
    sampwidth = 2
    silence_bytes = b'\x00' * int(sample_rate * num_channels * sampwidth * pause_between_sections)

    with wave.open(output_master_wav, 'wb') as outfile:
        outfile.setnchannels(num_channels)
        outfile.setsampwidth(sampwidth)
        outfile.setframerate(sample_rate)

        for idx, c_path in enumerate(chunk_files):
            with wave.open(c_path, 'rb') as infile:
                outfile.writeframes(infile.readframes(infile.getnframes()))
            if idx < len(chunk_files) - 1 and pause_between_sections > 0:
                outfile.writeframes(silence_bytes)

    # Master stats
    with wave.open(output_master_wav, 'rb') as wf:
        total_frames = wf.getnframes()
        master_duration = total_frames / float(sample_rate)
    master_size = os.path.getsize(output_master_wav)

    # Make secondary copy
    alt_copy = os.path.join(ROOT_DIR, "project_content", "audio", "full_voiceover_master_1.0x.wav")
    shutil.copyfile(output_master_wav, alt_copy)

    if artifact_dir and os.path.exists(artifact_dir):
        try:
            shutil.copyfile(output_master_wav, os.path.join(artifact_dir, "master_full_voiceover_1.0x.wav"))
        except Exception:
            pass

    mins = int(master_duration // 60)
    secs = int(master_duration % 60)
    print("🎉 ALL 17 SECTIONS SUCCESSFULLY GENERATED & CONCATENATED!")
    print(f"  • Master File : {output_master_wav}")
    print(f"  • Total Time  : {master_duration:.2f}s (~{mins} minutes {secs} seconds)")
    print(f"  • Total Size  : {master_size / (1024*1024):.2f} MB")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    run_batch_narrator()

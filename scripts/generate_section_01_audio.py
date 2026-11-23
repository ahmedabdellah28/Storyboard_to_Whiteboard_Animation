import os
import sys
import re

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine

def extract_section_01():
    transcript_file = os.path.join(ROOT_DIR, "project_content", "transcript_to_speech.txt")
    with open(transcript_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Match SECTION 01 content until next SECTION or end
    pattern = r"SECTION 01[^\n]*\n+(.*?)(?=\n+SECTION 02|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        raise ValueError("Could not find SECTION 01 in transcript_to_speech.txt")

    section_text = match.group(1).strip()
    return section_text

def main():
    text = extract_section_01()
    print("=" * 70)
    print("🎙️ GENERATING AUDIO FOR SECTION 01 (NEW PROJECT)")
    print("=" * 70)
    print(f"Words Count: {len(text.split())}")
    print(f"Snippet: {text[:100]}...\n")

    output_dir = os.path.join(ROOT_DIR, "project_content", "audio")
    os.makedirs(output_dir, exist_ok=True)
    output_wav = os.path.join(output_dir, "section_01.wav")

    engine = VoiceStudioEngine()
    print(f"• Model       : {engine.model}")
    print(f"• API Keys    : {len(engine.api_keys)} keys loaded")
    print(f"• Temperature : 0.8")
    print(f"• Speed       : 1.0")
    print(f"• Output File : {output_wav}\n")

    res = engine.generate_speech(
        transcript=text,
        output_wav_path=output_wav,
        voice_name="Fenrir",
        profile_key="SAUDI_YOUTH_CREATOR",
        director_note_key="HIGH_ENERGY_YOUTUBE",
        temperature=0.8,
        speed=1.0
    )

    print("=" * 70)
    print("🎉 SECTION 01 AUDIO GENERATION COMPLETE!")
    print(f"• File Path: {res['output_path']}")
    print(f"• Duration : {res['duration']}s")
    print(f"• Rate     : {res['sample_rate']} Hz")
    print("=" * 70)

if __name__ == "__main__":
    main()

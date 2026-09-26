"""
CLI Tool: Generate Expressive Arabic Voiceover using Gemini GenAI TTS
Directly generates high-quality WAV audio ready for the Whiteboard Animation Engine.
"""
import os
import sys
import argparse

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import re

# pyrefly: ignore [missing-import]
from engine.audio.tts_engine import GeminiTTSEngine, AUDIO_PROFILES, DIRECTOR_NOTES

DEFAULT_SCRIPT_FILE = os.path.join(ROOT_DIR, "project_content", "transcript_to_speech.txt")


def extract_first_sentence(text: str) -> str:
    """Extracts the first spoken sentence, ignoring stage tags like [emphasis]."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return "voiceover"
    
    # Filter out lines that are purely emotion/stage cues like [emphasis], [fast], etc.
    spoken_lines = [
        line for line in lines 
        if not (line.startswith('[') and line.endswith(']'))
        and not (line.startswith('(') and line.endswith(')'))
    ]
    candidate_line = spoken_lines[0] if spoken_lines else lines[0]
    
    # Strip any inline tags e.g. [emphasis]
    clean_line = re.sub(r'\[.*?\]', '', candidate_line).strip()
    clean_line = re.sub(r'\(.*?\)', '', clean_line).strip()
    if not clean_line:
        clean_line = candidate_line

    parts = re.split(r'[.!?؟]', clean_line)
    first_sentence = parts[0].strip() if parts and parts[0].strip() else clean_line
    return first_sentence


def sanitize_filename(name: str, max_len: int = 70) -> str:
    """Sanitizes text to form a safe, legal Windows/Linux filename."""
    cleaned = re.sub(r'[<>:"/\\|?*\n\r\t]', '', name).strip()
    cleaned = cleaned.rstrip('. ')
    if not cleaned:
        cleaned = "voiceover"
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip('. ')
    return cleaned


def main():
    parser = argparse.ArgumentParser(description="Generate Arabic Voiceover via Gemini TTS")
    parser.add_argument("--text", type=str, default=None, help="Spoken text/transcript")
    parser.add_argument("--script-file", type=str, default=None, help="Path to text file containing script")
    parser.add_argument("--output", type=str, default=None, help="Output WAV file path (defaults to first sentence of script)")
    parser.add_argument("--voice", type=str, default="Fenrir", help="Gemini Voice Name (e.g. Fenrir, Puck, Aoede, Kore, Charon)")
    parser.add_argument("--profile", type=str, default="SAUDI_YOUTH_CREATOR", choices=list(AUDIO_PROFILES.keys()), help="Audio Persona Profile")
    parser.add_argument("--director-note", type=str, default="HIGH_ENERGY_YOUTUBE", choices=list(DIRECTOR_NOTES.keys()), help="Director's note style")
    parser.add_argument("--api-key", type=str, default=None, help="Optional Gemini API Key")
    parser.add_argument("--model", type=str, default="gemini-3.1-flash-tts-preview", help="Gemini TTS Model")

    args = parser.parse_args()

    # Determine transcript source
    script_source = None
    if args.script_file and os.path.exists(args.script_file):
        script_source = args.script_file
        with open(args.script_file, "r", encoding="utf-8") as f:
            transcript = f.read()
    elif args.text:
        transcript = args.text
        script_source = "Direct text input"
    elif os.path.exists(DEFAULT_SCRIPT_FILE):
        script_source = DEFAULT_SCRIPT_FILE
        with open(DEFAULT_SCRIPT_FILE, "r", encoding="utf-8") as f:
            transcript = f.read()
    else:
        transcript = "النجاح في هذا المستوى ما يعتمد على الذكاء الخارق.\nيعتمد على كيف تلعب أوراقك."
        script_source = "Default fallback"

    # Determine output filename from first sentence if not explicitly given
    if args.output:
        output_file = args.output
    else:
        first_sent = extract_first_sentence(transcript)
        clean_name = sanitize_filename(first_sent)
        output_file = os.path.join(ROOT_DIR, "project_content", "audio", f"{clean_name}.wav")

    engine = GeminiTTSEngine(api_key=args.api_key, model=args.model)

    if not engine.api_key:
        print("\n" + "=" * 85)
        print("⚠️  تنبيه: لم يتم العثور على مفتاح GEMINI_API_KEY !")
        print("=" * 85)
        print("يمكنك وضع المفتاح بإحدى الطرق السهلة التالية:")
        print("  1. الطريقة الأفضل (ملف .env):")
        print("     افتح ملف `.env` في مجلد المشروع وضع المفتاح داخله:")
        print("     GEMINI_API_KEY=AIzaSy...")
        print("")
        print("  2. في نافذة PowerShell مباشرة قبل تشغيل الأمر:")
        print('     $env:GEMINI_API_KEY="AIzaSy..."')
        print("")
        print("  3. تمرير المفتاح مع الأمر مباشرة عبر البراميتر:")
        print('     python tools/generate_tts_voiceover.py --api-key "AIzaSy..."')
        print("=" * 85 + "\n")
        sys.exit(1)

    print("=" * 80)
    print("      🎙️ GEMINI GENAI VOICE-OVER GENERATION TOOL 🎙️")
    print("=" * 80)
    print(f"Script Source   : {script_source}")
    print(f"Persona Profile : {args.profile}")
    print(f"Voice           : {args.voice}")
    print(f"Output File     : {output_file}")
    print(f"Transcript Snippet:\n{transcript[:150]}...\n")

    try:
        res = engine.generate_speech(
            transcript=transcript,
            output_wav_path=output_file,
            voice_name=args.voice,
            profile_key=args.profile,
            director_note_key=args.director_note
        )
        print(f"🎉 Voiceover successfully generated! File ready at: {res['output_path']}")
        return res
    except Exception as e:
        print(f"❌ Error generating speech: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

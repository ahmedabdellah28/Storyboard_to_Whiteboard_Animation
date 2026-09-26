import os
import sys

# Safe console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine

engine = VoiceStudioEngine()
script_file = r"sections/06_mango/script.txt"
output_wav = r"sections/06_mango/voiceover.wav"

with open(script_file, "r", encoding="utf-8") as f:
    transcript = f.read().strip()

print(f"Synthesizing Section 06 Mango voiceover ({len(transcript.split())} words)...")

res = engine.generate_speech(
    transcript=transcript,
    output_wav_path=output_wav,
    voice_name="Fenrir",
    profile_key="SAUDI_YOUTH_CREATOR",
    director_note_key="DYNAMIC_WHITEBOARD_SWEETSPOT",
    speed=1.0,
    auto_chunk=False
)

print(f"\n--- SUCCESS ---")
print(f"Generated: {res['output_path']}")
print(f"Duration: {res['duration']:.2f}s")

import os
import sys

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine

engine = VoiceStudioEngine()

script_file = "project_content/sections_scripts/02_kiwi_الكيوي.txt"
output_file = "project_content/audio/kiwi_voiceover_sweetspot.wav"

with open(script_file, "r", encoding="utf-8") as f:
    transcript = f.read()

res = engine.generate_speech(
    transcript=transcript,
    output_wav_path=output_file,
    voice_name="Fenrir",
    profile_key="SAUDI_YOUTH_CREATOR",
    director_note_key="DYNAMIC_WHITEBOARD_SWEETSPOT",
    speed=1.0,
    auto_chunk=False # Single-shot natural continuous delivery!
)

print(f"\n--- SUCCESS ---")
print(f"Generated: {res['output_path']}")
print(f"Duration: {res['duration']:.2f}s")

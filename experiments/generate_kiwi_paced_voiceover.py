import os
import sys

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine
from voice_studio.profiles import AUDIO_PROFILES, DIRECTOR_NOTES

engine = VoiceStudioEngine()

script_file = "project_content/sections_scripts/02_kiwi_paced.txt"
output_file = "project_content/audio/kiwi_voiceover_paced.wav"
chunks_dir = "project_content/audio/kiwi_chunks_paced"

with open(script_file, "r", encoding="utf-8") as f:
    transcript = f.read()

res = engine.generate_segmented_speech(
    transcript=transcript,
    output_wav_path=output_file,
    voice_name="Fenrir",
    profile_key="SAUDI_YOUTH_CREATOR",
    director_note_key="WHITEBOARD_PACED",
    speed=1.0,
    pause_between_sections=1.2, # Natural 1.2s camera transition pause between rows
    chunks_dir=chunks_dir,
    resume=True
)

print("\n--- GENERATION COMPLETED ---")
print(f"Final output: {res['output_path']}")
print(f"Total Duration: {res['duration']:.2f} seconds")
print(f"Sample Rate: {res['sample_rate']} Hz")

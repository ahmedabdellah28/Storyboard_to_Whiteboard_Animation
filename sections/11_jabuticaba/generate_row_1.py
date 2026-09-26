import os
import sys
import time

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine

audio_dir = r"sections/11_jabuticaba/scratch/row_audio"
os.makedirs(audio_dir, exist_ok=True)

text = "الجابوتيكابا... أو مثل ما يسمونها أحياناً: العنب البرازيلي! وهذي من أغرب الفواكه في العالم، لأن أزهارها وثمارها تنمو مباشرة على الجذع الرئيسي والفروع السميكة، في ظاهرة نباتية مذهلة."

engine = VoiceStudioEngine()
out_wav = os.path.join(audio_dir, "row_1.wav")

print("Synthesizing Row 1 with VoiceStudioEngine...")
res = engine.generate_speech(
    transcript=text,
    output_wav_path=out_wav,
    voice_name="Fenrir",
    profile_key="SAUDI_YOUTH_CREATOR",
    director_note_key="DYNAMIC_WHITEBOARD_SWEETSPOT",
    speed=1.0,
    auto_chunk=False
)
print(f"Row 1 result: {res}")

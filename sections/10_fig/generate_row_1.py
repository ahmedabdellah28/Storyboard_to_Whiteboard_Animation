import os
import sys

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine

audio_dir = r"sections/10_fig/scratch/row_audio"
os.makedirs(audio_dir, exist_ok=True)

text = "التين... التين أغرب مما يبدو. وفيه فرضيات وأدلة أثرية تخليه من أقدم النباتات اللي زرعها الإنسان، ويمكن حتى أقدم من الحبوب، حيث عثر علماء الآثار في وادي الأردن على أدلة تعود لأكثر من أحد عشر ألف سنة."

engine = VoiceStudioEngine()
out_wav = os.path.join(audio_dir, "row_1.wav")

print("Synthesizing Row 1...")
res = engine.generate_speech(
    transcript=text,
    output_wav_path=out_wav,
    voice_name="Fenrir",
    profile_key="SAUDI_YOUTH_CREATOR",
    director_note_key="DYNAMIC_WHITEBOARD_SWEETSPOT",
    speed=1.0,
    auto_chunk=False
)
print(f"Row 1 generated successfully: {res['output_path']} ({res['duration']:.2f}s)")

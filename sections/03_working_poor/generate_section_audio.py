import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.voiceover_engine import generate_voiceover_zero_truncation

SEC_DIR = os.path.join(ROOT_DIR, "sections", "03_working_poor")
script_path = os.path.join(SEC_DIR, "script.txt")
out_wav = os.path.join(SEC_DIR, "voiceover.wav")
chunks_dir = os.path.join(SEC_DIR, "audio_chunks")

print("🎙️ Starting Zero-Truncation Voiceover Generation for Section 03 (Working Poor)...")
wav_path, dur = generate_voiceover_zero_truncation(
    script_path=script_path,
    output_wav_path=out_wav,
    chunks_dir=chunks_dir,
    voice_name="Fenrir",
    speed_factor=1.1,
    max_words_per_chunk=28
)
print(f"✅ Section 03 Voiceover generated successfully: {wav_path} ({dur:.2f}s)")

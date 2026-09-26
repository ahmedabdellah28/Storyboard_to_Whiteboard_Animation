import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "02_extreme_poverty")
WHISPER_PATH = os.path.join(SEC_DIR, "timing", "whisper.json")

with open(WHISPER_PATH, "r", encoding="utf-8") as f:
    whisper_data = json.load(f)

if isinstance(whisper_data, dict):
    print("Keys:", whisper_data.keys())
    segments = whisper_data.get("segments", [])
else:
    segments = whisper_data

print(f"Total segments: {len(segments)}")
for i, seg in enumerate(segments):
    print(f"[{i:02d}] {seg['start']:6.2f} -> {seg['end']:6.2f} : {seg['text']}")

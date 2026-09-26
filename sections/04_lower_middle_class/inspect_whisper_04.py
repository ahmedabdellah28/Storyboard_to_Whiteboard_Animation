import os
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "04_lower_middle_class")
WHISPER_PATH = os.path.join(SEC_DIR, "timing", "whisper.json")

with open(WHISPER_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total duration: {data.get('duration')}s")
print(f"Total segments: {len(data.get('segments', []))}")

for i, seg in enumerate(data.get('segments', [])):
    text = seg.get('text', '').strip()
    st = seg.get('start', 0.0)
    en = seg.get('end', 0.0)
    print(f"[{st:05.2f} - {en:05.2f}] {text}")

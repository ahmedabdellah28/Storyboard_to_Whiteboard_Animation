import os
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "06_upper_middle_class")
WHISPER_PATH = os.path.join(SEC_DIR, "timing", "whisper.json")

with open(WHISPER_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

for seg in data.get('segments', []):
    for w in seg.get('words', []):
        word = w.get('word', '').strip()
        st = w.get('start', 0.0)
        en = w.get('end', 0.0)
        print(f"{st:05.2f} - {en:05.2f}: {word}")

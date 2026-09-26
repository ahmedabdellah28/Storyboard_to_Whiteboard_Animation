import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
WHISPER_PATH = os.path.join(ROOT_DIR, "sections", "02_extreme_poverty", "timing", "whisper.json")

with open(WHISPER_PATH, "r", encoding="utf-8") as f:
    d = json.load(f)

for seg in d["segments"]:
    words = seg.get("words", [])
    w_str = " | ".join([f"{w['word']}({w['start']:.2f}-{w['end']:.2f})" for w in words])
    print(f"[{seg['start']:5.2f}-{seg['end']:5.2f}] {w_str}")

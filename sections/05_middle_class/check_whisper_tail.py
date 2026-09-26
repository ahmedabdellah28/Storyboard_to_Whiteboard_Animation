import os
import json

path = r"E:\image_to_animate\sections\05_middle_class\timing\whisper.json"
with open(path, "r", encoding="utf-8") as f:
    d = json.load(f)

for s in d.get("segments", []):
    if s.get("start", 0) > 65.0:
        print(f"[{s['start']:5.2f} .. {s['end']:5.2f}] {s['text']}")

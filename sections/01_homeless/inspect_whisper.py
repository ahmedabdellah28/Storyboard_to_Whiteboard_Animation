import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

with open('sections/01_homeless/timing/whisper.json', 'r', encoding='utf-8') as f:
    w_data = json.load(f)

segments = w_data.get('segments', [])
print(f"Total Whisper segments: {len(segments)}")
for i, seg in enumerate(segments, 1):
    print(f"Seg {i:02d}: [{seg['start']:6.2f}s .. {seg['end']:6.2f}s] {seg['text']}")

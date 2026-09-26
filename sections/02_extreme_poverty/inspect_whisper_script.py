import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

whisper_data = json.load(open(r'sections\02_extreme_poverty\timing\whisper.json', encoding='utf-8'))
segs = whisper_data['segments']
print(f"Total Whisper segments: {len(segs)}, duration: {whisper_data.get('duration', 106.56):.2f}s")
for idx, s in enumerate(segs):
    print(f"{idx+1:02d}: [{s['start']:6.2f}s .. {s['end']:6.2f}s] ({s['end']-s['start']:4.2f}s) \"{s['text']}\"")

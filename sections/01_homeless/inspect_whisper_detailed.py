import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

whisper_data = json.load(open(r'sections\01_homeless\timing\whisper.json', encoding='utf-8'))
segs = whisper_data['segments']
print(f"Total segments: {len(segs)}")
for idx, s in enumerate(segs):
    words = s.get('words', [])
    w_info = f"words: {len(words)}"
    print(f"{idx+1:02d}: [{s['start']:6.2f}s .. {s['end']:6.2f}s] ({s['end']-s['start']:4.2f}s) \"{s['text']}\"")

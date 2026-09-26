import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

with open('sections/01_homeless/timing/sentences.json', 'r', encoding='utf-8') as f:
    s_data = json.load(f)

sentences = s_data.get('sentences', s_data)
print(f"Total sentences: {len(sentences)}")
for x in sentences:
    print(f"{x['id']}: [{x['start']:6.2f}s .. {x['end']:6.2f}s] {x['text']}")

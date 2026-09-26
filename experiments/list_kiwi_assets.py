import json
import os

with open('project_content/kiwi_assets/metadata.json', 'r', encoding='utf-8') as f:
    meta = json.load(f)

for aid, info in sorted(meta.items()):
    box = info['orig_box']
    print(f"{aid}: Row {info['row']}, Col {info['col']:02d} -> Box=[X={box[0]:4d}, Y={box[1]:4d}, W={box[2]:3d}, H={box[3]:3d}], Area={info['area']:5d}")

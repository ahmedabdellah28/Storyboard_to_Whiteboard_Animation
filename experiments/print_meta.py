import json

with open("experiments/segmented_elements/elements_metadata.json", "r") as f:
    data = json.load(f)

for p, pd in data.items():
    print(f"*** {p} (size {pd['width']}x{pd['height']}) ***")
    for c in pd['components']:
        print(f"  comp {c['index']:02d}: bbox=({c['x']}, {c['y']}, {c['w']}, {c['h']}), area={c['area']}")

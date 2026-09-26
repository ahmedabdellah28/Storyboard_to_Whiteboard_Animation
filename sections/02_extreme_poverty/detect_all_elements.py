import cv2
import numpy as np
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

img = cv2.imread(r'sections\02_extreme_poverty\storyboard.png')
h, w = img.shape[:2]

# Binarize whiteboard: pure white background > 240
is_bg = (img[:, :, 0] > 240) & (img[:, :, 1] > 240) & (img[:, :, 2] > 240)
fg_mask = (~is_bg).astype(np.uint8) * 255

# Close small gaps
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

# Connected components
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)

# Row bands detected previously
bands = [
    (24, 218),
    (246, 430),
    (454, 622),
    (623, 802),
    (820, 1007)
]

print(f"Total connected components found: {num_labels - 1}")

# Group significant components by row
rows_components = [[] for _ in range(len(bands))]

for cid in range(1, num_labels):
    area = stats[cid, cv2.CC_STAT_AREA]
    if area < 100: # filter noise
        continue
    x = stats[cid, cv2.CC_STAT_LEFT]
    y = stats[cid, cv2.CC_STAT_TOP]
    bw = stats[cid, cv2.CC_STAT_WIDTH]
    bh = stats[cid, cv2.CC_STAT_HEIGHT]
    cy = centroids[cid][1]
    cx = centroids[cid][0]

    # Find matching band
    for r_idx, (y1, y2) in enumerate(bands):
        if y1 - 20 <= cy <= y2 + 20:
            rows_components[r_idx].append({
                'cid': cid,
                'x': int(x), 'y': int(y), 'w': int(bw), 'h': int(bh),
                'cx': float(cx), 'cy': float(cy),
                'area': int(area)
            })
            break

for r_idx, comps in enumerate(rows_components):
    # Sort left to right by cx
    comps.sort(key=lambda c: c['cx'])
    print(f"\n--- ROW {r_idx + 1} ({len(comps)} components) ---")
    for i, c in enumerate(comps):
        print(f"  Col {i+1:02d}: x={c['x']:4d}, y={c['y']:4d}, w={c['w']:3d}, h={c['h']:3d}, area={c['area']:5d}")

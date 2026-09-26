import cv2
import numpy as np
import os
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

img = cv2.imread(r'sections\02_extreme_poverty\storyboard.png')
h, w = img.shape[:2]

out_assets = r"sections\02_extreme_poverty\assets"
os.makedirs(out_assets, exist_ok=True)

# Binarize
is_bg = (img[:, :, 0] > 240) & (img[:, :, 1] > 240) & (img[:, :, 2] > 240)
fg_mask = (~is_bg).astype(np.uint8) * 255
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)

# Row bands
bands = [
    (1, (10, 230)),
    (2, (235, 440)),
    (3, (445, 630)),
    (4, (630, 815)),
    (5, (815, 1020))
]

print(f"Image dimensions: {w}x{h}")
for r_num, (y1, y2) in bands:
    comps = []
    for cid in range(1, num_labels):
        cy = centroids[cid][1]
        area = stats[cid, cv2.CC_STAT_AREA]
        if y1 <= cy <= y2 and area > 600:
            x = stats[cid, cv2.CC_STAT_LEFT]
            y = stats[cid, cv2.CC_STAT_TOP]
            bw = stats[cid, cv2.CC_STAT_WIDTH]
            bh = stats[cid, cv2.CC_STAT_HEIGHT]
            comps.append((x, y, bw, bh, area, cid))
    comps.sort(key=lambda c: c[0])
    print(f"Row {r_num}: {len(comps)} components (area > 600)")

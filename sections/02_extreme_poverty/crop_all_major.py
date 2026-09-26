import cv2
import numpy as np
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

img = cv2.imread(r'sections\02_extreme_poverty\storyboard.png')
h, w = img.shape[:2]

out_crops = r"sections\02_extreme_poverty\scratch\detected_crops"
os.makedirs(out_crops, exist_ok=True)

# Binarize
is_bg = (img[:, :, 0] > 240) & (img[:, :, 1] > 240) & (img[:, :, 2] > 240)
fg_mask = (~is_bg).astype(np.uint8) * 255
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)

bands = [
    (1, (20, 230)),
    (2, (235, 440)),
    (3, (445, 630)),
    (4, (630, 815)),
    (5, (815, 1020))
]

for r_num, (y1, y2) in bands:
    r_comps = []
    for cid in range(1, num_labels):
        cy = centroids[cid][1]
        area = stats[cid, cv2.CC_STAT_AREA]
        if y1 <= cy <= y2 and area > 1000:
            x = stats[cid, cv2.CC_STAT_LEFT]
            y = stats[cid, cv2.CC_STAT_TOP]
            bw = stats[cid, cv2.CC_STAT_WIDTH]
            bh = stats[cid, cv2.CC_STAT_HEIGHT]
            r_comps.append((x, y, bw, bh, area, cid))
            
    r_comps.sort(key=lambda c: c[0])
    print(f"\n--- ROW {r_num}: {len(r_comps)} major components ---")
    for idx, (x, y, bw, bh, area, cid) in enumerate(r_comps, 1):
        crop = img[max(0, y-5):min(h, y+bh+5), max(0, x-5):min(w, x+bw+5)]
        fname = f"r{r_num}_{idx:02d}_x{x}.png"
        cv2.imwrite(os.path.join(out_crops, fname), crop)
        print(f"  {fname:<20} | x={x:4d}, y={y:4d}, w={bw:3d}, h={bh:3d}, area={area:6d}")

print(f"\nAll crops saved to {out_crops}")

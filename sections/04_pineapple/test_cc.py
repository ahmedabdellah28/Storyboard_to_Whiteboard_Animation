import cv2
import numpy as np
import os
import json

img_path = 'sections/04_pineapple/storyboard.png'
bgr = cv2.imread(img_path)
h, w = bgr.shape[:2]

# 1. Detect pure white background
is_bg = (bgr[:, :, 0] > 245) & (bgr[:, :, 1] > 245) & (bgr[:, :, 2] > 245)
fg_mask = (~is_bg).astype(np.uint8) * 255

# 2. Morphological closure to solidify fine lines
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_mask_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

# 3. Connected components
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_mask_clean, connectivity=8)
print(f"Total components detected: {num_labels}")

# 4. Check for any touching bridges between rows or adjacent elements
comps = []
for i in range(1, num_labels):
    area = int(stats[i, cv2.CC_STAT_AREA])
    if area >= 300:
        cx, cy = float(centroids[i][0]), float(centroids[i][1])
        bx, by = int(stats[i, cv2.CC_STAT_LEFT]), int(stats[i, cv2.CC_STAT_TOP])
        bw, bh = int(stats[i, cv2.CC_STAT_WIDTH]), int(stats[i, cv2.CC_STAT_HEIGHT])
        comps.append({
            'id': i, 'cx': cx, 'cy': cy,
            'bx': bx, 'by': by, 'bw': bw, 'bh': bh,
            'area': area
        })

comps.sort(key=lambda x: (x['cy'] // 240, x['bx']))
print(f"Significant components (area >= 300): {len(comps)}")
for c in comps:
    print(f"ID={c['id']:2d} | Cy={c['cy']:5.1f}, Cx={c['cx']:5.1f} | Box=[X={c['bx']:4d}, Y={c['by']:4d}, W={c['bw']:3d}, H={c['bh']:3d}] | Area={c['area']:6d}")

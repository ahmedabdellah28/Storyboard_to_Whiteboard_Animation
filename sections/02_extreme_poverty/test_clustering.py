import cv2
import numpy as np
import sys

sys.stdout.reconfigure(encoding='utf-8')

img = cv2.imread(r'sections\02_extreme_poverty\storyboard.png')
h, w = img.shape[:2]

is_bg = (img[:, :, 0] > 240) & (img[:, :, 1] > 240) & (img[:, :, 2] > 240)
fg_mask = (~is_bg).astype(np.uint8) * 255
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)

bands = [
    (1, (10, 230)),
    (2, (235, 440)),
    (3, (445, 630)),
    (4, (630, 815)),
    (5, (815, 1020))
]

for r_num, (y1, y2) in bands:
    comps = []
    for cid in range(1, num_labels):
        cy = centroids[cid][1]
        area = stats[cid, cv2.CC_STAT_AREA]
        if y1 <= cy <= y2 and area > 150:
            x = stats[cid, cv2.CC_STAT_LEFT]
            y = stats[cid, cv2.CC_STAT_TOP]
            bw = stats[cid, cv2.CC_STAT_WIDTH]
            bh = stats[cid, cv2.CC_STAT_HEIGHT]
            comps.append([x, y, bw, bh, area, cid])
            
    comps.sort(key=lambda c: c[0])
    
    # Merge horizontally adjacent components if gap < 20 px
    clusters = []
    for c in comps:
        if not clusters:
            clusters.append(c)
        else:
            prev = clusters[-1]
            prev_x2 = prev[0] + prev[2]
            cur_x1 = c[0]
            if cur_x1 - prev_x2 < 22:
                # Merge
                nx1 = min(prev[0], c[0])
                ny1 = min(prev[1], c[1])
                nx2 = max(prev_x2, c[0] + c[2])
                ny2 = max(prev[1] + prev[3], c[1] + c[3])
                clusters[-1] = [nx1, ny1, nx2 - nx1, ny2 - ny1, prev[4] + c[4], None]
            else:
                clusters.append(c)
                
    print(f"\nRow {r_num}: {len(clusters)} visual clusters")
    for i, cl in enumerate(clusters, 1):
        print(f"  Cluster {i:02d}: x=[{cl[0]:4d} .. {cl[0]+cl[2]:4d}] (w={cl[2]:3d}, h={cl[3]:3d}, area={cl[4]:5d})")

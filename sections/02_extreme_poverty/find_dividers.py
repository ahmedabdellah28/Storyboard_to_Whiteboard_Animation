import cv2
import numpy as np
import sys

sys.stdout.reconfigure(encoding='utf-8')

img = cv2.imread(r'sections\02_extreme_poverty\storyboard.png')
h, w = img.shape[:2]

bands = [
    (1, (10, 230)),
    (2, (235, 440)),
    (3, (445, 630)),
    (4, (630, 815)),
    (5, (815, 1020))
]

for r_num, (y1, y2) in bands:
    row = img[y1:y2, :]
    gray = cv2.cvtColor(row, cv2.COLOR_BGR2GRAY)
    fg = (gray < 235).astype(np.uint8)
    col_density = np.sum(fg, axis=0) # sum of non-white pixels in each column
    
    # Print columns where density is very low (< 10)
    low_cols = np.where(col_density < 10)[0]
    # Group contiguous low_cols into valleys/dividers
    valleys = []
    if len(low_cols) > 0:
        v_start = low_cols[0]
        for i in range(1, len(low_cols)):
            if low_cols[i] > low_cols[i-1] + 1:
                valleys.append((v_start, low_cols[i-1]))
                v_start = low_cols[i]
        valleys.append((v_start, low_cols[-1]))
        
    print(f"\nRow {r_num} valleys (density < 10): {len(valleys)} separators")
    for v1, v2 in valleys:
        if v2 - v1 >= 2 and 15 < v1 < 1520:
            print(f"  Divider at x=[{v1:4d} .. {v2:4d}] (width={v2-v1+1})")

import cv2
import numpy as np
import sys

sys.stdout.reconfigure(encoding='utf-8')

img = cv2.imread(r'sections\02_extreme_poverty\storyboard.png')
h, w = img.shape[:2]
bands = [(20, 225), (240, 435), (450, 625), (625, 805), (815, 1010)]

for r_idx, (y1, y2) in enumerate(bands):
    row_crop = img[y1:y2, :]
    gray = cv2.cvtColor(row_crop, cv2.COLOR_BGR2GRAY)
    fg = (gray < 235).astype(np.uint8) * 255
    col_proj = np.sum(fg, axis=0)
    cells = []
    in_cell = False
    c_start = 0
    for x in range(w):
        if col_proj[x] > 80:
            if not in_cell:
                in_cell = True
                c_start = x
        else:
            if in_cell and (x - c_start > 30):
                # Lookahead gap
                if x + 15 >= w or np.max(col_proj[x:min(w, x + 18)]) <= 80:
                    in_cell = False
                    cells.append((c_start, x))
    if in_cell:
        cells.append((c_start, w))
    
    print(f"\nRow {r_idx + 1} ({len(cells)} cells detected):")
    for c_i, (c1, c2) in enumerate(cells):
        print(f"  Cell {c_i + 1:02d}: x=[{c1:4d} .. {c2:4d}] (w={c2 - c1:3d})")

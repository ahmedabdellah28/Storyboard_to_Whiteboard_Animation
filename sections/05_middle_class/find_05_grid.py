import cv2
import numpy as np

img = cv2.imread(r"E:\image_to_animate\sections\05_middle_class\storyboard.png")
h, w = img.shape[:2]
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
is_drawing = gray < 240

row_bounds = [
    (30, 260),
    (300, 515),
    (550, 765),
    (785, 1005)
]

for r_idx, (y1, y2) in enumerate(row_bounds, 1):
    row_crop = is_drawing[y1:y2, :]
    col_dens = np.sum(row_crop, axis=0) / float(y2 - y1)
    
    in_cell = False
    cells = []
    start_x = 0
    for x in range(w):
        if col_dens[x] > 0.01 and not in_cell:
            in_cell = True
            start_x = x
        elif col_dens[x] <= 0.01 and in_cell:
            in_cell = False
            if x - start_x > 20:
                cells.append((start_x, x))
    if in_cell and w - start_x > 20:
        cells.append((start_x, w))
        
    merged = []
    for c in cells:
        if not merged:
            merged.append(c)
        else:
            if c[0] - merged[-1][1] < 20:
                merged[-1] = (merged[-1][0], c[1])
            else:
                merged.append(c)
                
    print(f"Row {r_idx} (y: {y1}..{y2}): {len(merged)} cells:")
    for c_i, (cx1, cx2) in enumerate(merged, 1):
        print(f"   Cell {c_i}: x=[{cx1}..{cx2}], width={cx2-cx1}")

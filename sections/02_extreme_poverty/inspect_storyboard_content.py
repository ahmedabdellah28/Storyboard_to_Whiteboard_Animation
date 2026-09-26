import cv2
import numpy as np
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

img = cv2.imread(r'sections\02_extreme_poverty\storyboard.png')
h, w = img.shape[:2]

bands = [
    ("Row 1", 10, 230),
    ("Row 2", 235, 440),
    ("Row 3", 445, 630),
    ("Row 4", 630, 815),
    ("Row 5", 815, 1020)
]

out_debug = r"sections\02_extreme_poverty\scratch\row_crops"
os.makedirs(out_debug, exist_ok=True)

debug_vis = img.copy()

for r_name, y1, y2 in bands:
    row_crop = img[y1:y2, :]
    cv2.imwrite(os.path.join(out_debug, f"{r_name}.png"), row_crop)
    
    # Detect contours inside row
    gray = cv2.cvtColor(row_crop, cv2.COLOR_BGR2GRAY)
    mask = (gray < 235).astype(np.uint8) * 255
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    boxes = []
    for c in contours:
        bx, by, bw, bh = cv2.boundingRect(c)
        if bw * bh > 500 and bw > 20 and bh > 20: # filter out tiny noise
            boxes.append((bx, by + y1, bw, bh))
            
    # Sort left to right
    boxes.sort(key=lambda b: b[0])
    
    # Merge overlapping or touching boxes
    merged = []
    for b in boxes:
        if not merged:
            merged.append(list(b))
        else:
            prev = merged[-1]
            # If horizontal gap is small (< 25px) and overlap in Y
            if b[0] - (prev[0] + prev[2]) < 25:
                # Merge
                nx1 = min(prev[0], b[0])
                ny1 = min(prev[1], b[1])
                nx2 = max(prev[0] + prev[2], b[0] + b[2])
                ny2 = max(prev[1] + prev[3], b[1] + b[3])
                merged[-1] = [nx1, ny1, nx2 - nx1, ny2 - ny1]
            else:
                merged.append(list(b))
                
    print(f"\n{r_name}: {len(merged)} elements detected")
    for idx, (bx, by, bw, bh) in enumerate(merged, 1):
        cv2.rectangle(debug_vis, (bx, by), (bx + bw, by + bh), (0, 0, 255), 2)
        cv2.putText(debug_vis, f"{idx}", (bx + 5, by + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        print(f"  Item {idx:02d}: x={bx:4d}, y={by:4d}, w={bw:3d}, h={bh:3d}")

cv2.imwrite(os.path.join(out_debug, "all_detected_elements.png"), debug_vis)
print("\nSaved annotated detection image to:", os.path.join(out_debug, "all_detected_elements.png"))

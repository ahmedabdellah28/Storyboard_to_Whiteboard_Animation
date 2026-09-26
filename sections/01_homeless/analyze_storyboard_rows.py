import cv2
import numpy as np

data = np.fromfile('project_content/images/بلا ماوى.png', dtype=np.uint8)
img = cv2.imdecode(data, cv2.IMREAD_COLOR)
h, w = img.shape[:2]
print(f"Storyboard size: {w}x{h}")

is_bg = (img[:, :, 0] > 240) & (img[:, :, 1] > 240) & (img[:, :, 2] > 240)
fg_mask = (~is_bg).astype(np.uint8) * 255

# Analyze vertical projection to find row bands
v_proj = np.sum(fg_mask, axis=1)
threshold = w * 255 * 0.01  # 1% of row width

in_row = False
row_bands = []
start_y = 0
for y, val in enumerate(v_proj):
    if val > threshold and not in_row:
        in_row = True
        start_y = y
    elif val <= threshold and in_row:
        in_row = False
        if y - start_y > 40:  # significant height
            row_bands.append((start_y, y))
if in_row:
    row_bands.append((start_y, len(v_proj)))

print(f"Detected {len(row_bands)} rows:")
for i, (y1, y2) in enumerate(row_bands, 1):
    print(f"Row {i}: y={y1} .. {y2} (height={y2-y1})")

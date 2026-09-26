import cv2
import numpy as np

data = np.fromfile('project_content/images/بلا ماوى.png', dtype=np.uint8)
img = cv2.imdecode(data, cv2.IMREAD_COLOR)
h, w = img.shape[:2]

is_bg = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
fg_mask = (~is_bg).astype(np.uint8) * 255

# Apply morphological closing to connect parts of the same character (eyes, body, props)
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
fg_grouped = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_grouped, connectivity=8)

boxes = []
for i in range(1, num_labels):
    x, y, bw, bh, area = stats[i]
    if area > 1200 and bw > 30 and bh > 30:  # filter noise
        boxes.append((x, y, bw, bh, area))

print(f"Total significant element clusters: {len(boxes)}")

# Sort roughly by y (row) then x (col)
# Group into 6 vertical rows
row_height = h / 6.0
rows = [[] for _ in range(6)]
for b in boxes:
    cx = b[0] + b[2] / 2
    cy = b[1] + b[3] / 2
    r_idx = min(5, int(cy / row_height))
    rows[r_idx].append(b)

for r in range(6):
    rows[r].sort(key=lambda b: b[0])
    print(f"Row {r+1}: {len(rows[r])} elements")
    for c, b in enumerate(rows[r], 1):
        print(f"   Elem {c:02d}: x={b[0]}, y={b[1]}, w={b[2]}, h={b[3]}, area={b[4]}")

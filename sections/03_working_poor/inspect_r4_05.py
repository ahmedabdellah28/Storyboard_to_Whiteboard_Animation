import cv2
import numpy as np

img = cv2.imread(r"E:\image_to_animate\sections\03_working_poor\assets\r4_05_online_course.png", cv2.IMREAD_UNCHANGED)
h, w = img.shape[:2]
print(f"r4_05 size: {w}x{h}")

# Check vertical alpha projection to find the gap between top and bottom
alpha = img[:, :, 3]
row_density = np.sum(alpha > 20, axis=1)

for y in range(h):
    if row_density[y] == 0 or (y > 60 and y < 140 and row_density[y] < 5):
        print(f"Row {y}: alpha count = {row_density[y]}")

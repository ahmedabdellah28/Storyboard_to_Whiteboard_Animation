import cv2
import numpy as np

img = cv2.imread(r"E:\image_to_animate\sections\04_lower_middle_class\storyboard.png")
h, w = img.shape[:2]
print(f"Storyboard Section 04: {w}x{h}")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
is_drawing = gray < 240
row_dens = np.sum(is_drawing, axis=1) / float(w)

for y in range(0, h, 20):
    print(f"y={y:4d}: {'#' * int(row_dens[y] * 60)} ({row_dens[y]:.3f})")

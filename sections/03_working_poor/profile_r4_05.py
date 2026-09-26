import cv2
import numpy as np

img = cv2.imread(r"E:\image_to_animate\sections\03_working_poor\assets\r4_05_online_course.png", cv2.IMREAD_UNCHANGED)
h, w = img.shape[:2]
alpha = img[:, :, 3]
row_density = np.sum(alpha > 20, axis=1)

for y in range(0, h, 5):
    print(f"y={y:3d}: {'#' * int(row_density[y] / 5)} ({row_density[y]})")

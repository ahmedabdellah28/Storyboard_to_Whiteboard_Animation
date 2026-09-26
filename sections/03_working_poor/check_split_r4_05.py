import cv2
import numpy as np

img = cv2.imread(r"E:\image_to_animate\sections\03_working_poor\assets\r4_05_online_course.png", cv2.IMREAD_UNCHANGED)
alpha = img[:, :, 3]

for y in range(92, 106):
    xs = np.where(alpha[y, :] > 20)[0]
    print(f"y={y:3d}: count={len(xs):3d} min_x={xs[0] if len(xs) else -1} max_x={xs[-1] if len(xs) else -1}")

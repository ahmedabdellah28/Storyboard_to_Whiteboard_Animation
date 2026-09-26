import os
import cv2
import numpy as np

sec_dir = r"E:\image_to_animate\sections\03_working_poor"
assets_dir = os.path.join(sec_dir, "assets")
r4_05_path = os.path.join(assets_dir, "r4_05_online_course.png")

img = cv2.imread(r4_05_path, cv2.IMREAD_UNCHANGED)
h, w = img.shape[:2]

# Top: watch series (y: 0 to 95) - 95 cuts right before the lower antenna starts at 96
top_crop = img[0:95, :].copy()
alpha_top = top_crop[:, :, 3]
ys_t, xs_t = np.where(alpha_top > 20)
top_tight = top_crop[np.min(ys_t):np.max(ys_t)+1, np.min(xs_t):np.max(xs_t)+1]

# Bottom: online course (y: 96 to h)
bot_crop = img[96:h, :].copy()
alpha_bot = bot_crop[:, :, 3]
ys_b, xs_b = np.where(alpha_bot > 20)
bot_tight = bot_crop[np.min(ys_b):np.max(ys_b)+1, np.min(xs_b):np.max(xs_b)+1]

p_top = os.path.join(assets_dir, "r4_05a_watch_series.png")
p_bot = os.path.join(assets_dir, "r4_05b_online_course.png")

cv2.imwrite(p_top, top_tight)
cv2.imwrite(p_bot, bot_tight)

print(f"Cleaned saved r4_05a_watch_series: {top_tight.shape[1]}x{top_tight.shape[0]}")
print(f"Cleaned saved r4_05b_online_course: {bot_tight.shape[1]}x{bot_tight.shape[0]}")

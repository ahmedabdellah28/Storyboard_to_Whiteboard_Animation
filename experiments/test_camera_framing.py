import os
import sys
import cv2
import numpy as np

ROOT_DIR = r"E:\image_to_animate"
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.processing.whiteboard_processor import WhiteboardProcessor
from engine.processing.dynamic_border_detector import DynamicBorderDetector

img_path = os.path.join(ROOT_DIR, "project_content", "images", "ChatGPT Image Sep 18, 2026, 04_51_53 PM.png")
img = cv2.imread(img_path)
panels = WhiteboardProcessor.discover_panels(img)

# Master Canvas: 4800 x 2700
canvas_w, canvas_h = 4800, 2700
out_w, out_h = 1920, 1080
pw, ph = 900, 900

margin_x = 450
spacing_x = 600
margin_y = 300
spacing_y = 300

canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)

panel_centers = []
for idx, p in enumerate(panels):
    px, py, pw_orig, ph_orig = p["bbox"]
    raw_crop = img[py:py+ph_orig, px:px+pw_orig]
    clean = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)["clean_crop"]
    
    row = idx // 3
    col = idx % 3
    gx = margin_x + col * (pw + spacing_x)
    gy = margin_y + row * (ph + spacing_y)
    
    # Resize clean panel to 900x900
    resized = cv2.resize(clean, (pw, ph), interpolation=cv2.INTER_LANCZOS4)
    canvas[gy:gy+ph, gx:gx+pw] = resized
    
    # Draw border around panel
    cv2.rectangle(canvas, (gx, gy), (gx + pw, gy + ph), (30, 30, 30), 4)
    
    cx = gx + pw // 2
    cy = gy + ph // 2
    panel_centers.append((cx, cy))

def get_viewport_frame(cx, cy, vw, vh):
    src_pts = np.float32([
        [cx - vw / 2.0, cy - vh / 2.0],
        [cx + vw / 2.0, cy - vh / 2.0],
        [cx - vw / 2.0, cy + vh / 2.0]
    ])
    dst_pts = np.float32([[0, 0], [out_w, 0], [0, out_h]])
    M = cv2.getAffineTransform(src_pts, dst_pts)
    frame = cv2.warpAffine(canvas, M, (out_w, out_h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    return frame

out_dir = "experiments/camera_framing_tests"
os.makedirs(out_dir, exist_ok=True)

# 1. Panel 1 close-up (vw=2000, vh=1125)
f1 = get_viewport_frame(panel_centers[0][0], panel_centers[0][1], 2000, 1125)
cv2.imwrite(os.path.join(out_dir, "test_panel_1_closeup.jpg"), f1)

# 2. Panel 2 close-up
f2 = get_viewport_frame(panel_centers[1][0], panel_centers[1][1], 2000, 1125)
cv2.imwrite(os.path.join(out_dir, "test_panel_2_closeup.jpg"), f2)

# 3. Mid-pan between Panel 1 and Panel 2
mid_cx = (panel_centers[0][0] + panel_centers[1][0]) / 2.0
mid_cy = (panel_centers[0][1] + panel_centers[1][1]) / 2.0
f_mid = get_viewport_frame(mid_cx, mid_cy, 2000, 1125)
cv2.imwrite(os.path.join(out_dir, "test_mid_pan_p1_p2.jpg"), f_mid)

# 4. Panel 4 close-up
f4 = get_viewport_frame(panel_centers[3][0], panel_centers[3][1], 2000, 1125)
cv2.imwrite(os.path.join(out_dir, "test_panel_4_closeup.jpg"), f4)

# 5. Grand Outro (all 6 panels) (vw=5000, vh=2812.5)
f_outro = get_viewport_frame(canvas_w / 2.0, canvas_h / 2.0, 5000, 2812.5)
cv2.imwrite(os.path.join(out_dir, "test_grand_outro_full_sheet.jpg"), f_outro)

print("All framing test frames generated successfully in:", out_dir)

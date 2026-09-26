import os
import sys
import cv2

ROOT_DIR = r"E:\image_to_animate"
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.processing.whiteboard_processor import WhiteboardProcessor
from engine.processing.dynamic_border_detector import DynamicBorderDetector

img = cv2.imread("project_content/images/ChatGPT Image Sep 18, 2026, 06_29_19 PM.png")
panels = WhiteboardProcessor.discover_panels(img)

out_dir = "experiments/apple_storyboard"
os.makedirs(out_dir, exist_ok=True)

for i in range(3):
    px, py, pw, ph = panels[i]["bbox"]
    raw_crop = img[py:py+ph, px:px+pw]
    trimmed = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)["clean_crop"]
    # Resize to standard 900x900
    p_900 = cv2.resize(trimmed, (900, 900), interpolation=cv2.INTER_LANCZOS4)
    cv2.imwrite(os.path.join(out_dir, f"apple_panel_{i+1:02d}.png"), p_900)
    print(f"Panel {i+1} saved to {out_dir}/apple_panel_{i+1:02d}.png (shape: {p_900.shape})")

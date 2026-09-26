"""
High-Precision Semantic Element Extractor for All 6 Storyboard Panels.
Uses pure background floodfill + connected components clustering to isolate
every character, symbol, chart, badge, and icon with subpixel alpha transparency.
"""
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

out_base = "experiments/segmented_elements"
os.makedirs(out_base, exist_ok=True)

panel_elements_catalog = {}

for p_num in range(1, 7):
    px, py, pw, ph = panels[p_num - 1]["bbox"]
    raw_crop = img[py:py+ph, px:px+pw]
    clean = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)["clean_crop"]
    ch, cw = clean.shape[:2]
    
    p_dir = os.path.join(out_base, f"panel_{p_num:02d}")
    os.makedirs(p_dir, exist_ok=True)
    cv2.imwrite(os.path.join(p_dir, "clean_panel.png"), clean)
    
    # 1. Floodfill pure white background from all 4 borders
    bg_mask = np.zeros((ch + 2, cw + 2), dtype=np.uint8)
    ff = clean.copy()
    # Seed floodfill from multiple border points
    for bx in [0, cw // 2, cw - 1]:
        for by in [0, ch // 2, ch - 1]:
            # If the pixel is near white
            if np.all(clean[by, bx] >= 240):
                cv2.floodFill(ff, bg_mask, (bx, by), (0, 255, 0), loDiff=(12, 12, 12), upDiff=(12, 12, 12))
                
    is_bg = (bg_mask[1:-1, 1:-1] > 0)
    is_fg = (~is_bg).astype(np.uint8) * 255
    cv2.imwrite(os.path.join(p_dir, "fg_mask.png"), is_fg)
    
    # 2. Connected Components with filtering
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(is_fg)
    
    valid_comps = []
    for comp_id in range(1, num_labels):
        x, y, w, h, area = stats[comp_id]
        if area >= 80:  # ignore tiny single-pixel noise
            valid_comps.append({
                "id": comp_id,
                "bbox": (x, y, w, h),
                "area": area,
                "center": (float(centroids[comp_id][0]), float(centroids[comp_id][1]))
            })
            
    print(f"Panel {p_num}: {len(valid_comps)} candidate components detected.")
    
    # Save individual components as RGBA
    for c_idx, c in enumerate(valid_comps):
        cid = c["id"]
        x, y, w, h = c["bbox"]
        c_mask = (labels == cid).astype(np.uint8) * 255
        
        # Crop
        crop_bgr = clean[y:y+h, x:x+w].copy()
        crop_a = c_mask[y:y+h, x:x+w].copy()
        
        b, g, r = cv2.split(crop_bgr)
        crop_rgba = cv2.merge([b, g, r, crop_a])
        cv2.imwrite(os.path.join(p_dir, f"comp_{c_idx+1:02d}_area{c['area']}.png"), crop_rgba)
        
print("Inspection and segmentation complete!")

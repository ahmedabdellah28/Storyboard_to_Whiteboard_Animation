"""
Test Step 1: Dynamic Panel Discovery, Ordering & Border-Free Crop Extraction
File: experiments/test_step1_panel_extraction.py

Executes Step 1 exclusively:
1. Discovers all 12 panels dynamically.
2. Orders panels correctly.
3. Crops the interior content while suppressing the outer border.
4. Generates visual validation artifacts for user approval.
"""
import os
import sys
import cv2
import numpy as np

# Add modular pipeline
sys.path.insert(0, r"E:\image_to_animate\experiments\modular_pipeline")
from m1_panel_extractor import DynamicPanelExtractor

MASTER_IMG_PATH = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\.user_uploaded\media_1788292396282.png"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step1_panels"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Load Master Image
master_img = cv2.imread(MASTER_IMG_PATH)
if master_img is None:
    raise FileNotFoundError(f"Cannot load master image: {MASTER_IMG_PATH}")
mh, mw = master_img.shape[:2]

# 2. Run Step 1 Extractor with precise 2px inset
panels = DynamicPanelExtractor.extract_panels(master_img, border_inset=2)
print(f"[STEP 1] Discovered {len(panels)} panels dynamically.")

# 3. Generate Visual Artifact 1: Master Detection & Ordering Map
det_map = master_img.copy()
for p in panels:
    pid = p["id"]
    bx, by, bw, bh = p["outer_bbox"]
    ix, iy, iw_p, ih_p = p["interior_bbox"]
    
    # Outer detected rectangle in Cyan
    cv2.rectangle(det_map, (bx, by), (bx + bw, by + bh), (255, 200, 0), 2)
    # Inner cropped zone in Green (Zero Border)
    cv2.rectangle(det_map, (ix, iy), (ix + iw_p, iy + ih_p), (0, 255, 0), 2)
    
    # Badge showing panel order
    badge_text = f"Panel #{pid:02d}"
    cv2.rectangle(det_map, (bx + 4, by + 4), (bx + 80, by + 22), (0, 0, 0), -1)
    cv2.putText(det_map, badge_text, (bx + 6, by + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1, cv2.LINE_AA)

DET_MAP_PATH = os.path.join(OUTPUT_DIR, "step1_panel_detection_map.png")
cv2.imwrite(DET_MAP_PATH, det_map)
print(f"[STEP 1] Detection map saved: {DET_MAP_PATH}")

# 4. Save each individual cropped panel & build a clean 3x4 Gallery Grid
card_w, card_h = 320, 210
cols, rows = 4, 3
grid_img = np.full((rows * (card_h + 35) + 60, cols * (card_w + 15) + 15, 3), 245, dtype=np.uint8)

# Title Banner
cv2.rectangle(grid_img, (0, 0), (grid_img.shape[1], 50), (30, 30, 40), -1)
cv2.putText(grid_img, "STEP 1: ALL DYNAMICALLY EXTRACTED INTERIOR PANELS (ZERO BORDERS)", 
            (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (0, 220, 255), 2, cv2.LINE_AA)

for idx, p in enumerate(panels[:12]):
    pid = p["id"]
    crop = p["crop"]
    
    # Save individual crop
    crop_path = os.path.join(OUTPUT_DIR, f"panel_{pid:02d}_interior_crop.png")
    cv2.imwrite(crop_path, crop)
    
    # Add to gallery
    r = idx // cols
    c = idx % cols
    gx = 15 + c * (card_w + 15)
    gy = 60 + r * (card_h + 35)
    
    # White card frame
    cv2.rectangle(grid_img, (gx, gy), (gx + card_w, gy + card_h), (255, 255, 255), -1)
    cv2.rectangle(grid_img, (gx, gy), (gx + card_w, gy + card_h), (180, 180, 180), 1)
    
    # Fit crop into card
    sc = min((card_w - 10) / float(crop.shape[1]), (card_h - 10) / float(crop.shape[0]))
    cw_sc = int(crop.shape[1] * sc)
    ch_sc = int(crop.shape[0] * sc)
    crop_sc = cv2.resize(crop, (cw_sc, ch_sc), interpolation=cv2.INTER_AREA)
    
    ox = gx + (card_w - cw_sc) // 2
    oy = gy + (card_h - ch_sc) // 2
    grid_img[oy:oy+ch_sc, ox:ox+cw_sc] = crop_sc
    
    # Card Header
    cv2.rectangle(grid_img, (gx, gy), (gx + card_w, gy + 20), (45, 45, 55), -1)
    cv2.putText(grid_img, f"Panel #{pid:02d} ({crop.shape[1]}x{crop.shape[0]}px)", 
                (gx + 8, gy + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 255), 1, cv2.LINE_AA)

GRID_PATH = os.path.join(OUTPUT_DIR, "step1_all_panels_grid.png")
cv2.imwrite(GRID_PATH, grid_img)
print(f"[STEP 1] All panels grid saved: {GRID_PATH}")

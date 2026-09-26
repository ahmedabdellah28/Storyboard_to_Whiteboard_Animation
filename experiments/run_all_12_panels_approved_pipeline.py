"""
Run Full Approved Pipeline Across All 12 Panels (Steps 1, 2, and 3)
File: experiments/run_all_12_panels_approved_pipeline.py

Executes:
- Step 1: Dynamic Panel Discovery & Clean Interior Extraction (Panels #01 to #12)
- Step 2: Method A Layer Splitting (Graphics Layer vs Typography Layer on Pure White)
- Step 3: Exact Organic Contour & Entity Extraction (Zero Rectangles, Character Linework & Fills)
"""
import os
import sys
import cv2
import numpy as np

# Add paths
sys.path.insert(0, r"E:\image_to_animate\kivy")
sys.path.insert(0, r"E:\image_to_animate\experiments\modular_pipeline")

from m1_panel_extractor import DynamicPanelExtractor
from m2_layer_splitter import MethodALayerSplitter
from engine.core.scene import SceneConfig
from engine.core.stroke import Stroke, StrokeType
from engine.core.region import ColorRegion
from engine.processing.edge_extractor import EdgeExtractor
from engine.processing.stroke_classifier import StrokeClassifier
from engine.processing.region_extractor import RegionExtractor
from engine.processing.color_processor import ColorProcessor

MASTER_IMG_PATH = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\.user_uploaded\media_1788292396282.png"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results\all_12_panels_pipeline"
os.makedirs(OUTPUT_DIR, exist_ok=True)

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("="*80)
print("[PIPELINE] RUNNING FULL APPROVED PIPELINE ACROSS ALL 12 PANELS")
print("="*80)

# ----------------- STEP 1: DYNAMIC PANEL DISCOVERY -----------------
master_img = cv2.imread(MASTER_IMG_PATH)
if master_img is None:
    raise FileNotFoundError(f"Cannot load master image: {MASTER_IMG_PATH}")
mh, mw = master_img.shape[:2]

panels = DynamicPanelExtractor.extract_panels(master_img, border_inset=4)
print(f"[STEP 1] Discovered {len(panels)} panels dynamically.")

config = SceneConfig(
    detail_level="HIGH",
    color_palette_size=16,
    show_hand=True,
    drawing_speed=1.0
)

# Colors for distinct organic contours
CONTOUR_PALETTE = [
    (255, 120, 0),   # Cyan/Blue (Primary Character)
    (0, 200, 0),     # Green (Secondary Object / Bubble / Diagram)
    (0, 215, 255),   # Yellow/Gold (Emoji / Mascot)
    (220, 40, 220),  # Magenta (Detail / Accents)
    (0, 0, 255)      # Red (Symbols)
]

all_panel_data = []

# Process each panel through Steps 1, 2, and 3
for p in panels:
    pid = p["id"]
    crop = p["crop"]
    ph, pw = crop.shape[:2]
    
    # ----------------- STEP 2: METHOD A LAYER SPLITTING -----------------
    split_res = MethodALayerSplitter.split(crop)
    gfx_img = split_res["graphics_image"]
    txt_img = split_res["text_image"]
    gfx_mask = split_res["graphics_mask"]
    txt_mask = split_res["text_mask"]
    
    # Save individual layer files
    p_dir = os.path.join(OUTPUT_DIR, f"panel_{pid:02d}")
    os.makedirs(p_dir, exist_ok=True)
    
    cv2.imwrite(os.path.join(p_dir, f"p{pid:02d}_00_crop.png"), crop)
    cv2.imwrite(os.path.join(p_dir, f"p{pid:02d}_01_graphics.png"), gfx_img)
    cv2.imwrite(os.path.join(p_dir, f"p{pid:02d}_02_typography.png"), txt_img)
    
    # ----------------- STEP 3: ORGANIC CONTOUR EXTRACTION & CHARACTER ENGINE -----------------
    diff = 255.0 - gfx_img.astype(np.float32)
    dist = np.max(diff, axis=2)
    gfx_ink = (dist > 26.0).astype(np.uint8) * 255
    
    # Find discrete organic contours for characters/diagrams
    num_cc, lbls, stats, _ = cv2.connectedComponentsWithStats(gfx_ink)
    
    panel_entities = []
    contour_vis = gfx_img.copy()
    
    # Color coding and tracing
    ent_idx = 0
    for i in range(1, num_cc):
        carea = stats[i, cv2.CC_STAT_AREA]
        if carea < 35:
            continue
        comp_mask = (lbls == i).astype(np.uint8) * 255
        cnts, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        c_color = CONTOUR_PALETTE[ent_idx % len(CONTOUR_PALETTE)]
        ent_idx += 1
        
        # Draw smooth organic contour (Zero Rectangles)
        cv2.drawContours(contour_vis, cnts, -1, c_color, 2, cv2.LINE_AA)
        
        panel_entities.append({
            "comp_id": i,
            "mask": comp_mask,
            "contours": cnts,
            "area": carea,
            "color": c_color
        })
        
    cv2.imwrite(os.path.join(p_dir, f"p{pid:02d}_03_organic_contours.png"), contour_vis)
    
    # Character Engine Stroke & Region analysis on Graphics layer
    q_bgr, palette, bg_c = ColorProcessor.quantize(gfx_img, config)
    raw_strokes = EdgeExtractor.extract(gfx_img, config)
    classified_strokes = StrokeClassifier.classify(raw_strokes, gfx_img, q_bgr, config)
    raw_regions = RegionExtractor.extract(q_bgr, palette, bg_c, config)
    color_regions = [r for r in raw_regions if r.color != (255, 255, 255) and r.area > 25]
    
    all_panel_data.append({
        "id": pid,
        "crop": crop,
        "graphics": gfx_img,
        "typography": txt_img,
        "contour_vis": contour_vis,
        "entities_count": len(panel_entities),
        "strokes_count": len(classified_strokes),
        "fills_count": len(color_regions)
    })
    print(f"  [Panel #{pid:02d}] Split OK | {len(panel_entities)} Organic Entities | {len(classified_strokes)} Strokes | {len(color_regions)} Fills")

# ----------------- 4. MASTER ATLAS 1: 12-PANEL SPLIT COMPARISON -----------------
row_h = 135
col_w = 210
matrix_h = len(all_panel_data) * (row_h + 8) + 65
matrix_w = 3 * (col_w + 10) + 15
split_matrix = np.full((matrix_h, matrix_w, 3), 245, dtype=np.uint8)

cv2.rectangle(split_matrix, (0, 0), (matrix_w, 50), (30, 30, 40), -1)
cv2.putText(split_matrix, "ALL 12 PANELS: STEP 1 & 2 SPLIT (ORIGINAL | GRAPHICS | TYPOGRAPHY)", 
            (15, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 220, 255), 2, cv2.LINE_AA)

for r_idx, res in enumerate(all_panel_data):
    pid = res["id"]
    gy = 58 + r_idx * (row_h + 8)
    items = [res["crop"], res["graphics"], res["typography"]]
    headers = [f"P#{pid:02d} Original", f"P#{pid:02d} Graphics Layer", f"P#{pid:02d} Typography Layer"]
    
    for c_idx in range(3):
        gx = 10 + c_idx * (col_w + 10)
        img = items[c_idx]
        sc = min((col_w - 6) / float(img.shape[1]), (row_h - 22) / float(img.shape[0]))
        iw_sc = int(img.shape[1] * sc)
        ih_sc = int(img.shape[0] * sc)
        img_sc = cv2.resize(img, (iw_sc, ih_sc), interpolation=cv2.INTER_AREA)
        
        cv2.rectangle(split_matrix, (gx, gy), (gx+col_w, gy+row_h), (255, 255, 255), -1)
        cv2.rectangle(split_matrix, (gx, gy), (gx+col_w, gy+row_h), (180, 180, 180), 1)
        
        ox = gx + (col_w - iw_sc) // 2
        oy = gy + 20 + (row_h - 22 - ih_sc) // 2
        split_matrix[oy:oy+ih_sc, ox:ox+iw_sc] = img_sc
        
        cv2.rectangle(split_matrix, (gx, gy), (gx+col_w, gy+18), (45, 45, 55), -1)
        cv2.putText(split_matrix, headers[c_idx], (gx + 6, gy + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 255), 1, cv2.LINE_AA)

SPLIT_MATRIX_PATH = os.path.join(OUTPUT_DIR, "master_atlas_01_all_12_panels_split.png")
cv2.imwrite(SPLIT_MATRIX_PATH, split_matrix)
print(f"\n[SUCCESS] Master Split Matrix Saved: {SPLIT_MATRIX_PATH}")

# ----------------- 5. MASTER ATLAS 2: 12-PANEL ORGANIC CONTOURS GALLERY -----------------
card_w, card_h = 320, 210
cols, rows = 4, 3
contours_grid = np.full((rows * (card_h + 35) + 60, cols * (card_w + 15) + 15, 3), 245, dtype=np.uint8)

cv2.rectangle(contours_grid, (0, 0), (contours_grid.shape[1], 50), (30, 30, 40), -1)
cv2.putText(contours_grid, "ALL 12 PANELS: STEP 3 EXACT ORGANIC CONTOURS (ZERO RECTANGLES)", 
            (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 2, cv2.LINE_AA)

for idx, res in enumerate(all_panel_data):
    pid = res["id"]
    c_img = res["contour_vis"]
    
    r = idx // cols
    c = idx % cols
    gx = 15 + c * (card_w + 15)
    gy = 60 + r * (card_h + 35)
    
    cv2.rectangle(contours_grid, (gx, gy), (gx + card_w, gy + card_h), (255, 255, 255), -1)
    cv2.rectangle(contours_grid, (gx, gy), (gx + card_w, gy + card_h), (180, 180, 180), 1)
    
    sc = min((card_w - 10) / float(c_img.shape[1]), (card_h - 25) / float(c_img.shape[0]))
    cw_sc = int(c_img.shape[1] * sc)
    ch_sc = int(c_img.shape[0] * sc)
    c_sc = cv2.resize(c_img, (cw_sc, ch_sc), interpolation=cv2.INTER_AREA)
    
    ox = gx + (card_w - cw_sc) // 2
    oy = gy + 22 + (card_h - 25 - ch_sc) // 2
    contours_grid[oy:oy+ch_sc, ox:ox+cw_sc] = c_sc
    
    cv2.rectangle(contours_grid, (gx, gy), (gx + card_w, gy + 20), (45, 45, 55), -1)
    cv2.putText(contours_grid, f"Panel #{pid:02d} ({res['entities_count']} Entities, {res['strokes_count']} Strokes)", 
                (gx + 8, gy + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 220, 255), 1, cv2.LINE_AA)

CONTOURS_GRID_PATH = os.path.join(OUTPUT_DIR, "master_atlas_02_all_12_panels_organic_contours.png")
cv2.imwrite(CONTOURS_GRID_PATH, contours_grid)
print(f"[SUCCESS] Master Organic Contours Grid Saved: {CONTOURS_GRID_PATH}")
print("="*80 + "\n")

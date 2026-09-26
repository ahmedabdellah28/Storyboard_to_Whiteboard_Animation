"""
Test Step 2: Method A Layer Splitter (Graphics Layer vs Typography Layer)
File: experiments/test_step2_layer_splitter.py

Executes Step 2 exclusively:
1. Receives the clean border-free panel crops from Step 1.
2. Applies Method A Classical Topological Separation.
3. Outputs two pure image layers on pristine white backgrounds:
   - Layer 1: image_graphics (Characters, Mascots, Emojis, Bubbles, Diagrams).
   - Layer 2: image_text (Arabic & English Titles, Paragraphs, Equations, Bullet Points).
4. Generates side-by-side verification galleries for user approval.
"""
import os
import sys
import cv2
import numpy as np

# Ensure modular pipeline is in path
sys.path.insert(0, r"E:\image_to_animate\experiments\modular_pipeline")
from m1_panel_extractor import DynamicPanelExtractor
from m2_layer_splitter import MethodALayerSplitter

MASTER_IMG_PATH = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\.user_uploaded\media_1788292396282.png"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step2_split_layers"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Load Master Image & Extract Panels from Step 1 (exact inset=4 from benchmark)
master_img = cv2.imread(MASTER_IMG_PATH)
panels = DynamicPanelExtractor.extract_panels(master_img, border_inset=4)
print(f"[STEP 2] Loaded {len(panels)} panels from Step 1.")

# 2. Process All Panels with Method A Layer Splitter
split_results = []
for p in panels:
    pid = p["id"]
    crop = p["crop"]
    
    res = MethodALayerSplitter.split(crop)
    gfx_img = res["graphics_image"]
    txt_img = res["text_image"]
    
    # Save individual layer files
    cv2.imwrite(os.path.join(OUTPUT_DIR, f"panel_{pid:02d}_01_graphics.png"), gfx_img)
    cv2.imwrite(os.path.join(OUTPUT_DIR, f"panel_{pid:02d}_02_typography.png"), txt_img)
    
    split_results.append({
        "id": pid,
        "crop": crop,
        "graphics": gfx_img,
        "typography": txt_img
    })
    print(f"  -> Panel #{pid:02d} split into Graphics & Typography layers.")

# 3. Visual Artifact 1: Deep Close-Up Inspection for Panel 1 (Scene 1)
p1 = split_results[0]
p1_crop = p1["crop"]
p1_gfx = p1["graphics"]
p1_txt = p1["typography"]

# Scale up for high-res inspection (width=600px each)
target_w = 600
sc = target_w / float(p1_crop.shape[1])
target_h = int(p1_crop.shape[0] * sc)

c_orig = cv2.resize(p1_crop, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
c_gfx = cv2.resize(p1_gfx, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
c_txt = cv2.resize(p1_txt, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

p1_sheet = np.full((target_h + 80, target_w * 3 + 40, 3), 245, dtype=np.uint8)

# Title Banner
cv2.rectangle(p1_sheet, (0, 0), (p1_sheet.shape[1], 50), (30, 30, 40), -1)
cv2.putText(p1_sheet, "STEP 2 — PANEL 1 METHOD A SPLIT: ORIGINAL | GRAPHICS LAYER | TYPOGRAPHY LAYER", 
            (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (0, 220, 255), 2, cv2.LINE_AA)

col_labels = [
    "Original Panel 1",
    "Layer 1: Pure Graphics (Characters & Emojis)",
    "Layer 2: Pure Typography (Title & Arabic Text)"
]

cards = [c_orig, c_gfx, c_txt]
for idx in range(3):
    gx = 10 + idx * (target_w + 10)
    gy = 60
    p1_sheet[gy:gy+target_h, gx:gx+target_w] = cards[idx]
    cv2.rectangle(p1_sheet, (gx, gy), (gx+target_w, gy+target_h), (120, 120, 120), 2)
    # Header badge
    cv2.rectangle(p1_sheet, (gx, gy), (gx+target_w, gy+24), (45, 45, 55), -1)
    cv2.putText(p1_sheet, col_labels[idx], (gx + 10, gy + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1, cv2.LINE_AA)

P1_SHEET_PATH = os.path.join(OUTPUT_DIR, "step2_panel_01_split_inspection.png")
cv2.imwrite(P1_SHEET_PATH, p1_sheet)
print(f"[STEP 2] Panel 1 inspection sheet saved: {P1_SHEET_PATH}")

# 4. Visual Artifact 2: 12-Panel Complete Master Matrix
# 3 Columns: Original | Graphics | Typography for all 12 panels
row_h = 130
col_w = 200
matrix_h = len(split_results) * (row_h + 8) + 65
matrix_w = 3 * (col_w + 10) + 15
master_matrix = np.full((matrix_h, matrix_w, 3), 245, dtype=np.uint8)

cv2.rectangle(master_matrix, (0, 0), (matrix_w, 50), (30, 30, 40), -1)
cv2.putText(master_matrix, "STEP 2: ALL 12 PANELS SEPARATION MATRIX (METHOD A)", 
            (15, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 220, 255), 2, cv2.LINE_AA)

for r_idx, res in enumerate(split_results):
    pid = res["id"]
    gy = 58 + r_idx * (row_h + 8)
    
    items = [res["crop"], res["graphics"], res["typography"]]
    headers = [f"P#{pid:02d} Original", f"P#{pid:02d} Graphics", f"P#{pid:02d} Text"]
    
    for c_idx in range(3):
        gx = 10 + c_idx * (col_w + 10)
        img = items[c_idx]
        
        sc_m = min((col_w - 6) / float(img.shape[1]), (row_h - 22) / float(img.shape[0]))
        iw_sc = int(img.shape[1] * sc_m)
        ih_sc = int(img.shape[0] * sc_m)
        img_sc = cv2.resize(img, (iw_sc, ih_sc), interpolation=cv2.INTER_AREA)
        
        cv2.rectangle(master_matrix, (gx, gy), (gx+col_w, gy+row_h), (255, 255, 255), -1)
        cv2.rectangle(master_matrix, (gx, gy), (gx+col_w, gy+row_h), (180, 180, 180), 1)
        
        ox = gx + (col_w - iw_sc) // 2
        oy = gy + 20 + (row_h - 22 - ih_sc) // 2
        master_matrix[oy:oy+ih_sc, ox:ox+iw_sc] = img_sc
        
        cv2.rectangle(master_matrix, (gx, gy), (gx+col_w, gy+18), (45, 45, 55), -1)
        cv2.putText(master_matrix, headers[c_idx], (gx + 6, gy + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 255), 1, cv2.LINE_AA)

MATRIX_PATH = os.path.join(OUTPUT_DIR, "step2_all_12_panels_matrix.png")
cv2.imwrite(MATRIX_PATH, master_matrix)
print(f"[STEP 2] All 12 panels matrix saved: {MATRIX_PATH}")

"""
Test Step 3: Exact Organic Contour Silhouette Extraction (Zero Rectangles)
File: experiments/test_step3_exact_contour_silhouette.py

Implements Exact Organic Boundary Extraction:
1. Traces the true curved perimeter silhouette of each entity (NO rectangular bounding boxes).
2. Extracts each character/object strictly within its exact anatomical contour mask.
3. Decouples touching elements (Boy Character, Cloud Bubble, Emoji Mascot) into clean organic contours.
4. Generates high-definition contour maps and isolated silhouette galleries for user inspection.
"""
import os
import sys
import cv2
import numpy as np

# Paths
INPUT_GRAPHICS_PATH = r"E:\image_to_animate\experiments\results\step2_split_layers\panel_01_01_graphics.png"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step3_character_engine"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Load Graphics Image
gfx_img = cv2.imread(INPUT_GRAPHICS_PATH)
if gfx_img is None:
    raise FileNotFoundError(f"Cannot load graphics image: {INPUT_GRAPHICS_PATH}")
gh, gw = gfx_img.shape[:2]
print(f"[STEP 3] Loaded Graphics Image: {gw}x{gh}px")

# 2. Ink & Color Seeds for Organic Entity Isolation
diff = 255.0 - gfx_img.astype(np.float32)
dist = np.max(diff, axis=2)
ink_mask = (dist > 26.0).astype(np.uint8) * 255

hsv = cv2.cvtColor(gfx_img, cv2.COLOR_BGR2HSV)
sat = hsv[:, :, 1]
val = hsv[:, :, 2]
hue = hsv[:, :, 0]

# A. Emoji Organic Contour (Yellow Smiley)
emoji_seed = ((sat > 70) & (val > 70) & (hue >= 15) & (hue <= 42)).astype(np.uint8) * 255
num_em, lbl_em, st_em, _ = cv2.connectedComponentsWithStats(emoji_seed)
emoji_mask = np.zeros((gh, gw), dtype=np.uint8)
for i in range(1, num_em):
    ew = st_em[i, cv2.CC_STAT_WIDTH]
    eh = st_em[i, cv2.CC_STAT_HEIGHT]
    if 15 <= ew <= 55 and 15 <= eh <= 55 and st_em[i, cv2.CC_STAT_AREA] >= 60:
        comp_m = (lbl_em == i).astype(np.uint8) * 255
        dil = cv2.dilate(comp_m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        emoji_mask = cv2.bitwise_or(emoji_mask, cv2.bitwise_and(ink_mask, dil))

# B. Boy Character Organic Contour (Skin + Blue Hoodie + Hair)
# The boy character is strictly on the left (x <= 76)
skin_seed = (hue >= 5) & (hue <= 25) & (sat >= 20) & (sat <= 85) & (val >= 160) & (np.arange(gw)[np.newaxis, :] <= 76)
hoodie_seed = (hue >= 95) & (hue <= 135) & (sat >= 50) & (val >= 60) & (np.arange(gw)[np.newaxis, :] <= 76)
hair_seed = (val <= 90) & (np.arange(gw)[np.newaxis, :] <= 76) & (np.arange(gh)[:, np.newaxis] < gh * 0.65)

boy_seeds = (skin_seed | hoodie_seed | hair_seed).astype(np.uint8) * 255
# Grow seed only across pixels on the boy's side (x <= 76)
boy_grown = cv2.dilate(boy_seeds, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
boy_mask_raw = cv2.bitwise_and(ink_mask, boy_grown)
boy_mask_raw[:, 77:] = 0

num_b, lbl_b, st_b, _ = cv2.connectedComponentsWithStats(boy_mask_raw)
boy_mask = np.zeros((gh, gw), dtype=np.uint8)
for i in range(1, num_b):
    if st_b[i, cv2.CC_STAT_AREA] > 40:
        boy_mask[lbl_b == i] = 255

# C. Speech Bubble Organic Contour (Cloud Perimeter)
bubble_mask_raw = ink_mask.copy()
bubble_mask_raw[boy_mask > 0] = 0
bubble_mask_raw[emoji_mask > 0] = 0
num_bub, lbl_bub, st_bub, _ = cv2.connectedComponentsWithStats(bubble_mask_raw)
bubble_mask = np.zeros((gh, gw), dtype=np.uint8)
for i in range(1, num_bub):
    if st_bub[i, cv2.CC_STAT_AREA] > 80:
        bubble_mask[lbl_bub == i] = 255

# ----------------- 3. EXTRACT EXACT ORGANIC CONTOURS & ALPHA SILHOUETTES -----------------
entities = [
    {"name": "1. Boy Character Silhouette", "mask": boy_mask, "color": (255, 120, 0)}, # Cyan/Blue
    {"name": "2. Speech Bubble Cloud Contour", "mask": bubble_mask, "color": (0, 200, 0)}, # Green
    {"name": "3. Emoji Mascot Circular Contour", "mask": emoji_mask, "color": (0, 215, 255)} # Yellow
]

# Master Image with EXACT organic contour lines (ZERO RECTANGLES)
organic_contour_map = gfx_img.copy()

for ent in entities:
    m = ent["mask"]
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    ent["contours"] = cnts
    
    # Draw exact smooth organic contour curve around entity
    cv2.drawContours(organic_contour_map, cnts, -1, ent["color"], 2, cv2.LINE_AA)
    
    # Calculate centroid for floating badge
    M_mom = cv2.moments(m)
    if M_mom["m00"] > 0:
        cx = int(M_mom["m10"] / M_mom["m00"])
        cy = int(M_mom["m01"] / M_mom["m00"])
        cv2.circle(organic_contour_map, (cx, cy), 4, (0, 0, 0), -1)
        cv2.circle(organic_contour_map, (cx, cy), 3, ent["color"], -1)

ORGANIC_MAP_PATH = os.path.join(OUTPUT_DIR, "step3_exact_organic_contour_map.png")
cv2.imwrite(ORGANIC_MAP_PATH, organic_contour_map)
print(f"[STEP 3] Saved Exact Organic Contour Map (No Rectangles): {ORGANIC_MAP_PATH}")

# ----------------- 4. VISUAL ARTIFACT: ISOLATED ORGANIC SILHOUETTES GALLERY -----------------
card_w, card_h = 400, 300
cols = 3
atlas_w = cols * (card_w + 15) + 15
atlas_h = card_h + 80
atlas = np.full((atlas_h, atlas_w, 3), 245, dtype=np.uint8)

cv2.rectangle(atlas, (0, 0), (atlas_w, 50), (30, 30, 40), -1)
cv2.putText(atlas, "STEP 3: EXACT ORGANIC SILHOUETTE ISOLATION (ZERO RECTANGLES — TRUE ANATOMICAL BOUNDARIES)", 
            (20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 220, 255), 2, cv2.LINE_AA)

for idx, ent in enumerate(entities):
    gx = 15 + idx * (card_w + 15)
    gy = 60
    
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + card_h), (255, 255, 255), -1)
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + card_h), (200, 200, 200), 1)
    
    # Create isolated image containing ONLY this exact entity mask on pure white
    m = ent["mask"]
    ent_isolated = np.full_like(gfx_img, 255)
    ent_isolated[m > 0] = gfx_img[m > 0]
    
    # Draw its exact outer contour on the card
    cv2.drawContours(ent_isolated, ent["contours"], -1, ent["color"], 2, cv2.LINE_AA)
    
    # Fit into card nicely
    sc = min((card_w - 20) / float(gw), (card_h - 60) / float(gh))
    cw_sc = int(gw * sc)
    ch_sc = int(gh * sc)
    resized_iso = cv2.resize(ent_isolated, (cw_sc, ch_sc), interpolation=cv2.INTER_AREA)
    
    ox = gx + (card_w - cw_sc) // 2
    oy = gy + 26 + (card_h - 60 - ch_sc) // 2
    atlas[oy:oy+ch_sc, ox:ox+cw_sc] = resized_iso
    
    # Header badge
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + 24), (45, 45, 55), -1)
    cv2.putText(atlas, ent["name"], (gx + 8, gy + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, ent["color"], 1, cv2.LINE_AA)

ATLAS_PATH = os.path.join(OUTPUT_DIR, "step3_exact_isolated_silhouettes_atlas.png")
cv2.imwrite(ATLAS_PATH, atlas)
print(f"[STEP 3] Saved Exact Isolated Silhouettes Atlas: {ATLAS_PATH}")

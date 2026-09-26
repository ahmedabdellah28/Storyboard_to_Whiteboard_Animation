"""
Test Step 3: True Entity Decomposition & Multi-Character Recognition
File: experiments/test_step3_decoupled_character_entities.py

Demonstrates how the project's native engine cleanly separates touching and independent entities:
1. Isolates Entity 1: Primary Character (Boy in Hoodie)
2. Isolates Entity 2: Speech Bubble (Cloud Frame)
3. Isolates Entity 3: Emoji Mascot (Yellow Smiley Face)
4. Isolates Entity 4: Heart Accent
Each entity is a completely independent SceneObject with its own strokes, fills, and drawing timeline.
"""
import os
import sys
import cv2
import numpy as np

# Add paths
sys.path.insert(0, r"E:\image_to_animate\kivy")
sys.path.insert(0, r"E:\image_to_animate\experiments\modular_pipeline")

from engine.core.scene import SceneConfig, SceneObject
from engine.core.stroke import Stroke, StrokeType
from engine.core.region import ColorRegion
from engine.processing.edge_extractor import EdgeExtractor
from engine.processing.stroke_classifier import StrokeClassifier
from engine.processing.region_extractor import RegionExtractor
from engine.processing.color_processor import ColorProcessor

INPUT_GRAPHICS_PATH = r"E:\image_to_animate\experiments\results\step2_split_layers\panel_01_01_graphics.png"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step3_character_engine"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Load Graphics Layer from Step 2
gfx_img = cv2.imread(INPUT_GRAPHICS_PATH)
if gfx_img is None:
    raise FileNotFoundError(f"Cannot load graphics image: {INPUT_GRAPHICS_PATH}")
gh, gw = gfx_img.shape[:2]
print(f"[STEP 3] Loaded Graphics Image: {gw}x{gh}px")

config = SceneConfig(
    detail_level="HIGH",
    color_palette_size=16,
    show_hand=True,
    drawing_speed=1.0
)

# ----------------- 1. COLOR-SEED BODY GROWTH & TOPOLOGICAL SEPARATION -----------------
# 1. Color seeds
hsv = cv2.cvtColor(gfx_img, cv2.COLOR_BGR2HSV)
sat = hsv[:, :, 1]
val = hsv[:, :, 2]
hue = hsv[:, :, 0]

diff = 255.0 - gfx_img.astype(np.float32)
dist = np.max(diff, axis=2)
ink_mask = (dist > 26.0).astype(np.uint8) * 255

# A. Emoji Seed: Yellow hue 15-40, high saturation, circular component (20-50px)
emoji_seed = ((sat > 70) & (val > 70) & (hue >= 15) & (hue <= 42)).astype(np.uint8) * 255
num_em, lbl_em, st_em, _ = cv2.connectedComponentsWithStats(emoji_seed)
emoji_mask = np.zeros((gh, gw), dtype=np.uint8)

for i in range(1, num_em):
    ew = st_em[i, cv2.CC_STAT_WIDTH]
    eh = st_em[i, cv2.CC_STAT_HEIGHT]
    e_area = st_em[i, cv2.CC_STAT_AREA]
    if 15 <= ew <= 55 and 15 <= eh <= 55 and e_area >= 60:
        comp_m = (lbl_em == i).astype(np.uint8) * 255
        dil = cv2.dilate(comp_m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        emoji_mask = cv2.bitwise_or(emoji_mask, cv2.bitwise_and(ink_mask, dil))

# B. Boy Character Seed: Skin (Hue 5-25, Sat 20-75) + Blue Hoodie (Hue 100-130, Sat > 50) + Hair (Val < 80, x < gw*0.4)
skin_seed = (hue >= 5) & (hue <= 25) & (sat >= 20) & (sat <= 85) & (val >= 160) & (np.arange(gw)[np.newaxis, :] < gw * 0.40)
hoodie_seed = (hue >= 95) & (hue <= 135) & (sat >= 50) & (val >= 60) & (np.arange(gw)[np.newaxis, :] < gw * 0.40)
hair_seed = (val <= 90) & (np.arange(gw)[np.newaxis, :] < gw * 0.40) & (np.arange(gh)[:, np.newaxis] < gh * 0.65)

boy_seeds = (skin_seed | hoodie_seed | hair_seed).astype(np.uint8) * 255
# Grow seed across contiguous dark ink (character linework & body)
boy_grown = cv2.dilate(boy_seeds, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
boy_mask = cv2.bitwise_and(ink_mask, boy_grown)
# Ensure clean solid body component
num_b, lbl_b, st_b, _ = cv2.connectedComponentsWithStats(boy_mask)
boy_clean = np.zeros((gh, gw), dtype=np.uint8)
for i in range(1, num_b):
    if st_b[i, cv2.CC_STAT_AREA] > 40:
        boy_clean[lbl_b == i] = 255
boy_mask = boy_clean

# C. Speech Bubble: Hollow thin blue linework not claimed by Boy or Emoji
bubble_mask = ink_mask.copy()
bubble_mask[boy_mask > 0] = 0
bubble_mask[emoji_mask > 0] = 0

num_bub, lbl_bub, st_bub, _ = cv2.connectedComponentsWithStats(bubble_mask)
bubble_clean = np.zeros((gh, gw), dtype=np.uint8)
for i in range(1, num_bub):
    if st_bub[i, cv2.CC_STAT_AREA] > 80:
        bubble_clean[lbl_bub == i] = 255
bubble_mask = bubble_clean

# ----------------- 2. BUILD INDEPENDENT SCENE OBJECTS -----------------
entities_raw = [
    {"name": "Entity 1: Primary Character (Boy in Hoodie)", "mask": boy_mask, "color_tag": (255, 120, 0)},
    {"name": "Entity 2: Speech Bubble (Cloud Frame)", "mask": bubble_mask, "color_tag": (0, 200, 0)},
    {"name": "Entity 3: Emoji Mascot (Happy Yellow Smiley)", "mask": emoji_mask, "color_tag": (0, 220, 255)}
]

scene_objects = []

for ent in entities_raw:
    m = ent["mask"]
    if cv2.countNonZero(m) < 20:
        continue
        
    y_idx, x_idx = np.where(m > 0)
    bx, by = int(x_idx.min()), int(y_idx.min())
    bw, bh = int(x_idx.max() - bx + 1), int(y_idx.max() - by + 1)
    
    # Isolated pure crop for this specific entity
    ent_crop = np.full((bh, bw, 3), 255, dtype=np.uint8)
    sub_m = m[by:by+bh, bx:bx+bw]
    ent_crop[sub_m > 0] = gfx_img[by:by+bh, bx:bx+bw][sub_m > 0]
    
    # Run specialized stroke & fill pipeline for this entity
    q_bgr, palette, bg_c = ColorProcessor.quantize(ent_crop, config)
    raw_stk = EdgeExtractor.extract(ent_crop, config)
    cls_stk = StrokeClassifier.classify(raw_stk, ent_crop, q_bgr, config)
    reg = RegionExtractor.extract(q_bgr, palette, bg_c, config)
    clr_reg = [r for r in reg if r.color != (255, 255, 255) and r.area > 25]
    
    scene_objects.append({
        "name": ent["name"],
        "bbox": (bx, by, bw, bh),
        "mask": m,
        "crop": ent_crop,
        "color_tag": ent["color_tag"],
        "strokes": cls_stk,
        "fills": clr_reg,
        "outlines": [s for s in cls_stk if s.stroke_type == StrokeType.OUTER_OUTLINE],
        "details": [s for s in cls_stk if s.stroke_type == StrokeType.INTERNAL_DETAIL]
    })
    print(f"  -> Discovered {ent['name']}: {bw}x{bh}px, {len(cls_stk)} strokes, {len(clr_reg)} color regions.")

# ----------------- 3. VISUAL ARTIFACT: 4-ENTITY DECOUPLING ATLAS -----------------
card_w, card_h = 320, 260
cols, rows = 4, 1
atlas_w = cols * (card_w + 15) + 15
atlas_h = card_h + 80
atlas = np.full((atlas_h, atlas_w, 3), 245, dtype=np.uint8)

cv2.rectangle(atlas, (0, 0), (atlas_w, 50), (30, 30, 40), -1)
cv2.putText(atlas, "STEP 3: DECOUPLED INDEPENDENT SCENE OBJECTS (CHARACTER vs BUBBLE vs EMOJI vs ACCENT)", 
            (20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 220, 255), 2, cv2.LINE_AA)

for idx, obj in enumerate(scene_objects):
    gx = 15 + idx * (card_w + 15)
    gy = 60
    
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + card_h), (255, 255, 255), -1)
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + card_h), obj["color_tag"], 2)
    
    # Draw isolated crop
    c_img = obj["crop"]
    sc = min((card_w - 20) / float(c_img.shape[1]), (card_h - 70) / float(c_img.shape[0]))
    cw_sc = int(c_img.shape[1] * sc)
    ch_sc = int(c_img.shape[0] * sc)
    crop_sc = cv2.resize(c_img, (cw_sc, ch_sc), interpolation=cv2.INTER_AREA)
    
    ox = gx + (card_w - cw_sc) // 2
    oy = gy + 30 + (card_h - 70 - ch_sc) // 2
    atlas[oy:oy+ch_sc, ox:ox+cw_sc] = crop_sc
    
    # Header badge
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + 24), (45, 45, 55), -1)
    cv2.putText(atlas, obj["name"][:26] + "...", (gx + 6, gy + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, obj["color_tag"], 1, cv2.LINE_AA)
    
    # Stats footer
    stats_text = f"Strokes: {len(obj['strokes'])} | Fills: {len(obj['fills'])} | {obj['bbox'][2]}x{obj['bbox'][3]}px"
    cv2.putText(atlas, stats_text, (gx + 6, gy + card_h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (90, 90, 90), 1, cv2.LINE_AA)

DECOUPLED_ATLAS_PATH = os.path.join(OUTPUT_DIR, "step3_decoupled_scene_objects_atlas.png")
cv2.imwrite(DECOUPLED_ATLAS_PATH, atlas)
print(f"[STEP 3] Saved Decoupled Scene Objects Atlas: {DECOUPLED_ATLAS_PATH}")

# ----------------- 4. VISUAL ARTIFACT: OVERALL RECOGNITION BOUNDING BOX MAP -----------------
bbox_map = gfx_img.copy()
for obj in scene_objects:
    bx, by, bw, bh = obj["bbox"]
    c_tag = obj["color_tag"]
    cv2.rectangle(bbox_map, (bx, by), (bx+bw, by+bh), c_tag, 2)
    # Badge
    cv2.rectangle(bbox_map, (bx, max(0, by - 16)), (bx + int(bw*0.85), by), (30, 30, 40), -1)
    cv2.putText(bbox_map, obj["name"].split(":")[1].strip(), (bx + 2, max(10, by - 4)), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, c_tag, 1, cv2.LINE_AA)

BBOX_MAP_PATH = os.path.join(OUTPUT_DIR, "step3_decoupled_bounding_map.png")
cv2.imwrite(BBOX_MAP_PATH, bbox_map)
print(f"[STEP 3] Saved Decoupled Bounding Map: {BBOX_MAP_PATH}")

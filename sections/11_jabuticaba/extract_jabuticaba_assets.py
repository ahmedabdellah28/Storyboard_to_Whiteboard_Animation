import os
import sys
import json
import cv2
import numpy as np

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

sb_path = os.path.join(ROOT_DIR, "sections/11_jabuticaba/storyboard.png")
data = np.fromfile(sb_path, dtype=np.uint8)
img = cv2.imdecode(data, cv2.IMREAD_COLOR)
h, w = img.shape[:2]

assets_dir = os.path.join(ROOT_DIR, "sections/11_jabuticaba/assets")
scratch_dir = os.path.join(ROOT_DIR, "sections/11_jabuticaba/scratch")
os.makedirs(assets_dir, exist_ok=True)
os.makedirs(scratch_dir, exist_ok=True)

# Precise Non-Overlapping Bounding Boxes
crops = {
    # Row 1: Cauliflory & Trunk Blooming
    "r1_01_jabuticaba_hero_cluster": (0, 0, 385, 325),
    "r1_02_jabuticaba_tree_full": (385, 10, 745, 325),
    "r1_03_trunk_covered_fruits": (745, 0, 990, 335),
    "r1_04_trunk_berries_macro": (990, 0, 1290, 335),
    "r1_05_trunk_white_flowers_macro": (1290, 0, 1536, 335),

    # Row 2: Taste, Popping Sensation & Texture
    "r2_01_jabuticaba_trio_cut": (0, 340, 320, 550),
    "r2_02_traditional_grapes_comparison": (320, 330, 560, 570),
    "r2_03_popping_juice_burst_sequence": (560, 365, 980, 535),
    "r2_04_slices_cross_sections": (980, 350, 1310, 545),
    "r2_05_hand_holding_single_berry": (1310, 340, 1536, 550),

    # Row 3: Ripening, Rapid Spoilage & Export Barrier
    "r3_01_branch_ripening_gradient": (0, 560, 360, 765),
    "r3_02_spoilage_sequence_decay": (360, 605, 760, 735),
    "r3_03_calendar_rapid_spoilage_3days": (760, 550, 980, 735),
    "r3_04_export_crates_airplane_prohibited": (980, 560, 1300, 735),
    "r3_05_brazil_map_native_origin": (1300, 570, 1536, 765),

    # Row 4: Slow Growth Stages, Bountiful Harvest & Fresh Juice
    "r4_01_growth_sprout_stage": (5, 840, 130, 960),
    "r4_02_growth_sapling_stage": (130, 810, 255, 960),
    "r4_03_growth_bushy_juvenile_stage": (255, 790, 395, 960),
    "r4_04_growth_mature_tree_stage": (395, 765, 565, 960),
    "r4_05_growth_fruiting_tree_stage": (565, 755, 855, 960),
    "r4_06_basket_harvest_platter": (855, 745, 1240, 980),
    "r4_07_fresh_juice_tall_glass": (1240, 775, 1536, 975),
}

def clean_and_extract_rgba(crop_bgr, white_threshold=245, feather_radius=1):
    ch, cw = crop_bgr.shape[:2]
    
    min_chan = np.min(crop_bgr, axis=2)
    max_chan = np.max(crop_bgr, axis=2)
    is_white = (min_chan >= white_threshold) & ((max_chan - min_chan) < 18)
    
    mask = np.zeros((ch + 2, cw + 2), dtype=np.uint8)
    bg_mask = np.zeros((ch, cw), dtype=np.uint8)
    
    seeds = []
    for x in range(cw):
        if is_white[0, x]: seeds.append((x, 0))
        if is_white[ch - 1, x]: seeds.append((x, ch - 1))
    for y in range(ch):
        if is_white[y, 0]: seeds.append((0, y))
        if is_white[y, cw - 1]: seeds.append((cw - 1, y))
        
    for sx, sy in seeds:
        if bg_mask[sy, sx] == 0 and is_white[sy, sx]:
            cv2.floodFill(crop_bgr.copy(), mask, (sx, sy), 0, 
                          flags=cv2.FLOODFILL_MASK_ONLY | (4 << 8))
            bg_mask |= mask[1:ch+1, 1:cw+1]
            
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    bg_mask = cv2.dilate(bg_mask, kernel, iterations=1)
    bg_mask = (bg_mask > 0) & (min_chan >= (white_threshold - 10))
    
    alpha = np.where(bg_mask, 0, 255).astype(np.uint8)
    
    if feather_radius > 0:
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
        
    rgba = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = alpha
    
    coords = cv2.findNonZero((alpha > 10).astype(np.uint8))
    if coords is not None:
        bx, by, bw, bh = cv2.boundingRect(coords)
        pad = 4
        x1 = max(0, bx - pad)
        y1 = max(0, by - pad)
        x2 = min(cw, bx + bw + pad)
        y2 = min(ch, by + bh + pad)
        rgba = rgba[y1:y2, x1:x2]
        
    return rgba

metadata = {}
extracted_list = []

print("Extracting 22 Jabuticaba assets with refined coordinates...")
for name, (x1, y1, x2, y2) in crops.items():
    crop = img[y1:y2, x1:x2]
    w_thresh = 248 if ("trunk" in name or "flower" in name or "branch" in name) else 244
    rgba = clean_and_extract_rgba(crop, white_threshold=w_thresh)
    
    out_path = os.path.join(assets_dir, f"{name}.png")
    ext = os.path.splitext(out_path)[1]
    ok, buf = cv2.imencode(ext, rgba)
    if ok:
        buf.tofile(out_path)
        
    ah, aw = rgba.shape[:2]
    metadata[name] = {
        "file": f"{name}.png",
        "width": aw,
        "height": ah,
        "aspect_ratio": round(aw / float(ah), 3)
    }
    extracted_list.append((name, rgba))
    print(f"  Extracted: {name:40s} -> {aw}x{ah}")

meta_path = os.path.join(assets_dir, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)
print(f"\nMetadata written to {meta_path}")

# Build visual catalog
cat_cols = 5
cat_w = 1920
cat_h = 1080
catalog = np.full((cat_h, cat_w, 3), 245, dtype=np.uint8)

cell_w = cat_w // cat_cols
cell_h = cat_h // 5

for idx, (name, rgba) in enumerate(extracted_list):
    r = idx // cat_cols
    c = idx % cat_cols
    if r >= 5: break
    
    cx = c * cell_w + cell_w // 2
    cy = r * cell_h + cell_h // 2
    
    ah, aw = rgba.shape[:2]
    scale = min((cell_w - 20) / float(aw), (cell_h - 35) / float(ah))
    nw = int(aw * scale)
    nh = int(ah * scale)
    resized = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_AREA)
    
    x_off = cx - nw // 2
    y_off = cy - nh // 2 - 8
    
    rgb_part = resized[:, :, :3]
    a_part = resized[:, :, 3] / 255.0
    
    for ch_i in range(3):
        catalog[y_off:y_off+nh, x_off:x_off+nw, ch_i] = (
            rgb_part[:, :, ch_i] * a_part +
            catalog[y_off:y_off+nh, x_off:x_off+nw, ch_i] * (1.0 - a_part)
        ).astype(np.uint8)
        
    short_label = name.replace("jabuticaba_", "").replace("growth_", "")
    cv2.putText(catalog, short_label, (c * cell_w + 10, (r + 1) * cell_h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (50, 50, 50), 1, cv2.LINE_AA)

cat_out = os.path.join(scratch_dir, "clean_assets_catalog.png")
ok, buf = cv2.imencode(".png", catalog)
if ok:
    buf.tofile(cat_out)
print(f"Catalog image saved to {cat_out}")

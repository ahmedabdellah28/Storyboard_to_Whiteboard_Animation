import os
import sys
import json
import cv2
import numpy as np

# Safe console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("=====================================================================================")
print("  💎 ZERO-BOX CONNECTED-COMPONENTS EXTRACTION — SECTION 05: POMEGRANATE 💎")
print("=====================================================================================")

storyboard_path = "sections/05_pomegranate/storyboard.png"
out_dir = "sections/05_pomegranate/assets"
scratch_dir = "sections/05_pomegranate/scratch"
os.makedirs(out_dir, exist_ok=True)
os.makedirs(scratch_dir, exist_ok=True)

img = cv2.imread(storyboard_path)
if img is None:
    raise FileNotFoundError(f"Storyboard not found: {storyboard_path}")

H, W = img.shape[:2]
print(f"Loaded storyboard: {W}x{H}")

# 1. White background detection
is_bg = (img[:, :, 0] > 240) & (img[:, :, 1] > 240) & (img[:, :, 2] > 240)
fg = (~is_bg).astype(np.uint8) * 255

# Morphological closing to seal internal drawing gaps
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_closed = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)

# 2. Connected Components
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_closed, connectivity=8)
print(f"Detected {num_labels} connected components in storyboard.")

# 3. Component mapping for all 18 Pomegranate assets
asset_specs = [
    # Row 1
    {"id": "r1_01_hero_pomegranate", "cids": [2], "desc": "Hero ripe pomegranate whole and halved with ruby seeds"},
    {"id": "r1_02_ancient_ruins_tree", "cids": [3], "desc": "Pomegranate tree with ancient Persepolis relief carving and mountain"},
    {"id": "r1_03_ancient_map_iran_afghanistan", "cids": [4], "desc": "Ancient scroll map showing Iran and Afghanistan region"},
    {"id": "r1_04_pomegranate_sprout_growing", "cids": [5, 6, 7, 8], "desc": "Seeds sprouting from soil into growing seedling"},
    {"id": "r1_05_mature_fruitful_tree", "cids": [1], "desc": "Full-grown fruitful pomegranate tree loaded with red fruits"},

    # Row 2
    {"id": "r2_01_persian_king", "cids": [13], "desc": "Ancient Persian king in royal robes holding a pomegranate"},
    {"id": "r2_02_greek_and_roman_figures", "cids": [14], "desc": "Greek philosopher with Parthenon and Roman general with Colosseum"},
    {"id": "r2_03_fertility_pregnant_silhouette", "cids": [10], "desc": "Golden silhouette of pregnant mother (Fertility)"},
    {"id": "r2_04_prosperity_tree_sunburst", "cids": [11], "desc": "Radiant glowing tree of life (Prosperity)"},
    {"id": "r2_05_resurrection_stairway_heaven", "cids": [12], "desc": "Pomegranate with golden stairway to celestial sky (Resurrection)"},
    {"id": "r2_06_unity_hands_pomegranate", "cids": [9], "desc": "Diverse hands holding segments of one pomegranate (Unity)"},

    # Row 3
    {"id": "r3_01_torah_scroll_star_and_seed_zoom", "cids": [18], "desc": "Ancient Torah scroll with Star of David and magnifying lens on seed"},
    {"id": "r3_02_pomegranate_cross_section_seed_zoom", "cids": [17], "desc": "Cross section of pomegranate with magnifying lens on 613 seeds"},
    {"id": "r3_03_antioxidant_shield_molecules", "cids": [20], "desc": "Pomegranate with molecular lattice network and red protective shield"},
    {"id": "r3_04_cardiovascular_heart_ecg", "cids": [19], "desc": "Anatomical heart with glowing ECG pulse line and pomegranate leaves"},

    # Row 4
    {"id": "r4_01_pomegranate_juice_glass", "cids": [22], "desc": "Glass of ruby pomegranate juice with halved fruit"},
    {"id": "r4_02_salad_bowl_walnuts", "cids": [23], "desc": "Bowl of pomegranate arils with walnuts and green leaves"},
    {"id": "r4_03_botanical_blossoms_branch", "cids": [21], "desc": "Lush botanical branch with pomegranate blossoms and fruit"},
]

metadata = {}
extracted_assets = []

for spec in asset_specs:
    aid = spec["id"]
    cids = spec["cids"]
    desc = spec["desc"]

    # Union of all specified component IDs
    mask = np.isin(labels, cids).astype(np.uint8) * 255

    # Refine mask: remove pure white background pixels within bounding box
    bg_inside = (img[:, :, 0] > 244) & (img[:, :, 1] > 244) & (img[:, :, 2] > 244)
    mask[bg_inside] = 0

    # Smooth edges with slight feathering for anti-aliasing
    mask_blur = cv2.GaussianBlur(mask, (3, 3), 0.5)
    alpha = np.clip(mask_blur.astype(np.float32) / 255.0 * 255.0, 0, 255).astype(np.uint8)

    # Find tight bounding box of non-zero alpha
    coords = cv2.findNonZero(alpha)
    if coords is None:
        print(f"⚠️ Warning: No pixels found for {aid}!")
        continue

    bx, by, bw, bh = cv2.boundingRect(coords)

    # Slice tight box
    crop_bgr = img[by:by+bh, bx:bx+bw]
    crop_alpha = alpha[by:by+bh, bx:bx+bw]

    # Combine into BGRA
    rgba = cv2.merge([crop_bgr[:, :, 0], crop_bgr[:, :, 1], crop_bgr[:, :, 2], crop_alpha])

    out_file = os.path.join(out_dir, f"{aid}.png")
    cv2.imwrite(out_file, rgba)

    meta = {
        "aid": aid,
        "desc": desc,
        "storyboard_box": [int(bx), int(by), int(bw), int(bh)],
        "width": int(bw),
        "height": int(bh),
        "cids": cids
    }
    metadata[aid] = meta
    extracted_assets.append((aid, rgba, meta))
    print(f"Extracted: {aid:42s} | Size: {bw:4d}x{bh:4d} | Storyboard Box: ({bx}, {by}, {bw}, {bh})")

# Save metadata JSON
meta_path = os.path.join(out_dir, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)
print(f"\nMetadata saved to {meta_path} (Total assets: {len(metadata)})")

# 4. Generate Visual Catalog Grid
cat_cols = 4
cat_rows = (len(extracted_assets) + cat_cols - 1) // cat_cols
cell_w, cell_h = 420, 320
catalog = np.full((cat_rows * cell_h, cat_cols * cell_w, 3), 250, dtype=np.uint8)

for idx, (aid, asset_rgba, meta) in enumerate(extracted_assets):
    row = idx // cat_cols
    col = idx % cat_cols
    cx0 = col * cell_w
    cy0 = row * cell_h

    # Draw cell border
    cv2.rectangle(catalog, (cx0, cy0), (cx0 + cell_w - 1, cy0 + cell_h - 1), (220, 220, 220), 1)

    # Fit asset inside cell
    ah, aw = asset_rgba.shape[:2]
    scale = min((cell_w - 40) / float(aw), (cell_h - 60) / float(ah))
    nw, nh = int(aw * scale), int(ah * scale)
    scaled_asset = cv2.resize(asset_rgba, (nw, nh), interpolation=cv2.INTER_AREA)

    off_x = cx0 + (cell_w - nw) // 2
    off_y = cy0 + 10 + (cell_h - 60 - nh) // 2

    # Alpha composite onto catalog
    alp = scaled_asset[:, :, 3].astype(np.float32) / 255.0
    for c in range(3):
        catalog[off_y:off_y+nh, off_x:off_x+nw, c] = (
            scaled_asset[:, :, c].astype(np.float32) * alp +
            catalog[off_y:off_y+nh, off_x:off_x+nw, c].astype(np.float32) * (1.0 - alp)
        ).astype(np.uint8)

    # Asset label
    cv2.putText(catalog, aid, (cx0 + 10, cy0 + cell_h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1, cv2.LINE_AA)

cat_path = os.path.join(scratch_dir, "clean_pomegranate_catalog.png")
cv2.imwrite(cat_path, catalog)
print(f"Generated Visual Catalog: {cat_path}")
print("\n🎉 ZERO-BOX EXTRACTION COMPLETED WITH 100% ORGANIC SILHOUETTES!")

import os
import cv2
import numpy as np

# Load user's pristine new image with clear spacing
img_path = "project_content/images/ChatGPT Image Sep 18, 2026, 11_33_57 PM.png"
img = cv2.imread(img_path)
if img is None:
    raise FileNotFoundError(f"Cannot load {img_path}")

h, w = img.shape[:2]
diff_white = 255.0 - img.astype(np.float32)
dist_white = np.max(diff_white, axis=2)

# Pristine foreground mask
fg_mask = (dist_white > 12).astype(np.uint8)

# Smooth studio alpha calculation for anti-aliasing
alpha_channel = np.clip((dist_white - 2.0) / 10.0 * 255.0, 0, 255).astype(np.uint8)
rgba_img = np.dstack([img, alpha_channel])

# Connected components directly from pure white background
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_mask)
print(f"Total components in new image: {num_labels}")

out_dir = "experiments/exact_contour_assets"
os.makedirs(out_dir, exist_ok=True)

# 24 Perfect Narrative Elements (Top-to-Bottom, Left-to-Right)
narrative_elements = [
    # === ROW 1: Origins, Cold Climates & Wild Apple (Left to Right) ===
    ("01_giant_red_apple", (20, 20, 240, 265)),
    ("02_wild_sour_apple", (245, 80, 380, 255)),
    ("03_wild_branch", (380, 25, 630, 265)),
    ("04_apple_blossom_flower", (630, 90, 790, 265)),
    ("05_blooming_apple_tree", (790, 25, 1025, 265)),
    ("06_snowy_mountains_winter", (1025, 50, 1300, 265)),
    ("07_central_asia_map", (1300, 60, 1530, 265)),

    # === ROW 2: Roman Expansion & Cultivation (Left to Right) ===
    ("08_roman_soldier", (10, 260, 210, 515)),
    ("09_horse_cart_apples", (215, 310, 545, 515)),
    ("10_europe_map_arrow", (545, 290, 770, 510)),
    ("11_farmer_planting", (770, 305, 1015, 510)),
    ("12_tree_growing_stages", (1015, 285, 1530, 515)),

    # === ROW 3: Evolution Scale & Apple Diversity (Left to Right) ===
    ("13_evolution_scale", (15, 500, 735, 675)),
    ("14_hand_picking_apple", (735, 510, 1040, 680)),
    ("15_apple_varieties_rainbow", (1040, 530, 1530, 675)),

    # === ROW 4: Farming, Crate & Modern Harvest (Left to Right) ===
    ("16_seedling_cycle", (15, 675, 410, 830)),
    ("17_harvest_crate", (410, 670, 645, 830)),
    ("18_sliced_apples_juice", (645, 690, 1095, 830)),
    ("19_farmer_inspecting_apple", (1095, 670, 1295, 830)),
    ("20_quality_checkboxes", (1295, 690, 1530, 800)),

    # === ROW 5: Health, Nutrition & Storage (Left to Right) ===
    ("21_digestive_health_gut", (15, 825, 250, 1015)),
    ("22_vitamins_bubbles", (250, 840, 490, 1010)),
    ("23_heart_health_pulse", (490, 860, 705, 995)),
    ("24_wheat_fiber_apples", (705, 840, 955, 1010)),
    ("25_apple_harvest_pile", (955, 835, 1290, 1015)),
    ("26_refrigerator_modern_apples", (1290, 795, 1530, 1015)),
]

catalog = []
# Create Master Whiteboard Preview with EXACT CONTOURS
preview = np.full((h, w, 3), 255, dtype=np.uint8)

contour_colors = [
    (220, 50, 30),   # Vibrant Blue
    (30, 160, 230),  # Warm Orange
    (40, 180, 40),   # Emerald Green
    (180, 40, 160),  # Violet
    (20, 120, 220),  # Coral
    (0, 165, 255),   # Golden Yellow
]

for idx, (name, (bx1, by1, bx2, by2)) in enumerate(narrative_elements):
    matched_cids = []
    for cid in range(1, num_labels):
        cx, cy = centroids[cid]
        area = stats[cid, cv2.CC_STAT_AREA]
        if bx1 <= cx <= bx2 and by1 <= cy <= by2 and area >= 50:
            matched_cids.append(cid)
            
    if not matched_cids:
        print(f"Warning: No components matched for {name}")
        continue

    # 1. Exact organic contour mask
    comp_mask = np.isin(labels, matched_cids).astype(np.uint8) * 255
    contours, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    # Bounding slice for tight transparent PNG
    ys, xs = np.where(comp_mask > 0)
    x1, x2 = int(np.min(xs)), int(np.max(xs))
    y1, y2 = int(np.min(ys)), int(np.max(ys))
    
    # Crop RGBA strictly inside contour mask
    crop = rgba_img[y1:y2+1, x1:x2+1].copy()
    crop_m = comp_mask[y1:y2+1, x1:x2+1]
    crop[:, :, 3] = np.where(crop_m > 0, crop[:, :, 3], 0)
    
    out_file = os.path.join(out_dir, f"{name}.png")
    cv2.imwrite(out_file, crop)
    
    # Paste onto master preview
    c_bgr = crop[:, :, :3].astype(np.float32)
    c_a = crop[:, :, 3].astype(np.float32) / 255.0
    c_a3 = np.repeat(c_a[:, :, np.newaxis], 3, axis=2)
    roi = preview[y1:y2+1, x1:x2+1].astype(np.float32)
    preview[y1:y2+1, x1:x2+1] = np.clip(c_bgr * c_a3 + roi * (1.0 - c_a3), 0, 255).astype(np.uint8)
    
    # 2. Draw EXACT CONTOUR OUTLINE hugging the element (ZERO RECTANGLES)
    color = contour_colors[idx % len(contour_colors)]
    cv2.drawContours(preview, contours, -1, color, 2, cv2.LINE_AA)
    
    # Clean label along contour
    lbl_text = name.split("_", 1)[1]
    cv2.putText(preview, f"{idx+1}. {lbl_text}", (x1, max(18, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (30, 30, 30), 1, cv2.LINE_AA)
    
    catalog.append({
        "name": name,
        "file": out_file,
        "contour_points": sum(len(c) for c in contours),
        "size": f"{x2-x1+1}x{y2-y1+1}"
    })
    print(f"Extracted {name}: pts={sum(len(c) for c in contours)}, size={x2-x1+1}x{y2-y1+1}")

preview_path = "experiments/new_image_exact_contours_preview.jpg"
cv2.imwrite(preview_path, preview)
print(f"Saved exact organic contour preview to {preview_path}")

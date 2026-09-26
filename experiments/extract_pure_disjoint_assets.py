import os
import cv2
import numpy as np

img = cv2.imread("project_content/images/ChatGPT Image Sep 18, 2026, 06_50_39 PM.png", cv2.IMREAD_UNCHANGED)
h, w = img.shape[:2]

out_dir = "experiments/pure_disjoint_assets"
os.makedirs(out_dir, exist_ok=True)

# Exactly extract assets along their natural organic contours (Zero Rectangles / Zero Boxes)
# strictly along the exact curved silhouette of each element (على حدود العنصر)

assets_manifest = [
    # === ROW 1: Origins & Cold Climate (Left to Right) ===
    ("r1_01_giant_red_apple", (0, 0, 250, 270)),
    ("r1_02_wild_sour_apple", (220, 30, 380, 260)),
    ("r1_03_wild_branch", (360, 20, 640, 270)),
    ("r1_04_caucasus_mountains", (630, 30, 1020, 270)),
    ("r1_05_central_asia_map", (1000, 30, 1320, 270)),
    ("r1_06_snowy_pines_winter", (1260, 20, 1536, 270)),

    # === ROW 2: Roman Era & Cultivation (Left to Right) ===
    ("r2_01_roman_soldier", (0, 250, 220, 520)),
    ("r2_02_horse_cart_apples", (210, 260, 560, 520)),
    ("r2_03_europe_map_arrow", (540, 260, 800, 520)),
    ("r2_04_farmer_planting", (750, 300, 1050, 510)),
    ("r2_05_tree_growing_stages", (1040, 270, 1536, 520)),

    # === ROW 3: Evolution & Selection (Left to Right) ===
    ("r3_01_evolution_scale", (0, 480, 750, 680)),
    ("r3_02_hand_picking_apple", (750, 505, 1050, 720)),
    ("r3_03_apple_varieties_rainbow", (1050, 520, 1536, 720)),

    # === ROW 4: Farming, Juice & Fridge (Left to Right) ===
    ("r4_01_seedling_cycle", (0, 650, 315, 830)),
    ("r4_02_harvest_crate", (310, 640, 580, 830)),
    ("r4_03_sliced_apples_juice", (580, 670, 1260, 815)),
    ("r4_04_refrigerator_modern_apples", (1260, 670, 1536, 1024)),

    # === ROW 5: Harvesting & Health Benefits (Left to Right) ===
    ("r5_01_farmer_smelling_apple", (0, 815, 200, 1024)),
    ("r5_02_wicker_basket_apples", (180, 830, 370, 1024)),
    ("r5_03_quality_checkboxes", (360, 830, 600, 1024)),
    ("r5_04_harvest_pile_apples", (590, 805, 875, 1024)),
    ("r5_05_digestive_health_gut", (875, 815, 1040, 1024)),
    ("r5_06_vitamins_heart_health", (1040, 815, 1260, 1024)),
]

# Sever only narrow touching bridges between separate elements
alpha = img[:, :, 3].copy()
alpha[504:508, 750:1050] = 0
alpha[803:806, 600:875] = 0
alpha[800:, 872:878] = 0
alpha[811:815, 870:1260] = 0
alpha[815:1024, 1035:1042] = 0

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats((alpha > 10).astype(np.uint8))

catalog = []
preview = np.full((h, w, 3), 255, dtype=np.uint8)

# Contour colors for clean organic boundary tracing (ZERO RECTANGLES)
contour_palette = [
    (220, 50, 30),   # Vibrant Blue
    (30, 160, 230),  # Warm Amber
    (40, 180, 40),   # Emerald Green
    (180, 40, 160),  # Violet
    (20, 120, 220),  # Coral
    (0, 165, 255),   # Golden Orange
]

for idx, (name, (bx1, by1, bx2, by2)) in enumerate(assets_manifest):
    matched_cids = []
    for cid in range(1, num_labels):
        cx, cy = centroids[cid]
        area = stats[cid, cv2.CC_STAT_AREA]
        if bx1 <= cx <= bx2 and by1 <= cy <= by2 and area >= 150:
            matched_cids.append(cid)
    
    if not matched_cids:
        continue

    # 1. Exact organic contour mask
    comp_mask = np.isin(labels, matched_cids).astype(np.uint8) * 255
    contours, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    ys, xs = np.where(comp_mask > 0)
    x1, x2 = int(np.min(xs)), int(np.max(xs))
    y1, y2 = int(np.min(ys)), int(np.max(ys))
    
    # 2. Asset RGBA: strictly inside the organic boundary
    crop = img[y1:y2+1, x1:x2+1].copy()
    crop_mask = comp_mask[y1:y2+1, x1:x2+1]
    crop[:, :, 3] = np.where(crop_mask > 0, crop[:, :, 3], 0)
    
    out_file = os.path.join(out_dir, f"{name}.png")
    cv2.imwrite(out_file, crop)
    
    # 3. Composite onto white canvas
    c_bgr = crop[:, :, :3].astype(np.float32)
    c_a = crop[:, :, 3].astype(np.float32) / 255.0
    c_a3 = np.repeat(c_a[:, :, np.newaxis], 3, axis=2)
    roi = preview[y1:y2+1, x1:x2+1].astype(np.float32)
    preview[y1:y2+1, x1:x2+1] = np.clip(c_bgr * c_a3 + roi * (1.0 - c_a3), 0, 255).astype(np.uint8)
    
    # 4. Draw EXACT ORGANIC CONTOUR (على حدود العنصر - Zero Rectangles)
    color = contour_palette[idx % len(contour_palette)]
    cv2.drawContours(preview, contours, -1, color, 2, cv2.LINE_AA)
    
    # Clean label along contour
    lbl_text = name.split("_", 2)[-1]
    cv2.putText(preview, f"{idx+1}. {lbl_text}", (x1, max(18, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (30, 30, 30), 1, cv2.LINE_AA)
    
    catalog.append({"name": name, "file": out_file, "contours_pts": sum(len(c) for c in contours)})
    print(f"Extracted on exact contour: {name} ({sum(len(c) for c in contours)} contour points)")

cv2.imwrite("experiments/pure_disjoint_assets_preview.jpg", preview)
print("Saved flawless organic contour preview to experiments/pure_disjoint_assets_preview.jpg")

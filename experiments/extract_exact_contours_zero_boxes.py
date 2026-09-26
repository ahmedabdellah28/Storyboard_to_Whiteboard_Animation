import os
import cv2
import numpy as np

# Load original transparent asset sheet
src_path = "project_content/images/ChatGPT Image Sep 18, 2026, 06_50_39 PM.png"
img = cv2.imread(src_path, cv2.IMREAD_UNCHANGED)
if img is None:
    raise FileNotFoundError(f"Source image not found at {src_path}")

h, w = img.shape[:2]
alpha = img[:, :, 3].copy()

# Sever only the microscopic contact bridges between neighboring elements
alpha[504:508, 750:1050] = 0   # Sever narrow soil contact between farmer planting and hand picking
alpha[803:806, 600:875] = 0    # Sever narrow touch between juice splash and harvest pile
alpha[800:, 872:878] = 0       # Sever vertical touch between harvest pile and gut health
alpha[811:815, 870:1260] = 0   # Sever narrow touch between juice splash and gut/vitamins
alpha[815:1024, 1035:1042] = 0 # Sever vertical touch between gut health and vitamins

# Connected components on organic silhouettes
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats((alpha > 10).astype(np.uint8))

out_dir = "experiments/exact_contour_assets"
os.makedirs(out_dir, exist_ok=True)

# Define the 22 narrative assets by their precise component seed regions
# Organized strictly Left to Right, Top to Bottom
asset_definitions = [
    # --- ROW 1: Origins, Wild Fruit & Cold Climates (Left to Right) ---
    ("01_giant_red_apple", (0, 0, 250, 270)),
    ("02_wild_sour_apple", (220, 30, 380, 260)),
    ("03_wild_branch", (360, 20, 640, 270)),
    ("04_caucasus_mountains", (630, 30, 1020, 270)),
    ("05_central_asia_map", (1000, 30, 1320, 270)),
    ("06_snowy_pines_winter", (1260, 20, 1536, 270)),

    # --- ROW 2: Roman Era, Expansion & Cultivation (Left to Right) ---
    ("07_roman_soldier", (0, 250, 220, 520)),
    ("08_horse_cart_apples", (210, 260, 560, 520)),
    ("09_europe_map_arrow", (540, 260, 800, 520)),
    ("10_farmer_planting", (750, 300, 1050, 510)),
    ("11_tree_growing_stages", (1040, 270, 1536, 520)),

    # --- ROW 3: Size Evolution, Selection & Diversity (Left to Right) ---
    ("12_evolution_scale", (0, 480, 750, 680)),
    ("13_hand_picking_apple", (750, 505, 1050, 720)),
    ("14_apple_varieties_rainbow", (1050, 520, 1536, 720)),

    # --- ROW 4: Harvest Cycle & Modern Storage (Left to Right) ---
    ("15_seedling_cycle", (0, 650, 315, 830)),
    ("16_harvest_crate", (310, 640, 580, 830)),
    ("17_sliced_apples_juice", (580, 670, 1260, 815)),
    ("18_refrigerator_modern_apples", (1260, 670, 1536, 1024)),

    # --- ROW 5: Quality, Nutrition & Health Benefits (Left to Right) ---
    ("19_farmer_smelling_apple", (0, 815, 200, 1024)),
    ("20_wicker_basket_apples", (180, 830, 370, 1024)),
    ("21_quality_checkboxes", (360, 830, 600, 1024)),
    ("22_harvest_pile_apples", (590, 805, 875, 1024)),
    ("23_digestive_health_gut", (875, 815, 1040, 1024)),
    ("24_vitamins_heart_health", (1040, 815, 1260, 1024)),
]

print(f"Total defined assets: {len(asset_definitions)}")

# Build dictionary of component IDs inside each definition
catalog = []
for name, (bx1, by1, bx2, by2) in asset_definitions:
    matched_cids = []
    for cid in range(1, num_labels):
        cx, cy = centroids[cid]
        area = stats[cid, cv2.CC_STAT_AREA]
        if bx1 <= cx <= bx2 and by1 <= cy <= by2 and area >= 150:
            matched_cids.append(cid)
    
    if len(matched_cids) == 0:
        print(f"Warning: No components matched for {name}")
        continue

    # Build exact organic mask
    comp_mask = np.isin(labels, matched_cids).astype(np.uint8) * 255
    
    # Find exact contours (NO RECTANGLES)
    contours, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    # Bounding slice only for tight file cropping
    ys, xs = np.where(comp_mask > 0)
    x1, x2 = int(np.min(xs)), int(np.max(xs))
    y1, y2 = int(np.min(ys)), int(np.max(ys))
    
    # Asset RGBA: strictly inside the organic contour mask
    crop = img[y1:y2+1, x1:x2+1].copy()
    crop_mask = comp_mask[y1:y2+1, x1:x2+1]
    
    # Zero alpha outside contour
    crop[:, :, 3] = np.where(crop_mask > 0, crop[:, :, 3], 0)
    
    # Save isolated contour asset
    out_file = os.path.join(out_dir, f"{name}.png")
    cv2.imwrite(out_file, crop)
    
    catalog.append({
        "name": name,
        "file": out_file,
        "mask": comp_mask,
        "contours": contours,
        "bbox": (x1, y1, x2 - x1 + 1, y2 - y1 + 1),
        "crop": crop,
        "cids": matched_cids
    })
    print(f"Extracted along exact contour: {name} (pts={sum(len(c) for c in contours)})")

# --- CREATE CONTOUR BOUNDARY PREVIEW (ZERO BOXES / ZERO RECTANGLES) ---
# White canvas background
contour_preview = np.full((h, w, 3), 255, dtype=np.uint8)

# 1. First paste all assets on pure white
for item in catalog:
    crop = item["crop"]
    x, y, bw, bh = item["bbox"]
    c_bgr = crop[:, :, :3].astype(np.float32)
    c_a = crop[:, :, 3].astype(np.float32) / 255.0
    c_a3 = np.repeat(c_a[:, :, np.newaxis], 3, axis=2)
    roi = contour_preview[y:y+bh, x:x+bw].astype(np.float32)
    contour_preview[y:y+bh, x:x+bw] = np.clip(c_bgr * c_a3 + roi * (1.0 - c_a3), 0, 255).astype(np.uint8)

# 2. Draw stylish EXACT ORGANIC CONTOURS hugging the natural boundary of each element
# Palette of modern vibrant outline colors
contour_colors = [
    (220, 50, 30),   # Vibrant Blue
    (30, 160, 230),  # Warm Amber / Orange
    (40, 180, 40),   # Emerald Green
    (180, 40, 160),  # Violet
    (20, 120, 220),  # Coral
    (0, 165, 255),   # Golden Orange
]

for idx, item in enumerate(catalog):
    color = contour_colors[idx % len(contour_colors)]
    # Draw true contour line along the element's exact curved silhouette
    cv2.drawContours(contour_preview, item["contours"], -1, color, 2, cv2.LINE_AA)
    
    # Label at top of contour
    x, y, bw, bh = item["bbox"]
    lbl = item["name"].split("_", 1)[1] if "_" in item["name"] else item["name"]
    # Small aesthetic pill for label
    cv2.putText(contour_preview, f"#{idx+1} {lbl}", (x + 2, max(20, y - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (40, 40, 40), 1, cv2.LINE_AA)

preview_out = "experiments/exact_contour_boundary_preview.png"
cv2.imwrite(preview_out, contour_preview)
print(f"Saved exact contour boundary preview to {preview_out}")

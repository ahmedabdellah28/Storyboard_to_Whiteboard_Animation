import os
import cv2
import numpy as np

img = cv2.imread("project_content/images/ChatGPT Image Sep 18, 2026, 06_50_39 PM.png", cv2.IMREAD_UNCHANGED)
h, w = img.shape[:2]
alpha = img[:, :, 3].copy()

# 1. Sever narrow touch between farmer soil (y~505) and hand leaves (y~510):
# Only in x between [750, 1050]:
alpha[504:508, 750:1050] = 0

# 2. Sever tiny contact between juice splash (y~800) and harvest pile (y~805):
# Only in x between [600, 875] at y=803:
alpha[803:806, 600:875] = 0

# 3. Sever vertical contact between harvest pile (x < 875) and digestive gut (x >= 875):
alpha[800:, 872:878] = 0

# Connected components
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats((alpha > 10).astype(np.uint8))

out_dir = "experiments/exact_contour_assets"
os.makedirs(out_dir, exist_ok=True)

def extract_comp_contour(comp_ids, name):
    mask = np.isin(labels, comp_ids)
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return None
    x1, x2 = int(np.min(xs)), int(np.max(xs))
    y1, y2 = int(np.min(ys)), int(np.max(ys))
    
    crop = img[y1:y2+1, x1:x2+1].copy()
    crop_mask = mask[y1:y2+1, x1:x2+1]
    
    # Set alpha strictly to zero outside the component contour
    crop[:, :, 3] = np.where(crop_mask, crop[:, :, 3], 0)
    
    out_p = os.path.join(out_dir, f"{name}.png")
    cv2.imwrite(out_p, crop)
    print(f"Extracted {name}: size={x2-x1+1}x{y2-y1+1}, area={mask.sum()}")
    return crop, (x1, y1, x2-x1+1, y2-y1+1)

# Find components automatically matching each asset's centroid
def find_cids_in_box(x1, y1, x2, y2, min_area=300):
    cids = []
    for i in range(1, num_labels):
        x, y, bw, bh, area = stats[i]
        cx, cy = centroids[i]
        if x1 <= cx <= x2 and y1 <= cy <= y2 and area >= min_area:
            cids.append(i)
    return cids

# Map 22 assets using precise centroid bounding boxes
assets_manifest = [
    # Scene 1:
    ("01_giant_red_apple", find_cids_in_box(0, 0, 260, 280, 5000)),
    ("02_wild_sour_apple", find_cids_in_box(220, 30, 380, 260, 5000)),
    ("03_wild_branch", find_cids_in_box(360, 20, 640, 270, 5000)),
    ("04_caucasus_mountains", find_cids_in_box(630, 30, 1020, 270, 10000)),
    ("05_central_asia_map", find_cids_in_box(1000, 30, 1320, 270, 10000)),
    ("06_snowy_pines_winter", find_cids_in_box(1260, 20, 1536, 270, 1000)),

    # Scene 2:
    ("07_roman_soldier", find_cids_in_box(0, 250, 220, 520, 5000)),
    ("08_horse_cart_apples", find_cids_in_box(210, 260, 580, 520, 5000)),
    ("09_europe_map_arrow", find_cids_in_box(540, 260, 800, 520, 5000)),
    ("10_farmer_planting", find_cids_in_box(750, 300, 1050, 510, 5000)),
    ("11_tree_growing_stages", find_cids_in_box(1040, 270, 1536, 520, 2000)),

    # Scene 3:
    ("12_evolution_scale", find_cids_in_box(300, 480, 750, 680, 5000)),
    ("13_hand_picking_apple", find_cids_in_box(750, 505, 1050, 700, 5000)),
    ("14_apple_varieties_rainbow", find_cids_in_box(1050, 520, 1536, 700, 5000)),
    ("15_sliced_apples_juice", find_cids_in_box(550, 670, 1260, 810, 3000)),

    # Scene 4:
    ("16_farmer_smelling_apple", find_cids_in_box(0, 810, 220, 1024, 5000)),
    ("17_wicker_basket_apples", find_cids_in_box(180, 830, 370, 1024, 5000)),
    ("18_quality_checkboxes", find_cids_in_box(360, 830, 600, 1024, 3000)),
    ("19_harvest_pile_apples", find_cids_in_box(590, 805, 875, 1024, 5000)),
    ("20_digestive_health_gut", find_cids_in_box(875, 800, 1050, 1024, 3000)),
    ("21_vitamins_heart_health", find_cids_in_box(1040, 810, 1260, 1024, 3000)),

    # Scene 5 (Outro):
    ("22_refrigerator_modern_apples", find_cids_in_box(1260, 670, 1536, 1024, 10000)),
]

extracted_list = []
for name, cids in assets_manifest:
    res = extract_comp_contour(cids, name)
    if res is not None:
        crop, bbox = res
        extracted_list.append((name, crop, bbox))

# Preview
preview_canvas = np.full((h, w, 3), 255, dtype=np.uint8)
for name, crop, (bx, by, bw, bh) in extracted_list:
    c_bgr = crop[:, :, :3].astype(np.float32)
    c_a = crop[:, :, 3].astype(np.float32) / 255.0
    c_a3 = np.repeat(c_a[:, :, np.newaxis], 3, axis=2)
    roi = preview_canvas[by:by+bh, bx:bx+bw].astype(np.float32)
    preview_canvas[by:by+bh, bx:bx+bw] = np.clip(c_bgr * c_a3 + roi * (1.0 - c_a3), 0, 255).astype(np.uint8)

cv2.imwrite("experiments/exact_contour_pure_preview.png", preview_canvas)
print("Updated exact_contour_pure_preview.png with flawless uncut assets!")

import os
import json
import cv2

img = cv2.imread("project_content/images/ChatGPT Image Sep 18, 2026, 06_50_39 PM.png", cv2.IMREAD_UNCHANGED)
with open("experiments/transparent_assets_manifest.json") as f:
    manifest = json.load(f)

out_dir = "experiments/apple_video_assets"
os.makedirs(out_dir, exist_ok=True)

# Map asset ID to semantic name
semantic_map = {
    1: "apple_giant_red",
    6: "apple_wild_sour",
    3: "branch_wild_apples",
    4: "caucasus_mountains_forest",
    7: "map_central_asia_pin",
    8: "snowy_pines",
    5: "snowflake_large",
    2: "snowflake_small",
    9: "roman_soldier",
    12: "horse_cart_apples",
    10: "map_europe_arrow",
    14: "farmer_planting_tree",
    15: "seedling_growing",
    13: "apple_tree_cultivated",
    11: "apple_tree_mature",
    20: "apple_cross_section_wild",
    19: "apple_half_seeds",
    21: "arrow_yellow",
    18: "apple_sour_small",
    16: "apple_evolution_scale",
    22: "hand_picking_apple",
    17: "apple_varieties_rainbow",
    24: "seedling_soil",
    25: "cycle_arrow_top",
    29: "cycle_arrow_bot",
    23: "apple_duo",
    22: "apple_harvest_crate",
    26: "apple_cut_half",
    28: "apple_cut_slices_splash",
    30: "farmer_inspecting_scent",
    33: "wicker_basket_apples",
    34: "selection_checkboxes",
    28: "harvest_apple_pile",
    32: "digestive_health_gut",
    31: "vitamins_heart_health",
    27: "refrigerator_modern_apples"
}

# In manifest, let's match each asset by bbox
for item in manifest:
    aid = item["id"]
    x, y, bw, bh = item["bbox"]
    crop = img[y:y+bh, x:x+bw]
    sem_name = semantic_map.get(aid, f"asset_{aid:02d}")
    out_path = os.path.join(out_dir, f"{sem_name}.png")
    cv2.imwrite(out_path, crop)
    print(f"Saved {sem_name}.png (#{aid}, size={bw}x{bh})")

print("All semantic assets saved to experiments/apple_video_assets!")

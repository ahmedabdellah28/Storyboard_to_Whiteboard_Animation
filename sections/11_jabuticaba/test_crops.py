import os
import sys
import cv2
import numpy as np

ROOT_DIR = r"E:\image_to_animate"
img_path = os.path.join(ROOT_DIR, "sections/11_jabuticaba/storyboard.png")
data = np.fromfile(img_path, dtype=np.uint8)
img = cv2.imdecode(data, cv2.IMREAD_COLOR)
h, w = img.shape[:2]
print(f"Storyboard dimensions: {w}x{h}")

scratch_dir = os.path.join(ROOT_DIR, "sections/11_jabuticaba/scratch/test_crops")
os.makedirs(scratch_dir, exist_ok=True)

crops = {
    # Row 1
    "r1_01_jabuticaba_hero_cluster": (0, 0, 400, 260),
    "r1_02_jabuticaba_tree_full": (360, 0, 750, 260),
    "r1_03_trunk_covered_fruits": (750, 0, 990, 260),
    "r1_04_trunk_berries_macro": (990, 0, 1280, 260),
    "r1_05_trunk_white_flowers_macro": (1280, 0, 1536, 260),

    # Row 2
    "r2_01_jabuticaba_trio_cut": (0, 260, 310, 520),
    "r2_02_traditional_grapes_comparison": (310, 260, 560, 520),
    "r2_03_popping_juice_burst_sequence": (560, 280, 980, 510),
    "r2_04_slices_cross_sections": (980, 260, 1310, 520),
    "r2_05_hand_holding_single_berry": (1310, 260, 1536, 520),

    # Row 3
    "r3_01_branch_ripening_gradient": (0, 520, 360, 760),
    "r3_02_spoilage_sequence_decay": (360, 530, 750, 760),
    "r3_03_calendar_rapid_spoilage_3days": (750, 530, 980, 760),
    "r3_04_export_crates_airplane_prohibited": (980, 530, 1290, 760),
    "r3_05_brazil_map_native_origin": (1290, 530, 1536, 760),

    # Row 4
    "r4_01_growth_sprout_stage": (0, 780, 125, 990),
    "r4_02_growth_sapling_stage": (125, 780, 250, 990),
    "r4_03_growth_bushy_juvenile_stage": (250, 780, 375, 990),
    "r4_04_growth_mature_tree_stage": (375, 760, 550, 990),
    "r4_05_growth_fruiting_tree_stage": (550, 750, 850, 990),
    "r4_06_basket_harvest_platter": (850, 750, 1240, 1010),
    "r4_07_fresh_juice_tall_glass": (1240, 750, 1536, 1010),
}

for name, (x1, y1, x2, y2) in crops.items():
    crop = img[y1:y2, x1:x2]
    out_f = os.path.join(scratch_dir, f"{name}.png")
    cv2.imwrite(out_f, crop)
    print(f"Saved {name}: {crop.shape[1]}x{crop.shape[0]}")

print("Test crops completed!")

import os
import cv2
import numpy as np

img_path = "project_content/images/ChatGPT Image Sep 18, 2026, 11_33_57 PM.png"
img = cv2.imread(img_path)
h, w = img.shape[:2]

diff = 255.0 - img.astype(np.float32)
dist = np.max(diff, axis=2)
alpha_smooth = np.clip((dist - 2.0) / 10.0 * 255.0, 0, 255).astype(np.uint8)
rgba_img = np.dstack([img, alpha_smooth])

out_dir = "experiments/exact_contour_assets"
os.makedirs(out_dir, exist_ok=True)

def save_crop_contour(x1, y1, x2, y2, name):
    crop_rgba = rgba_img[y1:y2+1, x1:x2+1].copy()
    # Mask inside crop
    crop_dist = dist[y1:y2+1, x1:x2+1]
    mask = (crop_dist > 12).astype(np.uint8)
    
    # Clean empty edges
    ys, xs = np.where(mask > 0)
    if len(ys) == 0:
        return None
    cy1, cy2 = int(np.min(ys)), int(np.max(ys))
    cx1, cx2 = int(np.min(xs)), int(np.max(xs))
    
    final_crop = crop_rgba[cy1:cy2+1, cx1:cx2+1].copy()
    final_mask = mask[cy1:cy2+1, cx1:cx2+1]
    final_crop[:, :, 3] = np.where(final_mask > 0, final_crop[:, :, 3], 0)
    
    out_file = os.path.join(out_dir, f"{name}.png")
    cv2.imwrite(out_file, final_crop)
    print(f"Extracted sub-asset {name}: {final_crop.shape[1]}x{final_crop.shape[0]}")
    return final_crop

# 1. Four Tree Growing Stages (Individual Pieces)
save_crop_contour(1020, 400, 1105, 510, "12_tree_stage_1_seedling")
save_crop_contour(1115, 360, 1205, 510, "12_tree_stage_2_sapling")
save_crop_contour(1215, 310, 1330, 510, "12_tree_stage_3_growing")
save_crop_contour(1335, 290, 1520, 510, "12_tree_stage_4_mature")

# 2. Five Apple Varieties (Individual Pieces)
save_crop_contour(1050, 535, 1145, 665, "15_var_1_red")
save_crop_contour(1145, 535, 1235, 665, "15_var_2_green")
save_crop_contour(1235, 535, 1320, 665, "15_var_3_yellow")
save_crop_contour(1320, 535, 1410, 665, "15_var_4_dark")
save_crop_contour(1410, 535, 1515, 665, "15_var_5_striped")

# 3. Size Evolution Scale (3 Stages)
# Ancient small apples
save_crop_contour(25, 550, 195, 660, "13_evo_1_ancient_sour")
# Intermediate growth with arrow
save_crop_contour(195, 560, 455, 660, "13_evo_2_selection_growth")
# Giant modern honeycrisp
save_crop_contour(455, 510, 700, 660, "13_evo_3_giant_honeycrisp")

# 4. Four Quality Checkboxes (Individual Checked Apples)
save_crop_contour(1300, 690, 1355, 795, "20_check_1_green")
save_crop_contour(1355, 690, 1410, 795, "20_check_2_green")
save_crop_contour(1410, 690, 1465, 795, "20_check_3_green")
save_crop_contour(1465, 690, 1520, 795, "20_check_4_red_x")

print("All sub-assets extracted successfully!")

import os
import sys
import cv2
import numpy as np

ROOT_DIR = r"E:\image_to_animate"
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.processing.whiteboard_processor import WhiteboardProcessor
from engine.processing.dynamic_border_detector import DynamicBorderDetector

img_path = os.path.join(ROOT_DIR, "project_content", "images", "ChatGPT Image Sep 18, 2026, 04_51_53 PM.png")
img = cv2.imread(img_path)
panels = WhiteboardProcessor.discover_panels(img)

out_base = "experiments/semantic_layers"
os.makedirs(out_base, exist_ok=True)

for p_num in range(1, 7):
    px, py, pw, ph = panels[p_num - 1]["bbox"]
    raw_crop = img[py:py+ph, px:px+pw]
    clean = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)["clean_crop"]
    ch, cw = clean.shape[:2]
    
    p_dir = os.path.join(out_base, f"panel_{p_num:02d}")
    os.makedirs(p_dir, exist_ok=True)
    cv2.imwrite(os.path.join(p_dir, "clean_panel.png"), clean)
    
    # Floodfill background
    bg_mask = np.zeros((ch + 2, cw + 2), dtype=np.uint8)
    ff = clean.copy()
    for bx in [0, cw // 2, cw - 1]:
        for by in [0, ch // 2, ch - 1]:
            if np.all(clean[by, bx] >= 240):
                cv2.floodFill(ff, bg_mask, (bx, by), (0, 255, 0), loDiff=(12, 12, 12), upDiff=(12, 12, 12))
                
    is_bg = (bg_mask[1:-1, 1:-1] > 0)
    is_fg = (~is_bg).astype(np.uint8) * 255
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(is_fg)
    
    valid_comps = {}
    c_idx = 1
    for comp_id in range(1, num_labels):
        x, y, w, h, area = stats[comp_id]
        if area >= 80:
            valid_comps[c_idx] = {
                "id": comp_id, "bbox": (x, y, w, h), "area": area
            }
            c_idx += 1
            
    def make_layer(comp_indices, layer_name):
        mask = np.zeros((ch, cw), dtype=np.uint8)
        for ci in comp_indices:
            if ci in valid_comps:
                cid = valid_comps[ci]["id"]
                mask[labels == cid] = 255
        
        # Bounding box of combined mask
        ys, xs = np.where(mask > 0)
        if len(ys) == 0:
            return None
        min_x, max_x = int(np.min(xs)), int(np.max(xs))
        min_y, max_y = int(np.min(ys)), int(np.max(ys))
        lw = max_x - min_x + 1
        lh = max_y - min_y + 1
        
        crop_bgr = clean[min_y:max_y+1, min_x:max_x+1]
        crop_a = mask[min_y:max_y+1, min_x:max_x+1]
        b, g, r = cv2.split(crop_bgr)
        rgba = cv2.merge([b, g, r, crop_a])
        
        save_path = os.path.join(p_dir, f"{layer_name}.png")
        cv2.imwrite(save_path, rgba)
        
        # Also save metadata
        return {
            "name": layer_name,
            "file": save_path,
            "rel_x": min_x,
            "rel_y": min_y,
            "w": lw,
            "h": lh
        }

    layers = []
    if p_num == 1:
        layers.append(make_layer([4], "narrator_char"))
        layers.append(make_layer([1, 2, 3, 5, 6, 8, 9, 10, 11, 16, 17, 18, 19, 20], "thermometer_unit"))
        layers.append(make_layer([7], "crowd_silhouette"))
        layers.append(make_layer([12, 13], "red_figures"))
        layers.append(make_layer([14, 15], "badge_2percent"))
    elif p_num == 2:
        layers.append(make_layer([2, 4, 5, 6], "brain_profile"))
        layers.append(make_layer([1, 3, 7, 8, 9], "saturn_planet"))
        layers.append(make_layer([10, 11, 12], "warning_badge"))
        layers.append(make_layer([13], "stressed_person"))
        layers.append(make_layer([14, 15, 16, 17], "charts_ecg"))
    elif p_num == 3:
        layers.append(make_layer([3], "char_left"))
        layers.append(make_layer([4], "char_right"))
        layers.append(make_layer([1, 2, 5, 6, 7, 8, 9, 10, 11, 12], "icons_and_badges"))
    elif p_num == 4:
        layers.append(make_layer([1], "classroom_auditorium"))
        layers.append(make_layer([2, 3, 4, 5, 6, 7, 8], "desks_students"))
    elif p_num == 5:
        layers.append(make_layer([5], "char_thinker"))
        layers.append(make_layer([1, 4], "bubble_top_mid"))
        layers.append(make_layer([2, 6, 9], "bubble_top_right"))
        layers.append(make_layer([3, 7], "bubble_top_left"))
        layers.append(make_layer([8, 12], "bubble_mid_left"))
        layers.append(make_layer([10, 11, 13], "bubble_mid_right"))
        layers.append(make_layer([14], "bubble_bot_right"))
    elif p_num == 6:
        layers.append(make_layer([1], "hero_scene"))
        layers.append(make_layer([9], "key_device"))
        layers.append(make_layer([2, 3, 4, 5, 6, 7, 8], "energy_sparkles"))

    print(f"Panel {p_num}: Generated {len(layers)} semantic layers successfully.")

print("All semantic layers generated!")

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

out_base = "experiments/choreographed_layers"
os.makedirs(out_base, exist_ok=True)

for p_num in range(1, 7):
    px, py, pw, ph = panels[p_num - 1]["bbox"]
    raw_crop = img[py:py+ph, px:px+pw]
    clean = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)["clean_crop"]
    # Resize clean to standard 900x900
    clean_900 = cv2.resize(clean, (900, 900), interpolation=cv2.INTER_LANCZOS4)
    ch, cw = clean_900.shape[:2]
    
    p_dir = os.path.join(out_base, f"panel_{p_num:02d}")
    os.makedirs(p_dir, exist_ok=True)
    cv2.imwrite(os.path.join(p_dir, "clean_panel.png"), clean_900)
    
    # Background mask via floodfill
    bg_mask = np.zeros((ch + 2, cw + 2), dtype=np.uint8)
    ff = clean_900.copy()
    for bx in [0, cw // 2, cw - 1]:
        for by in [0, ch // 2, ch - 1]:
            if np.all(clean_900[by, bx] >= 240):
                cv2.floodFill(ff, bg_mask, (bx, by), (0, 255, 0), loDiff=(12, 12, 12), upDiff=(12, 12, 12))
                
    is_bg = (bg_mask[1:-1, 1:-1] > 0)
    is_fg = (~is_bg).astype(np.uint8) * 255
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(is_fg)
    
    comps = []
    for comp_id in range(1, num_labels):
        x, y, w, h, area = stats[comp_id]
        if area >= 200:
            comps.append({
                "id": comp_id, "bbox": (x, y, w, h), "area": area,
                "cx": float(centroids[comp_id][0]), "cy": float(centroids[comp_id][1])
            })
            
    print(f"Panel {p_num}: {len(comps)} components extracted for choreography.")
    
    def export_composite(comp_ids, name):
        mask = np.zeros((ch, cw), dtype=np.uint8)
        for cid in comp_ids:
            mask[labels == cid] = 255
        ys, xs = np.where(mask > 0)
        if len(ys) == 0:
            return
        x1, x2 = int(np.min(xs)), int(np.max(xs))
        y1, y2 = int(np.min(ys)), int(np.max(ys))
        
        crop_bgr = clean_900[y1:y2+1, x1:x2+1]
        crop_a = mask[y1:y2+1, x1:x2+1]
        b, g, r = cv2.split(crop_bgr)
        rgba = cv2.merge([b, g, r, crop_a])
        cv2.imwrite(os.path.join(p_dir, f"{name}.png"), rgba)
        # also save placement info
        with open(os.path.join(p_dir, f"{name}.txt"), "w") as f_txt:
            f_txt.write(f"{x1},{y1},{x2-x1+1},{y2-y1+1}")

    # Choreographic separation by panel
    if p_num == 1:
        # Narrator: x < 350
        narrator_ids = [c["id"] for c in comps if c["cx"] < 330 and c["cy"] > 100]
        export_composite(narrator_ids, "narrator")
        # Thermometer: x between 330 and 530
        thermo_ids = [c["id"] for c in comps if 330 <= c["cx"] <= 530]
        export_composite(thermo_ids, "thermometer")
        # Crowd: x > 530, y < 650
        crowd_ids = [c["id"] for c in comps if c["cx"] > 530 and c["cy"] < 650 and c["area"] > 5000]
        export_composite(crowd_ids, "crowd")
        # Red figures: x > 530, y < 650, red-ish
        red_ids = [c["id"] for c in comps if c["cx"] > 530 and c["cy"] < 650 and 1000 <= c["area"] <= 5000]
        export_composite(red_ids, "red_figures")
        # Badge 2%: x > 530, y >= 650
        badge_ids = [c["id"] for c in comps if c["cx"] > 530 and c["cy"] >= 650]
        export_composite(badge_ids, "badge_2pct")
        
    elif p_num == 2:
        # Brain Profile: central head
        brain_ids = [c["id"] for c in comps if 120 <= c["cx"] <= 550 and 200 <= c["cy"] <= 780]
        export_composite(brain_ids, "brain_profile")
        # Saturn planet: top left/mid
        saturn_ids = [c["id"] for c in comps if c["cy"] < 320 and c["cx"] < 500]
        export_composite(saturn_ids, "saturn")
        # Charts / Economy: top right
        chart_ids = [c["id"] for c in comps if c["cx"] > 550 and c["cy"] < 450]
        export_composite(chart_ids, "charts")
        # Stressed person: bottom right
        stressed_ids = [c["id"] for c in comps if c["cx"] > 550 and c["cy"] >= 650]
        export_composite(stressed_ids, "stressed_person")
        # Warning badge: bottom mid
        warn_ids = [c["id"] for c in comps if 400 <= c["cx"] <= 650 and 550 <= c["cy"] <= 850 and c["id"] not in brain_ids and c["id"] not in stressed_ids]
        export_composite(warn_ids, "warning_error")
        # Shapes & math: mid right
        math_ids = [c["id"] for c in comps if c["cx"] > 520 and 380 <= c["cy"] <= 650]
        export_composite(math_ids, "math_symbols")
        
    elif p_num == 3:
        # Left Brain Half (Logic/Gears): x < 450
        left_ids = [c["id"] for c in comps if c["cx"] < 450 and 150 <= c["cy"] <= 750]
        export_composite(left_ids, "brain_logic")
        # Right Brain Half (Creative/Color): x >= 450
        right_ids = [c["id"] for c in comps if c["cx"] >= 450 and 150 <= c["cy"] <= 750]
        export_composite(right_ids, "brain_creative")
        # Left icons (calculator, gear, puzzle, chess): x < 350
        left_icon_ids = [c["id"] for c in comps if c["cx"] < 350 and (c["cy"] < 300 or c["cy"] > 600)]
        export_composite(left_icon_ids, "icons_logic")
        # Right icons (palette, lightbulb, heart, plant): x > 550
        right_icon_ids = [c["id"] for c in comps if c["cx"] > 550]
        export_composite(right_icon_ids, "icons_creative")
        
    elif p_num == 4:
        # Development stages: the 3 figures
        fig_ids = [c["id"] for c in comps if c["cy"] < 600]
        export_composite(fig_ids, "growth_figures")
        # Bottom icons (blocks, books, mortarboard, glowing brain)
        bottom_ids = [c["id"] for c in comps if c["cy"] >= 600]
        export_composite(bottom_ids, "learning_elements")
        
    elif p_num == 5:
        # Central Thinker
        thinker_ids = [c["id"] for c in comps if 150 <= c["cx"] <= 700 and 350 <= c["cy"] <= 880]
        export_composite(thinker_ids, "char_thinker")
        # The 6 bubbles:
        b_house = [c["id"] for c in comps if c["cx"] < 350 and c["cy"] < 350]
        export_composite(b_house, "bubble_house")
        b_people = [c["id"] for c in comps if 350 <= c["cx"] <= 580 and c["cy"] < 300]
        export_composite(b_people, "bubble_people")
        b_money = [c["id"] for c in comps if c["cx"] > 580 and c["cy"] < 350]
        export_composite(b_money, "bubble_money")
        b_heart = [c["id"] for c in comps if c["cx"] < 350 and 350 <= c["cy"] <= 650]
        export_composite(b_heart, "bubble_heart")
        b_time = [c["id"] for c in comps if c["cx"] > 580 and 350 <= c["cy"] <= 650]
        export_composite(b_time, "bubble_time")
        b_plant = [c["id"] for c in comps if c["cx"] > 580 and c["cy"] > 650]
        export_composite(b_plant, "bubble_plant")

    elif p_num == 6:
        # Adventurer / Hero
        hero_ids = [c["id"] for c in comps if 350 <= c["cx"] <= 580 and c["cy"] > 450]
        export_composite(hero_ids, "hero_character")
        # Stairs & Door
        stairs_ids = [c["id"] for c in comps if 400 <= c["cx"] <= 800 and 100 <= c["cy"] <= 650]
        export_composite(stairs_ids, "stairs_and_door")
        # Compass
        compass_ids = [c["id"] for c in comps if c["cx"] > 550 and c["cy"] > 600]
        export_composite(compass_ids, "compass")
        # Floating symbols (cloud, target, mountain, chains)
        symbols_ids = [c["id"] for c in comps if c["cx"] < 400 or (c["cx"] > 700 and c["cy"] > 400)]
        export_composite(symbols_ids, "symbols_obstacles")

print("All choreographed layers successfully generated and mapped to 900x900 canvas coordinates!")

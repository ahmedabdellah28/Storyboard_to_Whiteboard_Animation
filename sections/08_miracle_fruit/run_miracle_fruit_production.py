import os
import sys
import json
import subprocess
import numpy as np

# Safe console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.dynamic_section_engine import DynamicSectionEngine, smootherstep, CAM_ZOOM

section_dir = os.path.join(ROOT_DIR, "sections/08_miracle_fruit")
engine = DynamicSectionEngine(section_dir)

# 1. Load layout
layout_path = os.path.join(section_dir, "placed_elements_layout.json")
with open(layout_path, "r", encoding="utf-8") as f:
    layout_data = json.load(f)

placed_elements = layout_data["elements"]
zones = layout_data["zones"]

# Flatten elements lookup
elem_map = {}
for row_key, r_elems in placed_elements.items():
    for el in r_elems:
        elem_map[el["aid"]] = el

# 2. Hero inking configs: (asset_id, start_time, duration)
# All hero elements use True Outside-In Contour Inking
hero_configs = [
    ("r1_01_miracle_fruit_berries_hero", 0.5, 3.2),
    ("r1_05_taste_receptors_tongue_loupe", 12.0, 3.5),
    ("r2_03_lemon_sugar_transformation", 25.0, 3.0),
    ("r3_02_coffee_to_sweet_latte", 32.2, 2.8),
    ("r4_04_glass_bowl_berries_cross_section", 51.5, 3.6),
]

# 3. Elements Staging List (Tight, energetic pacing with continuous narration sync)
staging = [
    # Row 1A
    {"asset": "r1_01_miracle_fruit_berries_hero", "t_start": 0.5, "t_dur": 3.2, "type": "outside_in_pen", "depth": 1},
    {"asset": "r1_02_miracle_plant_branch", "t_start": 4.2, "t_dur": 1.5, "type": "organic_grow", "depth": 2},

    # Row 1B
    {"asset": "r1_03_africa_west_map", "t_start": 8.4, "t_dur": 1.2, "type": "slide_down", "depth": 1},
    {"asset": "r1_04_miraculin_protein_molecule", "t_start": 10.2, "t_dur": 1.0, "type": "jelly_pop", "depth": 2},
    {"asset": "r1_05_taste_receptors_tongue_loupe", "t_start": 12.0, "t_dur": 3.5, "type": "outside_in_pen", "depth": 3},

    # Row 2A
    {"asset": "r2_01_man_eating_berry", "t_start": 19.0, "t_dur": 1.2, "type": "slide_down", "depth": 1},
    {"asset": "r2_02_man_amazed_sweet_taste", "t_start": 20.8, "t_dur": 1.2, "type": "jelly_pop", "depth": 2},

    # Row 2B
    {"asset": "r2_03_lemon_sugar_transformation", "t_start": 25.0, "t_dur": 3.0, "type": "outside_in_pen", "depth": 1},
    {"asset": "r2_04_lime_sugar_transformation", "t_start": 27.2, "t_dur": 1.0, "type": "pulse_pop", "depth": 2},
    {"asset": "r2_05_vinegar_to_apple_juice", "t_start": 28.5, "t_dur": 1.2, "type": "slide_down", "depth": 3},

    # Row 3A
    {"asset": "r3_01_gooseberry_fruit_salad", "t_start": 31.0, "t_dur": 1.0, "type": "slide_down", "depth": 1},
    {"asset": "r3_02_coffee_to_sweet_latte", "t_start": 32.2, "t_dur": 2.8, "type": "outside_in_pen", "depth": 2},

    # Row 3B
    {"asset": "r3_03_grapefruit_sugar_shift", "t_start": 36.0, "t_dur": 1.0, "type": "pulse_pop", "depth": 1},
    {"asset": "r3_04_pickles_sweet_transformation", "t_start": 37.5, "t_dur": 1.2, "type": "slide_down", "depth": 2},

    # Row 4A
    {"asset": "r4_01_african_harvester_basket", "t_start": 41.0, "t_dur": 1.2, "type": "slide_down", "depth": 1},
    {"asset": "r4_02_hands_cupping_berries", "t_start": 43.5, "t_dur": 1.2, "type": "jelly_pop", "depth": 2},
    {"asset": "r4_03_blooming_miracle_shrub", "t_start": 46.0, "t_dur": 1.8, "type": "organic_grow", "depth": 3},

    # Row 4B
    {"asset": "r4_04_glass_bowl_berries_cross_section", "t_start": 51.5, "t_dur": 3.6, "type": "outside_in_pen", "depth": 1},
    {"asset": "r4_05_smoothie_tall_glass_straw", "t_start": 56.5, "t_dur": 2.0, "type": "organic_grow", "depth": 2},
]

# Enrich staging with coordinates
elements_staging = []
for item in staging:
    aid = item["asset"]
    el = elem_map[aid]
    elements_staging.append({
        "asset": aid,
        "pos": (el["x"], el["y"]),
        "size": (el["w"], el["h"]),
        "t_start": item["t_start"],
        "t_dur": item["t_dur"],
        "type": item["type"],
        "depth": item["depth"]
    })

# 4. Camera Trajectory Function (8-Zone Navigation, 66.0s Duration)
z1A = zones["1"]["zone_A"]
z1B = zones["1"]["zone_B"]
z2A = zones["2"]["zone_A"]
z2B = zones["2"]["zone_B"]
z3A = zones["3"]["zone_A"]
z3B = zones["3"]["zone_B"]
z4A = zones["4"]["zone_A"]
z4B = zones["4"]["zone_B"]

def camera_trajectory(t):
    zoom = CAM_ZOOM

    # Zone 1A (0.0 -> 7.2s)
    if t < 7.2:
        return z1A[0], z1A[1], zoom

    # Pan 1A -> 1B (7.2 -> 8.2s)
    elif t < 8.2:
        p = smootherstep((t - 7.2) / 1.0)
        x = z1A[0] + (z1B[0] - z1A[0]) * p
        y = z1A[1] + (z1B[1] - z1A[1]) * p
        return x, y, zoom

    # Zone 1B (8.2 -> 18.0s)
    elif t < 18.0:
        return z1B[0], z1B[1], zoom

    # Transition 1B -> 2A (18.0 -> 19.0s)
    elif t < 19.0:
        p = smootherstep((t - 18.0) / 1.0)
        x = z1B[0] + (z2A[0] - z1B[0]) * p
        y = z1B[1] + (z2A[1] - z1B[1]) * p
        return x, y, zoom

    # Zone 2A (19.0 -> 24.0s)
    elif t < 24.0:
        return z2A[0], z2A[1], zoom

    # Pan 2A -> 2B (24.0 -> 25.0s)
    elif t < 25.0:
        p = smootherstep((t - 24.0) / 1.0)
        x = z2A[0] + (z2B[0] - z2A[0]) * p
        y = z2A[1] + (z2B[1] - z2A[1]) * p
        return x, y, zoom

    # Zone 2B (25.0 -> 30.0s)
    elif t < 30.0:
        return z2B[0], z2B[1], zoom

    # Transition 2B -> 3A (30.0 -> 31.0s)
    elif t < 31.0:
        p = smootherstep((t - 30.0) / 1.0)
        x = z2B[0] + (z3A[0] - z2B[0]) * p
        y = z2B[1] + (z3A[1] - z2B[1]) * p
        return x, y, zoom

    # Zone 3A (31.0 -> 35.0s)
    elif t < 35.0:
        return z3A[0], z3A[1], zoom

    # Pan 3A -> 3B (35.0 -> 36.0s)
    elif t < 36.0:
        p = smootherstep((t - 35.0) / 1.0)
        x = z3A[0] + (z3B[0] - z3A[0]) * p
        y = z3A[1] + (z3B[1] - z3A[1]) * p
        return x, y, zoom

    # Zone 3B (36.0 -> 40.0s)
    elif t < 40.0:
        return z3B[0], z3B[1], zoom

    # Transition 3B -> 4A (40.0 -> 41.0s)
    elif t < 41.0:
        p = smootherstep((t - 40.0) / 1.0)
        x = z3B[0] + (z4A[0] - z3B[0]) * p
        y = z3B[1] + (z4A[1] - z3B[1]) * p
        return x, y, zoom

    # Zone 4A (41.0 -> 50.5s)
    elif t < 50.5:
        return z4A[0], z4A[1], zoom

    # Pan 4A -> 4B (50.5 -> 51.5s)
    elif t < 51.5:
        p = smootherstep((t - 50.5) / 1.0)
        x = z4A[0] + (z4B[0] - z4A[0]) * p
        y = z4A[1] + (z4B[1] - z4A[1]) * p
        return x, y, zoom

    # Zone 4B (Finale steady hold on miracle fruit presentation, zero outro zoom-out)
    else:
        return z4B[0], z4B[1], zoom

# 5. Render Video (66.0s Duration)
duration_sec = 66.0
final_video = engine.render_section(hero_configs, elements_staging, camera_trajectory, duration_sec)

# 6. Extract Preview Frames
preview_dir = os.path.join(section_dir, "preview_frames")
os.makedirs(preview_dir, exist_ok=True)
preview_times = [2.0, 5.5, 9.5, 14.0, 20.0, 26.5, 33.0, 38.0, 44.0, 54.0, 62.0]
for idx, pt in enumerate(preview_times):
    p_img = os.path.join(preview_dir, f"frame_{idx+1:02d}_{pt:.1f}s.jpg")
    cmd = [
        "ffmpeg", "-y", "-ss", str(pt), "-i", final_video,
        "-vframes", "1", "-q:v", "2", p_img
    ]
    subprocess.run(cmd, capture_output=True)

print("Section 08 Miracle Fruit completed successfully with true outside-in inking and tight narration sync!")

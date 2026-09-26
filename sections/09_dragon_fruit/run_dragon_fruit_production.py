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

section_dir = os.path.join(ROOT_DIR, "sections/09_dragon_fruit")
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
    ("r1_01_dragon_fruit_white_flesh_hero", 0.5, 3.2),
    ("r1_04_dragon_fruit_red_flesh_hero", 7.8, 3.0),
    ("r2_02_cactus_branch_harvest", 17.0, 3.2),
    ("r3_02_three_varieties_lineup", 27.5, 3.6),
    ("r4_02_pitaya_smoothie_bowl", 39.0, 3.2),
]

# 3. Elements Staging List (Tight, continuous pacing with zero dead silences)
staging = [
    # Row 1A
    {"asset": "r1_01_dragon_fruit_white_flesh_hero", "t_start": 0.5, "t_dur": 3.2, "type": "outside_in_pen", "depth": 1},
    {"asset": "r1_02_dragon_fruit_cactus_tree", "t_start": 3.8, "t_dur": 1.2, "type": "organic_grow", "depth": 2},

    # Row 1B
    {"asset": "r1_03_blooming_night_flower_stem", "t_start": 6.2, "t_dur": 1.5, "type": "organic_grow", "depth": 1},
    {"asset": "r1_04_dragon_fruit_red_flesh_hero", "t_start": 7.8, "t_dur": 3.0, "type": "outside_in_pen", "depth": 2},

    # Row 2A
    {"asset": "r2_01_world_migration_map", "t_start": 12.2, "t_dur": 1.5, "type": "slide_down", "depth": 1},

    # Row 2B
    {"asset": "r2_02_cactus_branch_harvest", "t_start": 17.0, "t_dur": 3.2, "type": "outside_in_pen", "depth": 1},

    # Row 3A
    {"asset": "r3_01_vietnam_plantation_landscape", "t_start": 21.6, "t_dur": 1.5, "type": "slide_down", "depth": 1},

    # Row 3B
    {"asset": "r3_02_three_varieties_lineup", "t_start": 27.5, "t_dur": 3.6, "type": "outside_in_pen", "depth": 1},

    # Row 4A
    {"asset": "r4_01_nutritional_benefits_composition", "t_start": 33.7, "t_dur": 1.2, "type": "slide_down", "depth": 1},
    {"asset": "r4_05_dragon_fruit_slices_composition", "t_start": 35.0, "t_dur": 1.2, "type": "pulse_pop", "depth": 2},

    # Row 4B
    {"asset": "r4_02_pitaya_smoothie_bowl", "t_start": 39.0, "t_dur": 3.2, "type": "outside_in_pen", "depth": 1},
    {"asset": "r4_03_smoothie_tall_glass_straw", "t_start": 40.5, "t_dur": 1.5, "type": "organic_grow", "depth": 2},
    {"asset": "r4_04_cubed_dragon_fruit_plate", "t_start": 41.5, "t_dur": 1.2, "type": "jelly_pop", "depth": 3},
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

# 4. Camera Trajectory Function (8-Zone Navigation, 45.0s Duration)
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

    # Zone 1A (0.0 -> 5.2s)
    if t < 5.2:
        return z1A[0], z1A[1], zoom

    # Pan 1A -> 1B (5.2 -> 6.2s)
    elif t < 6.2:
        p = smootherstep((t - 5.2) / 1.0)
        x = z1A[0] + (z1B[0] - z1A[0]) * p
        y = z1A[1] + (z1B[1] - z1A[1]) * p
        return x, y, zoom

    # Zone 1B (6.2 -> 11.2s)
    elif t < 11.2:
        return z1B[0], z1B[1], zoom

    # Transition 1B -> 2A (11.2 -> 12.2s)
    elif t < 12.2:
        p = smootherstep((t - 11.2) / 1.0)
        x = z1B[0] + (z2A[0] - z1B[0]) * p
        y = z1B[1] + (z2A[1] - z1B[1]) * p
        return x, y, zoom

    # Zone 2A (12.2 -> 16.0s)
    elif t < 16.0:
        return z2A[0], z2A[1], zoom

    # Pan 2A -> 2B (16.0 -> 17.0s)
    elif t < 17.0:
        p = smootherstep((t - 16.0) / 1.0)
        x = z2A[0] + (z2B[0] - z2A[0]) * p
        y = z2A[1] + (z2B[1] - z2A[1]) * p
        return x, y, zoom

    # Zone 2B (17.0 -> 20.6s)
    elif t < 20.6:
        return z2B[0], z2B[1], zoom

    # Transition 2B -> 3A (20.6 -> 21.6s)
    elif t < 21.6:
        p = smootherstep((t - 20.6) / 1.0)
        x = z2B[0] + (z3A[0] - z2B[0]) * p
        y = z2B[1] + (z3A[1] - z2B[1]) * p
        return x, y, zoom

    # Zone 3A (21.6 -> 26.5s)
    elif t < 26.5:
        return z3A[0], z3A[1], zoom

    # Pan 3A -> 3B (26.5 -> 27.5s)
    elif t < 27.5:
        p = smootherstep((t - 26.5) / 1.0)
        x = z3A[0] + (z3B[0] - z3A[0]) * p
        y = z3A[1] + (z3B[1] - z3A[1]) * p
        return x, y, zoom

    # Zone 3B (27.5 -> 32.7s)
    elif t < 32.7:
        return z3B[0], z3B[1], zoom

    # Transition 3B -> 4A (32.7 -> 33.7s)
    elif t < 33.7:
        p = smootherstep((t - 32.7) / 1.0)
        x = z3B[0] + (z4A[0] - z3B[0]) * p
        y = z3B[1] + (z4A[1] - z3B[1]) * p
        return x, y, zoom

    # Zone 4A (33.7 -> 38.0s)
    elif t < 38.0:
        return z4A[0], z4A[1], zoom

    # Pan 4A -> 4B (38.0 -> 39.0s)
    elif t < 39.0:
        p = smootherstep((t - 38.0) / 1.0)
        x = z4A[0] + (z4B[0] - z4A[0]) * p
        y = z4A[1] + (z4B[1] - z4A[1]) * p
        return x, y, zoom

    # Zone 4B (Finale steady hold on modern pitaya creations, zero outro zoom-out)
    else:
        return z4B[0], z4B[1], zoom

# 5. Render Video (45.0s Duration)
duration_sec = 45.0
final_video = engine.render_section(hero_configs, elements_staging, camera_trajectory, duration_sec)

# 6. Extract Preview Frames
preview_dir = os.path.join(section_dir, "preview_frames")
os.makedirs(preview_dir, exist_ok=True)
preview_times = [2.0, 4.5, 8.5, 14.0, 18.5, 24.0, 29.5, 35.5, 41.0, 44.0]
for idx, pt in enumerate(preview_times):
    p_img = os.path.join(preview_dir, f"frame_{idx+1:02d}_{pt:.1f}s.jpg")
    cmd = [
        "ffmpeg", "-y", "-ss", str(pt), "-i", final_video,
        "-vframes", "1", "-q:v", "2", p_img
    ]
    subprocess.run(cmd, capture_output=True)

print("Section 09 Dragon Fruit completed successfully with true outside-in inking and tight narration sync!")

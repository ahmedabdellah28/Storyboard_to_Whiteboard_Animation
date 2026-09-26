import os
import sys
import json
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

section_dir = os.path.join(ROOT_DIR, "sections/07_dates")
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

# 2. Define Hero Inking configs: (asset_id, start_time, duration)
# All hero elements use True Outside-In Contour Inking
hero_configs = [
    ("r1_01_dates_bowl_hero", 0.5, 3.0),
    ("r1_06_ancient_papyrus_scroll", 12.5, 3.5),
    ("r2_03_energy_runner_bolt", 24.5, 3.2),
    ("r2_05_palm_growth_hourglass", 31.8, 3.2),
    ("r3_02_medjool_caramel_cut", 38.5, 3.8),
    ("r3_04_woven_baskets_saddlebag", 47.8, 3.2),
    ("r4_01_ancient_seed_loupe", 52.8, 3.8),
    ("r4_04_resurrected_green_palm", 65.0, 3.8),
]

# 3. Elements Staging List (Tight, continuous pacing with zero awkward silences)
staging = [
    # Row 1A
    {"asset": "r1_01_dates_bowl_hero", "t_start": 0.5, "t_dur": 3.0, "type": "outside_in_pen", "depth": 1},
    {"asset": "r1_02_mesopotamia_cradle", "t_start": 3.8, "t_dur": 1.0, "type": "slide_down", "depth": 2},
    {"asset": "r1_03_date_palm_tree", "t_start": 5.2, "t_dur": 1.2, "type": "organic_grow", "depth": 3},

    # Row 1B
    {"asset": "r1_04_ancient_cuneiform_tablet", "t_start": 9.2, "t_dur": 0.8, "type": "jelly_pop", "depth": 1},
    {"asset": "r1_05_ancient_palm_coin", "t_start": 10.8, "t_dur": 0.8, "type": "pulse_pop", "depth": 2},
    {"asset": "r1_06_ancient_papyrus_scroll", "t_start": 12.5, "t_dur": 3.5, "type": "outside_in_pen", "depth": 3},

    # Row 2A
    {"asset": "r2_01_palm_wreath_prosperity", "t_start": 21.8, "t_dur": 1.0, "type": "jelly_pop", "depth": 1},
    {"asset": "r2_02_dates_sugar_cubes", "t_start": 23.0, "t_dur": 1.0, "type": "slide_down", "depth": 2},
    {"asset": "r2_03_energy_runner_bolt", "t_start": 24.5, "t_dur": 3.2, "type": "outside_in_pen", "depth": 3},

    # Row 2B
    {"asset": "r2_04_palm_orchard_plantation", "t_start": 30.0, "t_dur": 1.2, "type": "organic_grow", "depth": 1},
    {"asset": "r2_05_palm_growth_hourglass", "t_start": 31.8, "t_dur": 3.2, "type": "outside_in_pen", "depth": 2},

    # Row 3A
    {"asset": "r3_01_date_varieties_lineup", "t_start": 36.8, "t_dur": 1.2, "type": "slide_down", "depth": 1},
    {"asset": "r3_02_medjool_caramel_cut", "t_start": 38.5, "t_dur": 3.8, "type": "outside_in_pen", "depth": 2},

    # Row 3B
    {"asset": "r3_03_desert_traveler_camel", "t_start": 46.0, "t_dur": 1.2, "type": "slide_down", "depth": 1},
    {"asset": "r3_04_woven_baskets_saddlebag", "t_start": 47.8, "t_dur": 3.2, "type": "outside_in_pen", "depth": 2},

    # Row 4A
    {"asset": "r4_01_ancient_seed_loupe", "t_start": 52.8, "t_dur": 3.8, "type": "outside_in_pen", "depth": 1},
    {"asset": "r4_02_seed_germination_pots", "t_start": 57.0, "t_dur": 1.8, "type": "organic_grow", "depth": 2},

    # Row 4B
    {"asset": "r4_03_ancient_desert_seed_ruins", "t_start": 63.2, "t_dur": 1.5, "type": "slide_down", "depth": 1},
    {"asset": "r4_04_resurrected_green_palm", "t_start": 65.0, "t_dur": 3.8, "type": "outside_in_pen", "depth": 2},
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

# 4. Camera Trajectory Function (8-Zone Navigation, 72.0s Duration)
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

    # Zone 1A (0.0 -> 7.7s)
    if t < 7.7:
        return z1A[0], z1A[1], zoom

    # Pan 1A -> 1B (7.7 -> 8.9s)
    elif t < 8.9:
        p = smootherstep((t - 7.7) / 1.2)
        x = z1A[0] + (z1B[0] - z1A[0]) * p
        y = z1A[1] + (z1B[1] - z1A[1]) * p
        return x, y, zoom

    # Zone 1B (8.9 -> 20.5s)
    elif t < 20.5:
        return z1B[0], z1B[1], zoom

    # Transition 1B -> 2A (20.5 -> 21.7s)
    elif t < 21.7:
        p = smootherstep((t - 20.5) / 1.2)
        x = z1B[0] + (z2A[0] - z1B[0]) * p
        y = z1B[1] + (z2A[1] - z1B[1]) * p
        return x, y, zoom

    # Zone 2A (21.7 -> 28.5s)
    elif t < 28.5:
        return z2A[0], z2A[1], zoom

    # Pan 2A -> 2B (28.5 -> 29.7s)
    elif t < 29.7:
        p = smootherstep((t - 28.5) / 1.2)
        x = z2A[0] + (z2B[0] - z2A[0]) * p
        y = z2A[1] + (z2B[1] - z2A[1]) * p
        return x, y, zoom

    # Zone 2B (29.7 -> 35.5s)
    elif t < 35.5:
        return z2B[0], z2B[1], zoom

    # Transition 2B -> 3A (35.5 -> 36.7s)
    elif t < 36.7:
        p = smootherstep((t - 35.5) / 1.2)
        x = z2B[0] + (z3A[0] - z2B[0]) * p
        y = z2B[1] + (z3A[1] - z2B[1]) * p
        return x, y, zoom

    # Zone 3A (36.7 -> 44.5s)
    elif t < 44.5:
        return z3A[0], z3A[1], zoom

    # Pan 3A -> 3B (44.5 -> 45.7s)
    elif t < 45.7:
        p = smootherstep((t - 44.5) / 1.2)
        x = z3A[0] + (z3B[0] - z3A[0]) * p
        y = z3A[1] + (z3B[1] - z3A[1]) * p
        return x, y, zoom

    # Zone 3B (45.7 -> 51.5s)
    elif t < 51.5:
        return z3B[0], z3B[1], zoom

    # Transition 3B -> 4A (51.5 -> 52.7s)
    elif t < 52.7:
        p = smootherstep((t - 51.5) / 1.2)
        x = z3B[0] + (z4A[0] - z3B[0]) * p
        y = z3B[1] + (z4A[1] - z3B[1]) * p
        return x, y, zoom

    # Zone 4A (52.7 -> 61.8s)
    elif t < 61.8:
        return z4A[0], z4A[1], zoom

    # Pan 4A -> 4B (61.8 -> 63.0s)
    elif t < 63.0:
        p = smootherstep((t - 61.8) / 1.2)
        x = z4A[0] + (z4B[0] - z4A[0]) * p
        y = z4A[1] + (z4B[1] - z4A[1]) * p
        return x, y, zoom

    # Zone 4B (Finale steady hold on resurrected palm, zero outro zoom-out)
    else:
        return z4B[0], z4B[1], zoom

# 5. Render Video (72.0s Duration)
duration_sec = 72.0
final_video = engine.render_section(hero_configs, elements_staging, camera_trajectory, duration_sec)

# 6. Extract Preview Frames
import subprocess
preview_dir = os.path.join(section_dir, "preview_frames")
os.makedirs(preview_dir, exist_ok=True)
preview_times = [2.0, 6.0, 15.0, 26.0, 33.0, 41.0, 49.0, 56.0, 68.0]
for idx, pt in enumerate(preview_times):
    p_img = os.path.join(preview_dir, f"frame_{idx+1:02d}_{pt:.1f}s.jpg")
    cmd = [
        "ffmpeg", "-y", "-ss", str(pt), "-i", final_video,
        "-vframes", "1", "-q:v", "2", p_img
    ]
    subprocess.run(cmd, capture_output=True)

print("Section 07 Dates completed successfully with true outside-in inking and tight narration sync!")

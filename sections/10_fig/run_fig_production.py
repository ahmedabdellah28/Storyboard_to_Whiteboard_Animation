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

section_dir = os.path.join(ROOT_DIR, "sections/10_fig")
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
# All hero elements use True Outside-In Contour Inking (Boundary Layer Infill)
hero_configs = [
    ("r1_01_fig_hero_fresh_cut", 0.5, 3.5),
    ("r1_05_fig_older_than_grains_comparison", 12.5, 3.5),
    ("r2_01_fig_magnified_internal_flowers", 19.3, 3.5),
    ("r2_05_dried_figs_platter", 31.2, 3.3),
    ("r3_02_fig_wasp_illustrated", 38.2, 3.3),
    ("r4_01_fig_varieties_lineup", 52.4, 3.6),
    ("r4_03_mature_fruiting_fig_tree", 60.0, 3.8),
]

# 3. Elements Staging List (Tight, continuous pacing with zero dead silences)
staging = [
    # Row 1A: The ancient fruit & neolithic origins
    {"asset": "r1_01_fig_hero_fresh_cut", "t_start": 0.5, "t_dur": 3.5, "type": "outside_in_pen", "depth": 1},
    {"asset": "r1_02_ancient_prehistoric_gatherers", "t_start": 4.2, "t_dur": 1.4, "type": "organic_grow", "depth": 2},
    {"asset": "r1_03_jordan_valley_neolithic_village", "t_start": 6.2, "t_dur": 1.5, "type": "slide_down", "depth": 1},

    # Row 1B: Historical stone carvings & older than grains
    {"asset": "r1_04_ancient_stone_carvings_fig", "t_start": 10.9, "t_dur": 1.4, "type": "pulse_pop", "depth": 1},
    {"asset": "r1_05_fig_older_than_grains_comparison", "t_start": 12.5, "t_dur": 3.5, "type": "outside_in_pen", "depth": 2},

    # Row 2A: The botanical surprise - inverted flower structure
    {"asset": "r2_01_fig_magnified_internal_flowers", "t_start": 19.3, "t_dur": 3.5, "type": "outside_in_pen", "depth": 1},
    {"asset": "r2_02_botanical_syconium_florets_loupe", "t_start": 23.0, "t_dur": 1.5, "type": "organic_grow", "depth": 2},

    # Row 2B: Crunchy seeds & delicious dried figs
    {"asset": "r2_03_crunchy_seeds_florets_detail", "t_start": 27.4, "t_dur": 1.3, "type": "jelly_pop", "depth": 1},
    {"asset": "r2_04_trio_fresh_figs_leaf", "t_start": 29.0, "t_dur": 1.4, "type": "organic_grow", "depth": 2},
    {"asset": "r2_05_dried_figs_platter", "t_start": 31.2, "t_dur": 3.3, "type": "outside_in_pen", "depth": 3},

    # Row 3A: Symbiosis with the fig wasp
    {"asset": "r3_01_fig_ostiole_wasp_entering", "t_start": 36.6, "t_dur": 1.4, "type": "slide_down", "depth": 1},
    {"asset": "r3_02_fig_wasp_illustrated", "t_start": 38.2, "t_dur": 3.3, "type": "outside_in_pen", "depth": 2},

    # Row 3B: Enzyme breakdown & modern commercial varieties
    {"asset": "r3_03_wasp_inside_fig_interior", "t_start": 43.9, "t_dur": 1.4, "type": "organic_grow", "depth": 1},
    {"asset": "r3_04_fig_enzymes_breakdown_diagram", "t_start": 45.6, "t_dur": 1.5, "type": "slide_down", "depth": 2},
    {"asset": "r3_05_commercial_fig_no_wasp_sign", "t_start": 47.5, "t_dur": 1.5, "type": "pulse_pop", "depth": 3},

    # Row 4A: Global varieties & sapling
    {"asset": "r4_01_fig_varieties_lineup", "t_start": 52.4, "t_dur": 3.6, "type": "outside_in_pen", "depth": 1},
    {"asset": "r4_02_fig_sapling_soil", "t_start": 56.5, "t_dur": 1.4, "type": "organic_grow", "depth": 2},

    # Row 4B: Mature fruiting tree & branch harvest (Finale hold)
    {"asset": "r4_03_mature_fruiting_fig_tree", "t_start": 60.0, "t_dur": 3.8, "type": "outside_in_pen", "depth": 1},
    {"asset": "r4_04_fig_branch_ripe_unripe", "t_start": 64.0, "t_dur": 1.5, "type": "organic_grow", "depth": 2},
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

# 4. Camera Trajectory Function (8-Zone Navigation, 68.0s Duration)
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

    # Zone 1A (0.0 -> 9.5s)
    if t < 9.5:
        return z1A[0], z1A[1], zoom

    # Pan 1A -> 1B (9.5 -> 10.7s)
    elif t < 10.7:
        p = smootherstep((t - 9.5) / 1.2)
        x = z1A[0] + (z1B[0] - z1A[0]) * p
        y = z1A[1] + (z1B[1] - z1A[1]) * p
        return x, y, zoom

    # Zone 1B (10.7 -> 18.2s)
    elif t < 18.2:
        return z1B[0], z1B[1], zoom

    # Transition 1B -> 2A (18.2 -> 19.3s)
    elif t < 19.3:
        p = smootherstep((t - 18.2) / 1.1)
        x = z1B[0] + (z2A[0] - z1B[0]) * p
        y = z1B[1] + (z2A[1] - z1B[1]) * p
        return x, y, zoom

    # Zone 2A (19.3 -> 26.0s)
    elif t < 26.0:
        return z2A[0], z2A[1], zoom

    # Pan 2A -> 2B (26.0 -> 27.2s)
    elif t < 27.2:
        p = smootherstep((t - 26.0) / 1.2)
        x = z2A[0] + (z2B[0] - z2A[0]) * p
        y = z2A[1] + (z2B[1] - z2A[1]) * p
        return x, y, zoom

    # Zone 2B (27.2 -> 35.5s)
    elif t < 35.5:
        return z2B[0], z2B[1], zoom

    # Transition 2B -> 3A (35.5 -> 36.6s)
    elif t < 36.6:
        p = smootherstep((t - 35.5) / 1.1)
        x = z2B[0] + (z3A[0] - z2B[0]) * p
        y = z2B[1] + (z3A[1] - z2B[1]) * p
        return x, y, zoom

    # Zone 3A (36.6 -> 42.5s)
    elif t < 42.5:
        return z3A[0], z3A[1], zoom

    # Pan 3A -> 3B (42.5 -> 43.7s)
    elif t < 43.7:
        p = smootherstep((t - 42.5) / 1.2)
        x = z3A[0] + (z3B[0] - z3A[0]) * p
        y = z3A[1] + (z3B[1] - z3A[1]) * p
        return x, y, zoom

    # Zone 3B (43.7 -> 51.3s)
    elif t < 51.3:
        return z3B[0], z3B[1], zoom

    # Transition 3B -> 4A (51.3 -> 52.4s)
    elif t < 52.4:
        p = smootherstep((t - 51.3) / 1.1)
        x = z3B[0] + (z4A[0] - z3B[0]) * p
        y = z3B[1] + (z4A[1] - z3B[1]) * p
        return x, y, zoom

    # Zone 4A (52.4 -> 58.8s)
    elif t < 58.8:
        return z4A[0], z4A[1], zoom

    # Pan 4A -> 4B (58.8 -> 60.0s)
    elif t < 60.0:
        p = smootherstep((t - 58.8) / 1.2)
        x = z4A[0] + (z4B[0] - z4A[0]) * p
        y = z4A[1] + (z4B[1] - z4A[1]) * p
        return x, y, zoom

    # Zone 4B (Finale steady hold on mature fig tree, ZERO outro zoom-out)
    else:
        return z4B[0], z4B[1], zoom

# 5. Render Video (68.0s Duration)
duration_sec = 68.0
final_video = engine.render_section(hero_configs, elements_staging, camera_trajectory, duration_sec)

# 6. Extract Preview Frames
preview_dir = os.path.join(section_dir, "preview_frames")
os.makedirs(preview_dir, exist_ok=True)
preview_times = [2.0, 5.0, 13.5, 17.0, 21.0, 32.5, 39.5, 47.0, 54.0, 62.0, 66.5]
for idx, pt in enumerate(preview_times):
    p_img = os.path.join(preview_dir, f"frame_{idx+1:02d}_{pt:.1f}s.jpg")
    cmd = [
        "ffmpeg", "-y", "-ss", str(pt), "-i", final_video,
        "-vframes", "1", "-q:v", "2", p_img
    ]
    subprocess.run(cmd, capture_output=True)

print("Section 10 Fig completed successfully with true outside-in inking and tight narration sync!")

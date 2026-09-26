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

section_dir = os.path.join(ROOT_DIR, "sections/11_jabuticaba")
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
    ("r1_01_jabuticaba_hero_cluster", 0.5, 3.5),
    ("r1_04_trunk_berries_macro", 11.8, 3.2),
    ("r2_01_jabuticaba_trio_cut", 17.1, 3.5),
    ("r2_03_popping_juice_burst_sequence", 25.8, 3.2),
    ("r3_01_branch_ripening_gradient", 33.8, 3.5),
    ("r3_05_brazil_map_native_origin", 46.2, 3.2),
    ("r4_05_growth_fruiting_tree_stage", 57.2, 3.5),
    ("r4_06_basket_harvest_platter", 61.0, 3.3),
]

# 3. Elements Staging List (Tight, continuous pacing with zero dead silences)
staging = [
    # Row 1A: Hero cluster with cut halves & full tree
    {"asset": "r1_01_jabuticaba_hero_cluster", "t_start": 0.5, "t_dur": 3.5, "type": "outside_in_pen", "depth": 1},
    {"asset": "r1_02_jabuticaba_tree_full", "t_start": 4.5, "t_dur": 1.5, "type": "organic_grow", "depth": 2},

    # Row 1B: Cauliflory trunk fruiting, macro berries & bark blossoms
    {"asset": "r1_03_trunk_covered_fruits", "t_start": 10.2, "t_dur": 1.4, "type": "slide_down", "depth": 1},
    {"asset": "r1_04_trunk_berries_macro", "t_start": 11.8, "t_dur": 3.2, "type": "outside_in_pen", "depth": 2},
    {"asset": "r1_05_trunk_white_flowers_macro", "t_start": 14.5, "t_dur": 1.5, "type": "organic_grow", "depth": 3},

    # Row 2A: Trio cut fruit & traditional grapes comparison
    {"asset": "r2_01_jabuticaba_trio_cut", "t_start": 17.1, "t_dur": 3.5, "type": "outside_in_pen", "depth": 1},
    {"asset": "r2_02_traditional_grapes_comparison", "t_start": 21.0, "t_dur": 1.5, "type": "organic_grow", "depth": 2},

    # Row 2B: Bursting popping sequence, slices & hand holding berry
    {"asset": "r2_03_popping_juice_burst_sequence", "t_start": 25.8, "t_dur": 3.2, "type": "outside_in_pen", "depth": 1},
    {"asset": "r2_04_slices_cross_sections", "t_start": 29.2, "t_dur": 1.4, "type": "jelly_pop", "depth": 2},
    {"asset": "r2_05_hand_holding_single_berry", "t_start": 30.8, "t_dur": 1.4, "type": "pulse_pop", "depth": 3},

    # Row 3A: Ripening branch & spoilage progression
    {"asset": "r3_01_branch_ripening_gradient", "t_start": 33.8, "t_dur": 3.5, "type": "outside_in_pen", "depth": 1},
    {"asset": "r3_02_spoilage_sequence_decay", "t_start": 37.8, "t_dur": 1.5, "type": "slide_down", "depth": 2},

    # Row 3B: 3-day calendar, export crates prohibited & Brazil origin map
    {"asset": "r3_03_calendar_rapid_spoilage_3days", "t_start": 42.8, "t_dur": 1.4, "type": "pulse_pop", "depth": 1},
    {"asset": "r3_04_export_crates_airplane_prohibited", "t_start": 44.5, "t_dur": 1.5, "type": "slide_down", "depth": 2},
    {"asset": "r3_05_brazil_map_native_origin", "t_start": 46.2, "t_dur": 3.2, "type": "outside_in_pen", "depth": 3},

    # Row 4A: Growth timeline stages from sprout to mature tree
    {"asset": "r4_01_growth_sprout_stage", "t_start": 50.6, "t_dur": 1.0, "type": "organic_grow", "depth": 1},
    {"asset": "r4_02_growth_sapling_stage", "t_start": 51.8, "t_dur": 1.0, "type": "organic_grow", "depth": 2},
    {"asset": "r4_03_growth_bushy_juvenile_stage", "t_start": 53.0, "t_dur": 1.0, "type": "organic_grow", "depth": 3},
    {"asset": "r4_04_growth_mature_tree_stage", "t_start": 54.2, "t_dur": 1.2, "type": "organic_grow", "depth": 4},

    # Row 4B: Loaded fruiting tree, overflowing basket & tall glass (Finale Hold)
    {"asset": "r4_05_growth_fruiting_tree_stage", "t_start": 57.2, "t_dur": 3.5, "type": "outside_in_pen", "depth": 1},
    {"asset": "r4_06_basket_harvest_platter", "t_start": 61.0, "t_dur": 3.3, "type": "outside_in_pen", "depth": 2},
    {"asset": "r4_07_fresh_juice_tall_glass", "t_start": 64.5, "t_dur": 1.5, "type": "organic_grow", "depth": 3},
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

    # Zone 1A (0.0 -> 8.8s)
    if t < 8.8:
        return z1A[0], z1A[1], zoom

    # Pan 1A -> 1B (8.8 -> 10.0s)
    elif t < 10.0:
        p = smootherstep((t - 8.8) / 1.2)
        x = z1A[0] + (z1B[0] - z1A[0]) * p
        y = z1A[1] + (z1B[1] - z1A[1]) * p
        return x, y, zoom

    # Zone 1B (10.0 -> 16.0s)
    elif t < 16.0:
        return z1B[0], z1B[1], zoom

    # Transition 1B -> 2A (16.0 -> 17.1s)
    elif t < 17.1:
        p = smootherstep((t - 16.0) / 1.1)
        x = z1B[0] + (z2A[0] - z1B[0]) * p
        y = z1B[1] + (z2A[1] - z1B[1]) * p
        return x, y, zoom

    # Zone 2A (17.1 -> 24.5s)
    elif t < 24.5:
        return z2A[0], z2A[1], zoom

    # Pan 2A -> 2B (24.5 -> 25.7s)
    elif t < 25.7:
        p = smootherstep((t - 24.5) / 1.2)
        x = z2A[0] + (z2B[0] - z2A[0]) * p
        y = z2A[1] + (z2B[1] - z2A[1]) * p
        return x, y, zoom

    # Zone 2B (25.7 -> 32.7s)
    elif t < 32.7:
        return z2B[0], z2B[1], zoom

    # Transition 2B -> 3A (32.7 -> 33.8s)
    elif t < 33.8:
        p = smootherstep((t - 32.7) / 1.1)
        x = z2B[0] + (z3A[0] - z2B[0]) * p
        y = z2B[1] + (z3A[1] - z2B[1]) * p
        return x, y, zoom

    # Zone 3A (33.8 -> 41.5s)
    elif t < 41.5:
        return z3A[0], z3A[1], zoom

    # Pan 3A -> 3B (41.5 -> 42.7s)
    elif t < 42.7:
        p = smootherstep((t - 41.5) / 1.2)
        x = z3A[0] + (z3B[0] - z3A[0]) * p
        y = z3A[1] + (z3B[1] - z3A[1]) * p
        return x, y, zoom

    # Zone 3B (42.7 -> 49.5s)
    elif t < 49.5:
        return z3B[0], z3B[1], zoom

    # Transition 3B -> 4A (49.5 -> 50.6s)
    elif t < 50.6:
        p = smootherstep((t - 49.5) / 1.1)
        x = z3B[0] + (z4A[0] - z3B[0]) * p
        y = z3B[1] + (z4A[1] - z3B[1]) * p
        return x, y, zoom

    # Zone 4A (50.6 -> 56.0s)
    elif t < 56.0:
        return z4A[0], z4A[1], zoom

    # Pan 4A -> 4B (56.0 -> 57.2s)
    elif t < 57.2:
        p = smootherstep((t - 56.0) / 1.2)
        x = z4A[0] + (z4B[0] - z4A[0]) * p
        y = z4A[1] + (z4B[1] - z4A[1]) * p
        return x, y, zoom

    # Zone 4B (Finale Steady Hold, ZERO OUTRO ZOOM-OUT!)
    else:
        return z4B[0], z4B[1], zoom

# 5. Duration and Audio Setup
duration_sec = 68.0

# 6. Auto-Generate SFX from Staging (PERFECT SYNC — no manual SFX cue times!)
camera_pans = [8.8, 16.0, 24.5, 32.7, 41.5, 49.5, 56.0]  # Zone/row transition times
sfx_cues = engine.generate_sfx_from_staging(elements_staging, camera_pans=camera_pans)
print(f"\n[SFX] Auto-generated {len(sfx_cues)} SFX cues from staging (100% sync guaranteed):")
for t, sfx_type, gain in sfx_cues:
    print(f"  {t:6.2f}s  {sfx_type:8s}  gain={gain:.2f}")

# 7. Re-Mix Master Audio with Auto-Generated SFX
voiceover_path = os.path.join(section_dir, "voiceover.wav")
master_audio = engine.mix_master_audio(voiceover_path, sfx_cues, target_duration_s=duration_sec)
print(f"\n[Audio] Master audio re-mixed with synced SFX: {master_audio}")

# 8. Render Video (68.0s Duration)
final_video = engine.render_section(hero_configs, elements_staging, camera_trajectory, duration_sec)

# 8. Extract Preview Frames
preview_dir = os.path.join(section_dir, "preview_frames")
os.makedirs(preview_dir, exist_ok=True)
preview_times = [2.0, 5.5, 12.5, 15.0, 19.0, 27.0, 35.0, 44.0, 48.0, 58.0, 62.5, 66.5]
for idx, pt in enumerate(preview_times):
    p_img = os.path.join(preview_dir, f"frame_{idx+1:02d}_{pt:.1f}s.jpg")
    cmd = [
        "ffmpeg", "-y", "-ss", str(pt), "-i", final_video,
        "-vframes", "1", "-q:v", "2", p_img
    ]
    subprocess.run(cmd, capture_output=True)

print("Section 11 Jabuticaba completed with authentic outside-in inking and auto-synced SFX!")

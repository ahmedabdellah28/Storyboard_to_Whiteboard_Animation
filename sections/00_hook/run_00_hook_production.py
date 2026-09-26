import os
import sys
import json
import wave
import shutil
import cv2
import numpy as np

# Safe console output
sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.dynamic_section_engine import DynamicSectionEngine, smootherstep

SEC_DIR = os.path.join(ROOT_DIR, "sections", "00_hook")
VOICEOVER_PATH = os.path.join(SEC_DIR, "voiceover.wav")
LAYOUT_PATH = os.path.join(SEC_DIR, "placed_elements_layout.json")

# Measure Voiceover Duration
with wave.open(VOICEOVER_PATH, 'rb') as wf:
    DURATION_SEC = wf.getnframes() / float(wf.getframerate())

print(f"🎬 Starting Section 00 Production (Pure Horizontal Tracking, Duration: {DURATION_SEC:.2f}s)")

# Load Layout
with open(LAYOUT_PATH, "r", encoding="utf-8") as f:
    layout_data = json.load(f)

placed_elements = layout_data["elements"]
zones = layout_data["zones"]
FIXED_Y = layout_data.get("fixed_y", 800.0)
CAM_ZOOM = layout_data.get("cam_zoom", 0.58)

# Flatten elements dict for quick lookup
elements_by_aid = {}
for z_name, elems in placed_elements.items():
    for el in elems:
        elements_by_aid[el["aid"]] = el

# Helper to get cam X for each zone
def get_zone_cam_x(z_name):
    return zones[z_name]["cam_pos"][0]

# Pure Horizontal Camera Pans (X-only, Y is strictly constant)
# (t_start, t_end, from_cam_x, to_cam_x)
CAM_PANS = [
    # Zone 1A -> Zone 1B (after pause on Zone 1A)
    (4.6, 5.2, get_zone_cam_x("zone_1A"), get_zone_cam_x("zone_1B")),
    # Zone 1B -> Zone 2A (after pause on Zone 1B)
    (7.9, 8.5, get_zone_cam_x("zone_1B"), get_zone_cam_x("zone_2A")),
    # Zone 2A -> Zone 2B (after pause on Zone 2A)
    (11.8, 12.4, get_zone_cam_x("zone_2A"), get_zone_cam_x("zone_2B")),
    # Zone 2B -> Zone 3A (after long hold on mansion)
    (17.0, 17.5, get_zone_cam_x("zone_2B"), get_zone_cam_x("zone_3A")),
    # Zone 3A -> Zone 3B
    (18.3, 18.7, get_zone_cam_x("zone_3A"), get_zone_cam_x("zone_3B")),
    # Zone 3B -> Zone 4A (after pause on 24h timeline)
    (20.2, 20.7, get_zone_cam_x("zone_3B"), get_zone_cam_x("zone_4A")),
    # Zone 4A -> Zone 4B
    (22.5, 23.0, get_zone_cam_x("zone_4A"), get_zone_cam_x("zone_4B")),
    # Zone 4B -> Zone 5A (after pause on problems)
    (25.4, 26.0, get_zone_cam_x("zone_4B"), get_zone_cam_x("zone_5A")),
    # Zone 5A -> Zone 5B (after hold on billionaire car)
    (29.4, 30.0, get_zone_cam_x("zone_5A"), get_zone_cam_x("zone_5B")),
]

def get_camera_state(t):
    """100% PURE HORIZONTAL CAMERA: Y is strictly fixed at FIXED_Y."""
    if t < CAM_PANS[0][0]:
        return (CAM_PANS[0][2], FIXED_Y, CAM_ZOOM)

    for i, (t_start, t_end, x_from, x_to) in enumerate(CAM_PANS):
        if t < t_start:
            return (x_from, FIXED_Y, CAM_ZOOM)
        elif t < t_end:
            p = smootherstep((t - t_start) / (t_end - t_start))
            cx = x_from + (x_to - x_from) * p
            return (cx, FIXED_Y, CAM_ZOOM)

    # Hold on final Zone 5B until the end
    final_x = CAM_PANS[-1][3]
    return (final_x, FIXED_Y, CAM_ZOOM)

# Element Staging with Speech Pause Holds
staging_specs = [
    # Zone 1A (0.0s - 4.6s) -> Holds 4.1s - 4.6s
    ("r1_01_waking_bed",        0.0, 1.4, "outside_in_pen", 5),
    ("r1_02_sad_sitting",       1.1, 0.9, "slide_down",     4),
    ("r1_03_no_job_fly_gym",    2.1, 1.0, "jelly_pop",      4),

    # Zone 1B (5.2s - 7.9s) -> Holds 7.2s - 7.9s
    ("r1_04_city_dawn",         5.2, 1.2, "outside_in_pen", 5),
    ("r1_05_crowd_safety",      6.3, 1.0, "jelly_pop",      4),

    # Zone 2A (8.5s - 11.8s) -> Holds 11.2s - 11.8s
    ("r2_01_homeless_sidewalk", 8.5, 0.9, "jelly_pop",      4),
    ("r2_02_small_room",        9.4, 0.9, "slide_down",     4),
    ("r2_03_neat_apartment",   10.4, 0.9, "slide_up",       4),

    # Zone 2B (12.4s - 17.0s) -> Holds 15.8s - 17.0s on Mansion
    ("r2_04_comfortable_room", 12.4, 0.9, "slide_down",     4),
    ("r2_05_luxury_suite",     13.4, 0.9, "slide_up",       4),
    ("r2_06_mansion_staff",    14.3, 1.5, "outside_in_pen", 5),

    # Zone 3A (17.5s - 18.3s)
    ("r3_01_stretching_man",   17.5, 0.8, "jelly_pop",      4),

    # Zone 3B (18.7s - 20.2s) -> Holds 19.8s - 20.2s on Timeline
    ("r3_02_timeline_24h",     18.7, 1.1, "outside_in_pen", 5),

    # Zone 4A (20.7s - 22.5s)
    ("r4_01_time_clock",       20.7, 1.0, "outside_in_pen", 5),
    ("r4_02_money_cash",       21.6, 0.9, "jelly_pop",      4),

    # Zone 4B (23.0s - 25.4s) -> Holds 24.8s - 25.4s on Problems
    ("r4_03_health_gym",       23.0, 0.9, "pulse_pop",     4),
    ("r4_04_problems_mind",    23.8, 1.0, "jelly_pop",      4),

    # Zone 5A (26.0s - 29.4s) -> Holds 28.6s - 29.4s on Billionaire Car
    ("r5_01_homeless_man",      26.0, 0.8, "slide_down",     4),
    ("r5_02_billionaire_car",   26.8, 1.8, "outside_in_pen", 5),

    # Zone 5B (30.0s - 36.31s) -> Holds 32.6s - 36.31s until end
    ("r5_03_thinking_question", 30.0, 1.1, "jelly_pop",      4),
    ("r5_04_rising_chart",      31.2, 1.4, "pulse_pop",     4),
]

elements_staging = []
hero_configs = []

for aid, t_st, t_dur, anim_type, depth in staging_specs:
    if aid not in elements_by_aid:
        print(f"⚠️ Warning: {aid} not in layout elements!")
        continue
    el = elements_by_aid[aid]
    elements_staging.append({
        'id': aid,
        'asset': aid,
        't_start': t_st,
        't_dur': t_dur,
        'type': anim_type,
        'pos': (el['x'], el['y']),
        'size': (el['w'], el['h']),
        'depth': depth
    })
    if anim_type == "outside_in_pen":
        hero_configs.append((aid, t_st, t_dur))

print(f"Staged {len(elements_staging)} elements ({len(hero_configs)} heroes for authentic outside-in inking).")

# Initialize Dynamic Section Engine
engine = DynamicSectionEngine(SEC_DIR)

# Generate SFX Cues & Mix Master Audio
print("\n" + "=" * 60)
print("🎵 GENERATING SYNCHRONIZED DUCKED AUDIO")
print("=" * 60)
pan_times = [p[0] for p in CAM_PANS]
sfx_cues = engine.generate_sfx_from_staging(elements_staging, camera_pans=pan_times)
print(f"Auto-generated {len(sfx_cues)} enriched SFX cues.")

master_audio_path = engine.mix_master_audio(VOICEOVER_PATH, sfx_cues, target_duration_s=DURATION_SEC)
print(f"✅ Master audio mixed: {master_audio_path}")

# Render 1080p Video (100% Horizontal Tracking)
print("\n" + "=" * 60)
print("🎥 RENDERING 1080P WHITEBOARD VIDEO (PURE HORIZONTAL TRACKING)")
print("=" * 60)
final_video_path = engine.render_section(
    hero_configs=hero_configs,
    elements_staging=elements_staging,
    camera_trajectory_fn=get_camera_state,
    duration_sec=DURATION_SEC
)

# Copy to Deliverables Folder
DELIVERABLES_DIR = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables", "sections")
os.makedirs(DELIVERABLES_DIR, exist_ok=True)

deliv_video = os.path.join(DELIVERABLES_DIR, "00_Hook_Whiteboard_1080p.mp4")
deliv_audio = os.path.join(DELIVERABLES_DIR, "00_Hook_Master_Audio.wav")

shutil.copyfile(final_video_path, deliv_video)
shutil.copyfile(master_audio_path, deliv_audio)

print("\n" + "=" * 80)
print("⭐ SECTION 00 DELIVERABLE SUCCESSFULLY PUBLISHED (PURE HORIZONTAL + PAUSE HOLDS)!")
print(f"  • Final Video : {deliv_video}")
print(f"  • Master Audio: {deliv_audio}")
print(f"  • Duration    : {DURATION_SEC:.2f}s")
print(f"  • Camera Mode : 100% Pure Horizontal Panning (Y = {FIXED_Y} constant)")
print("=" * 80 + "\n")

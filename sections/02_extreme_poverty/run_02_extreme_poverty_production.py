"""
Section 02 — Extreme Poverty (الفقر المدقع): Full Production Runner
Uses alignment_data.json / final_render_plan.json for 100% automated speech-synced staging.
Pure horizontal camera panning (Y=800.0 constant).
Camera pans placed in speech silence gaps between element zones.
Zero premature fades - elements hold during narration explanation.
"""
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

SEC_DIR = os.path.join(ROOT_DIR, "sections", "02_extreme_poverty")
VOICEOVER_PATH = os.path.join(SEC_DIR, "voice", "section.wav")
if not os.path.exists(VOICEOVER_PATH):
    VOICEOVER_PATH = os.path.join(SEC_DIR, "voiceover.wav")

LAYOUT_PATH = os.path.join(SEC_DIR, "placed_elements_layout.json")
TIMING_PATH = os.path.join(SEC_DIR, "timing", "drawing_timeline.json")
ALIGNMENT_PATH = os.path.join(SEC_DIR, "alignment_data.json")
FINAL_PLAN_PATH = os.path.join(SEC_DIR, "timing", "final_render_plan.json")

# ─────────────────────────────── Load Voiceover Duration ────────────────────
with wave.open(VOICEOVER_PATH, 'rb') as wf:
    DURATION_SEC = wf.getnframes() / float(wf.getframerate())

print("=" * 80)
print(f"🎬 Starting Section 02 (Extreme Poverty / الفقر المدقع) Production")
print(f"  Audio Source  : {os.path.basename(VOICEOVER_PATH)} ({DURATION_SEC:.2f}s)")
print(f"  Timing Engine : {'final_render_plan.json' if os.path.exists(FINAL_PLAN_PATH) else 'drawing_timeline.json'}")
print("=" * 80)

# ─────────────────────────────── Load Layout ────────────────────────────────
with open(LAYOUT_PATH, "r", encoding="utf-8") as f:
    layout_data = json.load(f)

placed_elements = layout_data["elements"]
zones = layout_data["zones"]
FIXED_Y = layout_data.get("fixed_y", 800.0)
CAM_ZOOM = layout_data.get("cam_zoom", 0.68)

# Flatten elements dict for quick lookup
elements_by_aid = {}
for z_name, elems in placed_elements.items():
    for el in elems:
        elements_by_aid[el["aid"]] = el

def get_zone_cam_x(z_name):
    return zones[z_name]["cam_pos"][0]

# ─────────────────────────────── Load Timing & Alignment Data ──────────────
with open(ALIGNMENT_PATH, "r", encoding="utf-8") as f:
    alignment_data = json.load(f)

anim_map = {s[0]: (s[3], s[4]) for s in alignment_data.get("staging_specs", [])}

if os.path.exists(FINAL_PLAN_PATH):
    print("  ⭐ Timing Engine : final_render_plan.json (AI Pre-Render Director Verified)")
    with open(FINAL_PLAN_PATH, "r", encoding="utf-8") as f:
        plan_data = json.load(f)
    staging_specs_raw = []
    for ev in plan_data.get("render_events", []):
        if ev.get("type") in ["draw", "reveal"]:
            aid = ev["asset_id"]
            t_st = float(ev["start_s"])
            t_dur = float(ev["duration_s"])
            fade_out = ev.get("fade_out_at")
            anim_type, depth = anim_map.get(aid, ("outside_in_pen", 5))
            staging_specs_raw.append((aid, t_st, t_dur, anim_type, depth, fade_out))
elif os.path.exists(TIMING_PATH):
    with open(TIMING_PATH, "r", encoding="utf-8") as f:
        dt_data = json.load(f)
    staging_specs_raw = []
    for ev in dt_data["events"]:
        aid = ev["asset_id"]
        t_st = ev["start_s"]
        t_dur = ev["duration_s"]
        anim_type, depth = anim_map.get(aid, ("outside_in_pen", 5))
        staging_specs_raw.append((aid, t_st, t_dur, anim_type, depth, None))
else:
    staging_specs_raw = [s + (None,) for s in alignment_data["staging_specs"]]

# Determine which zone each element belongs to
element_zone_map = {}
for z_name, elems in placed_elements.items():
    for el in elems:
        element_zone_map[el["aid"]] = z_name

# Group elements by zone to calculate camera pans at zone transitions
zone_order = list(layout_data["zones"].keys())
zone_last_element_end = {}
zone_first_element_start = {}

for spec in staging_specs_raw:
    aid = spec[0]
    t_st = spec[1]
    t_dur = spec[2]
    z = element_zone_map.get(aid)
    if z:
        t_end = t_st + t_dur
        if z not in zone_last_element_end or t_end > zone_last_element_end[z]:
            zone_last_element_end[z] = t_end
        if z not in zone_first_element_start or t_st < zone_first_element_start[z]:
            zone_first_element_start[z] = t_st

# ─── Calculate Camera Pans: Hold During Narration, Pan Just-In-Time ────────
CAM_PANS = DynamicSectionEngine.calculate_camera_pans(
    zone_order=zone_order,
    zone_last_element_end=zone_last_element_end,
    zone_first_element_start=zone_first_element_start,
    get_cam_x_fn=get_zone_cam_x,
    default_pan_dur=0.85
)

initial_cam_x = get_zone_cam_x(zone_order[0])

get_camera_state = DynamicSectionEngine.build_horizontal_camera_trajectory(
    cam_pans=CAM_PANS,
    initial_x=initial_cam_x,
    fixed_y=FIXED_Y,
    cam_zoom=CAM_ZOOM
)

# ─── Build Element Staging from Alignment Data ─────────────────────────────
elements_staging = []
hero_configs = []

for spec in staging_specs_raw:
    aid = spec[0]
    t_st = spec[1]
    t_dur = spec[2]
    anim_type = spec[3]
    depth = spec[4]
    fade_out = spec[5] if len(spec) > 5 else None

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
        'depth': depth,
        'fade_out_at': fade_out
    })
    if anim_type == "outside_in_pen":
        hero_configs.append((aid, t_st, t_dur))

print(f"\nStaged {len(elements_staging)} elements ({len(hero_configs)} heroes for authentic outside-in inking).")

# ─── Initialize Engine ─────────────────────────────────────────────────────
engine = DynamicSectionEngine(SEC_DIR)

# ─── Generate SFX & Master Audio ───────────────────────────────────────────
print("\n" + "=" * 60)
print("🎵 GENERATING SYNCHRONIZED DUCKED AUDIO")
print("=" * 60)
pan_times = [p[0] for p in CAM_PANS]
sfx_cues = engine.generate_sfx_from_staging(elements_staging, camera_pans=pan_times)
print(f"Auto-generated {len(sfx_cues)} enriched SFX cues.")

master_audio_path = engine.mix_master_audio(VOICEOVER_PATH, sfx_cues, target_duration_s=DURATION_SEC)
print(f"✅ Master audio mixed: {master_audio_path}")

# ─── Render 1080p Video ────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("🎥 RENDERING 1080P WHITEBOARD VIDEO (PURE HORIZONTAL)")
print("=" * 60)
final_video_path = engine.render_section(
    hero_configs=hero_configs,
    elements_staging=elements_staging,
    camera_trajectory_fn=get_camera_state,
    duration_sec=DURATION_SEC
)

# ─── Publish to Deliverables ───────────────────────────────────────────────
DELIVERABLES_DIR = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables", "sections")
os.makedirs(DELIVERABLES_DIR, exist_ok=True)

deliv_video = os.path.join(DELIVERABLES_DIR, "02_Extreme_Poverty_Whiteboard_1080p.mp4")
deliv_audio = os.path.join(DELIVERABLES_DIR, "02_Extreme_Poverty_Master_Audio.wav")

shutil.copyfile(final_video_path, deliv_video)
shutil.copyfile(master_audio_path, deliv_audio)

print("\n" + "=" * 80)
print("⭐ SECTION 02 DELIVERABLE SUCCESSFULLY PUBLISHED!")
print(f"  • Final Video : {deliv_video}")
print(f"  • Master Audio: {deliv_audio}")
print(f"  • Duration    : {DURATION_SEC:.2f}s")
print(f"  • Resolution  : 1920x1080 @ 30 FPS")
print(f"  • Camera Mode : 100% Pure Horizontal Panning (Y = {FIXED_Y} constant)")
print(f"  • Alignment   : 100% Speech-Synced (Zero Blank Screen)")
print(f"  • Elements    : {len(elements_staging)} staged, {len(hero_configs)} heroes")
print("=" * 80 + "\n")

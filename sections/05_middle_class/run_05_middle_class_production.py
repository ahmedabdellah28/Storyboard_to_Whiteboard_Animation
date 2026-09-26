"""
Section 05 — Middle Class (الطبقة المتوسطة): Full Production Runner
- 100% Automated Speech-Synced Staging from alignment_data.json
- Pure Horizontal Camera Panning (Y = 800.0 constant)
- Just-In-Time Camera Pan Timing & Narration Explanation Hold (Zero Blank Screen)
- Exact Drawing SFX Duration Trimming with smooth 40ms fade-out
"""
import os
import sys
import json
import wave
import shutil

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.dynamic_section_engine import DynamicSectionEngine

SEC_DIR = os.path.join(ROOT_DIR, "sections", "05_middle_class")
VOICEOVER_PATH = os.path.join(SEC_DIR, "voiceover.wav")
LAYOUT_PATH = os.path.join(SEC_DIR, "placed_elements_layout.json")
ALIGNMENT_PATH = os.path.join(SEC_DIR, "alignment_data.json")

# ─────────────────────────────── Load Voiceover Duration ────────────────────
with wave.open(VOICEOVER_PATH, 'rb') as wf:
    DURATION_SEC = wf.getnframes() / float(wf.getframerate())

print("=" * 80, flush=True)
print(f"🎬 Starting Section 05 (Middle Class / الطبقة المتوسطة) Production", flush=True)
print(f"  Duration: {DURATION_SEC:.2f}s | Pure Horizontal (Y=800.0) | Zero Blank Canvas", flush=True)
print("=" * 80, flush=True)

# ─────────────────────────────── Load Layout ────────────────────────────────
with open(LAYOUT_PATH, "r", encoding="utf-8") as f:
    layout_data = json.load(f)

placed_elements = layout_data["elements"]
zones = layout_data["zones"]
FIXED_Y = layout_data.get("fixed_y", 800.0)
CAM_ZOOM = layout_data.get("cam_zoom", 0.58)

elements_by_aid = {}
for z_name, elems in placed_elements.items():
    for el in elems:
        elements_by_aid[el["aid"]] = el

def get_zone_cam_x(z_name):
    return zones[z_name]["cam_pos"][0]

# ─────────────────────────────── Load Alignment Data ────────────────────────
with open(ALIGNMENT_PATH, "r", encoding="utf-8") as f:
    alignment_data = json.load(f)

staging_specs_raw = alignment_data["staging_specs"]

element_zone_map = {}
for z_name, elems in placed_elements.items():
    for el in elems:
        element_zone_map[el["aid"]] = z_name

zone_order = ["zone_1A", "zone_1B", "zone_2A", "zone_2B", "zone_3A", "zone_3B", "zone_4A", "zone_4B"]
zone_last_element_end = {}
zone_first_element_start = {}

for aid, t_st, t_dur, anim_type, depth in staging_specs_raw:
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

get_camera_state = DynamicSectionEngine.build_horizontal_camera_trajectory(
    cam_pans=CAM_PANS,
    initial_x=get_zone_cam_x("zone_1A"),
    fixed_y=FIXED_Y,
    cam_zoom=CAM_ZOOM
)

# ─── Build Element Staging ──────────────────────────────────────────────────
elements_staging = []
hero_configs = []

for aid, t_st, t_dur, anim_type, depth in staging_specs_raw:
    if aid not in elements_by_aid:
        print(f"⚠️ Warning: {aid} not in layout elements!", flush=True)
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

print(f"\nStaged {len(elements_staging)} elements ({len(hero_configs)} heroes for authentic outside-in inking).", flush=True)

# ─── Initialize Engine ─────────────────────────────────────────────────────
engine = DynamicSectionEngine(SEC_DIR)

# ─── Generate SFX & Master Audio ───────────────────────────────────────────
print("\n" + "=" * 60, flush=True)
print("🎵 GENERATING SYNCHRONIZED DUCKED AUDIO", flush=True)
print("=" * 60, flush=True)
pan_times = [p[0] for p in CAM_PANS]
sfx_cues = engine.generate_sfx_from_staging(elements_staging, camera_pans=pan_times)
print(f"Auto-generated {len(sfx_cues)} enriched SFX cues.", flush=True)

master_audio_path = engine.mix_master_audio(VOICEOVER_PATH, sfx_cues, target_duration_s=DURATION_SEC)
print(f"✅ Master audio mixed: {master_audio_path}", flush=True)

# ─── Render 1080p Video ────────────────────────────────────────────────────
print("\n" + "=" * 60, flush=True)
print("🎥 RENDERING 1080P WHITEBOARD VIDEO (PURE HORIZONTAL)", flush=True)
print("=" * 60, flush=True)
final_video_path = engine.render_section(
    hero_configs=hero_configs,
    elements_staging=elements_staging,
    camera_trajectory_fn=get_camera_state,
    duration_sec=DURATION_SEC
)

# ─── Publish to Deliverables ───────────────────────────────────────────────
DELIVERABLES_DIR = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables", "sections")
os.makedirs(DELIVERABLES_DIR, exist_ok=True)

deliv_video = os.path.join(DELIVERABLES_DIR, "05_Middle_Class_Whiteboard_1080p.mp4")
deliv_audio = os.path.join(DELIVERABLES_DIR, "05_Middle_Class_Master_Audio.wav")

shutil.copyfile(final_video_path, deliv_video)
shutil.copyfile(master_audio_path, deliv_audio)

print("\n" + "=" * 80, flush=True)
print("⭐ SECTION 05 DELIVERABLE SUCCESSFULLY PUBLISHED!", flush=True)
print(f"  • Final Video : {deliv_video}", flush=True)
print(f"  • Master Audio: {deliv_audio}", flush=True)
print(f"  • Duration    : {DURATION_SEC:.2f}s", flush=True)
print(f"  • Resolution  : 1920x1080 @ 30 FPS", flush=True)
print(f"  • Camera Mode : 100% Pure Horizontal Panning (Y = {FIXED_Y} constant)", flush=True)
print(f"  • Alignment   : 100% Gemini STT Speech-Synced", flush=True)
print(f"  • Elements    : {len(elements_staging)} staged, {len(hero_configs)} heroes", flush=True)
print("=" * 80 + "\n", flush=True)

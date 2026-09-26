import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.dynamic_section_engine import DynamicSectionEngine

layout = json.load(open(r'sections\01_homeless\placed_elements_layout.json', encoding='utf-8'))
zones = layout['zones']
plan = json.load(open(r'sections\01_homeless\timing\final_render_plan.json', encoding='utf-8'))

elem_zone = {el['aid']: z for z, els in layout['elements'].items() for el in els}
zone_order = list(zones.keys())

last_end = {}
first_st = {}
events = [e for e in plan['render_events'] if e.get('type') in ['draw', 'reveal']]

for ev in events:
    aid = ev['asset_id']
    z = elem_zone[aid]
    st = float(ev['start_s'])
    dur = float(ev['duration_s'])
    en = st + dur
    if z not in last_end or en > last_end[z]:
        last_end[z] = en
    if z not in first_st or st < first_st[z]:
        first_st[z] = st

pans = DynamicSectionEngine.calculate_camera_pans(
    zone_order, last_end, first_st, lambda z: zones[z]['cam_pos'][0], 0.85
)

get_cam = DynamicSectionEngine.build_horizontal_camera_trajectory(
    pans, zones[zone_order[0]]['cam_pos'][0], 800.0, layout['cam_zoom']
)

print("=" * 80)
print("ZONE CAM POSITIONS & ELEMENTS:")
for z in zone_order:
    elems = layout['elements'][z]
    print(f"{z:<10} | cam_x: {zones[z]['cam_pos'][0]:8.1f} | elems: {[e['aid'] for e in elems]}")

print("\n" * 1)
print("=" * 80)
print("TIMELINE EVENTS & ON-SCREEN VISIBILITY CHECK:")
WIDTH = 1920
HEIGHT = 1080
cam_zoom = layout['cam_zoom']

for ev in events:
    aid = ev['asset_id']
    st = float(ev['start_s'])
    dur = float(ev['duration_s'])
    en = st + dur
    z = elem_zone[aid]
    # find placed element
    pel = [e for e in layout['elements'][z] if e['aid'] == aid][0]
    
    # Check screen coordinates at start, middle, and end of drawing
    t_check = st + dur / 2.0
    cam_x, cam_y, zoom = get_cam(t_check)
    
    wx, wy = pel['x'], pel['y']
    ww, wh = pel['w'], pel['h']
    
    scr_x = int(round((wx - cam_x) * cam_zoom + (WIDTH / 2.0)))
    scr_y = int(round((wy - cam_y) * cam_zoom + (HEIGHT / 2.0)))
    scr_w = int(round(ww * cam_zoom))
    scr_h = int(round(wh * cam_zoom))
    
    is_visible = (scr_x + scr_w > 0 and scr_x < WIDTH and scr_y + scr_h > 0 and scr_y < HEIGHT)
    print(f"{aid:<25} | t={st:6.2f}s..{en:6.2f}s | zone: {z:<8} | cam_x={cam_x:7.1f} | scr_x={scr_x:5d}, scr_w={scr_w:4d} | VISIBLE: {is_visible}")

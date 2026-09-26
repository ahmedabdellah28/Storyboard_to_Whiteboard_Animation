import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

dt = json.load(open(r'sections\01_homeless\timing\drawing_timeline.json', encoding='utf-8'))['events']
fp = [e for e in json.load(open(r'sections\01_homeless\timing\final_render_plan.json', encoding='utf-8'))['render_events'] if e.get('type') in ['draw', 'reveal']]

print("=== TIMING COMPARISON (drawing_timeline vs final_render_plan) ===")
for d, f in zip(dt, fp):
    aid = d['asset_id']
    st_d = d['start_s']
    st_f = f['start_s']
    dur_d = d['duration_s']
    dur_f = f['duration_s']
    fade = f.get('fade_out_at')
    diff = st_f - st_d
    if abs(diff) > 0.05 or fade is not None:
        print(f"{aid:<25} | dt: {st_d:6.2f}s | plan: {st_f:6.2f}s (diff: {diff:+5.2f}s) | dur: {dur_f:4.2f}s | fade: {fade}")

import json

plan_path = r"E:\image_to_animate\sections\03_working_poor\timing\final_render_plan.json"
with open(plan_path, "r", encoding="utf-8") as f:
    plan = json.load(f)

draws = [e for e in plan.get("render_events", []) if e.get("type") in ["draw", "reveal"]]
for d in draws:
    print(f"{d.get('asset_id'):26s} | start: {d.get('start_s'):5.2f}s | dur: {d.get('duration_s'):4.2f}s | fade_out: {d.get('fade_out_at')}")

import os
import json

plan_path = r"E:\image_to_animate\sections\03_working_poor\timing\final_render_plan.json"
with open(plan_path, "r", encoding="utf-8") as f:
    plan = json.load(f)

events = plan.get("render_events", [])
draw_events = [e for e in events if e.get("type") in ["draw", "reveal"]]
print(f"Total render events: {len(events)}")
print(f"Total draw/reveal events: {len(draw_events)}")

fade_outs = [e for e in draw_events if e.get("fade_out_at") is not None]
print(f"Events with fade_out_at: {len(fade_outs)}")
for e in fade_outs:
    print(f"  {e.get('asset_id')}: fade_out_at = {e.get('fade_out_at')}")

# Enforce Zero Blank Screen Rule: Ensure all fade_out_at are None
for e in events:
    if "fade_out_at" in e and e["fade_out_at"] is not None:
        e["fade_out_at"] = None

with open(plan_path, "w", encoding="utf-8") as f:
    json.dump(plan, f, indent=2, ensure_ascii=False)

print("Enforced Zero Blank Screen: all fade_out_at set to None!")

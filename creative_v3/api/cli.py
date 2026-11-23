"""
Headless CLI for Creative Stickman Studio V3.
Usage:
  python -m creative_v3.api.cli list [--category A_performance]
  python -m creative_v3.api.cli validate
  python -m creative_v3.api.cli render-action <action_id> [--width 640] [--height 480] [--step 1]
  python -m creative_v3.api.cli render-batch [--start 1] [--end 100] [--width 480] [--height 360] [--step 2]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from creative_v3.engine.actions.catalog_100 import build_100_actions, get_action_map
from creative_v3.engine.actions.runner import (
    V3_ROOT,
    build_action_index_and_gallery,
    render_action_deliverables,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Creative Stickman Studio V3 Headless CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--category", default="")

    sub.add_parser("validate")

    p_one = sub.add_parser("render-action")
    p_one.add_argument("action_id")
    p_one.add_argument("--width", type=int, default=640)
    p_one.add_argument("--height", type=int, default=480)
    p_one.add_argument("--step", type=int, default=1)
    p_one.add_argument("--no-webm", action="store_true")

    p_batch = sub.add_parser("render-batch")
    p_batch.add_argument("--start", type=int, default=1)
    p_batch.add_argument("--end", type=int, default=100)
    p_batch.add_argument("--width", type=int, default=480)
    p_batch.add_argument("--height", type=int, default=360)
    p_batch.add_argument("--step", type=int, default=2)
    p_batch.add_argument("--no-webm", action="store_true")

    args = parser.parse_args()
    specs = build_100_actions()

    if args.cmd == "list":
        filtered = [s for s in specs if not args.category or s.category == args.category]
        print(json.dumps([{"number": s.number, "action_id": s.action_id, "category": s.category, "frames": s.duration_frames} for s in filtered], indent=2))
        return

    if args.cmd == "validate":
        errors = {s.action_id: s.validate() for s in specs if s.validate()}
        print(json.dumps({"total_actions": len(specs), "invalid_count": len(errors), "errors": errors}, indent=2))
        if errors:
            raise SystemExit(1)
        return

    if args.cmd == "render-action":
        amap = get_action_map()
        if args.action_id not in amap:
            raise SystemExit(f"Unknown action_id: {args.action_id}")
        qa = render_action_deliverables(
            amap[args.action_id],
            width=args.width,
            height=args.height,
            frame_step=args.step,
            export_webm=not args.no_webm,
        )
        print(json.dumps(qa, indent=2))
        return

    if args.cmd == "render-batch":
        qa_list = []
        for s in specs:
            if args.start <= s.number <= args.end:
                qa = render_action_deliverables(
                    s,
                    width=args.width,
                    height=args.height,
                    frame_step=args.step,
                    export_webm=not args.no_webm,
                )
                qa_list.append(qa)
                print(f"[{s.number:03d}/100] {s.action_id} -> {qa['status']} ({qa['rendered_frame_count']} frames)", flush=True)
        # Collect all existing qa.json for index
        all_qa = []
        for s in specs:
            qf = V3_ROOT / "actions" / f"action_{s.number:03d}" / "qa.json"
            if qf.exists():
                all_qa.append(json.loads(qf.read_text(encoding="utf-8")))
        if all_qa:
            cat_p, gal_p = build_action_index_and_gallery(all_qa)
            (V3_ROOT / "reports" / "visual_qa.json").write_text(
                json.dumps({"audited_count": len(all_qa), "passed": sum(1 for q in all_qa if q["status"] == "PASS"), "results": all_qa}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Index written: {cat_p} & {gal_p}")


if __name__ == "__main__":
    main()

"""Thin compatibility wrapper delegating voice+timing to unified `pipeline_cli.py` / `core.aion`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline_cli


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="Project folder inside projects/")
    ap.add_argument("--sections", nargs="+", type=int, default=list(range(1, 9)))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    all_ok = True
    for s in args.sections:
        sid = f"{s:02d}"
        ok_v = pipeline_cli.cmd_voice(sid, project=args.project, force=args.force)
        ok_t = pipeline_cli.cmd_timing(sid, project=args.project, force=args.force) if ok_v else False
        all_ok = all_ok and ok_v and ok_t
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

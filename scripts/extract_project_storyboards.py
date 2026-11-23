"""Thin compatibility wrapper delegating storyboard extraction to unified `pipeline_cli.py` / `core.aion`."""
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
    ap.add_argument("--project", required=True)
    ap.add_argument("--sections", nargs="+", type=int, default=list(range(1, 9)))
    ap.add_argument("--mode", choices=["grid", "contour"], default="grid")
    args = ap.parse_args()

    ok = True
    for s in args.sections:
        ok = ok and pipeline_cli.cmd_extract(f"{s:02d}", project=args.project, mode=args.mode)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

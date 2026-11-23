"""Golden-reference integrity snapshot for AION CLI regression tests.

Records size + sha256 of every file under a protected project so we can prove
that CLI development never mutates the reference outputs.

Usage:
    python tests/aion_cli/golden_snapshot.py capture [--project mind_glitches_ar]
    python tests/aion_cli/golden_snapshot.py verify  [--project mind_glitches_ar]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAP_DIR = Path(__file__).resolve().parent / "baselines"
IGNORE_PARTS = {"__pycache__"}


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build_manifest(project: str) -> dict:
    proj_dir = ROOT / "projects" / project
    files = {}
    dirs = []
    for p in sorted(proj_dir.rglob("*")):
        rel = p.relative_to(proj_dir)
        if IGNORE_PARTS.intersection(rel.parts):
            continue
        if p.is_dir():
            dirs.append(rel.as_posix())
        elif p.is_file():
            files[rel.as_posix()] = [p.stat().st_size, _sha256(p)]
    return {"project": project, "files": files, "dirs": dirs}


def snapshot_path(project: str) -> Path:
    return SNAP_DIR / f"{project}.golden.json"


def diff_manifest(project: str) -> dict:
    base = json.loads(snapshot_path(project).read_text(encoding="utf-8"))
    cur = build_manifest(project)
    bf, cf = base["files"], cur["files"]
    return {
        "added_files": sorted(set(cf) - set(bf)),
        "removed_files": sorted(set(bf) - set(cf)),
        "changed_files": sorted(k for k in set(bf) & set(cf) if bf[k] != cf[k]),
        "added_dirs": sorted(set(cur["dirs"]) - set(base["dirs"])),
        "removed_dirs": sorted(set(base["dirs"]) - set(cur["dirs"])),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["capture", "verify"])
    ap.add_argument("--project", default="mind_glitches_ar")
    args = ap.parse_args()

    if args.action == "capture":
        SNAP_DIR.mkdir(parents=True, exist_ok=True)
        man = build_manifest(args.project)
        snapshot_path(args.project).write_text(json.dumps(man, indent=1), encoding="utf-8")
        total = sum(v[0] for v in man["files"].values())
        print(f"captured {len(man['files'])} files / {len(man['dirs'])} dirs ({total / 1e9:.2f} GB) -> {snapshot_path(args.project)}")
        return 0

    d = diff_manifest(args.project)
    dirty = any(d.values())
    for k, v in d.items():
        if v:
            print(f"{k}: {len(v)}")
            for item in v[:15]:
                print(f"   {item}")
    print("GOLDEN INTACT" if not dirty else "GOLDEN MODIFIED")
    return 1 if dirty else 0


if __name__ == "__main__":
    sys.exit(main())

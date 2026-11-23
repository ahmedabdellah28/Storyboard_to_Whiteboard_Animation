"""Black-box CLI behavior harness for pipeline_cli.py.

Runs a fixed set of offline-safe commands (no TTS / GPU / network) against a
throwaway fixture project and records exit code + normalized stdout.

    python tests/aion_cli/cli_harness.py capture   # record baseline (run on UNMODIFIED CLI)
    python tests/aion_cli/cli_harness.py compare   # diff current behavior vs baseline

`.active_project` is always restored and the fixture project is always deleted.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "pipeline_cli.py"
FIXTURE = "aion_regression_fixture"
FIXTURE_DIR = ROOT / "projects" / FIXTURE
ACTIVE_FILE = ROOT / ".active_project"
BASELINE = Path(__file__).resolve().parent / "baselines" / "cli_behavior_baseline.json"

SUBCOMMANDS = ["init", "use", "projects", "paths", "voice", "timing", "extract",
               "render", "effects", "status", "merge", "enhance", "auto"]

# (case_id, argv, setup_fn_name)
CASES = [
    ("root_help", ["--help"]),
    *[(f"help_{s}", [s, "--help"]) for s in SUBCOMMANDS],
    ("init_fixture", ["init", FIXTURE, "--sections", "2", "--lang", "en"]),
    ("projects", ["projects"]),
    ("paths_sub_flag", ["paths", "--project", FIXTURE]),
    ("status_sub_flag", ["status", "--project", FIXTURE]),
    ("status_root_flag", ["--project", FIXTURE, "status"]),
    ("timing_no_audio", ["timing", "--section", "01", "--project", FIXTURE]),
    ("extract_no_storyboard", ["extract", "--section", "01", "--project", FIXTURE]),
    ("render_no_manifest", ["render", "--section", "01", "--project", FIXTURE]),
    ("merge_no_videos", ["merge", "--project", FIXTURE]),
    ("effects_list", ["effects", "--list"]),
    ("voice_no_script", ["voice", "--section", "01", "--project", FIXTURE], "remove_scripts"),
]


def _normalize(text: str) -> str:
    text = text.replace(str(ROOT), "<ROOT>").replace(str(ROOT).replace("\\", "/"), "<ROOT>")
    text = re.sub(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?", "<TS>", text)
    text = re.sub(r"\d+(\.\d+)? MB", "<N> MB", text)
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _setup(name: str | None) -> None:
    if name == "remove_scripts":
        for p in (FIXTURE_DIR / "inputs" / "script").rglob("*.txt"):
            p.unlink()


def run_cases(cases=CASES) -> dict:
    saved_active = ACTIVE_FILE.read_text(encoding="utf-8") if ACTIVE_FILE.exists() else None
    if FIXTURE_DIR.exists():
        shutil.rmtree(FIXTURE_DIR)
    results = {}
    try:
        for case in cases:
            cid, argv = case[0], case[1]
            _setup(case[2] if len(case) > 2 else None)
            proc = subprocess.run(
                [sys.executable, str(CLI), *argv], cwd=ROOT, capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=300,
            )
            results[cid] = {
                "argv": argv,
                "exit_code": proc.returncode,
                "stdout": _normalize(proc.stdout),
                "stderr_tail": _normalize(proc.stderr)[-600:],
                "active_after": ACTIVE_FILE.read_text(encoding="utf-8").strip() if ACTIVE_FILE.exists() else None,
            }
    finally:
        if saved_active is None:
            ACTIVE_FILE.unlink(missing_ok=True)
        else:
            ACTIVE_FILE.write_text(saved_active, encoding="utf-8")
        shutil.rmtree(FIXTURE_DIR, ignore_errors=True)
    return results


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "compare"
    res = run_cases()
    if action == "capture":
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        for cid, r in res.items():
            print(f"{cid:<24} exit={r['exit_code']}  active_after={r['active_after']}")
        print(f"baseline -> {BASELINE}")
        return 0
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    bad = 0
    for cid, r in res.items():
        b = base.get(cid)
        same = b is not None and b["stdout"] == r["stdout"] and b["exit_code"] == r["exit_code"]
        print(f"{'SAME' if same else 'DIFF'}  {cid}")
        bad += 0 if same else 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

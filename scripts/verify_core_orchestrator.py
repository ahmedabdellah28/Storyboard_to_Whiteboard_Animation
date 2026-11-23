#!/usr/bin/env python3
"""
Verify the canonical Core DAG production command actually exists and is importable.

The whiteboard-video SKILL.md names `core.orchestration.orchestrator` as the
single source of truth for section/project production. Before following any
production command from that skill, run this probe to confirm the module path
is real in the current checkout — the skill's canonical commands are only valid
when this returns OK.

Usage:
    python scripts/verify_core_orchestrator.py

Exit codes:
    0 — orchestrator module found and importable
    1 — module not found or not importable (skill commands will fail)
"""
import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TARGET = "core.orchestration.orchestrator"

if __name__ == "__main__":
    sys.path.insert(0, str(PROJECT_ROOT))

    print(f"Probing: {TARGET}")
    print(f"Project root: {PROJECT_ROOT}")
    print()

    try:
        mod = importlib.import_module(TARGET)
    except ModuleNotFoundError as e:
        print(f"FAIL — module not found: {e}")
        print()
        print("The SKILL.md canonical commands reference this module:")
        print(f"  python -m {TARGET} --section <NN_name>")
        print(f"  python -m {TARGET} --project <slug> --parallel 2 --assemble")
        print()
        print("If this is intentional (planned but not yet wired), the skill's")
        print("canonical commands are aspirational, not currently runnable.")
        sys.exit(1)

    print(f"OK — module imported from: {mod.__file__}")
    print()

    has_main = hasattr(mod, "main") or hasattr(mod, "__doc__")
    print(f"Has module-level 'main': {hasattr(mod, 'main')}")
    print(f"Module docstring length: {len(getattr(mod, '__doc__', '') or '')}")
    print()
    print("If 'main' is missing, the CLI entry point may not be wired yet.")
    sys.exit(0)

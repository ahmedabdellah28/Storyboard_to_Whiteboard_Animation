"""Pre-upgrade & non-regression pytest suite for pipeline_cli & golden project protection."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline_cli
from tests.aion_cli import cli_harness, golden_snapshot


def test_golden_reference_mind_glitches_ar_intact():
    """Golden project mind_glitches_ar must remain byte-for-byte unmodified."""
    snap = golden_snapshot.snapshot_path("mind_glitches_ar")
    assert snap.is_file(), "Golden baseline snapshot missing"
    diff = golden_snapshot.diff_manifest("mind_glitches_ar")
    assert not any(diff.values()), f"Golden reference mutated: {diff}"


def test_legacy_cli_help_and_subcommands_present():
    """Verify legacy entrypoint responds cleanly with all existing + new subcommands."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "pipeline_cli.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0
    for cmd in [
        "init", "use", "projects", "paths", "script", "voice", "timing",
        "extract", "semantic-map", "brief", "direct", "motion", "sfx",
        "render", "qa", "effects", "status", "merge", "enhance", "doctor",
        "cli-spec", "auto", "run",
    ]:
        assert cmd in proc.stdout, f"Missing subcommand {cmd!r} in --help"


def test_effects_list_fixed_and_works():
    """Verify effects --list crash (wrong CLI_PATH) is fixed."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "pipeline_cli.py"), "effects", "--list"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0
    assert "EFFECTCRAFT MOTION EFFECTS CATALOG" in proc.stdout


def test_core_modules_importable_for_reuse():
    """Verify core state/artifact/validation/API modules + core.aion are cleanly available."""
    from core.api.key_pool import APIKeyPool
    from core.artifacts.cache_validator import CacheValidator
    from core.state.state_store import StateStore
    from core.validation.environment_doctor import EnvironmentDoctor
    from core.validation.post_render_qa import PostRenderQAEngine
    from core.validation.recovery import CrashReconciliationEngine
    from core.aion.contracts import PIPELINE_STAGES

    assert len(PIPELINE_STAGES) == 12
    assert APIKeyPool is not None
    assert CacheValidator is not None
    assert StateStore is not None
    assert EnvironmentDoctor is not None
    assert PostRenderQAEngine is not None
    assert CrashReconciliationEngine is not None


def test_isolated_fixture_legacy_cli_runtime_compat():
    """Verify legacy runtime commands (init/projects/paths/status/missing-input errors) match baseline exactly."""
    saved_active = (ROOT / ".active_project").read_text(encoding="utf-8") if (ROOT / ".active_project").exists() else None
    runtime_cases = [c for c in cli_harness.CASES if not c[0].startswith(("root_help", "help_", "effects_"))]
    try:
        res = cli_harness.run_cases(runtime_cases)
        base = json.loads(cli_harness.BASELINE.read_text(encoding="utf-8"))
        for cid, r in res.items():
            assert r["exit_code"] == base[cid]["exit_code"], f"{cid} exit mismatch"
            assert r["stdout"] == base[cid]["stdout"], f"{cid} stdout drift"
    finally:
        if saved_active is not None:
            (ROOT / ".active_project").write_text(saved_active, encoding="utf-8")
        shutil.rmtree(ROOT / "projects" / cli_harness.FIXTURE, ignore_errors=True)

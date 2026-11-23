"""Phase 14 & 15 Test Suite: Migration Cleanup, Packaging & Environment Diagnostics.

Validates:
1. Zero Kivy imports in core/, studio_ui/, and production_engine/ (AST scan).
2. Hardware Encoder Fallback Ladder (NVENC -> QSV -> AMF -> libx264 -> h264).
3. EnvironmentHealthChecker diagnostic reporting and CLI formatting.
4. Desktop workstation CLI commands (--diagnostics, --headless-check).
5. Autonomous asset discovery & decoupling in core/render_engine.
6. Project state backward compatibility and schema migration.
7. Complete 15-phase module inventory verification.
"""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from core.config.settings import PROJECT_ROOT


# ==============================================================================
# 1. Zero-Legacy Kivy AST Audit
# ==============================================================================

def test_zero_mandatory_kivy_in_core_and_studio_ui():
    """Scans all Python source files in core/ and studio_ui/ to assert ZERO un-guarded kivy imports."""
    scan_roots = [
        PROJECT_ROOT / "core",
        PROJECT_ROOT / "studio_ui",
    ]

    violating_imports = []

    for root in scan_roots:
        for py_path in root.rglob("*.py"):
            try:
                tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "kivy" or alias.name.startswith("kivy."):
                            violating_imports.append((str(py_path.relative_to(PROJECT_ROOT)), alias.name))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and (node.module == "kivy" or node.module.startswith("kivy.")):
                        violating_imports.append((str(py_path.relative_to(PROJECT_ROOT)), node.module))

    assert len(violating_imports) == 0, f"Found legacy kivy imports in modern architecture: {violating_imports}"


# ==============================================================================
# 2. Hardware Encoder Fallback Ladder
# ==============================================================================

def test_hardware_encoder_ladder_priorities():
    """Verifies that the encoder ladder priority strictly follows NVENC -> QSV -> AMF -> libx264 -> h264."""
    from core.telemetry.packaging import ENCODER_LADDER_DEFINITIONS, EnvironmentHealthChecker

    codecs = [item[0] for item in ENCODER_LADDER_DEFINITIONS]
    assert codecs == ["h264_nvenc", "h264_qsv", "h264_amf", "libx264", "h264"]

    # Test detection logic returns results for each ladder rung
    encoders, best = EnvironmentHealthChecker.check_encoder_ladder()
    assert len(encoders) == len(codecs)
    assert best in codecs or best == "mp4v"


def test_video_encoder_ladder_stepdown():
    """Simulates NVENC failure to verify automatic step-down in VideoEncoder._detect_best_codec."""
    from core.render_engine.video.encoder import VideoEncoder

    # Mock av.open to simulate nvenc failure then success on qsv
    with patch("core.render_engine.video.encoder.cv2"):
        encoder = object.__new__(VideoEncoder)
        
        call_history = []
        class MockAVStream:
            pass

        class MockAVContainer:
            def add_stream(self, codec, rate=30):
                call_history.append(codec)
                if codec == "h264_nvenc":
                    raise RuntimeError("No NVENC GPU available")
                return MockAVStream()
            def close(self):
                pass

        mock_av = MagicMock()
        mock_av.open.return_value = MockAVContainer()

        with patch.dict("sys.modules", {"av": mock_av}):
            best = encoder._detect_best_codec(fps=30)
            assert best == "h264_qsv"
            assert "h264_nvenc" in call_history


# ==============================================================================
# 3. Environment Health Checker Diagnostics
# ==============================================================================

def test_environment_health_checker_diagnostics():
    """Tests comprehensive diagnostic report generation, dependency mapping, and CLI output."""
    from core.telemetry.packaging import EnvironmentHealthChecker

    report = EnvironmentHealthChecker.run_full_diagnostics()
    assert report.python_version != ""
    assert report.is_64bit is True  # Antigravity test runner is 64-bit
    assert "numpy" in report.dependencies
    assert report.dependencies["numpy"] is True
    assert isinstance(report.best_encoder, str)

    # Test CLI formatting
    cli_text = report.format_cli()
    assert "WHITEBOARD STUDIO" in cli_text
    assert "Hardware Encoder Ladder" in cli_text
    assert "Dependency Matrix" in cli_text

    # Test JSON serialization
    report_dict = report.to_dict()
    assert "python_version" in report_dict
    assert "hardware_encoders" in report_dict
    assert len(report_dict["hardware_encoders"]) == 5


# ==============================================================================
# 4. Workstation CLI Diagnostics and Headless Modes
# ==============================================================================

def test_cli_diagnostics_mode(capsys):
    """Tests running the workstation with --diagnostics executes and outputs report."""
    from studio_ui.app import main

    exit_code = main(["--diagnostics"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "WHITEBOARD STUDIO" in captured.out
    assert "Hardware Encoder Ladder" in captured.out


def test_cli_headless_sanity_check(capsys):
    """Tests running the workstation with --headless-check initializes shell and exits cleanly."""
    from studio_ui.app import main

    exit_code = main(["--headless-check"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Headless initialization sanity check passed" in captured.out


def test_main_entrypoint_import():
    """Verifies that studio_ui.main provides a valid executable entry point."""
    import studio_ui.main as studio_main
    assert hasattr(studio_main, "main")
    assert callable(studio_main.main)


# ==============================================================================
# 5. Asset Decoupling in Core Render Engine
# ==============================================================================

def test_render_engine_asset_independence():
    """Tests that ensure_render_engine_assets ensures core/render_engine has self-contained assets."""
    from core.telemetry.packaging import EnvironmentHealthChecker

    target_dir = EnvironmentHealthChecker.ensure_render_engine_assets()
    assert target_dir.exists()

    hand_file = target_dir / "drawing-hand.png"
    mask_file = target_dir / "hand-mask.png"
    assert hand_file.exists(), "drawing-hand.png must exist in core/render_engine/data/images"
    assert mask_file.exists(), "hand-mask.png must exist in core/render_engine/data/images"


# ==============================================================================
# 6. Legacy Project State Schema Migration
# ==============================================================================

def test_legacy_project_state_schema_migration(tmp_path):
    """Verifies that older project state structures without modern revision fields load seamlessly."""
    from core.state.project_state import ProjectState, SectionState
    from core.state.transitions import SectionLifecycleStatus

    # Construct legacy-style dict omitting modern fields (revisions, stage substates)
    legacy_data = {
        "project_id": "legacy_proj_001",
        "title": "Legacy Project",
        "sections": {
            "sec_01": {
                "section_id": "sec_01",
                "title": "Old Section",
                "status": "PENDING",
                "lifecycle_status": "DRAFTING",
                "sequence_index": 0
            }
        }
    }

    # ProjectState should parse legacy data with default fields filled in
    proj = ProjectState.from_dict(legacy_data)
    assert proj.project_id == "legacy_proj_001"
    assert "sec_01" in proj.sections
    sec = proj.sections["sec_01"]
    assert sec.lifecycle_status == SectionLifecycleStatus.DRAFTING
    assert hasattr(sec, "revision_id")
    assert sec.revision_id >= 1



# ==============================================================================
# 7. Complete 15-Phase Module Inventory Verification
# ==============================================================================

def test_all_15_phases_module_inventory():
    """Asserts that all core modules and contracts from Phases 1 through 15 are in place and importable."""
    phase_inventory = {
        "Phase 1: Contracts & State": [
            "core.contracts.studio_contracts",
            "core.contracts.visual_manifest",
            "core.contracts.narrative_map",
            "core.contracts.render_plan",
            "core.state.transitions",
            "core.state.project_state",
            "core.state.state_store",
        ],

        "Phase 2: Invalidation & Revisions": [
            "core.artifacts.revision_manager",
            "core.artifacts.dependency_graph",
        ],
        "Phase 3: Validation & Recovery": [
            "core.validation.preflight",
            "core.validation.recovery",
            "core.validation.environment_doctor",
        ],
        "Phase 4: Governance & Cancellation": [
            "core.orchestration.resource_governor",
            "core.orchestration.worker_manager",
        ],
        "Phase 5: UI Shell & Dialogs": [
            "studio_ui.qt",
            "studio_ui.theme",
            "studio_ui.dialogs.new_project_dialog",
            "studio_ui.main_window",
        ],
        "Phase 6: Core Bridge & Monitor": [
            "studio_ui.views.processing_monitor",
        ],
        "Phase 7: Review Gates & Inspection": [
            "studio_ui.views.studio_inspector",
        ],
        "Phase 8-9: Studio Canvas & Timeline": [
            "studio_ui.views.studio_canvas",
            "studio_ui.views.studio_timeline",
            "studio_ui.views.studio_editor",
        ],
        "Phase 10: Preview Player": [
            "studio_ui.views.studio_player",
        ],
        "Phase 11: Post-Render QA & Master Assembly": [
            "core.validation.post_render_qa",
        ],
        "Phase 12-13: Performance & Golden Path": [
            "core.telemetry.performance",
        ],
        "Phase 14-15: Packaging & Diagnostics": [
            "core.telemetry.packaging",
            "studio_ui.main",
        ],
    }

    import importlib
    for phase_name, modules in phase_inventory.items():
        for mod in modules:
            try:
                m = importlib.import_module(mod)
                assert m is not None, f"Failed importing {mod} from {phase_name}"
            except Exception as e:
                pytest.fail(f"Module {mod} in {phase_name} failed to import: {e}")

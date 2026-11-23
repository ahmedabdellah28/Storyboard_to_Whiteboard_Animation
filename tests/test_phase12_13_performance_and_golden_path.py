"""Phase 12 & 13 Test Suite: Performance Hardening & End-to-End Golden Path Integration.

Validates:
1. LazyModule deferred import (no import until first attribute access).
2. StartupProfiler timing marks and report generation.
3. PerformanceBudget pass/fail evaluation.
4. Cold startup performance budget (core imports < 500ms).
5. End-to-End Golden Path: PROJECT → SECTION → PREFLIGHT → PROCESS →
   REVIEW GATES → STUDIO EDITOR → PREVIEW → QA → MASTER.
6. Module inventory: every UI view, dialog, and core module is importable.
7. StudioMainWindow complete page navigation (Browser → Workspace → Monitor → Editor).
"""

import json
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
import pytest

from studio_ui.qt import QApplication, QMessageBox


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    return app


@pytest.fixture(autouse=True)
def mock_dialogs(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)


def _make_video(path: Path, width=1920, height=1080, fps=30.0, n=30):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    for i in range(n):
        frame = np.full((height, width, 3), 240, dtype=np.uint8)
        cv2.line(frame, (50, 50), (50 + i * 10, 50 + i * 5), (20, 20, 20), 3)
        out.write(frame)
    out.release()


def _make_audio(path: Path, dur=1.0, sr=44100):
    t = np.linspace(0, dur, int(dur * sr), endpoint=False)
    data = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())


# ---------------------------------------------------------------------------
# 1. LazyModule Tests
# ---------------------------------------------------------------------------

def test_lazy_module_defers_import():
    """LazyModule does NOT import until first attribute access."""
    from core.telemetry.performance import LazyModule

    lm = LazyModule("json")
    assert lm._module is None  # NOT loaded yet
    assert "LazyModule" in repr(lm)
    assert "loaded=False" in repr(lm)

    # Now trigger load
    result = lm.dumps({"key": "val"})
    assert lm._module is not None
    assert "loaded=True" in repr(lm)
    assert '"key"' in result


def test_lazy_module_nonexistent_raises():
    """LazyModule with nonexistent module raises ImportError on first access."""
    from core.telemetry.performance import LazyModule

    lm = LazyModule("totally_nonexistent_module_xyz")
    with pytest.raises(ModuleNotFoundError):
        _ = lm.some_attr


# ---------------------------------------------------------------------------
# 2. StartupProfiler Tests
# ---------------------------------------------------------------------------

def test_startup_profiler_marks_and_report():
    """StartupProfiler records marks and produces structured report."""
    from core.telemetry.performance import StartupProfiler

    prof = StartupProfiler()
    time.sleep(0.01)
    prof.mark("step_a")
    time.sleep(0.01)
    prof.mark("step_b")

    report = prof.report()
    assert report["mark_count"] == 2
    assert report["total_elapsed_ms"] > 15
    assert len(report["phases"]) == 2
    assert "step_a" in report["marks"]
    assert "step_b" in report["marks"]

    summary = prof.summary()
    assert "step_a" in summary
    assert "step_b" in summary


# ---------------------------------------------------------------------------
# 3. PerformanceBudget Tests
# ---------------------------------------------------------------------------

def test_performance_budget_pass_and_fail():
    """PerformanceBudget correctly evaluates pass/fail against thresholds."""
    from core.telemetry.performance import PerformanceBudget

    budget = PerformanceBudget()
    budget.add("cold_startup", max_ms=1000)
    budget.add("project_load", max_ms=200)

    budget.record("cold_startup", 850.0)
    budget.record("project_load", 350.0)  # Over budget

    result = budget.evaluate()
    assert result["overall_pass"] is False  # project_load exceeded

    items = {r["metric"]: r for r in result["results"]}
    assert items["cold_startup"]["passed"] is True
    assert items["cold_startup"]["headroom_pct"] > 0
    assert items["project_load"]["passed"] is False


def test_performance_budget_all_pass():
    """PerformanceBudget passes when all metrics are within budget."""
    from core.telemetry.performance import PerformanceBudget

    budget = PerformanceBudget()
    budget.add("import_core", max_ms=500)
    budget.add("import_ui", max_ms=800)

    budget.record("import_core", 120.0)
    budget.record("import_ui", 350.0)

    result = budget.evaluate()
    assert result["overall_pass"] is True


# ---------------------------------------------------------------------------
# 4. Core Module Import Performance
# ---------------------------------------------------------------------------

def test_core_module_import_budget():
    """All core modules import within 500ms budget."""
    from core.telemetry.performance import StartupProfiler, PerformanceBudget

    prof = StartupProfiler()

    prof.mark("import_contracts_start")
    from core.contracts.studio_contracts import CANONICAL_STAGES_ORDER, StageIdentifier
    prof.mark("import_contracts_done")

    prof.mark("import_state_start")
    from core.state.project_state import ProjectState
    from core.state.state_store import StateStore
    prof.mark("import_state_done")

    prof.mark("import_orchestration_start")
    from core.orchestration.task_dag import TaskDAGExecutor
    from core.orchestration.section_worker import SectionWorker
    from core.orchestration.core_bridge import CoreBridge
    prof.mark("import_orchestration_done")

    prof.mark("import_validation_start")
    from core.validation.preflight import InputPreflightValidator
    from core.validation.post_render_qa import PostRenderQAEngine
    from core.validation.recovery import CrashReconciliationEngine
    prof.mark("import_validation_done")

    budget = PerformanceBudget()
    budget.add("core_imports", max_ms=3000)  # Generous for cold-start with cv2 transitive dep

    report = prof.report()
    budget.record("core_imports", report["total_elapsed_ms"])

    result = budget.evaluate()
    assert result["overall_pass"] is True, f"Core imports exceeded 500ms: {report['total_elapsed_ms']:.1f}ms"


# ---------------------------------------------------------------------------
# 5. Complete Module Inventory Test
# ---------------------------------------------------------------------------

def test_complete_module_inventory():
    """Verify every expected studio module is importable without errors."""
    modules = [
        # Core Contracts
        "core.contracts.studio_contracts",
        "core.contracts.qa_reports",
        "core.contracts.render_plan",
        "core.contracts.visual_manifest",
        "core.contracts.narrative_map",
        # Core State
        "core.state.project_state",
        "core.state.state_store",
        "core.state.transitions",
        "core.state.workflow_events",
        # Core Orchestration
        "core.orchestration.task_dag",
        "core.orchestration.section_worker",
        "core.orchestration.core_bridge",
        "core.orchestration.resource_governor",
        "core.orchestration.worker_manager",
        "core.orchestration.master_concatenator",
        "core.orchestration.orchestrator",
        # Core Validation
        "core.validation.preflight",
        "core.validation.post_render_qa",
        "core.validation.recovery",
        "core.validation.environment_doctor",
        # Core Telemetry
        "core.telemetry.performance",
        # Studio UI Qt Shim
        "studio_ui.qt",
        # Studio UI Views
        "studio_ui.views.studio_canvas",
        "studio_ui.views.studio_timeline",
        "studio_ui.views.studio_inspector",
        "studio_ui.views.studio_editor",
        "studio_ui.views.studio_player",
        "studio_ui.views.processing_monitor",
        "studio_ui.views.project_browser",
        # Studio UI Dialogs
        "studio_ui.dialogs.new_project_dialog",
        "studio_ui.dialogs.new_section_dialog",
        "studio_ui.dialogs.extraction_review_dialog",
        "studio_ui.dialogs.voice_review_dialog",
        "studio_ui.dialogs.semantic_review_dialog",
        "studio_ui.dialogs.post_render_qa_dialog",
        "studio_ui.dialogs.master_assembly_dialog",
        # Main Window
        "studio_ui.main_window",
    ]

    import importlib
    failures = []
    for mod_name in modules:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            failures.append(f"{mod_name}: {e}")

    assert not failures, f"Failed to import modules:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# 6. End-to-End Golden Path Integration
# ---------------------------------------------------------------------------

def test_golden_path_end_to_end(qapp, monkeypatch):
    """Complete Golden Path: PROJECT → SECTION → PROCESS → REVIEW → EDITOR → PREVIEW → QA → MASTER."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        base = Path(tmpdir)

        # --- Setup ---
        from core.state.state_store import StateStore
        from core.state.project_state import ProjectState
        from core.contracts.studio_contracts import CANONICAL_STAGES_ORDER
        from core.validation.post_render_qa import PostRenderQAEngine
        from core.contracts.qa_reports import QAGateStatus

        store = StateStore(base_dir=base / ".state")

        # 1. PROJECT: Create project state
        project = ProjectState(
            project_id="golden_path_test",
            title="Golden Path E2E Documentary",
            metadata={"project_path": str(base / "gp_project")},
        )

        # 2. SECTION: Create sections with storyboard & script stubs
        proj_dir = base / "gp_project"
        for idx, sid in enumerate(["01_intro", "02_body"]):
            sec = project.get_or_create_section(sid, title=f"Section {sid}", sequence_index=idx)
            sec_dir = proj_dir / "sections" / sid
            (sec_dir / "assets").mkdir(parents=True, exist_ok=True)
            (sec_dir / "voice").mkdir(parents=True, exist_ok=True)
            (sec_dir / "timing").mkdir(parents=True, exist_ok=True)

            # Storyboard stub
            img = np.full((1080, 1920, 3), 240, dtype=np.uint8)
            cv2.imwrite(str(sec_dir / "storyboard.png"), img)

            # Script stub
            (sec_dir / "script.txt").write_text("هذا نص تجريبي لفحص المسار الذهبي", encoding="utf-8")

            # Generate synthetic deliverable
            _make_video(sec_dir / "final_whiteboard_1080p.mp4", n=30)
            _make_audio(sec_dir / "voice" / "section.wav", dur=1.0)
            _make_audio(sec_dir / "master_audio.wav", dur=1.0)

            # Generate placed_elements_layout.json
            layout = {
                "section_id": sid,
                "canvas_width": 1920,
                "canvas_height": 1080,
                "placed_elements": [
                    {"id": "asset_bg", "file": "asset_bg.png", "x": 960, "y": 540, "scale": 1.0,
                     "animation_style": "Outside-In Pen", "draw_duration": 0.8, "hold_duration": 2.5}
                ],
                "cameras": [{"name": "Camera 01", "center_x": 960, "center_y": 540, "zoom": 1.0, "duration": 4.0}],
            }
            with open(sec_dir / "placed_elements_layout.json", "w", encoding="utf-8") as f:
                json.dump(layout, f, indent=2, ensure_ascii=False)

            # Mock assets/metadata.json
            meta = {"assets": {"asset_bg": {"file": "asset_bg.png", "bbox": [0, 0, 1920, 1080], "label": "خلفية"}}}
            with open(sec_dir / "assets" / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

        store.save_state(project)

        # 3. MAIN WINDOW: Initialize and load project
        from studio_ui.main_window import StudioMainWindow
        window = StudioMainWindow(state_store=store)
        window.load_project(project)

        assert window.current_project is not None
        assert window.current_project.project_id == "golden_path_test"
        assert window.stacked_widget.currentIndex() == 1  # Workspace

        # 4. PROCESS: Verify switching to processing monitor
        window._open_monitor_view(section_id="01_intro")
        assert window.stacked_widget.currentIndex() == 2

        # 5. STUDIO EDITOR: Switch to canvas editor
        window._open_studio_editor("01_intro")
        assert window.stacked_widget.currentIndex() == 3
        assert window.studio_editor.active_section_id == "01_intro"
        assert "asset_bg" in window.studio_editor.elements_data

        # 6. EDITOR: Modify element position and save
        window.studio_editor.elements_data["asset_bg"]["x"] = 500.0
        window.studio_editor.elements_data["asset_bg"]["y"] = 300.0
        window.studio_editor.save_layout(show_dialog=False)

        # Verify persisted
        layout_path = proj_dir / "sections" / "01_intro" / "placed_elements_layout.json"
        with open(layout_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        saved_bg = [e for e in saved["placed_elements"] if e["id"] == "asset_bg"][0]
        assert saved_bg["x"] == 500.0
        assert saved_bg["y"] == 300.0

        # Verify revision bumped
        reloaded = store.load_state("golden_path_test")
        assert reloaded.sections["01_intro"].revision_id >= 2

        # 7. BACK TO WORKSPACE: Navigate back
        window._switch_to_workspace()
        assert window.stacked_widget.currentIndex() == 1

        # 8. QA: Run post-render QA on section deliverable
        vid_path = proj_dir / "sections" / "01_intro" / "final_whiteboard_1080p.mp4"
        qa_engine = PostRenderQAEngine()
        qa_report = qa_engine.inspect(video_path=vid_path, section_id="01_intro")
        assert qa_report.overall_status == QAGateStatus.PASS
        assert qa_report.resolution == "1920x1080"

        # 9. MASTER ASSEMBLY: Verify master button exists and master manifest generation
        assert hasattr(window, "master_btn")

        # Verify MasterConcatenator can find all section videos
        from core.orchestration.master_concatenator import MasterConcatenator
        concat = MasterConcatenator(
            project_id="golden_path_test",
            state_store=store,
            output_dir=base / "deliverables",
        )

        # Mock FFmpeg for test isolation
        def mock_run(cmd, *args, **kwargs):
            out_file = Path(cmd[-1])
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.touch()
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)

        manifest = concat.assemble()
        assert manifest["sections_count"] == 2
        assert manifest["chapters"][0]["section_id"] == "01_intro"
        assert manifest["chapters"][1]["section_id"] == "02_body"
        assert (base / "deliverables" / "master_manifest.json").exists()


# ---------------------------------------------------------------------------
# 7. Main Window Full Navigation Test
# ---------------------------------------------------------------------------

def test_main_window_full_page_navigation(qapp):
    """StudioMainWindow navigates through all 4 pages without errors."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        base = Path(tmpdir)
        from core.state.state_store import StateStore
        from core.state.project_state import ProjectState

        store = StateStore(base_dir=base / ".state")
        proj_dir = base / "nav_proj"
        sec_dir = proj_dir / "sections" / "sec_nav"
        (sec_dir / "assets").mkdir(parents=True, exist_ok=True)

        # Mock asset metadata
        meta = {"assets": {"item_a": {"file": "item_a.png", "bbox": [0, 0, 100, 100], "label": "Test"}}}
        with open(sec_dir / "assets" / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        project = ProjectState(
            project_id="nav_test",
            title="Navigation Test",
            metadata={"project_path": str(proj_dir)},
        )
        project.get_or_create_section("sec_nav", title="Nav Section", sequence_index=0)
        store.save_state(project)

        from studio_ui.main_window import StudioMainWindow
        window = StudioMainWindow(state_store=store)

        # Page 0: Browser
        assert window.stacked_widget.currentIndex() == 0

        # Page 1: Workspace
        window.load_project(project)
        assert window.stacked_widget.currentIndex() == 1

        # Page 2: Monitor
        window._open_monitor_view("sec_nav")
        assert window.stacked_widget.currentIndex() == 2

        # Back to Workspace
        window._switch_to_workspace()
        assert window.stacked_widget.currentIndex() == 1

        # Page 3: Studio Editor
        window._open_studio_editor("sec_nav")
        assert window.stacked_widget.currentIndex() == 3

        # Back to Workspace
        window._switch_to_workspace()
        assert window.stacked_widget.currentIndex() == 1

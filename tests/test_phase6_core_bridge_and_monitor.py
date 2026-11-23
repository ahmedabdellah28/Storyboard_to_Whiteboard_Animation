"""Comprehensive Unit & Offscreen Integration Tests for Phase 6.

Validates:
1. Typed TaskProgressEvent and PipelineLogEvent dispatch on WorkflowEventBus.
2. CoreBridge Qt Signal emissions across thread boundaries.
3. CoreBridge asynchronous task execution, state updates, and cooperative cancellation.
4. ProcessingMonitorView 18-stage card initialization and lifecycle badge styling.
5. Real-time stage card progress bar, duration, error, and review updates from signals.
6. Diagnostics log stream console with log level filtering, search, and clearing.
7. StudioMainWindow smooth switching between Timeline Roster and Processing Monitor.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import List

import pytest

# Ensure offscreen Qt platform for headless test execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from studio_ui.qt import QApplication, QWidget, Qt

# Initialize singleton offscreen QApplication
_APP = QApplication.instance() or QApplication(sys.argv)

from core.contracts.studio_contracts import STAGE_DEFINITIONS, StageIdentifier
from core.orchestration.core_bridge import CoreBridge
from core.orchestration.worker_manager import CancellationToken
from core.state.project_state import ProjectState, SectionState
from core.state.state_store import StateStore
from core.state.transitions import LifecycleStatus, ReviewGateStatus, TaskLifecycleStatus
from core.state.workflow_events import (
    PipelineLogEvent,
    TaskProgressEvent,
    TaskStatusChangedEvent,
    WorkflowEventBus,
)
from studio_ui.main_window import StudioMainWindow
from studio_ui.views.processing_monitor import ProcessingMonitorView, StageCardWidget


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        base = Path(tmpdir)
        state_dir = base / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)
        sec_dir = base / "sections" / "sec_test_01"
        sec_dir.mkdir(parents=True, exist_ok=True)
        (sec_dir / "storyboard.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
        (sec_dir / "script.txt").write_text(
            "This is a verified test script with sufficient narrative content.",
            encoding="utf-8",
        )
        yield base, sec_dir


def test_task_progress_and_pipeline_log_events():
    """Verify TaskProgressEvent and PipelineLogEvent publish and dispatch correctly."""
    bus = WorkflowEventBus()
    received_prog: List[TaskProgressEvent] = []
    received_log: List[PipelineLogEvent] = []

    bus.subscribe(TaskProgressEvent, lambda ev: received_prog.append(ev))
    bus.subscribe(PipelineLogEvent, lambda ev: received_log.append(ev))

    ev_prog = TaskProgressEvent(
        project_id="test_proj",
        section_id="sec_01",
        task_id="sec.tts",
        stage_id="sec.tts",
        progress=0.45,
        message="Synthesizing audio frame 45/100",
    )
    bus.publish(ev_prog)

    assert len(received_prog) == 1
    assert received_prog[0].progress == 0.45
    assert received_prog[0].task_id == "sec.tts"

    ev_log = PipelineLogEvent(
        project_id="test_proj",
        section_id="sec_01",
        stage_id="sec.whisper",
        level="WARNING",
        message="Whisper confidence below threshold at 00:04",
    )
    bus.publish(ev_log)

    assert len(received_log) == 1
    assert received_log[0].level == "WARNING"
    assert "Whisper confidence" in received_log[0].message


def test_core_bridge_signal_emission_on_bus_events():
    """Verify CoreBridge catches WorkflowEventBus events and emits corresponding Qt Signals."""
    bus = WorkflowEventBus()
    bridge = CoreBridge(event_bus=bus)

    emitted_tasks = []
    emitted_progress = []
    emitted_logs = []

    bridge.task_status_changed.connect(
        lambda proj, sec, task, st, dur, err: emitted_tasks.append((proj, sec, task, st, dur, err))
    )
    bridge.task_progress_updated.connect(
        lambda proj, sec, task, prog, msg: emitted_progress.append((proj, sec, task, prog, msg))
    )
    bridge.pipeline_log_received.connect(
        lambda ts, lvl, sec, stg, msg: emitted_logs.append((ts, lvl, sec, stg, msg))
    )

    # 1. Publish TaskStatusChangedEvent
    bus.publish(
        TaskStatusChangedEvent(
            project_id="proj_x",
            section_id="sec_1",
            task_id="sec.extraction",
            new_status=TaskLifecycleStatus.RUNNING,
            duration_seconds=0.0,
        )
    )
    assert len(emitted_tasks) == 1
    assert emitted_tasks[0][2] == "sec.extraction"
    assert emitted_tasks[0][3] == "RUNNING"

    # 2. Publish TaskProgressEvent
    bus.publish(
        TaskProgressEvent(
            project_id="proj_x",
            section_id="sec_1",
            task_id="sec.extraction",
            progress=0.8,
            message="Contours extracted",
        )
    )
    assert len(emitted_progress) == 1
    assert emitted_progress[0][3] == 0.8

    # 3. Publish PipelineLogEvent
    bus.publish(
        PipelineLogEvent(
            project_id="proj_x",
            section_id="sec_1",
            stage_id="sec.extraction",
            level="INFO",
            message="Extracted 5 assets",
        )
    )
    assert len(emitted_logs) == 1
    assert emitted_logs[0][1] == "INFO"
    assert emitted_logs[0][4] == "Extracted 5 assets"


def test_core_bridge_start_and_cancel_section(temp_workspace):
    """Verify CoreBridge starts background pipeline and can cooperatively cancel."""
    base, sec_dir = temp_workspace
    store = StateStore(base_dir=base / ".state")
    bus = WorkflowEventBus()
    bridge = CoreBridge(state_store=store, event_bus=bus)

    # Start section pipeline
    token = bridge.start_section_pipeline(
        project_id="test_proj",
        section_id="sec_test_01",
        section_path=sec_dir,
    )

    assert isinstance(token, CancellationToken)
    assert bridge.is_section_running("sec_test_01") is True

    # Request cancellation
    cancelled = bridge.cancel_section("sec_test_01", reason="Unit test cancellation")
    assert cancelled is True
    assert token.is_cancelled is True
    assert token.reason == "Unit test cancellation"


def test_processing_monitor_stage_cards_initialization():
    """Verify ProcessingMonitorView instantiates all 18 canonical stage cards correctly."""
    bridge = CoreBridge()
    monitor = ProcessingMonitorView(bridge=bridge)

    assert len(monitor.cards) == 18
    for sdef in STAGE_DEFINITIONS.values():
        assert sdef.identifier in monitor.cards
        card = monitor.cards[sdef.identifier]
        assert card.stage_def.index == sdef.index
        assert card.stage_def.name == sdef.name
        assert card.current_status == "PENDING"


def test_processing_monitor_receives_signals_and_updates_card_state():
    """Verify stage cards update dynamically when CoreBridge signals fire."""
    bridge = CoreBridge()
    monitor = ProcessingMonitorView(bridge=bridge)

    # Set up active project and section
    project = ProjectState(project_id="test_proj")
    sec = project.get_or_create_section("sec_01")
    monitor.set_project(project, initial_section_id="sec_01")

    # 1. Emit task status RUNNING for OCR (Stage 01)
    bridge.task_status_changed.emit("test_proj", "sec_01", "sec.ocr", "RUNNING", 0.0, "")
    ocr_card = monitor.cards[StageIdentifier.OCR]
    assert ocr_card.current_status == "RUNNING"

    # 2. Emit task progress for OCR
    bridge.task_progress_updated.emit("test_proj", "sec_01", "sec.ocr", 0.65, "65% done")
    assert ocr_card.progress_bar.value() == 65

    # 3. Emit task status COMPLETED for OCR
    bridge.task_status_changed.emit("test_proj", "sec_01", "sec.ocr", "COMPLETED", 2.45, "")
    assert ocr_card.current_status == "COMPLETED"
    assert ocr_card.progress_bar.value() == 100
    assert "2.45s" in ocr_card.elapsed_label.text()

    # Overall progress should reflect 1 completed stage
    assert monitor.overall_progress_bar.value() == 1


def test_processing_monitor_review_gate_and_error_handling():
    """Verify review gate prompt button and error labels display correctly."""
    bridge = CoreBridge()
    monitor = ProcessingMonitorView(bridge=bridge)

    project = ProjectState(project_id="test_proj")
    project.get_or_create_section("sec_01")
    monitor.set_project(project, initial_section_id="sec_01")

    # 1. Stage needs review (Extraction)
    bridge.task_status_changed.emit("test_proj", "sec_01", "sec.extraction", "NEEDS_REVIEW", 0.0, "")
    card_ext = monitor.cards[StageIdentifier.EXTRACTION]
    assert card_ext.current_status == "NEEDS_REVIEW"
    # In offscreen Qt, isVisible() checks parent chain; use !isHidden() for explicit flag
    assert card_ext.review_btn.isHidden() is False

    # 2. Stage failed (TTS)
    bridge.task_status_changed.emit("test_proj", "sec_01", "sec.tts", "FAILED", 1.1, "API Timeout 504")
    card_tts = monitor.cards[StageIdentifier.TTS]
    assert card_tts.current_status == "FAILED"
    assert card_tts.error_label.isHidden() is False
    assert "API Timeout 504" in card_tts.error_label.text()


def test_processing_monitor_log_filtering_and_clearing():
    """Verify log stream console filters by level and search term."""
    bridge = CoreBridge()
    monitor = ProcessingMonitorView(bridge=bridge)

    bridge.pipeline_log_received.emit("21:00:01", "INFO", "sec_01", "sec.tts", "TTS synthesis complete")
    bridge.pipeline_log_received.emit("21:00:02", "WARNING", "sec_01", "sec.audio_qa", "Audio slightly quiet")
    bridge.pipeline_log_received.emit("21:00:03", "ERROR", "sec_01", "sec.render", "Encoder crash NVENC")

    # All logs should be present initially
    text = monitor.log_console.toPlainText()
    assert "TTS synthesis complete" in text
    assert "Audio slightly quiet" in text
    assert "Encoder crash NVENC" in text

    # Filter to ERROR only
    monitor.log_level_filter.setCurrentText("ERROR")
    filtered_text = monitor.log_console.toPlainText()
    assert "Encoder crash NVENC" in filtered_text
    assert "TTS synthesis complete" not in filtered_text

    # Search filter
    monitor.log_level_filter.setCurrentText("ALL")
    monitor.log_search_input.setText("quiet")
    search_text = monitor.log_console.toPlainText()
    assert "Audio slightly quiet" in search_text
    assert "Encoder crash" not in search_text

    # Clear logs
    monitor._clear_logs()
    assert monitor.log_console.toPlainText() == ""


def test_main_window_switching_to_monitor_and_back(temp_workspace):
    """Verify StudioMainWindow transitions seamlessly between Timeline Roster and Processing Monitor."""
    base, _ = temp_workspace
    store = StateStore(base_dir=base / ".state")
    window = StudioMainWindow(state_store=store)

    project = ProjectState(project_id="p_nav_test", title="Navigation Test")
    project.get_or_create_section("sec_01", title="Intro Section", sequence_index=0)
    store.save_state(project)

    # Load project -> workspace index 1
    window.load_project(project)
    assert window.stacked_widget.currentIndex() == 1

    # Switch to processing monitor -> index 2
    window._open_monitor_view("sec_01")
    assert window.stacked_widget.currentIndex() == 2
    assert window.processing_monitor.active_section_id == "sec_01"

    # Switch back to workspace -> index 1
    window._switch_to_workspace()
    assert window.stacked_widget.currentIndex() == 1


def test_core_bridge_resolves_project_metadata_path(temp_workspace):
    """Verify start_section_pipeline prioritizes state.metadata['project_path'] over global SECTIONS_DIR."""
    base, _ = temp_workspace
    store = StateStore(base_dir=base / ".state")

    custom_proj_dir = base / "custom_projects" / "custom_doc"
    custom_sec_dir = custom_proj_dir / "sections" / "sec_custom"
    custom_sec_dir.mkdir(parents=True, exist_ok=True)
    (custom_sec_dir / "script.txt").write_text("Test script content", encoding="utf-8")
    (custom_sec_dir / "storyboard.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    project = ProjectState(
        project_id="custom_doc",
        title="Custom Documentary",
        metadata={"project_path": str(custom_proj_dir)},
    )
    project.get_or_create_section("sec_custom", title="Custom Sec", sequence_index=0)
    store.save_state(project)

    bridge = CoreBridge(state_store=store)

    # Calling start_section_pipeline without explicit section_path should resolve from metadata
    token = bridge.start_section_pipeline(
        project_id="custom_doc",
        section_id="sec_custom",
    )
    assert token is not None
    bridge.cancel_section("sec_custom")

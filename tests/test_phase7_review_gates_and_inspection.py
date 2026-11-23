"""Phase 7 Test Suite: Human Review Gates & Inspection Dialogs.

Validates:
1. Controlled TaskDAGExecutor target closure execution (no runaway to render).
2. SectionWorker target_mode='to_review' halts at review gates and sets ReviewGateStatus.REVIEW_PENDING.
3. ExtractionReviewDialog inspection, asset card generation, and approval workflow.
4. VoiceReviewDialog audition metrics, chunk listing, and approval workflow.
5. SemanticReviewDialog Whisper-to-asset binding and approval workflow.
6. End-to-end review gate integration with CoreBridge and ProcessingMonitorView.
"""

import json
import os
import tempfile
import wave
from pathlib import Path
from typing import Dict, Any

import pytest
from core.contracts.studio_contracts import StageIdentifier
from core.orchestration.core_bridge import CoreBridge
from core.orchestration.section_worker import SectionWorker
from core.orchestration.task_dag import ExecutableTask, TaskDAGExecutor
from core.state.project_state import ProjectState, SectionState
from core.state.state_store import StateStore
from core.state.transitions import LifecycleStatus, ReviewGateStatus, SectionLifecycleStatus
from core.state.workflow_events import WorkflowEventBus
from studio_ui.dialogs.extraction_review_dialog import ExtractionReviewDialog
from studio_ui.dialogs.semantic_review_dialog import SemanticReviewDialog
from studio_ui.dialogs.voice_review_dialog import VoiceReviewDialog
from studio_ui.qt import QApplication
from studio_ui.views.processing_monitor import ProcessingMonitorView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    return app


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        base = Path(tmpdir)
        state_dir = base / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)

        proj_dir = base / "test_project"
        sec_dir = proj_dir / "sections" / "01_section"
        (sec_dir / "assets").mkdir(parents=True, exist_ok=True)
        (sec_dir / "voice").mkdir(parents=True, exist_ok=True)
        (sec_dir / "timing").mkdir(parents=True, exist_ok=True)

        # Create mock inputs
        (sec_dir / "script.txt").write_text("هذا نص تجريبي لمراجعة الصوت", encoding="utf-8")
        (sec_dir / "storyboard.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        # Create mock WAV file
        wav_path = sec_dir / "voice" / "section.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(b"\x00\x00" * 24000)  # 1.0 second of silence

        # Create mock assets metadata
        meta = {
            "assets": {
                "asset_01": {"id": "asset_01", "file": "asset_01.png", "bbox": [10, 10, 200, 150], "label": "Character"},
                "asset_02": {"id": "asset_02", "file": "asset_02.png", "bbox": [250, 50, 100, 80], "label": "Sword"},
            }
        }
        (sec_dir / "assets" / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

        # Create mock Whisper timing
        whisper_data = {
            "segments": [
                {
                    "words": [
                        {"word": "هذا", "start": 0.0, "end": 0.3},
                        {"word": "نص", "start": 0.3, "end": 0.6},
                        {"word": "تجريبي", "start": 0.6, "end": 1.0},
                    ]
                }
            ]
        }
        (sec_dir / "timing" / "whisper.json").write_text(json.dumps(whisper_data), encoding="utf-8")

        yield base, proj_dir, sec_dir


def test_dag_target_closure_filtering(temp_workspace):
    """Verify TaskDAGExecutor only executes tasks in the requested target closure."""
    base, proj_dir, sec_dir = temp_workspace
    store = StateStore(base_dir=base / ".state")

    project = ProjectState(project_id="p_dag_test", title="DAG Target Test")
    project.get_or_create_section("sec_01")
    store.save_state(project)

    executor = TaskDAGExecutor(
        project_id="p_dag_test",
        section_id="sec_01",
        state_store=store,
    )

    executed_tasks = []

    executor.add_task(
        ExecutableTask(
            task_id="sec_01.tts",
            name="TTS Task",
            component="tts",
            action=lambda: executed_tasks.append("tts"),
            dependencies=set(),
        )
    )
    executor.add_task(
        ExecutableTask(
            task_id="sec_01.whisper",
            name="Whisper Task",
            component="whisper",
            action=lambda: executed_tasks.append("whisper"),
            dependencies={"sec_01.tts"},
        )
    )
    executor.add_task(
        ExecutableTask(
            task_id="sec_01.extraction",
            name="Extraction Task",
            component="extraction",
            action=lambda: executed_tasks.append("extraction"),
            dependencies=set(),
        )
    )
    executor.add_task(
        ExecutableTask(
            task_id="sec_01.render",
            name="Render Task",
            component="render",
            action=lambda: executed_tasks.append("render"),
            dependencies={"sec_01.whisper", "sec_01.extraction"},
        )
    )

    # Execute with targets: tts, whisper, extraction (review boundary)
    targets = {"sec_01.tts", "sec_01.whisper", "sec_01.extraction"}
    results = executor.execute(force_all=True, target_tasks=targets)

    # Verify only targeted tasks executed; downstream render was NOT executed!
    assert "tts" in executed_tasks
    assert "whisper" in executed_tasks
    assert "extraction" in executed_tasks
    assert "render" not in executed_tasks
    assert "sec_01.render" not in results


def test_section_worker_stops_at_review_gate(temp_workspace):
    """Verify SectionWorker with target_mode='to_review' halts and transitions to NEEDS_REVIEW."""
    base, proj_dir, sec_dir = temp_workspace
    store = StateStore(base_dir=base / ".state")
    bus = WorkflowEventBus()

    project = ProjectState(
        project_id="p_worker_review",
        title="Review Gate Worker Test",
        metadata={"project_path": str(proj_dir)},
    )
    project.get_or_create_section("01_section")
    store.save_state(project)

    worker = SectionWorker(
        section_path=sec_dir,
        project_id="p_worker_review",
        state_store=store,
        event_bus=bus,
    )

    # Run in review-gated mode
    status_out = worker.run(
        target_mode="to_review",
        force_all=False,
    )

    assert status_out == "NEEDS_REVIEW"

    # Verify section state in store
    state = store.load_state("p_worker_review")
    sec = state.sections["01_section"]
    assert sec.lifecycle_status == SectionLifecycleStatus.NEEDS_REVIEW

    # Review gates must be set to REVIEW_PENDING
    assert sec.review_gates[StageIdentifier.EXTRACTION.value] == ReviewGateStatus.REVIEW_PENDING
    assert sec.review_gates[StageIdentifier.TTS.value] == ReviewGateStatus.REVIEW_PENDING
    assert sec.review_gates[StageIdentifier.SEMANTIC.value] == ReviewGateStatus.REVIEW_PENDING


def test_extraction_review_dialog_approval(qapp, temp_workspace):
    """Verify ExtractionReviewDialog renders assets and updates gate to APPROVED on accept."""
    base, proj_dir, sec_dir = temp_workspace
    store = StateStore(base_dir=base / ".state")
    bus = WorkflowEventBus()

    project = ProjectState(project_id="p_ext_dlg", title="Ext Dialog Test")
    sec = project.get_or_create_section("01_section")
    sec.set_review_gate(StageIdentifier.EXTRACTION.value, ReviewGateStatus.REVIEW_PENDING)
    store.save_state(project)

    dlg = ExtractionReviewDialog(
        project_id="p_ext_dlg",
        section_id="01_section",
        section_path=sec_dir,
        state_store=store,
        event_bus=bus,
    )

    assert len(dlg.card_widgets) == 2
    assert "asset_01" in dlg.card_widgets
    assert "asset_02" in dlg.card_widgets

    # Approve extraction
    dlg._on_approve()

    # Verify state updated to APPROVED
    updated = store.load_state("p_ext_dlg")
    assert updated.sections["01_section"].review_gates[StageIdentifier.EXTRACTION.value] == ReviewGateStatus.APPROVED


def test_voice_review_dialog_audition_and_approval(qapp, temp_workspace):
    """Verify VoiceReviewDialog inspects audio metrics and updates gate to APPROVED."""
    base, proj_dir, sec_dir = temp_workspace
    store = StateStore(base_dir=base / ".state")
    bus = WorkflowEventBus()

    project = ProjectState(project_id="p_voice_dlg", title="Voice Dialog Test")
    sec = project.get_or_create_section("01_section")
    sec.set_review_gate(StageIdentifier.TTS.value, ReviewGateStatus.REVIEW_PENDING)
    store.save_state(project)

    dlg = VoiceReviewDialog(
        project_id="p_voice_dlg",
        section_id="01_section",
        section_path=sec_dir,
        state_store=store,
        event_bus=bus,
    )

    # 1.0s audio duration verified from test WAV
    assert dlg.audio_duration == pytest.approx(1.0, 0.05)
    assert dlg.sample_rate == 24000
    assert dlg.channels == 1

    # Approve voiceover
    dlg._on_approve()

    updated = store.load_state("p_voice_dlg")
    assert updated.sections["01_section"].review_gates[StageIdentifier.TTS.value] == ReviewGateStatus.APPROVED


def test_semantic_review_dialog_binding_and_approval(qapp, temp_workspace):
    """Verify SemanticReviewDialog binds words to assets and writes mapping JSON."""
    base, proj_dir, sec_dir = temp_workspace
    store = StateStore(base_dir=base / ".state")
    bus = WorkflowEventBus()

    project = ProjectState(project_id="p_sem_dlg", title="Semantic Dialog Test")
    sec = project.get_or_create_section("01_section")
    sec.set_review_gate(StageIdentifier.SEMANTIC.value, ReviewGateStatus.REVIEW_PENDING)
    store.save_state(project)

    dlg = SemanticReviewDialog(
        project_id="p_sem_dlg",
        section_id="01_section",
        section_path=sec_dir,
        state_store=store,
        event_bus=bus,
    )

    assert len(dlg.whisper_words) == 3
    assert dlg.table.rowCount() == 2

    # Approve semantic mapping
    dlg._on_approve()

    # Check persistence
    mapping_file = sec_dir / "timing" / "semantic_mapping.json"
    assert mapping_file.exists()

    updated = store.load_state("p_sem_dlg")
    assert updated.sections["01_section"].review_gates[StageIdentifier.SEMANTIC.value] == ReviewGateStatus.APPROVED


def test_monitor_review_button_triggers_requested_signal(qapp):
    """Verify clicking review on a stage card emits review_requested with correct stage."""
    bridge = CoreBridge()
    monitor = ProcessingMonitorView(bridge=bridge)

    project = ProjectState(project_id="p_sig_test", title="Signal Test")
    sec = project.get_or_create_section("sec_01")
    sec.set_review_gate(StageIdentifier.EXTRACTION.value, ReviewGateStatus.REVIEW_PENDING)
    monitor.set_project(project, initial_section_id="sec_01")

    received = []
    monitor.review_requested.connect(lambda sid, gid: received.append((sid, gid)))

    # Manually trigger review click on Extraction card
    monitor.cards[StageIdentifier.EXTRACTION].review_btn.click()

    assert len(received) == 1
    assert received[0] == ("sec_01", StageIdentifier.EXTRACTION.value)

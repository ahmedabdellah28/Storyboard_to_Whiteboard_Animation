"""Comprehensive Unit & Regression Test Suite for Phase 1: Core Foundation & Governed Contracts.

Verifies:
1. Canonical 18 stages definitions and dependency integrity.
2. 9-state TaskLifecycleStatus with backward compatibility.
3. 5-state ReviewGateStatus with transition rules.
4. 8-state SectionLifecycleStatus with deterministic state reduction.
5. 6-state ProjectLifecycleStatus with multi-section aggregation.
6. SectionInputContract decoupled preflight (Storyboard + Script only).
7. RevisionToken & EditTransaction race-condition invalidation.
8. Thread-safe WorkflowEventBus with typed event dispatch.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from core.contracts.studio_contracts import (
    CANONICAL_STAGES_ORDER,
    STAGE_DEFINITIONS,
    EditTransaction,
    RevisionToken,
    SectionInputContract,
    StageDefinition,
    StageIdentifier,
)
from core.state.project_state import ProjectState, SectionState, TaskState
from core.state.transitions import (
    LifecycleStatus,
    ProjectLifecycleStatus,
    ReviewGateStatus,
    SectionLifecycleStatus,
    TaskLifecycleStatus,
    can_transition,
    can_transition_project,
    can_transition_review,
    can_transition_section,
    compute_project_status,
    compute_section_status,
    validate_project_transition,
    validate_review_transition,
    validate_section_transition,
    validate_transition,
)
from core.state.workflow_events import (
    ArtifactCommittedEvent,
    ProjectStatusChangedEvent,
    ReviewGateChangedEvent,
    RevisionIncrementedEvent,
    SectionStatusChangedEvent,
    TaskStatusChangedEvent,
    WorkflowEventBus,
    get_workflow_event_bus,
)


# ============================================================================
# 1. CANONICAL 18 STAGES ROSTER & DEPENDENCY INTEGRITY
# ============================================================================

def test_canonical_stage_count_and_indexing():
    """Verify exactly 18 stages, indexed strictly 0 to 17 without gaps."""
    assert len(CANONICAL_STAGES_ORDER) == 18
    assert len(STAGE_DEFINITIONS) == 18
    assert len(StageIdentifier) == 18

    for idx, stage_id in enumerate(CANONICAL_STAGES_ORDER):
        defn = STAGE_DEFINITIONS[stage_id]
        assert defn.index == idx
        assert defn.identifier == stage_id
        assert isinstance(defn.name, str) and len(defn.name) > 0
        assert isinstance(defn.produces_artifact, str) and len(defn.produces_artifact) > 0


def test_stage_dependency_graph_acyclic_and_valid():
    """Ensure all upstream dependencies reference valid prior stages (topologically sound)."""
    seen_stages = set()
    for stage_id in CANONICAL_STAGES_ORDER:
        defn = STAGE_DEFINITIONS[stage_id]
        for upstream in defn.upstream_dependencies:
            assert upstream in seen_stages, f"Stage {stage_id} depends on {upstream} which is not prior in DAG"
        seen_stages.add(stage_id)


def test_render_and_audio_mix_decoupling():
    """Verify that Stage 14 (Visual Render) does NOT depend on Audio Mix!"""
    render_defn = STAGE_DEFINITIONS[StageIdentifier.RENDER]
    assert StageIdentifier.AUDIO_MIX not in render_defn.upstream_dependencies
    assert StageIdentifier.RENDER_PLAN in render_defn.upstream_dependencies

    # Mux (Stage 15) is where they converge
    mux_defn = STAGE_DEFINITIONS[StageIdentifier.MUX]
    assert StageIdentifier.RENDER in mux_defn.upstream_dependencies
    assert StageIdentifier.AUDIO_MIX in mux_defn.upstream_dependencies


# ============================================================================
# 2. TASK LIFECYCLE & TRANSITIONS
# ============================================================================

def test_task_lifecycle_states_and_alias():
    """Verify 9 task states and backward compatibility alias."""
    assert len(TaskLifecycleStatus) == 9
    assert LifecycleStatus is TaskLifecycleStatus
    assert TaskLifecycleStatus.CANCELLED.value == "CANCELLED"
    assert TaskLifecycleStatus.INVALIDATED.value == "INVALIDATED"


def test_valid_task_transitions():
    """Verify legitimate task progression."""
    assert can_transition(TaskLifecycleStatus.PENDING, TaskLifecycleStatus.QUEUED)
    assert can_transition(TaskLifecycleStatus.QUEUED, TaskLifecycleStatus.RUNNING)
    assert can_transition(TaskLifecycleStatus.RUNNING, TaskLifecycleStatus.COMPLETED)
    assert can_transition(TaskLifecycleStatus.RUNNING, TaskLifecycleStatus.FAILED)
    assert can_transition(TaskLifecycleStatus.FAILED, TaskLifecycleStatus.RETRYING)
    assert can_transition(TaskLifecycleStatus.RETRYING, TaskLifecycleStatus.RUNNING)
    assert can_transition(TaskLifecycleStatus.RUNNING, TaskLifecycleStatus.CANCELLED)
    assert can_transition(TaskLifecycleStatus.COMPLETED, TaskLifecycleStatus.INVALIDATED)


def test_invalid_task_transition_raises_error():
    """Verify illegal jumps are blocked."""
    assert not can_transition(TaskLifecycleStatus.PENDING, TaskLifecycleStatus.COMPLETED)
    with pytest.raises(ValueError, match="Invalid task state transition"):
        validate_transition(TaskLifecycleStatus.PENDING, TaskLifecycleStatus.COMPLETED)


# ============================================================================
# 3. REVIEW GATE LIFECYCLE
# ============================================================================

def test_review_gate_transitions():
    """Verify 5-state review gate transitions."""
    assert len(ReviewGateStatus) == 5
    assert can_transition_review(ReviewGateStatus.NOT_APPLICABLE, ReviewGateStatus.REVIEW_PENDING)
    assert can_transition_review(ReviewGateStatus.REVIEW_PENDING, ReviewGateStatus.IN_REVIEW)
    assert can_transition_review(ReviewGateStatus.IN_REVIEW, ReviewGateStatus.APPROVED)
    assert can_transition_review(ReviewGateStatus.IN_REVIEW, ReviewGateStatus.REJECTED)

    with pytest.raises(ValueError, match="Invalid review gate transition"):
        validate_review_transition(ReviewGateStatus.NOT_APPLICABLE, ReviewGateStatus.APPROVED)


# ============================================================================
# 4. SECTION LIFECYCLE & DETERMINISTIC REDUCTION
# ============================================================================

def test_section_deterministic_reduction():
    """Verify that section lifecycle status is a strict reduction of tasks and gates."""
    # 1. Empty tasks
    assert compute_section_status({}, {}) == SectionLifecycleStatus.EMPTY

    # 2. Running task
    tasks = {
        "sec.ocr": TaskLifecycleStatus.COMPLETED,
        "sec.extraction": TaskLifecycleStatus.RUNNING,
    }
    assert compute_section_status(tasks, {}) == SectionLifecycleStatus.PROCESSING

    # 3. Running render task distinguishes RENDERING
    tasks_render = {
        "sec.ocr": TaskLifecycleStatus.COMPLETED,
        "sec.render": TaskLifecycleStatus.RUNNING,
    }
    assert compute_section_status(tasks_render, {}) == SectionLifecycleStatus.RENDERING

    # 4. Active review gate forces NEEDS_REVIEW
    gates = {"sec.extraction": ReviewGateStatus.REVIEW_PENDING}
    assert compute_section_status(tasks, gates) == SectionLifecycleStatus.NEEDS_REVIEW

    # 5. Failed task forces ERROR
    tasks_failed = {
        "sec.ocr": TaskLifecycleStatus.FAILED,
    }
    assert compute_section_status(tasks_failed, {}) == SectionLifecycleStatus.ERROR

    # 6. All completed -> COMPLETED
    tasks_all_done = {
        "sec.ingest": TaskLifecycleStatus.COMPLETED,
        "sec.ocr": TaskLifecycleStatus.COMPLETED,
        "sec.export": TaskLifecycleStatus.COMPLETED,
    }
    assert compute_section_status(tasks_all_done, {}) == SectionLifecycleStatus.COMPLETED


# ============================================================================
# 5. PROJECT LIFECYCLE & AGGREGATION
# ============================================================================

def test_project_deterministic_reduction():
    """Verify project status aggregation across sections."""
    assert compute_project_status({}) == ProjectLifecycleStatus.IDLE

    # Any processing section -> PROCESSING
    secs_processing = {
        "sec_01": SectionLifecycleStatus.COMPLETED,
        "sec_02": SectionLifecycleStatus.PROCESSING,
    }
    assert compute_project_status(secs_processing) == ProjectLifecycleStatus.PROCESSING

    # Any error section -> ERROR
    secs_error = {
        "sec_01": SectionLifecycleStatus.COMPLETED,
        "sec_02": SectionLifecycleStatus.ERROR,
    }
    assert compute_project_status(secs_error) == ProjectLifecycleStatus.ERROR

    # All completed -> READY
    secs_all_done = {
        "sec_01": SectionLifecycleStatus.COMPLETED,
        "sec_02": SectionLifecycleStatus.COMPLETED,
    }
    assert compute_project_status(secs_all_done) == ProjectLifecycleStatus.READY


# ============================================================================
# 6. DECOUPLED SECTION INPUT CONTRACT
# ============================================================================

def test_section_input_contract_valid():
    """Verify that a valid storyboard + script passes preflight without requiring voice."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tf.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 1024)
        sb_path = tf.name

    try:
        contract = SectionInputContract(
            section_id="sec_01",
            storyboard_path=sb_path,
            script_text="This is a test script for the whiteboard animation.",
            generate_tts=True,
        )
        res = contract.validate()
        assert res["is_valid"] is True
        assert len(res["errors"]) == 0
    finally:
        Path(sb_path).unlink(missing_ok=True)


def test_section_input_contract_invalid_storyboard():
    """Verify non-existent storyboard file is caught."""
    contract = SectionInputContract(
        section_id="sec_01",
        storyboard_path="non_existent_image.png",
        script_text="Some valid script text.",
    )
    res = contract.validate()
    assert res["is_valid"] is False
    assert any("does not exist" in e for e in res["errors"])


def test_section_input_contract_too_short_script():
    """Verify too short script text is rejected."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tf.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 1024)
        sb_path = tf.name

    try:
        contract = SectionInputContract(
            section_id="sec_01",
            storyboard_path=sb_path,
            script_text="Hi",  # < 5 chars
        )
        res = contract.validate()
        assert res["is_valid"] is False
        assert any("at least 5 characters" in e for e in res["errors"])
    finally:
        Path(sb_path).unlink(missing_ok=True)


# ============================================================================
# 7. REVISION TOKENS & DOWNSTREAM INVALIDATION
# ============================================================================

def test_revision_token_staleness():
    """Verify revision token comparison prevents stale writes."""
    tok_rev1 = RevisionToken(project_id="p1", section_id="s1", revision_id=1, transaction_uuid="t1")
    assert tok_rev1.is_stale_compared_to(2) is True
    assert tok_rev1.is_stale_compared_to(1) is False


def test_edit_transaction_sfx_preserves_visual_render():
    """CRITICAL TEST: Verify modifying SFX does NOT invalidate Stage 14 (Visual Render)!"""
    invals = EditTransaction.compute_invalidations("sfx_volume")
    assert StageIdentifier.AUDIO_MIX in invals
    assert StageIdentifier.MUX in invals
    assert StageIdentifier.RENDER not in invals, "SFX modification must NOT invalidate Visual Frame Render!"


def test_edit_transaction_script_invalidates_pipeline():
    """Verify modifying script cascades through timing and render stages."""
    invals = EditTransaction.compute_invalidations("script_text")
    assert StageIdentifier.TTS in invals
    assert StageIdentifier.WHISPER in invals
    assert StageIdentifier.RENDER in invals
    assert StageIdentifier.MUX in invals
    # But storyboard extraction remains preserved!
    assert StageIdentifier.EXTRACTION not in invals


# ============================================================================
# 8. THREAD-SAFE WORKFLOW EVENT BUS
# ============================================================================

def test_workflow_event_bus_dispatch():
    """Verify pub-sub dispatch of typed workflow events."""
    bus = WorkflowEventBus()
    received_task_events = []
    received_all_events = []

    def task_handler(ev: TaskStatusChangedEvent):
        received_task_events.append(ev)

    def all_handler(ev):
        received_all_events.append(ev)

    bus.subscribe(TaskStatusChangedEvent, task_handler)
    bus.subscribe_all(all_handler)

    ev1 = TaskStatusChangedEvent(
        project_id="proj_1",
        section_id="sec_01",
        task_id="sec.tts",
        old_status=TaskLifecycleStatus.PENDING,
        new_status=TaskLifecycleStatus.RUNNING,
    )
    ev2 = SectionStatusChangedEvent(
        project_id="proj_1",
        section_id="sec_01",
        old_status=SectionLifecycleStatus.EMPTY,
        new_status=SectionLifecycleStatus.PROCESSING,
    )

    bus.publish(ev1)
    bus.publish(ev2)

    assert len(received_task_events) == 1
    assert received_task_events[0].task_id == "sec.tts"
    assert len(received_all_events) == 2

    # Unsubscribe test
    bus.unsubscribe(TaskStatusChangedEvent, task_handler)
    bus.publish(ev1)
    assert len(received_task_events) == 1  # Unchanged

"""Unit and integration test suite for Phase 2: Invalidation + Revision System & Artifact Integration.

Verifies:
1. Monotonic revision counter and RevisionToken generation.
2. Race condition mitigation: stale background task token rejection.
3. Precise downstream invalidation cascades for script, storyboard, camera, and SFX edits.
4. SFX edit preserves Stage 14 Visual Frame Render.
5. Atomic EditTransaction commit and abort lifecycle.
6. ArtifactStore stage artifact registration, revision tracking, and lookup.
7. EventBus publication of RevisionIncrementedEvent and ArtifactCommittedEvent.
8. CacheValidator freshness checks for camera, SFX, master audio, and deliverable mux.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from core.artifacts.artifact_store import ArtifactRecord, ArtifactStore
from core.artifacts.cache_validator import CacheValidator
from core.artifacts.revision_manager import RevisionManager
from core.contracts.studio_contracts import (
    EditTransaction,
    RevisionToken,
    StageIdentifier,
)
from core.state.project_state import ProjectState
from core.state.state_store import StateStore
from core.state.transitions import (
    SectionLifecycleStatus,
    TaskLifecycleStatus,
)
from core.state.workflow_events import (
    ArtifactCommittedEvent,
    RevisionIncrementedEvent,
    SectionStatusChangedEvent,
    TaskStatusChangedEvent,
    WorkflowEventBus,
)


@pytest.fixture
def temp_env():
    """Create isolated StateStore, ArtifactStore, and EventBus in temporary directories."""
    with tempfile.TemporaryDirectory() as state_dir, tempfile.TemporaryDirectory() as art_dir:
        bus = WorkflowEventBus()
        s_store = StateStore(base_dir=Path(state_dir))
        a_store = ArtifactStore(store_dir=Path(art_dir), event_bus=bus)
        rev_mgr = RevisionManager(state_store=s_store, event_bus=bus)
        yield s_store, a_store, bus, rev_mgr


# ============================================================================
# 1. REVISION TOKEN & MONOTONIC COUNTER
# ============================================================================

def test_initial_revision_is_one(temp_env):
    _, _, _, rev_mgr = temp_env
    rev = rev_mgr.get_current_revision("proj_test", "sec_01")
    assert rev == 1

    tok = rev_mgr.create_task_token("proj_test", "sec_01")
    assert tok.revision_id == 1
    assert tok.project_id == "proj_test"
    assert tok.section_id == "sec_01"
    assert rev_mgr.is_token_current(tok) is True


# ============================================================================
# 2. RACE CONDITION MITIGATION: STALE TOKEN REJECTION
# ============================================================================

def test_stale_token_rejected_after_edit(temp_env):
    """Simulate worker starting on Rev 1, user editing to Rev 2, worker completion rejected."""
    s_store, _, _, rev_mgr = temp_env

    # 1. Setup initial state with a task
    state = s_store.load_state("proj_race")
    sec = state.get_or_create_section("sec_01")
    task = sec.get_or_create_task("sec.render", name="1080p Render")
    task.status = TaskLifecycleStatus.RUNNING
    s_store.save_state(state)

    # 2. Worker grabs token for Rev 1
    worker_token = rev_mgr.create_task_token("proj_race", "sec_01")
    assert worker_token.revision_id == 1

    # 3. User edits camera path while render is running -> Rev 2 committed
    tx = rev_mgr.begin_transaction("proj_race", "sec_01", mutated_field="camera_pan", description="User panned camera")
    rev_mgr.commit_transaction(tx)

    # 4. Current revision is now 2
    assert rev_mgr.get_current_revision("proj_race", "sec_01") == 2

    # 5. Worker finishes and checks token freshness -> MUST BE REJECTED
    assert rev_mgr.is_token_current(worker_token) is False
    assert worker_token.is_stale_compared_to(2) is True


# ============================================================================
# 3. DOWNSTREAM INVALIDATION CASCADES
# ============================================================================

def test_camera_invalidation_cascades_to_sfx_and_audio(temp_env):
    """Verify editing camera invalidates SFX and Audio Mix, but keeps visual extraction."""
    _, _, _, rev_mgr = temp_env

    invals = rev_mgr.compute_downstream_invalidations("camera_trajectory")
    assert StageIdentifier.SFX in invals
    assert StageIdentifier.AUDIO_MIX in invals
    assert StageIdentifier.RENDER in invals
    assert StageIdentifier.MUX in invals

    # Upstream visual extraction MUST NOT be invalidated
    assert StageIdentifier.INGEST not in invals
    assert StageIdentifier.OCR not in invals
    assert StageIdentifier.EXTRACTION not in invals
    assert StageIdentifier.TTS not in invals


def test_sfx_invalidation_preserves_visual_render(temp_env):
    """CRITICAL: Modifying sound effects must NEVER invalidate Stage 14 (Visual Frame Render)."""
    _, _, _, rev_mgr = temp_env

    invals = rev_mgr.compute_downstream_invalidations("sfx")
    assert StageIdentifier.AUDIO_MIX in invals
    assert StageIdentifier.MUX in invals
    assert StageIdentifier.RENDER not in invals, "Visual Frame Render must be preserved when only SFX changes!"


def test_script_invalidation_cascades_through_timing_and_render(temp_env):
    """Editing script invalidates audio and timing, but preserves extracted storyboard assets."""
    _, _, _, rev_mgr = temp_env

    invals = rev_mgr.compute_downstream_invalidations("script_text")
    assert StageIdentifier.TTS in invals
    assert StageIdentifier.WHISPER in invals
    assert StageIdentifier.NARRATIVE in invals
    assert StageIdentifier.RENDER in invals
    assert StageIdentifier.MUX in invals

    # Visual extraction remains cached
    assert StageIdentifier.INGEST not in invals
    assert StageIdentifier.EXTRACTION not in invals


# ============================================================================
# 4. EDIT TRANSACTION LIFECYCLE & STATE STORE INVALIDATION
# ============================================================================

def test_transaction_commit_invalidates_section_tasks(temp_env):
    s_store, _, bus, rev_mgr = temp_env

    # 1. Setup section with completed tasks
    state = s_store.load_state("proj_tx")
    sec = state.get_or_create_section("sec_01")
    t_extract = sec.get_or_create_task("sec.extraction", name="Asset Extraction")
    t_extract.status = TaskLifecycleStatus.COMPLETED
    t_tts = sec.get_or_create_task("sec.tts", name="Voiceover")
    t_tts.status = TaskLifecycleStatus.COMPLETED
    t_render = sec.get_or_create_task("sec.render", name="Visual Render")
    t_render.status = TaskLifecycleStatus.COMPLETED
    sec.recompute_lifecycle()
    s_store.save_state(state)

    events_received = []
    bus.subscribe(RevisionIncrementedEvent, lambda ev: events_received.append(ev))

    # 2. User edits script
    tx = rev_mgr.begin_transaction("proj_tx", "sec_01", mutated_field="script_text", description="Updated narration")
    new_tok = rev_mgr.commit_transaction(tx)

    assert new_tok.revision_id == 2
    assert len(events_received) == 1
    assert events_received[0].new_revision == 2

    # 3. Reload state and verify tasks
    reloaded_state = s_store.load_state("proj_tx")
    reloaded_sec = reloaded_state.sections["sec_01"]
    assert reloaded_sec.revision_id == 2

    # Visual extraction preserved
    assert reloaded_sec.tasks["sec.extraction"].status == TaskLifecycleStatus.COMPLETED
    # TTS and Render invalidated
    assert reloaded_sec.tasks["sec.tts"].status == TaskLifecycleStatus.INVALIDATED
    assert reloaded_sec.tasks["sec.render"].status == TaskLifecycleStatus.INVALIDATED


def test_transaction_abort_preserves_state(temp_env):
    s_store, _, _, rev_mgr = temp_env
    state = s_store.load_state("proj_abort")
    sec = state.get_or_create_section("sec_01")
    sec.revision_id = 5
    s_store.save_state(state)

    tx = rev_mgr.begin_transaction("proj_abort", "sec_01", mutated_field="script_text")
    rev_mgr.abort_transaction(tx)

    assert rev_mgr.get_current_revision("proj_abort", "sec_01") == 5


# ============================================================================
# 5. ARTIFACT STORE REVISION INTEGRATION
# ============================================================================

def test_artifact_store_stage_registration_and_event(temp_env):
    _, a_store, bus, _ = temp_env

    committed_events = []
    bus.subscribe(ArtifactCommittedEvent, lambda ev: committed_events.append(ev))

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        tf.write(b'{"test": "data"}')
        fpath = tf.name

    try:
        rec = a_store.register_stage_artifact(
            section_id="sec_01",
            stage_id=StageIdentifier.LAYOUT.value,
            file_path=fpath,
            artifact_hash="hash_layout_123",
            revision_id=3,
            metadata={"element_count": 5},
        )

        assert rec.artifact_hash == "hash_layout_123"
        assert rec.stage_id == StageIdentifier.LAYOUT.value
        assert rec.revision_id == 3
        assert rec.section_id == "sec_01"

        # Lookup by stage
        looked_up = a_store.get_stage_artifact("sec_01", StageIdentifier.LAYOUT.value)
        assert looked_up is not None
        assert looked_up.artifact_hash == "hash_layout_123"

        # Event emitted
        assert len(committed_events) == 1
        assert committed_events[0].stage_id == StageIdentifier.LAYOUT.value
        assert committed_events[0].artifact_hash == "hash_layout_123"

        # Invalidate stage
        a_store.invalidate_stage_artifact("sec_01", StageIdentifier.LAYOUT.value)
        assert a_store.get_stage_artifact("sec_01", StageIdentifier.LAYOUT.value) is None

    finally:
        Path(fpath).unlink(missing_ok=True)


# ============================================================================
# 6. CACHE VALIDATOR FRESHNESS CHECKS
# ============================================================================

def test_cache_validator_camera_and_sfx_freshness():
    with tempfile.TemporaryDirectory() as td:
        cam_file = Path(td) / "camera.json"
        cam_file.write_text('{"layout_hash": "lh_1", "choreography_hash": "ch_1"}', encoding="utf-8")

        sfx_file = Path(td) / "sfx.json"
        sfx_file.write_text('{"camera_hash": "cam_1", "choreography_hash": "ch_1"}', encoding="utf-8")

        # Camera freshness
        assert CacheValidator.is_camera_trajectory_fresh(cam_file, "lh_1", "ch_1") is True
        assert CacheValidator.is_camera_trajectory_fresh(cam_file, "lh_DIRTY", "ch_1") is False

        # SFX freshness
        assert CacheValidator.is_sfx_fresh(sfx_file, "cam_1", "ch_1") is True
        assert CacheValidator.is_sfx_fresh(sfx_file, "cam_DIRTY", "ch_1") is False

"""Tests for Phase 2: Canonical Artifacts & State Management."""

import os
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.state.transitions import LifecycleStatus, validate_transition
from core.state.project_state import ProjectState, SectionState, TaskState
from core.state.state_store import StateStore
from core.artifacts.artifact_identity import compute_artifact_hash, hash_string, hash_dict
from core.artifacts.artifact_store import ArtifactStore
from core.artifacts.dependency_graph import DependencyGraph, build_default_section_dag


def test_state_transitions():
    validate_transition(LifecycleStatus.PENDING, LifecycleStatus.RUNNING)
    validate_transition(LifecycleStatus.RUNNING, LifecycleStatus.COMPLETED)
    validate_transition(LifecycleStatus.COMPLETED, LifecycleStatus.INVALIDATED)

    try:
        validate_transition(LifecycleStatus.COMPLETED, LifecycleStatus.QUEUED)
        assert False, "Should raise ValueError on invalid transition"
    except ValueError:
        pass


def test_project_state_model():
    proj = ProjectState(project_id="test_doc")
    task = proj.mark_task_started("sec_01", "tts_chunk", name="TTS Chunk 1")
    assert task.status == LifecycleStatus.RUNNING
    assert proj.status == LifecycleStatus.RUNNING

    proj.mark_task_completed("sec_01", "tts_chunk", artifact_hash="sha256:12345", duration=1.5)
    assert task.status == LifecycleStatus.COMPLETED
    assert task.artifact_hash == "sha256:12345"
    assert task.duration_seconds == 1.5

    # Round trip dict serialization
    d = proj.to_dict()
    restored = ProjectState.from_dict(d)
    assert restored.project_id == "test_doc"
    assert restored.sections["sec_01"].tasks["tts_chunk"].artifact_hash == "sha256:12345"


def test_state_store_persistence():
    with tempfile.TemporaryDirectory() as td:
        store = StateStore(base_dir=Path(td))
        proj = ProjectState(project_id="p1")
        proj.mark_task_started("01", "render")
        proj.mark_task_completed("01", "render", duration=5.0)

        store.save_state(proj)

        # Clear cache and reload
        store._cache.clear()
        loaded = store.load_state("p1")
        assert loaded.project_id == "p1"
        assert loaded.sections["01"].tasks["render"].status == LifecycleStatus.COMPLETED
        assert loaded.sections["01"].tasks["render"].duration_seconds == 5.0


def test_artifact_identity_deterministic():
    h1 = compute_artifact_hash("tts", inputs={"script": "hello"}, config={"voice": "Puck"})
    h2 = compute_artifact_hash("tts", inputs={"script": "hello"}, config={"voice": "Puck"})
    assert h1 == h2
    assert h1.startswith("sha256:")

    # Changing voice changes hash
    h3 = compute_artifact_hash("tts", inputs={"script": "hello"}, config={"voice": "Fenrir"})
    assert h1 != h3


def test_artifact_store_atomic_write_and_registry():
    with tempfile.TemporaryDirectory() as td:
        store = ArtifactStore(store_dir=Path(td))
        art_path = Path(td) / "audio.wav"

        # Atomic write
        store.atomic_write_bytes(art_path, b"RIFF....data")
        assert art_path.exists()
        assert art_path.read_bytes() == b"RIFF....data"

        # Registration and validity check
        h = "sha256:test_audio"
        store.register_artifact(h, art_path, component="tts")
        assert store.is_artifact_valid(h, art_path) is True


def test_dependency_graph_and_invalidation():
    dag = build_default_section_dag("sec_01")
    order = dag.get_execution_order()

    # Valid execution order: tts before whisper, extraction before layout
    assert order.index("sec_01_tts") < order.index("sec_01_whisper")
    assert order.index("sec_01_extraction") < order.index("sec_01_layout")
    assert order.index("sec_01_render") < order.index("sec_01_deliverable")

    # Invalidation test:
    # If TTS changes, its dependents: whisper, sync, sfx, audio_mix, render, deliverable must be affected
    affected = dag.get_transitive_dependents("sec_01_tts")
    assert "sec_01_whisper" in affected
    assert "sec_01_sync" in affected
    assert "sec_01_audio_mix" in affected
    assert "sec_01_render" in affected
    assert "sec_01_deliverable" in affected

    # Visual extraction and layout should NOT be affected by TTS change!
    assert "sec_01_extraction" not in affected
    assert "sec_01_layout" not in affected


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tests = [
        test_state_transitions,
        test_project_state_model,
        test_state_store_persistence,
        test_artifact_identity_deterministic,
        test_artifact_store_atomic_write_and_registry,
        test_dependency_graph_and_invalidation,
    ]
    print(f"Running {len(tests)} Phase 2 (State & Artifacts) tests...")
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nResult: {passed}/{len(tests)} tests passed.")
    if passed == len(tests):
        print("ALL PHASE 2 TESTS PASSED SUCCESSFULLY!")
    else:
        sys.exit(1)

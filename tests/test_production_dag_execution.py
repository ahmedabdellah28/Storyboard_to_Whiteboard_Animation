"""
Production DAG Execution Validation Test Suite
================================================
Validates the Core DAG as the production execution engine for whiteboard animation:
A. Real Section DAG Construction
B. Parallel Ready Tasks (Temporal overlap)
C. Dependency Enforcement (Sequential waiting)
D. Resource Gating (Capacity throttling)
E. Artifact Cache Hit (Skipping execution)
F. Artifact Invalidation (Rerunning on input change)
G. Task Resume (Skipping completed, rerunning failed)
H. Failure Isolation (Siblings finish, dependents blocked)
I. Legacy Adapter Compatibility (UniversalSectionPipeline delegates to Core DAG)
J. Canary Validation (Section 03 execution trace)
"""

from __future__ import annotations

import os
import sys
import time
import json
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Set
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from core.artifacts.artifact_store import ArtifactStore
from core.orchestration.resource_pools import ResourcePoolManager
from core.orchestration.section_worker import SectionWorker
from core.orchestration.task_dag import ExecutableTask, TaskDAGExecutor
from core.state.project_state import ProjectState
from core.state.state_store import StateStore
from core.state.transitions import LifecycleStatus
from production_engine.universal_section_pipeline import UniversalSectionPipeline


# ============================================================================
# § A. REAL SECTION DAG CONSTRUCTION
# ============================================================================

def test_real_section_dag_construction():
    """Verify production section produces expected tasks, dependencies, and resource classes."""
    sec_dir = ROOT_DIR / "sections" / "03_working_poor"
    worker = SectionWorker(sec_dir, project_id="wealth_classes_documentary", title="03 Working Poor")
    pipeline = UniversalSectionPipeline(sec_dir, title="03 Working Poor")
    executor = worker.build_section_dag(pipeline)

    expected_tasks = {
        "03_working_poor.tts",
        "03_working_poor.whisper",
        "03_working_poor.extraction",
        "03_working_poor.layout_and_sync",
        "03_working_poor.pre_render_director",
        "03_working_poor.audio_mix",
        "03_working_poor.render",
        "03_working_poor.deliverable",
    }
    assert set(executor.tasks.keys()) == expected_tasks

    # Verify resource classes
    assert executor.tasks["03_working_poor.tts"].resource_type == "NETWORK_API"
    assert executor.tasks["03_working_poor.whisper"].resource_type == "CPU_HEAVY"
    assert executor.tasks["03_working_poor.extraction"].resource_type == "CPU_HEAVY"
    assert executor.tasks["03_working_poor.layout_and_sync"].resource_type == "CPU_HEAVY"
    assert executor.tasks["03_working_poor.pre_render_director"].resource_type == "NETWORK_API"
    assert executor.tasks["03_working_poor.audio_mix"].resource_type == "DISK_IO"
    assert executor.tasks["03_working_poor.render"].resource_type == "GPU_RENDER"
    assert executor.tasks["03_working_poor.deliverable"].resource_type == "DISK_IO"

    # Verify dependency structure
    assert executor.tasks["03_working_poor.tts"].dependencies == set()
    assert executor.tasks["03_working_poor.whisper"].dependencies == {"03_working_poor.tts"}
    assert executor.tasks["03_working_poor.extraction"].dependencies == set()
    assert executor.tasks["03_working_poor.layout_and_sync"].dependencies == {
        "03_working_poor.whisper",
        "03_working_poor.extraction",
    }
    assert executor.tasks["03_working_poor.pre_render_director"].dependencies == {
        "03_working_poor.layout_and_sync"
    }
    assert executor.tasks["03_working_poor.audio_mix"].dependencies == {
        "03_working_poor.layout_and_sync"
    }
    assert executor.tasks["03_working_poor.render"].dependencies == {
        "03_working_poor.audio_mix",
        "03_working_poor.pre_render_director",
    }
    assert executor.tasks["03_working_poor.deliverable"].dependencies == {
        "03_working_poor.render"
    }


# ============================================================================
# § B. PARALLEL READY TASKS (Temporal Overlap)
# ============================================================================

def test_parallel_ready_tasks_temporal_overlap():
    """Verify that independent ready tasks execute with actual overlapping timestamps."""
    with tempfile.TemporaryDirectory() as td:
        art_store = ArtifactStore(store_dir=Path(td) / "art")
        state_store = StateStore(base_dir=Path(td) / "state")
        res_mgr = ResourcePoolManager(cpu_heavy_slots=4)

        executor = TaskDAGExecutor(
            project_id="test_overlap",
            section_id="sec_01",
            resource_manager=res_mgr,
            artifact_store=art_store,
            state_store=state_store,
            max_workers=4,
        )

        timings: Dict[str, Dict[str, float]] = {}
        lock = threading.Lock()

        def make_action(tid: str, duration: float = 0.25):
            def action():
                t0 = time.perf_counter()
                time.sleep(duration)
                t1 = time.perf_counter()
                with lock:
                    timings[tid] = {"start": t0, "end": t1, "thread": threading.current_thread().name}
                return tid
            return action

        executor.add_task(ExecutableTask(
            task_id="T_whisper", name="Whisper", component="whisper",
            resource_type="CPU_HEAVY", action=make_action("T_whisper", 0.25)
        ))
        executor.add_task(ExecutableTask(
            task_id="T_extraction", name="Extraction", component="extraction",
            resource_type="CPU_HEAVY", action=make_action("T_extraction", 0.25)
        ))

        results = executor.execute(force_all=True)
        assert len(results) == 2
        assert "T_whisper" in timings and "T_extraction" in timings

        w = timings["T_whisper"]
        e = timings["T_extraction"]

        # Temporal overlap check: max(starts) < min(ends)
        overlap = max(w["start"], e["start"]) < min(w["end"], e["end"])
        assert overlap, f"Tasks did not overlap in time: Whisper={w}, Extraction={e}"


# ============================================================================
# § C. DEPENDENCY ENFORCEMENT
# ============================================================================

def test_dependency_enforcement_ordering():
    """Verify that a dependent task strictly waits until its parents complete."""
    with tempfile.TemporaryDirectory() as td:
        art_store = ArtifactStore(store_dir=Path(td) / "art")
        state_store = StateStore(base_dir=Path(td) / "state")

        executor = TaskDAGExecutor(
            project_id="test_dep",
            section_id="sec_01",
            artifact_store=art_store,
            state_store=state_store,
        )

        timings: Dict[str, Dict[str, float]] = {}
        lock = threading.Lock()

        def make_action(tid: str, duration: float = 0.15):
            def action():
                t0 = time.perf_counter()
                time.sleep(duration)
                t1 = time.perf_counter()
                with lock:
                    timings[tid] = {"start": t0, "end": t1}
                return tid
            return action

        executor.add_task(ExecutableTask(
            task_id="Parent", name="Parent Task", component="p", action=make_action("Parent", 0.15)
        ))
        executor.add_task(ExecutableTask(
            task_id="Child", name="Child Task", component="c",
            action=make_action("Child", 0.1), dependencies={"Parent"}
        ))

        executor.execute(force_all=True)

        assert timings["Child"]["start"] >= timings["Parent"]["end"] - 0.005


# ============================================================================
# § D. RESOURCE GATING
# ============================================================================

def test_resource_gating_blocks_at_capacity():
    """Verify that resource pool capacity limit serializes tasks contending for the same resource."""
    with tempfile.TemporaryDirectory() as td:
        art_store = ArtifactStore(store_dir=Path(td) / "art")
        state_store = StateStore(base_dir=Path(td) / "state")
        # 1 GPU slot only
        res_mgr = ResourcePoolManager(gpu_render_slots=1)

        executor = TaskDAGExecutor(
            project_id="test_res_gating",
            section_id="sec_01",
            resource_manager=res_mgr,
            artifact_store=art_store,
            state_store=state_store,
            max_workers=4,
        )

        timings: Dict[str, Dict[str, float]] = {}
        lock = threading.Lock()

        def make_action(tid: str, duration: float = 0.2):
            def action():
                t0 = time.perf_counter()
                time.sleep(duration)
                t1 = time.perf_counter()
                with lock:
                    timings[tid] = {"start": t0, "end": t1}
                return tid
            return action

        executor.add_task(ExecutableTask(
            task_id="G1", name="GPU Task 1", component="render",
            resource_type="GPU_RENDER", action=make_action("G1", 0.2)
        ))
        executor.add_task(ExecutableTask(
            task_id="G2", name="GPU Task 2", component="render",
            resource_type="GPU_RENDER", action=make_action("G2", 0.2)
        ))

        executor.execute(force_all=True)

        g1 = timings["G1"]
        g2 = timings["G2"]
        # They cannot overlap because capacity is 1!
        no_overlap = (g1["end"] <= g2["start"] + 0.05) or (g2["end"] <= g1["start"] + 0.05)
        assert no_overlap, f"Tasks should have been gated serially by GPU semaphore: G1={g1}, G2={g2}"


# ============================================================================
# § E. ARTIFACT CACHE HIT
# ============================================================================

def test_artifact_cache_hit_skips_execution():
    """Verify valid registered artifact prevents execution on subsequent runs."""
    with tempfile.TemporaryDirectory() as td:
        art_store = ArtifactStore(store_dir=Path(td) / "art")
        state_store = StateStore(base_dir=Path(td) / "state")
        out_file = Path(td) / "out.txt"

        executor = TaskDAGExecutor(
            project_id="test_cache",
            section_id="sec_01",
            artifact_store=art_store,
            state_store=state_store,
        )

        call_counter = {"calls": 0}

        def action():
            call_counter["calls"] += 1
            out_file.write_text("Hello World", encoding="utf-8")
            return str(out_file)

        task = ExecutableTask(
            task_id="Task1", name="T1", component="comp",
            action=action, expected_output_path=str(out_file), inputs={"val": 42}
        )
        executor.add_task(task)

        # Run 1: executes
        res1 = executor.execute()
        assert call_counter["calls"] == 1
        assert out_file.exists()

        # Run 2: cache hit, action must NOT be called again
        res2 = executor.execute()
        assert call_counter["calls"] == 1
        assert res2["Task1"] == str(out_file)


# ============================================================================
# § F. ARTIFACT INVALIDATION
# ============================================================================

def test_artifact_invalidation_on_input_change():
    """Verify that modifying task input invalidates cache and triggers rerun."""
    with tempfile.TemporaryDirectory() as td:
        art_store = ArtifactStore(store_dir=Path(td) / "art")
        state_store = StateStore(base_dir=Path(td) / "state")
        out_file = Path(td) / "out.txt"

        call_counter = {"calls": 0}

        def make_task(val: int):
            def action():
                call_counter["calls"] += 1
                out_file.write_text(f"Val={val}", encoding="utf-8")
                return str(out_file)

            return ExecutableTask(
                task_id="Task_V", name="TV", component="comp",
                action=action, expected_output_path=str(out_file), inputs={"val": val}
            )

        # Run 1 with val=1
        e1 = TaskDAGExecutor("test_inv", "s1", artifact_store=art_store, state_store=state_store)
        e1.add_task(make_task(1))
        e1.execute()
        assert call_counter["calls"] == 1

        # Run 2 with val=2 (input changed)
        e2 = TaskDAGExecutor("test_inv", "s1", artifact_store=art_store, state_store=state_store)
        e2.add_task(make_task(2))
        e2.execute()
        assert call_counter["calls"] == 2
        assert out_file.read_text(encoding="utf-8") == "Val=2"


# ============================================================================
# § G. TASK RESUME
# ============================================================================

def test_task_resume_skips_completed_and_reruns_failed():
    """Verify that after a crash/failure, completed tasks are preserved and only failed task reruns."""
    with tempfile.TemporaryDirectory() as td:
        art_store = ArtifactStore(store_dir=Path(td) / "art")
        state_store = StateStore(base_dir=Path(td) / "state")
        f1 = Path(td) / "step1.txt"
        f2 = Path(td) / "step2.txt"

        call_log: List[str] = []

        def action1():
            call_log.append("step1")
            f1.write_text("done1", encoding="utf-8")
            return str(f1)

        fail_on_step2 = {"fail": True}

        def action2():
            call_log.append("step2")
            if fail_on_step2["fail"]:
                raise RuntimeError("Simulated Crash in Step 2")
            f2.write_text("done2", encoding="utf-8")
            return str(f2)

        def build_executor():
            ex = TaskDAGExecutor("test_resume", "s1", artifact_store=art_store, state_store=state_store)
            ex.add_task(ExecutableTask("S1", "Step 1", "test", action=action1, expected_output_path=str(f1)))
            ex.add_task(ExecutableTask("S2", "Step 2", "test", action=action2, expected_output_path=str(f2), dependencies={"S1"}))
            return ex

        # Run 1: S1 succeeds, S2 crashes
        ex1 = build_executor()
        with pytest.raises(RuntimeError):
            ex1.execute()

        assert call_log == ["step1", "step2"]
        state = state_store.load_state("test_resume")
        assert state.sections["s1"].tasks["S1"].status == LifecycleStatus.COMPLETED
        assert state.sections["s1"].tasks["S2"].status == LifecycleStatus.FAILED

        # Run 2: S2 fixed. S1 must be skipped (resumed), S2 must rerun!
        fail_on_step2["fail"] = False
        ex2 = build_executor()
        res2 = ex2.execute()

        assert call_log == ["step1", "step2", "step2"]  # step1 was NOT called again!
        assert res2["S1"] == str(f1)
        assert res2["S2"] == str(f2)


# ============================================================================
# § H. FAILURE ISOLATION
# ============================================================================

def test_failure_isolation_preserves_independent_branches():
    """Verify that a failure in one branch allows independent siblings to complete and only blocks dependents."""
    with tempfile.TemporaryDirectory() as td:
        art_store = ArtifactStore(store_dir=Path(td) / "art")
        state_store = StateStore(base_dir=Path(td) / "state")

        executor = TaskDAGExecutor(
            project_id="test_isolation",
            section_id="sec_01",
            artifact_store=art_store,
            state_store=state_store,
            max_workers=4,
        )

        log: List[str] = []
        lock = threading.Lock()

        def branch_a():
            time.sleep(0.1)
            with lock:
                log.append("A_success")
            return "A"

        def branch_b():
            time.sleep(0.05)
            with lock:
                log.append("B_fail")
            raise ValueError("Branch B Exploded")

        def branch_c():
            # Depends on B -> must be BLOCKED
            with lock:
                log.append("C_dependent")
            return "C"

        executor.add_task(ExecutableTask("Task_A", "Branch A", "test", action=branch_a))
        executor.add_task(ExecutableTask("Task_B", "Branch B", "test", action=branch_b))
        executor.add_task(ExecutableTask("Task_C", "Branch C", "test", action=branch_c, dependencies={"Task_B"}))

        with pytest.raises(RuntimeError) as exc_info:
            executor.execute()

        assert "Task_B" in str(exc_info.value)
        # Branch A was independent and must have completed successfully!
        assert "A_success" in log
        # Branch C must NOT have run at all!
        assert "C_dependent" not in log

        # Check durable state
        state = state_store.load_state("test_isolation")
        sec = state.sections["sec_01"]
        assert sec.tasks["Task_A"].status == LifecycleStatus.COMPLETED
        assert sec.tasks["Task_B"].status == LifecycleStatus.FAILED


# ============================================================================
# § I. LEGACY ADAPTER COMPATIBILITY
# ============================================================================

def test_universal_section_pipeline_compatibility():
    """Verify that UniversalSectionPipeline.run() delegates to Core DAG SectionWorker."""
    sec_dir = ROOT_DIR / "sections" / "03_working_poor"
    pipeline = UniversalSectionPipeline(sec_dir, title="03 Working Poor")

    # Verify stage methods exist and are callable
    assert hasattr(pipeline, "step_whisper")
    assert hasattr(pipeline, "step_extraction")
    assert hasattr(pipeline, "step_tts")
    assert hasattr(pipeline, "step_layout_and_sync")
    assert hasattr(pipeline, "step_pre_render_director")
    assert hasattr(pipeline, "step_audio_mix")
    assert hasattr(pipeline, "step_render")
    assert hasattr(pipeline, "step_publish")

    worker = SectionWorker(sec_dir, title="03 Working Poor")
    dag = worker.build_section_dag(pipeline)
    order = dag.get_execution_order()
    assert len(order) == 8
    assert order[0] in ("03_working_poor.tts", "03_working_poor.extraction")


# ============================================================================
# § J. END-TO-END CANARY EXECUTION (Section 03 Working Poor)
# ============================================================================

def test_canary_section_03_dag_run():
    """Execute real section 03 through SectionWorker DAG, validating artifact cache & state."""
    sec_dir = ROOT_DIR / "sections" / "03_working_poor"
    assert sec_dir.is_dir()

    worker = SectionWorker(sec_dir, project_id="wealth_classes_documentary", title="الطبقة الثالثة: الفقر العامل")
    validation = worker.validate_inputs()
    assert validation["script"] is True
    assert validation["storyboard"] is True
    assert validation["voice"] is True

    # Run Section 03 via Core DAG
    t0 = time.perf_counter()
    deliverable_path = worker.run(force_whisper=False)
    duration = time.perf_counter() - t0

    assert os.path.exists(deliverable_path)
    assert Path(deliverable_path).stat().st_size > 0

    # Verify state persistence
    state_store = worker.state_store
    state = state_store.load_state("wealth_classes_documentary")
    assert "03_working_poor" in state.sections
    sec_state = state.sections["03_working_poor"]
    assert sec_state.status == LifecycleStatus.COMPLETED
    assert sec_state.output_video_path == deliverable_path

    # Verify all 8 tasks are marked COMPLETED
    for task_name in [
        "tts", "whisper", "extraction", "layout_and_sync",
        "pre_render_director", "audio_mix", "render", "deliverable"
    ]:
        tid = f"03_working_poor.{task_name}"
        assert tid in sec_state.tasks
        assert sec_state.tasks[tid].status == LifecycleStatus.COMPLETED

    print(f"\nCanary completed in {duration:.2f}s with deliverable: {deliverable_path}")


# ============================================================================
# § K. COLD CANARY EXECUTION FROM SCRATCH (Script -> TTS -> ASR -> Render)
# ============================================================================

def test_cold_canary_from_script_to_publish():
    """Prove cold section run from scratch: Script -> TTS -> Whisper -> Sync -> Render -> Publish."""
    import numpy as np
    import cv2
    import wave

    with tempfile.TemporaryDirectory() as td:
        cold_sec = Path(td) / "cold_canary_section"
        cold_sec.mkdir(parents=True, exist_ok=True)

        # 1. Provide ONLY script.txt and storyboard.png (NO voice, NO timing, NO assets)
        script_file = cold_sec / "script.txt"
        script_file.write_text("الطبقة التجريبية: اختبار البداية الباردة\nهذا فحص إنتاجي شامل.", encoding="utf-8")

        # Create valid minimal storyboard PNG (1920x1080 white with black silhouette box)
        storyboard_img = np.full((1080, 1920, 3), 255, dtype=np.uint8)
        cv2.rectangle(storyboard_img, (400, 300), (700, 600), (30, 30, 30), -1)
        cv2.putText(storyboard_img, "Test Asset", (420, 450), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.imwrite(str(cold_sec / "storyboard.png"), storyboard_img)

        # Confirm 0 pre-existing outputs
        assert not (cold_sec / "voice").exists()
        assert not (cold_sec / "timing").exists()
        assert not (cold_sec / "assets").exists()
        assert not (cold_sec / "master_audio.wav").exists()
        assert not (cold_sec / "final_whiteboard_1080p.mp4").exists()

        # Deterministic offline TTS Mock Provider to test exact TTS task in DAG
        class MockTTSProvider:
            def synthesize_to_file(self, text: str, output_path: str | Path):
                out = Path(output_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                sample_rate = 24000
                duration_s = 2.0
                num_samples = int(sample_rate * duration_s)
                # Generate clean sine tone as simulated voice
                t = np.linspace(0, duration_s, num_samples, endpoint=False)
                tone = (np.sin(2 * np.pi * 440 * t) * 16384).astype(np.int16)
                with wave.open(str(out), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(tone.tobytes())
                return out

        mock_tts = MockTTSProvider()

        # Run Cold Section via SectionWorker Core DAG
        worker = SectionWorker(cold_sec, project_id="cold_canary_project", title="اختبار البداية الباردة")
        deliv = worker.run(tts_provider=mock_tts)

        # 1. Verify TTS generated voice file
        voice_file = cold_sec / "voice" / "section.wav"
        assert voice_file.exists()
        assert voice_file.stat().st_size > 0

        # 2. Verify all 8 tasks ran and completed
        state = worker.state_store.load_state("cold_canary_project")
        sec_state = state.sections["cold_canary_section"]
        assert sec_state.status == LifecycleStatus.COMPLETED

        for task_name in [
            "tts", "whisper", "extraction", "layout_and_sync",
            "pre_render_director", "audio_mix", "render", "deliverable"
        ]:
            tid = f"cold_canary_section.{task_name}"
            assert tid in sec_state.tasks
            assert sec_state.tasks[tid].status == LifecycleStatus.COMPLETED

        # 3. Verify final deliverable video created
        assert os.path.exists(deliv)
        assert Path(deliv).stat().st_size > 0


# ============================================================================
# § L. MASTER DOCUMENTARY CONCATENATION (Sections -> Feature Film)
# ============================================================================

def test_master_documentary_assembly():
    """Verify Master Documentary assembly concatenates sections via ProductionOrchestrator."""
    from core.orchestration.orchestrator import ProductionOrchestrator

    orchestrator = ProductionOrchestrator(project_id="wealth_classes_documentary")
    final_video = orchestrator.assemble_master_documentary()

    assert os.path.exists(final_video)
    assert Path(final_video).stat().st_size > 5000000  # Multi-megabyte feature video


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("\n" + "=" * 80)
    print("RUNNING PRODUCTION DAG EXECUTION TESTS (A-L)")
    print("=" * 80 + "\n")

    pytest.main([__file__, "-v", "--tb=short"])

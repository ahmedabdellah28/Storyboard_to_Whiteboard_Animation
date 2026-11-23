"""Unit and integration test suite for Phase 4: ResourceGovernor, WorkerManager & Cancellation.

Verifies:
1. ResourceGovernor dynamic hardware calculations for LOW, BALANCED, PERFORMANCE, and AUTO.
2. Semaphore pool adaptation to calculated hardware budgets.
3. GpuDeviceLock mutual exclusion and singleton behavior.
4. CancellationToken cooperative abort and OperationCancelledException.
5. WorkerManager multi-section submission, status inspection, and selective cancellation.
6. TaskDAGExecutor cooperative abortion on cancel token.
7. Clean import of core.render_engine without legacy sys.path manipulation.
"""

from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path
import pytest

from core.orchestration.resource_governor import (
    GpuDeviceLock,
    ResourceBudget,
    ResourceGovernor,
    ResourceProfile,
)
from core.orchestration.resource_pools import ResourcePoolManager
from core.orchestration.task_dag import ExecutableTask, TaskDAGExecutor
from core.orchestration.worker_manager import (
    CancellationToken,
    OperationCancelledException,
    WorkerManager,
    WorkerPriority,
)
from core.state.project_state import ProjectState
from core.state.state_store import StateStore
from core.state.transitions import TaskLifecycleStatus


# ============================================================================
# 1. RESOURCE GOVERNOR BUDGETS
# ============================================================================

def test_resource_governor_profiles():
    # LOW profile
    budget_low = ResourceGovernor.calculate_budget(ResourceProfile.LOW)
    assert budget_low.max_concurrent_tasks == 1
    assert budget_low.cpu_heavy_slots == 1
    assert budget_low.preview_cache_mb == 512
    assert budget_low.render_encoder == "libx264"

    # BALANCED profile
    budget_balanced = ResourceGovernor.calculate_budget(ResourceProfile.BALANCED)
    assert budget_balanced.max_concurrent_tasks >= 2
    assert budget_balanced.preview_cache_mb == 1536

    # PERFORMANCE profile
    budget_perf = ResourceGovernor.calculate_budget(ResourceProfile.PERFORMANCE)
    assert budget_perf.max_concurrent_tasks >= 2
    assert budget_perf.disk_io_slots == 4
    assert budget_perf.preview_cache_mb == 4096

    # AUTO profile
    budget_auto = ResourceGovernor.calculate_budget(ResourceProfile.AUTO)
    assert budget_auto.max_concurrent_tasks >= 1
    assert budget_auto.cpu_heavy_slots >= 1
    assert budget_auto.os_reserve_gb >= 2.0


def test_resource_governor_pool_adaptation():
    gov = ResourceGovernor(profile=ResourceProfile.LOW)
    pool = ResourcePoolManager()

    gov.apply_to_resource_pool(pool)

    # Verify semaphores adapted
    sem_cpu = pool.get_semaphore("CPU_HEAVY")
    assert sem_cpu.acquire(blocking=False) is True
    # Can't acquire second since LOW profile gives exactly 1 slot!
    assert sem_cpu.acquire(blocking=False) is False
    sem_cpu.release()


# ============================================================================
# 2. GPU DEVICE MUTEX
# ============================================================================

def test_gpu_device_lock_singleton_and_concurrency():
    lock1 = GpuDeviceLock()
    lock2 = GpuDeviceLock()
    assert lock1 is lock2

    acquired_first = lock1.acquire(blocking=False)
    assert acquired_first is True

    # Second thread should fail to acquire with 0 timeout
    second_acquired = False
    def try_acquire():
        nonlocal second_acquired
        second_acquired = lock2.acquire(blocking=False)

    t = threading.Thread(target=try_acquire)
    t.start()
    t.join()

    assert second_acquired is False

    lock1.release()


# ============================================================================
# 3. CANCELLATION TOKEN
# ============================================================================

def test_cancellation_token_lifecycle():
    tok = CancellationToken()
    assert tok.is_cancelled is False

    tok.cancel("User cancelled render")
    assert tok.is_cancelled is True
    assert tok.reason == "User cancelled render"

    with pytest.raises(OperationCancelledException, match="User cancelled render"):
        tok.throw_if_cancelled()


# ============================================================================
# 4. WORKER MANAGER CONCURRENCY & CANCELLATION
# ============================================================================

def test_worker_manager_submission_and_cancel():
    wm = WorkerManager(max_workers=2)

    completed_flag = threading.Event()

    def long_task(cancel_token: CancellationToken):
        for _ in range(20):
            if cancel_token.is_cancelled:
                return "CANCELLED_EXIT"
            time.sleep(0.05)
        completed_flag.set()
        return "SUCCESS"

    fut = wm.submit_section("sec_01", long_task)
    assert wm.is_section_running("sec_01") is True

    time.sleep(0.1)
    # Cancel section 01
    assert wm.cancel_section("sec_01", reason="Test cancel") is True

    res = fut.result(timeout=2.0)
    assert res == "CANCELLED_EXIT"
    assert wm.is_section_running("sec_01") is False

    wm.shutdown(wait=False)


# ============================================================================
# 5. TASK DAG EXECUTOR CANCELLATION INTEGRATION
# ============================================================================

def test_task_dag_executor_cancellation():
    with tempfile.TemporaryDirectory() as td:
        s_store = StateStore(base_dir=Path(td))
        tok = CancellationToken()

        executor = TaskDAGExecutor(
            project_id="proj_cancel",
            section_id="sec_01",
            state_store=s_store,
            cancel_token=tok,
        )

        def task_step_1():
            # Trigger cancellation during first task
            tok.cancel("Aborted mid-DAG")
            return "done_step_1"

        def task_step_2():
            return "should_not_run"

        executor.add_task(
            ExecutableTask(task_id="step_1", name="Step 1", component="test", action=task_step_1)
        )
        executor.add_task(
            ExecutableTask(
                task_id="step_2",
                name="Step 2",
                component="test",
                action=task_step_2,
                dependencies={"step_1"},
            )
        )

        res = executor.execute()

        # Step 1 may finish, but step 2 must be cancelled
        state = s_store.load_state("proj_cancel")
        sec = state.sections["sec_01"]

        assert sec.tasks["step_2"].status == TaskLifecycleStatus.CANCELLED


# ============================================================================
# 6. STANDALONE RENDER ENGINE IMPORT
# ============================================================================

def test_render_engine_standalone_import():
    """Verify core.render_engine imports cleanly without needing kivy directory."""
    from core.render_engine.render.renderer import Renderer
    from core.render_engine.pipeline.dynamic_whiteboard_renderer import DynamicWhiteboardRenderer
    from core.render_engine.render.hand_compositor import load_hand_asset_bgra
    from core.render_engine.processing.whiteboard_processor import WhiteboardProcessor

    assert Renderer is not None
    assert DynamicWhiteboardRenderer is not None
    assert load_hand_asset_bgra is not None
    assert WhiteboardProcessor is not None

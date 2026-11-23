"""Executable task DAG runner with parallel dispatch, resource gating, and artifact caching."""

from __future__ import annotations

import concurrent.futures
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from core.artifacts.artifact_identity import compute_artifact_hash
from core.artifacts.artifact_store import ArtifactStore, get_artifact_store
from core.orchestration.resource_pools import ResourcePoolManager, get_resource_manager
from core.state.project_state import ProjectState
from core.state.state_store import StateStore, get_state_store
from core.state.transitions import LifecycleStatus, TaskLifecycleStatus
from core.state.workflow_events import (
    TaskStatusChangedEvent,
    WorkflowEventBus,
    get_workflow_event_bus,
)
from core.telemetry.counters import get_telemetry_counters
from core.telemetry.timer import TaskTimer


@dataclass
class ExecutableTask:
    task_id: str
    name: str
    component: str
    resource_type: str = "DEFAULT"
    action: Optional[Callable[[], Any]] = None
    expected_output_path: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    section_id: str = ""
    retry_policy: Optional[Dict[str, Any]] = None
    state: LifecycleStatus = LifecycleStatus.PENDING

    def __init__(
        self,
        task_id: str,
        name: str,
        component: str,
        resource_type: str = "DEFAULT",
        action: Optional[Callable[[], Any]] = None,
        expected_output_path: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[Set[str]] = None,
        section_id: str = "",
        retry_policy: Optional[Dict[str, Any]] = None,
        resource_class: Optional[str] = None,
        state: LifecycleStatus = LifecycleStatus.PENDING,
    ) -> None:
        self.task_id = task_id
        self.name = name
        self.component = component
        self.resource_type = resource_class or resource_type
        self.action = action
        self.expected_output_path = expected_output_path
        self.inputs = inputs or {}
        self.config = config or {}
        self.dependencies = set(dependencies) if dependencies else set()
        self.section_id = section_id
        self.retry_policy = retry_policy
        self.state = state

    @property
    def resource_class(self) -> str:
        return self.resource_type

    @property
    def artifact_identity(self) -> str:
        return compute_artifact_hash(
            component=self.component,
            inputs=self.inputs,
            config=self.config,
        )


class TaskDAGExecutor:
    """Executes a directed graph of production tasks with parallel dispatch, caching, and resource limits."""

    def __init__(
        self,
        project_id: str,
        section_id: str,
        resource_manager: Optional[ResourcePoolManager] = None,
        artifact_store: Optional[ArtifactStore] = None,
        state_store: Optional[StateStore] = None,
        max_workers: int = 8,
        cancel_token: Optional[Any] = None,
        revision_token: Optional[Any] = None,
        event_bus: Optional[WorkflowEventBus] = None,
    ) -> None:
        self.project_id = project_id
        self.section_id = section_id
        self.resource_manager = resource_manager or get_resource_manager()
        self.artifact_store = artifact_store or get_artifact_store()
        self.state_store = state_store or get_state_store()
        self.counters = get_telemetry_counters()
        self.tasks: Dict[str, ExecutableTask] = {}
        self.max_workers = max_workers
        self.cancel_token = cancel_token
        self.revision_token = revision_token
        self.event_bus = event_bus or get_workflow_event_bus()
        self._lock = threading.Lock()

    def _publish_task_status(
        self,
        task_id: str,
        old_status: TaskLifecycleStatus,
        new_status: TaskLifecycleStatus,
        duration: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        if self.event_bus:
            rev = self.revision_token.revision_id if self.revision_token else 1
            self.event_bus.publish(
                TaskStatusChangedEvent(
                    project_id=self.project_id,
                    section_id=self.section_id,
                    task_id=task_id,
                    old_status=old_status,
                    new_status=new_status,
                    revision_id=rev,
                    duration_seconds=duration,
                    error=error,
                )
            )

    def add_task(self, task: ExecutableTask) -> None:
        self.tasks[task.task_id] = task

    def get_execution_order(self) -> List[str]:
        in_degree = {k: len(v.dependencies) for k, v in self.tasks.items()}
        queue = [k for k, deg in in_degree.items() if deg == 0]
        order: List[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for tid, t in self.tasks.items():
                if node in t.dependencies:
                    in_degree[tid] -= 1
                    if in_degree[tid] == 0:
                        queue.append(tid)

        if len(order) != len(self.tasks):
            unresolved = set(self.tasks.keys()) - set(order)
            raise ValueError(f"Cyclic dependency in task execution graph: {unresolved}")

        return order

    def _execute_task_action(self, task: ExecutableTask, art_hash: str) -> tuple[str, Any, float]:
        """Execute a single task with retries, resource semaphore, timing, and cancellation."""
        if self.cancel_token and getattr(self.cancel_token, "is_cancelled", False):
            reason = getattr(self.cancel_token, "reason", "Cancelled by user")
            with self._lock:
                state = self.state_store.load_state(self.project_id)
                state.mark_task_cancelled(self.section_id, task.task_id, reason=reason)
                self.state_store.save_state(state)
            self._publish_task_status(task.task_id, TaskLifecycleStatus.RUNNING, TaskLifecycleStatus.CANCELLED, error=reason)
            raise RuntimeError(f"Operation cancelled: {reason}")

        with self._lock:
            state = self.state_store.load_state(self.project_id)
            state.mark_task_started(self.section_id, task.task_id, name=task.name)
            self.state_store.save_state(state)
        self._publish_task_status(task.task_id, TaskLifecycleStatus.QUEUED, TaskLifecycleStatus.RUNNING)

        self.counters.record_cache_miss(task.component)
        print(f"  [DAG] 🚀 Executing task '{task.name}' [{task.resource_type}]...", flush=True)

        start_t = time.perf_counter()
        retries = task.retry_policy.get("max_retries", 0) if task.retry_policy else 0
        delay = task.retry_policy.get("delay", 1.0) if task.retry_policy else 1.0

        attempt = 0
        while True:
            if self.cancel_token and getattr(self.cancel_token, "is_cancelled", False):
                reason = getattr(self.cancel_token, "reason", "Cancelled by user")
                with self._lock:
                    state = self.state_store.load_state(self.project_id)
                    state.mark_task_cancelled(self.section_id, task.task_id, reason=reason)
                    self.state_store.save_state(state)
                self._publish_task_status(task.task_id, TaskLifecycleStatus.RUNNING, TaskLifecycleStatus.CANCELLED, error=reason)
                raise RuntimeError(f"Operation cancelled: {reason}")

            try:
                # Acquire resource semaphore with automatic release in finally block
                with self.resource_manager.acquire(task.resource_type):
                    if self.cancel_token and getattr(self.cancel_token, "is_cancelled", False):
                        reason = getattr(self.cancel_token, "reason", "Cancelled by user")
                        raise RuntimeError(f"Operation cancelled: {reason}")

                    with TaskTimer(task.task_id, category=task.component):
                        res = task.action() if task.action else None

                dur = time.perf_counter() - start_t

                # Revision guard: verify task token is not stale
                if self.revision_token:
                    from core.artifacts.revision_manager import get_revision_manager
                    rev_mgr = get_revision_manager()
                    if not rev_mgr.is_token_current(self.revision_token):
                        print(f"  [DAG] ⚠️ Dropping stale result for '{task.name}' (rev {self.revision_token.revision_id} is obsolete).")
                        return (task.task_id, None, dur)

                out_path = task.expected_output_path or (
                    str(res) if (res and isinstance(res, (str, Path))) else None
                )
                if out_path and Path(out_path).exists():
                    self.artifact_store.register_artifact(
                        artifact_hash=art_hash,
                        file_path=out_path,
                        component=task.component,
                    )

                with self._lock:
                    state = self.state_store.load_state(self.project_id)
                    state.mark_task_completed(
                        section_id=self.section_id,
                        task_id=task.task_id,
                        artifact_hash=art_hash,
                        duration=dur,
                    )
                    self.state_store.save_state(state)
                self._publish_task_status(task.task_id, TaskLifecycleStatus.RUNNING, TaskLifecycleStatus.COMPLETED, duration=dur)

                return (task.task_id, res, dur)

            except Exception as e:
                attempt += 1
                if attempt <= retries:
                    print(
                        f"  [DAG] ⚠️ Task '{task.name}' attempt {attempt} failed: {e}. Retrying in {delay}s...",
                        flush=True,
                    )
                    with self._lock:
                        state = self.state_store.load_state(self.project_id)
                        sec = state.get_or_create_section(self.section_id)
                        tstate = sec.get_or_create_task(task.task_id)
                        tstate.transition_to(LifecycleStatus.RETRYING)
                        self.state_store.save_state(state)
                    self._publish_task_status(task.task_id, TaskLifecycleStatus.RUNNING, TaskLifecycleStatus.RETRYING, error=str(e))

                    time.sleep(delay)

                    with self._lock:
                        state = self.state_store.load_state(self.project_id)
                        sec = state.get_or_create_section(self.section_id)
                        tstate = sec.get_or_create_task(task.task_id)
                        tstate.transition_to(LifecycleStatus.RUNNING)
                        self.state_store.save_state(state)
                    self._publish_task_status(task.task_id, TaskLifecycleStatus.RETRYING, TaskLifecycleStatus.RUNNING)
                else:
                    dur = time.perf_counter() - start_t
                    with self._lock:
                        state = self.state_store.load_state(self.project_id)
                        state.mark_task_failed(
                            section_id=self.section_id,
                            task_id=task.task_id,
                            error=str(e),
                            duration=dur,
                        )
                        self.state_store.save_state(state)
                    self._publish_task_status(task.task_id, TaskLifecycleStatus.RUNNING, TaskLifecycleStatus.FAILED, duration=dur, error=str(e))
                    raise e

    def execute(
        self,
        force_all: bool = False,
        target_tasks: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """Execute tasks via parallel ready-task dispatch, respecting resource pools, caching, and target boundaries."""
        # Ensure DAG is a valid DAG (detect cycles early)
        self.get_execution_order()

        # Compute required task closure if target_tasks is specified
        if target_tasks is not None:
            needed_tasks: Set[str] = set()

            def _gather_deps(tid: str) -> None:
                if tid in needed_tasks or tid not in self.tasks:
                    return
                needed_tasks.add(tid)
                for dep in self.tasks[tid].dependencies:
                    _gather_deps(dep)

            for t in target_tasks:
                _gather_deps(t)
        else:
            needed_tasks = set(self.tasks.keys())

        results: Dict[str, Any] = {}
        completed: Set[str] = set()
        failed: Set[str] = set()
        blocked: Set[str] = set()
        task_errors: Dict[str, Any] = {}
        in_flight: Dict[concurrent.futures.Future, ExecutableTask] = {}

        # 1. State resume & pre-check existing completed tasks
        with self._lock:
            state = self.state_store.load_state(self.project_id)
            sec_state = state.get_or_create_section(self.section_id)

            for task_id, task in self.tasks.items():
                if task_id not in needed_tasks:
                    continue
                art_hash = task.artifact_identity
                if not force_all and task_id in sec_state.tasks:
                    existing = sec_state.tasks[task_id]
                    if existing.status == LifecycleStatus.COMPLETED:
                        if task.expected_output_path:
                            if self.artifact_store.is_artifact_valid(
                                art_hash, task.expected_output_path
                            ):
                                self.counters.record_cache_hit(task.component)
                                print(
                                    f"  [DAG] ⚡ Resumed COMPLETED cache HIT for '{task.name}' ({task_id})",
                                    flush=True,
                                )
                                completed.add(task_id)
                                results[task_id] = task.expected_output_path
                                continue
                            else:
                                # Artifact invalid or missing on disk -> invalidate and rerun
                                existing.transition_to(LifecycleStatus.INVALIDATED)
                                existing.transition_to(LifecycleStatus.PENDING)
                        else:
                            completed.add(task_id)
                            results[task_id] = None
                            continue
                    elif existing.status == LifecycleStatus.FAILED:
                        # Failed tasks are reset to PENDING on resume
                        existing.transition_to(LifecycleStatus.PENDING)

            self.state_store.save_state(state)

        # 2. Parallel dispatch loop
        worker_count = min(self.max_workers, max(1, len(needed_tasks)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as pool:
            while not all(t in completed or t in failed or t in blocked for t in needed_tasks):
                if self.cancel_token and getattr(self.cancel_token, "is_cancelled", False):
                    reason = getattr(self.cancel_token, "reason", "Cancelled by user")
                    print(f"  [DAG] 🛑 Execution cancelled for section {self.section_id}: {reason}")
                    with self._lock:
                        st = self.state_store.load_state(self.project_id)
                        for tid, t in self.tasks.items():
                            if tid in needed_tasks and tid not in completed and tid not in failed:
                                st.mark_task_cancelled(self.section_id, tid, reason=reason)
                        self.state_store.save_state(st)
                    break

                in_flight_tids = {t.task_id for t in in_flight.values()}
                ready_tasks: List[ExecutableTask] = []

                # Find all currently ready independent tasks
                for tid, task in self.tasks.items():
                    if tid not in needed_tasks:
                        continue
                    if (
                        tid in completed
                        or tid in failed
                        or tid in blocked
                        or tid in in_flight_tids
                    ):
                        continue

                    # Check if any dependency failed or is blocked
                    if any(dep in failed or dep in blocked for dep in task.dependencies):
                        blocked.add(tid)
                        print(
                            f"  [DAG] ⛔ Task '{task.name}' ({tid}) BLOCKED due to failed dependency",
                            flush=True,
                        )
                        continue

                    # If all dependencies are COMPLETED, this task is ready to run!
                    if task.dependencies.issubset(completed):
                        ready_tasks.append(task)

                new_cache_hit = False

                for task in ready_tasks:
                    art_hash = task.artifact_identity

                    # Check artifact store cache
                    if not force_all and task.expected_output_path:
                        if self.artifact_store.is_artifact_valid(
                            art_hash, task.expected_output_path
                        ):
                            self.counters.record_cache_hit(task.component)
                            print(
                                f"  [DAG] ⚡ Cache HIT for task '{task.name}' ({task.task_id})",
                                flush=True,
                            )
                            with self._lock:
                                s = self.state_store.load_state(self.project_id)
                                s.mark_task_completed(
                                    section_id=self.section_id,
                                    task_id=task.task_id,
                                    artifact_hash=art_hash,
                                    duration=0.0,
                                    metadata={"cached": True},
                                )
                                self.state_store.save_state(s)

                            self._publish_task_status(task.task_id, TaskLifecycleStatus.PENDING, TaskLifecycleStatus.COMPLETED, duration=0.0)
                            completed.add(task.task_id)
                            results[task.task_id] = task.expected_output_path
                            new_cache_hit = True
                            continue

                    # Mark task QUEUED in state
                    with self._lock:
                        s = self.state_store.load_state(self.project_id)
                        s.mark_task_queued(self.section_id, task.task_id, name=task.name)
                        self.state_store.save_state(s)
                    self._publish_task_status(task.task_id, TaskLifecycleStatus.PENDING, TaskLifecycleStatus.QUEUED)

                    # Dispatch concurrently to thread pool
                    fut = pool.submit(self._execute_task_action, task, art_hash)
                    in_flight[fut] = task

                # If cache hits just completed, re-evaluate ready tasks before blocking
                if new_cache_hit:
                    continue

                if not in_flight:
                    # No tasks running and no new tasks ready -> remaining are blocked or cycles
                    break

                # Wait for any in-flight task to complete
                done, _ = concurrent.futures.wait(
                    in_flight.keys(),
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )

                for fut in done:
                    task = in_flight.pop(fut)
                    try:
                        tid, res, dur = fut.result()
                        completed.add(tid)
                        results[tid] = res
                        print(
                            f"  [DAG] ✅ Completed task '{task.name}' ({dur:.2f}s)",
                            flush=True,
                        )
                    except Exception as exc:
                        failed.add(task.task_id)
                        task_errors[task.task_id] = exc
                        print(
                            f"  [DAG] ❌ Failed task '{task.name}': {exc}",
                            flush=True,
                        )

        # 3. Final failure evaluation
        if failed:
            first_tid = next(iter(failed))
            first_err = task_errors.get(first_tid, "Unknown error")
            task_name = self.tasks[first_tid].name
            raise RuntimeError(
                f"Task '{task_name}' failed: {first_err} (total {len(failed)} failed tasks: {list(failed)})"
            )

        return results

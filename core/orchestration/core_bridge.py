"""Core Bridge & Pipeline Controller for Whiteboard Studio.

Part of Phase 6: Core Bridge, Processing Monitor & Section Lifecycle.
Bridges background task execution, TaskDAGExecutor, and WorkerManager with
the Qt UI event loop via thread-safe Qt Signals and the WorkflowEventBus.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.contracts.studio_contracts import StageIdentifier
from core.orchestration.resource_governor import ResourceGovernor, get_resource_governor
from core.orchestration.section_worker import SectionWorker
from core.orchestration.worker_manager import (
    CancellationToken,
    WorkerManager,
    get_worker_manager,
)
from core.state.project_state import ProjectState
from core.state.state_store import StateStore, get_state_store
from core.state.transitions import LifecycleStatus, SectionLifecycleStatus
from core.state.workflow_events import (
    ArtifactCommittedEvent,
    PipelineLogEvent,
    ProjectStatusChangedEvent,
    ReviewGateChangedEvent,
    RevisionIncrementedEvent,
    SectionStatusChangedEvent,
    TaskProgressEvent,
    TaskStatusChangedEvent,
    WorkflowEventBus,
    get_workflow_event_bus,
)
from studio_ui.qt import QObject, Signal, Slot

logger = logging.getLogger(__name__)


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


class CoreBridge(QObject):
    """Event-driven bridge connecting Core Pipeline Workers to the Qt Workstation UI."""

    # Qt Signals for UI components
    task_status_changed = Signal(str, str, str, str, float, str)  # (proj_id, sec_id, task_id, status_val, duration, error)
    task_progress_updated = Signal(str, str, str, float, str)     # (proj_id, sec_id, task_id, progress, msg)
    section_status_changed = Signal(str, str, str, int)            # (proj_id, sec_id, status_val, revision_id)
    project_status_changed = Signal(str, str)                      # (proj_id, status_val)
    review_gate_triggered = Signal(str, str, str, str)             # (proj_id, sec_id, stage_id, reason)
    pipeline_log_received = Signal(str, str, str, str, str)        # (timestamp, level, sec_id, stage_id, msg)

    section_started = Signal(str, str)                             # (proj_id, sec_id)
    section_finished = Signal(str, str, bool, str)                 # (proj_id, sec_id, success, message_or_path)
    project_started = Signal(str)                                  # (proj_id)
    project_finished = Signal(str, bool, str)                      # (proj_id, success, message)

    def __init__(
        self,
        state_store: Optional[StateStore] = None,
        event_bus: Optional[WorkflowEventBus] = None,
        worker_manager: Optional[WorkerManager] = None,
        governor: Optional[ResourceGovernor] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.state_store = state_store or get_state_store()
        self.event_bus = event_bus or get_workflow_event_bus()
        self.worker_manager = worker_manager or get_worker_manager()
        self.governor = governor or get_resource_governor()

        self._active_tokens: Dict[str, CancellationToken] = {}
        self._lock = threading.Lock()

        self._subscribe_to_event_bus()

    def _subscribe_to_event_bus(self) -> None:
        """Register listeners on the in-process WorkflowEventBus."""
        self.event_bus.subscribe(TaskStatusChangedEvent, self._handle_task_status_event)
        self.event_bus.subscribe(TaskProgressEvent, self._handle_task_progress_event)
        self.event_bus.subscribe(SectionStatusChangedEvent, self._handle_section_status_event)
        self.event_bus.subscribe(ProjectStatusChangedEvent, self._handle_project_status_event)
        self.event_bus.subscribe(ReviewGateChangedEvent, self._handle_review_gate_event)
        self.event_bus.subscribe(PipelineLogEvent, self._handle_pipeline_log_event)

    def _handle_task_status_event(self, ev: TaskStatusChangedEvent) -> None:
        status_val = ev.new_status.value if hasattr(ev.new_status, "value") else str(ev.new_status)
        self.task_status_changed.emit(
            ev.project_id,
            ev.section_id,
            ev.task_id,
            status_val,
            ev.duration_seconds,
            ev.error or "",
        )

    def _handle_task_progress_event(self, ev: TaskProgressEvent) -> None:
        self.task_progress_updated.emit(
            ev.project_id,
            ev.section_id,
            ev.task_id or ev.stage_id,
            ev.progress,
            ev.message,
        )

    def _handle_section_status_event(self, ev: SectionStatusChangedEvent) -> None:
        status_val = ev.new_status.value if hasattr(ev.new_status, "value") else str(ev.new_status)
        self.section_status_changed.emit(
            ev.project_id,
            ev.section_id,
            status_val,
            ev.revision_id,
        )

    def _handle_project_status_event(self, ev: ProjectStatusChangedEvent) -> None:
        status_val = ev.new_status.value if hasattr(ev.new_status, "value") else str(ev.new_status)
        self.project_status_changed.emit(
            ev.project_id,
            status_val,
        )

    def _handle_review_gate_event(self, ev: ReviewGateChangedEvent) -> None:
        self.review_gate_triggered.emit(
            ev.project_id,
            ev.section_id,
            ev.stage_id,
            ev.reason,
        )

    def _handle_pipeline_log_event(self, ev: PipelineLogEvent) -> None:
        ts = ev.timestamp[11:19] if len(ev.timestamp) >= 19 else _now_str()
        self.pipeline_log_received.emit(
            ts,
            ev.level,
            ev.section_id,
            ev.stage_id,
            ev.message,
        )

    # ------------------------------------------------------------------------
    # Public Execution Control Methods
    # ------------------------------------------------------------------------

    def is_section_running(self, section_id: str) -> bool:
        with self._lock:
            token = self._active_tokens.get(section_id)
            return token is not None and not token.is_cancelled

    def get_cancellation_token(self, section_id: str) -> Optional[CancellationToken]:
        with self._lock:
            return self._active_tokens.get(section_id)

    def start_section_pipeline(
        self,
        project_id: str,
        section_id: str,
        section_path: Optional[Path | str] = None,
        force_whisper: bool = False,
        force_all: bool = False,
        force_render: bool = False,
        title: Optional[str] = None,
        target_mode: str = "full",
    ) -> CancellationToken:
        """Starts asynchronous execution of a section pipeline in background workers."""
        with self._lock:
            if section_id in self._active_tokens and not self._active_tokens[section_id].is_cancelled:
                logger.warning(f"Section {section_id} is already running.")
                return self._active_tokens[section_id]

            token = CancellationToken()
            self._active_tokens[section_id] = token

        # Resolve section directory
        if section_path is not None:
            sec_dir = Path(section_path).resolve()
        else:
            state = self.state_store.load_state(project_id)
            sec_dir = None
            if state and state.metadata and state.metadata.get("project_path"):
                candidate = Path(state.metadata["project_path"]) / "sections" / section_id
                if candidate.exists() or (Path(state.metadata["project_path"]).is_dir()):
                    sec_dir = candidate

            if sec_dir is None:
                from core.config.settings import SECTIONS_DIR
                proj_sec_dir = SECTIONS_DIR / project_id / section_id
                if proj_sec_dir.is_dir():
                    sec_dir = proj_sec_dir
                else:
                    sec_dir = SECTIONS_DIR / section_id

        def _worker_job() -> None:
            self.section_started.emit(project_id, section_id)
            self.emit_log(
                project_id=project_id,
                section_id=section_id,
                stage_id="sec.ingest",
                level="INFO",
                message=f"Dispatched background execution for section '{section_id}' (mode={target_mode})",
            )

            try:
                worker = SectionWorker(
                    section_path=sec_dir,
                    project_id=project_id,
                    title=title,
                    state_store=self.state_store,
                    cancel_token=token,
                    event_bus=self.event_bus,
                )

                output_video = worker.run(
                    force_whisper=force_whisper,
                    force_all=(force_all or force_render),
                    cancel_token=token,
                    target_mode=target_mode,
                )

                if output_video == "NEEDS_REVIEW":
                    self.emit_log(
                        project_id=project_id,
                        section_id=section_id,
                        stage_id="sec.extraction",
                        level="INFO",
                        message=f"Section '{section_id}' entered review gates successfully.",
                    )
                    self.section_finished.emit(project_id, section_id, True, "NEEDS_REVIEW")
                else:
                    self.emit_log(
                        project_id=project_id,
                        section_id=section_id,
                        stage_id="sec.export",
                        level="INFO",
                        message=f"Section '{section_id}' completed successfully -> {output_video}",
                    )
                    self.section_finished.emit(project_id, section_id, True, output_video)

            except Exception as exc:
                if token.is_cancelled:
                    msg = f"Section '{section_id}' execution cancelled: {token.reason}"
                    self.emit_log(
                        project_id=project_id,
                        section_id=section_id,
                        stage_id="sec.cancel",
                        level="WARNING",
                        message=msg,
                    )
                    self.section_finished.emit(project_id, section_id, False, msg)
                else:
                    err_msg = f"Execution error in section '{section_id}': {exc}"
                    self.emit_log(
                        project_id=project_id,
                        section_id=section_id,
                        stage_id="sec.error",
                        level="ERROR",
                        message=err_msg,
                    )
                    self.section_finished.emit(project_id, section_id, False, err_msg)
            finally:
                with self._lock:
                    self._active_tokens.pop(section_id, None)

        # Submit task to worker manager or daemon thread
        threading.Thread(target=_worker_job, daemon=True, name=f"Worker-{section_id}").start()
        return token

    def cancel_section(self, section_id: str, reason: str = "User cancelled execution") -> bool:
        """Cancel an ongoing section pipeline execution."""
        with self._lock:
            token = self._active_tokens.get(section_id)
            if token and not token.is_cancelled:
                token.cancel(reason)
                self.emit_log(
                    project_id="",
                    section_id=section_id,
                    stage_id="sec.cancel",
                    level="WARNING",
                    message=f"Cancellation requested: {reason}",
                )
                return True
            return False

    def cancel_all(self, reason: str = "User cancelled all operations") -> None:
        """Cancel all active section workers."""
        with self._lock:
            for sec_id, token in list(self._active_tokens.items()):
                if not token.is_cancelled:
                    token.cancel(reason)

    def emit_log(
        self,
        project_id: str,
        section_id: str,
        stage_id: str,
        level: str,
        message: str,
    ) -> None:
        """Utility to dispatch a log event across the event bus and Qt signals."""
        self.event_bus.publish(
            PipelineLogEvent(
                project_id=project_id,
                section_id=section_id,
                stage_id=stage_id,
                level=level,
                message=message,
            )
        )


_GLOBAL_BRIDGE: Optional[CoreBridge] = None
_BRIDGE_LOCK = threading.Lock()


def get_core_bridge() -> CoreBridge:
    """Retrieve or create the global CoreBridge singleton."""
    global _GLOBAL_BRIDGE
    with _BRIDGE_LOCK:
        if _GLOBAL_BRIDGE is None:
            _GLOBAL_BRIDGE = CoreBridge()
        return _GLOBAL_BRIDGE

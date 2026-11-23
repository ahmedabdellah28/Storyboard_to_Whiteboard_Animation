"""Typed workflow events and in-process event bus for Whiteboard Studio.

Part of Phase 1: Core Foundation & Governed Contracts.
Provides decoupled event notifications for UI synchronization, telemetry, and background workers.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Type

from core.contracts.studio_contracts import StageIdentifier
from core.state.transitions import (
    ProjectLifecycleStatus,
    ReviewGateStatus,
    SectionLifecycleStatus,
    TaskLifecycleStatus,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkflowEvent:
    """Base class for all Whiteboard Studio workflow events."""
    project_id: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=_now_iso)


@dataclass
class TaskStatusChangedEvent(WorkflowEvent):
    """Fired when an individual DAG task changes execution status."""
    section_id: str = ""
    task_id: str = ""
    old_status: TaskLifecycleStatus = TaskLifecycleStatus.PENDING
    new_status: TaskLifecycleStatus = TaskLifecycleStatus.PENDING
    revision_id: int = 1
    duration_seconds: float = 0.0
    error: Optional[str] = None


@dataclass
class ReviewGateChangedEvent(WorkflowEvent):
    """Fired when a human review gate status changes (e.g., entered NEEDS_REVIEW, approved, rejected)."""
    section_id: str = ""
    stage_id: str = ""
    old_status: ReviewGateStatus = ReviewGateStatus.NOT_APPLICABLE
    new_status: ReviewGateStatus = ReviewGateStatus.NOT_APPLICABLE
    reason: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SectionStatusChangedEvent(WorkflowEvent):
    """Fired when a section's aggregate lifecycle status changes."""
    section_id: str = ""
    old_status: SectionLifecycleStatus = SectionLifecycleStatus.EMPTY
    new_status: SectionLifecycleStatus = SectionLifecycleStatus.EMPTY
    revision_id: int = 1


@dataclass
class ProjectStatusChangedEvent(WorkflowEvent):
    """Fired when the overall project lifecycle status transitions."""
    old_status: ProjectLifecycleStatus = ProjectLifecycleStatus.IDLE
    new_status: ProjectLifecycleStatus = ProjectLifecycleStatus.IDLE


@dataclass
class RevisionIncrementedEvent(WorkflowEvent):
    """Fired when a user edit increments section revision and invalidates downstream stages."""
    section_id: str = ""
    old_revision: int = 1
    new_revision: int = 2
    reason: str = ""
    invalidated_stages: List[str] = field(default_factory=list)


@dataclass
class ArtifactCommittedEvent(WorkflowEvent):
    """Fired when a verified artifact is committed to disk."""
    section_id: str = ""
    stage_id: str = ""
    artifact_type: str = ""
    artifact_path: str = ""
    artifact_hash: str = ""


@dataclass
class TaskProgressEvent(WorkflowEvent):
    """Fired when an individual task makes measurable execution progress (0.0 to 1.0)."""
    section_id: str = ""
    task_id: str = ""
    stage_id: str = ""
    progress: float = 0.0  # 0.0 to 1.0
    message: str = ""
    eta_seconds: Optional[float] = None


@dataclass
class PipelineLogEvent(WorkflowEvent):
    """Fired when an execution log message is produced during pipeline runs."""
    section_id: str = ""
    stage_id: str = ""
    level: str = "INFO"  # INFO, WARNING, ERROR, DEBUG
    message: str = ""


# ============================================================================
# THREAD-SAFE WORKFLOW EVENT BUS
# ============================================================================

EventHandler = Callable[[Any], None]


class WorkflowEventBus:
    """Thread-safe publish-subscribe event broker for Studio state updates."""

    def __init__(self) -> None:
        self._subscribers: Dict[Type[WorkflowEvent], List[EventHandler]] = {}
        self._all_subscribers: List[EventHandler] = []
        self._lock = threading.RLock()

    def subscribe(self, event_type: Type[WorkflowEvent], handler: EventHandler) -> None:
        """Register a callback for a specific event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Register a callback that receives every published event."""
        with self._lock:
            if handler not in self._all_subscribers:
                self._all_subscribers.append(handler)

    def unsubscribe(self, event_type: Type[WorkflowEvent], handler: EventHandler) -> None:
        """Unregister a callback for an event type."""
        with self._lock:
            if event_type in self._subscribers and handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

    def publish(self, event: WorkflowEvent) -> None:
        """Publish an event to all registered listeners."""
        with self._lock:
            handlers_to_call: List[EventHandler] = []
            ev_type = type(event)
            if ev_type in self._subscribers:
                handlers_to_call.extend(self._subscribers[ev_type])
            handlers_to_call.extend(self._all_subscribers)

        # Invoke outside of lock to prevent deadlocks
        for handler in handlers_to_call:
            try:
                handler(event)
            except Exception as e:
                print(f"⚠️ [WorkflowEventBus] Error in handler {handler}: {e}")

    def clear(self) -> None:
        """Clear all subscribers."""
        with self._lock:
            self._subscribers.clear()
            self._all_subscribers.clear()


_GLOBAL_EVENT_BUS: Optional[WorkflowEventBus] = None
_BUS_LOCK = threading.Lock()


def get_workflow_event_bus() -> WorkflowEventBus:
    global _GLOBAL_EVENT_BUS
    with _BUS_LOCK:
        if _GLOBAL_EVENT_BUS is None:
            _GLOBAL_EVENT_BUS = WorkflowEventBus()
        return _GLOBAL_EVENT_BUS

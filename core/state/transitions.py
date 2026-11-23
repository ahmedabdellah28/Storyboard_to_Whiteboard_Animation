"""Valid state transitions and lifecycle statuses for tasks, review gates, sections, and projects.

Formalized in Phase 1: Core Foundation & Governed Contracts.
"""

from __future__ import annotations

import enum
from typing import Any, Dict, Set


# ============================================================================
# 1. TASK EXECUTION LIFECYCLE (9 States)
# ============================================================================

class TaskLifecycleStatus(str, enum.Enum):
    """Execution status for individual DAG tasks."""
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"
    INVALIDATED = "INVALIDATED"


# Backward compatibility alias
LifecycleStatus = TaskLifecycleStatus


VALID_TASK_TRANSITIONS: Dict[TaskLifecycleStatus, Set[TaskLifecycleStatus]] = {
    TaskLifecycleStatus.PENDING: {
        TaskLifecycleStatus.QUEUED,
        TaskLifecycleStatus.RUNNING,
        TaskLifecycleStatus.SKIPPED,
        TaskLifecycleStatus.CANCELLED,
    },
    TaskLifecycleStatus.QUEUED: {
        TaskLifecycleStatus.RUNNING,
        TaskLifecycleStatus.FAILED,
        TaskLifecycleStatus.SKIPPED,
        TaskLifecycleStatus.CANCELLED,
    },
    TaskLifecycleStatus.RUNNING: {
        TaskLifecycleStatus.COMPLETED,
        TaskLifecycleStatus.FAILED,
        TaskLifecycleStatus.RETRYING,
        TaskLifecycleStatus.CANCELLED,
    },
    TaskLifecycleStatus.RETRYING: {
        TaskLifecycleStatus.QUEUED,
        TaskLifecycleStatus.RUNNING,
        TaskLifecycleStatus.FAILED,
        TaskLifecycleStatus.CANCELLED,
    },
    TaskLifecycleStatus.COMPLETED: {
        TaskLifecycleStatus.INVALIDATED,
        TaskLifecycleStatus.RUNNING,  # Force re-run override
    },
    TaskLifecycleStatus.FAILED: {
        TaskLifecycleStatus.RETRYING,
        TaskLifecycleStatus.QUEUED,
        TaskLifecycleStatus.RUNNING,
        TaskLifecycleStatus.PENDING,
    },
    TaskLifecycleStatus.CANCELLED: {
        TaskLifecycleStatus.PENDING,
        TaskLifecycleStatus.QUEUED,
    },
    TaskLifecycleStatus.SKIPPED: {
        TaskLifecycleStatus.PENDING,
        TaskLifecycleStatus.QUEUED,
        TaskLifecycleStatus.RUNNING,
    },
    TaskLifecycleStatus.INVALIDATED: {
        TaskLifecycleStatus.PENDING,
        TaskLifecycleStatus.QUEUED,
        TaskLifecycleStatus.RUNNING,
    },
}

# Backward compatibility alias
VALID_TRANSITIONS = VALID_TASK_TRANSITIONS


def can_transition(current: TaskLifecycleStatus, target: TaskLifecycleStatus) -> bool:
    """Check whether a transition between two task statuses is permissible."""
    if current == target:
        return True
    return target in VALID_TASK_TRANSITIONS.get(current, set())


def validate_transition(current: TaskLifecycleStatus, target: TaskLifecycleStatus) -> None:
    """Enforce permitted task transitions, raising ValueError on invalid state jumps."""
    if not can_transition(current, target):
        raise ValueError(f"Invalid task state transition: cannot transition from {current} to {target}")


# ============================================================================
# 2. REVIEW GATE LIFECYCLE (5 States)
# ============================================================================

class ReviewGateStatus(str, enum.Enum):
    """Status of human-in-the-loop inspection gates."""
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REVIEW_PENDING = "REVIEW_PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


VALID_REVIEW_TRANSITIONS: Dict[ReviewGateStatus, Set[ReviewGateStatus]] = {
    ReviewGateStatus.NOT_APPLICABLE: {
        ReviewGateStatus.REVIEW_PENDING,
    },
    ReviewGateStatus.REVIEW_PENDING: {
        ReviewGateStatus.IN_REVIEW,
        ReviewGateStatus.APPROVED,
        ReviewGateStatus.REJECTED,
        ReviewGateStatus.NOT_APPLICABLE,
    },
    ReviewGateStatus.IN_REVIEW: {
        ReviewGateStatus.APPROVED,
        ReviewGateStatus.REJECTED,
        ReviewGateStatus.REVIEW_PENDING,
    },
    ReviewGateStatus.APPROVED: {
        ReviewGateStatus.REVIEW_PENDING,   # When upstream invalidated
        ReviewGateStatus.NOT_APPLICABLE,
    },
    ReviewGateStatus.REJECTED: {
        ReviewGateStatus.REVIEW_PENDING,
        ReviewGateStatus.IN_REVIEW,
        ReviewGateStatus.NOT_APPLICABLE,
    },
}


def can_transition_review(current: ReviewGateStatus, target: ReviewGateStatus) -> bool:
    if current == target:
        return True
    return target in VALID_REVIEW_TRANSITIONS.get(current, set())


def validate_review_transition(current: ReviewGateStatus, target: ReviewGateStatus) -> None:
    if not can_transition_review(current, target):
        raise ValueError(f"Invalid review gate transition: cannot transition from {current} to {target}")


# ============================================================================
# 3. SECTION LIFECYCLE (8 States)
# ============================================================================

class SectionLifecycleStatus(str, enum.Enum):
    """Aggregate lifecycle state of an entire storyboard section."""
    EMPTY = "EMPTY"                     # Created, awaiting storyboard & script
    DRAFTING = "DRAFTING"               # Inputs present, ready for processing
    PROCESSING = "PROCESSING"           # Background worker executing stages
    NEEDS_REVIEW = "NEEDS_REVIEW"       # A review gate requires human signoff
    READY_TO_RENDER = "READY_TO_RENDER" # Stages 00..13 complete, ready for frame rasterization
    RENDERING = "RENDERING"             # Stage 14/15 active
    COMPLETED = "COMPLETED"             # Final deliverable produced & QA passed
    ERROR = "ERROR"                     # One or more tasks failed with exhausted retries


VALID_SECTION_TRANSITIONS: Dict[SectionLifecycleStatus, Set[SectionLifecycleStatus]] = {
    SectionLifecycleStatus.EMPTY: {
        SectionLifecycleStatus.DRAFTING,
    },
    SectionLifecycleStatus.DRAFTING: {
        SectionLifecycleStatus.PROCESSING,
        SectionLifecycleStatus.EMPTY,
    },
    SectionLifecycleStatus.PROCESSING: {
        SectionLifecycleStatus.NEEDS_REVIEW,
        SectionLifecycleStatus.READY_TO_RENDER,
        SectionLifecycleStatus.RENDERING,
        SectionLifecycleStatus.COMPLETED,
        SectionLifecycleStatus.ERROR,
        SectionLifecycleStatus.DRAFTING,  # On manual cancellation
    },
    SectionLifecycleStatus.NEEDS_REVIEW: {
        SectionLifecycleStatus.PROCESSING,
        SectionLifecycleStatus.READY_TO_RENDER,
        SectionLifecycleStatus.DRAFTING,
        SectionLifecycleStatus.ERROR,
    },
    SectionLifecycleStatus.READY_TO_RENDER: {
        SectionLifecycleStatus.RENDERING,
        SectionLifecycleStatus.DRAFTING,
        SectionLifecycleStatus.NEEDS_REVIEW,
    },
    SectionLifecycleStatus.RENDERING: {
        SectionLifecycleStatus.COMPLETED,
        SectionLifecycleStatus.ERROR,
        SectionLifecycleStatus.READY_TO_RENDER,  # On cancel
    },
    SectionLifecycleStatus.COMPLETED: {
        SectionLifecycleStatus.DRAFTING,         # On mutation/invalidation
        SectionLifecycleStatus.PROCESSING,       # On force re-run
    },
    SectionLifecycleStatus.ERROR: {
        SectionLifecycleStatus.PROCESSING,       # Retry
        SectionLifecycleStatus.DRAFTING,
        SectionLifecycleStatus.NEEDS_REVIEW,
    },
}


def can_transition_section(current: SectionLifecycleStatus, target: SectionLifecycleStatus) -> bool:
    if current == target:
        return True
    return target in VALID_SECTION_TRANSITIONS.get(current, set())


def validate_section_transition(current: SectionLifecycleStatus, target: SectionLifecycleStatus) -> None:
    if not can_transition_section(current, target):
        raise ValueError(f"Invalid section transition: cannot transition from {current} to {target}")


# ============================================================================
# 4. PROJECT LIFECYCLE (6 States)
# ============================================================================

class ProjectLifecycleStatus(str, enum.Enum):
    """Aggregate lifecycle state of the entire multi-section project."""
    IDLE = "IDLE"
    INGESTING = "INGESTING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    EXPORTING = "EXPORTING"
    ERROR = "ERROR"


VALID_PROJECT_TRANSITIONS: Dict[ProjectLifecycleStatus, Set[ProjectLifecycleStatus]] = {
    ProjectLifecycleStatus.IDLE: {
        ProjectLifecycleStatus.INGESTING,
        ProjectLifecycleStatus.PROCESSING,
    },
    ProjectLifecycleStatus.INGESTING: {
        ProjectLifecycleStatus.IDLE,
        ProjectLifecycleStatus.PROCESSING,
        ProjectLifecycleStatus.ERROR,
    },
    ProjectLifecycleStatus.PROCESSING: {
        ProjectLifecycleStatus.IDLE,
        ProjectLifecycleStatus.READY,
        ProjectLifecycleStatus.ERROR,
    },
    ProjectLifecycleStatus.READY: {
        ProjectLifecycleStatus.PROCESSING,
        ProjectLifecycleStatus.EXPORTING,
        ProjectLifecycleStatus.IDLE,
    },
    ProjectLifecycleStatus.EXPORTING: {
        ProjectLifecycleStatus.READY,
        ProjectLifecycleStatus.ERROR,
    },
    ProjectLifecycleStatus.ERROR: {
        ProjectLifecycleStatus.PROCESSING,
        ProjectLifecycleStatus.IDLE,
    },
}


def can_transition_project(current: ProjectLifecycleStatus, target: ProjectLifecycleStatus) -> bool:
    if current == target:
        return True
    return target in VALID_PROJECT_TRANSITIONS.get(current, set())


def validate_project_transition(current: ProjectLifecycleStatus, target: ProjectLifecycleStatus) -> None:
    if not can_transition_project(current, target):
        raise ValueError(f"Invalid project transition: cannot transition from {current} to {target}")


# ============================================================================
# DETERMINISTIC STATE AGGREGATION REDUCERS
# ============================================================================

def compute_section_status(
    task_statuses: Dict[str, TaskLifecycleStatus],
    review_gate_statuses: Dict[str, ReviewGateStatus],
) -> SectionLifecycleStatus:
    """Deterministically reduce task statuses and review gate statuses into a section status."""
    if not task_statuses:
        return SectionLifecycleStatus.EMPTY

    statuses = list(task_statuses.values())

    # 1. Any failed task -> ERROR
    if any(s == TaskLifecycleStatus.FAILED for s in statuses):
        return SectionLifecycleStatus.ERROR

    # 2. Any active review gate -> NEEDS_REVIEW
    if any(g in (ReviewGateStatus.REVIEW_PENDING, ReviewGateStatus.IN_REVIEW) for g in review_gate_statuses.values()):
        return SectionLifecycleStatus.NEEDS_REVIEW

    # 3. Any running or retrying task
    if any(s in (TaskLifecycleStatus.RUNNING, TaskLifecycleStatus.RETRYING) for s in statuses):
        # Distinguish rendering tasks (sec.render or sec.mux) from pre-render processing
        for tid, s in task_statuses.items():
            if s in (TaskLifecycleStatus.RUNNING, TaskLifecycleStatus.RETRYING):
                if any(k in tid for k in ("render", "mux")):
                    return SectionLifecycleStatus.RENDERING
        return SectionLifecycleStatus.PROCESSING

    # 4. Any queued task -> PROCESSING
    if any(s == TaskLifecycleStatus.QUEUED for s in statuses):
        return SectionLifecycleStatus.PROCESSING

    # 5. Check if all completed or skipped
    all_finished = all(s in (TaskLifecycleStatus.COMPLETED, TaskLifecycleStatus.SKIPPED) for s in statuses)
    if all_finished:
        return SectionLifecycleStatus.COMPLETED

    # 6. If pre-render stages finished, but render not queued -> READY_TO_RENDER
    return SectionLifecycleStatus.DRAFTING


def compute_project_status(
    section_statuses: Dict[str, SectionLifecycleStatus],
) -> ProjectLifecycleStatus:
    """Deterministically reduce section statuses into a project status."""
    if not section_statuses:
        return ProjectLifecycleStatus.IDLE

    statuses = list(section_statuses.values())

    if any(s == SectionLifecycleStatus.ERROR for s in statuses):
        return ProjectLifecycleStatus.ERROR

    if any(s in (SectionLifecycleStatus.PROCESSING, SectionLifecycleStatus.RENDERING) for s in statuses):
        return ProjectLifecycleStatus.PROCESSING

    if all(s == SectionLifecycleStatus.COMPLETED for s in statuses):
        return ProjectLifecycleStatus.READY

    return ProjectLifecycleStatus.IDLE

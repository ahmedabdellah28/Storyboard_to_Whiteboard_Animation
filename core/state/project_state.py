"""Project, section, task, and review gate state models.

Formalized in Phase 1: Core Foundation & Governed Contracts.
"""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

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


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@dataclass
class TaskState:
    task_id: str
    name: str = ""
    status: TaskLifecycleStatus = TaskLifecycleStatus.PENDING
    revision_id: int = 1
    artifact_hash: Optional[str] = None
    input_hashes: Dict[str, str] = field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    error: Optional[str] = None
    cancellation_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def transition_to(self, new_status: TaskLifecycleStatus) -> None:
        if self.status == new_status:
            return
        validate_transition(self.status, new_status)
        self.status = new_status
        if new_status == TaskLifecycleStatus.RUNNING and not self.started_at:
            self.started_at = _now_iso()
        elif new_status in (TaskLifecycleStatus.COMPLETED, TaskLifecycleStatus.FAILED, TaskLifecycleStatus.CANCELLED):
            self.completed_at = _now_iso()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "revision_id": self.revision_id,
            "artifact_hash": self.artifact_hash,
            "input_hashes": self.input_hashes,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "cancellation_reason": self.cancellation_reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskState:
        data_copy = dict(data)
        if "status" in data_copy:
            data_copy["status"] = TaskLifecycleStatus(data_copy["status"])
        return cls(**data_copy)


@dataclass
class SectionState:
    section_id: str
    title: str = ""
    sequence_index: int = 0
    status: LifecycleStatus = LifecycleStatus.PENDING
    lifecycle_status: SectionLifecycleStatus = SectionLifecycleStatus.EMPTY
    revision_id: int = 1
    review_gates: Dict[str, ReviewGateStatus] = field(default_factory=dict)
    tasks: Dict[str, TaskState] = field(default_factory=dict)
    output_video_path: Optional[str] = None
    output_audio_path: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def get_or_create_task(self, task_id: str, name: str = "", revision_id: Optional[int] = None) -> TaskState:
        if task_id not in self.tasks:
            self.tasks[task_id] = TaskState(
                task_id=task_id,
                name=name or task_id,
                revision_id=revision_id or self.revision_id,
            )
        return self.tasks[task_id]

    def set_review_gate(self, stage_id: str, status: ReviewGateStatus) -> None:
        """Update or register a human review gate status."""
        current = self.review_gates.get(stage_id, ReviewGateStatus.NOT_APPLICABLE)
        if current != status:
            validate_review_transition(current, status)
            self.review_gates[stage_id] = status
            self.recompute_lifecycle()
            self.updated_at = _now_iso()

    def recompute_lifecycle(self) -> SectionLifecycleStatus:
        """Recalculate section status from individual tasks and active review gates."""
        task_statuses = {tid: t.status for tid, t in self.tasks.items()}
        computed = compute_section_status(task_statuses, self.review_gates)
        self.lifecycle_status = computed
        # Map to legacy status for backwards compatibility
        if computed == SectionLifecycleStatus.COMPLETED:
            self.status = LifecycleStatus.COMPLETED
        elif computed == SectionLifecycleStatus.ERROR:
            self.status = LifecycleStatus.FAILED
        elif computed in (SectionLifecycleStatus.PROCESSING, SectionLifecycleStatus.RENDERING):
            self.status = LifecycleStatus.RUNNING
        else:
            self.status = LifecycleStatus.PENDING
        return computed

    def transition_to(self, new_status: LifecycleStatus) -> None:
        """Legacy transition method."""
        if self.status == new_status:
            return
        validate_transition(self.status, new_status)
        self.status = new_status
        self.updated_at = _now_iso()

    def increment_revision(self) -> int:
        """Bump section revision to protect against race conditions."""
        self.revision_id += 1
        self.updated_at = _now_iso()
        return self.revision_id

    def is_completed(self) -> bool:
        return self.lifecycle_status == SectionLifecycleStatus.COMPLETED or self.status == LifecycleStatus.COMPLETED

    def has_failed(self) -> bool:
        return self.lifecycle_status == SectionLifecycleStatus.ERROR or self.status == LifecycleStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "sequence_index": self.sequence_index,
            "status": self.status.value,
            "lifecycle_status": self.lifecycle_status.value,
            "revision_id": self.revision_id,
            "review_gates": {k: v.value for k, v in self.review_gates.items()},
            "tasks": {k: t.to_dict() for k, t in self.tasks.items()},
            "output_video_path": self.output_video_path,
            "output_audio_path": self.output_audio_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SectionState:
        raw_tasks = data.get("tasks", {})
        parsed_tasks = {
            tid: TaskState.from_dict(tdata) for tid, tdata in raw_tasks.items()
        }
        raw_gates = data.get("review_gates", {})
        parsed_gates = {
            gid: ReviewGateStatus(gval) for gid, gval in raw_gates.items()
        }
        raw_status = data.get("status", LifecycleStatus.PENDING.value)
        raw_lifecycle = data.get("lifecycle_status", SectionLifecycleStatus.EMPTY.value)

        return cls(
            section_id=data["section_id"],
            title=data.get("title", ""),
            sequence_index=data.get("sequence_index", 0),
            status=LifecycleStatus(raw_status),
            lifecycle_status=SectionLifecycleStatus(raw_lifecycle),
            revision_id=data.get("revision_id", 1),
            review_gates=parsed_gates,
            tasks=parsed_tasks,
            output_video_path=data.get("output_video_path"),
            output_audio_path=data.get("output_audio_path"),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )


@dataclass
class ProjectState:
    project_id: str
    title: str = ""
    schema_version: int = 2
    status: LifecycleStatus = LifecycleStatus.PENDING
    lifecycle_status: ProjectLifecycleStatus = ProjectLifecycleStatus.IDLE
    current_revision: int = 1
    sections: Dict[str, SectionState] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_or_create_section(self, section_id: str, title: str = "", sequence_index: int = 0) -> SectionState:
        if section_id not in self.sections:
            self.sections[section_id] = SectionState(
                section_id=section_id,
                title=title,
                sequence_index=sequence_index,
            )
            self.recompute_lifecycle()
            self.updated_at = _now_iso()
        return self.sections[section_id]

    def recompute_lifecycle(self) -> ProjectLifecycleStatus:
        """Recalculate project lifecycle from member sections."""
        section_statuses = {sid: s.lifecycle_status for sid, s in self.sections.items()}
        computed = compute_project_status(section_statuses)
        self.lifecycle_status = computed
        if computed == ProjectLifecycleStatus.READY:
            self.status = LifecycleStatus.COMPLETED
        elif computed == ProjectLifecycleStatus.ERROR:
            self.status = LifecycleStatus.FAILED
        elif computed in (ProjectLifecycleStatus.PROCESSING, ProjectLifecycleStatus.INGESTING, ProjectLifecycleStatus.EXPORTING):
            self.status = LifecycleStatus.RUNNING
        else:
            self.status = LifecycleStatus.PENDING
        return computed

    def transition_to(self, new_status: LifecycleStatus) -> None:
        """Legacy transition method."""
        if self.status == new_status:
            return
        validate_transition(self.status, new_status)
        self.status = new_status
        self.updated_at = _now_iso()

    def mark_task_queued(self, section_id: str, task_id: str, name: str = "", revision_id: Optional[int] = None) -> TaskState:
        sec = self.get_or_create_section(section_id)
        task = sec.get_or_create_task(task_id, name=name, revision_id=revision_id)
        if task.status == TaskLifecycleStatus.PENDING:
            task.transition_to(TaskLifecycleStatus.QUEUED)
        sec.recompute_lifecycle()
        self.recompute_lifecycle()
        self.updated_at = _now_iso()
        return task

    def mark_task_started(self, section_id: str, task_id: str, name: str = "", revision_id: Optional[int] = None) -> TaskState:
        sec = self.get_or_create_section(section_id)
        task = sec.get_or_create_task(task_id, name=name, revision_id=revision_id)
        task.transition_to(TaskLifecycleStatus.RUNNING)
        sec.recompute_lifecycle()
        self.recompute_lifecycle()
        self.updated_at = _now_iso()
        return task

    def mark_task_completed(
        self,
        section_id: str,
        task_id: str,
        artifact_hash: Optional[str] = None,
        duration: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskState:
        sec = self.get_or_create_section(section_id)
        task = sec.get_or_create_task(task_id)
        task.transition_to(TaskLifecycleStatus.COMPLETED)
        if artifact_hash:
            task.artifact_hash = artifact_hash
        task.duration_seconds = duration
        if metadata:
            task.metadata.update(metadata)
        sec.recompute_lifecycle()
        self.recompute_lifecycle()
        self.updated_at = _now_iso()
        return task

    def mark_task_failed(
        self,
        section_id: str,
        task_id: str,
        error: str,
        duration: float = 0.0,
    ) -> TaskState:
        sec = self.get_or_create_section(section_id)
        task = sec.get_or_create_task(task_id)
        task.transition_to(TaskLifecycleStatus.FAILED)
        task.error = error
        task.duration_seconds = duration
        sec.recompute_lifecycle()
        self.recompute_lifecycle()
        self.updated_at = _now_iso()
        return task

    def mark_task_cancelled(
        self,
        section_id: str,
        task_id: str,
        reason: str = "User cancelled execution",
    ) -> TaskState:
        sec = self.get_or_create_section(section_id)
        task = sec.get_or_create_task(task_id)
        task.cancellation_reason = reason
        task.transition_to(TaskLifecycleStatus.CANCELLED)
        sec.recompute_lifecycle()
        self.recompute_lifecycle()
        self.updated_at = _now_iso()
        return task

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "lifecycle_status": self.lifecycle_status.value,
            "current_revision": self.current_revision,
            "sections": {k: s.to_dict() for k, s in self.sections.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProjectState:
        raw_sections = data.get("sections", {})
        parsed_sections = {
            sid: SectionState.from_dict(sdata)
            for sid, sdata in raw_sections.items()
        }
        raw_status = data.get("status", LifecycleStatus.PENDING.value)
        raw_lifecycle = data.get("lifecycle_status", ProjectLifecycleStatus.IDLE.value)

        return cls(
            project_id=data["project_id"],
            title=data.get("title", ""),
            schema_version=data.get("schema_version", 2),
            status=LifecycleStatus(raw_status),
            lifecycle_status=ProjectLifecycleStatus(raw_lifecycle),
            current_revision=data.get("current_revision", 1),
            sections=parsed_sections,
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
            metadata=data.get("metadata", {}),
        )

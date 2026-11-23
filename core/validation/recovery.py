"""Crash reconciliation, orphan task self-healing, rolling backup recovery, and circuit breakers.

Part of Phase 3: Validation System & Recovery System.
Guarantees project durability and consistency across unexpected process terminations and crashes.
"""

from __future__ import annotations

import enum
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from core.contracts.studio_contracts import STAGE_DEFINITIONS, StageIdentifier
from core.state.project_state import ProjectState, SectionState, TaskState
from core.state.transitions import (
    ProjectLifecycleStatus,
    SectionLifecycleStatus,
    TaskLifecycleStatus,
)


@dataclass
class ReconciliationReport:
    """Detailed summary of tasks reconciled after application restart or crash."""
    reconciled_tasks_count: int = 0
    healed_to_completed: List[str] = field(default_factory=list)
    marked_as_failed: List[str] = field(default_factory=list)
    orphaned_temp_files_removed: int = 0
    project_status_restored: ProjectLifecycleStatus = ProjectLifecycleStatus.IDLE


class CrashReconciliationEngine:
    """Scans and heals uncommitted tasks and inconsistent states after abnormal shutdown."""

    @classmethod
    def reconcile_on_startup(
        cls,
        project_state: ProjectState,
        base_project_dir: Optional[Path] = None,
    ) -> ReconciliationReport:
        """Scan all sections and self-heal or mark failed any orphaned RUNNING/RETRYING tasks."""
        report = ReconciliationReport()

        for sec_id, sec in project_state.sections.items():
            sec_dir = base_project_dir / "sections" / sec_id if base_project_dir else None

            for tid, task in sec.tasks.items():
                if task.status in (TaskLifecycleStatus.RUNNING, TaskLifecycleStatus.RETRYING):
                    report.reconciled_tasks_count += 1

                    # Check if artifact was actually generated before the crash
                    artifact_found = False
                    if sec_dir and sec_dir.is_dir():
                        # Check canonical output candidates based on task ID
                        for stage in StageIdentifier:
                            if stage.value in tid or stage.name.lower() in tid.lower():
                                defn = STAGE_DEFINITIONS.get(stage)
                                if defn:
                                    expected_file = sec_dir / defn.produces_artifact
                                    if expected_file.is_file() and expected_file.stat().st_size > 0:
                                        artifact_found = True
                                        break

                    if artifact_found:
                        task.status = TaskLifecycleStatus.COMPLETED
                        report.healed_to_completed.append(f"{sec_id}:{tid}")
                    else:
                        task.status = TaskLifecycleStatus.FAILED
                        task.error = "Interrupted by abnormal application shutdown"
                        report.marked_as_failed.append(f"{sec_id}:{tid}")

            # Recompute section lifecycle after state reconciliation
            sec.recompute_lifecycle()

        # Recompute overall project lifecycle
        project_state.recompute_lifecycle()
        report.project_status_restored = project_state.lifecycle_status

        # Purge orphan temporary files
        if base_project_dir and base_project_dir.is_dir():
            report.orphaned_temp_files_removed = cls.cleanup_orphan_temp_files(base_project_dir)

        return report

    @staticmethod
    def cleanup_orphan_temp_files(search_dir: Path, max_age_seconds: int = 3600) -> int:
        """Purge temporary swap files (*.tmp, *.tmp.*) older than max_age_seconds."""
        removed = 0
        now = time.time()

        try:
            for p in search_dir.rglob("*.tmp*"):
                if p.is_file():
                    try:
                        mtime = p.stat().st_mtime
                        if now - mtime > max_age_seconds:
                            p.unlink(missing_ok=True)
                            removed += 1
                    except Exception:
                        pass
        except Exception:
            pass

        return removed

    @staticmethod
    def recover_from_backup(project_file_path: Path) -> Optional[ProjectState]:
        """Attempt to restore project state from rolling backup (.bak) file."""
        bak_file = project_file_path.with_name(f"{project_file_path.name}.bak")
        if not bak_file.is_file():
            return None

        try:
            with open(bak_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ProjectState.from_dict(data)
        except Exception as e:
            print(f"⚠️ [CrashReconciliation] Failed to load backup {bak_file}: {e}")
            return None


# ============================================================================
# CIRCUIT BREAKER (API Resilience)
# ============================================================================

class CircuitBreakerState(str, enum.Enum):
    CLOSED = "CLOSED"         # Normal operation, calls allowed
    OPEN = "OPEN"             # Tripped, calls rejected immediately
    HALF_OPEN = "HALF_OPEN"   # Testing recovery with single canary call


class CircuitBreaker:
    """Protects external APIs (Gemini TTS / Narrative) from runaway retries and outages."""

    def __init__(
        self,
        name: str = "default_circuit",
        failure_threshold: int = 3,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def record_success(self) -> None:
        """Reset failure metrics on successful operation."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def record_failure(self) -> None:
        """Increment failure count and trip circuit if threshold exceeded."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN

    def can_execute(self) -> bool:
        """Check if execution is permissible under current circuit state."""
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.cooldown_seconds:
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False

        # HALF_OPEN: allow canary execution
        return True

    def get_remaining_cooldown(self) -> float:
        if self.state != CircuitBreakerState.OPEN:
            return 0.0
        elapsed = time.time() - self.last_failure_time
        return max(0.0, self.cooldown_seconds - elapsed)

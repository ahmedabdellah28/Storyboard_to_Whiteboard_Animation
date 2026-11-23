"""Revision management and downstream invalidation tracker for Whiteboard Studio.

Part of Phase 2: Invalidation + Revision System & Artifact Integration.
Guarantees race-condition safety, revision monotonicity, and precise cascade computation.
"""

from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from core.contracts.studio_contracts import (
    CANONICAL_STAGES_ORDER,
    STAGE_DEFINITIONS,
    EditTransaction,
    RevisionToken,
    StageDefinition,
    StageIdentifier,
)
from core.state.project_state import ProjectState, SectionState
from core.state.state_store import StateStore, get_state_store
from core.state.transitions import (
    SectionLifecycleStatus,
    TaskLifecycleStatus,
)
from core.state.workflow_events import (
    RevisionIncrementedEvent,
    SectionStatusChangedEvent,
    TaskStatusChangedEvent,
    WorkflowEventBus,
    get_workflow_event_bus,
)


class RevisionManager:
    """Coordinates revisions and calculates cryptographic & structural invalidation cascades."""

    def __init__(
        self,
        state_store: Optional[StateStore] = None,
        event_bus: Optional[WorkflowEventBus] = None,
    ) -> None:
        self.state_store = state_store or get_state_store()
        self.event_bus = event_bus or get_workflow_event_bus()
        self._lock = threading.RLock()
        self._active_transactions: Dict[str, EditTransaction] = {}

    def get_current_revision(self, project_id: str, section_id: str) -> int:
        """Fetch current monotonic revision number for a section."""
        with self._lock:
            state = self.state_store.load_state(project_id)
            if section_id in state.sections:
                return state.sections[section_id].revision_id
            return 1

    def create_task_token(self, project_id: str, section_id: str) -> RevisionToken:
        """Generate an immutable token representing the current section revision for a task."""
        with self._lock:
            rev_id = self.get_current_revision(project_id, section_id)
            return RevisionToken(
                project_id=project_id,
                section_id=section_id,
                revision_id=rev_id,
                transaction_uuid=str(uuid.uuid4()),
            )

    def is_token_current(self, token: RevisionToken) -> bool:
        """Verify whether a background task's revision token is still fresh."""
        with self._lock:
            current_rev = self.get_current_revision(token.project_id, token.section_id)
            return token.revision_id == current_rev

    def compute_downstream_invalidations(self, mutated_field_or_stage: str) -> Set[StageIdentifier]:
        """Compute full downstream invalidation set for a mutation.
        
        Uses canonical StageDefinition dependency topology and specific mutation heuristics.
        """
        # 1. Check if string matches a known field heuristic in EditTransaction
        field_invals = EditTransaction.compute_invalidations(mutated_field_or_stage)
        if field_invals:
            return field_invals

        # 2. Check if string is a StageIdentifier
        stage_enum: Optional[StageIdentifier] = None
        for s in StageIdentifier:
            if s.value == mutated_field_or_stage or s.name.lower() == mutated_field_or_stage.lower():
                stage_enum = s
                break

        if stage_enum is None:
            return set()

        # Compute transitive dependents in canonical 18-stage DAG
        invalidated: Set[StageIdentifier] = set()
        queue = [stage_enum]

        # Build reverse dependency map
        reverse_deps: Dict[StageIdentifier, Set[StageIdentifier]] = {s: set() for s in StageIdentifier}
        for sid, defn in STAGE_DEFINITIONS.items():
            for up in defn.upstream_dependencies:
                reverse_deps[up].add(sid)

        while queue:
            curr = queue.pop(0)
            for dep in reverse_deps.get(curr, set()):
                if dep not in invalidated:
                    # Special Rule: SFX or Audio Mix changes do NOT invalidate Stage 14 (Visual Frame Render)
                    if curr in (StageIdentifier.SFX, StageIdentifier.AUDIO_MIX) and dep == StageIdentifier.RENDER:
                        continue
                    invalidated.add(dep)
                    queue.append(dep)

        return invalidated

    def begin_transaction(
        self,
        project_id: str,
        section_id: str,
        mutated_field: str,
        description: str = "",
    ) -> EditTransaction:
        """Initiate an edit transaction and precalculate invalidation cascades."""
        with self._lock:
            current_rev = self.get_current_revision(project_id, section_id)
            invals = self.compute_downstream_invalidations(mutated_field)

            tx = EditTransaction(
                project_id=project_id,
                section_id=section_id,
                mutated_fields=[mutated_field],
                description=description,
                target_revision_id=current_rev + 1,
                invalidated_stages=invals,
            )
            self._active_transactions[tx.transaction_uuid] = tx
            return tx

    def commit_transaction(self, transaction: EditTransaction) -> RevisionToken:
        """Atomically commit an edit transaction, invalidating affected tasks in StateStore."""
        with self._lock:
            project_id = transaction.project_id
            section_id = transaction.section_id

            state = self.state_store.load_state(project_id)
            sec = state.get_or_create_section(section_id)
            old_rev = sec.revision_id
            new_rev = transaction.target_revision_id

            # 1. Update section revision
            sec.revision_id = new_rev

            # 2. Invalidate affected tasks in section state
            invalidated_stage_ids = [s.value for s in transaction.invalidated_stages]
            for stage_id in invalidated_stage_ids:
                # Task IDs are typically "{section_id}.{stage_suffix}" or "{section_id}_{stage_suffix}"
                for tid, task in list(sec.tasks.items()):
                    if any(s.value in tid or s.name.lower() in tid.lower() for s in transaction.invalidated_stages):
                        old_st = task.status
                        if old_st != TaskLifecycleStatus.INVALIDATED:
                            task.status = TaskLifecycleStatus.INVALIDATED
                            self.event_bus.publish(
                                TaskStatusChangedEvent(
                                    project_id=project_id,
                                    section_id=section_id,
                                    task_id=tid,
                                    old_status=old_st,
                                    new_status=TaskLifecycleStatus.INVALIDATED,
                                    revision_id=new_rev,
                                )
                            )

            # 3. Recalculate section lifecycle
            old_sec_status = sec.lifecycle_status
            sec.recompute_lifecycle()
            self.state_store.save_state(state)

            # Clean up active transaction
            self._active_transactions.pop(transaction.transaction_uuid, None)

            # 4. Publish workflow events
            self.event_bus.publish(
                RevisionIncrementedEvent(
                    project_id=project_id,
                    section_id=section_id,
                    old_revision=old_rev,
                    new_revision=new_rev,
                    reason=transaction.description or f"Mutated {transaction.mutated_fields}",
                    invalidated_stages=invalidated_stage_ids,
                )
            )
            if old_sec_status != sec.lifecycle_status:
                self.event_bus.publish(
                    SectionStatusChangedEvent(
                        project_id=project_id,
                        section_id=section_id,
                        old_status=old_sec_status,
                        new_status=sec.lifecycle_status,
                        revision_id=new_rev,
                    )
                )

            return RevisionToken(
                project_id=project_id,
                section_id=section_id,
                revision_id=new_rev,
                transaction_uuid=transaction.transaction_uuid,
            )

    def abort_transaction(self, transaction: EditTransaction) -> None:
        """Cancel an uncommitted transaction."""
        with self._lock:
            self._active_transactions.pop(transaction.transaction_uuid, None)


_GLOBAL_REVISION_MANAGER: Optional[RevisionManager] = None
_REV_LOCK = threading.Lock()


def get_revision_manager() -> RevisionManager:
    global _GLOBAL_REVISION_MANAGER
    with _REV_LOCK:
        if _GLOBAL_REVISION_MANAGER is None:
            _GLOBAL_REVISION_MANAGER = RevisionManager()
        return _GLOBAL_REVISION_MANAGER

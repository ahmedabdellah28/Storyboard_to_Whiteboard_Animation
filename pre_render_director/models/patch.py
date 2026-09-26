"""Timeline patch models for deterministic, non-destructive timeline repair."""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class PatchOperation(str, Enum):
    ADD_EVENT = "ADD_EVENT"
    REMOVE_EVENT = "REMOVE_EVENT"
    UPDATE_EVENT = "UPDATE_EVENT"
    MOVE_EVENT = "MOVE_EVENT"
    RESIZE_EVENT = "RESIZE_EVENT"
    CHANGE_ASSET = "CHANGE_ASSET"
    CHANGE_ACTION = "CHANGE_ACTION"
    CHANGE_SFX = "CHANGE_SFX"
    CHANGE_CAMERA = "CHANGE_CAMERA"
    KEEP_EVENT = "KEEP_EVENT"
    REJECT_EVENT = "REJECT_EVENT"

class TimelinePatch(BaseModel):
    patch_id: str
    operation: PatchOperation
    event_id: Optional[str] = None
    from_asset: Optional[str] = None
    to_asset: Optional[str] = None
    changes: Dict[str, Any] = Field(default_factory=dict)
    new_event: Optional[Dict[str, Any]] = None
    confidence: float = 1.0
    reason: str = ""
    needs_review: bool = False

    def is_review_required(self, threshold: float = 0.65) -> bool:
        return self.needs_review or (self.confidence < threshold)

class PatchBatch(BaseModel):
    iteration: int = 1
    patches: List[TimelinePatch] = Field(default_factory=list)
    applied_count: int = 0
    rejected_count: int = 0
    notes: List[str] = Field(default_factory=list)

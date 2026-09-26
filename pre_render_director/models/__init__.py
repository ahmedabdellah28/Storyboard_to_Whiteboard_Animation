"""Models for Pre-Render Visual Director."""

from .input import (
    AssetMetadata,
    AssetCatalog,
    SectionInput,
    WordItem,
    SentenceItem,
    PauseItem,
    SemanticBeatItem
)
from .event import (
    ActionType,
    TimingStrategy,
    RenderEvent,
    SFXEvent,
    CameraEvent
)
from .patch import (
    PatchOperation,
    TimelinePatch,
    PatchBatch
)
from .output import (
    ValidationStatus,
    SemanticMatchScore,
    ValidationCheckResult,
    ValidationReport,
    VisualStateSnapshot,
    FinalRenderPlan
)

__all__ = [
    "AssetMetadata",
    "AssetCatalog",
    "SectionInput",
    "WordItem",
    "SentenceItem",
    "PauseItem",
    "SemanticBeatItem",
    "ActionType",
    "TimingStrategy",
    "RenderEvent",
    "SFXEvent",
    "CameraEvent",
    "PatchOperation",
    "TimelinePatch",
    "PatchBatch",
    "ValidationStatus",
    "SemanticMatchScore",
    "ValidationCheckResult",
    "ValidationReport",
    "VisualStateSnapshot",
    "FinalRenderPlan",
]

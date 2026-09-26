"""Output models for the Final Render Plan and QA Validation Reports."""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .event import RenderEvent
from .patch import TimelinePatch

class ValidationStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    BLOCK_RENDER = "BLOCK_RENDER"

class SemanticMatchScore(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    STRONG_MATCH = "STRONG_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    WEAK_MATCH = "WEAK_MATCH"
    CONTRADICTORY = "CONTRADICTORY"
    INVALID = "INVALID"

class ValidationCheckResult(BaseModel):
    check_id: str
    name: str
    passed: bool = True
    severity: str = "ERROR"  # ERROR, WARNING, INFO
    details: List[str] = Field(default_factory=list)

class ValidationReport(BaseModel):
    status: ValidationStatus = ValidationStatus.PASS
    overall_score: float = 1.0
    checks: List[ValidationCheckResult] = Field(default_factory=list)
    unresolved_issues: List[str] = Field(default_factory=list)
    missing_assets: List[Dict[str, str]] = Field(default_factory=list)
    review_required: bool = False
    review_items: List[Dict[str, Any]] = Field(default_factory=list)

class VisualStateSnapshot(BaseModel):
    time_s: float
    visible_assets: List[str] = Field(default_factory=list)
    drawing: List[str] = Field(default_factory=list)
    highlighted: List[str] = Field(default_factory=list)
    camera_focus: Optional[str] = None
    density: int = 0

class FinalRenderPlan(BaseModel):
    contract_version: str = "1.0.0"
    section_id: str
    audio_file: str
    audio_duration: float
    fps: int = 30
    resolution: Dict[str, int] = Field(default_factory=lambda: {"width": 1920, "height": 1080})
    validation: ValidationReport
    applied_patches: List[TimelinePatch] = Field(default_factory=list)
    render_events: List[Dict[str, Any]] = Field(default_factory=list)
    visual_states: List[VisualStateSnapshot] = Field(default_factory=list)
    review_required: bool = False

    def export_json(self) -> str:
        return self.model_dump_json(indent=2)

"""Contract: QA Reports for OSAS v3.1 Architecture.

Defines AssetCoverageReport and VisualQAReport with 10 strict Gates (A through J).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QAGateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class BlankOpeningType(str, Enum):
    UNEXPLAINED_BLANK = "UNEXPLAINED_BLANK"
    INTENTIONAL_INTRO = "INTENTIONAL_INTRO"
    PRE_SPEECH_MUSIC = "PRE_SPEECH_MUSIC"
    WAIT_FOR_FIRST_SEMANTIC_ANCHOR = "WAIT_FOR_FIRST_SEMANTIC_ANCHOR"


class AssetCoverageReport(BaseModel):
    contract_type: str = Field(default="asset_coverage_report", frozen=True)
    section_id: str
    total_extracted_assets: int
    classification_summary: Dict[str, int]
    total_required_assets: int
    scheduled_required_assets: int
    missing_assets: List[str] = Field(default_factory=list)
    unresolved_assets: List[str] = Field(default_factory=list)
    coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    status: QAGateStatus = Field(default=QAGateStatus.PASS)
    details: str = Field(default="")


class QAGateResult(BaseModel):
    gate_id: str
    gate_name: str
    status: QAGateStatus
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class VisualQAReport(BaseModel):
    contract_type: str = Field(default="visual_qa_report", frozen=True)
    section_id: str
    overall_status: QAGateStatus = Field(default=QAGateStatus.PASS)
    total_gates_evaluated: int = 10
    passed_gates: int = 10
    failed_gates: int = 0
    gates: List[QAGateResult] = Field(default_factory=list)
    summary: str = Field(default="")


class QACheckResult(BaseModel):
    check_id: str
    name: str
    status: QAGateStatus
    details: str = Field(default="")
    metrics: Dict[str, Any] = Field(default_factory=dict)


class PostRenderQAReport(BaseModel):
    contract_type: str = Field(default="post_render_qa_report", frozen=True)
    section_id: str
    video_path: str
    overall_status: QAGateStatus = Field(default=QAGateStatus.PASS)
    video_duration: float = 0.0
    audio_duration: float = 0.0
    duration_drift: float = 0.0
    total_frames: int = 0
    fps: float = 30.0
    resolution: str = "1920x1080"
    black_frames_count: int = 0
    frozen_frames_count: int = 0
    audio_clipping_detected: bool = False
    checks: List[QACheckResult] = Field(default_factory=list)
    summary: str = Field(default="")


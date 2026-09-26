"""Renderer contract and event models."""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ActionType(str, Enum):
    DRAW = "draw"
    ERASE = "erase"
    REVEAL = "reveal"
    CONNECT = "connect"
    HIGHLIGHT = "highlight"
    MOVE = "move"
    CAMERA = "camera"
    SFX = "sfx"
    WRITE = "write"

class TimingStrategy(str, Enum):
    START_ON_ANCHOR = "START_ON_ANCHOR"
    COMPLETE_ON_ANCHOR = "COMPLETE_ON_ANCHOR"
    CENTER_ON_ANCHOR = "CENTER_ON_ANCHOR"
    REVEAL_ON_ANCHOR = "REVEAL_ON_ANCHOR"
    DURING_PAUSE = "DURING_PAUSE"
    AFTER_ANCHOR = "AFTER_ANCHOR"
    FOLLOW_EVENT = "FOLLOW_EVENT"

class RenderEvent(BaseModel):
    event_id: str
    type: ActionType = ActionType.DRAW
    asset_id: Optional[str] = None
    start_s: float
    end_s: float
    duration_s: float
    action: str = "draw"
    timing_strategy: TimingStrategy = TimingStrategy.COMPLETE_ON_ANCHOR
    anchor_text: str = ""
    anchor_start_s: Optional[float] = None
    anchor_end_s: Optional[float] = None
    layer_order: int = 0
    keep_visible: bool = True
    fade_out_at: Optional[float] = None
    confidence: float = 1.0
    target_asset_id: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

    def to_renderer_dict(self) -> Dict[str, Any]:
        """Output clean self-contained contract for downstream renderer."""
        return {
            "event_id": self.event_id,
            "type": self.type.value if isinstance(self.type, ActionType) else str(self.type),
            "asset_id": self.asset_id,
            "start_s": round(self.start_s, 3),
            "end_s": round(self.end_s, 3),
            "duration_s": round(self.duration_s, 3),
            "action": self.action,
            "layer_order": self.layer_order,
            "keep_visible": self.keep_visible,
            "fade_out_at": round(self.fade_out_at, 3) if self.fade_out_at is not None else None,
            "target_asset_id": self.target_asset_id,
            "params": self.params
        }

class SFXEvent(BaseModel):
    event_id: str
    sfx_type: str = "marker_draw"
    start_s: float
    end_s: float
    duration_s: float
    anchor_asset_id: Optional[str] = None
    anchor_event_id: Optional[str] = None
    volume: float = 0.7

    def to_render_event(self) -> RenderEvent:
        return RenderEvent(
            event_id=self.event_id,
            type=ActionType.SFX,
            asset_id=self.anchor_asset_id,
            start_s=self.start_s,
            end_s=self.end_s,
            duration_s=self.duration_s,
            action=self.sfx_type,
            params={"volume": self.volume, "anchor_event_id": self.anchor_event_id}
        )

class CameraEvent(BaseModel):
    event_id: str
    camera_type: str = "pan"  # pan, zoom, focus
    start_s: float
    end_s: float
    duration_s: float
    target_asset_id: Optional[str] = None
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0

    def to_render_event(self) -> RenderEvent:
        return RenderEvent(
            event_id=self.event_id,
            type=ActionType.CAMERA,
            target_asset_id=self.target_asset_id,
            start_s=self.start_s,
            end_s=self.end_s,
            duration_s=self.duration_s,
            action=self.camera_type,
            params={"zoom": self.zoom, "pan_x": self.pan_x, "pan_y": self.pan_y}
        )

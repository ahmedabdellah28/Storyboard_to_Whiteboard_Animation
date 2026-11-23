"""
Typed data contracts and validators for Creative Stickman Studio V3:
character.json, pose.json, motion.json, action.json, target.json.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TargetSpec:
    target_id: str = "demo_card"
    target_type: str = "card"
    label: str = "KEY IDEA"
    x: float = 470.0
    y: float = 340.0
    width: float = 120.0
    height: float = 84.0
    color: str = "#0072CE"
    accent: str = "#FFD400"


@dataclass
class ActionEvent:
    phase: str  # prepare | move | contact | response | release | recover
    t_norm: float
    anchor: str
    detail: str


@dataclass
class ActionSpec:
    schema_version: str
    action_id: str
    number: int
    category: str
    title: str
    description: str
    duration_frames: int
    fps: int = 30
    required_anchors: List[str] = field(default_factory=list)
    target_type: str = "none"
    camera_suggestion: Dict[str, Any] = field(default_factory=dict)
    sound_cue_suggestion: Dict[str, Any] = field(default_factory=dict)
    effect_nodes: List[Dict[str, Any]] = field(default_factory=list)
    configurable_params: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    keyframes: List[Dict[str, Any]] = field(default_factory=list)
    expression_track: List[Dict[str, Any]] = field(default_factory=list)
    hand_track: List[Dict[str, Any]] = field(default_factory=list)
    prop_track: List[Dict[str, Any]] = field(default_factory=list)
    recovery_pose: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        errs: List[str] = []
        if not self.action_id:
            errs.append("action_id is required")
        if self.duration_frames < 15:
            errs.append(f"duration_frames too short: {self.duration_frames}")
        if not self.keyframes:
            errs.append("keyframes cannot be empty")
        phases = {e.get("phase") for e in self.events}
        for req in ("prepare", "move", "contact", "response", "release", "recover"):
            if req not in phases:
                errs.append(f"missing causal event phase: {req}")
        return errs

    def to_dict(self) -> dict:
        return asdict(self)


def load_rig(rig_path: Path) -> dict:
    return json.loads(rig_path.read_text(encoding="utf-8"))

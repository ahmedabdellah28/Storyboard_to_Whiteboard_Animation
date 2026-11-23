"""
Headless Character & Rig Control API for Creative Stickman Studio V3.2.
Exposes explicit commands:
  set_joint_angle, set_joint_position, set_ik_target, set_finger_curl,
  set_gaze_target, set_expression, set_viseme, set_view_id, set_view_blend,
  play_clip, render_frames, export_svg.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from creative_v3.characters.brand_mascot_v1.turnaround_builder import (
    EMOTIONS_12,
    VIEW_IDS,
    VISEMES_9,
)
from creative_v3.engine.kinematics.ik_solver import blend_ik_fk, solve_two_bone_ik
from creative_v3.engine.renderers.svg_renderer import (
    apply_pose_to_svg,
    build_contact_sheet,
    encode_preview_webm,
    load_view_svg_bytes,
    render_svg_bytes_to_png,
)
from creative_v3.engine.rigging.rig_model import load_rig


DEFAULT_RIG_PATH = Path(__file__).resolve().parents[1] / "characters" / "brand_mascot_v1" / "rig.json"


@dataclass
class RigState:
    pose: Dict[str, dict] = field(default_factory=dict)
    view_id: str = "front"
    view_blend: float = 0.0
    expression: str = "smile"
    viseme: Optional[str] = None
    gaze_xy: Tuple[float, float] = (0.0, 0.0)
    eyelid_left: Optional[float] = None
    eyelid_right: Optional[float] = None
    brow_left: Dict[str, float] = field(default_factory=lambda: {"ty": 0.0, "rot": 0.0})
    brow_right: Dict[str, float] = field(default_factory=lambda: {"ty": 0.0, "rot": 0.0})
    left_hand: str = "fist"
    right_hand: str = "open_palm"
    finger_curls: Dict[str, Dict[str, float]] = field(default_factory=dict)
    finger_spread: Dict[str, float] = field(default_factory=dict)
    scene_svg_behind: str = ""
    scene_svg_front: str = ""


def create_rig_state() -> RigState:
    return RigState()


def set_joint_angle(state: RigState, joint_id: str, angle_deg: float) -> RigState:
    rig = load_rig(DEFAULT_RIG_PATH)
    bone = rig.get("bones", {}).get(joint_id)
    if bone and "limits" in bone:
        lo, hi = bone["limits"]
        angle_deg = max(float(lo), min(float(hi), float(angle_deg)))
    entry = dict(state.pose.get(joint_id, {}))
    entry["rot"] = float(angle_deg)
    state.pose[joint_id] = entry
    return state


def set_joint_position(state: RigState, joint_id: str, tx: float, ty: float) -> RigState:
    entry = dict(state.pose.get(joint_id, {}))
    entry["tx"] = float(tx)
    entry["ty"] = float(ty)
    state.pose[joint_id] = entry
    return state


def set_ik_target(
    state: RigState,
    chain_id: str,
    target_xy: Tuple[float, float],
    weight: float = 1.0,
    bend_dir: int = 1,
) -> RigState:
    rig = load_rig(DEFAULT_RIG_PATH)
    chain = rig["ik_chains"][chain_id]
    upper = chain["upper"]
    lower = chain["lower"]
    upper_pivot = rig["bones"][upper]["pivot"]
    # Solve two-bone IK in local character coordinates
    ik_res = solve_two_bone_ik(
        root_xy=(float(upper_pivot[0]), float(upper_pivot[1])),
        target_xy=(float(target_xy[0]), float(target_xy[1])),
        l1=float(chain["l1"]),
        l2=float(chain["l2"]),
        bend_direction=bend_dir,
    )
    fk_u = float(state.pose.get(upper, {}).get("rot", 0.0))
    fk_l = float(state.pose.get(lower, {}).get("rot", 0.0))
    bu = blend_ik_fk(fk_u, ik_res.upper_angle_deg, weight)
    bl = blend_ik_fk(fk_l, ik_res.lower_angle_deg, weight)
    set_joint_angle(state, upper, bu)
    set_joint_angle(state, lower, bl)
    return state


def set_finger_curl(
    state: RigState,
    side: str,
    finger: str,
    curl: float,
    spread: Optional[float] = None,
) -> RigState:
    if side not in ("left", "right"):
        raise ValueError(f"Invalid side: {side}")
    if finger not in ("thumb", "index", "middle", "ring", "pinky"):
        raise ValueError(f"Invalid finger: {finger}")
    state.finger_curls.setdefault(side, {})[finger] = max(0.0, min(1.0, float(curl)))
    if spread is not None:
        state.finger_spread[side] = max(-1.0, min(1.0, float(spread)))
    if side == "left":
        state.left_hand = "articulated"
    else:
        state.right_hand = "articulated"
    return state


def set_gaze_target(state: RigState, gx: float, gy: float) -> RigState:
    state.gaze_xy = (max(-1.0, min(1.0, float(gx))), max(-1.0, min(1.0, float(gy))))
    return state


def set_expression(state: RigState, expression: str) -> RigState:
    if expression not in EMOTIONS_12 and expression not in ("blink", "squint", "wink"):
        raise ValueError(f"Unsupported expression: {expression}")
    state.expression = expression
    state.viseme = None
    return state


def set_viseme(state: RigState, viseme: Optional[str]) -> RigState:
    if viseme is not None:
        vkey = viseme if viseme.startswith("viseme_") else f"viseme_{viseme}"
        if vkey not in VISEMES_9:
            raise ValueError(f"Unsupported viseme: {viseme}")
        state.viseme = vkey
    else:
        state.viseme = None
    return state


def set_view_id(state: RigState, view_id: str) -> RigState:
    if view_id not in VIEW_IDS:
        raise ValueError(f"Unsupported view_id: {view_id}")
    state.view_id = view_id
    return state


def set_view_blend(state: RigState, blend: float) -> RigState:
    state.view_blend = max(0.0, min(1.0, float(blend)))
    return state


def export_svg(state: RigState, out_svg_path: Path) -> Path:
    svg_master = load_view_svg_bytes(state.view_id)
    rendered = apply_pose_to_svg(
        master_svg_bytes=svg_master,
        pose=state.pose,
        expression=state.expression,
        left_hand=state.left_hand,
        right_hand=state.right_hand,
        scene_svg_behind=state.scene_svg_behind,
        scene_svg_front=state.scene_svg_front,
        viseme=state.viseme,
        gaze_xy=state.gaze_xy,
        eyelid_left=state.eyelid_left,
        eyelid_right=state.eyelid_right,
        brow_left=state.brow_left,
        brow_right=state.brow_right,
        finger_curls=state.finger_curls or None,
        finger_spread=state.finger_spread or None,
        view_blend=state.view_blend,
    )
    out_svg_path.parent.mkdir(parents=True, exist_ok=True)
    out_svg_path.write_bytes(rendered)
    return out_svg_path


def render_frames(
    state_sequence: List[RigState],
    out_dir: Path,
    width: int = 640,
    height: int = 480,
) -> List[Path]:
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_paths: List[Path] = []
    trace: List[dict] = []
    for idx, st in enumerate(state_sequence):
        svg_master = load_view_svg_bytes(st.view_id)
        svg_bytes = apply_pose_to_svg(
            master_svg_bytes=svg_master,
            pose=st.pose,
            expression=st.expression,
            left_hand=st.left_hand,
            right_hand=st.right_hand,
            scene_svg_behind=st.scene_svg_behind,
            scene_svg_front=st.scene_svg_front,
            viseme=st.viseme,
            gaze_xy=st.gaze_xy,
            eyelid_left=st.eyelid_left,
            eyelid_right=st.eyelid_right,
            brow_left=st.brow_left,
            brow_right=st.brow_right,
            finger_curls=st.finger_curls or None,
            finger_spread=st.finger_spread or None,
            view_blend=st.view_blend,
        )
        out_png = frames_dir / f"frame_{idx:04d}.png"
        render_svg_bytes_to_png(svg_bytes, out_png, width=width, height=height)
        frame_paths.append(out_png)
        trace.append({
            "frame": idx,
            "view_id": st.view_id,
            "view_blend": st.view_blend,
            "expression": st.expression,
            "viseme": st.viseme,
            "gaze_xy": list(st.gaze_xy),
            "left_hand": st.left_hand,
            "right_hand": st.right_hand,
            "pose": copy.deepcopy(st.pose),
            "finger_curls": copy.deepcopy(st.finger_curls),
        })
    (out_dir / "control_trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    return frame_paths


def play_clip(
    clip_id: str,
    state_sequence: List[RigState],
    out_dir: Path,
    width: int = 640,
    height: int = 480,
    fps: int = 30,
) -> dict:
    """Render full RGBA frames, contact sheet, preview WebM, motion JSON, and control trace."""
    out_dir.mkdir(parents=True, exist_ok=True)
    frame_paths = render_frames(state_sequence, out_dir, width=width, height=height)
    contact_sheet = build_contact_sheet(frame_paths, out_dir / "contact_sheet.png")
    preview_webm = encode_preview_webm(out_dir / "frames", out_dir / "preview.webm", fps=fps)
    motion_meta = {
        "clip_id": clip_id,
        "frame_count": len(frame_paths),
        "fps": fps,
        "resolution": [width, height],
        "preview_webm": str(preview_webm),
        "contact_sheet": str(contact_sheet),
        "control_trace": str(out_dir / "control_trace.json"),
    }
    (out_dir / "motion.json").write_text(json.dumps(motion_meta, indent=2), encoding="utf-8")
    return motion_meta

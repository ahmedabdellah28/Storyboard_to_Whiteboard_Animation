"""
Deterministic 2-bone analytical IK solver, joint limit clamping, IK/FK blending,
and hierarchical forward kinematics for Creative Stickman Studio V3.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class TwoBoneIKResult:
    upper_angle_deg: float
    lower_angle_deg: float
    reached: bool
    target_distance: float


def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def solve_two_bone_ik(
    root_xy: Tuple[float, float],
    target_xy: Tuple[float, float],
    l1: float,
    l2: float,
    bend_direction: int = 1,
    upper_limits: Tuple[float, float] = (-175.0, 175.0),
    lower_limits: Tuple[float, float] = (-160.0, 160.0),
) -> TwoBoneIKResult:
    """
    Analytical 2-bone IK solver in 2D.
    Returns relative rotation angles (degrees) for upper and lower bones.
    """
    dx = target_xy[0] - root_xy[0]
    dy = target_xy[1] - root_xy[1]
    dist = math.hypot(dx, dy)
    min_reach = abs(l1 - l2) + 1e-3
    max_reach = (l1 + l2) - 1e-3
    reached = min_reach <= dist <= max_reach
    d = clamp(dist, min_reach, max_reach)

    cos_a = clamp((l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d), -1.0, 1.0)
    angle_a = math.acos(cos_a)

    cos_b = clamp((l1 * l1 + l2 * l2 - d * d) / (2.0 * l1 * l2), -1.0, 1.0)
    angle_b = math.acos(cos_b)

    base_angle = math.atan2(dy, dx)
    theta1 = base_angle - bend_direction * angle_a
    theta2 = bend_direction * (math.pi - angle_b)

    u_deg = clamp(math.degrees(theta1), upper_limits[0], upper_limits[1])
    l_deg = clamp(math.degrees(theta2), lower_limits[0], lower_limits[1])
    return TwoBoneIKResult(
        upper_angle_deg=round(u_deg, 3),
        lower_angle_deg=round(l_deg, 3),
        reached=reached,
        target_distance=round(dist, 3),
    )


def blend_ik_fk(fk_deg: float, ik_deg: float, weight: float) -> float:
    """Linearly blend between FK and IK joint angles (weight in [0, 1])."""
    w = clamp(weight, 0.0, 1.0)
    return fk_deg * (1.0 - w) + ik_deg * w


def compute_world_transforms(
    rig: dict,
    pose: Dict[str, dict],
) -> Dict[str, Tuple[float, float, float]]:
    """
    Evaluate world-space (x, y, rotation_deg) for every bone in `rig["bones"]`
    given local pose overrides {bone_id: {"rx": dx, "ry": dy, "rot": deg}}.
    """
    bones = rig["bones"]
    world: Dict[str, Tuple[float, float, float]] = {}

    def _resolve(bone_id: str) -> Tuple[float, float, float]:
        if bone_id in world:
            return world[bone_id]
        b = bones[bone_id]
        px, py = b["pivot"]
        local = pose.get(bone_id, {})
        dx = float(local.get("tx", 0.0))
        dy = float(local.get("ty", 0.0))
        rot = float(local.get("rot", 0.0))
        limits = b.get("limits")
        if limits:
            rot = clamp(rot, float(limits[0]), float(limits[1]))

        parent_id: Optional[str] = b.get("parent")
        if parent_id is None:
            wx, wy, wrot = px + dx, py + dy, rot
        else:
            pwx, pwy, pwrot = _resolve(parent_id)
            p_px, p_py = bones[parent_id]["pivot"]
            rel_x = (px - p_px) + dx
            rel_y = (py - p_py) + dy
            rad = math.radians(pwrot)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            wx = pwx + rel_x * cos_r - rel_y * sin_r
            wy = pwy + rel_x * sin_r + rel_y * cos_r
            wrot = pwrot + rot
        world[bone_id] = (round(wx, 2), round(wy, 2), round(wrot, 2))
        return world[bone_id]

    for bid in bones:
        _resolve(bid)
    return world


def compute_anchor_positions(
    rig: dict,
    world_bones: Dict[str, Tuple[float, float, float]],
) -> Dict[str, Tuple[float, float]]:
    """Resolve all named interaction anchors to world (x, y) coordinates."""
    anchors_out: Dict[str, Tuple[float, float]] = {}
    for name, cfg in rig.get("anchors", {}).items():
        bx, by, brot = world_bones[cfg["bone"]]
        ox, oy = cfg["offset"]
        rad = math.radians(brot)
        wx = bx + ox * math.cos(rad) - oy * math.sin(rad)
        wy = by + ox * math.sin(rad) + oy * math.cos(rad)
        anchors_out[name] = (round(wx, 2), round(wy, 2))
    return anchors_out

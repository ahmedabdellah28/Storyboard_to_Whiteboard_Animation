"""
Timeline easing curves, keyframe track interpolation, and secondary motion physics
for Creative Stickman Studio V3.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple


def ease_value(t: float, curve: str = "ease_in_out") -> float:
    """Evaluate normalized easing curve for t in [0, 1]."""
    t = max(0.0, min(1.0, float(t)))
    if curve == "linear":
        return t
    if curve == "ease_in":
        return t * t * t
    if curve == "ease_out":
        return 1.0 - (1.0 - t) ** 3
    if curve == "ease_in_out":
        return 4 * t * t * t if t < 0.5 else 1.0 - ((-2 * t + 2) ** 3) / 2.0
    if curve == "back_out":
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * ((t - 1.0) ** 3) + c1 * ((t - 1.0) ** 2)
    if curve == "anticipation":
        c1 = 1.8
        c3 = c1 + 1.0
        return c3 * (t ** 3) - c1 * (t ** 2)
    if curve == "elastic_out":
        if t in (0.0, 1.0):
            return t
        return (2.0 ** (-10.0 * t)) * math.sin((t * 10.0 - 0.75) * (2.0 * math.pi / 3.0)) + 1.0
    if curve == "bounce_out":
        n1, d1 = 7.5625, 2.75
        if t < 1.0 / d1:
            return n1 * t * t
        if t < 2.0 / d1:
            t -= 1.5 / d1
            return n1 * t * t + 0.75
        if t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + 0.9375
        t -= 2.625 / d1
        return n1 * t * t + 0.984375
    if curve == "spring":
        return 1.0 - math.exp(-6.0 * t) * math.cos(14.0 * t)
    if curve == "snap":
        return 1.0 if t >= 0.85 else (t / 0.85) ** 4
    return t


def interpolate_scalar_keyframes(
    keyframes: Sequence[Tuple[float, float, str]],
    t_norm: float,
) -> float:
    """
    Interpolate (time_norm, value, easing_name) keyframes at t_norm in [0, 1].
    """
    if not keyframes:
        return 0.0
    if t_norm <= keyframes[0][0]:
        return float(keyframes[0][1])
    if t_norm >= keyframes[-1][0]:
        return float(keyframes[-1][1])
    for idx in range(len(keyframes) - 1):
        t0, v0, _ = keyframes[idx]
        t1, v1, ease_name = keyframes[idx + 1]
        if t0 <= t_norm <= t1:
            span = max(1e-6, t1 - t0)
            local_t = (t_norm - t0) / span
            eased = ease_value(local_t, ease_name)
            return float(v0) + (float(v1) - float(v0)) * eased
    return float(keyframes[-1][1])


def interpolate_pose_keyframes(
    pose_keyframes: Sequence[dict],
    t_norm: float,
) -> Dict[str, dict]:
    """
    Interpolate structured pose keyframes:
    [{"t": 0.0, "ease": "ease_in_out", "bones": {"head_group": {"rot": -10}, ...}}, ...]
    """
    if not pose_keyframes:
        return {}
    if t_norm <= pose_keyframes[0]["t"]:
        return {k: dict(v) for k, v in pose_keyframes[0].get("bones", {}).items()}
    if t_norm >= pose_keyframes[-1]["t"]:
        return {k: dict(v) for k, v in pose_keyframes[-1].get("bones", {}).items()}

    for idx in range(len(pose_keyframes) - 1):
        k0 = pose_keyframes[idx]
        k1 = pose_keyframes[idx + 1]
        if k0["t"] <= t_norm <= k1["t"]:
            span = max(1e-6, k1["t"] - k0["t"])
            eased = ease_value((t_norm - k0["t"]) / span, k1.get("ease", "ease_in_out"))
            b0 = k0.get("bones", {})
            b1 = k1.get("bones", {})
            all_bones = set(b0.keys()) | set(b1.keys())
            out: Dict[str, dict] = {}
            for bone in all_bones:
                p0 = b0.get(bone, {})
                p1 = b1.get(bone, {})
                merged: dict = {}
                for prop in ("tx", "ty", "rot", "sx", "sy"):
                    if prop in p0 or prop in p1:
                        default_v = 1.0 if prop in ("sx", "sy") else 0.0
                        v0 = float(p0.get(prop, default_v))
                        v1 = float(p1.get(prop, default_v))
                        merged[prop] = round(v0 + (v1 - v0) * eased, 3)
                if merged:
                    out[bone] = merged
            return out
    return {}


def apply_secondary_tie_physics(
    pose: Dict[str, dict],
    torso_rot: float,
    root_vx: float,
    t_sec: float,
) -> Dict[str, dict]:
    """Add spring-like follow-through swing to tie_group based on torso motion."""
    tie = dict(pose.get("tie_group", {}))
    base_rot = float(tie.get("rot", 0.0))
    lag = -0.35 * torso_rot - 0.15 * root_vx + 2.2 * math.sin(t_sec * 5.0)
    tie["rot"] = round(max(-50.0, min(50.0, base_rot + lag)), 2)
    pose["tie_group"] = tie
    return pose

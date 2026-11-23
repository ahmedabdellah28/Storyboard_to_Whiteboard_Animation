"""
V3.2 Phase C+4: Mandatory Character Readiness Gallery (12 executable test clips).
Each clip produces RGBA frames, preview.webm, contact_sheet.png, motion.json,
control_trace.json, and readiness_qa.json inside character_readiness_gallery/.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List

from creative_v3.api.commands import (
    RigState,
    create_rig_state,
    play_clip,
    set_expression,
    set_finger_curl,
    set_gaze_target,
    set_ik_target,
    set_joint_angle,
    set_joint_position,
    set_view_blend,
    set_view_id,
    set_viseme,
)
from creative_v3.characters.brand_mascot_v1.turnaround_builder import (
    EMOTIONS_12,
    VIEW_IDS,
    VISEMES_9,
)

GALLERY_DIR = Path(__file__).resolve().parent / "character_readiness_gallery"


def _clip_01_turnaround_360(n_frames: int = 42) -> List[RigState]:
    order = ["front", "front_34_right", "profile_right", "back_34", "back", "profile_left", "front_34_left", "front"]
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        u = (i / max(1, n_frames - 1)) * (len(order) - 1)
        idx = min(len(order) - 2, int(u))
        frac = u - idx
        vid = order[idx] if frac < 0.5 else order[idx + 1]
        set_view_id(st, vid)
        set_view_blend(st, frac)
        set_joint_angle(st, "tie_group", math.sin(u * math.pi) * 6.0)
        seq.append(st)
    return seq


def _clip_02_walk_cycle(n_frames: int = 30) -> List[RigState]:
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        phase = (i / n_frames) * 2.0 * math.pi
        s = math.sin(phase)
        c = math.cos(phase)
        set_view_id(st, "front_34_right")
        set_joint_position(st, "pelvis_group", 0.0, -abs(c) * 10.0)
        set_joint_angle(st, "leg_left_upper", s * 28.0)
        set_joint_angle(st, "leg_left_lower", max(0.0, -c * 32.0))
        set_joint_angle(st, "leg_right_upper", -s * 28.0)
        set_joint_angle(st, "leg_right_lower", max(0.0, c * 32.0))
        set_joint_angle(st, "arm_left_upper", -s * 26.0)
        set_joint_angle(st, "arm_right_upper", s * 26.0)
        set_joint_angle(st, "tie_group", -s * 10.0)
        seq.append(st)
    return seq


def _clip_03_jump_land(n_frames: int = 30) -> List[RigState]:
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        t = i / max(1, n_frames - 1)
        if t < 0.25:
            # Anticipation crouch
            u = t / 0.25
            set_joint_position(st, "pelvis_group", 0.0, 28.0 * u)
            set_joint_angle(st, "leg_left_upper", -28.0 * u)
            set_joint_angle(st, "leg_left_lower", 48.0 * u)
            set_joint_angle(st, "leg_right_upper", -28.0 * u)
            set_joint_angle(st, "leg_right_lower", 48.0 * u)
            set_joint_angle(st, "arm_left_upper", 35.0 * u)
            set_joint_angle(st, "arm_right_upper", -35.0 * u)
        elif t < 0.72:
            # Airborne arc
            u = (t - 0.25) / 0.47
            arc = math.sin(u * math.pi)
            set_joint_position(st, "character_root", 0.0, -110.0 * arc)
            set_joint_angle(st, "arm_left_upper", -85.0 * arc)
            set_joint_angle(st, "arm_right_upper", 85.0 * arc)
            set_joint_angle(st, "tie_group", 18.0 * math.cos(u * math.pi))
            set_expression(st, "happy")
        else:
            # Land & recover
            u = 1.0 - (t - 0.72) / 0.28
            set_joint_position(st, "pelvis_group", 0.0, 22.0 * u)
            set_joint_angle(st, "leg_left_upper", -20.0 * u)
            set_joint_angle(st, "leg_left_lower", 36.0 * u)
            set_joint_angle(st, "leg_right_upper", -20.0 * u)
            set_joint_angle(st, "leg_right_lower", 36.0 * u)
        seq.append(st)
    return seq


def _clip_04_reach_ik(n_frames: int = 30) -> List[RigState]:
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        u = i / max(1, n_frames - 1)
        tx = 430.0 + 40.0 * math.sin(u * math.pi)
        ty = 260.0 - 70.0 * math.sin(u * math.pi)
        set_ik_target(st, "right_arm", (tx, ty), weight=1.0)
        set_gaze_target(st, 0.7 * math.sin(u * math.pi), -0.4 * math.sin(u * math.pi))
        st.scene_svg_front = f'<circle cx="{tx + 140:.1f}" cy="{ty - 40:.1f}" r="14" fill="#00C4B4" stroke="#0B0C10" stroke-width="4"/>'
        seq.append(st)
    return seq


def _clip_05_finger_articulation(n_frames: int = 30) -> List[RigState]:
    fingers = ["thumb", "index", "middle", "ring", "pinky"]
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        u = i / max(1, n_frames - 1)
        set_joint_angle(st, "arm_right_upper", -25.0)
        set_joint_angle(st, "arm_right_forearm", -20.0)
        for idx, fname in enumerate(fingers):
            curl = 0.5 + 0.5 * math.sin(u * 2.0 * math.pi - idx * 0.6)
            set_finger_curl(st, "right", fname, curl, spread=0.4 * math.cos(u * math.pi))
        seq.append(st)
    return seq


def _clip_06_eye_gaze_blink(n_frames: int = 30) -> List[RigState]:
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        u = i / max(1, n_frames - 1)
        set_gaze_target(st, math.sin(u * 2.0 * math.pi), math.cos(u * 2.0 * math.pi) * 0.6)
        # Blink at frame 10..13, wink at frame 22..26
        if 10 <= i <= 13:
            st.eyelid_left = 0.0
            st.eyelid_right = 0.0
        elif 22 <= i <= 26:
            st.eyelid_left = 1.0
            st.eyelid_right = 0.0
        else:
            st.eyelid_left = 1.0
            st.eyelid_right = 1.0
        seq.append(st)
    return seq


def _clip_07_expression_12(n_frames: int = 36) -> List[RigState]:
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        e_idx = min(len(EMOTIONS_12) - 1, (i * len(EMOTIONS_12)) // n_frames)
        expr = EMOTIONS_12[e_idx]
        set_expression(st, expr)
        if expr in ("angry", "determined"):
            st.brow_left = {"ty": 5.0, "rot": 12.0}
            st.brow_right = {"ty": 5.0, "rot": -12.0}
        elif expr in ("surprise", "curious"):
            st.brow_left = {"ty": -8.0, "rot": -6.0}
            st.brow_right = {"ty": -10.0, "rot": 6.0}
        seq.append(st)
    return seq


def _clip_08_lip_sync_visemes(n_frames: int = 27) -> List[RigState]:
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        v_idx = min(len(VISEMES_9) - 1, (i * len(VISEMES_9)) // n_frames)
        set_viseme(st, VISEMES_9[v_idx])
        set_joint_angle(st, "head_group", math.sin(i * 0.5) * 4.0)
        seq.append(st)
    return seq


def _clip_09_head_neck_tie_follow(n_frames: int = 30) -> List[RigState]:
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        u = (i / max(1, n_frames - 1)) * 2.0 * math.pi
        set_joint_angle(st, "torso_group", math.sin(u) * 18.0)
        set_joint_angle(st, "neck_group", math.sin(u - 0.3) * 10.0)
        set_joint_angle(st, "head_group", math.sin(u - 0.5) * 20.0)
        set_joint_angle(st, "tie_group", -math.sin(u - 0.8) * 32.0)
        seq.append(st)
    return seq


def _clip_10_prop_grip_remote(n_frames: int = 30) -> List[RigState]:
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        u = math.sin((i / max(1, n_frames - 1)) * math.pi)
        st.right_hand = "remote"
        set_joint_angle(st, "arm_right_upper", -40.0 * u)
        set_joint_angle(st, "arm_right_forearm", -25.0 * u)
        set_expression(st, "curious" if i < 15 else "happy")
        if 14 <= i <= 20:
            st.scene_svg_front = '<circle cx="620" cy="240" r="24" fill="none" stroke="#FFD400" stroke-width="5" stroke-dasharray="6 4"/>'
        seq.append(st)
    return seq


def _clip_11_squash_stretch_recoil(n_frames: int = 30) -> List[RigState]:
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        u = (i / max(1, n_frames - 1)) * 2.0 * math.pi
        sq = 1.0 - 0.14 * math.sin(u)
        st_y = 1.0 + 0.14 * math.sin(u)
        st.pose["character_root"] = {"tx": 0.0, "ty": 0.0, "rot": 0.0, "sx": sq, "sy": st_y}
        set_expression(st, "surprise" if math.sin(u) > 0 else "smile")
        seq.append(st)
    return seq


def _clip_12_combined_acting(n_frames: int = 36) -> List[RigState]:
    seq: List[RigState] = []
    for i in range(n_frames):
        st = create_rig_state()
        u = i / max(1, n_frames - 1)
        set_view_id(st, "front_34_left" if u < 0.5 else "front")
        set_joint_angle(st, "torso_group", -8.0 * math.sin(u * math.pi))
        set_joint_angle(st, "head_group", 6.0 * math.sin(u * math.pi))
        set_gaze_target(st, 0.6 * math.sin(u * math.pi), -0.2)
        set_finger_curl(st, "right", "thumb", 0.5)
        set_finger_curl(st, "right", "index", 0.0)
        set_finger_curl(st, "right", "middle", 0.9)
        set_finger_curl(st, "right", "ring", 0.9)
        set_finger_curl(st, "right", "pinky", 0.9)
        set_expression(st, "determined" if u < 0.5 else "smile")
        seq.append(st)
    return seq


CLIPS = [
    ("01_turnaround_360", _clip_01_turnaround_360),
    ("02_walk_cycle", _clip_02_walk_cycle),
    ("03_jump_land", _clip_03_jump_land),
    ("04_reach_ik", _clip_04_reach_ik),
    ("05_finger_articulation", _clip_05_finger_articulation),
    ("06_eye_gaze_blink", _clip_06_eye_gaze_blink),
    ("07_expression_12", _clip_07_expression_12),
    ("08_lip_sync_visemes", _clip_08_lip_sync_visemes),
    ("09_head_neck_tie_follow", _clip_09_head_neck_tie_follow),
    ("10_prop_grip_remote", _clip_10_prop_grip_remote),
    ("11_squash_stretch_recoil", _clip_11_squash_stretch_recoil),
    ("12_combined_acting", _clip_12_combined_acting),
]


def build_all_readiness_clips() -> dict:
    GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for clip_id, fn in CLIPS:
        seq = fn()
        meta = play_clip(clip_id, seq, GALLERY_DIR / clip_id, width=480, height=360, fps=30)
        meta["status"] = "PASS" if meta["frame_count"] == len(seq) else "FAIL"
        results.append(meta)
    summary = {
        "total_clips": len(results),
        "passed": sum(1 for r in results if r["status"] == "PASS"),
        "failed": sum(1 for r in results if r["status"] != "PASS"),
        "clips": results,
    }
    (GALLERY_DIR / "readiness_qa.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Readiness Gallery: {summary['passed']}/{summary['total_clips']} PASS")
    return summary


if __name__ == "__main__":
    build_all_readiness_clips()

"""
Comprehensive unit & rendering tests for Creative Stickman Studio V3.
Covers M2 (genuine layered SVG), M3 (IK/FK, easing, renderer, Studio API), and M4/M5 (100 actions).
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from lxml import etree

from creative_v3.engine.actions.catalog_100 import build_100_actions
from creative_v3.engine.actions.runner import CHAR_DIR, evaluate_frame_state
from creative_v3.engine.kinematics.ik_solver import (
    blend_ik_fk,
    compute_anchor_positions,
    compute_world_transforms,
    solve_two_bone_ik,
)
from creative_v3.engine.renderers.svg_renderer import apply_pose_to_svg, render_svg_bytes_to_png
from creative_v3.engine.rigging.rig_model import load_rig
from creative_v3.engine.timeline.easing import ease_value, interpolate_pose_keyframes
from creative_v3.studio.ui.server import app


def test_mascot_svg_is_genuine_layered_vector():
    svg_path = CHAR_DIR / "mascot_master.svg"
    assert svg_path.exists()
    raw = svg_path.read_text(encoding="utf-8")
    assert "<image" not in raw.lower()
    assert "data:image" not in raw.lower()
    assert "base64" not in raw.lower()

    root = etree.fromstring(raw.encode("utf-8"))
    assert root.get("viewBox") == "0 0 600 800"
    ids = {el.get("id") for el in root.iter() if el.get("id")}
    for req_id in (
        "character_root", "pelvis_group", "torso_group", "head_group", "tie_group",
        "arm_left_upper", "arm_left_forearm", "wrist_left",
        "arm_right_upper", "arm_right_forearm", "wrist_right",
        "leg_left_upper", "leg_left_lower", "foot_left",
        "leg_right_upper", "leg_right_lower", "foot_right",
        "mouth_group", "eyes_group", "hair_front", "hair_back",
    ):
        assert req_id in ids, f"Missing rig group: {req_id}"


def test_rig_ik_solver_and_world_anchors():
    rig = load_rig(CHAR_DIR / "rig.json")
    assert len(rig["bones"]) == 18
    assert len(rig["anchors"]) == 8
    assert len(rig["hand_poses"]) == 9
    assert len(rig["expressions"]) == 12
    assert len(rig["visemes"]) == 9
    assert len(rig["views"]) == 7

    ik = solve_two_bone_ik((0.0, 0.0), (90.0, 40.0), l1=70.0, l2=60.0)
    assert ik.reached is True
    assert abs(blend_ik_fk(10.0, 30.0, 0.5) - 20.0) < 1e-6

    world = compute_world_transforms(rig, {"torso_group": {"rot": 15.0}, "head_group": {"rot": -10.0}})
    anchors = compute_anchor_positions(rig, world)
    assert "right_palm" in anchors and "eyes" in anchors


def test_timeline_easing_and_interpolation():
    assert abs(ease_value(0.0, "ease_in_out")) < 1e-6
    assert abs(ease_value(1.0, "ease_in_out") - 1.0) < 1e-6
    assert ease_value(0.5, "back_out") > 0.5
    kfs = [
        {"t": 0.0, "bones": {"head_group": {"rot": 0.0}}},
        {"t": 1.0, "ease": "linear", "bones": {"head_group": {"rot": 20.0}}},
    ]
    mid = interpolate_pose_keyframes(kfs, 0.5)
    assert abs(mid["head_group"]["rot"] - 10.0) < 1e-3


def test_all_100_actions_distinct_and_valid():
    specs = build_100_actions()
    assert len(specs) == 100
    ids = [s.action_id for s in specs]
    assert len(set(ids)) == 100
    for s in specs:
        assert s.validate() == [], f"{s.action_id} failed validation"

    rig = load_rig(CHAR_DIR / "rig.json")
    # Verify distinct mid-frame poses/FX across representative categories
    s1 = evaluate_frame_state(specs[0], rig, 15)
    s2 = evaluate_frame_state(specs[6], rig, 15)
    assert s1["pose"] != s2["pose"]


def test_svg_pose_mutation_and_transparent_png_render(tmp_path):
    master = (CHAR_DIR / "mascot_master.svg").read_bytes()
    svg = apply_pose_to_svg(
        master,
        {"head_group": {"rot": 12.0}, "arm_right_upper": {"rot": -45.0}},
        expression="surprise",
        right_hand="remote",
    )
    out_png = tmp_path / "test_pose.png"
    render_svg_bytes_to_png(svg, out_png, 320, 240)
    assert out_png.exists() and out_png.stat().st_size > 5000


def test_studio_ui_fastapi_endpoints():
    client = TestClient(app)
    r_home = client.get("/")
    assert r_home.status_code == 200
    assert "Creative Stickman Studio V3" in r_home.text

    r_actions = client.get("/api/actions")
    assert r_actions.status_code == 200
    assert r_actions.json()["count"] == 100

    r_svg = client.post("/api/preview-svg", json={"expression": "wink", "right_hand": "snap"})
    assert r_svg.status_code == 200
    assert "<svg" in r_svg.text

    r_assets = client.get("/api/assets")
    assert r_assets.status_code == 200
    assert r_assets.json()["icon_count"] == 40
    assert r_assets.json()["prop_count"] == 20
    assert r_assets.json()["fx_primitive_count"] == 24

    r_ready = client.get("/api/readiness")
    assert r_ready.status_code == 200
    assert r_ready.json()["passed"] == 12


def test_v32_turnaround_7_views_and_headless_commands(tmp_path):
    from creative_v3.api.commands import (
        create_rig_state,
        export_svg,
        set_expression,
        set_finger_curl,
        set_gaze_target,
        set_joint_angle,
        set_view_blend,
        set_view_id,
        set_viseme,
    )

    turn_dir = CHAR_DIR / "turnaround_svg"
    expected_views = ["front", "front_34_left", "front_34_right", "profile_left", "profile_right", "back_34", "back"]
    for vid in expected_views:
        p = turn_dir / f"{vid}.svg"
        assert p.exists(), f"Missing turnaround view: {vid}"
        raw = p.read_text(encoding="utf-8")
        assert "<image" not in raw.lower()
        assert "base64" not in raw.lower()

    st = create_rig_state()
    set_view_id(st, "front_34_right")
    set_view_blend(st, 0.35)
    set_joint_angle(st, "head_group", 12.0)
    set_gaze_target(st, 0.6, -0.3)
    set_finger_curl(st, "right", "index", 0.1, spread=0.3)
    set_finger_curl(st, "right", "middle", 0.85)
    set_expression(st, "mischievous")
    set_viseme(st, "viseme_A")
    out_svg = export_svg(st, tmp_path / "exported_v32.svg")
    assert out_svg.exists() and "<svg" in out_svg.read_text(encoding="utf-8")

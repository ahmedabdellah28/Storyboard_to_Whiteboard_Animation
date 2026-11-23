from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_workflow_montage_isolated_on_ottoman_ankara_ar() -> None:
    proj_dir = REPO_ROOT / "projects" / "ottoman_ankara_ar"
    if not (proj_dir / "inputs" / "ankara_production_meta" / "WORKFLOW.json").is_file():
        pytest.skip("ottoman_ankara_ar WORKFLOW.json fixture not present")

    from core.aion.workflow_montage_director import (
        build_workflow_montage_episode,
        is_workflow_montage_project,
    )
    from core.aion.cinematic_director_v4 import apply_director_v4_layer

    assert is_workflow_montage_project(proj_dir) is True
    ep = build_workflow_montage_episode(proj_dir, write_section_graphs=False)
    dp = ep["direction_plan"]
    assert len(dp["sections"]) == 12
    assert dp["paths_relative_to"] == "ANKARA_PRODUCTION"

    s1 = dp["sections"][0]
    assert s1["section_id"] == "SECTION_01"
    # Strict Ankara Opening Rule: ONLY 2 backgrounds & 1 single cut across SECTION_01!
    bgs = s1["background_track"]
    assert len(bgs) == 2
    assert bgs[0]["background_id"] == "01_ankara_plain"
    assert bgs[1]["background_id"] == "02_edirne_council"
    assert bgs[1]["section_out_s"] == pytest.approx(s1["section_duration_s"], abs=0.05)

    # Element tracks: Bayezid leads ("أُسر بايزيد") then seal insert glides smoothly ("في أنقرة")
    elems = s1["element_tracks"]
    assert elems[0]["role"] == "grounded_character"
    assert elems[0]["anchor"] == "bottom_center_of_visible_bounds"
    assert elems[1]["role"] == "insert"
    assert elems[1]["in_s"] > elems[0]["in_s"]
    assert len(elems[1]["keyframes"]) >= 2

    # Edirne messenger has walking motion + dedicated camera focus push
    msg = next(e for e in elems if "04.png" in e["file"])
    assert msg["role"] == "grounded_character"
    assert "walk" in msg["action"]
    assert any(c["to_zoom"] > 1.1 for c in s1["camera_track"])

    # Director v4 never overwrites locked workflow_montage layout (no dark scrim, no forced icons/dividers, zero vfx)
    sg1 = ep["section_graphs"]["section_01"]
    assert sg1["video_format"] == "workflow_montage"
    assert sg1["cinema_stage"]["bg_scrim_opacity"] == 0.0
    v4_res = apply_director_v4_layer(sg1, proj_dir=proj_dir, section_id="section_01")
    out_sg = v4_res["scene_graph"]
    assert out_sg["video_format"] == "workflow_montage"
    assert out_sg["scenes"][0]["assets"][0]["entrance"] == "direct"
    assert not any(a.get("role") == "semantic_icon" for sc in out_sg["scenes"] for a in sc["assets"])
    assert not any("v4_divider" in str(pg.get("id", "")) for pg in out_sg.get("procedural_graphics", []))


def test_mehmed_educational_style_preserved_without_regression() -> None:
    proj_dir = REPO_ROOT / "projects" / "mind_glitches_ar"
    if not (proj_dir / "sections" / "section_01").is_dir():
        pytest.skip("mind_glitches_ar not present")

    from core.aion.workflow_montage_director import is_workflow_montage_project
    from core.aion.master_cinema_kit import detect_video_format

    assert is_workflow_montage_project(proj_dir) is False
    assert detect_video_format("ما هو سبب هذا الأمر؟") == "educational"


def test_cli_exposes_workflow_montage_format_flag() -> None:
    res = subprocess.run(
        [sys.executable, str(REPO_ROOT / "pipeline_cli.py"), "studio", "compile", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "workflow_montage" in res.stdout
    assert "educational" in res.stdout
    assert "narrative" in res.stdout

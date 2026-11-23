"""Tests for AION v2 + v3 + v4 Unified Resource & Motion Director."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.aion.cinematic_director_v4 import (
    apply_director_v4_layer,
    validate_cinematic_plan_v2,
    validate_motion_plan_v3,
)
from core.aion.resource_registry import ResourceRegistry


def test_resource_registry_fts5_bilingual_search_and_banned_effect_filter(tmp_path: Path):
    reg = ResourceRegistry(db_path=tmp_path / "catalog.sqlite")
    mehmed_dir = ROOT / "projects" / "mehmed_the_conqueror_ar"
    upserted = reg.ensure_core_indexed(proj_dir=mehmed_dir, section_id="section_01")
    assert upserted >= 25

    # Arabic query for lock icon
    lock_hits = reg.search_resources("قفل", kinds=["icon"], limit=5)
    assert any("lock" in h["id"] for h in lock_hits)

    # Arabic query for glow effect: must return GPU-safe glow, NEVER banned cclightrays!
    glow_hits = reg.search_resources("توهج", kinds=["effect"], only_supported=True, limit=10)
    assert any(h["id"] == "effect:ec.stylize.glow" for h in glow_hits)
    assert all("cclightrays" not in h["id"] for h in glow_hits)

    # Arabic query for ship/chain assets from mehmed_the_conqueror_ar
    ship_hits = reg.search_resources("منع السفن", kinds=["asset"], limit=8)
    assert len(ship_hits) >= 1

    # Stage-2 details lookup
    details = reg.get_resource_details(["effect:ec.stylize.glow"])
    assert len(details) == 1
    assert details[0]["parameters"]["intensity"]["max"] == 0.9


def test_v2_and_v3_validators_catch_gaps_and_unsupported_capabilities():
    manifest = {
        "schema_version": "aion.asset_manifest.v2",
        "assets": [
            {"asset_id": "e1", "capabilities": ["transform_2d", "opacity"]},
        ],
    }
    bad_v2 = {
        "schema_version": "aion.cinematic_plan.v2",
        "duration_sec": 6.0,
        "beats": [{"beat_id": "b1", "start_sec": 0.0, "end_sec": 6.0}],
        "shots": [
            {
                "shot_id": "s1",
                "beat_id": "b1",
                "start_sec": 0.5,  # uncovered start!
                "end_sec": 5.0,    # uncovered end!
                "focal_target": {"asset_id": "e1"},
                "asset_tracks": [
                    {"asset_id": "e1", "enter_sec": 0.5, "exit_sec": 5.0, "motion": "lip_sync"},  # unsupported!
                ],
            }
        ],
    }
    errs_v2 = validate_cinematic_plan_v2(manifest, bad_v2)
    assert any("uncovered video start" in e for e in errs_v2)
    assert any("uncovered video end" in e for e in errs_v2)
    assert any("unsupported motion lip_sync" in e for e in errs_v2)

    bad_v3 = {
        "schema_version": "aion.motion_plan.v3",
        "shots": [
            {
                "shot_id": "s1",
                "start_sec": 0.0,
                "end_sec": 3.0,
                "settle_hold_sec": 0.4,
                "transition": {"type": "cut", "start_sec": 3.0},
                "tracks": [
                    {
                        "track_id": "t_bad",
                        "property": "position",
                        "coordinate_space": "unitless",  # wrong space!
                        "keyframes": [
                            {"t_sec": 2.0, "value": {"x": 0.5, "y": 0.5}},
                            {"t_sec": 1.0, "value": {"x": 0.6, "y": 0.5}},  # non-increasing!
                        ],
                    }
                ],
            }
        ],
    }
    errs_v3 = validate_motion_plan_v3(bad_v3)
    assert any("wrong coordinate space" in e for e in errs_v3)
    assert any("keyframes not strictly increasing" in e for e in errs_v3)


def test_apply_director_v4_layer_on_real_mehmed_section(tmp_path: Path):
    mehmed_dir = ROOT / "projects" / "mehmed_the_conqueror_ar"
    v7_sg = mehmed_dir / "exports" / "runs" / "v7_master_edu" / "sections" / "section_01" / "scene_graph.v2.json"
    sg_in = json.loads(v7_sg.read_text(encoding="utf-8"))

    reg = ResourceRegistry(db_path=tmp_path / "catalog.sqlite")
    out_dir = tmp_path / "out_v4"
    res = apply_director_v4_layer(
        sg_in,
        proj_dir=mehmed_dir,
        section_id="section_01",
        out_dir=out_dir,
        registry=reg,
    )
    assert res["v2_errors"] == []
    assert res["v3_errors"] == []
    assert (out_dir / "asset_manifest.v2.json").is_file()
    assert (out_dir / "cinematic_plan.v2.json").is_file()
    assert (out_dir / "motion_plan.v3.json").is_file()
    assert len(res["motion_plan"]["shots"]) >= 5
    assert any(sc.get("focal_target") and sc.get("eye_trace") for sc in res["scene_graph"]["scenes"])
    assert len(res["scene_graph"]["relationships"]) >= 1
    assert len(res["scene_graph"]["motion_paths"]) >= 1
    assert res["scene_graph"]["contrast_metrics"]["verified_with_pillow"] is True


def test_apply_director_v4_layer_on_shaytan_section_zero_placeholders_and_no_duplicate_sfx(tmp_path: Path):
    shaytan_dir = ROOT / "projects" / "shaytan_tricks_ar"
    v7_sg = shaytan_dir / "exports" / "runs" / "v7_master_edu" / "sections" / "section_01" / "scene_graph.v2.json"
    sg_in = json.loads(v7_sg.read_text(encoding="utf-8"))

    reg = ResourceRegistry(db_path=tmp_path / "catalog.sqlite")
    out_dir = tmp_path / "shaytan_v4"
    res = apply_director_v4_layer(
        sg_in,
        proj_dir=shaytan_dir,
        section_id="section_01",
        out_dir=out_dir,
        registry=reg,
    )
    assert res["v2_errors"] == []
    assert res["v3_errors"] == []
    assert len(res["asset_manifest"]["assets"]) == 20
    sg_out = res["scene_graph"]
    assert "sfx_cues" not in sg_out
    assert all(not ph.get("text", "").startswith("[") for ph in (sg_out.get("hud_sequence") or {}).get("phrases", []))
    assert all(not tb.get("text", "").startswith("[") for tb in sg_out.get("typography", []))
    assert len(sg_out["relationships"]) >= 4
    assert len(sg_out["motion_paths"]) >= 6


def test_cli_defaults_director_v4_on_and_720p_and_full_sfx_inventory(tmp_path: Path):
    import pipeline_cli

    parser = pipeline_cli.build_parser()
    args_cmp = parser.parse_args(["studio", "compile", "--project", "demo", "--section", "01"])
    assert args_cmp.director_v4 is True
    assert args_cmp.resolution == "720p"
    assert args_cmp.video_format == "educational"

    args_off = parser.parse_args(["studio", "compile", "--project", "demo", "--section", "01", "--no-director-v4"])
    assert args_off.director_v4 is False

    reg = ResourceRegistry(db_path=tmp_path / "full_catalog.sqlite")
    reg.ensure_core_indexed()
    sfx_hits = reg.search_resources("whoosh", kinds=["sfx"], limit=5)
    assert len(sfx_hits) >= 1
    conn_hits = reg.search_resources("radar rings", kinds=["effect"], limit=5)
    assert any("repeater_rings" in h["id"] for h in conn_hits)


"""Comprehensive V5 Creative Studio Test Suite (Grammar, Vectors, V2 Schema, ECGC, QA, CLI & Golden Guard)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from core.aion.capability_prober import CAPABILITY_IDS, load_capabilities_registry
from core.aion.cinematic_composition import CinematicCompositionEngine, apparent_scale_for_depth
from core.aion.contracts import (
    REQUIRED_V2_SECTIONS,
    SCENE_GRAPH_V1,
    SCENE_GRAPH_V2,
    audit_scene_graph,
    get_scene_graph_version,
    migrate_scene_graph_v1_to_v2,
    validate_scene_graph_v2,
)
from core.aion.creative_director import AICreativeDirector
from core.aion.ecgc_compiler import CreativeGraphicsCompiler
from core.aion.motion_grammar import MotionDesignGrammarEngine, NARRATIVE_INTENTS
from core.aion.procedural_graphics import ProceduralGraphicsEngine, is_rtl_text
from core.aion.studio_cli import cmd_studio_compile
from core.aion.visual_qa import evaluate_creative_render


def test_capability_registry_complete_and_no_unknowns():
    reg = load_capabilities_registry()
    caps = reg.get("capabilities", {})
    assert len(caps) == len(CAPABILITY_IDS) == 20
    allowed = {"VERIFIED", "PARTIAL", "UNAVAILABLE", "BROKEN", "UNKNOWN"}
    for cid in CAPABILITY_IDS:
        assert cid in caps
        status = caps[cid]["status"]
        assert status in allowed
        assert status != "UNKNOWN", f"Capability {cid} was not empirically probed"
        assert caps[cid].get("fallback")


def test_motion_grammar_covers_all_15_intents_and_diversity():
    engine = MotionDesignGrammarEngine()
    assert len(engine.list_intents()) == 15
    assert set(engine.list_intents()) == set(NARRATIVE_INTENTS)

    c1 = engine.classify_intent("لماذا يقع دماغك في وهم بصري بسبب هذا المؤثر")
    assert c1.intent in NARRATIVE_INTENTS

    c2 = engine.classify_intent("أول خطوة ثم المرحلة الثانية في سير العملية")
    assert c2.intent == "process_flow"

    c3 = engine.classify_intent("دراسة أظهرت أن نسبة 85% من المشاهدين")
    assert c3.intent == "data_or_statistic"

    beats = [
        {"id": "b1", "start": 0.0, "end": 3.0, "text": "تخيل اليوم معنا فكرة عجيبة"},
        {"id": "b2", "start": 3.0, "end": 6.0, "text": "الفكرة تعني أن عقلك يبني الصورة"},
        {"id": "b3", "start": 6.0, "end": 9.0, "text": "وبسبب ذلك ترى وجها في الغيوم"},
    ]
    plan = engine.plan_section_grammar(beats)
    assert len(plan) == 3
    for p in plan:
        assert p["treatment"]["intent"] in NARRATIVE_INTENTS
        assert p["treatment"]["palette"]


def test_procedural_graphics_engine_vectors_and_rtl():
    proc = ProceduralGraphicsEngine(1920, 1080)
    assert len(proc.available_icons()) >= 40
    svg_brain = proc.get_svg_icon_markup("brain")
    assert svg_brain and "<svg" in svg_brain and "</svg>" in svg_brain

    arrow = proc.build_bezier_connector("a1", (200, 300), (900, 500), with_arrow=True)
    assert arrow["kind"] == "bezier_arrow"
    assert len(arrow["vertices"]) == 3
    assert len(arrow["arrow_head_vertices"]) == 3

    nodes = [
        {"position": [500, 400], "icon": "eyes", "label": "استقبال"},
        {"position": [900, 400], "icon": "neuron_network", "label": "معالجة"},
    ]
    net = proc.build_network_diagram(nodes, [(0, 1)], palette={"surface": "#162033", "primary": "#00D4C0", "accent": "#FFD400", "text": "#FFFFFF"}, t_start=0.0, t_end=4.0)
    assert len(net) == 3

    tl = proc.build_timeline_diagram([{"label": "بداية"}, {"label": "تحول"}], palette={"surface": "#162033", "primary": "#38BDF8", "accent": "#FFD400", "text": "#FFFFFF"}, t_start=0.0, t_end=4.0)
    assert any(x["kind"] == "bezier_arrow" for x in tl)

    bars = proc.build_bar_chart([{"label": "أ", "value": 40}, {"label": "ب", "value": 85}], palette={"primary": "#38BDF8", "accent": "#FFD400", "text": "#FFFFFF"}, t_start=0.0, t_end=4.0)
    assert len([x for x in bars if x["kind"] == "chart_bar"]) == 2

    assert is_rtl_text("محرك الإخراج الذكي") is True
    assert is_rtl_text("Signal Flow") is False
    typo = proc.build_kinetic_typography_block("t1", "العقل البشري", position=(960, 900), palette={"surface": "#162033", "accent": "#FFD400", "text": "#FFFFFF"}, t_start=0.0, t_end=3.0)
    assert typo["direction"] == "rtl"
    assert typo["animator_based_on"] == 2


def test_scene_graph_v1_migration_and_v2_validation():
    v1_sg = {
        "project_id": "test_sec",
        "fps": 24,
        "source_timeline": {"audio_file": "voice.wav", "duration_sec": 6.0},
        "background_timeline": [{"time": 0.0, "c1": "#F2EDE4"}],
        "scenes": [
            {
                "scene_id": "sc1",
                "time": {"start": 0.0, "end": 6.0},
                "assets": [
                    {"id": "e1", "path": "e1.png", "in": 0.2, "out": 5.5, "card_style": "warm", "effects": [{"type": "Glow", "intensity": 1.4}]}
                ],
            }
        ],
    }
    assert get_scene_graph_version(v1_sg) == SCENE_GRAPH_V1
    v2_sg = migrate_scene_graph_v1_to_v2(v1_sg)
    assert get_scene_graph_version(v2_sg) == SCENE_GRAPH_V2
    for req in REQUIRED_V2_SECTIONS:
        assert req in v2_sg
    # Preserves V1 structure & fixes harsh glow on bright canvas cleanly
    ok, issues = audit_scene_graph(v2_sg, auto_fix=True)
    assert ok
    assert any("Glow" in i and "Light Sweep" in i for i in issues)

    # Disallows unrequested host character by policy auto-fix
    v2_sg["quality_constraints"]["use_character"] = True
    ok2, issues2 = validate_scene_graph_v2(v2_sg, auto_fix=True)
    assert ok2
    assert v2_sg["quality_constraints"]["use_character"] is False
    assert any("presenter character" in i for i in issues2)


def test_cinematic_composition_and_qa_refinement_loop():
    comp = CinematicCompositionEngine(1920, 1080, safe_margin_px=96)
    clamped = comp.clamp_to_safe_zone((-50, 2000), elem_w=200, elem_h=120)
    assert clamped[0] >= 96 and clamped[1] <= 1080 - 96
    assert apparent_scale_for_depth(0.0, -1600.0, 1600.0) == 100.0
    assert apparent_scale_for_depth(320.0, -1600.0, 1600.0) > 100.0

    director = AICreativeDirector()
    sg = director.direct_scene({"section_id": "loop_test", "duration_sec": 3.0, "style_mode": "scientific_explanation", "headline": "اختبار"})
    refined, actions = director.refine_scene_graph_from_qa(
        sg,
        {"findings": [{"code": "STATIC_FROZEN_ANIMATION"}, {"code": "EDGE_CLIPPING_RISK"}, {"code": "WHITE_BLOWOUT"}]},
    )
    assert len(actions) == 3
    assert refined["camera"]["keyframes"][-1]["pos"][2] > sg["camera"]["keyframes"][-1]["pos"][2]


def test_golden_reference_protection_guard():
    # Attempting to compile into golden reference mind_glitches_ar MUST fail loudly
    with pytest.raises(PermissionError):
        cmd_studio_compile(project="mind_glitches_ar", section="01", style_mode="scientific_explanation")


def test_studio_cli_doctor_capabilities_and_preview(tmp_path):
    doc = subprocess.run(
        [sys.executable, str(ROOT_DIR / "pipeline_cli.py"), "studio", "doctor", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert doc.returncode == 0
    payload = json.loads(doc.stdout)
    assert payload["ok"] is True
    assert payload["golden_reference_integrity"] == "GOLDEN INTACT"
    assert payload["capabilities_registered"] == 20

    gt = subprocess.run(
        [sys.executable, str(ROOT_DIR / "pipeline_cli.py"), "studio", "graphics-test", "--mode", "scientific_explanation", "--out-dir", str(tmp_path), "--render-preview"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert gt.returncode == 0
    gt_data = json.loads(gt.stdout)
    assert gt_data["ok"] is True
    ecproj = Path(gt_data["results"]["scientific_explanation"]["ecproj"])
    assert ecproj.is_file()

    qa = evaluate_creative_render(
        qa_dir=tmp_path / "qa_out",
        ecproj_path=ecproj,
        preview_frames=sorted((tmp_path / "scientific_explanation" / "work" / "preview_frames").glob("*.png")),
    )
    assert qa["verdict"] in ("PASS", "NEEDS_REVIEW")
    assert Path(qa["contact_sheet"]).is_file()


def test_multi_beat_full_section_orchestrates_all_20_assets():
    director = AICreativeDirector()
    beats = [
        {"id": f"beat_{i + 1:02d}", "start": i * 6.0, "end": (i + 1) * 6.0, "text": f"Sentence {i + 1} explains visual illusion effect"}
        for i in range(8)
    ]
    assets = [{"id": f"entity_{i + 1:02d}", "icon": "brain"} for i in range(20)]
    sg = director.direct_scene({
        "section_id": "section_01",
        "duration_sec": 48.0,
        "beats": beats,
        "assets": assets,
        "style_mode": "auto",
    })
    assert sg["schema_version"] == SCENE_GRAPH_V2
    # All 20 entities must be scheduled chronologically across the 8 beats
    assert len(sg["asset_references"]) == 20
    assert len(sg["typography"]) == 8
    assert len(sg["camera"]["keyframes"]) >= 8
    assert len(sg["procedural_graphics"]) >= 8
    assert len(sg.get("background_timeline", [])) >= 8
    ok, issues = validate_scene_graph_v2(sg, auto_fix=True)
    assert ok, issues

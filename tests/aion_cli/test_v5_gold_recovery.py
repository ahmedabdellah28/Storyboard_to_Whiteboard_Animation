"""Unit & regression tests for AION V5 Gold Regression Recovery & Creative Quality Gate."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.aion.contracts import (
    SCENE_GRAPH_V2,
    get_scene_graph_version,
    migrate_scene_graph_v1_to_v2,
    validate_scene_graph_v2,
)
from core.aion.creative_director import AICreativeDirector
from core.aion.creative_qa_gate import evaluate_creative_judgments, evaluate_hard_gates
from core.aion.ecgc_compiler import CreativeGraphicsCompiler, CompileContext
from core.aion.semantic_storyboard_director import (
    _TRAILING_STOPWORDS,
    normalize_arabic,
    plan_semantic_section_allocation,
    synthesize_editorial_headline,
)


def test_editorial_headline_avoids_dangling_stopwords_and_captures_anchors():
    h1 = synthesize_editorial_headline("أما الخَلَل الثالث فتقدر تجرّبه على نفسك في البيت خلال ثلاثين ثانية بس، واسمه وهم بِيْنُوكْيُو.")
    assert "وهم" in h1 or "بينوكيو" in h1 or "بِيْنُوكْيُو" in h1
    assert not h1.endswith("على")

    h2 = synthesize_editorial_headline("في سنة 1930، عالم النفس الألماني وولفغانغ ميتزغر خلّى ناس يطالعون في مساحة لون صافية.")
    assert "١٩٣٠" in h2 or "1930" in h2
    assert len(h2.split()) <= 7

    h3 = synthesize_editorial_headline("النتيجة؟ أغلبهم دخلوا في هلوسة سمعية وبصرية خلال دقايق.")
    assert "النتيجة؟" in h3
    last_tok = normalize_arabic(h3.split()[-1].rstrip("،,.!؟?:"))
    assert last_tok not in _TRAILING_STOPWORDS


def test_v1_to_v2_migration_preserves_scenes_fps_and_editorial_headlines():
    gold_sg_path = ROOT / "projects" / "mind_glitches_ar" / "director" / "section_01" / "scene_graph.json"
    gold_v1 = json.loads(gold_sg_path.read_text(encoding="utf-8"))
    v2 = migrate_scene_graph_v1_to_v2(gold_v1)

    assert get_scene_graph_version(v2) == SCENE_GRAPH_V2
    assert v2["composition"]["fps"] == 30
    assert len(v2["scenes"]) == len(gold_v1["scenes"])
    assert all(sc.get("assets") for sc in v2["scenes"])
    assert len(v2["asset_library"]) > 0
    assert v2["typography"][0]["position"] == [960, 130]
    assert v2["typography"][0]["role"] == "editorial_headline"
    assert v2["subtitles"] == []
    ok, issues = validate_scene_graph_v2(v2, auto_fix=False)
    assert ok, issues


def test_v5_director_produces_real_scenes_no_medallions_no_mechanical_drift():
    tm = json.loads(
        (ROOT / "projects" / "mind_glitches_ar" / "sections" / "section_03" / "timing" / "section_03_timing_master.json")
        .read_text(encoding="utf-8")
    )
    beats = [{"id": f"b{i+1}", "start": s["start"], "end": s["end"], "text": s["text"]} for i, s in enumerate(tm["sentences"])]
    assets = [
        {"id": f"entity_{i:02d}", "path": str(ROOT / "cache" / "mind_glitches_ar_v5" / "sections" / "section_03" / "assets" / f"entity_{i:02d}.png")}
        for i in range(1, 21)
    ]

    director = AICreativeDirector(fps=30)
    sg = director.direct_scene({
        "section_id": "section_03",
        "fps": 30,
        "duration_sec": tm["duration"],
        "beats": beats,
        "words": tm["words"],
        "assets": assets,
        "style_mode": "auto",
    })

    # Real editorial scenes (not single empty dummy scene)
    assert len(sg["scenes"]) >= 4
    assert all(sc.get("assets") for sc in sg["scenes"])
    assert sg["fps"] == 30 and sg["composition"]["fps"] == 30

    # Zero icon_medallion spam & zero mechanical +-14px motion paths
    assert not any(p.get("kind") == "icon_medallion" for p in sg["procedural_graphics"])
    assert len(sg["motion_paths"]) == 0

    # Top editorial headlines separated from subtitles
    assert sg["subtitles"] == []
    assert all(float(t["position"][1]) < 240.0 for t in sg["typography"])

    # Varied entrances & restrained SFX/VFX
    entrances = {a.get("entrance") for a in sg["asset_references"]}
    assert len(entrances) >= 2
    assert len(sg["sfx"]) <= 18
    assert len(sg["vfx"]) <= 12

    # Hard & creative gates pass cleanly
    hard = evaluate_hard_gates(scene_graph=sg)
    assert all(g["passed"] for g in hard), hard
    creative = evaluate_creative_judgments(scene_graph=sg)
    assert creative["overall_creative_score"] >= 75, creative


def test_ecgc_compiler_emits_varied_entrances_and_zero_ghost_word_slide(tmp_path):
    director = AICreativeDirector(fps=30)
    beats = [
        {"id": "b1", "start": 0.0, "end": 4.5, "text": "أول خلل اسمه تأثير غانزفيلد"},
        {"id": "b2", "start": 4.5, "end": 9.5, "text": "في سنة 1930 بدأ الباحث تجربة الغرفة الحمراء"},
    ]
    assets = [{"id": f"entity_{i:02d}", "icon": "brain"} for i in range(1, 5)]
    sg = director.direct_scene({
        "section_id": "section_01",
        "fps": 30,
        "duration_sec": 9.5,
        "beats": beats,
        "assets": assets,
        "style_mode": "auto",
    })
    compiler = CreativeGraphicsCompiler()
    ctx = CompileContext(
        scene_graph=sg,
        section_dir=tmp_path,
        work_dir=tmp_path,
        comp_name="test_comp",
        width=1920,
        height=1080,
        fps=30,
        duration=9.5,
    )
    compiler.cap_resolver.resolve(ctx)
    compiler.asset_resolver.resolve(ctx)
    compiler.vector_builder.build_stage_and_vectors(ctx)
    compiler.timeline_compiler.compile(ctx)
    compiler.typo_compiler.compile(ctx)
    compiler.vfx_compiler.compile(ctx)

    # Editorial headlines should use clean pill_pop fade instead of slow word-by-word RangeSelector lag
    text_anim_cmds = [c for c in ctx.commands if c["command"] == "layer.addTextAnimator"]
    assert len(text_anim_cmds) == 0


def test_creative_gate_detects_v5_current_defects():
    v5_cur_sg_p = ROOT / "cache" / "mind_glitches_ar_v5" / "exports" / "runs" / "v5_ar_grounded" / "sections" / "section_03" / "scene_graph.v2.json"
    if not v5_cur_sg_p.is_file():
        return
    v5_cur_sg = json.loads(v5_cur_sg_p.read_text(encoding="utf-8"))
    hard = evaluate_hard_gates(scene_graph=v5_cur_sg)
    failed_ids = {g["id"] for g in hard if not g["passed"]}
    assert "scenes_structure" in failed_ids
    assert "sfx_vfx_restraint" in failed_ids

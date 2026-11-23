"""Regression & Integration Tests for AION Studio V7 Master Cinema Format System.

Verifies that the living-gradient, animated Lucide SVG icon, element-to-element arrow,
persistent top neon-glass live-typing HUD, gain-staged CC0 SFX, and `drop_shadow`-aware
QA rules work cleanly for ANY script and ANY extracted visual assets.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.aion.contracts import validate_scene_graph_v2
from core.aion.creative_director import AICreativeDirector
from core.aion.creative_qa_gate import evaluate_hard_gates
from core.aion.ecgc_compiler import CreativeGraphicsCompiler
from core.aion.master_cinema_kit import (
    LIVING_GRADIENT_PALETTES,
    build_caustics_opacity_keyframes,
    build_held_bg_timeline,
    build_master_format_section,
    detect_video_format,
    load_lucide_svg,
    pick_animated_icon_for_beat,
    resolve_pro_sfx,
)
from core.aion.visual_qa import evaluate_creative_render


def _make_synthetic_cutout(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGBA", (320, 320), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle([32, 32, 288, 288], radius=48, fill=(*color, 255), outline=(248, 250, 252, 255), width=6)
    im.save(path)


def test_format_auto_router_bilingual_educational_and_narrative():
    edu_ar = "كيف يعمل الدماغ؟ أولاً السبب العلمي والطريقة والخطوة الأولى للمقارنة والنتيجة."
    nar_ar = "ذات يوم في ليلة هادئة وقف السلطان أمام أسوار المدينة وفجأة بدأت المعركة."
    edu_en = "How does compound interest work? First let us explain the formula and compare step by step."
    nar_en = "Once upon a dark night, the empire stood at the edge of fate and suddenly the siege began."

    assert detect_video_format(edu_ar, "auto") == "educational"
    assert detect_video_format(nar_ar, "auto") == "narrative"
    assert detect_video_format(edu_en, "auto") == "educational"
    assert detect_video_format(nar_en, "auto") == "narrative"
    assert detect_video_format(edu_ar, "narrative") == "narrative"
    assert detect_video_format(nar_ar, "educational") == "educational"


def test_held_bg_timeline_and_caustics_light_dimming():
    tl = build_held_bg_timeline([
        {"time": 0.0, "mood": "imperial_slate"},
        {"time": 10.0, "mood": "sandstone_dawn"},
        {"time": 20.0, "mood": "twilight_indigo"},
    ], morph_sec=0.42)
    # 3 moods -> 5 keyframes (0.0, 9.58 hold, 10.0 morph, 19.58 hold, 20.0 morph)
    assert len(tl) == 5
    assert tl[1]["time"] == 9.58 and tl[1]["c1"] == LIVING_GRADIENT_PALETTES["imperial_slate"]["c1"]
    assert tl[2]["time"] == 10.0 and tl[2]["is_light"] is True
    assert tl[3]["time"] == 19.58 and tl[3]["is_light"] is True

    caustics = build_caustics_opacity_keyframes(tl, 30.0, dark_op=16.0, light_op=5.0)
    ops_by_t = dict(caustics)
    assert ops_by_t[0.0] == 16.0
    assert ops_by_t[10.0] == 5.0
    assert ops_by_t[20.0] == 16.0


def test_semantic_animated_lucide_picker_and_pro_sfx_catalog():
    lock_info = pick_animated_icon_for_beat("هناك عائق وسلسلة مغلقة تمنع التقدم")
    assert lock_info["icon"] == "lock" and lock_info["preset"] == "lock_snap"

    bulb_info = pick_animated_icon_for_beat("فجأة ظهرت فكرة وخطة ذكية للحل", used_icons=["lock"])
    assert bulb_info["icon"] == "lightbulb" and bulb_info["preset"] == "bulb_eureka"

    light_bulb = pick_animated_icon_for_beat("smart idea", is_light_bg=True)
    assert light_bulb["ring_fill"] == "#FAF5EB" and light_bulb["ring_fill_opacity"] >= 80.0

    svg_markup = load_lucide_svg("compass", "#F59E0B", stroke_w=2.3)
    assert "<svg" in svg_markup and "#F59E0B" in svg_markup

    sfx = resolve_pro_sfx("eureka_sparkle", time_sec=5.2, pan=0.2)
    assert sfx is not None
    assert Path(sfx["cue"]).is_file()
    assert -4.0 <= sfx["gain_db"] <= -1.0


def test_master_format_director_works_for_any_topic_and_enforces_element_to_element_arrows(tmp_path: Path):
    # Brand-new non-Mehmed topic: Arabic Psychology / AI Educational Explainer with 8 synthetic cutouts
    assets = []
    colors = [(220, 80, 60), (45, 160, 210), (50, 180, 120), (235, 165, 45), (150, 95, 220), (210, 70, 110), (70, 140, 200), (90, 190, 150)]
    for i, col in enumerate(colors, 1):
        ap = tmp_path / "assets" / f"item_{i:02d}.png"
        _make_synthetic_cutout(ap, col)
        assets.append({"id": f"item_{i:02d}", "path": str(ap)})

    beats = [
        {"id": "b1", "start": 0.0, "end": 6.0, "text": "كيف يحمي العقل نفسه من التشتت؟"},
        {"id": "b2", "start": 6.0, "end": 12.0, "text": "أولاً هناك حاجز وقفل يمنع التركيز العميق"},
        {"id": "b3", "start": 12.0, "end": 18.0, "text": "ثانياً فكرة ذكية وخطة بسيطة لتنظيم التقنية"},
        {"id": "b4", "start": 18.0, "end": 24.0, "text": "النتيجة نمو واضح وهجوم قوي على الكسل"},
        {"id": "b5", "start": 24.0, "end": 30.0, "text": "وفي النهاية البوصلة تقودك للهدف الصحيح"},
    ]

    director = AICreativeDirector(width=1920, height=1080, fps=30)
    sg_edu = director.direct_scene({
        "section_id": "section_01",
        "duration_sec": 30.0,
        "beats": beats,
        "assets": assets,
        "video_format": "educational",
    })
    ok_v, errs_v = validate_scene_graph_v2(sg_edu, auto_fix=False)
    assert ok_v, f"Validation errors: {errs_v}"
    assert sg_edu["video_format"] == "educational"
    assert sg_edu["cinema_stage"]["living_gradient"] is True
    assert sg_edu["cinema_stage"]["hide_floor_line"] is True
    assert sg_edu["hud_sequence"]["phrases"]
    assert all(not p.get("hidden") for p in sg_edu["hud_sequence"]["phrases"])

    # Verify icons are animated & arrows stay at illustration level (y > 480, never pointing into upper icons at y ~ 320!)
    svg_icons = [a for sc in sg_edu["scenes"] for a in sc["assets"] if a.get("role") == "semantic_icon"]
    assert len(svg_icons) >= 3
    assert all(a.get("icon_anim") for a in svg_icons)
    arrows = [p for p in sg_edu["procedural_graphics"] if p.get("kind") in ("bezier_connector", "bezier_arrow")]
    assert len(arrows) >= 2
    for arr in arrows:
        for vx, vy in arr["vertices"]:
            screen_y = vy + (sg_edu["height"] * 0.5)
            assert screen_y >= 450.0, f"Arrow vertex screen_y={screen_y} drifted toward floating icon zone!"

    # Narrative format must selectively hide HUD on suspense/climax chapters
    sg_nar = director.direct_scene({
        "section_id": "section_01",
        "duration_sec": 30.0,
        "beats": beats,
        "assets": assets,
        "video_format": "narrative",
    })
    assert sg_nar["video_format"] == "narrative"
    assert any(p.get("hidden") for p in sg_nar["hud_sequence"]["phrases"])
    assert sg_nar["hud_sequence"].get("visibility_keyframes")

    # Verify QA hard-gate treats grounding drop_shadow cleanly (PASS, not penalized as heavy VFX clutter!)
    gates = evaluate_hard_gates(scene_graph=sg_edu)
    restraint = next(g for g in gates if g["id"] == "sfx_vfx_restraint")
    assert restraint["passed"] is True, restraint["detail"]


def test_ecgc_compiles_v7_master_cinema_to_live_ecproj_and_preview(tmp_path: Path):
    """End-to-end live EffectCraft compile & preview frame verification on synthetic non-Mehmed assets."""
    sec_dir = tmp_path / "section_01"
    assets = []
    for i, col in enumerate([(220, 90, 50), (40, 150, 210), (50, 185, 130), (235, 175, 50)], 1):
        ap = sec_dir / "assets" / f"card_{i:02d}.png"
        _make_synthetic_cutout(ap, col)
        assets.append({"id": f"card_{i:02d}", "path": str(ap)})

    sg = build_master_format_section(
        {
            "section_id": "section_01",
            "duration_sec": 12.0,
            "beats": [
                {"id": "b1", "start": 0.0, "end": 4.0, "text": "حماية الأسوار وبداية الفكرة"},
                {"id": "b2", "start": 4.0, "end": 8.0, "text": "عائق القفل والسلسلة"},
                {"id": "b3", "start": 8.0, "end": 12.0, "text": "خطة ذكية نحو الهدف"},
            ],
            "assets": assets,
        },
        video_format="educational",
    )

    compiler = CreativeGraphicsCompiler()
    out_ecproj = tmp_path / "out" / "test_v7.ecproj"
    rep = compiler.compile_scene(
        sg,
        section_dir=sec_dir,
        work_dir=tmp_path / "work",
        out_ecproj=out_ecproj,
        out_mp4=None,
        voice_wav=None,
        preview_only=True,
        use_gpu=False,
    )
    assert rep["ok"] is True, rep
    assert out_ecproj.is_file()
    ec_text = out_ecproj.read_text(encoding="utf-8", errors="replace")
    assert "BG_Stage" in ec_text
    assert "BG_Caustics" in ec_text
    assert "BG_AstroRing_Outer" in ec_text
    assert "Pool_Spot" in ec_text
    assert "Master_Grade" in ec_text
    assert "TextCard_HUD" in ec_text
    assert "Text_HUD" in ec_text
    assert "TextCursor_HUD" in ec_text
    assert "IconRing_" in ec_text
    assert "IconRipple_" in ec_text
    assert "Stage_Floor_Line" not in ec_text

    qa = evaluate_creative_render(
        qa_dir=tmp_path / "qa",
        ecproj_path=out_ecproj,
        mp4_path=None,
        preview_frames=[Path(p) for p in rep.get("preview_frames", [])],
        scene_graph=sg,
        compile_report=rep,
    )
    assert qa["verdict"] == "PASS", json.dumps(qa, ensure_ascii=False, indent=2)


def test_cli_exposes_format_flag_on_studio_compile_and_preview():
    from pipeline_cli import build_parser

    parser = build_parser()
    parsed_cmp = parser.parse_args(["studio", "compile", "--section", "01"])
    parsed_prv = parser.parse_args(["studio", "preview", "--section", "01"])
    assert parsed_cmp.video_format == "educational"
    assert parsed_prv.video_format == "educational"

    r = subprocess.run(
        [sys.executable, str(ROOT / "pipeline_cli.py"), "studio", "compile", "--help"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode == 0
    assert "--format" in r.stdout
    assert "educational" in r.stdout and "narrative" in r.stdout

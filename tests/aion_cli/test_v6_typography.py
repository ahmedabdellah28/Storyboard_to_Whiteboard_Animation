"""Unit & integration tests for AION Typography Integration V6.1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.aion.creative_director import AICreativeDirector
from core.aion.creative_qa_gate import evaluate_hard_gates
from core.aion.kinetic_typography import (
    build_pre_shaped_arabic_svg,
    compile_kinetic_text_block,
)
from core.aion.typography_director import (
    plan_headline_treatment,
    resolve_font_for_text,
    select_project_typography_system,
)
from core.aion.typography_registry import (
    COMMERCIAL_LICENSE_REQUIRED,
    load_font_registry,
    verify_font_files_sha256,
)
from core.config.settings import TYPOGRAPHY_REGISTRY_PATH, get_effectcraft_subprocess_env

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_font_registry_sha256_and_commercial_license_guard() -> None:
    """Verify open font SHA-256 checksums, OFL licenses, EFFECTCRAFT_FONT_DIRS & strict commercial locks."""
    sha = verify_font_files_sha256()
    assert sha["manifest_present"] is True
    assert sha["verified_count"] >= 50
    assert sha["mismatch_count"] == 0
    assert sha["missing_count"] == 0

    assert TYPOGRAPHY_REGISTRY_PATH.is_file()
    reg = load_font_registry()
    fmap = {f["family"]: f for f in reg["families"]}

    for comm_name in ("Fit Arabic", "Panton Arabic", "Khareef", "Sakkal Saad Poster", "Druk"):
        assert comm_name in COMMERCIAL_LICENSE_REQUIRED
        entry = fmap[comm_name]
        assert entry["status"] == "LICENSE_REQUIRED"
        assert entry["license"] == "LICENSE_REQUIRED"
        assert entry["verified_in_effectcraft"] is False
        assert entry["fallback"] and entry["fallback"] in fmap

    # Open fonts present & visible in EffectCraft
    for open_fam in ("Cairo", "Alexandria", "Alyamama", "Amiri", "IBM Plex Sans Arabic", "Readex Pro", "Funnel Display"):
        entry = fmap[open_fam]
        assert entry["status"] in ("PASS", "PARTIAL")
        assert entry["verified_in_effectcraft"] is True
        assert entry["license_file"] and (ROOT_DIR / entry["license_file"]).is_file()

    env = get_effectcraft_subprocess_env()
    assert "EFFECTCRAFT_FONT_DIRS" in env
    assert "typography" in env["EFFECTCRAFT_FONT_DIRS"]


def test_typography_director_cohesion_fallback_and_aspect_adaptation() -> None:
    """Ensure cohesive <=2 fonts per video, safe mixed-script & commercial fallbacks, and 9:16 sizing."""
    sys_psych = select_project_typography_system(
        story_genre="psychological_cinematic",
        aspect_ratio="16:9",
        language="ar",
        script_text="تجربة وهم بينوكيو وكيف يعيد مخك بناء الواقع",
    )
    assert sys_psych["primary"] == "Cairo"
    assert sys_psych["display"] == "Alyamama"
    assert sys_psych["max_families"] == 2

    sys_doc = select_project_typography_system(
        story_genre="historical_documentary",
        aspect_ratio="16:9",
        language="ar",
        script_text="في عام 1990 وثقت التجربة التاريخية ظاهرة التظليل اللفظي",
    )
    assert sys_doc["primary"] == "IBM Plex Sans Arabic"
    assert sys_doc["display"] == "Amiri"

    sys_mob = select_project_typography_system(
        story_genre="shorts_viral_9x16",
        aspect_ratio="9:16",
        language="ar",
        script_text="وهم بصري سريع",
    )
    assert sys_mob["primary"] == "Alexandria"
    assert sys_mob["display"] == "Changa"

    # Commercial & incomplete-glyph fallbacks must resolve safely
    fb_comm, _, reason_c = resolve_font_for_text("وهم بينوكيو", "Fit Arabic")
    assert fb_comm != "Fit Arabic" and reason_c is not None
    fb_mixed, _, reason_m = resolve_font_for_text("تجربة AION 1988", "Mabroum")
    assert fb_mixed != "Mabroum" and reason_m is not None

    # Responsive 9:16 vs 16:9 placement & headline legibility
    blk_mob = plan_headline_treatment(
        text="مخك يعيد تركيب الواقع",
        beat_index=1,
        scene_index=0,
        t_start=0.0,
        t_end=3.0,
        mood={"is_light_bg": False, "text_color": "#F8FAFC", "card_bg": "#0F1E30", "card_border": "#38BDF8"},
        mood_key="midnight_mystery",
        typing_system=sys_mob,
        comp_width=1080,
        comp_height=1920,
        headline_id="mob_01",
    )
    assert blk_mob["size"] >= 50
    assert "box" in blk_mob and blk_mob["box"][2] <= 900
    assert 180.0 <= blk_mob["position"][1] <= 1500.0


def test_kinetic_typography_modes_and_shaped_arabic_svg_fallback(tmp_path: Path) -> None:
    """Verify all 5 kinetic treatments preserve RTL cursive joining and SVG fallback keeps source_text."""
    modes = [
        {"id": "k1", "text": "وهم بينوكيو", "animation_mode": "impact_title", "font": "Alyamama"},
        {"id": "k2", "text": "كشف بصري متصل بدون تقطيع", "animation_mode": "mask_reveal", "font": "Cairo"},
        {"id": "k3", "text": "مخك يعيد تركيب الواقع", "highlight_word": "تركيب", "animation_mode": "word_emphasis", "font": "Alexandria"},
        {"id": "k4", "text": "التظليل اللفظي والذاكرة", "kicker": "١٩٩٠ — وثيقة علمية", "animation_mode": "documentary_card", "font": "IBM Plex Sans Arabic", "display_font": "Amiri"},
        {"id": "k5", "text": "دقة الإدراك البصري AION", "metric": "+42%", "animation_mode": "data_callout", "font": "Readex Pro"},
    ]
    ease: list = []
    all_cmds = []
    for m in modes:
        cmds = compile_kinetic_text_block(
            {**m, "direction": "rtl", "size": 52, "position": [960, 140], "start": 0.0, "end": 3.0},
            comp_width=1920,
            comp_height=1080,
            comp_duration=4.0,
            comp_name="KineticTest",
            work_dir=tmp_path,
            ease_keys=ease,
        )
        all_cmds.extend(cmds)

    cmd_names = [c["command"] for c in all_cmds]
    assert "layer.setTrackMatte" in cmd_names  # mask_reveal uses Track Matte, never letter split
    assert "layer.setText" in cmd_names  # word_emphasis targets whole-word range
    assert not any(
        c["command"] == "prop.set"
        and "basedOn" in c["params"].get("path", "")
        and c["params"].get("value") == 0
        for c in all_cmds
    )

    # Pre-shaped SVG fallback keeps full glyphs (including isolated Waw in 'وهم') & preserves source_text
    svg_res = build_pre_shaped_arabic_svg(
        "وهم بينوكيو — مسار متصل",
        out_svg_path=tmp_path / "shaped.svg",
    )
    assert svg_res["source_text"] == "وهم بينوكيو — مسار متصل"
    assert svg_res["svg"].count("<path ") >= 15
    assert 'data-source-text="وهم بينوكيو — مسار متصل"' in svg_res["svg"]


def test_studio_fonts_cli_and_creative_gate_blocks_commercial_font() -> None:
    """Confirm `studio fonts --verify-sha --json` succeeds and QA Gate rejects LICENSE_REQUIRED usage."""
    proc = subprocess.run(
        [sys.executable, "pipeline_cli.py", "studio", "fonts", "--verify-sha", "--json"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["sha256_integrity"]["mismatch_count"] == 0
    assert payload["summary"]["license_required"] == 5

    # Creative gate rejects commercial LICENSE_REQUIRED font & >3-font bloat
    director = AICreativeDirector()
    sg = director.direct_scene({
        "section_id": "test_sec",
        "duration_sec": 4.0,
        "text": "وهم بينوكيو والعقل البشري",
        "style_mode": "editorial_motion_graphics",
    })
    sg["typography"][0]["font"] = "Fit Arabic"
    gates = {g["id"]: g for g in evaluate_hard_gates(scene_graph=sg)}
    assert gates["typography_readability"]["passed"] is False
    assert "Fit Arabic" in gates["typography_readability"]["detail"]

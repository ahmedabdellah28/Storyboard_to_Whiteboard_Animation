"""End-to-end AION CLI Upgrade Verification Tests:
- Script parsing & template placeholder guard
- Real PhotoCraft storyboard extraction -> Semantic Map -> Creative Brief -> Scene Graph
- Isolated runs (`exports/runs/<run_id>/`) non-overwriting guarantee
- Interrupted run `--resume` recovery
- Transaction rollback on stage failure
- Real EffectCraft GPU Render + PostRenderQA + Master Merge
- CLI_REFERENCE.md synced to live argparse spec
- Doctor JSON health check
"""
from __future__ import annotations

import json
import math
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline_cli
from core.aion.contracts import audit_scene_graph
from core.aion.docgen import extract_parser_spec, render_cli_reference_md
from core.aion.run_manager import IsolatedRunManager
from core.aion.script_stage import is_placeholder_script, split_master_script_sections


def _write_test_wav(path: Path, dur_sec: float = 2.0, sr: int = 48000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(dur_sec * sr)
    samples = [int(6000 * math.sin(2.0 * math.pi * 440.0 * i / sr)) for i in range(n)]
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{n}h", *samples))


def _write_test_storyboard_2x2(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (800, 600), (255, 255, 255))
    d = ImageDraw.Draw(im)
    colors = [(220, 60, 60), (40, 120, 220), (40, 170, 90), (220, 150, 30)]
    boxes = [(60, 50, 340, 250), (460, 50, 740, 250), (60, 340, 340, 550), (460, 340, 740, 550)]
    for col, box in zip(colors, boxes):
        d.ellipse(box, fill=col, outline=(20, 20, 20), width=5)
    im.save(path)


def test_required_documentation_and_live_cli_ref_sync():
    for doc in [
        "CLI_CAPABILITY_AUDIT.md",
        "SKILL.md",
        "AGENTS.md",
        "CLI_REFERENCE.md",
        "PIPELINE_CONTRACTS.md",
        "TOOL_CAPABILITIES.md",
    ]:
        p = ROOT / doc
        assert p.is_file() and p.stat().st_size > 300, f"Missing/empty required doc: {doc}"

    live_md = render_cli_reference_md(extract_parser_spec(pipeline_cli.build_parser()))
    disk_md = (ROOT / "CLI_REFERENCE.md").read_text(encoding="utf-8")
    assert disk_md == live_md, "CLI_REFERENCE.md drifted from live pipeline_cli.py parser!"


def test_default_resolution_is_720p_with_1080p_opt_in():
    """All video output commands default to 720p unless `--resolution 1080p` is explicitly requested."""
    from core.aion.ecgc_compiler import resolve_effectcraft_resolution

    assert resolve_effectcraft_resolution("720p") == "0.6666667"
    assert resolve_effectcraft_resolution("1080p") == "full"
    assert resolve_effectcraft_resolution("full") == "full"

    parser = pipeline_cli.build_parser()
    for argv in [
        ["render", "--section", "01"],
        ["run", "--start", "1", "--end", "1"],
        ["studio", "compile", "--section", "01"],
        ["studio", "shorts", "--action", "compile", "--all"],
    ]:
        parsed = parser.parse_args(argv)
        assert parsed.resolution == "720p", f"Expected 720p default for {argv}, got {parsed.resolution}"

    parsed_1080 = parser.parse_args(["studio", "compile", "--section", "01", "--resolution", "1080p"])
    assert parsed_1080.resolution == "1080p"


def test_script_parser_and_placeholder_guard():
    assert is_placeholder_script("SECTION 01 - [عنوان المشهد 1]\n[اكتب هنا نص السكربت الصوتي للسكشن 1]")
    sections = split_master_script_sections(
        "[SECTION 01: Intro]\nHello world test script line.\n\n[SECTION 02: Next]\nSecond section script text."
    )
    assert len(sections) == 2
    assert sections[0][0] == 1 and "Hello world" in sections[0][2]
    assert sections[1][0] == 2 and "Second section" in sections[1][2]


def test_scene_graph_contrast_and_glow_autofix():
    sg = {
        "source_timeline": {"audio_file": "sections/section_01/voice/section_01.wav", "duration_sec": 10.0},
        "background_timeline": [{"time": 0.0, "c1": "#152130"}],
        "scenes": [{
            "scene_id": "sc1",
            "assets": [{
                "id": "entity_01", "in": 0.2, "out": 5.0, "pos": [960, 540],
                "card_style": "warm",
                "effects": [{"type": "Glow", "intensity": 1.2, "radius": 24}],
            }],
        }],
    }
    ok, issues = audit_scene_graph(sg, auto_fix=True)
    assert ok
    assert sg["scenes"][0]["assets"][0]["card_style"] == "arctic"
    assert sg["scenes"][0]["assets"][0]["effects"][0]["type"] == "Light Sweep"
    assert any("FIXED" in x for x in issues)


def test_rollback_restores_previous_state_on_failure(tmp_path):
    rm = IsolatedRunManager(tmp_path, "rollback_test")
    rid = "run_rb"
    rm.init_or_load_run(rid)
    target = rm.section_out_dir(rid, "section_01") / "good.txt"
    partial = rm.section_out_dir(rid, "section_01") / "partial.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("original_good_data", encoding="utf-8")

    with pytest.raises(RuntimeError):
        with rm.stage_transaction(rid, "section_01", "render", watch_paths=[target, partial], rollback_on_fail=True):
            target.write_text("corrupted_data", encoding="utf-8")
            partial.write_text("orphan_half_file", encoding="utf-8")
            raise RuntimeError("Simulated crash mid-render")

    assert target.read_text(encoding="utf-8") == "original_good_data"
    assert not partial.exists()
    assert rm.get_stage_status(rid, "section_01", "render") == "FAILED"


def test_doctor_command_reports_healthy_json():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "pipeline_cli.py"), "doctor", "--json"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    assert proc.returncode == 0
    rep = json.loads(proc.stdout)
    assert rep["is_healthy"] is True
    assert rep["craftapp"]["effectcraft_cli"]["exists"] is True


def test_end_to_end_aion_stages_resume_isolation_and_gpu_render():
    """Full end-to-end verification using real EffectCraft GPU render, QA, merge & run isolation."""
    proj_name = "aion_e2e_smoke"
    proj_dir = ROOT / "projects" / proj_name
    saved_active = (ROOT / ".active_project").read_text(encoding="utf-8") if (ROOT / ".active_project").exists() else None
    shutil.rmtree(proj_dir, ignore_errors=True)

    try:
        # 0. Init EN project cleanly
        pipeline_cli.cmd_init(proj_name, num_sections=1, description="E2E Test", lang="en", voice="Puck")

        # 1. Supply valid script, audio, pre-aligned timing JSON, and 2x2 storyboard
        ms = proj_dir / "inputs" / "script" / "master_script.txt"
        ms.write_text("[SECTION 01: Test]\nTesting isolated runs, EffectCraft GPU rendering, and automated QA gates.\n", encoding="utf-8")
        _write_test_wav(proj_dir / "sections" / "section_01" / "voice" / "section_01.wav", dur_sec=2.2)
        tm_path = proj_dir / "sections" / "section_01" / "timing" / "section_01_timing_master.json"
        tm_path.parent.mkdir(parents=True, exist_ok=True)
        tm_path.write_text(json.dumps({
            "section_id": "section_01", "language": "en", "duration": 2.2, "words_count": 4,
            "sentences": [{"text": "Testing isolated runs.", "start": 0.1, "end": 1.1}, {"text": "Automated QA gates.", "start": 1.15, "end": 2.1}],
            "words": [{"word": "Testing", "start": 0.1, "end": 0.5, "duration": 0.4}, {"word": "QA", "start": 1.5, "end": 2.0, "duration": 0.5}],
        }, indent=2), encoding="utf-8")
        (proj_dir / "sections" / "section_01" / "timing" / "section_01_word_by_word.srt").write_text("1\n00:00:00,100 --> 00:00:00,500\nTesting\n\n", encoding="utf-8")
        _write_test_storyboard_2x2(proj_dir / "inputs" / "storyboards" / "section_01.png")

        # 2. Extract explicitly via CLI mode=grid (2x2)
        assert pipeline_cli.cmd_extract("01", project=proj_name, mode="grid", rows=2, cols=2)
        assert (proj_dir / "sections" / "section_01" / "assets" / "entity_04.png").is_file()

        # 3. Run partial stages up to 'direct' in run_01 -> verify checkpoint -> resume to 'merge'!
        assert pipeline_cli.cmd_run_aion(
            project=proj_name, start_sec=1, end_sec=1,
            from_stage="script", to_stage="direct", run_id="run_01",
        )
        rm = IsolatedRunManager(proj_dir, proj_name)
        assert rm.resolve_resume_stage("run_01", "section_01") == "motion"

        # 4. Resume run_01 -> completes motion, sfx, EffectCraft GPU render, QA, merge!
        assert pipeline_cli.cmd_run_aion(
            project=proj_name, start_sec=1, end_sec=1, resume=True, run_id="run_01",
        )
        mp4_r1 = rm.section_out_dir("run_01", "section_01") / "section_01_aion_master.mp4"
        qa_r1 = rm.section_qa_dir("run_01", "section_01") / "qa_contact_sheet.png"
        merged_r1 = rm.run_dir("run_01") / f"{proj_name}_run_01_master_720p.mp4"
        assert mp4_r1.is_file() and mp4_r1.stat().st_size > 10000
        assert qa_r1.is_file()
        assert merged_r1.is_file()
        pr = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(merged_r1)],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert pr.returncode == 0
        dims = (json.loads(pr.stdout).get("streams") or [{}])[0]
        assert (int(dims.get("width", 0)), int(dims.get("height", 0))) == (1280, 720)
        mtime_r1 = mp4_r1.stat().st_mtime_ns

        # 5. Start a SECOND isolated run (`run_02`) from 'motion' -> must NEVER overwrite run_01!
        assert pipeline_cli.cmd_run_aion(
            project=proj_name, start_sec=1, end_sec=1,
            from_stage="motion", to_stage="qa", run_id="run_02", skip_merge=True,
        )
        mp4_r2 = rm.section_out_dir("run_02", "section_01") / "section_01_aion_master.mp4"
        assert mp4_r2.is_file()
        assert mp4_r1.stat().st_mtime_ns == mtime_r1, "run_02 mutated run_01 output!"
    finally:
        if saved_active is not None:
            (ROOT / ".active_project").write_text(saved_active, encoding="utf-8")
        shutil.rmtree(proj_dir, ignore_errors=True)

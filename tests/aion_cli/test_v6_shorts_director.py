"""Tests for AION Shorts Director & Reusable CTA Engine (Phase 7)."""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest

from core.aion.shorts_cta import (
    CANONICAL_CTA_TEXT_AR,
    CTA_TIMING_PATH,
    CTA_WAV_PATH,
    build_cta_visual_sequence,
)
from core.aion.shorts_director import (
    _build_mind_glitches_short_specs,
    _resolve_short_specs,
    evaluate_longform_candidates,
    inspect_project_creative_data,
)
from core.aion.studio_cli import cmd_studio_shorts

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_inspect_project_creative_data_zero_image_reads() -> None:
    """Confirm `inspect` extracts sentence timings & JSON asset catalogs without reading images or mutating Gold."""
    digest = inspect_project_creative_data(ROOT_DIR / "projects" / "mind_glitches_ar", write_digest=False)
    assert digest["zero_image_reads"] is True
    assert digest["sections_count"] == 8
    sec01 = digest["sections"][0]
    assert sec01["section_id"] == "section_01"
    assert sec01["sentences_count"] >= 5
    assert sec01["assets_count"] == 20
    assert sec01["visual_assets_json"][0]["id"] == "entity_01"

    specs = _resolve_short_specs(ROOT_DIR / "cache" / "mind_glitches_ar_v5")
    assert len(specs) == 5
    assert isinstance(specs[0]["font_override"], tuple)


def test_reusable_cta_audio_present_and_verified() -> None:
    """Confirm shared Channel CTA asset exists once on disk cleanly without duplicate synthesis."""
    assert CTA_WAV_PATH.is_file()
    assert CTA_TIMING_PATH.is_file()
    tm = json.loads(CTA_TIMING_PATH.read_text(encoding="utf-8"))
    assert tm["text"] == CANONICAL_CTA_TEXT_AR
    assert 2.0 <= float(tm["duration"]) <= 9.0
    assert len(tm.get("words", [])) >= 10
    with wave.open(str(CTA_WAV_PATH), "rb") as wf:
        assert wf.getframerate() == 48000
        assert wf.getnchannels() == 1


def test_shorts_candidates_evaluation_and_distinct_identities() -> None:
    """Verify qualitative evaluation selects 5 varied Shorts with distinct typography & palettes."""
    cands = evaluate_longform_candidates(ROOT_DIR / "cache" / "mind_glitches_ar_v5")
    assert cands["selected_count"] == 5
    rejected = [c for c in cands["candidates"] if not c["selected"]]
    assert len(rejected) == 3
    for r in rejected:
        assert len(r["reason"]) >= 20

    specs = _build_mind_glitches_short_specs(ROOT_DIR / "cache" / "mind_glitches_ar_v5")
    assert len(specs) == 5
    # Verify non-cloning: multiple distinct font systems, genres, and palettes
    genres = {s["story_genre"] for s in specs}
    fonts = {s["font_override"] for s in specs}
    bgs = {s["palette"]["bg"] for s in specs}
    assert len(genres) >= 4
    assert len(fonts) >= 4
    assert len(bgs) == 5


def test_cta_visual_sequence_safe_9x16_geometry() -> None:
    """Ensure CTA animated vector sequence fits 1080x1920 cleanly without fake URLs."""
    vis = build_cta_visual_sequence(
        cta_start=45.0,
        total_dur=49.5,
        font_primary="Cairo",
        font_display="Alyamama",
        palette={"surface": "#0F172A", "primary": "#38BDF8", "accent": "#FFD400", "text": "#F8FAFC"},
    )
    assert len(vis["assets"]) == 3
    assert len(vis["graphics"]) == 3
    assert len(vis["typography"]) == 1
    txt = vis["typography"][0]["text"]
    assert "http" not in txt.lower()
    assert 220 <= vis["typography"][0]["position"][1] <= 1520


def test_golden_protection_blocks_shorts_write_and_cli_help() -> None:
    """Golden reference `mind_glitches_ar` must refuse Shorts writes; CLI help exposes studio shorts."""
    with pytest.raises(PermissionError):
        cmd_studio_shorts(action="plan", project="mind_glitches_ar")

    proc = subprocess.run(
        [sys.executable, "pipeline_cli.py", "studio", "shorts", "--help"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert proc.returncode == 0
    assert "--action" in proc.stdout
    assert "--short" in proc.stdout

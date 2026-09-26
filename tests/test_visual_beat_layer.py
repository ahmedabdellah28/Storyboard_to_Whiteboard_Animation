"""
Comprehensive Test Suite for Visual Beat Layer (ASATE Level 2 & 3)
Covers all 10 required architectural test cases and ensures zero regressions.
"""
import pytest
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.join(ROOT_DIR, "kivy") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, "kivy"))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.beat.speech_beat import SpeechBeat
from engine.beat.visual_beat import (
    VisualBeat,
    ElementTier,
    OverlapPolicy,
    TransitionPolicy,
    EmphasisPoint,
    TimingDecision
)
from engine.beat.beat_solver import BeatTimingSolver
from engine.beat.beat_mapper import BeatMapper
from engine.beat.beat_debugger import BeatTimelineVisualizer
from engine.pipeline.dynamic_srt_choreographer import DynamicSRTChoreographer


# ---------------------------------------------------------------------------------------
# CASE 1: Subtitle قصير + عنصر بسيط
# ---------------------------------------------------------------------------------------
def test_case_1_short_subtitle_simple_element():
    sb = SpeechBeat(id="sb_01", start=1.0, end=2.2, text="نقطة بسيطة")
    simple_elem = {
        "id": "circle_01",
        "name": "Circle",
        "category": "ICON_GRAPHIC",
        "stroke_pts": [(0, 0), (10, 10), (20, 20)]
    }
    vb = VisualBeat(
        id="vb_01",
        speech_beat_id=sb.id,
        start=sb.start,
        end=sb.end,
        elements=[simple_elem],
        primary_elements=["Circle"],
        hold_duration=0.3
    )

    scheduled = BeatTimingSolver.solve_beat(vb)
    assert len(scheduled) == 1
    res = scheduled[0]
    assert res["sync_start"] >= 1.0
    assert res["sync_end"] <= 2.2
    assert res["sync_duration"] >= BeatTimingSolver.MIN_ELEMENT_DURATION
    assert res["hold_duration"] > 0
    assert res["tier"] == "PRIMARY"


# ---------------------------------------------------------------------------------------
# CASE 2: Subtitle طويل + عدة عناصر
# ---------------------------------------------------------------------------------------
def test_case_2_long_subtitle_multiple_elements():
    sb = SpeechBeat(
        id="sb_02", 
        start=5.0, 
        end=12.0, 
        text="هنا نرى الشاب يقف أمام الشاشة ويشرح التفاصيل المعقدة للجمهور الحاضر"
    )
    elements = [
        {"id": "char_1", "name": "Young Man", "category": "CHARACTER", "stroke_pts": [(i, i) for i in range(200)]},
        {"id": "card_1", "name": "Info Card", "category": "CONTAINER_CARD", "stroke_pts": [(i, 0) for i in range(100)]},
        {"id": "text_1", "name": "Title Line", "category": "TITLE", "stroke_pts": [(0, i) for i in range(80)]},
        {"id": "icon_1", "name": "Sparkle", "category": "ICON_GRAPHIC", "stroke_pts": [(i, 2*i) for i in range(40)]}
    ]
    vb = VisualBeat(
        id="vb_02",
        speech_beat_id=sb.id,
        start=sb.start,
        end=sb.end,
        elements=elements,
        primary_elements=["Young Man"],
        secondary_elements=["Info Card", "Title Line", "Sparkle"],
        overlap_policy=OverlapPolicy.NATURAL,
        hold_duration=0.8
    )

    scheduled = BeatTimingSolver.solve_beat(vb)
    assert len(scheduled) == 4
    for elem in scheduled:
        assert elem["sync_start"] >= 5.0
        assert elem["sync_end"] <= 12.0
    
    # Verify primary character has highest budget
    char_sched = next(e for e in scheduled if e["id"] == "char_1")
    icon_sched = next(e for e in scheduled if e["id"] == "icon_1")
    assert char_sched["sync_duration"] > icon_sched["sync_duration"]


# ---------------------------------------------------------------------------------------
# CASE 3: Primary Element مهم جداً مع Semantic Emphasis
# ---------------------------------------------------------------------------------------
def test_case_3_primary_element_with_semantic_emphasis():
    sb = SpeechBeat(id="sb_03", start=12.4, end=15.8, text="وهذول يمثلون حوالي 2% من البشر")
    elements = [
        {"id": "people_group", "name": "People Group", "category": "CHARACTER"},
        {"id": "percentage_2", "name": "2%", "category": "TITLE"}
    ]
    emphasis = [EmphasisPoint(text="2%", target_time=14.7, element_id="percentage_2", weight=2.0)]
    
    vb = VisualBeat(
        id="vb_03",
        speech_beat_id=sb.id,
        start=12.4,
        end=15.8,
        elements=elements,
        primary_elements=["percentage_2"],
        secondary_elements=["people_group"],
        emphasis_points=emphasis,
        anticipation_window=0.35,
        hold_duration=0.6
    )

    scheduled = BeatTimingSolver.solve_beat(vb)
    p2 = next(e for e in scheduled if e["id"] == "percentage_2")
    # Pinned around 14.7s with anticipation
    assert 14.0 <= p2["sync_start"] <= 14.8
    assert p2["sync_end"] >= 14.7
    dec = next(d for d in vb.timing_decisions if d.element_id == "percentage_2")
    assert "Semantic emphasis" in dec.reason


# ---------------------------------------------------------------------------------------
# CASE 4: عدة Secondary Elements مع Controlled Overlap
# ---------------------------------------------------------------------------------------
def test_case_4_multiple_secondary_controlled_overlap():
    elems = [
        {"id": "elem_a", "name": "Item A", "category": "ICON_GRAPHIC"},
        {"id": "elem_b", "name": "Item B", "category": "ICON_GRAPHIC"},
        {"id": "elem_c", "name": "Item C", "category": "ICON_GRAPHIC"}
    ]

    # Test NONE policy
    vb_none = VisualBeat(
        id="vb_none", start=0.0, end=6.0, elements=elems,
        secondary_elements=["Item A", "Item B", "Item C"],
        overlap_policy=OverlapPolicy.NONE
    )
    sched_none = BeatTimingSolver.solve_beat(vb_none)
    assert sched_none[1]["sync_start"] >= sched_none[0]["sync_end"] - 0.05

    # Test NATURAL policy
    vb_nat = VisualBeat(
        id="vb_nat", start=0.0, end=6.0, elements=elems,
        secondary_elements=["Item A", "Item B", "Item C"],
        overlap_policy=OverlapPolicy.NATURAL
    )
    sched_nat = BeatTimingSolver.solve_beat(vb_nat)
    # With natural overlap, next element starts before previous completely ends
    assert sched_nat[1]["sync_start"] < sched_nat[0]["sync_end"]


# ---------------------------------------------------------------------------------------
# CASE 5: عنصر معقد يحتاج وقتاً أطول من Speech Beat (Adaptive Compression)
# ---------------------------------------------------------------------------------------
def test_case_5_complex_element_exceeding_speech():
    complex_char = {
        "id": "complex_subject",
        "name": "Detailed Anatomy",
        "category": "CHARACTER",
        "stroke_pts": [(i, i) for i in range(1500)]
    }
    # Tight window of only 1.2 seconds
    vb = VisualBeat(
        id="vb_tight",
        start=0.0,
        end=1.2,
        elements=[complex_char],
        primary_elements=["Detailed Anatomy"],
        hold_duration=0.2
    )

    scheduled = BeatTimingSolver.solve_beat(vb)
    assert len(scheduled) == 1
    elem = scheduled[0]
    # Clamped safely to the beat window
    assert elem["sync_start"] >= 0.0
    assert elem["sync_end"] <= 1.2
    # Speed multiplier increased to safely draw within window
    assert elem["speed_multiplier"] > 1.0


# ---------------------------------------------------------------------------------------
# CASE 6: Speech Beat قصير جداً
# ---------------------------------------------------------------------------------------
def test_case_6_ultra_short_speech_beat():
    # Only 0.4s spoken dialogue
    sb = SpeechBeat(id="sb_fast", start=4.0, end=4.4, text="نعم!")
    elem = {"id": "checkmark", "name": "Checkmark", "category": "EMOJI"}
    vb = VisualBeat(id="vb_fast", start=sb.start, end=sb.end, elements=[elem])

    scheduled = BeatTimingSolver.solve_beat(vb)
    assert len(scheduled) == 1
    assert scheduled[0]["sync_duration"] >= BeatTimingSolver.MIN_ELEMENT_DURATION


# ---------------------------------------------------------------------------------------
# CASE 7: وجود Pause (استغلال فترات الصمت)
# ---------------------------------------------------------------------------------------
def test_case_7_audio_pause_utilization():
    elem = {"id": "character", "name": "Teacher", "category": "CHARACTER"}
    vb = VisualBeat(id="vb_pause", start=10.0, end=11.5, elements=[elem], primary_elements=["Teacher"])
    
    # 0.6s pause available right after this beat
    scheduled = BeatTimingSolver.solve_beat(vb, available_pause=0.6)
    assert len(scheduled) == 1
    # Absorbs pause safely for drawing/hold
    assert scheduled[0]["sync_end"] <= 12.1


# ---------------------------------------------------------------------------------------
# CASE 8: وجود Beatين متداخلين (TransitionPolicy.OVERLAP)
# ---------------------------------------------------------------------------------------
def test_case_8_overlapping_beats():
    b1 = VisualBeat(
        id="vb_1", start=0.0, end=4.0,
        elements=[{"id": "e1", "name": "Subject 1", "category": "CHARACTER"}],
        transition_policy=TransitionPolicy.OVERLAP
    )
    b2 = VisualBeat(
        id="vb_2", start=4.0, end=8.0,
        elements=[{"id": "e2", "name": "Subject 2", "category": "CHARACTER"}]
    )

    solved = BeatTimingSolver.solve_storyboard([b1, b2], total_audio_duration=8.0)
    assert len(solved) == 2
    # Beat 2 starts slightly before Beat 1 completes
    assert solved[1].start < solved[0].end


# ---------------------------------------------------------------------------------------
# CASE 9: عدم وجود Visual Beat (Legacy Mode Fallback)
# ---------------------------------------------------------------------------------------
def test_case_9_legacy_mode_fallback():
    dummy_panels = [
        {"global_id": 1, "objects": [{"name": "Obj1", "category": "CHARACTER"}]},
        {"global_id": 2, "objects": [{"name": "Obj2", "category": "TITLE"}]}
    ]
    dummy_srt = [
        {"index": 1, "start": 0.0, "end": 2.0, "text": "مرحباً"},
        {"index": 2, "start": 2.0, "end": 4.0, "text": "بالجميع"}
    ]

    # Explicitly run with use_visual_beats=False
    legacy_panels = DynamicSRTChoreographer.choreograph_timeline(
        panels=dummy_panels,
        srt_entries=dummy_srt,
        total_audio_sec=4.0,
        use_visual_beats=False
    )
    assert len(legacy_panels) == 2
    assert legacy_panels[0]["start_time"] == 0.0
    assert "visual_beat" not in legacy_panels[0]


# ---------------------------------------------------------------------------------------
# CASE 10: Audio أطول أو أقصر قليلاً من مجموع الـ Visual Beats
# ---------------------------------------------------------------------------------------
def test_case_10_audio_duration_mismatch_resilience():
    b1 = VisualBeat(id="b1", start=0.0, end=3.0, elements=[{"id": "1", "name": "A"}])
    b2 = VisualBeat(id="b2", start=3.0, end=5.5, elements=[{"id": "2", "name": "B"}])
    
    # Master audio is 6.2s (0.7s longer than sum of beats)
    solved = BeatTimingSolver.solve_storyboard([b1, b2], total_audio_duration=6.2)
    assert solved[-1].end == 6.2

    # Also test timeline visualizer output
    ascii_out = BeatTimelineVisualizer.render_ascii_timeline(solved, total_duration=6.2)
    assert "VISUAL BEAT ASATE TIMELINE DIAGNOSTIC" in ascii_out
    assert "PRIMARY" in ascii_out

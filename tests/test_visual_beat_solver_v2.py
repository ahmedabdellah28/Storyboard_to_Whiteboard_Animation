"""
Unit Tests for Content-Aware Visual Timing Engine (ASATE Solver V2)
Validates 15 core architectural scenarios:
- Calibrated Physical Modeling (No Duration Presets)
- Decoupled Drawing Demand != Drawing Duration
- Speed Feasibility & Safe Ceilings
- Semantic Anchors (EMPHASIS, LEAD_IN)
- Timing Conflict Model & Resolution Search
- Inter-Beat BeatTransition Generation
- Legacy Choreographer Compatibility
"""
import pytest
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.join(ROOT_DIR, "kivy") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, "kivy"))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.beat.visual_beat import (
    VisualBeat,
    ElementTier,
    OverlapPolicy,
    TransitionPolicy,
    SemanticAnchor,
    AnchorType,
    AnchorSourceType,
    SpeedFeasibility,
    ConflictType,
    ConflictSeverity,
    DrawingDemand,
    BeatTransition
)
from engine.beat.speech_beat import SpeechBeat
from engine.beat.beat_solver import BeatTimingSolver
from engine.pipeline.dynamic_srt_choreographer import DynamicSRTChoreographer


class TestVisualBeatSolverV2:

    def test_case_1_suspiciously_short_speech_segment(self):
        """Case 1: 0.3s Speech + long text -> Suspicious speech segment detection & handling."""
        sb = SpeechBeat(
            id="sb_01",
            start=1.0,
            end=1.3,
            text="هذه جملة طويلة جدا لا يمكن نطقها في ثلث ثانية"
        )
        is_suspicious, info = sb.is_suspiciously_short()
        assert is_suspicious is True
        assert info["word_count"] >= 4
        assert info["recommended_min_duration"] > 1.0

    def test_case_2_demand_proportionality(self):
        """Case 2: Demand Proportionality - higher physical demand receives larger drawing budget."""
        elem_small = {
            "id": "small_icon",
            "name": "icon",
            "category": "ICON_GRAPHIC",
            "stroke_pts": [(0, 0), (10, 10), (20, 0)] # very short arc length
        }
        elem_large = {
            "id": "large_figure",
            "name": "figure",
            "category": "CHARACTER",
            "stroke_pts": [(i * 2, (i % 5) * 10) for i in range(150)] # long arc length
        }
        
        demand_s = BeatTimingSolver.calculate_drawing_demand(elem_small)
        demand_l = BeatTimingSolver.calculate_drawing_demand(elem_large)

        assert demand_l.arc_length_px > demand_s.arc_length_px
        assert demand_l.estimated_physical_effort > demand_s.estimated_physical_effort

        vb = VisualBeat(
            id="vb_02",
            start=0.0,
            end=4.0,
            elements=[elem_small, elem_large]
        )
        solved = BeatTimingSolver.solve_beat(vb)
        
        dur_s = next(e["sync_duration"] for e in solved if e["id"] == "small_icon")
        dur_l = next(e["sync_duration"] for e in solved if e["id"] == "large_figure")
        
        # Proportionality assertion: larger physical demand must get more time
        assert dur_l > dur_s

    def test_case_3_simple_element_fast_draw_generous_hold(self):
        """Case 3: 3.0s Speech + 1 simple element -> Low demand draws rapidly; remaining time becomes Hold."""
        elem_simple = {
            "id": "arrow",
            "name": "arrow",
            "category": "DECORATIVE",
            "stroke_pts": [(0, 0), (50, 0), (45, -5), (50, 0), (45, 5)]
        }
        vb = VisualBeat(
            id="vb_03",
            start=0.0,
            end=3.0,
            elements=[elem_simple],
            hold_duration=1.2
        )
        solved = BeatTimingSolver.solve_beat(vb)
        assert len(solved) == 1
        d = vb.timing_decisions[0]
        
        # Simple element draws quickly (< 1.5s in a 3s window)
        assert d.duration < 1.5
        # Hold window expands to give visual persistence
        assert vb.hold_window[1] >= 3.0

    def test_case_4_complex_element_spans_window(self):
        """Case 4: 3.0s Speech + 1 complex element -> High demand draws across window naturally."""
        elem_complex = {
            "id": "char_hero",
            "name": "hero",
            "category": "CHARACTER",
            "stroke_pts": [(i, i % 20) for i in range(400)],
            "bbox": (10, 10, 300, 400)
        }
        vb = VisualBeat(
            id="vb_04",
            start=0.0,
            end=3.0,
            elements=[elem_complex],
            primary_elements=["char_hero"]
        )
        solved = BeatTimingSolver.solve_beat(vb)
        d = vb.timing_decisions[0]
        # Spans the majority of available drawing budget
        assert d.duration >= 1.8

    def test_case_5_multi_element_overlap(self):
        """Case 5: 6.0s Speech + 5 elements -> Natural multi-element overlap without crowding."""
        elems = [
            {"id": f"elem_{i}", "name": f"item_{i}", "category": "ICON_GRAPHIC", "bbox": (0, 0, 50, 50)}
            for i in range(5)
        ]
        vb = VisualBeat(
            id="vb_05",
            start=0.0,
            end=6.0,
            elements=elems,
            overlap_policy=OverlapPolicy.NATURAL
        )
        solved = BeatTimingSolver.solve_beat(vb)
        assert len(solved) == 5
        # Verify subsequent elements overlap naturally (start of i < end of i-1)
        overlaps_found = 0
        for i in range(1, len(solved)):
            if solved[i]["sync_start"] < solved[i - 1]["sync_end"]:
                overlaps_found += 1
        assert overlaps_found >= 3

    def test_case_6_decoupled_tiering(self):
        """
        Case 6: Decoupled Tiering (DrawingDemand != Duration).
        A simple PRIMARY element draws quickly and holds;
        a complex SECONDARY element gets the physical time it needs.
        Proves PRIMARY does NOT force longer drawing duration.
        """
        simple_primary = {
            "id": "stat_2_percent",
            "name": "2%",
            "category": "TITLE",
            "stroke_pts": [(0, 0), (20, 0), (20, 20), (0, 20)] # Simple linework
        }
        complex_secondary = {
            "id": "bg_diagram",
            "name": "diagram",
            "category": "CONTAINER_CARD",
            "stroke_pts": [(i * 2, (i * 3) % 40) for i in range(300)], # Complex linework
            "bbox": (0, 0, 400, 300)
        }

        vb = VisualBeat(
            id="vb_06",
            start=0.0,
            end=5.0,
            elements=[simple_primary, complex_secondary],
            primary_elements=["stat_2_percent"],
            secondary_elements=["bg_diagram"]
        )
        solved = BeatTimingSolver.solve_beat(vb)
        d_prim = next(d for d in vb.timing_decisions if d.element_id == "stat_2_percent")
        d_sec = next(d for d in vb.timing_decisions if d.element_id == "bg_diagram")

        # Crucial architectural assertion:
        # Simple Primary draws FASTER than Complex Secondary because of physical demand!
        assert d_prim.duration < d_sec.duration
        # But Primary gets greater hold duration for viewer retention
        assert d_prim.hold_duration >= d_sec.hold_duration

    def test_case_7_semantic_anchor_emphasis(self):
        """Case 7: Semantic Anchor EMPHASIS -> Drawing completes precisely at keyword instant."""
        anchor_elem = {
            "id": "danger_icon",
            "name": "danger",
            "category": "EMOJI",
            "bbox": (0, 0, 60, 60)
        }
        anchor = SemanticAnchor(
            source="speech",
            source_text="هناك خطورة كبيرة",
            source_token="خطورة",
            source_type=AnchorSourceType.CONCEPT,
            target_element="danger_icon",
            target_time=2.40,
            anchor_type=AnchorType.EMPHASIS,
            tolerance=0.18
        )
        vb = VisualBeat(
            id="vb_07",
            start=0.0,
            end=3.0,
            elements=[anchor_elem],
            semantic_anchors=[anchor]
        )
        solved = BeatTimingSolver.solve_beat(vb)
        d = vb.timing_decisions[0]
        # Reveal finishes right at anchor target_time within tolerance
        assert abs(d.end - 2.40) <= 0.18

    def test_case_8_semantic_anchor_lead_in(self):
        """Case 8: Semantic Anchor LEAD_IN -> Drawing anticipates speech start."""
        elem = {
            "id": "car_subject",
            "name": "car",
            "category": "CHARACTER",
            "bbox": (0, 0, 150, 100)
        }
        anchor = SemanticAnchor(
            source="speech",
            source_text="السيارة تقترب",
            source_token="السيارة",
            source_type=AnchorSourceType.OBJECT,
            target_element="car_subject",
            target_time=1.20,
            anchor_type=AnchorType.LEAD_IN
        )
        vb = VisualBeat(
            id="vb_08",
            start=1.0,
            end=3.0,
            elements=[elem],
            semantic_anchors=[anchor]
        )
        # Pre-speech time is available (from 0.5s to 1.0s)
        solved = BeatTimingSolver.solve_beat(vb, available_pre_speech=0.40)
        d = vb.timing_decisions[0]
        # Drawing starts before speech start (anticipation > 0)
        assert d.start < 1.0
        assert d.anticipation > 0.0

    def test_case_9_dependent_elements_high_overlap(self):
        """Case 9: Dependent elements receive dynamic high overlap."""
        e1 = {"id": "box", "name": "card", "category": "CONTAINER_CARD", "bbox": (0, 0, 200, 200)}
        e2 = {"id": "box_text", "name": "text_inside", "category": "TEXT_LINE", "bbox": (10, 10, 100, 30)}
        vb = VisualBeat(
            id="vb_09",
            start=0.0,
            end=4.0,
            elements=[e1, e2],
            primary_elements=["box"],
            secondary_elements=["box_text"]
        )
        solved = BeatTimingSolver.solve_beat(vb)
        d1 = vb.timing_decisions[0]
        d2 = vb.timing_decisions[1]
        overlap_amt = d1.end - d2.start
        assert overlap_amt > 0.15

    def test_case_10_independent_elements_low_overlap(self):
        """Case 10: Independent elements have low overlap / sequential handoff."""
        e1 = {"id": "chart_a", "name": "chart", "category": "CONTAINER_CARD", "bbox": (0, 0, 100, 100)}
        e2 = {"id": "chart_b", "name": "chart2", "category": "CONTAINER_CARD", "bbox": (150, 0, 100, 100)}
        vb = VisualBeat(
            id="vb_10",
            start=0.0,
            end=4.0,
            elements=[e1, e2],
            overlap_policy=OverlapPolicy.LIMITED
        )
        solved = BeatTimingSolver.solve_beat(vb)
        d1 = vb.timing_decisions[0]
        d2 = vb.timing_decisions[1]
        # Limited overlap between independent cards
        assert d2.start >= (d1.start + d1.duration * 0.70)

    def test_case_11_long_pause_absorption(self):
        """Case 11: Long trailing pause absorbed into hold and drawing budget."""
        elem = {"id": "item", "name": "subject", "category": "CHARACTER", "bbox": (0, 0, 100, 100)}
        vb = VisualBeat(id="vb_11", start=0.0, end=1.5, elements=[elem])
        # Available pause is 1.5s
        solved = BeatTimingSolver.solve_beat(vb, available_pause=1.5)
        d = vb.timing_decisions[0]
        # Speed remains completely safe and normal
        assert d.feasibility == SpeedFeasibility.NORMAL
        assert d.speed_multiplier <= 1.25

    def test_case_12_no_pause_tight_transition(self):
        """Case 12: Zero pause between beats produces clean BeatTransition."""
        b1 = VisualBeat(id="vb_12a", start=0.0, end=2.0, elements=[{"id": "e1", "name": "item1"}])
        b2 = VisualBeat(id="vb_12b", start=2.0, end=4.0, elements=[{"id": "e2", "name": "item2"}])
        solved_beats, transitions = BeatTimingSolver.solve_storyboard([b1, b2], total_audio_duration=4.0, return_transitions=True)
        assert len(transitions) == 1
        t = transitions[0]
        assert t.from_beat_id == "vb_12a"
        assert t.to_beat_id == "vb_12b"
        assert t.transition_type == TransitionPolicy.KEEP

    def test_case_13_beat_transition_overlap(self):
        """Case 13: Inter-beat BeatTransition with OVERLAP policy."""
        b1 = VisualBeat(id="vb_13a", start=0.0, end=2.5, elements=[{"id": "e1", "name": "item1"}], transition_policy=TransitionPolicy.OVERLAP)
        b2 = VisualBeat(id="vb_13b", start=2.5, end=5.0, elements=[{"id": "e2", "name": "item2"}])
        solved_beats, transitions = BeatTimingSolver.solve_storyboard([b1, b2], total_audio_duration=5.0, return_transitions=True)
        assert len(transitions) == 1
        assert transitions[0].transition_type == TransitionPolicy.OVERLAP

    def test_case_14_legacy_mode_compatibility(self):
        """Case 14: DynamicSRTChoreographer runs in legacy mode when use_visual_beats=False."""
        panels = [{
            "global_id": 1,
            "objects": [{"id": "obj1", "name": "circle", "category": "ICON_GRAPHIC"}]
        }]
        subtitles = [{"index": 1, "start": 0.0, "end": 2.0, "text": "مرحبا بك"}]
        res = DynamicSRTChoreographer.choreograph_timeline(
            panels=panels,
            srt_entries=subtitles,
            total_audio_sec=2.0,
            use_visual_beats=False
        )
        assert len(res) == 1
        assert "objects" in res[0]
        assert len(res[0]["objects"]) == 1
        assert res[0]["objects"][0]["sync_duration"] > 0

    def test_case_15_impossible_deadline_conflict_generation(self):
        """
        Case 15: Impossible Deadline (High Demand + Late Anchor + Ultra-short Speech).
        Ensures Speed Feasibility flags INFEASIBLE, Resolution Search attempts mitigation,
        and structured TimingConflict is generated rather than forcing an impossible timeline or crashing.
        """
        # Massive workload: 5000px arc length
        heavy_elem = {
            "id": "heavy_blueprint",
            "name": "blueprint",
            "category": "CHARACTER",
            "stroke_pts": [(i, (i * 7) % 50) for i in range(1200)], # huge linework
            "bbox": (0, 0, 500, 500)
        }
        # Impossible deadline: 0.4s speech window, no pre-speech, no pause
        impossible_anchor = SemanticAnchor(
            source="speech",
            source_text="انتبه",
            source_token="انتبه",
            source_type=AnchorSourceType.CONCEPT,
            target_element="heavy_blueprint",
            target_time=0.35,
            anchor_type=AnchorType.EMPHASIS,
            tolerance=0.05
        )
        vb = VisualBeat(
            id="vb_15",
            start=0.0,
            end=0.40,
            elements=[heavy_elem],
            semantic_anchors=[impossible_anchor],
            primary_elements=["heavy_blueprint"]
        )
        solved = BeatTimingSolver.solve_beat(vb, available_pause=0.0, available_pre_speech=0.0)
        
        # 1. No crash!
        assert len(solved) == 1
        # 2. Timing Conflict must be explicitly registered!
        assert len(vb.timing_conflicts) > 0
        c = vb.timing_conflicts[0]
        assert c.conflict_type in (ConflictType.SPEED_CONFLICT, ConflictType.ANCHOR_CONFLICT)
        assert c.severity in (ConflictSeverity.HIGH, ConflictSeverity.CRITICAL)
        assert "heavy_blueprint" in c.affected_elements
        # 3. Solver capped speed at safe ceiling instead of exploding to 20x
        d = vb.timing_decisions[0]
        assert d.speed_multiplier <= BeatTimingSolver.MAX_SPEED_MULTIPLIER

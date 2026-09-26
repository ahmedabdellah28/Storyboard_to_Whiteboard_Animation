"""Tests for Temporal Validation and Inking Completion Synchronization."""

import pytest
from pre_render_director.models.event import TimingStrategy
from pre_render_director.director.temporal_validator import TemporalValidator

def test_complete_on_anchor_strategy():
    validator = TemporalValidator(audio_duration=60.0)
    
    # Anchor spoken between 3.5s and 5.0s, drawing demand = 2.0s
    start_s, end_s, dur_s = validator.compute_optimal_timing(
        anchor_start=3.5,
        anchor_end=5.0,
        drawing_demand=2.0,
        strategy=TimingStrategy.COMPLETE_ON_ANCHOR,
        prev_event_end=1.0
    )
    
    # Inking completes right on anchor end: 5.0s, starting at 3.0s (2.0s duration)
    assert end_s == 5.0
    assert start_s == 3.0
    assert dur_s == 2.0

def test_temporal_feasibility_detects_late_drawing():
    validator = TemporalValidator(audio_duration=60.0)
    
    # Drawing ends at 7.5s while anchor ended at 5.0s (2.5s late)
    feasibility = validator.evaluate_timing_feasibility(
        current_start=5.5,
        current_end=7.5,
        anchor_start=4.0,
        anchor_end=5.0,
        drawing_demand=2.0
    )
    
    assert feasibility["feasible"] is False
    assert feasibility["is_late"] is True
    assert len(feasibility["issues"]) > 0

def test_negative_start_clamped_safely():
    validator = TemporalValidator(audio_duration=60.0)
    
    # Anchor starts early at 0.5s, demand is 1.5s
    start_s, end_s, dur_s = validator.compute_optimal_timing(
        anchor_start=0.2,
        anchor_end=0.8,
        drawing_demand=1.5,
        strategy=TimingStrategy.COMPLETE_ON_ANCHOR,
        prev_event_end=0.0
    )
    
    assert start_s >= 0.0
    assert end_s > start_s

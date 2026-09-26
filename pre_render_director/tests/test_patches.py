"""Tests for Timeline Patch generation and application."""

import pytest
from pre_render_director.models.patch import TimelinePatch, PatchOperation
from pre_render_director.director.patch_generator import PatchGenerator, apply_patch_batch

def test_apply_change_asset_patch():
    events = [
        {"id": "D001", "type": "draw", "asset_id": "wrong_asset", "start_s": 1.0, "end_s": 2.5}
    ]
    
    patch = PatchGenerator.create_change_asset_patch(
        event_id="D001",
        from_asset="wrong_asset",
        to_asset="correct_asset",
        reason="Resolved visual mismatch",
        confidence=0.95
    )
    
    patched, batch = apply_patch_batch(events, [patch])
    
    assert batch.applied_count == 1
    assert patched[0]["asset_id"] == "correct_asset"
    assert patch.needs_review is False

def test_apply_timing_update_patch():
    events = [
        {"id": "D002", "type": "draw", "asset_id": "a2", "start_s": 4.0, "end_s": 6.0, "duration_s": 2.0}
    ]
    
    patch = PatchGenerator.create_timing_update_patch(
        event_id="D002",
        start_s=3.2,
        end_s=5.0,
        reason="Sync complete on anchor",
        confidence=0.9
    )
    
    patched, batch = apply_patch_batch(events, [patch])
    
    assert batch.applied_count == 1
    assert patched[0]["start_s"] == 3.2
    assert patched[0]["end_s"] == 5.0
    assert patched[0]["duration_s"] == 1.8

def test_low_confidence_triggers_review():
    patch = PatchGenerator.create_change_asset_patch(
        event_id="D003",
        from_asset="a1",
        to_asset="a2",
        reason="Ambiguous narration",
        confidence=0.55  # Below 0.65 threshold
    )
    
    assert patch.needs_review is True
    assert patch.is_review_required(0.65) is True

"""Tests for Final Render Plan creation and 12-check validation gate."""

import pytest
from pre_render_director.models.input import SectionInput, AssetMetadata, WordItem
from pre_render_director.models.output import ValidationStatus
from pre_render_director.director.orchestrator import DirectorOrchestrator
from pre_render_director.ai.provider import MockVisualDirectorProvider

def test_full_director_orchestration():
    # Build a realistic sample SectionInput
    assets = {
        "banner": AssetMetadata(asset_id="banner", file="banner.png", semantic_description="Title banner", visual_role="banner", drawing_demand=1.5),
        "waking": AssetMetadata(asset_id="waking", file="waking.png", semantic_description="Waking up on the street", visual_role="subject", drawing_demand=1.8),
        "backpack": AssetMetadata(asset_id="backpack", file="backpack.png", semantic_description="Checking backpack belongings", visual_role="subject", drawing_demand=1.6)
    }
    
    words = [
        WordItem(id="w1", text="بلا", start=0.0, end=0.5, duration=0.5),
        WordItem(id="w2", text="مأوى", start=0.5, end=1.2, duration=0.7),
        WordItem(id="w3", text="تصحى", start=1.5, end=2.0, duration=0.5),
        WordItem(id="w4", text="قبل", start=2.0, end=2.4, duration=0.4),
        WordItem(id="w5", text="الفجر", start=2.4, end=3.2, duration=0.8),
        WordItem(id="w6", text="تشيك", start=4.0, end=4.5, duration=0.5),
        WordItem(id="w7", text="على", start=4.5, end=4.8, duration=0.3),
        WordItem(id="w8", text="أغراضك", start=4.8, end=5.8, duration=1.0),
    ]
    
    drawings = [
        {"id": "D001", "type": "reveal", "asset_id": "banner", "start_s": 0.0, "end_s": 1.2, "anchor_text": "بلا مأوى"},
        {"id": "D002", "type": "draw", "asset_id": "waking", "start_s": 1.4, "end_s": 3.2, "anchor_text": "تصحى قبل الفجر"},
        {"id": "D003", "type": "draw", "asset_id": "backpack", "start_s": 4.0, "end_s": 5.8, "anchor_text": "تشيك على أغراضك"}
    ]
    
    section_input = SectionInput(
        section_id="test_section",
        script_text="بلا مأوى. تصحى قبل الفجر. تشيك على أغراضك.",
        audio_path="test_audio.wav",
        audio_duration=8.0,
        words=words,
        initial_drawings=drawings,
        assets=assets
    )
    
    orchestrator = DirectorOrchestrator(
        ai_provider=MockVisualDirectorProvider(),
        max_iterations=2
    )
    
    plan, review = orchestrator.execute(section_input)
    
    # 1. Validation Status Gate
    assert plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]
    assert plan.validation.overall_score >= 0.8
    
    # 2. Render Events Verification (Contract for Renderer)
    assert len(plan.render_events) >= 3
    # Check that events have renderer keys
    for rev in plan.render_events:
        assert "event_id" in rev
        assert "type" in rev
        assert "start_s" in rev
        assert "end_s" in rev
        assert rev["end_s"] >= rev["start_s"]
    
    # 3. Visual States are generated
    assert len(plan.visual_states) > 0
    
    # 4. JSON Serialization check
    json_out = plan.export_json()
    assert "contract_version" in json_out
    assert "test_section" in json_out

"""Tests for Semantic Validation and Contradiction Detection."""

import pytest
from pre_render_director.models.input import AssetMetadata, AssetCatalog
from pre_render_director.models.output import SemanticMatchScore
from pre_render_director.director.semantic_validator import SemanticValidator
from pre_render_director.director.asset_match_validator import AssetMatchValidator
from pre_render_director.ai.provider import MockVisualDirectorProvider

def test_semantic_validator_detects_contradiction():
    validator = SemanticValidator(ai_provider=MockVisualDirectorProvider())
    
    # Asset depicts a park bench
    bench_asset = AssetMetadata(
        asset_id="r3_01_park_bench_think",
        file="r3_01_park_bench_think.png",
        semantic_description="man sitting on a park bench",
        visual_role="subject",
        action="sitting on bench",
        objects=["bench", "park"]
    )
    
    # Narration states sleeping on concrete ground
    anchor_text = "النوم على صبة في الشارع"
    result = validator.validate(
        event_id="D003",
        asset=bench_asset,
        anchor_text=anchor_text
    )
    
    assert result.is_contradictory is True
    assert result.status == SemanticMatchScore.CONTRADICTORY
    assert "bench" in result.contradiction_reason.lower()

def test_semantic_validator_matches_correct_asset():
    validator = SemanticValidator(ai_provider=MockVisualDirectorProvider())
    
    backpack_asset = AssetMetadata(
        asset_id="r1_03_check_backpack",
        file="r1_03_check_backpack.png",
        semantic_description="person checking small backpack belongings",
        visual_role="subject",
        action="inspecting bag",
        objects=["backpack", "items"]
    )
    
    anchor_text = "تشيك على أغراضك القليلة"
    result = validator.validate(
        event_id="D004",
        asset=backpack_asset,
        anchor_text=anchor_text
    )
    
    assert result.is_contradictory is False
    assert result.status in [SemanticMatchScore.EXACT_MATCH, SemanticMatchScore.STRONG_MATCH]
    assert result.match_score >= 0.75

def test_asset_match_validator_detects_missing_asset():
    # Catalog contains only food and phone
    catalog = AssetCatalog(assets={
        "food": AssetMetadata(asset_id="food", file="food.png", semantic_description="eating meal"),
        "phone": AssetMetadata(asset_id="phone", file="phone.png", semantic_description="charging phone")
    })
    
    matcher = AssetMatchValidator(catalog)
    # Speech discusses legal identity documents
    best_asset, score, decision = matcher.find_best_asset("أوراق رسمية وهوية مفقودة", ["هوية", "إجراءات"])
    
    # Should not randomly match food or phone
    assert decision == "NO_VALID_ASSET"
    assert best_asset is None

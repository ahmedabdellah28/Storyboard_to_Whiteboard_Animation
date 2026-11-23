"""Tests for AssetSheetAdapter (Task 1).

Validates:
1. Valid extractor output ingestion
2. Missing asset file detection
3. Duplicate asset ID detection
4. Malformed JSON handling
5. Invalid bounding box detection
6. Missing/invalid diagnostics handling
7. Pydantic contract compliance
8. Deterministic output reproducibility
9. Source asset ID 100% reversible preservation
10. Hash mismatch handling
"""

import copy
import json
from pathlib import Path
import pytest

from core.contracts.visual_manifest import VisualManifest, ExtractionStatus, VisualType
from core.vision.asset_sheet_adapter import (
    AssetSheetAdapter,
    AssetSheetAdapterError,
    AssetFileNotFoundError,
    DuplicateAssetIdError,
    HashMismatchError,
    InvalidBoundingBoxError,
    InvalidMetricsError,
    MalformedAssetSheetError,
    adapt_asset_sheet,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_EXTRACTOR_DIR = REPO_ROOT / "asset_sheet_extractor_v2_output"


@pytest.fixture
def minimal_extractor_dir(tmp_path: Path):
    """Creates a minimal valid extractor output fixture."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy PNG file
    png_file = assets_dir / "asset_001.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRdummy")

    assets_data = {
        "version": "2.0",
        "assets": [
            {
                "asset_id": "asset_001",
                "file": "assets/asset_001.png",
                "status": "green",
                "reasons": [],
                "bbox": {"x": 100, "y": 150, "width": 80, "height": 120},
                "pixel_area": 5000,
                "crop_size": {"width": 90, "height": 130},
                "diagnostics": {
                    "area_ratio": 0.005,
                    "area_vs_median": 1.0,
                    "fill_ratio": 0.52,
                    "aspect_ratio": 0.6667,
                    "contour_complexity": 2.4,
                    "internal_peak_count": 1,
                    "neck_ratio": 0.1,
                },
            }
        ],
    }
    (tmp_path / "assets.json").write_text(json.dumps(assets_data), encoding="utf-8")

    report_data = {
        "version": "2.0",
        "input": "test_sheet.png",
        "image_size": {"width": 1920, "height": 1080},
        "estimated_background_rgb": [255, 255, 255],
        "parameters": {"background_distance": 28.0},
        "summary": {"asset_count": 1, "valid": 1},
    }
    (tmp_path / "report.json").write_text(json.dumps(report_data), encoding="utf-8")

    return tmp_path


# ============================================================================
# 1. VALID EXTRACTOR OUTPUT
# ============================================================================

def test_valid_extractor_output_real():
    """Verify that adapting the real workspace extractor output succeeds completely."""
    if not REAL_EXTRACTOR_DIR.is_dir():
        pytest.skip(f"Extractor output directory not found at {REAL_EXTRACTOR_DIR}")

    adapter = AssetSheetAdapter()
    manifest = adapter.adapt(REAL_EXTRACTOR_DIR)

    assert isinstance(manifest, VisualManifest)
    assert manifest.contract_type == "visual_manifest"
    assert manifest.version == "2.0"
    assert manifest.storyboard_id == "separated_comic_character_and_icon_asset_sheet"
    assert len(manifest.entities) == 55
    assert manifest.canvas_dimensions == {"width": 1536, "height": 1024}
    assert len(manifest.storyboard_hash) == 64
    assert len(manifest.structural_spatial_relations) >= 0


def test_valid_extractor_output_minimal(minimal_extractor_dir: Path):
    """Verify adaptation of a clean minimal fixture."""
    manifest = adapt_asset_sheet(minimal_extractor_dir)

    assert len(manifest.entities) == 1
    ent = manifest.entities[0]
    assert ent.visual_id == "asset_001"
    assert ent.bbox == (100, 150, 80, 120)
    assert ent.centroid == (140, 210)
    assert ent.extraction_status == ExtractionStatus.VALID_REQUIRED_ASSET
    assert ent.visual_type == VisualType.ATOMIC_OBJECT
    assert ent.demand_metrics.normalized_pixel_mass == 0.52
    assert ent.demand_metrics.aspect_ratio == 0.6667
    assert ent.mask_crop_path == "assets/asset_001.png"


# ============================================================================
# 2. MISSING ASSET FILE
# ============================================================================

def test_missing_asset_file(minimal_extractor_dir: Path):
    """Raise AssetFileNotFoundError when an asset file listed in assets.json does not exist."""
    png_file = minimal_extractor_dir / "assets" / "asset_001.png"
    png_file.unlink()

    adapter = AssetSheetAdapter()
    with pytest.raises(AssetFileNotFoundError) as exc_info:
        adapter.adapt(minimal_extractor_dir, strict_file_check=True)

    assert "Asset file missing on disk" in str(exc_info.value)
    assert "asset_001" in str(exc_info.value)


def test_broken_relative_path_traversal(minimal_extractor_dir: Path):
    """Raise AssetFileNotFoundError when a relative path attempts directory traversal."""
    assets_json_path = minimal_extractor_dir / "assets.json"
    data = json.loads(assets_json_path.read_text(encoding="utf-8"))
    data["assets"][0]["file"] = "../secret/asset_001.png"
    assets_json_path.write_text(json.dumps(data), encoding="utf-8")

    adapter = AssetSheetAdapter()
    with pytest.raises(AssetFileNotFoundError) as exc_info:
        adapter.adapt(minimal_extractor_dir)

    assert "Broken relative path" in str(exc_info.value)


# ============================================================================
# 3. DUPLICATE ASSET ID
# ============================================================================

def test_duplicate_asset_id(minimal_extractor_dir: Path):
    """Raise DuplicateAssetIdError when duplicate asset IDs are present in assets.json."""
    assets_json_path = minimal_extractor_dir / "assets.json"
    data = json.loads(assets_json_path.read_text(encoding="utf-8"))

    # Duplicate the asset
    dup_asset = copy.deepcopy(data["assets"][0])
    data["assets"].append(dup_asset)
    assets_json_path.write_text(json.dumps(data), encoding="utf-8")

    adapter = AssetSheetAdapter()
    with pytest.raises(DuplicateAssetIdError) as exc_info:
        adapter.adapt(minimal_extractor_dir)

    assert "Duplicate asset ID encountered: 'asset_001'" in str(exc_info.value)


# ============================================================================
# 4. MALFORMED JSON
# ============================================================================

def test_malformed_assets_json_syntax(minimal_extractor_dir: Path):
    """Raise MalformedAssetSheetError on JSON syntax error in assets.json."""
    (minimal_extractor_dir / "assets.json").write_text("{ unquoted_broken: json", encoding="utf-8")

    adapter = AssetSheetAdapter()
    with pytest.raises(MalformedAssetSheetError) as exc_info:
        adapter.adapt(minimal_extractor_dir)

    assert "Malformed JSON in assets.json" in str(exc_info.value)


def test_malformed_report_json_syntax(minimal_extractor_dir: Path):
    """Raise MalformedAssetSheetError on JSON syntax error in report.json."""
    (minimal_extractor_dir / "report.json").write_text("NOT_JSON", encoding="utf-8")

    adapter = AssetSheetAdapter()
    with pytest.raises(MalformedAssetSheetError) as exc_info:
        adapter.adapt(minimal_extractor_dir)

    assert "Malformed JSON in report.json" in str(exc_info.value)


def test_missing_assets_array(minimal_extractor_dir: Path):
    """Raise MalformedAssetSheetError when 'assets' key is missing or not a list."""
    (minimal_extractor_dir / "assets.json").write_text(json.dumps({"version": "2.0"}), encoding="utf-8")

    adapter = AssetSheetAdapter()
    with pytest.raises(MalformedAssetSheetError) as exc_info:
        adapter.adapt(minimal_extractor_dir)

    assert "must be a JSON object containing an 'assets' array" in str(exc_info.value)


# ============================================================================
# 5. INVALID BOUNDING BOX
# ============================================================================

@pytest.mark.parametrize(
    "invalid_bbox,expected_msg",
    [
        ({"x": -10, "y": 0, "width": 50, "height": 50}, "Negative bbox origin"),
        ({"x": 0, "y": -5, "width": 50, "height": 50}, "Negative bbox origin"),
        ({"x": 0, "y": 0, "width": 0, "height": 50}, "Invalid non-positive bbox dimensions"),
        ({"x": 0, "y": 0, "width": 50, "height": -1}, "Invalid non-positive bbox dimensions"),
        ({"x": "zero", "y": 0, "width": 50, "height": 50}, "Missing/non-numeric bbox coordinate"),
    ],
)
def test_invalid_bbox_coordinates(minimal_extractor_dir: Path, invalid_bbox, expected_msg):
    """Raise InvalidBoundingBoxError on negative origins or non-positive dimensions."""
    assets_json_path = minimal_extractor_dir / "assets.json"
    data = json.loads(assets_json_path.read_text(encoding="utf-8"))
    data["assets"][0]["bbox"] = invalid_bbox
    assets_json_path.write_text(json.dumps(data), encoding="utf-8")

    adapter = AssetSheetAdapter()
    with pytest.raises(InvalidBoundingBoxError) as exc_info:
        adapter.adapt(minimal_extractor_dir)

    assert expected_msg in str(exc_info.value)


# ============================================================================
# 6. MISSING OR INVALID DIAGNOSTICS
# ============================================================================

def test_missing_diagnostics_dict(minimal_extractor_dir: Path):
    """Raise InvalidMetricsError when diagnostics dictionary is missing."""
    assets_json_path = minimal_extractor_dir / "assets.json"
    data = json.loads(assets_json_path.read_text(encoding="utf-8"))
    del data["assets"][0]["diagnostics"]
    assets_json_path.write_text(json.dumps(data), encoding="utf-8")

    adapter = AssetSheetAdapter()
    with pytest.raises(InvalidMetricsError) as exc_info:
        adapter.adapt(minimal_extractor_dir)

    assert "Missing required 'diagnostics' dictionary" in str(exc_info.value)


@pytest.mark.parametrize(
    "bad_diag,expected_msg",
    [
        ({"area_ratio": 0.1, "aspect_ratio": 1.0, "contour_complexity": 2.0}, "Missing or non-numeric diagnostic metric 'fill_ratio'"),
        ({"fill_ratio": 1.5, "aspect_ratio": 1.0, "contour_complexity": 2.0}, "Out-of-range fill_ratio"),
        ({"fill_ratio": 0.5, "aspect_ratio": -0.5, "contour_complexity": 2.0}, "Non-positive aspect_ratio"),
        ({"fill_ratio": 0.5, "aspect_ratio": 1.0, "contour_complexity": -1.0}, "Negative contour_complexity"),
    ],
)
def test_invalid_diagnostic_values(minimal_extractor_dir: Path, bad_diag, expected_msg):
    """Raise InvalidMetricsError on out-of-range or missing diagnostic metrics."""
    assets_json_path = minimal_extractor_dir / "assets.json"
    data = json.loads(assets_json_path.read_text(encoding="utf-8"))
    data["assets"][0]["diagnostics"] = bad_diag
    assets_json_path.write_text(json.dumps(data), encoding="utf-8")

    adapter = AssetSheetAdapter()
    with pytest.raises(InvalidMetricsError) as exc_info:
        adapter.adapt(minimal_extractor_dir)

    assert expected_msg in str(exc_info.value)


# ============================================================================
# 7. CONTRACT VALIDATION
# ============================================================================

def test_pydantic_contract_validation(minimal_extractor_dir: Path):
    """Validate that the adapted manifest passes Pydantic model validation and round-trips."""
    adapter = AssetSheetAdapter()
    manifest = adapter.adapt(minimal_extractor_dir)

    raw_dict = manifest.model_dump()
    reloaded = VisualManifest.model_validate(raw_dict)

    assert reloaded.contract_type == "visual_manifest"
    assert reloaded.version == "2.0"
    assert len(reloaded.entities) == len(manifest.entities)
    assert reloaded.entities[0].visual_id == manifest.entities[0].visual_id


# ============================================================================
# 8. DETERMINISTIC OUTPUT
# ============================================================================

def test_deterministic_output(minimal_extractor_dir: Path):
    """Verify that multiple adaptations of the same extractor directory produce identical outputs."""
    adapter = AssetSheetAdapter()

    manifest_1 = adapter.adapt(minimal_extractor_dir)
    manifest_2 = adapter.adapt(minimal_extractor_dir)

    dump_1 = manifest_1.model_dump_json(indent=2)
    dump_2 = manifest_2.model_dump_json(indent=2)

    assert dump_1 == dump_2


# ============================================================================
# 9. SOURCE ASSET ID PRESERVATION (100% REVERSIBLE)
# ============================================================================

def test_source_asset_id_preservation():
    """Verify that visual_id exactly matches source asset_id across all assets."""
    if not REAL_EXTRACTOR_DIR.is_dir():
        pytest.skip("Real extractor output not present.")

    adapter = AssetSheetAdapter()
    manifest = adapter.adapt(REAL_EXTRACTOR_DIR)

    with open(REAL_EXTRACTOR_DIR / "assets.json", "r", encoding="utf-8") as f:
        orig_data = json.load(f)

    raw_assets = orig_data["assets"]
    assert len(manifest.entities) == len(raw_assets)

    for entity, raw in zip(manifest.entities, raw_assets):
        assert entity.visual_id == raw["asset_id"], (
            f"ID mismatch: entity visual_id '{entity.visual_id}' != source '{raw['asset_id']}'"
        )
        assert entity.mask_crop_path == raw["file"]
        # Verify file actually exists on disk
        target_file = REAL_EXTRACTOR_DIR / entity.mask_crop_path
        assert target_file.is_file(), f"Extracted PNG missing: {target_file}"


# ============================================================================
# 10. HASH MISMATCH
# ============================================================================

def test_hash_mismatch(minimal_extractor_dir: Path):
    """Raise HashMismatchError when an expected_hash does not match the computed hash."""
    adapter = AssetSheetAdapter()
    with pytest.raises(HashMismatchError) as exc_info:
        adapter.adapt(minimal_extractor_dir, expected_hash="0000000000000000000000000000000000000000000000000000000000000000")

    assert "Storyboard hash mismatch" in str(exc_info.value)

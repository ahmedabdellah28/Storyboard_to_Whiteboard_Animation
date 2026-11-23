# Asset Sheet Adapter Documentation

**Module:** `core/vision/asset_sheet_adapter.py`  
**Purpose:** Bridge between the existing Asset Sheet Extractor v2 output and the canonical TCM-DS Contract 1 (`VisualManifest`).

---

## 1. Input Schema

The adapter accepts the output directory produced by Asset Sheet Extractor v2 (e.g. `asset_sheet_extractor_v2_output/`).

### Required Files:
1. `assets/`: Directory containing extracted transparent PNG crops (e.g., `assets/asset_001.png` ... `assets/asset_055.png`).
2. `assets.json`: JSON catalog of extracted visual units.
3. `report.json`: JSON extraction metadata and summary.

### Schema: `assets.json`
```json
{
  "version": "2.0",
  "assets": [
    {
      "asset_id": "asset_001",
      "file": "assets/asset_001.png",
      "status": "red | yellow | green",
      "reasons": ["much_larger_than_typical_asset", "possible_touching_assets"],
      "bbox": { "x": 1316, "y": 14, "width": 203, "height": 544 },
      "pixel_area": 64718,
      "crop_size": { "width": 215, "height": 556 },
      "diagnostics": {
        "area_ratio": 0.0411466,
        "area_vs_median": 8.856,
        "fill_ratio": 0.586,
        "aspect_ratio": 0.3732,
        "contour_complexity": 5.433,
        "internal_peak_count": 2,
        "neck_ratio": 0.0835
      }
    }
  ]
}
```

### Schema: `report.json`
```json
{
  "version": "2.0",
  "input": "Separated Comic Character and Icon Asset Sheet.png",
  "image_size": { "width": 1536, "height": 1024 },
  "estimated_background_rgb": [254, 254, 254],
  "parameters": {
    "background_distance": 28.0,
    "fragment_gap": 5,
    "min_area_px": 16,
    "padding": 6
  },
  "summary": {
    "asset_count": 55,
    "valid": 32,
    "needs_review": 15,
    "possible_composites": 8
  }
}
```

---

## 2. Mapping Rules

The adapter maps extractor fields into `core.contracts.visual_manifest.VisualEntity` and `NormalizedDemandMetrics` without loss of source metadata:

| Source (`assets.json` / `report.json`) | Target Contract (`VisualManifest`) | Mapping Rule |
|---|---|---|
| `asset_id` | `VisualEntity.visual_id` | **100% reversible direct copy** (`"asset_001"`). Preserves exact asset identity. |
| index + 1 | `VisualEntity.sheet_order` | Sequential 1-based order in sheet (1..N). |
| `bbox.x, y, width, height` | `VisualEntity.bbox` | `(x, y, width, height)` as integer 4-tuple. |
| `bbox` center | `VisualEntity.centroid` | `(x + width // 2, y + height // 2)`. |
| `file` | `VisualEntity.mask_crop_path` | Normalized relative path (e.g. `"assets/asset_001.png"`). |
| `status`, `reasons` | `VisualEntity.extraction_status` | Maps `"fragment"` / `"tiny"` → `FRAGMENT`, `"duplicate"` → `DUPLICATE`, `"decorative"` → `DECORATIVE`, `"invalid"` → `INVALID_CROP`, otherwise `VALID_REQUIRED_ASSET`. |
| `reasons` | `VisualEntity.visual_type` | If reasons contain `"composite"` or `"possible_touching_assets"` or `"much_larger_than_typical_asset"` → `COMPOSITE_SCENE`; otherwise `ATOMIC_OBJECT`. |
| `diagnostics.fill_ratio` | `NormalizedDemandMetrics.normalized_pixel_mass` | Clamped to `[0.0, 1.0]`. |
| `diagnostics.aspect_ratio` | `NormalizedDemandMetrics.aspect_ratio` | Positive float `> 0.0`. |
| `diagnostics.contour_complexity` | `NormalizedDemandMetrics.normalized_contour_length` | Normalized: `min(1.0, max(0.0, contour_complexity / 8.0))`. |
| `diagnostics.neck_ratio`, `contour_complexity` | `NormalizedDemandMetrics.normalized_edge_complexity` | Weighted composite in `[0.0, 1.0]`. |
| `diagnostics.internal_peak_count` | `NormalizedDemandMetrics.stroke_count_estimate` | `max(1, int(round(internal_peak_count * 3 + contour_complexity)))`. |
| Derived | `NormalizedDemandMetrics.raw_demand_score` | Weighted sum: `0.40 * mass + 0.30 * contour + 0.30 * edge`. |
| Derived | `NormalizedDemandMetrics.demand_range_s` | `{"min_s": 1.0 + 0.8*raw, "target_s": 1.5 + 1.5*raw, "max_s": 2.5 + 2.0*raw}`. |
| `status`, `reasons`, `pixel_area`, `diagnostics` | `VisualEntity.visual_tags` | Preserved as tags (e.g. `status:red`, `reason:...`, `pixel_area:...`, `area_ratio:...`). |
| Top-level summary & parameters | `VisualManifest.metadata` | Preserved in `metadata["source_extractor_metadata"]` and `metadata["raw_asset_diagnostics"]`. |
| Overlapping bounding boxes | `VisualManifest.structural_spatial_relations` | Computed pairs with `SpatialRelationType.SUBPART_OVERLAP`. |

---

## 3. Output Contract

The adapter returns an instance of `VisualManifest` and optionally writes `visual_manifest.json`:

```json
{
  "contract_type": "visual_manifest",
  "version": "2.0",
  "storyboard_id": "separated_comic_character_and_icon_asset_sheet",
  "storyboard_hash": "dd7fe1c40ea49b7530d4520a9b0b4e96ff5150b260450aa46fdba08f8938aab2",
  "canvas_dimensions": {
    "width": 1536,
    "height": 1024
  },
  "entities": [
    {
      "visual_id": "asset_001",
      "sheet_order": 1,
      "centroid": [1417, 286],
      "extraction_status": "VALID_REQUIRED_ASSET",
      "visual_type": "composite_scene",
      "bbox": [1316, 14, 203, 544],
      "mask_crop_path": "assets/asset_001.png",
      "sub_components": [],
      "demand_metrics": {
        "normalized_pixel_mass": 0.586,
        "normalized_contour_length": 0.679125,
        "normalized_edge_complexity": 0.5483125,
        "stroke_count_estimate": 11,
        "aspect_ratio": 0.3732,
        "raw_demand_score": 0.60263125,
        "demand_range_s": {
          "min_s": 1.48,
          "target_s": 2.4,
          "max_s": 3.71
        }
      },
      "visual_tags": [
        "status:red",
        "reason:much_larger_than_typical_asset",
        "reason:possible_touching_assets",
        "pixel_area:64718",
        "area_ratio:0.041147"
      ],
      "description": "Asset asset_001 [status=red] 203x544 area=64718px reasons=much_larger_than_typical_asset,possible_touching_assets"
    }
  ],
  "structural_spatial_relations": [ ... ],
  "metadata": { ... }
}
```

---

## 4. Validation Rules

The adapter enforces strict pre-ingestion checks:

1. **Missing Files**:
   - `assets.json` and `report.json` must exist in `extractor_output_dir`.
   - Every asset crop referenced by `file` must exist on disk as a file.
2. **Path Traversal**:
   - Disallows `..` or escaping outside `extractor_output_dir`.
3. **Duplicate Asset IDs**:
   - Raises error if any `asset_id` appears more than once.
4. **Bounding Boxes**:
   - `x >= 0`, `y >= 0`.
   - `width > 0`, `height > 0`.
   - Numeric types required.
5. **Diagnostics & Metrics**:
   - `diagnostics` dictionary must be present on every asset.
   - `fill_ratio` must be within `[0.0, 1.05]`.
   - `aspect_ratio` must be `> 0.0`.
   - `contour_complexity` must be `>= 0.0`.
6. **Hash Integrity**:
   - If an `expected_hash` is provided, the adapter verifies that the computed storyboard SHA-256 hash matches exactly.

---

## 5. Error Handling

All adapter errors inherit from `AssetSheetAdapterError`:

| Exception Class | Trigger Condition |
|---|---|
| `MalformedAssetSheetError` | JSON syntax errors, missing `assets` array, missing `bbox`, non-dict entities. |
| `AssetFileNotFoundError` | Crop PNG missing on disk or relative path traversal attempt. |
| `DuplicateAssetIdError` | Same `asset_id` encountered multiple times. |
| `InvalidBoundingBoxError` | Negative coordinate origin or zero/negative width or height. |
| `InvalidMetricsError` | Missing `diagnostics` dict, non-numeric metric, out-of-range `fill_ratio`, or negative `aspect_ratio`. |
| `HashMismatchError` | Computed storyboard hash differs from `expected_hash`. |

---

## 6. Usage Example

```python
from pathlib import Path
from core.vision.asset_sheet_adapter import AssetSheetAdapter

adapter = AssetSheetAdapter()
manifest = adapter.adapt(
    extractor_output_dir=Path("asset_sheet_extractor_v2_output"),
    output_manifest_path=Path("asset_sheet_extractor_v2_output/visual_manifest.json"),
)

print(f"Imported {len(manifest.entities)} assets into {manifest.contract_type}.")
```

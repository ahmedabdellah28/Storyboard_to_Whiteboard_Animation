"""Asset Sheet Adapter for TCM-DS Contract Integration.

Converts existing Asset Sheet Extractor v2 outputs (assets/, assets.json, report.json)
into canonical TCM-DS VisualManifest contracts (Contract 1: visual_manifest.json).

Strict Rules:
- ZERO modification of existing extractor modules.
- ZERO AI image-analysis or external API calls.
- Reuses canonical models in core.contracts.visual_manifest.
- Preserves 100% reversible mapping: VisualEntity.visual_id == source asset_id.
- Strict input validation across files, schemas, bounding boxes, metrics, and hashes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from core.contracts.visual_manifest import (
    ExtractionStatus,
    NormalizedDemandMetrics,
    SpatialRelation,
    SpatialRelationType,
    VisualEntity,
    VisualManifest,
    VisualType,
)
from core.artifacts.artifact_identity import hash_file, hash_string


# ============================================================================
# EXCEPTION HIERARCHY
# ============================================================================

class AssetSheetAdapterError(Exception):
    """Base exception for all asset sheet adapter errors."""
    pass


class MalformedAssetSheetError(AssetSheetAdapterError):
    """Raised when assets.json or report.json is malformed or missing required keys."""
    pass


class AssetFileNotFoundError(AssetSheetAdapterError):
    """Raised when an asset PNG file is missing or its relative path is broken."""
    pass


class DuplicateAssetIdError(AssetSheetAdapterError):
    """Raised when duplicate asset IDs are detected in extractor output."""
    pass


class InvalidBoundingBoxError(AssetSheetAdapterError):
    """Raised when a bounding box has invalid coordinates or dimensions."""
    pass


class InvalidMetricsError(AssetSheetAdapterError):
    """Raised when diagnostic metrics are missing or have invalid out-of-range values."""
    pass


class HashMismatchError(AssetSheetAdapterError):
    """Raised when the calculated hash does not match the expected hash."""
    pass


# ============================================================================
# ADAPTER IMPLEMENTATION
# ============================================================================

class AssetSheetAdapter:
    """Adapts Asset Sheet Extractor v2 outputs into canonical TCM-DS VisualManifest."""

    def __init__(self, default_canvas_dims: Tuple[int, int] = (1920, 1080)) -> None:
        self.default_canvas_dims = default_canvas_dims

    def adapt(
        self,
        extractor_output_dir: Union[str, Path],
        storyboard_id: Optional[str] = None,
        storyboard_path: Optional[Union[str, Path]] = None,
        output_manifest_path: Optional[Union[str, Path]] = None,
        expected_hash: Optional[str] = None,
        strict_file_check: bool = True,
    ) -> VisualManifest:
        """Converts an extractor output directory into a validated VisualManifest.

        Args:
            extractor_output_dir: Path to directory containing assets/, assets.json, report.json.
            storyboard_id: Optional custom identifier for the storyboard.
            storyboard_path: Optional path to the source image to compute storyboard_hash.
            output_manifest_path: Optional destination to save visual_manifest.json.
            expected_hash: Optional expected SHA-256 hash to validate against.
            strict_file_check: If True, validates existence of every asset PNG file on disk.

        Returns:
            Validated VisualManifest instance conforming to core.contracts.visual_manifest.

        Raises:
            MalformedAssetSheetError: If JSON files are missing, unparseable, or schema-invalid.
            AssetFileNotFoundError: If any asset crop file is missing from disk.
            DuplicateAssetIdError: If duplicate asset IDs are encountered.
            InvalidBoundingBoxError: If bounding box coordinates or dimensions are invalid.
            InvalidMetricsError: If diagnostics or metrics are missing or out of valid bounds.
            HashMismatchError: If computed hash does not match expected_hash.
        """
        output_dir = Path(extractor_output_dir).resolve()
        if not output_dir.is_dir():
            raise MalformedAssetSheetError(f"Extractor output directory does not exist: {output_dir}")

        assets_json_path = output_dir / "assets.json"
        report_json_path = output_dir / "report.json"

        # 1. Validate JSON file existence and well-formedness
        if not assets_json_path.is_file():
            raise MalformedAssetSheetError(f"Missing assets.json in {output_dir}")
        if not report_json_path.is_file():
            raise MalformedAssetSheetError(f"Missing report.json in {output_dir}")

        assets_data = self._load_json(assets_json_path, "assets.json")
        report_data = self._load_json(report_json_path, "report.json")

        # 2. Validate top-level schema structures
        if not isinstance(assets_data, dict) or "assets" not in assets_data:
            raise MalformedAssetSheetError("assets.json must be a JSON object containing an 'assets' array.")
        if not isinstance(assets_data["assets"], list):
            raise MalformedAssetSheetError("'assets' in assets.json must be a list.")

        if not isinstance(report_data, dict):
            raise MalformedAssetSheetError("report.json must be a JSON object.")

        # 3. Canvas Dimensions & Storyboard ID resolution
        canvas_w, canvas_h = self._resolve_canvas_dimensions(report_data)
        resolved_storyboard_id = self._resolve_storyboard_id(storyboard_id, report_data, output_dir)

        # 4. Hash resolution & verification
        computed_hash = self._resolve_storyboard_hash(
            storyboard_path=storyboard_path,
            report_data=report_data,
            output_dir=output_dir,
        )
        if expected_hash is not None and computed_hash != expected_hash:
            raise HashMismatchError(
                f"Storyboard hash mismatch: computed '{computed_hash}', expected '{expected_hash}'"
            )

        # 5. Process and validate all assets
        raw_assets = assets_data["assets"]
        entities: List[VisualEntity] = []
        seen_ids: Set[str] = set()
        raw_diagnostics_map: Dict[str, Any] = {}

        for idx, raw_asset in enumerate(raw_assets):
            entity, raw_diag = self._convert_raw_asset(
                raw_asset=raw_asset,
                output_dir=output_dir,
                sheet_order=idx + 1,
                canvas_w=canvas_w,
                canvas_h=canvas_h,
                seen_ids=seen_ids,
                strict_file_check=strict_file_check,
            )
            entities.append(entity)
            raw_diagnostics_map[entity.visual_id] = raw_diag

        # 6. Detect structural spatial relations (overlaps between bboxes)
        spatial_relations = self._compute_spatial_relations(entities)

        # 7. Build rich metadata preserving 100% of extractor information
        metadata: Dict[str, Any] = {
            "source_extractor": "asset_sheet_extractor_v2",
            "source_version": report_data.get("version", "2.0"),
            "source_input": report_data.get("input", ""),
            "estimated_background_rgb": report_data.get("estimated_background_rgb", [255, 255, 255]),
            "parameters": report_data.get("parameters", {}),
            "summary": report_data.get("summary", {}),
            "notes": report_data.get("notes", ""),
            "imported_asset_count": len(entities),
            "raw_asset_diagnostics": raw_diagnostics_map,
        }

        # 8. Construct canonical VisualManifest contract
        manifest = VisualManifest(
            contract_type="visual_manifest",
            version="2.0",
            storyboard_id=resolved_storyboard_id,
            storyboard_hash=computed_hash,
            canvas_dimensions={"width": canvas_w, "height": canvas_h},
            entities=entities,
            structural_spatial_relations=spatial_relations,
            metadata=metadata,
        )

        # 9. Optionally persist visual_manifest.json
        if output_manifest_path is not None:
            out_p = Path(output_manifest_path).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                json.dump(manifest.model_dump(), f, indent=2, ensure_ascii=False)

        return manifest

    # ------------------------------------------------------------------------
    # INTERNAL HELPERS & VALIDATORS
    # ------------------------------------------------------------------------

    def _load_json(self, path: Path, label: str) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise MalformedAssetSheetError(f"Malformed JSON in {label} ({path}): {e}") from e
        except Exception as e:
            raise MalformedAssetSheetError(f"Error reading {label} ({path}): {e}") from e

    def _resolve_canvas_dimensions(self, report_data: Dict[str, Any]) -> Tuple[int, int]:
        if "image_size" in report_data and isinstance(report_data["image_size"], dict):
            w = report_data["image_size"].get("width")
            h = report_data["image_size"].get("height")
            if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
                return (w, h)
        return self.default_canvas_dims

    def _resolve_storyboard_id(
        self,
        custom_id: Optional[str],
        report_data: Dict[str, Any],
        output_dir: Path,
    ) -> str:
        if custom_id:
            return custom_id.strip()
        if "input" in report_data and isinstance(report_data["input"], str) and report_data["input"].strip():
            stem = Path(report_data["input"]).stem
            clean_id = stem.lower().replace(" ", "_").replace("-", "_")
            return clean_id
        return output_dir.name.lower().replace(" ", "_")

    def _resolve_storyboard_hash(
        self,
        storyboard_path: Optional[Union[str, Path]],
        report_data: Dict[str, Any],
        output_dir: Path,
    ) -> str:
        # A. If explicit storyboard_path passed and exists
        if storyboard_path:
            sb_p = Path(storyboard_path).resolve()
            if sb_p.is_file():
                return hash_file(sb_p)

        # B. Check if report_data['input'] exists relative to output_dir or its parent
        input_filename = report_data.get("input", "")
        if input_filename:
            candidate_paths = [
                output_dir / input_filename,
                output_dir.parent / input_filename,
                output_dir.parent.parent / input_filename,
            ]
            for cand in candidate_paths:
                if cand.is_file():
                    return hash_file(cand)

        # C. Fallback: hash foreground_mask.png or report.json
        fg_mask = output_dir / "foreground_mask.png"
        if fg_mask.is_file():
            return hash_file(fg_mask)

        report_p = output_dir / "report.json"
        return hash_file(report_p)

    def _convert_raw_asset(
        self,
        raw_asset: Any,
        output_dir: Path,
        sheet_order: int,
        canvas_w: int,
        canvas_h: int,
        seen_ids: Set[str],
        strict_file_check: bool,
    ) -> Tuple[VisualEntity, Dict[str, Any]]:
        if not isinstance(raw_asset, dict):
            raise MalformedAssetSheetError(f"Asset at index {sheet_order - 1} is not a JSON object.")

        # 1. Asset ID & Uniqueness
        asset_id = raw_asset.get("asset_id")
        if not asset_id or not isinstance(asset_id, str):
            raise MalformedAssetSheetError(f"Missing or invalid 'asset_id' at index {sheet_order - 1}")
        asset_id = asset_id.strip()
        if asset_id in seen_ids:
            raise DuplicateAssetIdError(f"Duplicate asset ID encountered: '{asset_id}'")
        seen_ids.add(asset_id)

        # 2. File Path & Existence
        rel_file = raw_asset.get("file")
        if not rel_file or not isinstance(rel_file, str):
            raise MalformedAssetSheetError(f"Missing or invalid 'file' path for asset '{asset_id}'")

        # Disallow directory traversal outside output_dir
        if ".." in rel_file.replace("\\", "/").split("/"):
            raise AssetFileNotFoundError(f"Broken relative path (traversal disallowed): '{rel_file}'")

        target_file = (output_dir / rel_file).resolve()
        if strict_file_check and not target_file.is_file():
            raise AssetFileNotFoundError(
                f"Asset file missing on disk for '{asset_id}': {target_file}"
            )

        # 3. Bounding Box Validation
        raw_bbox = raw_asset.get("bbox")
        if not isinstance(raw_bbox, dict):
            raise MalformedAssetSheetError(f"Missing or invalid 'bbox' dictionary for asset '{asset_id}'")

        for k in ("x", "y", "width", "height"):
            if k not in raw_bbox or not isinstance(raw_bbox[k], (int, float)):
                raise InvalidBoundingBoxError(f"Missing/non-numeric bbox coordinate '{k}' for asset '{asset_id}'")

        bx = int(raw_bbox["x"])
        by = int(raw_bbox["y"])
        bw = int(raw_bbox["width"])
        bh = int(raw_bbox["height"])

        if bx < 0 or by < 0:
            raise InvalidBoundingBoxError(f"Negative bbox origin ({bx}, {by}) for asset '{asset_id}'")
        if bw <= 0 or bh <= 0:
            raise InvalidBoundingBoxError(f"Invalid non-positive bbox dimensions {bw}x{bh} for asset '{asset_id}'")

        # 4. Diagnostics & Metric Validation
        diagnostics = raw_asset.get("diagnostics")
        if not isinstance(diagnostics, dict):
            raise InvalidMetricsError(f"Missing required 'diagnostics' dictionary for asset '{asset_id}'")

        for req_metric in ("fill_ratio", "aspect_ratio", "contour_complexity"):
            if req_metric not in diagnostics or not isinstance(diagnostics[req_metric], (int, float)):
                raise InvalidMetricsError(
                    f"Missing or non-numeric diagnostic metric '{req_metric}' for asset '{asset_id}'"
                )

        fill_ratio = float(diagnostics["fill_ratio"])
        aspect_ratio = float(diagnostics["aspect_ratio"])
        contour_complexity = float(diagnostics["contour_complexity"])

        if not (0.0 <= fill_ratio <= 1.05):
            raise InvalidMetricsError(f"Out-of-range fill_ratio={fill_ratio} for asset '{asset_id}' (expected 0.0..1.0)")
        if aspect_ratio <= 0.0:
            raise InvalidMetricsError(f"Non-positive aspect_ratio={aspect_ratio} for asset '{asset_id}'")
        if contour_complexity < 0.0:
            raise InvalidMetricsError(f"Negative contour_complexity={contour_complexity} for asset '{asset_id}'")

        fill_ratio_clamped = min(1.0, max(0.0, fill_ratio))

        # 5. Normalized Demand Metrics Calculation
        # Contour complexity is typically in [1.0, 8.0+]; normalize to [0.0, 1.0]
        norm_contour_len = min(1.0, max(0.0, contour_complexity / 8.0))
        neck_ratio = float(diagnostics.get("neck_ratio", 0.1))
        norm_edge_complex = min(1.0, max(0.0, 0.5 * min(1.0, max(0.0, neck_ratio * 5.0)) + 0.5 * norm_contour_len))

        internal_peaks = int(diagnostics.get("internal_peak_count", 1))
        stroke_count = max(1, int(round(internal_peaks * 3 + contour_complexity)))

        raw_demand = min(1.0, max(0.0, 0.40 * fill_ratio_clamped + 0.30 * norm_contour_len + 0.30 * norm_edge_complex))
        demand_metrics = NormalizedDemandMetrics(
            normalized_pixel_mass=fill_ratio_clamped,
            normalized_contour_length=norm_contour_len,
            normalized_edge_complexity=norm_edge_complex,
            stroke_count_estimate=stroke_count,
            aspect_ratio=aspect_ratio,
            raw_demand_score=raw_demand,
            demand_range_s={
                "min_s": round(1.0 + raw_demand * 0.8, 2),
                "target_s": round(1.5 + raw_demand * 1.5, 2),
                "max_s": round(2.5 + raw_demand * 2.0, 2),
            },
        )

        # 6. Status, Reasons & Visual Type Classification
        status = str(raw_asset.get("status", "green")).lower()
        reasons = [str(r) for r in raw_asset.get("reasons", []) if isinstance(r, (str, int, float))]

        extraction_status = ExtractionStatus.VALID_REQUIRED_ASSET
        if any("duplicate" in r.lower() for r in reasons):
            extraction_status = ExtractionStatus.DUPLICATE
        elif any("fragment" in r.lower() or "tiny" in r.lower() for r in reasons):
            extraction_status = ExtractionStatus.FRAGMENT
        elif any("decorative" in r.lower() for r in reasons):
            extraction_status = ExtractionStatus.DECORATIVE
        elif any("invalid" in r.lower() for r in reasons):
            extraction_status = ExtractionStatus.INVALID_CROP

        is_composite = any(
            "composite" in r.lower()
            or "possible_touching_assets" in r.lower()
            or "much_larger_than_typical_asset" in r.lower()
            for r in reasons
        )
        visual_type = VisualType.COMPOSITE_SCENE if is_composite else VisualType.ATOMIC_OBJECT

        # 7. Tags & Metadata Preservation
        pixel_area = raw_asset.get("pixel_area", bw * bh)
        crop_size = raw_asset.get("crop_size", {"width": bw, "height": bh})
        visual_tags: List[str] = [f"status:{status}"]
        for r in reasons:
            visual_tags.append(f"reason:{r}")
        visual_tags.append(f"pixel_area:{pixel_area}")
        visual_tags.append(f"area_ratio:{diagnostics.get('area_ratio', 0.0):.6f}")

        centroid = (bx + bw // 2, by + bh // 2)

        description = (
            f"Asset {asset_id} [status={status}] {bw}x{bh} area={pixel_area}px "
            f"reasons={','.join(reasons) if reasons else 'none'}"
        )

        entity = VisualEntity(
            visual_id=asset_id,
            sheet_order=sheet_order,
            centroid=centroid,
            extraction_status=extraction_status,
            visual_type=visual_type,
            bbox=(bx, by, bw, bh),
            mask_crop_path=rel_file.replace("\\", "/"),
            sub_components=[],
            demand_metrics=demand_metrics,
            visual_tags=visual_tags,
            description=description,
        )

        raw_diag_info = {
            "asset_id": asset_id,
            "status": status,
            "reasons": reasons,
            "pixel_area": pixel_area,
            "crop_size": crop_size,
            "diagnostics": diagnostics,
        }

        return entity, raw_diag_info

    def _compute_spatial_relations(self, entities: List[VisualEntity]) -> List[SpatialRelation]:
        """Identifies overlap and structural containment relationships between entities."""
        relations: List[SpatialRelation] = []
        for i, a in enumerate(entities):
            for j, b in enumerate(entities):
                if i >= j:
                    continue
                ax, ay, aw, ah = a.bbox
                bx, by, bw, bh = b.bbox

                x_overlap = max(0, min(ax + aw, bx + bw) - max(ax, bx))
                y_overlap = max(0, min(ay + ah, by + bh) - max(ay, by))
                overlap_area = x_overlap * y_overlap

                if overlap_area > 0:
                    min_area = min(aw * ah, bw * bh)
                    overlap_ratio = overlap_area / float(max(1, min_area))
                    relations.append(
                        SpatialRelation(
                            source=a.visual_id,
                            target=b.visual_id,
                            type=SpatialRelationType.SUBPART_OVERLAP,
                            allowed_overlap_ratio=round(min(1.0, overlap_ratio), 3),
                        )
                    )
        return relations


def adapt_asset_sheet(
    extractor_output_dir: Union[str, Path],
    storyboard_id: Optional[str] = None,
    storyboard_path: Optional[Union[str, Path]] = None,
    output_manifest_path: Optional[Union[str, Path]] = None,
    expected_hash: Optional[str] = None,
    strict_file_check: bool = True,
) -> VisualManifest:
    """Convenience functional interface to adapt an extractor output directory."""
    adapter = AssetSheetAdapter()
    return adapter.adapt(
        extractor_output_dir=extractor_output_dir,
        storyboard_id=storyboard_id,
        storyboard_path=storyboard_path,
        output_manifest_path=output_manifest_path,
        expected_hash=expected_hash,
        strict_file_check=strict_file_check,
    )

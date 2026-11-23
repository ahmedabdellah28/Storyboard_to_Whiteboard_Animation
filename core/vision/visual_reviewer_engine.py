"""Batch-Aware Visual Reviewer Engine (TCM-DS Contract 1 Generator).

Inspects extracted candidates from AdaptiveCandidateExtractor:
- Eliminates junk/speckles
- Computes NormalizedDemandMetrics (via DemandEstimator)
- Classifies entities into Composite Scene vs Atomic Object
- Generates pure visual_manifest.json (Contract 1)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
import cv2
import numpy as np

from core.contracts.visual_manifest import (
    VisualManifest,
    VisualEntity,
    VisualType,
    SpatialRelation,
    SpatialRelationType,
    NormalizedDemandMetrics,
)
from core.vision.adaptive_candidate_extractor import ExtractedCandidate
from core.vision.demand_estimator import DemandEstimator
from core.artifacts.artifact_identity import hash_file


class VisualReviewerEngine:
    """Evaluates extracted visual candidates and constructs Contract 1 (visual_manifest.json)."""

    def __init__(self, demand_estimator: Optional[DemandEstimator] = None) -> None:
        self.demand_estimator = demand_estimator or DemandEstimator()

    def review_and_build_manifest(
        self,
        storyboard_path: Path,
        candidates: List[ExtractedCandidate],
        storyboard_id: str,
        canvas_dimensions: tuple[int, int] = (1920, 1080),
        output_manifest_path: Optional[Path] = None,
    ) -> VisualManifest:
        """Reviews candidate visual entities and outputs a validated VisualManifest."""
        sb_hash = hash_file(storyboard_path)
        entities: List[VisualEntity] = []
        canvas_w, canvas_h = canvas_dimensions

        for cand in candidates:
            # 1. Junk / Noise filtering: filter tiny fragments under 3500 pixels
            if cand.area < 3500:
                continue

            # 2. Compute normalized demand metrics
            metrics = self.demand_estimator.compute_metrics(
                crop_bgr=cand.crop_bgr,
                mask=cand.mask,
                canvas_dimensions=canvas_dimensions,
            )

            # 3. Classify Composite Scene vs Atomic Object based on topology and complexity
            # Scenes typically have high stroke counts (> 30) or large canvas footprint (> 10%)
            is_composite = (metrics.stroke_count_estimate >= 35) or (metrics.raw_demand_score >= 0.65)
            v_type = VisualType.COMPOSITE_SCENE if is_composite else VisualType.ATOMIC_OBJECT

            entity = VisualEntity(
                visual_id=cand.candidate_id,
                sheet_order=getattr(cand, "sheet_order", len(entities) + 1),
                centroid=getattr(cand, "centroid", (int(cand.bbox[0] + cand.bbox[2] / 2.0), int(cand.bbox[1] + cand.bbox[3] / 2.0))),
                extraction_status="VALID_REQUIRED_ASSET",
                visual_type=v_type,
                bbox=cand.bbox,
                mask_crop_path=f"crops/{cand.candidate_id}.png",
                demand_metrics=metrics,
                visual_tags=[],
                description=f"Extracted entity {cand.candidate_id} ({v_type.value})",
            )
            entities.append(entity)

        # 4. Detect structural spatial relations between entities
        structural_relations: List[SpatialRelation] = []
        for i, ent_a in enumerate(entities):
            for j, ent_b in enumerate(entities):
                if i >= j:
                    continue
                ax, ay, aw, ah = ent_a.bbox
                bx, by, bw, bh = ent_b.bbox
                # Check horizontal/vertical adjacency
                x_overlap = max(0, min(ax + aw, bx + bw) - max(ax, bx))
                y_overlap = max(0, min(ay + ah, by + bh) - max(ay, by))
                if x_overlap > 0 and y_overlap > 0:
                    structural_relations.append(
                        SpatialRelation(
                            source=ent_a.visual_id,
                            target=ent_b.visual_id,
                            type=SpatialRelationType.SUBPART_OVERLAP,
                            allowed_overlap_ratio=0.30,
                        )
                    )

        manifest = VisualManifest(
            storyboard_id=storyboard_id,
            storyboard_hash=sb_hash,
            canvas_dimensions={"width": canvas_w, "height": canvas_h},
            entities=entities,
            structural_spatial_relations=structural_relations,
        )

        if output_manifest_path:
            output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest.model_dump(), f, indent=2, ensure_ascii=False)

        return manifest

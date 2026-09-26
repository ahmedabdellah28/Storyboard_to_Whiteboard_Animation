"""Validates asset catalog existence, file integrity, and semantic compatibility."""

from typing import List, Dict, Any, Tuple
from ..models.input import AssetCatalog, AssetMetadata
from ..models.output import ValidationCheckResult, SemanticMatchScore

def validate_asset_references(
    events: List[Dict[str, Any]],
    catalog: AssetCatalog
) -> Tuple[ValidationCheckResult, ValidationCheckResult]:
    """Runs CHECK 01 and CHECK 02."""
    c1_details = []
    c2_details = []

    for ev in events:
        eid = ev.get("event_id") or ev.get("id", "UNKNOWN")
        atype = ev.get("type", "draw")
        aid = ev.get("asset_id")

        if atype in ["draw", "reveal", "highlight", "erase"]:
            if not aid:
                c1_details.append(f"Event {eid} ({atype}) is missing asset_id.")
            else:
                asset = catalog.get(aid)
                if not asset:
                    c2_details.append(f"Event {eid} references missing asset '{aid}'.")
                elif asset.image_path:
                    import os
                    if not os.path.exists(asset.image_path):
                        c2_details.append(f"Asset '{aid}' image file not found on disk: {asset.image_path}")

    r1 = ValidationCheckResult(
        check_id="CHECK_01",
        name="Every event references valid asset",
        passed=(len(c1_details) == 0),
        severity="ERROR",
        details=c1_details
    )

    r2 = ValidationCheckResult(
        check_id="CHECK_02",
        name="Every asset exists",
        passed=(len(c2_details) == 0),
        severity="ERROR",
        details=c2_details
    )

    return r1, r2

def validate_semantic_matches(
    evaluation_results: List[Dict[str, Any]]
) -> Tuple[ValidationCheckResult, ValidationCheckResult]:
    """Runs CHECK 03 (Semantic match) and CHECK 04 (No contradiction)."""
    c3_details = []
    c4_details = []

    for item in evaluation_results:
        eid = item.get("event_id", "UNKNOWN")
        match = item.get("semantic_match", "STRONG_MATCH")
        is_contra = item.get("contradiction_detected", False)
        reason = item.get("contradiction_reason", "")

        if match in ["INVALID", "WEAK_MATCH"]:
            c3_details.append(f"Event {eid} has poor semantic match: {match}")

        if is_contra or match == "CONTRADICTORY":
            c4_details.append(f"Event {eid} contradictory: {reason}")

    r3 = ValidationCheckResult(
        check_id="CHECK_03",
        name="Every asset semantically matches",
        passed=(len(c3_details) == 0),
        severity="WARNING" if not any(x.endswith("INVALID") for x in c3_details) else "ERROR",
        details=c3_details
    )

    r4 = ValidationCheckResult(
        check_id="CHECK_04",
        name="No contradictory asset",
        passed=(len(c4_details) == 0),
        severity="ERROR",
        details=c4_details
    )

    return r3, r4

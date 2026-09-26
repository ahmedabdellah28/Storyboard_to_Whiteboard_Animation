"""Validates that asset visual dependencies are respected chronologically."""

from typing import List, Dict, Any
from ..models.input import AssetCatalog
from ..models.output import ValidationCheckResult

def validate_asset_dependencies(
    events: List[Dict[str, Any]],
    catalog: AssetCatalog
) -> ValidationCheckResult:
    """Runs CHECK 05: Dependencies are valid."""
    details = []

    # Map each asset to its first appearance time
    first_seen: Dict[str, float] = {}
    for ev in events:
        aid = ev.get("asset_id")
        if not aid:
            continue
        start_s = float(ev.get("start_s", 0.0))
        if aid not in first_seen or start_s < first_seen[aid]:
            first_seen[aid] = start_s

    # Verify each event's asset dependencies
    for ev in events:
        eid = ev.get("event_id") or ev.get("id", "UNKNOWN")
        aid = ev.get("asset_id")
        if not aid:
            continue
        start_s = float(ev.get("start_s", 0.0))

        asset = catalog.get(aid)
        if asset and asset.dependencies:
            for dep_id in asset.dependencies:
                if dep_id not in first_seen:
                    details.append(
                        f"Event {eid} ({aid}) depends on '{dep_id}', but '{dep_id}' never appears in timeline."
                    )
                elif first_seen[dep_id] > start_s + 0.05:
                    details.append(
                        f"Event {eid} ({aid}) starts at {start_s}s before its dependency '{dep_id}' (first seen at {first_seen[dep_id]}s)."
                    )

    return ValidationCheckResult(
        check_id="CHECK_05",
        name="Dependencies are valid",
        passed=(len(details) == 0),
        severity="ERROR",
        details=details
    )

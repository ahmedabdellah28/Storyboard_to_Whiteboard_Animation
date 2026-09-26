"""Generates and applies surgical, non-destructive timeline patches."""

import copy
from typing import List, Dict, Any, Tuple
from ..models.patch import TimelinePatch, PatchOperation, PatchBatch

class PatchGenerator:
    """Generates standard timeline patches from director feedback."""

    @staticmethod
    def create_change_asset_patch(
        event_id: str,
        from_asset: str,
        to_asset: str,
        reason: str,
        confidence: float = 0.95
    ) -> TimelinePatch:
        return TimelinePatch(
            patch_id=f"PATCH_SWAP_{event_id}",
            operation=PatchOperation.CHANGE_ASSET,
            event_id=event_id,
            from_asset=from_asset,
            to_asset=to_asset,
            changes={"asset_id": to_asset},
            confidence=confidence,
            reason=reason,
            needs_review=(confidence < 0.65)
        )

    @staticmethod
    def create_timing_update_patch(
        event_id: str,
        start_s: float,
        end_s: float,
        reason: str,
        confidence: float = 0.95
    ) -> TimelinePatch:
        return TimelinePatch(
            patch_id=f"PATCH_TIME_{event_id}",
            operation=PatchOperation.UPDATE_EVENT,
            event_id=event_id,
            changes={"start_s": round(start_s, 3), "end_s": round(end_s, 3), "duration_s": round(end_s - start_s, 3)},
            confidence=confidence,
            reason=reason,
            needs_review=(confidence < 0.65)
        )

def apply_patch_batch(
    events: List[Dict[str, Any]],
    patches: List[TimelinePatch]
) -> Tuple[List[Dict[str, Any]], PatchBatch]:
    """Applies a batch of patches to events list in place or creates a patched copy."""
    patched_events = copy.deepcopy(events)
    applied = 0
    rejected = 0
    notes = []

    # Index events by id
    event_map: Dict[str, Dict[str, Any]] = {}
    for ev in patched_events:
        eid = ev.get("event_id") or ev.get("id")
        if eid:
            event_map[eid] = ev

    for p in patches:
        eid = p.event_id
        op = p.operation

        if op == PatchOperation.KEEP_EVENT:
            applied += 1
            continue

        if op == PatchOperation.CHANGE_ASSET and eid in event_map:
            target_asset = p.to_asset or p.changes.get("asset_id")
            if target_asset:
                event_map[eid]["asset_id"] = target_asset
                applied += 1
                notes.append(f"Applied {p.patch_id}: Changed asset of {eid} to {target_asset}")
            else:
                rejected += 1

        elif op in [PatchOperation.UPDATE_EVENT, PatchOperation.MOVE_EVENT, PatchOperation.RESIZE_EVENT] and eid in event_map:
            ev = event_map[eid]
            for k, v in p.changes.items():
                ev[k] = v
            # Recompute duration_s if start or end changed
            if "start_s" in ev and "end_s" in ev:
                ev["duration_s"] = round(float(ev["end_s"]) - float(ev["start_s"]), 3)
            applied += 1
            notes.append(f"Applied {p.patch_id}: Updated {eid} with {list(p.changes.keys())}")

        elif op == PatchOperation.REMOVE_EVENT or op == PatchOperation.REJECT_EVENT:
            if eid in event_map:
                patched_events = [e for e in patched_events if (e.get("event_id") or e.get("id")) != eid]
                event_map.pop(eid, None)
                applied += 1
                notes.append(f"Applied {p.patch_id}: Removed {eid}")
            else:
                rejected += 1

        elif op == PatchOperation.ADD_EVENT and p.new_event:
            new_e = copy.deepcopy(p.new_event)
            patched_events.append(new_e)
            nid = new_e.get("event_id") or new_e.get("id")
            if nid:
                event_map[nid] = new_e
            applied += 1
            notes.append(f"Applied {p.patch_id}: Added new event {nid}")
        else:
            rejected += 1

    # Sort chronologically by start_s
    patched_events.sort(key=lambda x: float(x.get("start_s", 0.0)))

    batch = PatchBatch(
        patches=patches,
        applied_count=applied,
        rejected_count=rejected,
        notes=notes
    )
    return patched_events, batch

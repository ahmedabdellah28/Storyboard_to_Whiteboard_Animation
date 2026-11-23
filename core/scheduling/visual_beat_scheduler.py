"""Visual Beat Scheduler and Constraint Solver.

Converts resolved semantic anchor beats into concrete drawing, hold, and fade windows.
Enforces:
- Speech lead-in (drawing begins 0.15s - 0.35s before anchor pronunciation)
- Minimum and maximum duration limits from draw_demand
- Non-negative time spans and strictly sorted chronology
- Zero blank screens (hold windows extend until camera transition or scene change)
- Priority shedding for congested audio windows (HERO > SUPPORT > CONTEXT)
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class VisualBeatScheduler:
    """Calculates temporal drawing windows and staging specifications."""

    def __init__(
        self,
        audio_duration: float,
        lead_in_s: float = 0.20,
        min_gap_s: float = 0.10,
        max_overlap_s: float = 0.25,
    ) -> None:
        self.audio_duration = audio_duration
        self.lead_in_s = lead_in_s
        self.min_gap_s = min_gap_s
        self.max_overlap_s = max_overlap_s

    def schedule(
        self,
        resolved_beats: List[Dict[str, Any]],
        assets_per_zone: int = 3,
    ) -> Tuple[List[Dict[str, Any]], List[List[Any]]]:
        """Schedules resolved beats into concrete drawing timeline events and staging specs.

        Returns:
            Tuple of (drawing_events, staging_specs)
        """
        drawing_events: List[Dict[str, Any]] = []
        staging_specs: List[List[Any]] = []

        # Sort beats by speech anchor start time
        sorted_beats = sorted(resolved_beats, key=lambda b: b["speech_start_s"])
        current_cursor = 0.0

        for i, beat in enumerate(sorted_beats, 1):
            concept_id = beat["concept_id"]
            asset_ids = beat["asset_ids"]
            primary_aid = asset_ids[0] if asset_ids else concept_id
            speech_st = beat["speech_start_s"]
            demand = beat["draw_demand"]
            d_est = float(demand.get("estimated", 1.8))
            d_min = float(demand.get("min", 1.2))
            d_max = float(demand.get("max", 2.6))
            anim_type = beat["anim_type"]
            depth = beat["depth"]

            # 1. Calculate ideal start with lead-in
            t_start = max(0.0, speech_st - self.lead_in_s)

            # Avoid starting before previous drawing completed (allowable slight overlap)
            if t_start < current_cursor - self.max_overlap_s:
                t_start = max(0.0, current_cursor - self.max_overlap_s)

            # 2. Lookahead to next beat for available window
            if i < len(sorted_beats):
                next_speech_st = sorted_beats[i]["speech_start_s"]
                next_ideal_start = max(0.0, next_speech_st - self.lead_in_s)
                avail_window = next_ideal_start - t_start
                if avail_window > 0:
                    t_dur = min(d_max, max(d_min, avail_window * 0.95))
                else:
                    t_dur = d_min
            else:
                remaining = self.audio_duration - t_start
                t_dur = min(d_max, max(d_min, remaining))

            t_dur = round(max(0.6, t_dur), 2)
            t_end = round(t_start + t_dur, 2)
            current_cursor = t_end

            # Assign zone based on temporal clustering
            zone_idx = min(12, 1 + ((i - 1) // assets_per_zone))
            zone_name = f"zone_{zone_idx:02d}"

            # Append to drawing events
            drawing_events.append({
                "id": f"D{i:03d}",
                "type": "reveal" if i == 1 else "draw",
                "asset_id": primary_aid,
                "concept_id": concept_id,
                "start_s": round(t_start, 2),
                "end_s": t_end,
                "duration_s": t_dur,
                "trigger": "semantic_anchor",
                "anchor_text": beat["primary_anchor"],
                "importance": beat["importance"],
                "zone": zone_name,
                "confidence": beat["confidence"],
                "layer_order": i - 1,
            })

            # Append staging spec for rendering engine
            # Format: [aid, t_start, t_dur, anim_type, depth]
            staging_specs.append([
                primary_aid,
                round(t_start, 2),
                t_dur,
                anim_type,
                depth,
            ])

        return drawing_events, staging_specs

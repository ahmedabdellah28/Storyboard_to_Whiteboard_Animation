from typing import List, Dict, Any, Optional
from ..timeline.models import VisualBeatItem, PauseItem, DrawingItem
from .drawing_demand import DrawingDemandCalculator
from .drawing_duration import DrawingDurationEstimator

class BeatSolver:
    """
    Constraint-based temporal solver mapping visual beats and drawing demand into the actual DrawingTimeline.
    Decouples speech windows from drawing windows using lead-in timing, pause utilization, and dependency trees.
    """
    def __init__(
        self,
        max_lead_in_s: float = 0.45,
        max_lag_s: float = 0.30,
        pause_utilization: float = 0.85,
        allow_overlap: bool = True,
        max_overlap_s: float = 0.25
    ):
        self.max_lead_in_s = max_lead_in_s
        self.max_lag_s = max_lag_s
        self.pause_utilization = pause_utilization
        self.allow_overlap = allow_overlap
        self.max_overlap_s = max_overlap_s
        self.demand_calc = DrawingDemandCalculator()
        self.duration_est = DrawingDurationEstimator()

    def solve(
        self,
        visual_beats: List[VisualBeatItem],
        assets: List[Dict[str, Any]],
        pauses: List[PauseItem],
        section_duration: float
    ) -> List[DrawingItem]:
        """
        Solves drawing intervals [start_s, end_s] for all visual beats.
        Enforces hard temporal limits, dependencies, and maximizes rhythm & synchrony.
        """
        if not visual_beats:
            return []

        # Build asset lookup
        asset_map: Dict[str, Dict[str, Any]] = {}
        for a in assets:
            aid = str(a.get("aid", a.get("id", "")))
            asset_map[aid] = a

        drawing_events: List[DrawingItem] = []
        last_draw_end = 0.0

        for idx, vb in enumerate(visual_beats):
            asset_data = asset_map.get(vb.asset_id, {"aid": vb.asset_id})
            demand = self.demand_calc.compute_demand(asset_data)
            needed_duration = self.duration_est.estimate(demand)

            speech_start = vb.speech_anchor.start
            speech_end = vb.speech_anchor.end
            speech_span = max(0.1, speech_end - speech_start)

            # Target end time: sync element completion close to speech anchor completion
            ideal_end = speech_end
            
            # Lead-in calculation: If drawing takes longer than speech window, start before speech
            if needed_duration > speech_span:
                ideal_start = ideal_end - needed_duration
            else:
                # Start comfortably at or slightly after speech start
                ideal_start = speech_start

            # Check previous pauses: Can we shift start back into a preceding pause?
            for p in pauses:
                if p.end <= speech_start and (speech_start - p.end) < 0.4:
                    pause_room = p.duration * self.pause_utilization
                    shift = min(pause_room, self.max_lead_in_s)
                    ideal_start = max(0.0, ideal_start - shift)
                    break

            # Enforce hard constraints:
            # 1. Start cannot precede 0.0
            actual_start = max(0.0, ideal_start)

            # 2. Dependency ordering: cannot start before dependent assets finish
            dependencies = asset_data.get("depends_on", [])
            for dep_id in dependencies:
                for past_draw in drawing_events:
                    if past_draw.asset_id == dep_id:
                        actual_start = max(actual_start, past_draw.end_s)

            # 3. Overlap control with previous drawing
            if not self.allow_overlap:
                actual_start = max(actual_start, last_draw_end)
            else:
                actual_start = max(actual_start, last_draw_end - self.max_overlap_s)

            # Calculate actual end
            actual_end = actual_start + needed_duration

            # 4. End cannot exceed section duration
            if actual_end > section_duration:
                actual_end = section_duration
                actual_start = max(0.0, actual_end - needed_duration)
                if actual_end <= actual_start:
                    actual_start = max(0.0, actual_end - 0.20)

            dur = max(0.05, actual_end - actual_start)
            d_id = f"D{idx+1:03d}"

            trigger = "lead_in" if actual_start < speech_start - 0.05 else "semantic"
            if dependencies:
                trigger = "dependency"

            draw_item = DrawingItem(
                id=d_id,
                type=vb.action,
                asset_id=vb.asset_id,
                start_s=round(actual_start, 3),
                end_s=round(actual_end, 3),
                duration_s=round(dur, 3),
                trigger=trigger,
                anchor_text=vb.speech_anchor.text[:30],
                confidence=0.95,
                layer_order=idx
            )

            drawing_events.append(draw_item)
            last_draw_end = actual_end

        return drawing_events

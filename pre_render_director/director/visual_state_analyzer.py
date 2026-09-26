"""Visual state tracker and continuity analyzer across the whiteboard timeline."""

from typing import List, Dict, Any, Optional, Set
from ..models.output import VisualStateSnapshot

class VisualStateAnalyzer:
    """Analyzes continuous visual state on the whiteboard canvas over time."""

    def __init__(self, audio_duration: float):
        self.audio_duration = audio_duration

    def compute_visual_states(
        self,
        render_events: List[Dict[str, Any]],
        sample_interval: float = 0.5
    ) -> List[VisualStateSnapshot]:
        """Discretizes the timeline into chronological snapshots tracking visible and drawing assets."""
        if not render_events:
            return []

        # Find key timestamps (starts and ends of all events)
        timestamps: Set[float] = {0.0}
        for ev in render_events:
            st = float(ev.get("start_s", 0.0))
            en = float(ev.get("end_s", 0.0))
            timestamps.add(st)
            timestamps.add(en)

        if self.audio_duration > 0:
            timestamps.add(self.audio_duration)

        sorted_times = sorted(list(timestamps))
        snapshots: List[VisualStateSnapshot] = []

        # Maintain cumulative state of drawn elements
        visible_set: Set[str] = set()

        for t in sorted_times:
            currently_drawing: List[str] = []
            highlighted: List[str] = []
            camera_focus: Optional[str] = None

            for ev in render_events:
                aid = ev.get("asset_id")
                atype = ev.get("type", "draw")
                st = float(ev.get("start_s", 0.0))
                en = float(ev.get("end_s", 0.0))
                fade_out = ev.get("fade_out_at")

                # If element has finished drawing and hasn't faded out, it remains visible
                if aid and atype in ["draw", "reveal"]:
                    if t >= en:
                        if fade_out is None or t < float(fade_out):
                            visible_set.add(aid)
                        else:
                            visible_set.discard(aid)

                    # Actively drawing right now
                    if st <= t < en:
                        currently_drawing.append(aid)
                        # Currently drawing asset is the natural focus
                        camera_focus = aid

                elif atype == "highlight" and st <= t <= en and aid:
                    highlighted.append(aid)
                    camera_focus = aid

                elif atype == "camera" and st <= t <= en:
                    target = ev.get("target_asset_id")
                    if target:
                        camera_focus = target

                elif atype == "erase" and t >= en and aid:
                    visible_set.discard(aid)

            snap = VisualStateSnapshot(
                time_s=round(t, 3),
                visible_assets=sorted(list(visible_set)),
                drawing=sorted(currently_drawing),
                highlighted=sorted(highlighted),
                camera_focus=camera_focus,
                density=len(visible_set)
            )
            snapshots.append(snap)

        return snapshots

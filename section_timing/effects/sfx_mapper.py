from typing import List, Dict, Any, Optional
from ..timeline.models import DrawingItem, SFXItem

class SFXMapper:
    """Intelligently places SFX cues on key drawing events, reveals, and transitions without clutter."""
    
    ACTION_SFX_MAP = {
        "draw": "marker_draw",
        "reveal": "pop",
        "connect": "whoosh",
        "write": "marker_draw",
        "highlight": "ding",
        "erase": "eraser_wipe"
    }

    def map_sfx(
        self,
        drawings: List[DrawingItem],
        assets: Optional[List[Dict[str, Any]]] = None
    ) -> List[SFXItem]:
        sfx_events: List[SFXItem] = []
        asset_sfx_dict = {}
        if assets:
            for a in assets:
                aid = str(a.get("aid", a.get("id", "")))
                if "sfx" in a:
                    asset_sfx_dict[aid] = a["sfx"]

        counter = 1
        last_sfx_time = -2.0

        for d in drawings:
            # Check if asset explicitly requested SFX
            custom_sfx = asset_sfx_dict.get(d.asset_id)
            
            # If not explicitly requested, only trigger SFX on important actions and keep rhythmic breathing room (>= 1.2s gap)
            should_add = False
            sfx_type = "marker_draw"

            if custom_sfx:
                should_add = True
                sfx_type = custom_sfx
            elif d.type in ("reveal", "highlight", "connect"):
                if (d.start_s - last_sfx_time) >= 1.2:
                    should_add = True
                    sfx_type = self.ACTION_SFX_MAP.get(d.type, "pop")
            elif d.duration_s >= 1.2 and (d.start_s - last_sfx_time) >= 2.5:
                # Add subtle marker draw for prominent illustration
                should_add = True
                sfx_type = "marker_draw"

            if should_add:
                # SFX duration usually 0.4s - 0.8s
                sfx_dur = min(d.duration_s, 0.75) if sfx_type == "marker_draw" else 0.40
                sfx_events.append(SFXItem(
                    id=f"sfx_{counter:03d}",
                    type=sfx_type,
                    start_s=round(d.start_s, 3),
                    end_s=round(d.start_s + sfx_dur, 3),
                    duration_s=round(sfx_dur, 3),
                    anchor_asset_id=d.asset_id
                ))
                last_sfx_time = d.start_s
                counter += 1

        return sfx_events

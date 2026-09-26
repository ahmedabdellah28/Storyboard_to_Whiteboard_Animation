from typing import List, Dict, Any, Optional
from ..timeline.models import DrawingItem, CameraItem

class CameraMapper:
    """Generates cinematic camera movements (pan, zoom, reveal) synchronized with visual activity."""
    def map_camera(
        self,
        drawings: List[DrawingItem],
        assets: Optional[List[Dict[str, Any]]] = None,
        total_duration: float = 0.0
    ) -> List[CameraItem]:
        camera_events: List[CameraItem] = []
        if not drawings:
            return camera_events

        asset_zone_dict = {}
        if assets:
            for a in assets:
                aid = str(a.get("aid", a.get("id", "")))
                asset_zone_dict[aid] = a.get("zone", "zone_1A")

        counter = 1
        current_zone = None
        last_cam_time = 0.0

        for d in drawings:
            z = asset_zone_dict.get(d.asset_id)
            if z and z != current_zone:
                # Spatial pan to new zone
                pan_dur = 1.0
                pan_start = max(0.0, d.start_s - 0.25)
                pan_end = min(total_duration, pan_start + pan_dur)

                camera_events.append(CameraItem(
                    id=f"cam_{counter:03d}",
                    type="camera_pan",
                    start_s=round(pan_start, 3),
                    end_s=round(pan_end, 3),
                    duration_s=round(pan_end - pan_start, 3),
                    target_asset_id=d.asset_id,
                    params={"to_zone": z, "easing": "easeInOutCubic"}
                ))
                counter += 1
                current_zone = z
                last_cam_time = pan_end

        # If final moments exist and duration > 5s, add a gentle wide zoom out
        if total_duration > 6.0 and (total_duration - last_cam_time) > 2.0:
            zoom_start = max(0.0, total_duration - 2.5)
            camera_events.append(CameraItem(
                id=f"cam_{counter:03d}",
                type="camera_zoom_wide",
                start_s=round(zoom_start, 3),
                end_s=round(total_duration, 3),
                duration_s=round(total_duration - zoom_start, 3),
                target_asset_id=None,
                params={"scale": 1.0, "description": "Full scene canvas reveal"}
            ))

        return camera_events

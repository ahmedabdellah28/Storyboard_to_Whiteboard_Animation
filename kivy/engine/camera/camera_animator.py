import numpy as np
from enum import Enum
from typing import List, Tuple, Optional
from ..core.scene import Scene, SceneObject
from ..core.timeline import Timeline, CameraShot
from ..animation.easing import get_easing
from .camera import CameraState


class CameraPreset(Enum):
    SEQUENTIAL_OBJECT_FOCUS = "sequential_object_focus"
    STATIC = "static"
    SLOW_ZOOM = "slow_zoom"
    DYNAMIC = "dynamic"


class CameraAnimator:
    @staticmethod
    def get_state_at_time(
        shots: List[CameraShot],
        current_time: float,
        scene_w: int = 1920,
        scene_h: int = 1080
    ) -> CameraState:
        """
        Director's Camera Interpolator:
        - During FOCUS shots: Returns rock-solid static camera state (ZERO jitter)
        - During TRANSITION shots: Smoothly interpolates pan & zoom between previous and next shot using ease_in_out
        """
        if not shots:
            return CameraState(x=scene_w / 2.0, y=scene_h / 2.0, zoom=1.0)

        # Before first shot
        if current_time <= shots[0].start_time:
            return CameraState(
                x=float(shots[0].target_center[0]),
                y=float(shots[0].target_center[1]),
                zoom=float(shots[0].zoom)
            )

        # After last shot
        if current_time >= shots[-1].end_time:
            return CameraState(
                x=float(shots[-1].target_center[0]),
                y=float(shots[-1].target_center[1]),
                zoom=float(shots[-1].zoom)
            )

        # Find active shot
        for i in range(len(shots)):
            shot = shots[i]
            if shot.start_time <= current_time <= shot.end_time:
                # Check if this shot is an active transition
                is_transition = "TRANSITION" in shot.shot_name or shot.easing != "linear"
                
                if is_transition and i > 0:
                    prev_shot = shots[i - 1]
                    dur = max(1e-4, shot.end_time - shot.start_time)
                    t_norm = max(0.0, min(1.0, (current_time - shot.start_time) / dur))
                    easing_fn = get_easing(shot.easing)
                    t_eased = easing_fn(t_norm)

                    # Smooth interpolation of pan & zoom
                    cx = prev_shot.target_center[0] + t_eased * (shot.target_center[0] - prev_shot.target_center[0])
                    cy = prev_shot.target_center[1] + t_eased * (shot.target_center[1] - prev_shot.target_center[1])
                    zoom = prev_shot.zoom + t_eased * (shot.zoom - prev_shot.zoom)

                    return CameraState(x=float(cx), y=float(cy), zoom=float(zoom))
                else:
                    # Pure static focus shot
                    return CameraState(
                        x=float(shot.target_center[0]),
                        y=float(shot.target_center[1]),
                        zoom=float(shot.zoom)
                    )

        return CameraState(x=scene_w / 2.0, y=scene_h / 2.0, zoom=1.0)

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Any, Optional
from .stroke import Stroke
from .region import ColorRegion


@dataclass
class Keyframe:
    time: float                         # Timestamp in seconds
    value: Any                          # Generic value (float, tuple, ndarray)
    easing: str = "ease_in_out"         # "linear", "ease_in", "ease_out", "ease_in_out"


@dataclass
class CameraShot:
    start_time: float                   # Shot start timestamp (seconds)
    end_time: float                     # Shot end timestamp (seconds)
    target_bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    target_center: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=np.float64))
    zoom: float = 1.0                   # Viewport zoom multiplier
    easing: str = "ease_in_out"
    hold: float = 0.5                   # Rest/hold duration after settling on target
    shot_name: str = "shot"


@dataclass
class Track:
    name: str
    keyframes: List[Keyframe] = field(default_factory=list)


@dataclass
class StrokeEvent:
    start_time: float
    end_time: float
    stroke: Stroke
    easing: str = "ease_in_out"


@dataclass
class FillEvent:
    start_time: float
    end_time: float
    region: ColorRegion
    easing: str = "ease_in_out"


@dataclass
class Timeline:
    duration: float = 0.0
    stroke_events: List[StrokeEvent] = field(default_factory=list)
    fill_events: List[FillEvent] = field(default_factory=list)
    camera_shots: List[CameraShot] = field(default_factory=list)

    def get_active_strokes(self, current_time: float) -> List[Tuple[Stroke, float]]:
        """
        Returns list of (Stroke, progress) for all strokes that have started or completed.
        - If current_time < start_time: not included
        - If start_time <= current_time <= end_time: progress in [0.0, 1.0]
        - If current_time > end_time: progress = 1.0 (fully drawn)
        """
        active = []
        for ev in self.stroke_events:
            if current_time < ev.start_time:
                continue
            elif current_time >= ev.end_time:
                active.append((ev.stroke, 1.0, ev.easing))
            else:
                dur = max(1e-5, ev.end_time - ev.start_time)
                prog = min(1.0, max(0.0, (current_time - ev.start_time) / dur))
                active.append((ev.stroke, prog, ev.easing))
        return active

    def get_active_fills(self, current_time: float) -> List[Tuple[ColorRegion, float]]:
        """
        Returns list of (ColorRegion, progress) for all color fills.
        """
        active = []
        for ev in self.fill_events:
            if current_time < ev.start_time:
                continue
            elif current_time >= ev.end_time:
                active.append((ev.region, 1.0, ev.easing))
            else:
                dur = max(1e-5, ev.end_time - ev.start_time)
                prog = min(1.0, max(0.0, (current_time - ev.start_time) / dur))
                active.append((ev.region, prog, ev.easing))
        return active

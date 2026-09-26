"""Temporal validation, drawing demand feasibility, and completion synchronization."""

from typing import Dict, Any, Optional, Tuple
from ..models.event import TimingStrategy

class TemporalValidator:
    """Calculates and validates surgical start and end timings for visual events."""

    def __init__(
        self,
        audio_duration: float,
        min_duration: float = 0.8,
        max_duration: float = 4.5
    ):
        self.audio_duration = audio_duration
        self.min_duration = min_duration
        self.max_duration = max_duration

    def compute_optimal_timing(
        self,
        anchor_start: float,
        anchor_end: float,
        drawing_demand: float,
        strategy: TimingStrategy = TimingStrategy.COMPLETE_ON_ANCHOR,
        pause_before_s: float = 0.0,
        prev_event_end: float = 0.0
    ) -> Tuple[float, float, float]:
        """Calculates optimal (start_s, end_s, duration_s) based on strategy."""
        clamped_demand = max(self.min_duration, min(self.max_duration, drawing_demand))

        if strategy == TimingStrategy.COMPLETE_ON_ANCHOR:
            # Drawing finishes right as the anchor word completes
            target_end = anchor_end
            target_start = target_end - clamped_demand
            # If target start collides with previous event or is negative, adjust
            if target_start < prev_event_end:
                # Use available gap or slight lead-in
                target_start = max(prev_event_end + 0.05, 0.0)
                # Keep drawing duration as close to demand as possible
                target_end = target_start + clamped_demand
                if target_end > self.audio_duration and self.audio_duration > 0:
                    target_end = self.audio_duration

        elif strategy == TimingStrategy.START_ON_ANCHOR:
            target_start = anchor_start
            target_end = target_start + clamped_demand

        elif strategy == TimingStrategy.CENTER_ON_ANCHOR:
            mid = (anchor_start + anchor_end) / 2.0
            target_start = max(0.0, mid - (clamped_demand / 2.0))
            target_end = target_start + clamped_demand

        elif strategy == TimingStrategy.REVEAL_ON_ANCHOR:
            target_start = anchor_start
            target_end = anchor_start + 0.4
            clamped_demand = 0.4

        elif strategy == TimingStrategy.DURING_PAUSE:
            target_start = max(0.0, anchor_start - pause_before_s)
            target_end = anchor_start
            clamped_demand = target_end - target_start

        elif strategy == TimingStrategy.FOLLOW_EVENT:
            target_start = max(0.0, prev_event_end + 0.05)
            target_end = target_start + clamped_demand

        else:  # Fallback to COMPLETE_ON_ANCHOR
            target_end = anchor_end
            target_start = max(0.0, target_end - clamped_demand)

        # Final bounds safety check
        target_start = max(0.0, round(target_start, 3))
        if self.audio_duration > 0:
            target_end = min(self.audio_duration, round(target_end, 3))
        else:
            target_end = round(target_end, 3)

        if target_end <= target_start:
            target_end = round(target_start + self.min_duration, 3)

        actual_duration = round(target_end - target_start, 3)
        return target_start, target_end, actual_duration

    def evaluate_timing_feasibility(
        self,
        current_start: float,
        current_end: float,
        anchor_start: float,
        anchor_end: float,
        drawing_demand: float
    ) -> Dict[str, Any]:
        """Evaluates whether current event timing is feasible and timely."""
        issues = []
        is_late = False
        duration = current_end - current_start

        # Check if drawing completes too late after the concept was spoken
        if current_end > anchor_end + 1.2:
            is_late = True
            issues.append(f"Drawing completes at {current_end:.2f}s, well after speech anchor ends at {anchor_end:.2f}s.")

        # Check if duration is too rushed
        if duration < self.min_duration:
            issues.append(f"Drawing duration {duration:.2f}s is rushed (minimum {self.min_duration}s).")

        return {
            "feasible": len(issues) == 0,
            "is_late": is_late,
            "issues": issues,
            "current_duration": round(duration, 3)
        }

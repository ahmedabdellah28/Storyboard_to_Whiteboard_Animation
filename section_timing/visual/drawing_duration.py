class DrawingDurationEstimator:
    """Estimates realistic inking and animation durations from drawing demand."""
    def __init__(self, min_duration_s: float = 0.35, max_duration_s: float = 3.20):
        self.min_duration_s = min_duration_s
        self.max_duration_s = max_duration_s

    def estimate(self, demand: float) -> float:
        """
        Maps demand (0.0 to 1.0) into duration in seconds.
        Simple icon/arrow (demand 0.15) -> ~0.45s
        Medium element (demand 0.50) -> ~1.40s
        Complex character/map (demand 0.85) -> ~2.40s
        """
        demand = max(0.0, min(1.0, demand))
        dur = self.min_duration_s + (demand ** 0.85) * (self.max_duration_s - self.min_duration_s)
        return round(dur, 3)

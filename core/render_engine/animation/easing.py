import math
from typing import Callable


def linear(t: float) -> float:
    return float(t)


def ease_in(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    if t < 0.5:
        return 2.0 * t * t
    else:
        return 1.0 - math.pow(-2.0 * t + 2.0, 2) / 2.0


def ease_in_cubic(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * t


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - math.pow(1.0 - t, 3)


def ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    if t < 0.5:
        return 4.0 * t * t * t
    else:
        return 1.0 - math.pow(-2.0 * t + 2.0, 3) / 2.0


def get_easing(name: str) -> Callable[[float], float]:
    """Returns the easing function by name. Defaults to ease_in_out."""
    mapping = {
        "linear": linear,
        "ease_in": ease_in,
        "ease_out": ease_out,
        "ease_in_out": ease_in_out,
        "ease_in_cubic": ease_in_cubic,
        "ease_out_cubic": ease_out_cubic,
        "ease_in_out_cubic": ease_in_out_cubic,
    }
    return mapping.get(str(name).lower(), ease_in_out)

from typing import List
from ..timeline.models import WordItem, PauseItem

class PauseDetector:
    """Detects inter-word pauses and classifies them into rhythmic resource tiers."""
    def __init__(self, min_pause_s: float = 0.12):
        self.min_pause_s = min_pause_s

    def detect_pauses(self, words: List[WordItem]) -> List[PauseItem]:
        """Detects gaps between consecutive words."""
        pauses: List[PauseItem] = []
        counter = 1

        for i in range(len(words) - 1):
            curr_w = words[i]
            next_w = words[i + 1]

            gap = next_w.start - curr_w.end
            if gap >= self.min_pause_s:
                if gap < 0.25:
                    p_type = "micro_pause"
                elif gap < 0.50:
                    p_type = "short_pause"
                elif gap < 0.95:
                    p_type = "medium_pause"
                else:
                    p_type = "long_pause"

                pauses.append(PauseItem(
                    id=f"p{counter:03d}",
                    start=round(curr_w.end, 3),
                    end=round(next_w.start, 3),
                    duration=round(gap, 3),
                    type=p_type
                ))
                counter += 1

        return pauses

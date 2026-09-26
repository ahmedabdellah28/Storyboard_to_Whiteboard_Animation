from typing import List, Dict, Any, Tuple
from ..models.chunk import ChunkMetadata
from ..utils.logging import log

class ConsistencyManager:
    """Monitors pacing, speech rate (WPM), and energy continuity across chunks within a section."""
    def __init__(self, max_wpm_variance_ratio: float = 0.28, max_rms_variance_ratio: float = 0.45):
        self.max_wpm_variance_ratio = max_wpm_variance_ratio
        self.max_rms_variance_ratio = max_rms_variance_ratio

    def evaluate_consistency(self, chunks: List[ChunkMetadata]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Evaluates inter-chunk pacing and energy continuity.
        Returns: (is_consistent, issues_list, summary_metrics)
        """
        if len(chunks) <= 1:
            return True, [], {"status": "single_chunk"}

        wpms = [c.estimated_wpm for c in chunks if c.estimated_wpm > 0]
        rmss = [c.rms for c in chunks if c.rms > 0]

        issues: List[str] = []
        avg_wpm = sum(wpms) / len(wpms) if wpms else 0.0
        avg_rms = sum(rmss) / len(rmss) if rmss else 0.0

        for chunk in chunks:
            # Check WPM deviation
            if avg_wpm > 0 and chunk.estimated_wpm > 0:
                dev = abs(chunk.estimated_wpm - avg_wpm) / avg_wpm
                if dev > self.max_wpm_variance_ratio:
                    issue = f"PACING_INCONSISTENCY: Chunk {chunk.id} WPM ({chunk.estimated_wpm:.1f}) deviates by {dev*100:.1f}% from section average ({avg_wpm:.1f})"
                    issues.append(issue)
                    log.consistency(issue)

            # Check RMS deviation
            if avg_rms > 0 and chunk.rms > 0:
                rms_dev = abs(chunk.rms - avg_rms) / avg_rms
                if rms_dev > self.max_rms_variance_ratio:
                    issue = f"LOUDNESS_INCONSISTENCY: Chunk {chunk.id} RMS ({chunk.rms:.3f}) deviates from section average ({avg_rms:.3f})"
                    issues.append(issue)
                    log.consistency(issue)

        summary = {
            "average_wpm": round(avg_wpm, 1),
            "average_rms": round(avg_rms, 4),
            "chunk_wpms": [round(w, 1) for w in wpms],
            "issues": issues,
            "is_consistent": len(issues) == 0
        }

        return len(issues) == 0, issues, summary

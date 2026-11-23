"""
Beat Timeline Visualizer & Decision Log Exporter (ASATE Diagnostics V2)
Produces multi-track ASCII timeline charts, conflict reports, and JSON decision logs
for Content-Aware Timing verification.
"""
import json
from typing import List, Dict, Any, Optional
from .visual_beat import VisualBeat
from .speech_beat import SpeechBeat


class BeatTimelineVisualizer:
    """
    Diagnostic tool to inspect and verify Visual Beat synchronization,
    element overlaps, anticipation, hold times, feasibility, and conflicts across the timeline.
    """

    @classmethod
    def render_ascii_timeline(
        cls,
        visual_beats: List[VisualBeat],
        speech_beats: Optional[List[SpeechBeat]] = None,
        total_duration: Optional[float] = None,
        track_width: int = 80
    ) -> str:
        """
        Renders a multi-track ASCII representation of:
        - Audio / Global Time
        - Speech Beats
        - Visual Beats (Drawing & Hold Windows)
        - Primary Elements
        - Secondary Elements
        - Hold Periods
        - Timing Conflicts (if detected)
        """
        if not visual_beats:
            return "No Visual Beats available for timeline visualization."

        max_time = total_duration or max(b.end for b in visual_beats)
        time_scale = track_width / max(1.0, max_time)

        def time_to_col(t: float) -> int:
            return max(0, min(track_width - 1, int(round(t * time_scale))))

        lines = []
        lines.append("=" * (track_width + 20))
        lines.append(f"  [TIMELINE] VISUAL BEAT ASATE TIMELINE DIAGNOSTIC (Total: {max_time:.1f}s)")
        lines.append("=" * (track_width + 20))

        # 1. Time Axis
        time_axis = list(" " * track_width)
        step = max(5, int(round(max_time / 8.0)))
        for t in range(0, int(max_time) + 1, step):
            col = time_to_col(t)
            lbl = f"{t}s"
            for k, ch in enumerate(lbl):
                if col + k < track_width:
                    time_axis[col + k] = ch
        lines.append(f"{'TIME':<14} | {''.join(time_axis)} |")

        # 2. Speech Beats Track
        if speech_beats:
            speech_track = list(" " * track_width)
            for sb in speech_beats:
                c1 = time_to_col(sb.start)
                c2 = time_to_col(sb.end)
                for c in range(c1, c2):
                    speech_track[c] = "━"
                if c1 < track_width:
                    speech_track[c1] = "["
                if c2 - 1 < track_width and c2 > c1:
                    speech_track[c2 - 1] = "]"
            lines.append(f"{'SPEECH BEATS':<14} | {''.join(speech_track)} |")

        # 3. Visual Beats Drawing Track
        draw_track = list(" " * track_width)
        for b in visual_beats:
            c1 = time_to_col(b.drawing_window[0] if b.drawing_window[0] > 0 else b.start)
            c2 = time_to_col(b.drawing_window[1] if b.drawing_window[1] > 0 else b.end)
            for c in range(c1, c2):
                draw_track[c] = "█"
            if c1 < track_width:
                draw_track[c1] = "║"
        lines.append(f"{'VISUAL DRAW':<14} | {''.join(draw_track)} |")

        # 4. Primary Elements Track
        pri_track = list(" " * track_width)
        for b in visual_beats:
            for d in b.timing_decisions:
                if d.tier == "PRIMARY":
                    c1 = time_to_col(d.start)
                    c2 = time_to_col(d.end)
                    for c in range(c1, c2):
                        pri_track[c] = "▓"
        lines.append(f"{'PRIMARY (DRAW)':<14} | {''.join(pri_track)} |")

        # 5. Secondary Elements Track
        sec_track = list(" " * track_width)
        for b in visual_beats:
            for d in b.timing_decisions:
                if d.tier == "SECONDARY":
                    c1 = time_to_col(d.start)
                    c2 = time_to_col(d.end)
                    for c in range(c1, c2):
                        sec_track[c] = "▒"
        lines.append(f"{'SECONDARY':<14} | {''.join(sec_track)} |")

        # 6. Hold Periods Track
        hold_track = list(" " * track_width)
        for b in visual_beats:
            for d in b.timing_decisions:
                if d.hold_duration > 0:
                    c1 = time_to_col(d.end)
                    c2 = time_to_col(d.end + d.hold_duration)
                    for c in range(c1, c2):
                        hold_track[c] = "░"
        lines.append(f"{'HOLD PERIODS':<14} | {''.join(hold_track)} |")
        lines.append("-" * (track_width + 20))

        # 7. Check and display any Timing Conflicts
        all_conflicts = []
        for b in visual_beats:
            for c in b.timing_conflicts:
                all_conflicts.append((b.id, c))

        if all_conflicts:
            lines.append("  [!] DETECTED TIMING CONFLICTS & RESOLUTIONS:")
            for b_id, c in all_conflicts:
                lines.append(f"     [{c.severity.value}] {b_id} -> {c.conflict_type.value}: {c.description}")
                lines.append(f"          -> Resolution Attempted: {c.resolution_attempted}")
            lines.append("-" * (track_width + 20))

        return "\n".join(lines)

    @classmethod
    def export_timing_decisions_json(
        cls,
        visual_beats: List[VisualBeat],
        output_path: Optional[str] = None
    ) -> str:
        """
        Exports structured timing decisions explaining the exact rationale
        for start, end, duration, hold, feasibility, and conflicts across all beats.
        """
        report: Dict[str, Any] = {
            "total_beats": len(visual_beats),
            "beats": []
        }

        for b in visual_beats:
            b_info = {
                "beat_id": b.id,
                "speech_beat_id": b.speech_beat_id,
                "start": round(b.start, 2),
                "end": round(b.end, 2),
                "duration": round(b.duration, 2),
                "speech_window": [round(b.speech_window[0], 2), round(b.speech_window[1], 2)],
                "drawing_window": [round(b.drawing_window[0], 2), round(b.drawing_window[1], 2)],
                "hold_window": [round(b.hold_window[0], 2), round(b.hold_window[1], 2)],
                "overlap_policy": b.overlap_policy.value,
                "hold_duration": round(b.hold_duration, 2),
                "transition_policy": b.transition_policy.value,
                "primary_elements": b.primary_elements,
                "secondary_elements": b.secondary_elements,
                "decorative_elements": b.decorative_elements,
                "timing_conflicts": [c.to_dict() for c in b.timing_conflicts],
                "timing_decisions": [d.to_dict() for d in b.timing_decisions]
            }
            report["beats"].append(b_info)

        formatted_json = json.dumps(report, indent=2, ensure_ascii=False)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(formatted_json)

        return formatted_json

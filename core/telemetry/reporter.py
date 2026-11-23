"""Telemetry summary reporter for pipeline runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.telemetry.counters import get_telemetry_counters
from core.telemetry.timer import get_timer_registry


class TelemetryReporter:
    """Compiles and formats execution metrics into clear console and file reports."""

    def __init__(self, timer_registry=None, counters=None) -> None:
        self.timer_registry = timer_registry or get_timer_registry()
        self.counters = counters or get_telemetry_counters()

    def get_full_report_data(self) -> Dict[str, Any]:
        records = self.timer_registry.get_records()
        category_summary = self.timer_registry.get_summary_by_category()
        counters_snapshot = self.counters.get_snapshot()

        total_tracked_duration = sum(r.duration for r in records)

        stage_records = []
        for r in records:
            stage_records.append({
                "name": r.name,
                "category": r.category,
                "duration_seconds": round(r.duration, 2),
                "status": r.status,
                "error": r.error,
                "metadata": r.metadata,
            })

        return {
            "total_tracked_duration_seconds": round(total_tracked_duration, 2),
            "stages": stage_records,
            "category_summary": {
                k: {
                    "count": v["count"],
                    "total_duration_seconds": round(v["total_duration"], 2),
                    "success": v["success"],
                    "failed": v["failed"],
                }
                for k, v in category_summary.items()
            },
            "counters": counters_snapshot,
        }

    def format_ascii_table(self, title: str = "Pipeline Run Telemetry Summary") -> str:
        data = self.get_full_report_data()
        lines: List[str] = []

        width = 65
        lines.append("┌" + "─" * width + "┐")
        lines.append(f"│ {title.center(width - 2)} │")
        lines.append("├" + "─" * 26 + "┬" + "─" * 12 + "┬" + "─" * 11 + "┬" + "─" * 12 + "┤")
        lines.append(f"│ {'Stage / Task':<24} │ {'Duration':<10} │ {'Status':<9} │ {'Category':<10} │")
        lines.append("├" + "─" * 26 + "┼" + "─" * 12 + "┼" + "─" * 11 + "┼" + "─" * 12 + "┤")

        for s in data["stages"]:
            name = s["name"]
            if len(name) > 24:
                name = name[:21] + "..."
            dur = f"{s['duration_seconds']:.2f}s"
            status = s["status"]
            cat = s["category"][:10]
            lines.append(f"│ {name:<24} │ {dur:<10} │ {status:<9} │ {cat:<10} │")

        lines.append("├" + "─" * 26 + "┴" + "─" * 12 + "┴" + "─" * 11 + "┴" + "─" * 12 + "┤")
        tot_dur = f"{data['total_tracked_duration_seconds']:.2f}s"
        lines.append(f"│ Total Tracked Duration: {tot_dur:<39} │")

        totals = data["counters"]["totals"]
        lines.append("├" + "─" * width + "┤")
        lines.append(f"│ Metrics: API Calls={totals['api_calls']} | Failures={totals['api_failures']} | Retries={totals['retries']} | 429s={totals['rate_limits']:<7} │")
        lines.append(f"│ Cache:   Hits={totals['cache_hits']} | Misses={totals['cache_misses']} | Hit Rate={totals['cache_hit_rate_pct']}%{'':<22} │")
        lines.append("└" + "─" * width + "┘")

        return "\n".join(lines)

    def print_summary(self, title: str = "Pipeline Run Telemetry Summary") -> None:
        table = self.format_ascii_table(title)
        print(table, flush=True)

    def save_summary_json(self, file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.get_full_report_data()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def print_pipeline_summary(title: str = "Pipeline Run Summary") -> None:
    reporter = TelemetryReporter()
    reporter.print_summary(title)

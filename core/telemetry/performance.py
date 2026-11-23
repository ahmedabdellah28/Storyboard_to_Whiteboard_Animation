"""Performance Hardening Utilities.

Provides lazy import infrastructure and startup profiling to ensure
sub-1s cold startup for the Studio application shell.
"""

from __future__ import annotations

import importlib
import time
from typing import Any, Dict, List, Optional, Tuple


class LazyModule:
    """Deferred module loader that delays import until first attribute access.
    
    Usage:
        cv2 = LazyModule("cv2")
        np = LazyModule("numpy")
        # Module is NOT loaded until first access:
        result = cv2.VideoCapture(...)  # Import happens here
    """

    def __init__(self, module_name: str) -> None:
        self._module_name = module_name
        self._module: Optional[Any] = None

    def _load(self) -> Any:
        if self._module is None:
            self._module = importlib.import_module(self._module_name)
        return self._module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._load(), name)

    def __repr__(self) -> str:
        loaded = self._module is not None
        return f"<LazyModule '{self._module_name}' loaded={loaded}>"


class StartupProfiler:
    """Lightweight startup time profiler for measuring cold-start performance.
    
    Usage:
        profiler = StartupProfiler()
        profiler.mark("qt_import")
        import PyQt6
        profiler.mark("qt_imported")
        profiler.mark("state_store_init")
        store = StateStore()
        profiler.mark("state_store_ready")
        report = profiler.report()
    """

    def __init__(self) -> None:
        self._marks: List[Tuple[str, float]] = []
        self._start = time.perf_counter()
        self._marks.append(("__profiler_start__", self._start))

    def mark(self, label: str) -> float:
        """Record a named timestamp checkpoint. Returns elapsed seconds from start."""
        now = time.perf_counter()
        self._marks.append((label, now))
        return now - self._start

    def elapsed(self) -> float:
        """Total elapsed seconds since profiler creation."""
        return time.perf_counter() - self._start

    def report(self) -> Dict[str, Any]:
        """Generate a structured report of all marks and phase durations."""
        total = time.perf_counter() - self._start
        phases: List[Dict[str, Any]] = []

        for i in range(1, len(self._marks)):
            prev_label, prev_t = self._marks[i - 1]
            cur_label, cur_t = self._marks[i]
            phase_dur = cur_t - prev_t
            phases.append({
                "phase": f"{prev_label} → {cur_label}",
                "duration_ms": round(phase_dur * 1000, 2),
            })

        return {
            "total_elapsed_ms": round(total * 1000, 2),
            "mark_count": len(self._marks) - 1,
            "phases": phases,
            "marks": {label: round((t - self._start) * 1000, 2) for label, t in self._marks},
        }

    def summary(self) -> str:
        """Human-readable summary string."""
        r = self.report()
        lines = [f"Startup Profile ({r['total_elapsed_ms']:.1f}ms total):"]
        for ph in r["phases"]:
            lines.append(f"  {ph['phase']}: {ph['duration_ms']:.1f}ms")
        return "\n".join(lines)


class PerformanceBudget:
    """Performance budget checker with pass/fail thresholds.
    
    Usage:
        budget = PerformanceBudget()
        budget.add("cold_startup", max_ms=1000)
        budget.add("project_load", max_ms=200)
        budget.record("cold_startup", 850.0)
        budget.record("project_load", 120.0)
        results = budget.evaluate()
    """

    def __init__(self) -> None:
        self._budgets: Dict[str, float] = {}
        self._recorded: Dict[str, float] = {}

    def add(self, metric_name: str, max_ms: float) -> None:
        """Define a performance budget for a named metric."""
        self._budgets[metric_name] = max_ms

    def record(self, metric_name: str, elapsed_ms: float) -> None:
        """Record the actual measured time for a metric."""
        self._recorded[metric_name] = elapsed_ms

    def evaluate(self) -> Dict[str, Any]:
        """Evaluate all budgets and return pass/fail results."""
        results: List[Dict[str, Any]] = []
        all_pass = True
        for name, budget_ms in self._budgets.items():
            actual_ms = self._recorded.get(name, -1.0)
            passed = 0 < actual_ms <= budget_ms
            if not passed:
                all_pass = False
            results.append({
                "metric": name,
                "budget_ms": budget_ms,
                "actual_ms": round(actual_ms, 2),
                "passed": passed,
                "headroom_pct": round(((budget_ms - actual_ms) / budget_ms) * 100, 1) if actual_ms > 0 else -100.0,
            })
        return {
            "overall_pass": all_pass,
            "results": results,
        }

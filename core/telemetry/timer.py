"""Task timing utilities for observability and performance telemetry."""

from __future__ import annotations

import functools
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TimingRecord:
    name: str
    category: str = "general"
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    status: str = "PENDING"  # PENDING, SUCCESS, FAILED
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TimerRegistry:
    """Thread-safe registry for collecting timing records."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: List[TimingRecord] = []

    def record(self, timing: TimingRecord) -> None:
        with self._lock:
            self._records.append(timing)

    def get_records(self, category: Optional[str] = None) -> List[TimingRecord]:
        with self._lock:
            if category is None:
                return list(self._records)
            return [r for r in self._records if r.category == category]

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    def get_summary_by_category(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            summary: Dict[str, Dict[str, Any]] = {}
            for r in self._records:
                cat = r.category
                if cat not in summary:
                    summary[cat] = {"count": 0, "total_duration": 0.0, "success": 0, "failed": 0}
                summary[cat]["count"] += 1
                summary[cat]["total_duration"] += r.duration
                if r.status == "SUCCESS":
                    summary[cat]["success"] += 1
                elif r.status == "FAILED":
                    summary[cat]["failed"] += 1
            return summary


_GLOBAL_TIMER_REGISTRY = TimerRegistry()


def get_timer_registry() -> TimerRegistry:
    return _GLOBAL_TIMER_REGISTRY


class TaskTimer:
    """Context manager for timing code execution and collecting telemetry.

    Usage:
        with TaskTimer("tts_chunk_01", category="tts") as timer:
            # do work
            timer.set_metadata("words", 45)
    """

    def __init__(
        self,
        name: str,
        category: str = "general",
        registry: Optional[TimerRegistry] = None,
        auto_record: bool = True,
        log_level: Optional[int] = None,
    ) -> None:
        self.name = name
        self.category = category
        self.registry = registry or get_timer_registry()
        self.auto_record = auto_record
        self.log_level = log_level
        self.record = TimingRecord(name=name, category=category)
        self._start_perf: float = 0.0

    def __enter__(self) -> TaskTimer:
        self.record.start_time = time.time()
        self._start_perf = time.perf_counter()
        self.record.status = "RUNNING"
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        elapsed = time.perf_counter() - self._start_perf
        self.record.end_time = time.time()
        self.record.duration = elapsed

        if exc_type is not None:
            self.record.status = "FAILED"
            self.record.error = str(exc_val)
            if self.log_level is not None:
                logger.log(self.log_level, "Task %s failed after %.3fs: %s", self.name, elapsed, exc_val)
        else:
            self.record.status = "SUCCESS"
            if self.log_level is not None:
                logger.log(self.log_level, "Task %s completed in %.3fs", self.name, elapsed)

        if self.auto_record and self.registry is not None:
            self.registry.record(self.record)

        return False  # Do not suppress exceptions

    def set_metadata(self, key: str, value: Any) -> None:
        self.record.metadata[key] = value

    @property
    def duration(self) -> float:
        return self.record.duration


def time_task(name: Optional[str] = None, category: str = "general") -> Callable:
    """Decorator to measure execution time of functions.

    Usage:
        @time_task("render_frame", category="render")
        def render_frame(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        task_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with TaskTimer(name=task_name, category=category):
                return func(*args, **kwargs)

        return wrapper

    return decorator

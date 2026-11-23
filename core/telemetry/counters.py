"""Thread-safe telemetry counters for API calls, caching, retries, and data throughput."""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict


class TelemetryCounters:
    """Thread-safe metrics aggregator."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._api_calls: Dict[str, int] = defaultdict(int)
        self._api_failures: Dict[str, int] = defaultdict(int)
        self._retries: Dict[str, int] = defaultdict(int)
        self._rate_limits: Dict[str, int] = defaultdict(int)
        self._cache_hits: Dict[str, int] = defaultdict(int)
        self._cache_misses: Dict[str, int] = defaultdict(int)
        self._bytes_generated: Dict[str, int] = defaultdict(int)
        self._custom_counters: Dict[str, int] = defaultdict(int)

    def inc_api_call(self, provider: str = "gemini", model: str = "default") -> None:
        key = f"{provider}:{model}"
        with self._lock:
            self._api_calls[key] += 1

    def inc_api_failure(self, provider: str = "gemini", error_type: str = "unknown") -> None:
        key = f"{provider}:{error_type}"
        with self._lock:
            self._api_failures[key] += 1

    def inc_retry(self, provider: str = "gemini", reason: str = "rate_limit") -> None:
        key = f"{provider}:{reason}"
        with self._lock:
            self._retries[key] += 1

    def inc_rate_limit(self, provider: str = "gemini", key_id: str = "default") -> None:
        k = f"{provider}:{key_id}"
        with self._lock:
            self._rate_limits[k] += 1

    def record_cache_hit(self, component: str) -> None:
        with self._lock:
            self._cache_hits[component] += 1

    def record_cache_miss(self, component: str) -> None:
        with self._lock:
            self._cache_misses[component] += 1

    def inc_bytes_generated(self, data_type: str, count: int) -> None:
        with self._lock:
            self._bytes_generated[data_type] += count

    def inc_counter(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._custom_counters[name] += value

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            total_api_calls = sum(self._api_calls.values())
            total_api_failures = sum(self._api_failures.values())
            total_retries = sum(self._retries.values())
            total_rate_limits = sum(self._rate_limits.values())
            total_cache_hits = sum(self._cache_hits.values())
            total_cache_misses = sum(self._cache_misses.values())
            total_cache_requests = total_cache_hits + total_cache_misses
            cache_hit_rate = (
                (total_cache_hits / total_cache_requests * 100.0)
                if total_cache_requests > 0
                else 0.0
            )

            return {
                "totals": {
                    "api_calls": total_api_calls,
                    "api_failures": total_api_failures,
                    "retries": total_retries,
                    "rate_limits": total_rate_limits,
                    "cache_hits": total_cache_hits,
                    "cache_misses": total_cache_misses,
                    "cache_hit_rate_pct": round(cache_hit_rate, 1),
                },
                "api_calls_by_model": dict(self._api_calls),
                "api_failures_by_type": dict(self._api_failures),
                "retries_by_reason": dict(self._retries),
                "rate_limits_by_key": dict(self._rate_limits),
                "cache_hits_by_component": dict(self._cache_hits),
                "cache_misses_by_component": dict(self._cache_misses),
                "bytes_generated": dict(self._bytes_generated),
                "custom_counters": dict(self._custom_counters),
            }

    def reset(self) -> None:
        with self._lock:
            self._api_calls.clear()
            self._api_failures.clear()
            self._retries.clear()
            self._rate_limits.clear()
            self._cache_hits.clear()
            self._cache_misses.clear()
            self._bytes_generated.clear()
            self._custom_counters.clear()


_GLOBAL_COUNTERS = TelemetryCounters()


def get_telemetry_counters() -> TelemetryCounters:
    return _GLOBAL_COUNTERS

"""Tests for Core Foundation (Phase 0 & Phase 1)."""

import io
import os
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from core.config.settings import PROJECT_ROOT, DEFAULT_SAMPLE_RATE
from core.config.env_loader import EnvLoader, get_gemini_api_keys, load_project_env
from core.telemetry.timer import TaskTimer, TimerRegistry
from core.telemetry.counters import TelemetryCounters
from core.telemetry.reporter import TelemetryReporter
from core.audio.wav_utils import pcm_to_wav, get_wav_duration, stitch_wav_files, generate_silence_wav
from core.api.rate_limiter import TokenBucketRateLimiter
from core.api.key_pool import APIKeyPool, KeyStatus


def test_project_root_detection():
    assert PROJECT_ROOT.exists()
    assert (PROJECT_ROOT / ".env").exists()


def test_env_loader_finds_keys():
    keys = get_gemini_api_keys()
    assert len(keys) >= 4
    # Ensure no empty or placeholder strings
    for k in keys:
        assert len(k) > 10
        assert "placeholder" not in k.lower()


def test_telemetry_timer_and_registry():
    registry = TimerRegistry()
    with TaskTimer("test_step", category="unit_test", registry=registry) as timer:
        time.sleep(0.05)
        timer.set_metadata("items", 3)

    records = registry.get_records("unit_test")
    assert len(records) == 1
    rec = records[0]
    assert rec.name == "test_step"
    assert rec.duration >= 0.04
    assert rec.status == "SUCCESS"
    assert rec.metadata.get("items") == 3


def test_telemetry_counters():
    counters = TelemetryCounters()
    counters.inc_api_call("gemini", "gemini-2.5-flash")
    counters.inc_api_call("gemini", "gemini-2.5-flash")
    counters.inc_retry("gemini", "429")
    counters.record_cache_hit("tts")
    counters.record_cache_miss("tts")

    snap = counters.get_snapshot()
    assert snap["totals"]["api_calls"] == 2
    assert snap["totals"]["retries"] == 1
    assert snap["totals"]["cache_hits"] == 1
    assert snap["totals"]["cache_misses"] == 1
    assert snap["totals"]["cache_hit_rate_pct"] == 50.0


def test_telemetry_reporter():
    registry = TimerRegistry()
    counters = TelemetryCounters()
    with TaskTimer("stage_1", category="pipeline", registry=registry):
        pass
    counters.inc_api_call("gemini", "test_model")

    reporter = TelemetryReporter(timer_registry=registry, counters=counters)
    table = reporter.format_ascii_table("Test Run")
    assert "Test Run" in table
    assert "stage_1" in table
    assert "API Calls=1" in table


def test_pcm_to_wav_and_duration():
    # 0.1 second of 24000Hz 16-bit mono silence (2400 samples * 2 bytes = 4800 bytes)
    sample_rate = 24000
    pcm_bytes = b"\x00" * (sample_rate * 2 // 10)
    wav_bytes = pcm_to_wav(pcm_bytes, sample_rate=sample_rate)

    assert len(wav_bytes) == 44 + len(pcm_bytes)
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tf.write(wav_bytes)
        tf_path = tf.name

    try:
        dur = get_wav_duration(tf_path)
        assert abs(dur - 0.1) < 0.01
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)


def test_stitch_wav_files():
    sample_rate = 24000
    # Create two 0.05s chunks (1200 samples * 2 bytes = 2400 bytes each)
    chunk1_pcm = b"\x10\x00" * 1200
    chunk2_pcm = b"\x20\x00" * 1200
    wav1 = pcm_to_wav(chunk1_pcm, sample_rate=sample_rate)
    wav2 = pcm_to_wav(chunk2_pcm, sample_rate=sample_rate)

    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "chunk1.wav"
        p2 = Path(td) / "chunk2.wav"
        p1.write_bytes(wav1)
        p2.write_bytes(wav2)

        out = Path(td) / "stitched.wav"
        stitch_wav_files([p1, p2], out, silence_ms=50)

        assert out.exists()
        dur = get_wav_duration(out)
        # Expected: 0.05s + 0.05s (silence) + 0.05s = 0.15s
        assert abs(dur - 0.15) < 0.02


def test_token_bucket_rate_limiter():
    limiter = TokenBucketRateLimiter(rpm=60, burst_capacity=2)
    assert limiter.acquire(tokens=1, timeout=0.1) is True
    assert limiter.acquire(tokens=1, timeout=0.1) is True
    # Next immediate acquire should either wait or return False if timeout very short
    assert limiter.acquire(tokens=1, timeout=0.01) is False


def test_api_key_pool():
    test_keys = ["KEY_ALPHA_12345678", "KEY_BETA_12345678", "KEY_GAMMA_12345678"]
    pool = APIKeyPool(keys=test_keys)
    assert len(pool) == 3

    # Least loaded test
    k1 = pool.get_best_key()
    assert k1.total_calls == 1
    k2 = pool.get_best_key()
    assert k2.total_calls == 1
    assert k1.index != k2.index

    # 429 mark
    pool.handle_429(k1, "retryDelay: 2s", default_cooldown=2)
    assert k1.status == KeyStatus.RATE_LIMITED


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tests = [
        test_project_root_detection,
        test_env_loader_finds_keys,
        test_telemetry_timer_and_registry,
        test_telemetry_counters,
        test_telemetry_reporter,
        test_pcm_to_wav_and_duration,
        test_stitch_wav_files,
        test_token_bucket_rate_limiter,
        test_api_key_pool,
    ]
    print(f"Running {len(tests)} Core Foundation tests...")
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nResult: {passed}/{len(tests)} tests passed.")
    if passed == len(tests):
        print("ALL CORE FOUNDATION TESTS PASSED SUCCESSFULLY!")
    else:
        sys.exit(1)

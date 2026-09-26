"""
Unit Tests for Gemini GenAI TTS Engine
"""
import os
import sys
import struct
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.audio.tts_engine import (
    GeminiTTSEngine,
    parse_audio_mime_type,
    convert_raw_pcm_to_wav,
    AUDIO_PROFILES,
    DIRECTOR_NOTES
)


def test_parse_audio_mime_type():
    res = parse_audio_mime_type("audio/L16;rate=24000")
    assert res["rate"] == 24000
    assert res["bits_per_sample"] == 16

    res2 = parse_audio_mime_type("audio/L24;rate=48000")
    assert res2["rate"] == 48000
    assert res2["bits_per_sample"] == 24


def test_convert_raw_pcm_to_wav():
    dummy_pcm = b"\x00\x00" * 12000  # 12000 samples @ 16-bit = 0.5s @ 24kHz
    wav_bytes = convert_raw_pcm_to_wav(dummy_pcm, "audio/L16;rate=24000")

    assert wav_bytes.startswith(b"RIFF")
    assert b"WAVE" in wav_bytes[:12]
    assert b"fmt " in wav_bytes[:20]
    assert b"data" in wav_bytes[36:44]
    assert len(wav_bytes) == len(dummy_pcm) + 44


def test_build_prompt():
    engine = GeminiTTSEngine(api_key="mock_key")
    prompt = engine.build_prompt(
        transcript="مرحبا بكم",
        profile=AUDIO_PROFILES["SAUDI_YOUTH_CREATOR"],
        director_note=DIRECTOR_NOTES["HIGH_ENERGY_YOUTUBE"]
    )
    assert "Young Saudi male YouTube creator" in prompt
    assert "High energy" in prompt
    assert "مرحبا بكم" in prompt


def test_missing_api_key_raises_error():
    engine = GeminiTTSEngine(api_key=None)
    # Ensure env is clear for test
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
    engine.api_key = None

    with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
        engine.generate_speech("نص تجريبي", "dummy.wav")

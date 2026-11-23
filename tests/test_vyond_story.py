"""
Unit Tests for Voice Studio Vyond-Style Dramatic Story Section.
"""
import json
import os
import struct
import sys
import wave
from types import SimpleNamespace

import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.profiles import AUDIO_PROFILES, DIRECTOR_NOTES
from voice_studio.vyond_story import (
    BASE_DIRECTOR_PROMPT,
    DEFAULT_FEMALE_VOICE,
    DEFAULT_VYOND_MODEL,
    VyondStoryEngine,
    clean_pcm_audio,
    normalize_pcm,
    parse_story_script,
    split_into_safe_chunks,
)


def _make_pcm_tone(num_samples: int, amplitude: int = 8000) -> bytes:
    samples = [amplitude if i % 2 == 0 else -amplitude for i in range(num_samples)]
    return struct.pack(f"<{num_samples}h", *samples)


def test_profiles_registered():
    assert "EGYPTIAN_VYOND_STORYTELLER" in AUDIO_PROFILES
    assert "VYOND_DRAMATIC_STORY" in DIRECTOR_NOTES


def test_split_into_safe_chunks():
    short = "جملة قصيرة."
    assert split_into_safe_chunks(short, max_chars=500) == [short]

    s1 = "أول جملة طويلة شوية عشان نجرب التقسيم."
    s2 = "تاني جملة بتيجي بعدها على طول."
    s3 = "تالت جملة في النهاية؟"
    combined = f"{s1}   {s2}\n{s3}"
    chunks = split_into_safe_chunks(combined, max_chars=len(s1) + len(s2) + 2)
    assert len(chunks) == 2
    assert chunks[0] == f"{s1} {s2}"
    assert chunks[1] == s3


def test_clean_pcm_audio_trims_silence_and_normalizes():
    silence = b"\x00\x00" * 2400  # 100ms @ 24kHz
    tone = _make_pcm_tone(2400, amplitude=4000)
    raw = silence + tone + silence

    cleaned = clean_pcm_audio(raw, sample_rate=24000, silence_thresh_db=-42.0, headroom_db=2.0)
    assert len(cleaned) == len(tone)

    samples = struct.unpack(f"<{len(cleaned) // 2}h", cleaned)
    expected_peak = int(round(32767.0 * (10.0 ** (-2.0 / 20.0))))
    assert abs(max(abs(s) for s in samples) - expected_peak) <= 2


def test_normalize_pcm_handles_zero_signal():
    zeros = b"\x00\x00" * 100
    assert normalize_pcm(zeros) == zeros


def test_parse_story_script_json_and_tagged_text():
    json_payload = json.dumps(
        [
            {"emotion": "تشويق", "text": "في ليلة هادية...", "scene_break": False},
            {"emotion": "صدمة", "text": "سمعنا صوت غريب!", "scene_break": True},
        ],
        ensure_ascii=False,
    )
    parsed_json = parse_story_script(json_payload)
    assert len(parsed_json) == 2
    assert parsed_json[0]["emotion"] == "تشويق"
    assert parsed_json[1]["scene_break"] is True

    tagged = (
        "[المشاعر: حماس]\n"
        "بدأت الحكاية من هنا.\n"
        "---\n"
        "[المشاعر: خوف | scene_break]\n"
        "وفجأة النور قطع!"
    )
    parsed_text = parse_story_script(tagged)
    assert len(parsed_text) == 2
    assert parsed_text[0] == {"emotion": "حماس", "text": "بدأت الحكاية من هنا.", "scene_break": False}
    assert parsed_text[1] == {"emotion": "خوف", "text": "وفجأة النور قطع!", "scene_break": True}


def test_render_full_story_wav_and_mp3_with_mock_client(tmp_path):
    tone_pcm = _make_pcm_tone(2400, amplitude=6000)  # 0.1s @ 24kHz
    recorded_calls = []

    class FakeModels:
        def generate_content(self, model, contents, config):
            recorded_calls.append({"model": model, "contents": contents, "config": config})
            part = SimpleNamespace(inline_data=SimpleNamespace(data=tone_pcm))
            candidate = SimpleNamespace(content=SimpleNamespace(parts=[part]))
            return SimpleNamespace(candidates=[candidate])

    fake_client = SimpleNamespace(models=FakeModels())

    engine = VyondStoryEngine(
        api_key="test_key_123",
        model=DEFAULT_VYOND_MODEL,
        voice_name=DEFAULT_FEMALE_VOICE,
    )

    chunks = [
        {"emotion": "تشويق وغموض", "text": "اسمع الحكاية دي.", "scene_break": False},
        {"emotion": "صدمة", "text": "محدش صدق اللي حصل!", "scene_break": True},
    ]

    wav_out = tmp_path / "story.wav"
    res_wav = engine.render_full_story(
        story_chunks=chunks,
        output_file=str(wav_out),
        micro_pause_ms=180,
        scene_pause_ms=450,
        delay_between_chunks=0.0,
        speed=1.0,
        clean_mic=False,
        resume=False,
        client=fake_client,
    )

    assert res_wav["status"] == "SUCCESS"
    assert wav_out.exists()
    assert len(recorded_calls) == 2
    assert "emotion: تشويق وغموض." in recorded_calls[0]["contents"]
    assert "Transcript:\nاسمع الحكاية دي." in recorded_calls[0]["contents"]
    assert recorded_calls[0]["model"] == DEFAULT_VYOND_MODEL
    assert (
        recorded_calls[0]["config"].speech_config.voice_config.prebuilt_voice_config.voice_name
        == "Kore"
    )

    with wave.open(str(wav_out), "rb") as wf:
        # 2 * 100ms tone + 2 * 180ms micro_pause + 450ms scene_pause = 1010ms
        expected_frames = int(24000 * (0.2 + 0.36 + 0.45))
        assert wf.getnframes() == expected_frames

    mp3_out = tmp_path / "story.mp3"
    res_mp3 = engine.render_full_story(
        story_chunks=chunks,
        output_file=str(mp3_out),
        delay_between_chunks=0.0,
        resume=False,
        client=fake_client,
    )
    assert res_mp3["status"] == "SUCCESS"
    assert mp3_out.exists()
    assert mp3_out.stat().st_size > 500


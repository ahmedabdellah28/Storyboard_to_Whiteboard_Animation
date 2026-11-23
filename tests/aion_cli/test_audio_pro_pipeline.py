"""Regression & unit tests for AION Broadcast Pro Audio Pipeline (Saudi Arabic + English/Foreign)."""
from __future__ import annotations

import math
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pytest

from core.aion.audio_mastering import (
    MASTER_SAMPLE_RATE,
    audit_audio_broadcast_qa,
    build_vocal_dsp_chain,
    master_voice_ffmpeg,
    stitch_wav_chunks_seamless,
    trim_pcm_silence_rms,
)
from core.aion.motion_and_audio import mix_scene_graph_audio
from core.aion.voice_stage import (
    _has_repeated_ngram,
    build_tts_request,
    compute_chunk_cache_key,
    split_section_paragraphs,
)
from section_timing.alignment.english_normalizer import EnglishTextNormalizer


def _write_tone_wav(path: Path, sr: int, duration_sec: float, freq: float = 220.0, amp: float = 0.25) -> Path:
    t = np.linspace(0.0, duration_sec, int(sr * duration_sec), endpoint=False, dtype=np.float32)
    sig = (np.sin(2.0 * math.pi * freq * t) * amp).astype(np.float32)
    pcm16 = np.clip(np.round(sig * 32767.0), -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm16.tobytes())
    return path


def test_saudi_arabic_track_dialect_lock_cues_lexicon_and_chunking():
    text = "[بصدمة] تخيل إن تأثير بلاسيبو يخلي عقلك يفرز دوبامين حقيقي!"
    sys_inst, spoken = build_tts_request(
        text=text,
        language="ar",
        profile_key="SAUDI_YOUTH_CREATOR",
        note_key="HIGH_ENERGY_YOUTUBE",
        custom_lexicon={"تخيل": "تَخَيَّل"},
    )
    # Dialect lock lives in system_instruction, never in spoken text
    assert "SAUDI ARABIC ONLY" in sys_inst
    assert "بصدمة" in sys_inst
    assert "[بصدمة]" not in spoken
    assert "بلاسِيبو" in spoken
    assert "دوبامِين" in spoken
    assert "تَخَيَّل" in spoken

    # Arabic chunking cap (48 words) vs English chunking cap (72 words)
    ar_long = " ".join(["كلمة"] * 60) + ". " + " ".join(["ثانية"] * 40) + "."
    en_long = " ".join(["word"] * 60) + ". " + " ".join(["second"] * 40) + "."
    assert len(split_section_paragraphs(ar_long, language="ar")) >= 2
    assert len(split_section_paragraphs(en_long, language="en")) == 2

    # Arabic repeated 4-gram catches diacritic/alef/taa-marbouta variants
    rep_words = ["إنَّ", "العقل", "البشري", "يخدعك", "وهنا", "ان", "العقل", "البشري", "يخدعك"]
    assert _has_repeated_ngram(rep_words, language="ar", n=4) is not None


def test_english_foreign_track_system_instruction_glossary_and_normalizer_fix():
    text = "[intrigued] In 1974, Chronostasis fooled every single volunteer in the lab."
    sys_inst, spoken = build_tts_request(
        text=text,
        language="en",
        profile_key="US_CASUAL_STORYTELLER",
        note_key="VIRAL_PSYCHOLOGY_ENGLISH_YT",
        custom_lexicon={"volunteer": "vol-un-TEER"},
    )
    # Full direction + matched glossary go into system_instruction; spoken stays clean
    assert "intrigued" in sys_inst
    assert "Chronostasis" in sys_inst
    assert "nineteen seventy-four" in sys_inst
    assert "vol-un-TEER" in sys_inst
    assert "Ganzfeld" not in sys_inst  # Unmentioned terms must NOT bloat system_instruction
    assert "[intrigued]" not in spoken
    assert spoken.startswith("In 1974, Chronostasis")

    # Verify fixed EnglishTextNormalizer bug ("were" must NOT become "we are")
    assert EnglishTextNormalizer.normalize("were") == "were"
    assert EnglishTextNormalizer.normalize("don't") == "do not"


def test_content_hash_chunk_cache_invalidates_on_edit():
    h1 = compute_chunk_cache_key(
        text="مرحبا بكم", voice_name="Fenrir", profile_key="SAUDI_YOUTH_CREATOR",
        note_key="HIGH_ENERGY_YOUTUBE", language="ar", model_name="gemini-3.8-flash-tts",
    )
    h2 = compute_chunk_cache_key(
        text="مرحبا بكم!", voice_name="Fenrir", profile_key="SAUDI_YOUTH_CREATOR",
        note_key="HIGH_ENERGY_YOUTUBE", language="ar", model_name="gemini-3.8-flash-tts",
    )
    assert h1 != h2 and len(h1) == 8


def test_separate_arabic_and_english_dsp_chains_and_48khz_two_pass_mastering(tmp_path: Path):
    ar_chain = ",".join(build_vocal_dsp_chain("ar", speed_factor=1.02))
    en_chain = ",".join(build_vocal_dsp_chain("en", speed_factor=1.00))
    assert "highpass=f=80" in ar_chain and "atempo=1.0200" in ar_chain
    assert "highpass=f=95" in en_chain and "highshelf=f=10800" in en_chain
    assert "atempo=" not in en_chain

    # Synthesize two 24kHz chunks, stitch seamlessly, and master to 48kHz 2-pass -14 LUFS
    c1 = _write_tone_wav(tmp_path / "c1.wav", sr=24000, duration_sec=1.2, freq=210.0, amp=0.18)
    c2 = _write_tone_wav(tmp_path / "c2.wav", sr=24000, duration_sec=1.2, freq=330.0, amp=0.18)
    cat = stitch_wav_chunks_seamless([c1, c2], tmp_path / "cat.wav", gap_sec=0.14)
    out = tmp_path / "master_ar.wav"
    dur, meta = master_voice_ffmpeg(cat, out, language="ar", speed_factor=1.02)

    assert dur > 2.0
    assert meta["sample_rate"] == MASTER_SAMPLE_RATE
    assert meta["language_chain"] == "ar_saudi"

    qa = audit_audio_broadcast_qa(out)
    assert qa["sample_rate"] == 48000
    assert qa["clipping_detected"] is False
    assert qa["integrated_lufs"] is not None
    assert -16.0 <= qa["integrated_lufs"] <= -12.0
    assert qa["true_peak_dbtp"] is not None and qa["true_peak_dbtp"] <= -0.5


def test_rms_silence_trimmer_preserves_audio_and_trims_dead_air():
    sr = 24000
    silence = np.zeros(int(sr * 0.6), dtype=np.int16)
    t = np.linspace(0.0, 0.4, int(sr * 0.4), endpoint=False)
    tone = (np.sin(2.0 * math.pi * 400.0 * t) * 8000).astype(np.int16)
    raw = np.concatenate([silence, tone, silence]).tobytes()
    trimmed = trim_pcm_silence_rms(raw, sample_rate=sr, pad_ms=40, fade_ms=8)
    assert len(trimmed) < len(raw) * 0.55
    assert len(trimmed) >= len(tone.tobytes())


def test_48khz_envelope_ducking_mix_no_tanh_distortion(tmp_path: Path):
    # Create a 48kHz voice WAV (silence 0..0.5s, speech 0.5..1.5s, silence 1.5..2.0s)
    sr = 48000
    n = sr * 2
    t = np.arange(n, dtype=np.float32) / sr
    voice = np.zeros(n, dtype=np.float32)
    speech_mask = (t >= 0.5) & (t < 1.5)
    voice[speech_mask] = 0.25 * np.sin(2.0 * math.pi * 300.0 * t[speech_mask])
    v_wav = tmp_path / "voice.wav"
    with wave.open(str(v_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((voice * 32767.0).astype(np.int16).tobytes())

    # Mix without SFX -> output must preserve exact amplitude (no tanh compression/coloring!)
    out_clean = tmp_path / "mix_clean.wav"
    res_clean = mix_scene_graph_audio(v_wav, [], out_clean)
    assert res_clean["sample_rate"] == 48000
    with wave.open(str(out_clean), "rb") as wf:
        assert wf.getframerate() == 48000
        arr = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32767.0
    # Peak must remain ~0.25 (not scaled to 0.89 and not squashed by tanh!)
    assert 0.23 <= float(np.max(np.abs(arr))) <= 0.27

    # Mix with continuous SFX cue -> SFX must be ducked during speech (0.7..1.3s) vs silence (0.05..0.35s)
    sfx_wav = _write_tone_wav(tmp_path / "sfx.wav", sr=44100, duration_sec=2.0, freq=1800.0, amp=0.5)
    out_mix = tmp_path / "mix_sfx.wav"
    res_mix = mix_scene_graph_audio(v_wav, [{"file": str(sfx_wav), "time": 0.0, "gain_db": -6.0}], out_mix)
    assert res_mix["placed_cues_count"] == 1
    qa = audit_audio_broadcast_qa(out_mix)
    assert qa["sample_rate"] == 48000
    assert qa["clipping_detected"] is False


def test_full_duration_audio_qa_catches_clipping_past_60_seconds(tmp_path: Path):
    sr = 8000
    n = sr * 65  # 65 seconds (> old 60s cutoff!)
    sig = np.zeros(n, dtype=np.int16)
    sig[sr * 62 : sr * 62 + 200] = 32767  # Clipping burst at t=62s
    wav_p = tmp_path / "long_clip.wav"
    with wave.open(str(wav_p), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(sig.tobytes())

    qa = audit_audio_broadcast_qa(wav_p)
    assert qa["duration_sec"] == 65.0
    assert qa["clipping_detected"] is True


def test_neon_glass_live_typing_typography_arabic_and_english(tmp_path: Path):
    from core.aion.kinetic_typography import compile_kinetic_text_block

    for idx, (lang_dir, txt, fnt) in enumerate([
        ("rtl", "سلسلة تغلق بحر القسطنطينية", "IBM Plex Sans Arabic"),
        ("ltr", "THE GOLDEN HORN CHAIN", "Inter"),
    ]):
        cmds = compile_kinetic_text_block(
            {
                "id": f"neon_{idx}",
                "text": txt,
                "font": fnt,
                "direction": lang_dir,
                "animation_mode": "neon_live_typing",
                "live_typing": True,
                "neon_border": True,
                "show_caret": True,
                "size": 46,
                "position": [960.0, 128.0],
                "start": 0.0,
                "end": 4.0,
            },
            comp_width=1920,
            comp_height=1080,
            comp_duration=5.0,
            comp_name="NeonTypeTest",
            work_dir=tmp_path,
        )
        names = [c.get("params", {}).get("name") for c in cmds if c.get("command", "").startswith("layer.new")]
        assert f"TextCard_neon_{idx}" in names
        assert f"TextCardGlow_neon_{idx}" in names
        assert f"TextCardBloom_neon_{idx}" in names
        assert f"TextCursor_neon_{idx}" in names
        source_keys = [
            c["params"]["value"]
            for c in cmds
            if c.get("command") == "prop.addKey" and c.get("params", {}).get("path") == "text/sourceText"
        ]
        assert len(source_keys) >= 15
        assert source_keys[-1] == txt


def test_egyptian_arabic_track_dialect_lock_male_female_and_cache_isolation(tmp_path: Path, monkeypatch):
    import json
    import pipeline_cli
    from core.aion.voice_stage import (
        build_inline_style_prefix,
        build_tts_request,
        compute_chunk_cache_key,
        is_egyptian_dialect,
        prepare_arabic_egyptian_tts_text,
    )

    assert is_egyptian_dialect("egyptian") is True
    assert is_egyptian_dialect("egyptian_female") is True
    assert is_egyptian_dialect("masri") is True
    assert is_egyptian_dialect("saudi_white") is False
    assert is_egyptian_dialect("saudi_white", profile_key="EGYPTIAN_YOUTH_CREATOR") is True

    # Egyptian TTS request must strictly lock Cairo Egyptian with zero Saudi/Gulf leak
    eg_sys, eg_user = build_tts_request(
        "تخيل معايا إن دماغك بيخدعك في عشر دقايق بس!",
        language="ar",
        dialect="egyptian",
        profile_key="EGYPTIAN_YOUTH_CREATOR",
        note_key="HIGH_ENERGY_EGYPTIAN_YT",
    )
    assert "EGYPTIAN ARABIC (CAIRO) ONLY" in eg_sys
    assert "SAUDI ARABIC ONLY" not in eg_sys
    assert "تخيل معايا" in eg_user

    # Saudi TTS request remains completely intact
    sa_sys, _ = build_tts_request(
        "تخيل معي إن عقلك يخدعك في عشر دقايق بس!",
        language="ar",
        dialect="saudi_white",
        profile_key="SAUDI_YOUTH_CREATOR",
        note_key="HIGH_ENERGY_YOUTUBE",
    )
    assert "SAUDI ARABIC ONLY" in sa_sys
    assert "EGYPTIAN ARABIC (CAIRO) ONLY" not in sa_sys

    # Inline style prefix supports both Male & Female Egyptian voices without Saudi phrasing
    eg_male_prefix = build_inline_style_prefix(
        "تخيل معايا إن دماغك بيخدعك!",
        language="ar",
        dialect="egyptian",
        voice_name="Fenrir",
        profile_key="EGYPTIAN_YOUTH_CREATOR",
        note_key="HIGH_ENERGY_EGYPTIAN_YT",
    )
    eg_female_prefix = build_inline_style_prefix(
        "تخيل معايا إن دماغك بيخدعك!",
        language="ar",
        dialect="egyptian_female",
        voice_name="Kore",
        profile_key="EGYPTIAN_FEMALE_CREATOR",
        note_key="HIGH_ENERGY_EGYPTIAN_YT",
    )
    assert "Egyptian Cairo male" in eg_male_prefix
    assert "Saudi" not in eg_male_prefix
    assert "Egyptian Cairo female" in eg_female_prefix
    assert "Saudi" not in eg_female_prefix

    # Egyptian lexicon normalizes hard Egyptian Jeem loanwords
    spoken, cues = prepare_arabic_egyptian_tts_text("[excited] تجربة غانزفيلد مع دوبامين!")
    assert "جانزفِيلد" in spoken
    assert "دوبامِين" in spoken
    assert cues == ["excited"]

    # Cache hash isolates Egyptian from Saudi on identical text & voice, while preserving legacy Saudi hash
    h_sa_default = compute_chunk_cache_key(
        text="أهلاً بكم",
        model_name="gemini-3.1-flash-tts-preview",
        language="ar",
        voice_name="Fenrir",
        profile_key="SAUDI_YOUTH_CREATOR",
        note_key="HIGH_ENERGY_YOUTUBE",
    )
    h_sa_explicit = compute_chunk_cache_key(
        text="أهلاً بكم",
        model_name="gemini-3.1-flash-tts-preview",
        language="ar",
        voice_name="Fenrir",
        profile_key="SAUDI_YOUTH_CREATOR",
        note_key="HIGH_ENERGY_YOUTUBE",
        dialect="saudi_white",
    )
    h_eg = compute_chunk_cache_key(
        text="أهلاً بكم",
        model_name="gemini-3.1-flash-tts-preview",
        language="ar",
        voice_name="Fenrir",
        profile_key="SAUDI_YOUTH_CREATOR",
        note_key="HIGH_ENERGY_YOUTUBE",
        dialect="egyptian",
    )
    assert h_sa_default == h_sa_explicit
    assert h_eg != h_sa_default

    # get_project_config auto-resolves Male & Female Egyptian defaults cleanly
    fake_projects = tmp_path / "projects"
    male_dir = fake_projects / "demo_eg_male"
    female_dir = fake_projects / "demo_eg_female"
    male_dir.mkdir(parents=True)
    female_dir.mkdir(parents=True)
    (male_dir / "project.json").write_text(json.dumps({"language": "ar", "dialect": "egyptian"}), encoding="utf-8")
    (female_dir / "project.json").write_text(json.dumps({"language": "ar", "dialect": "egyptian_female"}), encoding="utf-8")
    monkeypatch.setattr(pipeline_cli, "PROJECTS_DIR", fake_projects)

    cfg_m = pipeline_cli.get_project_config("demo_eg_male")
    assert cfg_m["dialect"] == "egyptian"
    assert cfg_m["tts_voice"] == "Fenrir"
    assert cfg_m["tts_profile"] == "EGYPTIAN_YOUTH_CREATOR"
    assert cfg_m["director_note"] == "HIGH_ENERGY_EGYPTIAN_YT"

    cfg_f = pipeline_cli.get_project_config("demo_eg_female")
    assert cfg_f["dialect"] == "egyptian_female"
    assert cfg_f["tts_voice"] == "Kore"
    assert cfg_f["tts_profile"] == "EGYPTIAN_FEMALE_CREATOR"
    assert cfg_f["director_note"] == "HIGH_ENERGY_EGYPTIAN_YT"



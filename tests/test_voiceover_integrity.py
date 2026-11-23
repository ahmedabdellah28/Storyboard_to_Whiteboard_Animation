from pathlib import Path

from production_engine.universal_section_pipeline import UniversalSectionPipeline


def test_step_tts_uses_safe_zero_truncation_generator(monkeypatch, tmp_path):
    """Section TTS must delegate to the verified short-chunk generator, not a single long API call."""
    section = tmp_path / "06_omar_al_mukhtar"
    section.mkdir()
    (section / "script.txt").write_text(
        "عمر المختار المعلم البسيط الذي تحول إلى قائد مقاومة "
        "أرعبت الاحتلال الإيطالي وقاد المقاومة الليبية ضد جيش مدجج "
        "بالدبابات والطائرات واعتمد على حرب العصابات والصبر ومعرفة الصحراء",
        encoding="utf-8",
    )
    expected_audio = section / "voice" / "section.wav"
    calls = {}

    def fake_generate(script_path, output_wav_path, chunks_dir, **kwargs):
        calls.update(
            script_path=Path(script_path),
            output_wav_path=Path(output_wav_path),
            chunks_dir=Path(chunks_dir),
            kwargs=kwargs,
        )
        expected_audio.parent.mkdir(exist_ok=True)
        expected_audio.write_bytes(b"RIFF")
        return str(expected_audio), 12.34

    monkeypatch.setattr(
        "production_engine.universal_section_pipeline.generate_voiceover_zero_truncation",
        fake_generate,
    )

    pipeline = UniversalSectionPipeline(section, title="عمر المختار")
    output = pipeline.step_tts()

    assert Path(output) == expected_audio
    assert calls["script_path"] == section / "script.txt"
    assert calls["output_wav_path"] == expected_audio
    assert calls["chunks_dir"] == section / "voice" / "chunks"
    assert calls["kwargs"]["max_words_per_chunk"] == 28
    assert calls["kwargs"]["speed_factor"] == 1.1

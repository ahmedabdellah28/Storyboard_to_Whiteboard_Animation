from pathlib import Path
from section_tts.config import AppConfig
from section_tts.core.pipeline import SectionTTSPipeline
from section_tts.providers.mock import MockTTSProvider

def test_full_section_pipeline_with_mock_tts(tmp_path: Path):
    section_dir = tmp_path / "003"
    voice_dir = section_dir / "voice"
    section_dir.mkdir(parents=True)

    # 1. Create realistic Arabic section script (>60 words to force multi-chunking)
    script_text = (
        "الكيوي أصله الحقيقي ليس من نيوزيلندا كما يعتقد معظم الناس، "
        "بل هو في الحقيقة قادم من وديان الصين القديمة وكان يسمى عنب الثعلب الصيني. "
        "وعندما وصل إلى نيوزيلندا في أوائل القرن العشرين، قرر المزارعون تغيير اسمه بالكامل، "
        "ليشبه طائر الكيوي الوطني الشهير بريشه البني الداكن وشكله الصغير المميز!"
    )
    script_file = section_dir / "script.txt"
    script_file.write_text(script_text, encoding="utf-8")

    # 2. Setup pipeline with Mock provider
    cfg = AppConfig()
    cfg.chunking.max_words_per_chunk = 18  # Forces splitting into multiple chunks
    mock_provider = MockTTSProvider(sample_rate=24000)

    pipeline = SectionTTSPipeline(
        config=cfg,
        provider=mock_provider,
        force_regenerate=False,
        debug_mode=True
    )

    # 3. Execute Pipeline
    metadata = pipeline.process_section(
        script_path=script_file,
        output_dir=voice_dir,
        section_id="003"
    )

    # 4. Verify Outputs
    assert (voice_dir / "section.wav").exists()
    assert (voice_dir / "metadata.json").exists()
    assert (voice_dir / "debug" / "generation_report.json").exists()
    
    assert metadata.section_id == "003"
    assert metadata.duration > 0
    assert len(metadata.chunks) >= 2
    
    # Check that chunks exist on disk
    for ch in metadata.chunks:
        chunk_path = voice_dir / ch.file
        assert chunk_path.exists()
        assert ch.duration > 0
        assert ch.global_end > ch.global_start

    # 5. Test Cache Hit on second run
    cached_metadata = pipeline.process_section(
        script_path=script_file,
        output_dir=voice_dir,
        section_id="003"
    )
    assert cached_metadata.generation_hash == metadata.generation_hash
    assert cached_metadata.duration == metadata.duration

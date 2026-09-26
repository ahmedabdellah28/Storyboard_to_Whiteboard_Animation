from pathlib import Path
from section_tts.audio.validator import AudioValidator
from section_tts.config import ValidationConfig
from .test_stitcher import create_dummy_wav

def test_chunk_validation_pass(tmp_path: Path):
    validator = AudioValidator(ValidationConfig())
    wav_path = tmp_path / "good.wav"
    create_dummy_wav(wav_path, duration_sec=2.0)
    
    is_valid, errors, metrics = validator.validate_chunk(wav_path, text="هذا مقطع تجريبي ممتاز ومفيد جداً")
    assert is_valid is True
    assert len(errors) == 0
    assert metrics.duration == 2.0

def test_chunk_validation_too_short(tmp_path: Path):
    validator = AudioValidator(ValidationConfig(min_duration_per_chunk_sec=1.0))
    wav_path = tmp_path / "short.wav"
    create_dummy_wav(wav_path, duration_sec=0.3)
    
    is_valid, errors, metrics = validator.validate_chunk(wav_path, text="كلمة")
    assert is_valid is False
    assert any("below minimum" in e for e in errors)

from pathlib import Path
from section_tts.utils.hashing import compute_section_hash
from section_tts.core.cache_manager import CacheManager
from section_tts.models.metadata import SectionMetadata
from section_tts.models.chunk import ChunkMetadata

def test_section_hash_determinism():
    profile = {"name": "Test", "voice": "Fenrir"}
    h1 = compute_section_hash("مرحبا بكم", profile, "gemini-2.5-flash-preview-tts", "Fenrir", {"w": 28})
    h2 = compute_section_hash("مرحبا بكم", profile, "gemini-2.5-flash-preview-tts", "Fenrir", {"w": 28})
    assert h1 == h2

def test_section_hash_changes_on_text_change():
    profile = {"name": "Test", "voice": "Fenrir"}
    h1 = compute_section_hash("مرحبا بكم", profile, "gemini-2.5-flash-preview-tts", "Fenrir")
    h2 = compute_section_hash("مرحبا بكم جميعاً", profile, "gemini-2.5-flash-preview-tts", "Fenrir")
    assert h1 != h2

def test_section_hash_changes_on_voice_or_model_change():
    profile = {"name": "Test", "voice": "Fenrir"}
    h1 = compute_section_hash("مرحبا", profile, "gemini-2.5-flash-preview-tts", "Fenrir")
    h2 = compute_section_hash("مرحبا", profile, "gemini-2.5-flash-preview-tts", "Puck")
    h3 = compute_section_hash("مرحبا", profile, "gemini-2.0-flash", "Fenrir")
    assert h1 != h2
    assert h1 != h3

def test_cache_hit_and_miss(tmp_path: Path):
    cache_mgr = CacheManager(force_regenerate=False)
    test_dir = tmp_path / "section_001" / "voice"
    test_dir.mkdir(parents=True)

    sec_wav = test_dir / "section.wav"
    meta_json = test_dir / "metadata.json"
    
    # Write mock dummy audio file > 1000 bytes
    sec_wav.write_bytes(b"\x00" * 2000)
    
    meta = SectionMetadata(
        section_id="001",
        text="نص تجريبي",
        model="gemini-2.5-flash-preview-tts",
        voice="Fenrir",
        duration=5.0,
        total_words=2,
        average_wpm=150.0,
        generation_hash="abc123hash",
        chunks=[]
    )
    meta.save(meta_json)

    # Matching hash -> Cache HIT
    hit = cache_mgr.is_section_cached(test_dir, "abc123hash")
    assert hit is not None
    assert hit.section_id == "001"

    # Mismatched hash -> Cache MISS
    miss = cache_mgr.is_section_cached(test_dir, "different_hash")
    assert miss is None

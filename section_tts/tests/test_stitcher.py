import wave
from pathlib import Path
import numpy as np
from section_tts.audio.stitcher import AudioStitcher
from section_tts.audio.analyzer import AudioAnalyzer

def create_dummy_wav(path: Path, duration_sec: float = 1.0, freq: float = 440.0, sr: int = 24000):
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    sig = 0.5 * np.sin(2 * np.pi * freq * t)
    int16_pcm = (sig * 32767.0).astype(np.int16).tobytes()
    
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int16_pcm)

def test_stitching_chunks_order_and_duration(tmp_path: Path):
    stitcher = AudioStitcher(pause_between_chunks_ms=100, micro_crossfade_ms=10, expected_sample_rate=24000)
    c1 = tmp_path / "000.wav"
    c2 = tmp_path / "001.wav"
    c3 = tmp_path / "002.wav"
    out_sec = tmp_path / "section.wav"

    create_dummy_wav(c1, duration_sec=1.0)
    create_dummy_wav(c2, duration_sec=1.5)
    create_dummy_wav(c3, duration_sec=2.0)

    total_dur, timings = stitcher.stitch_chunks([c1, c2, c3], out_sec)

    assert out_sec.exists()
    assert len(timings) == 3
    # Check ordering
    assert timings[0]["global_start"] == 0.0
    assert timings[1]["global_start"] >= timings[0]["global_end"]
    assert timings[2]["global_start"] >= timings[1]["global_end"]
    # Total duration = sum of durations + 2 * pauses (0.1s each)
    expected_dur = 1.0 + 1.5 + 2.0 + (2 * 0.1)
    assert abs(total_dur - expected_dur) < 0.05

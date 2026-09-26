import io
import wave
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
import numpy as np

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False

@dataclass
class AudioMetrics:
    """Quantitative acoustic and pacing metrics of an audio segment."""
    duration: float
    sample_rate: int
    channels: int
    rms: float
    peak: float
    silence_ratio: float
    speech_ratio: float
    estimated_wpm: float

class AudioAnalyzer:
    """Analyzes audio signals and speech characteristics with vectorized numpy operations."""
    def __init__(self, silence_threshold: float = 0.015, frame_size_ms: float = 20.0):
        self.silence_threshold = silence_threshold
        self.frame_size_ms = frame_size_ms

    def load_audio_array(self, source: Path | str | bytes) -> Tuple[np.ndarray, int]:
        """Loads audio from path or bytes into a float32 numpy array normalized to [-1.0, 1.0]."""
        if isinstance(source, (str, Path)):
            filepath = Path(source)
            if HAS_SOUNDFILE:
                data, sr = sf.read(str(filepath), dtype="float32")
                return data, sr
            else:
                with wave.open(str(filepath), "rb") as wf:
                    sr = wf.getframerate()
                    n_channels = wf.getnchannels()
                    n_frames = wf.getnframes()
                    raw = wf.readframes(n_frames)
                    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                    if n_channels > 1:
                        data = data.reshape(-1, n_channels)
                return data, sr
        elif isinstance(source, bytes):
            if HAS_SOUNDFILE:
                data, sr = sf.read(io.BytesIO(source), dtype="float32")
                return data, sr
            else:
                with wave.open(io.BytesIO(source), "rb") as wf:
                    sr = wf.getframerate()
                    n_channels = wf.getnchannels()
                    n_frames = wf.getnframes()
                    raw = wf.readframes(n_frames)
                    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                    if n_channels > 1:
                        data = data.reshape(-1, n_channels)
                return data, sr
        else:
            raise TypeError(f"Unsupported audio source type: {type(source)}")

    def analyze(self, source: Path | str | bytes, text: Optional[str] = None) -> AudioMetrics:
        """Computes comprehensive metrics from an audio file, bytes, or buffer."""
        data, sr = self.load_audio_array(source)

        # Mono projection for analysis if multi-channel
        if data.ndim > 1:
            channels = data.shape[1]
            mono = np.mean(data, axis=1)
        else:
            channels = 1
            mono = data

        n_samples = len(mono)
        duration = float(n_samples) / float(sr) if sr > 0 else 0.0

        if n_samples == 0 or duration == 0:
            return AudioMetrics(
                duration=0.0,
                sample_rate=sr,
                channels=channels,
                rms=0.0,
                peak=0.0,
                silence_ratio=1.0,
                speech_ratio=0.0,
                estimated_wpm=0.0
            )

        # RMS & Peak
        rms = float(np.sqrt(np.mean(mono ** 2)))
        peak = float(np.max(np.abs(mono)))

        # Frame-level energy to calculate silence / speech ratio
        frame_len = max(1, int(sr * (self.frame_size_ms / 1000.0)))
        n_frames = n_samples // frame_len
        if n_frames > 0:
            frames = mono[:n_frames * frame_len].reshape(n_frames, frame_len)
            frame_rms = np.sqrt(np.mean(frames ** 2, axis=1))
            silence_frames = np.sum(frame_rms < self.silence_threshold)
            silence_ratio = float(silence_frames) / float(n_frames)
            speech_ratio = 1.0 - silence_ratio
        else:
            silence_ratio = 0.0
            speech_ratio = 1.0

        # Estimated WPM
        wpm = 0.0
        if text:
            words = [w for w in text.split() if w]
            word_count = len(words)
            if duration > 0:
                wpm = float(word_count) / (duration / 60.0)

        return AudioMetrics(
            duration=round(duration, 3),
            sample_rate=sr,
            channels=channels,
            rms=round(rms, 4),
            peak=round(peak, 4),
            silence_ratio=round(silence_ratio, 3),
            speech_ratio=round(speech_ratio, 3),
            estimated_wpm=round(wpm, 1)
        )

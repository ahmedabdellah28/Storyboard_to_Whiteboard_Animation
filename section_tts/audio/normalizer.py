import wave
from pathlib import Path
from typing import Tuple
import numpy as np
from .analyzer import AudioAnalyzer

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False

class LoudnessNormalizer:
    """Matches loudness across chunks while preventing clipping."""
    def __init__(self, target_rms: float = 0.15, max_peak: float = 0.95):
        self.target_rms = target_rms
        self.max_peak = max_peak
        self.analyzer = AudioAnalyzer()

    def normalize_array(self, data: np.ndarray) -> np.ndarray:
        """Normalizes audio float32 array to target RMS without exceeding max_peak."""
        if len(data) == 0:
            return data

        current_rms = np.sqrt(np.mean(data ** 2))
        current_peak = np.max(np.abs(data))

        if current_rms < 1e-6 or current_peak < 1e-6:
            return data

        # Desired gain to hit target_rms
        gain = self.target_rms / current_rms

        # Guard against clipping: do not exceed max_peak
        if current_peak * gain > self.max_peak:
            gain = self.max_peak / current_peak

        normalized = data * gain
        # Safety hard clip
        return np.clip(normalized, -1.0, 1.0)

    def normalize_file(self, in_path: Path | str, out_path: Path | str) -> Tuple[float, float]:
        """Reads a WAV file, normalizes it, and saves to out_path. Returns (old_rms, new_rms)."""
        in_path = Path(in_path)
        out_path = Path(out_path)
        data, sr = self.analyzer.load_audio_array(in_path)
        
        old_rms = float(np.sqrt(np.mean(data ** 2)))
        normalized = self.normalize_array(data)
        new_rms = float(np.sqrt(np.mean(normalized ** 2)))

        out_path.parent.mkdir(parents=True, exist_ok=True)
        if HAS_SOUNDFILE:
            sf.write(str(out_path), normalized, sr, subtype="PCM_16")
        else:
            int16_data = (normalized * 32767.0).astype(np.int16)
            with wave.open(str(out_path), "wb") as wf:
                wf.setnchannels(1 if normalized.ndim == 1 else normalized.shape[1])
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(int16_data.tobytes())

        return old_rms, new_rms

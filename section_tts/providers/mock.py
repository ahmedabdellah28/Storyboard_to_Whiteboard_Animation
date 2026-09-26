import io
import math
import struct
import numpy as np
from typing import Optional
from .base import TTSProvider, AudioResult
from ..models.voice import VoiceProfile, PerformanceCue
from ..models.chunk import ChunkContext
from .gemini import pcm_to_wav_bytes

class MockTTSProvider(TTSProvider):
    """Deterministic Mock TTS Provider generating synthetic sine wave speech audio for testing."""
    def __init__(self, sample_rate: int = 24000, target_wpm: float = 160.0):
        self.sample_rate = sample_rate
        self.target_wpm = target_wpm

    def generate(
        self,
        text: str,
        voice_profile: VoiceProfile,
        performance: PerformanceCue,
        context: Optional[ChunkContext] = None
    ) -> AudioResult:
        words = [w for w in text.split() if w]
        word_count = max(1, len(words))
        # duration = (words / target_wpm) * 60 seconds
        duration = max(1.0, (word_count / self.target_wpm) * 60.0)
        
        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, endpoint=False)
        # Generate harmonic speech-like signal (fundamental ~180Hz + harmonics)
        signal = 0.3 * np.sin(2 * np.pi * 180 * t) + 0.15 * np.sin(2 * np.pi * 360 * t)
        
        # Add slight natural pauses (dip amplitude) between words
        word_samples = n_samples // word_count
        for i in range(word_count):
            pause_start = min(n_samples - 1, (i + 1) * word_samples - int(0.04 * self.sample_rate))
            pause_end = min(n_samples, (i + 1) * word_samples)
            if pause_start < pause_end:
                signal[pause_start:pause_end] *= 0.05

        int16_pcm = (np.clip(signal, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
        wav_bytes = pcm_to_wav_bytes(int16_pcm, sample_rate=self.sample_rate)

        return AudioResult(
            audio_bytes=wav_bytes,
            sample_rate=self.sample_rate,
            duration=round(duration, 3),
            format="wav"
        )

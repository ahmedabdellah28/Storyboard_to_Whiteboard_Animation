from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from ..models.voice import VoiceProfile, PerformanceCue
from ..models.chunk import ChunkContext

@dataclass
class AudioResult:
    """Standardized result returned by any TTS provider."""
    audio_bytes: bytes
    sample_rate: int = 24000
    duration: float = 0.0
    format: str = "wav"

class TTSProvider(ABC):
    """Abstract base class decoupling the section TTS pipeline from specific TTS engines."""
    
    @abstractmethod
    def generate(
        self,
        text: str,
        voice_profile: VoiceProfile,
        performance: PerformanceCue,
        context: Optional[ChunkContext] = None
    ) -> AudioResult:
        """Synthesizes text into AudioResult."""
        pass

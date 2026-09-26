from dataclasses import dataclass, field
from typing import Optional
from pydantic import BaseModel, Field
from .voice import PerformanceCue

@dataclass
class ChunkContext:
    """Surrounding context for acoustic and intonation continuity."""
    previous_text: Optional[str] = None
    current_text: str = ""
    next_text: Optional[str] = None

@dataclass
class ChunkItem:
    """A semantic chunk prepared for TTS synthesis."""
    index: int
    text: str
    word_count: int
    context: ChunkContext
    cue: PerformanceCue
    generation_hash: str = ""

class ChunkMetadata(BaseModel):
    """Metadata recorded for each synthesized chunk inside a section."""
    id: int
    text: str
    file: str
    duration: float
    sample_rate: int = 24000
    estimated_wpm: float
    rms: float = 0.0
    peak: float = 0.0
    silence_ratio: float = 0.0
    global_start: float
    global_end: float
    performance_type: str = "FACT"
    generation_hash: str = ""

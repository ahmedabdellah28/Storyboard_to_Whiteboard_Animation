from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from .chunk import ChunkMetadata

class SectionMetadata(BaseModel):
    """The authoritative metadata document produced alongside section.wav."""
    section_id: str
    script_file: str = "script.txt"
    text: str
    model: str
    voice: str
    duration: float
    sample_rate: int = 24000
    total_words: int
    average_wpm: float
    audio_file: str = "section.wav"
    generation_hash: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    chunks: List[ChunkMetadata] = Field(default_factory=list)

    def save(self, filepath: Path) -> None:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, filepath: Path) -> Optional["SectionMetadata"]:
        filepath = Path(filepath)
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                return cls.model_validate_json(content)
        except Exception:
            return None

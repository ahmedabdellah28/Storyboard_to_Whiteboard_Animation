from pathlib import Path
from typing import Optional, Dict, Any
from ..models.metadata import SectionMetadata
from ..models.chunk import ChunkMetadata
from ..utils.hashing import compute_section_hash, compute_chunk_hash
from ..utils.logging import log

class CacheManager:
    """Handles section-level and chunk-level incremental caching."""
    def __init__(self, force_regenerate: bool = False):
        self.force_regenerate = force_regenerate

    def is_section_cached(
        self,
        output_dir: Path,
        expected_hash: str
    ) -> Optional[SectionMetadata]:
        """Checks if section.wav and metadata.json exist and match the input hash."""
        if self.force_regenerate:
            return None

        metadata_file = output_dir / "metadata.json"
        section_wav = output_dir / "section.wav"

        if not (metadata_file.exists() and section_wav.exists()):
            return None

        metadata = SectionMetadata.load(metadata_file)
        if metadata and metadata.generation_hash == expected_hash:
            if section_wav.stat().st_size > 1000:
                log.cache(f"Cache HIT for section {metadata.section_id} (hash {expected_hash[:8]}).")
                return metadata

        return None

    def is_chunk_cached(
        self,
        chunk_file: Path,
        expected_chunk_hash: str
    ) -> bool:
        """Checks if an individual chunk audio file exists and is valid."""
        if self.force_regenerate:
            return False

        if chunk_file.exists() and chunk_file.stat().st_size > 500:
            return True
        return False

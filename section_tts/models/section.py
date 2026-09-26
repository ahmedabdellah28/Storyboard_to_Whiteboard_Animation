from dataclasses import dataclass
from pathlib import Path
import re

@dataclass
class SectionScript:
    """Represents a section's original input script."""
    section_id: str
    script_path: Path
    raw_text: str
    clean_text: str
    word_count: int

    @classmethod
    def from_file(cls, script_path: Path, section_id: str = "") -> "SectionScript":
        script_path = Path(script_path).resolve()
        if not section_id:
            # e.g., if path is sections/003/script.txt -> section_id is "003"
            section_id = script_path.parent.name
        with open(script_path, "r", encoding="utf-8") as f:
            raw_text = f.read().strip()
        
        # Word count calculation preserving Arabic and English words
        words = [w for w in re.split(r'\s+', raw_text) if w]
        clean_text = " ".join(words)
        return cls(
            section_id=section_id,
            script_path=script_path,
            raw_text=raw_text,
            clean_text=clean_text,
            word_count=len(words)
        )

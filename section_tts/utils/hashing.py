import hashlib
import json
from typing import Any, Dict, Optional

def compute_hash(data: str) -> str:
    """Returns SHA256 hex digest for input string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def compute_section_hash(
    section_text: str,
    voice_profile_dict: Dict[str, Any],
    model: str,
    voice: str,
    settings: Optional[Dict[str, Any]] = None
) -> str:
    """
    Computes a deterministic hash representing the exact section input and configuration.
    If text, voice profile, model, voice, or generation settings do not change,
    this hash is identical.
    """
    payload = {
        "text": section_text.strip(),
        "voice_profile": voice_profile_dict,
        "model": model.strip(),
        "voice": voice.strip(),
        "settings": settings or {}
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return compute_hash(encoded)

def compute_chunk_hash(
    chunk_text: str,
    model: str,
    voice: str,
    performance_dict: Dict[str, Any]
) -> str:
    """Computes a deterministic hash for a single chunk."""
    payload = {
        "text": chunk_text.strip(),
        "model": model.strip(),
        "voice": voice.strip(),
        "performance": performance_dict
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return compute_hash(encoded)

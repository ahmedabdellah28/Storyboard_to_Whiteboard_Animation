"""Deterministic artifact identity and content hashing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

PathLike = Union[str, Path]


def hash_string(text: str) -> str:
    """Calculate SHA-256 hash of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_file(file_path: PathLike, chunk_size: int = 65536) -> str:
    """Calculate SHA-256 hash of a file's contents."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for hashing: {file_path}")

    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def hash_dict(data: Dict[str, Any]) -> str:
    """Deterministically hash a dictionary via sorted JSON serialization."""
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hash_string(serialized)


def compute_artifact_hash(
    component: str,
    inputs: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
    dependencies: Optional[Dict[str, str]] = None,
) -> str:
    """Generate a canonical deterministic SHA-256 hash identifying an artifact.

    Identity = SHA-256(component + inputs + config + dependency_hashes)
    """
    payload = {
        "component": component,
        "inputs": inputs or {},
        "config": config or {},
        "dependencies": dependencies or {},
    }
    digest = hash_dict(payload)
    return f"sha256:{digest}"

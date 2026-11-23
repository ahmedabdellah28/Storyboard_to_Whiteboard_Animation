"""Artifact registration, atomic storage, revision tracking, and lookup store.

Updated in Phase 2: Invalidation + Revision System & Artifact Integration.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.artifacts.artifact_identity import hash_file
from core.config.settings import PROJECT_ROOT
from core.state.workflow_events import ArtifactCommittedEvent, get_workflow_event_bus

PathLike = Union[str, Path]


@dataclass
class ArtifactRecord:
    artifact_hash: str
    file_path: str
    component: str
    stage_id: str = ""
    revision_id: int = 1
    section_id: str = ""
    size_bytes: int = 0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ArtifactStore:
    """Thread-safe catalog of generated artifacts preventing redundant processing."""

    def __init__(
        self,
        store_dir: Optional[Path] = None,
        event_bus: Optional[Any] = None,
    ) -> None:
        self.store_dir = store_dir or (PROJECT_ROOT / ".artifacts_cache")
        self.event_bus = event_bus
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.store_dir / "artifacts_manifest.json"
        self._lock = threading.RLock()
        self._records: Dict[str, ArtifactRecord] = {}
        self._stage_lookup: Dict[str, str] = {}  # key: "{section_id}:{stage_id}" -> artifact_hash
        self._load_manifest()

    def _load_manifest(self) -> None:
        if self.manifest_file.is_file():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        rec = ArtifactRecord(**v)
                        self._records[k] = rec
                        if rec.section_id and rec.stage_id:
                            self._stage_lookup[f"{rec.section_id}:{rec.stage_id}"] = rec.artifact_hash
            except Exception as e:
                print(f"⚠️ [ArtifactStore] Error loading manifest: {e}")

    def _save_manifest(self) -> None:
        temp_file = self.manifest_file.with_name(f"{self.manifest_file.name}.tmp")
        data = {k: asdict(v) for k, v in self._records.items()}
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if temp_file.exists():
            os.replace(temp_file, self.manifest_file)

    def register_artifact(
        self,
        artifact_hash: str,
        file_path: PathLike,
        component: str,
        metadata: Optional[Dict[str, Any]] = None,
        stage_id: str = "",
        revision_id: int = 1,
        section_id: str = "",
    ) -> ArtifactRecord:
        path = Path(file_path).resolve()
        size = path.stat().st_size if path.is_file() else 0
        record = ArtifactRecord(
            artifact_hash=artifact_hash,
            file_path=str(path),
            component=component,
            stage_id=stage_id,
            revision_id=revision_id,
            section_id=section_id,
            size_bytes=size,
            metadata=metadata or {},
        )
        with self._lock:
            self._records[artifact_hash] = record
            if section_id and stage_id:
                self._stage_lookup[f"{section_id}:{stage_id}"] = artifact_hash
            self._save_manifest()

        # Publish artifact committed event
        if section_id or stage_id:
            try:
                bus = self.event_bus or get_workflow_event_bus()
                bus.publish(
                    ArtifactCommittedEvent(
                        project_id=metadata.get("project_id", "") if metadata else "",
                        section_id=section_id,
                        stage_id=stage_id or component,
                        artifact_type=component,
                        artifact_path=str(path),
                        artifact_hash=artifact_hash,
                    )
                )
            except Exception:
                pass

        return record

    def register_stage_artifact(
        self,
        section_id: str,
        stage_id: str,
        file_path: PathLike,
        artifact_hash: str,
        revision_id: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ArtifactRecord:
        """Register an artifact produced by a canonical pipeline stage."""
        return self.register_artifact(
            artifact_hash=artifact_hash,
            file_path=file_path,
            component=stage_id,
            stage_id=stage_id,
            revision_id=revision_id,
            section_id=section_id,
            metadata=metadata,
        )

    def get_artifact(self, artifact_hash: str) -> Optional[ArtifactRecord]:
        with self._lock:
            return self._records.get(artifact_hash)

    def get_stage_artifact(self, section_id: str, stage_id: str) -> Optional[ArtifactRecord]:
        """Look up the latest registered artifact for a specific section stage."""
        with self._lock:
            h = self._stage_lookup.get(f"{section_id}:{stage_id}")
            if h:
                return self.get_artifact(h)
            return None

    def invalidate_stage_artifact(self, section_id: str, stage_id: str) -> None:
        """Remove stage cache reference to force recomputation on next run."""
        with self._lock:
            key = f"{section_id}:{stage_id}"
            if key in self._stage_lookup:
                del self._stage_lookup[key]

    def is_artifact_valid(self, artifact_hash: str, expected_path: Optional[PathLike] = None) -> bool:
        """Check if artifact exists, matches registered size, and is present on disk."""
        record = self.get_artifact(artifact_hash)
        if not record:
            return False

        check_path = Path(expected_path) if expected_path else Path(record.file_path)
        if not check_path.is_file():
            return False

        if check_path.stat().st_size == 0:
            return False

        if record.size_bytes > 0 and check_path.stat().st_size != record.size_bytes:
            return False

        return True

    @staticmethod
    def atomic_write_bytes(target_path: PathLike, data: bytes) -> Path:
        """Write binary data to target path atomically using a temporary file."""
        target = Path(target_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_target = target.with_name(f"{target.name}.tmp")

        with open(temp_target, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        if target.exists():
            target.unlink()
        os.replace(temp_target, target)
        return target

    @staticmethod
    def atomic_write_text(target_path: PathLike, text: str, encoding: str = "utf-8") -> Path:
        """Write string content to target path atomically using a temporary file."""
        target = Path(target_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_target = target.with_name(f"{target.name}.tmp")

        with open(temp_target, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())

        if target.exists():
            target.unlink()
        os.replace(temp_target, target)
        return target


_GLOBAL_ARTIFACT_STORE: Optional[ArtifactStore] = None
_STORE_LOCK = threading.Lock()


def get_artifact_store() -> ArtifactStore:
    global _GLOBAL_ARTIFACT_STORE
    with _STORE_LOCK:
        if _GLOBAL_ARTIFACT_STORE is None:
            _GLOBAL_ARTIFACT_STORE = ArtifactStore()
        return _GLOBAL_ARTIFACT_STORE

"""Durable JSON persistence store for project states."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Dict, Optional

from core.config.settings import PROJECT_ROOT
from core.state.project_state import ProjectState


class StateStore:
    """Thread-safe persistent state store using atomic writes."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or (PROJECT_ROOT / ".state")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._cache: Dict[str, ProjectState] = {}

    def get_state_file_path(self, project_id: str) -> Path:
        return self.base_dir / f"{project_id}_state.json"

    def load_state(self, project_id: str) -> ProjectState:
        with self._lock:
            if project_id in self._cache:
                return self._cache[project_id]

            state_file = self.get_state_file_path(project_id)
            if state_file.is_file():
                try:
                    with open(state_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        state = ProjectState.from_dict(data)
                        self._cache[project_id] = state
                        return state
                except Exception as e:
                    print(f"⚠️ [StateStore] Failed to parse state file {state_file}: {e}")

            # Initialize new state
            state = ProjectState(project_id=project_id)
            self._cache[project_id] = state
            return state

    def save_state(self, state: ProjectState) -> None:
        with self._lock:
            import datetime
            state.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self._cache[state.project_id] = state
            state_file = self.get_state_file_path(state.project_id)
            temp_file = state_file.with_name(f"{state_file.name}.tmp")

            data = state.to_dict()
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic file swap
            if os.path.exists(temp_file):
                os.replace(temp_file, state_file)

    def list_all_projects(self) -> list[dict]:
        """Scan base_dir for all project state files and return summary sorted by updated_at descending."""
        import datetime
        results = []
        if not self.base_dir.is_dir():
            return results

        for state_file in self.base_dir.glob("*_state.json"):
            stem = state_file.stem
            proj_id = stem[:-6] if stem.endswith("_state") else stem
            if not proj_id:
                continue
            try:
                mtime = state_file.stat().st_mtime
                mtime_iso = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).isoformat()
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                title = data.get("title") or proj_id
                sections = data.get("sections", {})
                updated_at = data.get("updated_at") or mtime_iso
                created_at = data.get("created_at") or mtime_iso

                results.append({
                    "project_id": proj_id,
                    "title": title,
                    "sections_count": len(sections),
                    "updated_at": updated_at,
                    "created_at": created_at,
                    "file_path": str(state_file),
                    "mtime": mtime,
                })
            except Exception:
                continue

        # Sort descending by updated_at (newest first)
        results.sort(key=lambda x: (x.get("updated_at") or "", x.get("mtime") or 0.0), reverse=True)
        return results


_GLOBAL_STATE_STORE: Optional[StateStore] = None
_STORE_LOCK = threading.Lock()


def get_state_store() -> StateStore:
    global _GLOBAL_STATE_STORE
    with _STORE_LOCK:
        if _GLOBAL_STATE_STORE is None:
            _GLOBAL_STATE_STORE = StateStore()
        return _GLOBAL_STATE_STORE

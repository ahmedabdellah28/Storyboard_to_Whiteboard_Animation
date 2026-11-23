"""Isolated Run Manager, Checkpoint Persistence, Resume & Rollback for AION CLI."""
from __future__ import annotations

import json
import shutil
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from core.aion.contracts import PIPELINE_STAGES
from core.state.state_store import StateStore
from core.state.transitions import TaskLifecycleStatus
from core.validation.recovery import CrashReconciliationEngine


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


class IsolatedRunManager:
    """Manages non-destructive run folders (`exports/runs/<run_id>/`), checkpoints, resume & rollback."""

    def __init__(self, proj_dir: Path, project_name: str) -> None:
        self.proj_dir = Path(proj_dir)
        self.project_name = project_name
        self.runs_root = self.proj_dir / "exports" / "runs"
        self._state_store: Optional[StateStore] = None

    @property
    def state_store(self) -> StateStore:
        if self._state_store is None:
            self._state_store = StateStore(base_dir=self.proj_dir / "state")
        return self._state_store

    def list_runs(self) -> List[str]:
        if not self.runs_root.is_dir():
            return []
        return sorted(
            [p.name for p in self.runs_root.iterdir() if p.is_dir() and (p / "run_manifest.json").is_file()]
        )

    def get_latest_run_id(self) -> Optional[str]:
        ptr = self.runs_root / "latest_run.json"
        if ptr.is_file():
            try:
                rid = json.loads(ptr.read_text(encoding="utf-8")).get("run_id")
                if rid and (self.runs_root / rid).is_dir():
                    return rid
            except Exception:
                pass
        runs = self.list_runs()
        return runs[-1] if runs else None

    def allocate_run_id(self, requested: Optional[str] = None, resume: bool = False) -> str:
        if requested:
            return requested
        if resume:
            latest = self.get_latest_run_id()
            if latest:
                return latest
        stamp = datetime.now().strftime("run_%Y%m%d_%H%M%S")
        cand = stamp
        idx = 1
        while (self.runs_root / cand).exists():
            idx += 1
            cand = f"{stamp}_{idx:02d}"
        return cand

    def run_dir(self, run_id: str) -> Path:
        return self.runs_root / run_id

    def manifest_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "run_manifest.json"

    def section_out_dir(self, run_id: str, sec_id: str) -> Path:
        return self.run_dir(run_id) / "sections" / sec_id

    def section_work_dir(self, run_id: str, sec_id: str) -> Path:
        return self.run_dir(run_id) / "work" / sec_id

    def section_qa_dir(self, run_id: str, sec_id: str) -> Path:
        return self.run_dir(run_id) / "qa" / sec_id

    def init_or_load_run(self, run_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        rdir = self.run_dir(run_id)
        rdir.mkdir(parents=True, exist_ok=True)
        mpath = self.manifest_path(run_id)
        if mpath.is_file():
            data = json.loads(mpath.read_text(encoding="utf-8"))
        else:
            data = {
                "schema_version": "aion.run_manifest.v1",
                "run_id": run_id,
                "project": self.project_name,
                "created_at": _utc_now(),
                "updated_at": _utc_now(),
                "status": "RUNNING",
                "config": config or {},
                "sections": {},
                "merge": {"status": "PENDING", "output": None, "updated_at": None},
            }
            _atomic_write_json(mpath, data)
        # Reconcile any orphaned state entries from an abrupt crash using core recovery engine
        pstate = self.state_store.load_state(self.project_name)
        if pstate.sections:
            rep = CrashReconciliationEngine.reconcile_on_startup(pstate, base_project_dir=self.proj_dir)
            if rep.reconciled_tasks_count > 0:
                self.state_store.save_state(pstate)
        self._set_latest_pointer(run_id)
        return data

    def _set_latest_pointer(self, run_id: str) -> None:
        _atomic_write_json(
            self.runs_root / "latest_run.json",
            {"run_id": run_id, "updated_at": _utc_now()},
        )

    def get_stage_status(self, run_id: str, sec_id: str, stage: str) -> str:
        mpath = self.manifest_path(run_id)
        if not mpath.is_file():
            return "PENDING"
        data = json.loads(mpath.read_text(encoding="utf-8"))
        if stage == "merge":
            return data.get("merge", {}).get("status", "PENDING")
        return data.get("sections", {}).get(sec_id, {}).get("stages", {}).get(stage, {}).get("status", "PENDING")

    def mark_stage(
        self,
        run_id: str,
        sec_id: Optional[str],
        stage: str,
        status: str,
        outputs: Optional[List[str]] = None,
        error: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        data = self.init_or_load_run(run_id)
        data["updated_at"] = _utc_now()
        entry = {
            "status": status,
            "outputs": outputs or [],
            "error": error,
            "metrics": metrics or {},
            "updated_at": _utc_now(),
        }
        if stage == "merge" or sec_id is None:
            data["merge"] = entry
        else:
            sec_entry = data["sections"].setdefault(sec_id, {"stages": {}})
            sec_entry["stages"][stage] = entry
        _atomic_write_json(self.manifest_path(run_id), data)

        # Mirror lifecycle state into core StateStore
        if sec_id:
            pstate = self.state_store.load_state(self.project_name)
            task_id = f"{run_id}:{stage}"
            if status == "RUNNING":
                pstate.mark_task_started(sec_id, task_id, name=stage)
            elif status == "COMPLETED":
                pstate.mark_task_started(sec_id, task_id, name=stage)
                pstate.mark_task_completed(sec_id, task_id, artifact_hash=run_id)
            elif status == "FAILED":
                pstate.mark_task_started(sec_id, task_id, name=stage)
                pstate.mark_task_failed(sec_id, task_id, error=error or "failed")
            self.state_store.save_state(pstate)

    def completed_stages(self, run_id: str, sec_id: str) -> List[str]:
        mpath = self.manifest_path(run_id)
        if not mpath.is_file():
            return []
        data = json.loads(mpath.read_text(encoding="utf-8"))
        stages = data.get("sections", {}).get(sec_id, {}).get("stages", {})
        return [s for s in PIPELINE_STAGES if stages.get(s, {}).get("status") == "COMPLETED"]

    def resolve_resume_stage(self, run_id: str, sec_id: str) -> str:
        """Returns the earliest stage not yet COMPLETED in this isolated run."""
        done = set(self.completed_stages(run_id, sec_id))
        for st in PIPELINE_STAGES:
            if st == "merge":
                continue
            if st not in done:
                return st
        return "qa"

    @contextmanager
    def stage_transaction(
        self,
        run_id: str,
        sec_id: Optional[str],
        stage: str,
        watch_paths: Optional[List[Path]] = None,
        rollback_on_fail: bool = True,
    ) -> Generator[None, None, None]:
        """Snapshots existing watched files before stage execution and restores/cleans on error."""
        rb_dir = self.run_dir(run_id) / ".rollback" / f"{sec_id or 'project'}_{stage}_{int(time.time()*1000)}"
        existed: Dict[Path, Optional[Path]] = {}
        for p in watch_paths or []:
            p = Path(p)
            if p.exists():
                rb_dir.mkdir(parents=True, exist_ok=True)
                bak = rb_dir / p.name
                if p.is_file():
                    shutil.copy2(p, bak)
                    existed[p] = bak
                elif p.is_dir():
                    shutil.copytree(p, bak, dirs_exist_ok=True)
                    existed[p] = bak
            else:
                existed[p] = None

        self.mark_stage(run_id, sec_id, stage, "RUNNING")
        try:
            yield
        except Exception as exc:
            if rollback_on_fail:
                self._apply_rollback(existed)
            self.mark_stage(run_id, sec_id, stage, "FAILED", error=str(exc))
            shutil.rmtree(rb_dir, ignore_errors=True)
            raise
        else:
            shutil.rmtree(rb_dir, ignore_errors=True)

    @staticmethod
    def _apply_rollback(existed: Dict[Path, Optional[Path]]) -> None:
        for orig, bak in existed.items():
            try:
                if bak is None:
                    if orig.is_file():
                        orig.unlink(missing_ok=True)
                    elif orig.is_dir():
                        shutil.rmtree(orig, ignore_errors=True)
                else:
                    if bak.is_file():
                        orig.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(bak, orig)
                    elif bak.is_dir():
                        if orig.exists():
                            shutil.rmtree(orig, ignore_errors=True)
                        shutil.copytree(bak, orig)
            except Exception:
                pass

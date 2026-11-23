"""Central production orchestrator for managing section lifecycles and parallel batch runs."""


from __future__ import annotations
from typing import Any
import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

from core.config.settings import PROJECT_ROOT, SECTIONS_DIR
from core.orchestration.resource_pools import get_resource_manager
from core.orchestration.section_worker import SectionWorker
from core.state.project_state import ProjectState
from core.state.state_store import StateStore, get_state_store
from core.state.transitions import LifecycleStatus
from core.telemetry.reporter import print_pipeline_summary
from core.telemetry.timer import TaskTimer


class ProductionOrchestrator:
    """Central orchestrator for whiteboard animation video production."""

    def __init__(
        self,
        project_id: str = "wealth_classes_documentary",
        sections_dir: Optional[Path] = None,
        state_store: Optional[StateStore] = None,
    ) -> None:
        self.project_id = project_id
        self.state_store = state_store or get_state_store()
        self.resource_manager = get_resource_manager()

        if sections_dir is not None:
            self.sections_dir = Path(sections_dir)
        else:
            state = self.state_store.load_state(project_id)
            if state and state.metadata and state.metadata.get("project_path"):
                cand = Path(state.metadata["project_path"]) / "sections"
                self.sections_dir = cand
            elif (SECTIONS_DIR / project_id).is_dir():
                self.sections_dir = SECTIONS_DIR / project_id
            else:
                self.sections_dir = SECTIONS_DIR

    def discover_sections(self) -> List[Path]:
        """Automatically find all valid section folders in the sections directory."""
        if not self.sections_dir.is_dir():
            return []

        candidates = []
        for p in sorted(self.sections_dir.iterdir()):
            if p.is_dir() and (p / "storyboard.png").exists() or (p / "script.txt").exists():
                candidates.append(p)
        return candidates

    def resolve_section_path(self, section_name_or_path: str) -> Path:
        """Resolve a section name (e.g. '03', '03_working_poor') or full path to a directory."""
        cand = Path(section_name_or_path).resolve()
        if cand.is_dir():
            return cand

        all_secs = self.discover_sections()

        # 1. Exact match
        for p in all_secs:
            if p.name.lower() == section_name_or_path.lower():
                return p

        # 2. Prefix match
        matches = [p for p in all_secs if p.name.startswith(f"{section_name_or_path}_")]
        if matches:
            if len(matches) > 1 and "wealth" in self.project_id.lower():
                doc_matches = [
                    p for p in matches
                    if not any(f in p.name for f in ["apple", "kiwi", "lemon", "pineapple", "pomegranate", "mango", "dates"])
                ]
                if doc_matches:
                    return doc_matches[0]
            return matches[0]

        # Fallback to direct path concatenation
        direct = self.sections_dir / section_name_or_path
        if direct.is_dir():
            return direct

        raise FileNotFoundError(f"Could not find section matching: {section_name_or_path}")

    def run_section(
        self,
        section_name_or_path: str,
        force_whisper: bool = False,
        title: Optional[str] = None,
        force_all: bool = False,
        force_render: bool = False,
        cancel_token: Optional[Any] = None,
    ) -> str:
        """Execute production pipeline for a single section."""
        sec_path = self.resolve_section_path(section_name_or_path)
        print(f"\n================================================================================")
        print(f"🎬 [Orchestrator] Starting Section: {sec_path.name}")
        print(f"================================================================================")

        if force_render:
            final_video = sec_path / "final_whiteboard_1080p.mp4"
            if final_video.exists():
                try:
                    final_video.unlink()
                except Exception:
                    pass

        worker = SectionWorker(
            section_path=sec_path,
            project_id=self.project_id,
            title=title,
            state_store=self.state_store,
            cancel_token=cancel_token,
        )
        return worker.run(
            force_whisper=force_whisper,
            force_all=(force_all or force_render),
            cancel_token=cancel_token,
        )

    def run_project(
        self,
        max_concurrent_sections: int = 2,
        force_whisper: bool = False,
        force_all: bool = False,
        force_render: bool = False,
    ) -> Dict[str, str]:
        """Execute all discovered sections with bounded concurrency and resource gating."""
        sections = self.discover_sections()
        if not sections:
            print(f"⚠️ [Orchestrator] No sections found in {self.sections_dir}")
            return {}

        print(f"\n================================================================================")
        print(f"🚀 [Orchestrator] Executing Project: {self.project_id}")
        print(f"  • Total Sections    : {len(sections)}")
        print(f"  • Max Concurrency   : {max_concurrent_sections} sections")
        print(f"================================================================================")

        state = self.state_store.load_state(self.project_id)
        state.transition_to(LifecycleStatus.RUNNING)
        self.state_store.save_state(state)

        results: Dict[str, str] = {}
        failures: Dict[str, str] = {}

        with ThreadPoolExecutor(max_workers=max_concurrent_sections) as pool:
            futures = {
                pool.submit(self.run_section, str(sec), force_whisper): sec.name
                for sec in sections
            }

            for future in as_completed(futures):
                sec_name = futures[future]
                try:
                    video_output = future.result()
                    results[sec_name] = video_output
                    print(f"  ✅ [Orchestrator] Section {sec_name} COMPLETED -> {video_output}", flush=True)
                except Exception as e:
                    failures[sec_name] = str(e)
                    print(f"  ❌ [Orchestrator] Section {sec_name} FAILED: {e}", flush=True)

        if not failures:
            state.transition_to(LifecycleStatus.COMPLETED)
        else:
            state.transition_to(LifecycleStatus.FAILED)
        self.state_store.save_state(state)

        print_pipeline_summary(title=f"Project {self.project_id} Run Summary")
        return results

    def assemble_master_documentary(
        self,
        output_dir: Optional[Path] = None,
        output_filename: str = "Full_Wealth_Classes_Documentary_1080p.mp4",
    ) -> str:
        """Assembles all section deliverable videos into the final master documentary film."""
        deliv_dir = output_dir or (PROJECT_ROOT / "output_animations" / self.project_id / "deliverables")
        sections_deliv_dir = deliv_dir / "sections"
        deliv_dir.mkdir(parents=True, exist_ok=True)

        if not sections_deliv_dir.is_dir():
            raise FileNotFoundError(f"No sections deliverable directory found at: {sections_deliv_dir}")

        video_files = sorted(list(sections_deliv_dir.glob("*_Whiteboard_1080p.mp4")))
        if not video_files:
            raise FileNotFoundError(f"No section deliverable videos found in {sections_deliv_dir}")

        print("\n" + "=" * 80)
        print(f"🎬 [Orchestrator] Assembling Master Documentary: {len(video_files)} Sections")
        print("=" * 80)

        concat_list_file = deliv_dir / "concat_video_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for v_path in video_files:
                f.write(f"file '{v_path.as_posix()}'\n")

        final_video_path = deliv_dir / output_filename
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(final_video_path),
        ]

        with TaskTimer(f"{self.project_id}_master_assembly", category="master_assembly"):
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"FFmpeg assembly failed: {res.stderr}")

        print(f"  ✅ [Orchestrator] Master Documentary Assembled -> {final_video_path}", flush=True)
        return str(final_video_path)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Central Production Platform Orchestrator")
    parser.add_argument("--section", type=str, default=None, help="Target section name or directory")
    parser.add_argument("--project", type=str, default="wealth_classes_documentary", help="Project identifier")
    parser.add_argument("--parallel", type=int, default=2, help="Max concurrent sections (default: 2)")
    parser.add_argument("--force-whisper", action="store_true", help="Force Whisper re-transcription")
    parser.add_argument("--force-all", action="store_true", help="Force re-execution of all DAG tasks")
    parser.add_argument("--force-render", action="store_true", help="Force re-rendering video even if cached")
    parser.add_argument("--assemble", action="store_true", help="Assemble final master documentary from sections")
    args = parser.parse_args()

    orchestrator = ProductionOrchestrator(project_id=args.project)

    if args.assemble:
        orchestrator.assemble_master_documentary()
    elif args.section:
        orchestrator.run_section(
            args.section,
            force_whisper=args.force_whisper,
            force_all=args.force_all,
            force_render=args.force_render,
        )
    else:
        orchestrator.run_project(
            max_concurrent_sections=args.parallel,
            force_whisper=args.force_whisper,
            force_all=args.force_all,
            force_render=args.force_render,
        )


if __name__ == "__main__":
    main()

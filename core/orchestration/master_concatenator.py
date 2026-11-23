"""Master Video Concatenator and Multi-Section Assembly Engine.

Sequentially stitches all validated section deliverables into a unified 1080p
master whiteboard film, generating chapter markers and master manifest.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import cv2

from core.config.settings import PROJECT_ROOT
from core.state.project_state import ProjectState, SectionState
from core.state.state_store import StateStore, get_state_store


class MasterConcatenator:
    """Multi-section assembly engine producing the final master documentary film."""

    def __init__(
        self,
        project_id: str,
        state_store: Optional[StateStore] = None,
        output_dir: Optional[Path] = None,
    ) -> None:
        self.project_id = project_id
        self.state_store = state_store or get_state_store()
        self.output_dir = output_dir or (PROJECT_ROOT / "output_animations" / project_id / "deliverables")

    def assemble(
        self,
        progress_cb: Optional[Callable[[str, float], None]] = None,
        output_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Assemble all completed section videos into master film with chapter markers."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = output_filename or f"Full_{self.project_id}_Master_1080p.mp4"
        out_video_path = self.output_dir / filename

        if progress_cb:
            progress_cb("Discovering and ordering project sections...", 0.1)

        # 1. Load project state and sort sections by sequence index
        project = self.state_store.load_state(self.project_id)
        if not project:
            raise ValueError(f"Project '{self.project_id}' not found in state store.")

        sections = sorted(project.sections.values(), key=lambda s: s.sequence_index)
        if not sections:
            raise ValueError(f"Project '{self.project_id}' has no sections to assemble.")

        # 2. Locate deliverable video files for each section
        section_entries: List[Dict[str, Any]] = []
        current_time = 0.0

        for sec in sections:
            video_file = self._find_section_video(project, sec)
            if not video_file or not video_file.exists():
                raise FileNotFoundError(
                    f"Deliverable video missing for section '{sec.section_id}'. "
                    f"Please render section before assembling master."
                )

            # Read duration via OpenCV
            cap = cv2.VideoCapture(str(video_file))
            fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0.0
            cap.release()

            entry = {
                "section_id": sec.section_id,
                "title": sec.title or sec.section_id,
                "sequence_index": sec.sequence_index,
                "video_path": str(video_file),
                "duration": round(duration, 3),
                "start_time": round(current_time, 3),
                "end_time": round(current_time + duration, 3),
            }
            section_entries.append(entry)
            current_time += duration

        if progress_cb:
            progress_cb(f"Preparing FFmpeg concat demuxer for {len(section_entries)} sections...", 0.3)

        # 3. Write concat list file
        concat_list = self.output_dir / "concat_master_list.txt"
        with open(concat_list, "w", encoding="utf-8") as f:
            for entry in section_entries:
                p = Path(entry["video_path"]).as_posix()
                f.write(f"file '{p}'\n")

        if progress_cb:
            progress_cb("Running FFmpeg stream concatenation...", 0.6)

        # 4. Execute FFmpeg concatenation
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(out_video_path),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            # Fallback to re-encoding if streams have mismatched codecs/sample rates
            if progress_cb:
                progress_cb("Mismatched streams detected, applying unified re-encode...", 0.7)
            cmd_reencode = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                str(out_video_path),
            ]
            res_re = subprocess.run(cmd_reencode, capture_output=True, text=True)
            if res_re.returncode != 0:
                raise RuntimeError(f"FFmpeg master concatenation failed: {res_re.stderr}")

        if progress_cb:
            progress_cb("Generating Master Deliverable Manifest & Chapter Markers...", 0.9)

        # 5. Build and save Master Manifest
        manifest = {
            "project_id": self.project_id,
            "master_video_path": str(out_video_path),
            "filename": filename,
            "total_duration": round(current_time, 3),
            "sections_count": len(section_entries),
            "chapters": section_entries,
            "assembled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        manifest_path = self.output_dir / "master_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        if progress_cb:
            progress_cb("Master film successfully created!", 1.0)

        return manifest

    def _find_section_video(self, project: ProjectState, sec: SectionState) -> Optional[Path]:
        """Locates the final deliverable video for a given section."""
        # 1. Check project path metadata
        proj_path = Path(project.metadata.get("project_path", "")) if project.metadata else None
        candidates = []
        if proj_path and proj_path.is_dir():
            s_dir = proj_path / "sections" / sec.section_id
            candidates.extend([
                s_dir / "final_whiteboard_1080p.mp4",
                s_dir / "deliverables" / f"{sec.section_id}_Whiteboard_1080p.mp4",
                s_dir / "video.mp4",
            ])

        # 2. Check standard deliverable outputs
        deliv_dir = PROJECT_ROOT / "output_animations" / self.project_id / "deliverables" / "sections"
        candidates.extend([
            deliv_dir / f"{sec.section_id}_Whiteboard_1080p.mp4",
            deliv_dir / f"{sec.section_id}.mp4",
        ])

        for c in candidates:
            if c.exists() and c.stat().st_size > 0:
                return c

        return None

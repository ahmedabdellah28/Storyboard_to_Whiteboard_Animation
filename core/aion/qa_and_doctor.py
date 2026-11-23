"""Stage 12: Automated QA Verification + Contact Sheet + Host Environment Doctor.

Reuses `core.validation.environment_doctor.EnvironmentDoctor`,
`core.validation.post_render_qa.PostRenderQAEngine`, and `core.api.key_pool`.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw

from core.aion.capability_prober import find_effectcraft_cli
from core.aion.contracts import audit_scene_graph
from core.aion.extract_stage import find_photocraft_cli
from core.validation.environment_doctor import EnvironmentDoctor
from core.validation.post_render_qa import PostRenderQAEngine

ROOT_DIR = Path(__file__).resolve().parents[2]


def run_doctor_check() -> Dict[str, Any]:
    """Probes host binaries (FFmpeg, EffectCraft, PhotoCraft), GPU encoders, storage & API keys."""
    diag = EnvironmentDoctor.run_full_diagnosis()
    ec_bin = find_effectcraft_cli() or (ROOT_DIR / "craftApp" / "effectcraft" / "target" / "release" / "effectcraft-cli.exe")
    pc_bin = find_photocraft_cli() or (ROOT_DIR / "craftApp" / "photocraft" / "target" / "release" / "photocraft-cli.exe")
    ac_bin = ROOT_DIR / "craftApp" / "anicraft" / "target" / "release" / "anicraft-cli.exe"

    key_count = 0
    try:
        from core.config.env_loader import get_gemini_api_keys
        key_count = len(get_gemini_api_keys())
    except Exception:
        pass

    return {
        "is_healthy": diag.is_healthy and ec_bin.is_file(),
        "python_version": diag.python_version,
        "free_disk_gb": diag.free_disk_gb,
        "ffmpeg": {
            "available": diag.ffmpeg_available,
            "version": diag.ffmpeg_version,
            "hardware_encoder": diag.hardware_encoder,
            "available_encoders": diag.available_encoders,
        },
        "craftapp": {
            "effectcraft_cli": {"exists": ec_bin.is_file(), "path": str(ec_bin)},
            "photocraft_cli": {"exists": pc_bin.is_file(), "path": str(pc_bin)},
            "anicraft_cli": {"exists": ac_bin.is_file(), "path": str(ac_bin)},
        },
        "gemini_api_keys_loaded": key_count,
        "issues": diag.issues,
        "recommendations": diag.recommendations,
    }


def extract_qa_contact_sheet(
    mp4_path: Path,
    qa_dir: Path,
    qa_times: List[float],
) -> Path:
    """Extracts 10 timestamped key frames into `qa_contact_sheet.png`."""
    qa_dir.mkdir(parents=True, exist_ok=True)
    thumbs: List[Image.Image] = []
    for idx_q, qt in enumerate(qa_times[:10]):
        q_png = qa_dir / f"qa_{idx_q:02d}_{qt:05.2f}s.png"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{qt:.2f}", "-i", str(mp4_path), "-frames:v", "1", str(q_png)],
            capture_output=True,
            check=True,
        )
        im = Image.open(q_png).convert("RGB").resize((640, 360), Image.Resampling.LANCZOS)
        d = ImageDraw.Draw(im)
        d.rectangle([(8, 8), (150, 34)], fill=(15, 23, 42))
        d.text((16, 14), f"t = {qt:.2f}s", fill=(255, 255, 255))
        thumbs.append(im)

    rows = max(1, (len(thumbs) + 1) // 2)
    sheet = Image.new("RGB", (640 * 2, 360 * rows), (15, 15, 20))
    for i, th in enumerate(thumbs):
        sheet.paste(th, ((i % 2) * 640, (i // 2) * 360))
    sheet_path = qa_dir / "qa_contact_sheet.png"
    sheet.save(sheet_path)
    return sheet_path


def run_qa_stage(
    proj_dir: Path,
    sec_id: str,
    mp4_path: Path,
    audio_path: Optional[Path],
    qa_dir: Path,
) -> Dict[str, Any]:
    """Runs Scene Graph contrast audit + PostRenderQAEngine inspection + 10-frame Contact Sheet."""
    sg_path = proj_dir / "director" / sec_id / "scene_graph.json"
    sg_issues: List[str] = []
    qa_times: List[float] = []
    dur = 30.0
    if sg_path.is_file():
        sg = json.loads(sg_path.read_text(encoding="utf-8"))
        _ok, sg_issues = audit_scene_graph(sg, auto_fix=False)
        dur = float(sg.get("source_timeline", {}).get("duration_sec", dur) or dur)
        qa_times = [float(t) for t in sg.get("qa_times", [])]
    if not qa_times:
        qa_times = [round(dur * k, 2) for k in (0.05, 0.14, 0.24, 0.34, 0.44, 0.54, 0.64, 0.74, 0.84, 0.94)]

    qa_dir.mkdir(parents=True, exist_ok=True)
    report_path = qa_dir / "qa_report.json"
    qa_engine = PostRenderQAEngine()
    qa_rep = qa_engine.inspect(
        video_path=mp4_path,
        audio_path=audio_path if (audio_path and audio_path.is_file()) else None,
        section_id=sec_id,
        output_report_path=report_path,
    )
    sheet_path = extract_qa_contact_sheet(mp4_path, qa_dir, qa_times) if mp4_path.is_file() else None
    passed = qa_rep.overall_status.value in ("PASS", "WARNING")
    return {
        "ok": passed,
        "overall_status": qa_rep.overall_status.value,
        "checks": [{"id": c.check_id, "status": c.status.value, "details": c.details} for c in qa_rep.checks],
        "scene_graph_issues": sg_issues,
        "contact_sheet": str(sheet_path) if sheet_path else None,
        "report_path": str(report_path),
    }

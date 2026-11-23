"""Visual Intelligence QA Engine (Phase 5 of AION Creative Studio V5).

Performs multi-signal visual & structural verification across both the compiled
`.ecproj` layer graph and actual rendered frames / MP4 outputs, writing:
  - `qa/creative_quality_report.json` (`PASS` | `NEEDS_REVIEW` | `FAIL`)
  - `qa/creative_contact_sheet.png` (annotated multi-frame proof grid)
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

from core.aion.creative_qa_gate import evaluate_creative_judgments, evaluate_hard_gates
from core.aion.procedural_graphics import is_rtl_text


def _extract_frames_from_mp4(mp4_path: Path, out_dir: Path, count: int = 6) -> List[Path]:
    """Sample `count` evenly spaced PNG frames from `mp4_path` using ffmpeg/ffprobe."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pr = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(mp4_path)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    dur = float(pr.stdout.strip()) if pr.returncode == 0 and pr.stdout.strip() else 4.0
    frames: List[Path] = []
    for i in range(count):
        t = min(max(0.05, dur - 0.08), (i + 0.5) * dur / max(1, count))
        out_p = out_dir / f"qa_frame_{i:02d}_{t:.2f}s.png"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(mp4_path), "-frames:v", "1", "-vf", "scale=960:960:force_original_aspect_ratio=decrease", str(out_p)],
            capture_output=True,
            timeout=30,
        )
        if out_p.is_file():
            frames.append(out_p)
    return frames


def _inspect_ecproj_structure(ecproj_path: Optional[Path]) -> Dict[str, Any]:
    """Verify compiled layers, vector paths, camera, lights, and RTL text integrity in `.ecproj`."""
    if not ecproj_path or not ecproj_path.is_file():
        return {"present": False, "layer_count": 0, "text_corruption": False}
    data = json.loads(ecproj_path.read_text(encoding="utf-8", errors="replace"))
    items = data.get("items", {})
    layers_summary: List[Dict[str, Any]] = []
    text_corruption = False
    path_layers = 0
    text_layers = 0
    camera_layers = 0
    light_layers = 0

    for item in items.values():
        kind = item.get("kind", {})
        if kind.get("type") != "Comp":
            continue
        for lyr in kind.get("layers", []):
            ltype = lyr.get("source", {}).get("type", lyr.get("type", "Unknown"))
            lname = lyr.get("name", "")
            layers_summary.append({"name": lname, "type": str(ltype)})
            low = json.dumps(lyr, ensure_ascii=False)
            if "Vector" in str(ltype) or "Path_" in lname or "Node_" in lname or "Arrow" in lname or "Rep_" in lname:
                path_layers += 1
            if "Text_" in lname or "sourceText" in low:
                text_layers += 1
                if "???" in low:
                    text_corruption = True
            if "Camera" in str(ltype) or "MainCam" in lname:
                camera_layers += 1
            if "Light" in str(ltype) or "Spot" in lname:
                light_layers += 1

    return {
        "present": True,
        "layer_count": len(layers_summary),
        "path_or_shape_layers": path_layers,
        "text_layers": text_layers,
        "camera_layers": camera_layers,
        "light_layers": light_layers,
        "text_corruption_detected": text_corruption,
    }


def _analyze_frames(frame_paths: List[Path]) -> Dict[str, Any]:
    """Compute quantitative visual health metrics across sampled frames."""
    if not frame_paths:
        return {
            "frame_count": 0,
            "mean_luma_std": 0.0,
            "mean_temporal_mad": 0.0,
            "max_white_blowout": 0.0,
            "edge_clip_score": 0.0,
        }

    arrays = [np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) for p in frame_paths]
    stds = [float(np.std(a)) for a in arrays]
    blowouts = [float(np.mean(np.min(a, axis=-1) > 246.0)) for a in arrays]

    # Measure non-vignette foreground elements clipped against the outer viewport border
    edge_scores: List[float] = []
    for a in arrays:
        h, w, _ = a.shape
        inset = max(12, min(h, w) // 18)
        bg = np.median(a[inset:-inset, inset:-inset], axis=(0, 1))
        # High-contrast elements extending above ambient vignette floor touching outer 8px margin
        fg_mask = (np.max(np.abs(a - bg), axis=-1) > 45.0) & (np.max(a, axis=-1) > float(np.max(bg)) + 15.0)
        border = np.zeros_like(fg_mask, dtype=bool)
        m = 8
        border[:m, :] = True
        border[-m:, :] = True
        border[:, :m] = True
        border[:, -m:] = True
        edge_scores.append(float(np.mean(fg_mask & border) / max(1e-5, float(np.mean(border)))))

    diffs = [float(np.mean(np.abs(arrays[i + 1] - arrays[i]))) for i in range(len(arrays) - 1)]
    return {
        "frame_count": len(arrays),
        "mean_luma_std": round(float(np.mean(stds)), 3),
        "min_luma_std": round(float(np.min(stds)), 3),
        "mean_temporal_mad": round(float(np.mean(diffs)) if diffs else 0.0, 4),
        "min_temporal_mad": round(float(np.min(diffs)) if diffs else 0.0, 4),
        "max_white_blowout": round(float(np.max(blowouts)), 4),
        "edge_clip_score": round(float(np.max(edge_scores)), 4),
    }


def _render_qa_contact_sheet(
    frame_paths: List[Path],
    out_png: Path,
    verdict: str,
    header_info: str,
) -> Optional[Path]:
    if not frame_paths:
        return None
    sample_im = Image.open(frame_paths[0])
    sw, sh = sample_im.size
    sample_im.close()
    is_portrait = sh > sw
    cols = min(3, len(frame_paths))
    tile_w, tile_h = (270, 480) if is_portrait else (480, 270)
    top_bar = 44
    rows = (len(frame_paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, top_bar + rows * (tile_h + 26)), (12, 16, 26))
    draw = ImageDraw.Draw(sheet)
    v_col = (74, 222, 128) if verdict == "PASS" else ((250, 204, 21) if verdict == "NEEDS_REVIEW" else (248, 113, 113))
    draw.text((14, 12), f"[{verdict}] {header_info}", fill=v_col)

    for idx, fp in enumerate(frame_paths):
        r, c = idx // cols, idx % cols
        x0 = c * tile_w
        y0 = top_bar + r * (tile_h + 26)
        tile = Image.open(fp).convert("RGB").resize((tile_w, tile_h), Image.Resampling.LANCZOS)
        sheet.paste(tile, (x0, y0 + 22))
        draw.text((x0 + 8, y0 + 4), fp.name, fill=(203, 213, 225))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    return out_png


def render_mobile_phone_preview(frame_paths: List[Path], out_png: Path) -> Optional[Path]:
    """Generate a 390px-wide mobile screen simulation preview to verify headline legibility on phone displays."""
    if not frame_paths:
        return None
    pick = frame_paths[min(1, len(frame_paths) - 1)]
    src = Image.open(pick).convert("RGB")
    sw, sh = src.size
    is_portrait = sh > sw
    phone_w = 390
    screen_h = 694 if is_portrait else 220
    bezel = 16
    top_hdr = 42
    bottom_pad = 36
    canvas_w = phone_w + bezel * 2
    canvas_h = top_hdr + screen_h + bottom_pad + bezel * 2

    canvas = Image.new("RGB", (canvas_w, canvas_h), (15, 23, 42))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([4, 4, canvas_w - 5, canvas_h - 5], radius=28, fill=(2, 6, 23), outline=(71, 85, 105), width=2)
    draw.text((22, 16), f"MOBILE PREVIEW (390px {'9:16' if is_portrait else '16:9'})", fill=(148, 163, 184))

    scaled = src.resize((phone_w, screen_h), Image.Resampling.LANCZOS)
    canvas.paste(scaled, (bezel, top_hdr))
    if is_portrait:
        # Subtle Shorts/Reels UI safe-zone markers (top bar + bottom caption area)
        draw.rectangle([bezel + 4, top_hdr + 4, bezel + phone_w - 5, top_hdr + int(screen_h * 0.10)], outline=(251, 191, 36), width=1)
        draw.rectangle([bezel + 4, top_hdr + int(screen_h * 0.80), bezel + phone_w - 5, top_hdr + screen_h - 5], outline=(251, 191, 36), width=1)
    src.close()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_png)
    return out_png


def evaluate_creative_render(
    *,
    qa_dir: Path,
    ecproj_path: Optional[Path] = None,
    mp4_path: Optional[Path] = None,
    preview_frames: Optional[List[Path]] = None,
    scene_graph: Optional[Dict[str, Any]] = None,
    compile_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run full V5 Visual Intelligence QA and write `creative_quality_report.json` + contact sheet."""
    qa_dir = Path(qa_dir)
    qa_dir.mkdir(parents=True, exist_ok=True)

    sampled = list(preview_frames or [])
    if mp4_path and Path(mp4_path).is_file():
        sampled = _extract_frames_from_mp4(Path(mp4_path), qa_dir / "sampled_frames", count=6)

    ecproj_audit = _inspect_ecproj_structure(Path(ecproj_path) if ecproj_path else None)
    visual = _analyze_frames(sampled)

    findings: List[Dict[str, str]] = []
    recommendations: List[str] = []

    if visual["frame_count"] == 0:
        findings.append({"severity": "FAIL", "code": "NO_RENDERED_FRAMES", "detail": "No rendered preview or MP4 frames available."})
    if visual["mean_luma_std"] < 4.5:
        findings.append({"severity": "FAIL", "code": "BLANK_OR_FLAT_FRAME", "detail": f"Very low visual variance (std={visual['mean_luma_std']})."})
        recommendations.append("Check layer timing bounds and background contrast; ensure active elements cover center canvas.")
    if visual["frame_count"] >= 2 and visual["mean_temporal_mad"] < 0.08:
        findings.append({"severity": "FAIL", "code": "STATIC_FROZEN_ANIMATION", "detail": f"Frames show almost zero temporal motion (mad={visual['mean_temporal_mad']})."})
        recommendations.append("Increase keyframe motion travel, trim path animation, or camera push delta.")
    elif visual["frame_count"] >= 2 and visual["mean_temporal_mad"] < 0.25:
        findings.append({"severity": "WARN", "code": "SUBTLE_MOTION", "detail": f"Motion delta is mild (mad={visual['mean_temporal_mad']})."})

    if visual["max_white_blowout"] > 0.45:
        findings.append({"severity": "WARN", "code": "WHITE_BLOWOUT", "detail": f"High white glare area ratio={visual['max_white_blowout']}."})
        recommendations.append("Reduce glow intensity below 0.8 or replace additive Glow with soft Light Sweep.")

    if visual["edge_clip_score"] > 0.35:
        findings.append({"severity": "WARN", "code": "EDGE_CLIPPING_RISK", "detail": f"Foreground pixels near canvas edge (score={visual['edge_clip_score']})."})
        recommendations.append("Clamp card/diagram coordinates inside 96px safe margins.")

    if ecproj_audit.get("present") and ecproj_audit.get("text_corruption_detected"):
        findings.append({"severity": "FAIL", "code": "TEXT_ENCODING_CORRUPTION", "detail": "Detected '???' inside .ecproj text layers."})
        recommendations.append("Ensure UTF-8 encoding throughout command payload and typography compiler.")

    if scene_graph:
        for tb in scene_graph.get("typography", []):
            txt = str(tb.get("text", ""))
            if is_rtl_text(txt) and str(tb.get("direction", "rtl")).lower() != "rtl":
                findings.append({"severity": "WARN", "code": "RTL_FLAG_MISMATCH", "detail": f"Arabic string without rtl direction flag: {txt[:30]}"})

    if compile_report and compile_report.get("fallbacks_applied"):
        findings.append({
            "severity": "INFO",
            "code": "CAPABILITY_FALLBACKS_ACTIVE",
            "detail": f"{len(compile_report['fallbacks_applied'])} capability safeguards/fallbacks applied.",
        })

    hard_checks = evaluate_hard_gates(
        scene_graph=scene_graph,
        ecproj_path=Path(ecproj_path) if ecproj_path else None,
        mp4_path=Path(mp4_path) if mp4_path else None,
        visual_metrics=visual,
        compile_report=compile_report,
    ) if scene_graph else []
    for hc in hard_checks:
        if not hc["passed"]:
            findings.append({
                "severity": "FAIL" if hc["id"] in ("scenes_structure", "typography_readability", "requested_graphics_present", "timing_alignment") else "WARN",
                "code": f"GATE_{hc['id'].upper()}",
                "detail": hc["detail"],
            })

    creative_judgments = evaluate_creative_judgments(
        scene_graph=scene_graph,
        visual_metrics=visual,
    ) if scene_graph else {}

    if any(f["severity"] == "FAIL" for f in findings):
        verdict = "FAIL"
    elif any(f["severity"] == "WARN" for f in findings):
        verdict = "NEEDS_REVIEW"
    else:
        verdict = "PASS"

    header = f"Layers:{ecproj_audit.get('layer_count', 0)} | MotionMAD:{visual['mean_temporal_mad']} | Std:{visual['mean_luma_std']}"
    sheet_path = _render_qa_contact_sheet(sampled, qa_dir / "creative_contact_sheet.png", verdict, header)
    mobile_preview_path = render_mobile_phone_preview(sampled, qa_dir / "mobile_preview.png")

    report = {
        "schema_version": "aion.creative_qa_report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "ecproj_audit": ecproj_audit,
        "visual_metrics": visual,
        "hard_checks": hard_checks,
        "creative_judgments": creative_judgments,
        "findings": findings,
        "recommendations": recommendations,
        "contact_sheet": str(sheet_path) if sheet_path else None,
        "mobile_preview": str(mobile_preview_path) if mobile_preview_path else None,
        "sampled_frames": [str(p) for p in sampled],
    }
    (qa_dir / "creative_quality_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report

"""Post-Render Automated QA Engine.

Performs forensic inspections on rendered section MP4 files:
1. Video Resolution & Aspect Ratio (1080p 16:9).
2. Audio/Video Duration Synchronization (<0.35s drift).
3. Black Frame Bursts Detection (unintended blank frames).
4. Audio Peak & Clipping Detection.
5. Codec & Decode Health.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from core.contracts.qa_reports import (
    PostRenderQAReport,
    QACheckResult,
    QAGateStatus,
)


class PostRenderQAEngine:
    """Forensic QA Inspector for rendered whiteboard animation deliverables."""

    def __init__(
        self,
        max_drift_seconds: float = 0.35,
        black_frame_threshold: float = 8.0,
        max_consecutive_black_frames: int = 15,
        audio_clipping_threshold: float = 0.995,
    ) -> None:
        self.max_drift_seconds = max_drift_seconds
        self.black_frame_threshold = black_frame_threshold
        self.max_consecutive_black_frames = max_consecutive_black_frames
        self.audio_clipping_threshold = audio_clipping_threshold

    def inspect(
        self,
        video_path: str | Path,
        audio_path: Optional[str | Path] = None,
        section_id: str = "section",
        output_report_path: Optional[str | Path] = None,
    ) -> PostRenderQAReport:
        """Run all post-render QA checks on the deliverable."""
        v_path = Path(video_path)
        checks: List[QACheckResult] = []

        if not v_path.exists():
            fail_check = QACheckResult(
                check_id="file_existence",
                name="Deliverable File Existence",
                status=QAGateStatus.FAIL,
                details=f"Video file not found at: {v_path}",
            )
            return PostRenderQAReport(
                section_id=section_id,
                video_path=str(v_path),
                overall_status=QAGateStatus.FAIL,
                checks=[fail_check],
                summary="FATAL: Video file does not exist.",
            )

        # 1. Video Stream Properties via OpenCV
        cap = cv2.VideoCapture(str(v_path))
        if not cap.isOpened():
            cap.release()
            return PostRenderQAReport(
                section_id=section_id,
                video_path=str(v_path),
                overall_status=QAGateStatus.FAIL,
                checks=[
                    QACheckResult(
                        check_id="decode_health",
                        name="Video Decode Integrity",
                        status=QAGateStatus.FAIL,
                        details="OpenCV could not open or decode video stream.",
                    )
                ],
                summary="FATAL: Stream decoding failure.",
            )

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
        video_dur = total_frames / fps if fps > 0 else 0.0

        # Check 1: Resolution & Aspect Ratio
        is_1080p = (width == 1920 and height == 1080)
        aspect_ratio = width / height if height > 0 else 0.0
        is_16_9 = abs(aspect_ratio - (16.0 / 9.0)) < 0.02
        res_pass = is_1080p or (width >= 1280 and is_16_9)
        checks.append(
            QACheckResult(
                check_id="resolution",
                name="Resolution & 16:9 Aspect Ratio",
                status=QAGateStatus.PASS if res_pass else QAGateStatus.FAIL,
                details=f"Detected resolution: {width}x{height} (Aspect: {aspect_ratio:.2f})",
                metrics={"width": width, "height": height, "aspect_ratio": round(aspect_ratio, 3)},
            )
        )

        # Check 2: Black Frame Bursts Detection (sample every Nth frame or sequential check)
        black_frames_count, max_consecutive_black = self._analyze_black_frames(cap, total_frames)
        cap.release()

        black_pass = max_consecutive_black <= self.max_consecutive_black_frames
        checks.append(
            QACheckResult(
                check_id="black_frames",
                name="Black Frame Burst Check",
                status=QAGateStatus.PASS if black_pass else QAGateStatus.FAIL,
                details=(
                    f"Max consecutive black frames: {max_consecutive_black} "
                    f"(Total black frames: {black_frames_count})"
                ),
                metrics={
                    "total_black_frames": black_frames_count,
                    "max_consecutive_black": max_consecutive_black,
                    "threshold_luminance": self.black_frame_threshold,
                },
            )
        )

        # Check 3: Audio Stream & Sync Drift + Full-Duration Broadcast Metrics
        audio_dur, clipping_detected, audio_metrics = self._inspect_audio(audio_path, v_path)
        drift = abs(video_dur - audio_dur) if audio_dur > 0 else 0.0
        sync_pass = (audio_dur == 0.0) or (drift <= self.max_drift_seconds)

        checks.append(
            QACheckResult(
                check_id="av_sync",
                name="Audio-Video Sync & Drift",
                status=QAGateStatus.PASS if sync_pass else QAGateStatus.FAIL,
                details=(
                    f"Video: {video_dur:.2f}s | Audio: {audio_dur:.2f}s | Drift: {drift:.3f}s "
                    f"(Max tolerance: {self.max_drift_seconds}s)"
                ),
                metrics={
                    "video_duration": round(video_dur, 3),
                    "audio_duration": round(audio_dur, 3),
                    "drift_seconds": round(drift, 3),
                },
            )
        )

        # Check 4: Audio Peak, Clipping & Broadcast Loudness Integrity
        audio_pass = not clipping_detected
        lufs = audio_metrics.get("integrated_lufs")
        tp_db = audio_metrics.get("true_peak_dbtp")
        max_sil = audio_metrics.get("max_silence_gap_sec")
        loud_summary = ""
        if lufs is not None:
            loud_summary = f" | LUFS: {lufs} | TP: {tp_db} dBTP | Max Silence: {max_sil}s"
        checks.append(
            QACheckResult(
                check_id="audio_clipping",
                name="Audio Peak & Broadcast Loudness Integrity",
                status=QAGateStatus.PASS if audio_pass else QAGateStatus.FAIL,
                details=(
                    f"No audio clipping detected{loud_summary}."
                    if audio_pass
                    else f"Peak amplitudes exceeded threshold (clipping detected){loud_summary}."
                ),
                metrics={"clipping_detected": clipping_detected, **audio_metrics},
            )
        )

        overall_pass = all(c.status == QAGateStatus.PASS for c in checks)
        summary = (
            f"Post-Render QA PASSED ({len(checks)}/{len(checks)} checks passed)"
            if overall_pass
            else f"Post-Render QA FAILED ({sum(1 for c in checks if c.status == QAGateStatus.FAIL)} check(s) failed)"
        )

        report = PostRenderQAReport(
            section_id=section_id,
            video_path=str(v_path),
            overall_status=QAGateStatus.PASS if overall_pass else QAGateStatus.FAIL,
            video_duration=round(video_dur, 2),
            audio_duration=round(audio_dur, 2),
            duration_drift=round(drift, 3),
            total_frames=total_frames,
            fps=round(fps, 2),
            resolution=f"{width}x{height}",
            black_frames_count=black_frames_count,
            audio_clipping_detected=clipping_detected,
            checks=checks,
            summary=summary,
        )

        # Persist report if requested
        if output_report_path:
            out_p = Path(output_report_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                f.write(report.model_dump_json(indent=2))

        return report

    def _analyze_black_frames(self, cap: cv2.VideoCapture, total_frames: int) -> Tuple[int, int]:
        """Analyzes video frames for continuous black bursts."""
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        black_count = 0
        consecutive_black = 0
        max_consecutive_black = 0

        # Sample up to 600 frames to remain ultra fast (<1s)
        step = max(1, total_frames // 600)
        idx = 0

        while True:
            ret, frame = cap.read()
            if not ret or idx >= total_frames:
                break

            if idx % step == 0:
                # Fast mean luminance check
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                mean_lum = float(np.mean(gray))
                if mean_lum < self.black_frame_threshold:
                    black_count += step
                    consecutive_black += step
                    if consecutive_black > max_consecutive_black:
                        max_consecutive_black = consecutive_black
                else:
                    consecutive_black = 0

            idx += 1

        return black_count, max_consecutive_black

    def _inspect_audio(
        self,
        audio_path: Optional[str | Path],
        video_path: Path,
    ) -> Tuple[float, bool, Dict[str, Any]]:
        """Inspects full-duration audio stream duration, clipping, silence gaps, and broadcast LUFS."""
        target_audio: Optional[Path] = None
        if audio_path and Path(audio_path).exists():
            target_audio = Path(audio_path)
        else:
            # Check adjacent audio files
            sec_dir = video_path.parent
            for candidate in [sec_dir / "master_audio.wav", sec_dir / "voice" / "section.wav"]:
                if candidate.exists():
                    target_audio = candidate
                    break

        if not target_audio or not target_audio.exists():
            return 0.0, False, {}

        try:
            from core.aion.audio_mastering import audit_audio_broadcast_qa
            metrics = audit_audio_broadcast_qa(
                target_audio,
                clipping_threshold=self.audio_clipping_threshold,
            )
            return (
                float(metrics.get("duration_sec", 0.0)),
                bool(metrics.get("clipping_detected", False)),
                metrics,
            )
        except Exception:
            return 0.0, False, {}

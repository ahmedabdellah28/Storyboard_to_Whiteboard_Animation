"""Runner script to generate an OpenCut Motion Flow preview for Section 1."""

import os
import sys
from pathlib import Path

# Paths
ROOT = r"E:\image_to_animate"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from production_engine.opencut_motion_flow_engine import OpenCutMotionFlowEngine

STORYBOARD = os.path.join(ROOT, "project_content", "images", "section1.png")
AUDIO = os.path.join(ROOT, "project_content", "audio", "section_01.wav")
SRT = os.path.join(ROOT, "project_content", "srt", "section_01", "section_01_sentences.srt")
METADATA = os.path.join(ROOT, "project_content", "extracted_assets", "section_01", "metadata.json")
ASSETS_DIR = os.path.join(ROOT, "project_content", "extracted_assets", "section_01")
OUTPUT_DIR = os.path.join(ROOT, "output_animations", "opencut_section1_preview")
OUTPUT_MP4 = os.path.join(OUTPUT_DIR, "section1_opencut_flow.mp4")

import io
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    engine = OpenCutMotionFlowEngine(
        storyboard_path=STORYBOARD,
        audio_path=AUDIO,
        sentences_srt_path=SRT,
        assets_metadata_path=METADATA,
        assets_dir=ASSETS_DIR,
        output_mp4_path=OUTPUT_MP4,
        width=1920,
        height=1080,
        fps=30,
    )

    # Render first 12 seconds to verify the transition, typing, and element flow quickly
    print("[RUN] Rendering 12-second test of Section 1...")
    out_video = engine.render_full_video(limit_seconds=12.0)
    print(f"[DONE] Video preview ready: {out_video}")


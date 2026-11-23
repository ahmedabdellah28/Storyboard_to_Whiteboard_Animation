"""Master Production Runner for Section 1.

Renders the full 56.3-second cinematic motion graphics explainer with:
- Alternating visual beats (Two-shot elements <-> Compound kinetic typography).
- Contextual Top Pop Badges.
- Cairo-Bold Arabic kinetic reveals.
- Micro-impact camera shake at hammer slam.
- Drop shadows, breathing idle physics, and 100% audio sync.
"""

import os
import sys
from pathlib import Path

# Fix stdout encoding for Windows console
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"E:\image_to_animate"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from production_engine.master_staged_motion_director import MasterStagedMotionDirector

STORYBOARD = os.path.join(ROOT, "project_content", "images", "section1.png")
AUDIO = os.path.join(ROOT, "project_content", "audio", "section_01.wav")
METADATA = os.path.join(ROOT, "project_content", "extracted_assets", "section_01", "metadata.json")
ASSETS_DIR = os.path.join(ROOT, "project_content", "extracted_assets", "section_01")
OUTPUT_DIR = os.path.join(ROOT, "output_animations", "master_section1_production")
OUTPUT_MP4 = os.path.join(OUTPUT_DIR, "section1_master_staged_motion_v6.mp4")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    director = MasterStagedMotionDirector(
        storyboard_path=STORYBOARD,
        audio_path=AUDIO,
        assets_metadata_path=METADATA,
        assets_dir=ASSETS_DIR,
        output_mp4_path=OUTPUT_MP4,
        width=1920,
        height=1080,
        fps=30,
    )

    print("[MASTER PRODUCTION] Rendering full 56-second cinematic video for Section 1...")
    out_video = director.render_master_video()
    print(f"[SUCCESS] Final Master Video is ready: {out_video}")

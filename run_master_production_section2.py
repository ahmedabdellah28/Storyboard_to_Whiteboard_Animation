import os
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production_engine.master_staged_motion_director_section2 import MasterStagedMotionDirectorSection2

ASSETS_DIR = ROOT / "project_content" / "extracted_assets" / "section_02"
AUDIO_WAV = ROOT / "project_content" / "audio" / "section_02.wav"
OUTPUT_DIR = ROOT / "output_animations" / "master_section2_production"
OUTPUT_MP4 = OUTPUT_DIR / "section2_master_staged_motion_v1.mp4"

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    director = MasterStagedMotionDirectorSection2(assets_dir=ASSETS_DIR)
    director.render_video(output_mp4=str(OUTPUT_MP4), audio_wav=str(AUDIO_WAV))

if __name__ == "__main__":
    main()

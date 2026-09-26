import argparse
import sys
from pathlib import Path
from typing import Optional

# Ensure package root is in sys.path
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from section_tts.config import load_config
from section_tts.core.pipeline import SectionTTSPipeline
from section_tts.utils.logging import log

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Section-Based Professional TTS Generator for Whiteboard/Explainer Pipelines"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--section",
        type=str,
        help="Path to section directory (e.g., sections/003) or script.txt file"
    )
    group.add_argument(
        "--all-sections",
        type=str,
        help="Path to directory containing multiple section folders to process in batch"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output voice directory (defaults to <section>/voice)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override Gemini TTS model (e.g., gemini-2.5-flash-preview-tts)"
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=None,
        help="Override voice name (e.g., Fenrir, Puck, Zephyr)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of audio, ignoring cache"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode and export detailed JSON analysis reports"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Maximum retry attempts on API or validation failures"
    )
    return parser

def process_single_section(
    section_arg: str,
    output_arg: Optional[str],
    pipeline: SectionTTSPipeline
) -> bool:
    sec_path = Path(section_arg).resolve()
    
    # Check if user passed directory or script.txt file
    if sec_path.is_file():
        script_path = sec_path
        section_dir = sec_path.parent
    else:
        section_dir = sec_path
        script_path = section_dir / "script.txt"

    if not script_path.exists():
        log.error(f"Script file not found: {script_path}")
        return False

    out_dir = Path(output_arg).resolve() if output_arg else section_dir / "voice"
    section_id = section_dir.name

    try:
        pipeline.process_section(
            script_path=script_path,
            output_dir=out_dir,
            section_id=section_id
        )
        return True
    except Exception as e:
        log.error(f"Failed processing section {section_id}: {str(e)}")
        return False

def main():
    parser = build_parser()
    args = parser.parse_args()

    # Load configuration
    cfg = load_config()
    if args.model:
        cfg.tts.model = args.model
    if args.voice:
        cfg.tts.voice = args.voice
    if args.max_retries is not None:
        cfg.retry.max_retries = args.max_retries

    pipeline = SectionTTSPipeline(
        config=cfg,
        force_regenerate=args.force,
        debug_mode=args.debug
    )

    if args.section:
        success = process_single_section(args.section, args.output, pipeline)
        sys.exit(0 if success else 1)

    elif args.all_sections:
        all_dir = Path(args.all_sections).resolve()
        if not all_dir.exists():
            log.error(f"Directory not found: {all_dir}")
            sys.exit(1)

        section_folders = sorted([
            d for d in all_dir.iterdir()
            if d.is_dir() and (d / "script.txt").exists()
        ])

        if not section_folders:
            log.error(f"No section folders containing script.txt found in {all_dir}")
            sys.exit(1)

        log.section(f"Found {len(section_folders)} sections to process in batch.")
        success_count = 0
        for s_folder in section_folders:
            out_dir = (Path(args.output) / s_folder.name) if args.output else None
            ok = process_single_section(str(s_folder), str(out_dir) if out_dir else None, pipeline)
            if ok:
                success_count += 1

        log.section(f"Batch completed: {success_count}/{len(section_folders)} sections processed successfully.")
        sys.exit(0 if success_count == len(section_folders) else 1)

if __name__ == "__main__":
    main()

import argparse
import sys
from pathlib import Path

# Safe UTF-8 console output on Windows
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

# Ensure root directory is in sys.path
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from section_timing.pipeline import TimingPipeline
from section_timing.transcription.faster_whisper_engine import FasterWhisperEngine

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Professional Audio-to-Visual Timing Engine for Whiteboard Explainer Pipelines"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--section",
        type=str,
        help="Path to section directory (e.g., sections/01_homeless)"
    )
    group.add_argument(
        "--all-sections",
        type=str,
        help="Path to parent directory containing sections to batch process"
    )

    parser.add_argument("--audio", type=str, default=None, help="Path to section audio file")
    parser.add_argument("--script", type=str, default=None, help="Path to section script.txt")
    parser.add_argument("--output", type=str, default=None, help="Output directory for timing JSONs")
    parser.add_argument("--model", type=str, default=None, help="Whisper model (small, medium, large-v3, turbo)")
    parser.add_argument("--device", type=str, default=None, help="Compute device (auto, cuda, cpu)")
    parser.add_argument("--force", action="store_true", help="Force Whisper re-transcription, bypassing cache")
    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    # Custom whisper engine if overrides provided
    engine = None
    if args.model or args.device:
        engine = FasterWhisperEngine(
            model_size=args.model or "small",
            device=args.device or "auto"
        )

    pipeline = TimingPipeline(whisper_engine=engine)

    if args.section:
        sec_dir = Path(args.section).resolve()
        if not sec_dir.exists():
            print(f"❌ Error: Section directory not found: {sec_dir}", file=sys.stderr)
            sys.exit(1)

        try:
            pipeline.process_section(
                section_dir=sec_dir,
                script_file=args.script,
                audio_file=args.audio,
                output_dir=args.output,
                force_whisper=args.force
            )
            print("✅ Section timing synthesis completed successfully!")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Error processing section: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.all_sections:
        all_dir = Path(args.all_sections).resolve()
        if not all_dir.exists():
            print(f"❌ Error: Directory not found: {all_dir}", file=sys.stderr)
            sys.exit(1)

        sections = sorted([d for d in all_dir.iterdir() if d.is_dir()])
        success_count = 0
        for s in sections:
            # Check if section has script.txt and audio
            has_script = (s / "script.txt").exists()
            has_audio = (s / "voice" / "section.wav").exists() or (s / "voiceover.wav").exists() or (s / "master_audio.wav").exists()
            if has_script and has_audio:
                try:
                    pipeline.process_section(section_dir=s, force_whisper=args.force)
                    success_count += 1
                except Exception as e:
                    print(f"⚠️ Failed on section {s.name}: {e}")

        print(f"🎉 Batch timing completed: {success_count}/{len(sections)} sections generated.")

if __name__ == "__main__":
    main()

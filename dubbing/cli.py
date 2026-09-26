"""
AI Audio Dubbing Engine CLI
===========================
Command-line interface for the standalone AI Audio Dubbing Engine.

Usage example:
    python -m dubbing.cli -a input.wav -l en -v Kore
    python dubbing/cli.py --audio interview.mp3 --target-language es --voice Aoede
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from .models.dubbing_models import DubbingConfig
from .pipeline.dubbing_pipeline import DubbingPipeline


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def print_progress(step: str, progress: float) -> None:
    """Console progress bar printer."""
    pct = int(progress * 100)
    bar_len = 25
    filled = int(bar_len * progress)
    bar = "=" * filled + "-" * (bar_len - filled)
    print(f"\r  [{bar}] {pct:3d}% | {step}", end="", flush=True)
    if progress >= 1.0:
        print()



def main():
    parser = argparse.ArgumentParser(
        description="AI Audio Dubbing Engine — Standalone Audio Dubbing Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--audio", "-a",
        required=True,
        help="Path to source audio file (.wav, .mp3, .m4a, .flac, .ogg, etc.)",
    )
    parser.add_argument(
        "--target-language", "-l",
        default="en",
        help="Target language code or name (e.g. en, English, fr, es, de, tr, ar)",
    )
    parser.add_argument(
        "--voice", "-v",
        default="Fenrir",
        help="Target TTS voice identifier (e.g. Fenrir, Puck, Aoede, Kore, Charon)",
    )
    parser.add_argument(
        "--profile",
        default="YOUTH_CREATOR",
        choices=["YOUTH_CREATOR", "PROFESSIONAL_EXPLAINER", "NARRATIVE_STORYTELLER"],
        help="Voice Studio Persona Profile (e.g. YOUTH_CREATOR, PROFESSIONAL_EXPLAINER)",
    )
    parser.add_argument(
        "--director-note",
        default="DYNAMIC_WHITEBOARD_SWEETSPOT",
        choices=["DYNAMIC_WHITEBOARD_SWEETSPOT", "HIGH_ENERGY_YOUTUBE", "CALM_EDUCATIONAL"],
        help="Directorial delivery style note",
    )
    parser.add_argument(
        "--model-size", "-m",
        default="small",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Faster-Whisper model size",
    )
    parser.add_argument(
        "--device", "-d",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Computation device for Whisper",
    )
    parser.add_argument(
        "--config", "-c",
        default=None,
        help="Path to custom dubbing.yaml configuration file",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="dubbing",
        help="Root output directory where project folder will be created",
    )
    parser.add_argument(
        "--project-name", "-p",
        default=None,
        help="Custom project name for output folder",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recomputation, ignoring cached intermediate results",
    )

    args = parser.parse_args()

    audio_path = os.path.abspath(args.audio)
    if not os.path.isfile(audio_path):
        print(f"\n[ERROR] Source audio file does not exist: {audio_path}", file=sys.stderr)
        sys.exit(1)

    # Load configuration
    if args.config and os.path.isfile(args.config):
        config = DubbingConfig.from_yaml(args.config)
        print(f"Loaded configuration from: {args.config}")
    else:
        # Check default config location
        default_yaml = os.path.join(os.path.dirname(__file__), "config", "dubbing.yaml")
        if os.path.isfile(default_yaml):
            config = DubbingConfig.from_yaml(default_yaml)
        else:
            config = DubbingConfig()

    # Override CLI flags
    config.asr_model_size = args.model_size
    config.asr_device = args.device
    config.tts_voice = args.voice
    if hasattr(args, "profile") and args.profile:
        config.tts_profile = args.profile
    if hasattr(args, "director_note") and args.director_note:
        config.tts_director_note = args.director_note

    print("\n" + "=" * 65)
    print("           AI AUDIO DUBBING ENGINE")
    print("=" * 65)
    print(f"  Input Audio    : {audio_path}")
    print(f"  Target Language: {args.target_language}")
    print(f"  TTS Voice      : {args.voice}")
    print(f"  Voice Persona  : {config.tts_profile}")
    print(f"  Delivery Style : {config.tts_director_note}")
    print(f"  Whisper Model  : {config.asr_model_size} ({config.asr_device})")
    print(f"  Output Base    : {os.path.abspath(args.output_dir)}")
    print("=" * 65 + "\n")

    pipeline = DubbingPipeline(config=config)

    try:
        result = pipeline.dub(
            audio_path=audio_path,
            target_language=args.target_language,
            voice=args.voice,
            project_name=args.project_name,
            output_base_dir=args.output_dir,
            progress_callback=print_progress,
            force_rebuild=args.force,
        )

        print("\n" + "=" * 65)
        print("           DUBBING COMPLETED SUCCESSFULLY!")
        print("=" * 65)
        print(f"  Project ID       : {result.project_id}")
        print(f"  Source Language  : {result.source_language}")
        print(f"  Target Language  : {result.target_language}")
        print(f"  Source Duration  : {result.source_audio.duration:.2f}s")
        print(f"  Total Segments   : {len(result.segments)}")
        print(f"  Dubbed Audio     : {result.output_audio}")
        print(f"  Transcript       : {result.transcript_path}")
        print(f"  Translation      : {result.translation_path}")
        print(f"  Metadata         : {result.metadata_path}")
        print("=" * 65 + "\n")

    except Exception as e:
        print(f"\n\n[FATAL ERROR] Dubbing pipeline failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()

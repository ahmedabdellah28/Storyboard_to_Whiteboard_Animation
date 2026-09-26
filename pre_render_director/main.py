"""CLI Entrypoint for AI Pre-Render Visual Director."""

import sys
import json
import argparse
from pathlib import Path

from .models.input import SectionInput
from .models.output import ValidationStatus
from .director.orchestrator import DirectorOrchestrator
from .ai.provider import get_ai_provider

def main():
    parser = argparse.ArgumentParser(
        description="AI Pre-Render Visual Director: The final intelligent QA and synchronization layer before Video Rendering."
    )
    parser.add_argument(
        "--section",
        type=str,
        default="sections/01_homeless",
        help="Path to section directory containing script.txt, voice/, timing/, and assets/"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save final_render_plan.json (default: <section>/timing/final_render_plan.json)"
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Path to save review_report.json (default: <section>/timing/review_report.json)"
    )
    parser.add_argument(
        "--mock-ai",
        action="store_true",
        help="Use deterministic offline Mock AI Provider (fast, zero API quota usage)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Maximum loop iterations for patch refinement (default: 3)"
    )

    args = parser.parse_args()

    # Ensure UTF-8 output on Windows console
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    section_path = Path(args.section)
    if not section_path.exists():
        print(f"[ERROR] Section path '{section_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"[PRE-RENDER DIRECTOR] Loading section from: {section_path.resolve()}")
    section_input = SectionInput.from_directory(section_path)
    print(f"   [OK] Script loaded: {len(section_input.script_text.split())} words")
    print(f"   [OK] Audio duration: {section_input.audio_duration:.2f}s")
    print(f"   [OK] Initial visual events: {len(section_input.initial_drawings)}")
    print(f"   [OK] Assets in catalog: {len(section_input.assets)}")

    # Provider
    provider_type = "mock" if args.mock_ai else "auto"
    ai_provider = get_ai_provider(provider_type)
    print(f"   [OK] AI Provider: {ai_provider.__class__.__name__}")

    # Orchestrator
    orchestrator = DirectorOrchestrator(
        ai_provider=ai_provider,
        max_iterations=args.max_iterations
    )

    print("\n[PRE-RENDER DIRECTOR] Executing QA and Synchronization Loop...")
    plan, review_report = orchestrator.execute(section_input)

    # Determine output destinations
    timing_dir = section_path / "timing"
    timing_dir.mkdir(parents=True, exist_ok=True)

    out_plan = Path(args.output) if args.output else (timing_dir / "final_render_plan.json")
    out_report = Path(args.report) if args.report else (timing_dir / "review_report.json")

    # Save Final Render Plan
    out_plan.write_text(plan.export_json(), encoding="utf-8")
    print(f"\n[FINAL RENDER PLAN] Exported {len(plan.render_events)} render events to: {out_plan.resolve()}")

    # Save Review Report
    out_report.write_text(json.dumps(review_report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[REVIEW REPORT] Exported QA report to: {out_report.resolve()}")

    # Print summary
    status = plan.validation.status
    print(f"\n==========================================")
    print(f" DIRECTOR GATE STATUS: {status.value}")
    print(f" OVERALL QA SCORE:    {plan.validation.overall_score:.2f} / 1.00")
    print(f" PATCHES APPLIED:     {len(plan.applied_patches)}")
    print(f" HUMAN REVIEW NEEDED: {plan.review_required}")
    print(f"==========================================")

    if status == ValidationStatus.BLOCK_RENDER:
        print("[WARNING] Timeline has blocking validation errors! Check review_report.json.", file=sys.stderr)
        sys.exit(1)
    else:
        print("[SUCCESS] Section approved for Video Renderer!")
        sys.exit(0)

if __name__ == "__main__":
    main()

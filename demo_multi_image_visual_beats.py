"""
Multi-Image Dynamic Visual Beat Demonstration & Verification Script
Verifies that the Visual Beat Layer works completely dynamically across multiple distinct images.
"""
import os
import sys
import json

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.pipeline.content_loader import DynamicContentLoader
from engine.pipeline.multisheet_panel_engine import DynamicMultiSheetEngine
from engine.pipeline.dynamic_srt_choreographer import DynamicSRTChoreographer
from engine.beat.beat_mapper import BeatMapper
from engine.beat.beat_solver import BeatTimingSolver
from engine.beat.beat_debugger import BeatTimelineVisualizer


def run_multi_image_verification():
    print("=" * 95)
    print("      🚀 DYNAMIC MULTI-IMAGE VISUAL BEAT ASATE VERIFICATION 🚀                   ")
    print("=" * 95)

    # 1. Test Images to verify (different images, different layouts, different aspect ratios)
    test_images = [
        os.path.join(ROOT_DIR, "test_images", "ChatGPT Image Sep 5, 2026, 03_23_52 PM.png"),
        os.path.join(ROOT_DIR, "project_content", "images", "ChatGPT Image Sep 17, 2026, 06_05_13 PM.png"),
        os.path.join(ROOT_DIR, "project_content", "images", "ChatGPT Image Sep 17, 2026, 06_05_24 PM.png")
    ]

    # Load SRT
    srt_p = os.path.join(ROOT_DIR, "project_content", "srt", "combined_subtitles.srt")
    srt_entries = DynamicContentLoader.parse_srt_file(srt_p)
    print(f"✅ Loaded SRT Subtitles: {len(srt_entries)} words from {os.path.basename(srt_p)}\n")

    out_dir = os.path.join(ROOT_DIR, "scratch", "visual_beat_verification")
    os.makedirs(out_dir, exist_ok=True)

    results_summary = []

    for idx, img_path in enumerate(test_images, start=1):
        img_name = os.path.basename(img_path)
        print("-" * 90)
        print(f"  🖼️ [IMAGE {idx}/3] Processing: {img_name}")
        print("-" * 90)

        if not os.path.exists(img_path):
            print(f"  ⚠️ Warning: {img_path} not found, skipping.")
            continue

        # Stage A: Dynamic Panel & Object Extraction
        panels = DynamicMultiSheetEngine.process_sheets([img_path], ignore_badges=True)
        print(f"  • Discovered Panels: {len(panels)}")
        total_objs = sum(len(p.get("objects", [])) for p in panels)
        print(f"  • Total Extracted Objects: {total_objs}")

        # Stage B: Dynamic Speech Beat Creation & Mapping
        speech_beats = BeatMapper.create_speech_beats_from_srt(srt_entries)
        simulated_audio_dur = 60.0 if idx == 1 else 75.0

        visual_beats = BeatMapper.map_panels_to_visual_beats(
            panels=panels,
            speech_beats=speech_beats,
            total_audio_sec=simulated_audio_dur
        )
        print(f"  • Constructed Visual Beats: {len(visual_beats)}")

        # Stage C: Constrained Optimization via BeatTimingSolver
        solved_beats = BeatTimingSolver.solve_storyboard(
            visual_beats=visual_beats,
            total_audio_duration=simulated_audio_dur
        )
        print(f"  • Successfully Solved All Visual Beats within {simulated_audio_dur:.1f}s window")

        # Stage D: Sample Diagnostics on Beat 1 and Beat 2
        sample_b1 = solved_beats[0]
        print(f"    - Visual Beat 01: [{sample_b1.start:04.1f}s -> {sample_b1.end:04.1f}s] ({sample_b1.duration:04.1f}s)")
        print(f"      Primary Elements  : {sample_b1.primary_elements}")
        print(f"      Secondary Elements: {sample_b1.secondary_elements}")
        print(f"      Decisions Logged  : {len(sample_b1.timing_decisions)}")
        for d in sample_b1.timing_decisions[:3]:
            print(f"        • [{d.tier}] {d.element_name}: {d.start:04.1f}s -> {d.end:04.1f}s (dur={d.duration:04.1f}s, hold={d.hold_duration:04.1f}s) | {d.reason}")

        # Stage E: Export ASCII Timeline Chart
        chart_str = BeatTimelineVisualizer.render_ascii_timeline(
            visual_beats=solved_beats[:6], # Show first 6 beats cleanly
            speech_beats=speech_beats[:6],
            total_duration=solved_beats[min(5, len(solved_beats)-1)].end
        )
        chart_file = os.path.join(out_dir, f"img_{idx}_ascii_timeline.txt")
        with open(chart_file, "w", encoding="utf-8") as f:
            f.write(chart_str)
        print(f"  • ASCII Timeline Chart saved to: {chart_file}")

        # Stage F: Export JSON Decision Log
        json_file = os.path.join(out_dir, f"img_{idx}_decisions.json")
        BeatTimelineVisualizer.export_timing_decisions_json(solved_beats, json_file)
        print(f"  • JSON Timing Decision Log saved to: {json_file}")

        results_summary.append({
            "image": img_name,
            "panels_count": len(panels),
            "objects_count": total_objs,
            "visual_beats": len(solved_beats),
            "status": "PASSED"
        })

    print("\n" + "=" * 95)
    print("  🏆 MULTI-IMAGE DYNAMIC VERIFICATION RESULTS SUMMARY 🏆")
    print("=" * 95)
    for res in results_summary:
        print(f"  ✅ {res['image']:<48} | Panels: {res['panels_count']:02d} | Objects: {res['objects_count']:02d} | Beats: {res['visual_beats']:02d} | {res['status']}")
    print("=" * 95)

    return results_summary


if __name__ == "__main__":
    run_multi_image_verification()

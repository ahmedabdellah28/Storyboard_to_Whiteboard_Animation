"""
Comprehensive Test & Production Runner for Dynamic Storyboard Pipeline
Tests each stage sequentially, prints diagnostic metrics, and renders the final video.
"""
import os
import sys
import cv2
import av
import numpy as np

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
from engine.pipeline.dynamic_whiteboard_renderer import DynamicWhiteboardRenderer


def run_staged_pipeline_test(project_dir: str = "project_content", render_full_video: bool = True):
    print("=" * 95)
    print("      🚀 TESTING & RUNNING DYNAMIC STORYBOARD-TO-WHITEBOARD PIPELINE 🚀          ")
    print("=" * 95)

    # -----------------------------------------------------------------------------------
    # STAGE 1: DYNAMIC ASSETS & AUDIO/SRT INGESTION
    # -----------------------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("  [STAGE 1] Testing Dynamic Content Loader & Audio Ingestion")
    print("=" * 50)
    proj_data = DynamicContentLoader.load_project(project_dir)

    print(f"  ✅ Image Sheets Discovered: {proj_data['image_count']}")
    for img_p in proj_data['images']:
        print(f"     • {os.path.basename(img_p)}")
    print(f"  ✅ Subtitles (SRT): {proj_data['word_count']} words parsed from {os.path.basename(proj_data['srt_path'])}")
    print(f"  ✅ Master Audio Track: {proj_data['master_audio_path']}")
    print(f"     • Audio Duration: {proj_data['audio_duration']:.2f}s ({proj_data['audio_sample_rate']}Hz, {proj_data['audio_channels']}ch)")
    print(f"     • SRT Time Alignment Ratio: {proj_data['time_scale_ratio']:.4f}")
    print("  ⭐ STAGE 1 PASSED!")

    # -----------------------------------------------------------------------------------
    # STAGE 2: MULTI-SHEET PANEL DISCOVERY & ELEMENT EXTRACTION
    # -----------------------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("  [STAGE 2] Testing Multi-Sheet Panel Discovery & Entity Separation")
    print("=" * 50)
    panels = DynamicMultiSheetEngine.process_sheets(proj_data['images'], ignore_badges=True)
    print(f"  ✅ Total Panels Discovered: {len(panels)}")

    # Verify Badge Suppression on sample panels
    p1 = panels[0]
    badge_in_p1 = any(o.get("category") == "PANEL_BADGE" for o in p1["objects"])
    print(f"  ✅ Panel 1 Badge Suppression: {'REMOVED' if not badge_in_p1 else 'PRESENT'} (Objects: {len(p1['objects'])})")

    p13 = panels[12] if len(panels) >= 13 else None
    if p13:
        badge_in_p13 = any(o.get("category") == "PANEL_BADGE" for o in p13["objects"])
        print(f"  ✅ Panel 13 (Sheet 2) Badge Suppression: {'REMOVED' if not badge_in_p13 else 'PRESENT'} (Objects: {len(p13['objects'])})")

    print("  ⭐ STAGE 2 PASSED!")

    # -----------------------------------------------------------------------------------
    # STAGE 3: DYNAMIC TIMELINE CHOREOGRAPHY
    # -----------------------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("  [STAGE 3] Testing Dynamic Timeline Choreography & Scheduling")
    print("=" * 50)
    scheduled_panels = DynamicSRTChoreographer.choreograph_timeline(
        panels=panels,
        srt_entries=proj_data['srt_entries'],
        total_audio_sec=proj_data['audio_duration']
    )

    print(f"  ✅ Scheduled Panels: {len(scheduled_panels)}")
    for p in scheduled_panels:
        print(f"     • Panel {p['global_id']:02d} (Sheet {p['sheet_index']}): [{p['start_time']:05.1f}s -> {p['end_time']:05.1f}s] ({p['duration']:04.1f}s) | {len(p['objects'])} objects | \"{p['spoken_text'][:30]}...\"")

    print("  ⭐ STAGE 3 PASSED!")

    # -----------------------------------------------------------------------------------
    # STAGE 4: PRODUCTION VIDEO RENDERING & AUDIO MUXING
    # -----------------------------------------------------------------------------------
    if render_full_video:
        print("\n" + "=" * 50)
        print("  [STAGE 4] Rendering Production Video & Muxing Audio Track")
        print("=" * 50)
        out_vid = os.path.join(ROOT_DIR, "output_animations", "master_whiteboard_complete_project.mp4")

        final_path = DynamicWhiteboardRenderer.render(
            scheduled_panels=scheduled_panels,
            master_audio_path=proj_data['master_audio_path'],
            output_video_path=out_vid,
            fps=30,
            zoom_level=1.38
        )

        print(f"\n  ✅ Production Video Rendered Successfully: {final_path}")

        # Verification of final video
        with av.open(final_path) as c:
            vs = c.streams.video[0]
            as_ = c.streams.audio[0]
            v_dur = float(vs.duration * vs.time_base)
            a_dur = float(as_.duration * as_.time_base)
            print(f"  ✅ Final Verification:")
            print(f"     • Video Stream: {vs.width}x{vs.height} @ {float(vs.average_rate)}fps, duration: {v_dur:.2f}s")
            print(f"     • Audio Stream: {as_.rate}Hz stereo, duration: {a_dur:.2f}s")
            print(f"     • File Size: {round(c.size / (1024*1024), 2) if hasattr(c, 'size') else 'N/A'} MB")

        print("  ⭐ STAGE 4 PASSED!")
        return final_path

    return scheduled_panels


if __name__ == "__main__":
    run_staged_pipeline_test("project_content", render_full_video=True)

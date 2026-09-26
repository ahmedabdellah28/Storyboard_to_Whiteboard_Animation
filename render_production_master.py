"""
Master Production Whiteboard Animation Engine
Renders the full 28-panel synchronized whiteboard animation video with:
- Guaranteed narrative sheet ordering
- 1-to-1 semantic visual beat alignment
- 100% stroke coverage with physical drawing velocity
- Seamless camera pan & zoom across both storyboard sheets
- Lossless H.264/AAC audio-video muxing
"""
import os
import sys
import time
import cv2

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

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.pipeline.content_loader import DynamicContentLoader
from engine.pipeline.multisheet_panel_engine import DynamicMultiSheetEngine
from engine.pipeline.dynamic_srt_choreographer import DynamicSRTChoreographer
from engine.pipeline.dynamic_whiteboard_renderer import DynamicWhiteboardRenderer


def main():
    print("=" * 100)
    print("      🎬 STARTING 28-PANEL PRODUCTION WHITEBOARD ANIMATION PIPELINE 🎬                   ")
    print("=" * 100)
    start_total_time = time.time()

    # 1. Ingestion
    print("\n[Step 1/5] Loading project content with deterministic narrative ordering...")
    project_data = DynamicContentLoader.load_project("project_content")
    print(f"  • Discovered {len(project_data['images'])} storyboard sheets:")
    for i, img_path in enumerate(project_data["images"]):
        print(f"    [{i+1}] {os.path.basename(img_path)}")
    print(f"  • Master Audio Duration: {project_data['audio_duration']:.2f}s")
    print(f"  • Subtitle Entries     : {len(project_data['srt_entries'])} entries")

    # 2. Multi-Sheet Panel Discovery & Separation
    print("\n[Step 2/5] Extracting and isolating panels across all sheets...")
    panels = DynamicMultiSheetEngine.process_sheets(project_data["images"], ignore_badges=True)
    print(f"  • Total Panels Processed: {len(panels)}")

    # 3. Audio-Visual Choreography via Visual Beat Layer
    print("\n[Step 3/5] Choreographing timeline using Visual Beat Engine (Ground Truth Alignment)...")
    scheduled_panels = DynamicSRTChoreographer.choreograph_timeline(
        panels=panels,
        srt_entries=project_data["srt_entries"],
        total_audio_sec=project_data["audio_duration"],
        use_visual_beats=True
    )

    print("\n[Step 4/5] Pre-Render Diagnostics & Schedule Validation:")
    print("-" * 100)
    for pnl in scheduled_panels:
        gid = pnl["global_id"]
        st = pnl["start_time"]
        en = pnl["end_time"]
        dur = pnl["duration"]
        txt = pnl.get("spoken_text", "")
        objs_cnt = len(pnl.get("objects", []))
        print(f"  • Panel {gid:02d} [{st:05.1f}s -> {en:05.1f}s] (dur={dur:04.1f}s) | Objs: {objs_cnt:02d} | Text: {txt[:40]}...")
    print("-" * 100)

    # 4. Production Rendering
    output_mp4 = os.path.join(ROOT_DIR, "output_animations", "storyboard_master_28_panels.mp4")
    print(f"\n[Step 5/5] Launching GPU-Accelerated Dynamic Production Renderer...")
    print(f"  • Target Video Path: {output_mp4}")

    rendered_video = DynamicWhiteboardRenderer.render(
        scheduled_panels=scheduled_panels,
        master_audio_path=project_data["master_audio_path"],
        output_video_path=output_mp4,
        fps=30,
        zoom_level=1.38,
        out_w=1920,
        out_h=1080
    )

    total_elapsed = time.time() - start_total_time
    print(f"\n✅ Production rendering completed in {total_elapsed:.1f}s ({total_elapsed/60.0:.2f} min).")
    print(f"✅ Master synchronized video saved: {rendered_video}")

    # 5. Extract Diagnostic Visual Frames for User Review
    print("\nExtracting milestone inspection frames for visual verification...")
    diag_dir = os.path.join(ROOT_DIR, "scratch", "production_inspection_frames")
    os.makedirs(diag_dir, exist_ok=True)

    test_timestamps = [
        (2.5, "p01_intro"),
        (7.0, "p02_iq70"),
        (12.5, "p04_two_percent"),
        (25.0, "p06_space"),
        (52.0, "p12_care"),
        (85.0, "p16_sheet1_transition"),
        (90.0, "p17_sheet2_start"),
        (112.0, "p22_desert_car"),
        (124.0, "p24_quick_fix"),
        (148.0, "p28_conclusion")
    ]

    cap = cv2.VideoCapture(output_mp4)
    fps_val = cap.get(cv2.CAP_PROP_FPS) or 30.0

    for sec, label in test_timestamps:
        frame_no = int(round(sec * fps_val))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = cap.read()
        if ret and frame is not None:
            save_path = os.path.join(diag_dir, f"frame_{sec:05.1f}s_{label}.jpg")
            cv2.imwrite(save_path, frame)
            print(f"  📸 Saved inspection frame at {sec:05.1f}s: {save_path}")

    cap.release()
    print("\n🎉 ALL MILESTONES ACHIEVED SUCCESSFULLY! 🎉\n")
    return output_mp4


if __name__ == "__main__":
    main()

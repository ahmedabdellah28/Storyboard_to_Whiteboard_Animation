"""
Test Sync & Natural Choreography Runner
Integrates:
- SRT transcript alignment to panels & elements
- Natural artist character drawing choreography (Linework -> Features -> Shading)
- Visual timeline schedule generation
"""
import os
import sys
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath('.'))

from dev_separator.transcript_timeline_aligner import TranscriptTimelineAligner
from dev_separator.natural_artist_choreographer import NaturalArtistChoreographer
from dev_separator.panel_pipeline import PanelPipeline


def run_sync_and_choreography_demo():
    srt_path = 'dev_separator/storyboard_transcript.srt'
    clean_p1_path = 'dev_separator/output_reports/panel_01/00_original_clean.png'
    
    clean_p1 = cv2.imread(clean_p1_path)
    if clean_p1 is None:
        raise FileNotFoundError(f"Could not load {clean_p1_path}")
        
    print("=== 1. Parsing Word-Level SRT Transcript ===")
    srt_entries = TranscriptTimelineAligner.parse_srt_file(srt_path)
    print(f"Loaded {len(srt_entries)} word entries from SRT.")
    print(f"Audio start: {srt_entries[0]['start']}s, Audio end: {srt_entries[-1]['end']}s")
    
    print("\n=== 2. Aligning Transcript to Panels ===")
    panel_windows = TranscriptTimelineAligner.align_transcript_to_panels(srt_entries, panel_count=12)
    print(f"Aligned {len(panel_windows)} panels to speech timeline:")
    for pw in panel_windows:
        print(f"  Panel {pw['panel_id']:02d}: [{pw['start_time']:04.1f}s -> {pw['end_time']:04.1f}s] ({pw['duration']:.1f}s) | \"{pw['spoken_text'][:45]}...\"")
        
    print("\n=== 3. Synchronizing Panel 1 Elements with Spoken Words ===")
    p1_pipeline_res = PanelPipeline.process_panel(clean_p1, panel_id=1)
    p1_objects = p1_pipeline_res["objects"]
    p1_timeline = panel_windows[0] # Panel 1
    
    synced_objs = TranscriptTimelineAligner.synchronize_panel_objects(p1_objects, p1_timeline)
    
    print(f"Panel 1 Schedule ({p1_timeline['duration']:.1f}s Total Spoken Duration):")
    for so in synced_objs:
        print(f"  • {so['name']}: {so['sync_start']:.2f}s -> {so['sync_end']:.2f}s (duration: {so['sync_duration']:.2f}s, speed: {so['speed_multiplier']}x)")
        
    print("\n=== 4. Natural Artist Character Choreography (Panel 1 Character) ===")
    char_obj = next(o for o in synced_objs if o["type"] == "CHARACTER")
    char_crop = char_obj["crop"]
    char_mask = char_obj["mask"]
    
    choreo = NaturalArtistChoreographer.generate_character_drawing_plan(char_crop, char_mask)
    print(f"Natural Choreography generated successfully:")
    print(f"  • Phase 1 (Line Art & Contours): {choreo['total_linework_strokes']} strokes (head-to-torso flow)")
    print(f"  • Phase 2 (Directional Shading): {choreo['total_shading_strokes']} strokes (smooth marker passes)")
    
    # 5. Render Visual Visualizations
    out_dir = 'dev_separator/output_reports/panel_01'
    
    # Visual Phase 1: Linework skeleton
    ch, cw = char_crop.shape[:2]
    linework_vis = np.full((ch, cw, 3), 255, dtype=np.uint8)
    for stroke in choreo["linework_strokes"]:
        for i in range(len(stroke) - 1):
            pt1 = (int(stroke[i][0]), int(stroke[i][1]))
            pt2 = (int(stroke[i+1][0]), int(stroke[i+1][1]))
            cv2.line(linework_vis, pt1, pt2, (30, 30, 30), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(out_dir, "03_natural_linework_phase.png"), linework_vis)
    
    # Visual Phase 2: Full Shaded character
    cv2.imwrite(os.path.join(out_dir, "04_natural_shaded_character.png"), char_crop)
    
    # Visual Schedule Chart
    chart_w = 700
    chart_h = 320
    chart = np.full((chart_h, chart_w, 3), 252, dtype=np.uint8)
    
    cv2.putText(chart, "AUDIO-VISUAL SYNCHRONIZATION SCHEDULE (Panel 01)", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (30, 30, 30), 2, cv2.LINE_AA)
    cv2.putText(chart, "Synchronizing Drawing Order & Speed with Spoken Voice (0.0s - 4.5s)", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (100, 100, 100), 1, cv2.LINE_AA)
                
    # Draw timeline axis
    axis_y = 75
    cv2.line(chart, (180, axis_y), (660, axis_y), (150, 150, 150), 2)
    for sec in range(5):
        sx = int(180 + (sec / 4.5) * 480)
        cv2.line(chart, (sx, axis_y - 4), (sx, axis_y + 4), (80, 80, 80), 2)
        cv2.putText(chart, f"{sec}.0s", (sx - 10, axis_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (80, 80, 80), 1)
        
    # Draw element bars
    start_y = 105
    for idx, so in enumerate(synced_objs):
        ey = start_y + idx * 28
        name_clean = so['name'].replace('Panel 01 - ', '')
        cv2.putText(chart, name_clean[:22], (20, ey + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (40, 40, 40), 1, cv2.LINE_AA)
        
        # Bar coordinates
        bx1 = int(180 + (so['sync_start'] / 4.5) * 480)
        bx2 = int(180 + (so['sync_end'] / 4.5) * 480)
        bw = max(6, bx2 - bx1)
        
        # Color
        color = (30, 180, 30) if so['type'] == 'CHARACTER' else ((255, 160, 0) if so['type'] == 'CONTAINER_CARD' else (200, 30, 180))
        cv2.rectangle(chart, (bx1, ey), (bx1 + bw, ey + 18), color, -1)
        cv2.rectangle(chart, (bx1, ey), (bx1 + bw, ey + 18), (40, 40, 40), 1)
        
        dur_label = f"{so['sync_duration']:.1f}s ({so['speed_multiplier']}x)"
        cv2.putText(chart, dur_label, (bx1 + bw + 6, ey + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (60, 60, 60), 1)
        
    cv2.imwrite(os.path.join(out_dir, "05_timeline_schedule_chart.png"), chart)
    print(f"Visual schedule chart saved to {os.path.join(out_dir, '05_timeline_schedule_chart.png')}")
    
    # Also copy to artifacts dir for easy preview
    dest = r'C:/Users/loper/.gemini/antigravity-ide/brain/158728a5-a939-4410-9555-755847fa7279'
    import shutil
    shutil.copy(os.path.join(out_dir, "03_natural_linework_phase.png"), f"{dest}/p01_natural_linework.png")
    shutil.copy(os.path.join(out_dir, "05_timeline_schedule_chart.png"), f"{dest}/p01_timeline_chart.png")
    print("Copied preview charts to artifacts directory successfully!")


if __name__ == '__main__':
    run_sync_and_choreography_demo()

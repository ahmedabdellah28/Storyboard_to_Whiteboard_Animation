"""
Real-World Storyboard Timing Report Generator
Runs complete ASATE Visual Beat pipeline on 3 real storyboard images with real SRT and Audio,
generating the detailed, per-beat Timing Report requested by the user.
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
from engine.beat.beat_mapper import BeatMapper
from engine.beat.beat_solver import BeatTimingSolver


def generate_full_real_world_reports():
    print("=" * 95)
    print("  🎬 REAL-WORLD AUDIT: GENERATING DETAILED BEAT TIMING REPORTS (3 BOARDS) 🎬      ")
    print("=" * 95)

    audio_path = os.path.join(ROOT_DIR, "project_content", "audio", "master_voiceover_concatenated.wav")
    srt_path = os.path.join(ROOT_DIR, "project_content", "srt", "combined_subtitles.srt")
    
    srt_entries = DynamicContentLoader.parse_srt_file(srt_path)
    print(f"✅ Real SRT: {len(srt_entries)} entries parsed from {os.path.basename(srt_path)}")
    print(f"✅ Real Master Audio: {audio_path} (Exists: {os.path.exists(audio_path)})\n")

    # 3 Real Storyboards
    boards = [
        {
            "name": "12-Panel Storyboard (Sheet 1 - Characters & Text Cards)",
            "image": os.path.join(ROOT_DIR, "project_content", "images", "ChatGPT Image Sep 17, 2026, 06_05_13 PM.png"),
            "audio_dur": 84.30  # Duration for Sheet 1
        },
        {
            "name": "16-Panel Storyboard (Test Archive Sheet - Multi-Grid)",
            "image": os.path.join(ROOT_DIR, "test_images", "ChatGPT Image Sep 5, 2026, 03_23_52 PM.png"),
            "audio_dur": 60.00
        },
        {
            "name": "Visually Distinct Storyboard (Sheet 2 - Tools, Cars, Direction Arrows)",
            "image": os.path.join(ROOT_DIR, "project_content", "images", "ChatGPT Image Sep 17, 2026, 06_05_24 PM.png"),
            "audio_dur": 66.90  # Duration for Sheet 2
        }
    ]

    out_md_path = os.path.join(ROOT_DIR, "docs", "REAL_WORLD_VISUAL_BEAT_TIMING_REPORT.md")
    md_lines = [
        "# تقرير فحص التوقيت الحقيقي لطبقة Visual Beat (Real-World Timing Audit Report)",
        "",
        "تم تشغيل هذا الفحص الشامل باستخدام **الملفات الحقيقية للمشروع** (صور الاستوري بورد الفعلية + ملف الصوت الموحد Master Audio + ملف الترجمة الحقيقي SRT)، لاستخراج تقرير التوقيت الدقيق لكل نبضة بصرية (Visual Beat) على النحو التالي:",
        ""
    ]

    for b_idx, b in enumerate(boards, start=1):
        print(f"[{b_idx}/3] Processing: {b['name']} ...")
        panels = DynamicMultiSheetEngine.process_sheets([b["image"]], ignore_badges=True)
        speech_beats = BeatMapper.create_speech_beats_from_srt(srt_entries)
        
        visual_beats = BeatMapper.map_panels_to_visual_beats(
            panels=panels,
            speech_beats=speech_beats,
            total_audio_sec=b["audio_dur"]
        )

        solved_beats = BeatTimingSolver.solve_storyboard(
            visual_beats=visual_beats,
            total_audio_duration=b["audio_dur"]
        )

        md_lines.append(f"## {b_idx}. {b['name']}")
        md_lines.append(f"- **ملف الصورة:** `{os.path.basename(b['image'])}`")
        md_lines.append(f"- **عدد البانلات المكتشفة:** {len(panels)}")
        md_lines.append(f"- **المدة الصوتية المخصصة:** {b['audio_dur']:.2f} ثانية")
        md_lines.append(f"- **عدد النبضات البصرية المنفذة:** {len(solved_beats)}")
        md_lines.append("")

        for vb in solved_beats:
            matched_sb = next((sb for sb in speech_beats if sb.id == vb.speech_beat_id), None)
            sp_st = matched_sb.start if matched_sb else vb.start
            sp_en = matched_sb.end if matched_sb else vb.end
            sp_dur = sp_en - sp_st

            md_lines.append(f"### 📍 Visual Beat: `{vb.id}` (Panel {vb.panel_id})")
            md_lines.append(f"- **Speech Window:** `[{sp_st:05.2f}s -> {sp_en:05.2f}s]` (المدة: **{sp_dur:04.2f}s**)")
            md_lines.append(f"- **Visual Window:** `[{vb.start:05.2f}s -> {vb.end:05.2f}s]` (المدة: **{vb.duration:04.2f}s**)")
            md_lines.append(f"- **النص المنطوق:** *\"{vb.narrative_text[:70]}...\"*")
            md_lines.append(f"- **Primary Elements:** `{vb.primary_elements}`")
            md_lines.append(f"- **Secondary Elements:** `{vb.secondary_elements}`")
            md_lines.append(f"- **Decorative Elements:** `{vb.decorative_elements}`")
            md_lines.append(f"- **Overlap Policy:** `{vb.overlap_policy.value}` | **Hold Time:** `{vb.hold_duration}s`")
            md_lines.append("")
            md_lines.append("| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |")
            md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

            for dec in vb.timing_decisions:
                md_lines.append(
                    f"| **{dec.element_name}** | `{dec.tier}` | `{dec.start:05.2f}s` | `{dec.end:05.2f}s` | "
                    f"`{dec.duration:04.2f}s` | `{dec.hold_duration:04.2f}s` | `{dec.anticipation:04.2f}s` | "
                    f"`{dec.speed_multiplier:04.2f}x` | {dec.reason} |"
                )
            md_lines.append("")
            md_lines.append("---")

    with open(out_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"\n🎉 Full Real-World Timing Report successfully generated at:\n   {out_md_path}")
    return out_md_path


if __name__ == "__main__":
    generate_full_real_world_reports()

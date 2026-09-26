"""
Real-World Storyboard Timing Report Generator V2 (Content-Aware Visual Timing Engine)
Runs complete ASATE Visual Beat Engine V2 on 3 real storyboard images with real SRT and Audio,
generating the detailed, per-beat Timing Report V2 with Physical Demand, Feasibility, and Transitions.
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
from engine.beat.beat_debugger import BeatTimelineVisualizer


def generate_full_real_world_reports_v2():
    print("=" * 95)
    print("  🎬 REAL-WORLD AUDIT V2: CONTENT-AWARE VISUAL BEAT TIMING (3 BOARDS) 🎬      ")
    print("=" * 95)

    audio_path = os.path.join(ROOT_DIR, "project_content", "audio", "master_voiceover_concatenated.wav")
    srt_path = os.path.join(ROOT_DIR, "project_content", "srt", "combined_subtitles.srt")
    
    srt_entries = DynamicContentLoader.parse_srt_file(srt_path)
    print(f"✅ Real SRT: {len(srt_entries)} entries parsed from {os.path.basename(srt_path)}")
    print(f"✅ Real Master Audio: {audio_path} (Exists: {os.path.exists(audio_path)})\n")

    boards = [
        {
            "name": "12-Panel Storyboard (Sheet 1 - Characters & Text Cards)",
            "image": os.path.join(ROOT_DIR, "project_content", "images", "ChatGPT Image Sep 17, 2026, 06_05_13 PM.png"),
            "audio_dur": 84.30
        },
        {
            "name": "16-Panel Storyboard (Test Archive Sheet - Multi-Grid)",
            "image": os.path.join(ROOT_DIR, "test_images", "ChatGPT Image Sep 5, 2026, 03_23_52 PM.png"),
            "audio_dur": 60.00
        },
        {
            "name": "Visually Distinct Storyboard (Sheet 2 - Tools, Cars, Direction Arrows)",
            "image": os.path.join(ROOT_DIR, "project_content", "images", "ChatGPT Image Sep 17, 2026, 06_05_24 PM.png"),
            "audio_dur": 66.90
        }
    ]

    out_md_path = os.path.join(ROOT_DIR, "docs", "REAL_WORLD_VISUAL_BEAT_TIMING_REPORT_V2.md")
    md_lines = [
        "# تقرير فحص التوقيت الحقيقي V2: محرك التوقيت البصري القائم على المحتوى (Content-Aware Timing Engine V2)",
        "",
        "> هذا التقرير يوثق نتائج تشغيل **Visual Beat Engine V2** على **ثلاث لوحات استوري بورد حقيقية** باستخدام ملف الصوت الفعلي وملف الترجمة SRT الحقيقي.",
        "> تم الانتقال بالكامل من مجرد تقريب المدد (Preset Timing) إلى **نموذج فيزيائي معاير** يعتمد على الجهد الفيزيائي الحقيقي للرسم (`DrawingDemand`)، وفحص الجدوى (`Speed Feasibility`)، وإدارة التعارضات (`Timing Conflict Model`)، وعلاقات الانتقال المستقلة بين النبضات (`BeatTransition`).",
        "",
        "---",
        "",
        "## الفروقات الجوهرية (BEFORE V1 vs AFTER V2)",
        "",
        "| المعيار المعماري | النظام السابق (Preset Timing V1) | النظام الجديد (Content-Aware V2) |",
        "| :--- | :--- | :--- |",
        "| **تحديد زمن الرسم** | مدد ثابتة وفق الفئة (شخصية 1.78s، أيقونة 0.60s، نص 0.42s) | **نموذج فيزيائي معاير**: $\\text{Demand} = \\sum \\|\\Delta p\\| \\to T = \\text{Effort} / v_{pen}$ |",
        "| **DrawingDemand** | كان مدمجاً في Duration | **مفصول تماماً**: $L_{arc}$, عدد الخطوط، النقاط، التعقيد، الكثافة $\\neq$ زمن الرسم |",
        "| **تصنيف العناصر (Tiers)** | كان يحدد مدة الرسم مسبقاً (Primary أطول دائماً) | **يحدد الأهمية السردية والحماية والـ Hold**؛ زمن الرسم يتبع الجهد الفيزيائي فقط |",
        "| **إدارة الانتقال (Transition)** | كان ملكية داخلية للنبضة تؤدي لتضارب النوافذ | **كيان مستقل (`BeatTransition`)** يربط بين Beat $A$ و Beat $B$ باستراتيجيات واضحة |",
        "| **فحص السرعة والجدوى** | تسريع غير مقيد عند ضيق الوقت (سرعات خيالية) | **Speed Feasibility** (`NORMAL`, `FAST`, `LIMITED`, `INFEASIBLE`) + 6 خطوات للحل |",
        "| **التعارضات المستحيلة** | محاولة إجبار الـ Timeline أو انهيار النظام | **كائنات `TimingConflict` موثقة** بالخطورة والحل المقترح |",
        "",
        "---",
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

        solved_beats, transitions = BeatTimingSolver.solve_storyboard(
            visual_beats=visual_beats,
            total_audio_duration=b["audio_dur"],
            return_transitions=True
        )

        md_lines.append(f"## {b_idx}. {b['name']}")
        md_lines.append(f"- **ملف الصورة:** `{os.path.basename(b['image'])}`")
        md_lines.append(f"- **عدد البانلات المكتشفة:** {len(panels)}")
        md_lines.append(f"- **المدة الصوتية:** {b['audio_dur']:.2f} ثانية")
        md_lines.append(f"- **عدد النبضات البصرية المنفذة:** {len(solved_beats)}")
        md_lines.append(f"- **عدد روابط الانتقال بين النبضات (`BeatTransitions`):** {len(transitions)}")
        md_lines.append("")

        # Summary Metrics Table
        md_lines.append("### 📊 جدول ملخص النبضات البصرية والنوافذ الزمنية الثلاث")
        md_lines.append("| Beat ID | Panel | Speech Window | Drawing Window | Hold Window | Total Effort (px) | Feasibility | Conflicts |")
        md_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

        for vb in solved_beats:
            sp_str = f"[{vb.speech_window[0]:.2f}s - {vb.speech_window[1]:.2f}s] ({vb.speech_window[1]-vb.speech_window[0]:.2f}s)"
            dr_str = f"[{vb.drawing_window[0]:.2f}s - {vb.drawing_window[1]:.2f}s] ({vb.drawing_window[1]-vb.drawing_window[0]:.2f}s)"
            ho_str = f"[{vb.hold_window[0]:.2f}s - {vb.hold_window[1]:.2f}s] ({vb.hold_window[1]-vb.hold_window[0]:.2f}s)"
            tot_effort = sum(d.estimated_physical_effort for d in vb.drawing_demands.values())
            feas_set = set(d.feasibility.value for d in vb.timing_decisions)
            feas_str = "/".join(feas_set) if feas_set else "NORMAL"
            conf_cnt = len(vb.timing_conflicts)
            conf_str = f"⚠️ {conf_cnt} Conflicts" if conf_cnt > 0 else "✅ 0"
            md_lines.append(f"| `{vb.id}` | {vb.panel_id} | {sp_str} | {dr_str} | {ho_str} | {tot_effort:.0f} | `{feas_str}` | {conf_str} |")

        md_lines.append("")
        md_lines.append("### 🔍 تفاصيل العناصر وقرارات التوقيت الفيزيائي في كل نبضة")

        for vb in solved_beats:
            md_lines.append(f"#### 📍 `{vb.id}` (Panel {vb.panel_id})")
            md_lines.append(f"- **النص المنطوق:** *\"{vb.narrative_text[:80]}...\"*")
            md_lines.append(f"- **Speech Window:** `[{vb.speech_window[0]:.2f}s -> {vb.speech_window[1]:.2f}s]` (مدة الكلام: **{vb.speech_window[1]-vb.speech_window[0]:.2f}s**)")
            md_lines.append(f"- **Drawing Window:** `[{vb.drawing_window[0]:.2f}s -> {vb.drawing_window[1]:.2f}s]` (مدة الرسم الفعلية: **{vb.drawing_window[1]-vb.drawing_window[0]:.2f}s**)")
            md_lines.append(f"- **Hold Window (بقاء العنصر في نظر المشاهد):** `[{vb.hold_window[0]:.2f}s -> {vb.hold_window[1]:.2f}s]` (مدة الثبات: **{vb.hold_window[1]-vb.hold_window[0]:.2f}s**)")

            if vb.semantic_anchors:
                md_lines.append("- **النقاط الدلالية الثابتة (`Semantic Anchors`):**")
                for sa in vb.semantic_anchors:
                    md_lines.append(f"  - 🎯 `{sa.source_token}` ({sa.source_type.value}) @ `{sa.target_time:.2f}s` -> Type: `{sa.anchor_type.value}`, Confidence: `{sa.confidence:.2f}`")

            if vb.timing_conflicts:
                md_lines.append("- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**")
                for tc in vb.timing_conflicts:
                    md_lines.append(f"  - **[{tc.severity.value}] {tc.conflict_type.value}:** {tc.description}")
                    md_lines.append(f"    - *محاولة الحل:* {tc.resolution_attempted}")

            md_lines.append("- **تفاصيل العناصر والجهد الفيزيائي:**")
            md_lines.append("  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |")
            md_lines.append("  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")

            for d in vb.timing_decisions:
                dem = d.demand
                arc_len = f"{dem.arc_length_px:.0f}" if dem else "N/A"
                eff = f"{dem.estimated_physical_effort:.0f}" if dem else "N/A"
                md_lines.append(f"  | `{d.element_id}` | `{d.tier}` | {arc_len} | {eff} | {d.start:.2f}s | {d.end:.2f}s | **{d.duration:.2f}s** | {d.hold_duration:.2f}s | {d.speed_multiplier:.2f}x | `{d.feasibility.value}` | *{d.reason[:40]}* |")

            md_lines.append("")

        # Transitions Section
        md_lines.append("### 🔗 روابط الانتقال بين النبضات (`BeatTransitions`)")
        md_lines.append("| From Beat | To Beat | Start Time | End Time | Transition Type | Strategy |")
        md_lines.append("| :--- | :--- | :---: | :---: | :---: | :--- |")
        for tr in transitions:
            md_lines.append(f"| `{tr.from_beat_id}` | `{tr.to_beat_id}` | {tr.start:.2f}s | {tr.end:.2f}s | `{tr.transition_type.value}` | {tr.strategy} |")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    with open(out_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"\n🎉 Successfully generated comprehensive V2 report: {out_md_path}")


if __name__ == "__main__":
    generate_full_real_world_reports_v2()

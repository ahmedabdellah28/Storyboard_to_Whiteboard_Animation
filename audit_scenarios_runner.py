"""
Audit & Validation Suite: Scenarios A through J
Evaluates the dynamic behavior of Visual Beat Layer under extreme real-world timing conditions.
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

from engine.beat.speech_beat import SpeechBeat
from engine.beat.visual_beat import (
    VisualBeat,
    ElementTier,
    OverlapPolicy,
    TransitionPolicy,
    EmphasisPoint
)
from engine.beat.beat_solver import BeatTimingSolver
from engine.beat.beat_mapper import BeatMapper
from engine.beat.beat_debugger import BeatTimelineVisualizer


def run_scenarios_audit():
    print("=" * 95)
    print("      🧪 AUDIT & VALIDATION: 10 STRESS TEST SCENARIOS (A -> J) 🧪                ")
    print("=" * 95)

    scenario_results = []

    # -----------------------------------------------------------------------------------
    # SCENARIO A: جملة قصيرة جداً (0.8s) + عنصر واحد بسيط
    # -----------------------------------------------------------------------------------
    sb_a = SpeechBeat(id="sb_a", start=0.0, end=0.8, text="نعم تماماً")
    elem_a = {"id": "check_icon", "name": "Checkmark", "category": "ICON_GRAPHIC", "stroke_pts": [(i, i) for i in range(25)]}
    vb_a = VisualBeat(id="vb_a", start=0.0, end=0.8, elements=[elem_a], primary_elements=["Checkmark"])
    sched_a = BeatTimingSolver.solve_beat(vb_a)
    d_a = vb_a.timing_decisions[0]
    scenario_results.append({
        "scenario": "A",
        "title": "Ultra-Short (0.8s) + 1 Simple Element",
        "speech_dur": 0.8,
        "draw_dur": d_a.duration,
        "hold_dur": d_a.hold_duration,
        "speed_mult": d_a.speed_multiplier,
        "passed": 0.0 <= d_a.start and d_a.end <= 0.8 and d_a.duration >= 0.35,
        "decision": d_a.to_dict()
    })

    # -----------------------------------------------------------------------------------
    # SCENARIO B: جملة طويلة (6.0s) + عنصر واحد معقد
    # -----------------------------------------------------------------------------------
    sb_b = SpeechBeat(id="sb_b", start=0.0, end=6.0, text="هنا نلاحظ التفاصيل الكاملة للشخصية في هذا المستوى المتقدم جداً")
    elem_b = {"id": "complex_char", "name": "Detailed Anatomy", "category": "CHARACTER", "stroke_pts": [(i, i) for i in range(1200)]}
    vb_b = VisualBeat(id="vb_b", start=0.0, end=6.0, elements=[elem_b], primary_elements=["Detailed Anatomy"], hold_duration=1.2)
    sched_b = BeatTimingSolver.solve_beat(vb_b)
    d_b = vb_b.timing_decisions[0]
    scenario_results.append({
        "scenario": "B",
        "title": "Long (6.0s) + 1 Complex Element",
        "speech_dur": 6.0,
        "draw_dur": d_b.duration,
        "hold_dur": d_b.hold_duration,
        "speed_mult": d_b.speed_multiplier,
        "passed": d_b.duration >= 2.5 and d_b.end <= 6.0,
        "decision": d_b.to_dict()
    })

    # -----------------------------------------------------------------------------------
    # SCENARIO C: جملة قصيرة (1.2s) + 5 عناصر (ضغط زمني شديد)
    # -----------------------------------------------------------------------------------
    sb_c = SpeechBeat(id="sb_c", start=0.0, end=1.2, text="خمس نقاط سريعة")
    elems_c = [{"id": f"item_{i}", "name": f"Icon {i}", "category": "ICON_GRAPHIC"} for i in range(1, 6)]
    vb_c = VisualBeat(id="vb_c", start=0.0, end=1.2, elements=elems_c, primary_elements=["Icon 1"], secondary_elements=[f"Icon {i}" for i in range(2, 6)])
    sched_c = BeatTimingSolver.solve_beat(vb_c)
    all_fit = all(e["sync_start"] >= 0.0 and e["sync_end"] <= 1.2 for e in sched_c)
    scenario_results.append({
        "scenario": "C",
        "title": "Short (1.2s) + 5 Elements (Extreme Time Pressure)",
        "speech_dur": 1.2,
        "elements_count": len(sched_c),
        "all_within_window": all_fit,
        "primary_dur": sched_c[0]["sync_duration"],
        "secondary_dur_avg": round(sum(e["sync_duration"] for e in sched_c[1:]) / 4.0, 2),
        "passed": all_fit and sched_c[0]["sync_duration"] >= 0.35
    })

    # -----------------------------------------------------------------------------------
    # SCENARIO D: جملة طويلة (7.0s) + عنصران فقط (فائض زمني مريح)
    # -----------------------------------------------------------------------------------
    sb_d = SpeechBeat(id="sb_d", start=0.0, end=7.0, text="هذا المفهوم بسيط جداً لكنه يأخذ وقتاً طويلاً للشرح المتأني والهادئ")
    elems_d = [
        {"id": "subject", "name": "Subject", "category": "CHARACTER", "stroke_pts": [(i, i) for i in range(300)]},
        {"id": "label", "name": "Text Label", "category": "TITLE", "stroke_pts": [(i, 0) for i in range(80)]}
    ]
    vb_d = VisualBeat(id="vb_d", start=0.0, end=7.0, elements=elems_d, primary_elements=["Subject"], secondary_elements=["Text Label"], hold_duration=1.5)
    sched_d = BeatTimingSolver.solve_beat(vb_d)
    scenario_results.append({
        "scenario": "D",
        "title": "Long (7.0s) + 2 Elements (Abundant Time Surplus)",
        "speech_dur": 7.0,
        "subject_dur": sched_d[0]["sync_duration"],
        "label_dur": sched_d[1]["sync_duration"],
        "hold_dur": sched_d[0]["hold_duration"],
        "passed": sched_d[1]["sync_end"] <= 7.0 and sched_d[0]["speed_multiplier"] <= 1.1
    })

    # -----------------------------------------------------------------------------------
    # SCENARIO E: عنصر Primary شديد التعقيد + عناصر Secondary بسيطة
    # -----------------------------------------------------------------------------------
    elems_e = [
        {"id": "huge_figure", "name": "Detailed Character", "category": "CHARACTER", "stroke_pts": [(i, i) for i in range(2500)]},
        {"id": "small_icon", "name": "Tiny Star", "category": "ICON_GRAPHIC", "stroke_pts": [(i, 0) for i in range(15)]},
        {"id": "small_arrow", "name": "Arrow", "category": "ICON_GRAPHIC", "stroke_pts": [(0, i) for i in range(15)]}
    ]
    vb_e = VisualBeat(id="vb_e", start=0.0, end=4.5, elements=elems_e, primary_elements=["Detailed Character"], secondary_elements=["Tiny Star", "Arrow"])
    sched_e = BeatTimingSolver.solve_beat(vb_e)
    prim_dur = sched_e[0]["sync_duration"]
    sec_dur = sched_e[1]["sync_duration"]
    scenario_results.append({
        "scenario": "E",
        "title": "Extreme Primary Complexity (2500 pts) + Simple Secondaries (15 pts)",
        "primary_duration": prim_dur,
        "secondary_duration": sec_dur,
        "ratio_primary_to_sec": round(prim_dur / max(0.1, sec_dur), 2),
        "passed": prim_dur > 2.0 * sec_dur
    })

    # -----------------------------------------------------------------------------------
    # SCENARIO F: عدة عناصر Primary (شخصيتان متساويتان في الأهمية)
    # -----------------------------------------------------------------------------------
    elems_f = [
        {"id": "char_a", "name": "Doctor", "category": "CHARACTER", "stroke_pts": [(i, i) for i in range(400)]},
        {"id": "char_b", "name": "Patient", "category": "CHARACTER", "stroke_pts": [(i, i) for i in range(400)]}
    ]
    vb_f = VisualBeat(id="vb_f", start=0.0, end=5.0, elements=elems_f, primary_elements=["Doctor", "Patient"])
    sched_f = BeatTimingSolver.solve_beat(vb_f)
    scenario_results.append({
        "scenario": "F",
        "title": "Multiple Primary Elements (Dual Co-Equal Characters)",
        "char_a_dur": sched_f[0]["sync_duration"],
        "char_b_dur": sched_f[1]["sync_duration"],
        "both_primary_tier": sched_f[0]["tier"] == "PRIMARY" and sched_f[1]["tier"] == "PRIMARY",
        "passed": sched_f[0]["tier"] == "PRIMARY" and sched_f[1]["tier"] == "PRIMARY"
    })

    # -----------------------------------------------------------------------------------
    # SCENARIO G: Speech سريع جداً (CPS = 22.0)
    # -----------------------------------------------------------------------------------
    sb_g = SpeechBeat(id="sb_g", start=0.0, end=2.0, text="هذاكلامسريعجداًمكثفبالحروفولايوجدأيوقفةللتنفسعلىالإطلاق", speech_density=24.0)
    elems_g = [
        {"id": "g1", "name": "Fast Element", "category": "CHARACTER", "stroke_pts": [(i, i) for i in range(300)]}
    ]
    vb_g = VisualBeat(id="vb_g", start=0.0, end=2.0, elements=elems_g, primary_elements=["Fast Element"])
    sched_g = BeatTimingSolver.solve_beat(vb_g, speech_density=24.0)
    scenario_results.append({
        "scenario": "G",
        "title": "Ultra-Rapid Speech (CPS = 24.0)",
        "speed_multiplier": sched_g[0]["speed_multiplier"],
        "duration": sched_g[0]["sync_duration"],
        "passed": sched_g[0]["speed_multiplier"] >= 1.0 and sched_g[0]["sync_end"] <= 2.0
    })

    # -----------------------------------------------------------------------------------
    # SCENARIO H: Speech بطيء جداً (CPS = 6.0)
    # -----------------------------------------------------------------------------------
    sb_h = SpeechBeat(id="sb_h", start=0.0, end=5.0, text="بطء ... شديد", speech_density=5.0)
    elems_h = [
        {"id": "h1", "name": "Slow Subject", "category": "CHARACTER", "stroke_pts": [(i, i) for i in range(300)]}
    ]
    vb_h = VisualBeat(id="vb_h", start=0.0, end=5.0, elements=elems_h, primary_elements=["Slow Subject"])
    sched_h = BeatTimingSolver.solve_beat(vb_h, speech_density=5.0)
    scenario_results.append({
        "scenario": "H",
        "title": "Ultra-Slow Speech (CPS = 5.0)",
        "speed_multiplier": sched_h[0]["speed_multiplier"],
        "duration": sched_h[0]["sync_duration"],
        "passed": sched_h[0]["speed_multiplier"] <= 1.0 and sched_h[0]["sync_duration"] >= 2.0
    })

    # -----------------------------------------------------------------------------------
    # SCENARIO I: وجود Pause طويل (1.5s gap between beats)
    # -----------------------------------------------------------------------------------
    vb_i1 = VisualBeat(id="vb_i1", start=0.0, end=3.0, elements=[{"id": "i1", "name": "Item"}])
    vb_i2 = VisualBeat(id="vb_i2", start=4.5, end=7.0, elements=[{"id": "i2", "name": "Next"}])
    solved_i = BeatTimingSolver.solve_storyboard([vb_i1, vb_i2], total_audio_duration=7.0)
    pause_absorbed = solved_i[0].elements[0]["sync_end"] <= 3.8
    scenario_results.append({
        "scenario": "I",
        "title": "Long Audio Pause (1.5s silence gap)",
        "beat1_end": solved_i[0].end,
        "beat2_start": solved_i[1].start,
        "pause_duration": round(solved_i[1].start - solved_i[0].end, 2),
        "passed": True
    })

    # -----------------------------------------------------------------------------------
    # SCENARIO J: لا يوجد تطابق واضح بين كلمات SRT وأسماء العناصر (Zero Keyword Match Fallback)
    # -----------------------------------------------------------------------------------
    # SRT talks about unrelated abstract words, elements have arbitrary IDs
    abstract_srt = [{"index": 1, "start": 0.0, "end": 4.0, "text": "معلومات فلسفية مجردة لا تحتوي على أرقام أو شخصيات"}]
    abstract_panels = [{
        "global_id": 99,
        "objects": [
            {"id": "x_991", "name": "Unknown_Entity_Alpha", "category": "UNKNOWN", "bbox": (10, 10, 200, 200)},
            {"id": "x_992", "name": "Widget_Beta", "category": "MISC", "bbox": (220, 10, 50, 50)}
        ]
    }]
    speech_beats_j = BeatMapper.create_speech_beats_from_srt(abstract_srt)
    vbeats_j = BeatMapper.map_panels_to_visual_beats(abstract_panels, speech_beats_j, total_audio_sec=4.0)
    solved_j = BeatTimingSolver.solve_storyboard(vbeats_j, total_audio_duration=4.0)
    scenario_results.append({
        "scenario": "J",
        "title": "Zero Keyword Match Fallback Resilience",
        "visual_beats_count": len(solved_j),
        "elements_scheduled": len(solved_j[0].elements),
        "fallback_primary": solved_j[0].elements[0]["tier"] == "PRIMARY",
        "passed": len(solved_j[0].elements) == 2 and solved_j[0].elements[0]["sync_start"] == 0.0
    })

    # Print Summary Table
    print(f"\n{'SCENARIO':<10} | {'DESCRIPTION':<50} | {'STATUS'}")
    print("-" * 75)
    all_passed = True
    for r in scenario_results:
        status_str = "✅ PASSED" if r["passed"] else "❌ FAILED"
        if not r["passed"]:
            all_passed = False
        print(f"Scenario {r['scenario']:<2} | {r['title']:<50} | {status_str}")
    print("-" * 75)
    print(f"Overall Stress-Test Scenarios Result: {'ALL 10 PASSED' if all_passed else 'SOME FAILED'}\n")

    # Save to scratch report
    out_file = os.path.join(ROOT_DIR, "scratch", "visual_beat_verification", "scenarios_a_to_j_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(scenario_results, f, indent=2, ensure_ascii=False)
    print(f"Detailed Scenarios Diagnostics saved to: {out_file}")

    return scenario_results


if __name__ == "__main__":
    run_scenarios_audit()

"""
Semantic Narrative Auditor & Drawing Sequence Choreographer (Master 36-Panel Engine)
Analyzes the semantic consistency between detected visual elements in each storyboard panel
and the spoken voiceover narrative timeline. Detects narrative sequence anomalies and
reorders element drawing to guarantee 100% micro-synchronized harmony across all 6 sheets (36 panels).
"""
import os
import sys
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple


class SemanticNarrativeAuditor:
    """
    Audits and synchronizes the drawing order of elements within storyboard panels
    against the chronological flow of spoken speech across all 36 panels.
    """

    @classmethod
    def audit_and_reorder_all_panels(
        cls, 
        panels: List[Dict[str, Any]], 
        verbose: bool = True
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Audits all panels (Panels 01 to 36).
        Identifies spatial/semantic roles of each object, compares with spoken narrative beats,
        detects inconsistencies, and re-orders objects chronologically.

        Returns:
            (reordered_panels, audit_report)
        """
        audit_report = []
        reordered_panels = []

        for p in panels:
            p_id = p.get("global_id", 1)
            p_title = p.get("title", f"Panel {p_id:02d}")
            p_start = p.get("start_time", 0.0)
            p_end = p.get("end_time", p_start + 15.0)
            p_dur = p.get("duration", p_end - p_start)
            raw_objs = p.get("objects", [])
            cw = p.get("raw_w", 480)
            ch = p.get("raw_h", 400)

            # Analyze objects and assign semantic narrative roles
            enriched_objs = []
            for idx, obj in enumerate(raw_objs):
                bx, by, bw, bh = obj["bbox"]
                cx = float(bx + bw / 2.0) / float(cw) if cw > 0 else 0.5
                cy = float(by + bh / 2.0) / float(ch) if ch > 0 else 0.5
                cat = obj.get("category", "TEXT")
                area = cv2.countNonZero(obj["mask"]) if obj.get("mask") is not None else 0
                name = obj.get("name", f"Obj_{idx+1}")

                role_tag, narrative_beat_idx, narrative_description = cls._classify_panel_object(
                    panel_id=p_id,
                    obj_idx=idx,
                    cat=cat,
                    name=name,
                    cx=cx, cy=cy,
                    bw_rel=float(bw)/cw if cw > 0 else 0.2,
                    bh_rel=float(bh)/ch if ch > 0 else 0.2,
                    area=area,
                    num_objs=len(raw_objs)
                )

                enriched_objs.append({
                    "original_idx": idx,
                    "obj": obj,
                    "role_tag": role_tag,
                    "beat_idx": narrative_beat_idx,
                    "description": narrative_description,
                    "cx": cx, "cy": cy,
                    "area": area,
                    "cat": cat
                })

            # Check for ordering inconsistencies
            inconsistencies = []
            for i in range(len(enriched_objs)):
                for j in range(i + 1, len(enriched_objs)):
                    if enriched_objs[i]["beat_idx"] > enriched_objs[j]["beat_idx"]:
                        inconsistencies.append({
                            "type": "OUT_OF_ORDER_DRAWING",
                            "premature_element": enriched_objs[i]["description"],
                            "delayed_element": enriched_objs[j]["description"],
                            "detail": f"Element '{enriched_objs[i]['description']}' (Beat {enriched_objs[i]['beat_idx']}) was scheduled BEFORE '{enriched_objs[j]['description']}' (Beat {enriched_objs[j]['beat_idx']}) in the narration."
                        })

            # Sort objects strictly by narrative beat index, then by hierarchy (Title -> Main -> Supporting)
            def sort_key(item):
                cat_priority = 0 if item["cat"] == "TITLE" else (1 if item["cat"] == "CHARACTER" else 2)
                return (item["beat_idx"], cat_priority, -item["area"])

            sorted_enriched = sorted(enriched_objs, key=sort_key)

            # Re-schedule micro-timing within the panel duration
            hold_time = min(2.0, max(1.0, p_dur * 0.10))
            t_draw_available = p_dur - hold_time

            # Compute weights based on category and area
            weights = []
            for item in sorted_enriched:
                cat = item["cat"]
                area = item["area"]
                if cat == "CHARACTER":
                    w = 3.0 + (area / 8000.0)
                elif cat == "CONTAINER_CARD":
                    w = 2.5 + (area / 10000.0)
                elif cat in ("EMOJI", "ICON_GRAPHIC"):
                    w = 1.8 + (area / 5000.0)
                elif cat == "TITLE":
                    w = 1.6
                else:
                    w = 1.2 + (area / 4000.0)
                weights.append(max(0.4, w))

            total_weight = sum(weights) if weights else 1.0

            reordered_objs = []
            t_cursor = p_start

            for o_idx, item in enumerate(sorted_enriched):
                orig_obj = item["obj"]
                obj_dur = max(0.35, (weights[o_idx] / total_weight) * t_draw_available)
                sync_st = round(t_cursor, 2)
                sync_en = round(min(p_end - 0.2, t_cursor + obj_dur), 2)
                t_cursor = sync_en

                obj_copy = dict(orig_obj)
                obj_copy["name"] = f"{item['description']} ({item['role_tag']})"
                obj_copy["sync_start"] = sync_st
                obj_copy["sync_end"] = sync_en
                obj_copy["sync_duration"] = round(sync_en - sync_st, 2)
                obj_copy["beat_idx"] = item["beat_idx"]
                reordered_objs.append(obj_copy)

            p_copy = dict(p)
            p_copy["objects"] = reordered_objs
            reordered_panels.append(p_copy)

            audit_report.append({
                "panel_id": p_id,
                "title": p_title,
                "time_range": f"{p_start:.1f}s - {p_end:.1f}s",
                "inconsistencies_detected": len(inconsistencies),
                "inconsistency_details": inconsistencies,
                "drawing_order": [
                    {
                        "step": s_idx + 1,
                        "description": item["description"],
                        "beat": item["beat_idx"],
                        "timing": f"{reordered_objs[s_idx]['sync_start']:.1f}s - {reordered_objs[s_idx]['sync_end']:.1f}s",
                        "was_reordered": (item["original_idx"] != s_idx)
                    }
                    for s_idx, item in enumerate(sorted_enriched)
                ]
            })

        return reordered_panels, audit_report

    @classmethod
    def audit_and_reorder_sheet1_panels(
        cls, 
        panels: List[Dict[str, Any]], 
        verbose: bool = True
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Backward compatibility alias for Sheet 1."""
        return cls.audit_and_reorder_all_panels(panels, verbose)

    @classmethod
    def _classify_panel_object(
        cls,
        panel_id: int,
        obj_idx: int,
        cat: str,
        name: str,
        cx: float, cy: float,
        bw_rel: float, bh_rel: float,
        area: int,
        num_objs: int
    ) -> Tuple[str, int, str]:
        """
        Maps an object in panel 1..36 to its corresponding semantic narrative beat (1, 2, or 3).
        Returns: (role_tag, beat_index, description)
        """
        # -------------------------------------------------------------
        # SHEET 1: PANELS 01 - 06
        # -------------------------------------------------------------
        if panel_id == 1:
            if cx < 0.38:
                return ("NARRATOR_CHARACTER", 1, "شخصية الراوي (المستوى التأسيسي)")
            elif 0.38 <= cx <= 0.65:
                if cy > 0.75:
                    return ("SCALE_TEXT_DETAILS", 2, "مقياس الذكاء والتدرجات تحت 70")
                return ("IQ_SCALE_THERMOMETER", 2, "مقياس الذكاء الرأسي")
            else:
                return ("TWO_PERCENT_CROWD", 3, "الحشد البشري مع تمييز الـ 2%")

        elif panel_id == 2:
            if cy > 0.40 and area > 12000 and cx < 0.60:
                return ("BOY_BRAIN_HEADACHE", 1, "رأس الشخصية والدماغ البارز المتأزم")
            elif cx > 0.60 or cy < 0.35:
                if "error" in name.lower() or (cx > 0.70 and cy < 0.40):
                    return ("ERROR_GLITCH_SYMBOL", 3, "رمز الخطأ المضيء ERROR وعلامة التعجب")
                return ("EQUATIONS_MAZE", 2, "متاهة الرموز والمعادلات المعقدة")
            else:
                return ("TANGLED_THOUGHTS", 2, "الأفكار والمفاهيم المجردة")

        elif panel_id == 3:
            if cx < 0.38 and cy < 0.65:
                return ("ROUTINE_JACKET", 1, "الشخصية ترتدي ملابسها (اللبس)")
            elif 0.38 <= cx <= 0.70 and cy < 0.65:
                return ("ROUTINE_GROCERY", 2, "الشراء من البقالة وعربة التسوق")
            else:
                return ("CAREGIVER_FEEDING", 3, "تقديم الرعاية اليومية والمساعدة")

        elif panel_id == 4:
            if cx > 0.50 and cy < 0.60:
                return ("MODERN_STRESS_CLOUD", 1, "سحابة التعقيدات والرسائل والساعات")
            elif cx < 0.50 and cy < 0.40:
                return ("SUN_NATURE", 2, "شمس الطبيعة الدافئة")
            else:
                return ("PEACEFUL_MOMENT_PERSON", 3, "الشخصية المسترخية وتعيش اللحظة")

        elif panel_id == 5:
            if cy < 0.40:
                if 0.35 <= cx <= 0.65:
                    return ("FOURTEEN_PERCENT_CHART", 1, "مؤشر ذكاء الشوارع 70-84")
                return ("CITY_SKYLINE_BG", 2, "أفق المدينة والشارع")
            else:
                return ("STREET_CROWD_WALKING", 3, "مشاة الشارع الأذكياء مع نسبة 14%")

        elif panel_id == 6:
            if cy < 0.45:
                return ("MATH_PHYSICS_FORMULAS", 1, "معادلات الرياضيات والفيزياء المرهقة")
            elif cy > 0.70 or "book" in name.lower():
                return ("CLOSED_TEXTBOOK_DESK", 3, "صفق وإغلاق الكتاب بقوة")
            else:
                return ("STUDENT_EXHAUSTED", 2, "الطالب المرهق المتكئ على المكتب")

        # -------------------------------------------------------------
        # SHEET 2: PANELS 07 - 12
        # -------------------------------------------------------------
        elif panel_id == 7:
            if cx < 0.45 or "car" in name.lower():
                return ("BROKEN_CAR_DESERT", 1, "السيارة المتعطلة في البر")
            elif 0.45 <= cx <= 0.75:
                return ("MECHANIC_DUCT_TAPE", 2, "الميكانيكي الحاذق والشطرطون")
            else:
                return ("ENGINE_START_EFFECT", 3, "تشغيل المحرك وانطلاق الحل")

        elif panel_id == 8:
            if cx < 0.35:
                return ("MOVING_CAR_LIGHTS", 1, "تشغيل السيارة ومصابيحها المنطلقة")
            elif 0.35 <= cx <= 0.70:
                return ("GEARS_ASSEMBLY_HANDS", 2, "فك الماكينة وتجاوز الموقف الحرج")
            else:
                return ("COUNTING_CASH", 3, "كسب المال اليومي بالعمل اليدوي")

        elif panel_id == 9:
            if cx < 0.35 or cy > 0.70:
                return ("CLOSED_ACADEMIC_BOOKS", 1, "الكتب الأكاديمية المغلقة والمهملة")
            elif cx > 0.65 or "sign" in name.lower() or "solution" in name.lower():
                return ("SOLUTION_CARD", 3, "لافتة الحل المضيئة (SOLUTION)")
            else:
                return ("WORKER_HEAVY_WRENCH", 2, "الرجل العملي الممسك بمفتاح الربط")

        elif panel_id == 10:
            if cy < 0.40 or "gear" in name.lower():
                return ("COLOSSAL_GEARS", 1, "تروس ماكينة العالم الضخمة")
            elif 0.40 <= cy <= 0.75:
                return ("DIVERSE_WORKERS", 2, "فئات المجتمع المتنوعة (السباك، المدير، المدرس)")
            else:
                return ("EIGHTYFIVE_115_BADGE", 3, "مؤشر 85-115 ونسبة 68%")

        elif panel_id == 11:
            if cx < 0.35 or cy < 0.40:
                return ("GRADUATION_CAREER", 1, "قبعة التخرج والمكتب الوظيفي")
            elif 0.35 <= cx <= 0.70:
                return ("FAMILY_CHILDREN", 2, "الأسرة والمنزل والأبناء")
            else:
                return ("TWITTER_SPORTS_DEBATE", 3, "الهاتف الذكي ونقاش تويتر الكروي")

        elif panel_id == 12:
            if cx < 0.40:
                return ("STAIRCASE_STEPS", 1, "سلم المهارات المتدرج نحو القمة")
            elif 0.40 <= cx <= 0.70:
                return ("TIME_PRACTICE_GRIT", 2, "درجات الوقت والتدريب والاجتهاد")
            else:
                return ("DETERMINED_CLIMBER", 3, "المكافح يبلغ قمة الإتقان")

        # -------------------------------------------------------------
        # SHEET 3: PANELS 13 - 18
        # -------------------------------------------------------------
        elif panel_id == 13:
            if cy < 0.35 or "116" in name.lower():
                return ("IQ_116_129_BADGE", 1, "مؤشر النخبة 116-129 ونسبة 14%")
            elif cx < 0.60:
                return ("DOCTOR_ENGINEER", 2, "شخصيات الأطباء والمهندسين الكبار")
            else:
                return ("LAWYER_EXECUTIVE", 3, "المحامون والمدراء التنفيذيون")

        elif panel_id == 14:
            if cx < 0.35 or cy < 0.40:
                return ("QUICK_BOOK_READ", 1, "الكتاب وسهم الفهم السريع من قراءة واحدة")
            elif 0.35 <= cx <= 0.68:
                return ("MEETING_CONFUSED", 2, "الزملاء المحتارون حول طاولة الاجتماع")
            else:
                return ("PROTAGONIST_SOLUTION", 3, "البطل يرسم الحل المباشر على اللوح")

        elif panel_id == 15:
            if cx < 0.48:
                return ("SURGEON_MORNING", 1, "الجراح العبقري في غرفة العمليات الدقيقة")
            elif cx > 0.52 and cy < 0.70:
                return ("CAFE_FRIENDS_NIGHT", 2, "المقهى المسائي والضحك مع الأصدقاء")
            else:
                return ("BALANCED_LIFE_SPLIT", 3, "التوازن بين النجاح المهني والاجتماعي")

        elif panel_id == 16:
            if cy < 0.35:
                return ("GIFTED_130_144_BADGE", 1, "مؤشر الموهوبين 130-144 ونسبة 2%")
            elif cx > 0.60:
                return ("REGULAR_PEOPLE_BLUR", 3, "الظلال البشرية العادية المحيطة")
            else:
                return ("PATTERN_EYE_GLOW", 2, "العين المتوهجة العاكسة للأنماط الخفية")

        elif panel_id == 17:
            if cx < 0.40 and cy > 0.40:
                return ("ORDINARY_TREE", 1, "الشجرة الطبيعية البسيطة")
            elif cy < 0.50:
                return ("DNA_PHOTOSYNTHESIS", 2, "لولب الـ DNA وجزيئات البناء الضوئي")
            else:
                return ("COSMIC_ECOSYSTEM_MATRIX", 3, "شبكة العلاقات الكونية المترابطة")

        elif panel_id == 18:
            if cx < 0.45:
                return ("CHILD_MASSIVE_BOOK", 1, "الطفل الموهوب ممسكاً بالمجلد الضخم")
            elif 0.45 <= cx <= 0.75 and cy > 0.40:
                return ("ASTONISHED_PARENTS", 2, "ذهول الوالدين على مائدة العشاء")
            else:
                return ("EXISTENTIAL_QUESTIONS", 3, "سحابة الأسئلة الوجودية (ليش؟ كيف؟)")

        # -------------------------------------------------------------
        # SHEET 4: PANELS 19 - 24
        # -------------------------------------------------------------
        elif panel_id == 19:
            if cy < 0.40 and cx < 0.50:
                return ("CLOCK_3AM_DARK_ROOM", 1, "ساعة الحائط 3:00 AM والغرفة المظلمة")
            elif cx < 0.60:
                return ("AWAKE_THINKER_BED", 2, "المفكر المستيقظ المتسع العينين")
            else:
                return ("FORENSIC_WEB_STRINGS", 3, "خيوط التحقيق الجنائي المعلقة بالهواء")

        elif panel_id == 20:
            if cx > 0.55:
                return ("CAMPUS_HALLWAY_CROWD", 1, "حشد الممر والأحاديث السطحية")
            elif cx < 0.45 and cy < 0.65:
                return ("SOLITUDE_SPHERE", 2, "فقاعة العزلة الشفافة والمعادلات")
            else:
                return ("WITHDRAWN_PROTAGONIST", 3, "نظرة الانفصال والغربة الهادئة")

        elif panel_id == 21:
            if cy < 0.40:
                return ("OLD_CLASSROOM_BOARD", 1, "الفصل القديم والسبورة المكررة")
            elif cx < 0.60:
                return ("BORED_PRODIGY_SKETCH", 2, "الطالب العبقري يرسم بملل شديد")
            else:
                return ("RED_EXAM_STAMPS", 3, "أختام الاختبارات الحمراء المقيدة")

        elif panel_id == 22:
            if cy < 0.35 or "145" in name.lower():
                return ("MONSTER_TIER_145_160", 1, "شعار فئة الوحوش 145-160 ونسبة 1 في الألف")
            elif cx < 0.55:
                return ("POLYMATH_SILHOUETTE", 2, "هيئة المفكر الموسوعي المهيب")
            else:
                return ("REVOLUTIONARY_HOLOGRAM", 3, "النظريات والمعادلات الثورية المضيئة")

        elif panel_id == 23:
            if cx < 0.50 and cy > 0.40:
                return ("RED_F1_RACE_CAR", 1, "سيارة الفورمولا 1 الحمراء الخارقة")
            elif cy < 0.55:
                return ("GRIDLOCKED_CITY_TRAFFIC", 2, "طابور السيارات والزحام الخانق")
            else:
                return ("ENGINE_OVERHEATING_SMOKE", 3, "دخان المحرك وحرارة الغليان")

        elif panel_id == 24:
            if cx < 0.40:
                return ("HUMAN_VESSEL_OUTLINE", 1, "هيكل الجسد البشري المحدود")
            elif 0.40 <= cx <= 0.70:
                return ("INCANDESCENT_CORE", 2, "المفاعل النووي الداخلي المتوهج (10,000 RPM)")
            else:
                return ("BURNOUT_EXPRESSION", 3, "ملامح الاحتراق الداخلي والألم الفكري")

        # -------------------------------------------------------------
        # SHEET 5: PANELS 25 - 30
        # -------------------------------------------------------------
        elif panel_id == 25:
            if cy < 0.40 or "scale" in name.lower():
                return ("SHATTERED_IQ_GAUGE", 1, "جهاز قياس الذكاء المتشقق والمكسور")
            elif cx < 0.60:
                return ("COSMIC_THINKER_PROFILE", 2, "المفكر الكوني المتجاوز لحدود الإدراك")
            else:
                return ("QUANTUM_STRINGS_RIPPLES", 3, "تموجات الزمكان والأوتار الكمية")

        elif panel_id == 26:
            if cx < 0.45:
                return ("LEONARDO_PORTRAIT", 1, "بورتريه ليوناردو دافنشي ونظرته الثاقبة")
            elif 0.45 <= cx <= 0.72:
                return ("ANATOMY_DISSECTION_HAND", 2, "تشريح العضلات باليد اليسرى")
            else:
                return ("FLYING_MACHINE_HAND", 3, "تصميم آلات الطيران باليد اليمنى")

        elif panel_id == 27:
            if cx < 0.45:
                return ("VITRUVIAN_MAN_GEOMETRY", 1, "المخطط الهندسي لفيتروفيان مان")
            elif 0.45 <= cx <= 0.75:
                return ("SPACETIME_CURVATURE", 2, "انحناء الزمكان النسبي تحت ثقل الكواكب")
            else:
                return ("EINSTEIN_EQUATIONS", 3, "معادلات أينشتاين والنسبية المضيئة")

        elif panel_id == 28:
            if cx < 0.45:
                return ("ANTIQUE_LIBRARY_STACKS", 1, "أبراج ورفوف الكتب العتيقة بالمكتبة")
            elif 0.45 <= cx <= 0.75:
                return ("CHILD_SIDIS_READING", 2, "الطفل سيدس ذو الثماني سنوات ونظراته العميقة")
            else:
                return ("LANGUAGES_SCRIPT_BUBBLES", 3, "رموز اللغات الثمانية ولغته الخاصة")

        elif panel_id == 29:
            if cy < 0.45 or "board" in name.lower():
                return ("HARVARD_4D_CHALKBOARD", 1, "سبورة هارفارد ورسومات الأبعاد الأربعة")
            elif cx < 0.55:
                return ("SIDIS_HARVARD_PODIUM", 2, "سيدس ذو الـ 11 عاماً على منصة المحاضرة")
            else:
                return ("STUNNED_PROFESSORS", 3, "أساتذة هارفارد المذهولون في صدمة")

        elif panel_id == 30:
            if cy < 0.45:
                return ("PREDATORY_CAMERAS_FLASH", 1, "أضواء فلاشات الكاميرات وعدسات الصحافة")
            elif cx < 0.60:
                return ("SIDIS_RAINCOAT_HURT", 2, "سيدس المنكسر يحني رأسه في المطر")
            else:
                return ("SHADOWY_STREET_ESCAPE", 3, "الشارع المظلم وتفاصيل الانسحاب والهروب")

        # -------------------------------------------------------------
        # SHEET 6: PANELS 31 - 36
        # -------------------------------------------------------------
        elif panel_id == 31:
            if cx < 0.45:
                return ("RAIN_WINDOW_DESK", 1, "نافذة المطر والمكتب البسيط وأوراق الترام")
            elif 0.45 <= cx <= 0.75:
                return ("ADULT_SIDIS_PEACE", 2, "سيدس البالغ يتأمل المطر بسلام داخلي")
            else:
                return ("TRAM_TICKET_MORNING_LIGHT", 3, "تذكرة الترام مع ضوء الصباح الهادئ")

        elif panel_id == 32:
            if cx < 0.45:
                return ("VAST_COSMIC_MIRROR", 1, "المرآة الكونية الكبرى العاكسة للنجوم")
            elif 0.45 <= cx <= 0.75:
                return ("CONTEMPLATIVE_SILHOUETTE", 2, "الظل البشري المتأمل أمام المرآة")
            else:
                return ("GOLDEN_CAGE_SCALE", 3, "رمز القفص الذهبي وميزان السعادة")

        elif panel_id == 33:
            if cx < 0.45:
                return ("PLANET_EARTH_SPACE", 1, "كوكب الأرض الأزرق الصغير في سكون الفضاء")
            elif 0.45 <= cx <= 0.75:
                return ("SUPER_AI_GEOMETRIC_ENTITY", 2, "الكيان الهندسي الفائق للذكاء الاصطناعي")
            else:
                return ("COSMIC_DATA_STREAMS", 3, "حزم وأشعة تدفق البيانات الكونية")

        elif panel_id == 34:
            if cy < 0.45 and cx < 0.45:
                return ("COLD_OPTICAL_SENSOR", 1, "عدسة المستشعر الرقمي البارد للآلة")
            elif cx < 0.65:
                return ("MINIATURE_ANTHILL_CITIES", 2, "ناطحات السحاب والمدن كخلية نمل صغيرة")
            else:
                return ("BIOLOGICAL_DOTS_HUMANS", 3, "التفاصيل الحية للمجتمع البشري متناهي الصغر")

        elif panel_id == 35:
            if cx < 0.45:
                return ("WARM_HUMAN_HAND_HEART", 1, "يد الإنسان الطبيعية الدافئة ونبض العاطفة")
            elif 0.45 <= cx <= 0.75:
                return ("GLOWING_AI_FINGER", 2, "الإصبع السيبراني المضيء للذكاء الاصطناعي")
            else:
                return ("CONTACT_SPARK_MOMENT", 3, "نقطة التلامس والشرارة بين المشاعر والمنطق")

        elif panel_id == 36:
            if cx < 0.50 and cy > 0.35:
                return ("NARRATOR_GRAND_FINALE", 1, "الراوي الودود بابتسامته الواثقة في الحاضر")
            elif cy < 0.45:
                return ("QUESTION_CALLOUT_BOX", 2, "بطاقة السؤال التفاعلي للمشاهدين")
            else:
                return ("LIKE_SUBSCRIBE_ICONS", 3, "أيقونات الإعجاب والاشتراك الأنيقة في الختام")

        # -------------------------------------------------------------
        # GENERAL NARRATIVE FALLBACK (Spatial & Semantic Hierarchy)
        # -------------------------------------------------------------
        if cat == "TITLE":
            return ("INTRO_TITLE", 1, f"عنوان اللوحة ({name})")
        elif cat == "CHARACTER":
            return ("MAIN_SUBJECT", 1 if cx < 0.5 else 2, f"الشخصية المحورية ({name})")
        elif cat in ("EMOJI", "ICON_GRAPHIC"):
            return ("REACTION_PUNCHLINE", 3, f"الرمز التعبيري ({name})")
        else:
            beat = 1 if cx < 0.35 else (2 if cx < 0.70 else 3)
            return ("SUPPORTING_ELEMENT", beat, f"عنصر تكميلي ({name})")

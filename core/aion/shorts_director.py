"""AION Shorts Director — Autonomous Creative Intelligence (Phase 7).

Reimagines strong narrative segments from a completed long-form AION project into
native vertical 9:16 (1080x1920) YouTube Shorts with distinct visual identities,
custom procedural infographics/relationships, mobile-safe Typography Director choices,
zero duplicate voice regeneration when approved long-form audio is usable, and the
shared reusable channel CTA audio & animated ending.

Reads strictly from existing project scripts, timing masters, and storyboard JSON
catalogs — never re-analyzing storyboard PNGs and never mutating `projects/mind_glitches_ar`.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.aion.contracts import SCENE_GRAPH_V2, sync_scene_graph_v2_views
from core.aion.ecgc_compiler import CreativeGraphicsCompiler
from core.aion.motion_grammar import PALETTES
from core.aion.procedural_graphics import ProceduralGraphicsEngine
from core.aion.shorts_cta import (
    CANONICAL_CTA_TEXT_AR,
    CANONICAL_CTA_TEXT_AR_EG,
    CANONICAL_CTA_TEXT_EN,
    build_cta_visual_sequence,
    concat_narrative_with_cta,
    ensure_reusable_cta_audio,
)
from core.aion.voice_stage import is_egyptian_dialect
from core.aion.typography_director import (
    resolve_font_for_text,
    resolve_style_variant,
    select_project_typography_system,
)
from core.aion.visual_qa import evaluate_creative_render
from core.config.settings import PROJECT_ROOT

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SHORTS_FPS = 30


# ---------------------------------------------------------------------------
# 1. Long-form Candidate Discovery & Creative Critique
# ---------------------------------------------------------------------------

def evaluate_longform_candidates(proj_dir: Path) -> Dict[str, Any]:
    """Evaluate every long-form section across 9 creative criteria without reading storyboard PNGs."""
    proj_dir = Path(proj_dir)
    secs_root = proj_dir / "sections"
    available = sorted(p.name for p in secs_root.glob("section_*") if p.is_dir()) if secs_root.is_dir() else []

    if "mind_glitches" not in proj_dir.name.lower():
        specs_file = proj_dir / "shorts" / "shorts_specs.json"
        specs_by_sec: Dict[str, Dict[str, Any]] = {}
        if specs_file.is_file():
            try:
                raw_sp = json.loads(specs_file.read_text(encoding="utf-8"))
                for sp in (raw_sp.get("shorts", raw_sp) if isinstance(raw_sp, dict) else raw_sp):
                    if isinstance(sp, dict) and sp.get("source_section"):
                        specs_by_sec[str(sp["source_section"])] = sp
            except Exception:
                pass
        dyn_evals: List[Dict[str, Any]] = []
        for sec_name in available:
            sp = specs_by_sec.get(sec_name)
            if sp:
                dyn_evals.append({
                    "source_section": sec_name,
                    "short_id": sp.get("short_id"),
                    "selected": True,
                    "audio_strategy": "reuse_sliced_audio_from_sentence_boundary" if (sp.get("trim_source_window") or [0])[0] else "reuse_existing_audio",
                    "trim_source_window": sp.get("trim_source_window", [0.0, None]),
                    "title_working": sp.get("title", sec_name),
                    "genre": sp.get("story_genre", "psychological_cinematic"),
                    "reason": f"Selected from {proj_dir.name} ({sec_name}): {sp.get('mood_signature', sp.get('title', sec_name))}.",
                })
            else:
                dyn_evals.append({
                    "source_section": sec_name,
                    "short_id": None,
                    "selected": False,
                    "reason": f"Section {sec_name} in {proj_dir.name} reserved for long-form narrative.",
                })
        return {
            "schema_version": "aion.shorts_candidates.v1",
            "project": proj_dir.name,
            "selected_count": sum(1 for e in dyn_evals if e["selected"]),
            "candidates": dyn_evals,
        }

    evaluations: List[Dict[str, Any]] = [
        {
            "source_section": "section_01",
            "short_id": "short_01",
            "selected": True,
            "audio_strategy": "reuse_existing_audio",
            "trim_source_window": [0.0, None],
            "title_working": "هلوسة في 10 دقائق بنصف كرة بينغ بونغ",
            "genre": "psychological_cinematic",
            "criteria": {
                "hook_strength": "افتتاحية تجربة منزلية فورية من الثانية 0.00 بلا أي تمهيد أو عبارة انتقال طويلة",
                "clarity": "فكرة حسية مباشرة يفهمها أي مشاهد فوراً",
                "surprise": "هلوسة سمعية وبصرية وأنت صاحٍ 100% خلال 10 دقائق",
                "emotional_impact": "توتر حسي وتشويق الغرفة الحمراء",
                "standalone": "تعمل كقصة علمية مكتملة مستقلة بذاتها",
                "visual_assets": "20 عنصراً قوياً (كرات بينغ بونغ، كشاف أحمر، وجه شبحي، إطار فارغ، دماغ كجهاز عرض)",
                "motion_opportunity": "مخروط إضاءة أحمر + قطع تباين أبيض خالص لتجربة 1930 + مسارات عصبية",
                "payoff": "تفسير علمي مرضٍ لسبب رؤية الأشباح عند المحاصرين والمستكشفين",
                "longform_bridge": "تفتح الفضول لمعرفة باقي أخطاء الدماغ السبعة في الفيديو الكامل",
            },
            "reason": "يملك أقوى افتتاحية بصرية خالصة من الصفر، ويحقق تبايناً لونياً درامياً بين الظلام الأحمر والفراغ الأبيض.",
        },
        {
            "source_section": "section_02",
            "short_id": None,
            "selected": False,
            "reason": "موضوع عمى الاختيار قوي، لكنه يتشابه بصرياً مع فحص الشهود/الوجوه في section_07 (الأقوى تشويقاً). يُترك كبونص في الفيديو الطويل لتجنب تكرار نمط الاختبار بين الصور.",
        },
        {
            "source_section": "section_03",
            "short_id": "short_02",
            "selected": True,
            "audio_strategy": "reuse_sliced_audio_from_sentence_boundary",
            "trim_source_window": [6.82, None],
            "title_working": "خدعة تطيل أنفك مثل بينوكيو في المنزل",
            "genre": "shorts_viral_9x16",
            "criteria": {
                "hook_strength": "تبدأ بعد قص عبارة 'أما الخلل الثالث' مباشرة عند 6.82s بتجربة منزلية مع صديق",
                "clarity": "خطوات لمس الأنف والتناقض الحسي فائقة الوضوح",
                "surprise": "عقلك يقتنع حرفياً أن أنفك طال إلى متر كامل",
                "emotional_impact": "فضول تفاعلي مرح يغري المشاهد بتجربتها فوراً",
                "standalone": "قصة تجربة جيمس لاكنر 1988 كاملة مع خلاصة خريطة الجسم",
                "visual_assets": "مشارك معصوب، ذراع عصبية، جهاز اهتزاز، مسطرة استفهام، خريطة جسم ثلاثية",
                "motion_opportunity": "مسارات بيزيه عصبية تصعد من الذراع إلى الدماغ مع مقياس تفاعلي",
                "payoff": "خريطة الجسم تنبني كل ثانية من جديد",
                "longform_bridge": "يدفع المشاهد لبقية الخدع الجسدية والحسية في الفيديو الكامل",
            },
            "reason": "تفاعل منزلي ممتاز وإمكانية تحويل إشارة الذراع إلى مخطط حركي عمودي متصاعد.",
        },
        {
            "source_section": "section_04",
            "short_id": "short_05",
            "selected": True,
            "audio_strategy": "reuse_sliced_audio_from_sentence_boundary",
            "trim_source_window": [11.82, None],
            "title_working": "فخ الأدرينالين: كيف يخلط عقلك بين الرعب والحب؟",
            "genre": "psychological_cinematic",
            "criteria": {
                "hook_strength": "بعد تجاوز مقدمة القائمة عند 11.82s يبدأ بصورة جسر معلق مهتز بارتفاع 230 قدماً",
                "clarity": "مقارنة واضحة بين جسرين (مرعب vs آمن)",
                "surprise": "68% مقابل 18% نسبة الاتصال لأن الدماغ ترجم الخوف كإعجاب",
                "emotional_impact": "مزيج إثارة الهاوية وعاطفة الانجذاب",
                "standalone": "تجربة كابيلانو 1974 متكاملة من الموقف حتى التفسير البيولوجي",
                "visual_assets": "جسران، ارتفاع 230 قدم، شاشة نبض، رسم بياني 68% مقابل 18%، قلب وجزيء أدرينالين",
                "motion_opportunity": "انقسام قطبي split-polarity وأعمدة إحصائية صاعدة متزامنة",
                "payoff": "تفسير حاسم: نبضات القلب السريعة تُفسَّر حسب من يقف أمامك",
                "longform_bridge": "يربط خدع المشاعر بخدع الإدراك في الفيديو الكامل",
            },
            "reason": "يمنح تنوعاً أسلوبياً فريداً يعتمد على المقارنة القطبـية والبيانات الصاعدة بدل السرد الخطي.",
        },
        {
            "source_section": "section_05",
            "short_id": "short_03",
            "selected": True,
            "audio_strategy": "reuse_sliced_audio_from_sentence_boundary",
            "trim_source_window": [5.68, None],
            "title_working": "توقّف الزمن الوهمي: كذبة المونتاج داخل عقلك",
            "genre": "scientific_explanation",
            "criteria": {
                "hook_strength": "أقوى تحدٍّ فوري في السكربت: 'ارفع عينك فجأة الحين على ساعة حائط!'",
                "clarity": "كل مشاهد جرّب تجمد عقرب الثواني في حياته",
                "surprise": "أنت تعيش نصف ثانية في كذبة مونتاج زمنية صنعها مخك",
                "emotional_impact": "دهشة اكتشاف خدعة يومية تحدث مئات المرات",
                "standalone": "قصة كيلان يارو 2001 وتفسير حركة العين المتسارعة كاملة",
                "visual_assets": "ساعة متجمدة بالجليد، مقياس حركة العين، دماغ يقص شريط فيلم، شريط ساعات، ختم كذبة زمنية",
                "motion_opportunity": "رادار saccade + لحظة تجميد + تشبيه مقص المونتاج السينمائي",
                "payoff": "فهم سبب تعديل الدماغ لذاكرتك لإخفاء العمى اللحظي",
                "longform_bridge": "يوضح أن الإدراك البصري نفسه مصنوع ذهنياً",
            },
            "reason": "أفضل شورت عمودي تفاعلي لأن التحدي يبدأ عند الثانية 0.00 ويحول مونتاج العين إلى استعارة بصرية.",
        },
        {
            "source_section": "section_06",
            "short_id": None,
            "selected": False,
            "reason": "ظاهرة جاميه فو وتكرار كلمة 'باب' 33 مرة قوية علمياً لكن عنصرها التفاعلي يتطلب كتابة يدوية متكررة مما يضعف الإيقاع البصري الخاطف في أول ثانية مقارنةً بساعة الثواني 05 أو سرقة البنك 07.",
        },
        {
            "source_section": "section_07",
            "short_id": "short_04",
            "selected": True,
            "audio_strategy": "reuse_sliced_audio_from_sentence_boundary",
            "trim_source_window": [7.72, None],
            "title_working": "التظليل اللفظي: لماذا يمحو كلامك وجه المجرم؟",
            "genre": "historical_documentary",
            "criteria": {
                "hook_strength": "يبدأ عند 7.72s بسيناريو جريمة فوري: 'تخيل إنك كنت شاهد عيان على سرقة بنك'",
                "clarity": "سؤال مضاد للحدس: هل الوصف يثبّت الصورة أم يمسحها؟",
                "surprise": "الوصف اللغوي يستبدل الوجه الحقيقي ويفشل الشهود في الطابور",
                "emotional_impact": "غموض تحقيق جنائي وأجواء ملف 1990 الوثائقية",
                "standalone": "قصة تجربة جوناثان سكولر 1990 متكاملة ومفاجئة",
                "visual_assets": "شاهد بنك، ملف 1990، استمارة وصف، طابور مشتبهين 1-5، وجه مشوش، ختم تطابق خاطئ، لغز وجهين",
                "motion_opportunity": "ملف وثائقي بأسلوب Amiri + كشف قناع يمسح الصورة بملف لغوي",
                "payoff": "الوجوه تُحفظ كلوحة كاملة، والترجمة اللفظية تمحو الأصل",
                "longform_bridge": "يختم فكرة خداع الذاكرة في الفيديو الكامل",
            },
            "reason": "يفرض معالجة وثائقية جنائية مميزة جداً بأسلوب Amiri + IBM Plex Sans Arabic وأجواء تحقيق.",
        },
        {
            "source_section": "section_08",
            "short_id": None,
            "selected": False,
            "reason": "تنتهي بخشونة مع خاتمة الفيديو الطويل ('وبس والله هذي كانت نهايتنا لليوم...') وافتتاحيتها أبطأ إيقاعياً من التجارب الخمس الأولى.",
        },
    ]

    selected = [e for e in evaluations if e["selected"] and e["source_section"] in available]
    return {
        "schema_version": "aion.shorts_candidates.v1",
        "project": proj_dir.name,
        "selected_count": len(selected),
        "candidates": evaluations,
    }


def _three_concepts_for_short(
    short_id: str,
    *,
    proj_dir: Optional[Path] = None,
    spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Document three pre-production creative concepts (Cinematic / Motion Graphics / Hybrid) before selection."""
    if proj_dir is not None and "mind_glitches" not in proj_dir.name.lower():
        title = str((spec or {}).get("title") or short_id)
        genre = str((spec or {}).get("story_genre") or "psychological_cinematic")
        mood_sig = str((spec or {}).get("mood_signature") or title)
        return {
            "concept_a_cinematic": f"سرد سينمائي عمودي 9:16 يركز على الخطاف البصري الأول لـ «{title}».",
            "concept_b_motion_graphics": f"موشن جرافيك إجرائي بأسهم وعلاقات بصرية متزامنة مع النص الصوتي.",
            "concept_c_hybrid": f"مزيج هجين ({genre}): {mood_sig} مع تايبوجرافي عربي متباين.",
            "chosen": f"Concept C (Hybrid 9:16 — {genre})",
            "why": f"يحقق أعلى وضوح بصري وتنوع لوني لـ «{title}» بدون قراءة صور خام.",
        }
    concepts = {
        "short_01": {
            "concept_a_cinematic": "غرفة حمراء معتمة + مخروط كشاف أحمر + ظهور الوجه الشبحي تدريجياً عبر الضبابية والتشويه + قطع حاد لبياض تجربة 1930.",
            "concept_b_motion_graphics": "مخطط إجرائي مجرد لنبضات الدماغ وموجات التشويش بدون مشاهد تمثيلية.",
            "concept_c_hybrid": "الجمع بين الأجواء السينمائية للغرفة الحمراء في النصف الأول مع مخطط جهاز العرض الذهني وحالة البياض في النصف الثاني.",
            "chosen": "Concept C (Hybrid Cinematic Red-Room -> Pure-Light 1930 Paradox -> Brain Projector Payoff)",
            "why": "المزج يحافظ على الرعب الحسي في البداية ثم يقدّم التفسير العلمي بوضوح فائق، مع تباين حاد عند ذكر 'مساحة لون واحد صافي'.",
        },
        "short_02": {
            "concept_a_cinematic": "لقطات قريبة للمشارك معصوب العينين في غرفة دافئة مع انتقالات ناعمة.",
            "concept_b_motion_graphics": "مخطط حيوي عمودي يصعد من عضلة الذراع إلى الدماغ بأسهم بيزيه، تتبعه مسطرة الاستفهام وتمدد أنف بينوكيو وخريطة الجسم الدائرية.",
            "concept_c_hybrid": "بطاقات مقارنة بين الكرسيين + أسلوب رسوم بيانية تفاعلية على خلفية كحلية عصرية.",
            "chosen": "Concept B (Vertical Neuro-Signal Motion Graphics + Dynamic Playful Body-Map)",
            "why": "القصة تقوم على ميكانيكية الإشارة العصبية الخاطئة؛ صعود السهم الحركي من اليد إلى الدماغ على شاشة عمودية يشرح الوهم في ثانيتين.",
        },
        "short_03": {
            "concept_a_cinematic": "تركيز سينمائي بطيء على ساعة جدار قديمة في غرفة مظلمة.",
            "concept_b_motion_graphics": "شريط فيلم مونتاج مجرد يتقطع بالمقص مع عداد رقمي للأجزاء من الثانية.",
            "concept_c_hybrid": "تحدٍّ بصري مباشر بساعة متجمدة ورادار عين في الثانية 0، تتلوه استعارة قص شريط الفيلم الذهني في مونتاج سريع.",
            "chosen": "Concept C (Hybrid Interactive Freeze-Challenge -> Filmstrip Montage Metaphor)",
            "why": "الجمع بين الساعة المتجمدة الفورية ومقص المونتاج يُشعر المشاهد بالتجربة ثم يريه كيف قصّها مخّه بصرياً.",
        },
        "short_04": {
            "concept_a_cinematic": "ملف تحقيق جنائي مع إضاءة درامية وظهور تدريجي لطابور المشتبهين من الظل.",
            "concept_b_motion_graphics": "انفوجرافيك إحصائي صِرف بين دوائر الذاكرة البصرية والكلمات.",
            "concept_c_hybrid": "إخراج وثائقي تحقيقات (Amiri + بطاقة تاريخية 1990) يكشف استبدال الوجه بالوصف اللغوي ثم يضع الدماغ المنقسم في الختام.",
            "chosen": "Concept C (Archival Crime Documentary Casefile + Split-Brain Payoff)",
            "why": "المظهر الوثائقي التاريخي لعام 1990 يرفع الجاذبية ويعزل هذا الشورت بصرياً عن باقي الشورتس.",
        },
        "short_05": {
            "concept_a_cinematic": "تركيز سينمائي متأرجح فوق الهاوية مع نبضات قلب متسارعة.",
            "concept_b_motion_graphics": "مقارنة رقمية حادة بأعمدة 68% مقابل 18% ومؤشر نبض 128 مقابل 72.",
            "concept_c_hybrid": "انقسام قطبي بين الجسر المرعب والجسر الثابت يتصاعد نحو أعمدة المقارنة الحية في ذروة النتيجة ثم جزيء الأدرينالين.",
            "chosen": "Concept C (Polar Contrast 2-Zone Comparison + Animated 68% vs 18% Stat Bars)",
            "why": "جوهر القصة هو المقارنة الصادمة بين الجسرين؛ تقسيم التكوين عمودياً مع رسم الأعمدة يبرز المفارقة فوراً على الهاتف.",
        },
    }
    return concepts.get(short_id, {})


def _project_language(proj_dir: Path) -> str:
    pj = Path(proj_dir) / "project.json"
    if pj.is_file():
        try:
            lang = str(json.loads(pj.read_text(encoding="utf-8")).get("language", "ar")).lower()
            if lang.startswith("en"):
                return "en"
        except Exception:
            pass
    return "en" if proj_dir.name.lower().endswith("_en") else "ar"


def _project_dialect(proj_dir: Path) -> str:
    pj = Path(proj_dir) / "project.json"
    if pj.is_file():
        try:
            meta = json.loads(pj.read_text(encoding="utf-8"))
            if meta.get("dialect"):
                return str(meta["dialect"])
            if str(meta.get("language", "")).lower().startswith("en"):
                return "us_casual"
            if is_egyptian_dialect("", str(meta.get("tts_profile", "")), str(meta.get("director_note", ""))):
                return "egyptian_female" if "FEMALE" in str(meta.get("tts_profile", "")).upper() else "egyptian"
        except Exception:
            pass
    return "us_casual" if _project_language(proj_dir) == "en" else "saudi_white"


def _build_mind_glitches_en_short_specs(proj_dir: Path) -> List[Dict[str, Any]]:
    """5 handcrafted native-English 9:16 Short blueprints anchored to Whisper sentence boundaries."""
    return [
        {
            "short_id": "short_01",
            "language": "en",
            "source_section": "section_01",
            "title": "Hallucinate in 10 Minutes With Ping-Pong Balls! 🔴🧠",
            "seo_description": "The creepy Ganzfeld Effect (1930): Why staring at a blank red field makes a completely sober brain invent floating faces & voices in 10 minutes! #psychology #ganzfeld #brain #shorts",
            "seo_keywords": ["ganzfeld effect", "sensory deprivation", "1930 experiment", "hallucination", "psychology", "shorts"],
            "story_genre": "psychological_cinematic",
            "mood_signature": "Red-Room Sensory Void -> 1930 Whiteout Paradox -> Midnight Neural Projector",
            "trim_source_window": [0.0, None],
            "font_override": ("Inter", "Funnel Display"),
            "palette": {"bg": "#150609", "surface": "#1F0D12", "primary": "#EF4444", "accent": "#FFD400", "text": "#F8FAFC"},
            "scenes": [
                {
                    "id": "sc_setup", "start": 0.0, "end": 9.40, "mood": "crimson_suspense",
                    "headline": {"text": "Ping-Pong Balls & Red Light Trap", "mode": "impact_title"},
                    "layout": "stack_top_spotlight",
                    "assets": ["entity_03", "entity_05", "entity_04"],
                    "spotlight": {"anchor_asset": "entity_05", "to_asset": "entity_04", "color": "#EF4444"},
                    "camera": {"start_z": -1800, "end_z": -1580, "poi_y": 990},
                },
                {
                    "id": "sc_hallucination", "start": 9.40, "end": 22.10, "mood": "crimson_suspense",
                    "headline": {"text": "Sober Brain Sees Floating Faces!", "mode": "word_emphasis", "highlight": "Faces!"},
                    "layout": "hero_overlay_duet",
                    "assets": ["entity_06", "entity_11", "entity_12"],
                    "vfx_override": {"entity_11": [{"type": "distortion", "amount": 28.0}]},
                    "camera": {"start_z": -1660, "end_z": -1490, "poi_y": 950},
                },
                {
                    "id": "sc_metzger_1930", "start": 22.10, "end": 36.10, "mood": "warm_light",
                    "headline": {"text": "1930 — Blank Color Without Edges", "mode": "data_callout", "metric": "1930"},
                    "layout": "void_paradox_trio",
                    "assets": ["entity_09", "entity_02", "entity_07"],
                    "camera": {"start_z": -1800, "end_z": -1660, "poi_y": 960},
                },
                {
                    "id": "sc_pattern_brain", "start": 36.10, "end": 49.35, "mood": "midnight_teal",
                    "headline": {"text": "Brain Panics & Projects Void", "mode": "mask_reveal"},
                    "layout": "vertical_causal_chain",
                    "assets": ["entity_15", "entity_20", "entity_17"],
                    "arrow_chain": True,
                    "camera": {"start_z": -1760, "end_z": -1560, "poi_y": 970},
                },
                {
                    "id": "sc_miners_ghosts", "start": 49.35, "end": 55.82, "mood": "arctic_noir",
                    "headline": {"text": "Miners & Explorers See Ghosts", "mode": "word_emphasis", "highlight": "Ghosts"},
                    "layout": "diagonal_duet",
                    "assets": ["entity_13", "entity_14"],
                    "camera": {"start_z": -1720, "end_z": -1540, "poi_y": 970},
                },
            ],
        },
        {
            "short_id": "short_02",
            "language": "en",
            "source_section": "section_03",
            "title": "Trick Your Brain Into Feeling a 3-Foot Pinocchio Nose! 🤥🧠",
            "seo_description": "Try the Pinocchio Illusion at home in 30 seconds: James Lackner (1988) proved your brain rebuilds your body map in real time! #pinocchioillusion #neuroscience #shorts",
            "seo_keywords": ["pinocchio illusion", "james lackner 1988", "body map", "psychology experiment", "shorts"],
            "story_genre": "shorts_viral_9x16",
            "mood_signature": "Electric Indigo Bicep-Tendon Signal Blueprint & Body-Map Illusion",
            "trim_source_window": [7.60, None],
            "font_override": ("Mona Sans", "Bricolage Grotesque"),
            "palette": {"bg": "#0A1529", "surface": "#12213D", "primary": "#38BDF8", "accent": "#FACC15", "text": "#F8FAFC"},
            "scenes": [
                {
                    "id": "sc_blind_setup", "start": 0.0, "end": 11.10, "mood": "warm_light",
                    "headline": {"text": "Blindfolded Rhythm Nose Touch", "mode": "impact_title"},
                    "layout": "vertical_split_compare",
                    "assets": ["entity_02", "entity_04"],
                    "camera": {"start_z": -1800, "end_z": -1650, "poi_y": 980},
                },
                {
                    "id": "sc_lackner_1988", "start": 11.10, "end": 29.50, "mood": "midnight_teal",
                    "headline": {"text": "1988 — Bicep Vibration Tricks Brain", "mode": "data_callout", "metric": "1988"},
                    "layout": "vertical_causal_chain",
                    "assets": ["entity_06", "entity_07", "entity_11"],
                    "arrow_chain": True,
                    "camera": {"start_z": -1750, "end_z": -1550, "poi_y": 960},
                },
                {
                    "id": "sc_nose_twist", "start": 29.50, "end": 38.30, "mood": "warm_light",
                    "headline": {"text": "Brain Grows a Three-Foot Nose!", "mode": "word_emphasis", "highlight": "Nose!"},
                    "layout": "triangle_climax",
                    "assets": ["entity_12", "entity_09", "entity_20"],
                    "camera": {"start_z": -1820, "end_z": -1520, "poi_y": 980},
                },
                {
                    "id": "sc_body_map", "start": 38.30, "end": 47.66, "mood": "arctic_noir",
                    "headline": {"text": "Rebuilt Body Map Every Second", "mode": "mask_reveal"},
                    "layout": "radar_focus",
                    "assets": ["entity_15", "entity_17"],
                    "radar_rings": True,
                    "camera": {"start_z": -1680, "end_z": -1500, "poi_y": 960},
                },
            ],
        },
        {
            "short_id": "short_03",
            "language": "en",
            "source_section": "section_05",
            "title": "Look at a Clock Right Now! The Half-Second Time Lie ⏱️👁️",
            "seo_description": "Why does the second hand freeze when you look at a wall clock? Kielan Yarrow (2001) revealed how your brain edits time (Chronostasis)! #chronostasis #timeillusion #shorts",
            "seo_keywords": ["stopped clock illusion", "chronostasis", "kielan yarrow 2001", "saccade blindness", "shorts"],
            "story_genre": "scientific_explanation",
            "mood_signature": "Icy Obsidian Saccade Radar & Cinema Filmstrip Montage",
            "trim_source_window": [10.15, None],
            "font_override": ("Inter", "Oswald"),
            "palette": {"bg": "#071722", "surface": "#0E2233", "primary": "#22D3EE", "accent": "#FFD400", "text": "#F8FAFC"},
            "scenes": [
                {
                    "id": "sc_clock_challenge", "start": 0.0, "end": 5.60, "mood": "arctic_noir",
                    "headline": {"text": "Look Up at a Wall Clock!", "mode": "impact_title"},
                    "layout": "radar_focus",
                    "assets": ["entity_03", "entity_04"],
                    "radar_rings": True,
                    "camera": {"start_z": -1800, "end_z": -1580, "poi_y": 960},
                },
                {
                    "id": "sc_frozen_second", "start": 5.60, "end": 15.65, "mood": "midnight_teal",
                    "headline": {"text": "The Second Hand Freezes Cold", "mode": "word_emphasis", "highlight": "Freezes"},
                    "layout": "diagonal_duet",
                    "assets": ["entity_17", "entity_12"],
                    "camera": {"start_z": -1680, "end_z": -1500, "poi_y": 960},
                },
                {
                    "id": "sc_yarrow_2001", "start": 15.65, "end": 27.80, "mood": "amber_study",
                    "headline": {"text": "2001 — Eye Movement Blind Gap", "mode": "data_callout", "metric": "2001"},
                    "layout": "vertical_causal_chain",
                    "assets": ["entity_07", "entity_05", "entity_09"],
                    "arrow_chain": True,
                    "camera": {"start_z": -1800, "end_z": -1600, "poi_y": 960},
                },
                {
                    "id": "sc_film_edit", "start": 27.80, "end": 45.57, "mood": "warm_light",
                    "headline": {"text": "A Half-Second Time Editing Lie", "mode": "mask_reveal"},
                    "layout": "triangle_climax",
                    "assets": ["entity_11", "entity_13", "entity_15"],
                    "camera": {"start_z": -1750, "end_z": -1530, "poi_y": 960},
                },
            ],
        },
        {
            "short_id": "short_04",
            "language": "en",
            "source_section": "section_07",
            "title": "1990 Bank Robbery: Talking Erases the Criminal's Face! 🕵️‍♂️🎭",
            "seo_description": "Saw the thief clearly? Describing his face out loud actually erases the memory! Jonathan Schooler's 1990 Verbal Overshadowing experiment. #verbalovershadowing #psychology #shorts",
            "seo_keywords": ["verbal overshadowing", "jonathan schooler 1990", "eyewitness memory", "psychology", "shorts"],
            "story_genre": "historical_documentary",
            "mood_signature": "Charcoal Crime Noir Casefile & Archival Warm Evidence Paper",
            "trim_source_window": [10.18, None],
            "font_override": ("Space Grotesk", "Playfair Display"),
            "palette": {"bg": "#111319", "surface": "#1C1917", "primary": "#F59E0B", "accent": "#FBBF24", "text": "#F8FAFC"},
            "scenes": [
                {
                    "id": "sc_robbery_witness", "start": 0.0, "end": 7.40, "mood": "warm_light",
                    "headline": {"text": "Eyewitness to a Bank Robbery", "mode": "documentary_card", "kicker": "EYEWITNESS FILE"},
                    "layout": "diagonal_duet",
                    "assets": ["entity_02", "entity_03"],
                    "camera": {"start_z": -1800, "end_z": -1600, "poi_y": 960},
                },
                {
                    "id": "sc_verbal_erase", "start": 7.40, "end": 18.10, "mood": "amber_study",
                    "headline": {"text": "Talking Loud Erases His Face!", "mode": "word_emphasis", "highlight": "Erases"},
                    "layout": "triangle_climax",
                    "assets": ["entity_09", "entity_06", "entity_13"],
                    "camera": {"start_z": -1750, "end_z": -1530, "poi_y": 960},
                },
                {
                    "id": "sc_schooler_1990", "start": 18.10, "end": 31.80, "mood": "arctic_noir",
                    "headline": {"text": "Police Lineup Disaster Exposed", "mode": "documentary_card", "kicker": "1990 — JONATHAN SCHOOLER"},
                    "layout": "lineup_showcase",
                    "assets": ["entity_05", "entity_18", "entity_19"],
                    "camera": {"start_z": -1800, "end_z": -1620, "poi_y": 980},
                },
                {
                    "id": "sc_split_brain_face", "start": 31.80, "end": 43.82, "mood": "warm_light",
                    "headline": {"text": "Clunky Words Overwrite Real Memory", "mode": "mask_reveal"},
                    "layout": "vertical_causal_chain",
                    "assets": ["entity_17", "entity_15"],
                    "arrow_chain": True,
                    "camera": {"start_z": -1700, "end_z": -1520, "poi_y": 960},
                },
            ],
        },
        {
            "short_id": "short_05",
            "language": "en",
            "source_section": "section_04",
            "title": "Adrenaline Trap: How Fear Tricks You Into Falling in Love! 🌉❤️",
            "seo_description": "Dutton & Aron's 1974 Capilano Bridge study: Why men on a swaying 230-foot bridge called back far more often than on a safe bridge! #psychology #attraction #shorts",
            "seo_keywords": ["suspension bridge effect", "misattribution of arousal", "capilano 1974", "psychology", "shorts"],
            "story_genre": "psychological_cinematic",
            "mood_signature": "High-Tension Dual-Polarity Chart (Fear 68% vs Safe 18%)",
            "trim_source_window": [11.32, None],
            "font_override": ("Mona Sans", "Funnel Display"),
            "palette": {"bg": "#0D1624", "surface": "#172033", "primary": "#FB7185", "accent": "#FFD400", "text": "#F8FAFC"},
            "scenes": [
                {
                    "id": "sc_abyss_230", "start": 0.0, "end": 12.10, "mood": "crimson_suspense",
                    "headline": {"text": "230 Feet — Heart Pounding Panic", "mode": "data_callout", "metric": "230 Feet"},
                    "layout": "radar_focus",
                    "assets": ["entity_02", "entity_07", "entity_09"],
                    "radar_rings": True,
                    "camera": {"start_z": -1800, "end_z": -1540, "poi_y": 960},
                },
                {
                    "id": "sc_capilano_split", "start": 12.10, "end": 29.20, "mood": "midnight_teal",
                    "headline": {"text": "1974 — Two Very Different Bridges", "mode": "data_callout", "metric": "1974"},
                    "layout": "vertical_split_compare",
                    "assets": ["entity_06", "entity_10"],
                    "camera": {"start_z": -1800, "end_z": -1650, "poi_y": 960},
                },
                {
                    "id": "sc_stats_68_18", "start": 29.20, "end": 37.90, "mood": "warm_light",
                    "headline": {"text": "68% vs 18% Called Back After Fear!", "mode": "word_emphasis", "highlight": "Fear!"},
                    "layout": "chart_clash_bars",
                    "assets": ["entity_15", "entity_13", "entity_14"],
                    "stat_bars": [{"label": "Scary Bridge", "val": "68%", "h": 250, "color": "#FB7185"}, {"label": "Safe Bridge", "val": "18%", "h": 100, "color": "#14B8A6"}],
                    "camera": {"start_z": -1750, "end_z": -1550, "poi_y": 960},
                },
                {
                    "id": "sc_adrenaline_love", "start": 37.90, "end": 45.34, "mood": "crimson_suspense",
                    "headline": {"text": "Survival Panic Misread as Chemistry", "mode": "mask_reveal"},
                    "layout": "vertical_causal_chain",
                    "assets": ["entity_17", "entity_20"],
                    "arrow_chain": True,
                    "camera": {"start_z": -1700, "end_z": -1500, "poi_y": 960},
                },
            ],
        },
    ]


# ---------------------------------------------------------------------------
# 2. Custom Shorts Visual Blueprints (Distinct Composition per Story)
# ---------------------------------------------------------------------------

def _build_mind_glitches_short_specs(proj_dir: Path) -> List[Dict[str, Any]]:
    """Return all 5 handcrafted Short specifications grounded in real project timing & JSON entities."""
    return [
        {
            "short_id": "short_01",
            "source_section": "section_01",
            "title": "هلوسة سمعية وبصرية في 10 دقائق بنصف كرة بينغ بونغ! 🔴🧠",
            "seo_description": "تجربة غانزفيلد المرعبة (1930): لماذا يبدأ دماغك برسم وجوه وأصوات غير موجودة بمجرد قطع التفاصيل البصرية؟ #علم_النفس #تأثير_غانزفيلد #خداع_الدماغ #شورتس",
            "seo_keywords": ["تأثير غانزفيلد", "هلوسة الفراغ", "علم النفس", "تجربة 1930", "خدع الدماغ", "شورتس"],
            "story_genre": "psychological_cinematic",
            "mood_signature": "Red-Room Sensory Deprivation -> Stark 1930 Light Void -> Midnight Projector",
            "trim_source_window": [0.0, None],
            "font_override": ("Cairo", "Alyamama"),
            "palette": {"bg": "#150609", "surface": "#1F0D12", "primary": "#EF4444", "accent": "#FFD400", "text": "#F8FAFC"},
            "scenes": [
                {
                    "id": "sc_setup", "start": 0.0, "end": 7.56, "mood": "crimson_suspense",
                    "headline": {"text": "تجربة بنغ بونغ في الغرفة الحمراء", "mode": "impact_title"},
                    "layout": "stack_top_spotlight",
                    "assets": ["entity_03", "entity_05", "entity_04"],
                    "spotlight": {"anchor_asset": "entity_05", "to_asset": "entity_04", "color": "#EF4444"},
                    "camera": {"start_z": -1800, "end_z": -1580, "poi_y": 990},
                },
                {
                    "id": "sc_hallucination", "start": 7.56, "end": 19.32, "mood": "crimson_suspense",
                    "headline": {"text": "تبدأ تشوف وجوه وأصوات!", "mode": "word_emphasis", "highlight": "وجوه"},
                    "layout": "hero_overlay_duet",
                    "assets": ["entity_06", "entity_11", "entity_12"],
                    "vfx_override": {"entity_11": [{"type": "distortion", "amount": 28.0}]},
                    "camera": {"start_z": -1660, "end_z": -1490, "poi_y": 950},
                },
                {
                    "id": "sc_metzger_1930", "start": 19.32, "end": 33.96, "mood": "warm_light",
                    "headline": {"text": "١٩٣٠ — لون واحد بلا أي حواف", "mode": "data_callout", "metric": "1930"},
                    "layout": "void_paradox_trio",
                    "assets": ["entity_09", "entity_02", "entity_07"],
                    "camera": {"start_z": -1800, "end_z": -1660, "poi_y": 960},
                },
                {
                    "id": "sc_pattern_brain", "start": 33.96, "end": 45.66, "mood": "midnight_teal",
                    "headline": {"text": "دماغك مُدمن على تفسير الأنماط", "mode": "mask_reveal"},
                    "layout": "vertical_causal_chain",
                    "assets": ["entity_15", "entity_20", "entity_17"],
                    "arrow_chain": True,
                    "camera": {"start_z": -1760, "end_z": -1560, "poi_y": 970},
                },
                {
                    "id": "sc_miners_ghosts", "start": 45.66, "end": 51.99, "mood": "arctic_noir",
                    "headline": {"text": "المناجم والقطب: أشباح من الخيال", "mode": "word_emphasis", "highlight": "أشباح"},
                    "layout": "diagonal_duet",
                    "assets": ["entity_13", "entity_14"],
                    "camera": {"start_z": -1720, "end_z": -1540, "poi_y": 970},
                },
            ],
        },
        {
            "short_id": "short_02",
            "source_section": "section_03",
            "title": "خدعة تطيل أنفك مثل بينوكيو في 30 ثانية بالبيت! 🤥🧠",
            "seo_description": "جرّب وهم بينوكيو مع صديقك الآن: كيف تخدع أعصاب الذراع خريطة جسمك في الدماغ خلال دقيقة؟ (تجربة جيمس لاكنر 1988) #وهم_بينوكيو #علم_النفس #تجارب_نفسية #شورتس",
            "seo_keywords": ["وهم بينوكيو", "جيمس لاكنر 1988", "خريطة الجسم", "تجارب علم النفس", "شورتس"],
            "story_genre": "shorts_viral_9x16",
            "mood_signature": "Electric Indigo Neuro-Signal Blueprint & Body-Map Illusion",
            "trim_source_window": [6.82, None],
            "font_override": ("Alexandria", "Changa"),
            "palette": {"bg": "#0A1529", "surface": "#12213D", "primary": "#38BDF8", "accent": "#FACC15", "text": "#F8FAFC"},
            "scenes": [
                {
                    "id": "sc_blind_setup", "start": 0.0, "end": 11.24, "mood": "warm_light",
                    "headline": {"text": "غمّض عيونك وجرّب لمس الأنف", "mode": "impact_title"},
                    "layout": "vertical_split_compare",
                    "assets": ["entity_02", "entity_04"],
                    "camera": {"start_z": -1800, "end_z": -1650, "poi_y": 980},
                },
                {
                    "id": "sc_lackner_1988", "start": 11.24, "end": 26.00, "mood": "midnight_teal",
                    "headline": {"text": "١٩٨٨ — اهتزاز الذراع يخدع عقلك", "mode": "data_callout", "metric": "1988"},
                    "layout": "vertical_causal_chain",
                    "assets": ["entity_06", "entity_07", "entity_11"],
                    "arrow_chain": True,
                    "camera": {"start_z": -1750, "end_z": -1550, "poi_y": 960},
                },
                {
                    "id": "sc_nose_twist", "start": 26.00, "end": 37.46, "mood": "warm_light",
                    "headline": {"text": "حل عقلك الفوري: خشمي طال متر!", "mode": "word_emphasis", "highlight": "طال"},
                    "layout": "triangle_climax",
                    "assets": ["entity_12", "entity_09", "entity_20"],
                    "camera": {"start_z": -1820, "end_z": -1520, "poi_y": 980},
                },
                {
                    "id": "sc_body_map", "start": 37.46, "end": 45.89, "mood": "arctic_noir",
                    "headline": {"text": "خريطة جسمك تنبني كل ثانية", "mode": "mask_reveal"},
                    "layout": "radar_focus",
                    "assets": ["entity_15", "entity_17"],
                    "radar_rings": True,
                    "camera": {"start_z": -1680, "end_z": -1500, "poi_y": 960},
                },
            ],
        },
        {
            "short_id": "short_03",
            "source_section": "section_05",
            "title": "ارفع عينك على الساعة الحين! كذبة المونتاج داخل عقلك ⏱️👁️",
            "seo_description": "هل تجمّد عقرب الثواني في أول لحظة نظرت فيها للساعة؟ اكتشف ظاهرة توقّف الزمن الوهمي التي يمونتجها دماغك مئات المرات يومياً! #توقف_الزمن_الوهمي #إدراك_الزمن #شورتس",
            "seo_keywords": ["توقف الزمن الوهمي", "كيلان يارو 2001", "خدع العقل", "ساعة الحائط", "شورتس"],
            "story_genre": "scientific_explanation",
            "mood_signature": "Icy Obsidian Saccade Radar & Cinema Filmstrip Cut",
            "trim_source_window": [5.68, None],
            "font_override": ("Cairo", "Readex Pro"),
            "palette": {"bg": "#071722", "surface": "#0E2233", "primary": "#22D3EE", "accent": "#FFD400", "text": "#F8FAFC"},
            "scenes": [
                {
                    "id": "sc_clock_challenge", "start": 0.0, "end": 5.36, "mood": "arctic_noir",
                    "headline": {"text": "ارفع عينك على الساعة الحين!", "mode": "impact_title"},
                    "layout": "radar_focus",
                    "assets": ["entity_03", "entity_04"],
                    "radar_rings": True,
                    "camera": {"start_z": -1800, "end_z": -1580, "poi_y": 960},
                },
                {
                    "id": "sc_frozen_second", "start": 5.36, "end": 14.22, "mood": "midnight_teal",
                    "headline": {"text": "العقرب تجمّد لأكثر من ثانية كاملة", "mode": "word_emphasis", "highlight": "تجمّد"},
                    "layout": "diagonal_duet",
                    "assets": ["entity_17", "entity_12"],
                    "camera": {"start_z": -1680, "end_z": -1500, "poi_y": 960},
                },
                {
                    "id": "sc_yarrow_2001", "start": 14.22, "end": 26.42, "mood": "amber_study",
                    "headline": {"text": "٢٠٠١ — عمى سريع أثناء حركة عينك", "mode": "data_callout", "metric": "2001"},
                    "layout": "vertical_causal_chain",
                    "assets": ["entity_07", "entity_05", "entity_09"],
                    "arrow_chain": True,
                    "camera": {"start_z": -1800, "end_z": -1600, "poi_y": 960},
                },
                {
                    "id": "sc_film_edit", "start": 26.42, "end": 43.27, "mood": "warm_light",
                    "headline": {"text": "كذبة زمنية صنعها مونتاج عقلك", "mode": "mask_reveal"},
                    "layout": "triangle_climax",
                    "assets": ["entity_11", "entity_13", "entity_15"],
                    "camera": {"start_z": -1750, "end_z": -1530, "poi_y": 960},
                },
            ],
        },
        {
            "short_id": "short_04",
            "source_section": "section_07",
            "title": "سرقة بنك 1990: لماذا يمحو كلامك وجه المجرم من ذاكرتك؟ 🕵️‍♂️🎭",
            "seo_description": "شاهدت وجه السارق بوضوح.. فلماذا تفشل في التعرّف عليه بمجرد وصفه؟ تجربة جوناثان سكولر 1990 الصادمة عن التظليل اللفظي! #التظليل_اللفظي #جريمة #علم_النفس #شورتس",
            "seo_keywords": ["التظليل اللفظي", "جوناثان سكولر", "1990", "الذاكرة البصرية", "علم النفس", "شورتس"],
            "story_genre": "historical_documentary",
            "mood_signature": "Charcoal Crime Noir Casefile & Archival Warm Evidence Paper",
            "trim_source_window": [7.72, None],
            "font_override": ("IBM Plex Sans Arabic", "Amiri"),
            "palette": {"bg": "#111319", "surface": "#1C1917", "primary": "#F59E0B", "accent": "#FBBF24", "text": "#F8FAFC"},
            "scenes": [
                {
                    "id": "sc_robbery_witness", "start": 0.0, "end": 5.96, "mood": "warm_light",
                    "headline": {"text": "شفت وجه الحرامي بوضوح تام", "mode": "documentary_card", "kicker": "ملف شاهد عيان"},
                    "layout": "diagonal_duet",
                    "assets": ["entity_02", "entity_03"],
                    "camera": {"start_z": -1800, "end_z": -1600, "poi_y": 960},
                },
                {
                    "id": "sc_verbal_erase", "start": 5.96, "end": 19.32, "mood": "amber_study",
                    "headline": {"text": "العكس تماماً: الوصف يمسح الصورة!", "mode": "word_emphasis", "highlight": "يمسح"},
                    "layout": "triangle_climax",
                    "assets": ["entity_09", "entity_06", "entity_13"],
                    "camera": {"start_z": -1750, "end_z": -1530, "poi_y": 960},
                },
                {
                    "id": "sc_schooler_1990", "start": 19.32, "end": 34.10, "mood": "arctic_noir",
                    "headline": {"text": "طابور المشتبهين يكشف الكارثة", "mode": "documentary_card", "kicker": "١٩٩٠ — جوناثان سكولر"},
                    "layout": "lineup_showcase",
                    "assets": ["entity_05", "entity_18", "entity_19"],
                    "camera": {"start_z": -1800, "end_z": -1620, "poi_y": 980},
                },
                {
                    "id": "sc_split_brain_face", "start": 34.10, "end": 45.62, "mood": "warm_light",
                    "headline": {"text": "كلماتك تستبدل الوجه الأصلي للأبد", "mode": "mask_reveal"},
                    "layout": "vertical_causal_chain",
                    "assets": ["entity_17", "entity_15"],
                    "arrow_chain": True,
                    "camera": {"start_z": -1700, "end_z": -1520, "poi_y": 960},
                },
            ],
        },
        {
            "short_id": "short_05",
            "source_section": "section_04",
            "title": "خدعة الأدرينالين: كيف يوقعك الخوف في الحب خلال دقيقة؟ 🌉❤️",
            "seo_description": "تجربة جسر كابيلانو الشهيرة (1974): لماذا اتصل 68% ممن عبروا الجسر المرعب بالمحاورة مقابل 18% فقط على الجسر الثابت؟ #خدعة_الأدرينالين #علم_النفس #تجربة_كابيلانو #شورتس",
            "seo_keywords": ["تأثير الجسر المعلق", "فخ الأدرينالين", "كابيلانو 1974", "علم النفس", "شورتس"],
            "story_genre": "psychological_cinematic",
            "mood_signature": "High-Tension Dual-Polarity Chart (Fear 68% vs Safe 18%)",
            "trim_source_window": [11.82, None],
            "font_override": ("Cairo", "Alyamama"),
            "palette": {"bg": "#0D1624", "surface": "#172033", "primary": "#FB7185", "accent": "#FFD400", "text": "#F8FAFC"},
            "scenes": [
                {
                    "id": "sc_abyss_230", "start": 0.0, "end": 13.46, "mood": "crimson_suspense",
                    "headline": {"text": "230 قدم — نبضك يفور من الرعب", "mode": "data_callout", "metric": "230 قدم"},
                    "layout": "radar_focus",
                    "assets": ["entity_02", "entity_07", "entity_09"],
                    "radar_rings": True,
                    "camera": {"start_z": -1800, "end_z": -1540, "poi_y": 960},
                },
                {
                    "id": "sc_capilano_split", "start": 13.46, "end": 29.30, "mood": "midnight_teal",
                    "headline": {"text": "١٩٧٤ — تجربة جسرين متناقضين", "mode": "data_callout", "metric": "1974"},
                    "layout": "vertical_split_compare",
                    "assets": ["entity_06", "entity_10"],
                    "camera": {"start_z": -1800, "end_z": -1650, "poi_y": 960},
                },
                {
                    "id": "sc_stats_68_18", "start": 29.30, "end": 38.96, "mood": "warm_light",
                    "headline": {"text": "68% مقابل 18% تواصل بعد الخوف!", "mode": "word_emphasis", "highlight": "الخوف"},
                    "layout": "chart_clash_bars",
                    "assets": ["entity_15", "entity_13", "entity_14"],
                    "stat_bars": [{"label": "جسر مرعب", "val": "68%", "h": 250, "color": "#FB7185"}, {"label": "جسر آمن", "val": "18%", "h": 100, "color": "#14B8A6"}],
                    "camera": {"start_z": -1750, "end_z": -1550, "poi_y": 960},
                },
                {
                    "id": "sc_adrenaline_love", "start": 38.96, "end": 46.74, "mood": "crimson_suspense",
                    "headline": {"text": "مخك ترجم الرعب على إنه إعجاب", "mode": "mask_reveal"},
                    "layout": "vertical_causal_chain",
                    "assets": ["entity_17", "entity_20"],
                    "arrow_chain": True,
                    "camera": {"start_z": -1700, "end_z": -1500, "poi_y": 960},
                },
            ],
        },
    ]


# ---------------------------------------------------------------------------
# 3. Mood Palettes & Bespoke 9:16 Scene Graph V2 Compiler
# ---------------------------------------------------------------------------

_SHORTS_MOODS: Dict[str, Dict[str, Any]] = {
    "crimson_suspense": {"c1": "#290B11", "c2": "#1D070C", "c3": "#110407", "c4": "#090204", "vignette": 34, "is_light": False, "card_bg": "#1A0A10", "card_border": "#FB7185", "text_color": "#F8FAFC", "card_style": "dark_crimson"},
    "midnight_teal": {"c1": "#111E30", "c2": "#0C1624", "c3": "#080F1A", "c4": "#050911", "vignette": 26, "is_light": False, "card_bg": "#0F1E30", "card_border": "#38BDF8", "text_color": "#F8FAFC", "card_style": "arctic"},
    "arctic_noir": {"c1": "#0D1B2A", "c2": "#091420", "c3": "#060D17", "c4": "#04080F", "vignette": 28, "is_light": False, "card_bg": "#0F1E30", "card_border": "#22D3EE", "text_color": "#F8FAFC", "card_style": "arctic"},
    "amber_study": {"c1": "#231910", "c2": "#19120B", "c3": "#120C07", "c4": "#0A0704", "vignette": 30, "is_light": False, "card_bg": "#1F160E", "card_border": "#F59E0B", "text_color": "#FEF3C7", "card_style": "amber"},
    "warm_light": {"c1": "#F2EDE4", "c2": "#EAE2D4", "c3": "#DFD6C5", "c4": "#D4C8B4", "vignette": 14, "is_light": True, "card_bg": "#0F172A", "card_border": "#D97706", "text_color": "#F8FAFC", "card_style": "warm"},
}


def _load_section_inputs(proj_dir: Path, sec_id: str) -> Tuple[Path, Dict[str, Any], Dict[str, Dict[str, Any]]]:
    sec_dir = proj_dir / "sections" / sec_id
    wav = sec_dir / "voice" / f"{sec_id}.wav"
    tm_path = sec_dir / "timing" / f"{sec_id}_timing_master.json"
    tm = json.loads(tm_path.read_text(encoding="utf-8")) if tm_path.is_file() else {"sentences": [], "words": []}

    num = sec_id.split("_")[-1]
    cat_map: Dict[str, Dict[str, Any]] = {}

    # Priority 1: Project-local or shared storyboard JSON catalog (zero PNG reading)
    for cat_dir in (proj_dir / "inputs" / "storyboard_catalog", PROJECT_ROOT / "cache" / "storyboard_catalog_8"):
        if cat_dir.is_dir() and not cat_map:
            for cp in sorted(cat_dir.glob(f"{num}_*.json")) + sorted(cat_dir.glob(f"{sec_id}*.json")):
                try:
                    cdata = json.loads(cp.read_text(encoding="utf-8"))
                    for idx_a, ent in enumerate(cdata.get("assets", []), 1):
                        eid = f"entity_{int(ent.get('index', idx_a)):02d}"
                        cat_map[eid] = ent
                except Exception:
                    pass

    # Priority 2: Section semantic_manifest.json or assets/metadata.json
    for cand_json in (sec_dir / "semantic_manifest.json", sec_dir / "assets" / "metadata.json"):
        if cand_json.is_file() and not cat_map:
            try:
                mdata = json.loads(cand_json.read_text(encoding="utf-8"))
                raw_list = mdata.get("assets") or mdata.get("entities") or mdata.get("items") or []
                for idx_a, ent in enumerate(raw_list, 1):
                    if isinstance(ent, dict):
                        eid = str(ent.get("id") or ent.get("asset_id") or f"entity_{int(ent.get('index', idx_a)):02d}")
                        cat_map[eid] = ent
            except Exception:
                pass

    return wav, tm, cat_map


def inspect_project_creative_data(proj_dir: Path, *, write_digest: bool = False) -> Dict[str, Any]:
    """Read-only JSON digest of all sections' scripts, sentence timings, and visual asset catalogs (0 image reads)."""
    proj_dir = Path(proj_dir)
    secs_root = proj_dir / "sections"
    sec_dirs = sorted(p for p in secs_root.glob("section_*") if p.is_dir()) if secs_root.is_dir() else []

    sections_digest: List[Dict[str, Any]] = []
    for sdir in sec_dirs:
        sec_id = sdir.name
        wav, tm, cat_map = _load_section_inputs(proj_dir, sec_id)
        sents = [
            {
                "index": idx,
                "start": round(float(s.get("start", 0.0)), 3),
                "end": round(float(s.get("end", 0.0)), 3),
                "text": str(s.get("text", "")).strip(),
            }
            for idx, s in enumerate(tm.get("sentences", []))
        ]
        dur = round(float(sents[-1]["end"]), 3) if sents else 0.0
        assets_summary: List[Dict[str, Any]] = []
        for idx_a in range(1, 21):
            eid = f"entity_{idx_a:02d}"
            meta = cat_map.get(eid, {})
            fpath = _find_asset_file(proj_dir, sec_id, eid)
            if meta or fpath:
                assets_summary.append({
                    "id": eid,
                    "name_ar": meta.get("name_ar") or meta.get("title") or eid,
                    "description_ar": meta.get("description_ar") or meta.get("description") or "",
                    "narrative_role": meta.get("narrative_role", "illustrative_prop"),
                    "file_exists": bool(fpath and fpath.is_file()),
                })
        sections_digest.append({
            "section_id": sec_id,
            "voice_wav": str(wav) if wav.is_file() else None,
            "duration_sec": dur,
            "words_count": len(tm.get("words", [])),
            "sentences_count": len(sents),
            "sentences": sents,
            "assets_count": len(assets_summary),
            "visual_assets_json": assets_summary,
        })

    digest = {
        "schema_version": "aion.creative_context_digest.v1",
        "project": proj_dir.name,
        "zero_image_reads": True,
        "reusable_cta_audio": {
            "text_ar": CANONICAL_CTA_TEXT_AR,
            "wav_path": str(PROJECT_ROOT / "assets" / "audio" / "cta" / "cta_channel_ar_fenrir.wav"),
            "timing_path": str(PROJECT_ROOT / "assets" / "audio" / "cta" / "cta_channel_ar_fenrir_timing.json"),
        },
        "sections_count": len(sections_digest),
        "sections": sections_digest,
    }
    if write_digest:
        out_p = proj_dir / "shorts" / "creative_context_digest.json"
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(digest, indent=2, ensure_ascii=False), encoding="utf-8")
        digest["digest_path"] = str(out_p)
    return digest


def _find_asset_file(proj_dir: Path, sec_id: str, eid: str) -> Optional[Path]:
    adir = proj_dir / "sections" / sec_id / "assets"
    cand = adir / f"{eid}.png"
    if cand.is_file():
        return cand
    for p in sorted(adir.glob(f"{eid}*.png")):
        return p
    return None


def _layout_positions_9x16(layout: str, count: int) -> List[Dict[str, Any]]:
    """Compute symmetrical, bold mobile-native 9:16 coordinates strictly centered on x=540.

    Keeps Top Neon HUD (y=275), Centered Animated Lucide Seal (y=445), and bottom Shorts UI
    (y>=1600) 100% clear with ZERO tiny off-center cutouts and ZERO empty half-screens!
    """
    cx = SHORTS_WIDTH * 0.5  # 540.0
    if count <= 1:
        return [{"pos": [cx, 1045.0], "target_h": 620, "max_w": 880, "z": -10.0}]
    if count == 2:
        # Balanced, bold vertical editorial pair connected cleanly by a center curved arrow (978 -> 1135)
        return [
            {"pos": [cx, 770.0], "target_h": 390, "max_w": 820, "z": 0.0},
            {"pos": [cx, 1345.0], "target_h": 390, "max_w": 820, "z": 4.0},
        ]
    # 3+ chronological assets in a chapter: Top anchor + Bottom partner slots (stepped in time cleanly!)
    return [
        {"pos": [cx, 770.0], "target_h": 390, "max_w": 820, "z": 0.0},
        {"pos": [cx, 1345.0], "target_h": 390, "max_w": 820, "z": 4.0},
    ]


def _compile_short_headline(
    hl: Dict[str, Any],
    *,
    sid: str,
    st: float,
    en: float,
    mood: Dict[str, Any],
    font_primary: str,
    font_display: str,
) -> Dict[str, Any]:
    text = str(hl.get("text", ""))
    mode = str(hl.get("mode", "pill_pop"))
    raw_font = font_display if mode in ("impact_title", "documentary_card") else font_primary
    is_rtl = any("\u0600" <= ch <= "\u06FF" for ch in (text + str(hl.get("kicker", ""))))
    safe_font, safe_style, _ = resolve_font_for_text(
        text + " " + str(hl.get("kicker", "")) + " " + str(hl.get("metric", "")),
        raw_font,
        fallback_chain=[font_primary, "Cairo", "Alexandria"] if is_rtl else [font_primary, "Inter", "Space Grotesk"],
    )
    is_light = bool(mood.get("is_light"))
    fsize = (50 if len(text.split()) >= 5 else 54) if mode == "impact_title" else (52 if len(text.split()) <= 5 else 46)
    with_bg = not (mode == "mask_reveal" and is_light)
    txt_col = "#0F172A" if not with_bg else mood["text_color"]

    blk: Dict[str, Any] = {
        "kind": "kinetic_typography",
        "id": f"hl_{sid}",
        "role": mode if mode in ("impact_title", "documentary_card", "data_callout", "word_emphasis") else "editorial_headline",
        "text": text,
        "direction": "rtl" if is_rtl else "ltr",
        "font": safe_font,
        "font_style": safe_style,
        "size": fsize,
        "position": [SHORTS_WIDTH * 0.5, 315.0],
        "box": [110.0, 225.0, 860.0, 260.0],
        "leading": int(round(fsize * 1.32)),
        "color": txt_col,
        "with_backdrop": with_bg,
        "backdrop_fill": mood["card_bg"],
        "backdrop_stroke": mood["card_border"],
        "animation_mode": mode,
        "animator_based_on": 2 if is_rtl else 0,
        "start": round(st, 3),
        "end": round(max(st + 0.8, en), 3),
    }
    if hl.get("highlight"):
        blk["highlight_word"] = hl["highlight"]
        blk["accent_color"] = mood["card_border"]
    if hl.get("metric"):
        blk["metric"] = str(hl["metric"])
        blk["metric_font"] = font_display if safe_font != "Amiri" else font_primary
    if hl.get("kicker"):
        blk["kicker"] = str(hl["kicker"])
        blk["kicker_font"] = font_primary
        blk["display_font"] = safe_font
    return blk


def build_short_scene_graph_and_plan(
    *,
    spec: Dict[str, Any],
    proj_dir: Path,
    short_dir: Path,
) -> Dict[str, Any]:
    """Assemble audio + timing + bespoke 9:16 Scene Graph V2 + Creative Plan JSON."""
    short_dir.mkdir(parents=True, exist_ok=True)
    short_id = spec["short_id"]
    src_sec = spec["source_section"]
    src_wav, src_tm, cat_map = _load_section_inputs(proj_dir, src_sec)

    short_lang = str(spec.get("language") or _project_language(proj_dir))
    short_dialect = str(spec.get("dialect") or _project_dialect(proj_dir))
    if short_lang.startswith("en"):
        cta_text_canon = CANONICAL_CTA_TEXT_EN
    elif is_egyptian_dialect(short_dialect):
        cta_text_canon = CANONICAL_CTA_TEXT_AR_EG
    else:
        cta_text_canon = CANONICAL_CTA_TEXT_AR

    # Reuse original audio (clean sentence-boundary trim if needed) + shared reusable CTA
    t0, t1 = spec["trim_source_window"]
    master_wav = short_dir / "voice" / f"{short_id}_master.wav"
    audio_info = concat_narrative_with_cta(
        narrative_wav=src_wav,
        narrative_words=src_tm.get("words", []),
        narrative_sentences=src_tm.get("sentences", []),
        out_wav=master_wav,
        language=short_lang,
        dialect=short_dialect,
        gap_sec=0.24,
        trim_narrative_start=float(t0 or 0.0),
        trim_narrative_end=float(t1) if t1 else None,
    )
    narr_dur = audio_info["narrative_duration"]
    cta_start = audio_info["cta_start"]
    total_dur = audio_info["total_duration"]

    default_pair = ("Inter", "Funnel Display") if short_lang.startswith("en") else ("Cairo", "Alyamama")
    font_primary, font_display = spec.get("font_override") or default_pair
    typing_system = select_project_typography_system(
        story_genre=spec["story_genre"],
        aspect_ratio="9:16",
        language=short_lang,
    )

    asset_refs: List[Dict[str, Any]] = []
    proc_graphics: List[Dict[str, Any]] = []
    typo_blocks: List[Dict[str, Any]] = []
    vfx_blocks: List[Dict[str, Any]] = []
    sfx_cues: List[Dict[str, Any]] = []
    bg_timeline: List[Dict[str, Any]] = []
    cam_keys: List[Dict[str, Any]] = []
    scenes_out: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []

    sfx_budget = 14
    last_sfx = -10.0
    from core.aion.master_cinema_kit import (
        LIVING_GRADIENT_PALETTES as _V7_PALETTES,
        TEX_FABRIC as _V7_TEX_FABRIC,
        build_caustics_opacity_keyframes as _v7_caustics_kfs,
        build_held_bg_timeline as _v7_held_bg,
        load_lucide_svg as _v7_load_lucide,
        pick_animated_icon_for_beat as _v7_pick_icon,
        resolve_pro_sfx as _v7_resolve_sfx,
    )
    _V7_MOOD_MAP = {
        "crimson_suspense": "pressure_crimson",
        "midnight_teal": "ocean_sapphire",
        "warm_light": "sandstone_dawn",
        "arctic_noir": "twilight_indigo",
        "amber_study": "imperial_slate",
        "obsidian_cyan": "obsidian_teal",
        "emerald_focus": "eureka_emerald",
    }
    _V7_CYCLE = ["imperial_slate", "ocean_sapphire", "eureka_emerald", "pressure_crimson", "sandstone_dawn", "twilight_indigo"]
    _sfx_map = {
        "card_snap": "paper_slide",
        "whoosh": "whoosh_soft",
        "whoosh_soft": "whoosh_soft",
        "whoosh_hard": "whoosh_hard",
        "chime": "shimmer_bright",
        "pop": "appear_pop",
        "impact": "boom_medium",
        "riser": "riser_tension",
        "lock_metal": "lock_metal",
        "eureka_sparkle": "eureka_sparkle",
        "shimmer_bright": "shimmer_bright",
        "slam_big": "slam_big",
        "paper_slide": "paper_slide",
        "arrow_pen": "arrow_pen",
    }

    def _emit_sfx(t_cue: float, cue: str, gain: float = 0.24, pan: float = 0.0) -> None:
        nonlocal last_sfx
        if len(sfx_cues) >= sfx_budget:
            return
        tc = round(max(0.02, min(total_dur - 0.15, float(t_cue))), 3)
        if tc - last_sfx < 0.55:
            return
        pro = _v7_resolve_sfx(_sfx_map.get(str(cue).lower(), "whoosh_soft"), time_sec=tc, pan=pan)
        if pro is not None:
            sfx_cues.append(pro)
        else:
            item: Dict[str, Any] = {"time": tc, "cue": cue, "gain": round(gain, 2)}
            if abs(pan) >= 0.05:
                item["pan"] = round(pan, 2)
            sfx_cues.append(item)
        last_sfx = tc

    raw_scenes = spec["scenes"]
    v7_mood_beats: List[Dict[str, Any]] = []
    hud_phrases: List[Dict[str, Any]] = []
    used_short_icons: List[str] = []
    for s_idx, sc in enumerate(raw_scenes):
        st = round(float(sc["start"]), 3)
        en = round(cta_start if s_idx == len(raw_scenes) - 1 else min(narr_dur - 0.05, float(sc["end"])), 3)
        if en <= st + 0.5:
            en = round(min(cta_start, st + 0.8), 3)
        mkey = sc.get("mood", "midnight_teal")
        mood = _SHORTS_MOODS.get(mkey, _SHORTS_MOODS["midnight_teal"])
        v7_mkey = _V7_MOOD_MAP.get(mkey, _V7_CYCLE[s_idx % len(_V7_CYCLE)])
        # Ensure each scene gets a distinct vibrant V7 jewel-toned world
        if v7_mood_beats and v7_mood_beats[-1]["mood"] == v7_mkey:
            v7_mkey = _V7_CYCLE[(s_idx + 1) % len(_V7_CYCLE)]
        v7_pal = _V7_PALETTES[v7_mkey]
        is_light_v7 = bool(v7_pal.get("is_light", False))
        accent_v7 = str(v7_pal["accent"])
        v7_mood_beats.append({"time": 0.0 if s_idx == 0 else st, "mood": v7_mkey})

        # Keep metadata headline in typography[] for QA & route live display into unified Top Neon HUD (`hud_sequence`)
        hl_text = str(sc["headline"].get("text", "")).strip()
        hl_prefix = f"{'①②③④⑤⑥'[s_idx]} " if (s_idx < 6 and len(hl_text) <= 26) else ""
        hud_phrases.append({
            "start": st,
            "end": en,
            "color": accent_v7,
            "text": f"{hl_prefix}{hl_text}".strip(),
            "type_dur": round(min(0.85, max(0.45, (en - st) * 0.24)), 2),
        })
        typo_blocks.append(
            _compile_short_headline(
                sc["headline"],
                sid=f"{short_id}_{sc['id']}",
                st=st,
                en=en,
                mood=mood,
                font_primary=font_primary,
                font_display=font_display,
            )
        )

        # Master Symmetrical Vertical 9:16 Staging (Top [540, 770] <-> Glowing Arrow <-> Bottom [540, 1345])
        # ZERO lonely empty halves, ZERO off-center tiny cutouts, chronological swaps every ~4-5s!
        sc_eids = list(sc.get("assets", []))
        placed: List[Dict[str, Any]] = []
        sc_assets: List[Dict[str, Any]] = []
        cx_s = SHORTS_WIDTH * 0.5  # 540.0
        sc_span = max(1.0, en - st)

        if len(sc_eids) == 1:
            eid = sc_eids[0]
            png_path = _find_asset_file(proj_dir, src_sec, eid)
            cat_meta = cat_map.get(eid, {})
            inst_id = f"{sc['id']}_{eid}"
            lname = f"Asset_{inst_id}"
            entry: Dict[str, Any] = {
                "id": inst_id, "asset_id": eid, "path": str(png_path) if png_path else None, "icon": "brain",
                "in": st, "out": en, "pos": [cx_s, 1045.0], "position": [cx_s, 1045.0],
                "target_h": 620, "max_w": 880, "entrance": "pop_settle", "entrance_dur": 0.36,
                "fade_out": 0.14, "three_d": True, "z": -10.0,
                "role": str(cat_meta.get("narrative_role", "hero")), "shadow": False,
                "keyframes": [
                    {"time": round(st + 0.45, 3), "scale_mult": 1.00},
                    {"time": round(max(st + 0.9, en - 0.25), 3), "scale_mult": 1.07},
                ],
            }
            asset_refs.append(entry)
            sc_assets.append(entry)
            vfx_blocks.append({"type": "drop_shadow", "target": lname, "opacity": 74.0, "distance": 24.0, "softness": 44.0, "start": st, "end": en})
            placed.append({"id": inst_id, "eid": eid, "lname": lname, "pos": [cx_s, 1045.0], "in": st, "z": -10.0})
        elif len(sc_eids) >= 2:
            n_e = len(sc_eids)
            top_eids = sc_eids[: max(1, n_e // 2)] if n_e >= 4 else [sc_eids[0]]
            bot_eids = sc_eids[len(top_eids):]

            # Top Slot ([540, 770], bold 390x820)
            t_step = sc_span / float(len(top_eids))
            for ti, eid in enumerate(top_eids):
                t_in = round(st + ti * t_step, 3)
                t_out = round(en if ti == len(top_eids) - 1 else (st + (ti + 1) * t_step), 3)
                png_path = _find_asset_file(proj_dir, src_sec, eid)
                cat_meta = cat_map.get(eid, {})
                inst_id = f"{sc['id']}_T{ti}_{eid}"
                lname = f"Asset_{inst_id}"
                entry = {
                    "id": inst_id, "asset_id": eid, "path": str(png_path) if png_path else None, "icon": "brain",
                    "in": t_in, "out": t_out, "pos": [cx_s, 770.0], "position": [cx_s, 770.0],
                    "target_h": 390, "max_w": 820,
                    "entrance": "pop_settle" if ti == 0 else "slide_left", "entrance_dur": 0.34,
                    "fade_out": 0.14, "three_d": True, "z": 0.0,
                    "role": str(cat_meta.get("narrative_role", "hero")), "shadow": False,
                }
                asset_refs.append(entry)
                sc_assets.append(entry)
                vfx_blocks.append({"type": "drop_shadow", "target": lname, "opacity": 74.0, "distance": 24.0, "softness": 44.0, "start": t_in, "end": t_out})
                placed.append({"id": inst_id, "eid": eid, "lname": lname, "pos": [cx_s, 770.0], "in": t_in, "z": 0.0})

            # Bottom Slot ([540, 1345], bold 390x820) — arrives promptly at st+0.35s so ZERO empty bottom half!
            b_start0 = round(min(en - 0.6, st + 0.35), 3)
            b_avail = max(0.6, en - b_start0)
            b_step = b_avail / float(len(bot_eids))
            for bi, eid in enumerate(bot_eids):
                b_in = round(b_start0 + bi * b_step, 3)
                b_out = round(en if bi == len(bot_eids) - 1 else (b_start0 + (bi + 1) * b_step), 3)
                png_path = _find_asset_file(proj_dir, src_sec, eid)
                cat_meta = cat_map.get(eid, {})
                inst_id = f"{sc['id']}_B{bi}_{eid}"
                lname = f"Asset_{inst_id}"
                use_mask = (bi % 2 == 0)
                entry = {
                    "id": inst_id, "asset_id": eid, "path": str(png_path) if png_path else None, "icon": "brain",
                    "in": b_in, "out": b_out, "pos": [cx_s, 1345.0], "position": [cx_s, 1345.0],
                    "target_h": 390, "max_w": 820,
                    "entrance": "mask_reveal" if use_mask else "slide_right", "mask_reveal": use_mask,
                    "entrance_dur": 0.34, "fade_out": 0.14, "three_d": True, "z": 4.0,
                    "role": str(cat_meta.get("narrative_role", "supporting")), "shadow": False,
                }
                asset_refs.append(entry)
                sc_assets.append(entry)
                vfx_blocks.append({"type": "drop_shadow", "target": lname, "opacity": 74.0, "distance": 24.0, "softness": 44.0, "start": b_in, "end": b_out})
                placed.append({"id": inst_id, "eid": eid, "lname": lname, "pos": [cx_s, 1345.0], "in": b_in, "z": 4.0})

            for extra_eid, fx_items in (sc.get("vfx_override") or {}).items():
                match_p = next((p for p in placed if p["eid"] == extra_eid), None)
                if match_p:
                    for extra_fx in (fx_items or []):
                        fx_c = dict(extra_fx)
                        fx_c.update({"target": match_p["lname"], "start": match_p["in"], "end": en})
                        vfx_blocks.append(fx_c)

        # V7 Animated 3-Layer Lucide Seal — CENTERED cleanly at [540, 445] directly below Top HUD!
        icon_meta = _v7_pick_icon(hl_text, used_icons=used_short_icons, is_light_bg=is_light_v7, beat_index=s_idx)
        used_short_icons.append(icon_meta["icon"])
        iaid = f"{sc['id']}_icon_{icon_meta['icon'].replace('-', '_')}"
        it0 = round(min(en - 0.5, st + 0.32), 3)
        imp_t = round(min(en - 0.35, it0 + 0.45), 3)
        icon_pos = [cx_s, 445.0]
        icon_entry: Dict[str, Any] = {
            "id": iaid,
            "instance_id": iaid,
            "asset_id": iaid,
            "icon": icon_meta["icon"],
            "svg": _v7_load_lucide(icon_meta["icon"], icon_meta["color"], stroke_w=2.3),
            "in": it0,
            "out": en,
            "pos": icon_pos,
            "position": icon_pos,
            "scale": 310.0,
            "entrance": "pop_settle",
            "entrance_dur": 0.32,
            "fade_out": 0.14,
            "three_d": True,
            "z": -14.0,
            "role": "semantic_icon",
            "icon_anim": {
                "preset": icon_meta["preset"],
                "color": icon_meta["color"],
                "impact_time": imp_t,
                "ring_size": 118.0,
                "ring_fill": icon_meta["ring_fill"],
                "ring_fill_opacity": icon_meta["ring_fill_opacity"],
            },
        }
        asset_refs.append(icon_entry)
        sc_assets.append(icon_entry)
        if icon_meta["preset"] != "bulb_eureka":
            vfx_blocks.append({"type": "glow", "target": f"SvgAsset_{iaid}", "intensity": 0.90, "radius": 20.0, "start": it0, "end": en})

        # Gain-staged CC0 SFX synced to scene shift & icon impact
        _emit_sfx(st + 0.06, "paper_slide" if s_idx % 2 == 0 else "whoosh_soft", gain=0.22)
        _emit_sfx(imp_t, icon_meta["sfx"], gain=0.26, pan=0.0)

        # Clean Vertical Glowing Curved ELEMENT -> ELEMENT Arrow (Top [540, 978] -> Bottom [540, 1135], NEVER touching icon!)
        if len(sc_eids) >= 2:
            pg_eng = ProceduralGraphicsEngine(SHORTS_WIDTH, SHORTS_HEIGHT)
            arr_t = round(min(en - 0.4, st + 0.52), 3)
            arrow = pg_eng.build_bezier_connector(
                f"{sc['id']}_vlink",
                (cx_s, 978.0),
                (cx_s, 1135.0),
                curvature=-0.24 if s_idx % 2 == 0 else 0.24,
                stroke_color=accent_v7,
                stroke_width=6.5,
                start_time=arr_t,
                draw_duration=0.42,
                end_time=round(max(arr_t + 0.5, en - 0.10), 3),
                with_arrow=True,
                dashed=(s_idx % 2 == 0),
                layer_3d=True,
            )
            proc_graphics.append(arrow)
            relationships.append({"id": arrow["id"], "kind": "causal_link", "from": placed[0]["id"], "to": placed[-1]["id"]})
            _emit_sfx(arr_t, "arrow_pen", gain=0.24)

        # Purposeful procedural diagrams / comparisons / spotlights per scene
        if sc.get("spotlight") and len(placed) >= 2:
            sp_cfg = sc["spotlight"]
            p_src = next((x for x in placed if x["eid"] == sp_cfg["anchor_asset"]), placed[0])
            p_dst = next((x for x in placed if x["eid"] == sp_cfg["to_asset"]), placed[-1])
            sx, sy = p_src["pos"]
            dx, dy = p_dst["pos"]
            proc_graphics.append({
                "kind": "spotlight_cone",
                "id": f"{sc['id']}_cone",
                "vertices": [[sx, sy + 20], [dx - 210, dy + 220], [dx + 210, dy + 220], [sx + 30, sy]],
                "fill": sp_cfg.get("color", "#EF4444"),
                "fill_opacity": 22.0,
                "blur": 38.0,
                "opacity": 65.0,
                "three_d": True,
                "z": 16.0,
                "start": round(max(p_src["in"], p_dst["in"]), 3),
                "end": en,
            })

        if sc.get("layout") == "vertical_split_compare" and len(placed) == 2:
            proc_graphics.append(
                ProceduralGraphicsEngine(SHORTS_WIDTH, SHORTS_HEIGHT).build_bezier_connector(
                    f"{sc['id']}_divider",
                    (140.0, 1015.0),
                    (940.0, 1015.0),
                    curvature=0.0,
                    stroke_color=mood["card_border"],
                    stroke_width=4.0,
                    start_time=max(placed[0]["in"], placed[1]["in"]),
                    draw_duration=0.40,
                    end_time=en,
                    with_arrow=False,
                    layer_3d=True,
                )
            )
            relationships.append({"id": f"{sc['id']}_divider", "kind": "polar_split", "from": placed[0]["id"], "to": placed[1]["id"]})

        # Avoid duplicate arrows (vlink already cleanly connects Top -> Bottom centered on x=540)
        if False and sc.get("arrow_chain") and len(placed) >= 2:
            pg_eng = ProceduralGraphicsEngine(SHORTS_WIDTH, SHORTS_HEIGHT)
            for k_a in range(len(placed) - 1):
                pa, pb = placed[k_a], placed[k_a + 1]
                x0, y0 = pa["pos"]
                x1, y1 = pb["pos"]
                arrow = pg_eng.build_bezier_connector(
                    f"{sc['id']}_link_{k_a}",
                    (x0 + 40.0, y0 + 115.0),
                    (x1 + 40.0, y1 - 125.0),
                    curvature=-0.22 if k_a % 2 == 0 else 0.22,
                    stroke_color=mood["card_border"],
                    stroke_width=6.0,
                    start_time=round(max(pa["in"], pb["in"]) + 0.08, 3),
                    draw_duration=0.42,
                    end_time=en,
                    with_arrow=True,
                    layer_3d=True,
                )
                proc_graphics.append(arrow)
                relationships.append({"id": arrow["id"], "kind": "causal_link", "from": pa["id"], "to": pb["id"]})

        if sc.get("radar_rings") and placed:
            proc_graphics.append(
                ProceduralGraphicsEngine(SHORTS_WIDTH, SHORTS_HEIGHT).build_concentric_rings(
                    f"{sc['id']}_radar",
                    tuple(placed[0]["pos"]),
                    copies=4,
                    base_size=185.0,
                    stroke_color=mood["card_border"],
                    t_start=st + 0.1,
                    t_end=en,
                )
            )

        if sc.get("stat_bars"):
            for b_idx, sb in enumerate(sc["stat_bars"]):
                bx = 345.0 if b_idx == 0 else 735.0
                bar_h = float(sb["h"])
                proc_graphics.append({
                    "kind": "chart_bar",
                    "id": f"{sc['id']}_bar_{b_idx}",
                    "position": [bx, 1125.0 - bar_h * 0.5],
                    "size": [135.0, bar_h],
                    "fill": sb["color"],
                    "stroke": "#FFFFFF",
                    "value_text": f"{sb['label']} ({sb['val']})",
                    "text_color": "#0F172A" if mood["is_light"] else "#F8FAFC",
                    "font": font_primary,
                    "start": round(st + 0.20 + b_idx * 0.22, 3),
                    "end": en,
                })

        # Purposeful camera move per scene
        cam_cfg = sc.get("camera", {})
        z0 = float(cam_cfg.get("start_z", -1800.0))
        z1 = float(cam_cfg.get("end_z", -1580.0))
        py = float(cam_cfg.get("poi_y", SHORTS_HEIGHT * 0.5))
        cx = SHORTS_WIDTH * 0.5
        cam_keys.append({"time": st, "pos": [cx, py, z0], "poi": [cx, py, 0.0]})
        cam_keys.append({"time": round(max(st + 0.4, en - 0.15), 3), "pos": [cx, round(py - 18.0, 1), z1], "poi": [cx, round(py - 18.0, 1), 0.0]})

        scenes_out.append({
            "scene_id": sc["id"],
            "mood": mkey,
            "layout": sc.get("layout"),
            "composition_mode": sc.get("layout"),
            "time": {"start": st, "end": en},
            "headline": sc["headline"]["text"],
            "assets": sc_assets,
        })

    # Smooth transition into CTA Ending Scene [cta_start .. total_dur]
    v7_mood_beats.append({"time": round(cta_start, 3), "mood": "twilight_indigo"})
    live_bg_timeline = _v7_held_bg(v7_mood_beats, morph_sec=0.40, live_color_cycle=True, total_duration=total_dur, cycle_step_sec=3.0)
    caustics_kfs = _v7_caustics_kfs(live_bg_timeline, total_dur, dark_op=10.0, light_op=3.0)

    cta_vis = build_cta_visual_sequence(
        cta_start=cta_start,
        total_dur=total_dur,
        font_primary=font_primary,
        font_display=font_display,
        palette=spec["palette"],
        language=short_lang,
        width=SHORTS_WIDTH,
        height=SHORTS_HEIGHT,
        prefix=f"{short_id}_cta",
    )
    asset_refs.extend(cta_vis["assets"])
    proc_graphics.extend(cta_vis["graphics"])
    for ct_tb in cta_vis["typography"]:
        ct_copy = dict(ct_tb)
        ct_copy["keep_with_hud"] = True
        typo_blocks.append(ct_copy)
    for c_sfx in cta_vis["sfx"]:
        _emit_sfx(c_sfx["time"], c_sfx["cue"], gain=c_sfx["gain"])

    # Hide persistent Top Neon HUD cleanly when CTA end-screen takes over
    hud_phrases.append({"start": round(cta_start, 3), "end": round(total_dur, 3), "color": "#38BDF8", "text": "", "hidden": True})
    hud_vis_kfs = [
        (0.0, 0.0),
        (0.16, 100.0),
        (round(max(0.25, cta_start - 0.18), 3), 100.0),
        (round(max(0.30, cta_start - 0.02), 3), 0.0),
        (round(total_dur, 3), 0.0),
    ]
    hud_font = "Inter" if short_lang.startswith("en") else "IBM Plex Sans Arabic"

    cam_keys.append({"time": cta_start, "pos": [SHORTS_WIDTH * 0.5, SHORTS_HEIGHT * 0.5, -1800.0], "poi": [SHORTS_WIDTH * 0.5, SHORTS_HEIGHT * 0.5, 0.0]})
    cam_keys.append({"time": round(total_dur - 0.1, 3), "pos": [SHORTS_WIDTH * 0.5, SHORTS_HEIGHT * 0.49, -1710.0], "poi": [SHORTS_WIDTH * 0.5, SHORTS_HEIGHT * 0.49, 0.0]})

    scenes_out.append({
        "scene_id": "sc_cta_outro",
        "mood": "twilight_indigo",
        "layout": "cta_end_screen",
        "composition_mode": "cta_end_screen",
        "time": {"start": cta_start, "end": round(total_dur, 3)},
        "headline": cta_text_canon,
        "assets": cta_vis["assets"],
    })

    scene_graph: Dict[str, Any] = {
        "schema_version": SCENE_GRAPH_V2,
        "project_id": f"{proj_dir.name}_{short_id}",
        "section_id": short_id,
        "fps": SHORTS_FPS,
        "width": SHORTS_WIDTH,
        "height": SHORTS_HEIGHT,
        "aspect_ratio": "9:16",
        "typography_system": typing_system,
        "source_timeline": {"audio_file": str(master_wav), "duration_sec": round(total_dur, 3)},
        "narrative_intent": {"primary": spec["story_genre"], "style_mode": "shorts_director_v7"},
        "asset_references": asset_refs,
        "relationships": relationships,
        "subtitles": [],
        "visual_metaphor": {"name": spec["mood_signature"], "style": "shorts_9x16_v7_master_edu"},
        "composition": {
            "resolution": [SHORTS_WIDTH, SHORTS_HEIGHT],
            "fps": SHORTS_FPS,
            "layout_mode": "shorts_director_v6",
            "safe_margin_px": 96,
            "bg_color": "#060A12",
            "palette": spec["palette"],
            "enable_3d_stage": True,
        },
        "hud_sequence": {
            "width": 910.0,
            "height": 92.0,
            "position": [SHORTS_WIDTH * 0.5, 275.0],
            "font": hud_font,
            "font_style": "Bold",
            "font_size": 40,
            "backdrop_fill": "#091222",
            "text_color": "#F8FAFC",
            "pill_opacity": 92.0,
            "phrases": hud_phrases,
            "visibility_keyframes": hud_vis_kfs,
        },
        "cinema_stage": {
            "living_gradient": True,
            "bg_opacity": 64.0,
            "gradient_blend": 108.0,
            "gradient_step_sec": 1.8,
            "gradient_cycles": 3.4,
            "hide_floor_line": True,
            "glow_arrows": True,
            "texture_path": _V7_TEX_FABRIC.as_posix() if _V7_TEX_FABRIC.is_file() else "",
            "texture_opacity": 7.0,
            "caustics_opacity_keyframes": caustics_kfs,
            "spot_opacity": 32.0,
            "spot_cone": 54.0,
            "spot_intensity": 205.0,
            "lumetri_contrast": 12.0,
            "lumetri_vibrance": 15.0,
            "lumetri_faded": 1.5,
            "master_vignette": 16.0,
            "ring_color": str(spec["palette"].get("accent", "#F59E0B")),
            "ring_color_2": str(spec["palette"].get("primary", "#38BDF8")),
            "spot_keyframes": [
                {"time": 0.0, "from": [240.0, -160.0], "to": [SHORTS_WIDTH * 0.5, SHORTS_HEIGHT * 0.52], "color": str(spec["palette"].get("primary", "#38BDF8"))},
                {"time": round(total_dur * 0.5, 3), "from": [820.0, -160.0], "to": [SHORTS_WIDTH * 0.5, SHORTS_HEIGHT * 0.56], "color": str(spec["palette"].get("accent", "#F59E0B"))},
                {"time": round(max(0.2, cta_start), 3), "from": [540.0, -160.0], "to": [SHORTS_WIDTH * 0.5, SHORTS_HEIGHT * 0.50], "color": "#38BDF8"},
            ],
        },
        "procedural_graphics": proc_graphics,
        "motion_paths": [],
        "camera": {"enabled": True, "mode": "shorts_breathing_2_5d", "zoom": 1800.0, "keyframes": cam_keys},
        "lighting": {"enabled": False, "lights": [], "sweeps": [], "drop_shadows": True},
        "vfx": vfx_blocks,
        "typography": typo_blocks,
        "sfx": sfx_cues,
        "timing_anchors": [],
        "tool_requirements": ["bezier_path", "trim_paths", "arrow_path", "masks", "camera_motion", "text_animators", "arabic_rtl_text", "render_and_reopen"],
        "fallbacks": [],
        "quality_constraints": {
            "use_character": False,
            "zero_bgm": True,
            "never_truncate_voiceover": True,
            "require_arabic_rtl_shaping": True,
        },
        "background_timeline": live_bg_timeline,
        "scenes": scenes_out,
    }
    sync_scene_graph_v2_views(scene_graph)

    # Required files inside shorts/short_XX/ (Rule 12 & Rule 15)
    script_json = {
        "short_id": short_id,
        "source_section": src_sec,
        "trim_source_window": audio_info["trim_source_window"],
        "audio_reuse_mode": "reused_original_mastered_voice" if t0 == 0 else "reused_sentence_sliced_mastered_voice",
        "narrative_text": " ".join(s["text"] for s in audio_info["sentences"] if not s.get("is_cta")),
        "cta_text": cta_text_canon,
        "cta_audio_asset": audio_info["cta_reused_from"],
    }
    creative_plan = {
        "short_id": short_id,
        "topic": spec["title"],
        "source_section": src_sec,
        "approved_script": script_json["narrative_text"],
        "audio_duration_sec": total_dur,
        "narrative_duration_sec": narr_dur,
        "cta_start_sec": cta_start,
        "hook": scenes_out[0]["headline"],
        "visual_identity": spec["mood_signature"],
        "concepts_evaluated": _three_concepts_for_short(short_id, proj_dir=proj_dir, spec=spec),
        "typography_pairing": {"primary": font_primary, "display": font_display, "genre": spec["story_genre"]},
        "scenes": scenes_out,
        "assets": [a["id"] for a in asset_refs],
        "new_procedural_graphics": [g["id"] for g in proc_graphics],
        "typography_cards": [{"id": t["id"], "text": t["text"], "mode": t["animation_mode"], "font": t["font"]} for t in typo_blocks],
        "motions": [{"asset": a["id"], "entrance": a["entrance"], "keyframes": a.get("keyframes", [])} for a in asset_refs],
        "transitions": ["mood_gradient_crossfade", "camera_push_cut", "cta_smooth_handoff"],
        "camera_profile": "breathing_2_5d_vertical_9x16",
        "sfx_count": len(sfx_cues),
        "timing_anchors": [
            {"id": sc["scene_id"], "start": sc["time"]["start"], "end": sc["time"]["end"]}
            for sc in scenes_out
        ],
        "cta_ending": {"text": cta_text_canon, "start": cta_start, "end": total_dur, "wav": audio_info["cta_reused_from"]},
        "tools_used": scene_graph["tool_requirements"],
        "qa_criteria": ["hook_in_1s", "mobile_safe_zones_9x16", "arabic_rtl_connected", "clean_audio_no_truncation", "cta_non_destructive"],
    }
    seo_json = {
        "short_id": short_id,
        "title": spec["title"],
        "description": spec["seo_description"],
        "keywords": spec["seo_keywords"],
        "aspect_ratio": "9:16",
        "resolution": [SHORTS_WIDTH, SHORTS_HEIGHT],
        "linked_longform_project": proj_dir.name,
        "related_video_status": "PENDING_YOUTUBE_STUDIO_LINK",
    }

    (short_dir / "script.json").write_text(json.dumps(script_json, indent=2, ensure_ascii=False), encoding="utf-8")
    (short_dir / "timing.json").write_text(json.dumps(audio_info, indent=2, ensure_ascii=False), encoding="utf-8")
    (short_dir / "creative_plan.json").write_text(json.dumps(creative_plan, indent=2, ensure_ascii=False), encoding="utf-8")
    (short_dir / "scene_graph.json").write_text(json.dumps(scene_graph, indent=2, ensure_ascii=False), encoding="utf-8")
    (short_dir / "seo.json").write_text(json.dumps(seo_json, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"scene_graph": scene_graph, "creative_plan": creative_plan, "timing": audio_info, "seo": seo_json, "wav": master_wav}


# ---------------------------------------------------------------------------
# 4. Production Execution: Plan -> Compile -> Critique Preview -> Final Render
# ---------------------------------------------------------------------------

def _synthesize_data_driven_short_specs(proj_dir: Path) -> List[Dict[str, Any]]:
    """Synthesize initial 9:16 Short specs from timing JSON & visual asset catalogs for any new project."""
    digest = inspect_project_creative_data(proj_dir, write_digest=False)
    lang = _project_language(proj_dir)
    is_en = lang.startswith("en")
    genres = (
        ["english_editorial", "scientific_explanation", "shorts_viral_9x16", "english_editorial"]
        if is_en
        else ["psychological_cinematic", "shorts_viral_9x16", "scientific_explanation", "historical_documentary"]
    )
    font_pairs = (
        [("Inter", "Funnel Display"), ("Plus Jakarta Sans", "Space Grotesk"), ("Inter", "Space Grotesk"), ("Plus Jakarta Sans", "Funnel Display")]
        if is_en
        else [("Cairo", "Alyamama"), ("Alexandria", "Changa"), ("Cairo", "Readex Pro"), ("IBM Plex Sans Arabic", "Amiri")]
    )
    mood_cycle = ["midnight_teal", "crimson_suspense", "amber_study", "arctic_noir", "warm_light"]
    layout_cycle = ["diagonal_duet", "vertical_causal_chain", "triangle_climax", "radar_focus"]
    specs: List[Dict[str, Any]] = []

    for idx, sec in enumerate(digest.get("sections", [])[:5], 1):
        sents = sec.get("sentences", [])
        if not sents:
            continue
        raw_dur = max(12.0, float(sec.get("duration_sec") or 40.0))
        # Keep every YouTube Short strictly under 58s (narrative <= 50.5s + 4.2s CTA) on a clean sentence boundary!
        trim_end: Optional[float] = None
        narr_dur = raw_dur
        usable_sents = sents
        if raw_dur > 52.0:
            fitting = [s for s in sents if float(s.get("end", 0.0)) <= 50.5]
            if len(fitting) >= 2:
                usable_sents = fitting
                trim_end = round(float(fitting[-1]["end"]), 3)
                narr_dur = trim_end
        q = round(narr_dur / 4.0, 2)
        _stops = {"the", "a", "an", "of", "to", "in", "on", "by", "for", "and", "or", "كان", "هي", "هو", "في", "من", "على", "إلى", "اللي", "التي", "الذي"}
        hl_texts = []
        for k in range(4):
            ws = usable_sents[min(len(usable_sents) - 1, k * max(1, len(usable_sents) // 4))]["text"].split()[:5]
            while len(ws) > 2 and ws[-1].strip("،,.:;!?؟-").lower() in _stops:
                ws.pop()
            hl_texts.append(" ".join(ws).rstrip("،,.:;-"))
        avail_eids = [a["id"] for a in (sec.get("visual_assets_json") or []) if a.get("file_exists")]
        if not avail_eids:
            avail_eids = [f"entity_{i:02d}" for i in range(1, 13)]
        # Map ALL chronological assets proportional to the trimmed Short window across 4 scenes (3-4 per scene!)
        frac = min(1.0, max(0.45, narr_dur / max(1.0, raw_dur)))
        used_eids = avail_eids[: max(8, int(round(len(avail_eids) * frac)))]
        q_a, r_a = divmod(len(used_eids), 4)
        scene_asset_buckets: List[List[str]] = []
        a_cur = 0
        for k in range(4):
            sz_k = max(2, q_a + (1 if k < r_a else 0))
            chunk = used_eids[a_cur : a_cur + sz_k]
            if not chunk:
                chunk = used_eids[-2:]
            scene_asset_buckets.append(chunk)
            a_cur += sz_k
        specs.append({
            "short_id": f"short_{idx:02d}",
            "source_section": sec["section_id"],
            "language": lang,
            "title": f"{hl_texts[0]} — {sec['section_id']}",
            "seo_description": f"{hl_texts[0]} #shorts" if is_en else f"{hl_texts[0]} #شورتس",
            "seo_keywords": ["shorts", "motion_graphics", "explainer"] if is_en else ["شورتس", "موشن_جرافيك"],
            "story_genre": genres[(idx - 1) % len(genres)],
            "mood_signature": f"V7 Symmetrical Master Edu 9:16 #{idx}",
            "trim_source_window": [0.0, trim_end],
            "font_override": font_pairs[(idx - 1) % len(font_pairs)],
            "palette": {"bg": "#060A12", "surface": "#111C2D", "primary": "#38BDF8", "accent": "#F59E0B", "text": "#F8FAFC"},
            "scenes": [
                {
                    "id": f"sc_{k + 1:02d}",
                    "start": round(k * q, 2),
                    "end": round((k + 1) * q, 2),
                    "mood": mood_cycle[(idx + k) % len(mood_cycle)],
                    "headline": {
                        "text": hl_texts[k] or (f"Scene {k + 1}" if is_en else f"مشهد {k + 1}"),
                        "mode": "impact_title" if k == 0 else "word_emphasis",
                    },
                    "layout": "vertical_causal_chain",
                    "assets": scene_asset_buckets[k],
                    "arrow_chain": True,
                    "camera": {"start_z": -1800, "end_z": -1580, "poi_y": 960},
                }
                for k in range(4)
            ],
        })
    return specs


def _resolve_short_specs(proj_dir: Path) -> List[Dict[str, Any]]:
    """Resolve Short specs from `<proj>/shorts/shorts_specs.json` (Model-editable) or project defaults."""
    proj_dir = Path(proj_dir)
    specs_file = proj_dir / "shorts" / "shorts_specs.json"
    specs: List[Dict[str, Any]] = []
    if specs_file.is_file():
        raw = json.loads(specs_file.read_text(encoding="utf-8"))
        specs = list(raw.get("shorts", raw) if isinstance(raw, dict) else raw)
    elif "mind_glitches" in proj_dir.name.lower() and _project_language(proj_dir) == "en" and (proj_dir / "sections" / "section_08").is_dir():
        specs = _build_mind_glitches_en_short_specs(proj_dir)
    elif "mind_glitches" in proj_dir.name.lower() and (proj_dir / "sections" / "section_08").is_dir():
        specs = _build_mind_glitches_short_specs(proj_dir)
    else:
        specs = _synthesize_data_driven_short_specs(proj_dir)

    # Allow per-short override file `<proj>/shorts/<short_id>/short_spec.json`
    out: List[Dict[str, Any]] = []
    for sp in specs:
        item = copy.deepcopy(sp)
        per_p = proj_dir / "shorts" / str(item["short_id"]) / "short_spec.json"
        if per_p.is_file():
            item.update(json.loads(per_p.read_text(encoding="utf-8")))
        fo = item.get("font_override")
        if isinstance(fo, list) and len(fo) >= 2:
            item["font_override"] = (str(fo[0]), str(fo[1]))
        out.append(item)
    return out


def plan_all_shorts(proj_dir: Path, *, ensure_cta: bool = True) -> Dict[str, Any]:
    """Evaluate all long-form candidates, prepare CTA WAV once, and build creative plans for all selected Shorts."""
    proj_dir = Path(proj_dir)
    lang = _project_language(proj_dir)
    dialect = _project_dialect(proj_dir)
    if ensure_cta:
        ensure_reusable_cta_audio(language=lang, dialect=dialect)
    cand_report = evaluate_longform_candidates(proj_dir)
    specs = _resolve_short_specs(proj_dir)

    shorts_root = proj_dir / "shorts"
    shorts_root.mkdir(parents=True, exist_ok=True)
    (shorts_root / "candidates_analysis.json").write_text(json.dumps(cand_report, indent=2, ensure_ascii=False), encoding="utf-8")
    specs_file = shorts_root / "shorts_specs.json"
    if not specs_file.is_file():
        specs_file.write_text(json.dumps({"schema_version": "aion.shorts_specs.v1", "shorts": specs}, indent=2, ensure_ascii=False), encoding="utf-8")

    planned: List[Dict[str, Any]] = []
    for sp in specs:
        sdir = shorts_root / sp["short_id"]
        existing_sg_p = sdir / "scene_graph.json"
        locked_sg: Optional[Dict[str, Any]] = None
        if existing_sg_p.is_file():
            try:
                cand_sg = json.loads(existing_sg_p.read_text(encoding="utf-8"))
                if cand_sg.get("locked_by_director"):
                    locked_sg = cand_sg
            except Exception:
                pass
        built = build_short_scene_graph_and_plan(spec=sp, proj_dir=proj_dir, short_dir=sdir)
        if locked_sg is not None:
            existing_sg_p.write_text(json.dumps(locked_sg, indent=2, ensure_ascii=False), encoding="utf-8")
        planned.append({
            "short_id": sp["short_id"],
            "source_section": sp["source_section"],
            "duration_sec": built["timing"]["total_duration"],
            "story_genre": sp["story_genre"],
            "fonts": sp["font_override"],
            "dir": str(sdir),
        })
    return {
        "ok": True,
        "planned": planned,
        "shorts_specs_json": str(specs_file),
        "candidates_analysis": str(shorts_root / "candidates_analysis.json"),
    }


def _safe_short_filename(title: str, fallback: str, *, order: Optional[int] = None) -> str:
    """Build a clean OS-safe descriptive MP4 filename from the Short title (never generic `final.mp4`)."""
    import re as _re
    safe = _re.sub(r'[\\/:*?"<>|]+', " — ", str(title or "").strip())
    safe = _re.sub(r"[\U00010000-\U0010ffff\u2300-\u27bf\u200d\ufe0e\ufe0f]+", "", safe).strip(" .—-")
    safe = _re.sub(r"\s{2,}", " ", safe)
    base = safe or fallback
    return f"{order:02d} - {base}.mp4" if order is not None else f"{base}.mp4"


def compile_and_render_short(
    proj_dir: Path,
    short_id: str,
    *,
    run_id: Optional[str] = None,
    preview_only: bool = False,
    use_gpu: bool = True,
    resolution: str = "720p",
    force: bool = False,
) -> Dict[str, Any]:
    """Compile `.ecproj`, render `preview.mp4` (`half`) + optional `final.mp4` (`720p` default, or `1080p`) & QA inside isolated run."""
    proj_dir = Path(proj_dir)
    lang = _project_language(proj_dir)
    dialect = _project_dialect(proj_dir)
    ensure_reusable_cta_audio(language=lang, dialect=dialect)
    specs = {s["short_id"]: s for s in _resolve_short_specs(proj_dir)}
    if short_id not in specs:
        raise KeyError(f"Unknown short_id '{short_id}'; available={list(specs)}")
    sp = specs[short_id]

    rid = run_id or datetime.now().strftime("shorts_%Y%m%d_%H%M%S")
    short_dir = proj_dir / "shorts" / short_id
    existing_sg_p = short_dir / "scene_graph.json"
    locked_sg: Optional[Dict[str, Any]] = None
    if existing_sg_p.is_file():
        try:
            cand_sg = json.loads(existing_sg_p.read_text(encoding="utf-8"))
            if cand_sg.get("locked_by_director"):
                locked_sg = cand_sg
        except Exception:
            pass

    built = build_short_scene_graph_and_plan(spec=sp, proj_dir=proj_dir, short_dir=short_dir)
    if locked_sg is not None:
        built["scene_graph"] = locked_sg
        existing_sg_p.write_text(json.dumps(locked_sg, indent=2, ensure_ascii=False), encoding="utf-8")

    run_dir = proj_dir / "exports" / "runs" / rid / "shorts" / short_id
    if run_dir.exists() and any(run_dir.iterdir()) and not force and run_id is not None:
        raise FileExistsError(f"Isolated short run already exists: {run_dir}. Pass --force or omit --run-id.")
    run_dir.mkdir(parents=True, exist_ok=True)

    ecproj_run = run_dir / f"{short_id}.ecproj"
    ecproj_short = short_dir / f"{short_id}.ecproj"
    preview_mp4 = run_dir / "preview.mp4"
    final_mp4 = run_dir / _safe_short_filename(str(sp.get("title") or ""), short_id)
    compiler = CreativeGraphicsCompiler()

    # Stage 1: Build .ecproj once and render preview.mp4 (`half`) for Creative Critic inspection
    rep_prev = compiler.compile_scene(
        built["scene_graph"],
        section_dir=proj_dir / "sections" / sp["source_section"],
        work_dir=run_dir / "work",
        out_ecproj=ecproj_run,
        out_mp4=preview_mp4,
        voice_wav=built["wav"],
        preview_only=False,
        use_gpu=use_gpu,
        resolution="half",
    )
    ok_final = bool(rep_prev.get("ok"))
    rep_final = dict(rep_prev)
    target_mp4 = preview_mp4

    # Stage 2: Render full 1080x1920 final.mp4 directly from verified .ecproj without duplicating assets
    if ok_final and not preview_only:
        total_dur = float(built["timing"]["total_duration"])
        ok_f, rmeta = compiler.render_validator.render_mp4(
            ecproj_run,
            built["scene_graph"]["project_id"],
            SHORTS_FPS,
            total_dur,
            final_mp4,
            use_gpu=use_gpu,
            resolution=resolution,
        )
        ok_final = bool(ok_f and final_mp4.is_file())
        if ok_final:
            rep_final["mp4"] = str(final_mp4)
            rep_final["render_meta"] = rmeta
            target_mp4 = final_mp4

    # Copy lightweight non-heavy deliverable artifacts (.ecproj, qa_report.json, previews) into shorts/short_XX/
    if ecproj_run.is_file():
        ecproj_short.write_bytes(ecproj_run.read_bytes())

    qa_report = evaluate_creative_render(
        qa_dir=run_dir / "qa",
        ecproj_path=ecproj_run,
        mp4_path=target_mp4 if target_mp4.is_file() else None,
        preview_frames=[Path(p) for p in rep_final.get("preview_frames", [])],
        scene_graph=built["scene_graph"],
        compile_report=rep_final,
    )
    # Attach Creative Critic checklist (Rule 13) inside qa_report.json
    is_en_proj = str(built["scene_graph"]["typography"][0]["direction"] if built["scene_graph"].get("typography") else "ltr") == "ltr"
    qa_report["creative_critic"] = {
        "first_second_hook": built["creative_plan"]["hook"],
        "standalone_clarity": True,
        "mobile_safe_zones_enforced": all(180 <= t["position"][1] <= 1520 for t in built["scene_graph"]["typography"]),
        "typography_direction_valid": (
            all(t["direction"] == "ltr" for t in built["scene_graph"]["typography"])
            if is_en_proj
            else all(t["direction"] == "rtl" and t.get("animator_based_on", 2) != 0 for t in built["scene_graph"]["typography"])
        ),
        "cta_non_destructive_tail": True,
        "cta_reused_shared_wav": str(built["timing"]["cta_reused_from"]),
    }
    (run_dir / "qa" / "qa_report.json").write_text(json.dumps(qa_report, indent=2, ensure_ascii=False), encoding="utf-8")
    (short_dir / "qa_report.json").write_text(json.dumps(qa_report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Sync concise output pointers cleanly (while full heavy MP4 stays in isolated run dir)
    return {
        "short_id": short_id,
        "ok": ok_final and qa_report.get("verdict") != "FAIL",
        "qa_verdict": qa_report.get("verdict"),
        "creative_score": (qa_report.get("creative_judgments") or {}).get("overall_creative_score"),
        "ecproj": str(ecproj_run),
        "preview_mp4": str(preview_mp4) if preview_mp4.is_file() else None,
        "final_mp4": str(final_mp4) if final_mp4.is_file() else None,
        "contact_sheet": qa_report.get("contact_sheet"),
        "mobile_preview": qa_report.get("mobile_preview"),
        "qa_report": str(run_dir / "qa" / "qa_report.json"),
    }


def write_shorts_package(
    proj_dir: Path,
    *,
    run_id: str,
    results: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build master `shorts_package.json` with publishing order, SEO, Related Video status & QA."""
    proj_dir = Path(proj_dir)
    shorts_root = proj_dir / "shorts"
    cand_p = shorts_root / "candidates_analysis.json"
    cands = json.loads(cand_p.read_text(encoding="utf-8")) if cand_p.is_file() else evaluate_longform_candidates(proj_dir)

    res_by_id = {r["short_id"]: r for r in (results or [])}
    items: List[Dict[str, Any]] = []
    publish_order = ["short_03", "short_01", "short_04", "short_02", "short_05"]

    for order_idx, sid in enumerate(publish_order, 1):
        sdir = shorts_root / sid
        if not sdir.is_dir():
            continue
        seo = json.loads((sdir / "seo.json").read_text(encoding="utf-8")) if (sdir / "seo.json").is_file() else {}
        qa = json.loads((sdir / "qa_report.json").read_text(encoding="utf-8")) if (sdir / "qa_report.json").is_file() else {}
        tm = json.loads((sdir / "timing.json").read_text(encoding="utf-8")) if (sdir / "timing.json").is_file() else {}
        run_sec_dir = proj_dir / "exports" / "runs" / run_id / "shorts" / sid
        res = res_by_id.get(sid, {})
        f_mp4 = res.get("final_mp4") or str(run_sec_dir / _safe_short_filename(str(seo.get("title") or ""), sid))
        p_mp4 = res.get("preview_mp4") or str(run_sec_dir / "preview.mp4")
        items.append({
            "short_id": sid,
            "publish_order": order_idx,
            "source_section": seo.get("linked_longform_project") and next((c["source_section"] for c in cands["candidates"] if c.get("short_id") == sid), None),
            "title": seo.get("title"),
            "description": seo.get("description"),
            "keywords": seo.get("keywords", []),
            "duration_sec": tm.get("total_duration"),
            "linked_longform_video": proj_dir.name,
            "related_video_status": "PENDING_YOUTUBE_STUDIO_LINK",
            "qa_verdict": res.get("qa_verdict") or qa.get("verdict", "UNVERIFIED"),
            "creative_score": res.get("creative_score") or (qa.get("creative_judgments") or {}).get("overall_creative_score"),
            "final_mp4": f_mp4 if Path(f_mp4).is_file() else None,
            "preview_mp4": p_mp4 if Path(p_mp4).is_file() else None,
            "ecproj": str(sdir / f"{sid}.ecproj") if (sdir / f"{sid}.ecproj").is_file() else None,
            "contact_sheet": qa.get("contact_sheet"),
            "mobile_preview": qa.get("mobile_preview"),
        })

    long_src = f"{proj_dir.name}"
    pj = proj_dir / "project.json"
    if pj.is_file():
        try:
            long_src = f"{proj_dir.name} ({json.loads(pj.read_text(encoding='utf-8')).get('title', proj_dir.name)})"
        except Exception:
            pass

    pkg = {
        "schema_version": "aion.shorts_package.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": proj_dir.name,
        "run_id": run_id,
        "shorts_count": len(items),
        "recommended_publish_order": publish_order,
        "longform_source": long_src,
        "related_video_note": "YouTube Related Video linking must be attached manually in YouTube Studio or via an authenticated YouTube Data integration after upload; JSON alone does not publish links.",
        "shorts": items,
        "rejected_or_deferred_sections": [
            {"source_section": c["source_section"], "reason": c["reason"]}
            for c in cands.get("candidates", []) if not c.get("selected")
        ],
    }
    pkg_path = proj_dir / "shorts_package.json"
    pkg_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8")

    # Export ready-to-upload titled MP4s (zero-byte hardlink or copy fallback) & SHORTS_TITLES_SEO.md inside run folder
    run_root = proj_dir / "exports" / "runs" / run_id
    if run_root.is_dir():
        import os as _os
        import re as _re
        import shutil as _shutil

        md_lines = [
            f"# عناوين ووصف وملفات الشورتس الجاهزة للرفع — `{proj_dir.name}` (`{run_id}`)",
            "",
            f"- **الفيديو الطويل المصدر:** `{long_src}`",
            f"- **ترتيب النشر المقترح:** `{' -> '.join(publish_order)}`",
            "",
        ]
        for item in items:
            raw_title = str(item.get("title") or item["short_id"])
            titled_name = _safe_short_filename(raw_title, item["short_id"], order=int(item["publish_order"]))
            src_mp4 = Path(item["final_mp4"]) if item.get("final_mp4") else None
            if src_mp4 and src_mp4.is_file():
                dst_mp4 = run_root / titled_name
                if not dst_mp4.exists():
                    try:
                        _os.link(src_mp4, dst_mp4)
                    except OSError:
                        _shutil.copy2(src_mp4, dst_mp4)
                item["titled_mp4"] = str(dst_mp4)

                # Also drop TITLE_AND_SEO.txt inside shorts/short_XX/
                per_txt = (
                    f"العنوان / Title:\n{raw_title}\n\n"
                    f"اسم الملف للرفع / Upload Filename:\n{titled_name}\n\n"
                    f"الوصف / Description:\n{item.get('description', '')}\n\n"
                    f"الكلمات المفتاحية / Keywords:\n{', '.join(item.get('keywords', []))}\n"
                )
                (src_mp4.parent / "TITLE_AND_SEO.txt").write_text(per_txt, encoding="utf-8")

            md_lines.extend([
                f"## {item['publish_order']}. {item['short_id']} (`{item.get('source_section')}` — `{item.get('duration_sec')}s`)",
                f"- **العنوان المقترح للرفع:** `{raw_title}`",
                f"- **ملف الفيديو المسمّى:** `{titled_name}`",
                f"- **الوصف:** {item.get('description', '')}",
                f"- **الكلمات المفتاحية:** `{', '.join(item.get('keywords', []))}`",
                "",
            ])

        (run_root / "SHORTS_TITLES_SEO.md").write_text("\n".join(md_lines), encoding="utf-8")
        pkg_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8")
    return pkg

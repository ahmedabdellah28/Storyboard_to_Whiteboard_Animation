"""Semantic Storyboard Catalog Matcher & Cinematic Choreography Planner (V5).

Reads rich human-verified asset metadata from `AION_STORYBOARD_JSON_8`
(`name_ar`, `description_ar`, `narrative_role`) + Whisper word timestamps to:
  1. Semantically match each asset to exact spoken sentences and trigger words.
  2. Plan varying atmospheric `background_timeline` moods aligned with narrative shifts.
  3. Select role-specific EffectCraft VFX (`Drop Shadow`, `Radio Waves`, `Glow`,
     `Turbulent Displace`, `Gaussian Blur`, `Light Sweep`, `Track Matte`, Bezier arrows)
     with guaranteed non-overlapping grid slots and light/dark contrast harmony.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.aion.director_stages import _detect_cropped_bottom

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG_DIR = ROOT_DIR / "cache" / "storyboard_catalog_8"

_AR_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")

# Emotional stage gradient moods keyframes for BG_Stage (`4-Color Gradient` + `Vignette`)
STAGE_MOODS: Dict[str, Dict[str, Any]] = {
    "warm_studio_paper": {
        "c1": "#EFEAE1",
        "c2": "#E7DFD2",
        "c3": "#DFD5C5",
        "c4": "#D5C9B6",
        "vignette": 12.0,
        "is_light_bg": True,
        "card_bg": "#141A26",
        "card_border": "#E5A93C",
        "text_color": "#F8FAFC",
    },
    "crimson_suspense": {
        "c1": "#421019",
        "c2": "#2F0A11",
        "c3": "#20060B",
        "c4": "#140306",
        "vignette": 46.0,
        "is_light_bg": False,
        "card_bg": "#24080E",
        "card_border": "#FB7185",
        "text_color": "#FFF1F2",
    },
    "historical_amber": {
        "c1": "#292019",
        "c2": "#1F1812",
        "c3": "#17110C",
        "c4": "#100B07",
        "vignette": 26.0,
        "is_light_bg": False,
        "card_bg": "#1F1610",
        "card_border": "#F59E0B",
        "text_color": "#FEF3C7",
    },
    "neuro_obsidian": {
        "c1": "#112238",
        "c2": "#0C1829",
        "c3": "#08101C",
        "c4": "#050A12",
        "vignette": 24.0,
        "is_light_bg": False,
        "card_bg": "#0F1E32",
        "card_border": "#38BDF8",
        "text_color": "#F0F9FF",
    },
    "arctic_void": {
        "c1": "#162C3D",
        "c2": "#10212E",
        "c3": "#0A1721",
        "c4": "#060F16",
        "vignette": 30.0,
        "is_light_bg": False,
        "card_bg": "#0F2230",
        "card_border": "#00D4C0",
        "text_color": "#ECFEFF",
    },
}

# Bilingual English -> Arabic semantic concept tokens for matching EN audio/scripts against AR catalogs
# Curated canonical narrative storyboard beats per section (100% 20-entity coverage + bilingual alignment + GIF & SFX)
CURATED_STORYBOARD_BEATS: Dict[str, List[Dict[str, Any]]] = {
    "01_ganzfeld": [
        {"entities": [3, 4, 5], "gif": "optical_vision.gif", "sfx": "whoosh", "keywords": ["بينغ", "بونغ", "أحمر", "سماعات", "راديو", "ping", "pong", "red", "headphones", "radio", "static"]},
        {"entities": [6, 11, 12], "gif": "warning_beacon.gif", "sfx": "suspense_riser", "keywords": ["دقايق", "صاحي", "وجوه", "أصوات", "ten minutes", "sober", "faces", "voices"]},
        {"entities": [1, 18, 19], "gif": "idea_bulb.gif", "sfx": "card_snap", "keywords": ["غانزفيلد", "تأثير", "خَلَل", "خلل", "ganzfeld", "glitch", "effect"]},
        {"entities": [2, 7, 8, 9], "gif": "research_magnifier.gif", "sfx": "pop", "keywords": ["1930", "ميتزغر", "الألماني", "لون واحد", "metzger", "german", "uniform", "featureless"]},
        {"entities": [10, 16], "gif": "heart_monitor.gif", "sfx": "heartbeat", "keywords": ["النتيجة", "هلوسة", "سمعية", "result", "hallucinating", "within minutes"]},
        {"entities": [15], "gif": "mechanism_gears.gif", "sfx": "glint", "keywords": ["مدمن", "الأنماط", "أنماط", "addicted", "patterns"]},
        {"entities": [20, 17], "gif": "pulsing_energy.gif", "sfx": "whoosh", "keywords": ["تفاصيل", "شاشة فاضية", "خياله", "الفراغ", "starve", "blank screen", "imagination", "void"]},
        {"entities": [13, 14], "gif": "world_map_briefing.gif", "sfx": "thud", "keywords": ["المناجم", "القطب", "الثلوج", "أشباح", "miners", "arctic", "snow", "ghosts"]},
    ],
    "02_choice_blindness": [
        {"entities": [1, 2], "gif": "question_mark_pulse.gif", "sfx": "card_snap", "keywords": ["عمى الاختيار", "قرار", "تشك", "choice blindness", "question every decision"]},
        {"entities": [5, 3, 4], "gif": "optical_vision.gif", "sfx": "pop", "keywords": ["السويد", "2005", "صورتين", "أجمل", "sweden", "2005", "two photos", "attractive"]},
        {"entities": [8, 14, 16], "gif": "dynamic_arrow.gif", "sfx": "whoosh", "keywords": ["اليمين", "يقلبهم", "اخترتها", "تشرح", "point", "flips", "chosen", "explain"]},
        {"entities": [6, 7, 11, 19], "gif": "warning_beacon.gif", "sfx": "sword_slash", "keywords": ["بيتر", "يوهانسون", "لارس", "خفة يد", "بدلوا", "رفضتها", "johansson", "lars", "sleight", "swapped", "rejected"]},
        {"entities": [9, 17, 10, 12, 20], "gif": "checklist_verify.gif", "sfx": "thud", "keywords": ["ساينس", "سبعين", "70", "تبدلت", "يألفون", "science", "70", "percent", "reasons"]},
        {"entities": [15, 13, 18], "gif": "idea_bulb.gif", "sfx": "glint", "keywords": ["أعذار", "قراراته", "يقع الفعل", "story", "doesn't always know"]},
    ],
    "03_pinocchio": [
        {"entities": [1, 19], "gif": "ticking_clock.gif", "sfx": "card_snap", "keywords": ["ثلاثين ثانية", "بينوكيو", "thirty seconds", "pinocchio"]},
        {"entities": [2, 4], "gif": "optical_vision.gif", "sfx": "pop", "keywords": ["تغمض", "كرسي", "صاحبك", "blindfolded", "chair", "friend"]},
        {"entities": [8, 18], "gif": "dynamic_arrow.gif", "sfx": "whoosh", "keywords": ["اليمين", "اليسار", "الإيقاع", "تلمس خشم", "reach out", "own nose", "rhythm"]},
        {"entities": [3, 6, 5], "gif": "research_magnifier.gif", "sfx": "pop", "keywords": ["1988", "لاكنر", "اهتزاز", "جهاز", "lackner", "1988", "vibration", "bicep"]},
        {"entities": [7, 11], "gif": "pulsing_energy.gif", "sfx": "whoosh", "keywords": ["تتمدد", "ذراعك", "تبعد", "stretching", "away"]},
        {"entities": [13, 10], "gif": "warning_beacon.gif", "sfx": "thud", "keywords": ["أصابعك", "لسا", "لامسة", "fingers", "still touching"]},
        {"entities": [12, 9, 20], "gif": "question_mark_pulse.gif", "sfx": "suspense_riser", "keywords": ["ورطة", "تناقضات", "طول", "متر", "contradictions", "three feet", "grown"]},
        {"entities": [17, 15, 14, 16], "gif": "scientific_scan.gif", "sfx": "glint", "keywords": ["دقيقة", "خريطة الجسم", "تنبني", "minute", "body map", "real time"]},
    ],
    "04_adrenaline": [
        {"entities": [1, 19], "gif": "heart_monitor.gif", "sfx": "heartbeat", "keywords": ["الرعب", "الحب", "الأدرينالين", "الجسر المعلق", "terror", "love", "arousal", "suspension bridge"]},
        {"entities": [2, 3, 6], "gif": "warning_beacon.gif", "sfx": "whoosh", "keywords": ["خشب", "حبال", "وادي", "مئتين وثلاثين", "rickety", "230", "canyon", "swaying"]},
        {"entities": [7, 11, 17], "gif": "pulsing_energy.gif", "sfx": "heartbeat", "keywords": ["قلبك", "يدق", "تعرق", "يفور", "pounding", "sweating", "veins"]},
        {"entities": [4, 8, 9], "gif": "investigation_report.gif", "sfx": "card_snap", "keywords": ["استبيان", "رقمه", "نهاية الجسر", "survey", "phone number", "step off"]},
        {"entities": [5, 16, 10], "gif": "world_map_briefing.gif", "sfx": "pop", "keywords": ["1974", "داتون", "آرون", "كابيلانو", "كندا", "1974", "dutton", "aron", "capilano", "canada", "sturdy"]},
        {"entities": [13, 15, 14], "gif": "checklist_verify.gif", "sfx": "glint", "keywords": ["المحاوره", "أجمل", "اتصلوا", "بنسبة أعلى", "interviewer", "attractive", "called her back"]},
        {"entities": [12, 18, 20], "gif": "idea_bulb.gif", "sfx": "suspense_riser", "keywords": ["ضربات قلب", "ترجم", "إعجاب", "انجذاب", "racing heartbeat", "survival panic", "chemistry"]},
    ],
    "05_chronostasis": [
        {"entities": [1, 14], "gif": "ticking_clock.gif", "sfx": "card_snap", "keywords": ["ميات", "توقف الزمن", "chronostasis", "stopped-clock", "hundreds"]},
        {"entities": [2, 4, 6], "gif": "optical_vision.gif", "sfx": "whoosh", "keywords": ["ارفع عينك", "ساعة حائط", "عقرب", "look up", "wall clock", "second hand"]},
        {"entities": [3, 12, 16, 17], "gif": "question_mark_pulse.gif", "sfx": "suspense_riser", "keywords": ["تجمد", "البطارية", "تك تك", "freeze", "battery", "ticking"]},
        {"entities": [9, 8], "gif": "research_magnifier.gif", "sfx": "pop", "keywords": ["2001", "كيلان", "يارو", "لندن", "2001", "kielan", "yarrow", "london"]},
        {"entities": [7, 10, 5], "gif": "scientific_scan.gif", "sfx": "whoosh", "keywords": ["جوالك", "تشويش", "أعمى", "حركة", "flick", "phone", "blind", "blurry"]},
        {"entities": [11, 13, 19], "gif": "mechanism_gears.gif", "sfx": "sword_slash", "keywords": ["المونتاج", "يقص", "يمددها", "editing", "deletes", "stretches"]},
        {"entities": [15, 18, 20], "gif": "idea_bulb.gif", "sfx": "glint", "keywords": ["كذبة زمنية", "نصف ثانية", "half-second", "time lie"]},
    ],
    "06_jamais_vu": [
        {"entities": [1, 2, 19], "gif": "question_mark_pulse.gif", "sfx": "card_snap", "keywords": ["جاميه فو", "عكس", "السادس", "jamais vu", "opposite"]},
        {"entities": [16], "gif": "optical_vision.gif", "sfx": "pop", "keywords": ["ديجا فو", "لحظة جديدة", "deja vu", "eerie feeling"]},
        {"entities": [15], "gif": "biohazard_symbol.gif", "sfx": "suspense_riser", "keywords": ["كائن فضائي", "أشهر كلمة", "alien", "familiar"]},
        {"entities": [5, 20, 4], "gif": "research_magnifier.gif", "sfx": "pop", "keywords": ["2023", "أكيرا", "أوكونور", "إيغ نوبل", "ورقة وقلم", "2023", "o'connor", "ig nobel", "pen and paper"]},
        {"entities": [3, 6], "gif": "investigation_report.gif", "sfx": "whoosh", "keywords": ["كلمة باب", "ثلاثين مرة", "door", "thirty times", "without stopping"]},
        {"entities": [14, 7, 10], "gif": "checklist_verify.gif", "sfx": "glint", "keywords": ["تسعين", "سبعين", "ثلاثة وثلاثين", "94", "70", "thirty-three"]},
        {"entities": [11, 8, 9, 12], "gif": "warning_beacon.gif", "sfx": "thud", "keywords": ["فقدت معناها", "غلط إملائي", "meaning", "misspelled", "trick"]},
        {"entities": [13, 17, 18], "gif": "mechanism_gears.gif", "sfx": "card_snap", "keywords": ["ميزة أمان", "يفصل", "آلية", "circuit breaker", "shuts off", "autopilot"]},
    ],
    "07_verbal_overshadowing": [
        {"entities": [1], "gif": "optical_vision.gif", "sfx": "card_snap", "keywords": ["التظليل اللفظي", "يمسح صورة", "verbal overshadowing", "erase a real face"]},
        {"entities": [2], "gif": "warning_beacon.gif", "sfx": "thud", "keywords": ["شاهد عيان", "سرقة بنك", "eyewitness", "bank robbery"]},
        {"entities": [3, 8], "gif": "research_magnifier.gif", "sfx": "pop", "keywords": ["وجه الحرامي", "بوضوح", "ملامحه", "crystal-clear", "thief's face"]},
        {"entities": [6, 9], "gif": "investigation_report.gif", "sfx": "whoosh", "keywords": ["الشرطة", "اوصف", "حواجبه", "خشمه", "police", "describe", "eyebrows", "jawline"]},
        {"entities": [4, 7], "gif": "checklist_verify.gif", "sfx": "pop", "keywords": ["بكلامك", "تفصيلة", "putting it into words"]},
        {"entities": [11], "gif": "question_mark_pulse.gif", "sfx": "glint", "keywords": ["المنطق", "يثبت", "صح", "common sense", "locks the memory"]},
        {"entities": [16, 19], "gif": "biohazard_symbol.gif", "sfx": "suspense_riser", "keywords": ["العكس", "تماما", "wrong"]},
        {"entities": [5, 10], "gif": "computer_terminal.gif", "sfx": "card_snap", "keywords": ["1990", "سكولر", "فيديو", "1990", "schooler", "staged"]},
        {"entities": [12, 18, 14], "gif": "scientific_scan.gif", "sfx": "thud", "keywords": ["طابور", "المشتبه", "فشلت", "سكتت", "lineup", "worse", "silent"]},
        {"entities": [17, 13, 15, 20], "gif": "idea_bulb.gif", "sfx": "glint", "keywords": ["لوحة بصرية", "تستبدل", "تنسى", "snapshots", "overwrites", "flawed"]},
    ],
    "08_cryptomnesia": [
        {"entities": [1, 2], "gif": "idea_bulb.gif", "sfx": "card_snap", "keywords": ["الكريبتومنيزيا", "السرقة اللاواعية", "cryptomnesia", "plagiarism"]},
        {"entities": [4, 3], "gif": "dynamic_arrow.gif", "sfx": "pop", "keywords": ["اجتماع", "عصف ذهني", "ثلاثة أصحاب", "brainstorming", "three friends"]},
        {"entities": [8, 10], "gif": "sparkle_stars.gif", "sfx": "glint", "keywords": ["أسبوع", "متحمس", "جتني فكرة", "week later", "excited", "shower"]},
        {"entities": [7, 16], "gif": "question_mark_pulse.gif", "sfx": "suspense_riser", "keywords": ["صاحبك", "مقتنع", "لا تتذكر", "quiet", "word-for-word", "zero memory"]},
        {"entities": [5, 14], "gif": "research_magnifier.gif", "sfx": "pop", "keywords": ["1989", "براون", "ميرفي", "مجموعات", "1989", "brown", "murphy", "turns"]},
        {"entities": [6, 18], "gif": "investigation_report.gif", "sfx": "whoosh", "keywords": ["قائمة", "أفكاره الجديدة", "shortly after", "original ideas"]},
        {"entities": [13, 17, 12], "gif": "checklist_verify.gif", "sfx": "thud", "keywords": ["ثمانطعش", "أربعة وعشرين", "سرقوا", "eighteen", "twenty-four", "stole"]},
        {"entities": [9, 11, 15, 19], "gif": "mechanism_gears.gif", "sfx": "whoosh", "keywords": ["تاغ", "المصدر", "ملف إبداعاتك", "drops the receipt", "ego folder"]},
        {"entities": [20], "gif": "thumbs_up_like.gif", "sfx": "glint", "keywords": ["نهايتنا", "اللايك", "الاشتراك", "أمان الله", "wrap", "like and subscribe", "see you"]},
    ],
}

_EN_TO_AR_CONCEPTS: Dict[str, List[str]] = {
    "ganzfeld": ["غانزفيلد", "هلوسة", "الفراغ"],
    "ping": ["بينغ", "كرتي", "كرة"],
    "pong": ["بونغ", "كرتي", "كرة"],
    "eye": ["عين", "عيون", "عصابة"],
    "eyes": ["عين", "عيون", "تغطية"],
    "red": ["أحمر", "حمراء"],
    "light": ["ضوء", "كشاف", "مصباح", "مضيء"],
    "radio": ["راديو", "تسجيل", "موجات", "موجة"],
    "static": ["موجة", "تشويش", "تذبذب", "تسجيل"],
    "headphones": ["سماعات", "استلق"],
    "chair": ["كرسي", "مستلق"],
    "hallucinat": ["هلوسة", "شبحي", "يصرخ", "وجوه"],
    "ghost": ["شبحي", "أشباح", "عارض"],
    "ghosts": ["أشباح", "عارض"],
    "face": ["وجه", "وجوه", "ملامح"],
    "faces": ["وجوه", "وجه"],
    "metzger": ["عالم", "تسجيل", "1930"],
    "german": ["عالم", "تسجيل"],
    "psychologist": ["عالم", "باحث"],
    "blank": ["فارغ", "خالية", "شاشة"],
    "screen": ["إطار", "فارغ", "مضيء"],
    "pattern": ["أنماط", "عدسة", "بحث"],
    "patterns": ["أنماط", "عدسة", "بحث"],
    "brain": ["دماغ", "مخ", "رأس", "عقل"],
    "miner": ["منجم", "خوذة", "تعدين"],
    "miners": ["منجم", "خوذة", "تعدين"],
    "arctic": ["ثلوج", "مستكشف"],
    "snow": ["ثلوج", "مستكشف"],
    "projector": ["عارض", "بكرة"],
    "choice": ["اختيار", "بطاقتين"],
    "blindness": ["عمى", "قناع"],
    "swedish": ["سويدي", "باحث"],
    "johansson": ["سويدي", "باحث"],
    "card": ["بطاقتين", "استمارة", "لوحة"],
    "cards": ["بطاقتين", "صورتين"],
    "switch": ["يبدل", "تبديل", "تقلب"],
    "swap": ["يبدل", "تبديل", "تقلب"],
    "excuse": ["أعذار", "تبرير", "ميزان"],
    "mirror": ["مرآة"],
    "science": ["ساينس", "كتاب"],
    "pinocchio": ["بينوكيو", "أنف"],
    "blindfold": ["معصوب", "عصابة"],
    "nose": ["أنف", "أنفه"],
    "vibrat": ["اهتزاز", "جهاز"],
    "muscle": ["عضلة", "ذراع"],
    "arm": ["ذراع", "عضلة", "مرفق"],
    "bridge": ["جسر", "معلق"],
    "adrenaline": ["أدرينالين", "خوف"],
    "capilano": ["جسر", "باحث"],
    "woman": ["امرأة", "مراسلة", "استبيان"],
    "heart": ["قلب", "نبضات", "نار"],
    "clock": ["ساعة", "عقرب", "ثانية", "وقت"],
    "freeze": ["توقف", "جمود", "متوقفة"],
    "saccade": ["عين", "بؤبؤ", "حركة"],
    "jamais": ["غربة", "غريبة", "آلة كاتبة"],
    "word": ["كلمة", "باب", "حبر"],
    "repeat": ["تكرار", "يكرر", "33"],
    "car": ["سيارة", "مقود"],
    "switch off": ["مفتاح", "OFF"],
    "bank": ["بنك", "سطو"],
    "robbery": ["سطو", "ملثم"],
    "witness": ["شاهد", "مشتبه"],
    "lineup": ["صف", "مشتبهين"],
    "schooler": ["شولر", "باحث"],
    "describe": ["وصف", "استمارة", "دفتر"],
    "puzzle": ["أحجية"],
    "eras": ["يمحو", "ممحاة"],
    "cryptomnesia": ["سرقة", "كريبتومنيسيا", "اللاواعية"],
    "brainstorm": ["عصف", "اجتماع", "طاولة"],
    "shower": ["استحمام", "يستحم"],
    "source": ["مصدر", "ورقة"],
    "trophy": ["كأس", "صاحب"],
    "fingerprint": ["بصمة", "عدسة"],
    "cassette": ["كاسيت", "شريط"],
    "handshake": ["يتصافحان", "صديقين"],
}


_AR_SYNONYM_GROUPS: List[Tuple[str, ...]] = [
    ("منجم", "مناجم", "تعدين"),
    ("ثلج", "ثلوج", "متجمد", "قطب", "قطبي"),
    ("وجه", "وجوه", "ملامح"),
    ("صوت", "اصوات", "سماعات", "راديو", "تشويش"),
    ("نمط", "انماط"),
    ("هلس", "هلوسه", "هلوسة"),
    ("بدل", "يبدل", "تبديل", "متبدلتان", "تقلب"),
    ("بطاقه", "بطاقتين", "صوره", "صورتين"),
    ("انف", "انفه", "بينوكيو"),
    ("مغمض", "عصابه", "معصوب", "تغطيه"),
    ("اهتز", "اهتزاز", "جهاز"),
    ("جسر", "معلق"),
    ("خوف", "مخيف", "مذعور", "رعب", "قلق"),
    ("ساعه", "عقرب", "ثانيه", "ثواني"),
    ("توقف", "جمود", "متوقفه"),
    ("كلمه", "كلمات", "تكرار", "يكرر"),
    ("شاهد", "مشتبه", "مشتبهين", "جريمه", "سطو"),
    ("سرقه", "مسروق", "افكار", "فكره"),
    ("صديق", "صديقين", "زميل"),
]


def normalize_arabic(text: str) -> str:
    """Normalize Arabic diacritics & letter variants for reliable token matching."""
    t = _AR_DIACRITICS.sub("", (text or "").lower())
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    t = t.replace("ة", "ه").replace("ى", "ي")
    return t


def _strip_ar_affix(tok: str) -> str:
    for p in ("وال", "بال", "كال", "فال", "لل", "ال"):
        if len(tok) > len(p) + 2 and tok.startswith(p):
            return tok[len(p):]
    return tok


def _extract_tokens(text: str) -> List[str]:
    norm = normalize_arabic(text)
    raw_tokens = re.findall(r"[\w\u0600-\u06FF]+", norm)
    expanded: List[str] = []
    for tok in raw_tokens:
        st = _strip_ar_affix(tok)
        expanded.extend([tok, st])
        for grp in _AR_SYNONYM_GROUPS:
            norm_grp = [normalize_arabic(g) for g in grp]
            if any(g == tok or g == st or (len(g) >= 4 and g in st) or (len(st) >= 4 and st in g) for g in norm_grp):
                expanded.extend(norm_grp)
        for eng_k, ar_list in _EN_TO_AR_CONCEPTS.items():
            if eng_k in tok:
                for x in ar_list:
                    nx = normalize_arabic(x)
                    expanded.extend([nx, _strip_ar_affix(nx)])
    return expanded


def load_storyboard_catalog(
    section_id: str,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> Optional[Dict[str, Any]]:
    """Load catalog JSON (`01_ganzfeld.json`..`08_cryptomnesia.json`) for a given section."""
    m = re.search(r"(\d+)", str(section_id))
    if not m or not catalog_dir.is_dir():
        return None
    sec_prefix = f"{int(m.group(1)):02d}_"
    match = next(iter(sorted(catalog_dir.glob(f"{sec_prefix}*.json"))), None)
    if not match:
        return None
    return json.loads(match.read_text(encoding="utf-8"))


def classify_beat_mood(text: str, beat_idx: int, total_beats: int, prev_mood: Optional[str] = None) -> str:
    """Pick varied emotional background mood anchored to beat narrative meaning."""
    norm = normalize_arabic(text)
    if beat_idx == 0 and any(k in norm for k in ("تخيل", "اليوم", "مرحبا", "imagine", "suppose", "today")):
        return "warm_studio_paper"
    if any(k in norm for k in ("هلوسه", "مخيف", "اشباح", "وجوه واشكال", "صراخ", "جريمه", "سطو", "خطا", "صدمه", "غاضب", "رعب", "panic", "hallucinat", "scary", "ghost", "robbery", "wrong", "fear", "shock")):
        mood = "crimson_suspense"
    elif re.search(r"\b(?:19\d{2}|20\d{2})\b", norm) or any(k in norm for k in ("عالم النفس", "باحث", "دراسه", "تجربه", "psychologist", "researcher", "study", "experiment")):
        mood = "historical_amber"
    elif any(k in norm for k in ("الثلوج", "القطب", "المتجمد", "ساعه", "توقف", "زمن", "فراغ", "شاشه فاضيه", "arctic", "snow", "clock", "freeze", "blank screen", "mirror")):
        mood = "arctic_void"
    elif any(k in norm for k in ("دماغ", "مخك", "انماط", "تفسير", "سبب", "نتيجه", "%", "نسبه", "brain", "pattern", "reason", "percent", "cause")):
        mood = "neuro_obsidian"
    elif beat_idx == total_beats - 1:
        mood = "warm_studio_paper"
    else:
        mood = "neuro_obsidian"

    if prev_mood == mood and mood in ("neuro_obsidian", "crimson_suspense") and beat_idx % 2 == 1:
        mood = "warm_studio_paper" if mood == "neuro_obsidian" else "arctic_void"
    return mood


def _score_asset_beat(asset: Dict[str, Any], beat_tokens: List[str], b_idx: int, total_beats: int) -> float:
    desc = f"{asset.get('name_ar', '')} {asset.get('description_ar', '')}"
    a_tokens = set(_extract_tokens(desc))
    b_set = set(beat_tokens)
    overlap = a_tokens & b_set
    score = 0.0
    for tok in overlap:
        if len(tok) <= 2 and not tok.isdigit():
            continue
        # Years & numeric metrics carry extra strong semantic binding
        if tok.isdigit():
            score += 6.0
        elif len(tok) >= 4:
            score += 2.6
        else:
            score += 1.4

    role = asset.get("narrative_role", "")
    # Section identifier ("badge") belongs at intro or glitch-naming beat
    if role == "section_identifier":
        if b_idx == 0:
            score += 2.2
        if any(k in b_set for k in ("تاثير", "اسمه", "اسم", "effect", "called")):
            score += 4.5
    if role == "concept_explanation" and b_idx >= max(1, total_beats // 2):
        score += 1.2
    if role == "data_callout" and any(t.isdigit() for t in b_set):
        score += 2.0

    # Slight chronological soft tiebreaker matching natural row order (1..20 -> beat 0..N)
    expected_beat = (int(asset.get("index", 1)) - 1) * total_beats / 20.0
    score -= abs(expected_beat - b_idx) * 0.12
    return score


def _find_word_trigger_time(
    asset: Dict[str, Any],
    words: List[Dict[str, Any]],
    beat_start: float,
    beat_end: float,
) -> Optional[float]:
    """Find spoken word timestamp inside [beat_start, beat_end] that names this asset."""
    desc_tokens = set(_extract_tokens(f"{asset.get('name_ar', '')} {asset.get('description_ar', '')}"))
    desc_tokens = {t for t in desc_tokens if len(t) >= 3 or t.isdigit()}
    if not words or not desc_tokens:
        return None
    for w in words:
        wt = float(w.get("start", -1.0))
        if wt < beat_start - 0.1 or wt > beat_end - 0.4:
            continue
        w_toks = set(_extract_tokens(str(w.get("word", w.get("text", "")))))
        if w_toks & desc_tokens:
            return round(max(beat_start, wt - 0.08), 3)
    return None


_TRAILING_STOPWORDS = frozenset({
    "في", "على", "من", "إلى", "الى", "عن", "مع", "ب", "ل", "ك", "إن", "ان", "أن",
    "اللي", "الذي", "التي", "عشان", "لأن", "لان", "خلال", "عبر", "بين", "حول", "تحت",
    "فوق", "بعد", "قبل", "أو", "او", "و", "ثم", "حتى", "بس", "هنا", "هذا", "هذه",
    "يملا", "يملأ", "تعطي", "تعطيه", "يقول", "تقول", "يصير", "تقدر", "تخيل", "تعيش", "سرقة",
    "in", "on", "at", "to", "of", "for", "with", "and", "or", "the", "a", "an", "that", "which",
})

_AR_NUM_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _to_editorial_numerals(text: str, use_arabic_indic: bool = True) -> str:
    if not use_arabic_indic:
        return text
    return text.translate(_AR_NUM_DIGITS)


def synthesize_editorial_headline(
    text: str,
    catalog_items: Optional[List[Dict[str, Any]]] = None,
    intent: str = "concept_reveal",
) -> str:
    """Distill a spoken narration beat into a concise 2-6 word editorial headline (never raw mid-sentence truncation)."""
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if not raw:
        return "مشهد توضيحي"

    is_ar = any("\u0600" <= ch <= "\u06FF" for ch in raw)
    norm = normalize_arabic(raw)
    cats = catalog_items or []

    # 1. Explicit phenomenon naming ("اسمه ..." / "called ...")
    m_name_ar = re.search(r"(?:واسمه|اسمه|اسمها|تسمى|يسمى|called)\s+([^،,.!؟?\n]+)", raw, re.IGNORECASE)
    if m_name_ar:
        phenom = re.sub(r"[.!؟?]+$", "", m_name_ar.group(1).strip())
        # Check for glitch number prefix ("أول خلل", "ثاني خلل", "الخَلَل الثالث", ...)
        m_ord = re.search(r"(أول|ثاني|ثالث|رابع|خامس|سادس|سابع|ثامن|الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن)\s+خ[ًٌٍَُِْ]*ل[ًٌٍَُِْ]*ل|خ[ًٌٍَُِْ]*ل[ًٌٍَُِْ]*ل\s+(?:رقم\s*)?(الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن)", raw)
        if m_ord:
            ord_tok = next((g for g in m_ord.groups() if g), "")
            ord_map = {"الأول": "أول", "الثاني": "ثاني", "الثالث": "ثالث", "الرابع": "رابع", "الخامس": "خامس", "السادس": "سادس", "السابع": "سابع", "الثامن": "ثامن"}
            ord_clean = ord_map.get(ord_tok, ord_tok)
            cand = f"{ord_clean} خلل: {phenom}"
            if len(cand.split()) <= 7:
                return cand
        out_ph = " ".join(phenom.split()[:5])
        if not is_ar and out_ph:
            out_ph = out_ph[0].upper() + out_ph[1:]
        return out_ph

    # 2. Historical study anchor with year (19xx / 20xx)
    m_yr = re.search(r"\b(19\d{2}|20\d{2})\b", raw)
    if m_yr:
        yr = m_yr.group(1)
        yr_disp = _to_editorial_numerals(yr) if is_ar else yr
        # Prefer action clause from narration after the year if concise & descriptive
        after_yr = raw.split(yr, 1)[1].strip(" ،,.:؛-")
        if after_yr:
            sub = synthesize_editorial_headline(after_yr, None, intent)
            sub_words = sub.split()
            if not is_ar and len(sub_words) > 5:
                sub = " ".join(sub_words[:5])
                sub_words = sub.split()
            if sub and 2 <= len(sub_words) <= 5 and normalize_arabic(sub_words[-1].rstrip("،,.!؟?:")) not in _TRAILING_STOPWORDS:
                return f"{yr_disp} — {sub}"
        # Fallback to matched catalog item name cleanly stripped of year & dangling 'و'
        for ca in cats:
            cname = str((ca.get("name_en") if not is_ar else ca.get("name_ar")) or "").strip()
            if not cname or (not is_ar and any("\u0600" <= ch <= "\u06FF" for ch in cname)):
                continue
            if ca.get("narrative_role") in ("research_context", "data_callout") and len(cname.split()) <= 6:
                clean_c = re.sub(rf"(?:و?\s*(?:سنة|عام)\s*)?\b{yr}\b", "", cname).strip(" —-و،")
                if clean_c and len(clean_c.split()) >= 2:
                    out_c = " ".join(clean_c.split()[:4])
                    return f"{yr_disp} — {out_c[0].upper() + out_c[1:] if not is_ar else out_c}"
        return f"تجربة {yr_disp}" if is_ar else f"{yr_disp} — Lab Experiment"

    # 3. Rhetorical question + result ("النتيجة؟ ..." / "ليش؟ ...")
    if "؟" in raw or "?" in raw:
        sep = "؟" if "؟" in raw else "?"
        q_part, _, rest = raw.partition(sep)
        q_words = q_part.strip().split()
        if 1 <= len(q_words) <= 3:
            if rest.strip():
                rest_hl = synthesize_editorial_headline(rest, cats, intent)
                rest_words = rest_hl.split()
                max_rest = max(2, 6 - len(q_words))
                if len(rest_words) > max_rest:
                    trimmed = rest_words[:max_rest]
                    while len(trimmed) > 2 and normalize_arabic(trimmed[-1].rstrip("،,.!؟?:")) in _TRAILING_STOPWORDS:
                        trimmed.pop()
                    rest_hl = " ".join(trimmed)
                return f"{q_part.strip()}{sep} {rest_hl}"
            return f"{q_part.strip()}{sep}"

    # 4. Short punchy sentence or multi-clause distillation
    stripped = re.sub(r"^(?:أما|بس|وهذا بالضبط سبب إن|السبب إن|اللي ما تدري عنه إن|هنا|تخيل(?: لو)?|أو|فجأة)\s+", "", raw).strip()
    stripped = re.sub(r"^(?:لما|عندما|تجيب|تقدر)\s+", "", stripped).strip()
    clauses = [c.strip() for c in re.split(r"[،,!.\n]+", stripped) if len(c.strip().split()) >= 2]
    chosen = clauses[0] if clauses else stripped
    if not is_ar and len(clauses) >= 2 and len(chosen.split()) <= 2:
        chosen = clauses[1]
    # Prefer a consequence/punchline clause when the sentence has a cause/action turnaround
    if len(clauses) >= 2:
        tail = clauses[-1]
        m_turn = re.search(r"(?:ويبدأ|يبدأ|فيخترع|عشان|ليملأ|والنتيجة|فتبدأ)\s+(.+)", tail)
        if m_turn and len(m_turn.group(1).split()) >= 2:
            chosen = m_turn.group(1).strip()
        elif len(tail.split()) <= 6 and any(k in normalize_arabic(tail) for k in ("يملا", "فراغ", "يطول", "يلحق", "تنس", "تستبدل", "عكس", "هلوس", "اشباح", "أشباح", "اعذار", "أعذار", "وهم", "خريط")):
            chosen = tail
    chosen = re.sub(r"^(?:إن|أن|وإن|لأن|عشان|على إنه|إنها|تجيب|تقدر|تبدأ|يعني|إنك كنت|أنت حرفياً قاعد|حرفياً قاعد|قاعد)\s+", "", chosen).strip()
    chosen = re.sub(r"^(?:إنك كنت|أنت حرفياً قاعد|حرفياً قاعد|قاعد)\s+", "", chosen).strip()
    chosen = re.sub(r"\s+عشان\s+", " لـ", chosen)
    chosen = re.sub(r"\s+لـ(ي|ت|ن|أ)", r" ل\1", chosen)
    if not is_ar:
        chosen = re.sub(r"^(?:now\s+let'?s\s+move\s+to|moving\s+on\s+to|next\s+up\s+is|here'?s\s+the\s+catch|that'?s\s+why|that'?s\s+the\s+exact\s+reason|imagine|picture|within\s+(?:minutes|a\s+single\s+minute))\s+", "", chosen, flags=re.IGNORECASE).strip()
        chosen = re.sub(r"(\d+)\s+percent\b", r"\1%", chosen, flags=re.IGNORECASE)

    words = chosen.split()
    if len(words) > 6:
        # Preserve complete final object if only 7 words and last word completes a verb
        if len(words) == 7 and normalize_arabic(words[5]) in _TRAILING_STOPWORDS:
            words = words[:7]
        else:
            words = words[:6]
    while len(words) > 2 and normalize_arabic(words[-1].rstrip("،,.!؟?:")) in _TRAILING_STOPWORDS:
        words.pop()
    res = " ".join(words).strip(" ،,:-")
    if not is_ar and res:
        res = res[0].upper() + res[1:]
    return res if res else " ".join(raw.split()[:5])


def _is_flat_bottom_crop(png_path: Optional[Path]) -> bool:
    """Detect flat horizontal bottom cuts inside the opaque bounding box (handles padded PNG margins)."""
    if not png_path or not png_path.is_file():
        return False
    try:
        import numpy as np
        from PIL import Image
        with Image.open(png_path) as im:
            alpha = np.array(im.convert("RGBA"))[:, :, 3] > 25
        ys, xs = np.where(alpha)
        if len(ys) == 0:
            return False
        y_max = int(ys.max())
        x_min, x_max = int(xs.min()), int(xs.max())
        bw = max(1, x_max - x_min + 1)
        if bw < 40 or y_max < 30:
            return False
        # Check bottom 5 rows of the actual drawn object (not transparent padding)
        band = alpha[max(0, y_max - 5):y_max + 1, x_min:x_max + 1]
        cols_hit = np.any(band, axis=0)
        frac = float(np.sum(cols_hit)) / float(bw)
        return frac >= 0.56
    except Exception:
        return _detect_cropped_bottom(png_path)


def _choose_asset_fx_profile(
    asset: Dict[str, Any],
    is_light_bg: bool,
    *,
    png_path: Optional[Path] = None,
    is_dark_card_mood: bool = False,
) -> Dict[str, Any]:
    """Select restrained, semantically justified EffectCraft effects (no blanket VFX/drop_shadow spam)."""
    text = normalize_arabic(f"{asset.get('name_ar', '')} {asset.get('description_ar', '')}")
    role = asset.get("narrative_role", "illustrative_prop")
    cropped_bottom = _is_flat_bottom_crop(png_path)
    # Cutout props (goggles, magnifying lens, blank frame, floating symbols) stay borderless; flat-base/human plates use cards
    is_cutout_prop = any(k in text for k in (
        "بينغ بونغ", "كشاف", "عدسه", "مكبره", "اطار مضيء", "جهاز اهتزاز", "شارة", "شاره", "بروجيكتور", "عارض اشباح",
        "spotlight", "magnifier", "blank screen", "vibrat", "badge", "projector", "hourglass", "eye rewind", "molecule",
    ))
    has_ground_base = any(k in text for k in ("خوذه", "مستكشف", "ثلوج", "miners helmet", "snow explorer"))
    needs_card = (not is_cutout_prop) and bool(cropped_bottom or has_ground_base or role in ("research_context", "human_example"))

    profile: Dict[str, Any] = {
        # Cards carry their own crisp baked shadow; only floating cutouts use light subtle shadow when helpful
        "drop_shadow": (not needs_card) and role not in ("section_identifier",),
        "mask_reveal": False,
        "fx": [],
        "card_wrap": needs_card,
        "sfx": "pop",
    }

    if role == "section_identifier":
        profile["fx"].append({"type": "Light Sweep", "intensity": 28.0, "width": 46.0, "delay": 0.65})
        profile["sfx"] = "card_snap"
    elif any(k in text for k in ("كشاف", "مصباح", "متوهج", "شعاع", "تنبثق منه", "تنبعث منه", "عارض اشباح", "spotlight", "projector", "lightbulb")):
        # Luminous props get restrained Glow ONLY on dark stages (AGENTS.md guard on bright BGs)
        if not is_light_bg:
            profile["fx"].append({"type": "glow", "intensity": 0.72, "radius": 24.0})
        else:
            profile["fx"].append({"type": "Light Sweep", "intensity": 24.0, "delay": 0.65})
        profile["sfx"] = "glint"
    elif any(k in text for k in ("راديو", "موجات صوتيه", "جهاز اهتزاز", "انذار")):
        profile["fx"].append({"type": "radio_waves", "color": "#38BDF8", "frequency": 1.6, "expansion": 140.0})
        profile["sfx"] = "whoosh"
    elif any(k in text for k in ("دوامه", "ذائب", "يمحو", "يتلاشى")):
        profile["fx"].append({"type": "distortion", "amount": 26.0})
        profile["sfx"] = "suspense_riser"
    elif any(k in text for k in ("اطار مضيء فارغ", "شاشه فاضيه", "مساحه بيضاء خاليه")) and role != "human_example":
        profile["mask_reveal"] = True
        profile["sfx"] = "soft_fade"
    elif role == "data_callout":
        profile["fx"].append({"type": "Light Sweep", "intensity": 26.0, "delay": 0.60})
        profile["sfx"] = "card_snap"
    elif role == "research_context":
        profile["sfx"] = "pop"
    return profile


def _merge_short_beats(raw_beats: List[Dict[str, Any]], min_dur: float = 2.0) -> List[Dict[str, Any]]:
    """Merge ultra-short rhetorical beats (<2.0s) into following/preceding beat to avoid flash cuts."""
    if len(raw_beats) <= 1:
        return list(raw_beats)
    merged: List[Dict[str, Any]] = []
    carry_prefix: Optional[Dict[str, Any]] = None
    for b in raw_beats:
        cur = dict(b)
        if carry_prefix is not None:
            cur["start"] = float(carry_prefix["start"])
            cur["text"] = f"{carry_prefix.get('text', '')} {cur.get('text', '')}".strip()
            carry_prefix = None
        if (float(cur.get("end", 0.0)) - float(cur.get("start", 0.0))) < min_dur:
            carry_prefix = cur
        else:
            merged.append(cur)
    if carry_prefix is not None:
        if merged:
            merged[-1]["end"] = float(carry_prefix["end"])
            merged[-1]["text"] = f"{merged[-1].get('text', '')} {carry_prefix.get('text', '')}".strip()
        else:
            merged.append(carry_prefix)
    return merged


def _pick_beat_icon_and_sfx(text: str, curated_entry: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """Select verified animated GIF icon filename & synchronized studio SFX stem for a beat."""
    if curated_entry:
        return str(curated_entry.get("gif", "idea_bulb.gif")), str(curated_entry.get("sfx", "pop"))
    norm = normalize_arabic(text)
    if any(k in norm for k in ("قلب", "نبض", "ادرينالين", "heart", "adrenaline")):
        return "heart_monitor.gif", "heartbeat"
    if any(k in norm for k in ("ساعه", "ثانيه", "دقيقه", "توقف", "clock", "second", "freeze")):
        return "ticking_clock.gif", "card_snap"
    if any(k in norm for k in ("هلوسه", "خوف", "خطر", "سطو", "verdict", "panic", "warning", "robbery")):
        return "warning_beacon.gif", "suspense_riser"
    if any(k in norm for k in ("بحث", "تجربه", "عالم", "دراسه", "research", "study", "experiment")):
        return "research_magnifier.gif", "pop"
    if any(k in norm for k in ("عين", "عيون", "صوره", "مرآه", "eye", "face", "mirror")):
        return "optical_vision.gif", "whoosh"
    return "idea_bulb.gif", "glint"


def _is_major_scene_pivot(text: str) -> bool:
    norm = normalize_arabic(text)
    return bool(
        re.search(r"\b(?:19\d{2}|20\d{2})\b", norm)
        or any(k in norm for k in (
            "اسمه", "النتيجه", "العكس", "السبب", "ليش", "وهذا بالضبط", "المفاجاه",
            "خلال دقيقه", "في النهايه", "الخلاصه", "result", "because", "opposite", "why",
        ))
    )


def _infer_composition_mode(scene_text: str, assets: List[Dict[str, Any]], intent: str) -> str:
    """Choose visual staging mode from narrative semantics & element roles (not fixed templates)."""
    norm = normalize_arabic(scene_text)
    n = len(assets)
    if any(k in norm for k in ("المناجم", "القطب", "مقابل", "عكس", "بينما", "ثابت وامن", "فشلت", "مجموعه", "compare", "versus", "unlike")):
        if n >= 2:
            return "split_polarity"
    if any(k in norm for k in ("السبب", "يرسم", "تنبني", "تضارب", "يخدع العقل", "يعالج", "آليه", "اليه", "تفسير", "مخطط", "pattern", "signal", "process", "because")):
        if n >= 2:
            return "living_diagram"
    if n == 1:
        return "spotlight_focus"
    if n == 2:
        return "hero_solo_then_shift"
    if n == 3:
        return "evidence_trio"
    return "staged_sequence"


def group_beats_into_scenes(
    beat_plans: List[Dict[str, Any]],
    total_duration: float,
) -> List[Dict[str, Any]]:
    """Group micro-beats into cohesive editorial scenes (typically 4-7 per ~50s section) without rigid rules."""
    if not beat_plans:
        return []

    raw_groups: List[List[Dict[str, Any]]] = [[beat_plans[0]]]
    for bp in beat_plans[1:]:
        prev_grp = raw_groups[-1]
        prev_start = float(prev_grp[0]["beat"]["start"])
        cur_beat = bp["beat"]
        cur_dur = float(cur_beat["end"]) - float(cur_beat["start"])
        prev_dur = float(prev_grp[-1]["beat"]["end"]) - prev_start
        cur_items = len(bp.get("items", []))
        prev_items = sum(len(x.get("items", [])) for x in prev_grp)
        cur_text = str(cur_beat.get("text", ""))

        # Merge short follow-up beats into same scene if they continue the setup/argument and don't crowd assets
        can_merge = (
            (cur_dur < 4.3 or prev_dur < 3.6)
            and (prev_dur + cur_dur <= 14.5)
            and (prev_items + cur_items <= 4)
            and not _is_major_scene_pivot(cur_text)
        )
        # Avoid merging too aggressively if total scene count would become < 4 on a long section
        if can_merge and (len(raw_groups) + (len(beat_plans) - beat_plans.index(bp) - 1) >= 4 or total_duration < 30.0):
            prev_grp.append(bp)
        else:
            raw_groups.append([bp])

    # Balance mood contrast across consecutive scenes (warm light vs rich dark moods)
    scenes_out: List[Dict[str, Any]] = []
    prev_scene_mood: Optional[str] = None
    for s_idx, grp in enumerate(raw_groups):
        st = float(grp[0]["beat"]["start"])
        en = float(grp[-1]["beat"]["end"])
        combined_text = " ".join(str(x["beat"].get("text", "")) for x in grp)
        all_items = [it for x in grp for it in x.get("items", [])]

        # Re-evaluate scene-level mood and enforce light/dark variety so scenes breathe visually
        mood_key = classify_beat_mood(combined_text, s_idx, len(raw_groups), prev_mood=prev_scene_mood)
        if prev_scene_mood == mood_key and len(raw_groups) >= 3:
            is_prev_light = STAGE_MOODS[prev_scene_mood]["is_light_bg"]
            mood_key = "neuro_obsidian" if is_prev_light else "warm_studio_paper"
        prev_scene_mood = mood_key
        mood_cfg = STAGE_MOODS[mood_key]

        comp_mode = _infer_composition_mode(combined_text, all_items, intent=grp[0].get("intent", "concept_reveal"))
        scene_hl = grp[0].get("editorial_headline") or synthesize_editorial_headline(
            str(grp[0]["beat"].get("text", "")),
            [it["catalog_meta"] for it in grp[0].get("items", [])],
        )

        # Pick scene-level continuity behavior
        continuity = "mood_shift_reset" if s_idx > 0 else "cold_open"
        if comp_mode in ("living_diagram", "split_polarity"):
            continuity = "analytical_focus"

        scenes_out.append({
            "scene_index": s_idx,
            "scene_id": f"sc_{s_idx + 1:02d}",
            "start": round(st, 3),
            "end": round(en, 3),
            "mood_key": mood_key,
            "mood": mood_cfg,
            "composition_mode": comp_mode,
            "continuity": continuity,
            "headline": scene_hl,
            "sub_beats": grp,
        })
    return scenes_out


def plan_semantic_section_allocation(
    *,
    section_id: str,
    beats: List[Dict[str, Any]],
    input_assets: List[Dict[str, Any]],
    words: Optional[List[Dict[str, Any]]] = None,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> Dict[str, Any]:
    """Match 100% of extracted PNGs against semantic catalog + editorial scene choreography + word triggers."""
    catalog = load_storyboard_catalog(section_id, catalog_dir=catalog_dir)
    beats = _merge_short_beats(beats, min_dur=2.0)
    n_beats = max(1, len(beats))
    beat_token_lists = [_extract_tokens(str(b.get("text", ""))) for b in beats]

    # Map entity_XX path by index 1..20
    by_index: Dict[int, Dict[str, Any]] = {}
    for idx_pos, a in enumerate(input_assets):
        m = re.search(r"(\d+)", str(a.get("id", "")))
        ent_idx = int(m.group(1)) if m else (idx_pos + 1)
        by_index[ent_idx] = a

    catalog_assets = list((catalog or {}).get("assets", []))
    cat_by_idx: Dict[int, Dict[str, Any]] = {int(c["index"]): c for c in catalog_assets if "index" in c}
    if not catalog_assets:
        for ent_idx, a in sorted(by_index.items()):
            entry = {
                "index": ent_idx,
                "name_ar": a.get("id", f"entity_{ent_idx:02d}"),
                "description_ar": "",
                "narrative_role": "illustrative_prop",
            }
            catalog_assets.append(entry)
            cat_by_idx[ent_idx] = entry

    sb_id = str((catalog or {}).get("storyboard_id", ""))
    curated_list = CURATED_STORYBOARD_BEATS.get(sb_id)
    assignments: List[List[Dict[str, Any]]] = [[] for _ in range(n_beats)]
    curated_meta_per_beat: List[Optional[Dict[str, Any]]] = [None for _ in range(n_beats)]

    if curated_list and len(by_index) >= 16:
        if n_beats == len(curated_list):
            for b_idx, cbeat in enumerate(curated_list):
                curated_meta_per_beat[b_idx] = cbeat
                for eidx in cbeat["entities"]:
                    if eidx in by_index and eidx in cat_by_idx:
                        assignments[b_idx].append(cat_by_idx[eidx])
        else:
            n_c = len(curated_list)
            for k, cbeat in enumerate(curated_list):
                kw_norms = [normalize_arabic(kw) for kw in cbeat.get("keywords", [])]
                best_b = min(
                    range(n_beats),
                    key=lambda bi: (
                        abs((bi / max(1, n_beats - 1)) - (k / max(1, n_c - 1))) * 3.0
                        - sum(2.5 for kw in kw_norms if kw and kw in normalize_arabic(str(beats[bi].get("text", ""))))
                        + len(assignments[bi]) * 0.45
                    ),
                )
                if curated_meta_per_beat[best_b] is None:
                    curated_meta_per_beat[best_b] = cbeat
                for eidx in cbeat["entities"]:
                    if eidx in by_index and eidx in cat_by_idx:
                        assignments[best_b].append(cat_by_idx[eidx])
            for empty_b in range(n_beats):
                if not assignments[empty_b]:
                    donor_b = max(range(n_beats), key=lambda bi: len(assignments[bi]))
                    if len(assignments[donor_b]) > 1:
                        assignments[empty_b].append(assignments[donor_b].pop(-1))
    else:
        max_per_beat = max(2, min(4, (len(catalog_assets) + n_beats - 1) // n_beats + 1))
        scored_pairs: List[Tuple[float, int, Dict[str, Any]]] = []
        for cat_a in catalog_assets:
            ent_idx = int(cat_a.get("index", 1))
            if ent_idx not in by_index:
                continue
            best_b = 0
            best_s = -1e9
            for b_idx in range(n_beats):
                s = _score_asset_beat(cat_a, beat_token_lists[b_idx], b_idx, n_beats)
                if s > best_s:
                    best_s = s
                    best_b = b_idx
            scored_pairs.append((best_s, best_b, cat_a))

        scored_pairs.sort(key=lambda x: x[0], reverse=True)
        for best_s, best_b, cat_a in scored_pairs:
            if len(assignments[best_b]) < max_per_beat:
                assignments[best_b].append(cat_a)
            else:
                cand_b = min(
                    range(n_beats),
                    key=lambda bi: (len(assignments[bi]), -_score_asset_beat(cat_a, beat_token_lists[bi], bi, n_beats)),
                )
                assignments[cand_b].append(cat_a)

        if len(scored_pairs) >= n_beats:
            for empty_b in range(n_beats):
                if not assignments[empty_b]:
                    donor_b = max(range(n_beats), key=lambda bi: len(assignments[bi]))
                    if len(assignments[donor_b]) > 1:
                        pick = max(
                            assignments[donor_b],
                            key=lambda ca: _score_asset_beat(ca, beat_token_lists[empty_b], empty_b, n_beats),
                        )
                        assignments[donor_b].remove(pick)
                        assignments[empty_b].append(pick)

    beat_moods: List[str] = []
    prev_m: Optional[str] = None
    for b_idx, b in enumerate(beats):
        m = classify_beat_mood(str(b.get("text", "")), b_idx, n_beats, prev_mood=prev_m)
        beat_moods.append(m)
        prev_m = m

    beat_plans: List[Dict[str, Any]] = []
    light_sweep_budget = 2
    for b_idx, b in enumerate(beats):
        st = float(b.get("start", 0.0))
        en = float(b.get("end", st + 4.0))
        dur_b = max(0.8, en - st)
        mood_key = beat_moods[b_idx]
        mood_cfg = STAGE_MOODS[mood_key]
        beat_items = assignments[b_idx]
        gif_name, beat_sfx = _pick_beat_icon_and_sfx(str(b.get("text", "")), curated_meta_per_beat[b_idx])
        ed_headline = synthesize_editorial_headline(str(b.get("text", "")), beat_items)

        enriched_items: List[Dict[str, Any]] = []
        for rank, cat_a in enumerate(beat_items):
            ent_idx = int(cat_a["index"])
            src_asset = by_index[ent_idx]
            raw_p = Path(str(src_asset.get("path", ""))) if src_asset.get("path") else None
            if rank == 0:
                in_t = round(st + 0.08, 3)
                trig = None
            else:
                trig = _find_word_trigger_time(cat_a, words or [], st + 0.35, max(st + 0.45, en - 1.35))
                stagger_t = round(st + min(rank * 1.15, dur_b * 0.48), 3)
                in_t = trig if trig is not None else stagger_t
                in_t = min(in_t, max(st + 0.25, en - 1.25))
            fx_prof = _choose_asset_fx_profile(cat_a, bool(mood_cfg["is_light_bg"]), png_path=raw_p)
            # Enforce section-level Light Sweep restraint (max 2 per section)
            kept_fx = []
            for fx_e in fx_prof["fx"]:
                if fx_e.get("type") == "Light Sweep":
                    if light_sweep_budget > 0:
                        light_sweep_budget -= 1
                        kept_fx.append(fx_e)
                else:
                    kept_fx.append(fx_e)
            fx_prof["fx"] = kept_fx

            enriched_items.append({
                "entity_index": ent_idx,
                "src_asset": src_asset,
                "catalog_meta": cat_a,
                "in_time": round(max(st, in_t), 3),
                "out_time": round(en, 3),
                "word_triggered": trig is not None,
                "fx_profile": fx_prof,
            })

        beat_plans.append({
            "beat_index": b_idx,
            "beat": b,
            "mood_key": mood_key,
            "mood": mood_cfg,
            "gif_icon": gif_name,
            "beat_sfx": beat_sfx,
            "editorial_headline": ed_headline,
            "items": enriched_items,
        })

    total_dur = max([float(b.get("end", 0.0)) for b in beats] + [0.0])
    scene_groups = group_beats_into_scenes(beat_plans, total_dur)

    return {
        "catalog_title": (catalog or {}).get("title_ar", section_id),
        "catalog_used": catalog is not None,
        "beat_plans": beat_plans,
        "scene_groups": scene_groups,
    }

"""AION Typography Director (Phase 6 — Typography Integration V6.1).

Deterministic, story-driven font pairing and kinetic typography planner that operates
strictly from project metadata, storyboard/semantic JSON, narration script, and voice timing
— never re-reading storyboard images and never converting spoken subtitles into chaotic
word-by-word captions.

Core Enforcements:
  - Cohesive 2-font system per video (1 primary + 1 display, plus documented fallback).
  - Never uses commercial fonts marked `LICENSE_REQUIRED` (automatically falls back cleanly).
  - Validates Arabic RTL, Tashkeel, mixed AR/EN & digit glyph coverage before locking a font.
  - Adapts typography hierarchy, sizing, wrapping box & safe margins across `16:9` and `9:16`.
  - Assigns purposeful kinetic roles (`impact_title`, `editorial_headline`, `mask_reveal`,
    `word_emphasis`, `documentary_card`, `data_callout`) aligned to Gold clarity.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.aion.kinetic_typography import is_rtl_str
from core.aion.typography_registry import COMMERCIAL_LICENSE_REQUIRED, load_font_registry
from core.config.settings import TYPOGRAPHY_SETTINGS_PATH

_AR_DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "max_families_per_video": 2,
    "story_pairings": {
        "psychological_cinematic": {"primary": "Cairo", "display": "Alyamama", "fallback": "Alexandria", "min_headline_duration_sec": 1.8},
        "historical_documentary": {"primary": "IBM Plex Sans Arabic", "display": "Amiri", "fallback": "Cairo", "min_headline_duration_sec": 2.2},
        "shorts_viral_9x16": {"primary": "Alexandria", "display": "Changa", "fallback": "Cairo", "min_headline_duration_sec": 1.6},
        "scientific_explanation": {"primary": "Cairo", "display": "Readex Pro", "fallback": "IBM Plex Sans Arabic", "min_headline_duration_sec": 1.8},
        "english_editorial": {"primary": "Inter", "display": "Funnel Display", "fallback": "Space Grotesk", "min_headline_duration_sec": 1.8},
    },
}

_HIST_KWS = ("تاريخ", "حرب", "معركة", "وثائقي", "أرشيف", "عام ", "تجربة", "مختبر", "جامعة", "قرن", "محارب", "قائد", "جوناثان", "1990", "1988", "2001", "١٩٨٨", "١٩٩٠", "٢٠٠١")
_PSYCH_KWS = ("وهم", "عقل", "مخك", "إدراك", "خلل", "نفس", "ذاكرة", "بينوكيو", "تظليل", "توقع", "حقيقة", "واقع", "غوريلا", "بقعة", "اهتزاز")
_PIVOT_WORDS = (
    "وهم", "بينوكيو", "الحرامي", "المجرم", "كذبة", "تركيب", "يتوقع", "خريطة", "تخيل", "حقيقة", "خطأ", "خدعة", "فراغ", "الزمن", "تنسى", "اختبار",
    "hallucinating", "illusion", "swapped", "freeze", "stretching", "contradictions", "overwrites", "erase", "blind", "panic", "romantic", "alien", "plagiarism", "ghosts", "void", "lie",
)


def _load_settings() -> Dict[str, Any]:
    if TYPOGRAPHY_SETTINGS_PATH.is_file():
        try:
            return json.loads(TYPOGRAPHY_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_SETTINGS


def _registry_map(registry: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    reg = registry if registry is not None else load_font_registry()
    return {f["family"]: f for f in reg.get("families", []) if isinstance(f, dict) and f.get("family")}


def infer_story_genre(
    *,
    story_genre: str = "auto",
    aspect_ratio: str = "16:9",
    language: str = "ar",
    script_text: str = "",
    style_mode: str = "auto",
) -> str:
    """Choose a coherent story typography genre cleanly from metadata, aspect & script."""
    sg = str(story_genre or "auto").strip().lower()
    if sg in DEFAULT_SETTINGS["story_pairings"]:
        return sg
    if aspect_ratio.strip() == "9:16":
        return "shorts_viral_9x16"
    if str(language).lower().startswith("en") or (script_text and not is_rtl_str(script_text)):
        return "english_editorial"
    txt = str(script_text or "")
    hist_hits = sum(1 for k in _HIST_KWS if k in txt)
    psych_hits = sum(1 for k in _PSYCH_KWS if k in txt)
    if style_mode == "historical_documentary" or (hist_hits >= 3 and hist_hits > psych_hits):
        return "historical_documentary"
    if psych_hits >= 1 or style_mode in ("cinematic_2_5d", "editorial_motion_graphics"):
        return "psychological_cinematic"
    if style_mode == "scientific_explanation":
        return "scientific_explanation"
    return "psychological_cinematic"


def resolve_font_for_text(
    text: str,
    requested_font: str,
    *,
    fallback_chain: Optional[List[str]] = None,
    reg_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[str, str, Optional[str]]:
    """Validate `requested_font` against license, EffectCraft availability & script glyph coverage."""
    rmap = reg_map if reg_map is not None else _registry_map()
    has_ar = is_rtl_str(text)
    has_latin_or_ascii = bool(re.search(r"[A-Za-z0-9]", text or ""))
    has_tashkeel = bool(_AR_DIACRITICS_RE.search(text or ""))

    chain = [requested_font] + list(fallback_chain or []) + (["Cairo", "Alexandria", "IBM Plex Sans Arabic"] if has_ar else ["Inter", "Funnel Display"])
    reason: Optional[str] = None

    for cand in chain:
        if not cand:
            continue
        info = rmap.get(cand)
        if cand in COMMERCIAL_LICENSE_REQUIRED or (info and info.get("status") == "LICENSE_REQUIRED"):
            if cand == requested_font:
                fb = (info or {}).get("fallback") or COMMERCIAL_LICENSE_REQUIRED.get(cand, {}).get("fallback", "Cairo")
                reason = f"'{cand}' is LICENSE_REQUIRED; substituted open fallback '{fb}'"
                if fb not in chain:
                    chain.append(fb)
            continue
        if not info:
            continue
        if not info.get("verified_in_effectcraft") or info.get("status") == "FAIL":
            if cand == requested_font:
                reason = f"'{cand}' unverified or FAILED render check; falling back"
            continue
        cov = info.get("language_script_coverage", {})
        if has_ar and not cov.get("arabic", False):
            if cand == requested_font:
                reason = f"'{cand}' lacks Arabic script coverage; falling back"
            continue
        if has_latin_or_ascii and not cov.get("latin", False):
            if cand == requested_font:
                reason = f"'{cand}' ({info.get('status')}) lacks ASCII digits/Latin; falling back"
            continue
        if has_tashkeel and cand == "Lalezar":
            if cand == requested_font:
                reason = "'Lalezar' compresses heavy Tashkeel vertically; falling back"
            continue

        # Pick valid installed weight/style name for EffectCraft
        avail_styles = list((info.get("style") or {}).get("styles_available") or ["Regular"])
        chosen_style = "Bold" if "Bold" in avail_styles else ("SemiBold" if "SemiBold" in avail_styles else avail_styles[0])
        return cand, chosen_style, reason

    # Ultimate deterministic safe defaults
    return ("Cairo" if has_ar else "Inter"), "Bold", reason or "Fallback to baseline safe studio font"


def resolve_style_variant(font_family: str, desired_style: str, reg_map: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    """Map desired weight (`ExtraBold`, `Bold`, `SemiBold`, `Regular`) to a style present in EffectCraft."""
    rmap = reg_map if reg_map is not None else _registry_map()
    info = rmap.get(font_family, {})
    avail = list((info.get("style") or {}).get("styles_available") or [])
    if not avail:
        return "Bold" if desired_style != "Regular" else "Regular"
    if desired_style in avail:
        return desired_style
    order = {
        "Black": ["Black", "ExtraBold", "Bold", "SemiBold", "Regular"],
        "ExtraBold": ["ExtraBold", "Black", "Bold", "SemiBold", "Regular"],
        "Bold": ["Bold", "SemiBold", "ExtraBold", "Regular"],
        "SemiBold": ["SemiBold", "Bold", "Medium", "Regular"],
        "Regular": ["Regular", "Medium", "Bold"],
    }
    for cand in order.get(desired_style, ["Bold", "Regular"]):
        if cand in avail:
            return cand
    return avail[0]


def select_project_typography_system(
    *,
    story_genre: str = "auto",
    aspect_ratio: str = "16:9",
    language: str = "ar",
    script_text: str = "",
    style_mode: str = "auto",
    registry: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Select the cohesive 2-font system (`primary` + `display`) + safe fallback for an entire video."""
    settings = _load_settings()
    rmap = _registry_map(registry)
    resolved_genre = infer_story_genre(
        story_genre=story_genre,
        aspect_ratio=aspect_ratio,
        language=language,
        script_text=script_text,
        style_mode=style_mode,
    )
    pair = dict(settings.get("story_pairings", {}).get(resolved_genre, DEFAULT_SETTINGS["story_pairings"]["psychological_cinematic"]))

    probe_sample = script_text[:120] if script_text else ("\u062a\u062c\u0631\u0628\u0629 AION 1988" if not str(language).startswith("en") else "AION Studio 1988")
    primary, primary_style, p_note = resolve_font_for_text(probe_sample, pair.get("primary", "Cairo"), fallback_chain=[pair.get("fallback", "Cairo")], reg_map=rmap)
    display_cand = pair.get("display", primary)
    display, display_style, d_note = resolve_font_for_text(
        "\u0648\u0647\u0645 \u0628\u064a\u0646\u0648\u0643\u064a\u0648 \u0661\u0669\u0668\u0668" if not str(language).startswith("en") else "AION",
        display_cand,
        fallback_chain=[primary, pair.get("fallback", "Cairo")],
        reg_map=rmap,
    )

    return {
        "story_genre": resolved_genre,
        "aspect_ratio": aspect_ratio,
        "primary": primary,
        "primary_style": primary_style,
        "display": display,
        "display_style": resolve_style_variant(display, "ExtraBold" if aspect_ratio == "9:16" else display_style, rmap),
        "fallback": pair.get("fallback", "Cairo"),
        "max_families": int(settings.get("max_families_per_video", 2)),
        "min_headline_duration_sec": float(pair.get("min_headline_duration_sec", 1.8)),
        "notes": [n for n in (p_note, d_note) if n],
    }


def _find_highlight_word(text: str) -> Optional[str]:
    words = text.split()
    if len(words) < 3:
        return None
    for kw in _PIVOT_WORDS:
        for w in words:
            clean = re.sub(r"[،,.!؟?:()\"']", "", w)
            if kw in clean.lower() and len(clean) >= 3:
                return clean
    # Fallback: longest word in the second half (not first preposition)
    cands = [re.sub(r"[،,.!؟?:()\"']", "", w) for w in words[1:]]
    cands = [c for c in cands if len(_AR_DIACRITICS_RE.sub("", c)) >= 4]
    return max(cands, key=len) if cands else None


def plan_headline_treatment(
    *,
    text: str,
    beat_index: int,
    scene_index: int,
    t_start: float,
    t_end: float,
    mood: Dict[str, Any],
    mood_key: str,
    typing_system: Dict[str, Any],
    comp_width: int,
    comp_height: int,
    headline_id: str,
    reg_map: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Direct one `editorial_headline` block with cohesive typography, legibility & purposeful kinetic motion."""
    rmap = reg_map if reg_map is not None else _registry_map()
    genre = typing_system["story_genre"]
    is_mobile = comp_height > comp_width
    dur = max(0.8, t_end - t_start)
    words = text.split()
    rtl = is_rtl_str(text)
    primary = typing_system["primary"]
    display = typing_system["display"]

    # Detect structured year/tag pattern: e.g. "١٩٨٨ — عصابة عينين" or "1988 — ..."
    m_date = re.match(r"^([\u0660-\u06690-9]{4})\s*[—\-–:]\s*(.+)$", text.strip())
    m_num = re.search(r"([+\-]?[0-9\u0660-\u0669]+[.,:]?[0-9\u0660-\u0669]*\s*(?:%|percent|feet|seconds?|minutes?|ثانية))", text, re.IGNORECASE)

    anim_mode = "pill_pop"
    chosen_font = primary
    chosen_style = typing_system["primary_style"]
    display_text = text
    extra: Dict[str, Any] = {}

    if genre == "historical_documentary" and (m_date or beat_index == 0 or scene_index % 2 == 0):
        anim_mode = "documentary_card"
        chosen_font = primary
        if m_date:
            extra["kicker"] = f"{m_date.group(1)} — وثيقة وتجربة" if rtl else f"{m_date.group(1)} — CASE STUDY"
            display_text = m_date.group(2).strip()
        elif beat_index == 0:
            extra["kicker"] = "سجل تاريخي موثق" if rtl else "DOCUMENTED CASE"
        extra["display_font"] = display
        extra["kicker_font"] = primary
    elif m_date or m_num:
        anim_mode = "data_callout"
        chosen_font = primary
        if m_date:
            extra["metric"] = m_date.group(1).strip()
            display_text = m_date.group(2).strip()
        else:
            extra["metric"] = m_num.group(1).strip()
        extra["metric_font"] = display
    elif (beat_index == 0 and len(words) <= 5) or (len(words) <= 3 and scene_index % 2 == 0):
        anim_mode = "impact_title"
        chosen_font = display
        chosen_style = typing_system["display_style"]
    elif len(words) >= 4 and _find_highlight_word(text) and beat_index % 2 == 1:
        anim_mode = "word_emphasis"
        chosen_font = primary
        hw = _find_highlight_word(text)
        extra["highlight_word"] = hw
        extra["emphasis_style"] = resolve_style_variant(chosen_font, "ExtraBold", rmap)
        extra["accent_color"] = mood.get("card_border", "#FACC15")
    elif dur >= 2.6 and beat_index >= 2 and beat_index % 3 == 0:
        anim_mode = "mask_reveal"
        chosen_font = primary

    # Final safety & coverage guard (never selects LICENSE_REQUIRED or broken mixed-script fonts)
    safe_font, safe_style, fb_note = resolve_font_for_text(
        display_text + " " + str(extra.get("kicker", "")) + " " + str(extra.get("metric", "")),
        chosen_font,
        fallback_chain=[primary, typing_system["fallback"]],
        reg_map=rmap,
    )
    if anim_mode == "word_emphasis" and "highlight_word" in extra:
        extra["emphasis_style"] = resolve_style_variant(safe_font, "ExtraBold", rmap)

    # Responsive typography sizing & safe zone positioning across 16:9 & 9:16
    if is_mobile:
        base_sz = 64 if anim_mode == "impact_title" else (58 if len(words) <= 4 else 52)
        cx = round(comp_width * 0.5, 1)
        pos_y = 265.0 if anim_mode != "data_callout" else 310.0
        box_w = int(comp_width * 0.80)  # 864px inside 1080px mobile frame
        box_x = round((comp_width - box_w) * 0.5, 1)
        extra["box"] = [box_x, round(pos_y - 70.0, 1), box_w, 260]
        extra["leading"] = int(round(base_sz * 1.32))
    else:
        base_sz = 56 if anim_mode == "impact_title" else (52 if len(words) <= 3 else 46)
        cx, pos_y = round(comp_width * 0.5, 1), (146.0 if anim_mode in ("documentary_card", "data_callout") else 128.0)

    is_light = bool(mood.get("is_light_bg"))
    text_col = mood.get("text_color", "#F8FAFC")
    card_bg = mood.get("card_bg", "#0F1E30")
    border_col = mood.get("card_border", "#FBBF24")
    if anim_mode == "mask_reveal" and is_light:
        # Ensure strong dark-on-light contrast for unboxed or lightly pill-backed reveal
        text_col = "#0F172A"
        with_bg = False
    else:
        with_bg = True

    block: Dict[str, Any] = {
        "kind": "kinetic_typography",
        "id": headline_id,
        "role": anim_mode if anim_mode in ("impact_title", "documentary_card", "data_callout", "word_emphasis") else "editorial_headline",
        "text": display_text,
        "direction": "rtl" if rtl else "ltr",
        "font": safe_font,
        "font_style": safe_style,
        "size": base_sz,
        "position": [cx, pos_y],
        "color": text_col,
        "with_backdrop": with_bg,
        "backdrop_fill": card_bg,
        "backdrop_stroke": border_col,
        "animation_mode": anim_mode,
        "animator_based_on": 2 if rtl else 0,
        "start": round(t_start, 3),
        "end": round(max(t_start + 0.65, t_end), 3),
        "story_genre": genre,
        **extra,
    }
    if fb_note:
        block["font_fallback_note"] = fb_note
    return block

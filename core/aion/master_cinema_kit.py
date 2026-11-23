"""AION Studio V7 Master Cinema & Format Kit (`core/aion/master_cinema_kit.py`).

Script-agnostic, asset-agnostic production primitives that standardize:
1. Video Format Profiles & Auto-Routing (`educational` | `narrative`)
2. Supportive Live-Shifting 4-Color Gradient Palettes (`LIVING_GRADIENT_PALETTES`)
   with HOLD + SMOOTH-MORPH transitions (zero muddy mid-beat color drift)
3. Animated Lucide SVG Icon Library (2,411 local ISC SVGs) + Bilingual Semantic Matcher
   & 5 Verified GPU-Fast Animation Presets (`shield_guard`, `lock_snap`, `bulb_eureka`,
   `battle_strike`, `compass_seek`)
4. Pre-Ducking Gain-Staged CC0 SFX Catalog (`-1.8` to `-3.5 dB` for -14 LUFS voiceover)
5. General-Purpose Master Format Scene Graph V2 Builder (`build_master_format_section`)
   enforcing:
   - Grid-free supportive live gradients + subtle astrolabe arcs + sweeping CC Spotlight
   - Organic cutouts with studio drop-shadows (zero stiff boxed cards)
   - Zero lonely half-empty frames (single heroes command center & glide aside when paired)
   - Glowing curved Bezier arrows strictly connecting ELEMENT <-> ELEMENT (never icons!)
   - Single persistent Unified Top Neon-Glass Live-Typing HUD (`hud_sequence`)
"""
from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.aion.contracts import SCENE_GRAPH_V2, sync_scene_graph_v2_views
from core.aion.procedural_graphics import ProceduralGraphicsEngine
from core.aion.semantic_storyboard_director import synthesize_editorial_headline

ROOT_DIR = Path(__file__).resolve().parents[2]
LUCIDE_DIR = ROOT_DIR / "assets" / "icons_lucide"
SFX_KIT_DIR = ROOT_DIR / "assets" / "sfx_pro" / "wyzowl_sfx_kit" / "sfx-kit-1.0.0" / "sounds"
SEA_FOLEY_WAV = ROOT_DIR / "assets" / "sfx_pro" / "wikimedia_foley" / "sea_waves_ambience.wav"
TEX_FABRIC = ROOT_DIR / "assets" / "textures" / "polyhaven_bi_stretch_1k.jpg"
TEX_LEATHER = ROOT_DIR / "assets" / "textures" / "polyhaven_brown_leather_1k.jpg"

# ==============================================================================
# 1. SUPPORTIVE LIVE-GRADIENT MOOD PALETTES (10 Rich Jewel-Toned Worlds)
#    Designed to run at soft `bg_opacity=64%` over `#060A12` with live color waves!
# ==============================================================================
LIVING_GRADIENT_PALETTES: Dict[str, Dict[str, Any]] = {
    "imperial_slate": {
        "c1": "#1D4260", "c2": "#2E6A7D", "c3": "#7C522E", "c4": "#172D44",
        "vignette": 16.0, "is_light": False, "accent": "#F59E0B", "secondary": "#38BDF8",
    },
    "ocean_sapphire": {
        "c1": "#0A3A5C", "c2": "#1A6F8A", "c3": "#0E2440", "c4": "#5E4B28",
        "vignette": 18.0, "is_light": False, "accent": "#F59E0B", "secondary": "#38BDF8",
    },
    "eureka_emerald": {
        "c1": "#0D4A3E", "c2": "#1E785E", "c3": "#5B6428", "c4": "#0D3542",
        "vignette": 18.0, "is_light": False, "accent": "#34D399", "secondary": "#F59E0B",
    },
    "pressure_crimson": {
        "c1": "#5E152E", "c2": "#8E2842", "c3": "#321636", "c4": "#7D3722",
        "vignette": 20.0, "is_light": False, "accent": "#F43F5E", "secondary": "#F59E0B",
    },
    "sandstone_dawn": {
        "c1": "#DEC69F", "c2": "#C49E6E", "c3": "#EAD9BD", "c4": "#A87E52",
        "vignette": 14.0, "is_light": True, "accent": "#DC2626", "secondary": "#D97706",
    },
    "twilight_indigo": {
        "c1": "#15365C", "c2": "#25668A", "c3": "#292E66", "c4": "#1E586B",
        "vignette": 18.0, "is_light": False, "accent": "#38BDF8", "secondary": "#F59E0B",
    },
    "candle_bronze": {
        "c1": "#5E3A1E", "c2": "#805028", "c3": "#223447", "c4": "#3D2414",
        "vignette": 20.0, "is_light": False, "accent": "#F59E0B", "secondary": "#38BDF8",
    },
    "cosmic_violet": {
        "c1": "#2C2663", "c2": "#4F3B8A", "c3": "#1A3759", "c4": "#5E336E",
        "vignette": 18.0, "is_light": False, "accent": "#A78BFA", "secondary": "#38BDF8",
    },
    "clean_ivory": {
        "c1": "#E5DAC5", "c2": "#CFC0A5", "c3": "#EFE8DA", "c4": "#BCA88A",
        "vignette": 12.0, "is_light": True, "accent": "#0284C7", "secondary": "#D97706",
    },
    "obsidian_teal": {
        "c1": "#0E344A", "c2": "#1B5E73", "c3": "#182D4D", "c4": "#226B68",
        "vignette": 18.0, "is_light": False, "accent": "#38BDF8", "secondary": "#34D399",
    },
}

FORMAT_MOOD_CYCLES: Dict[str, List[str]] = {
    "educational": [
        "imperial_slate",
        "ocean_sapphire",
        "eureka_emerald",
        "pressure_crimson",
        "sandstone_dawn",
        "twilight_indigo",
    ],
    "narrative": [
        "candle_bronze",
        "ocean_sapphire",
        "eureka_emerald",
        "pressure_crimson",
        "sandstone_dawn",
        "twilight_indigo",
    ],
}

# ==============================================================================
# 2. VIDEO FORMAT PROFILES & BILINGUAL AUTO-ROUTER
# ==============================================================================
VIDEO_FORMATS: Dict[str, Dict[str, Any]] = {
    "educational": {
        "name": "Educational Explainer",
        "hud_mode": "persistent",
        "bg_opacity": 64.0,
        "texture": "fabric",
        "texture_opacity": 7.0,
        "mist_opacity_dark": 10.0,
        "mist_opacity_light": 3.0,
        "spot_opacity": 34.0,
        "spot_cone": 54.0,
        "spot_intensity": 210.0,
        "lumetri_contrast": 12.0,
        "lumetri_vibrance": 16.0,
        "lumetri_faded": 1.5,
        "master_vignette": 16.0,
        "use_arrows": True,
        "max_icons": 5,
        "hud_width": 880.0,
        "hud_height": 84.0,
    },
    "narrative": {
        "name": "Cinematic Storytelling",
        "hud_mode": "selective_cinematic",
        "bg_opacity": 62.0,
        "texture": "leather",
        "texture_opacity": 8.0,
        "mist_opacity_dark": 12.0,
        "mist_opacity_light": 3.0,
        "spot_opacity": 40.0,
        "spot_cone": 52.0,
        "spot_intensity": 220.0,
        "lumetri_contrast": 14.0,
        "lumetri_vibrance": 14.0,
        "lumetri_faded": 2.5,
        "master_vignette": 20.0,
        "use_arrows": True,
        "max_icons": 4,
        "hud_width": 840.0,
        "hud_height": 82.0,
    },
}

_EDU_KEYWORDS = (
    "كيف", "لماذا", "السبب", "الخطوة", "أولاً", "ثانياً", "ثالثاً", "مقارنة", "الفرق",
    "نتيجة", "قاعدة", "تفسير", "تحليل", "مثال", "نسبة", "علمياً", "الطريقة", "شرح",
    "how", "why", "step", "reason", "compare", "difference", "formula", "principle", "explain", "method",
)
_NAR_KEYWORDS = (
    "ذات يوم", "فجأة", "في ليلة", "قصة", "حكاية", "معركة", "حصار", "السلطان", "الإمبراطور",
    "ملك", "بطل", "تخيّل", "لحظة", "صمت", "قبل", "بعد سنين", "في أبريل", "عام",
    "once", "suddenly", "story", "legend", "empire", "siege", "battle", "night", "imagine", "king", "fate",
)


def detect_video_format(script_text: str, explicit_format: str = "auto") -> str:
    """Resolve `educational` or `narrative` cleanly from explicit override or bilingual text signals."""
    fmt = str(explicit_format or "auto").strip().lower()
    if fmt in VIDEO_FORMATS:
        return fmt
    if fmt in ("story", "storytelling", "cinematic", "documentary"):
        return "narrative"
    if fmt in ("edu", "explainer", "tutorial", "scientific"):
        return "educational"

    low = (script_text or "").lower()
    edu_hits = sum(1 for k in _EDU_KEYWORDS if k in low)
    nar_hits = sum(1 for k in _NAR_KEYWORDS if k in low)
    return "narrative" if nar_hits > edu_hits else "educational"


def build_held_bg_timeline(
    mood_beats: Sequence[Dict[str, Any]],
    morph_sec: float = 0.42,
    *,
    live_color_cycle: bool = False,
    total_duration: Optional[float] = None,
    cycle_step_sec: float = 3.2,
) -> List[Dict[str, Any]]:
    """Expand per-scene mood definitions into HOLD + SMOOTH-MORPH keyframes.

    When `live_color_cycle=True`, also smoothly rotates the 4 harmonious gradient colors
    (`c1..c4`) mid-scene every `cycle_step_sec` seconds so background colors visibly breathe
    and flow in live motion without ever turning muddy between scenes!
    """
    resolved: List[Dict[str, Any]] = []
    for mb in mood_beats:
        t0 = round(max(0.0, float(mb["time"])), 3)
        mood_key = str(mb.get("mood", "imperial_slate"))
        pal = LIVING_GRADIENT_PALETTES.get(mood_key, LIVING_GRADIENT_PALETTES["imperial_slate"])
        resolved.append({
            "time": t0,
            "c1": str(mb.get("c1", pal["c1"])),
            "c2": str(mb.get("c2", pal["c2"])),
            "c3": str(mb.get("c3", pal["c3"])),
            "c4": str(mb.get("c4", pal["c4"])),
            "vignette": float(mb.get("vignette", pal["vignette"])),
            "mood": mood_key,
            "is_light": bool(mb.get("is_light", pal.get("is_light", False))),
        })

    # Clockwise / diagonal permutations of the same 4 harmonious palette tones
    perms = ((0, 1, 2, 3), (1, 3, 0, 2), (3, 2, 1, 0), (2, 0, 3, 1))
    expanded: List[Dict[str, Any]] = []
    for idx, entry in enumerate(resolved):
        t0 = entry["time"]
        t_next = resolved[idx + 1]["time"] if idx + 1 < len(resolved) else (float(total_duration) if total_duration else t0)
        t_hold_end = round(max(t0 + 0.05, t_next - morph_sec), 3) if idx + 1 < len(resolved) else round(t_next, 3)

        expanded.append(dict(entry))
        base_cols = [entry["c1"], entry["c2"], entry["c3"], entry["c4"]]

        if live_color_cycle and t_hold_end > t0 + cycle_step_sec * 0.8:
            t_cur = round(t0 + cycle_step_sec, 3)
            p_idx = 1
            while t_cur < t_hold_end - 0.55:
                perm = perms[p_idx % len(perms)]
                expanded.append({
                    "time": t_cur,
                    "c1": base_cols[perm[0]], "c2": base_cols[perm[1]],
                    "c3": base_cols[perm[2]], "c4": base_cols[perm[3]],
                    "vignette": entry["vignette"], "mood": entry["mood"], "is_light": entry["is_light"],
                })
                t_cur = round(t_cur + cycle_step_sec, 3)
                p_idx += 1

        if idx + 1 < len(resolved) and t_hold_end > expanded[-1]["time"] + 0.02:
            last_c = expanded[-1]
            expanded.append({
                "time": t_hold_end,
                "c1": last_c["c1"], "c2": last_c["c2"], "c3": last_c["c3"], "c4": last_c["c4"],
                "vignette": last_c["vignette"], "mood": last_c["mood"], "is_light": last_c["is_light"],
            })
        elif live_color_cycle and idx + 1 == len(resolved) and total_duration and t_hold_end > expanded[-1]["time"] + 0.4:
            perm = perms[1]
            expanded.append({
                "time": round(float(total_duration), 3),
                "c1": base_cols[perm[0]], "c2": base_cols[perm[1]],
                "c3": base_cols[perm[2]], "c4": base_cols[perm[3]],
                "vignette": entry["vignette"], "mood": entry["mood"], "is_light": entry["is_light"],
            })
    return expanded


def build_caustics_opacity_keyframes(
    held_bg_timeline: Sequence[Dict[str, Any]],
    duration: float,
    *,
    dark_op: float = 16.0,
    light_op: float = 5.0,
) -> List[Tuple[float, float]]:
    """Auto-dim Screen caustics on light parchment/ivory moods so bright scenes stay pure & crisp."""
    kfs: List[Tuple[float, float]] = []
    for entry in held_bg_timeline:
        t = round(float(entry["time"]), 3)
        op = light_op if entry.get("is_light") else dark_op
        if not kfs or abs(kfs[-1][0] - t) > 0.02:
            kfs.append((t, op))
        else:
            kfs[-1] = (t, op)
    if not kfs:
        return [(0.0, dark_op), (round(duration, 3), dark_op)]
    if kfs[-1][0] < duration - 0.05:
        kfs.append((round(duration, 3), kfs[-1][1]))
    return kfs


# ==============================================================================
# 3. ANIMATED LUCIDE SVG ICON LIBRARY & SEMANTIC MATCHER
# ==============================================================================
SEMANTIC_ICON_RULES: List[Dict[str, Any]] = [
    {
        "icon": "lock", "preset": "lock_snap", "color": "#F59E0B", "sfx": "lock_metal",
        "patterns": r"سلسل|قفل|حاجز|عائق|منع|إغلاق|مغلق|محاصر|عالق|سر|lock|chain|block|barrier|trapped|seal",
    },
    {
        "icon": "lightbulb", "preset": "bulb_eureka", "color": "#34D399", "sfx": "eureka_sparkle",
        "patterns": r"فكرة|خطة|حل|ذكاء|عبقر|اكتشاف|اختراع|ابتكار|الالتفاف|أبريل|مفاج|idea|plan|solution|eureka|insight|clever|discover",
    },
    {
        "icon": "flame", "preset": "battle_strike", "color": "#DC2626", "sfx": "slam_big",
        "patterns": r"هجوم|معركة|مدفع|نار|انفجار|اقتحام|سقوط|تدمير|صراع|أزمة|ضغط|attack|battle|cannon|fire|flame|assault|fall|crisis",
    },
    {
        "icon": "shield", "preset": "shield_guard", "color": "#38BDF8", "sfx": "shimmer_bright",
        "patterns": r"أسوار|سور|درع|حماية|دفاع|حصن|أمان|مقاوم|صمود|wall|shield|defend|protect|fortress|guard|security",
    },
    {
        "icon": "compass", "preset": "compass_seek", "color": "#F59E0B", "sfx": "paper_slide",
        "patterns": r"خريطة|طريق|اتجاه|بوصلة|سنين|سنوات|وجهة|رحلة|قلعة ثانية|لاحق|map|compass|route|years|next|journey|direction",
    },
    {
        "icon": "trending-up", "preset": "bulb_eureka", "color": "#34D399", "sfx": "shimmer_bright",
        "patterns": r"نمو|ربح|ارتفاع|زيادة|اقتصاد|مال|استثمار|سوق|growth|profit|rise|market|economy|revenue|scale",
    },
    {
        "icon": "brain", "preset": "shield_guard", "color": "#A78BFA", "sfx": "shimmer_bright",
        "patterns": r"عقل|دماغ|تفكير|نفسي|ذاكرة|وهم|إدراك|تركيز|mind|brain|psychology|memory|cognitive|bias|habit",
    },
    {
        "icon": "clock", "preset": "compass_seek", "color": "#38BDF8", "sfx": "whoosh_soft",
        "patterns": r"وقت|زمن|قرن|ساعة|تاريخ|توقيت|انتظار|time|clock|century|hour|schedule|era|history",
    },
    {
        "icon": "scale", "preset": "compass_seek", "color": "#F59E0B", "sfx": "whoosh_soft",
        "patterns": r"مقارنة|ميزان|توازن|عدل|قرار|فرق|مقابل|compare|balance|scale|decision|versus|tradeoff",
    },
    {
        "icon": "target", "preset": "shield_guard", "color": "#34D399", "sfx": "shimmer_bright",
        "patterns": r"هدف|نتيجة|نصر|نجاح|عاصمة|إنجاز|تركيز|goal|target|victory|result|success|achieve",
    },
    {
        "icon": "alert-triangle", "preset": "lock_snap", "color": "#F43F5E", "sfx": "lock_metal",
        "patterns": r"تحذير|خطر|خطأ|فخ|مشكلة|كارثة|انهيار|warn|danger|risk|trap|mistake|fail|problem",
    },
    {
        "icon": "cpu", "preset": "bulb_eureka", "color": "#38BDF8", "sfx": "eureka_sparkle",
        "patterns": r"تقنية|نظام|خوارزم|برمج|حاسوب|آلة|تكنولوجيا|tech|cpu|system|algorithm|code|machine|ai",
    },
]

_FALLBACK_ICON_CYCLE = [
    {"icon": "sparkles", "preset": "shield_guard", "color": "#38BDF8", "sfx": "shimmer_bright"},
    {"icon": "lightbulb", "preset": "bulb_eureka", "color": "#34D399", "sfx": "eureka_sparkle"},
    {"icon": "target", "preset": "battle_strike", "color": "#F59E0B", "sfx": "shimmer_bright"},
    {"icon": "compass", "preset": "compass_seek", "color": "#F59E0B", "sfx": "paper_slide"},
]


def load_lucide_svg(icon_name: str, stroke_hex: str = "#38BDF8", stroke_w: float = 2.3) -> str:
    """Load an ISC-licensed Lucide SVG from `assets/icons_lucide/` and style stroke color/width."""
    stem = str(icon_name or "sparkles").strip().lower().replace("_", "-")
    p = LUCIDE_DIR / f"{stem}.svg"
    if not p.is_file():
        p = LUCIDE_DIR / "sparkles.svg"
    if not p.is_file():
        # Safe minimal vector fallback if directory is absent in a slim test env
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
            f'fill="none" stroke="{stroke_hex}" stroke-width="{stroke_w:.1f}" '
            f'stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/></svg>'
        )
    raw = p.read_text(encoding="utf-8")
    return (
        raw.replace('stroke="currentColor"', f'stroke="{stroke_hex}"')
        .replace('stroke-width="2"', f'stroke-width="{stroke_w:.1f}"')
    )


def pick_animated_icon_for_beat(
    text: str,
    *,
    used_icons: Optional[Sequence[str]] = None,
    is_light_bg: bool = False,
    beat_index: int = 0,
) -> Dict[str, Any]:
    """Match any Arabic/English beat text to a semantic Lucide icon + GPU-fast animation preset."""
    used = set(used_icons or [])
    txt = str(text or "")
    chosen: Optional[Dict[str, Any]] = None

    for rule in SEMANTIC_ICON_RULES:
        if re.search(rule["patterns"], txt, flags=re.IGNORECASE):
            if rule["icon"] not in used:
                chosen = dict(rule)
                break
            if chosen is None:
                chosen = dict(rule)

    if chosen is None:
        for cand in _FALLBACK_ICON_CYCLE:
            if cand["icon"] not in used:
                chosen = dict(cand)
                break
        if chosen is None:
            chosen = dict(_FALLBACK_ICON_CYCLE[beat_index % len(_FALLBACK_ICON_CYCLE)])

    stroke_hex = str(chosen["color"])
    if is_light_bg and stroke_hex.upper() in ("#34D399", "#38BDF8", "#A78BFA"):
        # Deepen bright neon strokes slightly on warm light parchment for razor contrast
        stroke_hex = {"#34D399": "#059669", "#38BDF8": "#0284C7", "#A78BFA": "#7C3AED"}[stroke_hex.upper()]

    return {
        "icon": str(chosen["icon"]),
        "preset": str(chosen["preset"]),
        "color": stroke_hex,
        "sfx": str(chosen.get("sfx", "shimmer_bright")),
        "ring_fill": "#FAF5EB" if is_light_bg else "#0B1628",
        "ring_fill_opacity": 82.0 if is_light_bg else 58.0,
    }


# ==============================================================================
# 4. GAIN-STAGED CC0 SFX CATALOG (Calibrated for -14 LUFS Voiceover + RMS Ducking)
# ==============================================================================
SFX_CATALOG: Dict[str, Tuple[str, float, Optional[float]]] = {
    "hud_type_quick":   ("keyboard/keyboard-typing-quick-short.wav",   -2.8, 0.90),
    "hud_type_steady":  ("keyboard/keyboard-typing-steady-short.wav",  -3.2, 0.90),
    "arrow_pen":        ("writing-and-drawing/writing-pen-draw.wav",   -2.5, 0.85),
    "arrow_marker":     ("writing-and-drawing/writing-marker-draw.wav",-2.5, 0.90),
    "lock_metal":       ("cinematic-hits/cinematic-metal-big.wav",     -2.5, 1.40),
    "eureka_sparkle":   ("shimmers/shimmer-medium-sparkle.wav",        -1.8, 1.25),
    "shimmer_bright":   ("shimmers/shimmer-short-bright.wav",          -2.4, 1.10),
    "shimmer_celestial":("shimmers/shimmer-long-celestial.wav",        -2.0, 2.20),
    "whoosh_soft":      ("whooshes/whoosh-medium-soft.wav",            -2.6, 0.90),
    "whoosh_hard":      ("whooshes/whoosh-medium-hard.wav",            -2.6, 0.90),
    "whoosh_heavy":     ("whooshes/whoosh-slow-heavy.wav",             -2.5, 1.10),
    "swish_zip":        ("swishes-and-zips/swish-hard.wav",            -2.8, 0.80),
    "paper_slide":      ("foley/foley-paper-slide.wav",                -2.0, 0.90),
    "appear_pop":       ("appear-and-vanish/appear-materialise.wav",   -2.4, 0.90),
    "riser_tension":    ("risers-and-fallers/riser-tension-build.wav", -2.2, 2.10),
    "boom_soft":        ("booms-and-bass/boom-hit-soft.wav",           -2.5, 1.50),
    "boom_medium":      ("booms-and-bass/boom-hit-medium.wav",         -2.6, 1.35),
    "boom_big":         ("booms-and-bass/boom-hit-big.wav",            -2.0, 1.55),
    "slam_big":         ("cinematic-hits/cinematic-slam-big.wav",      -2.2, 1.45),
}


def resolve_pro_sfx(
    event_key: str,
    *,
    time_sec: float,
    pan: float = 0.0,
    gain_override: Optional[float] = None,
    max_duration_override: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Return a validated, gain-staged SFX cue dict referencing local CC0 WAVs (or None if missing)."""
    if event_key == "sea_ambience":
        if SEA_FOLEY_WAV.is_file():
            cue: Dict[str, Any] = {
                "time": round(max(0.0, float(time_sec)), 3),
                "cue": SEA_FOLEY_WAV.as_posix(),
                "gain_db": float(gain_override if gain_override is not None else -1.5),
            }
            if max_duration_override:
                cue["max_duration"] = round(float(max_duration_override), 2)
            return cue
        return None

    spec = SFX_CATALOG.get(event_key)
    if not spec:
        return None
    rel_path, default_gain, default_max_dur = spec
    full_p = SFX_KIT_DIR / rel_path
    if not full_p.is_file():
        return None
    out: Dict[str, Any] = {
        "time": round(max(0.0, float(time_sec)), 3),
        "cue": full_p.as_posix(),
        "gain_db": float(gain_override if gain_override is not None else default_gain),
    }
    md = max_duration_override if max_duration_override is not None else default_max_dur
    if md:
        out["max_duration"] = round(float(md), 2)
    if abs(pan) > 0.01:
        out["pan"] = round(float(pan), 2)
    return out


# ==============================================================================
# 5. GENERAL-PURPOSE MASTER FORMAT SCENE GRAPH BUILDER (ANY Script & ANY Assets!)
# ==============================================================================
_AR_NORM_TRANS = str.maketrans("أإآىةؤئ", "اااهوءي")
_AR_DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670\u0640]")

# Bilingual concept bridges linking English filenames/descriptions <-> Arabic/English spoken words
_CONCEPT_BRIDGES: List[Tuple[str, str]] = [
    ("chain", "سلسل حديد حاجز مرفا"),
    ("wall", "سور اسوار جدار حجر حصن"),
    ("seawall", "جدار بحر مرفا سور"),
    ("ruler", "سلطان محمد الفاتح حاكم ملك"),
    ("turban", "سلطان محمد الفاتح عثمان"),
    ("crowned", "امبراطور قسطنطين ملك تاج"),
    ("guard", "امبراطور حارس بوابه جند"),
    ("map", "خريطه خرائط موقع طريق الخليج القرن"),
    ("waterway", "خليج القرن الذهبي مرفا مضيق ماء"),
    ("ship", "سفن سفينه اسطول بحر شراع"),
    ("fleet", "اسطول سفن بحر عثما"),
    ("shipwright", "صناعه هيكل خشب نجار بناء سفن ابريل"),
    ("hull", "هيكل سفن خشب نقل ابريل"),
    ("hill", "تل جبل بر ارض نقل"),
    ("oxen", "نقل برا جر ثيران جنود سفن"),
    ("haul", "نقل برا جر جنود سفن"),
    ("cannon", "مدفع مدافع قصف هجوم مايو"),
    ("breach", "هجوم سقوط ثغره تدمير سور مايو"),
    ("flag", "رايه علم نصر عاصمه فتح"),
    ("fortress", "قلعه حصن بلغراد"),
    ("island", "جزيره قلعه بلغراد نهر"),
    ("phone", "هاتف جوال شاشه تليفون"),
    ("scale", "ميزان عدل قرار خيار توازن"),
    ("mask", "قناع خدعه وجه شيطان"),
    ("clock", "ساعه وقت زمن يوم"),
    ("calendar", "يوم تقويم تاريخ نوفمبر مايو"),
    ("voyager", "فويجر مسبار مركبه فضاء"),
    ("dish", "طبق اشاره راديو هوائي رساله"),
    ("earth", "ارض كوكب عالم"),
]


def _norm_tokens(text: str) -> List[str]:
    cleaned = _AR_DIACRITICS_RE.sub("", str(text or "").lower()).translate(_AR_NORM_TRANS)
    cleaned = re.sub(r"[_\-/.،,;:!?؟\"'()\[\]{}|]+", " ", cleaned)
    out: List[str] = []
    for tok in cleaned.split():
        if len(tok) < 2:
            continue
        # Light Arabic definite article strip for better matching
        if tok.startswith("ال") and len(tok) >= 4:
            out.append(tok[2:])
        out.append(tok)
    return out


def align_assets_to_spoken_timeline(
    assets_in: List[Dict[str, Any]],
    words: List[Dict[str, Any]],
    beats: List[Dict[str, Any]],
    duration: float,
) -> List[Tuple[Dict[str, Any], float]]:
    """Align EVERY storyboard asset monotonically to its exact spoken word/sentence timestamp.

    Reads each asset's JSON catalog metadata (`filename`, `name_ar`, `description_ar`,
    `name_en`, `description_en`, `narrative_role`) and matches against Faster-Whisper
    `words` / `beats` using strict chronological dynamic programming so:
    1. Every element enters at the exact spoken moment matching its description.
    2. Order is 100% strictly chronological (`entity_01` < `entity_02` < ... < `entity_N`).
    3. Consecutive entrances stay cleanly spaced (never bunching or skipping).
    """
    n = len(assets_in)
    if n == 0:
        return []
    if n == 1:
        return [(assets_in[0], 0.0)]

    # Build spoken anchor timeline (full word-level sliding 4-word windows for sub-second precision)
    anchors: List[Tuple[float, set]] = []
    if words and len(words) >= 6:
        step = max(1, len(words) // min(220, len(words)))
        for wi in range(0, len(words), step):
            wt = max(0.0, min(duration - 0.8, float(words[wi].get("start", 0.0))))
            win_txt = " ".join(str(w.get("word", w.get("text", ""))) for w in words[wi : min(len(words), wi + 4)])
            anchors.append((wt, set(_norm_tokens(win_txt))))
    elif beats:
        for b in beats:
            bt = max(0.0, min(duration - 0.8, float(b.get("start", 0.0))))
            anchors.append((bt, set(_norm_tokens(str(b.get("text", ""))))))

    if not anchors:
        return [(a, round((i / float(n)) * max(1.0, duration - 1.5), 3)) for i, a in enumerate(assets_in)]

    # Build enriched semantic token sets per asset from storyboard_catalog JSON metadata
    asset_tokens: List[set] = []
    for a in assets_in:
        raw_desc = " ".join(
            str(a.get(k, "") or "")
            for k in ("filename", "name_ar", "description_ar", "name_en", "description_en")
        )
        toks = set(_norm_tokens(raw_desc))
        low_desc = raw_desc.lower()
        for eng_k, ar_exp in _CONCEPT_BRIDGES:
            if eng_k in low_desc or any(t in toks for t in _norm_tokens(ar_exp)):
                toks.add(eng_k)
                toks.update(_norm_tokens(ar_exp))
        asset_tokens.append(toks)

    # Monotonic DP alignment: strict chronological order + exact semantic hits + balanced documentary spacing
    m = len(anchors)
    avg_gap = max(1.0, (duration - 1.6) / max(1, n))
    min_gap = max(0.85, min(1.8, avg_gap * 0.45))
    max_gap = max(4.2, avg_gap * 1.95)
    expected_times = [(i / float(n)) * max(1.0, duration - 1.6) for i in range(n)]

    scores: List[List[float]] = []
    for i in range(n):
        row_s: List[float] = []
        exp_t = expected_times[i]
        is_opener = (i == 0 and str(assets_in[0].get("narrative_role", "")) == "section_identifier")
        for j in range(m):
            at, atoks = anchors[j]
            if is_opener:
                s = 25.0 if j == 0 else -12.0 * abs(at)
            else:
                overlap = len(asset_tokens[i] & atoks)
                if overlap == 0 and asset_tokens[i]:
                    for tk in asset_tokens[i]:
                        if len(tk) >= 4 and any((tk in w or w in tk) for w in atoks if len(w) >= 4):
                            overlap += 0.65
                time_diff = abs(at - exp_t) / max(1.0, duration)
                s = (overlap * 4.5) - (time_diff * time_diff * 85.0)
            row_s.append(s)
        scores.append(row_s)

    NEG_INF = -1e9
    dp = [[NEG_INF] * m for _ in range(n)]
    parent = [[-1] * m for _ in range(n)]
    for j in range(m):
        dp[0][j] = scores[0][j]

    for i in range(1, n):
        for j in range(i, m):
            at_j = anchors[j][0]
            best_v = NEG_INF
            best_p = -1
            for p in range(i - 1, j):
                if dp[i - 1][p] <= NEG_INF * 0.5:
                    continue
                gap = at_j - anchors[p][0]
                if gap < min_gap:
                    continue
                # Penalize overly wide gaps so no 10-second blank drift can ever happen
                gap_pen = 0.0
                if gap > max_gap:
                    gap_pen = -2.2 * ((gap - max_gap) ** 2)
                cand = dp[i - 1][p] + scores[i][j] + gap_pen
                if cand > best_v:
                    best_v = cand
                    best_p = p
            dp[i][j] = best_v
            parent[i][j] = best_p

    # Backtrack best sequence (fallback to uniform spacing if anchors were too sparse)
    best_last = max(range(m), key=lambda j: dp[n - 1][j])
    if dp[n - 1][best_last] <= NEG_INF * 0.5:
        return [(a, round(expected_times[i], 3)) for i, a in enumerate(assets_in)]

    chosen_j = [0] * n
    cur = best_last
    for i in range(n - 1, -1, -1):
        chosen_j[i] = cur
        cur = parent[i][cur] if i > 0 else 0

    aligned: List[Tuple[Dict[str, Any], float]] = []
    for i, a in enumerate(assets_in):
        t_sel = 0.0 if i == 0 else round(anchors[chosen_j[i]][0], 3)
        if i > 0 and t_sel <= aligned[-1][1] + 0.35:
            t_sel = round(min(duration - 0.6, aligned[-1][1] + 0.65), 3)
        aligned.append((a, t_sel))
    return aligned


def _partition_list(items: List[Any], n_groups: int) -> List[List[Any]]:
    if not items:
        return [[] for _ in range(max(1, n_groups))]
    n = max(1, min(n_groups, len(items)))
    q, r = divmod(len(items), n)
    out: List[List[Any]] = []
    idx = 0
    for g in range(n):
        sz = q + (1 if g < r else 0)
        out.append(items[idx:idx + sz])
        idx += sz
    return out


_TRAILING_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "at", "by", "for", "with", "and", "or", "but", "that", "is", "are", "was", "were",
    "في", "من", "على", "إلى", "عن", "مع", "كان", "كانت", "هي", "هو", "اللي", "التي", "الذي", "و", "ثم", "أو", "ما", "أن", "إن",
}


def _clean_hud_phrase(raw_text: str, lang: str, max_words: int = 5, max_chars: int = 36) -> str:
    txt = str(raw_text or "").strip()
    # Never let bracketed production/editorial directives (e.g. [آية قرآنية صامتة: ...]) appear on screen
    if "[آية" in txt or "آية قرآنية" in txt:
        txt = re.sub(r"\[[^\]]*\]?", "", txt).strip()
        if not txt:
            return "تدبّر الآية الكريمة"
    else:
        txt = re.sub(r"\[[^\]]*\]?", "", txt).strip()
    if not txt:
        return "مشهد رئيسي" if lang == "ar" else "Key Insight"
    try:
        ed = synthesize_editorial_headline(txt)
        if ed and len(ed.strip()) >= 3:
            txt = ed.strip()
    except Exception:
        pass
    words = txt.split()[:max_words]
    # Fit comfortably inside 880px neon HUD pill without ever touching side borders
    while len(words) > 2 and len(" ".join(words)) > max_chars:
        words.pop()
    while len(words) > 2 and words[-1].strip("،,.:;!?؟-").lower() in _TRAILING_STOPWORDS:
        words.pop()
    out = " ".join(words).rstrip("،,.:;-")
    return out or ("مشهد رئيسي" if lang == "ar" else "Key Insight")


def build_master_format_section(
    brief: Dict[str, Any],
    *,
    video_format: str = "auto",
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> Dict[str, Any]:
    """Direct ANY script, timing beats, and extracted asset list into a Master Cinema Scene Graph V2.

    Works identically for History, Science, Finance, Psychology, Biography, or Tech scripts:
    - Selects Educational Explainer vs Cinematic Narrative format automatically (or via explicit arg).
    - Builds color-theory-harmonized HOLD+MORPH live 4-Color Gradient moods (no grids, no floor line).
    - Stages ALL provided visual assets chronologically in balanced pairs/solo-to-duet layouts (zero empty halves).
    - Connects ELEMENT <-> ELEMENT strictly with glowing curved Bezier arrows (never pointing to icons).
    - Adds 3–5 genuinely animated Lucide SVG icons (`Trim Paths` + rotating ring + shockwave ripple + semantic motion).
    - Routes ALL headlines into ONE persistent Unified Top Neon-Glass Live-Typing HUD (`hud_sequence`).
    - Attaches calibrated pre-ducking CC0 SFX cues (plus subtle sea foley if maritime cues appear in narrative mode).
    """
    beats: List[Dict[str, Any]] = list(brief.get("beats") or [])
    assets_in: List[Dict[str, Any]] = list(brief.get("assets") or [])
    words: List[Dict[str, Any]] = list(brief.get("words") or [])
    sec_id = str(brief.get("section_id") or "section_01")
    script_text = str(brief.get("script_text") or " ".join(str(b.get("text", "")) for b in beats))
    lang = "ar" if re.search(r"[\u0600-\u06FF]", script_text) else "en"

    dur = float(brief.get("duration_sec") or 0.0)
    if dur <= 0.0:
        if beats:
            dur = max(float(b.get("end", 0.0)) for b in beats)
        elif words:
            dur = max(float(w.get("end", 0.0)) for w in words)
        else:
            dur = 20.0
    dur = round(max(4.0, dur), 3)

    if not beats:
        beats = [{"id": "b1", "start": 0.0, "end": dur, "text": script_text or ("عرض بصري" if lang == "ar" else "Visual Overview")}]

    fmt = detect_video_format(script_text, video_format)
    profile = VIDEO_FORMATS[fmt]
    mood_cycle = FORMAT_MOOD_CYCLES[fmt]

    # Decide 4–6 visual chapters scaled to section duration & asset count
    target_chapters = max(3, min(6, max(len(beats) // 2, 4) if dur >= 28.0 else 3))
    if len(assets_in) > 0:
        target_chapters = min(target_chapters, max(1, len(assets_in)))
    if len(beats) < target_chapters:
        target_chapters = max(1, len(beats))

    beat_groups = _partition_list(beats, target_chapters)

    # Build held-then-morphed mood timeline (reserve `sandstone_dawn` for climax chapter when >= 4 chapters!)
    mood_beats: List[Dict[str, Any]] = []
    chapter_windows: List[Tuple[float, float, str, str]] = []
    for c_idx, bgrp in enumerate(beat_groups):
        c_start = 0.0 if c_idx == 0 else round(float(bgrp[0].get("start", 0.0)), 3)
        c_end = dur if c_idx == len(beat_groups) - 1 else round(float(beat_groups[c_idx + 1][0].get("start", bgrp[-1].get("end", dur))), 3)
        if c_end <= c_start + 0.4:
            c_end = round(min(dur, c_start + max(1.0, dur / target_chapters)), 3)
        c_text = " ".join(str(b.get("text", "")) for b in bgrp)

        # Climax placement: penultimate chapter (when >=5) or 4th chapter gets luminous Sandstone Dawn reveal!
        if target_chapters >= 5 and c_idx == target_chapters - 2:
            mood_key = "sandstone_dawn"
        elif target_chapters == 4 and c_idx == 2:
            mood_key = "sandstone_dawn"
        else:
            mood_key = mood_cycle[c_idx % len(mood_cycle)]
            if mood_key == "sandstone_dawn":
                mood_key = "twilight_indigo"

        mood_beats.append({"time": c_start, "mood": mood_key})
        chapter_windows.append((c_start, c_end, mood_key, c_text))

    # Align ALL assets monotonically to their EXACT spoken timestamps from storyboard_catalog JSON + timing_master.json!
    aligned_assets = align_assets_to_spoken_timeline(assets_in, words, beats, dur)
    asset_groups: List[List[Tuple[Dict[str, Any], float]]] = [[] for _ in range(target_chapters)]
    for a_item, a_time in aligned_assets:
        placed_ci = target_chapters - 1
        for ci, (cs_w, ce_w, _, _) in enumerate(chapter_windows):
            if cs_w <= a_time < ce_w:
                placed_ci = ci
                break
        asset_groups[placed_ci].append((a_item, a_time))
    # Ensure no chapter is ever completely empty when assets exist (borrow cleanly from neighbor while preserving order)
    if aligned_assets:
        for ci in range(target_chapters):
            if not asset_groups[ci]:
                donor = max(range(target_chapters), key=lambda k: len(asset_groups[k]))
                if len(asset_groups[donor]) >= 2:
                    if donor < ci:
                        moved = asset_groups[donor].pop()
                        asset_groups[ci].append((moved[0], chapter_windows[ci][0]))
                    else:
                        moved = asset_groups[donor].pop(0)
                        asset_groups[ci].append((moved[0], chapter_windows[ci][0]))

    held_bg_tl = build_held_bg_timeline(mood_beats, morph_sec=0.42, live_color_cycle=True, total_duration=dur, cycle_step_sec=3.2)
    caustics_kfs = build_caustics_opacity_keyframes(
        held_bg_tl,
        dur,
        dark_op=float(profile["mist_opacity_dark"]),
        light_op=float(profile["mist_opacity_light"]),
    )

    first_pal = LIVING_GRADIENT_PALETTES[chapter_windows[0][2]]
    tex_file = TEX_FABRIC if profile["texture"] == "fabric" else TEX_LEATHER
    is_portrait = height > width

    # Geometry scaling (works seamlessly for 16:9 AND 9:16!)
    cx = width * 0.5
    left_x = round(width * 0.29, 1)
    right_x = round(width * 0.685, 1)
    stage_y = round(height * 0.555, 1)
    right_y_under_icon = round(height * 0.595, 1)
    icon_y = round(height * 0.295, 1)
    hud_y = round(height * 0.088, 1)

    scenes: List[Dict[str, Any]] = []
    hud_phrases: List[Dict[str, Any]] = []
    hud_vis_kfs: List[Tuple[float, float]] = []
    proc_graphics: List[Dict[str, Any]] = []
    vfx_list: List[Dict[str, Any]] = []
    sfx_list: List[Dict[str, Any]] = []
    spot_kfs: List[Dict[str, Any]] = []
    cam_kfs: List[Dict[str, Any]] = [{"time": 0.0, "pos": [cx, height * 0.5, -1680.0], "poi": [cx, height * 0.5, 0.0]}]

    proc = ProceduralGraphicsEngine(width, height)
    used_icons: List[str] = []
    icons_placed = 0

    # Optional non-musical sea ambience in narrative mode if maritime cues exist
    if fmt == "narrative" and re.search(r"بحر|سفن|خليج|مرفأ|أسطول|محيط|sea|ship|fleet|harbor|ocean", script_text, re.IGNORECASE):
        sea_cue = resolve_pro_sfx("sea_ambience", time_sec=min(4.0, dur * 0.1), max_duration_override=min(34.0, dur * 0.65))
        if sea_cue:
            sfx_list.append(sea_cue)

    for c_idx, (c_start, c_end, mood_key, c_text) in enumerate(chapter_windows):
        pal = LIVING_GRADIENT_PALETTES[mood_key]
        is_light = bool(pal.get("is_light", False))
        accent_hex = str(pal["accent"])
        c_assets_raw = asset_groups[c_idx]
        c_span = max(0.8, c_end - c_start)
        headline = _clean_hud_phrase(c_text, lang, max_words=6)

        # Narrative format hides HUD on the suspense chapter (c_idx == 1) and pure-visual climax (sandstone_dawn)
        hide_hud_here = (
            fmt == "narrative"
            and target_chapters >= 4
            and (c_idx == 1 or mood_key == "sandstone_dawn")
        )

        # HUD phrases & visibility timeline
        if hide_hud_here:
            hud_phrases.append({"start": c_start, "end": c_end, "color": accent_hex, "text": "", "hidden": True})
        else:
            prefix = f"{'①②③④⑤⑥'[c_idx]} " if (fmt == "educational" and c_idx < 6 and len(headline) <= 28) else ""
            hud_phrases.append({
                "start": c_start, "end": c_end, "color": accent_hex,
                "text": f"{prefix}{headline}".strip(),
                "type_dur": round(min(0.86, max(0.45, c_span * 0.22)), 2),
            })
            type_sfx = resolve_pro_sfx("hud_type_quick" if c_idx % 2 == 0 else "hud_type_steady", time_sec=c_start + 0.08)
            if type_sfx and fmt == "educational":
                sfx_list.append(type_sfx)

        # Spotlight & gentle camera cadence
        spot_x = right_x if (c_idx % 2 == 1 and not is_portrait) else (cx if len(c_assets_raw) <= 1 else left_x)
        spot_kfs.append({"time": c_start, "from": [round(spot_x * 0.55, 1), -140.0], "to": [spot_x, stage_y], "color": accent_hex})
        if c_idx > 0:
            z_push = -1530.0 if (c_idx % 2 == 1) else -1680.0
            poi_x = cx + (35.0 if c_idx % 2 == 1 else 0.0)
            cam_kfs.append({"time": round(c_start + 0.65, 3), "pos": [poi_x, height * 0.5 + 6.0, z_push], "poi": [poi_x, height * 0.5 + 6.0, 0.0]})
            # Transition SFX
            if mood_key == "sandstone_dawn":
                if fmt == "narrative" and c_start > 2.6:
                    riser = resolve_pro_sfx("riser_tension", time_sec=c_start - 2.35, max_duration_override=2.05)
                    if riser:
                        sfx_list.append(riser)
                hit = resolve_pro_sfx("boom_big" if fmt == "narrative" else "boom_medium", time_sec=c_start)
                if hit:
                    sfx_list.append(hit)
            else:
                tr = resolve_pro_sfx("whoosh_hard" if c_idx % 2 else "whoosh_soft", time_sec=c_start, pan=-0.2 if c_idx % 2 else 0.2)
                if tr:
                    sfx_list.append(tr)

        # Stage visual assets inside this chapter — ZERO empty half-frames!
        scene_assets: List[Dict[str, Any]] = []
        n_a = len(c_assets_raw)

        # Choose animated Lucide icon for this chapter (within format budget)
        add_icon = (icons_placed < int(profile["max_icons"])) and (fmt == "educational" or c_idx >= 1)
        icon_meta: Optional[Dict[str, Any]] = None
        if add_icon:
            icon_meta = pick_animated_icon_for_beat(c_text, used_icons=used_icons, is_light_bg=is_light, beat_index=c_idx)
            used_icons.append(icon_meta["icon"])
            icons_placed += 1

        if n_a == 1:
            # Solo Hero commands GRAND CENTER!
            a0, _t0_a = c_assets_raw[0]
            aid = f"m{c_idx:02d}_hero_{a0.get('id', '01')}"
            scene_assets.append({
                "id": aid, "instance_id": aid, "asset_id": str(a0.get("id", aid)),
                "path": str(a0.get("path", "")),
                "in": c_start, "out": c_end,
                "pos": [cx, stage_y], "position": [cx, stage_y],
                "target_h": int(height * 0.47), "max_w": int(width * 0.42),
                "entrance": "pop_settle", "entrance_dur": 0.38, "fade_out": 0.16,
                "three_d": True, "z": 0.0, "role": "hero", "shadow": False,
                "keyframes": [
                    {"time": round(c_start + 0.5, 3), "scale_mult": 1.00},
                    {"time": round(max(c_start + 0.8, c_end - 0.3), 3), "scale_mult": 1.06},
                ],
            })
            vfx_list.append({"type": "drop_shadow", "target": f"Asset_{aid}", "opacity": 74.0, "distance": 24.0, "softness": 44.0, "start": c_start, "end": c_end})
            if icon_meta:
                iaid = f"m{c_idx:02d}_icon_{icon_meta['icon'].replace('-', '_')}"
                ix = round(width * 0.77, 1) if not is_portrait else round(width * 0.80, 1)
                iy = round(height * 0.25, 1)
                imp_t = round(min(c_end - 0.5, c_start + 0.75), 3)
                scene_assets.append(_make_anim_icon_dict(iaid, icon_meta, c_start + 0.25, c_end, [ix, iy], imp_t))
                if icon_meta["preset"] != "bulb_eureka":
                    vfx_list.append({"type": "glow", "target": f"SvgAsset_{iaid}", "intensity": 0.90, "radius": 20.0, "start": round(c_start + 0.25, 3), "end": c_end})
                isx = resolve_pro_sfx(icon_meta["sfx"], time_sec=imp_t, pan=0.25)
                if isx:
                    sfx_list.append(isx)

        elif n_a >= 2:
            # STRICT CHRONOLOGICAL LEFT <-> RIGHT ALTERNATION aligned to exact spoken word timestamps!
            # Even indices (0, 2, 4...) -> Left slot; Odd indices (1, 3, 5...) -> Right slot.
            # Every asset appears right when the narrator mentions it, never out of order, and stays visible ~5-6s!
            left_timed: List[Tuple[Dict[str, Any], float]] = []
            right_timed: List[Tuple[Dict[str, Any], float]] = []
            for local_i, (a_obj, a_ts) in enumerate(c_assets_raw):
                clamped_t = round(max(c_start, min(c_end - 0.55, a_ts)), 3)
                if local_i == 0:
                    # Chapter opener anchors cleanly at chapter start so there is zero blank gap
                    clamped_t = c_start
                if local_i % 2 == 0:
                    if left_timed and clamped_t <= left_timed[-1][1] + 0.65:
                        clamped_t = round(min(c_end - 0.45, left_timed[-1][1] + 0.75), 3)
                    left_timed.append((a_obj, clamped_t))
                else:
                    if right_timed and clamped_t <= right_timed[-1][1] + 0.65:
                        clamped_t = round(min(c_end - 0.45, right_timed[-1][1] + 0.75), 3)
                    right_timed.append((a_obj, clamped_t))

            # Emit Left column assets cleanly timed to exact spoken entrances & non-overlapping exits
            for li, (la, lt0) in enumerate(left_timed):
                lt1 = round(c_end if li == len(left_timed) - 1 else max(lt0 + 0.5, left_timed[li + 1][1] - 0.04), 3)
                laid = f"m{c_idx:02d}_L{li}_{la.get('id', li)}"
                ent = "pop_settle" if li == 0 else "slide_left"
                kfs_left: List[Dict[str, Any]] = []
                start_pos = [left_x, stage_y]
                if fmt == "narrative" and c_idx == 0 and li == 0 and right_timed and (right_timed[0][1] - lt0) >= 0.8:
                    t_glide = round(max(lt0 + 0.45, right_timed[0][1] - 0.25), 3)
                    start_pos = [cx, stage_y]
                    kfs_left = [
                        {"time": t_glide, "pos": [cx, stage_y, 0.0], "scale_mult": 1.04},
                        {"time": round(min(lt1 - 0.2, t_glide + 0.55), 3), "pos": [left_x, stage_y, 0.0], "scale_mult": 0.95},
                    ]
                a_dict: Dict[str, Any] = {
                    "id": laid, "instance_id": laid, "asset_id": str(la.get("id", laid)),
                    "path": str(la.get("path", "")),
                    "in": lt0, "out": lt1,
                    "pos": start_pos, "position": start_pos,
                    "target_h": int(height * 0.42), "max_w": int(width * 0.285),
                    "entrance": ent, "entrance_dur": 0.36, "fade_out": 0.16,
                    "three_d": True, "z": 0.0, "role": "hero" if li == 0 else "supporting", "shadow": False,
                }
                if kfs_left:
                    a_dict["keyframes"] = kfs_left
                scene_assets.append(a_dict)
                vfx_list.append({"type": "drop_shadow", "target": f"Asset_{laid}", "opacity": 74.0, "distance": 24.0, "softness": 44.0, "start": lt0, "end": lt1})

            # Emit Right column assets cleanly timed to exact spoken entrances & non-overlapping exits
            ry_use = right_y_under_icon if icon_meta else stage_y
            rh_use = int(height * (0.335 if icon_meta else 0.405))
            r_start_base = right_timed[0][1] if right_timed else round(min(c_end - 0.5, c_start + 0.35), 3)

            for ri, (ra, rt0) in enumerate(right_timed):
                rt1 = round(c_end if ri == len(right_timed) - 1 else max(rt0 + 0.5, right_timed[ri + 1][1] - 0.04), 3)
                raid = f"m{c_idx:02d}_R{ri}_{ra.get('id', ri)}"
                use_mask = (ri % 2 == 0)
                scene_assets.append({
                    "id": raid, "instance_id": raid, "asset_id": str(ra.get("id", raid)),
                    "path": str(ra.get("path", "")),
                    "in": rt0, "out": rt1,
                    "pos": [right_x, ry_use], "position": [right_x, ry_use],
                    "target_h": rh_use, "max_w": int(width * 0.265),
                    "entrance": "mask_reveal" if use_mask else "slide_right",
                    "mask_reveal": use_mask, "entrance_dur": 0.36, "fade_out": 0.16,
                    "three_d": True, "z": 0.0, "role": "supporting", "shadow": False,
                })
                vfx_list.append({"type": "drop_shadow", "target": f"Asset_{raid}", "opacity": 74.0, "distance": 24.0, "softness": 44.0, "start": rt0, "end": rt1})

            # Curved Glowing ELEMENT -> ELEMENT Arrow ONLY (enters right when first Right partner arrives!)
            if profile["use_arrows"] and not is_portrait:
                arr_t0 = round(min(c_end - 0.4, r_start_base + 0.15), 3)
                p_from = (round(left_x + width * 0.145, 1), stage_y)
                p_to = (round(right_x - width * 0.132, 1), ry_use)
                proc_graphics.append(
                    proc.build_bezier_connector(
                        f"m{c_idx:02d}_arrow", p_from, p_to,
                        curvature=-0.18 if c_idx % 2 == 0 else -0.22,
                        stroke_color=accent_hex, stroke_width=5.6,
                        start_time=arr_t0, draw_duration=0.48, end_time=round(max(arr_t0 + 0.5, c_end - 0.10), 3),
                        with_arrow=True, dashed=(c_idx % 2 == 0),
                    )
                )
                pen_sfx = resolve_pro_sfx("arrow_pen" if c_idx % 2 == 0 else "arrow_marker", time_sec=arr_t0)
                if pen_sfx:
                    sfx_list.append(pen_sfx)

            # Animated Lucide Icon positioned cleanly ABOVE the right subject (zero overlap with arrow!)
            if icon_meta:
                iaid = f"m{c_idx:02d}_icon_{icon_meta['icon'].replace('-', '_')}"
                it0 = round(min(c_end - 0.5, c_start + 0.45), 3)
                imp_t = round(min(c_end - 0.35, it0 + 0.55), 3)
                icon_x = round(cx, 1) if mood_key == "sandstone_dawn" else right_x
                scene_assets.append(_make_anim_icon_dict(iaid, icon_meta, it0, c_end, [icon_x, icon_y], imp_t))
                if icon_meta["preset"] != "bulb_eureka":
                    vfx_list.append({"type": "glow", "target": f"SvgAsset_{iaid}", "intensity": 0.90, "radius": 20.0, "start": it0, "end": c_end})
                isx = resolve_pro_sfx(icon_meta["sfx"], time_sec=imp_t, pan=0.22)
                if isx:
                    sfx_list.append(isx)

        comp_mode = "hero_center" if n_a == 1 else ("living_diagram" if c_idx % 2 == 1 else "split_polarity")
        scenes.append({
            "scene_id": f"{fmt[:3]}_{c_idx + 1:02d}",
            "intent": "solution_insight" if mood_key == "eureka_emerald" else ("climax_peak" if mood_key == "sandstone_dawn" else "explanatory_diagram"),
            "headline": "" if hide_hud_here else headline,
            "mood": mood_key,
            "composition_mode": comp_mode,
            "time": {"start": c_start, "end": c_end},
            "assets": scene_assets,
        })

    # Compute clean HUD visibility keyframes for narrative mode when some chapters hide HUD
    if any(p.get("hidden") for p in hud_phrases):
        hud_vis_kfs = _build_hud_visibility_keyframes(hud_phrases, dur)

    cam_kfs.append({"time": dur, "pos": [cx, height * 0.5, -1620.0], "poi": [cx, height * 0.5, 0.0]})

    hud_seq: Dict[str, Any] = {
        "width": float(profile["hud_width"]) if not is_portrait else round(width * 0.86, 1),
        "height": float(profile["hud_height"]),
        "position": [cx, hud_y],
        "font": "IBM Plex Sans Arabic" if lang == "ar" else "Inter",
        "font_style": "Bold",
        "font_size": 38 if not is_portrait else 44,
        "backdrop_fill": "#091222",
        "text_color": "#F8FAFC",
        "pill_opacity": 92.0,
        "phrases": hud_phrases,
    }
    if hud_vis_kfs:
        hud_seq["visibility_keyframes"] = hud_vis_kfs

    typo_meta = [
        {
            "kind": "kinetic_typography",
            "id": f"hud_meta_{i}",
            "text": p["text"],
            "direction": "rtl" if lang == "ar" else "ltr",
            "font": hud_seq["font"],
            "size": hud_seq["font_size"],
            "color": "#F8FAFC",
            "start": p["start"],
            "end": p["end"],
            "with_backdrop": True,
            "backdrop_fill": "#091222",
            "backdrop_stroke": p["color"],
        }
        for i, p in enumerate(hud_phrases)
        if not p.get("hidden") and str(p.get("text", "")).strip()
    ]

    # Keep SFX mix clean, spacious, and strictly within per-duration QA restraint budget
    sfx_budget = max(8, int(dur * 0.36))
    sfx_list = _budget_sfx_cues(sfx_list, max_cues=sfx_budget)

    sg: Dict[str, Any] = {
        "schema_version": SCENE_GRAPH_V2,
        "section_id": sec_id,
        "video_format": fmt,
        "width": width,
        "height": height,
        "fps": fps,
        "narrative_intent": {
            "primary": "educational_explainer" if fmt == "educational" else "cinematic_storytelling",
            "format": fmt,
            "summary": _clean_hud_phrase(script_text, lang, max_words=10),
        },
        "visual_metaphor": {
            "stage_style": f"living_gradient_{fmt}",
            "connectors": "element_to_element_curved_bezier",
            "icons": "animated_lucide_trim_paths",
        },
        "lighting": {"enabled": False, "lights": []},
        "timing_anchors": [
            {"id": f"ch_{idx + 1:02d}", "start": w_st, "end": w_en, "mood": w_mood}
            for idx, (w_st, w_en, w_mood, _) in enumerate(chapter_windows)
        ],
        "tool_requirements": [
            "4-Color Gradient", "Fractal Noise", "ec.perspective.ccspotlight",
            "ec.color.lumetri", "ec.stylize.glow", "ec.stylize.ccvignette",
            "edit.pasteSvg", "layer.addShapeItem:trim",
        ],
        "fallbacks": {
            "texture_missing": "skip_overlay_texture",
            "sfx_missing": "voice_only_clean",
        },
        "quality_constraints": {
            "zero_square_grid": True,
            "zero_floor_line": True,
            "element_to_element_arrows_only": True,
            "zero_cclightrays_cpu_stall": True,
            "max_white_blowout": 0.05,
        },
        "source_timeline": {
            "audio_file": str(brief.get("audio_file") or f"sections/{sec_id}/voice/{sec_id}.wav"),
            "duration_sec": dur,
            "beats": beats,
            "words": words,
        },
        "composition": {
            "layout_mode": "semantic_v5_cinematic_story",
            "video_format": fmt,
            "bg_color": "#060A12",
            "palette": {
                "name": f"master_{fmt}",
                "bg": "#060A12",
                "surface": first_pal["c2"],
                "primary": first_pal["accent"],
                "accent": first_pal["secondary"],
                "secondary": first_pal["secondary"],
                "danger": "#F43F5E",
                "text": "#F8FAFC",
                "text_muted": "#94A3B8",
                "is_light_bg": False,
            },
            "enable_3d_stage": True,
            "fps": fps,
        },
        "background_timeline": held_bg_tl,
        "cinema_stage": {
            "living_gradient": True,
            "bg_opacity": float(profile["bg_opacity"]),
            "gradient_blend": 108.0,
            "gradient_step_sec": 1.8,
            "gradient_cycles": 3.4,
            "hide_floor_line": True,
            "glow_arrows": True,
            "texture_path": tex_file.as_posix() if tex_file.is_file() else "",
            "texture_opacity": float(profile["texture_opacity"]),
            "ring_color": first_pal["accent"],
            "ring_color_2": first_pal["secondary"],
            "spot_opacity": float(profile["spot_opacity"]),
            "spot_cone": float(profile["spot_cone"]),
            "spot_intensity": float(profile["spot_intensity"]),
            "lumetri_contrast": float(profile["lumetri_contrast"]),
            "lumetri_vibrance": float(profile["lumetri_vibrance"]),
            "lumetri_faded": float(profile["lumetri_faded"]),
            "master_vignette": float(profile["master_vignette"]),
            "caustics_opacity_keyframes": caustics_kfs,
            "spot_keyframes": spot_kfs,
        },
        "camera": {
            "enabled": True,
            "mode": "educational_focus" if fmt == "educational" else "cinematic_push",
            "zoom": 1680.0,
            "keyframes": cam_kfs,
        },
        "hud_sequence": hud_seq,
        "scenes": scenes,
        "typography": typo_meta,
        "procedural_graphics": proc_graphics,
        "vfx": vfx_list,
        "sfx": sfx_list,
        "sfx_cues": list(sfx_list),
        "motion_paths": [],
        "relationships": [],
        "asset_library": {},
        "asset_references": [],
    }
    return sync_scene_graph_v2_views(sg)


def _make_anim_icon_dict(
    aid: str,
    icon_meta: Dict[str, Any],
    t0: float,
    t1: float,
    pos: List[float],
    impact_t: float,
) -> Dict[str, Any]:
    return {
        "id": aid,
        "instance_id": aid,
        "asset_id": aid,
        "icon": icon_meta["icon"],
        "svg": load_lucide_svg(icon_meta["icon"], icon_meta["color"], stroke_w=2.3),
        "in": round(max(0.0, t0), 3),
        "out": round(t1, 3),
        "pos": pos,
        "position": pos,
        "scale": 340.0,
        "entrance": "pop_settle",
        "entrance_dur": 0.34,
        "fade_out": 0.16,
        "three_d": True,
        "z": -12.0,
        "role": "semantic_icon",
        "icon_anim": {
            "preset": icon_meta["preset"],
            "color": icon_meta["color"],
            "impact_time": round(impact_t, 3),
            "ring_size": 136.0,
            "ring_fill": icon_meta["ring_fill"],
            "ring_fill_opacity": icon_meta["ring_fill_opacity"],
        },
    }


def _build_hud_visibility_keyframes(phrases: List[Dict[str, Any]], dur: float) -> List[Tuple[float, float]]:
    vis: List[Tuple[float, float]] = [(0.0, 0.0)]
    prev_on = False
    for idx, ph in enumerate(phrases):
        st = round(float(ph["start"]), 3)
        is_on = not bool(ph.get("hidden")) and bool(str(ph.get("text", "")).strip())
        if idx == 0:
            if is_on:
                vis.append((round(min(dur, st + 0.16), 3), 100.0))
            prev_on = is_on
            continue
        if is_on != prev_on:
            t_pre = round(max(vis[-1][0] + 0.02, st - 0.18), 3)
            t_post = round(min(dur, max(t_pre + 0.05, st + 0.08)), 3)
            vis.append((t_pre, 100.0 if prev_on else 0.0))
            vis.append((t_post, 100.0 if is_on else 0.0))
            prev_on = is_on
    t_end_hold = round(max(vis[-1][0] + 0.02, dur - 0.18), 3)
    vis.append((t_end_hold, 100.0 if prev_on else 0.0))
    vis.append((round(dur, 3), 0.0))
    return vis


def _budget_sfx_cues(cues: List[Dict[str, Any]], *, max_cues: int) -> List[Dict[str, Any]]:
    """Keep SFX crisp and spacious: drop overly close overlaps (<0.35s) and honor duration cap."""
    ordered = sorted(cues, key=lambda c: float(c.get("time", 0.0)))
    spaced: List[Dict[str, Any]] = []
    for c in ordered:
        t = float(c.get("time", 0.0))
        is_bed = "sea_waves" in str(c.get("cue", ""))
        if is_bed or not spaced or (t - float(spaced[-1].get("time", -9.0))) >= 0.35:
            spaced.append(c)
    if len(spaced) <= max_cues:
        return spaced
    # Evenly keep highest-value cues up to max_cues (preserving ambient bed & climax hits)
    step = len(spaced) / float(max_cues)
    return [spaced[int(i * step)] for i in range(max_cues)]


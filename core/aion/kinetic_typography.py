"""AION Kinetic Typography Compiler & Pre-Shaped Arabic SVG Engine (V6.1).

Supports five production kinetic treatments without ever splitting cursive Arabic characters:
  - `mask_reveal`      : RTL/LTR directional Track Matte wipe + optional accent hairline over intact text.
  - `word_emphasis`    : Intact Arabic sentence with native `layer.setText {range}` accent highlight & scale punch.
  - `impact_title`     : High-contrast display headline with snap-scale settle (`116% -> 98% -> 100%`) + legibility scrim.
  - `documentary_card` : Archival plate with accent rule, optional date/kicker tag, and staggered editorial reveal.
  - `data_callout`     : Prominent tabular metric badge (`metric`) paired with concise Arabic context line.

Includes `build_pre_shaped_arabic_svg()` (`arabic_reshaper` + `python-bidi` + `fontTools` outlines)
for SVG fallback when a target effect or glyph set lacks native renderer support, preserving `source_text`.
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import arabic_reshaper
from bidi.algorithm import get_display
from fontTools.pens.boundsPen import ControlBoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import ImageFont

from core.config.settings import TYPOGRAPHY_FONTS_DIR

_AR_DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")

# Isolated Presentation-Forms-B -> Unicode base mapping for variable fonts that shape via GSUB only
_PFB_TO_BASE: Dict[int, int] = {
    0xFE80: 0x0621, 0xFE81: 0x0622, 0xFE83: 0x0623, 0xFE85: 0x0624,
    0xFE87: 0x0625, 0xFE89: 0x0626, 0xFE8D: 0x0627, 0xFE8F: 0x0628,
    0xFE93: 0x0629, 0xFE95: 0x062A, 0xFE99: 0x062B, 0xFE9D: 0x062C,
    0xFEA1: 0x062D, 0xFEA5: 0x062E, 0xFEA9: 0x062F, 0xFEAB: 0x0630,
    0xFEAD: 0x0631, 0xFEAF: 0x0632, 0xFEB1: 0x0633, 0xFEB5: 0x0634,
    0xFEB9: 0x0635, 0xFEBD: 0x0636, 0xFEC1: 0x0637, 0xFEC5: 0x0638,
    0xFEC9: 0x0639, 0xFECD: 0x063A, 0xFED1: 0x0641, 0xFED5: 0x0642,
    0xFED9: 0x0643, 0xFEDD: 0x0644, 0xFEE1: 0x0645, 0xFEE5: 0x0646,
    0xFEE9: 0x0647, 0xFEED: 0x0648, 0xFEEF: 0x0649, 0xFEF1: 0x064A,
}


def is_rtl_str(text: str) -> bool:
    """Return True if `text` contains Arabic/Hebrew right-to-left script characters."""
    return any("\u0600" <= ch <= "\u06FF" or "\u0750" <= ch <= "\u077F" for ch in (text or ""))


def _xml_escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _find_font_ttf_for_measure(font_family: Optional[str]) -> Optional[Path]:
    """Locate local TTF/variable TTF for Arabic or Latin pixel-width measurement."""
    if font_family:
        slug = re.sub(r"[^A-Za-z0-9_-]", "_", font_family.strip())
        for sub in ("arabic", "latin"):
            fam_dir = TYPOGRAPHY_FONTS_DIR / sub / slug
            if fam_dir.is_dir():
                ttfs = sorted(fam_dir.glob("*.ttf"))
                for fp in ttfs:
                    if "Bold" in fp.name or "[wght]" in fp.name or "[opsz,wght]" in fp.name:
                        return fp
                if ttfs:
                    return ttfs[0]
    try:
        return _find_default_svg_font_path(font_family)
    except Exception:
        return None


def _measure_text_width_px(text: str, font_family: Optional[str], fsize: int, is_rtl: bool) -> float:
    """Measure rendered glyph width in px using reshaped RTL text or native LTR text."""
    if not text:
        return 0.0
    fp = _find_font_ttf_for_measure(font_family)
    if fp and fp.is_file():
        try:
            font_obj = ImageFont.truetype(str(fp), int(max(12, fsize)))
            sample = get_display(arabic_reshaper.reshape(text)) if is_rtl else text
            return float(font_obj.getlength(sample))
        except Exception:
            pass
    vis_chars = len(_AR_DIACRITICS_RE.sub("", text))
    return float(vis_chars) * fsize * (0.47 if is_rtl else 0.56)


def _find_default_svg_font_path(font_family: Optional[str] = None) -> Path:
    """Prefer static TTFs with full Presentation-Forms-B tables (`IBM Plex Sans Arabic`, `Amiri`)."""
    candidates = [
        TYPOGRAPHY_FONTS_DIR / "arabic" / "IBM_Plex_Sans_Arabic" / "IBMPlexSansArabic-Bold.ttf",
        TYPOGRAPHY_FONTS_DIR / "arabic" / "Amiri" / "Amiri-Bold.ttf",
        TYPOGRAPHY_FONTS_DIR / "arabic" / "Tajawal" / "Tajawal-Bold.ttf",
        TYPOGRAPHY_FONTS_DIR / "arabic" / "Almarai" / "Almarai-Bold.ttf",
    ]
    if font_family:
        slug = re.sub(r"[^A-Za-z0-9_-]", "_", font_family.strip())
        fam_dir = TYPOGRAPHY_FONTS_DIR / "arabic" / slug
        if fam_dir.is_dir():
            ttfs = sorted(fam_dir.glob("*.ttf"))
            for fp in ttfs:
                if "Bold" in fp.name:
                    candidates.insert(0, fp)
                    break
            if ttfs:
                candidates.insert(0, ttfs[0])
    for c in candidates:
        if c.is_file():
            tt = TTFont(str(c), lazy=True)
            cmap = tt.getBestCmap() or {}
            # Verify isolated Waw + Heh PF-B coverage for shaped SVG reliability
            if 0xFEED in cmap or 0x0648 in cmap:
                return c
    raise FileNotFoundError("No Arabic TTF available for pre-shaped SVG fallback.")


def build_pre_shaped_arabic_svg(
    source_text: str,
    *,
    font_path: Optional[Path] = None,
    font_family: Optional[str] = None,
    fill_hex: str = "#FFD400",
    font_size: float = 54.0,
    out_svg_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Render connected RTL Arabic text into vector `<svg>` glyph paths while preserving `source_text`."""
    clean_src = str(source_text or "").strip()
    fp = Path(font_path) if font_path and Path(font_path).is_file() else _find_default_svg_font_path(font_family)

    tt = TTFont(str(fp))
    cmap = tt.getBestCmap() or {}
    glyph_set = tt.getGlyphSet()
    hmtx = tt["hmtx"]
    upem = max(256.0, float(tt["head"].unitsPerEm))
    scale = float(font_size) / upem

    # If chosen font lacks Presentation Forms-B glyphs, fall back cleanly to IBM Plex Sans Arabic Bold
    reshaped = arabic_reshaper.reshape(clean_src)
    visual = get_display(reshaped)
    if any(ord(ch) not in cmap and _PFB_TO_BASE.get(ord(ch), ord(ch)) not in cmap for ch in visual if ord(ch) > 127):
        fb = TYPOGRAPHY_FONTS_DIR / "arabic" / "IBM_Plex_Sans_Arabic" / "IBMPlexSansArabic-Bold.ttf"
        if fb.is_file() and fb != fp:
            fp = fb
            tt = TTFont(str(fp))
            cmap = tt.getBestCmap() or {}
            glyph_set = tt.getGlyphSet()
            hmtx = tt["hmtx"]
            upem = max(256.0, float(tt["head"].unitsPerEm))
            scale = float(font_size) / upem

    pen_x = 0.0
    baseline_y = float(font_size) * 1.15
    paths: List[str] = []
    min_x, min_y, max_x, max_y = 1e9, 1e9, -1e9, -1e9

    for ch in visual:
        cp = ord(ch)
        gname = cmap.get(cp) or cmap.get(_PFB_TO_BASE.get(cp, cp))
        if not gname or gname not in glyph_set:
            pen_x += upem * 0.28
            continue
        xform = (scale, 0.0, 0.0, -scale, pen_x * scale, baseline_y)
        sp = SVGPathPen(glyph_set)
        bp = ControlBoundsPen(glyph_set)
        glyph_set[gname].draw(TransformPen(sp, xform))
        glyph_set[gname].draw(TransformPen(bp, xform))
        d = sp.getCommands().strip()
        if d:
            paths.append(f'<path d="{d}" fill="{fill_hex}" stroke="none"/>')
            if bp.bounds:
                bx0, by0, bx1, by1 = bp.bounds
                min_x, min_y = min(min_x, bx0), min(min_y, by0)
                max_x, max_y = max(max_x, bx1), max(max_y, by1)
        adv, _ = hmtx[gname]
        pen_x += float(adv)

    pad = 16.0
    if max_x <= min_x:
        min_x, min_y, max_x, max_y = 0.0, 0.0, max(120.0, pen_x * scale), baseline_y + 12.0
    vx = round(min_x - pad, 1)
    vy = round(min_y - pad, 1)
    vw = round((max_x - min_x) + pad * 2.0, 1)
    vh = round((max_y - min_y) + pad * 2.0, 1)
    esc = _xml_escape(clean_src)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx} {vy} {vw} {vh}" '
        f'width="{int(round(vw))}" height="{int(round(vh))}" data-source-text="{esc}">'
        f'<metadata><source_text>{esc}</source_text><font>{fp.stem}</font></metadata>'
        f'{"".join(paths)}</svg>'
    )
    if out_svg_path is not None:
        Path(out_svg_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_svg_path).write_text(svg, encoding="utf-8")

    return {
        "source_text": clean_src,
        "font_used": fp.stem,
        "svg": svg,
        "width": vw,
        "height": vh,
        "svg_path": str(out_svg_path) if out_svg_path else None,
        "svg_sha256": hashlib.sha256(svg.encode("utf-8")).hexdigest()[:16],
    }


def _fade_out_cmds(cmds: List[Dict[str, Any]], layer: str, st: float, en: float, comp_dur: float, fade: float = 0.08) -> None:
    if en >= comp_dur - 0.12 or (en - st) <= fade * 1.8:
        return
    t0 = round(max(st + 0.05, en - fade), 3)
    cmds.append({"command": "prop.addKey", "params": {"layer": layer, "path": "transform/opacity", "time": t0, "timeBase": "comp", "value": 100.0}})
    cmds.append({"command": "prop.addKey", "params": {"layer": layer, "path": "transform/opacity", "time": round(en, 3), "timeBase": "comp", "value": 0.0}})


def _append_neon_border_cmds(
    cmds: List[Dict[str, Any]],
    *,
    tid: str,
    kind: str,
    size: List[float],
    position: List[float],
    stroke_hex: str,
    st: float,
    en: float,
    comp_duration: float,
    tb: Dict[str, Any],
    scale_keyframes: Optional[List[Tuple[float, List[float]]]] = None,
    pulse_time: Optional[float] = None,
) -> None:
    """Add dual-pass Neon Glass HUD border glow (wide soft bloom + crisp neon core rim + pulse)."""
    bloom_name = f"TextCardBloom_{tid}"
    rim_name = f"TextCardGlow_{tid}"
    base_rad = float(tb.get("neon_radius", 26.0))
    base_int = min(0.95, float(tb.get("neon_intensity", 0.90)))
    layers_cfg = [
        (bloom_name, float(tb.get("neon_bloom_w", 2.5)), round(base_int * 0.62, 2), round(base_rad * 1.35, 1), True),
        (rim_name, float(tb.get("neon_stroke_w", 3.6)), base_int, round(base_rad * 0.48, 1), False),
    ]
    for gname, sw, g_int, g_rad, do_pulse in layers_cfg:
        cmds.append({
            "command": "layer.newShape",
            "params": {
                "kind": kind,
                "name": gname,
                "size": size,
                "position": position,
                "fill": stroke_hex,
                "fillOpacity": 0.0,
                "stroke": stroke_hex,
                "strokeWidth": sw,
            },
        })
        cmds.append({"command": "layer.timing", "params": {"layers": [gname], "in": st, "out": en}})
        cmds.append({"command": "effect.apply", "params": {"layers": [gname], "effect": "ec.stylize.glow"}})
        cmds.append({"command": "prop.set", "params": {"layer": gname, "path": "effects/#1/intensity", "value": g_int}})
        if do_pulse and pulse_time and pulse_time + 0.35 < en:
            cmds.append({"command": "prop.addKey", "params": {"layer": gname, "path": "effects/#1/radius", "time": round(max(st, pulse_time - 0.04), 3), "timeBase": "comp", "value": g_rad}})
            cmds.append({"command": "prop.addKey", "params": {"layer": gname, "path": "effects/#1/radius", "time": round(pulse_time + 0.14, 3), "timeBase": "comp", "value": round(g_rad * 1.45, 1)}})
            cmds.append({"command": "prop.addKey", "params": {"layer": gname, "path": "effects/#1/radius", "time": round(pulse_time + 0.40, 3), "timeBase": "comp", "value": g_rad}})
        else:
            cmds.append({"command": "prop.set", "params": {"layer": gname, "path": "effects/#1/radius", "value": g_rad}})
        if scale_keyframes:
            for kt, sval in scale_keyframes:
                cmds.append({"command": "prop.addKey", "params": {"layer": gname, "path": "transform/scale", "time": kt, "timeBase": "comp", "value": sval}})
        else:
            cmds.append({"command": "prop.addKey", "params": {"layer": gname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 35.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": gname, "path": "transform/opacity", "time": round(min(en, st + 0.18), 3), "timeBase": "comp", "value": 100.0}})
        _fade_out_cmds(cmds, gname, st, en, comp_duration)


def _append_live_typing_cmds(
    cmds: List[Dict[str, Any]],
    *,
    tid: str,
    layer: str,
    text_val: str,
    t_start: float,
    t_end: float,
    en: float,
    font_family: str,
    fsize: int,
    pos: List[float],
    is_rtl: bool,
    accent_hex: str,
    show_caret: bool = True,
) -> None:
    """Animate progressive RTL/LTR live typing via `text/sourceText` + pixel-tracked glowing caret."""
    indices = [i for i, ch in enumerate(text_val, 1) if not ch.isspace()]
    if not indices:
        return
    if indices[-1] != len(text_val):
        indices.append(len(text_val))
    span = max(0.28, t_end - t_start)
    total_steps = len(indices)

    cur_name = f"TextCursor_{tid}"
    if show_caret:
        cur_end = round(min(en - 0.04, t_end + 0.42), 3)
        start_x = round(pos[0] + (10.0 if is_rtl else -10.0), 1)
        cmds.append({
            "command": "layer.newShape",
            "params": {
                "kind": "rect",
                "name": cur_name,
                "size": [3.5, round(fsize * 0.90, 1)],
                "position": [start_x, pos[1]],
                "fill": accent_hex,
                "stroke": False,
            },
        })
        cmds.append({"command": "effect.apply", "params": {"layers": [cur_name], "effect": "ec.stylize.glow"}})
        cmds.append({"command": "prop.set", "params": {"layer": cur_name, "path": "effects/#1/intensity", "value": 0.92}})
        cmds.append({"command": "prop.set", "params": {"layer": cur_name, "path": "effects/#1/radius", "value": 10.0}})
        cmds.append({"command": "layer.timing", "params": {"layers": [cur_name], "in": round(max(0.0, t_start - 0.02), 3), "out": cur_end}})

    for step_idx, char_end in enumerate(indices, 1):
        tk = round(t_start + (step_idx / float(total_steps)) * span, 3)
        sub_str = text_val[:char_end]
        cmds.append({
            "command": "prop.addKey",
            "params": {
                "layer": layer,
                "path": "text/sourceText",
                "time": tk,
                "timeBase": "comp",
                "value": sub_str,
            },
        })
        if show_caret:
            w_sub = _measure_text_width_px(sub_str, font_family, fsize, is_rtl)
            offset_x = (w_sub * 0.5) + 12.0
            cx_cur = round(pos[0] - offset_x if is_rtl else pos[0] + offset_x, 1)
            cmds.append({
                "command": "prop.addKey",
                "params": {"layer": cur_name, "path": "transform/position", "time": tk, "timeBase": "comp", "value": [cx_cur, pos[1], 0.0]},
            })

    if show_caret and t_end + 0.10 < en:
        cur_end = round(min(en - 0.04, t_end + 0.42), 3)
        mid1 = round(min(cur_end - 0.08, t_end + 0.14), 3)
        mid2 = round(min(cur_end - 0.04, t_end + 0.28), 3)
        cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/opacity", "time": round(t_end + 0.02, 3), "timeBase": "comp", "value": 100.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/opacity", "time": mid1, "timeBase": "comp", "value": 15.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/opacity", "time": mid2, "timeBase": "comp", "value": 100.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/opacity", "time": cur_end, "timeBase": "comp", "value": 0.0}})


def _resolve_word_char_range(text: str, highlight_word: Optional[str]) -> Optional[Tuple[int, int]]:
    """Find whole-word UTF-16/char indices inside `text` so Arabic letter ligatures inside a word never break."""
    if not text:
        return None
    if highlight_word:
        idx = text.find(highlight_word)
        if idx >= 0:
            return (idx, idx + len(highlight_word))
    # Fallback: pick longest meaningful token (>= 4 chars) inside a multi-word string
    words = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", text)]
    if len(words) < 2:
        return None
    # Prefer middle/final punch word
    best = max(words[1:], key=lambda x: len(_AR_DIACRITICS_RE.sub("", x[2])))
    if len(best[2]) >= 3:
        return (best[0], best[1])
    return None


def _estimate_card_dims(text: str, fsize: int, comp_width: int, tb: Dict[str, Any]) -> Tuple[int, int]:
    vis_chars = len(_AR_DIACRITICS_RE.sub("", text))
    box = tb.get("box")
    if isinstance(box, (list, tuple)) and len(box) == 4:
        bw_inner = float(box[2])
        cw = max(280, min(int(comp_width * 0.88), int(bw_inner + 64)))
        font_name = str(tb.get("font") or "")
        w_factor = 0.56 if font_name in ("Alexandria", "Changa") else 0.49
        est_lines = max(1, min(4, int(math.ceil((vis_chars * fsize * w_factor) / max(180.0, bw_inner)))))
        leading = float(tb.get("leading") or fsize * 1.32)
        content_h = fsize + (est_lines - 1) * leading
        ch = max(fsize + 46, min(int(float(box[3]) + 32), int(content_h + 48)))
        return cw, ch
    cw = int(tb.get("pill_w", max(320, min(int(comp_width * 0.84), int(vis_chars * fsize * 0.52 + 108)))))
    ch = int(tb.get("pill_h", fsize + 46))
    return cw, ch


def _text_pos_and_box(
    tb: Dict[str, Any],
    pos: List[float],
    fsize: int,
    cw: int,
    ch: int,
    with_backdrop: bool,
) -> Tuple[Dict[str, Any], List[float]]:
    box = tb.get("box")
    if isinstance(box, (list, tuple)) and len(box) == 4:
        bw = float(box[2])
        vis_chars = len(_AR_DIACRITICS_RE.sub("", str(tb.get("text", ""))))
        font_name = str(tb.get("font") or "")
        w_factor = 0.56 if font_name in ("Alexandria", "Changa") else 0.49
        est_lines = max(1, min(4, int(math.ceil((vis_chars * fsize * w_factor) / max(180.0, bw)))))
        leading = float(tb.get("leading") or fsize * 1.32)
        content_h = fsize + (est_lines - 1) * leading
        # Align card center cleanly around the visual center of the paragraph box
        top_y = float(pos[1]) - ch * (0.38 if est_lines == 1 else 0.44)
        card_center_y = top_y + content_h * 0.50 + 4.0
        return (
            {"box": [round(float(box[0]), 1), round(top_y, 1), round(bw, 1), round(max(float(box[3]), content_h + 40.0), 1)]},
            [float(pos[0]), round(card_center_y, 1)],
        )
    txt_y = float(pos[1]) + fsize * 0.30 if with_backdrop else float(pos[1])
    return {"position": [round(float(pos[0]), 1), round(txt_y, 1)]}, pos


def compile_kinetic_text_block(
    tb: Dict[str, Any],
    *,
    comp_width: int,
    comp_height: int,
    comp_duration: float,
    comp_name: str,
    work_dir: Optional[Path] = None,
    ease_keys: Optional[List[Dict[str, Any]]] = None,
    palette: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Compile a single Scene Graph typography block into EffectCraft CLI commands."""
    cmds: List[Dict[str, Any]] = []
    ease = ease_keys if ease_keys is not None else []
    pal = palette or {}

    text_val = str(tb.get("text", "")).strip()
    if not text_val:
        return cmds

    tid = str(tb.get("id", "typo_0"))
    tname = f"Text_{tid}"
    st = max(0.0, float(tb.get("start", tb.get("in", 0.0))))
    en = min(comp_duration, float(tb.get("end", tb.get("out", comp_duration))))
    if en <= st:
        en = min(comp_duration, st + 1.0)

    pos = [float(x) for x in tb.get("position", tb.get("pos", [comp_width * 0.5, min(220.0, comp_height * 0.14)]))]
    fsize = int(tb.get("size", 46))
    rtl = is_rtl_str(text_val) if tb.get("direction", "auto") == "auto" else (str(tb.get("direction")).lower() == "rtl")
    font = str(tb.get("font") or ("Cairo" if rtl else "Inter"))
    style_name = str(tb.get("font_style") or tb.get("style") or "Bold")
    anim_mode = str(tb.get("animation_mode") or tb.get("role") or "pill_pop").lower()
    with_backdrop = bool(tb.get("with_backdrop", tb.get("pill", True)))
    fill_hex = str(tb.get("color", pal.get("text", "#F8FAFC")))
    bg_hex = str(tb.get("backdrop_fill", tb.get("pill_bg", pal.get("surface", "#1E293B"))))
    stroke_hex = str(tb.get("backdrop_stroke", tb.get("pill_border", pal.get("accent", "#FFD400"))))
    accent_hex = str(tb.get("accent_color", stroke_hex))
    neon_border = bool(tb.get("neon_border", False))
    live_typing = bool(tb.get("live_typing", False)) or (anim_mode in ("live_typing", "neon_live_typing"))
    if anim_mode == "neon_live_typing":
        neon_border = True
        with_backdrop = True
    if with_backdrop and neon_border and fill_hex.upper() in ("#0F172A", "#1E293B", "#111827", "#000000"):
        fill_hex = "#F8FAFC"
    # Use pixel-accurate text width measurement when live_typing / neon_border is active so the card fits snugly
    if live_typing or neon_border:
        measured_w = _measure_text_width_px(text_val, font, fsize, rtl)
        cw = int(tb.get("pill_w", max(320, min(int(comp_width * 0.84), int(round(measured_w + 116))))))
        ch = int(tb.get("pill_h", fsize + 46))
    else:
        cw, ch = _estimate_card_dims(text_val, fsize, comp_width, tb)

    # SVG Pre-Shaped Fallback path when requested or font is incompatible with native text layer
    if str(tb.get("render_backend", "native")).lower() == "svg_fallback":
        svg_out = Path(work_dir) / f"svg_typo_{tid}.svg" if work_dir else None
        svg_info = build_pre_shaped_arabic_svg(text_val, font_family=font, fill_hex=fill_hex, font_size=float(fsize), out_svg_path=svg_out)
        if with_backdrop:
            pname = f"TextCard_{tid}"
            cmds.append({"command": "layer.newShape", "params": {"kind": "rounded", "name": pname, "size": [cw, ch], "position": pos, "fill": bg_hex, "fillOpacity": float(tb.get("pill_opacity", 92.0)), "stroke": stroke_hex, "strokeWidth": float(tb.get("border_w", 3.5))}})
            cmds.append({"command": "layer.timing", "params": {"layers": [pname], "in": st, "out": en}})
            _fade_out_cmds(cmds, pname, st, en, comp_duration)
        sname = f"SvgText_{tid}"
        cmds.append({"command": "edit.pasteSvg", "params": {"name": sname, "comp": comp_name, "svg": svg_info["svg"]}})
        cmds.append({"command": "prop.set", "params": {"layer": sname, "path": "transform/position", "value": [pos[0], pos[1], 0.0]}})
        cmds.append({"command": "layer.timing", "params": {"layers": [sname], "in": st, "out": en}})
        _fade_out_cmds(cmds, sname, st, en, comp_duration)
        return cmds

    placement, card_pos = _text_pos_and_box(tb, pos, fsize, cw, ch, with_backdrop)

    # 1. DOCUMENTARY CARD — Archival plate + accent spine + optional date kicker + headline
    if anim_mode == "documentary_card":
        kicker = str(tb.get("kicker", "")).strip()
        card_h = max(ch + (68 if kicker else 20), fsize + (110 if kicker else 56))
        card_w = max(cw + 48, 460) if neon_border else min(int(comp_width * 0.88), max(cw, int(comp_width * (0.76 if comp_width < comp_height else 0.56))))
        pname = f"TextCard_{tid}"
        cmds.append({
            "command": "layer.newShape",
            "params": {
                "kind": "rect",
                "name": pname,
                "size": [card_w, card_h],
                "position": card_pos,
                "fill": bg_hex,
                "fillOpacity": float(tb.get("pill_opacity", 94.0)),
                "stroke": stroke_hex,
                "strokeWidth": 2.5,
            },
        })
        cmds.append({"command": "layer.timing", "params": {"layers": [pname], "in": st, "out": en}})
        cmds.append({"command": "prop.addKey", "params": {"layer": pname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 40.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": pname, "path": "transform/opacity", "time": round(min(en, st + 0.16), 3), "timeBase": "comp", "value": 100.0}})
        _fade_out_cmds(cmds, pname, st, en, comp_duration)
        if neon_border:
            _append_neon_border_cmds(
                cmds, tid=tid, kind="rect", size=[card_w, card_h], position=card_pos,
                stroke_hex=stroke_hex, st=st, en=en, comp_duration=comp_duration, tb=tb,
            )

        # Vertical accent spine bar on reading side (right edge for RTL, left edge for LTR)
        bar_name = f"DocSpine_{tid}"
        bar_x = card_pos[0] + card_w * 0.5 - 8.0 if rtl else card_pos[0] - card_w * 0.5 + 8.0
        cmds.append({
            "command": "layer.newShape",
            "params": {"kind": "rect", "name": bar_name, "size": [10, card_h], "position": [round(bar_x, 1), card_pos[1]], "fill": accent_hex, "strokeType": "none"},
        })
        cmds.append({"command": "layer.timing", "params": {"layers": [bar_name], "in": st, "out": en}})
        cmds.append({"command": "prop.addKey", "params": {"layer": bar_name, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [100.0, 20.0, 100.0]}})
        cmds.append({"command": "prop.addKey", "params": {"layer": bar_name, "path": "transform/scale", "time": round(min(en, st + 0.22), 3), "timeBase": "comp", "value": [100.0, 100.0, 100.0]}})
        ease.extend([{"layer": bar_name, "path": "transform/scale", "time": st}, {"layer": bar_name, "path": "transform/scale", "time": round(min(en, st + 0.22), 3)}])
        _fade_out_cmds(cmds, bar_name, st, en, comp_duration)

        if kicker:
            kname = f"TextKicker_{tid}"
            cmds.append({
                "command": "layer.newText",
                "params": {
                    "name": kname,
                    "text": kicker,
                    "font": str(tb.get("kicker_font") or font),
                    "style": "SemiBold" if font == "IBM Plex Sans Arabic" else "Bold",
                    "size": max(24, int(fsize * 0.54)),
                    "fill": accent_hex,
                    "direction": "rtl" if is_rtl_str(kicker) else "ltr",
                    "justify": "center",
                    "position": [card_pos[0], round(card_pos[1] - card_h * 0.21, 1)],
                },
            })
            cmds.append({"command": "layer.timing", "params": {"layers": [kname], "in": round(st + 0.03, 3), "out": en}})
            _fade_out_cmds(cmds, kname, st + 0.03, en, comp_duration)

        title_y = card_pos[1] + (fsize * 0.48 if kicker else fsize * 0.28)
        title_font = str(tb.get("display_font") or font)
        init_doc_txt = text_val[0] if (live_typing and len(text_val) > 1) else text_val
        cmds.append({
            "command": "layer.newText",
            "params": {
                "name": tname,
                "text": init_doc_txt,
                "font": title_font,
                "style": "Bold",
                "size": fsize,
                "fill": fill_hex,
                "direction": "rtl" if rtl else "ltr",
                "justify": "center",
                "position": [card_pos[0], round(title_y, 1)],
            },
        })
        t_in = round(st + 0.04, 3)
        cmds.append({"command": "layer.timing", "params": {"layers": [tname], "in": t_in, "out": en}})
        if live_typing and len(text_val) > 1:
            type_end = round(min(en - 0.15, t_in + min(1.05, max(0.48, (en - t_in) * 0.28))), 3)
            cur_y = round(title_y - fsize * 0.30, 1)
            _append_live_typing_cmds(
                cmds, tid=tid, layer=tname, text_val=text_val, t_start=t_in, t_end=type_end, en=en,
                font_family=title_font, fsize=fsize, pos=[card_pos[0], cur_y], is_rtl=rtl,
                accent_hex=stroke_hex, show_caret=bool(tb.get("show_caret", True)),
            )
        else:
            cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": t_in, "timeBase": "comp", "value": 40.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": round(min(en, t_in + 0.16), 3), "timeBase": "comp", "value": 100.0}})
        _fade_out_cmds(cmds, tname, t_in, en, comp_duration)
        return cmds

    # 2. DATA CALLOUT — Metric/stat badge + Arabic explanation label
    if anim_mode == "data_callout":
        metric = str(tb.get("metric", "")).strip()
        if not metric:
            m_num = re.search(r"[+\-]?\d[\d.,:%]*|[\u0660-\u0669]+", text_val)
            metric = m_num.group(0) if m_num else ""
        # Avoid repeating standalone year/metric (including Arabic-Indic vs ASCII digits) at start of label
        def _norm_d(s: str) -> str:
            return s.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
        lbl_text = text_val
        if metric and _norm_d(lbl_text).startswith(_norm_d(metric)):
            m_lead = re.match(r"^[+\-]?[0-9\u0660-\u0669.,:%]+\s*(?:قدم|ثانية|ft|feet|percent|seconds?|minutes?)?\s*[—\-–:\s]*", lbl_text, re.IGNORECASE)
            if m_lead and len(lbl_text[m_lead.end():].strip().split()) >= 2:
                lbl_text = lbl_text[m_lead.end():].strip()
        pname = f"TextCard_{tid}"
        card_w = min(int(comp_width * 0.88), max(cw + (140 if metric else 40), 420))
        card_h = max(ch + 62, fsize * 2 + 56 if metric else fsize + 52)
        cmds.append({
            "command": "layer.newShape",
            "params": {"kind": "rounded", "name": pname, "size": [card_w, card_h], "position": card_pos, "fill": bg_hex, "fillOpacity": 94.0, "stroke": stroke_hex, "strokeWidth": 3.5},
        })
        cmds.append({"command": "layer.timing", "params": {"layers": [pname], "in": st, "out": en}})
        cmds.append({"command": "prop.addKey", "params": {"layer": pname, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [76.0, 76.0, 100.0]}})
        cmds.append({"command": "prop.addKey", "params": {"layer": pname, "path": "transform/scale", "time": round(min(en, st + 0.24), 3), "timeBase": "comp", "value": [100.0, 100.0, 100.0]}})
        ease.extend([{"layer": pname, "path": "transform/scale", "time": st}, {"layer": pname, "path": "transform/scale", "time": round(min(en, st + 0.24), 3)}])
        _fade_out_cmds(cmds, pname, st, en, comp_duration)

        if metric:
            mname = f"TextMetric_{tid}"
            cmds.append({
                "command": "layer.newText",
                "params": {
                    "name": mname, "text": metric, "font": str(tb.get("metric_font") or font), "style": "Bold",
                    "size": int(fsize * 1.12), "fill": accent_hex, "direction": "ltr", "justify": "center",
                    "position": [card_pos[0], round(card_pos[1] - fsize * 0.04, 1)],
                },
            })
            cmds.append({"command": "layer.timing", "params": {"layers": [mname], "in": round(st + 0.04, 3), "out": en}})
            _fade_out_cmds(cmds, mname, st + 0.04, en, comp_duration)

        lbl_y = card_pos[1] + (fsize * 0.72 if metric else fsize * 0.28)
        cmds.append({
            "command": "layer.newText",
            "params": {
                "name": tname, "text": lbl_text, "font": font, "style": style_name,
                "size": max(32, int(fsize * 0.76)) if metric else fsize, "fill": fill_hex,
                "direction": "rtl" if rtl else "ltr", "justify": "center",
                "position": [card_pos[0], round(lbl_y, 1)],
            },
        })
        cmds.append({"command": "layer.timing", "params": {"layers": [tname], "in": round(st + 0.08, 3), "out": en}})
        _fade_out_cmds(cmds, tname, st + 0.08, en, comp_duration)
        return cmds

    # Optional rounded card backdrop for pill_pop, impact_title, word_emphasis, mask_reveal, live_typing, neon_live_typing
    type_st = round(min(en - 0.30, st + 0.08), 3)
    type_en = round(min(en - 0.15, type_st + min(1.00, max(0.45, (en - st) * 0.26))), 3)
    if with_backdrop:
        pname = f"TextCard_{tid}"
        cmds.append({
            "command": "layer.newShape",
            "params": {
                "kind": "rounded",
                "name": pname,
                "size": [cw, ch],
                "position": card_pos,
                "fill": bg_hex,
                "fillOpacity": float(tb.get("pill_opacity", 84.0 if neon_border else 92.0)),
                "stroke": stroke_hex,
                "strokeWidth": float(tb.get("border_w", 1.8 if neon_border else 3.5)),
            },
        })
        cmds.append({"command": "layer.timing", "params": {"layers": [pname], "in": st, "out": en}})
        if neon_border:
            cmds.append({"command": "effect.apply", "params": {"layers": [pname], "effect": "ec.perspective.dropshadow"}})
            cmds.append({"command": "prop.set", "params": {"layer": pname, "path": "effects/#1/opacity", "value": 60.0}})
            cmds.append({"command": "prop.set", "params": {"layer": pname, "path": "effects/#1/distance", "value": 10.0}})
            cmds.append({"command": "prop.set", "params": {"layer": pname, "path": "effects/#1/softness", "value": 24.0}})
        if anim_mode == "impact_title":
            card_kfs = [
                (st, [116.0, 116.0, 100.0]),
                (round(min(en, st + 0.18), 3), [98.0, 98.0, 100.0]),
                (round(min(en, st + 0.28), 3), [100.0, 100.0, 100.0]),
            ]
        else:
            card_kfs = [
                (st, [80.0, 88.0, 100.0]),
                (round(min(en, st + 0.16), 3), [103.0, 102.0, 100.0]),
                (round(min(en, st + 0.26), 3), [100.0, 100.0, 100.0]),
            ]
        for kt, sval in card_kfs:
            cmds.append({"command": "prop.addKey", "params": {"layer": pname, "path": "transform/scale", "time": kt, "timeBase": "comp", "value": sval}})
        ease.extend([
            {"layer": pname, "path": "transform/scale", "time": st},
            {"layer": pname, "path": "transform/scale", "time": card_kfs[-1][0]},
        ])
        _fade_out_cmds(cmds, pname, st, en, comp_duration)
        if neon_border:
            _append_neon_border_cmds(
                cmds, tid=tid, kind="rounded", size=[cw, ch], position=card_pos,
                stroke_hex=stroke_hex, st=st, en=en, comp_duration=comp_duration, tb=tb,
                scale_keyframes=card_kfs, pulse_time=type_en if live_typing else None,
            )

    # Core text layer (single intact string preserves 100% Arabic contextual cursive shaping)
    init_text = text_val[0] if (live_typing and len(text_val) > 1) else text_val
    text_params: Dict[str, Any] = {
        "name": tname,
        "text": init_text,
        "font": font,
        "style": style_name,
        "size": fsize,
        "fill": fill_hex,
        "direction": "rtl" if rtl else "ltr",
        "justify": "center",
        **placement,
    }
    if tb.get("leading"):
        text_params["leading"] = int(tb["leading"])
    if not with_backdrop and bool(tb.get("outline", False)):
        text_params["applyStroke"] = True
        text_params["stroke"] = "#020617"
        text_params["strokeWidth"] = float(tb.get("outline_w", 2.0))
        text_params["strokeOverFill"] = False
    cmds.append({"command": "layer.newText", "params": text_params})
    t_in = round(st, 3)
    cmds.append({"command": "layer.timing", "params": {"layers": [tname], "in": t_in, "out": en}})

    # Live Typing mode (character-by-character native HarfBuzz shaping via sourceText + glowing caret)
    if live_typing and len(text_val) > 1:
        _append_live_typing_cmds(
            cmds, tid=tid, layer=tname, text_val=text_val, t_start=type_st, t_end=type_en, en=en,
            font_family=font, fsize=fsize, pos=card_pos, is_rtl=rtl,
            accent_hex=stroke_hex, show_caret=bool(tb.get("show_caret", True)),
        )
        _fade_out_cmds(cmds, tname, t_in, en, comp_duration)
        return cmds

    # 3. MASK REVEAL — Alpha Track Matte directional RTL/LTR reveal (zero broken ligatures!)
    if anim_mode == "mask_reveal":
        matte_name = f"TextMatte_{tid}"
        wipe_w = max(cw + 120, 620)
        wipe_h = max(ch + 80, fsize * 3)
        start_offset = wipe_w if rtl else -wipe_w
        cmds.append({
            "command": "layer.newShape",
            "params": {"kind": "rect", "name": matte_name, "size": [wipe_w, wipe_h], "position": [card_pos[0] + start_offset, card_pos[1]], "fill": "#FFFFFF", "strokeType": "none"},
        })
        cmds.append({"command": "layer.timing", "params": {"layers": [matte_name], "in": st, "out": en}})
        wipe_end = round(min(en, t_in + min(0.24, max(0.18, (en - t_in) * 0.18))), 3)
        cmds.append({"command": "prop.addKey", "params": {"layer": matte_name, "path": "transform/position", "time": t_in, "timeBase": "comp", "value": [card_pos[0] + start_offset, card_pos[1], 0.0]}})
        cmds.append({"command": "prop.addKey", "params": {"layer": matte_name, "path": "transform/position", "time": wipe_end, "timeBase": "comp", "value": [card_pos[0], card_pos[1], 0.0]}})
        ease.extend([{"layer": matte_name, "path": "transform/position", "time": t_in}, {"layer": matte_name, "path": "transform/position", "time": wipe_end}])
        cmds.append({"command": "layer.setTrackMatte", "params": {"layer": tname, "matte": matte_name, "kind": "alpha"}})

    # 4. WORD EMPHASIS — Whole-word character range highlight + bolder style
    elif anim_mode == "word_emphasis":
        rng = tb.get("highlight_range") or _resolve_word_char_range(text_val, tb.get("highlight_word"))
        if rng and len(rng) == 2:
            emph_params: Dict[str, Any] = {
                "layer": tname,
                "range": [int(rng[0]), int(rng[1])],
                "fill": accent_hex,
                "size": int(round(fsize * 1.12)),
            }
            if tb.get("emphasis_style"):
                emph_params["style"] = str(tb["emphasis_style"])
            cmds.append({"command": "layer.setText", "params": emph_params})
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": t_in, "timeBase": "comp", "value": 86.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": round(min(en, t_in + 0.08), 3), "timeBase": "comp", "value": 100.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/scale", "time": t_in, "timeBase": "comp", "value": [92.0, 92.0, 100.0]}})
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/scale", "time": round(min(en, t_in + 0.22), 3), "timeBase": "comp", "value": [100.0, 100.0, 100.0]}})

    # 5. IMPACT TITLE — Snap entrance on display text
    elif anim_mode == "impact_title":
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": t_in, "timeBase": "comp", "value": 88.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": round(min(en, t_in + 0.08), 3), "timeBase": "comp", "value": 100.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/scale", "time": t_in, "timeBase": "comp", "value": [110.0, 110.0, 100.0]}})
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/scale", "time": round(min(en, t_in + 0.22), 3), "timeBase": "comp", "value": [100.0, 100.0, 100.0]}})
        ease.extend([{"layer": tname, "path": "transform/scale", "time": t_in}, {"layer": tname, "path": "transform/scale", "time": round(min(en, t_in + 0.22), 3)}])

    # 6. WORD SLIDE (preserved word-level RangeSelector with RTL ligature lock basedOn=2)
    elif anim_mode in ("word_slide", "kinetic_words"):
        cmds.append({"command": "layer.addTextAnimator", "params": {"layer": tname, "properties": ["opacity", "position"]}})
        based_on = 2 if rtl else int(tb.get("animator_based_on", 0))
        cmds.append({"command": "prop.set", "params": {"layer": tname, "path": "text/animators/animator/selectors/rangeSelector/advanced/basedOn", "value": based_on}})
        cmds.append({"command": "prop.set", "params": {"layer": tname, "path": "text/animators/animator/properties/opacity", "value": 0.0}})
        cmds.append({"command": "prop.set", "params": {"layer": tname, "path": "text/animators/animator/properties/position", "value": [0, 10, 0]}})
        anim_end = min(en, t_in + min(0.30, max(0.18, (en - t_in) * 0.25)))
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "text/animators/animator/selectors/rangeSelector/start", "time": t_in, "timeBase": "comp", "value": 0.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "text/animators/animator/selectors/rangeSelector/start", "time": round(anim_end, 3), "timeBase": "comp", "value": 100.0}})

    # 7. PILL POP / DEFAULT — Crisp scale & opacity settle inside backing pill
    else:
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": t_in, "timeBase": "comp", "value": 88.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": round(min(en, t_in + 0.08), 3), "timeBase": "comp", "value": 100.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/scale", "time": t_in, "timeBase": "comp", "value": [92.0, 92.0, 100.0]}})
        cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/scale", "time": round(min(en, t_in + 0.20), 3), "timeBase": "comp", "value": [100.0, 100.0, 100.0]}})

    _fade_out_cmds(cmds, tname, t_in, en, comp_duration)
    return cmds

"""AION Pipeline Contracts & Scene Graph Validation Helpers (V1 & V2)."""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

PIPELINE_STAGES: List[str] = [
    "script",
    "voice",
    "timing",
    "extract",
    "semantic-map",
    "brief",
    "direct",
    "motion",
    "sfx",
    "render",
    "qa",
    "merge",
]

SECTION_STAGES: List[str] = PIPELINE_STAGES[:-1]

SCENE_GRAPH_V1 = "aion.scene_graph.v1"
SCENE_GRAPH_V2 = "aion.scene_graph.v2"

REQUIRED_V2_SECTIONS: Tuple[str, ...] = (
    "narrative_intent",
    "asset_references",
    "visual_metaphor",
    "composition",
    "procedural_graphics",
    "motion_paths",
    "camera",
    "lighting",
    "vfx",
    "typography",
    "sfx",
    "timing_anchors",
    "tool_requirements",
    "fallbacks",
    "quality_constraints",
)


def _hex_luma(hex_c: str) -> float:
    h = (hex_c or "#141820").lstrip("#")
    if len(h) != 6:
        return 128.0
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def bg_hex_at(background_timeline: List[Dict[str, Any]], t: float) -> str:
    if not background_timeline:
        return "#F2EDE4"
    cur = background_timeline[0]
    for b in background_timeline:
        if float(b.get("time", 0.0)) <= t + 0.05:
            cur = b
    return str(cur.get("c1", "#F2EDE4"))


def audit_scene_graph(sg: Dict[str, Any], auto_fix: bool = False) -> Tuple[bool, List[str]]:
    """Checks AION scene_graph.json invariants (timing bounds, card contrast, Glow blowout)."""
    issues: List[str] = []
    if "source_timeline" not in sg or "audio_file" not in sg["source_timeline"]:
        issues.append("ERROR: missing source_timeline.audio_file")
    if not isinstance(sg.get("scenes"), list) or not sg["scenes"]:
        issues.append("ERROR: scenes must be a non-empty list")

    dur = float(sg.get("source_timeline", {}).get("duration_sec", 0.0) or 0.0)
    bg_tl = sg.get("background_timeline", [])

    for sc in sg.get("scenes", []):
        for asset in sc.get("assets", []):
            aid = asset.get("id", "?")
            st = float(asset.get("in", 0.0))
            en = float(asset.get("out", 0.0))
            if en <= st:
                issues.append(f"ERROR: {aid} invalid timing [{st}..{en}]")
            if dur > 0 and en > dur + 0.25:
                issues.append(f"WARN: {aid} out={en} exceeds audio duration={dur:.2f}s")

            # Contrast check against dominant midpoint of asset visibility (avoids boundary 0.1s false positives)
            mid_t = st + min(0.8, max(0.1, (en - st) * 0.45))
            bg_hex = bg_hex_at(bg_tl, mid_t)
            is_dark = _hex_luma(bg_hex) < 120.0
            cs = asset.get("card_style")
            if cs == "warm" and is_dark:
                msg = f"CONTRAST: {aid} uses warm card on dark bg {bg_hex} at t={mid_t:.2f}s"
                if auto_fix:
                    asset["card_style"] = "dark_crimson" if int(bg_hex.lstrip("#")[0:2], 16) > int(bg_hex.lstrip("#")[4:6], 16) else "arctic"
                    issues.append(f"FIXED {msg} -> {asset['card_style']}")
                else:
                    issues.append(f"WARN: {msg}")
            elif cs in ("dark_crimson", "arctic", "amber") and not is_dark:
                msg = f"CONTRAST: {aid} uses {cs} card on light bg {bg_hex} at t={mid_t:.2f}s"
                if auto_fix:
                    asset["card_style"] = "warm"
                    issues.append(f"FIXED {msg} -> warm")
                else:
                    issues.append(f"WARN: {msg}")

            # Strong additive Glow blowout check
            for eff in asset.get("effects", []):
                if eff.get("type") == "Glow" and float(eff.get("intensity", 1.0)) >= 1.0:
                    msg = f"BLOWOUT: {aid} has strong Glow (intensity={eff.get('intensity')})"
                    if auto_fix:
                        eff["type"] = "Light Sweep"
                        eff["time"] = round(st + 0.65, 2)
                        eff.setdefault("color", "#FBBF24")
                        issues.append(f"FIXED {msg} -> Light Sweep")
                    else:
                        issues.append(f"WARN: {msg}")

    if is_ecgc_v2_graph(sg):
        _, v2_issues = validate_scene_graph_v2(sg, auto_fix=auto_fix)
        issues.extend(v2_issues)

    has_error = any(x.startswith("ERROR:") for x in issues)
    return (not has_error), issues


def is_ecgc_v2_graph(sg: Dict[str, Any]) -> bool:
    """Distinguish Creative Studio V5 ECGC Scene Graph V2 from legacy V4 hybrid scene_graph.json."""
    return isinstance(sg, dict) and all(k in sg for k in ("narrative_intent", "composition", "procedural_graphics"))


def get_scene_graph_version(sg: Dict[str, Any]) -> str:
    """Return explicit schema version (`aion.scene_graph.v1` or `aion.scene_graph.v2`)."""
    if is_ecgc_v2_graph(sg):
        return SCENE_GRAPH_V2
    return SCENE_GRAPH_V1


def _normalize_typo_entry(entry: Dict[str, Any], idx: int, dur: float, default_dir: str = "rtl") -> Dict[str, Any]:
    """Normalize V1/V2 typography item preserving editorial headline vs subtitle separation."""
    out = dict(entry)
    out.setdefault("id", f"typo_{idx}")
    if "start" not in out and "in" in out:
        out["start"] = float(out["in"])
    if "end" not in out and "out" in out:
        out["end"] = float(out["out"])
    out.setdefault("start", 0.0)
    out.setdefault("end", dur)
    if "position" not in out and "pos" in out:
        out["position"] = list(out["pos"])
    if "backdrop_fill" not in out and "pill_bg" in out:
        out["backdrop_fill"] = out["pill_bg"]
    if "backdrop_stroke" not in out and "pill_border" in out:
        out["backdrop_stroke"] = out["pill_border"]
    if "with_backdrop" not in out and "pill" in out:
        out["with_backdrop"] = bool(out["pill"])
    out.setdefault("direction", default_dir)
    out.setdefault("role", "editorial_headline")
    out.setdefault("animation_mode", "pill_pop")
    return out


def sync_scene_graph_v2_views(sg: Dict[str, Any]) -> Dict[str, Any]:
    """Keep scene-grouped `scenes[]`, `asset_library`, and flat `asset_references` synchronized."""
    dur = float(sg.get("source_timeline", {}).get("duration_sec", 0.0) or 0.0)
    scenes = sg.get("scenes") or []
    asset_library: Dict[str, Dict[str, Any]] = dict(sg.get("asset_library") or {})

    # Populate library from scenes and/or asset_references
    flattened: List[Dict[str, Any]] = []
    for sc_idx, sc in enumerate(scenes):
        sc_id = str(sc.get("scene_id") or f"scene_{sc_idx + 1:02d}")
        sc.setdefault("scene_id", sc_id)
        sc.setdefault("intent", sc.get("intent") or "concept_reveal")
        sc_assets = sc.get("assets") or []
        for a_idx, a in enumerate(sc_assets):
            src_id = str(a.get("asset_id") or a.get("id") or f"asset_{a_idx}")
            inst_id = str(a.get("instance_id") or a.get("id") or f"{sc_id}_{src_id}_{a_idx}")
            if src_id not in asset_library:
                asset_library[src_id] = {
                    "asset_id": src_id,
                    "path": a.get("path"),
                    "icon": a.get("icon"),
                }
            elif not asset_library[src_id].get("path") and a.get("path"):
                asset_library[src_id]["path"] = a.get("path")

            ref = copy.deepcopy(a)
            ref["id"] = inst_id
            ref["asset_id"] = src_id
            ref["scene_id"] = sc_id
            if "path" not in ref and asset_library[src_id].get("path"):
                ref["path"] = asset_library[src_id]["path"]
            if "icon" not in ref and asset_library[src_id].get("icon"):
                ref["icon"] = asset_library[src_id]["icon"]
            if "position" not in ref and "pos" in ref:
                ref["position"] = list(ref["pos"])
            ref.setdefault("in", float(sc.get("time", {}).get("start", 0.0)))
            ref.setdefault("out", float(sc.get("time", {}).get("end", dur)))
            flattened.append(ref)

    if flattened:
        sg["asset_references"] = flattened
    elif sg.get("asset_references") and len(scenes) == 1 and not scenes[0].get("assets"):
        # Legacy V2 fallback: reflect flat asset_references back into asset_library
        for ref in sg["asset_references"]:
            src_id = str(ref.get("asset_id") or ref.get("id") or "asset")
            if src_id not in asset_library:
                asset_library[src_id] = {
                    "asset_id": src_id,
                    "path": ref.get("path"),
                    "icon": ref.get("icon"),
                }

    if asset_library:
        sg["asset_library"] = asset_library
    sg.setdefault("subtitles", [])
    sg.setdefault("relationships", [])
    return sg


def migrate_scene_graph_v1_to_v2(
    sg: Dict[str, Any],
    *,
    narrative_intent: str = "concept_reveal",
    visual_metaphor: str = "explanatory_diagram",
    palette: Optional[Dict[str, Any]] = None,
    use_character: bool = False,
) -> Dict[str, Any]:
    """Non-destructively wrap an existing V1 scene graph with V2 Creative Director fields."""
    out = copy.deepcopy(sg)
    dur = float(out.get("source_timeline", {}).get("duration_sec", 0.0) or 0.0)
    scenes = out.get("scenes", [])
    default_dir = str(out.get("text_direction") or "rtl").lower()
    asset_refs: List[Dict[str, Any]] = []
    asset_library: Dict[str, Dict[str, Any]] = {}
    typo_blocks: List[Dict[str, Any]] = []
    subtitle_blocks: List[Dict[str, Any]] = []
    vfx_blocks: List[Dict[str, Any]] = []
    sfx_blocks: List[Dict[str, Any]] = []
    anchors: List[Dict[str, Any]] = []
    motion_paths: List[Dict[str, Any]] = []
    proc_graphics: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []

    for sc_idx, sc in enumerate(scenes):
        sc_id = sc.get("scene_id", f"scene_{sc_idx + 1:02d}")
        sc_st = float(sc.get("time", {}).get("start", 0.0))
        sc_en = float(sc.get("time", {}).get("end", dur))
        sc.setdefault("intent", narrative_intent if sc_idx == 0 else "concept_reveal")
        for a_idx, asset in enumerate(sc.get("assets", [])):
            src_id = str(asset.get("asset_id") or asset.get("id") or f"asset_{a_idx}")
            inst_id = f"{sc_id}_{src_id}_{a_idx}" if len(scenes) > 1 else src_id
            if src_id not in asset_library:
                asset_library[src_id] = {"asset_id": src_id, "path": asset.get("path"), "icon": asset.get("icon")}
            ref_entry = copy.deepcopy(asset)
            ref_entry["id"] = inst_id
            ref_entry["asset_id"] = src_id
            ref_entry["scene_id"] = sc_id
            ref_entry["in"] = float(asset.get("in", sc_st))
            ref_entry["out"] = float(asset.get("out", sc_en))
            ref_entry.setdefault("role", "supporting")
            if "position" not in ref_entry and "pos" in ref_entry:
                ref_entry["position"] = list(ref_entry["pos"])
            asset_refs.append(ref_entry)

            anchors.append({
                "anchor_id": f"{inst_id}_in",
                "time": float(asset.get("in", sc_st)),
                "type": "asset_entrance",
                "target": inst_id,
            })
            for eff in asset.get("effects", []):
                vfx_blocks.append({
                    "target": f"Asset_{inst_id}",
                    "type": eff.get("type", "Light Sweep"),
                    "start": float(eff.get("time", asset.get("in", sc_st))),
                    "end": float(asset.get("out", sc_en)),
                    "time": float(eff.get("time", asset.get("in", sc_st))),
                    "duration": float(eff.get("duration", 0.65)),
                    "intensity": eff.get("intensity", 0.5),
                    "width": eff.get("width", 42.0),
                    "radius": eff.get("radius", 24.0),
                    "color": eff.get("color", "#FBBF24"),
                    "frequency": eff.get("frequency"),
                    "expansion": eff.get("expansion"),
                })
        for wc in sc.get("word_cards", sc.get("words", [])):
            subtitle_blocks.append({
                "id": wc.get("id", f"{sc_id}_wc"),
                "text": wc.get("text", ""),
                "start": float(wc.get("start", wc.get("in", 0.0))),
                "end": float(wc.get("end", wc.get("out", dur))),
                "direction": default_dir,
                "role": "subtitle",
            })

    if isinstance(out.get("typography"), list) and out["typography"]:
        typo_blocks = [_normalize_typo_entry(t, idx, dur, default_dir=default_dir) for idx, t in enumerate(out["typography"])]
    elif subtitle_blocks:
        typo_blocks = list(subtitle_blocks)

    for sidx, cue in enumerate(out.get("sfx_cues", [])):
        sfx_blocks.append({
            "time": float(cue.get("time", 0.0)),
            "cue": cue.get("file", cue.get("cue", "pop")),
            "gain_db": float(cue.get("gain_db", -12.0)),
            **({"pan": float(cue["pan"])} if "pan" in cue else {}),
            **({"max_duration": float(cue["max_duration"])} if "max_duration" in cue else {}),
        })

    for sh_idx, sh in enumerate(out.get("procedural_shapes", [])):
        sh_copy = copy.deepcopy(sh)
        sh_copy.setdefault("id", sh.get("name", f"proc_{sh_idx}"))
        sh_copy.setdefault("start", float(sh.get("in", 0.0)))
        sh_copy.setdefault("end", float(sh.get("out", dur)))
        proc_graphics.append(sh_copy)
        if sh.get("trim") or "link" in str(sh.get("name", "")).lower():
            relationships.append({"id": sh_copy["id"], "kind": "procedural_link", "start": sh_copy["start"], "end": sh_copy["end"]})

    bg_tl = out.get("background_timeline", [])
    bg_hex = bg_hex_at(bg_tl, 0.0) if bg_tl else (palette or {}).get("bg", "#0F172A")
    cam_keys = list(out.get("camera_timeline", []))

    out["schema_version"] = SCENE_GRAPH_V2
    out.setdefault("narrative_intent", {"primary": narrative_intent, "beats": []})
    out.setdefault("asset_library", asset_library)
    out.setdefault("asset_references", asset_refs)
    out.setdefault("relationships", relationships)
    out.setdefault("subtitles", subtitle_blocks)
    out.setdefault("visual_metaphor", {"name": visual_metaphor, "style": "creative_studio_v5"})
    out.setdefault("composition", {
        "resolution": [int(out.get("width", 1920)), int(out.get("height", 1080))],
        "fps": int(out.get("fps", 30)),
        "layout_mode": "adaptive_2_5d",
        "safe_margin_px": 96,
        "bg_color": bg_hex,
        "palette": palette or {},
    })
    out.setdefault("procedural_graphics", proc_graphics)
    out.setdefault("motion_paths", motion_paths)
    out.setdefault("camera", {"enabled": True, "mode": "scene_choreography", "zoom": 1800.0 if cam_keys else 1650.0, "keyframes": cam_keys})
    out.setdefault("lighting", {"enabled": False, "lights": [], "sweeps": []})
    out.setdefault("vfx", vfx_blocks)
    out["typography"] = typo_blocks
    out.setdefault("sfx", sfx_blocks)
    out.setdefault("timing_anchors", anchors)
    out.setdefault("tool_requirements", ["shape_layer", "bezier_path", "trim_paths", "arabic_rtl_text"])
    out.setdefault("fallbacks", [])
    out.setdefault("quality_constraints", {
        "use_character": bool(use_character),
        "zero_bgm": True,
        "never_truncate_voiceover": True,
        "no_harsh_glow_on_bright_bg": True,
        "require_arabic_rtl_shaping": True,
    })
    return out


def validate_scene_graph_v2(
    sg: Dict[str, Any],
    *,
    auto_fix: bool = False,
) -> Tuple[bool, List[str]]:
    """Validate Creative Scene Graph V2 completeness, scene integrity, contrast, and V5 policy constraints."""
    issues: List[str] = []
    if str(sg.get("schema_version", "")) != SCENE_GRAPH_V2:
        issues.append(f"WARN: expected schema_version='{SCENE_GRAPH_V2}', got '{sg.get('schema_version')}'")

    for req_key in REQUIRED_V2_SECTIONS:
        if req_key not in sg:
            issues.append(f"ERROR: missing V2 section '{req_key}'")

    if auto_fix:
        sync_scene_graph_v2_views(sg)

    qc = sg.get("quality_constraints") or {}
    if qc.get("use_character") and not qc.get("explicit_character_request"):
        if auto_fix:
            qc["use_character"] = False
            issues.append("FIXED POLICY: disabled presenter character unless explicitly requested")
        else:
            issues.append("WARN: presenter character enabled without explicit request (V5 default false)")

    comp_meta = sg.get("composition") or {}
    bg_tl = sg.get("background_timeline") or []
    default_bg = str(comp_meta.get("bg_color", "#0F172A"))

    # Validate card_style contrast on asset_references & scenes[].assets against active timeline bg
    for asset in sg.get("asset_references", []):
        cs = asset.get("card_style")
        if not cs:
            continue
        st = float(asset.get("in", 0.0))
        en = float(asset.get("out", st + 1.0))
        mid_t = st + min(0.8, max(0.1, (en - st) * 0.45))
        bg_hex = bg_hex_at(bg_tl, mid_t) if bg_tl else default_bg
        is_dark = _hex_luma(bg_hex) < 120.0
        if cs == "warm" and is_dark:
            msg = f"CONTRAST: {asset.get('id')} uses warm card on dark bg {bg_hex} at t={mid_t:.2f}s"
            if auto_fix:
                r = int(bg_hex.lstrip("#")[0:2], 16)
                b = int(bg_hex.lstrip("#")[4:6], 16)
                asset["card_style"] = "dark_crimson" if r > b else "arctic"
                issues.append(f"FIXED {msg} -> {asset['card_style']}")
            else:
                issues.append(f"WARN: {msg}")
        elif cs in ("dark_crimson", "arctic", "amber") and not is_dark:
            msg = f"CONTRAST: {asset.get('id')} uses {cs} card on light bg {bg_hex} at t={mid_t:.2f}s"
            if auto_fix:
                asset["card_style"] = "warm"
                issues.append(f"FIXED {msg} -> warm")
            else:
                issues.append(f"WARN: {msg}")

    # Validate Glow intensity against active bg at effect time
    for fx in sg.get("vfx", []):
        if str(fx.get("type", "")).lower() == "glow" and float(fx.get("intensity", 1.0)) >= 1.0:
            fx_t = float(fx.get("start", fx.get("time", 0.0)))
            bg_hex = bg_hex_at(bg_tl, fx_t) if bg_tl else default_bg
            if _hex_luma(bg_hex) >= 165.0:
                msg = f"BLOWOUT: V2 Glow intensity={fx.get('intensity')} on bright bg {bg_hex}"
                if auto_fix:
                    fx["type"] = "Light Sweep"
                    fx["intensity"] = 0.5
                    issues.append(f"FIXED {msg} -> Light Sweep")
                else:
                    issues.append(f"WARN: {msg}")

    # Protect Arabic ligatures against per-char animation
    for tb in sg.get("typography", []):
        txt = str(tb.get("text", ""))
        has_ar = any(0x0600 <= ord(c) <= 0x06FF for c in txt)
        if has_ar:
            if str(tb.get("direction", "rtl")).lower() != "rtl":
                if auto_fix:
                    tb["direction"] = "rtl"
                    issues.append(f"FIXED RTL direction on typography '{tb.get('id', '?')}'")
                else:
                    issues.append(f"WARN: Arabic typography '{tb.get('id', '?')}' missing direction=rtl")
            if tb.get("animation_mode") in ("word_slide", "kinetic_words") and int(tb.get("animator_based_on", 2)) == 0:
                if auto_fix:
                    tb["animator_based_on"] = 2
                    issues.append(f"FIXED animator_based_on=2 on Arabic typography '{tb.get('id', '?')}'")
                else:
                    issues.append(f"WARN: Arabic typography '{tb.get('id', '?')}' uses per-char animator")

    has_error = any(x.startswith("ERROR:") for x in issues)
    return (not has_error), issues


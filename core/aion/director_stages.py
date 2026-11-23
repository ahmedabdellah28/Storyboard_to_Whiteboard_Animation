"""Stages 5, 6 & 7: Semantic Mapping, Creative Brief, and AION Director (scene_graph.json)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image

from core.aion.contracts import audit_scene_graph


def _detect_cropped_bottom(png_path: Path) -> bool:
    """Heuristic matching P1 Asset Audit: checks if illustration terminates flush/flat along bottom edge."""
    try:
        im = Image.open(png_path).convert("RGBA")
        arr = np.array(im)[:, :, 3] > 25
        h, w = arr.shape
        if h < 20 or w < 20:
            return False
        bottom_band = arr[max(0, h - 8):h, :]
        bottom_cols = np.any(bottom_band, axis=0)
        frac = float(np.sum(bottom_cols)) / float(w)
        return frac >= 0.36
    except Exception:
        return False


def _short_headline(text: str, language: str, max_words: int = 5) -> str:
    cleaned = re.sub(r'[.,!?؟،:"\'()\[\]]', " ", text or "").strip()
    words = [w for w in cleaned.split() if w]
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])


def run_semantic_map_stage(
    proj_dir: Path,
    sec_id: str,
    force: bool = False,
) -> Dict[str, Any]:
    """Builds `director/section_XX/semantic_map.json` linking assets cleanly to narration timing."""
    out_path = proj_dir / "director" / sec_id / "semantic_map.json"
    if out_path.is_file() and not force:
        return json.loads(out_path.read_text(encoding="utf-8"))

    sec_dir = proj_dir / "sections" / sec_id
    assets_dir = sec_dir / "assets"
    timing_path = sec_dir / "timing" / f"{sec_id}_timing_master.json"
    if not timing_path.is_file():
        raise FileNotFoundError(f"Timing master missing: {timing_path}. Run 'timing' first.")

    tm = json.loads(timing_path.read_text(encoding="utf-8"))
    duration = float(tm.get("duration", 0.0))
    sentences = tm.get("sentences") or []
    if not sentences and tm.get("words"):
        ws = tm["words"]
        sentences = [{"text": " ".join(w["word"] for w in ws), "start": ws[0]["start"], "end": ws[-1]["end"]}]

    meta_path = assets_dir / "metadata.json"
    entity_keys: List[str] = []
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        entity_keys = sorted(meta.keys())
    else:
        entity_keys = sorted(
            p.stem for p in assets_dir.glob("*.png")
            if not any(tag in p.name.lower() for tag in ("contact_sheet", "preview", "_composite"))
        )
        if not entity_keys:
            entity_keys = sorted(p.stem for p in assets_dir.glob("*_composite.png"))

    if not entity_keys:
        raise FileNotFoundError(f"No extracted assets found in {assets_dir}. Run 'extract' first.")

    # Chronological sentence-to-asset alignment preserving 100% asset usage budget
    n_ent = len(entity_keys)
    n_sent = max(1, len(sentences))
    mappings: List[Dict[str, Any]] = []
    for idx, aid in enumerate(entity_keys):
        s_idx = min(n_sent - 1, int(idx * n_sent / max(1, n_ent)))
        sent = sentences[s_idx]
        s_st = float(sent.get("start", round(idx * duration / n_ent, 2)))
        s_en = float(sent.get("end", round((idx + 1) * duration / n_ent, 2)))
        png_path = assets_dir / f"{aid}.png"
        cropped_bottom = _detect_cropped_bottom(png_path) if png_path.is_file() else False
        mappings.append({
            "asset_id": aid,
            "file": f"{aid}.png",
            "sentence_index": s_idx,
            "sentence_text": sent.get("text", ""),
            "target_start": round(s_st, 3),
            "target_end": round(max(s_st + 0.8, s_en), 3),
            "needs_framing": cropped_bottom,
            "recommended_preprocess": ["exhibit_card"] if cropped_bottom else [],
            "role": "hero" if idx == 0 else ("climax" if idx == n_ent - 1 else "narrative"),
        })

    payload = {
        "schema_version": "aion.semantic_map.v1",
        "section_id": sec_id,
        "language": tm.get("language", "ar"),
        "duration_sec": duration,
        "assets_count": n_ent,
        "sentences_count": len(sentences),
        "mappings": mappings,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def run_brief_stage(
    proj_dir: Path,
    sec_id: str,
    project_cfg: Dict[str, Any],
    force: bool = False,
) -> Dict[str, Any]:
    """Builds `director/section_XX/creative_brief.json` encoding framing, palette & typography rules."""
    out_path = proj_dir / "director" / sec_id / "creative_brief.json"
    if out_path.is_file() and not force:
        return json.loads(out_path.read_text(encoding="utf-8"))

    lang = (project_cfg.get("language") or "ar").lower()
    is_en = lang.startswith("en")
    brief = {
        "schema_version": "aion.creative_brief.v1",
        "section_id": sec_id,
        "language": "en" if is_en else "ar",
        "text_direction": "ltr" if is_en else "rtl",
        "typography_font": "Segoe UI" if is_en else "Cairo",
        "use_character": False,
        "palette_moods": {
            "warm_editorial": {"c1": "#F2EDE4", "c2": "#EBE4D8", "c3": "#E3DACB", "c4": "#DAD0BE", "vignette": 12, "card_style": "warm"},
            "midnight_mystery": {"c1": "#152130", "c2": "#101A26", "c3": "#0B131D", "c4": "#070C13", "vignette": 28, "card_style": "arctic"},
            "crimson_twist": {"c1": "#2D1116", "c2": "#210C10", "c3": "#17070A", "c4": "#0F0406", "vignette": 40, "card_style": "dark_crimson"},
        },
        "directing_rules": [
            "Match exhibit card_style strictly to active background mood (warm on light, arctic/dark_crimson on dark).",
            "Never apply intense Glow (>= 1.0) over bright white/yellow typography cards; use Light Sweep instead.",
            "Center solo entities at X=960 initially and slide smoothly with keyframes when companion enters.",
            "Synchronize narration without truncation via AudioTools RMS ducking.",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
    return brief


def run_direct_stage(
    proj_dir: Path,
    sec_id: str,
    project_cfg: Dict[str, Any],
    force: bool = False,
) -> Dict[str, Any]:
    """Synthesizes or validates `director/section_XX/scene_graph.json` from semantic_map + brief."""
    dir_dir = proj_dir / "director" / sec_id
    sg_path = dir_dir / "scene_graph.json"
    if sg_path.is_file() and not force:
        sg = json.loads(sg_path.read_text(encoding="utf-8"))
        _ok, issues = audit_scene_graph(sg, auto_fix=True)
        if any(i.startswith("FIXED ") for i in issues):
            sg_path.write_text(json.dumps(sg, indent=2, ensure_ascii=False), encoding="utf-8")
        return sg

    sem_path = dir_dir / "semantic_map.json"
    brief_path = dir_dir / "creative_brief.json"
    timing_path = proj_dir / "sections" / sec_id / "timing" / f"{sec_id}_timing_master.json"

    if not sem_path.is_file():
        run_semantic_map_stage(proj_dir, sec_id, force=False)
    if not brief_path.is_file():
        run_brief_stage(proj_dir, sec_id, project_cfg, force=False)

    sem = json.loads(sem_path.read_text(encoding="utf-8"))
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    tm = json.loads(timing_path.read_text(encoding="utf-8"))

    duration = float(tm.get("duration", sem.get("duration_sec", 45.0)))
    sentences = tm.get("sentences") or []
    mappings = sem.get("mappings", [])
    moods = brief.get("palette_moods", {})
    mood_order = ["warm_editorial", "midnight_mystery", "crimson_twist"]

    # Group sequentially into 2-to-3-asset balanced scenes
    n_scenes = max(3, min(7, (len(mappings) + 2) // 3))
    sc_dur = duration / float(n_scenes)

    bg_timeline: List[Dict[str, Any]] = []
    cam_timeline: List[Dict[str, Any]] = [
        {"time": 0.0, "pos": [960, 540, -1800], "poi": [960, 540, 0]}
    ]
    scenes: List[Dict[str, Any]] = []
    typography: List[Dict[str, Any]] = []
    sfx_cues: List[Dict[str, Any]] = []

    for i in range(n_scenes):
        st = round(i * sc_dur, 2)
        en = round(duration if i == n_scenes - 1 else (i + 1) * sc_dur, 2)
        mood_name = mood_order[i % len(mood_order)]
        mood = moods.get(mood_name, {"c1": "#152130", "c2": "#101A26", "c3": "#0B131D", "c4": "#070C13", "vignette": 28, "card_style": "arctic"})

        if i == 0:
            bg_timeline.append({"time": 0.0, **{k: mood[k] for k in ("c1", "c2", "c3", "c4", "vignette")}})
        else:
            prev_mood = moods.get(mood_order[(i - 1) % len(mood_order)], mood)
            bg_timeline.append({"time": round(max(0.0, st - 0.25), 2), **{k: prev_mood[k] for k in ("c1", "c2", "c3", "c4", "vignette")}})
            bg_timeline.append({"time": round(st + 0.25, 2), **{k: mood[k] for k in ("c1", "c2", "c3", "c4", "vignette")}})

        if i % 2 == 1:
            cam_timeline.append({"time": round((st + en) / 2.0, 2), "pos": [960, 528, -1690], "poi": [960, 528, 0]})
        elif i > 0:
            cam_timeline.append({"time": st, "pos": [960, 540, -1800], "poi": [960, 540, 0]})

        a0 = int(round(i * len(mappings) / float(n_scenes)))
        a1 = int(round((i + 1) * len(mappings) / float(n_scenes)))
        chunk_maps = mappings[a0:a1] or [mappings[min(i, len(mappings) - 1)]]
        chunk_maps = chunk_maps[:3]

        sc_assets: List[Dict[str, Any]] = []
        slots_2 = [[610, 550], [1310, 550]]
        slots_3 = [[480, 550], [960, 550], [1460, 550]]
        slots = slots_2 if len(chunk_maps) <= 2 else slots_3
        step_t = min(1.8, (en - st) / max(1, len(chunk_maps)))

        for k, mp in enumerate(chunk_maps):
            a_in = round(st + 0.15 + k * step_t, 2)
            a_out = round(en - 0.1, 2)
            target_pos = slots[k]
            entry: Dict[str, Any] = {
                "id": mp["asset_id"],
                "in": a_in,
                "out": min(round(duration - 0.05, 2), max(a_in + 0.8, a_out)),
                "pos": [960, target_pos[1]] if (k == 0 and len(chunk_maps) >= 2) else target_pos,
                "target_h": 420 if len(chunk_maps) <= 2 else 390,
                "entrance": "pop_settle" if k == 0 else ("slide_right" if k == len(chunk_maps) - 1 else "soft_fade"),
            }
            if k == 0 and len(chunk_maps) >= 2:
                slide_t = round(st + 0.15 + step_t, 2)
                entry["keyframes"] = [
                    {"time": round(max(a_in + 0.2, slide_t - 0.35), 2), "pos": [960, target_pos[1]]},
                    {"time": slide_t, "pos": target_pos},
                ]
            if mp.get("needs_framing"):
                entry["preprocess"] = ["exhibit_card"]
                entry["card_style"] = mood.get("card_style", "warm")
            if k == 0:
                entry["effects"] = [{"type": "Light Sweep", "time": round(a_in + 0.55, 2), "color": "#FBBF24"}]
            sc_assets.append(entry)

        scenes.append({"scene_id": f"sc_{i+1:02d}", "time": {"start": st, "end": en}, "assets": sc_assets})

        # Headline pill synced cleanly to sentence starting near scene
        sc_sent = sentences[min(len(sentences) - 1, int(i * len(sentences) / float(n_scenes)))] if sentences else {"text": f"Scene {i+1}"}
        pill_text = _short_headline(sc_sent.get("text", f"Scene {i+1}"), brief.get("language", "ar"))
        typography.append({
            "text": pill_text,
            "pos": [960, 125],
            "in": round(st + 0.15, 2),
            "out": round(min(duration - 0.1, en - 0.1), 2),
            "size": 44,
            "pill_bg": "#0F1E30" if mood_name != "crimson_twist" else "#3B0712",
            "pill_border": "#FBBF24" if mood_name == "warm_editorial" else ("#38BDF8" if mood_name == "midnight_mystery" else "#FB7185"),
            "direction": brief.get("text_direction", "rtl"),
            "font": brief.get("typography_font", "Cairo"),
        })
        sfx_cues.append({
            "file": "pop" if i % 3 == 0 else ("whoosh" if i % 3 == 1 else "glint"),
            "time": round(st + 0.18, 2),
            "gain_db": -11.0,
        })

    cam_timeline.append({"time": round(max(0.5, duration - 0.1), 2), "pos": [960, 535, -1660], "poi": [960, 535, 0]})

    qa_pts = [round(max(0.5, min(duration - 0.5, duration * (k + 0.5) / 10.0)), 2) for k in range(10)]
    sg = {
        "schema_version": "aion.scene_graph.v2",
        "project_id": f"{proj_dir.name}_{sec_id}",
        "language": brief.get("language", "ar"),
        "text_direction": brief.get("text_direction", "rtl"),
        "font": brief.get("typography_font", "Cairo"),
        "fps": int(project_cfg.get("fps", 30)),
        "use_character": bool(brief.get("use_character", False)),
        "source_timeline": {
            "audio_file": f"sections/{sec_id}/voice/{sec_id}.wav",
            "duration_sec": round(duration, 3),
            "alignment_file": f"sections/{sec_id}/timing/{sec_id}_timing_master.json",
        },
        "qa_times": qa_pts,
        "background_timeline": bg_timeline,
        "camera_timeline": cam_timeline,
        "scenes": scenes,
        "procedural_shapes": [],
        "typography": typography,
        "sfx_cues": sfx_cues,
    }
    audit_scene_graph(sg, auto_fix=True)
    dir_dir.mkdir(parents=True, exist_ok=True)
    sg_path.write_text(json.dumps(sg, indent=2, ensure_ascii=False), encoding="utf-8")
    return sg

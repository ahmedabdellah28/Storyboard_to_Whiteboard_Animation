"""Creative Quality Gate & 3-Way Regression Benchmark (Gold vs V5 Current vs V5 Fixed).

Clearly separates:
  1. Hard Automated Gates (`hard_checks`): deterministic PASS/FAIL checks for
     scene structure, timing integrity, Arabic RTL safety, contrast, SFX/VFX
     restraint, requested procedural graphics presence, and render validity.
  2. Advisory Creative Judgments (`creative_judgments`): non-template heuristic
     scoring (0-100) for composition diversity, motion curve variety, editorial
     conciseness, and mood continuity.
  3. 3-Way Comparison (`compare_three_way`): benchmarks Gold vs V5 Current vs
     V5 Fixed with side-by-side contact sheets and an explicit non-regression gate.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from core.aion.contracts import _hex_luma, audit_scene_graph, bg_hex_at
from core.aion.procedural_graphics import is_rtl_text
from core.aion.semantic_storyboard_director import _TRAILING_STOPWORDS, normalize_arabic
from core.aion.typography_registry import COMMERCIAL_LICENSE_REQUIRED


def probe_mp4_meta(mp4_path: Optional[Path]) -> Dict[str, Any]:
    """Probe MP4 video/audio stream metadata (duration, fps, resolution, codecs)."""
    if not mp4_path or not Path(mp4_path).is_file():
        return {"present": False}
    pr = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate",
            "-of", "json", str(mp4_path),
        ],
        capture_output=True, text=True, timeout=20,
    )
    if pr.returncode != 0:
        return {"present": True, "error": pr.stderr[:300]}
    try:
        data = json.loads(pr.stdout)
    except Exception:
        return {"present": True, "error": "ffprobe json parse error"}

    fmt = data.get("format", {})
    streams = data.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
    fps_val = 0.0
    rfr = str(v_stream.get("r_frame_rate", "0/1"))
    if "/" in rfr:
        num, den = rfr.split("/", 1)
        try:
            fps_val = round(float(num) / max(1.0, float(den)), 3)
        except Exception:
            fps_val = 0.0
    return {
        "present": True,
        "duration_sec": round(float(fmt.get("duration") or 0.0), 3),
        "size_mb": round(float(fmt.get("size") or 0.0) / (1024 * 1024), 2),
        "bit_rate": int(fmt.get("bit_rate") or 0),
        "width": int(v_stream.get("width") or 0),
        "height": int(v_stream.get("height") or 0),
        "fps": fps_val,
        "video_codec": v_stream.get("codec_name"),
        "audio_codec": a_stream.get("codec_name"),
    }


def _collect_ecproj_layer_names(ecproj_path: Optional[Path]) -> Tuple[bool, List[str], bool]:
    if not ecproj_path or not Path(ecproj_path).is_file():
        return False, [], False
    data = json.loads(Path(ecproj_path).read_text(encoding="utf-8", errors="replace"))
    names: List[str] = []
    text_corruption = False
    for item in data.get("items", {}).values():
        kind = item.get("kind", {})
        if kind.get("type") != "Comp":
            continue
        for lyr in kind.get("layers", []):
            names.append(str(lyr.get("name", "")))
            if "???" in json.dumps(lyr, ensure_ascii=False):
                text_corruption = True
    return True, names, text_corruption


def evaluate_hard_gates(
    *,
    scene_graph: Optional[Dict[str, Any]],
    ecproj_path: Optional[Path] = None,
    mp4_path: Optional[Path] = None,
    visual_metrics: Optional[Dict[str, Any]] = None,
    compile_report: Optional[Dict[str, Any]] = None,
    source_wav_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Run deterministic PASS/FAIL automated engineering & visual-integrity gates."""
    gates: List[Dict[str, Any]] = []
    sg = scene_graph or {}
    dur = float(sg.get("source_timeline", {}).get("duration_sec", 0.0) or 0.0)
    is_v2 = "asset_references" in sg and "procedural_graphics" in sg
    scenes = sg.get("scenes") or []
    layout_mode = str(sg.get("composition", {}).get("layout_mode", "auto"))

    # 1. Scene structure gate (multi-scene sections >= 20s must not collapse into 1 empty dummy scene)
    if dur >= 20.0 and layout_mode in ("auto", "semantic_v5_cinematic_story"):
        non_empty_scenes = [sc for sc in scenes if sc.get("assets")]
        ok_scenes = len(scenes) >= 3 and len(non_empty_scenes) == len(scenes)
        gates.append({
            "id": "scenes_structure",
            "passed": ok_scenes,
            "detail": f"scenes={len(scenes)}, non_empty={len(non_empty_scenes)} (expected >=3 populated scenes for {dur:.1f}s)",
        })
    else:
        gates.append({
            "id": "scenes_structure",
            "passed": bool(scenes),
            "detail": f"scenes={len(scenes)} (short/test mode='{layout_mode}')",
        })

    # 2. Timing alignment & zero voice truncation
    mp4_meta = probe_mp4_meta(mp4_path)
    wav_dur = 0.0
    if source_wav_path and Path(source_wav_path).is_file():
        wp = probe_mp4_meta(source_wav_path)
        wav_dur = float(wp.get("duration_sec", 0.0))
    ok_timing = True
    timing_detail = "no mp4/wav mismatch"
    if mp4_meta.get("present") and dur > 0:
        ref_d = wav_dur if wav_dur > 0 else dur
        diff = abs(float(mp4_meta.get("duration_sec", 0.0)) - ref_d)
        ok_timing = diff <= 0.45 and bool(mp4_meta.get("audio_codec"))
        timing_detail = f"mp4={mp4_meta.get('duration_sec')}s vs ref={ref_d:.3f}s (diff={diff:.3f}s), audio={mp4_meta.get('audio_codec')}"
    gates.append({"id": "timing_alignment", "passed": ok_timing, "detail": timing_detail})

    # 3. Typography & Arabic RTL readability + License & Pairing discipline
    ec_present, layer_names, text_corrupted = _collect_ecproj_layer_names(ecproj_path)
    typo_items = sg.get("typography") or []
    is_mobile = int(sg.get("height", 1080)) > int(sg.get("width", 1920))
    min_sz = 42 if is_mobile else 32
    rtl_bad = []
    small_txt = []
    commercial_bad = []
    used_fonts = set()
    for tb in typo_items:
        txt = str(tb.get("text", ""))
        f_used = str(tb.get("font") or "")
        if f_used:
            used_fonts.add(f_used)
        if f_used in COMMERCIAL_LICENSE_REQUIRED:
            commercial_bad.append(f_used)
        if is_rtl_text(txt):
            if str(tb.get("direction", "rtl")).lower() != "rtl":
                rtl_bad.append(txt[:25])
            if tb.get("animation_mode") in ("word_slide", "kinetic_words") and int(tb.get("animator_based_on", 2)) == 0:
                rtl_bad.append(f"char_split:{txt[:20]}")
        sz = int(tb.get("size", 44))
        if sz < min_sz:
            small_txt.append(sz)
    font_bloat = len(used_fonts) > 3
    ok_typo = (not text_corrupted) and (not rtl_bad) and (not small_txt) and (not commercial_bad) and (not font_bloat)
    gates.append({
        "id": "typography_readability",
        "passed": ok_typo,
        "detail": f"corrupted={text_corrupted}, rtl_issues={rtl_bad}, undersized={small_txt}, commercial_blocked={commercial_bad}, fonts_used={sorted(used_fonts)}",
    })

    # 4. Contrast & Glow blowout gate
    _, sg_issues = audit_scene_graph(sg, auto_fix=False) if sg else (True, [])
    blowout_errs = [x for x in sg_issues if "BLOWOUT" in x or "CONTRAST" in x or x.startswith("ERROR:")]
    vis_blowout = float((visual_metrics or {}).get("max_white_blowout", 0.0))
    ok_contrast = (not blowout_errs) and vis_blowout <= 0.45
    gates.append({
        "id": "contrast_and_blowout",
        "passed": ok_contrast,
        "detail": f"sg_issues={len(blowout_errs)}, white_blowout={vis_blowout}",
    })

    # 5. SFX & VFX restraint (no medallion spam, no 30-cue pop floods)
    pg_items = sg.get("procedural_graphics") or []
    medallion_cnt = sum(1 for p in pg_items if p.get("kind") == "icon_medallion")
    sfx_list = sg.get("sfx") if is_v2 else sg.get("sfx_cues", [])
    sfx_cnt = len(sfx_list or [])
    vfx_list = sg.get("vfx") or []
    # Grounding studio `drop_shadow` on organic cutouts is baseline compositing, not heavy VFX clutter
    heavy_vfx_list = [v for v in vfx_list if str(v.get("type", "")).lower() != "drop_shadow"]
    vfx_cnt = len(heavy_vfx_list) if is_v2 else sum(len(a.get("effects", [])) for sc in scenes for a in sc.get("assets", []))
    max_sfx = max(12, int(dur * 0.40)) if dur > 0 else 20
    max_vfx = max(10, int(dur * 0.30)) if dur > 0 else 15
    ok_restraint = (medallion_cnt <= 1) and (sfx_cnt <= max_sfx) and (vfx_cnt <= max_vfx)
    gates.append({
        "id": "sfx_vfx_restraint",
        "passed": ok_restraint,
        "detail": f"medallions={medallion_cnt} (<=1), sfx={sfx_cnt} (<={max_sfx}), heavy_vfx={vfx_cnt} (<={max_vfx})",
    })

    # 6. Requested procedural graphics present in compiled .ecproj (no silent downgrade!)
    missing_proc: List[str] = []
    if ec_present:
        lname_set = set(layer_names)
        for p in pg_items:
            kind = str(p.get("kind", ""))
            gid = str(p.get("id", p.get("name", "")))
            if kind in ("bezier_connector", "bezier_arrow") and f"Path_{gid}" not in lname_set:
                missing_proc.append(f"Path_{gid}")
            elif kind == "repeater_rings" and f"Rep_{gid}" not in lname_set:
                missing_proc.append(f"Rep_{gid}")
            elif kind == "spotlight_cone" and f"SpotCone_{gid}" not in lname_set:
                missing_proc.append(f"SpotCone_{gid}")
            elif kind == "shape_node" and f"Node_{gid}" not in lname_set:
                missing_proc.append(f"Node_{gid}")
        cam = sg.get("camera") or {}
        if cam.get("enabled") and cam.get("keyframes") and "MainCam" not in lname_set:
            missing_proc.append("MainCam")
    gates.append({
        "id": "requested_graphics_present",
        "passed": len(missing_proc) == 0,
        "detail": f"missing_layers={missing_proc}" if missing_proc else "all requested vectors & camera compiled",
    })

    # 7. Render integrity & FPS compliance
    expected_fps = int(sg.get("fps") or sg.get("composition", {}).get("fps") or 0)
    expr_errors = (compile_report or {}).get("render_meta", {}).get("expr_errors", [])
    fps_ok = (not mp4_meta.get("present")) or (expected_fps <= 0) or (abs(float(mp4_meta.get("fps", 0.0)) - expected_fps) <= 0.5)
    vm = visual_metrics or {}
    vis_ok = (vm.get("frame_count", 0) == 0) or (
        vm.get("mean_luma_std", 0.0) >= 4.5
        and (vm.get("frame_count", 0) < 2 or vm.get("mean_temporal_mad", 0.0) >= 0.08)
        and vm.get("edge_clip_score", 0.0) <= 0.35
    )
    gates.append({
        "id": "render_integrity",
        "passed": bool(fps_ok and vis_ok and not expr_errors),
        "detail": f"fps={mp4_meta.get('fps')}/{expected_fps}, expr_errors={len(expr_errors)}, edge_clip={vm.get('edge_clip_score')}, luma_std={vm.get('mean_luma_std')}, mad={vm.get('mean_temporal_mad')}",
    })

    return gates


def evaluate_creative_judgments(
    *,
    scene_graph: Optional[Dict[str, Any]],
    visual_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Score non-template editorial & motion-design quality (0-100) cleanly separate from hard gates."""
    sg = scene_graph or {}
    scenes = sg.get("scenes") or []
    is_v2 = "asset_references" in sg
    all_assets = [a for sc in scenes for a in sc.get("assets", [])]
    if not all_assets and is_v2:
        all_assets = list(sg.get("asset_references") or [])

    # 1. Composition diversity (distinct layout modes / spatial positions)
    comp_modes = {sc.get("composition_mode") for sc in scenes if sc.get("composition_mode")}
    xs = {round(float((a.get("position") or a.get("pos") or [960])[0]) / 80.0) for a in all_assets}
    comp_score = min(100, int(35 + len(comp_modes) * 18 + min(5, len(xs)) * 8)) if scenes else 30

    # 2. Motion curve variety (entrance types + purposeful keyframes, penalize 100% uniform ±14px drift)
    entrances = {a.get("entrance") for a in all_assets if a.get("entrance")}
    kfs_assets = sum(1 for a in all_assets if a.get("keyframes"))
    motion_paths = sg.get("motion_paths") or []
    uniform_drift_only = bool(motion_paths) and all(
        len(mp.get("keyframes", [])) == 2
        and abs(abs(float(mp["keyframes"][1]["pos"][0]) - float(mp["keyframes"][0]["pos"][0])) - 14.0) < 0.5
        for mp in motion_paths if len(mp.get("keyframes", [])) >= 2
    )
    motion_score = 45
    motion_score += min(35, len(entrances) * 11)
    motion_score += min(20, kfs_assets * 4)
    if uniform_drift_only:
        motion_score = max(25, motion_score - 30)
    motion_score = min(100, motion_score)

    # 3. Editorial conciseness of headlines (2-6 words, no dangling stopword cutoff, top/editorial placement)
    typos = sg.get("typography") or []
    hl_scores: List[float] = []
    for tb in typos:
        txt = str(tb.get("text", "")).strip()
        words = txt.split()
        if not words:
            continue
        last_w = normalize_arabic(words[-1].rstrip("،,.!؟?:"))
        s = 100.0
        if len(words) > 7:
            s -= 25.0
        if last_w in _TRAILING_STOPWORDS:
            s -= 40.0
        pos_y = float((tb.get("position") or tb.get("pos") or [960, 130])[1])
        if pos_y > 800 and tb.get("role", "editorial_headline") != "subtitle":
            s -= 20.0  # bottom caption masquerading as headline
        hl_scores.append(max(0.0, s))
    editorial_score = int(round(sum(hl_scores) / max(1, len(hl_scores)))) if typos else 40

    # 4. Mood & camera continuity (distinct alternating moods, no excessive dupe keyframes)
    bg_tl = sg.get("background_timeline") or []
    distinct_c1 = {str(b.get("c1", "")).upper() for b in bg_tl}
    cam_kfs = (sg.get("camera") or {}).get("keyframes") or sg.get("camera_timeline") or []
    mood_score = min(100, 35 + min(4, len(distinct_c1)) * 14 + min(4, len(cam_kfs) // 2) * 5)

    overall = int(round(0.28 * comp_score + 0.25 * motion_score + 0.30 * editorial_score + 0.17 * mood_score))
    notes: List[str] = []
    if uniform_drift_only:
        notes.append("Detected uniform +-14px mechanical drift across motion_paths.")
    if len(entrances) <= 1 and len(all_assets) >= 4:
        notes.append("Low entrance animation variety across assets.")
    if editorial_score < 75:
        notes.append("Some headlines appear truncated on stopwords or placed in subtitle zone.")

    return {
        "overall_creative_score": overall,
        "dimensions": {
            "composition_diversity": comp_score,
            "motion_variety": motion_score,
            "editorial_conciseness": editorial_score,
            "mood_and_camera_continuity": mood_score,
        },
        "observed": {
            "scene_count": len(scenes),
            "asset_instances": len(all_assets),
            "composition_modes": sorted(comp_modes),
            "entrance_types": sorted(entrances),
            "keyframed_assets": kfs_assets,
            "distinct_bg_moods": len(distinct_c1),
        },
        "advisory_notes": notes,
    }


def compare_three_way(
    *,
    gold_sg_path: Path,
    gold_mp4_path: Path,
    v5_current_sg_path: Path,
    v5_current_mp4_path: Path,
    v5_fixed_sg_path: Path,
    v5_fixed_mp4_path: Path,
    out_dir: Path,
    gold_ecproj_path: Optional[Path] = None,
    v5_current_ecproj_path: Optional[Path] = None,
    v5_fixed_ecproj_path: Optional[Path] = None,
    source_wav_path: Optional[Path] = None,
    sample_fractions: Tuple[float, ...] = (0.12, 0.32, 0.55, 0.78, 0.92),
) -> Dict[str, Any]:
    """Benchmark Gold vs V5 Current vs V5 Fixed across hard gates, creative scores & side-by-side frames."""
    from core.aion.visual_qa import _analyze_frames

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates = [
        ("gold", gold_sg_path, gold_ecproj_path, gold_mp4_path),
        ("v5_current", v5_current_sg_path, v5_current_ecproj_path, v5_current_mp4_path),
        ("v5_fixed", v5_fixed_sg_path, v5_fixed_ecproj_path, v5_fixed_mp4_path),
    ]

    summary: Dict[str, Any] = {}
    sampled_by_tag: Dict[str, List[Path]] = {}
    ref_dur = float(probe_mp4_meta(gold_mp4_path).get("duration_sec") or 45.0)

    for tag, sg_p, ec_p, mp4_p in candidates:
        sg = json.loads(Path(sg_p).read_text(encoding="utf-8")) if sg_p and Path(sg_p).is_file() else {}
        mp4_meta = probe_mp4_meta(mp4_p)
        dur = float(mp4_meta.get("duration_sec") or ref_dur or 30.0)

        tag_frames: List[Path] = []
        if mp4_p and Path(mp4_p).is_file():
            fdir = out_dir / "frames" / tag
            fdir.mkdir(parents=True, exist_ok=True)
            for idx, frac in enumerate(sample_fractions):
                t = round(min(max(0.15, dur - 0.15), dur * frac), 2)
                fp = fdir / f"{tag}_{idx:02d}_{t:.2f}s.png"
                subprocess.run(
                    ["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(mp4_p), "-frames:v", "1", "-vf", "scale=640:-1", str(fp)],
                    capture_output=True, timeout=30,
                )
                if fp.is_file():
                    tag_frames.append(fp)
        sampled_by_tag[tag] = tag_frames
        vis = _analyze_frames(tag_frames)
        hard = evaluate_hard_gates(
            scene_graph=sg,
            ecproj_path=ec_p,
            mp4_path=mp4_p,
            visual_metrics=vis,
            source_wav_path=source_wav_path,
        )
        creative = evaluate_creative_judgments(scene_graph=sg, visual_metrics=vis)
        summary[tag] = {
            "mp4": mp4_meta,
            "visual_metrics": vis,
            "hard_passed": all(g["passed"] for g in hard),
            "hard_checks": hard,
            "creative": creative,
        }

    # Build 3-row side-by-side comparison contact sheet (Row 0 = Gold, Row 1 = V5 Current, Row 2 = V5 Fixed)
    cols = len(sample_fractions)
    tile_w, tile_h = 480, 270
    header_h, label_w = 38, 150
    sheet_path = out_dir / "three_way_comparison.png"
    sheet = Image.new("RGB", (label_w + cols * tile_w, header_h + 3 * tile_h), (14, 18, 28))
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 10), f"3-Way Comparison | Gold vs V5 Current vs V5 Fixed", fill=(248, 250, 252))
    row_colors = {"gold": (250, 204, 21), "v5_current": (248, 113, 113), "v5_fixed": (74, 222, 128)}
    for r_idx, tag in enumerate(("gold", "v5_current", "v5_fixed")):
        y0 = header_h + r_idx * tile_h
        sc_txt = f"{tag.upper()}\nScore: {summary[tag]['creative']['overall_creative_score']}\nHard: {'PASS' if summary[tag]['hard_passed'] else 'FAIL'}"
        draw.text((12, y0 + 24), sc_txt, fill=row_colors[tag])
        for c_idx, fp in enumerate(sampled_by_tag.get(tag, [])[:cols]):
            tile = Image.open(fp).convert("RGB").resize((tile_w, tile_h), Image.Resampling.LANCZOS)
            sheet.paste(tile, (label_w + c_idx * tile_w, y0))
    sheet.save(sheet_path)

    # Non-regression decision
    v5_cur_score = summary["v5_current"]["creative"]["overall_creative_score"]
    v5_fix_score = summary["v5_fixed"]["creative"]["overall_creative_score"]
    no_regression = bool(summary["v5_fixed"]["hard_passed"]) and (v5_fix_score >= v5_cur_score)

    report = {
        "schema_version": "aion.three_way_benchmark.v1",
        "no_regression": no_regression,
        "promote_recommended": no_regression and v5_fix_score > v5_cur_score,
        "comparison_sheet": str(sheet_path),
        "results": summary,
    }
    (out_dir / "three_way_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report

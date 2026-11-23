"""Continuous Place-First Workflow Montage Director (`--format workflow_montage`).

Implements stable-location continuous directing for staged historical episodes
built from `WORKFLOW.json` + ordered `SECTION_XX/SECTION.json` packages:
1. Place-first `background_track` keeping physical scenes sustained across
   multiple beats (`SECTION_01` opening rule: `01_ankara_plain.png` -> single
   cut to `02_edirne_council.png` through the end of Section 01; mentioned
   places/treaties appear as `insert` visuals inside the room).
2. Motivated `element_tracks` with explicit initial state, keyframed paths,
   cause-and-effect persistence/receding (`then: hold` / `recede`), bottom-center
   visible-bounds grounding (`y_px = 840`) on characters, and walking displacement
   strictly restricted to walking poses.
3. Unified `camera_track` (3D zero-parallax `z=0` plane shared by background,
   shadows, and grounded characters) with zero uniform auto-effects clutter.
4. Outputs complete executable `direction_plan.json` alongside EffectCraft
   `scene_graph.v2.json` files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.aion.contracts import sync_scene_graph_v2_views, validate_scene_graph_v2
from core.aion.master_cinema_kit import LIVING_GRADIENT_PALETTES

CANVAS_W = 1920
CANVAS_H = 1080


def _norm_ar(text: str) -> str:
    s = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", str(text or ""))
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ى", "ي").replace("ة", "ه")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def resolve_workflow_meta_dir(proj_dir: Path) -> Optional[Path]:
    for cand in (
        proj_dir / "inputs" / "ankara_production_meta",
        proj_dir / "inputs" / "workflow_meta",
        proj_dir / "inputs",
        proj_dir,
    ):
        if (cand / "WORKFLOW.json").is_file():
            return cand
    return None


def is_workflow_montage_project(proj_dir: Path) -> bool:
    return resolve_workflow_meta_dir(Path(proj_dir)) is not None


def _find_phrase_time(
    phrase: str,
    words: List[Dict[str, Any]],
    search_start_idx: int,
    fallback_t: float,
    max_t: Optional[float] = None,
) -> Tuple[float, int]:
    norm_words = [(_norm_ar(w.get("word", "")), float(w.get("start", 0.0))) for w in words]
    tokens = [t for t in _norm_ar(phrase).split() if len(t) >= 2]
    if tokens:
        for wi in range(max(0, search_start_idx), len(norm_words)):
            if max_t is not None and norm_words[wi][1] > max_t:
                break
            w0 = norm_words[wi][0]
            if w0 == tokens[0] or (len(tokens[0]) >= 3 and tokens[0] in w0):
                if len(tokens) == 1:
                    return (round(norm_words[wi][1], 3), wi + 1)
                w1 = norm_words[wi + 1][0] if wi + 1 < len(norm_words) else ""
                if w1 == tokens[1] or (len(tokens[1]) >= 3 and tokens[1] in w1):
                    return (round(norm_words[wi][1], 3), wi + 1)
        for wi in range(max(0, search_start_idx), len(norm_words)):
            if max_t is not None and norm_words[wi][1] > max_t:
                break
            w0 = norm_words[wi][0]
            if w0 == tokens[0] or (len(tokens[0]) >= 4 and tokens[0][:4] in w0):
                return (round(norm_words[wi][1], 3), wi + 1)
    return (round(fallback_t, 3), search_start_idx)


def _match_scene_windows(
    sj_scenes: List[Dict[str, Any]],
    words: List[Dict[str, Any]],
    sec_dur: float,
    est_sec_start: float,
    est_sec_end: float,
) -> List[Tuple[float, float]]:
    starts: List[float] = [0.0]
    cursor = 0
    est_span = max(1.0, est_sec_end - est_sec_start)
    for idx in range(1, len(sj_scenes)):
        sc = sj_scenes[idx]
        est_local = (float(sc["start_seconds"]) - est_sec_start) / est_span * sec_dur
        t_found, new_cursor = _find_phrase_time(str(sc.get("entry_cue_ar") or ""), words, cursor, est_local)
        if new_cursor > cursor:
            cursor = new_cursor
        min_t = starts[-1] + 1.25
        max_t = sec_dur - 1.25 * (len(sj_scenes) - idx)
        starts.append(round(max(min_t, min(max_t, t_found)), 3))
    return [
        (round(st, 3), round(starts[i + 1] if i + 1 < len(starts) else sec_dur, 3))
        for i, st in enumerate(starts)
    ]


def _resolve_media_path(proj_dir: Path, rel_path: str, sid_upper: str) -> Path:
    norm = str(rel_path).replace("\\", "/")
    if norm.startswith("BACKGROUNDS/"):
        return (proj_dir / "inputs" / "backgrounds" / Path(norm).name).resolve()
    m = re.match(r"EXTRACTED_ASSETS/(SECTION_\d+)/(\d+)\.png$", norm)
    if m:
        return (proj_dir / "sections" / m.group(1).lower() / "assets" / f"entity_{int(m.group(2)):02d}.png").resolve()
    return (proj_dir / "sections" / sid_upper.lower() / "assets" / Path(norm).name).resolve()


def _is_walking_pose(asset: Dict[str, Any]) -> bool:
    blob = f"{asset.get('title_en', '')} {asset.get('description_en', '')}".lower()
    if any(st in blob for st in ("standing", "seated", "at attention", "at rest")):
        return False
    return any(kw in blob for kw in ("messenger", "walking", "running", "striding", "porter", "traveler", "pack mule"))


def _character_leads_sentence(sec_id: str, sc_num: int, sc: Dict[str, Any]) -> bool:
    frag = str(sc.get("narration_fragment_ar") or "").strip()
    head = " ".join(frag.split()[:4])
    if sec_id == "SECTION_01":
        if sc_num in (1, 2, 5, 6):
            return True
        if sc_num in (3, 4):
            return False
    person_openers = (
        "أُسر بايزيد", "لكن حين وصل", "صارت الأسرة", "كان لقب بايزيد",
        "ظهر محمد", "محمد لم يرث", "كان عليه", "دخل عيسى", "مناصرو أمير",
        "راقب الحكم البيزنطي", "خسر سليمان", "فالأمير الجديد", "عبر محمد",
        "تمكن محمد", "فصار يحكم", "لم يحصل محمد", "حين انتصر محمد",
        "حين نقرأ رواية", "المنتصر يستمر", "أما المهزوم", "فالناس الذين",
        "تيمور", "تمركز سليمان", "الأمير", "بعض الأسر", "وحين دخل تيمور",
        "وبعض القوى", "بعض القادة", "يسعى الفائز", "وبعده وجد محمد",
    )
    return any(head.startswith(p) or p in head for p in person_openers)


def _pick_second_phrase_cue(frag: str) -> str:
    frag_clean = frag.strip()
    explicit = {
        "أُسر بايزيد في أنقرة سنة ألف وأربعمئة واثنتين.": "في أنقرة",
        "لكن حين وصل خبر أسره إلى أدرنة،": "خبر أسره",
        "بقيت المدينة في يد العثمانيين،": "في يد العثمانيين",
    }
    if frag_clean in explicit:
        return explicit[frag_clean]
    tokens = frag_clean.split()
    if len(tokens) <= 2:
        return frag_clean
    return " ".join(tokens[max(2, len(tokens) // 2) : min(len(tokens), max(2, len(tokens) // 2) + 3)])


def _second_entry_time(cue_second: str, words: List[Dict[str, Any]], s0: float, s1: float) -> float:
    words_in = [w for w in words if float(w.get("start", 0.0)) >= s0 - 0.05 and float(w.get("start", 0.0)) < s1 - 0.30]
    if len(words_in) >= 2:
        t_hit, hit_i = _find_phrase_time(cue_second, words_in, 1, s0 + (s1 - s0) * 0.42, max_t=s1 - 0.40)
        if hit_i > 1 or t_hit > s0 + 0.25:
            return round(max(s0 + 0.30, min(s1 - 0.45, t_hit)), 3)
        return round(max(s0 + 0.30, min(s1 - 0.45, float(words_in[len(words_in) // 2]["start"]))), 3)
    return round(s0 + (s1 - s0) * 0.40, 3)


def _sustained_background_plan(
    sec_idx: int,
    sj_scenes: List[Dict[str, Any]],
    windows: List[Tuple[float, float]],
    sec_dur: float,
) -> List[Dict[str, Any]]:
    """Derive clean, sustained physical locations (`background_track`) per section without scene-by-scene room strobing."""

    def _entry(bg_id: str, sc_i: int, in_t: float, out_t: float, reason: str, cue: str = "") -> Dict[str, Any]:
        return {
            "background_id": bg_id,
            "file": f"BACKGROUNDS/{bg_id}.png",
            "section_in_s": round(in_t, 3),
            "section_out_s": round(out_t, 3),
            "cut_cue_ar": cue or (str(sj_scenes[sc_i].get("entry_cue_ar") or "") if sc_i < len(sj_scenes) else ""),
            "reason_ar": reason,
        }

    # Scene start helper
    st = lambda idx: windows[min(idx, len(windows) - 1)][0]

    if sec_idx == 1:
        # Strict Ankara Opening Rule: 01_ankara_plain -> ONE single cut to 02_edirne_council until end!
        t_cut = st(1)
        return [
            _entry("01_ankara_plain", 0, 0.0, t_cut, "تبدأ الحلقة من ساحة أنقرة حيث أُسر بايزيد", "أُسر بايزيد"),
            _entry("02_edirne_council", 1, t_cut, sec_dur, "ينتقل السرد من الأسر إلى وصول الخبر إلى مقر الحكم في أدرنة ويبقى فيها", "لكن حين وصل خبر أسره إلى أدرنة"),
        ]
    if sec_idx == 2:
        t_cut = st(1)
        return [
            _entry("01_ankara_plain", 0, 0.0, t_cut, "يُعرّف المشهد بلقب بايزيد الصاعقة في ساحة أنقرة", "كان لقب بايزيد"),
            _entry("06_anatolian_gate", 1, t_cut, sec_dur, "ينتقل السرد إلى الأناضول وبوابات الإمارات التي ضمها بايزيد ثم عادت مع تيمور", "قبل الهزيمة"),
        ]
    if sec_idx == 3:
        return [
            _entry("06_anatolian_gate", 0, 0.0, st(2), "الوقفة الأولى مع صدمة الهزيمة في بوابات الأناضول", "بدت الهزيمة"),
            _entry("02_edirne_council", 2, st(2), st(4), "انتقال إلى روم إيلي وأدرنة حيث بقيت المدن والحاميات", "في روم إيلي"),
            _entry("04_gallipoli_quay", 4, st(4), sec_dur, "رصيف المضائق الذي يفصل الضفتين وتجارة الشرق والغرب", "كانت المضائق"),
        ]
    if sec_idx == 4:
        return [
            _entry("02_edirne_council", 0, 0.0, st(3), "تمركز سليمان جلبي في قاعة أدرنة الأوروبية", "تمركز سليمان"),
            _entry("12_gallipoli_treaty_room", 3, st(3), sec_dur, "الانتقال إلى غرفة تسوية غاليبولي حيث تُعرض سالونيك والموازين كوثائق وإدراجات", "توصل في غاليبولي"),
        ]
    if sec_idx == 5:
        return [
            _entry("03_amasya_terrace", 0, 0.0, st(3), "ظهور محمد جلبي على مصطبة وادي أماسيا المحاطة بالجبال", "على الجانب الآخر"),
            _entry("10_anatolian_pass", 3, st(3), st(5), "عبور الجبال والممرات الموسمية بين الأقاليم", "بينهم جبال"),
            _entry("03_amasya_terrace", 5, st(5), sec_dur, "عودة إلى قيادة محمد في أماسيا مع ورود الأخبار وخريطة العبور كإدراجات", "محمد لم يرث"),
        ]
    if sec_idx == 6:
        return [
            _entry("02_edirne_council", 0, 0.0, sec_dur, "قاعة الحكم تظل المسرح الثابت لصراع الورثة والتحالفات المتحركة", "دخل عيسى"),
        ]
    if sec_idx == 7:
        return [
            _entry("05_byzantine_hall", 0, 0.0, sec_dur, "القاعة البيزنطية في القسطنطينية تراقب التنافس وتزن الوعود وتشتري الوقت", "راقب الحكم"),
        ]
    if sec_idx == 8:
        return [
            _entry("10_anatolian_pass", 0, 0.0, st(2), "رحلة حمولة القمح عبر الممر الزراعي قبل وصولها إلى السوق", "هناك طريقة أخرى"),
            _entry("07_rumelian_market", 2, st(2), sec_dur, "السوق العام يستمر كمكان متصل يظهر فيه أثر الفراغ على التجار والأجور والمعابر", "يُراد إيصالها"),
        ]
    if sec_idx == 9:
        return [
            _entry("02_edirne_council", 0, 0.0, st(3), "تحول السلطة في أدرنة من سليمان إلى موسى", "خسر سليمان"),
            _entry("05_byzantine_hall", 3, st(3), st(6), "انعكاس تبدل أدرنة داخل القسطنطينية وإعادة ترتيب التفاهمات", "فالأمير الجديد"),
            _entry("04_gallipoli_quay", 6, st(6), sec_dur, "رصيف المضيق مع عبور محمد نحو الضفة الأوروبية لاختبار التحالف", "يمكننا الآن"),
        ]
    if sec_idx == 10:
        return [
            _entry("02_edirne_council", 0, 0.0, sec_dur, "قاعة أدرنة الموحدة سنة 1413 تستعرض طريق العودة والتسويات كوثائق ومعابر مدمجة", "بحلول سنة"),
        ]
    if sec_idx == 11:
        return [
            _entry("11_court_archive", 0, 0.0, sec_dur, "أرشيف البلاط يستقر طوال السيكشن لتأمل رواية المنتصر والمهزوم", "حين نقرأ رواية"),
        ]
    # sec_idx == 12
    return [
        _entry("02_edirne_council", 0, 0.0, st(6), "قاعة أدرنة بعد نصر 1413 تستعيد ما بقي من موارد المدن والأقاليم كإدراجات", "حين انتصر محمد"),
        _entry("12_gallipoli_treaty_room", 6, st(6), sec_dur, "الختام داخل غرفة اتفاق غاليبولي لتأكيد التئام الروابط بين الضفتين", "هنا تكتمل"),
    ]


def _assemble_element_tracks_and_camera(
    proj_dir: Path,
    sec_idx: int,
    sid_upper: str,
    sj_scenes: List[Dict[str, Any]],
    windows: List[Tuple[float, float]],
    words: List[Dict[str, Any]],
    abs_offset: float,
    sec_dur: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build motivated `element_tracks` (with explicit initial->path->hold keyframes & persistence) + `camera_track`."""
    element_tracks: List[Dict[str, Any]] = []
    sg_assets_flat: List[Dict[str, Any]] = []
    sg_shadows: List[Dict[str, Any]] = []
    camera_segments: List[Dict[str, Any]] = []

    active_insert: Optional[Dict[str, Any]] = None  # Persistent explanatory insert that can glide/recede cleanly
    layer_counter = 2

    def _add_asset_pair(
        *,
        sc_num: int,
        asset: Dict[str, Any],
        in_l: float,
        out_l: float,
        cue_ar: str,
        pos_init: List[float],
        pos_rest: List[float],
        scale_init: float = 1.0,
        scale_rest: float = 1.0,
        op_init: float = 100.0,
        op_rest: float = 100.0,
        t_move_dur: float = 0.72,
        recede_at: Optional[Tuple[float, List[float], float, float]] = None,
        action_desc: str = "hold",
        relation_note: str = "",
        target_vis_h: float = 450.0,
        target_max_side: float = 300.0,
    ) -> Dict[str, Any]:
        nonlocal layer_counter
        layer_idx = layer_counter
        layer_counter += 1
        a_rel = str(asset["file"])
        a_disk = _resolve_media_path(proj_dir, a_rel, sid_upper)
        is_g = bool(asset.get("grounded", False))
        role = "grounded_character" if is_g else "insert"
        anchor = "bottom_center_of_visible_bounds" if is_g else "center_of_visible_bounds"
        inst_id = f"s{sec_idx:02d}_sc{sc_num:02d}_{int(asset['number']):02d}"
        aid = f"entity_{int(asset['number']):02d}"

        t_arr = round(min(out_l - 0.12, in_l + max(0.35, t_move_dur)), 3)
        kfs_plan: List[Dict[str, Any]] = []
        kfs_sg: List[Dict[str, Any]] = []

        if pos_init != pos_rest or abs(scale_init - scale_rest) > 0.005 or abs(op_init - op_rest) > 0.5:
            kfs_plan.append({
                "time_s": round(abs_offset + in_l, 3),
                "section_time_s": round(in_l, 3),
                "cue_ar": cue_ar,
                "position_px": pos_init,
                "scale": scale_init,
                "opacity": op_init,
                "state": "enter",
            })
            kfs_plan.append({
                "time_s": round(abs_offset + t_arr, 3),
                "section_time_s": t_arr,
                "position_px": pos_rest,
                "scale": scale_rest,
                "opacity": op_rest,
                "easing": "ease_out",
                "state": "hold",
            })
            kfs_sg.append({"time": round(in_l, 3), "pos": [pos_init[0], pos_init[1], 0.0], "scale_mult": scale_init, "opacity": op_init})
            kfs_sg.append({"time": t_arr, "pos": [pos_rest[0], pos_rest[1], 0.0], "scale_mult": scale_rest, "opacity": op_rest})
        else:
            kfs_plan.append({
                "time_s": round(abs_offset + in_l, 3),
                "section_time_s": round(in_l, 3),
                "cue_ar": cue_ar,
                "position_px": pos_rest,
                "scale": scale_rest,
                "opacity": op_rest,
                "state": "hold",
            })

        if recede_at is not None:
            t_rec, r_pos, r_sc, r_op = recede_at
            t_rec = round(max(t_arr + 0.15, min(out_l - 0.2, t_rec)), 3)
            t_rec_end = round(min(out_l - 0.05, t_rec + 0.65), 3)
            # Hold previous resting state just before recede begins!
            kfs_plan.append({
                "time_s": round(abs_offset + t_rec, 3),
                "section_time_s": t_rec,
                "position_px": pos_rest,
                "scale": scale_rest,
                "opacity": op_rest,
                "state": "reposition_start",
            })
            kfs_plan.append({
                "time_s": round(abs_offset + t_rec_end, 3),
                "section_time_s": t_rec_end,
                "position_px": r_pos,
                "scale": r_sc,
                "opacity": r_op,
                "easing": "ease_out",
                "state": "recede_hold",
            })
            kfs_sg.append({"time": t_rec, "pos": [pos_rest[0], pos_rest[1], 0.0], "scale_mult": scale_rest, "opacity": op_rest})
            kfs_sg.append({"time": t_rec_end, "pos": [r_pos[0], r_pos[1], 0.0], "scale_mult": r_sc, "opacity": r_op})

        track_rec: Dict[str, Any] = {
            "id": inst_id,
            "file": a_rel,
            "disk_path": str(a_disk),
            "role": role,
            "title_en": asset.get("title_en", ""),
            "anchor": anchor,
            "layer": layer_idx,
            "in_s": round(abs_offset + in_l, 3),
            "out_s": round(abs_offset + out_l, 3),
            "section_in_s": round(in_l, 3),
            "section_out_s": round(out_l, 3),
            "entry_cue_ar": cue_ar,
            "position_px": pos_rest,
            "action": action_desc,
            "relation_to_previous": relation_note,
            "keyframes": kfs_plan,
            "then": "recede_hold" if recede_at else "hold",
        }
        if is_g:
            track_rec["target_visible_height_px"] = target_vis_h
        else:
            track_rec["target_max_side_px"] = target_max_side

        sg_obj: Dict[str, Any] = {
            "id": inst_id,
            "instance_id": inst_id,
            "asset_id": aid,
            "path": str(a_disk),
            "in": round(in_l, 3),
            "out": round(out_l, 3),
            "pos": pos_init,
            "position": pos_init,
            "grounded": is_g,
            "anchor_mode": "visible_bounds",
            "entrance": "direct",
            "initial_opacity": op_init,
            "fade_out": 0.0,
            "three_d": True,
            "z": 0.0,  # Zero parallax lock with BG_Scenery & GroundShadow!
            "role": role,
        }
        if kfs_sg:
            sg_obj["keyframes"] = kfs_sg
        if is_g:
            sg_obj["target_visible_height_px"] = target_vis_h
            sh_kfs = None
            if pos_init != pos_rest:
                sh_kfs = [
                    {"time": round(in_l, 3), "pos": [pos_init[0], round(pos_init[1] + 3.0, 1)]},
                    {"time": t_arr, "pos": [pos_rest[0], round(pos_rest[1] + 3.0, 1)]},
                ]
            sg_shadows.append({
                "id": f"shadow_{inst_id}",
                "kind": "ground_shadow",
                "shape": "ellipse",
                "position": [pos_init[0], round(pos_init[1] + 3.0, 1)],
                "size": [145.0, 22.0],
                "fill": "#1A140E",
                "opacity": 26.0,
                "start": round(in_l, 3),
                "end": round(out_l, 3),
                "three_d": True,
                "z": 0.0,
                "no_pop": True,
                "fade_out": 0.0,
                **({"keyframes": sh_kfs} if sh_kfs else {}),
            })
        else:
            sg_obj["target_max_side_px"] = target_max_side

        element_tracks.append(track_rec)
        sg_assets_flat.append(sg_obj)
        return track_rec

    # Default wide camera base segment helper with strict zero-edge-bleed bounds clamping
    def _clamp_cam(px: List[float], z_mag: float) -> Tuple[List[float], float]:
        zm = max(1.0, float(z_mag))
        safe_dx = max(0.0, (CANVAS_W * 0.5) * (1.005 - 1.0 / zm) - 12.0)
        safe_dy = max(0.0, (CANVAS_H * 0.5) * (1.005 - 1.0 / zm) - 8.0)
        cx = round(max(CANVAS_W * 0.5 - safe_dx, min(CANVAS_W * 0.5 + safe_dx, float(px[0]))), 1)
        cy = round(max(CANVAS_H * 0.5 - safe_dy, min(CANVAS_H * 0.5 + safe_dy, float(px[1]))), 1)
        return ([cx, cy], zm)

    def _add_cam_seg(subject: str, cue: str, st_l: float, en_l: float, p0: List[float], p1: List[float], z0: float, z1: float, note: str) -> None:
        cp0, cz0 = _clamp_cam(p0, z0)
        cp1, cz1 = _clamp_cam(p1, z1)
        camera_segments.append({
            "focus_subject_ar": subject,
            "cue_ar": cue,
            "start_s": round(abs_offset + st_l, 3),
            "end_s": round(abs_offset + en_l, 3),
            "section_start_s": round(st_l, 3),
            "section_end_s": round(en_l, 3),
            "from_pos_px": cp0,
            "to_pos_px": cp1,
            "from_zoom": cz0,
            "to_zoom": cz1,
            "note_ar": note,
        })

    # Per-scene choreography across SECTION_01..12
    for sc_idx, (sc, (s0, s1)) in enumerate(zip(sj_scenes, windows)):
        sc_num = int(sc["scene_number"])
        frag = str(sc.get("narration_fragment_ar") or "")
        cue1 = str(sc.get("entry_cue_ar") or (frag.split()[0] if frag else ""))
        cue2 = _pick_second_phrase_cue(frag)

        raw_assets = sorted(sc["assets"], key=lambda a: int(a.get("order_in_scene", a.get("number", 0))))
        grounded_list = [a for a in raw_assets if bool(a.get("grounded", False))]
        insert_list = [a for a in raw_assets if not bool(a.get("grounded", False))]
        char_leads = _character_leads_sentence(sid_upper, sc_num, sc)
        t2_local = _second_entry_time(cue2, words, s0, s1) if len(raw_assets) >= 2 else s0

        # SECTION 01 Bespoke Continuous Hall Choreography matching user blueprint!
        if sec_idx == 1:
            if sc_num == 1:
                # Bayezid on Ankara plain, seal glides in from left on "في أنقرة" and holds beside him
                _add_asset_pair(
                    sc_num=1, asset=grounded_list[0], in_l=s0, out_l=s1, cue_ar="أُسر بايزيد",
                    pos_init=[1380.0, 840.0], pos_rest=[1380.0, 840.0],
                    action_desc="hold_grounded", relation_note="افتتاحية سهل أنقرة: تثبيت بايزيد على الأرض", target_vis_h=450.0,
                )
                _add_asset_pair(
                    sc_num=1, asset=insert_list[0], in_l=t2_local, out_l=s1, cue_ar="في أنقرة",
                    pos_init=[455.0, 490.0], pos_rest=[560.0, 465.0], scale_init=0.90, scale_rest=1.0, op_init=85.0, op_rest=100.0,
                    t_move_dur=0.68, action_desc="slide_in_and_hold", relation_note="يدخل الختم المنكسر قرب بايزيد لإظهار سقوط سلطته", target_max_side=310.0,
                )
                _add_cam_seg("ساحة أنقرة وبايزيد", "أُسر بايزيد", s0, s1, [960, 540], [960, 540], 1.0, 1.0, "كادر واسع ثابت لتثبيت جغرافية الهزيمة")
            elif sc_num == 2:
                # Single cut to Edirne Council; Messenger walks in; short camera push onto the sealed dispatch!
                _add_asset_pair(
                    sc_num=2, asset=grounded_list[0], in_l=s0, out_l=s1, cue_ar="لكن حين وصل",
                    pos_init=[1500.0, 840.0], pos_rest=[1320.0, 840.0], t_move_dur=1.05,
                    action_desc="walk_in_to_deliver_dispatch", relation_note="قطع واحد إلى القاعة ودخول الرسول بالرسالة المختومة", target_vis_h=440.0,
                )
                _add_cam_seg(
                    "الرسالة المختومة بيد الرسول", "خبر أسره", s0, s1,
                    [960, 540], [1110, 595], 1.0, 1.20,
                    "حركة كاميرا مدروسة تقترب من الرسول والرسالة مع ثبات الأرضية",
                )
            elif sc_num == 3:
                # Edirne gate enters first, then recedes smoothly to side in Sc04 to make space for chest & treasurer!
                s4_end = windows[3][1]  # Keep gate visible into Sc04 ("بقيت فيها موارد")!
                s4_start = windows[3][0]
                _add_asset_pair(
                    sc_num=3, asset=insert_list[0], in_l=s0, out_l=s4_end, cue_ar="بقيت المدينة",
                    pos_init=[580.0, 470.0], pos_rest=[560.0, 470.0], t_move_dur=0.45,
                    recede_at=(s4_start, [330.0, 385.0], 0.72, 82.0),
                    action_desc="present_then_glide_aside_for_treasury", relation_note="تتراجع البوابة لطرف الكادر لإفساح مكان لصندوق الموارد", target_max_side=285.0,
                )
                _add_asset_pair(
                    sc_num=3, asset=grounded_list[0], in_l=t2_local, out_l=s1, cue_ar="في يد العثمانيين",
                    pos_init=[1380.0, 840.0], pos_rest=[1380.0, 840.0], op_init=0.0, op_rest=100.0, t_move_dur=0.22,
                    action_desc="reveal_guard_grounded", relation_note="حارس البوابة يتمركز على الأرضية بجانب مجسّم أدرنة", target_vis_h=420.0,
                )
                _add_cam_seg("بوابة أدرنة والحارس", "بقيت المدينة", s0, s1, [1110, 595], [960, 540], 1.20, 1.0, "عودة تدريجية للكادر الواسع داخل قاعة أدرنة")
            elif sc_num == 4:
                # Cash chest arrives right beside receding gate + treasurer holds ledger on right!
                _add_asset_pair(
                    sc_num=4, asset=insert_list[0], in_l=s0, out_l=s1, cue_ar="وبقيت فيها موارد",
                    pos_init=[790.0, 545.0], pos_rest=[730.0, 490.0], scale_init=0.90, scale_rest=1.0, op_init=0.0, op_rest=100.0,
                    t_move_dur=0.55, action_desc="rise_to_focus_beside_gate", relation_note="يظهر الصندوق بجوار البوابة المتراجعة لبيان بقاء الموارد في أدرنة", target_max_side=290.0,
                )
                _add_asset_pair(
                    sc_num=4, asset=grounded_list[0], in_l=t2_local, out_l=s1, cue_ar=cue2,
                    pos_init=[1380.0, 840.0], pos_rest=[1380.0, 840.0], op_init=0.0, op_rest=100.0, t_move_dur=0.20,
                    action_desc="treasurer_with_ledger", relation_note="أمين الخزينة على يمين الكادر يعرض السجل", target_vis_h=440.0,
                )
                _add_cam_seg("المدينة والموارد", "وبقيت فيها موارد", s0, s1, [960, 540], [960, 540], 1.0, 1.0, "ثبات الكادر لتظهر العلاقة بين البوابة والصندوق والسجل")
            elif sc_num == 5:
                # Stay in Edirne Council! Fractured Anatolia relief enters as explanatory insert + gentle safe pan toward it!
                _add_asset_pair(
                    sc_num=5, asset=insert_list[0], in_l=s0, out_l=s1, cue_ar="على الجانب الآخر",
                    pos_init=[430.0, 445.0], pos_rest=[610.0, 465.0], scale_init=0.90, scale_rest=1.05, op_init=0.0, op_rest=100.0,
                    t_move_dur=0.75, action_desc="explanatory_map_insert_slide", relation_note="خريطة تفكك الأناضول تدخل كإدراج توضيحي مع بقاء قاعة أدرنة", target_max_side=320.0,
                )
                _add_cam_seg("إدراج الأناضول داخل القاعة", "على الجانب الآخر", s0, s1, [960, 540], [860, 505], 1.0, 1.14, "انتقال انتباه الكاميرا نحو خريطة الأناضول الممزقة داخل القاعة")
            elif sc_num == 6:
                # Return focus to Edirne affairs: Süleyman + triple wax seals! Keep triple seals gliding up-left into Sc07!
                s7_end = windows[6][1]
                s7_start = windows[6][0]
                _add_asset_pair(
                    sc_num=6, asset=grounded_list[0], in_l=s0, out_l=s1, cue_ar="صارت الأسرة",
                    pos_init=[1380.0, 840.0], pos_rest=[1380.0, 840.0],
                    action_desc="hold_prince_grounded", relation_note="عودة التركيز داخل القاعة مع الأمير سليمان", target_vis_h=445.0,
                )
                _add_asset_pair(
                    sc_num=6, asset=insert_list[0], in_l=t2_local, out_l=s7_end, cue_ar=cue2,
                    pos_init=[470.0, 470.0], pos_rest=[580.0, 465.0], scale_init=0.92, scale_rest=1.0, op_init=0.0, op_rest=100.0, t_move_dur=0.60,
                    recede_at=(s7_start, [330.0, 385.0], 0.72, 76.0),
                    action_desc="three_seals_present_then_recede", relation_note="تظهر الأختام الثلاثة للدلالة على تعدد الأمراء ثم تتراجع قبيل الاتفاق", target_max_side=310.0,
                )
                _add_cam_seg("الأسرة والأختام الثلاثة", "صارت الأسرة", s0, s1, [860, 505], [960, 540], 1.14, 1.0, "عودة للاتساع الكامل أمام المفارقة")
            elif sc_num in (7, 8):
                # Treaties/Hourglass inserts inside continuing Edirne hall (no Byzantine location cut!)
                _add_asset_pair(
                    sc_num=sc_num, asset=insert_list[0], in_l=s0, out_l=s1, cue_ar=cue1,
                    pos_init=[680.0, 495.0], pos_rest=[660.0, 470.0], scale_init=0.92, scale_rest=1.0, op_init=0.0, op_rest=100.0,
                    t_move_dur=0.55, action_desc="treaty_breathing_room_insert", relation_note="إدراج الوثيقة/الساعة الرملية داخل سياق القاعة", target_max_side=300.0,
                )
                _add_cam_seg("وثائق التهدئة والمتنفس", cue1, s0, s1, [960, 540], [960, 540], 1.0, 1.0, "كادر ثابت لعرض بنود التسوية والزمن")
            elif sc_num == 9:
                # Tied ribbons treaty moves to center beside Mehmed grounded! Keeps scroll visible into Sc10 finale!
                s10_end = windows[9][1]
                s10_start = windows[9][0]
                _add_asset_pair(
                    sc_num=9, asset=insert_list[0], in_l=s0, out_l=s10_end, cue_ar="ثم نتتبع",
                    pos_init=[460.0, 470.0], pos_rest=[580.0, 465.0], scale_init=0.92, scale_rest=1.0, op_init=0.0, op_rest=100.0, t_move_dur=0.65,
                    recede_at=(s10_start, [335.0, 385.0], 0.72, 80.0),
                    action_desc="diplomatic_scroll_then_recede", relation_note="وثيقة التحالفات تتراجع لطرف الكادر عند ختام الوحدة", target_max_side=305.0,
                )
                _add_asset_pair(
                    sc_num=9, asset=grounded_list[0], in_l=t2_local, out_l=s1, cue_ar=cue2,
                    pos_init=[1380.0, 840.0], pos_rest=[1380.0, 840.0], op_init=0.0, op_rest=100.0, t_move_dur=0.45,
                    action_desc="mehmed_united_command", relation_note="دخول محمد جلبي على الأرضية عند ذكر صاحب الأوامر الواحد", target_vis_h=450.0,
                )
                _add_cam_seg("تغيّر التحالفات حتى 1413", "ثم نتتبع", s0, s1, [960, 540], [960, 540], 1.0, 1.0, "اتزان التكوين قبل الحسم")
            elif sc_num == 10:
                _add_asset_pair(
                    sc_num=10, asset=insert_list[0], in_l=s0, out_l=s1, cue_ar="يومها بان",
                    pos_init=[750.0, 510.0], pos_rest=[680.0, 475.0], scale_init=0.92, scale_rest=1.0, op_init=0.0, op_rest=100.0,
                    t_move_dur=0.60, action_desc="paired_gates_resolution", relation_note="البوابات المتحدة تتقدم جوار التحالفات المتراجعة", target_max_side=300.0,
                )
                _add_asset_pair(
                    sc_num=10, asset=grounded_list[0], in_l=t2_local, out_l=s1, cue_ar=cue2,
                    pos_init=[1380.0, 840.0], pos_rest=[1380.0, 840.0], op_init=0.0, op_rest=100.0, t_move_dur=0.40,
                    action_desc="mehmed_final_hold", relation_note="خاتمة السيكشن الأول داخل قاعة أدرنة", target_vis_h=450.0,
                )
                _add_cam_seg("الخاتمة: ما بقي من موارد", "يومها بان", s0, s1, [960, 540], [960, 540], 1.0, 1.0, "ثبات ختامي متوازن")

        # SECTIONS 02..12: Consistent place-first motivated motion & persistence!
        else:
            ordered = (grounded_list + insert_list) if char_leads else (insert_list + grounded_list)
            for ord_i, asset in enumerate(ordered):
                a_in = s0 if ord_i == 0 else t2_local
                a_cue = cue1 if ord_i == 0 else cue2
                is_g = bool(asset.get("grounded", False))
                is_walk = is_g and _is_walking_pose(asset)
                gx_base = float(asset.get("stage_x_px") or (1380.0 if is_g else 560.0))
                if is_g:
                    gy = float(asset.get("stage_baseline_y_px") or 840.0)
                    p0 = [round(gx_base + 115.0, 1), gy] if is_walk else [gx_base, gy]
                    p1 = [gx_base, gy]
                    op0 = 100.0 if ord_i == 0 else 0.0
                    _add_asset_pair(
                        sc_num=sc_num, asset=asset, in_l=a_in, out_l=s1, cue_ar=a_cue,
                        pos_init=p0, pos_rest=p1, op_init=op0, op_rest=100.0, t_move_dur=0.85 if is_walk else 0.35,
                        action_desc="walk_arrival_hold" if is_walk else "grounded_hold",
                        relation_note="ثبات على خط الأرض بعد الدخول" if not is_walk else "حركة مشي مضبوطة على الأرضية",
                        target_vis_h=345.0 if "mule" in str(asset.get("title_en", "")).lower() else 445.0,
                    )
                else:
                    # Motivated short directional slide from margin to settled resting composition
                    p0 = [round(gx_base - 80.0, 1), 485.0]
                    p1 = [gx_base, 468.0]
                    _add_asset_pair(
                        sc_num=sc_num, asset=asset, in_l=a_in, out_l=s1, cue_ar=a_cue,
                        pos_init=p0, pos_rest=p1, scale_init=0.92, scale_rest=1.0,
                        op_init=100.0 if ord_i == 0 else 0.0, op_rest=100.0, t_move_dur=0.65,
                        action_desc="slide_to_resting_focus",
                        relation_note="انزلاق إدراجي هادئ نحو موضع الثبات",
                        target_max_side=300.0,
                    )
            # Gentle purposeful camera push every dramatic climax scene (e.g. Sc05/Sc09), wide calm hold elsewhere
            if sc_num in (2, 7) and grounded_list:
                _add_cam_seg(f"تركيز المشهد {sc_num}", cue1, s0, s1, [960, 540], [1080, 555], 1.0, 1.12, "اقتراب هادئ لتعميق التركيز على الفعل داخل نفس المكان")
            else:
                _add_cam_seg(f"المشهد {sc_num}", cue1, s0, s1, [960, 540], [960, 540], 1.0, 1.0, "كادر ثابت يحفظ وضوح الشخصيات والإدراجات")

    return element_tracks, sg_assets_flat, sg_shadows, camera_segments


def _mood_for_section(sec_idx: int) -> str:
    return {
        1: "imperial_slate",
        2: "candle_bronze",
        3: "ocean_sapphire",
        4: "sandstone_dawn",
        5: "sandstone_dawn",
        6: "pressure_crimson",
        7: "twilight_indigo",
        8: "candle_bronze",
        9: "obsidian_teal",
        10: "eureka_emerald",
        11: "twilight_indigo",
        12: "imperial_slate",
    }.get(sec_idx, "imperial_slate")


def build_workflow_montage_episode(
    proj_dir: Path,
    *,
    write_section_graphs: bool = True,
) -> Dict[str, Any]:
    """Read `WORKFLOW.json` + ordered `SECTION.json` files and emit `direction_plan.json` + EffectCraft `scene_graph.v2.json`."""
    proj_dir = Path(proj_dir)
    meta_dir = resolve_workflow_meta_dir(proj_dir)
    if meta_dir is None:
        raise FileNotFoundError(f"WORKFLOW.json not found inside project: {proj_dir}")

    wf = json.loads((meta_dir / "WORKFLOW.json").read_text(encoding="utf-8"))
    direction_sections: List[Dict[str, Any]] = []
    abs_offset = 0.0
    missing_files: List[str] = []
    section_graphs: Dict[str, Dict[str, Any]] = {}

    for sec_idx, sec_meta in enumerate(wf["sections"], 1):
        sid_upper = sec_meta["section_id"]
        sid_low = sid_upper.lower()
        sec_json_p = meta_dir / sid_upper / "SECTION.json"
        if not sec_json_p.is_file():
            sec_json_p = meta_dir / "EXTRACTED_ASSETS" / sid_upper / "SECTION.json"
        sj = json.loads(sec_json_p.read_text(encoding="utf-8"))

        tm_p = proj_dir / "sections" / sid_low / "timing" / f"{sid_low}_timing_master.json"
        if tm_p.is_file():
            tm = json.loads(tm_p.read_text(encoding="utf-8"))
            words = tm.get("words", [])
            sec_dur = round(float(tm.get("duration_sec") or tm.get("audio_duration_sec") or (words[-1]["end"] if words else 35.0)), 3)
            timing_status = "synced_from_audio"
            windows = _match_scene_windows(sj["scenes"], words, sec_dur, float(sj["start_seconds"]), float(sj["end_seconds"]))
        else:
            words = []
            sec_dur = round(float(sj["end_seconds"]) - float(sj["start_seconds"]), 3)
            timing_status = "estimated"
            est0 = float(sj["start_seconds"])
            windows = [
                (round(float(sc["start_seconds"]) - est0, 3), round(float(sc["end_seconds"]) - est0, 3))
                for sc in sj["scenes"]
            ]

        bg_track_raw = _sustained_background_plan(sec_idx, sj["scenes"], windows, sec_dur)
        bg_track_plan: List[Dict[str, Any]] = []
        sg_bg_layers: List[Dict[str, Any]] = []
        for b in bg_track_raw:
            b_disk = _resolve_media_path(proj_dir, b["file"], sid_upper)
            if not b_disk.is_file():
                missing_files.append(f"{sid_upper}: {b['file']} ({b_disk})")
            bg_track_plan.append({
                "file": b["file"],
                "background_id": b["background_id"],
                "in_s": round(abs_offset + b["section_in_s"], 3),
                "out_s": round(abs_offset + b["section_out_s"], 3),
                "section_in_s": b["section_in_s"],
                "section_out_s": b["section_out_s"],
                "cut_cue_ar": b["cut_cue_ar"],
                "reason_ar": b["reason_ar"],
            })
            sg_bg_layers.append({
                "path": str(b_disk),
                "in": b["section_in_s"],
                "out": b["section_out_s"],
                "opacity": 100.0,
                "ken_burns": False,
                "fade_sec": 0.0,
                "three_d": True,
                "z": 0.0,
            })

        elem_tracks, sg_assets_flat, sg_shadows, cam_segments = _assemble_element_tracks_and_camera(
            proj_dir=proj_dir,
            sec_idx=sec_idx,
            sid_upper=sid_upper,
            sj_scenes=sj["scenes"],
            windows=windows,
            words=words,
            abs_offset=abs_offset,
            sec_dur=sec_dur,
        )
        for et in elem_tracks:
            if not Path(et["disk_path"]).is_file():
                missing_files.append(f"{sid_upper}: {et['file']} ({et['disk_path']})")

        # Convert camera_track into EffectCraft 3D Camera keyframes (`zoom=1650`, matching z=-1650/mag)
        cam_kfs: List[Dict[str, Any]] = []
        for cs in cam_segments:
            st_c = cs["section_start_s"]
            en_c = cs["section_end_s"]
            z_start = round(-1650.0 / max(0.5, cs["from_zoom"]), 1)
            z_end = round(-1650.0 / max(0.5, cs["to_zoom"]), 1)
            px0, py0 = cs["from_pos_px"]
            px1, py1 = cs["to_pos_px"]
            if not cam_kfs or abs(cam_kfs[-1]["time"] - st_c) > 0.02:
                cam_kfs.append({"time": st_c, "pos": [float(px0), float(py0), z_start], "poi": [float(px0), float(py0), 0.0]})
            if en_c > st_c + 0.05:
                t_mid = round(min(en_c - 0.04, st_c + (en_c - st_c) * 0.72), 3)
                cam_kfs.append({"time": t_mid, "pos": [float(px1), float(py1), z_end], "poi": [float(px1), float(py1), 0.0]})

        mood = _mood_for_section(sec_idx)
        pal = LIVING_GRADIENT_PALETTES.get(mood, LIVING_GRADIENT_PALETTES["imperial_slate"])

        # Distribute elements into validated scene buckets strictly partitioning [0, sec_dur]
        sg_scenes: List[Dict[str, Any]] = []
        for sc_idx, (sc, (s0, s1)) in enumerate(zip(sj["scenes"], windows)):
            sc_num = int(sc["scene_number"])
            in_bucket = [
                a for a in sg_assets_flat
                if s0 - 1e-4 <= float(a["in"]) < s1 - 1e-4
                or (sc_idx == 0 and float(a["in"]) == 0.0)
            ]
            # Guarantee every scene has a valid primary element visible inside [s0, s1]
            if not in_bucket:
                active_here = [a for a in sg_assets_flat if float(a["in"]) <= s0 and float(a["out"]) > s0 + 0.05]
                in_bucket = active_here[:1]
            sg_scenes.append({
                "scene_id": f"beat_{sc_num:02d}",
                "time": {"start": s0, "end": s1},
                "headline": str(sc.get("entry_cue_ar") or f"beat_{sc_num:02d}")[:32],
                "mood": mood,
                "composition": "stable_place_continuous",
                "assets": in_bucket,
            })

        sg_v2: Dict[str, Any] = {
            "schema_version": "aion.scene_graph.v2",
            "project_id": f"{proj_dir.name}_{sid_low}",
            "section_id": sid_low,
            "video_format": "workflow_montage",
            "locked_by_director": True,
            "duration": sec_dur,
            "total_duration": sec_dur,
            "width": CANVAS_W,
            "height": CANVAS_H,
            "source_timeline": {"duration_sec": sec_dur},
            "composition": {
                "width": CANVAS_W,
                "height": CANVAS_H,
                "resolution": [CANVAS_W, CANVAS_H],
                "fps": 30,
                "duration": sec_dur,
                "enable_3d_stage": True,
            },
            "cinema_stage": {
                "aspect": "16:9",
                "video_format": "workflow_montage",
                "mood": mood,
                "palette": pal,
                "bg_scrim_opacity": 0.0,
                "disable_master_grade": True,
            },
            "background_layers": sg_bg_layers,
            "narrative_intent": {
                "primary": "continuous_place_story_montage",
                "format": "workflow_montage",
                "summary": sj["title_ar"],
            },
            "visual_metaphor": {
                "stage_style": "sustained_room_motivated_motion",
                "connectors": "spatial_layout_no_arrows",
                "icons": "none_uncluttered",
            },
            "motion_paths": [],
            "lighting": {"enabled": False, "lights": []},
            "timing_anchors": [
                {"id": f"beat_{i+1:02d}", "start": w0, "end": w1, "mood": mood}
                for i, (w0, w1) in enumerate(windows)
            ],
            "tool_requirements": ["camera_3d_locked_floor"],
            "fallbacks": {"texture_missing": "skip", "sfx_missing": "voice_only_clean"},
            "quality_constraints": {
                "grounded_characters_on_floor": True,
                "zero_uniform_auto_effects": True,
                "visible_bounds_anchors": True,
            },
            "scenes": sg_scenes,
            "assets": sg_assets_flat,
            "procedural_graphics": sg_shadows,
            "vfx": [],
            "sfx": [],
            "typography": [],
            "camera": {
                "enabled": True,
                "type": "motivated_focus_3d",
                "zoom": 1650.0,
                "keyframes": cam_kfs,
            },
        }
        sync_scene_graph_v2_views(sg_v2)
        # Preserve multi-scene spanning `out` timestamps intact after sync
        sg_v2["assets"] = sg_assets_flat
        ok, errs = validate_scene_graph_v2(sg_v2)
        if not ok:
            raise ValueError(f"Direction plan validation failed {sid_low}: {errs}")

        section_graphs[sid_low] = sg_v2
        if write_section_graphs:
            sg_out = proj_dir / "sections" / sid_low / "scene_graph.v2.json"
            sg_out.parent.mkdir(parents=True, exist_ok=True)
            sg_out.write_text(json.dumps(sg_v2, indent=2, ensure_ascii=False), encoding="utf-8")

        clean_elems = [{k: v for k, v in e.items() if k != "disk_path"} for e in elem_tracks]
        direction_sections.append({
            "section_id": sid_upper,
            "title_ar": sj["title_ar"],
            "timing_status": timing_status,
            "canvas_px": [CANVAS_W, CANVAS_H],
            "section_start_s": round(abs_offset, 3),
            "section_end_s": round(abs_offset + sec_dur, 3),
            "section_duration_s": sec_dur,
            "background_track": bg_track_plan,
            "element_tracks": clean_elems,
            "camera_track": cam_segments,
        })
        abs_offset = round(abs_offset + sec_dur, 3)

    if missing_files:
        raise FileNotFoundError("Missing workflow montage media files:\n" + "\n".join(missing_files))

    direction_plan = {
        "schema_version": "ankara.direction_plan.v2",
        "project_id": wf["project_id"],
        "title_ar": wf["title_ar"],
        "paths_relative_to": "ANKARA_PRODUCTION",
        "timing_status": "synced_from_audio" if any(s["timing_status"] == "synced_from_audio" for s in direction_sections) else "estimated",
        "canvas_px": [CANVAS_W, CANVAS_H],
        "episode_duration_s": abs_offset,
        "sections": direction_sections,
    }
    if write_section_graphs:
        (proj_dir / "direction_plan.json").write_text(
            json.dumps(direction_plan, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return {"direction_plan": direction_plan, "section_graphs": section_graphs}


def build_workflow_montage_section(proj_dir: Path, section_id: str) -> Dict[str, Any]:
    res = build_workflow_montage_episode(proj_dir, write_section_graphs=True)
    sid_low = str(section_id).lower()
    if sid_low not in res["section_graphs"]:
        raise KeyError(f"Section '{sid_low}' not found in WORKFLOW.json for {proj_dir.name}")
    return res["section_graphs"][sid_low]

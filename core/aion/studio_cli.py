"""AION Creative Studio V5 CLI Handlers (`pipeline_cli.py studio ...`).

Exposes:
  - `studio doctor`        : Read-only readiness check (EffectCraft, capabilities, fonts, disk, golden integrity)
  - `studio capabilities`  : Show or re-probe `config/effectcraft_capabilities.json`
  - `studio graphics-test` : Verify grammar + procedural vectors + Scene Graph V2 + EffectCraft test frame
  - `studio compile`       : Direct (if needed) + ECGC V2 compile + MP4 render inside isolated run directory
  - `studio preview`       : Fast multi-frame ECGC V2 preview + contact sheet inside isolated run directory
  - `studio qa`            : Visual Intelligence QA (`creative_quality_report.json` + `creative_contact_sheet.png`)
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.aion.capability_prober import (
    CAPABILITY_IDS,
    DEFAULT_CAPABILITIES_PATH,
    find_effectcraft_cli,
    load_capabilities_registry,
    run_capability_probes,
)
from core.aion.contracts import migrate_scene_graph_v1_to_v2, SCENE_GRAPH_V2
from core.aion.creative_director import AICreativeDirector
from core.aion.ecgc_compiler import CreativeGraphicsCompiler
from core.aion.motion_grammar import MotionDesignGrammarEngine, NARRATIVE_INTENTS
from core.aion.procedural_graphics import ProceduralGraphicsEngine
from core.aion.semantic_storyboard_director import synthesize_editorial_headline
from core.aion.typography_registry import (
    build_and_probe_font_registry,
    load_font_registry,
    verify_font_files_sha256,
)
from core.aion.visual_qa import evaluate_creative_render
from core.config.settings import TYPOGRAPHY_REGISTRY_PATH, get_effectcraft_font_dirs

ROOT_DIR = Path(__file__).resolve().parents[2]
PROJECTS_DIR = ROOT_DIR / "projects"
PROTECTED_PROJECTS = {"mind_glitches_ar"}


def _active_project_name() -> str:
    ap = ROOT_DIR / ".active_project"
    if ap.is_file():
        val = ap.read_text(encoding="utf-8", errors="replace").strip()
        if val:
            return val
    return "mind_glitches_ar"


def _resolve_project(project: Optional[str]) -> str:
    return (project or _active_project_name()).strip()


def _resolve_project_dir(proj: str) -> Path:
    p = Path(proj)
    if p.is_absolute() and p.is_dir():
        return p.resolve()
    rel = (ROOT_DIR / proj)
    if rel.is_dir():
        return rel.resolve()
    return (PROJECTS_DIR / proj).resolve()


def _is_protected(proj_dir: Path, proj: str) -> bool:
    return proj in PROTECTED_PROJECTS or proj_dir.name in PROTECTED_PROJECTS


def _norm_sec_id(sec: str) -> str:
    s = str(sec).strip()
    if s.startswith("section_"):
        return s
    return f"section_{s.zfill(2)}" if s.isdigit() else f"section_{s}"


def _build_run_section_dir(proj: str, sec_id: str, run_id: Optional[str], *, force: bool = False) -> Path:
    proj_dir = _resolve_project_dir(proj)
    if _is_protected(proj_dir, proj):
        raise PermissionError(
            f"Refusing to write inside golden reference project '{proj}'. Copy to an isolated test project first."
        )
    rid = run_id or datetime.now().strftime("v5_%Y%m%d_%H%M%S")
    base = proj_dir / "exports" / "runs" / rid / "sections" / sec_id
    if base.exists() and any(base.iterdir()) and not force and run_id is not None:
        raise FileExistsError(
            f"Isolated run directory already populated: {base}. Omit --run-id for a fresh run or pass --force."
        )
    base.mkdir(parents=True, exist_ok=True)
    return base


def _latest_run_dir(proj: str, sec_id: str) -> Optional[Path]:
    runs_dir = _resolve_project_dir(proj) / "exports" / "runs"
    if not runs_dir.is_dir():
        return None
    candidates = sorted(
        [p / "sections" / sec_id for p in runs_dir.iterdir() if p.is_dir() and (p / "sections" / sec_id).is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _collect_brief_from_project(proj: str, sec_id: str, style_mode: str, duration_override: Optional[float] = None) -> Dict[str, Any]:
    proj_dir = _resolve_project_dir(proj)
    sec_dir = proj_dir / "sections" / sec_id
    script_txt = ""
    for cand in (
        sec_dir / "script.txt",
        proj_dir / "inputs" / "script" / "sections" / f"{sec_id}.txt",
        proj_dir / "script.txt",
    ):
        if cand.is_file():
            script_txt = cand.read_text(encoding="utf-8", errors="replace").strip()
            break

    audio_wav: Optional[Path] = None
    for cand in (
        sec_dir / "voice" / f"{sec_id}.wav",
        sec_dir / "voice.wav",
        sec_dir / f"{sec_id}_voice.wav",
        sec_dir / "audio" / "voice.wav",
    ):
        if cand.is_file():
            audio_wav = cand
            break
    if audio_wav is None and sec_dir.is_dir():
        wavs = sorted(sec_dir.rglob("*.wav"))
        if wavs:
            audio_wav = wavs[0]

    beats: List[Dict[str, Any]] = []
    words_list: List[Dict[str, Any]] = []
    timing_path = sec_dir / "timing" / f"{sec_id}_timing_master.json"
    if timing_path.is_file():
        try:
            tdata = json.loads(timing_path.read_text(encoding="utf-8"))
            words_list = list(tdata.get("words", []))
            for idx, s in enumerate(tdata.get("sentences", [])):
                beats.append({
                    "id": f"beat_{idx + 1:02d}",
                    "start": float(s.get("start", 0.0)),
                    "end": float(s.get("end", 4.0)),
                    "text": str(s.get("text", "")),
                })
            if not script_txt and beats:
                script_txt = " ".join(b["text"] for b in beats)
        except Exception:
            pass

    dur = float(duration_override or 0.0)
    if dur <= 0.0 and audio_wav and audio_wav.is_file():
        pr = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_wav)],
            capture_output=True,
            text=True,
        )
        if pr.returncode == 0 and pr.stdout.strip():
            dur = float(pr.stdout.strip())
    if dur <= 0.0:
        dur = 5.5

    # Trim beat list to dur if duration is shorter
    if beats:
        beats = [b for b in beats if b["start"] < dur - 0.1]
        for b in beats:
            b["end"] = min(dur, b["end"])

    assets: List[Dict[str, Any]] = []
    assets_dir = sec_dir / "assets"
    cat_map: Dict[str, Dict[str, Any]] = {}
    try:
        from core.aion.shorts_director import _load_section_inputs
        _, _, cat_map = _load_section_inputs(proj_dir, sec_id)
    except Exception:
        pass
    if assets_dir.is_dir():
        pngs = sorted([
            p for p in assets_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and "contact_sheet" not in p.stem.lower()
        ])
        for p in pngs:
            meta = cat_map.get(p.stem, {})
            assets.append({
                "id": p.stem,
                "path": str(p),
                "filename": meta.get("filename", p.name),
                "name_ar": meta.get("name_ar", ""),
                "name_en": meta.get("name_en", ""),
                "description_ar": meta.get("description_ar", ""),
                "description_en": meta.get("description_en", ""),
                "narrative_role": meta.get("narrative_role", "illustrative_prop"),
                "row": meta.get("row"),
                "col": meta.get("col"),
            })

    proj_fps = 30
    proj_lang = "ar"
    proj_meta_p = proj_dir / "project.json"
    if proj_meta_p.is_file():
        try:
            pmeta = json.loads(proj_meta_p.read_text(encoding="utf-8"))
            if pmeta.get("fps"):
                proj_fps = int(pmeta["fps"])
            if pmeta.get("language"):
                proj_lang = str(pmeta["language"])
        except Exception:
            pass

    headline = synthesize_editorial_headline(script_txt) if script_txt else f"{proj} — {sec_id}"
    return {
        "section_id": sec_id,
        "language": proj_lang,
        "fps": proj_fps,
        "duration_sec": round(dur, 3),
        "audio_file": str(audio_wav) if audio_wav else "",
        "text": script_txt or headline,
        "headline": headline,
        "beats": beats or None,
        "words": words_list,
        "assets": assets,
        "style_mode": style_mode,
    }


def cmd_studio_doctor(*, as_json: bool = False) -> bool:
    """Read-only verification of V5 studio dependencies, EffectCraft CLI, and empirical capabilities."""
    cli = find_effectcraft_cli()
    reg = load_capabilities_registry(DEFAULT_CAPABILITIES_PATH)
    caps = reg.get("capabilities", {})
    summary = reg.get("summary", {})
    free_gb = round(shutil.disk_usage(ROOT_DIR).free / (1024 ** 3), 2)
    ffmpeg_ok = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

    # Check golden snapshot script read-only if baseline and project exist
    golden_status = "UNCHECKED"
    golden_script = ROOT_DIR / "tests" / "aion_cli" / "golden_snapshot.py"
    golden_proj = ROOT_DIR / "projects" / "mind_glitches_ar"
    if golden_script.is_file():
        if golden_proj.is_dir():
            gr = subprocess.run(
                [sys.executable, str(golden_script), "verify", "--project", "mind_glitches_ar"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            golden_status = gr.stdout.strip() or f"rc={gr.returncode}"
        else:
            golden_status = "SKIPPED (no local mind_glitches_ar)"

    typo_reg = load_font_registry() if TYPOGRAPHY_REGISTRY_PATH.is_file() else {}
    typo_sum = typo_reg.get("summary", {})
    payload = {
        "ok": bool(cli and ffmpeg_ok and len(caps) == len(CAPABILITY_IDS)),
        "effectcraft_cli": str(cli) if cli else None,
        "ffmpeg_available": ffmpeg_ok,
        "disk_free_gb": free_gb,
        "capabilities_file": str(DEFAULT_CAPABILITIES_PATH),
        "capabilities_registered": len(caps),
        "capabilities_expected": len(CAPABILITY_IDS),
        "capability_summary": summary,
        "narrative_intents_supported": len(NARRATIVE_INTENTS),
        "asset_factory_icons": len(ProceduralGraphicsEngine.available_icons()),
        "typography_library": {
            "effectcraft_font_dirs": get_effectcraft_font_dirs(),
            "font_registry_path": str(TYPOGRAPHY_REGISTRY_PATH),
            "registry_present": TYPOGRAPHY_REGISTRY_PATH.is_file(),
            "fonts_pass": typo_sum.get("pass", 0),
            "fonts_partial": typo_sum.get("partial", 0),
            "commercial_license_required": typo_sum.get("license_required", 5),
        },
        "golden_reference_integrity": golden_status,
        "active_project": _active_project_name(),
    }
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("=== AION CREATIVE STUDIO V5 DOCTOR ===")
        print(f"EffectCraft CLI    : {payload['effectcraft_cli']}")
        print(f"FFmpeg / FFprobe   : {'OK' if ffmpeg_ok else 'MISSING'}")
        print(f"Disk Free          : {free_gb} GB")
        print(f"Capabilities       : {len(caps)}/{len(CAPABILITY_IDS)} {summary}")
        print(f"Grammar Intents    : {len(NARRATIVE_INTENTS)}")
        print(f"Procedural Icons   : {payload['asset_factory_icons']}")
        print(f"Golden Ref Status  : {golden_status}")
    return bool(payload["ok"])


def cmd_studio_capabilities(*, probe: bool = False, only: Optional[str] = None, as_json: bool = False, use_gpu: bool = False) -> bool:
    """Display cached EffectCraft capabilities or run live empirical probes."""
    if probe:
        only_list = [x.strip() for x in only.split(",") if x.strip()] if only else None
        reg = run_capability_probes(out_json_path=DEFAULT_CAPABILITIES_PATH, only_ids=only_list, use_gpu=use_gpu)
    else:
        reg = load_capabilities_registry(DEFAULT_CAPABILITIES_PATH)
        if not reg.get("capabilities"):
            reg = run_capability_probes(out_json_path=DEFAULT_CAPABILITIES_PATH, use_gpu=use_gpu)

    if as_json:
        print(json.dumps(reg, indent=2, ensure_ascii=False))
        return True


def cmd_studio_fonts(*, probe: bool = False, verify_sha: bool = False, as_json: bool = False) -> bool:
    """Inspect licensed studio font registry, verify SHA-256 hashes, and optionally run live EffectCraft probes."""
    if probe:
        reg = build_and_probe_font_registry(run_live_probe=True)
    elif verify_sha:
        reg = load_font_registry()
        reg["sha256_integrity"] = verify_font_files_sha256()
    else:
        reg = load_font_registry()

    if as_json:
        print(json.dumps(reg, indent=2, ensure_ascii=False))
        return reg.get("sha256_integrity", {}).get("mismatch_count", 0) == 0

    print(f"AION Typography Registry : {TYPOGRAPHY_REGISTRY_PATH}")
    print(f"EFFECTCRAFT_FONT_DIRS    : {reg.get('effectcraft_font_dirs')}")
    print(f"Summary                  : {reg.get('summary', {})}")
    print(f"SHA-256 Integrity        : {reg.get('sha256_integrity', {})}")
    for fam in reg.get("families", []):
        print(f"  [{fam.get('status', '?'):16s}] {fam.get('family', '?'):24s} ec={str(fam.get('verified_in_effectcraft')):5s} lic={fam.get('license')} fallback={fam.get('fallback')}")
    return reg.get("sha256_integrity", {}).get("mismatch_count", 0) == 0

    print(f"EffectCraft Capabilities Registry: {DEFAULT_CAPABILITIES_PATH}")
    print(f"Summary: {reg.get('summary', {})}")
    for cid, c in reg.get("capabilities", {}).items():
        print(f"  [{c.get('status', 'UNKNOWN'):9s}] {cid:20s} — {c.get('title', '')}")
    return True


def cmd_studio_fonts(*, probe: bool = False, verify_sha: bool = False, as_json: bool = False) -> bool:
    """Inspect licensed studio font registry, verify SHA-256 hashes, and optionally run live EffectCraft probes."""
    if probe:
        reg = build_and_probe_font_registry(run_live_probe=True)
    elif verify_sha:
        reg = load_font_registry()
        reg["sha256_integrity"] = verify_font_files_sha256()
    else:
        reg = load_font_registry()

    if as_json:
        print(json.dumps(reg, indent=2, ensure_ascii=False))
        return reg.get("sha256_integrity", {}).get("mismatch_count", 0) == 0

    print(f"AION Typography Registry : {TYPOGRAPHY_REGISTRY_PATH}")
    print(f"EFFECTCRAFT_FONT_DIRS    : {reg.get('effectcraft_font_dirs')}")
    print(f"Summary                  : {reg.get('summary', {})}")
    print(f"SHA-256 Integrity        : {reg.get('sha256_integrity', {})}")
    for fam in reg.get("families", []):
        print(f"  [{fam.get('status', '?'):16s}] {fam.get('family', '?'):24s} ec={str(fam.get('verified_in_effectcraft')):5s} lic={fam.get('license')} fallback={fam.get('fallback')}")
    return reg.get("sha256_integrity", {}).get("mismatch_count", 0) == 0


def cmd_studio_graphics_test(*, mode: str = "all", out_dir: Optional[str] = None, render_preview: bool = False) -> bool:
    """Run procedural graphics, grammar, V2 schema, and optional live EffectCraft preview check."""
    out_root = Path(out_dir) if out_dir else (ROOT_DIR / "cache" / "studio_graphics_test")
    out_root.mkdir(parents=True, exist_ok=True)

    grammar = MotionDesignGrammarEngine()
    assert len(grammar.list_intents()) == 15
    director = AICreativeDirector()

    modes = ["scientific_explanation", "cinematic_2_5d", "editorial_motion_graphics"] if mode == "all" else [mode]
    results: Dict[str, Any] = {}
    compiler = CreativeGraphicsCompiler()

    for m in modes:
        mdir = out_root / m
        mdir.mkdir(parents=True, exist_ok=True)
        brief = {
            "section_id": f"test_{m}",
            "duration_sec": 3.0,
            "headline": "العقل البشري يبني الواقع",
            "subline": f"Studio Graphics Test: {m}",
            "style_mode": m,
        }
        sg_v2 = director.direct_scene(brief)
        (mdir / "scene_graph.v2.json").write_text(json.dumps(sg_v2, indent=2, ensure_ascii=False), encoding="utf-8")

        if render_preview:
            rep = compiler.compile_scene(
                sg_v2,
                section_dir=mdir,
                work_dir=mdir / "work",
                out_ecproj=mdir / f"{m}.ecproj",
                preview_only=True,
                use_gpu=False,
            )
            results[m] = {"ok": rep.get("ok"), "frames": len(rep.get("preview_frames", [])), "ecproj": rep.get("ecproj")}
        else:
            results[m] = {
                "ok": sg_v2.get("schema_version") == SCENE_GRAPH_V2,
                "procedural_items": len(sg_v2.get("procedural_graphics", [])),
                "typography_items": len(sg_v2.get("typography", [])),
            }

    print(json.dumps({"ok": all(v.get("ok") for v in results.values()), "results": results, "out_dir": str(out_root)}, indent=2, ensure_ascii=False))
    return all(v.get("ok") for v in results.values())


def _discover_sections(proj_dir: Path) -> List[str]:
    secs_root = proj_dir / "sections"
    if not secs_root.is_dir():
        return []
    return sorted([p.name for p in secs_root.iterdir() if p.is_dir() and p.name.startswith("section_")])


def cmd_studio_compile(
    *,
    project: Optional[str],
    section: Optional[str] = None,
    all_sections: bool = False,
    style_mode: str = "auto",
    video_format: str = "educational",
    aspect: str = "16:9",
    story_genre: str = "auto",
    run_id: Optional[str] = None,
    preview_only: bool = False,
    use_gpu: bool = True,
    resolution: str = "720p",
    force: bool = False,
    duration_override: Optional[float] = None,
    director_v4: bool = True,
) -> bool:
    """Direct (V2), compile via 10-stage ECGC, render preview/MP4 inside isolated run dir."""
    proj = _resolve_project(project)
    proj_dir = _resolve_project_dir(proj)
    if _is_protected(proj_dir, proj):
        raise PermissionError(
            f"Refusing to write inside golden reference project '{proj}'. Copy to an isolated test project first."
        )
    sec_list = _discover_sections(proj_dir) if all_sections else ([_norm_sec_id(section)] if section else [])
    if not sec_list:
        raise ValueError("Specify --section <id> or pass --all.")

    w_out, h_out = (1080, 1920) if aspect == "9:16" else (1920, 1080)
    shared_run_id = run_id or datetime.now().strftime("v5_%Y%m%d_%H%M%S")
    compiler = CreativeGraphicsCompiler()
    director = AICreativeDirector(width=w_out, height=h_out)
    overall_ok = True
    results: List[Dict[str, Any]] = []

    for sec_id in sec_list:
        run_sec_dir = _build_run_section_dir(proj, sec_id, shared_run_id, force=force)
        sec_src_dir = proj_dir / "sections" / sec_id

        sg_cand = sec_src_dir / "scene_graph.v2.json"
        voice_wav: Optional[Path] = None
        cand_wav = sec_src_dir / "voice" / f"{sec_id}.wav"
        if cand_wav.is_file():
            voice_wav = cand_wav
        from core.aion.workflow_montage_director import (
            build_workflow_montage_episode,
            is_workflow_montage_project,
        )

        fmt_req = str(video_format or "educational").lower()
        if fmt_req == "auto" and is_workflow_montage_project(proj_dir):
            fmt_req = "workflow_montage"

        use_existing_sg = False
        loaded_cand: Optional[Dict[str, Any]] = None
        if fmt_req == "workflow_montage":
            # Dedicated bright-scenery, grounded-floor, WORKFLOW.json + SECTION.json montage pipeline.
            # Cleanly separated from V7/V8 Mehmed educational & narrative explainer pipelines!
            ep_res = build_workflow_montage_episode(proj_dir, write_section_graphs=True)
            sg_v2 = copy.deepcopy(ep_res["section_graphs"][sec_id])
            use_existing_sg = True
        elif (
            sg_cand.is_file()
            and story_genre == "auto"
            and style_mode == "auto"
            and duration_override is None
        ):
            try:
                loaded_cand = json.loads(sg_cand.read_text(encoding="utf-8"))
            except Exception:
                loaded_cand = None
            if loaded_cand is not None:
                cand_aspect = str((loaded_cand.get("canvas") or {}).get("aspect_ratio") or (loaded_cand.get("cinema_stage") or {}).get("aspect") or "16:9")
                is_v7_custom = bool(loaded_cand.get("cinema_stage") or loaded_cand.get("hud_sequence"))
                cand_fmt = str(loaded_cand.get("video_format") or (loaded_cand.get("cinema_stage") or {}).get("video_format") or "").lower()
                if cand_aspect == aspect:
                    if fmt_req == "legacy":
                        use_existing_sg = True
                    elif is_v7_custom and (not cand_fmt or cand_fmt == fmt_req or fmt_req == "auto"):
                        use_existing_sg = True

        if fmt_req == "workflow_montage":
            pass
        elif use_existing_sg and loaded_cand is not None:
            sg_v2 = loaded_cand
        else:
            brief = _collect_brief_from_project(proj, sec_id, style_mode=style_mode, duration_override=duration_override)
            brief["aspect_ratio"] = aspect
            brief["story_genre"] = story_genre
            brief["video_format"] = fmt_req
            if brief.get("audio_file") and Path(str(brief["audio_file"])).is_file():
                voice_wav = Path(str(brief["audio_file"]))
            sg_v2 = director.direct_scene(brief)
            # Preserve hand-authored Quranic verse cards when upgrading legacy sections to V7 Master Cinema
            if loaded_cand and loaded_cand.get("quran_cards") and not sg_v2.get("quran_cards"):
                sg_v2["quran_cards"] = copy.deepcopy(loaded_cand["quran_cards"])

        if director_v4 and fmt_req != "workflow_montage":
            from core.aion.cinematic_director_v4 import apply_director_v4_layer
            sg_v2 = apply_director_v4_layer(
                sg_v2,
                proj_dir=proj_dir,
                section_id=sec_id,
                out_dir=run_sec_dir,
            )["scene_graph"]

        sg_path = run_sec_dir / "scene_graph.v2.json"
        sg_path.write_text(json.dumps(sg_v2, indent=2, ensure_ascii=False), encoding="utf-8")

        ecproj = run_sec_dir / f"{sec_id}_studio.ecproj"
        mp4 = run_sec_dir / f"{sec_id}_studio.mp4"
        rep = compiler.compile_scene(
            sg_v2,
            section_dir=sec_src_dir if sec_src_dir.is_dir() else run_sec_dir,
            work_dir=run_sec_dir / "work",
            out_ecproj=ecproj,
            out_mp4=None if preview_only else mp4,
            voice_wav=voice_wav,
            preview_only=preview_only,
            use_gpu=use_gpu,
            resolution=resolution,
        )
        qa = evaluate_creative_render(
            qa_dir=run_sec_dir / "qa",
            ecproj_path=ecproj,
            mp4_path=mp4 if (not preview_only and mp4.is_file()) else None,
            preview_frames=[Path(p) for p in rep.get("preview_frames", [])],
            scene_graph=sg_v2,
            compile_report=rep,
        )
        sec_ok = bool(rep.get("ok")) and qa.get("verdict") != "FAIL"
        overall_ok = overall_ok and sec_ok
        results.append({
            "section": sec_id,
            "ok": sec_ok,
            "qa_verdict": qa.get("verdict"),
            "mp4": rep.get("mp4"),
            "elapsed_sec": rep.get("elapsed_sec"),
        })

    print(json.dumps({"run_id": shared_run_id, "ok": overall_ok, "sections": results}, indent=2, ensure_ascii=False))
    return overall_ok


def cmd_studio_merge(
    *,
    project: Optional[str],
    run_id: Optional[str] = None,
    out_file: Optional[str] = None,
) -> bool:
    """Merge isolated `studio compile` section MP4s chronologically via FFmpeg concat."""
    proj = _resolve_project(project)
    proj_dir = _resolve_project_dir(proj)
    runs_dir = proj_dir / "exports" / "runs"
    if not runs_dir.is_dir():
        raise FileNotFoundError(f"No runs folder in {proj_dir}")
    if run_id:
        run_root = runs_dir / run_id
    else:
        cands = sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
        if not cands:
            raise FileNotFoundError(f"No completed run inside {runs_dir}")
        run_root = cands[0]

    secs_dir = run_root / "sections"
    clips = sorted(secs_dir.glob("section_*/section_*_studio.mp4"))
    if not clips:
        raise FileNotFoundError(f"No *_studio.mp4 clips found under {secs_dir}")

    res_tag = "720p"
    try:
        pr0 = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(clips[0])],
            capture_output=True, text=True,
        )
        if pr0.returncode == 0:
            st0 = (json.loads(pr0.stdout).get("streams") or [{}])[0]
            if max(int(st0.get("width", 1280)), int(st0.get("height", 720))) > 1280:
                res_tag = "1080p"
    except Exception:
        pass
    master_mp4 = Path(out_file) if out_file else (run_root / f"{proj_dir.name}_{run_root.name}_studio_v6_master_{res_tag}.mp4")
    master_mp4.parent.mkdir(parents=True, exist_ok=True)
    concat_txt = run_root / "studio_concat_list.txt"
    concat_txt.write_text("\n".join(f"file '{c.resolve().as_posix()}'" for c in clips), encoding="utf-8")

    proc = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", "-movflags", "+faststart", str(master_mp4)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    ffp = {}
    if proc.returncode == 0 and master_mp4.is_file():
        pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "json", str(master_mp4)], capture_output=True, text=True)
        if pr.returncode == 0:
            ffp = json.loads(pr.stdout)
    ok = proc.returncode == 0 and master_mp4.is_file()
    print(json.dumps({"ok": ok, "run_id": run_root.name, "clips": len(clips), "master_mp4": str(master_mp4), "ffprobe": ffp}, indent=2, ensure_ascii=False))
    return ok


def cmd_studio_qa(
    *,
    project: Optional[str],
    section: str,
    run_id: Optional[str] = None,
    out_dir: Optional[str] = None,
) -> bool:
    """Inspect latest (or explicit) studio render cleanly without mutating reference projects."""
    proj = _resolve_project(project)
    proj_dir = _resolve_project_dir(proj)
    sec_id = _norm_sec_id(section)
    if run_id:
        target_dir = proj_dir / "exports" / "runs" / run_id / "sections" / sec_id
    else:
        target_dir = _latest_run_dir(proj, sec_id) or (proj_dir / "sections" / sec_id)

    # Read-only protection for mind_glitches_ar
    if out_dir:
        qa_dir = Path(out_dir)
    elif _is_protected(proj_dir, proj):
        qa_dir = ROOT_DIR / "cache" / "qa_readonly" / proj_dir.name / sec_id
    else:
        qa_dir = target_dir / "qa"

    ecproj = next(iter(sorted(target_dir.glob("*.ecproj"))), None)
    mp4 = next(iter(sorted(target_dir.glob("*.mp4"))), None)
    sg_p = target_dir / "scene_graph.v2.json"
    sg = json.loads(sg_p.read_text(encoding="utf-8")) if sg_p.is_file() else None
    previews = sorted((target_dir / "work" / "preview_frames").glob("*.png")) if (target_dir / "work" / "preview_frames").is_dir() else []

    rep = evaluate_creative_render(
        qa_dir=qa_dir,
        ecproj_path=ecproj,
        mp4_path=mp4,
        preview_frames=previews,
        scene_graph=sg,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return rep.get("verdict") != "FAIL"


def cmd_studio_shorts(
    *,
    action: str = "plan",
    project: Optional[str] = None,
    short_id: Optional[str] = None,
    all_shorts: bool = False,
    run_id: Optional[str] = None,
    preview_only: bool = False,
    use_gpu: bool = True,
    resolution: str = "720p",
    force: bool = False,
) -> bool:
    """Execute AION Shorts Director (`inspect` | `plan` | `compile` | `package`)."""
    from core.aion.shorts_director import (
        compile_and_render_short,
        inspect_project_creative_data,
        plan_all_shorts,
        write_shorts_package,
    )

    proj = _resolve_project(project)
    proj_dir = _resolve_project_dir(proj)

    if action == "inspect":
        is_prot = _is_protected(proj_dir, proj)
        res = inspect_project_creative_data(proj_dir, write_digest=not is_prot)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return True

    if _is_protected(proj_dir, proj):
        raise PermissionError(
            f"Refusing to write Shorts inside golden reference project '{proj}'. Copy to an isolated project first."
        )

    rid = run_id or "shorts_v6"
    if action == "plan":
        res = plan_all_shorts(proj_dir, ensure_cta=True)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return bool(res.get("ok"))

    if action == "compile":
        plan_res = plan_all_shorts(proj_dir, ensure_cta=True)
        avail = [p["short_id"] for p in plan_res.get("planned", [])]
        targets = avail if all_shorts else ([short_id] if short_id else [])
        if not targets:
            raise ValueError("Specify --short short_01 or pass --all.")
        out_list: List[Dict[str, Any]] = []
        ok_all = True
        for sid in targets:
            rep = compile_and_render_short(
                proj_dir,
                sid,
                run_id=rid,
                preview_only=preview_only,
                use_gpu=use_gpu,
                resolution=resolution,
                force=force,
            )
            ok_all = ok_all and bool(rep.get("ok"))
            out_list.append(rep)
        if all_shorts:
            pkg = write_shorts_package(proj_dir, run_id=rid, results=out_list)
            print(json.dumps({"ok": ok_all, "run_id": rid, "shorts": out_list, "package_json": str(proj_dir / "shorts_package.json"), "shorts_count": pkg["shorts_count"]}, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"ok": ok_all, "run_id": rid, "shorts": out_list}, indent=2, ensure_ascii=False))
        return ok_all

    if action == "package":
        pkg = write_shorts_package(proj_dir, run_id=rid)
        print(json.dumps({"ok": True, "package_json": str(proj_dir / "shorts_package.json"), "shorts_count": pkg["shorts_count"]}, indent=2, ensure_ascii=False))
        return True

    raise ValueError(f"Unsupported studio shorts action: {action}")


def cmd_studio_export_720p(
    *,
    inputs: List[str],
    out_dir: Optional[str] = None,
    crf: int = 18,
    force: bool = False,
) -> bool:
    """Lossless-audio Lanczos transcode to 720p (`1280x720` landscape or `720x1280` vertical 9:16)."""
    src_paths: List[Path] = []
    for raw in inputs:
        p = Path(raw)
        if any(ch in raw for ch in ("*", "?")):
            src_paths.extend(sorted(p.parent.glob(p.name)))
        elif p.is_dir():
            src_paths.extend(sorted(p.glob("*.mp4")))
        elif p.is_file():
            src_paths.append(p)
        else:
            raise FileNotFoundError(f"Input video not found: {raw}")

    if not src_paths:
        raise FileNotFoundError("No MP4 files matched for 720p export.")

    results: List[Dict[str, Any]] = []
    all_ok = True
    for src in src_paths:
        if "projects\\mind_glitches_ar\\" in str(src).lower() or "projects/mind_glitches_ar/" in str(src).lower():
            raise PermissionError(f"Refusing to write inside golden reference project: {src}")

        pr = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(src)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if pr.returncode != 0:
            raise RuntimeError(f"ffprobe failed on {src}: {pr.stderr}")
        st = (json.loads(pr.stdout).get("streams") or [{}])[0]
        sw, sh = int(st.get("width", 1920)), int(st.get("height", 1080))
        tw, th = (720, 1280) if sh > sw else (1280, 720)

        target_dir = Path(out_dir) if out_dir else (src.parent / "720p")
        target_dir.mkdir(parents=True, exist_ok=True)
        dst = target_dir / src.name
        if dst.is_file() and not force:
            results.append({"input": str(src), "output": str(dst), "skipped_existing": True, "target_res": f"{tw}x{th}"})
            continue

        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src),
                "-vf", f"scale={tw}:{th}:flags=lanczos",
                "-c:v", "libx264", "-crf", str(int(crf)), "-preset", "medium",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-c:a", "copy",
                str(dst),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        ffp: Dict[str, Any] = {}
        ok_one = proc.returncode == 0 and dst.is_file()
        if ok_one:
            pr2 = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-show_entries", "format=duration,size", "-of", "json", str(dst)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if pr2.returncode == 0:
                ffp = json.loads(pr2.stdout)
        else:
            all_ok = False
        results.append({
            "input": str(src),
            "output": str(dst),
            "ok": ok_one,
            "source_res": f"{sw}x{sh}",
            "target_res": f"{tw}x{th}",
            "ffprobe": ffp,
        })

    print(json.dumps({"ok": all_ok, "count": len(results), "exports": results}, indent=2, ensure_ascii=False))
    return all_ok


def cmd_studio_resources(
    *,
    query: str = "",
    kind: Optional[str] = None,
    project: Optional[str] = None,
    section: Optional[str] = None,
    rebuild: bool = False,
    limit: int = 12,
    as_json: bool = False,
) -> bool:
    """Index & search verified AION Studio resources via SQLite FTS5 (v4)."""
    from core.aion.resource_registry import ResourceRegistry, discover_core_resources

    reg = ResourceRegistry()
    proj_dir = _resolve_project_dir(_resolve_project(project)) if project else None
    sec_id = _norm_sec_id(section) if section else None
    if rebuild:
        reg.index_resources(discover_core_resources(), clear_existing=True)
    upserted = reg.ensure_core_indexed(proj_dir=proj_dir, section_id=sec_id)
    kinds = [kind] if kind else None
    hits = reg.search_resources(query or "lucide glow background", kinds=kinds, only_supported=True, limit=limit)
    payload = {"ok": True, "indexed_upserted": upserted, "query": query, "count": len(hits), "results": hits}
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"🔎 AION v4 Resource Registry | upserted={upserted} | hits={len(hits)}")
        for h in hits:
            print(f"  - [{h['kind']}] {h['id']} ({h['display_name']}) | caps={h['capabilities']} | score={h['score']}")
    return True

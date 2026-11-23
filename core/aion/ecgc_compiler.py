"""EffectCraft Creative Graphics Compiler — ECGC (Phase 4 of AION Creative Studio V5).

Modular 10-component compiler translating Creative Scene Graph V2 (`aion.scene_graph.v2`)
into editable EffectCraft projects (`.ecproj`), preview frames, and rendered MP4s:
  1. SceneGraphValidator
  2. CapabilityResolver
  3. AssetResolver
  4. VectorGeometryBuilder
  5. MotionTimelineCompiler
  6. TypographyCompiler
  7. VFXCompiler
  8. AudioCueCompiler
  9. EffectCraftProjectBuilder
 10. RenderValidator
"""
from __future__ import annotations

import copy
import json
import math
import re
import shutil
import subprocess
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.aion.capability_prober import (
    DEFAULT_CAPABILITIES_PATH,
    find_effectcraft_cli,
    load_capabilities_registry,
    run_capability_probes,
)
from core.aion.kinetic_typography import _measure_text_width_px, compile_kinetic_text_block, is_rtl_str
from core.config.settings import get_effectcraft_subprocess_env
from core.aion.cinematic_composition import DEPTH_PLANES_Z, apparent_scale_for_depth
from core.aion.contracts import (
    SCENE_GRAPH_V2,
    migrate_scene_graph_v1_to_v2,
    sync_scene_graph_v2_views,
    validate_scene_graph_v2,
)
from core.aion.motion_and_audio import mix_scene_graph_audio, prepare_asset_derivative
from core.aion.procedural_graphics import ProceduralGraphicsEngine, is_rtl_text

ROOT_DIR = Path(__file__).resolve().parents[2]
_AR_DIACRITICS_RE = re.compile(r"[\u0617-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")


def _hex_to_rgba_float(hex_str: str, alpha: float = 1.0) -> List[float]:
    h = (hex_str or "#0F172A").lstrip("#")
    if len(h) != 6:
        return [0.06, 0.09, 0.16, alpha]
    return [
        round(int(h[0:2], 16) / 255.0, 4),
        round(int(h[2:4], 16) / 255.0, 4),
        round(int(h[4:6], 16) / 255.0, 4),
        alpha,
    ]


def _add_fade_out(cmds: List[Dict[str, Any]], layer: str, st: float, en: float, comp_dur: float, fade_sec: float = 0.18) -> None:
    """Apply clean exit opacity dissolve before beat boundary cut (skipped on final frame or zero fade)."""
    if fade_sec <= 0.01 or en >= comp_dur - 0.05 or (en - st) <= (fade_sec + 0.35):
        return
    t0 = round(max(st + 0.25, en - fade_sec), 3)
    cmds.append({"command": "prop.addKey", "params": {"layer": layer, "path": "transform/opacity", "time": t0, "timeBase": "comp", "value": 100.0}})
    cmds.append({"command": "prop.addKey", "params": {"layer": layer, "path": "transform/opacity", "time": round(en, 3), "timeBase": "comp", "value": 0.0}})


@dataclass
class CompileContext:
    """Shared compilation state threaded across the 10 ECGC pipeline components."""

    scene_graph: Dict[str, Any]
    section_dir: Path
    work_dir: Path
    comp_name: str
    width: int
    height: int
    fps: int
    duration: float
    capabilities: Dict[str, Any] = field(default_factory=dict)
    resolved_capabilities: Dict[str, Any] = field(default_factory=dict)
    fallbacks_applied: List[Dict[str, str]] = field(default_factory=list)
    quality_impacts: List[str] = field(default_factory=list)
    resolved_assets: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    svg_markups: Dict[str, str] = field(default_factory=dict)
    commands: List[Dict[str, Any]] = field(default_factory=list)
    three_d_layers: List[str] = field(default_factory=list)
    ease_keys: List[Dict[str, Any]] = field(default_factory=list)
    validation_issues: List[str] = field(default_factory=list)
    mixed_audio_path: Optional[Path] = None
    fx_counter: Dict[str, int] = field(default_factory=dict)
    imported_files: Dict[str, str] = field(default_factory=dict)


# 1. Scene Graph Validator
class SceneGraphValidator:
    """Validates and normalizes V1/V2 scene graphs before compilation."""

    def validate(self, raw_sg: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        sg = copy.deepcopy(raw_sg)
        if sg.get("schema_version") != SCENE_GRAPH_V2:
            sg = migrate_scene_graph_v1_to_v2(sg)
        else:
            sync_scene_graph_v2_views(sg)
        ok, issues = validate_scene_graph_v2(sg, auto_fix=True)
        if not ok:
            raise ValueError(f"Scene Graph V2 validation failed: {issues}")
        return sg, issues


# 2. Capability Resolver
class CapabilityResolver:
    """Checks required features against empirical `config/effectcraft_capabilities.json`."""

    def __init__(self, cap_path: Path = DEFAULT_CAPABILITIES_PATH):
        self.cap_path = Path(cap_path)

    def resolve(self, ctx: CompileContext) -> None:
        reg = load_capabilities_registry(self.cap_path)
        caps = reg.get("capabilities", {})
        if not caps:
            reg = run_capability_probes(out_json_path=self.cap_path, use_gpu=False)
            caps = reg.get("capabilities", {})
        ctx.capabilities = caps

        reqs = list(ctx.scene_graph.get("tool_requirements", []))
        for req in reqs:
            entry = caps.get(req)
            if not entry:
                ctx.resolved_capabilities[req] = "UNKNOWN"
                ctx.quality_impacts.append(f"Capability '{req}' absent from registry.")
                continue
            status = entry.get("status", "UNKNOWN")
            ctx.resolved_capabilities[req] = status
            if status in ("BROKEN", "UNAVAILABLE"):
                fb = entry.get("fallback", "manual raster fallback")
                ctx.fallbacks_applied.append({"capability": req, "status": status, "fallback": fb})
                ctx.quality_impacts.append(f"Downgraded '{req}' ({status}) -> fallback: {fb}")
            elif status == "PARTIAL" and req == "arabic_rtl_text":
                # Enforce safe word-mode or backdrop card rather than per-char splits
                ctx.fallbacks_applied.append({
                    "capability": req,
                    "status": "PARTIAL",
                    "fallback": "Enforce word-mode RangeSelector (basedOn=2) + RTL alignment to protect Arabic ligatures",
                })


# 3. Asset Resolver
class AssetResolver:
    """Resolves section PNG/raster files and `asset_factory` / procedural SVG icons."""

    def resolve(self, ctx: CompileContext) -> None:
        derived_dir = ctx.work_dir / "derived_ecgc"
        derived_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = ctx.section_dir / "assets"
        proc = ProceduralGraphicsEngine(ctx.width, ctx.height)

        for ref in ctx.scene_graph.get("asset_references", []):
            aid = str(ref.get("id", "asset"))
            raw_path = ref.get("path")
            cand: Optional[Path] = None
            if raw_path:
                rp = Path(str(raw_path))
                if rp.is_file():
                    cand = rp
                elif (assets_dir / rp.name).is_file():
                    cand = assets_dir / rp.name
                elif (ctx.section_dir / raw_path).is_file():
                    cand = ctx.section_dir / raw_path
            if cand is None:
                if ref.get("svg"):
                    ctx.svg_markups[aid] = str(ref["svg"])
                    ctx.resolved_assets[aid] = {"kind": "svg", "svg_key": aid, "ref": ref}
                    continue
                # Try procedural/brand vector icon match, then local ISC Lucide SVG library
                icon_key = str(ref.get("icon") or aid).lower()
                lucide_stem = icon_key.replace("_", "-")
                p_lucide = ROOT_DIR / "assets" / "icons_lucide" / f"{lucide_stem}.svg"
                if p_lucide.is_file():
                    raw_svg = p_lucide.read_text(encoding="utf-8")
                    stroke_hex = str((ref.get("icon_anim") or {}).get("color") or ref.get("icon_color") or "#38BDF8")
                    stroke_w = float(ref.get("icon_stroke_width", 2.3))
                    ctx.svg_markups[aid] = (
                        raw_svg.replace('stroke="currentColor"', f'stroke="{stroke_hex}"')
                        .replace('stroke-width="2"', f'stroke-width="{stroke_w:.1f}"')
                    )
                    ctx.resolved_assets[aid] = {"kind": "svg", "svg_key": lucide_stem, "ref": ref}
                    continue
                svg = proc.get_svg_icon_markup(icon_key)
                if svg:
                    ctx.svg_markups[aid] = svg
                    ctx.resolved_assets[aid] = {"kind": "svg", "svg_key": icon_key, "ref": ref}
                    continue
                # Try asset_factory file by stem
                for sub in ("icons", "props", "fx"):
                    p_svg = ROOT_DIR / "creative_v3" / "asset_factory" / sub / f"{icon_key}.svg"
                    if p_svg.is_file():
                        ctx.svg_markups[aid] = p_svg.read_text(encoding="utf-8")
                        ctx.resolved_assets[aid] = {"kind": "svg", "svg_key": icon_key, "ref": ref}
                        break
                if aid not in ctx.resolved_assets:
                    ctx.quality_impacts.append(f"Asset '{aid}' missing on disk; fallback shape placeholder used.")
                continue

            # Deduplicate derivative generation by source stem + preprocessing style so reused assets share media items
            prep_list = ref.get("preprocess") or []
            prep_tag = f"{'_'.join(prep_list)}_{ref.get('card_style', 'warm')}" if prep_list else "raw"
            prep_cfg = {
                "id": cand.stem,
                "uid": f"{cand.stem}_{prep_tag}",
                "path": cand.name,
                **{k: ref[k] for k in ("preprocess", "card_style", "fade_frac") if k in ref},
            }
            prep_path, pw, ph = prepare_asset_derivative(prep_cfg, cand.parent, derived_dir)
            ctx.resolved_assets[aid] = {
                "kind": "raster",
                "path": prep_path.resolve().as_posix(),
                "width": pw,
                "height": ph,
                "ref": ref,
            }

        # Pre-resolve icons inside procedural_graphics
        for pg in ctx.scene_graph.get("procedural_graphics", []):
            icon_key = pg.get("icon")
            if icon_key and icon_key not in ctx.svg_markups:
                svg = proc.get_svg_icon_markup(str(icon_key))
                if svg:
                    ctx.svg_markups[str(icon_key)] = svg


# 4. Vector Geometry Builder
class VectorGeometryBuilder:
    """Emits native Shape layers, Bezier Trim paths, Arrowheads, Repeaters, Masks, Mattes, and SVG pastes."""

    def build_stage_and_vectors(self, ctx: CompileContext) -> None:
        comp = ctx.scene_graph.get("composition", {})
        palette = comp.get("palette") or {}
        bg_hex = str(comp.get("bg_color") or palette.get("bg") or "#0F172A")
        surface_hex = str(palette.get("surface") or "#1E293B")
        accent_hex = str(palette.get("accent") or "#FFD400")
        primary_hex = str(palette.get("primary") or "#38BDF8")

        # Atmospheric non-3D background canvas + animated 4-color gradient moods + Vignette
        bg_tl = ctx.scene_graph.get("background_timeline") or []
        ctx.commands.append({"command": "layer.newSolid", "params": {"name": "BG_Stage", "color": bg_hex, "width": ctx.width, "height": ctx.height}})
        ctx.commands.append({"command": "effect.apply", "params": {"effect": "4-Color Gradient", "layers": ["BG_Stage"]}})
        ctx.commands.append({"command": "effect.apply", "params": {"effect": "ec.stylize.ccvignette", "layers": ["BG_Stage"]}})
        if bg_tl:
            for bm in bg_tl:
                bt = round(max(0.0, float(bm.get("time", 0.0))), 3)
                for idx_c, kc in enumerate(("c1", "c2", "c3", "c4"), start=1):
                    val_c = bm.get(kc, bg_hex if idx_c % 2 else surface_hex)
                    ctx.commands.append({
                        "command": "prop.addKey",
                        "params": {"layer": "BG_Stage", "path": f"effects/#1/positionsColors/color{idx_c}", "time": bt, "timeBase": "comp", "value": _hex_to_rgba_float(str(val_c))},
                    })
                if "vignette" in bm:
                    ctx.commands.append({
                        "command": "prop.addKey",
                        "params": {"layer": "BG_Stage", "path": "effects/#2/amount", "time": bt, "timeBase": "comp", "value": float(bm["vignette"])},
                    })
        else:
            ctx.commands.append({"command": "prop.set", "params": {"layer": "BG_Stage", "path": "effects/#1/positionsColors/color1", "value": _hex_to_rgba_float(bg_hex)}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": "BG_Stage", "path": "effects/#1/positionsColors/color2", "value": _hex_to_rgba_float(surface_hex)}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": "BG_Stage", "path": "effects/#1/positionsColors/color3", "value": _hex_to_rgba_float(bg_hex)}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": "BG_Stage", "path": "effects/#1/positionsColors/color4", "value": _hex_to_rgba_float(surface_hex)}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": "BG_Stage", "path": "effects/#2/amount", "value": 18.0}})

        # Use opaque shadow plane ONLY when static dark single-scene 3D lighting is enabled without multi-mood background_timeline
        lighting = ctx.scene_graph.get("lighting") or {}
        if not bg_tl and (comp.get("enable_3d_stage") or lighting.get("enabled")):
            ctx.commands.append({
                "command": "layer.newSolid",
                "params": {"name": "Stage_ShadowPlane", "color": surface_hex, "width": ctx.width, "height": ctx.height},
            })
            ctx.commands.append({"command": "prop.set", "params": {"layer": "Stage_ShadowPlane", "path": "transform/position", "value": [ctx.width / 2.0, ctx.height / 2.0, 260.0]}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": "Stage_ShadowPlane", "path": "transform/scale", "value": [146.0, 146.0, 100.0]}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": "Stage_ShadowPlane", "path": "materialOptions/acceptsShadows", "value": 1}})
            ctx.three_d_layers.append("Stage_ShadowPlane")

        # Subtle 3D architectural floor line (omitted when cinema_stage.hide_floor_line is enabled)
        cinema_stage = ctx.scene_graph.get("cinema_stage") or {}
        hide_floor_line = bool(cinema_stage.get("hide_floor_line", False))
        stage_ground = ctx.scene_graph.get("stage_ground") or {}
        if stage_ground.get("enabled") and not hide_floor_line:
            hy = float(stage_ground.get("horizon_y", ctx.height * 0.635))
            ctx.commands.append({
                "command": "layer.newShape",
                "params": {
                    "kind": "rect",
                    "name": "Stage_HorizonRule",
                    "size": [3400.0, 2.0],
                    "position": [ctx.width * 0.5, hy],
                    "fill": "#9A8F7E",
                    "fillOpacity": 42.0,
                    "stroke": False,
                },
            })
            ctx.commands.append({"command": "layer.timing", "params": {"layers": ["Stage_HorizonRule"], "in": 0.0, "out": ctx.duration}})
            ctx.three_d_layers.append("Stage_HorizonRule")
        elif comp.get("enable_3d_stage") and bg_tl and not hide_floor_line:
            ctx.commands.append({
                "command": "layer.newShape",
                "params": {
                    "kind": "rect",
                    "name": "Stage_Floor_Line",
                    "size": [3400.0, 2.0],
                    "position": [ctx.width * 0.5, round(ctx.height * 0.804, 1)],
                    "fill": "#9A8F7E",
                    "fillOpacity": 38.0,
                    "stroke": False,
                },
            })
            ctx.commands.append({"command": "layer.timing", "params": {"layers": ["Stage_Floor_Line"], "in": 0.0, "out": ctx.duration}})
            ctx.three_d_layers.append("Stage_Floor_Line")

        # V7 Living Cinema Stage (GPU-fast orbiting 4-Color Gradient + subtle caustics + texture + astrolabe arcs + spotlight)
        if cinema_stage:
            self._emit_cinema_stage_layers(ctx, cinema_stage)

        # Optional per-beat Illustrated Historical/Environmental Backgrounds + Dark Legibility Scrim
        bg_layers = ctx.scene_graph.get("background_layers") or []
        if bg_layers:
            imported_bgs = ctx.imported_files
            for bidx, bg_item in enumerate(bg_layers):
                bp = Path(str(bg_item.get("path", "")))
                if not bp.is_file():
                    continue
                bposix = bp.resolve().as_posix()
                if bposix not in imported_bgs:
                    ctx.commands.append({"command": "file.import", "params": {"paths": [bposix], "addToComp": False}})
                    imported_bgs[bposix] = bp.name
                try:
                    from PIL import Image as _PILImage
                    with _PILImage.open(bp) as im_b:
                        bw, bh = im_b.size
                except Exception:
                    bw, bh = ctx.width, ctx.height
                cover_sc = round(max(ctx.width / max(1, bw), ctx.height / max(1, bh)) * 101.0, 2)
                st_b = max(0.0, float(bg_item.get("in", 0.0)))
                en_b = min(ctx.duration, float(bg_item.get("out", ctx.duration)))
                if en_b <= st_b:
                    continue
                op_peak = float(bg_item.get("opacity", 94.0))
                bname = f"BG_Scenery_{bidx}"
                # Extend layer out past crossfade only when crossfade is enabled
                fade_bg = float(bg_item.get("fade_sec", 0.0 if str((ctx.scene_graph.get("cinema_stage") or {}).get("video_format", "")) == "workflow_montage" else 0.35))
                has_next = (bidx + 1 < len(bg_layers)) and (float(bg_layers[bidx + 1].get("in", ctx.duration)) <= en_b + 0.05)
                out_eff = round(min(ctx.duration, en_b + fade_bg + 0.03), 3) if (has_next and fade_bg > 0.01) else en_b
                pan_x = float(bg_item.get("pan_x", 0.0))
                pan_y = float(bg_item.get("pan_y", 0.0))
                bg_z = float(bg_item.get("z", 0.0))
                bg_3d = bool(bg_item.get("three_d", False))
                cx_b, cy_b = ctx.width * 0.5, ctx.height * 0.5
                ctx.commands.append({
                    "command": "layer.addItem",
                    "params": {
                        "item": imported_bgs[bposix],
                        "in": st_b,
                        "out": out_eff,
                        "position": [cx_b, cy_b],
                        "anchor": [bw * 0.5, bh * 0.5],
                    },
                })
                ctx.commands.append({"command": "layer.settings", "params": {"layer": "#1", "name": bname}})
                if bg_3d:
                    ctx.commands.append({"command": "prop.set", "params": {"layer": bname, "path": "transform/position", "value": [cx_b, cy_b, bg_z]}})
                    ctx.three_d_layers.append(bname)
                if abs(pan_x) > 0.5 or abs(pan_y) > 0.5:
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": bname, "path": "transform/position", "time": st_b, "timeBase": "comp", "value": [round(cx_b - pan_x * 0.5, 1), round(cy_b - pan_y * 0.5, 1), bg_z] if bg_3d else [round(cx_b - pan_x * 0.5, 1), round(cy_b - pan_y * 0.5, 1)]}})
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": bname, "path": "transform/position", "time": out_eff, "timeBase": "comp", "value": [round(cx_b + pan_x * 0.5, 1), round(cy_b + pan_y * 0.5, 1), bg_z] if bg_3d else [round(cx_b + pan_x * 0.5, 1), round(cy_b + pan_y * 0.5, 1)]}})
                if bg_item.get("ken_burns", True):
                    kb_end = float(bg_item.get("ken_burns_scale", 1.045))
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": bname, "path": "transform/scale", "time": st_b, "timeBase": "comp", "value": [cover_sc, cover_sc, 100.0]}})
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": bname, "path": "transform/scale", "time": out_eff, "timeBase": "comp", "value": [round(cover_sc * kb_end, 2), round(cover_sc * kb_end, 2), 100.0]}})
                else:
                    ctx.commands.append({"command": "prop.set", "params": {"layer": bname, "path": "transform/scale", "value": [cover_sc, cover_sc, 100.0]}})
                if fade_bg > 0.01:
                    t_in_e = round(min(out_eff - 0.05, st_b + fade_bg), 3)
                    if st_b > 0.02:
                        ctx.commands.append({"command": "prop.addKey", "params": {"layer": bname, "path": "transform/opacity", "time": st_b, "timeBase": "comp", "value": 0.0}})
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": bname, "path": "transform/opacity", "time": t_in_e if st_b > 0.02 else st_b, "timeBase": "comp", "value": op_peak}})
                    if not has_next and en_b < ctx.duration - 0.02:
                        t_out_s = round(max(t_in_e + 0.05, en_b - fade_bg), 3)
                        if t_out_s > t_in_e:
                            ctx.commands.append({"command": "prop.addKey", "params": {"layer": bname, "path": "transform/opacity", "time": t_out_s, "timeBase": "comp", "value": op_peak}})
                            ctx.commands.append({"command": "prop.addKey", "params": {"layer": bname, "path": "transform/opacity", "time": en_b, "timeBase": "comp", "value": 0.0}})
                else:
                    ctx.commands.append({"command": "prop.set", "params": {"layer": bname, "path": "transform/opacity", "value": op_peak}})
            scrim_op = float((ctx.scene_graph.get("cinema_stage") or {}).get("bg_scrim_opacity", 0.0))
            if scrim_op > 0.5:
                ctx.commands.append({"command": "layer.newSolid", "params": {"name": "BG_DarkScrim", "color": "#060A12", "width": ctx.width, "height": ctx.height}})
                ctx.commands.append({"command": "layer.timing", "params": {"layers": ["BG_DarkScrim"], "in": 0.0, "out": ctx.duration}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": "BG_DarkScrim", "path": "transform/opacity", "value": scrim_op}})

        # Emit ground contact shadows BELOW assets before assets render
        proc_items = ctx.scene_graph.get("procedural_graphics", [])
        for pg in proc_items:
            if str(pg.get("kind", "")) == "ground_shadow":
                self._emit_procedural_item(ctx, pg, palette, primary_hex, accent_hex)

        # Raster & SVG asset imports (unique media paths imported once with addToComp=False)
        imported_files = ctx.imported_files
        for aid, resolved in ctx.resolved_assets.items():
            ref = resolved["ref"]
            st = max(0.0, float(ref.get("in", 0.0)))
            en = min(ctx.duration, float(ref.get("out", ctx.duration)))
            if en <= st:
                en = min(ctx.duration, st + 1.0)
            pos = ref.get("position", ref.get("pos", [ctx.width * 0.5, ctx.height * 0.5]))
            z = float(ref.get("z", 0.0))
            pw = int(resolved.get("width", 400))
            ph = int(resolved.get("height", 400))
            vis_bbox = (0, 0, pw, ph)
            if resolved["kind"] == "raster" and ref.get("anchor_mode") == "visible_bounds":
                try:
                    from PIL import Image as _PILVis
                    with _PILVis.open(resolved["path"]) as _imv:
                        pw, ph = _imv.size
                        _bb = _imv.convert("RGBA").getchannel("A").getbbox()
                        if _bb:
                            vis_bbox = _bb
                except Exception:
                    vis_bbox = (0, 0, pw, ph)
            vis_w = max(1, vis_bbox[2] - vis_bbox[0])
            vis_h = max(1, vis_bbox[3] - vis_bbox[1])

            if resolved["kind"] == "raster" and ref.get("target_visible_height_px"):
                scale_h = (float(ref["target_visible_height_px"]) / vis_h) * 100.0
                if ref.get("max_w"):
                    scale_w = (float(ref["max_w"]) / vis_w) * 100.0
                    base_scale = min(220.0, scale_h, scale_w)
                else:
                    base_scale = min(220.0, scale_h)
            elif resolved["kind"] == "raster" and ref.get("target_max_side_px"):
                base_scale = min(220.0, (float(ref["target_max_side_px"]) / max(vis_w, vis_h)) * 100.0)
            elif resolved["kind"] == "raster" and ref.get("target_h"):
                scale_h = (float(ref["target_h"]) / max(1, ph)) * 100.0
                if ref.get("max_w"):
                    scale_w = (float(ref["max_w"]) / max(1, pw)) * 100.0
                    base_scale = min(220.0, scale_h, scale_w)
                else:
                    base_scale = min(220.0, scale_h)
            else:
                base_scale = float(ref.get("scale", 95.0))
            is_3d = bool(ref.get("three_d", True))

            if resolved["kind"] == "raster":
                fpath = resolved["path"]
                if fpath not in imported_files:
                    ctx.commands.append({"command": "file.import", "params": {"paths": [fpath], "addToComp": False}})
                    imported_files[fpath] = Path(fpath).name
                lname = f"Asset_{aid}"
                if ref.get("anchor_mode") == "visible_bounds":
                    anchor = (
                        [(vis_bbox[0] + vis_bbox[2]) * 0.5, float(vis_bbox[3])]
                        if ref.get("grounded", False)
                        else [(vis_bbox[0] + vis_bbox[2]) * 0.5, (vis_bbox[1] + vis_bbox[3]) * 0.5]
                    )
                else:
                    anchor = [pw / 2.0, float(ph)] if ref.get("grounded", False) else [pw / 2.0, ph / 2.0]
                ctx.commands.append({
                    "command": "layer.addItem",
                    "params": {"item": imported_files[fpath], "in": st, "out": en, "position": [float(pos[0]), float(pos[1])], "anchor": anchor},
                })
                ctx.commands.append({"command": "layer.settings", "params": {"layer": "#1", "name": lname}})
            else:
                lname = f"SvgAsset_{aid}"
                svg_markup = ctx.svg_markups[aid]
                ctx.commands.append({"command": "edit.pasteSvg", "params": {"svg": svg_markup, "name": lname, "comp": ctx.comp_name}})
                ctx.commands.append({"command": "layer.timing", "params": {"layers": [lname], "in": st, "out": en}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/position", "value": [float(pos[0]), float(pos[1]), 0.0]}})
                base_scale = float(ref.get("scale", 220.0))

            if is_3d:
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/position", "value": [float(pos[0]), float(pos[1]), z]}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "materialOptions/castsShadows", "value": 1}})
                ctx.three_d_layers.append(lname)

            # Scale adjusted for 3D depth plane
            comp_scale = round(base_scale * (apparent_scale_for_depth(z) / 100.0) if is_3d and z != 0 else base_scale, 2)

            # Optional reveal mask wipe on hero image/SVG
            entrance = str(ref.get("entrance") or ("mask_reveal" if ref.get("mask_reveal") else "pop_settle"))
            ent_dur = min(max(0.18, float(ref.get("entrance_dur", 0.36))), max(0.2, (en - st) * 0.55))
            if ref.get("mask_reveal") or entrance == "mask_reveal":
                mw = max(320, int(resolved.get("width", 420)))
                mh = max(240, int(resolved.get("height", 360)))
                ctx.commands.append({"command": "mask.new", "params": {"layer": lname, "vertices": [[0, 0], [mw, 0], [mw, mh], [0, mh]], "closed": True}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "masks/mask/feather", "value": [28, 28]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "masks/mask/expansion", "time": st, "timeBase": "comp", "value": -mw * 0.6}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "masks/mask/expansion", "time": round(min(en, st + 0.60), 3), "timeBase": "comp", "value": 40.0}})

            # Meaning-driven entrance animation vocabulary (never forced uniform pop_settle!)
            if entrance == "slide_right":
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/scale", "value": [comp_scale, comp_scale, 100.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": st, "timeBase": "comp", "value": [float(pos[0]) + 140.0, float(pos[1]), z]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": round(st + ent_dur, 3), "timeBase": "comp", "value": [float(pos[0]), float(pos[1]), z]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": round(min(en, st + ent_dur * 0.72), 3), "timeBase": "comp", "value": 100.0}})
                ctx.ease_keys.extend([
                    {"layer": lname, "path": "transform/position", "time": st},
                    {"layer": lname, "path": "transform/position", "time": round(st + ent_dur, 3)},
                ])
            elif entrance == "slide_left":
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/scale", "value": [comp_scale, comp_scale, 100.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": st, "timeBase": "comp", "value": [float(pos[0]) - 140.0, float(pos[1]), z]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": round(st + ent_dur, 3), "timeBase": "comp", "value": [float(pos[0]), float(pos[1]), z]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": round(min(en, st + ent_dur * 0.72), 3), "timeBase": "comp", "value": 100.0}})
                ctx.ease_keys.extend([
                    {"layer": lname, "path": "transform/position", "time": st},
                    {"layer": lname, "path": "transform/position", "time": round(st + ent_dur, 3)},
                ])
            elif entrance == "slide_down":
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/scale", "value": [comp_scale, comp_scale, 100.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": st, "timeBase": "comp", "value": [float(pos[0]), float(pos[1]) - 90.0, z]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": round(st + ent_dur, 3), "timeBase": "comp", "value": [float(pos[0]), float(pos[1]), z]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": round(min(en, st + ent_dur * 0.72), 3), "timeBase": "comp", "value": 100.0}})
                ctx.ease_keys.extend([
                    {"layer": lname, "path": "transform/position", "time": st},
                    {"layer": lname, "path": "transform/position", "time": round(st + ent_dur, 3)},
                ])
            elif entrance == "rise_up":
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/scale", "value": [comp_scale, comp_scale, 100.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": st, "timeBase": "comp", "value": [float(pos[0]), float(pos[1]) + 88.0, z]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": round(st + ent_dur, 3), "timeBase": "comp", "value": [float(pos[0]), float(pos[1]), z]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": round(min(en, st + ent_dur * 0.75), 3), "timeBase": "comp", "value": 100.0}})
                ctx.ease_keys.extend([
                    {"layer": lname, "path": "transform/position", "time": st},
                    {"layer": lname, "path": "transform/position", "time": round(st + ent_dur, 3)},
                ])
            elif entrance == "zoom_drift":
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [round(comp_scale * 0.82, 2), round(comp_scale * 0.82, 2), 100.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": round(st + ent_dur, 3), "timeBase": "comp", "value": [comp_scale, comp_scale, 100.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": round(min(en, st + ent_dur * 0.72), 3), "timeBase": "comp", "value": 100.0}})
                ctx.ease_keys.extend([
                    {"layer": lname, "path": "transform/scale", "time": st},
                    {"layer": lname, "path": "transform/scale", "time": round(st + ent_dur, 3)},
                ])
            elif entrance in ("cut", "direct"):
                init_op = float(ref.get("initial_opacity", 100.0))
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/scale", "value": [comp_scale, comp_scale, 100.0]}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/opacity", "value": init_op}})
            elif entrance in ("soft_fade", "fade_in", "mask_reveal"):
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/scale", "value": [comp_scale, comp_scale, 100.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": round(st + ent_dur, 3), "timeBase": "comp", "value": 100.0}})
            else:  # pop_settle
                t_over = round(st + ent_dur * 0.68, 3)
                t_in_end = round(st + ent_dur, 3)
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [round(comp_scale * 0.25, 2), round(comp_scale * 0.25, 2), 100.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": t_over, "timeBase": "comp", "value": [round(comp_scale * 1.07, 2), round(comp_scale * 1.07, 2), 100.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": t_in_end, "timeBase": "comp", "value": [comp_scale, comp_scale, 100.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": round(min(en, st + 0.16), 3), "timeBase": "comp", "value": 100.0}})
                ctx.ease_keys.extend([
                    {"layer": lname, "path": "transform/scale", "time": st},
                    {"layer": lname, "path": "transform/scale", "time": t_in_end},
                ])

            # Compile purposeful mid-hold keyframes (slide-aside, tension push, emphasis pulse)
            for kf in ref.get("keyframes", []):
                kt = float(kf["time"])
                if "pos" in kf:
                    kp = kf["pos"]
                    kz = float(kf.get("z", kp[2] if len(kp) > 2 else z))
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": kt, "timeBase": "comp", "value": [float(kp[0]), float(kp[1]), kz]}})
                    ctx.ease_keys.append({"layer": lname, "path": "transform/position", "time": kt})
                if "scale_mult" in kf:
                    sm = round(comp_scale * float(kf["scale_mult"]), 2)
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": kt, "timeBase": "comp", "value": [sm, sm, 100.0]}})
                    ctx.ease_keys.append({"layer": lname, "path": "transform/scale", "time": kt})
                if "opacity" in kf:
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": kt, "timeBase": "comp", "value": float(kf["opacity"])}})
                if "rotation" in kf:
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/rotation", "time": kt, "timeBase": "comp", "value": float(kf["rotation"])}})
                    ctx.ease_keys.append({"layer": lname, "path": "transform/rotation", "time": kt})

            fade_out_sec = float(ref.get("fade_out", 0.22))
            _add_fade_out(ctx.commands, lname, st, en, ctx.duration, fade_sec=fade_out_sec)

        # Procedural Vector Graphics & Grounded UI Medallions (ground_shadow already emitted under assets)
        for pg in proc_items:
            if str(pg.get("kind", "")) != "ground_shadow":
                self._emit_procedural_item(ctx, pg, palette, primary_hex, accent_hex)

        # V7 Glowing Element-to-Element Arrows (opt-in via cinema_stage.glow_arrows)
        if cinema_stage.get("glow_arrows"):
            for pg in proc_items:
                if str(pg.get("kind", "")) in ("bezier_connector", "bezier_arrow"):
                    aname = f"Path_{pg['id']}"
                    ctx.commands.extend([
                        {"command": "effect.apply", "params": {"layers": [aname], "effect": "ec.stylize.glow"}},
                        {"command": "prop.set", "params": {"layer": aname, "path": "effects/#1/intensity", "value": 0.62}},
                        {"command": "prop.set", "params": {"layer": aname, "path": "effects/#1/radius", "value": 15.0}},
                    ])

        # V7 Animated Lucide SVG Icon Rigs (opt-in via asset.icon_anim)
        for aid, resolved in ctx.resolved_assets.items():
            if resolved["kind"] == "svg" and resolved["ref"].get("icon_anim"):
                self._inject_animated_lucide_rig(ctx, aid, resolved["ref"], resolved["ref"]["icon_anim"])

    def _emit_cinema_stage_layers(self, ctx: CompileContext, cinema: Dict[str, Any]) -> None:
        """Emit GPU-fast living 4-Color Gradient sweeping mesh orbits + calibrated bg_opacity + subtle caustics/texture/spotlight."""
        dur = ctx.duration
        w, h = float(ctx.width), float(ctx.height)

        # Reduced-glare background opacity over deep obsidian comp floor (lets artwork & live gradient waves pop!)
        bg_opacity = float(cinema.get("bg_opacity", 64.0))
        ctx.commands.append({"command": "prop.set", "params": {"layer": "BG_Stage", "path": "transform/opacity", "value": bg_opacity}})

        if cinema.get("living_gradient", True):
            # Blend ~108 keeps moving color lobes distinctly visible yet silky smooth
            ctx.commands.append({"command": "prop.set", "params": {"layer": "BG_Stage", "path": "effects/#1/blend", "value": float(cinema.get("gradient_blend", 108.0))}})
            step_sec = float(cinema.get("gradient_step_sec", 1.8))
            n_steps = max(3, int(round(dur / max(0.8, step_sec))))
            cycles = float(cinema.get("gradient_cycles", 3.4))
            for s in range(n_steps + 1):
                t_val = round(min(dur, (s / float(n_steps)) * dur), 3)
                ang = (t_val / max(1.0, dur)) * math.tau * cycles
                # Wide sweeping figure-8 / orbital trajectories so gradient color pools visibly glide across the canvas!
                p1 = [round(w * (0.28 + 0.30 * math.sin(ang)), 1),             round(h * (0.26 + 0.24 * math.cos(ang * 0.85)), 1)]
                p2 = [round(w * (0.72 + 0.28 * math.cos(ang * 0.92 + 0.9)), 1), round(h * (0.28 + 0.26 * math.sin(ang * 1.15)), 1)]
                p3 = [round(w * (0.30 + 0.30 * math.cos(ang * 0.78 + 1.8)), 1), round(h * (0.74 + 0.24 * math.sin(ang * 0.95)), 1)]
                p4 = [round(w * (0.70 + 0.28 * math.sin(ang * 0.88 + 2.6)), 1), round(h * (0.72 + 0.25 * math.cos(ang * 1.08)), 1)]
                for pidx, pt in enumerate((p1, p2, p3, p4), start=1):
                    ctx.commands.append({
                        "command": "prop.addKey",
                        "params": {"layer": "BG_Stage", "path": f"effects/#1/positionsColors/point{pidx}", "time": t_val, "timeBase": "comp", "value": pt},
                    })

        # Subtle horizontal living caustic shimmer (`Screen`, low opacity so it never muddies the live gradient)
        ctx.commands.extend([
            {"command": "layer.newSolid", "params": {"name": "BG_Caustics", "color": "#000000", "width": int(w), "height": int(h)}},
            {"command": "layer.timing", "params": {"layers": ["BG_Caustics"], "in": 0.0, "out": dur}},
            {"command": "effect.apply", "params": {"layers": ["BG_Caustics"], "effect": "Fractal Noise"}},
            {"command": "prop.set", "params": {"layer": "BG_Caustics", "path": "effects/#1/contrast", "value": 64.0}},
            {"command": "prop.set", "params": {"layer": "BG_Caustics", "path": "effects/#1/brightness", "value": -36.0}},
            {"command": "prop.set", "params": {"layer": "BG_Caustics", "path": "effects/#1/transform/uniformScaling", "value": False}},
            {"command": "prop.set", "params": {"layer": "BG_Caustics", "path": "effects/#1/transform/scaleWidth", "value": 480.0}},
            {"command": "prop.set", "params": {"layer": "BG_Caustics", "path": "effects/#1/transform/scaleHeight", "value": 150.0}},
            {"command": "prop.set", "params": {"layer": "BG_Caustics", "path": "effects/#1/opacity", "value": 100.0}},
            {"command": "prop.addKey", "params": {"layer": "BG_Caustics", "path": "effects/#1/evolution", "time": 0.0, "timeBase": "comp", "value": 0.0}},
            {"command": "prop.addKey", "params": {"layer": "BG_Caustics", "path": "effects/#1/evolution", "time": dur, "timeBase": "comp", "value": 240.0}},
            {"command": "layer.setBlendMode", "params": {"layers": ["BG_Caustics"], "mode": "Screen"}},
        ])
        caustics_kfs = cinema.get("caustics_opacity_keyframes")
        if caustics_kfs:
            for ct, cop in caustics_kfs:
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": "BG_Caustics", "path": "transform/opacity", "time": round(float(ct), 3), "timeBase": "comp", "value": float(cop)}})
        else:
            ctx.commands.append({"command": "prop.set", "params": {"layer": "BG_Caustics", "path": "transform/opacity", "value": float(cinema.get("mist_opacity", 10.0))}})

        # Optional overscanned surface grain texture (`Overlay`, 225% scale so ZERO edge lines ever show)
        tex_path = str(cinema.get("texture_path") or "").strip()
        if tex_path and Path(tex_path).is_file():
            tex_posix = Path(tex_path).resolve().as_posix()
            if tex_posix not in ctx.imported_files:
                ctx.commands.append({"command": "file.import", "params": {"paths": [tex_posix], "addToComp": False}})
                ctx.imported_files[tex_posix] = Path(tex_path).name
            ctx.commands.extend([
                {"command": "layer.addItem", "params": {"item": ctx.imported_files[tex_posix], "position": [w * 0.5, h * 0.5], "in": 0.0, "out": dur}},
                {"command": "layer.settings", "params": {"layer": "#1", "name": "BG_Texture"}},
                {"command": "layer.setBlendMode", "params": {"layers": ["BG_Texture"], "mode": "Overlay"}},
                {"command": "prop.set", "params": {"layer": "BG_Texture", "path": "transform/scale", "value": [225.0, 225.0, 100.0]}},
                {"command": "prop.set", "params": {"layer": "BG_Texture", "path": "transform/opacity", "value": float(cinema.get("texture_opacity", 7.0))}},
            ])

        # Delicate Trim-Paths Orbital Astrolabe Arcs (NO square grid!)
        ring_color = str(cinema.get("ring_color", "#F59E0B"))
        ring_color_2 = str(cinema.get("ring_color_2", "#38BDF8"))
        base_d = min(w, h)
        ctx.commands.extend([
            {"command": "layer.newShape", "params": {"kind": "ellipse", "name": "BG_AstroRing_Outer", "size": [round(base_d * 1.09, 1), round(base_d * 1.09, 1)], "position": [w * 0.5, h * 0.54], "fill": ring_color, "fillOpacity": 0.0, "stroke": ring_color, "strokeWidth": 1.4}},
            {"command": "layer.timing", "params": {"layers": ["BG_AstroRing_Outer"], "in": 0.0, "out": dur}},
            {"command": "layer.addShapeItem", "params": {"layer": "BG_AstroRing_Outer", "kind": "trim"}},
            {"command": "prop.set", "params": {"layer": "BG_AstroRing_Outer", "path": "contents/trim/start", "value": 8.0}},
            {"command": "prop.set", "params": {"layer": "BG_AstroRing_Outer", "path": "contents/trim/end", "value": 76.0}},
            {"command": "prop.addKey", "params": {"layer": "BG_AstroRing_Outer", "path": "contents/trim/offset", "time": 0.0, "timeBase": "comp", "value": 0.0}},
            {"command": "prop.addKey", "params": {"layer": "BG_AstroRing_Outer", "path": "contents/trim/offset", "time": dur, "timeBase": "comp", "value": 160.0}},
            {"command": "prop.set", "params": {"layer": "BG_AstroRing_Outer", "path": "transform/opacity", "value": 9.0}},
            {"command": "layer.newShape", "params": {"kind": "ellipse", "name": "BG_AstroRing_Inner", "size": [round(base_d * 0.72, 1), round(base_d * 0.72, 1)], "position": [w * 0.5, h * 0.54], "fill": ring_color_2, "fillOpacity": 0.0, "stroke": ring_color_2, "strokeWidth": 1.1}},
            {"command": "layer.timing", "params": {"layers": ["BG_AstroRing_Inner"], "in": 0.0, "out": dur}},
            {"command": "layer.addShapeItem", "params": {"layer": "BG_AstroRing_Inner", "kind": "trim"}},
            {"command": "prop.set", "params": {"layer": "BG_AstroRing_Inner", "path": "contents/trim/start", "value": 16.0}},
            {"command": "prop.set", "params": {"layer": "BG_AstroRing_Inner", "path": "contents/trim/end", "value": 64.0}},
            {"command": "prop.addKey", "params": {"layer": "BG_AstroRing_Inner", "path": "contents/trim/offset", "time": 0.0, "timeBase": "comp", "value": 0.0}},
            {"command": "prop.addKey", "params": {"layer": "BG_AstroRing_Inner", "path": "contents/trim/offset", "time": dur, "timeBase": "comp", "value": -210.0}},
            {"command": "prop.set", "params": {"layer": "BG_AstroRing_Inner", "path": "transform/opacity", "value": 8.0}},
        ])

        # Focused Gallery CC Spotlight Pool supporting the active hero artwork
        spot_kfs = cinema.get("spot_keyframes") or []
        if spot_kfs or float(cinema.get("spot_opacity", 0.0)) > 0.0:
            ctx.commands.extend([
                {"command": "layer.newSolid", "params": {"name": "Pool_Spot", "color": "#000000", "width": int(w), "height": int(h)}},
                {"command": "layer.timing", "params": {"layers": ["Pool_Spot"], "in": 0.0, "out": dur}},
                {"command": "effect.apply", "params": {"layers": ["Pool_Spot"], "effect": "ec.perspective.ccspotlight"}},
                {"command": "prop.set", "params": {"layer": "Pool_Spot", "path": "effects/#1/height", "value": 72.0}},
                {"command": "prop.set", "params": {"layer": "Pool_Spot", "path": "effects/#1/coneAngle", "value": float(cinema.get("spot_cone", 54.0))}},
                {"command": "prop.set", "params": {"layer": "Pool_Spot", "path": "effects/#1/edgeSoftness", "value": 85.0}},
                {"command": "prop.set", "params": {"layer": "Pool_Spot", "path": "effects/#1/intensity", "value": float(cinema.get("spot_intensity", 210.0))}},
                {"command": "layer.setBlendMode", "params": {"layers": ["Pool_Spot"], "mode": "Screen"}},
                {"command": "prop.set", "params": {"layer": "Pool_Spot", "path": "transform/opacity", "value": float(cinema.get("spot_opacity", 34.0))}},
            ])
            for sk in spot_kfs:
                st_t = round(float(sk["time"]), 3)
                ctx.commands.extend([
                    {"command": "prop.addKey", "params": {"layer": "Pool_Spot", "path": "effects/#1/from", "time": st_t, "timeBase": "comp", "value": sk.get("from", [w * 0.25, -140.0])}},
                    {"command": "prop.addKey", "params": {"layer": "Pool_Spot", "path": "effects/#1/to", "time": st_t, "timeBase": "comp", "value": sk.get("to", [w * 0.5, h * 0.54])}},
                    {"command": "prop.addKey", "params": {"layer": "Pool_Spot", "path": "effects/#1/color", "time": st_t, "timeBase": "comp", "value": _hex_to_rgba_float(str(sk.get("color", "#38BDF8")))}},
                ])

    def _inject_animated_lucide_rig(
        self,
        ctx: CompileContext,
        aid: str,
        ref: Dict[str, Any],
        anim_cfg: Dict[str, Any],
    ) -> None:
        """Compile GPU-fast 3-layer animated Lucide SVG icon rig:
        IconRipple (impact shockwave) + IconRing (Trim Paths glowing halo) + SvgAsset (Trim Paths draw + semantic motion).
        """
        lname = f"SvgAsset_{aid}"
        st = max(0.0, float(ref.get("in", 0.0)))
        en = min(ctx.duration, float(ref.get("out", ctx.duration)))
        if en <= st:
            return
        pos = [float(x) for x in ref.get("position", ref.get("pos", [ctx.width * 0.68, ctx.height * 0.30]))]
        z = float(ref.get("z", -12.0))
        base_scale = float(ref.get("scale", 340.0))
        color = str(anim_cfg.get("color", "#38BDF8"))
        preset = str(anim_cfg.get("preset", "shield_guard"))
        impact_t = float(anim_cfg.get("impact_time", st + 0.42))
        ring_size = float(anim_cfg.get("ring_size", 136.0))
        ring_fill = str(anim_cfg.get("ring_fill", "#0B1628"))
        ring_fill_op = float(anim_cfg.get("ring_fill_opacity", 58.0))

        svg_idx = None
        for idx, c in enumerate(ctx.commands):
            if c.get("command") == "edit.pasteSvg" and c.get("params", {}).get("name") == lname:
                svg_idx = idx
                break
        if svg_idx is None:
            return

        ring_name = f"IconRing_{aid}"
        ripple_name = f"IconRipple_{aid}"
        fade_s = round(max(st + 0.25, en - 0.18), 3)

        back_cmds: List[Dict[str, Any]] = [
            # Expanding shockwave ring on impact moment (GPU-fast, zero heavy blur)
            {
                "command": "layer.newShape",
                "params": {
                    "kind": "ellipse", "name": ripple_name,
                    "size": [ring_size, ring_size], "position": [pos[0], pos[1]],
                    "fill": color, "fillOpacity": 0.0, "stroke": color, "strokeWidth": 3.4,
                },
            },
            {"command": "layer.timing", "params": {"layers": [ripple_name], "in": st, "out": en}},
            {"command": "prop.set", "params": {"layer": ripple_name, "path": "transform/position", "value": [pos[0], pos[1], z + 4.0]}},
            {"command": "prop.addKey", "params": {"layer": ripple_name, "path": "transform/scale", "time": round(max(st, impact_t - 0.04), 3), "timeBase": "comp", "value": [78.0, 78.0, 100.0]}},
            {"command": "prop.addKey", "params": {"layer": ripple_name, "path": "transform/scale", "time": round(min(en, impact_t + 0.72), 3), "timeBase": "comp", "value": [195.0, 195.0, 100.0]}},
            {"command": "prop.addKey", "params": {"layer": ripple_name, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}},
            {"command": "prop.addKey", "params": {"layer": ripple_name, "path": "transform/opacity", "time": round(max(st + 0.01, impact_t - 0.02), 3), "timeBase": "comp", "value": 0.0}},
            {"command": "prop.addKey", "params": {"layer": ripple_name, "path": "transform/opacity", "time": round(min(en, impact_t + 0.06), 3), "timeBase": "comp", "value": 85.0}},
            {"command": "prop.addKey", "params": {"layer": ripple_name, "path": "transform/opacity", "time": round(min(en, impact_t + 0.72), 3), "timeBase": "comp", "value": 0.0}},
            # Animated Glowing Orbital Ring (draws on with Trim Paths + gentle breathing pulse)
            {
                "command": "layer.newShape",
                "params": {
                    "kind": "ellipse", "name": ring_name,
                    "size": [ring_size, ring_size], "position": [pos[0], pos[1]],
                    "fill": ring_fill, "fillOpacity": ring_fill_op, "stroke": color, "strokeWidth": 3.0,
                },
            },
            {"command": "layer.timing", "params": {"layers": [ring_name], "in": st, "out": en}},
            {"command": "prop.set", "params": {"layer": ring_name, "path": "transform/position", "value": [pos[0], pos[1], z + 2.0]}},
            {"command": "layer.addShapeItem", "params": {"layer": ring_name, "kind": "trim"}},
            {"command": "prop.addKey", "params": {"layer": ring_name, "path": "contents/trim/end", "time": round(st, 3), "timeBase": "comp", "value": 0.0}},
            {"command": "prop.addKey", "params": {"layer": ring_name, "path": "contents/trim/end", "time": round(min(en, st + 0.50), 3), "timeBase": "comp", "value": 100.0}},
            {"command": "prop.addKey", "params": {"layer": ring_name, "path": "contents/trim/offset", "time": round(st, 3), "timeBase": "comp", "value": -90.0}},
            {"command": "prop.addKey", "params": {"layer": ring_name, "path": "contents/trim/offset", "time": round(en, 3), "timeBase": "comp", "value": 120.0}},
            {"command": "effect.apply", "params": {"layers": [ring_name], "effect": "ec.stylize.glow"}},
            {"command": "prop.set", "params": {"layer": ring_name, "path": "effects/#1/intensity", "value": 0.75}},
            {"command": "prop.set", "params": {"layer": ring_name, "path": "effects/#1/radius", "value": 18.0}},
            {"command": "prop.addKey", "params": {"layer": ring_name, "path": "transform/opacity", "time": round(st, 3), "timeBase": "comp", "value": 0.0}},
            {"command": "prop.addKey", "params": {"layer": ring_name, "path": "transform/opacity", "time": round(min(en, st + 0.16), 3), "timeBase": "comp", "value": 100.0}},
            {"command": "prop.addKey", "params": {"layer": ring_name, "path": "transform/opacity", "time": fade_s, "timeBase": "comp", "value": 100.0}},
            {"command": "prop.addKey", "params": {"layer": ring_name, "path": "transform/opacity", "time": round(en, 3), "timeBase": "comp", "value": 0.0}},
        ]
        ctx.three_d_layers.extend([ripple_name, ring_name])

        icon_motion_cmds: List[Dict[str, Any]] = [
            {"command": "layer.addShapeItem", "params": {"layer": lname, "kind": "trim"}},
            {"command": "prop.set", "params": {"layer": lname, "path": "contents/trim/mode", "value": 0}},
            {"command": "prop.addKey", "params": {"layer": lname, "path": "contents/trim/end", "time": round(st, 3), "timeBase": "comp", "value": 0.0}},
            {"command": "prop.addKey", "params": {"layer": lname, "path": "contents/trim/end", "time": round(min(en, st + 0.58), 3), "timeBase": "comp", "value": 100.0}},
        ]
        ctx.ease_keys.extend([
            {"layer": lname, "path": "contents/trim/end", "time": round(st, 3)},
            {"layer": lname, "path": "contents/trim/end", "time": round(min(en, st + 0.58), 3)},
            {"layer": ring_name, "path": "contents/trim/end", "time": round(st, 3)},
            {"layer": ring_name, "path": "contents/trim/end", "time": round(min(en, st + 0.50), 3)},
        ])

        t_cur = st + 0.55
        bob_idx = 0
        while t_cur < en - 0.45:
            dy = -9.0 if (bob_idx % 2 == 0) else 7.0
            sc_ring = 104.0 if (bob_idx % 2 == 0) else 98.0
            back_cmds.append({"command": "prop.addKey", "params": {"layer": ring_name, "path": "transform/position", "time": round(t_cur, 3), "timeBase": "comp", "value": [pos[0], round(pos[1] + dy, 1), z + 2.0]}})
            back_cmds.append({"command": "prop.addKey", "params": {"layer": ring_name, "path": "transform/scale", "time": round(t_cur, 3), "timeBase": "comp", "value": [sc_ring, sc_ring, 100.0]}})
            icon_motion_cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": round(t_cur, 3), "timeBase": "comp", "value": [pos[0], round(pos[1] + dy, 1), z]}})
            ctx.ease_keys.append({"layer": lname, "path": "transform/position", "time": round(t_cur, 3)})
            ctx.ease_keys.append({"layer": ring_name, "path": "transform/position", "time": round(t_cur, 3)})
            t_cur += 1.05
            bob_idx += 1

        if preset == "shield_guard":
            for k_t, mult, rot in [
                (impact_t, 1.15, -5.0),
                (impact_t + 0.30, 0.98, 3.0),
                (impact_t + 0.62, 1.04, 0.0),
                (min(en - 0.5, impact_t + 3.2), 1.11, -3.0),
                (min(en - 0.3, impact_t + 3.65), 1.00, 0.0),
            ]:
                if st < k_t < en:
                    sc = round(base_scale * mult, 1)
                    icon_motion_cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": round(k_t, 3), "timeBase": "comp", "value": [sc, sc, 100.0]}})
                    icon_motion_cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/rotation", "time": round(k_t, 3), "timeBase": "comp", "value": rot}})
        elif preset == "lock_snap":
            for k_t, mult, rot in [
                (impact_t - 0.08, 1.00, 0.0),
                (impact_t + 0.04, 1.22, -19.0),
                (impact_t + 0.14, 0.94, 15.0),
                (impact_t + 0.24, 1.08, -9.0),
                (impact_t + 0.34, 0.98, 4.5),
                (impact_t + 0.44, 1.00, 0.0),
            ]:
                if st < k_t < en:
                    sc = round(base_scale * mult, 1)
                    icon_motion_cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": round(k_t, 3), "timeBase": "comp", "value": [sc, sc, 100.0]}})
                    icon_motion_cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/rotation", "time": round(k_t, 3), "timeBase": "comp", "value": rot}})
        elif preset == "bulb_eureka":
            ctx.fx_counter[lname] = ctx.fx_counter.get(lname, 0) + 1
            fx_slot = f"effects/#{ctx.fx_counter[lname]}"
            icon_motion_cmds.extend([
                {"command": "effect.apply", "params": {"layers": [lname], "effect": "ec.stylize.glow"}},
                {"command": "prop.addKey", "params": {"layer": lname, "path": f"{fx_slot}/radius", "time": round(st, 3), "timeBase": "comp", "value": 16.0}},
                {"command": "prop.addKey", "params": {"layer": lname, "path": f"{fx_slot}/radius", "time": round(min(en, impact_t + 0.14), 3), "timeBase": "comp", "value": 46.0}},
                {"command": "prop.addKey", "params": {"layer": lname, "path": f"{fx_slot}/radius", "time": round(min(en, impact_t + 0.85), 3), "timeBase": "comp", "value": 24.0}},
                {"command": "prop.addKey", "params": {"layer": lname, "path": f"{fx_slot}/intensity", "time": round(st, 3), "timeBase": "comp", "value": 0.55}},
                {"command": "prop.addKey", "params": {"layer": lname, "path": f"{fx_slot}/intensity", "time": round(min(en, impact_t + 0.14), 3), "timeBase": "comp", "value": 2.15}},
                {"command": "prop.addKey", "params": {"layer": lname, "path": f"{fx_slot}/intensity", "time": round(min(en, impact_t + 0.85), 3), "timeBase": "comp", "value": 1.05}},
            ])
            for k_t, mult, rot in [
                (impact_t + 0.08, 1.24, -8.0),
                (impact_t + 0.28, 0.96, 6.0),
                (impact_t + 0.50, 1.04, 0.0),
                (min(en - 1.5, impact_t + 4.6), 1.14, 5.0),
                (min(en - 0.8, impact_t + 5.1), 1.00, 0.0),
            ]:
                if st < k_t < en:
                    sc = round(base_scale * mult, 1)
                    icon_motion_cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": round(k_t, 3), "timeBase": "comp", "value": [sc, sc, 100.0]}})
                    icon_motion_cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/rotation", "time": round(k_t, 3), "timeBase": "comp", "value": rot}})
        elif preset == "battle_strike":
            for k_t, mult, rot in [
                (impact_t + 0.04, 1.28, -14.0),
                (impact_t + 0.18, 0.94, 10.0),
                (impact_t + 0.34, 1.06, -4.0),
                (impact_t + 0.50, 1.00, 0.0),
                (min(en - 0.4, impact_t + 2.0), 1.12, 4.0),
                (min(en - 0.2, impact_t + 2.5), 1.00, 0.0),
            ]:
                if st < k_t < en:
                    sc = round(base_scale * mult, 1)
                    icon_motion_cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": round(k_t, 3), "timeBase": "comp", "value": [sc, sc, 100.0]}})
                    icon_motion_cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/rotation", "time": round(k_t, 3), "timeBase": "comp", "value": rot}})
        elif preset == "compass_seek":
            for k_t, rot in [
                (st + 0.10, -38.0), (st + 0.62, 26.0), (st + 1.15, -15.0),
                (st + 1.68, 8.0), (st + 2.20, -3.0), (st + 2.80, 0.0),
                (min(en - 1.2, st + 4.1), 7.0), (min(en - 0.3, st + 5.5), -5.0),
            ]:
                if st < k_t < en:
                    icon_motion_cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/rotation", "time": round(k_t, 3), "timeBase": "comp", "value": rot}})
                    ctx.ease_keys.append({"layer": lname, "path": "transform/rotation", "time": round(k_t, 3)})

        ctx.commands[svg_idx:svg_idx] = back_cmds
        ctx.commands.extend(icon_motion_cmds)

    def _emit_procedural_item(
        self,
        ctx: CompileContext,
        pg: Dict[str, Any],
        palette: Dict[str, Any],
        primary_hex: str,
        accent_hex: str,
    ) -> None:
        kind = str(pg.get("kind", "shape_node"))
        gid = str(pg.get("id", "proc_item"))
        st = max(0.0, float(pg.get("start", 0.0)))
        en = min(ctx.duration, float(pg.get("end", ctx.duration)))
        if en <= st:
            en = min(ctx.duration, st + 1.0)

        if kind in ("bezier_connector", "bezier_arrow"):
            lname = f"Path_{gid}"
            stage_3d = bool(pg.get("three_d") or ctx.scene_graph.get("composition", {}).get("enable_3d_stage"))
            z_p = float(pg.get("z", 0.0))
            ctx.commands.append({"command": "layer.newShape", "params": {"kind": "none", "name": lname}})
            ctx.commands.append({"command": "layer.timing", "params": {"layers": [lname], "in": st, "out": en}})
            if stage_3d:
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/position", "value": [ctx.width / 2.0, ctx.height / 2.0, z_p]}})
                ctx.three_d_layers.append(lname)
            ctx.commands.append({
                "command": "shape.newPath",
                "params": {
                    "layer": lname,
                    "vertices": pg["vertices"],
                    "inTangents": pg.get("in_tangents"),
                    "outTangents": pg.get("out_tangents"),
                    "closed": False,
                    "stroke": pg.get("stroke_color", primary_hex),
                    "strokeWidth": float(pg.get("stroke_width", 8.0)),
                    "fill": False,
                    "name": f"{gid}_Path",
                },
            })
            if pg.get("dashed"):
                ctx.commands.append({"command": "shape.dashes.add", "params": {"layer": lname}})
            ctx.commands.append({"command": "layer.addShapeItem", "params": {"layer": lname, "kind": "trim"}})
            draw_end = min(en, st + max(0.25, float(pg.get("draw_duration", 0.7))))
            ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "contents/trim/end", "time": st, "timeBase": "comp", "value": 0.0}})
            ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "contents/trim/end", "time": round(draw_end, 3), "timeBase": "comp", "value": 100.0}})
            _add_fade_out(ctx.commands, lname, st, en, ctx.duration)
            ctx.ease_keys.extend([
                {"layer": lname, "path": "contents/trim/end", "time": st},
                {"layer": lname, "path": "contents/trim/end", "time": round(draw_end, 3)},
            ])
            if pg.get("with_arrow") and pg.get("arrow_head_vertices"):
                hname = f"ArrowHead_{gid}"
                ctx.commands.append({"command": "layer.newShape", "params": {"kind": "none", "name": hname}})
                ctx.commands.append({"command": "layer.timing", "params": {"layers": [hname], "in": st, "out": en}})
                if stage_3d:
                    ctx.commands.append({"command": "prop.set", "params": {"layer": hname, "path": "transform/position", "value": [ctx.width / 2.0, ctx.height / 2.0, z_p]}})
                    ctx.three_d_layers.append(hname)
                ctx.commands.append({
                    "command": "shape.newPath",
                    "params": {
                        "layer": hname,
                        "vertices": pg["arrow_head_vertices"],
                        "closed": True,
                        "fill": pg.get("stroke_color", accent_hex),
                        "stroke": False,
                        "name": f"{gid}_Head",
                    },
                })
                h_in = max(st, draw_end - 0.16)
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": hname, "path": "transform/opacity", "time": round(h_in, 3), "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": hname, "path": "transform/opacity", "time": round(min(en, draw_end + 0.05), 3), "timeBase": "comp", "value": 100.0}})
                _add_fade_out(ctx.commands, hname, st, en, ctx.duration)

        elif kind == "shape_node":
            lname = f"Node_{gid}"
            pos = pg.get("position", [ctx.width / 2.0, ctx.height / 2.0])
            size = pg.get("size", [120.0, 120.0])
            z = float(pg.get("z", 0.0))
            node_3d = bool(pg.get("three_d") or ctx.scene_graph.get("composition", {}).get("enable_3d_stage"))
            ctx.commands.append({
                "command": "layer.newShape",
                "params": {
                    "kind": pg.get("shape", "ellipse"),
                    "name": lname,
                    "size": size,
                    "fill": pg.get("fill", "#162033"),
                    "stroke": pg.get("stroke", primary_hex),
                    "strokeWidth": float(pg.get("stroke_width", 5.0)),
                    "position": [float(pos[0]), float(pos[1])],
                },
            })
            ctx.commands.append({"command": "layer.timing", "params": {"layers": [lname], "in": st, "out": en}})
            if node_3d:
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/position", "value": [float(pos[0]), float(pos[1]), z]}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": lname, "path": "materialOptions/castsShadows", "value": 1}})
                ctx.three_d_layers.append(lname)

            settle_t = min(en, st + 0.35)
            ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [20, 20, 100]}})
            ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": round(settle_t, 3), "timeBase": "comp", "value": [100, 100, 100]}})
            ctx.ease_keys.extend([
                {"layer": lname, "path": "transform/scale", "time": st},
                {"layer": lname, "path": "transform/scale", "time": round(settle_t, 3)},
            ])

            icon_key = pg.get("icon")
            if icon_key and icon_key in ctx.svg_markups:
                iname = f"NodeIcon_{gid}"
                ctx.commands.append({"command": "edit.pasteSvg", "params": {"svg": ctx.svg_markups[icon_key], "name": iname, "comp": ctx.comp_name}})
                ctx.commands.append({"command": "layer.timing", "params": {"layers": [iname], "in": st + 0.05, "out": en}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": iname, "path": "transform/position", "value": [float(pos[0]), float(pos[1]), z]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": iname, "path": "transform/scale", "time": round(st + 0.05, 3), "timeBase": "comp", "value": [10, 10, 100]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": iname, "path": "transform/scale", "time": round(min(en, st + 0.4), 3), "timeBase": "comp", "value": [110, 110, 100]}})
                if node_3d:
                    ctx.three_d_layers.append(iname)

            label = str(pg.get("label", "")).strip()
            if label:
                tname = f"NodeLbl_{gid}"
                rtl = is_rtl_text(label)
                ctx.commands.append({
                    "command": "layer.newText",
                    "params": {
                        "name": tname,
                        "text": label,
                        "font": str(pg.get("font") or "Cairo"),
                        "style": "Bold",
                        "size": 28,
                        "fill": pg.get("label_color", "#F8FAFC"),
                        "direction": "rtl" if rtl else "ltr",
                        "justify": "center",
                        "position": [float(pos[0]), float(pos[1]) + float(size[1]) * 0.5 + 42.0],
                    },
                })
                ctx.commands.append({"command": "layer.timing", "params": {"layers": [tname], "in": st + 0.1, "out": en}})
                if node_3d:
                    ctx.commands.append({"command": "prop.set", "params": {"layer": tname, "path": "transform/position", "value": [float(pos[0]), float(pos[1]) + float(size[1]) * 0.5 + 42.0, z]}})
                    ctx.three_d_layers.append(tname)
                _add_fade_out(ctx.commands, tname, st + 0.1, en, ctx.duration)
            _add_fade_out(ctx.commands, lname, st, en, ctx.duration)
            if icon_key and icon_key in ctx.svg_markups:
                _add_fade_out(ctx.commands, f"NodeIcon_{gid}", st + 0.05, en, ctx.duration)

        elif kind == "badge_card":
            cname = f"Card_{gid}"
            pos = pg.get("position", [ctx.width / 2.0, ctx.height / 2.0])
            size = pg.get("size", [320.0, 140.0])
            ctx.commands.append({
                "command": "layer.newShape",
                "params": {
                    "kind": "rounded",
                    "name": cname,
                    "size": size,
                    "fill": pg.get("fill", "#1E293B"),
                    "stroke": pg.get("stroke", primary_hex),
                    "strokeWidth": 4.0,
                    "position": [float(pos[0]), float(pos[1])],
                },
            })
            ctx.commands.append({"command": "layer.timing", "params": {"layers": [cname], "in": st, "out": en}})
            if pg.get("use_track_matte"):
                mname = f"Matte_{gid}"
                ctx.commands.append({
                    "command": "layer.newShape",
                    "params": {"kind": "rect", "name": mname, "size": size, "fill": "#FFFFFF", "stroke": False, "position": [float(pos[0]) - float(size[0]), float(pos[1])]},
                })
                ctx.commands.append({"command": "layer.timing", "params": {"layers": [mname], "in": st, "out": en}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": mname, "path": "transform/position", "time": st, "timeBase": "comp", "value": [float(pos[0]) - float(size[0]), float(pos[1]), 0.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": mname, "path": "transform/position", "time": round(min(en, st + 0.45), 3), "timeBase": "comp", "value": [float(pos[0]), float(pos[1]), 0.0]}})
                ctx.commands.append({"command": "layer.setTrackMatte", "params": {"layer": cname, "matte": mname, "kind": "alpha"}})
            else:
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": cname, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [40, 40, 100]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": cname, "path": "transform/scale", "time": round(min(en, st + 0.36), 3), "timeBase": "comp", "value": [100, 100, 100]}})
            _add_fade_out(ctx.commands, cname, st, en, ctx.duration)

            title = str(pg.get("title", "")).strip()
            subtitle = str(pg.get("subtitle", "")).strip()
            if title:
                tname = f"CardTxt_{gid}"
                rtl = is_rtl_text(title)
                t_in = st + (0.20 if pg.get("use_track_matte") else 0.02)
                ctx.commands.append({
                    "command": "layer.newText",
                    "params": {
                        "name": tname,
                        "text": title,
                        "font": str(pg.get("font") or "Cairo"),
                        "style": "Bold",
                        "size": 34 if not subtitle else 30,
                        "fill": pg.get("text_color", "#F8FAFC"),
                        "direction": "rtl" if rtl else "ltr",
                        "justify": "center",
                        "position": [float(pos[0]), float(pos[1]) - (8.0 if subtitle else -8.0)],
                    },
                })
                ctx.commands.append({"command": "layer.timing", "params": {"layers": [tname], "in": t_in, "out": en}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": t_in, "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": round(min(en, t_in + 0.10), 3), "timeBase": "comp", "value": 100.0}})
                _add_fade_out(ctx.commands, tname, t_in, en, ctx.duration)
            if subtitle:
                sname = f"CardSub_{gid}"
                rtl_s = is_rtl_text(subtitle)
                s_in = st + (0.24 if pg.get("use_track_matte") else 0.05)
                ctx.commands.append({
                    "command": "layer.newText",
                    "params": {
                        "name": sname,
                        "text": subtitle,
                        "font": str(pg.get("font") or "Cairo"),
                        "size": 24,
                        "fill": palette.get("accent", accent_hex),
                        "direction": "rtl" if rtl_s else "ltr",
                        "justify": "center",
                        "position": [float(pos[0]), float(pos[1]) + 32.0],
                    },
                })
                ctx.commands.append({"command": "layer.timing", "params": {"layers": [sname], "in": s_in, "out": en}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/opacity", "time": s_in, "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/opacity", "time": round(min(en, s_in + 0.10), 3), "timeBase": "comp", "value": 100.0}})
                _add_fade_out(ctx.commands, sname, s_in, en, ctx.duration)

        elif kind == "chart_bar":
            bname = f"Bar_{gid}"
            pos = pg.get("position", [960.0, 600.0])
            size = pg.get("size", [80.0, 220.0])
            ctx.commands.append({
                "command": "layer.newShape",
                "params": {"kind": "rounded", "name": bname, "size": size, "fill": pg.get("fill", primary_hex), "stroke": pg.get("stroke", "#FFFFFF"), "strokeWidth": 2.5, "position": pos},
            })
            ctx.commands.append({"command": "layer.timing", "params": {"layers": [bname], "in": st, "out": en}})
            ctx.commands.append({"command": "prop.addKey", "params": {"layer": bname, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [100, 5, 100]}})
            ctx.commands.append({"command": "prop.addKey", "params": {"layer": bname, "path": "transform/scale", "time": round(min(en, st + 0.55), 3), "timeBase": "comp", "value": [100, 100, 100]}})
            if pg.get("value_text"):
                vname = f"BarVal_{gid}"
                vtxt = str(pg["value_text"])
                ctx.commands.append({
                    "command": "layer.newText",
                    "params": {
                        "name": vname,
                        "text": vtxt,
                        "font": str(pg.get("font") or "Cairo"),
                        "style": "Bold",
                        "size": 30,
                        "fill": pg.get("text_color", "#FFFFFF"),
                        "direction": "rtl" if is_rtl_text(vtxt) else "ltr",
                        "justify": "center",
                        "position": [float(pos[0]), float(pos[1]) - float(size[1]) * 0.5 - 24.0],
                    },
                })
                ctx.commands.append({"command": "layer.timing", "params": {"layers": [vname], "in": st + 0.22, "out": en}})

        elif kind == "repeater_rings":
            rname = f"Rep_{gid}"
            center = pg.get("center", [ctx.width / 2.0, ctx.height / 2.0])
            bs = float(pg.get("base_size", 110.0))
            ctx.commands.append({
                "command": "layer.newShape",
                "params": {"kind": "ellipse", "name": rname, "size": [bs, bs], "fill": False, "stroke": pg.get("stroke_color", "#00D4C0"), "strokeWidth": 4.0, "position": center},
            })
            ctx.commands.append({"command": "layer.timing", "params": {"layers": [rname], "in": st, "out": en}})
            ctx.commands.append({"command": "layer.addShapeItem", "params": {"layer": rname, "kind": "repeater"}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": rname, "path": "contents/repeater/copies", "value": int(pg.get("copies", 5))}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": rname, "path": "contents/repeater/transform/position", "value": [0, 0]}})
            ctx.commands.append({"command": "prop.addKey", "params": {"layer": rname, "path": "contents/repeater/transform/scale", "time": st, "timeBase": "comp", "value": [105, 105]}})
            ctx.commands.append({"command": "prop.addKey", "params": {"layer": rname, "path": "contents/repeater/transform/scale", "time": round(en, 3), "timeBase": "comp", "value": [145, 145]}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": rname, "path": "contents/repeater/transform/endOpacity", "value": 15.0}})
            if ctx.scene_graph.get("composition", {}).get("enable_3d_stage"):
                ctx.commands.append({"command": "prop.set", "params": {"layer": rname, "path": "transform/position", "value": [float(center[0]), float(center[1]), float(pg.get("z", 12.0))]}})
                ctx.three_d_layers.append(rname)

        elif kind == "depth_plane":
            dname = f"Plane_{gid}"
            pos = pg.get("position", [ctx.width / 2.0, ctx.height / 2.0])
            size = pg.get("size", [520.0, 320.0])
            z = float(pg.get("z", DEPTH_PLANES_Z["mid_stage"]))
            ctx.commands.append({
                "command": "layer.newShape",
                "params": {"kind": pg.get("shape", "rounded"), "name": dname, "size": size, "fill": pg.get("fill", "#1E293B"), "stroke": pg.get("stroke", primary_hex), "strokeWidth": 4.0, "position": pos},
            })
            ctx.commands.append({"command": "layer.timing", "params": {"layers": [dname], "in": st, "out": en}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": dname, "path": "transform/position", "value": [float(pos[0]), float(pos[1]), z]}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": dname, "path": "materialOptions/castsShadows", "value": 1}})
            ctx.three_d_layers.append(dname)

        elif kind == "spotlight_cone":
            sname = f"SpotCone_{gid}"
            verts_local = [[float(v[0]) - ctx.width / 2.0, float(v[1]) - ctx.height / 2.0] for v in pg.get("vertices", [])]
            if len(verts_local) >= 3:
                ctx.commands.append({"command": "layer.newShape", "params": {"kind": "none", "name": sname}})
                ctx.commands.append({
                    "command": "shape.newPath",
                    "params": {
                        "layer": sname,
                        "vertices": verts_local,
                        "closed": True,
                        "fill": pg.get("fill", "#E11D48"),
                        "fillOpacity": float(pg.get("fill_opacity", 24.0)),
                        "stroke": False,
                        "name": f"{gid}_Cone",
                    },
                })
                if pg.get("blur"):
                    ctx.commands.append({"command": "effect.apply", "params": {"effect": "Gaussian Blur", "layers": [sname]}})
                    ctx.commands.append({"command": "prop.set", "params": {"layer": sname, "path": "effects/Gaussian Blur/blurriness", "value": float(pg["blur"])}})
                ctx.commands.append({"command": "layer.timing", "params": {"layers": [sname], "in": st, "out": en}})
                max_op = float(pg.get("opacity", 70.0))
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/opacity", "time": round(min(en, st + 0.25), 3), "timeBase": "comp", "value": max_op}})
                if en - st > 0.55:
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/opacity", "time": round(max(st + 0.25, en - 0.25), 3), "timeBase": "comp", "value": max_op}})
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/opacity", "time": en, "timeBase": "comp", "value": 0.0}})
                if pg.get("three_d", True):
                    ctx.commands.append({"command": "prop.set", "params": {"layer": sname, "path": "transform/position", "value": [ctx.width / 2.0, ctx.height / 2.0, float(pg.get("z", 16.0))]}})
                    ctx.three_d_layers.append(sname)

        elif kind == "ground_shadow":
            sname = f"GroundShadow_{gid}"
            pos = pg.get("position", [ctx.width / 2.0, ctx.height * 0.64])
            size = pg.get("size", [260.0, 24.0])
            ctx.commands.append({
                "command": "layer.newShape",
                "params": {
                    "kind": "ellipse",
                    "name": sname,
                    "size": size,
                    "fill": pg.get("fill", "#04070D"),
                    "fillOpacity": float(pg.get("opacity", 48.0)),
                    "stroke": False,
                    "position": [float(pos[0]), float(pos[1])],
                },
            })
            ctx.commands.append({"command": "layer.timing", "params": {"layers": [sname], "in": st, "out": en}})
            if pg.get("three_d"):
                ctx.commands.append({"command": "prop.set", "params": {"layer": sname, "path": "transform/position", "value": [float(pos[0]), float(pos[1]), float(pg.get("z", 0.0))]}})
                ctx.three_d_layers.append(sname)
            if pg.get("keyframes"):
                for kf in pg["keyframes"]:
                    kp = kf["pos"]
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/position", "time": float(kf["time"]), "timeBase": "comp", "value": [float(kp[0]), float(kp[1]), float(pg.get("z", 0.0))] if pg.get("three_d") else [float(kp[0]), float(kp[1])]}})
                    ctx.ease_keys.append({"layer": sname, "path": "transform/position", "time": float(kf["time"])})
            if not pg.get("no_pop"):
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [30.0, 40.0, 100.0]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/scale", "time": round(min(en, st + 0.35), 3), "timeBase": "comp", "value": [100.0, 100.0, 100.0]}})
            _add_fade_out(ctx.commands, sname, st, en, ctx.duration, fade_sec=float(pg.get("fade_out", 0.18)))

        elif kind == "icon_medallion":
            mname = f"IconPill_{gid}"
            pos = pg.get("position", [ctx.width - 140.0, 112.0])
            psize = float(pg.get("size", 112.0))
            ctx.commands.append({
                "command": "layer.newShape",
                "params": {
                    "kind": "ellipse",
                    "name": mname,
                    "size": [psize, psize],
                    "fill": pg.get("fill", "#F8FAFC"),
                    "fillOpacity": 96.0,
                    "stroke": pg.get("stroke", accent_hex),
                    "strokeWidth": 4.0,
                    "position": [float(pos[0]), float(pos[1])],
                },
            })
            ctx.commands.append({"command": "layer.timing", "params": {"layers": [mname], "in": st, "out": en}})
            ctx.commands.append({"command": "prop.addKey", "params": {"layer": mname, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [30.0, 30.0, 100.0]}})
            ctx.commands.append({"command": "prop.addKey", "params": {"layer": mname, "path": "transform/scale", "time": round(min(en, st + 0.28), 3), "timeBase": "comp", "value": [100.0, 100.0, 100.0]}})
            ctx.commands.append({"command": "effect.apply", "params": {"layers": [mname], "effect": "ec.perspective.dropshadow"}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": mname, "path": "effects/#1/opacity", "value": 52.0}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": mname, "path": "effects/#1/distance", "value": 10.0}})
            ctx.commands.append({"command": "prop.set", "params": {"layer": mname, "path": "effects/#1/softness", "value": 20.0}})
            _add_fade_out(ctx.commands, mname, st, en, ctx.duration)

            gif_raw = pg.get("gif_path")
            if gif_raw:
                gp = Path(str(gif_raw))
                if not gp.is_file():
                    gp = ROOT_DIR / "assets" / "gifs" / gp.name
                if gp.is_file():
                    gpos_key = gp.resolve().as_posix()
                    if gpos_key not in ctx.imported_files:
                        ctx.commands.append({"command": "file.import", "params": {"paths": [gpos_key]}})
                        ctx.imported_files[gpos_key] = gp.name
                    gw, gh = 100, 100
                    try:
                        from PIL import Image as _PILImage
                        with _PILImage.open(gp) as _im:
                            gw, gh = _im.size
                    except Exception:
                        pass
                    target_icon_px = psize * 0.68
                    gscale = round((target_icon_px / max(1, max(gw, gh))) * 100.0, 2)
                    gname = f"IconGif_{gid}"
                    ctx.commands.append({
                        "command": "layer.addItem",
                        "params": {"item": ctx.imported_files[gpos_key], "in": st, "out": en, "position": [float(pos[0]), float(pos[1])]},
                    })
                    ctx.commands.append({"command": "layer.settings", "params": {"layer": "#1", "name": gname}})
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": gname, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [round(gscale * 0.35, 2), round(gscale * 0.35, 2), 100.0]}})
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": gname, "path": "transform/scale", "time": round(min(en, st + 0.28), 3), "timeBase": "comp", "value": [gscale, gscale, 100.0]}})
                    _add_fade_out(ctx.commands, gname, st, en, ctx.duration)


# 5. Motion Timeline Compiler
class MotionTimelineCompiler:
    """Applies motion paths, subtle expressions, 3D switch, active camera keyframes, and easy-ease."""

    def compile(self, ctx: CompileContext) -> None:
        for mp in ctx.scene_graph.get("motion_paths", []):
            target = mp.get("layer")
            keys = mp.get("keyframes", [])
            if not target or not keys:
                continue
            for k in keys:
                kt = float(k["time"])
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": target, "path": "transform/position", "time": kt, "timeBase": "comp", "value": k["pos"]}})
                ctx.ease_keys.append({"layer": target, "path": "transform/position", "time": kt})
            if mp.get("idle_expression"):
                # Safe floating micro-oscillation via verified Expressions engine
                amp = float(mp.get("amplitude", 8.0))
                freq = float(mp.get("frequency", 1.8))
                ctx.commands.append({
                    "command": "prop.setExpression",
                    "params": {"layer": target, "path": "transform/position", "expression": f"[value[0], value[1] + Math.sin(time * {freq:.2f}) * {amp:.1f}, value[2]]", "enabled": True},
                })

        if ctx.three_d_layers:
            ctx.commands.append({"command": "layer.setSwitch", "params": {"layers": sorted(set(ctx.three_d_layers)), "switch": "threeD", "value": True}})

        cam = ctx.scene_graph.get("camera") or {}
        if cam.get("enabled") and cam.get("keyframes"):
            ctx.commands.append({"command": "layer.newCamera", "params": {"name": "MainCam", "type": "twoNode", "zoom": float(cam.get("zoom", 1650.0))}})
            for ck in cam["keyframes"]:
                kt = float(ck["time"])
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": "MainCam", "path": "transform/position", "time": kt, "timeBase": "comp", "value": ck["pos"]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": "MainCam", "path": "transform/poi", "time": kt, "timeBase": "comp", "value": ck.get("poi", [ctx.width / 2.0, ctx.height / 2.0, 0.0])}})
                ctx.ease_keys.extend([
                    {"layer": "MainCam", "path": "transform/position", "time": kt},
                    {"layer": "MainCam", "path": "transform/poi", "time": kt},
                ])


# 6. Typography Compiler
class TypographyCompiler:
    """Compiles Arabic RTL & LTR editorial headlines, Unified Top Neon HUD (`hud_sequence`), and V6.1 Kinetic Typography."""

    def compile(self, ctx: CompileContext) -> None:
        # Optional global Lumetri + Vignette Adjustment Layer strictly BELOW typography / HUD
        cinema = ctx.scene_graph.get("cinema_stage")
        if cinema and not cinema.get("disable_master_grade"):
            dur = ctx.duration
            ctx.commands.extend([
                {"command": "layer.newAdjustment", "params": {"name": "Master_Grade"}},
                {"command": "layer.timing", "params": {"layers": ["Master_Grade"], "in": 0.0, "out": dur}},
                {"command": "effect.apply", "params": {"layers": ["Master_Grade"], "effect": "ec.color.lumetri"}},
                {"command": "prop.set", "params": {"layer": "Master_Grade", "path": "effects/#1/basicCorrection/tone/contrast", "value": float(cinema.get("lumetri_contrast", 12.0))}},
                {"command": "prop.set", "params": {"layer": "Master_Grade", "path": "effects/#1/creative/adjustments/vibrance", "value": float(cinema.get("lumetri_vibrance", 16.0))}},
                {"command": "prop.set", "params": {"layer": "Master_Grade", "path": "effects/#1/creative/adjustments/fadedFilm", "value": float(cinema.get("lumetri_faded", 2.0))}},
                {"command": "effect.apply", "params": {"layers": ["Master_Grade"], "effect": "ec.stylize.ccvignette"}},
                {"command": "prop.set", "params": {"layer": "Master_Grade", "path": "effects/#2/amount", "value": float(cinema.get("master_vignette", 18.0))}},
            ])

        hud = ctx.scene_graph.get("hud_sequence")
        comp = ctx.scene_graph.get("composition", {})
        palette = comp.get("palette") or {}
        if hud:
            self._compile_unified_hud_sequence(ctx, hud)
            # Also compile explicit overlay blocks (e.g., 9:16 Shorts CTA end-screen cards) marked keep_with_hud
            for idx, tb in enumerate(ctx.scene_graph.get("typography", [])):
                if not tb.get("keep_with_hud"):
                    continue
                text_val = str(tb.get("text", "")).strip()
                if not text_val:
                    continue
                block = dict(tb)
                block.setdefault("id", f"typo_{idx}")
                ctx.commands.extend(
                    compile_kinetic_text_block(
                        block,
                        comp_width=ctx.width,
                        comp_height=ctx.height,
                        comp_duration=ctx.duration,
                        comp_name=ctx.comp_name,
                        work_dir=ctx.work_dir,
                        ease_keys=ctx.ease_keys,
                        palette=palette,
                    )
                )
        else:
            for idx, tb in enumerate(ctx.scene_graph.get("typography", [])):
                text_val = str(tb.get("text", "")).strip()
                if not text_val:
                    continue
                block = dict(tb)
                block.setdefault("id", f"typo_{idx}")
                cmds = compile_kinetic_text_block(
                    block,
                    comp_width=ctx.width,
                    comp_height=ctx.height,
                    comp_duration=ctx.duration,
                    comp_name=ctx.comp_name,
                    work_dir=ctx.work_dir,
                    ease_keys=ctx.ease_keys,
                    palette=palette,
                )
                ctx.commands.extend(cmds)

        # Silent Quranic Verse Cards (`quran_cards`: full-screen dark navy + gold frame + Amiri verse)
        for q_idx, qc in enumerate(ctx.scene_graph.get("quran_cards", [])):
            q_st = float(qc.get("start", 0.0))
            q_en = float(qc.get("end", q_st + 4.8))
            if q_en <= q_st:
                continue
            cx = ctx.width * 0.5
            cy = ctx.height * 0.5
            fade_d = min(0.35, max(0.15, (q_en - q_st) * 0.14))
            pref = f"Quran_{q_idx:02d}"
            layers_q: List[str] = []

            bg_name = f"{pref}_BG"
            layers_q.append(bg_name)
            ctx.commands.append({"command": "layer.newSolid", "params": {"name": bg_name, "color": "#09111E", "width": ctx.width, "height": ctx.height}})

            fw, fh = int(ctx.width * 0.80), int(ctx.height * 0.56)
            fr_name = f"{pref}_Frame"
            in_name = f"{pref}_Inner"
            bd_name = f"{pref}_Badge"
            bt_name = f"{pref}_BadgeTxt"
            ref_name = f"{pref}_Ref"
            layers_q.extend([fr_name, in_name, bd_name, bt_name, ref_name])

            ctx.commands.extend([
                {"command": "layer.newShape", "params": {"kind": "rounded", "name": fr_name, "size": [fw, fh], "position": [cx, cy + 12], "fill": "#0D1726", "fillOpacity": 96, "stroke": "#D4AF37", "strokeWidth": 4.0}},
                {"command": "layer.newShape", "params": {"kind": "rounded", "name": in_name, "size": [fw - 44, fh - 44], "position": [cx, cy + 12], "fill": "#0D1726", "fillOpacity": 0, "stroke": "#D4AF37", "strokeWidth": 1.5}},
                {"command": "layer.newShape", "params": {"kind": "rounded", "name": bd_name, "size": [320, 62], "position": [cx, cy - fh * 0.5 + 12], "fill": "#1A2940", "fillOpacity": 100, "stroke": "#D4AF37", "strokeWidth": 2.5}},
                {"command": "layer.newText", "params": {"name": bt_name, "text": "القرآن الكريم", "font": "Cairo", "style": "Bold", "size": 32, "fill": "#F3D37A", "direction": "rtl", "justify": "center", "position": [cx, cy - fh * 0.5 + 23]}},
            ])

            lines = [str(x).strip() for x in (qc.get("verse_lines") or []) if str(x).strip()]
            v_sz = 48 if len(lines) <= 2 and max((len(x) for x in lines), default=0) < 95 else 40
            y_base = cy - 34 if len(lines) == 2 else cy + 6
            y_step = 94
            line_slots: List[Tuple[str, float, float, float, float]] = []
            t_cursor = q_st + 0.25
            avail_write = max(1.6, (q_en - q_st) - 1.25)
            per_line_dur = avail_write / max(1, len(lines[:3]))
            for li, ltxt in enumerate(lines[:3]):
                ln = f"{pref}_L{li}"
                layers_q.append(ln)
                ctx.commands.append({
                    "command": "layer.newText",
                    "params": {
                        "name": ln, "text": ltxt, "font": "Amiri", "style": "Bold",
                        "size": v_sz, "fill": "#F8FAFC", "direction": "rtl", "justify": "center",
                        "position": [cx, y_base + li * y_step],
                    },
                })
                l_st = round(t_cursor, 3)
                l_en = round(min(q_en - 0.65, l_st + per_line_dur - 0.08), 3)
                ctx.commands.extend([
                    {"command": "effect.apply", "params": {"effect": "Linear Wipe", "layers": [ln]}},
                    {"command": "prop.set", "params": {"layer": ln, "path": "effects/#1/angle", "value": 90.0}},
                    {"command": "prop.set", "params": {"layer": ln, "path": "effects/#1/feather", "value": 24.0}},
                    {"command": "prop.addKey", "params": {"layer": ln, "path": "effects/#1/completion", "time": l_st, "timeBase": "comp", "value": 100.0}},
                    {"command": "prop.addKey", "params": {"layer": ln, "path": "effects/#1/completion", "time": l_en, "timeBase": "comp", "value": 0.0}},
                ])
                line_hw = min(fw * 0.44, max(220.0, len(ltxt) * (v_sz * 0.24)))
                line_slots.append((ln, l_st, l_en, y_base + li * y_step, line_hw))
                t_cursor = l_en + 0.08

            ctx.commands.append({
                "command": "layer.newText",
                "params": {
                    "name": ref_name, "text": str(qc.get("surah_ref", "")), "font": "Cairo", "style": "Bold",
                    "size": 34, "fill": "#D4AF37", "direction": "rtl", "justify": "center",
                    "position": [cx, cy + fh * 0.5 - 66],
                },
            })

            # Glowing Golden Pen Nib gliding RTL along each verse line as it is written
            nib_name = f"{pref}_Nib"
            if line_slots:
                layers_q.append(nib_name)
                ctx.commands.append({
                    "command": "layer.newShape",
                    "params": {"kind": "ellipse", "name": nib_name, "size": [14, 14], "position": [cx + line_slots[0][4], line_slots[0][3] - 12], "fill": "#FFD700", "fillOpacity": 100, "stroke": "#FFF7CC", "strokeWidth": 2.0},
                })
                ctx.commands.append({"command": "effect.apply", "params": {"effect": "Glow", "layers": [nib_name]}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": nib_name, "path": "effects/#1/intensity", "value": 1.1}})
                for _, l_st, l_en, ly, hw in line_slots:
                    ctx.commands.extend([
                        {"command": "prop.addKey", "params": {"layer": nib_name, "path": "transform/position", "time": l_st, "timeBase": "comp", "value": [cx + hw, ly - 12]}},
                        {"command": "prop.addKey", "params": {"layer": nib_name, "path": "transform/position", "time": l_en, "timeBase": "comp", "value": [cx - hw, ly - 12]}},
                    ])

            ctx.commands.append({"command": "layer.timing", "params": {"layers": layers_q, "in": q_st, "out": q_en}})
            # Card bloom scale
            for sname in (fr_name, in_name, bd_name):
                ctx.commands.extend([
                    {"command": "prop.addKey", "params": {"layer": sname, "path": "transform/scale", "time": q_st, "timeBase": "comp", "value": [93.0, 93.0, 100.0]}},
                    {"command": "prop.addKey", "params": {"layer": sname, "path": "transform/scale", "time": round(q_st + fade_d, 3), "timeBase": "comp", "value": [100.0, 100.0, 100.0]}},
                ])
            for lname in layers_q:
                if lname == nib_name and line_slots:
                    nib_end = line_slots[-1][2]
                    ctx.commands.extend([
                        {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": line_slots[0][1], "timeBase": "comp", "value": 0.0}},
                        {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": round(line_slots[0][1] + 0.12, 3), "timeBase": "comp", "value": 95.0}},
                        {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": max(line_slots[0][1] + 0.15, nib_end - 0.10), "timeBase": "comp", "value": 95.0}},
                        {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": round(nib_end + 0.08, 3), "timeBase": "comp", "value": 0.0}},
                    ])
                    continue
                target_op = 98.0 if lname == bg_name else 100.0
                fade_in_t = round(max(q_st + 0.25, q_en - 1.55), 3) if lname == ref_name else q_st
                ctx.commands.extend([
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": fade_in_t, "timeBase": "comp", "value": 0.0}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": round(fade_in_t + fade_d, 3), "timeBase": "comp", "value": target_op}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": max(fade_in_t + fade_d, q_en - fade_d), "timeBase": "comp", "value": target_op}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": q_en, "timeBase": "comp", "value": 0.0}},
                ])

    def _compile_unified_hud_sequence(self, ctx: CompileContext, hud: Dict[str, Any]) -> None:
        """Compile a single persistent Top Neon-Glass Live-Typing HUD bar updating cleanly in-place."""
        cmds = ctx.commands
        dur = ctx.duration
        phrases: List[Dict[str, Any]] = hud.get("phrases") or []
        bar_w = float(hud.get("width", 880.0))
        bar_h = float(hud.get("height", 84.0))
        pos = [float(x) for x in hud.get("position", [ctx.width * 0.5, 96.0])]
        font_family = str(hud.get("font", "IBM Plex Sans Arabic"))
        font_style = str(hud.get("font_style", "Bold"))
        fsize = int(hud.get("font_size", 38))
        bg_fill = str(hud.get("backdrop_fill", "#091222"))
        text_fill = str(hud.get("text_color", "#F8FAFC"))
        base_opacity = float(hud.get("pill_opacity", 92.0))
        fade_out_end = round(max(0.1, dur - 0.14), 3)

        first_non_empty = next((str(p.get("text", "")).strip() for p in phrases if not p.get("hidden") and str(p.get("text", "")).strip()), "")
        hud_dir = "rtl" if is_rtl_str(first_non_empty) else "ltr"

        card_name = "TextCard_HUD"
        cmds.append({
            "command": "layer.newShape",
            "params": {
                "kind": "rounded", "name": card_name, "size": [bar_w, bar_h], "position": pos,
                "fill": bg_fill, "fillOpacity": base_opacity,
                "stroke": str(phrases[0].get("color", "#38BDF8")) if phrases else "#38BDF8", "strokeWidth": 1.6,
            },
        })
        cmds.append({"command": "layer.timing", "params": {"layers": [card_name], "in": 0.0, "out": dur}})
        cmds.append({"command": "effect.apply", "params": {"layers": [card_name], "effect": "ec.perspective.dropshadow"}})
        cmds.append({"command": "prop.set", "params": {"layer": card_name, "path": "effects/#1/opacity", "value": 64.0}})
        cmds.append({"command": "prop.set", "params": {"layer": card_name, "path": "effects/#1/distance", "value": 12.0}})
        cmds.append({"command": "prop.set", "params": {"layer": card_name, "path": "effects/#1/softness", "value": 28.0}})
        cmds.append({"command": "prop.addKey", "params": {"layer": card_name, "path": "transform/scale", "time": 0.0, "timeBase": "comp", "value": [88.0, 92.0, 100.0]}})
        cmds.append({"command": "prop.addKey", "params": {"layer": card_name, "path": "transform/scale", "time": 0.24, "timeBase": "comp", "value": [100.0, 100.0, 100.0]}})

        hud_vis = hud.get("visibility_keyframes")
        if hud_vis:
            for vt, vop in hud_vis:
                cmds.append({"command": "prop.addKey", "params": {"layer": card_name, "path": "transform/opacity", "time": round(float(vt), 3), "timeBase": "comp", "value": float(vop)}})
        else:
            cmds.append({"command": "prop.addKey", "params": {"layer": card_name, "path": "transform/opacity", "time": 0.0, "timeBase": "comp", "value": 0.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": card_name, "path": "transform/opacity", "time": 0.14, "timeBase": "comp", "value": 100.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": card_name, "path": "transform/opacity", "time": fade_out_end, "timeBase": "comp", "value": 100.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": card_name, "path": "transform/opacity", "time": dur, "timeBase": "comp", "value": 0.0}})

        unique_colors: List[str] = []
        for p in phrases:
            c = str(p.get("color", "#38BDF8")).upper()
            if c not in unique_colors:
                unique_colors.append(c)

        for cidx, chex in enumerate(unique_colors):
            for pass_tag, sw, g_int, g_rad in (("Bloom", 2.4, 0.56, 30.0), ("Glow", 3.4, 0.88, 12.0)):
                rname = f"TextCard_{pass_tag}_HUD_{cidx}"
                cmds.append({
                    "command": "layer.newShape",
                    "params": {"kind": "rounded", "name": rname, "size": [bar_w, bar_h], "position": pos, "fill": chex, "fillOpacity": 0.0, "stroke": chex, "strokeWidth": sw},
                })
                cmds.append({"command": "layer.timing", "params": {"layers": [rname], "in": 0.0, "out": dur}})
                cmds.append({"command": "effect.apply", "params": {"layers": [rname], "effect": "ec.stylize.glow"}})
                cmds.append({"command": "prop.set", "params": {"layer": rname, "path": "effects/#1/intensity", "value": g_int}})
                cmds.append({"command": "prop.set", "params": {"layer": rname, "path": "effects/#1/radius", "value": g_rad}})
                cmds.append({"command": "prop.addKey", "params": {"layer": rname, "path": "transform/scale", "time": 0.0, "timeBase": "comp", "value": [88.0, 92.0, 100.0]}})
                cmds.append({"command": "prop.addKey", "params": {"layer": rname, "path": "transform/scale", "time": 0.24, "timeBase": "comp", "value": [100.0, 100.0, 100.0]}})

                first_active = (bool(phrases) and str(phrases[0].get("color", "")).upper() == chex and not phrases[0].get("hidden"))
                cmds.append({"command": "prop.addKey", "params": {"layer": rname, "path": "transform/opacity", "time": 0.0, "timeBase": "comp", "value": 100.0 if first_active else 0.0}})
                prev_active = first_active
                for pidx, ph in enumerate(phrases):
                    pst = float(ph["start"])
                    is_active = (str(ph.get("color", "")).upper() == chex) and (not ph.get("hidden"))
                    if pidx > 0 and is_active != prev_active:
                        t_pre = round(max(0.0, pst - 0.14), 3)
                        t_now = round(max(t_pre + 0.02, pst + 0.04), 3)
                        cmds.append({"command": "prop.addKey", "params": {"layer": rname, "path": "transform/opacity", "time": t_pre, "timeBase": "comp", "value": 100.0 if prev_active else 0.0}})
                        cmds.append({"command": "prop.addKey", "params": {"layer": rname, "path": "transform/opacity", "time": t_now, "timeBase": "comp", "value": 100.0 if is_active else 0.0}})
                    prev_active = is_active
                cmds.append({"command": "prop.addKey", "params": {"layer": rname, "path": "transform/opacity", "time": fade_out_end, "timeBase": "comp", "value": 100.0 if prev_active else 0.0}})
                cmds.append({"command": "prop.addKey", "params": {"layer": rname, "path": "transform/opacity", "time": dur, "timeBase": "comp", "value": 0.0}})

        tname = "Text_HUD"
        cur_name = "TextCursor_HUD"
        text_y = round(pos[1] + fsize * 0.28, 1)
        cur_y = pos[1]
        first_txt = str(phrases[0].get("text", " "))[:1] if (phrases and not phrases[0].get("hidden")) else " "

        cmds.append({
            "command": "layer.newText",
            "params": {"name": tname, "text": first_txt, "font": font_family, "style": font_style, "size": fsize, "fill": text_fill, "direction": hud_dir, "justify": "center", "position": [pos[0], text_y]},
        })
        cmds.append({"command": "layer.timing", "params": {"layers": [tname], "in": 0.0, "out": dur}})
        if hud_vis:
            for vt, vop in hud_vis:
                cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": round(float(vt), 3), "timeBase": "comp", "value": float(vop)}})
        else:
            cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": 0.0, "timeBase": "comp", "value": 0.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": 0.14, "timeBase": "comp", "value": 100.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": fade_out_end, "timeBase": "comp", "value": 100.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": dur, "timeBase": "comp", "value": 0.0}})

        cmds.append({
            "command": "layer.newShape",
            "params": {"kind": "rect", "name": cur_name, "size": [3.5, round(fsize * 0.90, 1)], "position": [pos[0] + 10.0, cur_y], "fill": "#38BDF8", "stroke": False},
        })
        cmds.append({"command": "effect.apply", "params": {"layers": [cur_name], "effect": "ec.stylize.glow"}})
        cmds.append({"command": "prop.set", "params": {"layer": cur_name, "path": "effects/#1/intensity", "value": 0.92}})
        cmds.append({"command": "prop.set", "params": {"layer": cur_name, "path": "effects/#1/radius", "value": 10.0}})
        cmds.append({"command": "layer.timing", "params": {"layers": [cur_name], "in": 0.0, "out": dur}})

        for pidx, ph in enumerate(phrases):
            txt = str(ph.get("text", "")).strip()
            pst = float(ph["start"])
            pen = float(ph["end"])
            if ph.get("hidden") or not txt:
                cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "text/sourceText", "time": round(pst, 3), "timeBase": "comp", "value": " "}})
                cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/opacity", "time": round(pst, 3), "timeBase": "comp", "value": 0.0}})
                continue

            if pidx > 0:
                t_clr = round(max(0.0, pst - 0.10), 3)
                cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "text/sourceText", "time": t_clr, "timeBase": "comp", "value": " "}})
                cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/position", "time": t_clr, "timeBase": "comp", "value": [pos[0] + 8.0, cur_y, 0.0]}})

            rtl = is_rtl_str(txt)
            t_type0 = round(pst + (0.14 if pidx == 0 else 0.02), 3)
            type_dur = float(ph.get("type_dur", min(1.05, max(0.42, (pen - t_type0) * 0.34))))
            t_type1 = round(min(pen - 0.16, t_type0 + type_dur), 3)

            if t_type0 > 0.08:
                cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/opacity", "time": round(max(0.0, t_type0 - 0.08), 3), "timeBase": "comp", "value": 0.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/opacity", "time": round(max(0.0, t_type0 - 0.02), 3), "timeBase": "comp", "value": 100.0}})

            indices = [i for i, ch in enumerate(txt, 1) if not ch.isspace()]
            if not indices or indices[-1] != len(txt):
                indices.append(len(txt))
            span = max(0.28, t_type1 - t_type0)
            for s_idx, c_end in enumerate(indices, 1):
                tk = round(t_type0 + (s_idx / float(len(indices))) * span, 3)
                sub = txt[:c_end]
                cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "text/sourceText", "time": tk, "timeBase": "comp", "value": sub}})
                w_sub = _measure_text_width_px(sub, font_family, fsize, rtl)
                off_x = (w_sub * 0.5) + 16.0
                cx_cur = round(pos[0] - off_x if rtl else pos[0] + off_x, 1)
                cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/position", "time": tk, "timeBase": "comp", "value": [cx_cur, cur_y, 0.0]}})

            b1 = round(min(pen - 0.14, t_type1 + 0.16), 3)
            b2 = round(min(pen - 0.08, t_type1 + 0.34), 3)
            b3 = round(min(pen - 0.04, t_type1 + 0.52), 3)
            if b3 > t_type1 + 0.05:
                cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/opacity", "time": round(t_type1 + 0.02, 3), "timeBase": "comp", "value": 100.0}})
                cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/opacity", "time": b1, "timeBase": "comp", "value": 15.0}})
                cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/opacity", "time": b2, "timeBase": "comp", "value": 90.0}})
                cmds.append({"command": "prop.addKey", "params": {"layer": cur_name, "path": "transform/opacity", "time": b3, "timeBase": "comp", "value": 0.0}})


# 7. VFX Compiler
class VFXCompiler:
    """Applies verified 3D Lights, Light Sweeps, Glow (clamped on light stages), Blur, Distortion, and Particles."""

    def compile(self, ctx: CompileContext) -> None:
        lighting = ctx.scene_graph.get("lighting") or {}
        if lighting.get("enabled"):
            for lgt in lighting.get("lights", []):
                lname = str(lgt.get("name", "KeySpot"))
                lkind = str(lgt.get("kind", "Spot"))
                params: Dict[str, Any] = {
                    "kind": lkind,
                    "name": lname,
                    "color": lgt.get("color", "#FFFFFF"),
                    "intensity": float(lgt.get("intensity", 120.0)),
                    "castsShadows": bool(lgt.get("castsShadows", False)),
                }
                if lkind == "Spot":
                    params["coneAngle"] = float(lgt.get("coneAngle", 88.0))
                    params["coneFeather"] = float(lgt.get("coneFeather", 60.0))
                ctx.commands.append({"command": "layer.newLight", "params": params})
                for k in lgt.get("keyframes", []):
                    kt = float(k["time"])
                    ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": kt, "timeBase": "comp", "value": k["pos"]}})
                    if k.get("poi"):
                        ctx.commands.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/poi", "time": kt, "timeBase": "comp", "value": k["poi"]}})

        for vidx, fx in enumerate(ctx.scene_graph.get("vfx", [])):
            ftype = str(fx.get("type", "")).lower()
            st = max(0.0, float(fx.get("start", fx.get("time", 0.0))))
            en = min(ctx.duration, float(fx.get("end", ctx.duration)))
            if en <= st:
                en = min(ctx.duration, st + 1.0)

            if ftype == "particles":
                pname = f"VFX_Particles_{vidx}"
                ctx.commands.append({"command": "layer.newSolid", "params": {"name": pname, "color": "#000000", "width": ctx.width, "height": ctx.height}})
                ctx.commands.append({"command": "layer.setBlendMode", "params": {"layers": [pname], "mode": "Screen"}})
                ctx.commands.append({"command": "layer.timing", "params": {"layers": [pname], "in": st, "out": en}})
                ctx.commands.append({"command": "effect.apply", "params": {"layer": pname, "effect": "ec.sim.ccparticlesystems2"}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": pname, "path": "effects/#1/birthRate", "value": float(fx.get("birth_rate", 6.0))}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": pname, "path": "effects/#1/physics/velocity", "value": float(fx.get("velocity", 1.8))}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": pname, "path": "effects/#1/physics/gravity", "value": float(fx.get("gravity", -0.05))}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": pname, "path": "effects/#1/particle/particleType", "value": 2}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": pname, "path": "effects/#1/particle/birthColor", "value": _hex_to_rgba_float(str(fx.get("color", "#00D4C0")))}})
                p_op = float(fx.get("opacity", 18.0))
                ctx.commands.append({"command": "prop.set", "params": {"layer": pname, "path": "effects/#1/particle/maxOpacity", "value": p_op}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": pname, "path": "transform/opacity", "value": min(28.0, p_op * 1.4)}})
                continue

            target = fx.get("target")
            if not target:
                continue
            ctx.fx_counter[target] = ctx.fx_counter.get(target, 0) + 1
            fx_slot = f"effects/#{ctx.fx_counter[target]}"
            if ftype in ("light sweep", "light_sweep"):
                ctx.commands.append({"command": "effect.apply", "params": {"layers": [target], "effect": "ec.generate.cclightsweep"}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/sweepIntensity", "value": float(fx.get("intensity", 24.0))}})
                if "width" in fx and fx["width"] is not None:
                    ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/width", "value": float(fx["width"])}})
                if "color" in fx and fx["color"]:
                    ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/lightColor", "value": _hex_to_rgba_float(str(fx["color"]))}})
                # Local bounds if target is resolved raster asset
                aid_key = target[len("Asset_"):] if target.startswith("Asset_") else ""
                ra = ctx.resolved_assets.get(aid_key, {})
                lw = float(ra.get("width", ctx.width * 0.6))
                lh = float(ra.get("height", ctx.height * 0.6))
                t_m = float(fx.get("time", st))
                sweep_dur = max(0.25, float(fx.get("duration", 0.65)))
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": target, "path": f"{fx_slot}/center", "time": t_m, "timeBase": "comp", "value": [-60.0, lh * 0.5]}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": target, "path": f"{fx_slot}/center", "time": round(min(en, t_m + sweep_dur), 3), "timeBase": "comp", "value": [lw + 60.0, lh * 0.5]}})
            elif ftype == "drop_shadow":
                ctx.commands.append({"command": "effect.apply", "params": {"layers": [target], "effect": "ec.perspective.dropshadow"}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/opacity", "value": float(fx.get("opacity", 55.0))}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/distance", "value": float(fx.get("distance", 16.0))}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/softness", "value": float(fx.get("softness", 34.0))}})
            elif ftype == "radio_waves":
                ctx.commands.append({"command": "effect.apply", "params": {"layers": [target], "effect": "ec.generate.radiowaves"}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/waveMotion/frequency", "value": float(fx.get("frequency", 1.3))}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/waveMotion/expansion", "value": float(fx.get("expansion", 140.0))}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/waveStroke/color", "value": _hex_to_rgba_float(str(fx.get("color", "#38BDF8")))}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/waveStroke/opacity", "value": 65.0}})
            elif ftype == "blur":
                ctx.commands.append({"command": "effect.apply", "params": {"layers": [target], "effect": "ec.blur.gaussian"}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": target, "path": f"{fx_slot}/blurriness", "time": st, "timeBase": "comp", "value": float(fx.get("from_blur", 32.0))}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": target, "path": f"{fx_slot}/blurriness", "time": round(min(en, st + 0.55), 3), "timeBase": "comp", "value": float(fx.get("to_blur", 0.0))}})
            elif ftype == "distortion":
                ctx.commands.append({"command": "effect.apply", "params": {"layers": [target], "effect": "ec.distort.turbulentdisplace"}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": target, "path": f"{fx_slot}/amount", "time": st, "timeBase": "comp", "value": float(fx.get("amount", 35.0))}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": target, "path": f"{fx_slot}/amount", "time": round(min(en, st + 0.5), 3), "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": target, "path": f"{fx_slot}/evolution", "time": st, "timeBase": "comp", "value": 0.0}})
                ctx.commands.append({"command": "prop.addKey", "params": {"layer": target, "path": f"{fx_slot}/evolution", "time": round(min(en, st + 0.5), 3), "timeBase": "comp", "value": 180.0}})
            elif ftype == "glow":
                ctx.commands.append({"command": "effect.apply", "params": {"layers": [target], "effect": "ec.stylize.glow"}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/intensity", "value": min(0.95, float(fx.get("intensity", 0.7)))}})
                ctx.commands.append({"command": "prop.set", "params": {"layer": target, "path": f"{fx_slot}/radius", "value": float(fx.get("radius", 32.0))}})


# 8. Audio Cue Compiler
class AudioCueCompiler:
    """Synthesizes & mixes ZERO-BGM RMS-ducked studio SFX onto clean voiceover without truncation."""

    def compile_audio(self, ctx: CompileContext, voice_wav: Optional[Path], out_wav: Path) -> Optional[Path]:
        if voice_wav and voice_wav.is_file():
            raw_cues = ctx.scene_graph.get("sfx", [])
            norm_cues: List[Dict[str, Any]] = []
            for c in raw_cues:
                if "gain_db" in c:
                    gain_db = float(c["gain_db"])
                else:
                    g_lin = max(0.02, float(c.get("gain", 0.28)))
                    gain_db = max(-22.0, min(-6.0, round(20.0 * math.log10(g_lin), 2)))
                entry: Dict[str, Any] = {
                    "file": str(c.get("cue") or c.get("file") or "pop"),
                    "time": float(c.get("time", 0.0)),
                    "gain_db": gain_db,
                }
                if "pan" in c:
                    entry["pan"] = float(c["pan"])
                if "max_duration" in c:
                    entry["max_duration"] = float(c["max_duration"])
                norm_cues.append(entry)

            mix_scene_graph_audio(voice_wav, norm_cues, out_wav)
            ctx.mixed_audio_path = out_wav
            return ctx.mixed_audio_path
        # Generate silent WAV for pure silent visual graphics tests if requested (48kHz broadcast standard)
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        n_frames = max(1, int(round(ctx.duration * 48000)))
        with wave.open(str(out_wav), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00\x00" * n_frames)
        ctx.mixed_audio_path = out_wav
        return out_wav


# 9. EffectCraft Project Builder
class EffectCraftProjectBuilder:
    """Writes & executes EffectCraft CLI commands and persists an editable `.ecproj`."""

    def build_project(
        self,
        ctx: CompileContext,
        out_ecproj: Path,
        *,
        use_gpu: bool = False,
    ) -> Tuple[bool, str]:
        cli = find_effectcraft_cli()
        if cli is None:
            return False, "effectcraft-cli.exe not found"

        out_ecproj.parent.mkdir(parents=True, exist_ok=True)
        head_cmds: List[Dict[str, Any]] = []

        # Optional nested precomp badge if requested in scene_graph
        nested = ctx.scene_graph.get("nested_badge")
        if nested:
            inner_name = str(nested.get("comp_name", "NestedEmblem"))
            head_cmds.append({
                "command": "comp.new",
                "params": {"name": inner_name, "width": 520, "height": 220, "frameRate": ctx.fps, "duration": ctx.duration, "background": "#000000"},
            })
            head_cmds.append({
                "command": "layer.newShape",
                "params": {"kind": "rounded", "name": "NestedFrame", "size": [480, 170], "fill": nested.get("fill", "#162033"), "stroke": nested.get("stroke", "#FFD400"), "strokeWidth": 4, "position": [260, 110]},
            })
            head_cmds.append({
                "command": "layer.newText",
                "params": {"name": "NestedTitle", "text": str(nested.get("text", "AION V5")), "font": "Cairo", "style": "Bold", "size": 40, "fill": "#FFFFFF", "direction": "rtl" if is_rtl_text(str(nested.get("text", ""))) else "ltr", "justify": "center", "position": [260, 122]},
            })

        # Main composition
        head_cmds.append({
            "command": "comp.new",
            "params": {
                "name": ctx.comp_name,
                "width": ctx.width,
                "height": ctx.height,
                "frameRate": ctx.fps,
                "duration": ctx.duration,
                "background": ctx.scene_graph.get("composition", {}).get("bg_color", "#0F172A"),
            },
        })

        all_cmds = head_cmds + list(ctx.commands)
        if ctx.ease_keys:
            all_cmds.append({"command": "keys.select", "params": {"keys": ctx.ease_keys}})
            all_cmds.append({"command": "keys.easyEase", "params": {"which": "both"}})
        if nested:
            npos = nested.get("position", [ctx.width - 250, 110])
            nscale = float(nested.get("scale", 62.0))
            all_cmds.append({"command": "layer.addItem", "params": {"item": inner_name, "position": npos, "in": 0.0, "out": ctx.duration}})
            all_cmds.append({"command": "prop.addKey", "params": {"layer": inner_name, "path": "transform/scale", "time": 0.0, "timeBase": "comp", "value": [25, 25, 100]}})
            all_cmds.append({"command": "prop.addKey", "params": {"layer": inner_name, "path": "transform/scale", "time": 0.45, "timeBase": "comp", "value": [nscale, nscale, 100]}})

        if ctx.mixed_audio_path and ctx.mixed_audio_path.is_file():
            all_cmds.append({"command": "file.import", "params": {"paths": [ctx.mixed_audio_path.resolve().as_posix()], "addToComp": True}})

        all_cmds.append({"command": "file.saveAs", "params": {"path": out_ecproj.resolve().as_posix()}})

        cmd_file = ctx.work_dir / f"{ctx.comp_name}_ecgc_commands.json"
        cmd_file.parent.mkdir(parents=True, exist_ok=True)
        cmd_file.write_text(json.dumps(all_cmds, ensure_ascii=False, indent=2), encoding="utf-8")

        cmd = [str(cli)]
        if use_gpu:
            cmd.append("--gpu")
        cmd.extend(["--empty", "run", "--commands", str(cmd_file), "--json"])
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90, env=get_effectcraft_subprocess_env())
        if res.returncode != 0 or not out_ecproj.is_file():
            return False, (res.stderr or res.stdout)[:800]
        return True, "ok"


# 10. Render Validator
def resolve_effectcraft_resolution(resolution: str = "720p") -> str:
    """Map user/CLI resolution tokens (`720p`, `1080p`, `full`, ...) to EffectCraft `--resolution` values."""
    val = str(resolution or "720p").strip().lower()
    if val in ("720p", "720", "hd"):
        # Canonical 1920x1080 * 2/3 = 1280x720, and 1080x1920 * 2/3 = 720x1280
        return "0.6666667"
    if val in ("1080p", "1080", "fhd", "full"):
        return "full"
    return str(resolution)


class RenderValidator:
    """Renders preview PNG frames or full MP4, validates `expr.errors` and `ffprobe` streams."""

    def render_preview_frames(
        self,
        ecproj: Path,
        comp_name: str,
        duration: float,
        preview_dir: Path,
        *,
        sample_count: int = 4,
        max_side: int = 960,
        use_gpu: bool = False,
    ) -> List[Path]:
        cli = find_effectcraft_cli()
        if cli is None:
            raise FileNotFoundError("effectcraft-cli.exe not found")
        preview_dir.mkdir(parents=True, exist_ok=True)
        times = [
            round(min(max(0.05, duration - 0.05), (i + 0.5) * duration / max(1, sample_count)), 3)
            for i in range(sample_count)
        ]
        frames: List[Path] = []
        for idx, t in enumerate(times):
            out_png = preview_dir / f"preview_{idx:02d}_{t:.2f}s.png"
            cmd = [str(cli)]
            if use_gpu:
                cmd.append("--gpu")
            cmd.extend([
                "--project",
                str(ecproj),
                "render-frame",
                "--comp",
                comp_name,
                "--time",
                f"{t:.3f}",
                "--max-side",
                str(max_side),
                "--out",
                str(out_png),
            ])
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45, env=get_effectcraft_subprocess_env())
            if res.returncode == 0 and out_png.is_file():
                frames.append(out_png)
        return frames

    def render_mp4(
        self,
        ecproj: Path,
        comp_name: str,
        fps: int,
        duration: float,
        out_mp4: Path,
        *,
        use_gpu: bool = True,
        audio_on: bool = True,
        resolution: str = "720p",
    ) -> Tuple[bool, Dict[str, Any]]:
        cli = find_effectcraft_cli()
        if cli is None:
            return False, {"error": "effectcraft-cli.exe not found"}
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        ec_res = resolve_effectcraft_resolution(resolution)
        cmd = [str(cli), "--project", str(ecproj)]
        if use_gpu:
            cmd.append("--gpu")
        cmd.extend([
            "render",
            "--comp",
            comp_name,
            "--out",
            str(out_mp4),
            "--fps",
            str(fps),
            "--start",
            "0",
            "--end",
            f"{duration:.3f}",
            "--resolution",
            ec_res,
            "--audio",
            "on" if audio_on else "off",
            "--bitrate",
            "8500",
        ])
        ec_env = get_effectcraft_subprocess_env()
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=420, env=ec_env)
        if (res.returncode != 0 or not out_mp4.is_file()) and use_gpu:
            # Explicit non-silent GPU->CPU fallback recorded in report
            cpu_cmd = [x for x in cmd if x != "--gpu"]
            res = subprocess.run(cpu_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, env=ec_env)
            used_gpu = False
        else:
            used_gpu = use_gpu

        # Check expressions
        expr_proc = subprocess.run([str(cli), "--project", str(ecproj), "exec", "expr.errors", "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ec_env)
        expr_errors: List[Any] = []
        try:
            expr_errors = json.loads(expr_proc.stdout).get("errors", [])
        except Exception:
            pass

        ffp = {}
        if out_mp4.is_file():
            pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "json", str(out_mp4)], capture_output=True, text=True)
            if pr.returncode == 0:
                try:
                    ffp = json.loads(pr.stdout)
                except Exception:
                    pass
        return (res.returncode == 0 and out_mp4.is_file()), {
            "used_gpu": used_gpu,
            "expr_errors": expr_errors,
            "ffprobe": ffp,
            "stderr": res.stderr[:500],
        }


class CreativeGraphicsCompiler:
    """Orchestrates all 10 ECGC modules cleanly from V2 Scene Graph to `.ecproj` + frames/MP4."""

    def __init__(self, cap_path: Path = DEFAULT_CAPABILITIES_PATH):
        self.validator = SceneGraphValidator()
        self.cap_resolver = CapabilityResolver(cap_path)
        self.asset_resolver = AssetResolver()
        self.vector_builder = VectorGeometryBuilder()
        self.timeline_compiler = MotionTimelineCompiler()
        self.typo_compiler = TypographyCompiler()
        self.vfx_compiler = VFXCompiler()
        self.audio_compiler = AudioCueCompiler()
        self.project_builder = EffectCraftProjectBuilder()
        self.render_validator = RenderValidator()

    def compile_scene(
        self,
        raw_scene_graph: Dict[str, Any],
        *,
        section_dir: Path,
        work_dir: Path,
        out_ecproj: Path,
        out_mp4: Optional[Path] = None,
        voice_wav: Optional[Path] = None,
        preview_only: bool = False,
        use_gpu: bool = True,
        resolution: str = "720p",
    ) -> Dict[str, Any]:
        """Run full 10-stage ECGC compile and write `compile_report.json`."""
        t0 = time.time()
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        sg, issues = self.validator.validate(raw_scene_graph)
        comp_meta = sg.get("composition", {})
        res = comp_meta.get("resolution", [1920, 1080])
        dur = float(sg.get("source_timeline", {}).get("duration_sec") or sg.get("total_duration") or 5.0)
        ctx = CompileContext(
            scene_graph=sg,
            section_dir=Path(section_dir),
            work_dir=work_dir,
            comp_name=str(sg.get("project_id") or sg.get("section_id") or "AION_Studio_V5"),
            width=int(res[0]),
            height=int(res[1]),
            fps=int(comp_meta.get("fps") or sg.get("fps") or 24),
            duration=dur,
            validation_issues=issues,
        )

        # Stages 2..8
        self.cap_resolver.resolve(ctx)
        self.asset_resolver.resolve(ctx)
        self.vector_builder.build_stage_and_vectors(ctx)
        self.timeline_compiler.compile(ctx)
        self.typo_compiler.compile(ctx)
        self.vfx_compiler.compile(ctx)

        mixed_wav = work_dir / f"{ctx.comp_name}_mixed_audio.wav"
        if voice_wav is None:
            cand_audio = ctx.section_dir / str(sg.get("source_timeline", {}).get("audio_file", ""))
            if cand_audio.is_file():
                voice_wav = cand_audio
        self.audio_compiler.compile_audio(ctx, voice_wav, mixed_wav)

        # Stage 9: Build & persist .ecproj
        built, build_msg = self.project_builder.build_project(ctx, out_ecproj, use_gpu=False)
        if not built:
            return {"ok": False, "stage": "project_build", "error": build_msg}

        # Stage 10: Preview PNGs + Optional MP4 Render
        preview_dir = work_dir / "preview_frames"
        preview_frames = self.render_validator.render_preview_frames(
            out_ecproj, ctx.comp_name, ctx.duration, preview_dir, sample_count=4, use_gpu=False
        )
        render_meta: Dict[str, Any] = {}
        ok_render = True
        if not preview_only and out_mp4 is not None:
            ok_render, render_meta = self.render_validator.render_mp4(
                out_ecproj, ctx.comp_name, ctx.fps, ctx.duration, out_mp4, use_gpu=use_gpu, resolution=resolution
            )

        report = {
            "ok": bool(built and ok_render),
            "schema_version": SCENE_GRAPH_V2,
            "ecproj": str(out_ecproj),
            "mp4": str(out_mp4) if out_mp4 and not preview_only else None,
            "preview_frames": [str(p) for p in preview_frames],
            "capabilities_used": ctx.resolved_capabilities,
            "fallbacks_applied": ctx.fallbacks_applied,
            "quality_impacts": ctx.quality_impacts,
            "validation_issues": ctx.validation_issues,
            "render_meta": render_meta,
            "elapsed_sec": round(time.time() - t0, 2),
        }
        (work_dir / "compile_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return report

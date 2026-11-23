"""
Step 2 of 24s Cinematic Master Production in EffectCraft (Polished Pro AE Edition):
Produces a 1920x1080 @ 25fps (600 frames = 24.00s Seamless Loop) showcase combining:
- PhotoCraft-sharpened 2x AniCraft character sequence (Character_Motion_Project_v4)
- True GPU Gaussian Blur studio spotlights & floor shadows (zero hard circular edges)
- Strict layer.timing isolation for HUD section titles (zero overlapping text)
- 100% procedural vector VFX, Trim Paths icons (Magnifier w/ transparent lens & handle,
  Evidence cards w/ labels, Neural network w/ pulsing nodes, Heartbeat ECG + Fractures,
  Full Lightbulb w/ filament & clean neck/base, Fountain Pen Signature + Seamless Loop Ring)
- Synchronized muxing with master_audio_24s.wav + 12-panel inspection sheet.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
EC_CLI = ROOT / "craftApp" / "effectcraft" / "target" / "release" / "effectcraft-cli.exe"
WORK_DIR = ROOT / "creative_v3" / "renders" / "cine_master_24s"
SEQ_HD_DIR = WORK_DIR / "char_seq_hd"
AUDIO_WAV = WORK_DIR / "master_audio_24s.wav"

W, H = 1920, 1080
FPS = 25
DURATION = 24.0


def cmd(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    return {"command": command, "params": params}


def key(layer: str, path: str, time: float, value: Any) -> Dict[str, Any]:
    return cmd("prop.addKey", {
        "layer": layer,
        "path": path,
        "time": round(time, 4),
        "value": value,
    })


def set_prop(layer: str, path: str, value: Any) -> Dict[str, Any]:
    return cmd("prop.set", {"layer": layer, "path": path, "value": value})


def add_gaussian_blur(cmds: List[Dict[str, Any]], layer: str, radius: float) -> None:
    cmds.append(cmd("effect.apply", {"effect": "Gaussian Blur", "layers": [layer]}))
    cmds.append(set_prop(layer, "effects/#1/blurriness", float(radius)))
    cmds.append(set_prop(layer, "effects/#1/repeatEdge", False))


def add_fade_window(
    cmds: List[Dict[str, Any]],
    layer: str,
    t0: float,
    t1: float,
    fade: float = 0.25,
    peak: float = 100.0,
) -> None:
    cmds.append(cmd("layer.timing", {"layers": [layer], "in": max(0.0, t0), "out": min(DURATION, t1)}))
    cmds.append(key(layer, "transform/opacity", max(0.0, t0), 0.0))
    cmds.append(key(layer, "transform/opacity", min(t1, t0 + fade), peak))
    cmds.append(key(layer, "transform/opacity", max(t0 + fade, t1 - fade), peak))
    if t1 < DURATION:
        cmds.append(key(layer, "transform/opacity", t1, 0.0))


def make_trim_path(
    cmds: List[Dict[str, Any]],
    name: str,
    vertices: List[List[float]],
    stroke: List[float],
    stroke_w: float,
    t_draw0: float,
    t_draw1: float,
    t_hide: float,
    closed: bool = False,
    t_show: float | None = None,
) -> None:
    if t_show is None:
        t_show = max(0.0, t_draw0 - 0.05)
    cmds.append(cmd("layer.newShape", {"name": name, "kind": "none"}))
    cmds.append(set_prop(name, "transform/position", [0.0, 0.0]))
    cmds.append(cmd("shape.newPath", {
        "layer": name,
        "vertices": vertices,
        "closed": closed,
        "fill": False,
        "stroke": stroke,
        "strokeWidth": stroke_w,
    }))
    cmds.append(cmd("layer.addShapeItem", {"layer": name, "kind": "trim"}))
    cmds.append(key(name, "contents/trim/start", max(0.0, t_show), 0.0))
    cmds.append(key(name, "contents/trim/end", max(0.0, t_show), 0.0))
    cmds.append(key(name, "contents/trim/end", t_draw0, 0.0))
    cmds.append(key(name, "contents/trim/end", t_draw1, 100.0))
    add_fade_window(cmds, name, t_show, t_hide, fade=0.18, peak=100.0)


def build_commands() -> List[Dict[str, Any]]:
    cmds: List[Dict[str, Any]] = [
        cmd("comp.new", {"name": "CineMaster_24s", "width": W, "height": H, "fps": FPS, "duration": DURATION}),
        cmd("layer.newSolid", {"name": "BG_Base", "color": [0.042, 0.062, 0.105, 1.0], "width": W, "height": H}),
    ]

    # True GPU-blurred Studio Spotlights (smooth falloff, ZERO hard circular rims!)
    glow_specs = [
        ("Glow_Hook_Cyan", [0.10, 0.48, 0.88], [920.0, 920.0], [960.0, 520.0], [(0.0, 4.2, 48.0), (8.0, 12.2, 54.0)]),
        ("Glow_Evidence_Amber", [0.85, 0.56, 0.18], [880.0, 880.0], [1200.0, 500.0], [(4.0, 8.2, 40.0), (20.0, 24.0, 38.0)]),
        ("Glow_Tension_Crimson", [0.86, 0.09, 0.14], [1050.0, 1050.0], [960.0, 540.0], [(12.0, 16.05, 62.0)]),
        ("Glow_Climax_Gold", [1.0, 0.78, 0.22], [1050.0, 1050.0], [1050.0, 460.0], [(16.0, 20.3, 62.0)]),
    ]
    for gname, gcol, gsz, gpos, gwins in glow_specs:
        cmds.append(cmd("layer.newShape", {
            "name": gname, "kind": "ellipse", "size": gsz,
            "fill": gcol, "fillOpacity": 100.0, "position": gpos,
        }))
        add_gaussian_blur(cmds, gname, 220.0)
        cmds.append(key(gname, "transform/opacity", 0.0, 0.0))
        for t0, t1, peak in gwins:
            cmds.append(key(gname, "transform/opacity", max(0.0, t0 - 0.15), 0.0))
            cmds.append(key(gname, "transform/opacity", t0 + 0.40, peak))
            cmds.append(key(gname, "transform/opacity", max(t0 + 0.40, t1 - 0.40), peak))
            if t1 < DURATION:
                cmds.append(key(gname, "transform/opacity", t1, 0.0))

    # Subtle Vector Blueprint Grid
    cmds.append(cmd("layer.newShape", {"name": "BG_Grid", "kind": "none"}))
    cmds.append(set_prop("BG_Grid", "transform/position", [0.0, 0.0]))
    for gx in range(160, W, 160):
        cmds.append(cmd("shape.newPath", {
            "layer": "BG_Grid", "vertices": [[float(gx), 80.0], [float(gx), 990.0]],
            "closed": False, "fill": False, "stroke": [0.35, 0.65, 0.95], "strokeOpacity": 7.0, "strokeWidth": 1.5,
        }))
    for gy in range(180, H, 180):
        cmds.append(cmd("shape.newPath", {
            "layer": "BG_Grid", "vertices": [[80.0, float(gy)], [1840.0, float(gy)]],
            "closed": False, "fill": False, "stroke": [0.35, 0.65, 0.95], "strokeOpacity": 7.0, "strokeWidth": 1.5,
        }))

    # Master Camera Null
    cmds.append(cmd("layer.newNull", {"name": "Cam_Master"}))
    cmds.append(set_prop("Cam_Master", "transform/position", [960.0, 540.0]))
    cmds.append(set_prop("Cam_Master", "transform/anchor", [0.0, 0.0]))

    stage_layers: List[str] = ["BG_Grid"]

    # =========================================================================
    # CHARACTER RIG LAYER + SOFT STUDIO FLOOR SHADOW
    # =========================================================================
    cmds.append(cmd("layer.newShape", {
        "name": "Char_Shadow", "kind": "ellipse", "size": [250.0, 38.0],
        "fill": [0.01, 0.015, 0.03], "fillOpacity": 100.0, "position": [960.0, 862.0],
    }))
    add_gaussian_blur(cmds, "Char_Shadow", 24.0)
    cmds.append(set_prop("Char_Shadow", "transform/opacity", 65.0))
    stage_layers.append("Char_Shadow")

    first_frame = SEQ_HD_DIR / "frame_00001.png"
    cmds.append(cmd("file.import", {"paths": [str(first_frame)], "sequence": True, "frameRate": 25.0, "addToComp": True}))
    cmds.append(cmd("layer.rename", {"name": "Char_Master_Seq"}))
    cmds.append(set_prop("Char_Master_Seq", "transform/scale", [68.0, 68.0]))
    cmds.append(set_prop("Char_Master_Seq", "transform/position", [960.0, 565.0]))
    stage_layers.append("Char_Master_Seq")

    # Story-driven character blocking (Rule of Thirds when explaining right cards, centered for drama & loop)
    char_xs = [
        (0.0, 960.0), (1.15, 960.0), (1.65, 600.0),          # Hook: shock center -> step left to point at card
        (3.85, 600.0), (4.20, 520.0), (7.80, 520.0),         # Evidence board: left anchor
        (8.20, 550.0), (11.75, 550.0),                       # Neuro X-Ray: left-center turnaround
        (12.20, 960.0), (15.95, 960.0),                      # Dark Tension: claustrophobic center
        (16.05, 720.0), (19.65, 720.0),                      # Climax: heroic jump & epiphany bulb on right
        (20.15, 620.0), (22.65, 620.0), (23.45, 960.0), (24.00, 960.0),  # Resolution: present card -> glide center for seamless loop
    ]
    for t, cx in char_xs:
        cmds.append(key("Char_Master_Seq", "transform/position", t, [cx, 565.0]))
        cmds.append(key("Char_Shadow", "transform/position", t, [cx, 862.0]))

    for t, sx, op in [(16.0, 100.0, 65.0), (16.45, 50.0, 28.0), (16.75, 42.0, 22.0), (17.25, 100.0, 65.0)]:
        cmds.append(key("Char_Shadow", "transform/scale", t, [sx, sx]))
        cmds.append(key("Char_Shadow", "transform/opacity", t, op))

    # =========================================================================
    # SECTION 1 (0.00 - 4.00s): HOOK — Shockwaves + Question Card + Trim "?"
    # =========================================================================
    for idx, (r0, r1, t_start, t_end, col) in enumerate([
        (60.0, 740.0, 0.0, 0.90, [0.22, 0.78, 1.0]),
        (40.0, 520.0, 0.12, 1.00, [0.95, 0.85, 0.35]),
    ]):
        sname = f"Hook_Shockwave_{idx}"
        cmds.append(cmd("layer.newShape", {
            "name": sname, "kind": "ellipse", "size": [100.0, 100.0],
            "fillType": "none", "stroke": col, "strokeWidth": 6.0, "position": [960.0, 520.0],
        }))
        cmds.append(cmd("layer.timing", {"layers": [sname], "in": t_start, "out": t_end}))
        cmds.append(key(sname, "transform/scale", t_start, [r0, r0]))
        cmds.append(key(sname, "transform/scale", t_end, [r1, r1]))
        cmds.append(key(sname, "transform/opacity", t_start, 90.0))
        cmds.append(key(sname, "transform/opacity", t_end, 0.0))
        stage_layers.append(sname)

    cmds.append(cmd("layer.newShape", {
        "name": "Hook_Card", "kind": "rounded", "size": [540.0, 430.0],
        "fill": [0.06, 0.10, 0.18], "fillOpacity": 88.0, "stroke": [0.24, 0.72, 0.98],
        "strokeWidth": 3.0, "position": [1380.0, 520.0],
    }))
    add_fade_window(cmds, "Hook_Card", 1.30, 4.00, fade=0.22)
    cmds.append(key("Hook_Card", "transform/scale", 1.30, [86.0, 86.0]))
    cmds.append(key("Hook_Card", "transform/scale", 1.62, [100.0, 100.0]))
    stage_layers.append("Hook_Card")

    make_trim_path(
        cmds, "Hook_QMark_Curve",
        vertices=[[1320.0, 405.0], [1380.0, 345.0], [1445.0, 395.0], [1385.0, 475.0], [1385.0, 535.0]],
        stroke=[0.30, 0.86, 1.0], stroke_w=14.0,
        t_draw0=1.50, t_draw1=2.30, t_hide=4.00,
    )
    stage_layers.append("Hook_QMark_Curve")
    cmds.append(cmd("layer.newShape", {
        "name": "Hook_QMark_Dot", "kind": "ellipse", "size": [22.0, 22.0],
        "fill": [1.0, 0.82, 0.26], "position": [1385.0, 580.0],
    }))
    add_fade_window(cmds, "Hook_QMark_Dot", 2.25, 4.00, fade=0.15)
    stage_layers.append("Hook_QMark_Dot")

    cmds.append(cmd("layer.newText", {
        "name": "Hook_Card_Label", "text": "WHY DO PATTERNS BREAK?", "size": 24.0,
        "fill": [0.88, 0.95, 1.0], "position": [1380.0, 665.0], "justify": "center",
    }))
    add_fade_window(cmds, "Hook_Card_Label", 2.20, 4.00, fade=0.18)
    stage_layers.append("Hook_Card_Label")

    # =========================================================================
    # SECTION 2 (4.00 - 8.00s): IMMERSION — Evidence Board + Strings + Magnifier
    # =========================================================================
    ev_cards = [
        ("Ev_Card_1", "CLUE 01 // TRIGGER", [1050.0, 345.0], -3.0, 4.20, [0.96, 0.30, 0.32]),
        ("Ev_Card_2", "CLUE 02 // ROUTINE", [1510.0, 395.0], 2.5, 4.85, [0.28, 0.78, 0.96]),
        ("Ev_Card_3", "CLUE 03 // REWARD LOOP", [1270.0, 695.0], -1.5, 5.55, [1.0, 0.76, 0.25]),
    ]
    for cname, clabel, cpos, crot, t_in, cstroke in ev_cards:
        cmds.append(cmd("layer.newShape", {
            "name": cname, "kind": "rounded", "size": [340.0, 210.0],
            "fill": [0.08, 0.12, 0.19], "fillOpacity": 92.0, "stroke": cstroke, "strokeWidth": 3.0, "position": cpos,
        }))
        cmds.append(set_prop(cname, "transform/rotation", crot))
        add_fade_window(cmds, cname, t_in, 8.00, fade=0.22)
        cmds.append(key(cname, "transform/scale", t_in, [82.0, 82.0]))
        cmds.append(key(cname, "transform/scale", t_in + 0.28, [100.0, 100.0]))
        stage_layers.append(cname)

        # Card label text inside each evidence card
        tname = f"{cname}_Txt"
        cmds.append(cmd("layer.newText", {
            "name": tname, "text": clabel, "size": 19.0,
            "fill": [0.92, 0.96, 1.0], "position": [cpos[0], cpos[1] - 28.0], "justify": "center",
        }))
        cmds.append(set_prop(tname, "transform/rotation", crot))
        add_fade_window(cmds, tname, t_in + 0.08, 8.00, fade=0.18)
        stage_layers.append(tname)

        # Simulated evidence lines inside card
        lname = f"{cname}_Lines"
        make_trim_path(
            cmds, lname,
            vertices=[[cpos[0] - 110.0, cpos[1] + 22.0], [cpos[0] + 110.0, cpos[1] + 22.0]],
            stroke=cstroke, stroke_w=3.0,
            t_draw0=t_in + 0.15, t_draw1=t_in + 0.55, t_hide=8.00, t_show=t_in + 0.10,
        )
        stage_layers.append(lname)

        pname = f"{cname}_Pin"
        cmds.append(cmd("layer.newShape", {
            "name": pname, "kind": "ellipse", "size": [20.0, 20.0],
            "fill": [0.96, 0.22, 0.24], "position": [cpos[0], cpos[1] - 88.0],
        }))
        add_fade_window(cmds, pname, t_in + 0.1, 8.00, fade=0.16)
        stage_layers.append(pname)

    make_trim_path(
        cmds, "Ev_Red_Strings",
        vertices=[[1050.0, 257.0], [1510.0, 307.0], [1270.0, 607.0], [1050.0, 257.0]],
        stroke=[0.96, 0.24, 0.26], stroke_w=3.5,
        t_draw0=5.10, t_draw1=6.75, t_hide=8.00,
    )
    stage_layers.append("Ev_Red_Strings")

    # Pro Magnifying Glass: transparent glass center (fillOpacity: 16%) + rim + handle
    cmds.append(cmd("layer.newShape", {
        "name": "Ev_Magnifier", "kind": "ellipse", "size": [155.0, 155.0],
        "fill": [0.40, 0.88, 1.0], "fillOpacity": 16.0, "stroke": [0.78, 0.94, 1.0], "strokeWidth": 7.0,
        "position": [1050.0, 345.0],
    }))
    add_fade_window(cmds, "Ev_Magnifier", 5.00, 7.90, fade=0.22)
    for t, mx, my in [(5.00, 1050.0, 345.0), (6.00, 1510.0, 395.0), (7.10, 1270.0, 695.0)]:
        cmds.append(key("Ev_Magnifier", "transform/position", t, [mx, my]))
    stage_layers.append("Ev_Magnifier")

    # Magnifier handle parented to Ev_Magnifier (do NOT re-parent to Cam_Master or it overrides Ev_Magnifier!)
    cmds.append(cmd("layer.newShape", {"name": "Ev_Mag_Handle", "kind": "none"}))
    cmds.append(set_prop("Ev_Mag_Handle", "transform/position", [0.0, 0.0]))
    cmds.append(cmd("shape.newPath", {
        "layer": "Ev_Mag_Handle", "vertices": [[1105.0, 400.0], [1175.0, 470.0]],
        "closed": False, "fill": False, "stroke": [0.78, 0.94, 1.0], "strokeWidth": 12.0,
    }))
    add_fade_window(cmds, "Ev_Mag_Handle", 5.00, 7.90, fade=0.22)
    cmds.append(cmd("layer.setParent", {"layers": ["Ev_Mag_Handle"], "parent": "Ev_Magnifier"}))

    # =========================================================================
    # SECTION 3 (8.00 - 12.00s): MECHANISM — MRI Sonar + Scanline + Neural Web
    # =========================================================================
    for r_idx, (t0, t1) in enumerate([(8.15, 9.60), (8.95, 10.60)]):
        rname = f"Neuro_MRI_Ring_{r_idx}"
        cmds.append(cmd("layer.newShape", {
            "name": rname, "kind": "ellipse", "size": [120.0, 120.0],
            "fillType": "none", "stroke": [0.18, 0.92, 0.88], "strokeWidth": 4.0, "position": [550.0, 350.0],
        }))
        cmds.append(cmd("layer.timing", {"layers": [rname], "in": t0, "out": t1}))
        cmds.append(key(rname, "transform/scale", t0, [40.0, 40.0]))
        cmds.append(key(rname, "transform/scale", t1, [420.0, 420.0]))
        cmds.append(key(rname, "transform/opacity", t0, 88.0))
        cmds.append(key(rname, "transform/opacity", t1, 0.0))
        stage_layers.append(rname)

    # Soft blurred glow under crisp vertical scanline
    cmds.append(cmd("layer.newShape", {
        "name": "Neuro_ScanGlow", "kind": "rect", "size": [48.0, 620.0],
        "fill": [0.18, 0.95, 0.92], "fillOpacity": 70.0, "position": [350.0, 550.0],
    }))
    add_gaussian_blur(cmds, "Neuro_ScanGlow", 26.0)
    add_fade_window(cmds, "Neuro_ScanGlow", 8.20, 11.40, fade=0.20, peak=65.0)
    for t, sx in [(8.25, 350.0), (9.45, 750.0), (10.60, 350.0), (11.35, 720.0)]:
        cmds.append(key("Neuro_ScanGlow", "transform/position", t, [sx, 550.0]))
    stage_layers.append("Neuro_ScanGlow")

    cmds.append(cmd("layer.newShape", {
        "name": "Neuro_ScanBar", "kind": "rect", "size": [6.0, 620.0],
        "fill": [0.75, 1.0, 0.98], "fillOpacity": 95.0, "position": [350.0, 550.0],
    }))
    add_fade_window(cmds, "Neuro_ScanBar", 8.20, 11.40, fade=0.20)
    for t, sx in [(8.25, 350.0), (9.45, 750.0), (10.60, 350.0), (11.35, 720.0)]:
        cmds.append(key("Neuro_ScanBar", "transform/position", t, [sx, 550.0]))
    stage_layers.append("Neuro_ScanBar")

    nodes = [
        [1040.0, 520.0], [1230.0, 330.0], [1240.0, 700.0],
        [1450.0, 430.0], [1470.0, 620.0], [1680.0, 520.0],
    ]
    synapses = [
        [nodes[0], nodes[1], nodes[3], nodes[5]],
        [nodes[0], nodes[2], nodes[4], nodes[5]],
        [nodes[1], nodes[4]], [nodes[2], nodes[3]],
    ]
    for s_idx, verts in enumerate(synapses):
        make_trim_path(
            cmds, f"Neuro_Synapse_{s_idx}", verts,
            stroke=[0.20, 0.94, 0.90], stroke_w=4.0,
            t_draw0=8.60 + s_idx * 0.25, t_draw1=10.20 + s_idx * 0.22, t_hide=12.00,
        )
        stage_layers.append(f"Neuro_Synapse_{s_idx}")

    for n_idx, npos in enumerate(nodes):
        nname = f"Neuro_Node_{n_idx}"
        cmds.append(cmd("layer.newShape", {
            "name": nname, "kind": "ellipse", "size": [38.0, 38.0],
            "fill": [0.18, 0.96, 0.92], "stroke": [0.88, 1.0, 1.0], "strokeWidth": 3.0,
            "position": npos,
        }))
        t_in = 8.50 + n_idx * 0.22
        add_fade_window(cmds, nname, t_in, 12.00, fade=0.20)
        cmds.append(key(nname, "transform/scale", t_in, [40.0, 40.0]))
        cmds.append(key(nname, "transform/scale", t_in + 0.3, [115.0, 115.0]))
        cmds.append(key(nname, "transform/scale", t_in + 0.55, [95.0, 95.0]))
        stage_layers.append(nname)

    cmds.append(cmd("layer.newText", {
        "name": "Neuro_Label", "text": "SYNAPTIC PATHWAY ACTIVATION", "size": 21.0,
        "fill": [0.40, 0.96, 0.94], "position": [1360.0, 240.0], "justify": "center",
    }))
    add_fade_window(cmds, "Neuro_Label", 8.60, 12.00, fade=0.22)
    stage_layers.append("Neuro_Label")

    # =========================================================================
    # SECTION 4 (12.00 - 16.00s): ESCALATION — Puppet Strings + ECG + Fractures
    # =========================================================================
    for st_idx, sx in enumerate([830.0, 910.0, 1010.0, 1090.0]):
        make_trim_path(
            cmds, f"Tension_String_{st_idx}",
            vertices=[[sx, 60.0], [sx, 500.0]],
            stroke=[0.95, 0.28, 0.30], stroke_w=2.5,
            t_draw0=12.15 + st_idx * 0.12, t_draw1=13.10 + st_idx * 0.12, t_hide=16.00,
        )
        stage_layers.append(f"Tension_String_{st_idx}")

    ecg_pts = [
        [240.0, 900.0], [420.0, 900.0], [450.0, 825.0], [480.0, 955.0], [510.0, 900.0],
        [720.0, 900.0], [745.0, 805.0], [770.0, 975.0], [795.0, 900.0],
        [1040.0, 900.0], [1060.0, 785.0], [1082.0, 985.0], [1102.0, 900.0],
        [1280.0, 900.0], [1298.0, 765.0], [1318.0, 995.0], [1338.0, 900.0],
        [1490.0, 900.0], [1508.0, 755.0], [1528.0, 995.0], [1680.0, 900.0],
    ]
    make_trim_path(
        cmds, "Tension_ECG_Wave", ecg_pts,
        stroke=[1.0, 0.24, 0.28], stroke_w=4.5,
        t_draw0=12.10, t_draw1=15.65, t_hide=16.00,
    )
    stage_layers.append("Tension_ECG_Wave")

    fractures = [
        [[180.0, 120.0], [440.0, 260.0], [620.0, 390.0]],
        [[1740.0, 140.0], [1480.0, 300.0], [1290.0, 420.0]],
        [[190.0, 820.0], [460.0, 680.0], [670.0, 600.0]],
        [[1730.0, 820.0], [1450.0, 680.0], [1250.0, 590.0]],
    ]
    for f_idx, fverts in enumerate(fractures):
        make_trim_path(
            cmds, f"Tension_Fracture_{f_idx}", fverts,
            stroke=[1.0, 0.88, 0.88], stroke_w=3.5,
            t_draw0=14.50 + f_idx * 0.14, t_draw1=15.40 + f_idx * 0.10, t_hide=16.02,
        )
        stage_layers.append(f"Tension_Fracture_{f_idx}")

    # =========================================================================
    # SECTION 5 (16.00 - 20.00s): CLIMAX — Flash + Sunburst + Detailed Full Bulb
    # =========================================================================
    cmds.append(cmd("layer.newSolid", {"name": "Climax_Flash", "color": [1.0, 0.96, 0.84, 1.0], "width": W, "height": H}))
    cmds.append(cmd("layer.timing", {"layers": ["Climax_Flash"], "in": 15.96, "out": 16.50}))
    cmds.append(key("Climax_Flash", "transform/opacity", 15.96, 0.0))
    cmds.append(key("Climax_Flash", "transform/opacity", 16.06, 82.0))
    cmds.append(key("Climax_Flash", "transform/opacity", 16.50, 0.0))

    for ray_i in range(8):
        ang = math.radians(ray_i * 45.0 + 18.0)
        x0, y0 = 720.0 + 135.0 * math.cos(ang), 490.0 + 135.0 * math.sin(ang)
        x1, y1 = 720.0 + 340.0 * math.cos(ang), 490.0 + 340.0 * math.sin(ang)
        make_trim_path(
            cmds, f"Climax_Ray_{ray_i}", [[round(x0, 1), round(y0, 1)], [round(x1, 1), round(y1, 1)]],
            stroke=[1.0, 0.86, 0.30], stroke_w=5.0,
            t_draw0=16.10, t_draw1=16.70, t_hide=19.95,
        )
        stage_layers.append(f"Climax_Ray_{ray_i}")

    # Full Detailed Lightbulb (Blurred Golden Halo + Glass + Inner M-Filament + Clean Screw Base!)
    bx, by = 1380.0, 440.0
    cmds.append(cmd("layer.newShape", {
        "name": "Bulb_Halo", "kind": "ellipse", "size": [280.0, 280.0],
        "fill": [1.0, 0.82, 0.25], "fillOpacity": 100.0, "position": [bx, by],
    }))
    add_gaussian_blur(cmds, "Bulb_Halo", 85.0)
    add_fade_window(cmds, "Bulb_Halo", 16.50, 20.00, fade=0.30, peak=55.0)
    stage_layers.append("Bulb_Halo")

    cmds.append(cmd("layer.newShape", {
        "name": "Bulb_Glass", "kind": "ellipse", "size": [150.0, 150.0],
        "fill": [1.0, 0.88, 0.34], "fillOpacity": 94.0, "stroke": [1.0, 0.98, 0.82], "strokeWidth": 4.0,
        "position": [bx, by],
    }))
    add_fade_window(cmds, "Bulb_Glass", 16.55, 20.00, fade=0.25)
    cmds.append(key("Bulb_Glass", "transform/scale", 16.55, [45.0, 45.0]))
    cmds.append(key("Bulb_Glass", "transform/scale", 16.95, [110.0, 110.0]))
    cmds.append(key("Bulb_Glass", "transform/scale", 17.20, [100.0, 100.0]))
    stage_layers.append("Bulb_Glass")

    # Glowing inner filament shaped cleanly inside glass
    make_trim_path(
        cmds, "Bulb_Filament",
        vertices=[[bx - 22.0, by + 50.0], [bx - 16.0, by - 8.0], [bx, by + 8.0], [bx + 16.0, by - 8.0], [bx + 22.0, by + 50.0]],
        stroke=[1.0, 0.99, 0.92], stroke_w=5.0,
        t_draw0=16.70, t_draw1=17.25, t_hide=20.00,
    )
    stage_layers.append("Bulb_Filament")

    # Clean silver screw base sitting cleanly BELOW the glass bottom (by + 96) + contact cap (by + 124)
    cmds.append(cmd("layer.newShape", {
        "name": "Bulb_Base", "kind": "rounded", "size": [68.0, 42.0],
        "fill": [0.72, 0.78, 0.86], "stroke": [0.32, 0.38, 0.48], "strokeWidth": 3.0,
        "position": [bx, by + 94.0],
    }))
    add_fade_window(cmds, "Bulb_Base", 16.65, 20.00, fade=0.22)
    stage_layers.append("Bulb_Base")

    cmds.append(cmd("layer.newShape", {
        "name": "Bulb_Tip", "kind": "ellipse", "size": [34.0, 18.0],
        "fill": [0.46, 0.52, 0.62], "position": [bx, by + 118.0],
    }))
    add_fade_window(cmds, "Bulb_Tip", 16.65, 20.00, fade=0.22)
    stage_layers.append("Bulb_Tip")

    for li in range(7):
        ang = math.radians(-165.0 + li * 25.0)
        rx0, ry0 = bx + 98.0 * math.cos(ang), by + 98.0 * math.sin(ang)
        rx1, ry1 = bx + 138.0 * math.cos(ang), by + 138.0 * math.sin(ang)
        make_trim_path(
            cmds, f"Bulb_Ray_{li}", [[round(rx0, 1), round(ry0, 1)], [round(rx1, 1), round(ry1, 1)]],
            stroke=[1.0, 0.90, 0.38], stroke_w=5.5,
            t_draw0=16.95 + li * 0.04, t_draw1=17.45 + li * 0.04, t_hide=20.00,
        )
        stage_layers.append(f"Bulb_Ray_{li}")

    # =========================================================================
    # SECTION 6 (20.00 - 24.00s): RESOLUTION — Right-Side Card + Signature + Loop
    # =========================================================================
    cmds.append(cmd("layer.newShape", {
        "name": "Res_Card", "kind": "rounded", "size": [620.0, 320.0],
        "fill": [0.06, 0.10, 0.17], "fillOpacity": 90.0, "stroke": [0.32, 0.84, 0.68],
        "strokeWidth": 3.5, "position": [1360.0, 500.0],
    }))
    add_fade_window(cmds, "Res_Card", 20.20, 23.25, fade=0.28)
    stage_layers.append("Res_Card")

    cmds.append(cmd("layer.newText", {
        "name": "Res_Title_Txt", "text": "KEY TAKEAWAY: BREAK THE HABIT LOOP", "size": 24.0,
        "fill": [0.42, 0.94, 0.75], "position": [1360.0, 425.0], "justify": "center",
    }))
    add_fade_window(cmds, "Res_Title_Txt", 20.35, 23.20, fade=0.22)
    stage_layers.append("Res_Title_Txt")

    make_trim_path(
        cmds, "Res_Signature_Trim",
        vertices=[[1160.0, 540.0], [1250.0, 495.0], [1335.0, 550.0], [1445.0, 502.0], [1560.0, 530.0]],
        stroke=[0.42, 0.94, 0.75], stroke_w=6.5,
        t_draw0=21.10, t_draw1=22.40, t_hide=23.25,
    )
    stage_layers.append("Res_Signature_Trim")

    cmds.append(cmd("layer.newShape", {
        "name": "Loop_Bridge_Ring", "kind": "ellipse", "size": [140.0, 140.0],
        "fillType": "none", "stroke": [0.22, 0.78, 1.0], "strokeWidth": 5.0,
        "position": [960.0, 520.0],
    }))
    cmds.append(cmd("layer.timing", {"layers": ["Loop_Bridge_Ring"], "in": 22.80, "out": 24.0}))
    cmds.append(key("Loop_Bridge_Ring", "transform/opacity", 22.80, 0.0))
    cmds.append(key("Loop_Bridge_Ring", "transform/opacity", 23.25, 85.0))
    cmds.append(key("Loop_Bridge_Ring", "transform/opacity", 23.96, 0.0))
    cmds.append(key("Loop_Bridge_Ring", "transform/scale", 22.80, [480.0, 480.0]))
    cmds.append(key("Loop_Bridge_Ring", "transform/scale", 23.98, [55.0, 55.0]))
    stage_layers.append("Loop_Bridge_Ring")

    # Parent all stage layers to Cam_Master with compensate=True!
    cmds.append(cmd("layer.setParent", {"layers": stage_layers, "parent": "Cam_Master"}))

    # Cinematic Camera Choreography
    cam_keys = [
        (0.00, [960.0, 540.0], [114.0, 114.0], -1.5),
        (0.28, [960.0, 540.0], [100.0, 100.0], 0.0),
        (4.20, [945.0, 540.0], [102.0, 102.0], 0.0),
        (8.00, [960.0, 540.0], [104.0, 104.0], 0.0),
        (12.00, [960.0, 540.0], [100.0, 100.0], 0.0),
        (14.80, [960.0, 530.0], [112.0, 112.0], -1.2),
        (15.70, [960.0, 525.0], [118.0, 118.0], 1.4),
        (16.00, [960.0, 540.0], [122.0, 122.0], -1.8),
        (16.36, [960.0, 540.0], [100.0, 100.0], 0.0),
        (20.00, [960.0, 540.0], [102.0, 102.0], 0.0),
        (23.50, [960.0, 540.0], [100.0, 100.0], 0.0),
        (24.00, [960.0, 540.0], [100.0, 100.0], 0.0),
    ]
    for t, cpos, csc, crot in cam_keys:
        cmds.append(key("Cam_Master", "transform/position", t, cpos))
        cmds.append(key("Cam_Master", "transform/scale", t, csc))
        cmds.append(key("Cam_Master", "transform/rotation", t, crot))

    # =========================================================================
    # TOP & BOTTOM HUD CHOREOGRAPHY (Strict layer.timing in/out -> ZERO overlap!)
    # =========================================================================
    cmds.append(cmd("layer.newShape", {
        "name": "HUD_Top_Bar", "kind": "rect", "size": [1920.0, 74.0],
        "fill": [0.025, 0.04, 0.075], "fillOpacity": 82.0, "position": [960.0, 37.0],
    }))
    cmds.append(cmd("layer.newShape", {
        "name": "HUD_Progress_Track", "kind": "rect", "size": [1680.0, 8.0],
        "fill": [0.18, 0.26, 0.38], "fillOpacity": 55.0, "position": [960.0, 1024.0],
    }))
    make_trim_path(
        cmds, "HUD_Progress_Fill",
        vertices=[[120.0, 1024.0], [1800.0, 1024.0]],
        stroke=[0.24, 0.84, 1.0], stroke_w=8.0,
        t_draw0=0.0, t_draw1=23.95, t_hide=24.0, t_show=0.0,
    )

    sec_titles = [
        ("HUD_S1", "01 // COLD OPEN — THE PATTERN INTERRUPT", 0.0, 4.0, [0.35, 0.88, 1.0]),
        ("HUD_S2", "02 // EVIDENCE BOARD — CONNECTING THE CLUES", 4.0, 8.0, [1.0, 0.78, 0.35]),
        ("HUD_S3", "03 // NEURO X-RAY — INSIDE THE MECHANISM", 8.0, 12.0, [0.22, 0.96, 0.90]),
        ("HUD_S4", "04 // ESCALATION — BREAKING POINT TENSION", 12.0, 16.0, [1.0, 0.34, 0.36]),
        ("HUD_S5", "05 // CLIMAX — PARADIGM SHIFT & EPIPHANY", 16.0, 20.0, [1.0, 0.86, 0.30]),
        ("HUD_S6", "06 // RESOLUTION — KEY TAKEAWAY & SEAMLESS LOOP", 20.0, 24.0, [0.42, 0.94, 0.75]),
    ]
    for sname, txt, t0, t1, col in sec_titles:
        cmds.append(cmd("layer.newText", {
            "name": sname, "text": txt, "size": 24.0,
            "fill": col, "position": [960.0, 44.0], "justify": "center",
        }))
        cmds.append(cmd("layer.timing", {"layers": [sname], "in": t0, "out": t1}))

    return cmds


def make_contact_sheet(mp4_path: Path, out_sheet: Path) -> None:
    tmp_dir = WORK_DIR / "_sheet_frames"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    picks = [
        ("01 HOOK Hit", 0.24),
        ("01 HOOK QMark", 2.40),
        ("02 EVIDENCE 1", 5.20),
        ("02 EVIDENCE 2", 6.80),
        ("03 NEURO Scan", 9.40),
        ("03 NEURO Web", 11.20),
        ("04 TENSION", 13.60),
        ("04 FRACTURE", 15.60),
        ("05 CLIMAX Jump", 16.56),
        ("05 BULB Idea", 18.40),
        ("06 YES/SIGN", 21.60),
        ("06 LOOP End", 23.60),
    ]

    imgs = []
    for i, (label, ts) in enumerate(picks):
        frame_p = tmp_dir / f"pick_{i:02d}.png"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{ts:.2f}", "-i", str(mp4_path), "-frames:v", "1", str(frame_p)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        im = Image.open(frame_p).convert("RGB").resize((480, 270), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(im)
        draw.rectangle((8, 238, 225, 262), fill=(10, 14, 22))
        draw.text((14, 243), f"{label} ({ts:.2f}s)", fill=(130, 220, 255))
        imgs.append(im)

    sheet = Image.new("RGB", (480 * 4, 270 * 3), (8, 12, 18))
    for i, im in enumerate(imgs):
        sheet.paste(im, ((i % 4) * 480, (i // 4) * 270))
    sheet.save(out_sheet)


def main() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    # Clean leftover _fx_check.json if any
    (WORK_DIR / "_fx_check.json").unlink(missing_ok=True)

    cmds_path = WORK_DIR / "cine_master_24s_cmds.json"
    proj_path = WORK_DIR / "cine_master_24s.ecproj"
    silent_mp4 = WORK_DIR / "cine_master_24s_silent.mp4"
    final_mp4 = WORK_DIR / "cine_master_24s_final.mp4"
    sheet_path = WORK_DIR / "cine_master_24s_sheet.png"

    cmds_path.write_text(json.dumps(build_commands(), indent=2), encoding="utf-8")
    subprocess.run(
        [str(EC_CLI), "run", "--commands", str(cmds_path), "--save-as", str(proj_path)],
        check=True,
    )
    subprocess.run(
        [str(EC_CLI), "render", str(proj_path), "--out", str(silent_mp4)],
        check=True,
    )

    if not AUDIO_WAV.exists():
        raise FileNotFoundError(f"Master audio missing: {AUDIO_WAV}")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(silent_mp4),
            "-i", str(AUDIO_WAV),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "320k",
            "-shortest",
            str(final_mp4),
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    make_contact_sheet(final_mp4, sheet_path)
    print(f"FINAL 24s MASTER RENDERED -> {final_mp4}")
    print(f"INSPECTION SHEET         -> {sheet_path}")


if __name__ == "__main__":
    main()

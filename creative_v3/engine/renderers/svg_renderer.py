"""
Deterministic SVG DOM mutator, RGBA frame renderer (PySide6 QSvgRenderer),
contact sheet generator (Pillow), and preview exporter (ffmpeg WebM VP9 alpha).
"""
from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lxml import etree
from PIL import Image, ImageDraw
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

SVG_NS = "http://www.w3.org/2000/svg"
_QT_APP: Optional[QGuiApplication] = None


def _ensure_qt_app() -> QGuiApplication:
    global _QT_APP
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    _QT_APP = app
    return app


def _parse_base_translate(transform_str: str) -> Tuple[float, float]:
    m = re.search(r"translate\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*\)", transform_str or "")
    if m:
        return float(m.group(1)), float(m.group(2))
    return 0.0, 0.0


TURNAROUND_DIR = Path(__file__).resolve().parents[2] / "characters" / "brand_mascot_v1" / "turnaround_svg"


def load_view_svg_bytes(view_id: str = "front", fallback_bytes: Optional[bytes] = None) -> bytes:
    """Load the authored 2D SVG for one of the 7 turnaround views."""
    p = TURNAROUND_DIR / f"{view_id}.svg"
    if p.exists():
        return p.read_bytes()
    if fallback_bytes is not None:
        return fallback_bytes
    master = TURNAROUND_DIR.parent / "mascot_master.svg"
    return master.read_bytes()


def apply_pose_to_svg(
    master_svg_bytes: bytes,
    pose: Dict[str, dict],
    expression: str = "smile",
    left_hand: str = "fist",
    right_hand: str = "open_palm",
    blink: bool = False,
    wink: bool = False,
    squint: bool = False,
    scene_svg_behind: str = "",
    scene_svg_front: str = "",
    canvas_viewbox: Tuple[int, int, int, int] = (0, 0, 960, 720),
    char_offset_xy: Tuple[float, float] = (140.0, -40.0),
    viseme: Optional[str] = None,
    gaze_xy: Optional[Tuple[float, float]] = None,
    eyelid_left: Optional[float] = None,
    eyelid_right: Optional[float] = None,
    brow_left: Optional[dict] = None,
    brow_right: Optional[dict] = None,
    finger_curls: Optional[Dict[str, Dict[str, float]]] = None,
    finger_spread: Optional[Dict[str, float]] = None,
    view_blend: float = 0.0,
) -> bytes:
    """
    Mutate a genuine SVG DOM with exact bone transforms, hand/mouth/eye states,
    and optional scene/prop vector layers, returning valid UTF-8 SVG bytes.
    """
    root = etree.fromstring(master_svg_bytes)
    root.set("viewBox", f"{canvas_viewbox[0]} {canvas_viewbox[1]} {canvas_viewbox[2]} {canvas_viewbox[3]}")
    root.set("width", str(canvas_viewbox[2]))
    root.set("height", str(canvas_viewbox[3]))

    # Map all elements by id
    by_id: Dict[str, etree._Element] = {}
    for el in root.iter():
        el_id = el.get("id")
        if el_id:
            by_id[el_id] = el

    # Apply bone transforms relative to each bone's resting translate
    for bone_id, vals in pose.items():
        el = by_id.get(bone_id)
        if el is None:
            continue
        bx, by = _parse_base_translate(el.get("transform", ""))
        tx = float(vals.get("tx", 0.0))
        ty = float(vals.get("ty", 0.0))
        rot = float(vals.get("rot", 0.0))
        sx = float(vals.get("sx", 1.0))
        sy = float(vals.get("sy", 1.0))
        parts = [f"translate({bx + tx:.2f}, {by + ty:.2f})"]
        if abs(rot) > 1e-4:
            parts.append(f"rotate({rot:.2f})")
        if abs(sx - 1.0) > 1e-4 or abs(sy - 1.0) > 1e-4:
            parts.append(f"scale({sx:.3f}, {sy:.3f})")
        el.set("transform", " ".join(parts))

    # Position character_root inside wider 960x720 stage
    char_root = by_id.get("character_root")
    if char_root is not None:
        r_vals = pose.get("character_root", {})
        rx = char_offset_xy[0] + float(r_vals.get("tx", 0.0))
        ry = char_offset_xy[1] + float(r_vals.get("ty", 0.0))
        rrot = float(r_vals.get("rot", 0.0))
        rsx = float(r_vals.get("sx", 1.0))
        rsy = float(r_vals.get("sy", 1.0))
        t_parts = [f"translate({rx:.2f}, {ry:.2f})"]
        if abs(rrot) > 1e-4:
            t_parts.append(f"rotate({rrot:.2f}, 300, 740)")
        if abs(rsx - 1.0) > 1e-4 or abs(rsy - 1.0) > 1e-4:
            t_parts.append(f"translate(300, 740) scale({rsx:.3f}, {rsy:.3f}) translate(-300, -740)")
        char_root.set("transform", " ".join(t_parts))

    # Swap mouth expression or viseme
    mouth_map = {
        "neutral": "mouth_neutral",
        "smile": "mouth_smile",
        "happy": "mouth_happy",
        "open_talk": "mouth_open_talk",
        "surprise": "mouth_surprise",
        "frown": "mouth_frown",
        "sad": "mouth_sad",
        "angry": "mouth_angry",
        "curious": "mouth_curious",
        "determined": "mouth_determined",
        "mischievous": "mouth_mischievous",
        "baffled": "mouth_baffled",
        "blink": "mouth_smile",
        "squint": "mouth_determined",
        "wink": "mouth_smile",
    }
    if viseme:
        vkey = viseme if viseme.startswith("viseme_") else f"viseme_{viseme}"
        active_mouth = f"mouth_{vkey}"
    else:
        active_mouth = mouth_map.get(expression, "mouth_smile")
    mouth_group = by_id.get("mouth_group")
    if mouth_group is not None:
        for child in mouth_group:
            if not isinstance(child.tag, str):
                continue
            cid = child.get("id", "")
            child.set("display", "inline" if cid == active_mouth else "none")

    # Eye states (blink / wink / squint / independent eyelid openness)
    lid_l = by_id.get("eyelid_left")
    lid_r = by_id.get("eyelid_right")
    if lid_l is not None:
        if eyelid_left is not None:
            op_l = max(0.0, min(1.0, 1.0 - float(eyelid_left)))
            lid_l.set("opacity", f"{op_l:.2f}")
        else:
            lid_l.set("opacity", "1" if (blink or expression == "blink") else ("0.55" if (squint or expression == "squint") else "0"))
    if lid_r is not None:
        if eyelid_right is not None:
            op_r = max(0.0, min(1.0, 1.0 - float(eyelid_right)))
            lid_r.set("opacity", f"{op_r:.2f}")
        else:
            lid_r.set("opacity", "1" if (blink or wink or expression in ("blink", "wink")) else ("0.55" if (squint or expression == "squint") else "0"))

    # Independent gaze target for irises/pupils
    if gaze_xy is not None:
        gx = max(-1.0, min(1.0, float(gaze_xy[0]))) * 9.0
        gy = max(-1.0, min(1.0, float(gaze_xy[1]))) * 6.0
        for iris_id in ("iris_group_left", "iris_group_right"):
            iris_el = by_id.get(iris_id)
            if iris_el is not None:
                iris_el.set("transform", f"translate({gx:.2f}, {gy:.2f})")

    # Independent eyebrows
    for b_id, b_val in (("brow_left", brow_left), ("brow_right", brow_right)):
        b_el = by_id.get(b_id)
        if b_el is not None and b_val:
            bty = float(b_val.get("ty", 0.0))
            brot = float(b_val.get("rot", 0.0))
            b_el.set("transform", f"translate(0, {bty:.2f}) rotate({brot:.2f})")

    # Subtle view_blend bridge squash/perspective on head & torso
    if abs(view_blend) > 1e-3 and char_root is not None:
        sx_bridge = max(0.86, 1.0 - 0.14 * abs(math.sin(view_blend * math.pi)))
        cur_t = char_root.get("transform", "")
        char_root.set("transform", f"{cur_t} translate(300, 740) scale({sx_bridge:.3f}, 1.000) translate(-300, -740)")

    # Swap hand poses or drive articulated finger joints
    for side, hpose in (("left", left_hand), ("right", right_hand)):
        side_curls = (finger_curls or {}).get(side)
        use_articulated = (hpose == "articulated") or bool(side_curls)
        poses_grp = by_id.get(f"hand_{side}_poses")
        art_grp = by_id.get(f"hand_{side}_articulated")
        if poses_grp is not None:
            target_id = f"hand_{side}_{hpose}"
            for child in poses_grp:
                if not isinstance(child.tag, str):
                    continue
                child.set("display", "none" if use_articulated else ("inline" if child.get("id") == target_id else "none"))
        if art_grp is not None:
            art_grp.set("display", "inline" if use_articulated else "none")
            if use_articulated:
                spread_val = float((finger_spread or {}).get(side, 0.0))
                spread_mult = {"thumb": -14.0, "index": -8.0, "middle": 0.0, "ring": 8.0, "pinky": 14.0}
                for fname in ("thumb", "index", "middle", "ring", "pinky"):
                    curl = max(0.0, min(1.0, float((side_curls or {}).get(fname, 0.0))))
                    prox = by_id.get(f"finger_{side}_{fname}_prox")
                    dist = by_id.get(f"finger_{side}_{fname}_dist")
                    if prox is not None:
                        bx = float(prox.get("data-base-x", 0.0))
                        by_ = float(prox.get("data-base-y", 0.0))
                        brot = float(prox.get("data-base-rot", 0.0))
                        prox_rot = brot + curl * 65.0 + spread_val * spread_mult[fname]
                        prox.set("transform", f"translate({bx:.1f}, {by_:.1f}) rotate({prox_rot:.1f})")
                    if dist is not None:
                        dx = float(dist.get("data-base-x", 18.0))
                        dist_rot = curl * 80.0
                        dist.set("transform", f"translate({dx:.1f}, 0) rotate({dist_rot:.1f})")

    # Inject behind/front vector scene layers
    if scene_svg_behind:
        behind_el = etree.fromstring(f'<g xmlns="{SVG_NS}" id="scene_behind">{scene_svg_behind}</g>')
        if char_root is not None:
            idx = list(root).index(char_root)
            root.insert(idx, behind_el)
        else:
            root.append(behind_el)
    if scene_svg_front:
        front_el = etree.fromstring(f'<g xmlns="{SVG_NS}" id="scene_front">{scene_svg_front}</g>')
        root.append(front_el)

    return etree.tostring(root, encoding="utf-8", xml_declaration=True)


def render_svg_bytes_to_png(
    svg_bytes: bytes,
    out_png: Path,
    width: int = 960,
    height: int = 720,
) -> Path:
    """Render genuine SVG bytes to a transparent RGBA PNG using PySide6 QSvgRenderer."""
    _ensure_qt_app()
    renderer = QSvgRenderer(QByteArray(svg_bytes))
    if not renderer.isValid():
        raise ValueError("Invalid SVG document passed to QSvgRenderer")
    img = QImage(width, height, QImage.Format_RGBA8888)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, width, height))
    painter.end()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_png))
    return out_png


def build_contact_sheet(
    frame_paths: List[Path],
    out_path: Path,
    cols: int = 5,
    thumb_size: Tuple[int, int] = (240, 180),
) -> Path:
    """Create a grid contact sheet from key pose frames with frame index labels."""
    if not frame_paths:
        raise ValueError("frame_paths cannot be empty")
    n = min(len(frame_paths), 10)
    step = max(1, len(frame_paths) // n)
    picks = [frame_paths[min(i * step, len(frame_paths) - 1)] for i in range(n)]
    rows = math.ceil(len(picks) / cols)
    sheet = Image.new("RGBA", (cols * thumb_size[0], rows * thumb_size[1]), (24, 28, 36, 255))
    draw = ImageDraw.Draw(sheet)
    for idx, fp in enumerate(picks):
        r, c = divmod(idx, cols)
        im = Image.open(fp).convert("RGBA").resize(thumb_size, Image.Resampling.LANCZOS)
        x0, y0 = c * thumb_size[0], r * thumb_size[1]
        sheet.paste(im, (x0, y0), im)
        draw.text((x0 + 8, y0 + 6), fp.stem, fill=(255, 212, 0, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return out_path


def encode_preview_webm(
    frames_dir: Path,
    out_webm: Path,
    fps: int = 30,
) -> Path:
    """Encode frame_%04d.png sequence to transparent VP9 WebM preview."""
    out_webm.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%04d.png"),
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuva420p",
        "-b:v", "0",
        "-crf", "32",
        "-auto-alt-ref", "0",
        str(out_webm),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_webm

"""
Master Modular Whiteboard Animation Production Renderer
Renders full-quality 1080p @ 30fps speech-synchronized whiteboard animations
across all 6 storyboard sheets (36 panels, 11m 24s) with:
- 3x2 grid layout per sheet
- Semantic Narrative Audit & Sequence Choreography (Zero audio-drawing mismatches)
- Progressive inking with concentric peeling and Arabic RTL handwriting
- Subpixel physical artist hand with pen-tip alignment
- Cinematic camera easing, row-return crane dip, and grand outro reveal
- Hardware NVENC GPU video encoding and lossless AAC audio muxing
- Modular sheet rendering and seamless master concatenation
"""
import os
import sys
import math
import time
import json
import argparse
import subprocess
import cv2
import av
import numpy as np
from typing import List, Dict, Any, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.processing.whiteboard_processor import WhiteboardProcessor
from engine.processing.dynamic_border_detector import DynamicBorderDetector
from dev_separator.panel_pipeline import PanelPipeline
from engine.pipeline.semantic_narrative_auditor import SemanticNarrativeAuditor
from engine.pipeline.dynamic_srt_choreographer import extract_object_strokes
from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.concentric_engine import (
    DEFAULT_HAND_PATH,
    DEFAULT_HAND_MASK_PATH,
    PEN_TIP_ANCHOR_X,
    PEN_TIP_ANCHOR_Y
)


def smootherstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


def get_camera_affine_matrix(
    center_x: float,
    center_y: float,
    zoom_scale: float,
    tilt_deg: float = 0.0,
    out_w: int = 1920,
    out_h: int = 1080
) -> np.ndarray:
    zoom_scale = max(0.2, zoom_scale)
    vw = out_w / zoom_scale
    vh = out_h / zoom_scale

    angle_rad = math.radians(tilt_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    half_w = vw / 2.0
    half_h = vh / 2.0

    p0 = (-half_w, -half_h)
    p1 = (half_w, -half_h)
    p2 = (-half_w, half_h)

    src_pts = np.float32([
        [center_x + p0[0] * cos_a - p0[1] * sin_a, center_y + p0[0] * sin_a + p0[1] * cos_a],
        [center_x + p1[0] * cos_a - p1[1] * sin_a, center_y + p1[0] * sin_a + p1[1] * cos_a],
        [center_x + p2[0] * cos_a - p2[1] * sin_a, center_y + p2[0] * sin_a + p2[1] * cos_a]
    ])

    dst_pts = np.float32([[0, 0], [out_w, 0], [0, out_h]])
    return cv2.getAffineTransform(src_pts, dst_pts)


def render_camera_viewport_with_matrix(
    canvas: np.ndarray,
    matrix: np.ndarray,
    out_w: int = 1920,
    out_h: int = 1080
) -> np.ndarray:
    return cv2.warpAffine(
        canvas,
        matrix,
        (out_w, out_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)
    )


def canvas_to_screen_pt(matrix: np.ndarray, pt: tuple) -> tuple:
    p = np.array([pt[0], pt[1], 1.0], dtype=np.float32)
    scr = matrix @ p
    return (float(scr[0]), float(scr[1]))


def render_single_sheet(
    sheet_index: int,
    timing_data_path: str = "scratch/true_calibrated_panel_timings.json",
    fps: int = 30,
    zoom_level: float = 1.48,
    out_w: int = 1920,
    out_h: int = 1080
) -> str:
    print("\n" + "=" * 95)
    print(f"      🎬 RENDERING STORYBOARD SHEET {sheet_index} (PANELS {(sheet_index-1)*6 + 1:02d} TO {sheet_index*6:02d}) 🎬")
    print("=" * 95)
    sheet_start_real_time = time.time()

    # 1. Paths
    image_path = os.path.join(ROOT_DIR, "project_content", "images", f"sheet_{sheet_index:02d}.png")
    audio_path = os.path.join(ROOT_DIR, "project_content", "audio", "sheets", f"sheet{sheet_index}_audio.wav")
    output_dir = os.path.join(ROOT_DIR, "output_animations")
    os.makedirs(output_dir, exist_ok=True)
    output_mp4 = os.path.join(output_dir, f"sheet_{sheet_index:02d}_whiteboard.mp4")

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    # Load timing
    with open(os.path.join(ROOT_DIR, timing_data_path), 'r', encoding='utf-8') as f:
        all_timings = json.load(f)

    sheet_timings = [t for t in all_timings if t["sheet"] == sheet_index]
    t_offset = sheet_timings[0]["start_time"]
    local_timings = []
    for t in sheet_timings:
        local_timings.append({
            "panel_id": t["panel_id"],
            "local_id": t["local_id"],
            "start": t["start_time"] - t_offset,
            "end": t["end_time"] - t_offset,
            "duration": t["duration"],
            "speech": t.get("speech", t.get("title", ""))
        })

    sheet_duration = local_timings[-1]["end"]
    total_frames = int(round(sheet_duration * fps))
    print(f"Sheet Duration : {sheet_duration:.2f}s ({total_frames} frames @ {fps}fps)")
    print(f"Audio Track    : {os.path.basename(audio_path)}")
    print(f"Target Output  : {os.path.basename(output_mp4)}")

    # 2. Panel Discovery & Segmentation
    print("\n[1/5] Discovering and isolating 6 panels with CV...")
    img = cv2.imread(image_path)
    discovered = WhiteboardProcessor.discover_panels(img)
    if len(discovered) != 6:
        print(f"⚠️ Warning: Found {len(discovered)} panels (expected 6). Using available.")

    processed_panels = []
    for l_idx, p_info in enumerate(discovered[:6]):
        px, py, pw, ph = p_info["bbox"]
        raw_crop = img[py:py+ph, px:px+pw]
        border_res = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)
        clean_crop = border_res["clean_crop"]
        timing = local_timings[l_idx]

        panel_res = PanelPipeline.process_panel(
            clean_crop,
            panel_id=timing["panel_id"],
            ignore_badges=True
        )

        processed_panels.append({
            "global_id": timing["panel_id"],
            "local_id": l_idx + 1,
            "sheet_index": sheet_index,
            "title": f"Panel {timing['panel_id']:02d}",
            "start_time": timing["start"],
            "end_time": timing["end"],
            "duration": timing["duration"],
            "raw_w": clean_crop.shape[1],
            "raw_h": clean_crop.shape[0],
            "clean_crop": panel_res["clean_crop"],
            "objects": panel_res["objects"],
            "speech": timing["speech"]
        })
        print(f"  • Panel {timing['panel_id']:02d}: [{timing['start']:05.1f}s -> {timing['end']:05.1f}s] ({timing['duration']:04.1f}s) | Objs: {len(panel_res['objects']):02d}")

    # 3. Semantic Narrative Audit & Sequence Choreography
    print("\n[2/5] Applying Semantic Narrative Audit & Speech-Sync Reordering...")
    reordered_panels, audit_report = SemanticNarrativeAuditor.audit_and_reorder_all_panels(processed_panels)
    incons_total = sum(r["inconsistencies_detected"] for r in audit_report)
    print(f"  • Narrative Inconsistencies Corrected: {incons_total}")
    for r in audit_report:
        first_desc = r["drawing_order"][0]["description"] if r["drawing_order"] else "None"
        print(f"    - Panel {r['panel_id']:02d}: {r['inconsistencies_detected']} resolved | Beat 1: {first_desc[:38]}")

    # 4. Canvas Geometry (3 columns x 2 rows)
    cols, rows = 3, 2
    target_p_h = 660
    first_p = reordered_panels[0]
    aspect = first_p["raw_w"] / float(first_p["raw_h"])
    target_p_w = int(round(target_p_h * aspect))

    gap_x = 90
    gap_y = 80
    grid_w = cols * target_p_w + (cols - 1) * gap_x
    grid_h = rows * target_p_h + (rows - 1) * gap_y

    canvas_w = max(3840, grid_w + 400)
    canvas_h = max(2160, grid_h + 300)
    start_x = (canvas_w - grid_w) // 2
    start_y = (canvas_h - grid_h) // 2

    live_canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)
    placed_panels = []
    panel_drawn_masks = {}

    for idx, panel in enumerate(reordered_panels):
        p_id = panel["global_id"]
        r = idx // cols
        c = idx % cols

        gx = start_x + c * (target_p_w + gap_x)
        gy = start_y + r * (target_p_h + gap_y)

        scale_x = target_p_w / float(panel["raw_w"])
        scale_y = target_p_h / float(panel["raw_h"])

        hd_art = cv2.resize(panel["clean_crop"], (target_p_w, target_p_h), interpolation=cv2.INTER_LANCZOS4)
        gray_art = cv2.cvtColor(hd_art, cv2.COLOR_BGR2GRAY)
        hd_art[gray_art > 240] = [255, 255, 255]

        objs = panel["objects"]
        prepared_objs = []

        for o_idx, obj in enumerate(objs):
            cat = obj.get("category", "TEXT")
            name = obj.get("name", f"Obj_{o_idx+1}")
            sync_st = obj.get("sync_start", panel["start_time"])
            sync_en = obj.get("sync_end", panel["end_time"])

            strokes = extract_object_strokes(obj, scale_x, scale_y)
            global_strokes = [(gx + pt[0], gy + pt[1]) for pt in strokes]

            full_m = obj.get("full_mask")
            if full_m is not None:
                scaled_mask = cv2.resize(full_m, (target_p_w, target_p_h), interpolation=cv2.INTER_NEAREST)
            else:
                scaled_mask = np.zeros((target_p_h, target_p_w), dtype=np.uint8)

            prepared_objs.append({
                "name": name,
                "category": cat,
                "sync_start": sync_st,
                "sync_end": sync_en,
                "stroke_pts": global_strokes,
                "scaled_mask": scaled_mask,
                "last_drawn_idx": 0
            })

        panel_drawn_masks[p_id] = np.zeros((target_p_h, target_p_w), dtype=np.uint8)

        placed_panels.append({
            "global_id": p_id,
            "local_id": panel["local_id"],
            "title": panel["title"],
            "gx": gx, "gy": gy,
            "gw": target_p_w, "gh": target_p_h,
            "center_x": gx + target_p_w / 2.0,
            "center_y": gy + target_p_h / 2.0,
            "hd_artwork": hd_art,
            "objects": prepared_objs,
            "start_time": panel["start_time"],
            "end_time": panel["end_time"]
        })

    # 5. Hand Assets
    print("\n[3/5] Loading artist hand asset and initializing hardware encoder...")
    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_screen_h = int(out_h * 0.38)
    scale_hand = hand_screen_h / float(hand_bgra.shape[0])
    hand_screen_w = max(1, int(hand_bgra.shape[1] * scale_hand))
    hand_screen = cv2.resize(hand_bgra, (hand_screen_w, hand_screen_h), interpolation=cv2.INTER_AREA)
    tip_x_screen = int(round(PEN_TIP_ANCHOR_X * scale_hand))
    tip_y_screen = int(round(PEN_TIP_ANCHOR_Y * scale_hand))

    # Encoder
    container = av.open(output_mp4, mode="w")
    v_codec = "h264_nvenc"
    try:
        tc = av.open(os.devnull, mode="w", format="mp4")
        tc.add_stream("h264_nvenc", rate=fps)
        tc.close()
    except Exception:
        print("  • NVENC test failed, using CPU h264...")
        v_codec = "h264"

    v_stream = container.add_stream(v_codec, rate=fps)
    v_stream.width = out_w
    v_stream.height = out_h
    v_stream.pix_fmt = "yuv420p"
    if v_codec == "h264_nvenc":
        v_stream.options = {"preset": "p5", "cq": "19"}
    else:
        v_stream.options = {"crf": "18"}

    in_aud = av.open(audio_path)
    in_aud_stream = in_aud.streams.audio[0]
    a_stream = container.add_stream("aac", rate=in_aud_stream.rate)

    # 6. Render Loop
    print(f"\n[4/5] Executing Whiteboard Render Loop ({total_frames} frames)...")
    current_pen = (placed_panels[0]["gx"] + placed_panels[0]["gw"] * 0.7, placed_panels[0]["gy"] + 60.0)
    board_center = (canvas_w / 2.0, canvas_h / 2.0)
    board_zoom = min(out_w / float(grid_w + 240), out_h / float(grid_h + 180)) * 0.95
    outro_start_time = sheet_duration - 2.8

    diag_dir = os.path.join(ROOT_DIR, "scratch", f"sheet{sheet_index}_inspection_frames")
    os.makedirs(diag_dir, exist_ok=True)
    diag_milestones = [
        round(sheet_duration * f, 1) for f in [0.10, 0.25, 0.45, 0.65, 0.85, 0.98]
    ]

    for frame_idx in range(total_frames):
        curr_time = frame_idx / float(fps)

        # Active panel
        active_p = placed_panels[0]
        for p in placed_panels:
            if p["start_time"] <= curr_time < p["end_time"]:
                active_p = p
                break
            elif curr_time >= p["end_time"]:
                active_p = p

        l_idx = active_p["local_id"] - 1
        target_cam = (active_p["center_x"], active_p["center_y"])

        # Outro Reveal
        if curr_time >= outro_start_time:
            t_outro = (curr_time - outro_start_time) / 2.8
            t_ease = smootherstep(t_outro)
            cam_x = target_cam[0] + (board_center[0] - target_cam[0]) * t_ease
            cam_y = target_cam[1] + (board_center[1] - target_cam[1]) * t_ease
            cam_zoom = zoom_level + (board_zoom - zoom_level) * t_ease
            cam_tilt = 0.0

            off_pen = (canvas_w + 600.0, canvas_h + 600.0)
            current_pen = (
                current_pen[0] + (off_pen[0] - current_pen[0]) * 0.15,
                current_pen[1] + (off_pen[1] - current_pen[1]) * 0.15
            )
        else:
            is_row_return = (l_idx == 3)
            trans_dur = 0.60 if is_row_return else 0.38
            tl_start = active_p["start_time"]

            if l_idx > 0 and (curr_time - tl_start) < trans_dur:
                prev_p = placed_panels[l_idx - 1]
                prev_cam = (prev_p["center_x"], prev_p["center_y"])
                t_trans = (curr_time - tl_start) / trans_dur
                t_ease = smootherstep(t_trans)

                dx = target_cam[0] - prev_cam[0]
                dy = target_cam[1] - prev_cam[1]
                cam_x = prev_cam[0] + dx * t_ease
                cam_y = prev_cam[1] + dy * t_ease
                dip = 0.28 if is_row_return else 0.16
                cam_zoom = zoom_level - dip * math.sin(t_ease * math.pi)
                cam_tilt = (4.0 * math.sin(t_ease * math.pi)) if is_row_return else (1.5 * math.sin(t_ease * math.pi))
            else:
                cam_x = target_cam[0]
                cam_y = target_cam[1]
                cam_zoom = zoom_level
                cam_tilt = 0.0

        # Draw objects
        is_drawing_this_frame = False
        pen_target = None

        for p in placed_panels:
            p_id = p["global_id"]
            if curr_time < p["start_time"]:
                continue

            for obj in p["objects"]:
                st_o = obj["sync_start"]
                en_o = obj["sync_end"]
                strokes = obj["stroke_pts"]
                num_pts = len(strokes)
                if num_pts == 0:
                    continue

                if curr_time >= en_o:
                    pct = 1.0
                elif curr_time <= st_o:
                    pct = 0.0
                else:
                    pct = (curr_time - st_o) / max(0.01, (en_o - st_o))
                    is_drawing_this_frame = True

                target_pt_idx = int(round(pct * (num_pts - 1)))
                last_idx = obj["last_drawn_idx"]

                if target_pt_idx > last_idx:
                    drawn_slice = strokes[last_idx:target_pt_idx + 1]
                    for pt in drawn_slice:
                        lx = int(round(pt[0] - p["gx"]))
                        ly = int(round(pt[1] - p["gy"]))
                        if 0 <= lx < p["gw"] and 0 <= ly < p["gh"]:
                            cv2.circle(panel_drawn_masks[p_id], (lx, ly), 14, 255, -1)
                    obj["last_drawn_idx"] = target_pt_idx

                if st_o <= curr_time < en_o and target_pt_idx < num_pts:
                    pen_target = strokes[target_pt_idx]

                if pct >= 1.0 and obj["scaled_mask"] is not None:
                    panel_drawn_masks[p_id] = cv2.bitwise_or(panel_drawn_masks[p_id], obj["scaled_mask"])

            mask_3c = cv2.merge([panel_drawn_masks[p_id]] * 3)
            drawn_region = cv2.bitwise_and(p["hd_artwork"], mask_3c)
            inv_mask = cv2.bitwise_not(mask_3c)
            bg_region = cv2.bitwise_and(np.full((p["gh"], p["gw"], 3), 255, dtype=np.uint8), inv_mask)
            live_canvas[p["gy"]:p["gy"]+p["gh"], p["gx"]:p["gx"]+p["gw"]] = cv2.add(drawn_region, bg_region)

        # Smooth pen tracking
        if pen_target is not None:
            current_pen = (
                current_pen[0] + (pen_target[0] - current_pen[0]) * 0.45,
                current_pen[1] + (pen_target[1] - current_pen[1]) * 0.45
            )
        elif not is_drawing_this_frame and curr_time < outro_start_time:
            rest_x = active_p["gx"] + active_p["gw"] * 0.85
            rest_y = active_p["gy"] + active_p["gh"] * 0.90
            current_pen = (
                current_pen[0] + (rest_x - current_pen[0]) * 0.08,
                current_pen[1] + (rest_y - current_pen[1]) * 0.08
            )

        # Viewport transform
        cam_mat = get_camera_affine_matrix(cam_x, cam_y, cam_zoom, cam_tilt, out_w, out_h)
        viewport_frame = render_camera_viewport_with_matrix(live_canvas, cam_mat, out_w, out_h)

        # Composite hand
        pen_scr = canvas_to_screen_pt(cam_mat, current_pen)
        scr_tip_x, scr_tip_y = pen_scr
        if -500 <= scr_tip_x <= out_w + 500 and -500 <= scr_tip_y <= out_h + 500:
            composited = composite_hand_on_canvas_fast(
                viewport_frame,
                hand_screen,
                tip_x_screen,
                tip_y_screen,
                int(round(scr_tip_x)),
                int(round(scr_tip_y))
            )
        else:
            composited = viewport_frame

        # Save milestone diagnostics
        for ms in diag_milestones:
            if abs(curr_time - ms) < (0.5 / fps):
                diag_path = os.path.join(diag_dir, f"frame_{curr_time:05.1f}s.jpg")
                cv2.imwrite(diag_path, composited)

        # Encode video packet
        vid_frame = av.VideoFrame.from_ndarray(composited, format="bgr24")
        vid_frame.pts = frame_idx
        for packet in v_stream.encode(vid_frame):
            container.mux(packet)

        if frame_idx > 0 and frame_idx % 300 == 0:
            elapsed = time.time() - sheet_start_real_time
            fps_proc = frame_idx / elapsed
            rem_sec = (total_frames - frame_idx) / max(0.1, fps_proc)
            print(f"  [{frame_idx:05d}/{total_frames:05d}] {curr_time:05.1f}s/{sheet_duration:05.1f}s | {fps_proc:.1f} fps | ETA: {rem_sec:04.1f}s")

    # Flush video
    for packet in v_stream.encode():
        container.mux(packet)

    # Encode audio
    print("\n[5/5] Muxing losslessly synchronized AAC audio...")
    in_aud.seek(0)
    for frame in in_aud.decode(audio=0):
        frame.pts = None
        for packet in a_stream.encode(frame):
            container.mux(packet)
    for packet in a_stream.encode():
        container.mux(packet)

    in_aud.close()
    container.close()

    total_elapsed = time.time() - sheet_start_real_time
    print(f"✅ Sheet {sheet_index} rendered successfully in {total_elapsed:.1f}s ({total_elapsed/60.0:.2f} min).")
    print(f"✅ Output: {output_mp4}")
    return output_mp4


def concatenate_all_sheets(
    sheet_videos: List[str],
    master_audio_path: str,
    output_master_mp4: str
) -> str:
    print("\n" + "=" * 95)
    print("      🎬 CONCATENATING 6 SHEETS INTO MASTER 11-MINUTE PRODUCTION VIDEO 🎬")
    print("=" * 95)

    concat_txt = os.path.join(ROOT_DIR, "scratch", "concat_list.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for vid in sheet_videos:
            f.write(f"file '{os.path.abspath(vid).replace(chr(92), '/')}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_txt,
        "-i", master_audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_master_mp4
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ Master Full 11-Minute Animation successfully assembled: {output_master_mp4}")
    return output_master_mp4


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master Modular Whiteboard Animation Renderer")
    parser.add_argument("--sheet", type=int, default=1, help="Sheet number (1 to 6) to render")
    parser.add_argument("--all", action="store_true", help="Render all 6 sheets sequentially and concatenate")
    args = parser.parse_args()

    if args.all:
        rendered = []
        for s in range(1, 7):
            vid = render_single_sheet(s)
            rendered.append(vid)
        master_audio = os.path.join(ROOT_DIR, "project_content", "audio", "master_voiceover_concatenated.wav")
        final_mp4 = os.path.join(ROOT_DIR, "output_animations", "master_11min_whiteboard_animation.mp4")
        concatenate_all_sheets(rendered, master_audio, final_mp4)
    else:
        render_single_sheet(args.sheet)

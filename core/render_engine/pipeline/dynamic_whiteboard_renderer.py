"""
Dynamic Whiteboard Production Renderer
Renders full cinematic camera choreography, screen-space hand compositing,
progressive ink deposition, and losslessly muxes voiceover audio into final MP4.
"""
import os
import sys
import math
import cv2
import av
import numpy as np
from typing import List, Dict, Any, Tuple

try:
    from core.render_engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
    from core.render_engine.render.concentric_engine import (
        DEFAULT_HAND_PATH,
        DEFAULT_HAND_MASK_PATH,
        PEN_TIP_ANCHOR_X,
        PEN_TIP_ANCHOR_Y
    )
except ImportError:
    from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
    from engine.render.concentric_engine import (
        DEFAULT_HAND_PATH,
        DEFAULT_HAND_MASK_PATH,
        PEN_TIP_ANCHOR_X,
        PEN_TIP_ANCHOR_Y
    )
from .dynamic_srt_choreographer import extract_object_strokes


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


class DynamicWhiteboardRenderer:
    @classmethod
    def render(
        cls,
        scheduled_panels: List[Dict[str, Any]],
        master_audio_path: str,
        output_video_path: str,
        fps: int = 30,
        zoom_level: float = 1.38,
        out_w: int = 1920,
        out_h: int = 1080
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
        num_panels = len(scheduled_panels)
        total_duration = scheduled_panels[-1]["end_time"]
        total_frames = int(round(total_duration * fps))

        print("\n=========================================================================================")
        print("          🎬 PRODUCTION DYNAMIC WHITEBOARD RENDERER (ALL PANELS) 🎬                      ")
        print("=========================================================================================")
        print(f"Panels Count    : {num_panels}")
        print(f"Total Duration  : {total_duration:.2f}s ({total_frames} frames @ {fps}fps)")
        print(f"Master Audio    : {master_audio_path}")
        print(f"Output Video    : {output_video_path}")
        print("-----------------------------------------------------------------------------------------")

        # 1. Setup Canvas Architecture
        # Grid layout: 4 columns, rows = ceil(N / 4)
        cols = 4
        rows = int(math.ceil(num_panels / float(cols)))
        target_p_h = 510
        gap_x = 80
        gap_y = 65

        first_p = scheduled_panels[0]
        aspect = first_p["raw_w"] / float(first_p["raw_h"])
        target_p_w = int(round(target_p_h * aspect))

        grid_w = cols * target_p_w + (cols - 1) * gap_x
        grid_h = rows * target_p_h + (rows - 1) * gap_y

        canvas_w = max(3840, grid_w + 200)
        canvas_h = max(2160, grid_h + 200)

        start_x = (canvas_w - grid_w) // 2
        start_y = (canvas_h - grid_h) // 2

        live_canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)

        # 2. Position panels & precompute global drawing coordinates
        placed_panels = []
        panel_drawn_masks = {}

        for idx, panel in enumerate(scheduled_panels):
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

            # Objects with global stroke points
            prepared_objs = []
            for obj in panel["objects"]:
                strokes = extract_object_strokes(obj, scale_x, scale_y)
                global_strokes = [(gx + pt[0], gy + pt[1]) for pt in strokes]

                full_m = obj.get("full_mask")
                if full_m is not None:
                    scaled_mask = cv2.resize(full_m, (target_p_w, target_p_h), interpolation=cv2.INTER_NEAREST)
                else:
                    scaled_mask = np.zeros((target_p_h, target_p_w), dtype=np.uint8)

                prepared_objs.append({
                    "name": obj["name"],
                    "category": obj["category"],
                    "sync_start": obj["sync_start"],
                    "sync_end": obj["sync_end"],
                    "stroke_pts": global_strokes,
                    "scaled_mask": scaled_mask,
                    "last_drawn_idx": 0
                })

            panel_drawn_masks[p_id] = np.zeros((target_p_h, target_p_w), dtype=np.uint8)

            placed_panels.append({
                "global_id": p_id,
                "gx": gx, "gy": gy,
                "gw": target_p_w, "gh": target_p_h,
                "center_x": gx + target_p_w / 2.0,
                "center_y": gy + target_p_h / 2.0,
                "hd_artwork": hd_art,
                "objects": prepared_objs,
                "start_time": panel["start_time"],
                "end_time": panel["end_time"]
            })

        # 3. Load Hand Asset
        hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
        hand_screen_h = int(out_h * 0.38)
        scale_hand = hand_screen_h / float(hand_bgra.shape[0])
        hand_screen_w = max(1, int(hand_bgra.shape[1] * scale_hand))
        hand_screen = cv2.resize(hand_bgra, (hand_screen_w, hand_screen_h), interpolation=cv2.INTER_AREA)
        tip_x_screen = int(round(PEN_TIP_ANCHOR_X * scale_hand))
        tip_y_screen = int(round(PEN_TIP_ANCHOR_Y * scale_hand))

        # 4. Initialize PyAV Encoder Container with Video & Audio
        temp_video_path = output_video_path
        container = av.open(temp_video_path, mode="w")

        v_codec = "h264"
        try:
            tc = av.open(os.devnull, mode="w", format="mp4")
            tc.add_stream("h264_nvenc", rate=fps)
            tc.close()
            v_codec = "h264_nvenc"
        except Exception:
            v_codec = "h264"

        v_stream = container.add_stream(v_codec, rate=fps)
        v_stream.width = out_w
        v_stream.height = out_h
        v_stream.pix_fmt = "yuv420p"
        v_stream.options = {"crf": "18"}

        # Audio stream
        in_aud = av.open(master_audio_path)
        in_aud_stream = in_aud.streams.audio[0]
        a_stream = container.add_stream("aac", rate=in_aud_stream.rate)

        # 5. Main Render Loop
        current_pen = (placed_panels[0]["gx"] + placed_panels[0]["gw"] * 0.7, placed_panels[0]["gy"] + 60.0)

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

            p_idx = active_p["global_id"] - 1
            target_cam = (active_p["center_x"], active_p["center_y"])

            # Camera transition with intelligent easing for row returns and sheet transition
            is_sheet_trans = (p_idx == 16)
            is_row_return = (p_idx > 0 and p_idx % cols == 0)
            trans_dur = 0.55 if is_sheet_trans else (0.42 if is_row_return else 0.35)
            tl_start = active_p["start_time"]
            if p_idx > 0 and (curr_time - tl_start) < trans_dur:
                prev_p = placed_panels[p_idx - 1]
                prev_cam = (prev_p["center_x"], prev_p["center_y"])
                t_trans = (curr_time - tl_start) / trans_dur
                t_ease = smootherstep(t_trans)

                dx = target_cam[0] - prev_cam[0]
                dy = target_cam[1] - prev_cam[1]
                cam_x = prev_cam[0] + dx * t_ease
                cam_y = prev_cam[1] + dy * t_ease
                dip = 0.32 if is_sheet_trans else 0.18
                cam_zoom = zoom_level - dip * math.sin(t_ease * math.pi)
                cam_tilt = (1.0 if dx >= 0 else -1.0) * (1.6 if is_sheet_trans else 1.1) * math.sin(t_ease * math.pi)
            else:
                cam_x, cam_y = target_cam
                cam_zoom = zoom_level
                cam_tilt = 0.0

            # Multi-object continuous drawing without jumping
            active_drawing_objs = [
                obj for obj in active_p["objects"]
                if obj["sync_start"] <= curr_time <= obj["sync_end"] and len(obj["stroke_pts"]) > 0
            ]

            p_m = panel_drawn_masks[active_p["global_id"]]
            gx, gy = active_p["gx"], active_p["gy"]
            gw, gh = active_p["gw"], active_p["gh"]
            art = active_p["hd_artwork"]

            if active_drawing_objs:
                # In realistic whiteboard animation, a single artist hand focuses on one object at a time
                # Select the active object that is currently drawing
                primary_obj = active_drawing_objs[0]
                for obj in active_drawing_objs:
                    if obj["last_drawn_idx"] < len(obj["stroke_pts"]) - 1:
                        primary_obj = obj
                        break

                ost = primary_obj["sync_start"]
                oen = primary_obj["sync_end"]
                odur = max(0.05, oen - ost)
                prog = max(0.0, min(1.0, (curr_time - ost) / odur))

                s_pts = primary_obj["stroke_pts"]
                pt_idx = min(len(s_pts) - 1, int(round(prog * (len(s_pts) - 1))))
                last_i = primary_obj["last_drawn_idx"]

                brush_r = 8 if primary_obj["category"] in ("TITLE", "TEXT_LINE", "TEXT") else 10

                for i in range(last_i, pt_idx + 1):
                    lx = int(round(s_pts[i][0] - gx))
                    ly = int(round(s_pts[i][1] - gy))
                    if 0 <= lx < gw and 0 <= ly < gh:
                        cv2.circle(p_m, (lx, ly), brush_r, 255, -1)
                        if i > 0:
                            plx = int(round(s_pts[i-1][0] - gx))
                            ply = int(round(s_pts[i-1][1] - gy))
                            step_dist = math.hypot(lx - plx, ly - ply)
                            if step_dist <= 26.0:
                                cv2.line(p_m, (plx, ply), (lx, ly), 255, thickness=brush_r * 2)

                primary_obj["last_drawn_idx"] = pt_idx
                target_pen = s_pts[pt_idx]

                # Natural human hand easing: continuous smooth transit with zero teleportation jumps
                d_pen = math.hypot(target_pen[0] - current_pen[0], target_pen[1] - current_pen[1])
                max_step = max(35.0, min(110.0, d_pen * 0.45))
                if d_pen > max_step:
                    current_pen = (
                        current_pen[0] + (target_pen[0] - current_pen[0]) * (max_step / d_pen),
                        current_pen[1] + (target_pen[1] - current_pen[1]) * (max_step / d_pen)
                    )
                else:
                    current_pen = (
                        current_pen[0] * 0.25 + target_pen[0] * 0.75,
                        current_pen[1] * 0.25 + target_pen[1] * 0.75
                    )
                live_canvas[gy:gy+gh, gx:gx+gw][p_m > 0] = art[p_m > 0]

            else:
                # Restful hold or glide towards next element/panel
                if curr_time >= active_p["end_time"] - 0.25 and p_idx < len(placed_panels) - 1:
                    next_p = placed_panels[p_idx + 1]
                    target_d = (next_p["gx"] + next_p["gw"] * 0.70, next_p["gy"] + 60.0)
                    current_pen = (
                        current_pen[0] + (target_d[0] - current_pen[0]) * 0.20,
                        current_pen[1] + (target_d[1] - current_pen[1]) * 0.20
                    )
                else:
                    # Subtle organic idle drift during visual hold
                    current_pen = (
                        current_pen[0] + 0.25 * math.sin(curr_time * 2.0),
                        current_pen[1] + 0.25 * math.cos(curr_time * 2.0)
                    )

            # Ensure finished objects are fully revealed without sudden pops
            for p in placed_panels:
                gx_p, gy_p, gw_p, gh_p = p["gx"], p["gy"], p["gw"], p["gh"]
                art_p = p["hd_artwork"]
                p_mask = panel_drawn_masks[p["global_id"]]
                for obj in p["objects"]:
                    if curr_time >= obj["sync_end"]:
                        # Finish drawing any remaining stroke points
                        s_pts_obj = obj["stroke_pts"]
                        if obj["last_drawn_idx"] < len(s_pts_obj) - 1:
                            brush_r = 8 if obj["category"] in ("TITLE", "TEXT_LINE", "TEXT") else 10
                            for i in range(obj["last_drawn_idx"], len(s_pts_obj)):
                                lx = int(round(s_pts_obj[i][0] - gx_p))
                                ly = int(round(s_pts_obj[i][1] - gy_p))
                                if 0 <= lx < gw_p and 0 <= ly < gh_p:
                                    cv2.circle(p_mask, (lx, ly), brush_r, 255, -1)
                                    if i > 0:
                                        plx = int(round(s_pts_obj[i-1][0] - gx_p))
                                        ply = int(round(s_pts_obj[i-1][1] - gy_p))
                                        if math.hypot(lx - plx, ly - ply) <= 26.0:
                                            cv2.line(p_mask, (plx, ply), (lx, ly), 255, thickness=brush_r * 2)
                            obj["last_drawn_idx"] = len(s_pts_obj) - 1

                        sm = obj.get("scaled_mask")
                        if sm is not None:
                            p_mask[sm > 0] = 255
                live_canvas[gy_p:gy_p+gh_p, gx_p:gx_p+gw_p][p_mask > 0] = art_p[p_mask > 0]

            # Render Camera Viewport
            M = get_camera_affine_matrix(cam_x, cam_y, cam_zoom, cam_tilt, out_w, out_h)
            viewport = render_camera_viewport_with_matrix(live_canvas, M, out_w, out_h)

            scr_tip_x, scr_tip_y = canvas_to_screen_pt(M, current_pen)

            composited = composite_hand_on_canvas_fast(
                viewport,
                hand_screen,
                tip_x_screen,
                tip_y_screen,
                int(round(scr_tip_x)),
                int(round(scr_tip_y))
            )

            # Write Video Frame
            vf = av.VideoFrame.from_ndarray(composited, format="bgr24")
            vf.pts = frame_idx
            for pkt in v_stream.encode(vf):
                container.mux(pkt)

            if (frame_idx + 1) % 90 == 0 or frame_idx == total_frames - 1:
                pct = ((frame_idx + 1) / float(total_frames)) * 100.0
                cur_s = (frame_idx + 1) / float(fps)
                print(f"  • Progress: {pct:05.1f}% | Time: {cur_s:05.1f}s / {total_duration:.1f}s (Frame {frame_idx+1}/{total_frames})")

        # Flush video
        for pkt in v_stream.encode():
            container.mux(pkt)

        # 6. Mux Audio Track
        print("\n[DynamicWhiteboardRenderer] Muxing master audio stream...")
        for a_frame in in_aud.decode(in_aud_stream):
            t_s = float(a_frame.pts * in_aud_stream.time_base) if a_frame.pts is not None else 0.0
            if t_s > total_duration + 0.10:
                break
            a_frame.pts = None
            for pkt in a_stream.encode(a_frame):
                container.mux(pkt)

        for pkt in a_stream.encode():
            container.mux(pkt)

        container.close()
        in_aud.close()

        print("\n=========================================================================================")
        print("🎉 MASTER WHITEBOARD ANIMATION COMPLETED SUCCESSFULLY! 🎉")
        print(f"  • Final Output Video: {output_video_path}")
        print(f"  • Total Duration    : {total_duration:.2f}s")
        print(f"  • Total Panels      : {num_panels}")
        print("=========================================================================================")
        return output_video_path

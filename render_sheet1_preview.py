"""
Production Whiteboard Animation Renderer for Storyboard Sheet 1 (Panels 01 to 06)
Renders a 1080p synchronized whiteboard animation video with:
- 3x2 grid layout matching the 2D Kurzgesagt storyboard Sheet 1
- Full hand-drawn concentric inking with subpixel pen-tip alignment
- Speech-synchronized timing across all 6 panels (00:00 to 01:30, 89.91s total)
- Smooth cinematic camera panning, row-return crane easing, and grand outro reveal
- Lossless AAC/H.264 audio-video muxing using sheet1_master_audio.wav
- Milestone diagnostic frame extraction for visual review
"""
import os
import sys
import math
import time
import cv2
import av
import numpy as np

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


def render_sheet1_video():
    print("=" * 100)
    print("      🎬 STARTING SHEET 1 PRODUCTION WHITEBOARD ANIMATION (PANELS 01-06) 🎬                   ")
    print("=" * 100)
    start_total_time = time.time()

    # 1. Inputs
    img_path = os.path.join(ROOT_DIR, "project_content", "images", "sheet1_iq_foundations.jpg")
    audio_path = os.path.join(ROOT_DIR, "project_content", "audio", "sheet1_master_audio.wav")
    output_mp4 = os.path.join(ROOT_DIR, "output_animations", "sheet1_whiteboard_preview.mp4")
    os.makedirs(os.path.dirname(output_mp4), exist_ok=True)

    if not os.path.exists(img_path):
        raise FileNotFoundError(f"Storyboard sheet image not found: {img_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Master audio track not found: {audio_path}")

    # Audio duration
    in_aud = av.open(audio_path)
    in_aud_stream = in_aud.streams.audio[0]
    total_duration = float(in_aud_stream.duration * in_aud_stream.time_base) if in_aud_stream.duration else 89.91
    in_aud.close()

    fps = 30
    out_w = 1920
    out_h = 1080
    zoom_level = 1.32
    total_frames = int(round(total_duration * fps))

    print(f"  • Image Sheet: {os.path.basename(img_path)}")
    print(f"  • Audio File : {os.path.basename(audio_path)} (Duration: {total_duration:.2f}s)")
    print(f"  • Output MP4 : {output_mp4}")
    print(f"  • Resolution : {out_w}x{out_h} @ {fps}fps ({total_frames} frames)")

    # 2. Panel Extraction
    print("\n[Step 1/5] Extracting and segmenting panels from Sheet 1...")
    sheet_img = cv2.imread(img_path)
    discovered = WhiteboardProcessor.discover_panels(sheet_img)
    print(f"  • Discovered {len(discovered)} panels in 3x2 grid.")

    # Ground truth audio timestamps based on narrative pauses
    # Panel 01: 0.0s -> 15.0s (15.0s) - المستوى التأسيسي (< 70)
    # Panel 02: 15.0s -> 34.5s (19.5s) - كيف تبدو الحياة؟ (الدماغ وحالة إيرور)
    # Panel 03: 34.5s -> 48.5s (14.0s) - مهارات أساسية ورعاية الآخرين
    # Panel 04: 48.5s -> 71.5s (23.0s) - راحة البال والعيش في اللحظة
    # Panel 05: 71.5s -> 81.0s (9.5s) - ذكاء الشوارع (70-84)
    # Panel 06: 81.0s -> 89.91s (8.91s) - المدرسة وإغلاق الكتاب
    panel_timings = [
        {"id": 1, "start": 0.0, "end": 15.0, "title": "المستوى التأسيسي (< 70)"},
        {"id": 2, "start": 15.0, "end": 34.5, "title": "الدماغ وحالة إيرور"},
        {"id": 3, "start": 34.5, "end": 48.5, "title": "المهام الروتينية والرعاية"},
        {"id": 4, "start": 48.5, "end": 71.5, "title": "راحة البال والعيش في اللحظة"},
        {"id": 5, "start": 71.5, "end": 81.0, "title": "ذكاء الشوارع (70-84)"},
        {"id": 6, "start": 81.0, "end": total_duration, "title": "معاناة المدرسة وإغلاق الكتاب"}
    ]

    processed_panels = []
    for idx, p_info in enumerate(discovered):
        px, py, pw, ph = p_info["bbox"]
        raw_crop = sheet_img[py:py+ph, px:px+pw]
        border_res = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)
        clean_crop = border_res["clean_crop"]

        panel_res = PanelPipeline.process_panel(
            clean_crop,
            panel_id=idx + 1,
            ignore_badges=True
        )

        timing = panel_timings[idx]
        processed_panels.append({
            "global_id": idx + 1,
            "title": timing["title"],
            "start_time": timing["start"],
            "end_time": timing["end"],
            "duration": timing["end"] - timing["start"],
            "raw_w": clean_crop.shape[1],
            "raw_h": clean_crop.shape[0],
            "clean_crop": panel_res["clean_crop"],
            "objects": panel_res["objects"]
        })
        print(f"  • Panel {idx+1}: [{timing['start']:04.1f}s -> {timing['end']:04.1f}s] ({timing['end']-timing['start']:04.1f}s) | Objs: {len(panel_res['objects'])} | {timing['title']}")

    from engine.pipeline.semantic_narrative_auditor import SemanticNarrativeAuditor

    # Apply Semantic Narrative Audit & Sequence Choreography
    print("\n[Audit & Alignment] Running Semantic Narrative Auditor...")
    reordered_panels, audit_report = SemanticNarrativeAuditor.audit_and_reorder_sheet1_panels(processed_panels)

    total_inconsistencies = sum(r["inconsistencies_detected"] for r in audit_report)
    print(f"  • Total Narrative Inconsistencies Detected & Corrected: {total_inconsistencies}")
    for r in audit_report:
        if r["inconsistencies_detected"] > 0:
            print(f"    - Panel {r['panel_id']} ({r['title']}): {r['inconsistencies_detected']} out-of-order elements resolved.")

    # 3. Canvas Geometry (3 columns x 2 rows)
    cols = 3
    rows = 2
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

    print(f"\n[Step 2/5] Canvas Layout: {canvas_w}x{canvas_h} | Grid: {grid_w}x{grid_h} (3x2 panels, each {target_p_w}x{target_p_h})")

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

    # 4. Load Hand Asset
    print("\n[Step 3/5] Loading realistic artist hand asset...")
    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_screen_h = int(out_h * 0.38)
    scale_hand = hand_screen_h / float(hand_bgra.shape[0])
    hand_screen_w = max(1, int(hand_bgra.shape[1] * scale_hand))
    hand_screen = cv2.resize(hand_bgra, (hand_screen_w, hand_screen_h), interpolation=cv2.INTER_AREA)
    tip_x_screen = int(round(PEN_TIP_ANCHOR_X * scale_hand))
    tip_y_screen = int(round(PEN_TIP_ANCHOR_Y * scale_hand))

    # 5. Initialize Hardware-Accelerated Video Encoder + Audio Container
    print("\n[Step 4/5] Initializing GPU NVENC hardware video encoder and AAC audio...")
    container = av.open(output_mp4, mode="w")

    v_codec = "h264_nvenc"
    try:
        tc = av.open(os.devnull, mode="w", format="mp4")
        tc.add_stream("h264_nvenc", rate=fps)
        tc.close()
    except Exception:
        print("  • NVENC test failed, falling back to CPU h264...")
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

    # 6. Main Render Loop
    print("\n[Step 5/5] Executing Whiteboard Animation Rendering Engine...")
    current_pen = (placed_panels[0]["gx"] + placed_panels[0]["gw"] * 0.7, placed_panels[0]["gy"] + 60.0)

    board_center = (canvas_w / 2.0, canvas_h / 2.0)
    board_zoom = min(out_w / float(grid_w + 240), out_h / float(grid_h + 180)) * 0.95
    outro_start_time = total_duration - 3.2

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

        # Grand Outro Reveal during final 3.2s
        if curr_time >= outro_start_time:
            t_outro = (curr_time - outro_start_time) / 3.2
            t_ease = smootherstep(t_outro)
            cam_x = target_cam[0] + (board_center[0] - target_cam[0]) * t_ease
            cam_y = target_cam[1] + (board_center[1] - target_cam[1]) * t_ease
            cam_zoom = zoom_level + (board_zoom - zoom_level) * t_ease
            cam_tilt = 0.0

            # Hand glides smoothly offscreen bottom-right
            off_pen = (canvas_w + 600.0, canvas_h + 600.0)
            current_pen = (
                current_pen[0] + (off_pen[0] - current_pen[0]) * 0.15,
                current_pen[1] + (off_pen[1] - current_pen[1]) * 0.15
            )

        else:
            # Panel-to-panel camera transitions
            is_row_return = (p_idx == 3)  # Transition from Panel 3 (Row 0) to Panel 4 (Row 1)
            trans_dur = 0.60 if is_row_return else 0.38
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
                dip = 0.28 if is_row_return else 0.16
                cam_zoom = zoom_level - dip * math.sin(t_ease * math.pi)
                cam_tilt = (1.0 if dx >= 0 else -1.0) * (1.5 if is_row_return else 1.0) * math.sin(t_ease * math.pi)
            else:
                cam_x, cam_y = target_cam
                cam_zoom = zoom_level
                cam_tilt = 0.0

            # Active drawing elements
            active_drawing_objs = [
                obj for obj in active_p["objects"]
                if obj["sync_start"] <= curr_time <= obj["sync_end"] and len(obj["stroke_pts"]) > 0
            ]

            p_m = panel_drawn_masks[active_p["global_id"]]
            gx, gy = active_p["gx"], active_p["gy"]
            gw, gh = active_p["gw"], active_p["gh"]
            art = active_p["hd_artwork"]

            if active_drawing_objs:
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

                # Natural human hand easing without teleportation jumps
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
                # Holding state / smooth glide to next panel
                if curr_time >= active_p["end_time"] - 0.25 and p_idx < len(placed_panels) - 1:
                    next_p = placed_panels[p_idx + 1]
                    target_d = (next_p["gx"] + next_p["gw"] * 0.70, next_p["gy"] + 60.0)
                    current_pen = (
                        current_pen[0] + (target_d[0] - current_pen[0]) * 0.20,
                        current_pen[1] + (target_d[1] - current_pen[1]) * 0.20
                    )
                else:
                    current_pen = (
                        current_pen[0] + 0.25 * math.sin(curr_time * 2.0),
                        current_pen[1] + 0.25 * math.cos(curr_time * 2.0)
                    )

        # Reveal completed objects
        for p in placed_panels:
            gx_p, gy_p, gw_p, gh_p = p["gx"], p["gy"], p["gw"], p["gh"]
            art_p = p["hd_artwork"]
            p_mask = panel_drawn_masks[p["global_id"]]
            for obj in p["objects"]:
                if curr_time >= obj["sync_end"]:
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

        # Camera Viewport Transformation
        M = get_camera_affine_matrix(cam_x, cam_y, cam_zoom, cam_tilt, out_w, out_h)
        viewport = render_camera_viewport_with_matrix(live_canvas, M, out_w, out_h)

        scr_tip_x, scr_tip_y = canvas_to_screen_pt(M, current_pen)

        # Hand Compositing (hidden if moved far off-screen)
        if -500 <= scr_tip_x <= out_w + 500 and -500 <= scr_tip_y <= out_h + 500:
            composited = composite_hand_on_canvas_fast(
                viewport,
                hand_screen,
                tip_x_screen,
                tip_y_screen,
                int(round(scr_tip_x)),
                int(round(scr_tip_y))
            )
        else:
            composited = viewport

        # Encode Frame
        vf = av.VideoFrame.from_ndarray(composited, format="bgr24")
        vf.pts = frame_idx
        for pkt in v_stream.encode(vf):
            container.mux(pkt)

        if (frame_idx + 1) % 90 == 0 or frame_idx == total_frames - 1:
            pct = ((frame_idx + 1) / float(total_frames)) * 100.0
            cur_s = (frame_idx + 1) / float(fps)
            print(f"  • Progress: {pct:05.1f}% | Time: {cur_s:05.1f}s / {total_duration:.1f}s (Frame {frame_idx+1}/{total_frames})")

    # Flush Video Stream
    for pkt in v_stream.encode():
        container.mux(pkt)

    # 7. Mux Audio Stream
    print("\n[Muxing Audio] Synchronizing master voiceover audio track...")
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

    total_elapsed = time.time() - start_total_time
    print(f"\n✅ Video render completed in {total_elapsed:.1f}s ({total_elapsed/60.0:.2f} min).")
    print(f"✅ Final Video: {output_mp4}")

    # 8. Milestone Diagnostic Frame Extraction
    print("\n[Extracting Frames] Generating visual milestone inspection frames...")
    diag_dir = os.path.join(ROOT_DIR, "scratch", "sheet1_inspection_frames")
    os.makedirs(diag_dir, exist_ok=True)

    milestones = [
        (4.0, "panel01_narrator_scale"),
        (14.0, "panel01_complete_crowd"),
        (22.0, "panel02_brain_maze"),
        (33.5, "panel02_complete_error"),
        (36.0, "panel03_step1_jacket"),
        (39.0, "panel03_step2_grocery_cart"),
        (41.5, "panel03_step3_delivery_worker"),
        (45.0, "panel03_step4_caregiver_feeding"),
        (52.0, "panel04_step1_stress_cloud"),
        (62.0, "panel04_step2_peaceful_moment"),
        (72.5, "panel05_step1_14percent_indicator"),
        (77.0, "panel05_step2_street_crowd_walking"),
        (85.0, "panel06_school_struggle"),
        (89.0, "full_sheet1_outro_reveal")
    ]

    cap = cv2.VideoCapture(output_mp4)
    fps_val = cap.get(cv2.CAP_PROP_FPS) or 30.0

    saved_frames = []
    for sec, label in milestones:
        f_no = int(round(sec * fps_val))
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_no)
        ret, frame = cap.read()
        if ret and frame is not None:
            f_path = os.path.join(diag_dir, f"frame_{sec:05.1f}s_{label}.jpg")
            cv2.imwrite(f_path, frame)
            saved_frames.append((sec, label, f_path))
            print(f"  📸 Saved frame at {sec:05.1f}s: {f_path}")

    cap.release()
    print("\n🎉 SHEET 1 VIDEO GENERATION & INSPECTION COMPLETE! 🎉\n")
    return output_mp4, saved_frames


if __name__ == "__main__":
    render_sheet1_video()

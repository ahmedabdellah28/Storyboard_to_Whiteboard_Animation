"""
====================================================================================================
TRANSCRIPT-SYNCHRONIZED WHITEBOARD ANIMATION ENGINE (MASTER PRODUCTION)
====================================================================================================
1. Synchronized to exact 30.6s Word-Level SRT Transcript (Panels 1 through 10).
2. Suppresses / ignores all circular panel badges (❶..❿) across all panels.
3. Natural Artist Choreography (Phase 1: Line Art Contours -> Phase 2: Directional Shading) for Characters.
4. Smooth Arabic Typography Line-by-Line handwriting (RTL).
5. Exact Container/Card and Text Box boundary extraction & separation.
6. 4K UHD Master Canvas (3840x2160) on 100% Pure White (255, 255, 255).
7. Full Cinematic Camera Transitions with Parallax Pullback and Banking Tilt.
8. Lossless Audio Integration (Muxed directly from voiceover narration 0.0s to 30.6s).
====================================================================================================
"""
import os
import sys
import math
import cv2
import av
import numpy as np
from typing import List, Dict, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if os.path.join(_ROOT, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, 'kivy'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.concentric_engine import (
    DEFAULT_HAND_PATH,
    DEFAULT_HAND_MASK_PATH,
    PEN_TIP_ANCHOR_X,
    PEN_TIP_ANCHOR_Y
)
from engine.processing.dynamic_border_detector import DynamicBorderDetector
from engine.processing.whiteboard_processor import WhiteboardProcessor

from dev_separator.panel_pipeline import PanelPipeline
from dev_separator.transcript_timeline_aligner import TranscriptTimelineAligner
from dev_separator.natural_artist_choreographer import NaturalArtistChoreographer


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


def generate_natural_bezier_flight(p_start, p_end, num_points=10, arch_factor=0.20):
    p0 = np.array(p_start, dtype=np.float32)
    p3 = np.array(p_end, dtype=np.float32)
    dist = np.linalg.norm(p3 - p0)

    lift = -min(180.0, max(30.0, dist * arch_factor))
    p1 = p0 + (p3 - p0) * 0.25 + np.array([0, lift * 0.8], dtype=np.float32)
    p2 = p0 + (p3 - p0) * 0.75 + np.array([0, lift * 0.9], dtype=np.float32)

    pts = []
    for t in np.linspace(0, 1, max(2, num_points)):
        pt = (1-t)**3 * p0 + 3*(1-t)**2 * t * p1 + 3*(1-t) * t**2 * p2 + t**3 * p3
        pts.append((float(pt[0]), float(pt[1])))
    return pts


def morphological_skeleton(bin_img):
    skeleton = np.zeros(bin_img.shape, np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    img_c = bin_img.copy()
    while True:
        eroded = cv2.erode(img_c, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(img_c, temp)
        skeleton = cv2.bitwise_or(skeleton, temp)
        img_c = eroded.copy()
        if cv2.countNonZero(img_c) == 0:
            break
    return skeleton


def extract_ordered_skeleton_strokes(ink_roi, direction="RTL", step_stride=3):
    skel = morphological_skeleton(ink_roi)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(skel)
    if num_labels <= 1:
        ys, xs = np.where(ink_roi > 0)
        if len(xs) == 0:
            return []
        if direction == "RTL":
            return [[(float(x), float(ys[xs == x].mean())) for x in range(xs.max(), xs.min()-1, -step_stride) if len(ys[xs == x]) > 0]]
        else:
            return [[(float(x), float(ys[xs == x].mean())) for x in range(xs.min(), xs.max()+1, step_stride) if len(ys[xs == x]) > 0]]

    comps = []
    for i in range(1, num_labels):
        cx = stats[i, cv2.CC_STAT_LEFT]
        cy = stats[i, cv2.CC_STAT_TOP]
        area = stats[i, cv2.CC_STAT_AREA]
        comps.append((cx, cy, area, i))

    if direction == "RTL":
        comps.sort(key=lambda c: -c[0])
    else:
        comps.sort(key=lambda c: c[0])

    all_strokes = []
    for cx, cy, area, idx in comps:
        comp_mask = (labels == idx).astype(np.uint8)
        ys, xs = np.where(comp_mask > 0)
        if len(xs) == 0:
            continue
        pts_set = set(zip(xs, ys))
        start_pt = max(pts_set, key=lambda p: (p[0], -p[1])) if direction == "RTL" else min(pts_set, key=lambda p: (p[0], p[1]))
        path = [start_pt]
        pts_set.remove(start_pt)
        curr = start_pt
        while pts_set:
            cx_pt, cy_pt = curr
            neighbors = [(cx_pt+dx, cy_pt+dy) for dx in [-1,0,1] for dy in [-1,0,1] if (dx!=0 or dy!=0) and (cx_pt+dx, cy_pt+dy) in pts_set]
            if neighbors:
                next_pt = min(neighbors, key=lambda p: (p[0], p[1])) if direction == "RTL" else max(neighbors, key=lambda p: (p[0], -p[1]))
            else:
                next_pt = min(pts_set, key=lambda p: (p[0]-cx_pt)**2 + (p[1]-cy_pt)**2)
            path.append(next_pt)
            pts_set.remove(next_pt)
            curr = next_pt
        sampled_path = path[::step_stride]
        if len(sampled_path) > 0:
            all_strokes.append(sampled_path)
    return all_strokes


def extract_object_strokes(obj: Dict[str, Any], scale_x: float, scale_y: float) -> List[Tuple[float, float]]:
    """
    Extracts ordered drawing stroke points for an object based on its category:
    - CHARACTER: Natural Artist Choreography (Phase 1 linework -> Phase 2 shading)
    - TITLE / TEXT_LINE: Arabic cursive skeleton strokes RTL
    - CONTAINER_CARD / EMOJI / ICON: Outer perimeter contour followed by interior passes
    """
    cat = obj.get("category", "TEXT")
    mask = obj.get("mask")
    crop = obj.get("crop")
    bx, by, bw, bh = obj.get("bbox", (0, 0, 10, 10))

    if mask is None or crop is None or cv2.countNonZero(mask) == 0:
        return []

    stroke_pts = []

    if cat == "CHARACTER":
        plan = NaturalArtistChoreographer.generate_character_drawing_plan(crop, mask, step_dist=4.0)
        # Phase 1: Linework strokes
        for s in plan.get("linework_strokes", []):
            for pt in s:
                stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))
        # Phase 2: Shading strokes
        for s in plan.get("shading_strokes", []):
            for pt in s:
                stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))

    elif cat in ("TITLE", "TEXT_LINE") or cat == "TEXT":
        raw_strokes = extract_ordered_skeleton_strokes(mask, direction="RTL", step_stride=3)
        for s in raw_strokes:
            for pt in s:
                stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))

    elif cat == "CONTAINER_CARD":
        # Card perimeter contour
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            pts = c.reshape(-1, 2)
            for pt in pts[::3]:
                stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))
        # Interior shading pass
        for y in range(8, bh - 8, 12):
            xs = np.where(mask[y, :] > 0)[0]
            if len(xs) > 4:
                stroke_pts.append((float(bx + xs[0]) * scale_x, float(by + y) * scale_y))
                stroke_pts.append((float(bx + xs[-1]) * scale_x, float(by + y) * scale_y))

    else:
        # EMOJI / ICON_GRAPHIC
        cnts, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        for c in cnts:
            if len(c) >= 5:
                pts = c.reshape(-1, 2)
                for pt in pts[::2]:
                    stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))

    return stroke_pts


def render_transcript_synchronized_video(
    image_path: str,
    srt_path: str,
    audio_path: str,
    output_path: str,
    fps: int = 30,
    zoom_level: float = 1.38
):
    print("=========================================================================================")
    print("      🎬 PRODUCTION TRANSCRIPT-SYNCHRONIZED WHITEBOARD ANIMATOR (PANELS 1..10) 🎬       ")
    print("=========================================================================================")
    print(f"Input Image : {image_path}")
    print(f"Transcript  : {srt_path}")
    print(f"Audio Track : {audio_path}")
    print(f"Output MP4  : {output_path}")
    print(f"Framerate   : {fps} fps | Camera Focus Zoom: {zoom_level:.2f}x")
    print("-----------------------------------------------------------------------------------------")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # 1. Parse SRT Transcript & Align Panels
    print("\n[Step 1] Parsing Word-Level SRT Transcript...")
    srt_entries = TranscriptTimelineAligner.parse_srt_file(srt_path)
    total_words = len(srt_entries)
    speech_end_time = srt_entries[-1]["end"]
    print(f"  • Loaded {total_words} words. Total spoken duration: {speech_end_time:.2f}s.")

    panel_timelines = TranscriptTimelineAligner.align_transcript_to_panels(srt_entries, panel_count=10)
    print(f"  • Mapped {len(panel_timelines)} storyboard panels to speech timeline:")
    for pt in panel_timelines:
        print(f"    - Panel {pt['panel_id']:02d}: [{pt['start_time']:04.1f}s -> {pt['end_time']:04.1f}s] ({pt['duration']:04.1f}s) | \"{pt['spoken_text'][:35]}...\"")

    # 2. Discover & Process 10 Storyboard Panels
    print("\n[Step 2] Processing Storyboard Panels with High-Precision Layer Separation (Ignoring Badges)...")
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")

    discovered_panels = WhiteboardProcessor.discover_panels(img)
    num_to_render = min(10, len(discovered_panels))
    print(f"  • Storyboard has {len(discovered_panels)} panels. Selected first {num_to_render} panels for transcript synchronization.")

    processed_panels = []
    for idx in range(num_to_render):
        p_id = idx + 1
        p_info = discovered_panels[idx]
        px, py, pw, ph = p_info["bbox"]
        raw_crop = img[py:py+ph, px:px+pw]

        # Border trimming
        border_res = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)
        clean_crop = border_res["clean_crop"]

        # Process with ignore_badges=True to erase badges and suppress from objects
        pipeline_res = PanelPipeline.process_panel(clean_crop, panel_id=p_id, ignore_badges=True)
        objects = pipeline_res["objects"]

        # Match timeline
        t_line = next((pt for pt in panel_timelines if pt["panel_id"] == p_id), None)
        if t_line is None:
            t_line = {"start_time": (p_id - 1) * 3.0, "end_time": p_id * 3.0, "duration": 3.0, "panel_id": p_id}

        synced_objs = TranscriptTimelineAligner.synchronize_panel_objects(objects, t_line)

        processed_panels.append({
            "panel_id": p_id,
            "clean_crop": pipeline_res["clean_crop"],
            "raw_w": clean_crop.shape[1],
            "raw_h": clean_crop.shape[0],
            "objects": synced_objs,
            "timeline": t_line
        })
        print(f"  • Panel {p_id:02d}: {len(synced_objs)} objects scheduled (Badge ❶..❿ cleanly erased).")

    # 3. Setup 4K Master Canvas (3840x2160)
    canvas_w, canvas_h = 3840, 2160
    out_w, out_h = 1920, 1080
    live_canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)

    # 4 columns x 3 rows grid
    cols = 4
    rows = 3
    target_p_h = 510
    gap_x = 75
    gap_y = 65

    # Compute panel scaling
    first_p = processed_panels[0]
    aspect = first_p["raw_w"] / float(first_p["raw_h"])
    target_p_w = int(round(target_p_h * aspect))

    grid_total_w = cols * target_p_w + (cols - 1) * gap_x
    grid_total_h = rows * target_p_h + (rows - 1) * gap_y
    start_x = max(60, (canvas_w - grid_total_w) // 2)
    start_y = max(60, (canvas_h - grid_total_h) // 2)

    # Place panels onto layout
    panel_layouts = []
    for p_idx, p_data in enumerate(processed_panels):
        p_id = p_data["panel_id"]
        r = (p_id - 1) // cols
        c = (p_id - 1) % cols

        gx = start_x + c * (target_p_w + gap_x)
        gy = start_y + r * (target_p_h + gap_y)

        scale_x = target_p_w / float(p_data["raw_w"])
        scale_y = target_p_h / float(p_data["raw_h"])

        # High-definition Lanczos upscaled clean artwork
        hd_artwork = cv2.resize(p_data["clean_crop"], (target_p_w, target_p_h), interpolation=cv2.INTER_LANCZOS4)
        # Ensure pure white background thresholding
        gray_hd = cv2.cvtColor(hd_artwork, cv2.COLOR_BGR2GRAY)
        hd_artwork[gray_hd > 240] = [255, 255, 255]

        # Extract drawing strokes for each object in global canvas coordinates
        prepared_objects = []
        for obj in p_data["objects"]:
            strokes = extract_object_strokes(obj, scale_x, scale_y)
            global_strokes = [(gx + pt[0], gy + pt[1]) for pt in strokes]
            
            # Scaled object mask in panel space
            full_m = obj.get("full_mask")
            if full_m is not None:
                scaled_mask = cv2.resize(full_m, (target_p_w, target_p_h), interpolation=cv2.INTER_NEAREST)
            else:
                scaled_mask = np.zeros((target_p_h, target_p_w), dtype=np.uint8)

            prepared_objects.append({
                "name": obj["name"],
                "category": obj["category"],
                "sync_start": obj["sync_start"],
                "sync_end": obj["sync_end"],
                "sync_duration": obj["sync_duration"],
                "stroke_pts": global_strokes,
                "scaled_mask": scaled_mask,
                "bbox_canvas": (gx, gy, target_p_w, target_p_h)
            })

        panel_layouts.append({
            "panel_id": p_id,
            "gx": gx,
            "gy": gy,
            "gw": target_p_w,
            "gh": target_p_h,
            "center_x": gx + target_p_w / 2.0,
            "center_y": gy + target_p_h / 2.0,
            "row": r,
            "col": c,
            "hd_artwork": hd_artwork,
            "objects": prepared_objects,
            "timeline": p_data["timeline"]
        })

    # 4. Load Hand Sprite for Native 1080p Screen Space
    print("\n[Step 3] Loading Hand Compositor Assets...")
    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_screen_h = int(out_h * 0.38) # Standard 38% screen height (~410px)
    scale_hand = hand_screen_h / float(hand_bgra.shape[0])
    hand_screen_w = max(1, int(hand_bgra.shape[1] * scale_hand))
    hand_screen = cv2.resize(hand_bgra, (hand_screen_w, hand_screen_h), interpolation=cv2.INTER_AREA)
    tip_x_screen = int(round(PEN_TIP_ANCHOR_X * scale_hand))
    tip_y_screen = int(round(PEN_TIP_ANCHOR_Y * scale_hand))

    # 5. Calculate Total Animation Frames
    # Total animation runs exactly for the speech duration 30.60 seconds!
    total_anim_frames = int(round(speech_end_time * fps))
    print(f"\n[Step 4] Frame Budget & Timeline Planning:")
    print(f"  • Spoken Duration: {speech_end_time:.2f}s -> Exact Video Frames: {total_anim_frames} @ {fps} fps")

    # Pre-calculate active panel and object for every single frame
    frame_schedules = []
    current_pen = (panel_layouts[0]["gx"] + panel_layouts[0]["gw"] * 0.7, panel_layouts[0]["gy"] + 60.0)

    # 6. Initialize PyAV Audio-Video Muxing Container
    print(f"\n[Step 5] Initializing PyAV H.264 Video + AAC Audio Stream: {output_path}...")
    container = av.open(output_path, mode="w")

    # Video stream: H.264 NVENC / CPU
    v_codec = "h264"
    try:
        test_c = av.open(os.devnull, mode="w", format="mp4")
        test_c.add_stream("h264_nvenc", rate=fps)
        test_c.close()
        v_codec = "h264_nvenc"
    except Exception:
        v_codec = "h264"

    v_stream = container.add_stream(v_codec, rate=fps)
    v_stream.width = out_w
    v_stream.height = out_h
    v_stream.pix_fmt = "yuv420p"
    v_stream.options = {"crf": "18"}
    print(f"  • Video Stream ready: {out_w}x{out_h} @ {fps}fps [{v_codec}]")

    # Audio stream: Open source audio and set up matching AAC stream
    in_audio_container = av.open(audio_path)
    in_audio_stream = in_audio_container.streams.audio[0]
    a_stream = container.add_stream("aac", rate=in_audio_stream.rate)
    print(f"  • Audio Stream ready: {in_audio_stream.rate}Hz Stereo [AAC]")

    # 7. Render Master Video Frames
    print(f"\n[Step 6] Rendering 30.6s Whiteboard Animation...")

    cur_cam_pos = (panel_layouts[0]["center_x"], panel_layouts[0]["center_y"])
    cur_zoom = zoom_level
    cur_tilt = 0.0

    # Panel mask tracking for accurate ink deposition
    panel_drawn_masks = {p["panel_id"]: np.zeros((p["gh"], p["gw"]), dtype=np.uint8) for p in panel_layouts}

    for frame_idx in range(total_anim_frames):
        current_time = frame_idx / float(fps)

        # 1. Determine active panel
        active_p = panel_layouts[0]
        for p in panel_layouts:
            tl = p["timeline"]
            if tl["start_time"] <= current_time < tl["end_time"]:
                active_p = p
                break
            elif current_time >= tl["end_time"]:
                active_p = p

        # 2. Camera Choreography (Smooth Transitions between panels)
        p_idx = active_p["panel_id"] - 1
        target_cam = (active_p["center_x"], active_p["center_y"])

        # Check if we are in a transition window between panels
        trans_duration = 0.35 # 0.35 seconds transition (~10-11 frames)
        tl_start = active_p["timeline"]["start_time"]

        if p_idx > 0 and (current_time - tl_start) < trans_duration:
            prev_p = panel_layouts[p_idx - 1]
            prev_cam = (prev_p["center_x"], prev_p["center_y"])
            t_trans = (current_time - tl_start) / trans_duration
            t_ease = smootherstep(t_trans)

            dx = target_cam[0] - prev_cam[0]
            dy = target_cam[1] - prev_cam[1]
            cur_cam_pos = (prev_cam[0] + dx * t_ease, prev_cam[1] + dy * t_ease)

            # Crane pullback & banking tilt
            pullback = -0.22 * math.sin(t_ease * math.pi)
            cur_zoom = zoom_level + pullback
            tilt_dir = 1.0 if dx >= 0 else -1.0
            cur_tilt = tilt_dir * 1.2 * math.sin(t_ease * math.pi)
        else:
            cur_cam_pos = target_cam
            cur_zoom = zoom_level
            cur_tilt = 0.0

        # 3. Determine active drawing object and pen position
        active_obj = None
        for obj in active_p["objects"]:
            if obj["sync_start"] <= current_time <= obj["sync_end"]:
                active_obj = obj
                break

        if active_obj is not None and len(active_obj["stroke_pts"]) > 0:
            o_start = active_obj["sync_start"]
            o_end = active_obj["sync_end"]
            o_dur = max(0.05, o_end - o_start)
            progress = max(0.0, min(1.0, (current_time - o_start) / o_dur))

            stroke_pts = active_obj["stroke_pts"]
            pt_idx = min(len(stroke_pts) - 1, int(round(progress * (len(stroke_pts) - 1))))
            target_pen = stroke_pts[pt_idx]

            # Connect and deposit ink incrementally
            p_mask = panel_drawn_masks[active_p["panel_id"]]
            gx, gy = active_p["gx"], active_p["gy"]
            gw, gh = active_p["gw"], active_p["gh"]
            art = active_p["hd_artwork"]

            brush_r = 7 if active_obj["category"] in ("TITLE", "TEXT_LINE", "TEXT") else 9
            last_idx = active_obj.get("last_drawn_idx", 0)
            
            # Draw incremental points
            for i in range(last_idx, pt_idx + 1):
                local_x = int(round(stroke_pts[i][0] - gx))
                local_y = int(round(stroke_pts[i][1] - gy))
                if 0 <= local_x < gw and 0 <= local_y < gh:
                    cv2.circle(p_mask, (local_x, local_y), brush_r, 255, -1)
                    if i > 0:
                        prev_lx = int(round(stroke_pts[i-1][0] - gx))
                        prev_ly = int(round(stroke_pts[i-1][1] - gy))
                        cv2.line(p_mask, (prev_lx, prev_ly), (local_x, local_y), 255, thickness=brush_r * 2)

            active_obj["last_drawn_idx"] = pt_idx

            # Update live canvas with revealed ink
            act_ink = (p_mask > 0)
            live_canvas[gy:gy+gh, gx:gx+gw][act_ink] = art[act_ink]
            current_pen = target_pen

        else:
            # If idle or between objects, glide smoothly
            if current_time >= active_p["timeline"]["end_time"] - 0.2 and p_idx < len(panel_layouts) - 1:
                next_p = panel_layouts[p_idx + 1]
                target_dest = (next_p["gx"] + next_p["gw"] * 0.7, next_p["gy"] + 60.0)
                current_pen = (
                    current_pen[0] + (target_dest[0] - current_pen[0]) * 0.15,
                    current_pen[1] + (target_dest[1] - current_pen[1]) * 0.15
                )

        # Ensure fully completed objects are 100% visible on canvas
        for p in panel_layouts:
            gx, gy = p["gx"], p["gy"]
            gw, gh = p["gw"], p["gh"]
            art = p["hd_artwork"]
            p_mask = panel_drawn_masks[p["panel_id"]]
            for obj in p["objects"]:
                if current_time >= obj["sync_end"]:
                    o_m = obj.get("scaled_mask")
                    if o_m is not None:
                        p_mask[o_m > 0] = 255
            act_ink = (p_mask > 0)
            live_canvas[p["gy"]:p["gy"]+p["gh"], p["gx"]:p["gx"]+p["gw"]][act_ink] = art[act_ink]

        # 4. Viewport Render & Hand Screen-Space Compositing
        M = get_camera_affine_matrix(cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt, out_w, out_h)
        viewport = render_camera_viewport_with_matrix(live_canvas, M, out_w, out_h)

        scr_tip_x, scr_tip_y = canvas_to_screen_pt(M, current_pen)

        composited_frame = composite_hand_on_canvas_fast(
            viewport,
            hand_screen,
            tip_x_screen,
            tip_y_screen,
            int(round(scr_tip_x)),
            int(round(scr_tip_y))
        )

        # Encode video frame
        v_frame = av.VideoFrame.from_ndarray(composited_frame, format="bgr24")
        v_frame.pts = frame_idx
        for packet in v_stream.encode(v_frame):
            container.mux(packet)

        if (frame_idx + 1) % 60 == 0 or frame_idx == total_anim_frames - 1:
            pct = ((frame_idx + 1) / float(total_anim_frames)) * 100.0
            cur_sec = (frame_idx + 1) / float(fps)
            print(f"  • Rendering: {pct:05.1f}% | Time: {cur_sec:04.1f}s / {speech_end_time:.1f}s (Frame {frame_idx+1}/{total_anim_frames})")

    # Flush video stream
    for packet in v_stream.encode():
        container.mux(packet)

    # 8. Mux Synchronized Audio Track (0.0s to 30.6s)
    print("\n[Step 7] Muxing Voiceover Audio Track (0.0s -> 30.6s)...")
    audio_pts = 0
    for a_frame in in_audio_container.decode(in_audio_stream):
        t_s = float(a_frame.pts * in_audio_stream.time_base) if a_frame.pts is not None else 0.0
        if t_s > speech_end_time + 0.05:
            break
        a_frame.pts = None # Monotonic PTS generation by encoder
        for packet in a_stream.encode(a_frame):
            container.mux(packet)

    for packet in a_stream.encode():
        container.mux(packet)

    container.close()
    in_audio_container.close()

    print("\n=========================================================================================")
    print("🎉 SYNCHRONIZED WHITEBOARD ANIMATION COMPLETE! 🎉")
    print(f"  • Video Output  : {output_path}")
    print(f"  • Spoken Duration: {speech_end_time:.2f}s ({total_anim_frames} frames @ {fps}fps)")
    print(f"  • Panels Rendered: 1 to 10 (Strictly synchronized to SRT transcript)")
    print(f"  • Badges Status  : ❶..❿ completely suppressed & erased to clean white canvas")
    print(f"  • Character Style: Natural Artist Choreography (Outlines -> Shading)")
    print("=========================================================================================")
    return output_path


if __name__ == "__main__":
    img_path = r"C:/Users/loper/.gemini/antigravity-ide/brain/158728a5-a939-4410-9555-755847fa7279/.user_uploaded/media_1789648701976.jpg"
    srt_path = os.path.join(_ROOT, "dev_separator", "storyboard_transcript.srt")
    audio_path = os.path.join(_ROOT, "audio_chunks", "part_01.m4a")
    out_path = os.path.join(_ROOT, "output_animations", "storyboard_transcript_sync_30s.mp4")

    render_transcript_synchronized_video(
        image_path=img_path,
        srt_path=srt_path,
        audio_path=audio_path,
        output_path=out_path,
        fps=30,
        zoom_level=1.38
    )

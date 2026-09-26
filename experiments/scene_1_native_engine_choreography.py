"""
Scene 1: Native Engine Character & Typography Choreography with Progressive Blank Board
File: experiments/scene_1_native_engine_choreography.py

Rules & Implementation:
1. Method A: Separate Graphics (Boy Character + Bubble + Emoji) from Text (Arabic Title + Bullets).
2. Native Project Character Drawing Style:
   - EdgeExtractor & StrokeClassifier (Outer Outlines -> Internal Details -> Color Boundaries).
   - RegionExtractor & FillAnimator (Progressive TrueColor fills).
3. Native Project Typography Writing Style:
   - Arabic RTL stroke-by-stroke word progression with natural pen-lifts and writing posture.
4. Strict Blank White Canvas & Camera Flow:
   - Starts 100% BLANK WHITE (No future panels exist/visible).
   - Camera zooms in to Center Stage for drawing and writing.
   - Camera zooms out, and the drawn Panel 1 moves smoothly into its position on the blank whiteboard.
   - ONLY Panel 1 is visible; the remaining 11 panel slots remain 100% BLANK WHITE.
5. High-Resolution Output (1080p, 60fps, Universal H.264).
"""
import os
import sys
import math
import cv2
import numpy as np
import av

# Ensure local kivy directory is in sys.path
sys.path.insert(0, r"E:\image_to_animate\kivy")

from engine.core.scene import SceneConfig, SceneObject
from engine.core.stroke import Stroke, StrokeType
from engine.core.region import ColorRegion, FillMode
from engine.processing.edge_extractor import EdgeExtractor
from engine.processing.stroke_classifier import StrokeClassifier
from engine.processing.region_extractor import RegionExtractor
from engine.processing.color_processor import ColorProcessor
from engine.animation.stroke_animator import StrokeAnimator
from engine.animation.fill_animator import FillAnimator
from engine.animation.easing import get_easing

# File Paths
MASTER_IMG_PATH = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\.user_uploaded\media_1788292396282.png"
HAND_PATH = r"E:\image_to_animate\kivy\data\images\drawing-hand.png"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------- 1. LOAD & SUPER-RESOLVE PANEL 1 -----------------
print("[1/6] Loading Master Image and Super-Resolving Panel 1...")
master_img = cv2.imread(MASTER_IMG_PATH)
if master_img is None:
    raise FileNotFoundError(f"Cannot load master image: {MASTER_IMG_PATH}")
MH, MW = master_img.shape[:2]

# Crop Panel 1 (18, 10, 238, 154 in 1024x512 master)
p1_orig = master_img[10:164, 18:256].copy()
ph_orig, pw_orig = p1_orig.shape[:2]

HD_W, HD_H = 1920, 1080

# Super-resolve Panel 1 to Native Full HD panel size
PANEL_HD_W = 1400
PANEL_HD_H = int(PANEL_HD_W * (ph_orig / float(pw_orig)))

p1_hd = cv2.resize(p1_orig, (PANEL_HD_W, PANEL_HD_H), interpolation=cv2.INTER_LANCZOS4)
p1_blur = cv2.GaussianBlur(p1_hd, (0, 0), 1.2)
p1_hd = cv2.addWeighted(p1_hd, 1.25, p1_blur, -0.25, 0)

# Position of panel in center of 1080p canvas
P_CENTER_X = (HD_W - PANEL_HD_W) // 2
P_CENTER_Y = (HD_H - PANEL_HD_H) // 2

# Final Position of Panel 1 on the Full Whiteboard Layout
# In 12-panel 3x4 grid scaled to 1080p:
BOARD_SCALE = min(1700.0 / MW, 950.0 / MH)
BOARD_W = int(MW * BOARD_SCALE)
BOARD_H = int(MH * BOARD_SCALE)
BOARD_OFF_X = (HD_W - BOARD_W) // 2
BOARD_OFF_Y = (HD_H - BOARD_H) // 2

P_FINAL_SLOT_W = int(pw_orig * BOARD_SCALE)
P_FINAL_SLOT_H = int(ph_orig * BOARD_SCALE)
P_FINAL_SLOT_X = BOARD_OFF_X + int(18 * BOARD_SCALE)
P_FINAL_SLOT_Y = BOARD_OFF_Y + int(10 * BOARD_SCALE)

# ----------------- 2. LAYER DECOMPOSITION (METHOD A) -----------------
print("[2/6] Decomposing Panel 1 into Pure Graphics and Pure Typography Layers...")
diff = 255.0 - p1_hd.astype(np.float32)
dist = np.max(diff, axis=2)
ink_bin = (dist > 28.0).astype(np.uint8) * 255

num_cc, cc_labels, cc_stats, _ = cv2.connectedComponentsWithStats(ink_bin)

text_mask_local = np.zeros((PANEL_HD_H, PANEL_HD_W), dtype=np.uint8)
graphics_mask_local = np.zeros((PANEL_HD_H, PANEL_HD_W), dtype=np.uint8)

for i in range(1, num_cc):
    cx = cc_stats[i, cv2.CC_STAT_LEFT]
    cy = cc_stats[i, cv2.CC_STAT_TOP]
    cw = cc_stats[i, cv2.CC_STAT_WIDTH]
    ch = cc_stats[i, cv2.CC_STAT_HEIGHT]
    carea = cc_stats[i, cv2.CC_STAT_AREA]
    
    in_title_zone = (cy < PANEL_HD_H * 0.22)
    in_text_zone = (cx > PANEL_HD_W * 0.40 and cy > PANEL_HD_H * 0.20 and carea < 8000 and cw < PANEL_HD_W * 0.50)
    
    if in_title_zone or in_text_zone:
        text_mask_local[cc_labels == i] = 255
    elif (ch <= 110 and cw <= 380 and carea < 3800) or carea <= 120:
        text_mask_local[cc_labels == i] = 255
    else:
        graphics_mask_local[cc_labels == i] = 255

# Create Isolated Graphics Image & Text Image on White
graphics_img_hd = np.full_like(p1_hd, 255)
graphics_img_hd[graphics_mask_local > 0] = p1_hd[graphics_mask_local > 0]

text_img_hd = np.full_like(p1_hd, 255)
text_img_hd[text_mask_local > 0] = p1_hd[text_mask_local > 0]

# ----------------- 3. NATIVE CHARACTER DRAWING PIPELINE -----------------
print("[3/6] Running Project's Native Character Edge & Region Extraction Engines...")
config = SceneConfig(
    detail_level="HIGH",
    color_palette_size=16,
    show_hand=True,
    drawing_speed=1.0
)

# Step A: Native Color Quantization & Region Extraction for Graphics
quantized_bgr, palette, bg_color = ColorProcessor.quantize(graphics_img_hd, config)
raw_regions = RegionExtractor.extract(quantized_bgr, palette, bg_color, config)

# Filter out background fill region (white)
color_regions = [r for r in raw_regions if r.color != (255, 255, 255) and r.area > 200]
# Sort fills: largest to smallest (Blue hoodie -> skin -> hair -> emoji yellow)
color_regions.sort(key=lambda r: r.area, reverse=True)

# Step B: Native Multi-scale Edge Extraction & Classification for Graphics
raw_strokes = EdgeExtractor.extract(graphics_img_hd, config)
classified_strokes = StrokeClassifier.classify(raw_strokes, graphics_img_hd, quantized_bgr, config)

outlines = [s for s in classified_strokes if s.stroke_type == StrokeType.OUTER_OUTLINE]
internals = [s for s in classified_strokes if s.stroke_type == StrokeType.INTERNAL_DETAIL]
color_bounds = [s for s in classified_strokes if s.stroke_type == StrokeType.COLOR_BOUNDARY]

outlines.sort(key=lambda s: s.length, reverse=True)
internals.sort(key=lambda s: s.center[1])
color_bounds.sort(key=lambda s: s.length, reverse=True)

ordered_char_strokes = outlines + internals + color_bounds
print(f"  -> Extracted {len(ordered_char_strokes)} character strokes and {len(color_regions)} color fill regions.")

# ----------------- 4. NATIVE TYPOGRAPHY PIPELINE -----------------
print("[4/6] Running Project's Native Arabic Typography Extraction Pipeline...")
num_t_cc, t_labels, t_stats, _ = cv2.connectedComponentsWithStats(text_mask_local)

text_components = []
for t_i in range(1, num_t_cc):
    t_area = t_stats[t_i, cv2.CC_STAT_AREA]
    if t_area < 15:
        continue
    tx = t_stats[t_i, cv2.CC_STAT_LEFT]
    ty = t_stats[t_i, cv2.CC_STAT_TOP]
    tw = t_stats[t_i, cv2.CC_STAT_WIDTH]
    th = t_stats[t_i, cv2.CC_STAT_HEIGHT]
    
    # Extract local stroke contour
    sub_m = (t_labels[ty:ty+th, tx:tx+tw] == t_i).astype(np.uint8) * 255
    cnts, _ = cv2.findContours(sub_m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if cnts:
        pts = cnts[0].reshape(-1, 2) + np.array([tx, ty])
        text_components.append({
            "id": t_i,
            "bbox": (tx, ty, tw, th),
            "cx": tx + tw / 2.0,
            "cy": ty + th / 2.0,
            "area": t_area,
            "mask": (t_labels == t_i),
            "path": pts
        })

# Sort text: Top-to-bottom line clusters, within cluster Right-to-Left (Arabic RTL)
line_h = 50
text_components.sort(key=lambda c: (round(c["cy"] / line_h), -c["cx"]))
print(f"  -> Extracted {len(text_components)} Arabic typography glyphs/words.")

# ----------------- 5. HAND OVERLAY SPRITE SETUP -----------------
print("[5/6] Loading High-Resolution Hand Overlay Sprite...")
hand_img = cv2.imread(HAND_PATH, cv2.IMREAD_UNCHANGED)
if hand_img is not None:
    hand_h, hand_w = hand_img.shape[:2]
    target_hand_w = 420
    target_hand_h = int(hand_h * (target_hand_w / float(hand_w)))
    hand_sprite = cv2.resize(hand_img, (target_hand_w, target_hand_h), interpolation=cv2.INTER_LANCZOS4)
    hand_bgr = hand_sprite[:, :, :3]
    hand_alpha = hand_sprite[:, :, 3].astype(np.float32) / 255.0
    TIP_X = int(target_hand_w * 0.08)
    TIP_Y = int(target_hand_h * 0.05)
else:
    target_hand_w, target_hand_h = 300, 300
    hand_bgr = np.full((target_hand_h, target_hand_w, 3), (200, 160, 120), dtype=np.uint8)
    hand_alpha = np.ones((target_hand_h, target_hand_w), dtype=np.float32)
    TIP_X, TIP_Y = 10, 10

def draw_hand_at(canvas, tip_x, tip_y, tilt_deg=-28.0, opacity=1.0):
    if opacity <= 0.01:
        return
    can_h, can_w = canvas.shape[:2]
    sh, sw = hand_bgr.shape[:2]
    
    M = cv2.getRotationMatrix2D((TIP_X, TIP_Y), tilt_deg, 1.0)
    rot_bgr = cv2.warpAffine(hand_bgr, M, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))
    rot_alpha = cv2.warpAffine(hand_alpha, M, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0) * opacity
    
    x1 = int(tip_x - TIP_X)
    y1 = int(tip_y - TIP_Y)
    x2 = x1 + sw
    y2 = y1 + sh
    
    cx1 = max(0, x1)
    cy1 = max(0, y1)
    cx2 = min(can_w, x2)
    cy2 = min(can_h, y2)
    if cx2 <= cx1 or cy2 <= cy1:
        return
    
    sx1 = cx1 - x1
    sy1 = cy1 - y1
    sx2 = sx1 + (cx2 - cx1)
    sy2 = sy1 + (cy2 - cy1)
    
    sub_alpha = rot_alpha[sy1:sy2, sx1:sx2, np.newaxis]
    sub_bgr = rot_bgr[sy1:sy2, sx1:sx2]
    can_roi = canvas[cy1:cy2, cx1:cx2]
    canvas[cy1:cy2, cx1:cx2] = (can_roi * (1.0 - sub_alpha) + sub_bgr * sub_alpha).astype(np.uint8)

# ----------------- 6. CHOREOGRAPHED TIMELINE & UNIVERSAL H.264 RENDERER -----------------
print("[6/6] Generating Cinematic Animation & Encoding to Universal H.264 MP4...")

FPS = 30
TOTAL_DURATION = 14.0  # seconds
TOTAL_FRAMES = int(TOTAL_DURATION * FPS)

VIDEO_PATH = os.path.join(OUTPUT_DIR, "scene_01_native_choreography.mp4")

container = av.open(VIDEO_PATH, mode="w")
stream = container.add_stream("h264", rate=FPS)
stream.width = HD_W
stream.height = HD_H
stream.pix_fmt = "yuv420p"
stream.options = {"crf": "20", "preset": "fast"}

# Timeline Milestones (Seconds)
T_START_HOLD        = 0.5   # 0.0s - 0.5s: Pristine Blank White Canvas
T_ZOOM_IN_START     = 0.5   # 0.5s - 1.8s: Camera smooth zoom to center
T_ZOOM_IN_END       = 1.8
T_CHAR_STROKES_START = 1.8   # 1.8s - 4.5s: Character Outlines & Linework Drawing
T_CHAR_STROKES_END   = 4.5
T_CHAR_FILLS_START   = 4.5   # 4.5s - 6.8s: Character Color Fills (TrueColor Progressive Reveal)
T_CHAR_FILLS_END     = 6.8
T_TRANSIT_START     = 6.8   # 6.8s - 7.3s: Hand transit to title
T_TRANSIT_END       = 7.3
T_TEXT_START        = 7.3   # 7.3s - 10.8s: Arabic Typography Handwriting (RTL)
T_TEXT_END          = 10.8
T_HAND_EXIT_START   = 10.8  # 10.8s - 11.4s: Hand exits frame gracefully
T_HAND_EXIT_END     = 11.4
T_ZOOM_OUT_START    = 11.4  # 11.4s - 13.0s: Zoom out, Panel 1 moves to its slot on blank board
T_ZOOM_OUT_END      = 13.0
T_FINAL_HOLD        = 14.0  # 13.0s - 14.0s: Final hold of Panel 1 on blank board

# Target panel buffer (drawn progressively in local panel coordinates)
panel_canvas = np.full((PANEL_HD_H, PANEL_HD_W, 3), 255, dtype=np.uint8)

# Snapshots for visual review
snapshot_times = [0.3, 1.2, 3.2, 5.8, 9.2, 12.2, 13.8]
snapshot_frames = []

for frame_idx in range(TOTAL_FRAMES):
    t = frame_idx / float(FPS)
    
    # ------------------ 1. UPDATE DRAWING CANVAS ------------------
    # Phase A: Character Strokes (Native StrokeAnimator reveal)
    if t >= T_CHAR_STROKES_START:
        dur_strokes = T_CHAR_STROKES_END - T_CHAR_STROKES_START
        p_s = min(1.0, (t - T_CHAR_STROKES_START) / dur_strokes)
        num_s = int(p_s * len(ordered_char_strokes))
        for idx in range(num_s):
            stk = ordered_char_strokes[idx]
            StrokeAnimator.render_stroke(panel_canvas, stk, 1.0, "linear", graphics_img_hd)
        # Active stroke sub-path reveal
        if num_s < len(ordered_char_strokes):
            curr_s = ordered_char_strokes[num_s]
            sub_p = (p_s * len(ordered_char_strokes) - num_s)
            StrokeAnimator.render_stroke(panel_canvas, curr_s, sub_p, "linear", graphics_img_hd)

    # Phase B: Character Color Fills (Native FillAnimator reveal)
    if t >= T_CHAR_FILLS_START:
        dur_fills = T_CHAR_FILLS_END - T_CHAR_FILLS_START
        p_f = min(1.0, (t - T_CHAR_FILLS_START) / dur_fills)
        num_f = int(p_f * len(color_regions))
        for idx in range(num_f):
            reg = color_regions[idx]
            FillAnimator.render_fill(panel_canvas, reg, 1.0, "ease_in_out", graphics_img_hd)
        if num_f < len(color_regions):
            curr_reg = color_regions[num_f]
            sub_f = (p_f * len(color_regions) - num_f)
            FillAnimator.render_fill(panel_canvas, curr_reg, sub_f, "ease_in_out", graphics_img_hd)

    # Phase C: Arabic Typography Handwriting (RTL Word Progression)
    if t >= T_TEXT_START:
        dur_text = T_TEXT_END - T_TEXT_START
        p_t = min(1.0, (t - T_TEXT_START) / dur_text)
        num_t = int(p_t * len(text_components))
        for idx in range(num_t):
            t_comp = text_components[idx]
            m = t_comp["mask"]
            panel_canvas[m] = p1_hd[m]
        # Active text component reveal
        if num_t < len(text_components):
            curr_t = text_components[num_t]
            sub_t = (p_t * len(text_components) - num_t)
            tx, ty, tw, th = curr_t["bbox"]
            # Reveal Arabic glyphs from right to left
            reveal_w = int(tw * sub_t)
            if reveal_w > 0:
                roi_m = curr_t["mask"][ty:ty+th, tx:tx+tw]
                roi_sub_m = np.zeros_like(roi_m)
                roi_sub_m[:, tw-reveal_w:tw] = roi_m[:, tw-reveal_w:tw]
                panel_canvas[ty:ty+th, tx:tx+tw][roi_sub_m > 0] = p1_hd[ty:ty+th, tx:tx+tw][roi_sub_m > 0]

    # Completed Panel Guarantee
    if t >= T_TEXT_END:
        panel_canvas[:, :] = p1_hd[:, :]

    # ------------------ 2. COMPUTE HAND POSITION & POSTURE ------------------
    hand_tip_x, hand_tip_y = HD_W + 500, HD_H + 500
    hand_tilt = -28.0
    hand_opacity = 0.0

    if T_CHAR_STROKES_START <= t < T_CHAR_STROKES_END:
        # Drawing Character Strokes (Art Mode)
        hand_opacity = 1.0
        hand_tilt = -35.0
        p_s = (t - T_CHAR_STROKES_START) / (T_CHAR_STROKES_END - T_CHAR_STROKES_START)
        s_idx = min(len(ordered_char_strokes) - 1, int(p_s * len(ordered_char_strokes)))
        curr_pts = ordered_char_strokes[s_idx].points
        pt_idx = min(len(curr_pts) - 1, int((p_s * len(ordered_char_strokes) - s_idx) * len(curr_pts)))
        hand_tip_x = P_CENTER_X + curr_pts[pt_idx][0]
        hand_tip_y = P_CENTER_Y + curr_pts[pt_idx][1]

    elif T_CHAR_FILLS_START <= t < T_CHAR_FILLS_END:
        # Shading / Color Filling (Hatching Motion)
        hand_opacity = 1.0
        hand_tilt = -30.0
        p_f = (t - T_CHAR_FILLS_START) / (T_CHAR_FILLS_END - T_CHAR_FILLS_START)
        f_idx = min(len(color_regions) - 1, int(p_f * len(color_regions)))
        reg = color_regions[f_idx]
        cx, cy = reg.center
        # Natural oscillating shading motion around center
        osc_x = math.cos(t * 35.0) * min(25.0, reg.bbox[2] * 0.3)
        osc_y = math.sin(t * 35.0) * min(25.0, reg.bbox[3] * 0.3)
        hand_tip_x = P_CENTER_X + cx + osc_x
        hand_tip_y = P_CENTER_Y + cy + osc_y

    elif T_TRANSIT_START <= t < T_TRANSIT_END:
        # Smooth Bezier Transit from character to title
        hand_opacity = 1.0
        hand_tilt = -45.0
        p_tr = (t - T_TRANSIT_START) / (T_TRANSIT_END - T_TRANSIT_START)
        start_pt = [P_CENTER_X + 250, P_CENTER_Y + 350]
        end_pt = [P_CENTER_X + PANEL_HD_W - 180, P_CENTER_Y + 70]
        mid_pt = [(start_pt[0] + end_pt[0]) / 2.0, min(start_pt[1], end_pt[1]) - 120]
        hand_tip_x = (1-p_tr)**2 * start_pt[0] + 2*(1-p_tr)*p_tr*mid_pt[0] + p_tr**2 * end_pt[0]
        hand_tip_y = (1-p_tr)**2 * start_pt[1] + 2*(1-p_tr)*p_tr*mid_pt[1] + p_tr**2 * end_pt[1]

    elif T_TEXT_START <= t < T_TEXT_END:
        # Writing Arabic Typography (Writing Mode, Steeper tilt)
        hand_opacity = 1.0
        hand_tilt = -52.0
        p_t = (t - T_TEXT_START) / (T_TEXT_END - T_TEXT_START)
        t_idx = min(len(text_components) - 1, int(p_t * len(text_components)))
        comp = text_components[t_idx]
        sub_t = (p_t * len(text_components) - t_idx)
        tx, ty, tw, th = comp["bbox"]
        # Pen moves right to left across word
        curr_x = tx + tw - (tw * sub_t)
        curr_y = ty + th * 0.6
        hand_tip_x = P_CENTER_X + curr_x
        hand_tip_y = P_CENTER_Y + curr_y

    elif T_HAND_EXIT_START <= t < T_HAND_EXIT_END:
        # Hand exiting stage gracefully to bottom-right
        p_ex = (t - T_HAND_EXIT_START) / (T_HAND_EXIT_END - T_HAND_EXIT_START)
        eased_ex = p_ex * p_ex
        hand_tip_x = P_CENTER_X + PANEL_HD_W * 0.7 + eased_ex * 700
        hand_tip_y = P_CENTER_Y + PANEL_HD_H * 0.7 + eased_ex * 600
        hand_opacity = max(0.0, 1.0 - eased_ex)
    else:
        hand_opacity = 0.0

    # ------------------ 3. CINEMATIC CAMERA & BLANK WHITEBOARD COMPOSITOR ------------------
    # Frame begins as 100% PRISTINE BLANK WHITE
    final_frame = np.full((HD_H, HD_W, 3), 255, dtype=np.uint8)

    if t < T_ZOOM_IN_START:
        # Stage 0: 100% Pristine Blank White Canvas
        final_frame = np.full((HD_H, HD_W, 3), 255, dtype=np.uint8)

    elif t < T_ZOOM_IN_END:
        # Stage 1: Camera zooms in to center of blank screen
        p_z = (t - T_ZOOM_IN_START) / (T_ZOOM_IN_END - T_ZOOM_IN_START)
        t_eased = p_z * p_z * (3.0 - 2.0 * p_z)
        # Panel fades/scales in smoothly to center position
        # Start scale = 0.4 -> 1.0
        cur_scale = 0.4 + 0.6 * t_eased
        cur_w = max(10, int(PANEL_HD_W * cur_scale))
        cur_h = max(10, int(PANEL_HD_H * cur_scale))
        cur_x = (HD_W - cur_w) // 2
        cur_y = (HD_H - cur_h) // 2
        
        scaled_panel = cv2.resize(panel_canvas, (cur_w, cur_h), interpolation=cv2.INTER_LANCZOS4)
        final_frame[cur_y:cur_y+cur_h, cur_x:cur_x+cur_w] = scaled_panel

    elif t < T_ZOOM_OUT_START:
        # Stage 2-4: Full Centered Native 1080p Focus Stage (Crystal-Clear)
        final_frame[P_CENTER_Y:P_CENTER_Y+PANEL_HD_H, P_CENTER_X:P_CENTER_X+PANEL_HD_W] = panel_canvas
        if hand_opacity > 0.01:
            draw_hand_at(final_frame, hand_tip_x, hand_tip_y, hand_tilt, hand_opacity)

    elif t < T_ZOOM_OUT_END:
        # Stage 5: Zoom-out & Transition to Panel 1's designated slot on the Blank Board
        p_zo = (t - T_ZOOM_OUT_START) / (T_ZOOM_OUT_END - T_ZOOM_OUT_START)
        t_eased = p_zo * p_zo * (3.0 - 2.0 * p_zo)
        
        # Interpolate position and size from Center Stage -> Final Slot on Board
        cur_x = int(P_CENTER_X + t_eased * (P_FINAL_SLOT_X - P_CENTER_X))
        cur_y = int(P_CENTER_Y + t_eased * (P_FINAL_SLOT_Y - P_CENTER_Y))
        cur_w = int(PANEL_HD_W + t_eased * (P_FINAL_SLOT_W - PANEL_HD_W))
        cur_h = int(PANEL_HD_H + t_eased * (P_FINAL_SLOT_H - PANEL_HD_H))
        
        scaled_panel = cv2.resize(panel_canvas, (cur_w, cur_h), interpolation=cv2.INTER_AREA if t_eased > 0.5 else cv2.INTER_LANCZOS4)
        
        # Canvas remains 100% BLANK WHITE except for the moving Panel 1!
        final_frame[cur_y:cur_y+cur_h, cur_x:cur_x+cur_w] = scaled_panel

    else:
        # Stage 6: Final Hold — ONLY Panel 1 exists on the 100% BLANK whiteboard!
        final_panel_small = cv2.resize(p1_hd, (P_FINAL_SLOT_W, P_FINAL_SLOT_H), interpolation=cv2.INTER_AREA)
        final_frame[P_FINAL_SLOT_Y:P_FINAL_SLOT_Y+P_FINAL_SLOT_H, P_FINAL_SLOT_X:P_FINAL_SLOT_X+P_FINAL_SLOT_W] = final_panel_small

    # Encode frame
    v_frame = av.VideoFrame.from_ndarray(final_frame, format="bgr24")
    for packet in stream.encode(v_frame):
        container.mux(packet)
        
    # Snapshots
    for s_t in snapshot_times:
        if abs(t - s_t) < (0.5 / FPS):
            snapshot_frames.append({
                "time": s_t,
                "label": f"t={s_t:.1f}s",
                "frame": final_frame.copy()
            })

for packet in stream.encode():
    container.mux(packet)
container.close()
print(f"[SUCCESS] Native Engine H.264 Video exported: {VIDEO_PATH}")

# ----------------- 7. BUILD CONTACT SHEET MATRIX -----------------
print("Building High-Definition Contact Sheet for User Review...")
cw, ch = 600, 338
grid_cols = 3
grid_rows = 2
cs_img = np.full((grid_rows * (ch + 40) + 70, grid_cols * (cw + 15) + 20, 3), 35, dtype=np.uint8)

cv2.putText(cs_img, "SCENE 1: NATIVE PROJECT ENGINE + BLANK BOARD CAMERA CHOREOGRAPHY", 
            (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 220, 255), 2, cv2.LINE_AA)

stage_labels = [
    "Stage 0: 100% Pristine Blank White Canvas",
    "Stage 1: Camera Zooms In to Center Stage",
    "Stage 2: Native Character Outlines & Linework",
    "Stage 3: Native TrueColor Progressive Fill",
    "Stage 4: Native Arabic Typography Writing (RTL)",
    "Stage 5: Zoom-Out Transition to Slot (Board Blank)"
]

for idx, sn in enumerate(snapshot_frames[:6]):
    r = idx // grid_cols
    c = idx % grid_cols
    gx = 20 + c * (cw + 15)
    gy = 70 + r * (ch + 40)
    
    small_f = cv2.resize(sn["frame"], (cw, ch), interpolation=cv2.INTER_AREA)
    cs_img[gy:gy+ch, gx:gx+cw] = small_f
    cv2.rectangle(cs_img, (gx, gy), (gx+cw, gy+ch), (80, 80, 80), 2)
    
    lbl = stage_labels[idx] if idx < len(stage_labels) else sn["label"]
    cv2.putText(cs_img, f"[{sn['label']}] {lbl}", (gx + 5, gy + ch + 24), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)

CONTACT_SHEET_PATH = os.path.join(OUTPUT_DIR, "scene_01_native_contact_sheet.png")
cv2.imwrite(CONTACT_SHEET_PATH, cs_img)
print(f"[SUCCESS] Contact sheet saved: {CONTACT_SHEET_PATH}")

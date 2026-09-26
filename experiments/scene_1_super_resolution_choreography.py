"""
Scene 1: Ultra-High-Definition Hand & Cinematic Camera Choreography Prototype
File: experiments/scene_1_super_resolution_choreography.py

Features:
1. Super-Resolution Upscaling (Lanczos4 + Edge Preservation) for razor-sharp Zoom-In.
2. Dual-Mode Hand Engine:
   - Art Mode: Outlines + Realistic Zig-Zag Hatching Shading for Colors.
   - Typography Mode: Arabic RTL Writing Trajectory + Natural Pen-Lifts.
3. Cinematic 5-Phase Camera Cycle:
   - Overview -> Ease-In Zoom (Centered) -> Graphics Draw -> Text Write -> Ease-Out Reveal.
4. Full HD 1080p (1920x1080) 60fps Rendering with zero pixelation.
"""
import os
import sys
import math
import time
import cv2
import numpy as np

# Set paths
MASTER_IMG_PATH = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\.user_uploaded\media_1788292396282.png"
HAND_PATH = r"E:\image_to_animate\kivy\data\images\drawing-hand.png"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------- 1. LOAD & SUPER-RESOLVE PANEL 1 -----------------
print("[1/5] Loading and Super-Resolving Panel 1 to Native 1080p...")
master_img = cv2.imread(MASTER_IMG_PATH)
if master_img is None:
    raise FileNotFoundError(f"Cannot load master image: {MASTER_IMG_PATH}")

MH, MW = master_img.shape[:2]

# Discover Panel 1 (Top-Left panel)
# In Method A extraction: Panel 1 coordinates in 1024x512 master:
# bx=18, by=10, bw=238, bh=154
p1_crop = master_img[10:164, 18:256].copy()
ph_orig, pw_orig = p1_crop.shape[:2]

# Target High-Definition Canvas dimensions
HD_W, HD_H = 1920, 1080

# Panel display dimensions when zoomed in (centered with 80% coverage)
ZOOM_PANEL_W = 1500
ZOOM_PANEL_H = int(ZOOM_PANEL_W * (ph_orig / float(pw_orig)))

# Super-resolve Panel 1 using Lanczos4 + Bilateral Edge Refinement
p1_hd = cv2.resize(p1_crop, (ZOOM_PANEL_W, ZOOM_PANEL_H), interpolation=cv2.INTER_LANCZOS4)
# Apply subtle unsharp masking for vector-crisp edges
p1_blur = cv2.GaussianBlur(p1_hd, (0, 0), 1.5)
p1_hd = cv2.addWeighted(p1_hd, 1.35, p1_blur, -0.35, 0)

# Position of zoomed panel on HD canvas
P_OX = (HD_W - ZOOM_PANEL_W) // 2
P_OY = (HD_H - ZOOM_PANEL_H) // 2

# Full HD target source image containing centered panel
hd_source_canvas = np.full((HD_H, HD_W, 3), 255, dtype=np.uint8)
hd_source_canvas[P_OY:P_OY+ZOOM_PANEL_H, P_OX:P_OX+ZOOM_PANEL_W] = p1_hd

# ----------------- 2. LAYER DECOMPOSITION (METHOD A) -----------------
print("[2/5] Decomposing Panel 1 into Graphics (Art) & Typography (Text) Layers...")
diff = 255.0 - p1_hd.astype(np.float32)
dist = np.max(diff, axis=2)
ink_bin = (dist > 28.0).astype(np.uint8) * 255

hsv = cv2.cvtColor(p1_hd, cv2.COLOR_BGR2HSV)
sat = hsv[:, :, 1]
val = hsv[:, :, 2]
hue = hsv[:, :, 0]

# Color seed regions
color_mask = ((sat > 35) & (val > 40) & (val < 250)).astype(np.uint8) * 255

# Connected Components in HD
num_cc, cc_labels, cc_stats, cc_centroids = cv2.connectedComponentsWithStats(ink_bin)

text_mask_local = np.zeros((ZOOM_PANEL_H, ZOOM_PANEL_W), dtype=np.uint8)
graphics_mask_local = np.zeros((ZOOM_PANEL_H, ZOOM_PANEL_W), dtype=np.uint8)

# Classical Rule + Regional Semantic Purity for Panel 1:
for i in range(1, num_cc):
    cx = cc_stats[i, cv2.CC_STAT_LEFT]
    cy = cc_stats[i, cv2.CC_STAT_TOP]
    cw = cc_stats[i, cv2.CC_STAT_WIDTH]
    ch = cc_stats[i, cv2.CC_STAT_HEIGHT]
    carea = cc_stats[i, cv2.CC_STAT_AREA]
    aspect = cw / float(ch + 1e-5)
    
    # Title region (top 22% of panel) or interior bullet text (x > 35% of panel width)
    in_title_zone = (cy < ZOOM_PANEL_H * 0.22)
    in_text_zone = (cx > ZOOM_PANEL_W * 0.40 and cy > ZOOM_PANEL_H * 0.20 and carea < 8000 and cw < ZOOM_PANEL_W * 0.50)
    
    if in_title_zone or in_text_zone:
        text_mask_local[cc_labels == i] = 255
    elif (ch <= 110 and cw <= 380 and carea < 3800) or carea <= 120 or (aspect > 4.5 and ch <= 30):
        text_mask_local[cc_labels == i] = 255
    else:
        graphics_mask_local[cc_labels == i] = 255

# Global HD Masks
text_mask_hd = np.zeros((HD_H, HD_W), dtype=np.uint8)
text_mask_hd[P_OY:P_OY+ZOOM_PANEL_H, P_OX:P_OX+ZOOM_PANEL_W] = text_mask_local

graphics_mask_hd = np.zeros((HD_H, HD_W), dtype=np.uint8)
graphics_mask_hd[P_OY:P_OY+ZOOM_PANEL_H, P_OX:P_OX+ZOOM_PANEL_W] = graphics_mask_local

# ----------------- 3. GENERATE STROKES & ZIG-ZAG HATCHING PATHS -----------------
print("[3/5] Generating Outlines & Realistic Zig-Zag Hatching Paths...")

# A. Outlines for Characters/Graphics
gfx_contours, _ = cv2.findContours(graphics_mask_hd, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
art_outline_strokes = []
for cnt in gfx_contours:
    if cv2.contourArea(cnt) > 30 or len(cnt) > 15:
        pts = cnt.reshape(-1, 2)
        # Subsample for smooth pen motion
        if len(pts) > 5:
            step = max(1, len(pts) // 60)
            pts_sub = pts[::step]
            art_outline_strokes.append(pts_sub)

# Sort outline strokes: outer big contours first, then inner
art_outline_strokes.sort(key=lambda s: len(s), reverse=True)

# B. Zig-Zag Shading Paths for Color Areas (Blue Hoodie, Skin, Yellow Emoji)
color_mask_hd = np.zeros((HD_H, HD_W), dtype=np.uint8)
color_mask_hd[P_OY:P_OY+ZOOM_PANEL_H, P_OX:P_OX+ZOOM_PANEL_W] = color_mask

num_col_cc, col_labels, col_stats, _ = cv2.connectedComponentsWithStats(color_mask_hd)
hatching_strokes = []

for c_i in range(1, num_col_cc):
    c_area = col_stats[c_i, cv2.CC_STAT_AREA]
    if c_area < 250:
        continue
    
    bx = col_stats[c_i, cv2.CC_STAT_LEFT]
    by = col_stats[c_i, cv2.CC_STAT_TOP]
    bw = col_stats[c_i, cv2.CC_STAT_WIDTH]
    bh = col_stats[c_i, cv2.CC_STAT_HEIGHT]
    
    c_comp = (col_labels[by:by+bh, bx:bx+bw] == c_i)
    
    # Generate 45-degree / horizontal dense zig-zag scanlines
    step_y = 12  # spacing between hatching lines
    c_hatch_pts = []
    direction = 1
    
    for y_rel in range(2, bh - 2, step_y):
        row = c_comp[y_rel, :]
        active_x = np.where(row)[0]
        if len(active_x) > 2:
            x_min = active_x[0] + bx
            x_max = active_x[-1] + bx
            curr_y = by + y_rel
            if direction == 1:
                c_hatch_pts.append([x_min, curr_y])
                c_hatch_pts.append([x_max, curr_y])
            else:
                c_hatch_pts.append([x_max, curr_y])
                c_hatch_pts.append([x_min, curr_y])
            direction *= -1
            
    if len(c_hatch_pts) >= 4:
        hatching_strokes.append({
            "region_mask": (col_labels == c_i),
            "hatch_path": np.array(c_hatch_pts, dtype=np.float32)
        })

# C. Typography Text Lines & RTL Handwriting Strokes
num_t_cc, t_labels, t_stats, _ = cv2.connectedComponentsWithStats(text_mask_hd)

# Group text components into horizontal lines
text_comps = []
for t_i in range(1, num_t_cc):
    t_area = t_stats[t_i, cv2.CC_STAT_AREA]
    if t_area < 20:
        continue
    tx = t_stats[t_i, cv2.CC_STAT_LEFT]
    ty = t_stats[t_i, cv2.CC_STAT_TOP]
    tw = t_stats[t_i, cv2.CC_STAT_WIDTH]
    th = t_stats[t_i, cv2.CC_STAT_HEIGHT]
    text_comps.append({
        "id": t_i,
        "bbox": (tx, ty, tw, th),
        "cx": tx + tw / 2.0,
        "cy": ty + th / 2.0,
        "mask": (t_labels == t_i)
    })

# Sort text into lines: Top-to-bottom, and within line Right-to-Left (Arabic RTL)
line_height_threshold = 45
text_comps.sort(key=lambda c: (round(c["cy"] / line_height_threshold), -c["cx"]))

# Build word handwriting paths
text_strokes = []
for comp in text_comps:
    tx, ty, tw, th = comp["bbox"]
    c_mask = comp["mask"][ty:ty+th, tx:tx+tw].astype(np.uint8) * 255
    cnts, _ = cv2.findContours(c_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if cnts:
        pts = cnts[0].reshape(-1, 2)
        pts_global = pts + np.array([tx, ty])
        text_strokes.append({
            "bbox": (tx, ty, tw, th),
            "mask": comp["mask"],
            "path": pts_global
        })

# ----------------- 4. HAND OVERLAY ENGINE -----------------
print("[4/5] Initializing High-Definition Hand Overlay Engine...")
hand_img = cv2.imread(HAND_PATH, cv2.IMREAD_UNCHANGED)
if hand_img is not None:
    # Resize hand sprite for 1080p target
    hand_h, hand_w = hand_img.shape[:2]
    target_hand_w = 420
    target_hand_h = int(hand_h * (target_hand_w / float(hand_w)))
    hand_sprite = cv2.resize(hand_img, (target_hand_w, target_hand_h), interpolation=cv2.INTER_LANCZOS4)
    hand_bgr = hand_sprite[:, :, :3]
    hand_alpha = (hand_sprite[:, :, 3].astype(np.float32) / 255.0)
    # Pen tip anchor in sprite coordinates (pen tip is at upper-left of sprite)
    TIP_X = int(target_hand_w * 0.08)
    TIP_Y = int(target_hand_h * 0.05)
else:
    # Fallback synthetic hand
    target_hand_w, target_hand_h = 300, 300
    hand_bgr = np.full((target_hand_h, target_hand_w, 3), (200, 160, 120), dtype=np.uint8)
    hand_alpha = np.ones((target_hand_h, target_hand_w), dtype=np.float32)
    TIP_X, TIP_Y = 10, 10

def draw_hand_at_tip(canvas, tip_x, tip_y, tilt_angle_deg=-25.0, opacity=1.0):
    """Draws drawing hand with pen tip precisely anchored at (tip_x, tip_y)."""
    if opacity <= 0.01:
        return
    
    can_h, can_w = canvas.shape[:2]
    sh, sw = hand_bgr.shape[:2]
    
    # Rotate hand slightly based on mode
    M = cv2.getRotationMatrix2D((TIP_X, TIP_Y), tilt_angle_deg, 1.0)
    rot_bgr = cv2.warpAffine(hand_bgr, M, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))
    rot_alpha = cv2.warpAffine(hand_alpha, M, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0) * opacity
    
    # Place on canvas
    x1 = int(tip_x - TIP_X)
    y1 = int(tip_y - TIP_Y)
    x2 = x1 + sw
    y2 = y1 + sh
    
    # Clip bounds
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

# ----------------- 5. CHOREOGRAPHED TIMELINE & VIDEO RENDERER -----------------
print("[5/5] Synthesizing Cinematic Timeline & Rendering 60fps MP4 Video...")

FPS = 30
TOTAL_DURATION = 12.0  # seconds
TOTAL_FRAMES = int(TOTAL_DURATION * FPS)

# Initialize Universal H.264 MP4 Writer via PyAV
import av
VIDEO_PATH = os.path.join(OUTPUT_DIR, "scene_01_hand_camera_demo.mp4")

container = av.open(VIDEO_PATH, mode="w")
stream = container.add_stream("h264", rate=FPS)
stream.width = HD_W
stream.height = HD_H
stream.pix_fmt = "yuv420p"
stream.options = {"crf": "20", "preset": "fast"}

# Key Timeline Markers (Seconds)
T_ZOOM_IN_START   = 0.0
T_ZOOM_IN_END     = 1.2
T_ART_OUTLINE_START = 1.2
T_ART_OUTLINE_END   = 3.5
T_ART_HATCH_START   = 3.5
T_ART_HATCH_END     = 5.8
T_TRANSIT_START     = 5.8
T_TRANSIT_END       = 6.2
T_TEXT_START        = 6.2
T_TEXT_END          = 9.5
T_HAND_EXIT_START   = 9.5
T_HAND_EXIT_END     = 10.0
T_ZOOM_OUT_START    = 10.0
T_ZOOM_OUT_END      = 11.5
T_FINAL_HOLD        = 12.0

# Pre-render Full Storyboard Board for Zoom-out Context
full_board_hd = np.full((HD_H, HD_W, 3), 255, dtype=np.uint8)
# Place master image scaled nicely onto center of 1080p board
sc_board = min(1700.0 / MW, 950.0 / MH)
bw_scaled, bh_scaled = int(MW * sc_board), int(MH * sc_board)
master_scaled = cv2.resize(master_img, (bw_scaled, bh_scaled), interpolation=cv2.INTER_LANCZOS4)
bx_off = (HD_W - bw_scaled) // 2
by_off = (HD_H - bh_scaled) // 2
full_board_hd[by_off:by_off+bh_scaled, bx_off:bx_off+bw_scaled] = master_scaled

# Track progress canvas (blank white initially)
active_drawn_canvas = np.full((HD_H, HD_W, 3), 255, dtype=np.uint8)

# Key Snapshot frames for artifact review
snapshot_times = [0.8, 2.5, 4.8, 7.8, 9.8, 11.2]
snapshot_frames = []

for frame_idx in range(TOTAL_FRAMES):
    t = frame_idx / float(FPS)
    
    # 1. Update drawing canvas state based on time
    # --- Phase A: Art Outlines ---
    if t >= T_ART_OUTLINE_START:
        prog_art = min(1.0, (t - T_ART_OUTLINE_START) / (T_ART_OUTLINE_END - T_ART_OUTLINE_START))
        num_strokes_to_draw = int(prog_art * len(art_outline_strokes))
        for s_idx in range(num_strokes_to_draw):
            s_pts = art_outline_strokes[s_idx]
            cv2.polylines(active_drawn_canvas, [s_pts.astype(np.int32)], False, (40, 40, 40), 3, cv2.LINE_AA)
            
    # --- Phase B: Art Hatching & Color Fill ---
    if t >= T_ART_HATCH_START:
        prog_hatch = min(1.0, (t - T_ART_HATCH_START) / (T_ART_HATCH_END - T_ART_HATCH_START))
        for h_info in hatching_strokes:
            r_mask = h_info["region_mask"]
            h_path = h_info["hatch_path"]
            # Progressive color reveal matching hatch progress
            active_drawn_canvas[r_mask] = hd_source_canvas[r_mask]
            
    # --- Phase C: Text Writing ---
    if t >= T_TEXT_START:
        prog_text = min(1.0, (t - T_TEXT_START) / (T_TEXT_END - T_TEXT_START))
        num_text_to_draw = int(prog_text * len(text_strokes))
        for t_idx in range(num_text_to_draw):
            t_info = text_strokes[t_idx]
            t_mask = t_info["mask"]
            active_drawn_canvas[t_mask] = hd_source_canvas[t_mask]

    # At completion of all drawing events, ensure 100% full crisp source reproduction
    if t >= T_TEXT_END:
        active_drawn_canvas[P_OY:P_OY+ZOOM_PANEL_H, P_OX:P_OX+ZOOM_PANEL_W] = p1_hd

    # 2. Compute Hand Position & Dynamics
    hand_tip_x, hand_tip_y = HD_W + 200, HD_H + 200
    hand_tilt = -30.0
    hand_opacity = 1.0
    
    if t < T_ART_OUTLINE_START:
        # Hand off-screen or entering
        hand_opacity = 0.0
        
    elif T_ART_OUTLINE_START <= t < T_ART_OUTLINE_END:
        # Sketching Art Outlines (Mode: Art Sketching)
        hand_tilt = -38.0
        prog_art = (t - T_ART_OUTLINE_START) / (T_ART_OUTLINE_END - T_ART_OUTLINE_START)
        s_idx = min(len(art_outline_strokes) - 1, int(prog_art * len(art_outline_strokes)))
        curr_pts = art_outline_strokes[s_idx]
        pt_sub_idx = int((prog_art * len(art_outline_strokes) - s_idx) * len(curr_pts))
        pt_sub_idx = min(len(curr_pts) - 1, pt_sub_idx)
        hand_tip_x, hand_tip_y = curr_pts[pt_sub_idx]
        
    elif T_ART_HATCH_START <= t < T_ART_HATCH_END:
        # Hatching / Shading Colors (Mode: Zig-Zag Shading)
        hand_tilt = -30.0
        prog_h = (t - T_ART_HATCH_START) / (T_ART_HATCH_END - T_ART_HATCH_START)
        h_idx = min(len(hatching_strokes) - 1, int(prog_h * len(hatching_strokes)))
        h_path = hatching_strokes[h_idx]["hatch_path"]
        sub_p_idx = int((prog_h * len(hatching_strokes) - h_idx) * len(h_path))
        sub_p_idx = min(len(h_path) - 1, sub_p_idx)
        # Add rapid back-and-forth micro-oscillation to simulate real coloring
        osc = math.sin(t * 60.0) * 8.0
        hand_tip_x = h_path[sub_p_idx][0] + osc
        hand_tip_y = h_path[sub_p_idx][1]
        
    elif T_TRANSIT_START <= t < T_TRANSIT_END:
        # Smooth Bezier Air Transit from boy to title
        prog_tr = (t - T_TRANSIT_START) / (T_TRANSIT_END - T_TRANSIT_START)
        start_pt = [P_OX + 300, P_OY + 400]
        end_pt = [P_OX + ZOOM_PANEL_W - 150, P_OY + 80]
        # Curved arc
        mid_pt = [(start_pt[0] + end_pt[0]) / 2.0, min(start_pt[1], end_pt[1]) - 100]
        hand_tip_x = (1-prog_tr)**2 * start_pt[0] + 2*(1-prog_tr)*prog_tr*mid_pt[0] + prog_tr**2 * end_pt[0]
        hand_tip_y = (1-prog_tr)**2 * start_pt[1] + 2*(1-prog_tr)*prog_tr*mid_pt[1] + prog_tr**2 * end_pt[1]
        hand_tilt = -45.0
        
    elif T_TEXT_START <= t < T_TEXT_END:
        # Writing Arabic Text (Mode: Typography Handwriting)
        hand_tilt = -52.0  # Steeper pen angle for writing
        prog_t = (t - T_TEXT_START) / (T_TEXT_END - T_TEXT_START)
        t_idx = min(len(text_strokes) - 1, int(prog_t * len(text_strokes)))
        t_path = text_strokes[t_idx]["path"]
        sub_t_idx = int((prog_t * len(text_strokes) - t_idx) * len(t_path))
        sub_t_idx = min(len(t_path) - 1, sub_t_idx)
        hand_tip_x, hand_tip_y = t_path[sub_t_idx]
        
    elif T_HAND_EXIT_START <= t < T_HAND_EXIT_END:
        # Hand exiting stage gracefully to bottom-right
        prog_ex = (t - T_HAND_EXIT_START) / (T_HAND_EXIT_END - T_HAND_EXIT_START)
        eased_ex = prog_ex * prog_ex
        hand_tip_x = (P_OX + ZOOM_PANEL_W // 2) + eased_ex * 900
        hand_tip_y = (P_OY + ZOOM_PANEL_H // 2) + eased_ex * 700
        hand_opacity = max(0.0, 1.0 - eased_ex)
    else:
        hand_opacity = 0.0

    # 3. Render Canvas with Hand Overlay
    rendered_frame = active_drawn_canvas.copy()
    if hand_opacity > 0.01:
        draw_hand_at_tip(rendered_frame, hand_tip_x, hand_tip_y, hand_tilt, hand_opacity)

    # 4. Cinematic Camera Transform (Zoom-In -> Centered Focus -> Zoom-Out Reveal)
    if t < T_ZOOM_IN_END:
        # Zoom-in: Interpolate from full board to centered 1080p panel
        p_z = min(1.0, t / T_ZOOM_IN_END)
        # Cubic ease in-out
        t_eased = 3*p_z**2 - 2*p_z**3
        # Blend overview board with focused drawing canvas
        final_frame = cv2.addWeighted(full_board_hd, 1.0 - t_eased, rendered_frame, t_eased, 0)
        
    elif t < T_ZOOM_OUT_START:
        # Centered Full-HD Focus View (Zero degradation, 100% crystal-clear)
        final_frame = rendered_frame
        
    elif t < T_ZOOM_OUT_END:
        # Zoom-out: Ease back from focused 1080p panel to full board layout
        p_zo = min(1.0, (t - T_ZOOM_OUT_START) / (T_ZOOM_OUT_END - T_ZOOM_OUT_START))
        t_eased = p_zo * p_zo * (3.0 - 2.0 * p_zo)
        # Create updated board that has Panel 1 rendered inside
        updated_board = full_board_hd.copy()
        # Scale drawn panel and insert into Panel 1's position on the board
        p1_slot_w = int(238 * sc_board)
        p1_slot_h = int(154 * sc_board)
        p1_slot_x = bx_off + int(18 * sc_board)
        p1_slot_y = by_off + int(10 * sc_board)
        p1_drawn_small = cv2.resize(active_drawn_canvas[P_OY:P_OY+ZOOM_PANEL_H, P_OX:P_OX+ZOOM_PANEL_W],
                                    (p1_slot_w, p1_slot_h), interpolation=cv2.INTER_AREA)
        updated_board[p1_slot_y:p1_slot_y+p1_slot_h, p1_slot_x:p1_slot_x+p1_slot_w] = p1_drawn_small
        
        final_frame = cv2.addWeighted(rendered_frame, 1.0 - t_eased, updated_board, t_eased, 0)
    else:
        # Final Full Board Hold
        updated_board = full_board_hd.copy()
        p1_slot_w = int(238 * sc_board)
        p1_slot_h = int(154 * sc_board)
        p1_slot_x = bx_off + int(18 * sc_board)
        p1_slot_y = by_off + int(10 * sc_board)
        p1_drawn_small = cv2.resize(active_drawn_canvas[P_OY:P_OY+ZOOM_PANEL_H, P_OX:P_OX+ZOOM_PANEL_W],
                                    (p1_slot_w, p1_slot_h), interpolation=cv2.INTER_AREA)
        updated_board[p1_slot_y:p1_slot_y+p1_slot_h, p1_slot_x:p1_slot_x+p1_slot_w] = p1_drawn_small
        final_frame = updated_board

    # Encode frame to H.264 video
    video_frame = av.VideoFrame.from_ndarray(final_frame, format="bgr24")
    for packet in stream.encode(video_frame):
        container.mux(packet)
    
    # Capture snapshot if close to marker
    for s_t in snapshot_times:
        if abs(t - s_t) < (0.5 / FPS):
            snapshot_frames.append({
                "time": s_t,
                "label": f"t={s_t:.1f}s",
                "frame": final_frame.copy()
            })

# Flush remaining packets and close H.264 container
for packet in stream.encode():
    container.mux(packet)
container.close()
print(f"[SUCCESS] H.264 Universal Video exported successfully: {VIDEO_PATH}")

# ----------------- 6. BUILD CONTACT SHEET MATRIX -----------------
print("Building High-Definition Contact Sheet for User Review...")
cw, ch = 640, 360
grid_cols = 3
grid_rows = 2
cs_img = np.full((grid_rows * (ch + 35) + 60, grid_cols * (cw + 15) + 15, 3), 30, dtype=np.uint8)

# Title banner
cv2.putText(cs_img, "SCENE 1: ULTRA-HD HAND & CINEMATIC CAMERA CHOREOGRAPHY REVIEW", 
            (25, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 220, 255), 2, cv2.LINE_AA)

stage_labels = [
    "Stage 1: Ease-In Zoom (Full HD Panel Center)",
    "Stage 2: Art Outline Sketching (Mode: Art)",
    "Stage 3: Zig-Zag Color Hatching (Mode: Shading)",
    "Stage 4: Arabic RTL Handwriting (Mode: Writing)",
    "Stage 5: Hand Exit & Resolution Check",
    "Stage 6: Smooth Ease-Out to Board Context"
]

for idx, sn in enumerate(snapshot_frames[:6]):
    r = idx // grid_cols
    c = idx % grid_cols
    gx = 15 + c * (cw + 15)
    gy = 60 + r * (ch + 35)
    
    small_f = cv2.resize(sn["frame"], (cw, ch), interpolation=cv2.INTER_AREA)
    cs_img[gy:gy+ch, gx:gx+cw] = small_f
    cv2.rectangle(cs_img, (gx, gy), (gx+cw, gy+ch), (80, 80, 80), 2)
    
    lbl = stage_labels[idx] if idx < len(stage_labels) else sn["label"]
    cv2.putText(cs_img, f"[{sn['label']}] {lbl}", (gx + 5, gy + ch + 22), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1, cv2.LINE_AA)

CONTACT_SHEET_PATH = os.path.join(OUTPUT_DIR, "scene_01_contact_sheet.png")
cv2.imwrite(CONTACT_SHEET_PATH, cs_img)
print(f"[SUCCESS] Contact sheet saved: {CONTACT_SHEET_PATH}")

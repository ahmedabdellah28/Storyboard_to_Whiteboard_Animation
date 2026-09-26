"""
Phase 6 — Professional Native Character & Text Whiteboard Animation
File: experiments/drawing_methods/render_native_character_and_text_animation.py

Leverages the project's AUTHENTIC native whiteboard engine:
1. CHARACTER ANIMATION (Outside-In Organic Decomposition):
   - Uses extract_dynamic_organic_parts & build_gapless_orbital_path (OUTSIDE_IN).
   - Traces the outer silhouette boundary first, then organic internal parts (Face, Hair, Hoodie, Folds).
   - Continuous Bézier air transits with calibrated hand compositing and cinematic viewport zoom.
2. TEXT WRITING ANIMATION (Harmonious RTL Handwriting):
   - Continuous pen tip trajectory along the Arabic baseline with ease-in/ease-out.
   - Ink reveals synchronously at pen nib with zero jump or lag.
"""
import os
import sys
import math
import cv2
import numpy as np

# Include kivy engine paths
sys.path.insert(0, r"E:\image_to_animate\kivy")
sys.path.insert(0, r"E:\image_to_animate\experiments\modular_pipeline")
sys.path.insert(0, r"E:\image_to_animate\experiments\draw_priority")

from engine.video.encoder import VideoEncoder
from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.viewport_transform import render_camera_viewport
from engine.render.concentric_engine import (
    DEFAULT_HAND_PATH,
    DEFAULT_HAND_MASK_PATH,
    PEN_TIP_ANCHOR_X,
    PEN_TIP_ANCHOR_Y,
    build_gapless_orbital_path
)
from engine.processing.dynamic_decomposition import (
    extract_dynamic_organic_parts,
    generate_smooth_bezier
)
from downstream_artifact_consumer import DownstreamArtifactConsumer

OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step6_drawing_methods"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Output Paths
CHAR_MP4_PATH = os.path.join(OUTPUT_DIR, "professional_character_animation.mp4")
TEXT_MP4_PATH = os.path.join(OUTPUT_DIR, "professional_text_animation.mp4")

# Load Hand Asset
hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
if hand_bgra is None:
    raise FileNotFoundError("Native hand asset missing.")

OUT_W, OUT_H = 1920, 1080
FPS = 30

# =============================================================================
# 1. CHARACTER DRAWING ANIMATION (OUTSIDE-IN ORGANIC DECOMPOSITION)
# =============================================================================
print("[NATIVE ENGINE] Starting Professional Character Animation (Outside-In)...")

p1_data = DownstreamArtifactConsumer.load_panel_artifacts(1)
gfx_p1 = p1_data["graphics_image"]
ph, pw = gfx_p1.shape[:2]

# Extract Boy Character from Step 3 Graphics
diff_g = 255.0 - gfx_p1.astype(np.float32)
ink_g = (np.max(diff_g, axis=2) > 26.0).astype(np.uint8) * 255

num_cc, lbls, stats, _ = cv2.connectedComponentsWithStats(ink_g)
boy_comp_idx = 1
for i in range(1, num_cc):
    bx, by, bw, bh, area = stats[i]
    if bh > ph * 0.35 and area > 500 and (bx + bw * 0.5) < pw * 0.40:
        boy_comp_idx = i
        break

bx, by, bw, bh, _ = stats[boy_comp_idx]
pad = 12
bx1, by1 = max(0, bx - pad), max(0, by - pad)
bx2, by2 = min(pw, bx + bw + pad), min(ph, by + bh + pad)

# Pure character artwork with exact organic boundary
char_crop = np.full((by2 - by1, bx2 - bx1, 3), 255, dtype=np.uint8)
c_mask = (lbls[by1:by2, bx1:bx2] == boy_comp_idx).astype(np.uint8) * 255
char_crop[c_mask > 0] = gfx_p1[by1:by2, bx1:bx2][c_mask > 0]

# Decompose Character using Native extract_dynamic_organic_parts
ch_h, ch_w = char_crop.shape[:2]
organic_parts = extract_dynamic_organic_parts(c_mask, char_crop, min_parts=4, max_parts=7)
print(f"  Character decomposed into {len(organic_parts)} organic anatomical layers (Outside -> Inside).")

# Setup Canvas Layout for Character Demo
char_scale = (OUT_H * 0.75) / float(ch_h)
scaled_cw = int(round(ch_w * char_scale))
scaled_ch = int(round(ch_h * char_scale))
char_resized = cv2.resize(char_crop, (scaled_cw, scaled_ch), interpolation=cv2.INTER_LANCZOS4)

pos_x = (OUT_W - scaled_cw) // 2
pos_y = (OUT_H - scaled_ch) // 2

target_full_canvas = np.full((OUT_H, OUT_W, 3), 255, dtype=np.uint8)
target_full_canvas[pos_y:pos_y+scaled_ch, pos_x:pos_x+scaled_cw] = char_resized

# Hand Scaling
hand_target_h = int(OUT_H * 0.32)
scale_h = hand_target_h / float(hand_bgra.shape[0])
new_hw = max(1, int(hand_bgra.shape[1] * scale_h))
hand_scaled = cv2.resize(hand_bgra, (new_hw, hand_target_h), interpolation=cv2.INTER_AREA)
scaled_tip_x = int(round(PEN_TIP_ANCHOR_X * scale_h))
scaled_tip_y = int(round(PEN_TIP_ANCHOR_Y * scale_h))

writer = VideoEncoder(CHAR_MP4_PATH, OUT_W, OUT_H, FPS, crf=18)
live_canvas = np.full((OUT_H, OUT_W, 3), 255, dtype=np.uint8)
ink_mask = np.zeros((OUT_H, OUT_W), dtype=np.uint8)

cam_center = (OUT_W / 2.0, OUT_H / 2.0)
cam_zoom = 1.65 # Cinematic focus on character

# Intro frames
current_pen = (pos_x + scaled_cw // 2, pos_y - 60)
for i in range(12):
    t = (i + 1) / 12.0
    cam_view = render_camera_viewport(live_canvas, cam_center[0], cam_center[1], 1.0 + (cam_zoom - 1.0) * t, OUT_W, OUT_H)
    writer.write(cam_view)

brush_r = max(3, int(round(5.0 * char_scale)))
step_px = 16.0

for p_idx, part in enumerate(organic_parts):
    p_mask = part["mask"]
    part_art = np.full_like(char_crop, 255)
    part_art[p_mask > 0] = char_crop[p_mask > 0]
    
    # 360° Orbital Paths from OUTSIDE to INSIDE
    strokes = build_gapless_orbital_path(part_art, ring_step=4, sample_interval=2.0, brush_radius=6, drawing_direction="OUTSIDE_IN")
    
    for stroke in strokes:
        if len(stroke) < 2:
            continue
        stroke_canvas = [(pos_x + int(round(pt[0] * char_scale)), pos_y + int(round(pt[1] * char_scale))) for pt in stroke]
        
        # Smooth Bézier air transit to stroke start
        transit = generate_smooth_bezier(current_pen, stroke_canvas[0], num_points=6)
        for t_pt in transit:
            frame_h = composite_hand_on_canvas_fast(live_canvas, hand_scaled, scaled_tip_x, scaled_tip_y, t_pt[0], t_pt[1])
            cam_view = render_camera_viewport(frame_h, cam_center[0], cam_center[1], cam_zoom, OUT_W, OUT_H)
            writer.write(cam_view)
            
        last_pt = stroke_canvas[0]
        accum = 0.0
        
        for nxt_pt in stroke_canvas[1:]:
            cv2.line(ink_mask, last_pt, nxt_pt, 255, thickness=brush_r * 2, lineType=cv2.LINE_AA)
            cv2.circle(ink_mask, nxt_pt, radius=brush_r, color=255, thickness=-1, lineType=cv2.LINE_AA)
            
            active = (ink_mask[pos_y:pos_y+scaled_ch, pos_x:pos_x+scaled_cw] > 0)
            live_canvas[pos_y:pos_y+scaled_ch, pos_x:pos_x+scaled_cw][active] = char_resized[active]
            
            accum += np.linalg.norm(np.array(nxt_pt) - np.array(last_pt))
            if accum >= step_px:
                frame_h = composite_hand_on_canvas_fast(live_canvas, hand_scaled, scaled_tip_x, scaled_tip_y, nxt_pt[0], nxt_pt[1])
                cam_view = render_camera_viewport(frame_h, cam_center[0], cam_center[1], cam_zoom, OUT_W, OUT_H)
                writer.write(cam_view)
                accum = 0.0
                
            last_pt = nxt_pt
        current_pen = last_pt

# Ensure 100% artwork revealed
live_canvas[pos_y:pos_y+scaled_ch, pos_x:pos_x+scaled_cw] = char_resized

# Outro: Hand leaves surface smoothly & Zoom out to view complete character
exit_pts = generate_smooth_bezier(current_pen, (OUT_W + 150, OUT_H + 150), num_points=12)
for idx, e_pt in enumerate(exit_pts):
    t = idx / float(len(exit_pts))
    z = cam_zoom + (1.0 - cam_zoom) * t
    frame_h = composite_hand_on_canvas_fast(live_canvas, hand_scaled, scaled_tip_x, scaled_tip_y, e_pt[0], e_pt[1])
    cam_view = render_camera_viewport(frame_h, cam_center[0], cam_center[1], z, OUT_W, OUT_H)
    writer.write(cam_view)

# Hold final frame
final_view = render_camera_viewport(live_canvas, cam_center[0], cam_center[1], 1.0, OUT_W, OUT_H)
for _ in range(30):
    writer.write(final_view)
writer.release()
print(f"[SUCCESS] Native Character Video Exported: {CHAR_MP4_PATH}")


# =============================================================================
# 2. TEXT WRITING ANIMATION (HARMONIOUS RTL HANDWRITING)
# =============================================================================
print("[NATIVE ENGINE] Starting Professional Text Animation (Harmonious RTL)...")

txt_p1 = p1_data["typography_image"]
diff_t = 255.0 - txt_p1.astype(np.float32)
txt_ink = (np.max(diff_t, axis=2) > 26.0).astype(np.uint8) * 255

# Crop the speech bubble text region: "ثق بنفسك", "لا تستسلم.", "ركز على هدفك", "كل يوم خطوة للأمام"
tx_min, ty_min, tw, th = int(pw * 0.44), int(ph * 0.20), int(pw * 0.46), int(ph * 0.65)
sub_text_art = txt_p1[ty_min:ty_min+th, tx_min:tx_min+tw]
sub_text_ink = txt_ink[ty_min:ty_min+th, tx_min:tx_min+tw]

# Scale up for clean widescreen display
t_scale = (OUT_H * 0.65) / float(th)
scaled_tw = int(round(tw * t_scale))
scaled_th = int(round(th * t_scale))
text_resized = cv2.resize(sub_text_art, (scaled_tw, scaled_th), interpolation=cv2.INTER_LANCZOS4)
text_ink_resized = cv2.resize(sub_text_ink, (scaled_tw, scaled_th), interpolation=cv2.INTER_NEAREST)

pos_tx = (OUT_W - scaled_tw) // 2
pos_ty = (OUT_H - scaled_th) // 2

# Identify lines
num_t, lbl_t, stat_t, _ = cv2.connectedComponentsWithStats(text_ink_resized)
glyphs = []
for i in range(1, num_t):
    gx, gy, gw, gh, ga = stat_t[i]
    if ga < 4: continue
    glyphs.append({"bbox": (gx, gy, gw, gh), "cx": gx + gw/2.0, "cy": gy + gh/2.0, "mask": (lbl_t == i)})

glyphs.sort(key=lambda g: g["cy"])
text_lines = []
if glyphs:
    cur_l = [glyphs[0]]
    ly1, ly2 = glyphs[0]["bbox"][1], glyphs[0]["bbox"][1] + glyphs[0]["bbox"][3]
    for g in glyphs[1:]:
        gy, gh = g["bbox"][1], g["bbox"][3]
        if gy <= ly2 + 10 and (gy + gh) >= ly1 - 10:
            cur_l.append(g)
            ly1 = min(ly1, gy)
            ly2 = max(ly2, gy + gh)
        else:
            text_lines.append(cur_l)
            cur_l = [g]
            ly1, ly2 = gy, gy + gh
    if cur_l: text_lines.append(cur_l)

writer_t = VideoEncoder(TEXT_MP4_PATH, OUT_W, OUT_H, FPS, crf=18)
live_canvas_t = np.full((OUT_H, OUT_W, 3), 255, dtype=np.uint8)

cam_center_t = (OUT_W / 2.0, OUT_H / 2.0)
cam_zoom_t = 1.45

# Intro
current_pen_t = (pos_tx + scaled_tw, pos_ty - 40)
for i in range(10):
    t = (i + 1) / 10.0
    cam_v = render_camera_viewport(live_canvas_t, cam_center_t[0], cam_center_t[1], 1.0 + (cam_zoom_t - 1.0) * t, OUT_W, OUT_H)
    writer_t.write(cam_v)

for l_idx, line in enumerate(text_lines):
    # Sort glyphs in reading order (Right to Left: descending X)
    line.sort(key=lambda g: g["cx"], reverse=True)
    
    lx_max = max(g["bbox"][0] + g["bbox"][2] for g in line)
    lx_min = min(g["bbox"][0] for g in line)
    ly_mid = int(np.mean([g["cy"] for g in line]))
    
    line_start_pt = (pos_tx + lx_max, pos_ty + ly_mid)
    
    # Smooth Bézier air transit to start of line
    air_transit = generate_smooth_bezier(current_pen_t, line_start_pt, num_points=8)
    for a_pt in air_transit:
        frame_h = composite_hand_on_canvas_fast(live_canvas_t, hand_scaled, scaled_tip_x, scaled_tip_y, a_pt[0], a_pt[1])
        cam_v = render_camera_viewport(frame_h, cam_center_t[0], cam_center_t[1], cam_zoom_t, OUT_W, OUT_H)
        writer_t.write(cam_v)
        
    # Write line along RTL trajectory
    line_duration_frames = max(24, int((lx_max - lx_min) / 9.0))
    for f in range(line_duration_frames + 1):
        progress = f / float(line_duration_frames)
        # Easing: natural pen speed
        ease_p = progress * progress * (3.0 - 2.0 * progress)
        cur_x_rel = lx_max - ease_p * (lx_max - lx_min)
        
        # Reveal pixels to the right of pen
        revealed_mask = np.zeros((scaled_th, scaled_tw), dtype=bool)
        for g in line:
            if g["bbox"][0] >= cur_x_rel - 12:
                revealed_mask |= g["mask"]
            elif g["bbox"][0] + g["bbox"][2] >= cur_x_rel:
                pm = g["mask"].copy()
                pm[:, :int(cur_x_rel)] = False
                revealed_mask |= pm
                
        # Update canvas
        live_canvas_t[pos_ty:pos_ty+scaled_th, pos_tx:pos_tx+scaled_tw][revealed_mask] = text_resized[revealed_mask]
        
        # Pen coordinate with natural writing micro-vibration
        pen_gx = pos_tx + cur_x_rel
        pen_gy = pos_ty + ly_mid + 3.0 * math.sin(progress * 18.0)
        
        frame_h = composite_hand_on_canvas_fast(live_canvas_t, hand_scaled, scaled_tip_x, scaled_tip_y, int(pen_gx), int(pen_gy))
        cam_v = render_camera_viewport(frame_h, cam_center_t[0], cam_center_t[1], cam_zoom_t, OUT_W, OUT_H)
        writer_t.write(cam_v)
        current_pen_t = (int(pen_gx), int(pen_gy))

# Ensure all text is 100% rendered
all_text_mask = np.zeros((scaled_th, scaled_tw), dtype=bool)
for l in text_lines:
    for g in l:
        all_text_mask |= g["mask"]
live_canvas_t[pos_ty:pos_ty+scaled_th, pos_tx:pos_tx+scaled_tw][all_text_mask] = text_resized[all_text_mask]

# Outro exit
exit_pts = generate_smooth_bezier(current_pen_t, (OUT_W + 150, OUT_H + 150), num_points=12)
for idx, e_pt in enumerate(exit_pts):
    t = idx / float(len(exit_pts))
    z = cam_zoom_t + (1.0 - cam_zoom_t) * t
    frame_h = composite_hand_on_canvas_fast(live_canvas_t, hand_scaled, scaled_tip_x, scaled_tip_y, e_pt[0], e_pt[1])
    cam_v = render_camera_viewport(frame_h, cam_center_t[0], cam_center_t[1], z, OUT_W, OUT_H)
    writer_t.write(cam_v)

for _ in range(30):
    final_v = render_camera_viewport(live_canvas_t, cam_center_t[0], cam_center_t[1], 1.0, OUT_W, OUT_H)
    writer_t.write(final_v)

writer_t.release()
print(f"[SUCCESS] Native Text Video Exported: {TEXT_MP4_PATH}")
print("="*80 + "\n")

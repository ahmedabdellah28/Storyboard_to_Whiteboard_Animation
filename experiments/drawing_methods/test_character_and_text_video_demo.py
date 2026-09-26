"""
Phase 6 — Character & Text Drawing Methods Video Demo
File: experiments/drawing_methods/test_character_and_text_video_demo.py

Demonstrates:
1. CHARACTER DRAWING via Native Engine:
   - Feeds the exact organic boundary of the character into the native DedicatedCharacterEngine.
   - Draws outer contours (Silhouettes) first -> Inner details (Face, eyes, hair, folds) -> Outside-in color shading.
2. HARMONIOUS HANDWRITING SIMULATION:
   - Natural fluid RTL baseline stroke trajectory.
   - Pen nib perfectly aligned with progressive ink emergence.
   - Smooth pen transit between lines.
3. Exports:
   - character_drawing_demo.mp4
   - text_writing_demo.mp4
   - character_drawing_stages.png
   - text_writing_stages.png
"""
import os
import sys
import math
import cv2
import numpy as np
import av

# Add engine paths
sys.path.insert(0, r"E:\image_to_animate\kivy")
sys.path.insert(0, r"E:\image_to_animate\experiments\modular_pipeline")
sys.path.insert(0, r"E:\image_to_animate\experiments\draw_priority")

from m3_character_engine import DedicatedCharacterEngine
from downstream_artifact_consumer import DownstreamArtifactConsumer

OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step6_drawing_methods"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HAND_PATH = r"E:\image_to_animate\kivy\data\images\drawing-hand.png"

# =============================================================================
# 1. SETUP HAND SPRITE & COMPOSITOR
# =============================================================================
hand_raw = cv2.imread(HAND_PATH, cv2.IMREAD_UNCHANGED)
if hand_raw is None:
    raise FileNotFoundError(f"Hand asset missing: {HAND_PATH}")

HAND_W = 380
HAND_H = int(hand_raw.shape[0] * (HAND_W / float(hand_raw.shape[1])))
hand_sprite = cv2.resize(hand_raw, (HAND_W, HAND_H), interpolation=cv2.INTER_LANCZOS4)
hand_bgr = hand_sprite[:, :, :3]
hand_alpha = hand_sprite[:, :, 3].astype(np.float32) / 255.0

TIP_ANCHOR_X = int(HAND_W * 0.08)
TIP_ANCHOR_Y = int(HAND_H * 0.05)

def overlay_hand(canvas: np.ndarray, tip_x: float, tip_y: float, tilt_deg: float = -32.0):
    """Blends drawing hand onto canvas at precise pen tip anchor."""
    sh, sw = hand_bgr.shape[:2]
    M = cv2.getRotationMatrix2D((TIP_ANCHOR_X, TIP_ANCHOR_Y), tilt_deg, 1.0)
    rot_bgr = cv2.warpAffine(hand_bgr, M, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    rot_alpha = cv2.warpAffine(hand_alpha, M, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)

    x1, y1 = int(tip_x - TIP_ANCHOR_X), int(tip_y - TIP_ANCHOR_Y)
    x2, y2 = x1 + sw, y1 + sh

    cx1, cy1 = max(0, x1), max(0, y1)
    cx2, cy2 = min(canvas.shape[1], x2), min(canvas.shape[0], y2)

    if cx2 <= cx1 or cy2 <= cy1:
        return

    sx1, sy1 = cx1 - x1, cy1 - y1
    sx2, sy2 = sx1 + (cx2 - cx1), sy1 + (cy2 - cy1)

    sub_alpha = rot_alpha[sy1:sy2, sx1:sx2, np.newaxis]
    sub_hand = rot_bgr[sy1:sy2, sx1:sx2]
    canvas[cy1:cy2, cx1:cx2] = (canvas[cy1:cy2, cx1:cx2] * (1.0 - sub_alpha) + sub_hand * sub_alpha).astype(np.uint8)


# =============================================================================
# 2. PART A: CHARACTER DRAWING DEMO (OUTLINES -> DETAILS -> OUTSIDE-IN FILLS)
# =============================================================================
print("[PHASE 6 DEMO] Initializing Character Drawing Test using Native Engine...")

# Load Panel 1 Graphics Artifact
p1_data = DownstreamArtifactConsumer.load_panel_artifacts(1)
gfx_p1 = p1_data["graphics_image"]
ph, pw = gfx_p1.shape[:2]

# Extract Boy Character Mask (Step 3 Organic Silhouette)
diff_g = 255.0 - gfx_p1.astype(np.float32)
dist_g = np.max(diff_g, axis=2)
ink_g = (dist_g > 26.0).astype(np.uint8) * 255

num_cc, lbls, stats, _ = cv2.connectedComponentsWithStats(ink_g)
# Boy character component is on the left
boy_comp_idx = 1
for i in range(1, num_cc):
    bx, by, bw, bh, area = stats[i]
    if bh > ph * 0.35 and area > 500 and (bx + bw * 0.5) < pw * 0.40:
        boy_comp_idx = i
        break

boy_mask = (lbls == boy_comp_idx).astype(np.uint8) * 255
boy_crop_isolated = np.full_like(gfx_p1, 255)
boy_crop_isolated[boy_mask > 0] = gfx_p1[boy_mask > 0]

# Upscale to crisp HD resolution for beautiful demonstration
HD_W, HD_H = 1280, 720
CANVAS_PAD_X, CANVAS_PAD_Y = 240, 60
CANVAS_DRAW_W = 540
CANVAS_DRAW_H = int(CANVAS_DRAW_W * (ph / float(pw)))

boy_hd = cv2.resize(boy_crop_isolated, (CANVAS_DRAW_W, CANVAS_DRAW_H), interpolation=cv2.INTER_LANCZOS4)

# Pass Character to Native DedicatedCharacterEngine
engine = DedicatedCharacterEngine()
char_engine_data = engine.process_graphics(boy_hd)
ordered_strokes = char_engine_data["ordered_strokes"]
color_regions = char_engine_data["color_regions"]

print(f"  Character Engine identified: {len(ordered_strokes)} structural strokes & {len(color_regions)} color regions.")

# Video setup for Character
FPS = 30
DURATION_SEC = 5.0
TOTAL_FRAMES = int(FPS * DURATION_SEC)

CHAR_VIDEO_PATH = os.path.join(OUTPUT_DIR, "character_drawing_demo.mp4")
container = av.open(CHAR_VIDEO_PATH, mode="w")
stream = container.add_stream("h264", rate=FPS)
stream.width = HD_W
stream.height = HD_H
stream.pix_fmt = "yuv420p"
stream.options = {"crf": "18", "preset": "medium"}

char_snapshots = []
snapshot_milestones = [0.15, 0.40, 0.65, 0.85, 1.0]

for f_idx in range(TOTAL_FRAMES):
    t = f_idx / float(TOTAL_FRAMES)
    frame = np.full((HD_H, HD_W, 3), 255, dtype=np.uint8)
    
    # Target canvas for character
    char_canvas = np.full((CANVAS_DRAW_H, CANVAS_DRAW_W, 3), 255, dtype=np.uint8)
    
    # Phase 1: 0% to 50% -> Outlines (Outside silhouette) and Internal Facial Lines
    # Phase 2: 50% to 100% -> Color Fills (Hoodie, Skin, Hair) from Outside in
    tip_x, tip_y = -100, -100
    
    if t <= 0.50:
        stroke_p = t / 0.50
        num_s = int(stroke_p * len(ordered_strokes))
        for s_i in range(num_s):
            stk = ordered_strokes[s_i]
            for pt in stk.points:
                cv2.circle(char_canvas, (int(pt[0]), int(pt[1])), max(1, int(stk.width * 0.7)), (30, 30, 30), -1)
        if num_s > 0 and len(ordered_strokes[num_s - 1].points) > 0:
            last_pt = ordered_strokes[num_s - 1].points[-1]
            tip_x = CANVAS_PAD_X + last_pt[0]
            tip_y = CANVAS_PAD_Y + last_pt[1]
    else:
        # Full strokes rendered
        for stk in ordered_strokes:
            for pt in stk.points:
                cv2.circle(char_canvas, (int(pt[0]), int(pt[1])), max(1, int(stk.width * 0.7)), (30, 30, 30), -1)
                
        # Progressive outside-in shading
        fill_p = (t - 0.50) / 0.50
        num_f = int(fill_p * len(color_regions))
        for r_i in range(num_f):
            r = color_regions[r_i]
            r_mask = cv2.resize(r.mask, (CANVAS_DRAW_W, CANVAS_DRAW_H), interpolation=cv2.INTER_NEAREST)
            char_canvas[r_mask > 0] = boy_hd[r_mask > 0]
            
        if num_f > 0 and num_f - 1 < len(color_regions):
            cur_r = color_regions[num_f - 1]
            tip_x = CANVAS_PAD_X + cur_r.center[0]
            tip_y = CANVAS_PAD_Y + cur_r.center[1]

    # Mount character on HD frame
    frame[CANVAS_PAD_Y:CANVAS_PAD_Y+CANVAS_DRAW_H, CANVAS_PAD_X:CANVAS_PAD_X+CANVAS_DRAW_W] = char_canvas
    
    # Overlay Title Card
    cv2.rectangle(frame, (0, 0), (HD_W, 55), (35, 30, 25), -1)
    phase_label = "PHASE 1: OUTLINES & FACIAL DETAILING (خارج للداخل)" if t <= 0.50 else "PHASE 2: PROGRESSIVE TRUECOLOR COLORING"
    cv2.putText(frame, f"CHARACTER DRAWING TEST: {phase_label}", (30, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 2, cv2.LINE_AA)
    
    # Overlay Hand
    if tip_x > 0 and tip_y > 0:
        overlay_hand(frame, tip_x, tip_y, tilt_deg=-30.0)
        
    v_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
    for pkt in stream.encode(v_frame):
        container.mux(pkt)
        
    # Record milestone snapshots
    for m_t in snapshot_milestones:
        if abs(t - m_t) < (0.5 / TOTAL_FRAMES):
            char_snapshots.append((m_t, frame.copy()))

for pkt in stream.encode():
    container.mux(pkt)
container.close()
print(f"[SUCCESS] Exported Character Pilot Video: {CHAR_VIDEO_PATH}")


# =============================================================================
# 3. PART B: HARMONIOUS HANDWRITING SIMULATION (ARABIC RTL)
# =============================================================================
print("[PHASE 6 DEMO] Initializing Harmonious Handwriting Simulation Video...")

# Extract Arabic text lines from Panel 1
txt_p1 = p1_data["typography_image"]
diff_t = 255.0 - txt_p1.astype(np.float32)
txt_ink = (np.max(diff_t, axis=2) > 26.0).astype(np.uint8) * 255

TEXT_VIDEO_PATH = os.path.join(OUTPUT_DIR, "text_writing_demo.mp4")
container_t = av.open(TEXT_VIDEO_PATH, mode="w")
stream_t = container_t.add_stream("h264", rate=FPS)
stream_t.width = HD_W
stream_t.height = HD_H
stream_t.pix_fmt = "yuv420p"
stream_t.options = {"crf": "18", "preset": "medium"}

# Focus on the speech bubble text area in HD
C_X, C_Y, C_W, C_H = int(pw * 0.45), int(ph * 0.20), int(pw * 0.45), int(ph * 0.65)
sub_txt_ink = txt_ink[C_Y:C_Y+C_H, C_X:C_X+C_W]
sub_txt_bgr = txt_p1[C_Y:C_Y+C_H, C_X:C_X+C_W]

TXT_DRAW_W = 600
TXT_DRAW_H = int(TXT_DRAW_W * (C_H / float(C_W)))
sub_txt_hd = cv2.resize(sub_txt_bgr, (TXT_DRAW_W, TXT_DRAW_H), interpolation=cv2.INTER_LANCZOS4)
sub_ink_hd = cv2.resize(sub_txt_ink, (TXT_DRAW_W, TXT_DRAW_H), interpolation=cv2.INTER_NEAREST)

# Identify individual horizontal lines in text
num_t, lbl_t, stat_t, _ = cv2.connectedComponentsWithStats(sub_ink_hd)
line_crops = []
t_glyphs = []
for i in range(1, num_t):
    gx, gy, gw, gh, ga = stat_t[i]
    if ga < 4: continue
    t_glyphs.append({"bbox": (gx, gy, gw, gh), "cx": gx + gw/2.0, "cy": gy + gh/2.0, "mask": (lbl_t == i)})

t_glyphs.sort(key=lambda g: g["cy"])
# Group into lines
text_lines_hd = []
if t_glyphs:
    curr_l = [t_glyphs[0]]
    ly1, ly2 = t_glyphs[0]["bbox"][1], t_glyphs[0]["bbox"][1] + t_glyphs[0]["bbox"][3]
    for g in t_glyphs[1:]:
        gy, gh = g["bbox"][1], g["bbox"][3]
        if gy <= ly2 + 8 and (gy + gh) >= ly1 - 8:
            curr_l.append(g)
            ly1 = min(ly1, gy)
            ly2 = max(ly2, gy + gh)
        else:
            text_lines_hd.append(curr_l)
            curr_l = [g]
            ly1, ly2 = gy, gy + gh
    if curr_l: text_lines_hd.append(curr_l)

TEXT_FRAMES = int(FPS * 4.5)
text_snapshots = []
t_milestones = [0.20, 0.45, 0.70, 0.90, 1.0]

for f_idx in range(TEXT_FRAMES):
    t = f_idx / float(TEXT_FRAMES)
    frame = np.full((HD_H, HD_W, 3), 255, dtype=np.uint8)
    txt_canvas = np.full((TXT_DRAW_H, TXT_DRAW_W, 3), 255, dtype=np.uint8)
    
    # Calculate which line is currently being written
    total_lines = max(1, len(text_lines_hd))
    line_progress_total = t * total_lines
    active_line_idx = min(total_lines - 1, int(line_progress_total))
    line_sub_t = line_progress_total - active_line_idx
    
    # 1. Render all previously completed lines
    for prev_idx in range(active_line_idx):
        for g in text_lines_hd[prev_idx]:
            txt_canvas[g["mask"]] = sub_txt_hd[g["mask"]]
            
    # 2. Render active line with smooth RTL sweep (Right to Left: 1.0 -> 0.0)
    act_line = text_lines_hd[active_line_idx]
    lx_min = min(g["bbox"][0] for g in act_line)
    lx_max = max(g["bbox"][0] + g["bbox"][2] for g in act_line)
    ly_mid = int(np.mean([g["cy"] for g in act_line]))
    
    # RTL pen position
    pen_rel_x = lx_max - line_sub_t * (lx_max - lx_min)
    
    # Reveal glyphs to the right of current pen position
    for g in act_line:
        if g["bbox"][0] >= pen_rel_x - 10:
            txt_canvas[g["mask"]] = sub_txt_hd[g["mask"]]
        elif g["bbox"][0] + g["bbox"][2] >= pen_rel_x:
            # Partial glyph reveal
            part_mask = g["mask"].copy()
            part_mask[:, :int(pen_rel_x)] = False
            txt_canvas[part_mask] = sub_txt_hd[part_mask]
            
    # Global pen position
    T_PAD_X, T_PAD_Y = 320, 120
    global_tip_x = T_PAD_X + pen_rel_x
    global_tip_y = T_PAD_Y + ly_mid
    
    # Mount text canvas on frame
    frame[T_PAD_Y:T_PAD_Y+TXT_DRAW_H, T_PAD_X:T_PAD_X+TXT_DRAW_W] = txt_canvas
    
    # Title Banner
    cv2.rectangle(frame, (0, 0), (HD_W, 55), (20, 35, 40), -1)
    cv2.putText(frame, "HARMONIOUS HANDWRITING TEST: FLUID RTL INK FLOW (متابعة القلم للكتابة العربية)", 
                (30, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (50, 255, 130), 2, cv2.LINE_AA)
                
    # Overlay Hand
    overlay_hand(frame, global_tip_x, global_tip_y, tilt_deg=-34.0)
    
    v_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
    for pkt in stream_t.encode(v_frame):
        container_t.mux(pkt)
        
    for m_t in t_milestones:
        if abs(t - m_t) < (0.5 / TEXT_FRAMES):
            text_snapshots.append((m_t, frame.copy()))

for pkt in stream_t.encode():
    container_t.mux(pkt)
container_t.close()
print(f"[SUCCESS] Exported Text Handwriting Pilot Video: {TEXT_VIDEO_PATH}")


# =============================================================================
# 4. GENERATE STAGE SHEETS (CONTACT SHEETS)
# =============================================================================
# A. Character Drawing Stages Sheet
cs_w, cs_h = 240, 135
cs_img = np.full((cs_h + 65, 5 * (cs_w + 12) + 12, 3), 245, dtype=np.uint8)
cv2.rectangle(cs_img, (0, 0), (cs_img.shape[1], 45), (35, 30, 25), -1)
cv2.putText(cs_img, "CHARACTER DRAWING SEQUENCE: OUTLINES -> FACIAL DETAILS -> OUTSIDE-IN FILLS", 
            (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 220, 255), 2, cv2.LINE_AA)

stage_labels_char = [
    "1. Outer Outline Sketch",
    "2. Facial & Hair Detailing",
    "3. Hoodie Infill Begins",
    "4. Shading & Skin Tone",
    "5. Fully Completed Character"
]

for idx, (m_t, snap) in enumerate(char_snapshots[:5]):
    gx = 12 + idx * (cs_w + 12)
    gy = 55
    sc = cv2.resize(snap, (cs_w, cs_h), interpolation=cv2.INTER_AREA)
    cs_img[gy:gy+cs_h, gx:gx+cs_w] = sc
    cv2.rectangle(cs_img, (gx, gy), (gx+cs_w, gy+cs_h), (180, 160, 130), 1)
    cv2.rectangle(cs_img, (gx, gy+cs_h), (gx+cs_w, gy+cs_h+20), (45, 40, 30), -1)
    cv2.putText(cs_img, stage_labels_char[idx], (gx+4, gy+cs_h+15), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 220, 255), 1, cv2.LINE_AA)

CHAR_STAGES_PATH = os.path.join(OUTPUT_DIR, "character_drawing_stages.png")
cv2.imwrite(CHAR_STAGES_PATH, cs_img)
print(f"[SUCCESS] Saved Character Stages Sheet: {CHAR_STAGES_PATH}")

# B. Text Writing Stages Sheet
ts_img = np.full((cs_h + 65, 5 * (cs_w + 12) + 12, 3), 245, dtype=np.uint8)
cv2.rectangle(ts_img, (0, 0), (ts_img.shape[1], 45), (20, 35, 40), -1)
cv2.putText(ts_img, "HARMONIOUS HANDWRITING SEQUENCE: LINE-BY-LINE FLUID RTL PEN SYNCHRONIZATION", 
            (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (50, 255, 130), 2, cv2.LINE_AA)

stage_labels_txt = [
    "1. Line 1: 'ثق' Ink Emergence",
    "2. Line 1 Completed -> RTL",
    "3. Line 2: 'لا تستسلم' Begins",
    "4. Line 2 Completed",
    "5. Pen Retracts from Surface"
]

for idx, (m_t, snap) in enumerate(text_snapshots[:5]):
    gx = 12 + idx * (cs_w + 12)
    gy = 55
    sc = cv2.resize(snap, (cs_w, cs_h), interpolation=cv2.INTER_AREA)
    ts_img[gy:gy+cs_h, gx:gx+cs_w] = sc
    cv2.rectangle(ts_img, (gx, gy), (gx+cs_w, gy+cs_h), (140, 180, 160), 1)
    cv2.rectangle(ts_img, (gx, gy+cs_h), (gx+cs_w, gy+cs_h+20), (30, 45, 50), -1)
    cv2.putText(ts_img, stage_labels_txt[idx], (gx+4, gy+cs_h+15), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (50, 255, 130), 1, cv2.LINE_AA)

TXT_STAGES_PATH = os.path.join(OUTPUT_DIR, "text_writing_stages.png")
cv2.imwrite(TXT_STAGES_PATH, ts_img)
print(f"[SUCCESS] Saved Text Stages Sheet: {TXT_STAGES_PATH}")
print("="*80 + "\n")

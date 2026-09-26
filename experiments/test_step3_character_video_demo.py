"""
Step 3 Character Engine Video Demo:
Demonstrates the exact internal drawing sequence of the Character Engine:
1. Outer Outlines (Silhouette)
2. Facial Features & Internal Detailing (Eyes, Nose, Smile, Folds)
3. Progressive TrueColor Fill (Blue Hoodie, Skin Tone, Dark Hair, Yellow Emoji)
"""
import os
import sys
import math
import cv2
import numpy as np
import av

# Add paths
sys.path.insert(0, r"E:\image_to_animate\kivy")
sys.path.insert(0, r"E:\image_to_animate\experiments\modular_pipeline")

from m3_character_engine import DedicatedCharacterEngine

INPUT_GRAPHICS_PATH = r"E:\image_to_animate\experiments\results\step2_split_layers\panel_01_01_graphics.png"
HAND_PATH = r"E:\image_to_animate\kivy\data\images\drawing-hand.png"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step3_character_engine"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Load Graphics Image
gfx_img_small = cv2.imread(INPUT_GRAPHICS_PATH)
gh_s, gw_s = gfx_img_small.shape[:2]

# Scale up for crisp 1080p rendering
HD_W, HD_H = 1920, 1080
PANEL_W = 1400
PANEL_H = int(PANEL_W * (gh_s / float(gw_s)))

gfx_hd = cv2.resize(gfx_img_small, (PANEL_W, PANEL_H), interpolation=cv2.INTER_LANCZOS4)

# 2. Run Character Engine
engine = DedicatedCharacterEngine()
char_data = engine.process_graphics(gfx_hd)

# 3. Setup Hand
hand_img = cv2.imread(HAND_PATH, cv2.IMREAD_UNCHANGED)
target_hand_w = 420
target_hand_h = int(hand_img.shape[0] * (target_hand_w / float(hand_img.shape[1])))
hand_sprite = cv2.resize(hand_img, (target_hand_w, target_hand_h), interpolation=cv2.INTER_LANCZOS4)
hand_bgr = hand_sprite[:, :, :3]
hand_alpha = hand_sprite[:, :, 3].astype(np.float32) / 255.0
TIP_X = int(target_hand_w * 0.08)
TIP_Y = int(target_hand_h * 0.05)

def draw_hand(canvas, tip_x, tip_y, tilt_deg=-35.0):
    sh, sw = hand_bgr.shape[:2]
    M = cv2.getRotationMatrix2D((TIP_X, TIP_Y), tilt_deg, 1.0)
    rot_bgr = cv2.warpAffine(hand_bgr, M, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))
    rot_alpha = cv2.warpAffine(hand_alpha, M, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
    
    x1, y1 = int(tip_x - TIP_X), int(tip_y - TIP_Y)
    x2, y2 = x1 + sw, y1 + sh
    
    cx1, cy1 = max(0, x1), max(0, y1)
    cx2, cy2 = min(canvas.shape[1], x2), min(canvas.shape[0], y2)
    if cx2 <= cx1 or cy2 <= cy1: return
    
    sx1, sy1 = cx1 - x1, cy1 - y1
    sx2, sy2 = sx1 + (cx2 - cx1), sy1 + (cy2 - cy1)
    sub_a = rot_alpha[sy1:sy2, sx1:sx2, np.newaxis]
    sub_b = rot_bgr[sy1:sy2, sx1:sx2]
    canvas[cy1:cy2, cx1:cx2] = (canvas[cy1:cy2, cx1:cx2] * (1.0 - sub_a) + sub_b * sub_a).astype(np.uint8)

# 4. Render Video
FPS = 30
DURATION = 8.0 # seconds
TOTAL_FRAMES = int(FPS * DURATION)

VIDEO_PATH = os.path.join(OUTPUT_DIR, "step3_character_drawing_demo.mp4")
container = av.open(VIDEO_PATH, mode="w")
stream = container.add_stream("h264", rate=FPS)
stream.width = HD_W
stream.height = HD_H
stream.pix_fmt = "yuv420p"
stream.options = {"crf": "20", "preset": "fast"}

P_OX = (HD_W - PANEL_W) // 2
P_OY = (HD_H - PANEL_H) // 2

panel_canvas = np.full((PANEL_H, PANEL_W, 3), 255, dtype=np.uint8)

# Stages:
# 0.0s - 3.5s: Strokes (Outlines -> Details)
# 3.5s - 7.0s: Progressive Fills (Hoodie -> Skin -> Hair -> Emoji)
# 7.0s - 8.0s: Final Hold

snapshot_times = [1.2, 2.8, 4.5, 6.2, 7.5]
snapshot_frames = []

for f_idx in range(TOTAL_FRAMES):
    t = f_idx / float(FPS)
    
    p_stroke = min(1.0, t / 3.5)
    p_fill = 0.0 if t < 3.5 else min(1.0, (t - 3.5) / 3.5)
    
    tip_x_l, tip_y_l, tilt = DedicatedCharacterEngine.render_frame_progress(
        panel_canvas, char_data, p_stroke, p_fill
    )
    
    frame = np.full((HD_H, HD_W, 3), 255, dtype=np.uint8)
    frame[P_OY:P_OY+PANEL_H, P_OX:P_OX+PANEL_W] = panel_canvas
    
    if t < 7.0 and tip_x_l > 0:
        draw_hand(frame, P_OX + tip_x_l, P_OY + tip_y_l, tilt)
        
    v_f = av.VideoFrame.from_ndarray(frame, format="bgr24")
    for pkt in stream.encode(v_f):
        container.mux(pkt)
        
    for s_t in snapshot_times:
        if abs(t - s_t) < (0.5 / FPS):
            snapshot_frames.append({
                "time": s_t,
                "label": f"t={s_t:.1f}s",
                "frame": frame.copy()
            })

for pkt in stream.encode():
    container.mux(pkt)
container.close()

# Contact Sheet
cw, ch = 560, 315
cols = len(snapshot_frames)
cs_img = np.full((ch + 60, cols * (cw + 15) + 15, 3), 35, dtype=np.uint8)
cv2.putText(cs_img, "STEP 3: CHARACTER ENGINE DRAWING SEQUENCE (OUTLINES -> DETAILS -> TRUECOLOR FILLS)",
            (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 2, cv2.LINE_AA)

stage_names = [
    "1. Outer Outline Sketch",
    "2. Facial & Hair Detailing",
    "3. Blue Hoodie Progressive Fill",
    "4. Skin & Emoji TrueColor Shading",
    "5. Completed Graphics Layer"
]

for idx, sn in enumerate(snapshot_frames[:5]):
    gx = 15 + idx * (cw + 15)
    gy = 45
    small = cv2.resize(sn["frame"], (cw, ch), interpolation=cv2.INTER_AREA)
    cs_img[gy:gy+ch, gx:gx+cw] = small
    cv2.rectangle(cs_img, (gx, gy), (gx+cw, gy+ch), (80, 80, 80), 2)
    s_name = stage_names[idx] if idx < len(stage_names) else sn["label"]
    cv2.putText(cs_img, f"[{sn['label']}] {s_name}", (gx + 5, gy + ch - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1, cv2.LINE_AA)

CS_PATH = os.path.join(OUTPUT_DIR, "step3_drawing_sequence_sheet.png")
cv2.imwrite(CS_PATH, cs_img)
print(f"[STEP 3] Saved Video: {VIDEO_PATH}")
print(f"[STEP 3] Saved Sequence Sheet: {CS_PATH}")

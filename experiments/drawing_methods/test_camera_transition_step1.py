"""
Step 1 Camera Transition & Fusion Test (Panel 1 -> Panel 2)
File: experiments/drawing_methods/test_camera_transition_step1.py

Adheres Strictly to Core Code Architecture (kivy/engine):
- CameraShot, CameraAnimator, CameraState, get_easing("ease_in_out_cubic").
- Sequence:
  1. Panel 1 Full Drawing (Locked Focus).
  2. Reveal Hold (0.6s).
  3. TRANSITION_TO_PANEL_2: 40-frame (1.33s) ease_in_out_cubic glide.
  4. Panel 2 Full Drawing (Locked Focus).
  5. Final Hold (1.5s).
"""
import os
import sys
import cv2
import numpy as np

# Setup Core Engine Imports
sys.path.insert(0, r"E:\image_to_animate\kivy")
from engine.camera.camera import Camera, CameraState
from engine.camera.camera_animator import CameraAnimator
from engine.core.timeline import CameraShot
from engine.animation.easing import get_easing
from engine.video.encoder import VideoEncoder

BRAIN_DIR = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f"
VIDEO_1_PATH = os.path.join(BRAIN_DIR, "dynamic_panel_01.mp4")
VIDEO_2_PATH = os.path.join(BRAIN_DIR, "dynamic_panel_02.mp4")
OUT_MERGED_PATH = os.path.join(BRAIN_DIR, "step1_camera_transition_p1_to_p2.mp4")

print("="*80)
print("TESTING STEP 1 CAMERA TRANSITION: PANEL 1 -> PANEL 2")
print("="*80)

cap1 = cv2.VideoCapture(VIDEO_1_PATH)
fps = cap1.get(cv2.CAP_PROP_FPS) or 30.0
w = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
h = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
total_f1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))

encoder = VideoEncoder(OUT_MERGED_PATH, w, h, fps=int(round(fps)), crf=16)

# Read Video 1, trimming excessive end hold to crisp 18 frames (0.6s)
# Video 1 has 75 frames of outro hold at the end. We keep all drawing + 18 hold frames.
trim_end_f1 = max(100, total_f1 - 55)

print(f"[1/3] Streaming Panel 1 ({trim_end_f1} frames)...")
last_frame_1 = None
for f_idx in range(trim_end_f1):
    ret, frame = cap1.read()
    if not ret: break
    encoder.write_frame(frame)
    last_frame_1 = frame.copy()
cap1.release()

# Read first frame of Video 2
cap2 = cv2.VideoCapture(VIDEO_2_PATH)
ret, first_frame_2 = cap2.read()
total_f2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))

# -----------------------------------------------------------------------------
# 2. GENERATE CANONICAL CAMERA TRANSITION (EASE_IN_OUT_CUBIC)
# -----------------------------------------------------------------------------
TRANSITION_FRAMES = 40  # ~1.33s at 30fps
GUTTER = 160            # Whiteboard margin between panels

print(f"[2/3] Generating Camera Transition ({TRANSITION_FRAMES} frames @ ease_in_out_cubic)...")
easing_fn = get_easing("ease_in_out_cubic")

# Build dual-panel whiteboard panorama
panorama_w = w * 2 + GUTTER
panorama = np.full((h, panorama_w, 3), 255, dtype=np.uint8)
panorama[:, :w] = last_frame_1

# Subtle whiteboard vertical separator
sep_x = w + GUTTER // 2
cv2.line(panorama, (sep_x, int(h * 0.10)), (sep_x, int(h * 0.90)), (225, 230, 228), 2)
panorama[:, w + GUTTER:] = first_frame_2

for i in range(TRANSITION_FRAMES):
    t_norm = i / float(TRANSITION_FRAMES - 1)
    t_eased = easing_fn(t_norm)
    
    # Camera travels from 0 to (w + GUTTER)
    curr_cam_x = int(round(t_eased * (w + GUTTER)))
    viewport = np.ascontiguousarray(panorama[:, curr_cam_x:curr_cam_x + w])
    encoder.write_frame(viewport)

# -----------------------------------------------------------------------------
# 3. STREAM PANEL 2 DRAWING
# -----------------------------------------------------------------------------
print(f"[3/3] Streaming Panel 2 ({total_f2} frames)...")
encoder.write_frame(first_frame_2)
while True:
    ret, frame = cap2.read()
    if not ret: break
    encoder.write_frame(frame)
cap2.release()

encoder.close()
print(f"[SUCCESS] Step 1 Transition Video Finalized: {OUT_MERGED_PATH}")

# -----------------------------------------------------------------------------
# CONTACT SHEET INSPECTION
# -----------------------------------------------------------------------------
cap_res = cv2.VideoCapture(OUT_MERGED_PATH)
tot_res = int(cap_res.get(cv2.CAP_PROP_FRAME_COUNT))
dur_s = tot_res / float(fps)

# Sample around transition point:
# Transition happens at: frame trim_end_f1 to trim_end_f1 + TRANSITION_FRAMES
t_start = trim_end_f1
t_mid = t_start + TRANSITION_FRAMES // 2
t_end = t_start + TRANSITION_FRAMES

indices = [
    t_start - 30,           # Panel 1 near completion
    t_start,                # Panel 1 finished (Hold)
    t_start + 12,           # Transition 30% (Glide)
    t_mid,                  # Transition 50% (Passing separator)
    t_end - 6,              # Transition 85% (Approaching Panel 2)
    t_end + 30              # Panel 2 drawing starts
]

frames = []
for idx in indices:
    cap_res.set(cv2.CAP_PROP_POS_FRAMES, min(idx, tot_res - 1))
    ret, f = cap_res.read()
    if ret: frames.append(f)
cap_res.release()

sheet_dest = os.path.join(BRAIN_DIR, "step1_camera_transition_contact_sheet.png")
if frames:
    fw, fh = 300, 169
    sheet = np.full((fh + 65, len(frames) * (fw + 12) + 12, 3), 245, dtype=np.uint8)
    cv2.rectangle(sheet, (0, 0), (sheet.shape[1], 42), (25, 45, 30), -1)
    cv2.putText(sheet, f"STEP 1: CAMERA TRANSITION P1 -> P2 (ease_in_out_cubic - {dur_s:.1f}s)", 
                (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (50, 255, 120), 1, cv2.LINE_AA)
    
    stage_titles = [
        "1. Panel 1 (Focus)",
        "2. Panel 1 Reveal Hold",
        "3. Glide (Ease-In)",
        "4. Passing Gutter Separator",
        "5. Arriving at Panel 2 (Ease-Out)",
        "6. Panel 2 (Focus Drawing)"
    ]
    for i, fr in enumerate(frames):
        gx = 12 + i * (fw + 12)
        gy = 50
        sm = cv2.resize(fr, (fw, fh), interpolation=cv2.INTER_AREA)
        sheet[gy:gy+fh, gx:gx+fw] = sm
        cv2.rectangle(sheet, (gx, gy), (gx+fw, gy+fh), (140, 180, 160), 1)
        cv2.rectangle(sheet, (gx, gy+fh), (gx+fw, gy+fh+15), (35, 45, 40), -1)
        cv2.putText(sheet, stage_titles[i], (gx+5, gy+fh+12), cv2.FONT_HERSHEY_SIMPLEX, 0.22, (0, 220, 255), 1, cv2.LINE_AA)
        
    cv2.imwrite(sheet_dest, sheet)
    print(f"Contact sheet saved to: {sheet_dest}")

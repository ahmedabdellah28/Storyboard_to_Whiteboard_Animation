"""
Extract high-resolution contact sheet for the complete Panel 1 Masterpiece animation.
"""
import os
import shutil
import cv2
import numpy as np

SRC_VID = r"E:\image_to_animate\experiments\results\step6_drawing_methods\panel_01_masterpiece_animation.mp4"
DEST_DIR = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f"
DEST_VID = os.path.join(DEST_DIR, "panel_01_masterpiece_animation.mp4")
OUT_IMG = os.path.join(DEST_DIR, "panel_01_masterpiece_contact_sheet.png")

# Copy video to brain directory via Python (guaranteed reliable)
try:
    shutil.copy2(SRC_VID, DEST_VID)
    print("Copied video successfully.")
except Exception as e:
    print(f"Copy error: {e}")

cap = cv2.VideoCapture(SRC_VID)
total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# Sample 6 key milestones:
# 1. Title being written (Frame 300)
# 2. Boy character being drawn (Frame 1200)
# 3. Speech bubble cloud loop (Frame 2200)
# 4. Text lines being written steadily (Frame 3200)
# 5. Emoji mascot & heart (Frame 4200)
# 6. Complete pristine artwork finale (Frame 4700)
indices = [350, 1400, 2300, 3400, 4300, total_f - 20]

frames = []
for idx in indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, min(idx, total_f - 1))
    ret, f = cap.read()
    if ret:
        frames.append(f)
cap.release()

if frames:
    fw, fh = 300, 169
    sheet = np.full((fh + 65, len(frames) * (fw + 12) + 12, 3), 245, dtype=np.uint8)
    cv2.rectangle(sheet, (0, 0), (sheet.shape[1], 42), (25, 45, 30), -1)
    cv2.putText(sheet, "COMPLETE PANEL 1 WHITEBOARD MASTERPIECE (STABLE 1.15x FRAMING - ZERO JITTER - 1080p)", 
                (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (50, 255, 120), 1, cv2.LINE_AA)
                
    stage_titles = [
        "1. Title (RTL Medial Skeleton)",
        "2. Boy (Native Outside-In)",
        "3. Speech Bubble Container",
        "4. Steady RTL Text Lines",
        "5. Mascot & Heart Accents",
        "6. Complete 1080p Masterpiece"
    ]
    
    for i, fr in enumerate(frames):
        gx = 12 + i * (fw + 12)
        gy = 50
        sm = cv2.resize(fr, (fw, fh), interpolation=cv2.INTER_AREA)
        sheet[gy:gy+fh, gx:gx+fw] = sm
        cv2.rectangle(sheet, (gx, gy), (gx+fw, gy+fh), (140, 180, 160), 1)
        cv2.rectangle(sheet, (gx, gy+fh), (gx+fw, gy+fh+15), (35, 45, 40), -1)
        cv2.putText(sheet, stage_titles[i], (gx+5, gy+fh+12), cv2.FONT_HERSHEY_SIMPLEX, 0.26, (0, 220, 255), 1, cv2.LINE_AA)
        
    cv2.imwrite(OUT_IMG, sheet)
    print(f"Saved: {OUT_IMG}")

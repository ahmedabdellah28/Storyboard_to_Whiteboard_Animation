"""
Extract contact sheet for the Prototype 8 Medial Skeleton Text Animation
"""
import os
import cv2
import numpy as np

OUTPUT_DIR = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f"
TEXT_VID = os.path.join(OUTPUT_DIR, "prototype8_authentic_text_animation.mp4")
OUT_IMG = os.path.join(OUTPUT_DIR, "prototype8_text_contact_sheet.png")

cap = cv2.VideoCapture(TEXT_VID)
total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
num_frames = 6
indices = np.linspace(20, total_f - 30, num_frames, dtype=int)

frames = []
for idx in indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, f = cap.read()
    if ret:
        frames.append(f)
cap.release()

if frames:
    fw, fh = 280, 158
    sheet = np.full((fh + 60, num_frames * (fw + 10) + 10, 3), 245, dtype=np.uint8)
    cv2.rectangle(sheet, (0, 0), (sheet.shape[1], 40), (20, 35, 45), -1)
    cv2.putText(sheet, "EXACT PROTOTYPE 8: 1-PIXEL MEDIAL SKELETON HANDWRITING (auto_master_video.mp4 METHOD)", 
                (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 220, 255), 1, cv2.LINE_AA)
    
    for i, fr in enumerate(frames):
        gx = 10 + i * (fw + 10)
        gy = 48
        sm = cv2.resize(fr, (fw, fh), interpolation=cv2.INTER_AREA)
        sheet[gy:gy+fh, gx:gx+fw] = sm
        cv2.rectangle(sheet, (gx, gy), (gx+fw, gy+fh), (180, 180, 180), 1)
        
    cv2.imwrite(OUT_IMG, sheet)
    print(f"Saved: {OUT_IMG}")

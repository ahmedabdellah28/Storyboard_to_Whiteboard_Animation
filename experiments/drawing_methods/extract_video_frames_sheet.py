"""
Extract contact sheet frames from the two newly generated professional MP4 videos.
"""
import os
import cv2
import numpy as np

OUTPUT_DIR = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f"
CHAR_VID = os.path.join(OUTPUT_DIR, "professional_character_animation.mp4")
TEXT_VID = os.path.join(OUTPUT_DIR, "professional_text_animation.mp4")

def extract_sheet(vid_path, out_img_path, title_text, num_frames=6):
    cap = cv2.VideoCapture(vid_path)
    total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = np.linspace(5, total_f - 15, num_frames, dtype=int)
    
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, f = cap.read()
        if ret:
            frames.append(f)
    cap.release()
    
    if not frames:
        return
        
    fw, fh = 280, 158
    sheet = np.full((fh + 60, num_frames * (fw + 10) + 10, 3), 245, dtype=np.uint8)
    cv2.rectangle(sheet, (0, 0), (sheet.shape[1], 40), (25, 35, 45), -1)
    cv2.putText(sheet, title_text, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 220, 255), 1, cv2.LINE_AA)
    
    for i, fr in enumerate(frames):
        gx = 10 + i * (fw + 10)
        gy = 48
        sm = cv2.resize(fr, (fw, fh), interpolation=cv2.INTER_AREA)
        sheet[gy:gy+fh, gx:gx+fw] = sm
        cv2.rectangle(sheet, (gx, gy), (gx+fw, gy+fh), (180, 180, 180), 1)
        
    cv2.imwrite(out_img_path, sheet)
    print(f"Saved: {out_img_path}")

extract_sheet(CHAR_VID, os.path.join(OUTPUT_DIR, "professional_character_contact_sheet.png"), 
              "AUTHENTIC PROGRAM ENGINE: OUTSIDE-IN CHARACTER DRAWING WITH ORBITAL LAYERS")

extract_sheet(TEXT_VID, os.path.join(OUTPUT_DIR, "professional_text_contact_sheet.png"), 
              "AUTHENTIC PROGRAM ENGINE: HARMONIOUS RTL FLUID HANDWRITING SYNCHRONIZATION")

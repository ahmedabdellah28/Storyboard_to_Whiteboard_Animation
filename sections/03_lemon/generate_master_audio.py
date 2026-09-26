import os
import sys

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.mix_section_audio import mix_section_audio

vo_path = "sections/03_lemon/voiceover.wav"
out_audio = "sections/03_lemon/master_audio.wav"

sfx_cues = [
    # Row 1
    (0.0,  'marker', 0.06),  # Hero lemon drawing
    (1.6,  'pop',    0.065), # Hybrid citrus & DNA
    (4.5,  'whoosh', 0.06),  # Asia/India map
    (8.2,  'marker', 0.06),  # Dr. James Lind
    (14.5, 'pop',    0.065), # Scurvy clipboard before/after cure
    
    # Row 2
    (24.0, 'marker', 0.065), # Naval scurvy ship
    (28.2, 'pop',    0.06),  # Lemon squeezing ink
    (31.5, 'whoosh', 0.06),  # Red arrow
    (32.5, 'whoosh', 0.065), # Heat reveal writing
    (37.4, 'marker', 0.06),  # Lush lemon tree
    (40.2, 'pop',    0.065), # All-season circular cycle
    
    # Row 3
    (44.0, 'pop',    0.06),  # Glass lemon water & liver check
    (47.5, 'pop',    0.065), # Detox myth with red cross
    (54.5, 'chime',  0.075), # Vitamin C golden burst orb
    (56.8, 'pop',    0.06),  # Citric acid molecule
    (58.5, 'whoosh', 0.06),  # Kidney stones anatomy
    (60.5, 'pop',    0.065), # Stone reduction arrow & broken fragments
]

mix_section_audio(vo_path, sfx_cues, out_audio)
print("Mixed sections/03_lemon/master_audio.wav successfully with 50% marker volume!")

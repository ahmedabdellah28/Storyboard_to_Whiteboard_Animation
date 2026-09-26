import os
import sys

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.mix_section_audio import mix_section_audio

vo_path = "sections/01_apple/voiceover.wav"
out_audio = "sections/01_apple/master_audio.wav"

sfx_cues = [
    # Row 1 (0.0s - 13.5s)
    (0.0,  'marker', 0.06), # Giant apple hero
    (2.2,  'pop',    0.065), # Wild apple after giant apple is done
    (3.2,  'whoosh', 0.06), # Branch
    (4.5,  'pop',    0.06), # Flower
    (6.5,  'pop',    0.065), # Forest blooming tree
    (9.5,  'whoosh', 0.065), # Snowy Caucasus mountains
    (11.2, 'pop',    0.065), # Central Asia map
    
    # Row 2 (13.5s - 25.0s)
    (14.2, 'marker', 0.065), # Roman soldier hero
    (17.5, 'whoosh', 0.06), # Europe map after soldier is done
    (18.2, 'whoosh', 0.065), # Horse cart
    (19.5, 'marker', 0.06), # Farmer planting tree
    (22.0, 'pop',    0.06), # Tree stage 1
    (22.6, 'pop',    0.06), # Tree stage 2
    (23.2, 'pop',    0.065), # Tree stage 3
    (23.8, 'pop',    0.07), # Tree stage 4 mature
    
    # Row 3 (25.0s - 44.0s)
    (25.5, 'pop',    0.06), # Evolution 1 ancient sour
    (27.2, 'pop',    0.065), # Evolution 2 selection arrow
    (29.0, 'pop',    0.07), # Evolution 3 giant honeycrisp
    (35.0, 'whoosh', 0.065), # Hand picking apple
    (40.5, 'pop',    0.06), # Variety 1 red
    (41.2, 'pop',    0.06), # Variety 2 green
    (41.9, 'pop',    0.06), # Variety 3 yellow
    (42.6, 'pop',    0.06), # Variety 4 dark
    (43.3, 'pop',    0.065), # Variety 5 striped
    
    # Row 4 (44.0s - 51.5s)
    (45.0, 'whoosh', 0.06), # Seedling cycle
    (46.2, 'whoosh', 0.065), # Harvest crate
    (47.8, 'chime',  0.075), # Sliced apple & golden juice burst
    (49.3, 'pop',    0.065), # Farmer inspecting quality
    (50.2, 'pop',    0.06), # Checkbox 1
    (50.5, 'pop',    0.06), # Checkbox 2
    (50.8, 'pop',    0.06), # Checkbox 3
    (51.1, 'pop',    0.06), # Checkbox 4
    
    # Row 5 (51.5s - 60.88s)
    (52.0, 'whoosh', 0.065), # Digestive gut
    (52.8, 'pop',    0.065), # Vitamins bubbles
    (53.6, 'pop',    0.07), # Heartbeat pulse
    (54.8, 'whoosh', 0.065), # Wheat fiber
    (55.6, 'pop',    0.065), # Harvest pile
    (56.5, 'whoosh', 0.07)  # Modern refrigerator
]

mix_section_audio(vo_path, sfx_cues, out_audio)

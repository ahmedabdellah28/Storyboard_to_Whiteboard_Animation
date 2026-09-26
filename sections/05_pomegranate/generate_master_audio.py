import os
import sys

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.mix_section_audio import mix_section_audio

vo_path = "sections/05_pomegranate/voiceover.wav"
out_audio = "sections/05_pomegranate/master_audio.wav"

# SFX cues aligned 100% with speech phrases and 45.0s cinematic timing
sfx_cues = [
    # Phrase 01 (0.30s - 0.80s): "الرمان."
    (0.0,  'marker', 0.055), # r1_01_hero_pomegranate inking

    # Phrase 02 (1.70s - 4.95s): "الرمان من أقدم الفواكه المزروعة على وجه الأرض..."
    (1.5,  'pop',    0.060), # r1_02_ancient_ruins_tree

    # Phrase 03 (5.50s - 10.60s): "...في مناطق من إيران وأفغانستان"
    (5.0,  'whoosh', 0.055), # Pan to Zone 1B
    (5.8,  'pop',    0.065), # r1_03_ancient_map_iran_afghanistan
    (7.2,  'pop',    0.060), # r1_04_pomegranate_sprout_growing
    (8.6,  'chime',  0.070), # r1_05_mature_fruitful_tree

    # Phrase 04 (11.55s - 14.90s): "وكان له مكانة كبيرة عند الفرس واليونانيين والرومان."
    (10.8, 'whoosh', 0.060), # Transition to Row 2A
    (11.6, 'marker', 0.060), # r2_01_persian_king
    (13.0, 'pop',    0.065), # r2_02_greek_and_roman_figures

    # Phrase 05 (15.40s - 21.55s): "وارتبط في ثقافات وأديان مختلفة برموز مثل الخصوبة والازدهار والقيامة والوحدة."
    (15.0, 'whoosh', 0.055), # Pan to Zone 2B
    (15.8, 'pop',    0.065), # r2_03_fertility_pregnant_silhouette
    (17.2, 'chime',  0.070), # r2_04_prosperity_tree_sunburst
    (18.6, 'chime',  0.075), # r2_05_resurrection_stairway_heaven
    (20.0, 'pop',    0.065), # r2_06_unity_hands_pomegranate

    # Phrase 06 (22.20s - 28.50s): "وفي بعض التقاليد اليهودية... ثمرة الرمان فيها 613 حبة..."
    (21.8, 'whoosh', 0.060), # Transition to Row 3A
    (22.6, 'marker', 0.060), # r3_01_torah_scroll_star_and_seed_zoom

    # Phrase 07 & 08 (28.85s - 32.95s): "...نفس عدد الوصايا في التوراة، مع إن الرقم نفسه محل نقاش."
    (28.8, 'pop',    0.065), # r3_02_pomegranate_cross_section_seed_zoom

    # Phrase 09 (33.70s - 37.60s): "أما غذائياً، فالرمان غني بمركبات مضادة للأكسدة..."
    (32.8, 'whoosh', 0.055), # Pan to Zone 3B
    (33.8, 'chime',  0.075), # r3_03_antioxidant_shield_molecules

    # Phrase 10 (37.95s - 42.15s): "...ولهذا ارتبط كثيراً بفوائد صحية للقلب والأوعية وغيرها."
    (37.6, 'whoosh', 0.060), # Transition to Row 4A
    (38.4, 'pop',    0.070), # r3_04_cardiovascular_heart_ecg
    (39.5, 'pop',    0.060), # r4_01_pomegranate_juice_glass
    (40.8, 'pop',    0.065), # r4_02_salad_bowl_walnuts

    # Finale (42.0s - 45.0s): Pan to Botanical splendor & tranquil hold
    (42.0, 'whoosh', 0.055), # Pan to Zone 4B
    (42.6, 'marker', 0.065), # r4_03_botanical_blossoms_branch
]

mix_section_audio(vo_path, sfx_cues, out_audio, target_duration_s=47.0)
print("Mixed sections/05_pomegranate/master_audio.wav with 47.0s duration and pristine sync!")

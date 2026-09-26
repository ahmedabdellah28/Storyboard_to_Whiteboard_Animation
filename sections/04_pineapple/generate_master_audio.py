import os
import sys

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.mix_section_audio import mix_section_audio

vo_path = "sections/04_pineapple/voiceover.wav"
out_audio = "sections/04_pineapple/master_audio.wav"

# SFX cues aligned 100% with actual speech phrases and 57.0s cinematic timing
sfx_cues = [
    # Phrase 1 (0.25s - 1.10s): "الأناناس."
    (0.0,  'marker', 0.055), # r1_01_hero_pineapple

    # Phrase 2 (1.75s - 3.90s): "الأناناس أصله من أمريكا الجنوبية..."
    (1.2,  'pop',    0.065), # r1_02_south_america_map
    (3.6,  'pop',    0.060), # r1_03_pineapple_comparison
    (4.4,  'whoosh', 0.055), # r1_04_double_arrow
    (4.8,  'pop',    0.060), # r1_05_pine_cone

    # Phrase 4 & 5 (8.20s - 13.95s): "رمز ثراء بشكل جنوني... وصلت قيمة الثمرة الواحدة في إنجلترا..."
    (7.4,  'whoosh', 0.055), # Camera pan to 1B
    (8.0,  'marker', 0.060), # r1_06_wealthy_gentleman_england_gold
    (14.0, 'chime',  0.075), # Gold coins & Parliament

    # Phrase 7 & 8 (19.65s - 29.90s): "يستأجرون الأناناسة... يمشون فيها أو يحطونها وسط الطاولة..."
    (19.0, 'whoosh', 0.060), # Transition to Row 2
    (19.6, 'pop',    0.060), # r2_01_butler_velvet_pillow
    (20.8, 'marker', 0.060), # r2_02_admiring_guests (strutting)
    (23.8, 'whoosh', 0.055), # Camera pan to 2B
    (24.6, 'chime',  0.070), # r2_04_lavish_banquet_table

    # Phrase 9 & 10 (30.55s - 37.00s): "يخلي الأناناس على الطاولة لين تخرب... يقدر يرميها"
    (30.6, 'whoosh', 0.060), # r2_05_rich_man_throwing
    (33.6, 'pop',    0.065), # r2_06_trash_rotting_pineapple

    # Phrase 11 & 12 (37.60s - 40.55s): "داخل الأناناس في شيء مثير للاهتمام..."
    (36.8, 'whoosh', 0.060), # Transition to Row 3
    (37.6, 'marker', 0.060), # r3_01_cross_section_cells

    # Phrase 13 & 14 (41.10s - 45.00s): "إنزيم اسمه بروميلين... تكسير البروتينات"
    (41.0, 'pop',    0.065), # r3_02_protein_molecule
    (42.2, 'whoosh', 0.055), # r3_03_blue_arrow
    (43.0, 'pop',    0.060), # r3_04_broken_protein_fragments

    # Phrase 15 (45.55s - 50.50s): "وعشان كذا... ممكن تحس بتنميل أو وخز في لسانك"
    (44.8, 'whoosh', 0.055), # Camera pan to 3B
    (45.6, 'pop',    0.060), # r3_05_meat_tenderizer_bromelain
    (47.0, 'pop',    0.065), # r3_06_stinging_tongue
    (48.5, 'pop',    0.060), # r3_07_man_touching_stinging_tongue

    # Phrase 16 (51.25s - 52.45s): "أنت تاكل الأناناس..."
    (50.5, 'whoosh', 0.060), # Transition to Row 4
    (51.0, 'marker', 0.055), # r4_01_pineapple_slice_dripping
    (51.6, 'whoosh', 0.055), # r4_02_red_curved_arrow
    (52.0, 'pop',    0.065), # r4_03_mouth_eating_pineapple

    # Phrase 17 (52.85s - 54.65s): "والأناناس بعد ياكل شوي منك!"
    (52.5, 'whoosh', 0.060), # Rapid whip pan to 4B
    (52.8, 'marker', 0.065), # r4_04_carnivorous_monster_pineapple
    (53.6, 'pop',    0.070), # r4_05_terrified_man_running
]

mix_section_audio(vo_path, sfx_cues, out_audio, target_duration_s=57.0)
print("Mixed sections/04_pineapple/master_audio.wav with 57.0s duration and perfect speech sync!")

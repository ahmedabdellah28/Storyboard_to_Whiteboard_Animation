import os
import sys

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.mix_section_audio import mix_section_audio

vo_path = "sections/06_mango/voiceover.wav"
out_audio = "sections/06_mango/master_audio.wav"

sfx_cues = [
    # p1 (0.0s - 1.0s): "المانجو."
    (0.0,  'marker', 0.055), # r1_01_hero_mango inking

    # p2 (1.0s - 7.0s): "في جنوب آسيا يسمونها ملكة الفواكه..."
    (1.2,  'chime',  0.070), # r1_02_crowned_king_mango
    (3.6,  'pop',    0.065), # r1_03_indian_man_taj_mahal

    # p3 (7.0s - 13.5s): "أصلها يرجع إلى مناطق من الهند وميانمار وزراعتها تمتد لآلاف السنين."
    (7.0,  'whoosh', 0.055), # Pan to Zone 1B
    (7.8,  'pop',    0.065), # r1_04_ancient_map_india_myanmar

    # p4 (13.5s - 18.0s): "ودخلت بقوة في التاريخ والثقافة والديانات الآسيوية."
    (13.6, 'chime',  0.070), # r1_05_buddha_temple_mango_tree

    # p5 (18.0s - 25.5s): "وفي الهند تحديدا عندك مئات الأنواع من المانجو..."
    (17.6, 'whoosh', 0.060), # Transition to Row 2A
    (18.4, 'marker', 0.060), # r2_01_ancient_scroll_manuscript
    (20.5, 'pop',    0.070), # r2_02_mango_varieties_grid

    # p6 (25.5s - 33.5s): "في أنواع قوامها كريمي وأنواع فيها ألياف أكثر وأنواع طعمها يوصل للحلاوة الشديدة."
    (25.0, 'whoosh', 0.055), # Pan to Zone 2B
    (25.8, 'pop',    0.065), # r2_03_creamy_texture_mango
    (27.8, 'pop',    0.065), # r2_04_fibrous_texture_mango
    (30.0, 'chime',  0.075), # r2_05_super_sweet_mango_sugar

    # p7 (33.5s - 40.0s): "والتجار البرتغاليون كان لهم دور مهم في نشر المانجو..."
    (33.0, 'whoosh', 0.060), # Transition to Row 3A
    (33.8, 'marker', 0.060), # r3_01_portuguese_explorer_caravel
    (36.0, 'whoosh', 0.065), # r3_02_world_map_trade_routes

    # p8 (40.0s - 45.0s): "حتى وصلت إلى أفريقيا والبرازيل ومناطق استوائية كثيرة."
    (39.5, 'whoosh', 0.055), # Pan to Zone 3B
    (40.3, 'pop',    0.065), # r3_03_tropical_harbor_mango_crates
    (42.0, 'chime',  0.070), # r3_04_globe_mango_distribution

    # p9 (45.0s - 49.5s) & p10 (49.5s - 55.0s):
    # Transition to Row 4A
    (44.5, 'whoosh', 0.060), # Transition to Row 4A
    (45.3, 'pop',    0.065), # r4_02_mango_blossoms_inflorescence
    (46.8, 'chime',  0.075), # r4_01_vitamin_c_shield_molecules

    # Pan to Zone 4B (Finale)
    (49.0, 'whoosh', 0.055), # Pan to Zone 4B
    (49.8, 'pop',    0.065), # r4_03_cross_section_mango_halves
    (50.8, 'pop',    0.065), # r4_04_three_mangoes_trio
    (52.0, 'marker', 0.070), # r4_05_mango_smoothie_dessert_bowl
]

mix_section_audio(vo_path, sfx_cues, out_audio, target_duration_s=57.0)
print("Mixed sections/06_mango/master_audio.wav with 57.0s duration and pristine sync!")

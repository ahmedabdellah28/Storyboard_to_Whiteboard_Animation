import os
import sys
import json

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.dynamic_section_engine import DynamicSectionEngine

sec_dir = os.path.join(ROOT_DIR, "sections/10_fig")
engine = DynamicSectionEngine(sec_dir)

layout_spec = {
    1: {
        'zone_A': {
            'x_start': 200.0,
            'elements': [
                ("r1_01_fig_hero_fresh_cut", 140.0),
                ("r1_02_ancient_prehistoric_gatherers", 140.0),
                ("r1_03_jordan_valley_neolithic_village", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r1_04_ancient_stone_carvings_fig", 140.0),
                ("r1_05_fig_older_than_grains_comparison", 0.0),
            ]
        }
    },
    2: {
        'zone_A': {
            'x_start': 200.0,
            'elements': [
                ("r2_01_fig_magnified_internal_flowers", 140.0),
                ("r2_02_botanical_syconium_florets_loupe", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r2_03_crunchy_seeds_florets_detail", 120.0),
                ("r2_04_trio_fresh_figs_leaf", 120.0),
                ("r2_05_dried_figs_platter", 0.0),
            ]
        }
    },
    3: {
        'zone_A': {
            'x_start': 200.0,
            'elements': [
                ("r3_01_fig_ostiole_wasp_entering", 140.0),
                ("r3_02_fig_wasp_illustrated", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r3_03_wasp_inside_fig_interior", 130.0),
                ("r3_04_fig_enzymes_breakdown_diagram", 130.0),
                ("r3_05_commercial_fig_no_wasp_sign", 0.0),
            ]
        }
    },
    4: {
        'zone_A': {
            'x_start': 200.0,
            'elements': [
                ("r4_01_fig_varieties_lineup", 140.0),
                ("r4_02_fig_sapling_soil", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r4_03_mature_fruiting_fig_tree", 140.0),
                ("r4_04_fig_branch_ripe_unripe", 0.0),
            ]
        }
    }
}

layout_file = engine.calculate_layout(layout_spec, base_scale=2.5)
print(f"Layout computed successfully: {layout_file}")

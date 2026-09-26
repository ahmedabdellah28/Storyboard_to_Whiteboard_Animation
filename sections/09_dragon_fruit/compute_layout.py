import os
import sys
import json

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.dynamic_section_engine import DynamicSectionEngine

sec_dir = os.path.join(ROOT_DIR, "sections/09_dragon_fruit")
engine = DynamicSectionEngine(sec_dir)

layout_spec = {
    1: {
        'zone_A': {
            'x_start': 200.0,
            'elements': [
                ("r1_01_dragon_fruit_white_flesh_hero", 160.0),
                ("r1_02_dragon_fruit_cactus_tree", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r1_03_blooming_night_flower_stem", 160.0),
                ("r1_04_dragon_fruit_red_flesh_hero", 0.0),
            ]
        }
    },
    2: {
        'zone_A': {
            'x_start': 400.0,
            'elements': [
                ("r2_01_world_migration_map", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r2_02_cactus_branch_harvest", 0.0),
            ]
        }
    },
    3: {
        'zone_A': {
            'x_start': 200.0,
            'elements': [
                ("r3_01_vietnam_plantation_landscape", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r3_02_three_varieties_lineup", 0.0),
            ]
        }
    },
    4: {
        'zone_A': {
            'x_start': 200.0,
            'elements': [
                ("r4_01_nutritional_benefits_composition", 140.0),
                ("r4_05_dragon_fruit_slices_composition", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r4_02_pitaya_smoothie_bowl", 120.0),
                ("r4_03_smoothie_tall_glass_straw", 120.0),
                ("r4_04_cubed_dragon_fruit_plate", 0.0),
            ]
        }
    }
}

layout_file = engine.calculate_layout(layout_spec, base_scale=2.3)
print(f"Layout computed successfully: {layout_file}")

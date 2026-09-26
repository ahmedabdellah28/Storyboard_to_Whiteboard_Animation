import os
import sys
import json

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.dynamic_section_engine import DynamicSectionEngine

sec_dir = os.path.join(ROOT_DIR, "sections/11_jabuticaba")
engine = DynamicSectionEngine(sec_dir)

layout_spec = {
    1: {
        'zone_A': {
            'x_start': 200.0,
            'elements': [
                ("r1_01_jabuticaba_hero_cluster", 140.0),
                ("r1_02_jabuticaba_tree_full", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r1_03_trunk_covered_fruits", 120.0),
                ("r1_04_trunk_berries_macro", 120.0),
                ("r1_05_trunk_white_flowers_macro", 0.0),
            ]
        }
    },
    2: {
        'zone_A': {
            'x_start': 200.0,
            'elements': [
                ("r2_01_jabuticaba_trio_cut", 140.0),
                ("r2_02_traditional_grapes_comparison", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r2_03_popping_juice_burst_sequence", 120.0),
                ("r2_04_slices_cross_sections", 120.0),
                ("r2_05_hand_holding_single_berry", 0.0),
            ]
        }
    },
    3: {
        'zone_A': {
            'x_start': 200.0,
            'elements': [
                ("r3_01_branch_ripening_gradient", 140.0),
                ("r3_02_spoilage_sequence_decay", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r3_03_calendar_rapid_spoilage_3days", 120.0),
                ("r3_04_export_crates_airplane_prohibited", 120.0),
                ("r3_05_brazil_map_native_origin", 0.0),
            ]
        }
    },
    4: {
        'zone_A': {
            'x_start': 200.0,
            'elements': [
                ("r4_01_growth_sprout_stage", 90.0),
                ("r4_02_growth_sapling_stage", 90.0),
                ("r4_03_growth_bushy_juvenile_stage", 90.0),
                ("r4_04_growth_mature_tree_stage", 0.0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ("r4_05_growth_fruiting_tree_stage", 130.0),
                ("r4_06_basket_harvest_platter", 130.0),
                ("r4_07_fresh_juice_tall_glass", 0.0),
            ]
        }
    }
}

layout_file = engine.calculate_layout(layout_spec, base_scale=2.5)
print(f"Layout computed successfully: {layout_file}")

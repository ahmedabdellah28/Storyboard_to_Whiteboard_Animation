import os
import shutil
import glob

workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
print(f"Cleaning workspace at: {workspace_root}")

# 1. Scratch python scripts to remove from root
root_scripts_to_remove = [
    "analyze_exclamation_marks.py",
    "benchmark_user_run.py",
    "debug_padlock_storyboard_order.py",
    "debug_panel_4_red_marks.py",
    "inspect_mddialog_dismiss.py",
    "inspect_source_storyboard_panels.py",
    "scratch_test.py",
    "scratch_test_pipeline.py",
    "test_advanced_english_settings_dialog.py",
    "test_card_lifecycle_and_manual_box.py",
    "test_character_separation_and_reaction_precision.py",
    "test_clean_settings_dialog.py",
    "test_complete_pipeline.py",
    "test_drawing_direction_modes.py",
    "test_embedded_settings_buttons.py",
    "test_end_to_end.py",
    "test_engine_all.py",
    "test_entity_coverage.py",
    "test_entity_ordering_rules.py",
    "test_fix_extraction.py",
    "test_full_app_integration.py",
    "test_full_settings_parse_and_save.py",
    "test_grouping_reaction_marks.py",
    "test_horizontal_dynamic.py",
    "test_investigate.py",
    "test_manual_annotation.py",
    "test_master_storyboard.py",
    "test_new_studio_architecture.py",
    "test_orbital_bug.py",
    "test_panel_debug.py",
    "test_panel_entities_detail.py",
    "test_panel_entity_spatial_accuracy.py",
    "test_reaction_ordering.py",
    "test_render_panel_with_reaction.py",
    "test_render_user_shock_comic.py",
    "test_settings_buttons.py",
    "test_settings_dialog_click.py",
    "test_single_element_animation_and_preview.py",
    "test_smart_grouping.py",
    "test_storyboard_camera.py",
    "test_storyboard_landscape.py",
    "test_strict_card_to_video_alignment.py",
    "test_strict_user_order_rendering.py",
    "test_ui_instantiation.py",
    "test_zaid.py",
    "verify_orbital_fix.py"
]

for s in root_scripts_to_remove:
    p = os.path.join(workspace_root, s)
    if os.path.exists(p):
        try:
            os.remove(p)
            print(f"Removed script: {s}")
        except Exception as e:
            print(f"Error removing {s}: {e}")

# 2. Test images in root to remove
root_images_to_remove = [
    "Man_interacting_with_magical_obj…_202608291251.jpeg",
    "Man_looking_at_floating_padlock_202608281822.jpeg",
    "Man_unlocking_glowing_padlock_st…_202608291709.jpeg",
    "Storyboard_showing_Zaid_building…_202608281849.jpeg",
    "storyboard_olive_oil.jpg",
    "storyboard_potion.jpg"
]
for img_name in root_images_to_remove:
    p = os.path.join(workspace_root, img_name)
    if os.path.exists(p):
        try:
            os.remove(p)
            print(f"Removed root test image: {img_name}")
        except Exception as e:
            print(f"Error removing {img_name}: {e}")

# 3. Scratch directories to remove
dirs_to_remove = [
    "output_test_run",
    "output_benchmark",
    "output_engine_test",
    "save_videos",
    "debug",
    "bkp_recipes",
    os.path.join("tools", "video_snapshots")
]

for d in dirs_to_remove:
    p = os.path.join(workspace_root, d)
    if os.path.exists(p):
        try:
            shutil.rmtree(p, ignore_errors=True)
            print(f"Removed directory: {d}")
        except Exception as e:
            print(f"Error removing directory {d}: {e}")

# 4. Clean __pycache__ folders
for root, dirs, files in os.walk(workspace_root):
    for d in dirs:
        if d == "__pycache__":
            p = os.path.join(root, d)
            try:
                shutil.rmtree(p, ignore_errors=True)
                print(f"Removed pycache: {os.path.relpath(p, workspace_root)}")
            except Exception:
                pass

print("✓ Workspace cleaned successfully!")

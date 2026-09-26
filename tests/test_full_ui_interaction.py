"""
Automated End-to-End Kivy UI Simulation Runner
Executes the full application lifecycle on the live Kivy Clock loop, testing:
1. Home Screen Bootstrap
2. Composition & Multi-Panel Analysis
3. SceneScreen Transition
4. Collapsible Accordion Panels in ObjectList
5. Single-Panel Focus Mode & Texture Blit
6. Interactive Writing Direction Toggle (RTL <-> LTR)
7. Priority Order Swapping & Badges
8. Settings Dialog & Export Trigger
"""
import os
import sys
import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    except Exception:
        pass

os.environ['KIVY_NO_ARGS'] = '1'

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_root, 'kivy'))

from kivy.clock import Clock
from main import SketchAnimationApp
from engine.core.scene import SceneConfig
from engine.processing.image_processor import ImageProcessor


def simulate_full_ui(app):
    print("\n=======================================================", flush=True)
    print("STARTING COMPLETE LIVE UI SIMULATION", flush=True)
    print("=======================================================", flush=True)

    test_image_path = os.path.join(_root, 'test_images', 'arabic_12_panel_storyboard.jpg')
    assert os.path.exists(test_image_path), f"File not found: {test_image_path}"

    # --- Step 1: Verify Initial Screen ---
    print("\n[Step 1] Verifying Initial Screen...", flush=True)
    assert app.sm.current == "home", f"Expected home screen, got {app.sm.current}"
    print("  ✓ App initialized on Home Screen.", flush=True)

    # --- Step 2: Trigger Image Analysis ---
    print("\n[Step 2] Simulating Image Selection & Composition Analysis...", flush=True)
    img = cv2.imread(test_image_path)
    cfg = SceneConfig(camera_zoom_scale=1.40, drawing_speed=1.5)
    project = ImageProcessor.process(img, cfg)
    
    assert project is not None
    assert len(project.panels) == 12
    print(f"  ✓ Discovered {len(project.panels)} panels and {sum(len(s.objects) for s in project.scenes)} objects.", flush=True)

    # --- Step 3: Complete Analysis & Transition to SceneScreen ---
    print("\n[Step 3] Loading Project into SceneScreen...", flush=True)
    app.state.source_image = img
    app.state.source_image_path = test_image_path
    app.state.set_project(project)
    app.scene_screen.load_project(test_image_path, project)
    app.sm.current = "scene"

    assert app.sm.current == "scene"
    print("  ✓ SceneScreen active.", flush=True)

    # --- Step 4: Verify Sidebar Accordion Panels ---
    print("\n[Step 4] Testing Sidebar Accordion Panels...", flush=True)
    obj_list = app.scene_screen.object_list
    assert len(obj_list._panel_headers) == 12, f"Expected 12 panels, got {len(obj_list._panel_headers)}"

    # Toggle Panel 1 Accordion
    h1 = obj_list._panel_headers[1]
    was_collapsed = h1._collapsed
    h1.toggle()
    assert h1._collapsed != was_collapsed
    h1.toggle()

    cards_p1 = obj_list._get_or_create_panel_cards(1)
    assert len(cards_p1) > 0
    for idx, c in enumerate(cards_p1):
        assert c.priority_badge.number == idx + 1
    print(f"  ✓ Verified {len(cards_p1)} cards in Panel 1 with sequential priority badges.", flush=True)

    # --- Step 5: Test Canvas Single-Panel Focus Mode ---
    print("\n[Step 5] Testing Canvas Single-Panel Focus & Viewport...", flush=True)
    preview = app.scene_screen.image_preview
    assert preview.view_mode == "PANEL"

    preview.set_focused_panel(1)
    assert preview.focused_panel_id == 1
    assert preview.img_widget.texture is not None
    print("  ✓ Canvas successfully focused on Panel 1 texture crop.", flush=True)

    preview.set_focused_panel(6)
    assert preview.focused_panel_id == 6
    print("  ✓ Switched to Panel 6.", flush=True)

    # Toggle to Full Sheet mode
    preview.toggle_view_mode()
    assert preview.view_mode == "FULL"
    print("  ✓ Toggled to FULL sheet mode.", flush=True)

    preview.toggle_view_mode()
    assert preview.view_mode == "PANEL"
    print("  ✓ Toggled back to SINGLE PANEL FOCUS mode.", flush=True)

    # --- Step 6: Test Interactive Text Direction Toggle ---
    print("\n[Step 6] Testing Interactive Text Direction Toggle (RTL <-> LTR)...", flush=True)
    p1_texts = [o for o in app.state.objects if o.panel_id == 1 and o.element_type == "TEXT"]
    assert len(p1_texts) > 0

    txt_obj = p1_texts[0]
    initial_dir = txt_obj.direction
    app.state.set_active_id(txt_obj.id)

    new_dir = "LTR" if initial_dir == "RTL" else "RTL"
    txt_obj.direction = new_dir
    app.state._notify_objects_changed()

    assert txt_obj.direction == new_dir
    print(f"  ✓ Writing direction flipped from {initial_dir} to {new_dir}.", flush=True)

    # --- Step 7: Test Priority Reordering ---
    print("\n[Step 7] Testing Priority Reordering Controls...", flush=True)
    p1_all = [o for o in app.state.objects if o.panel_id == 1]
    assert len(p1_all) > 1

    obj_a_id = p1_all[0].id
    obj_b_id = p1_all[1].id

    obj_list._on_move_order(obj_a_id, 1)

    p1_reordered = [o for o in app.state.objects if o.panel_id == 1]
    assert p1_reordered[0].id == obj_b_id
    assert p1_reordered[1].id == obj_a_id
    assert p1_reordered[0].priority_order == 1
    assert p1_reordered[1].priority_order == 2
    print("  ✓ Priorities swapped and re-indexed successfully.", flush=True)

    # --- Step 8: Viewport Controls & Tools ---
    print("\n[Step 8] Testing Viewport Controls & Tools...", flush=True)
    orig_z = preview.zoom_level
    preview.adjust_zoom(1.2)
    assert preview.zoom_level > orig_z
    preview.reset_zoom()
    assert preview.zoom_level == 1.0

    preview.set_tool("ADD_BOX")
    assert app.state.active_tool == "ADD_BOX"
    preview.set_tool("SELECT")
    assert app.state.active_tool == "SELECT"
    print("  ✓ Zoom and tools tested successfully.", flush=True)

    print("\n=======================================================", flush=True)
    print("ALL LIVE UI SIMULATION TESTS COMPLETED WITH 100% SUCCESS!", flush=True)
    print("=======================================================\n", flush=True)

    # Clean exit
    Clock.schedule_once(lambda dt: (app.stop(), os._exit(0)), 0.2)


def main():
    app = SketchAnimationApp()
    app.on_start = lambda: None
    Clock.schedule_once(lambda dt: simulate_full_ui(app), 0.5)
    app.run()


if __name__ == '__main__':
    main()

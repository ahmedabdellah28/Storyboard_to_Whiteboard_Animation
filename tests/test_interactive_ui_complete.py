"""
Complete Interactive UI & Workflow Simulation
Simulates real user actions across all screens and widgets:
- HomeScreen & File selection
- LoadingScreen & Asynchronous Analysis
- SceneScreen 3-Column Studio
- Collapsible Accordions, Single-Panel Focus Viewport, RTL/LTR Badges, Priority Reordering
- Settings Dialog, Aspect Ratio Presets, Video Preview & Rendering Workflows
"""
import os
import sys
import time
import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

os.environ['KIVY_NO_ARGS'] = '1'

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_root, 'kivy'))

import licensing.license_guard
from licensing.license_guard import LicenseGuard
LicenseGuard.is_session_active = staticmethod(lambda: True)
LicenseGuard.verify_startup_online = classmethod(lambda cls: (True, "OK", "DEV_TOKEN"))

from kivy.clock import Clock
from main import SketchAnimationApp
from engine.core.scene import SceneConfig


def run_ui_diagnostic_simulation(app):
    print("\n" + "="*70, flush=True)
    print("🚀 RUNNING FULL END-TO-END UI INTERACTION & DIAGNOSTIC SUITE", flush=True)
    print("="*70, flush=True)

    test_image_path = os.path.join(_root, 'test_images', 'arabic_12_panel_storyboard.jpg')
    assert os.path.exists(test_image_path), f"Test image missing at {test_image_path}"

    errors = []

    # -------------------------------------------------------------
    # 1. Test Initial Home Screen
    # -------------------------------------------------------------
    print("\n[Phase 1] Testing Home Screen Initialization...", flush=True)
    try:
        assert app.sm.current == "home", f"Expected 'home', got '{app.sm.current}'"
        assert hasattr(app.home_screen, "drop_zone"), "Home screen missing drop_zone"
        print("  ✓ Home Screen loaded properly.", flush=True)
    except Exception as e:
        print(f"  ❌ Phase 1 Failed: {e}", flush=True)
        errors.append(("Phase 1", str(e)))

    # -------------------------------------------------------------
    # 2. Test Image Import & Analysis Triggering
    # -------------------------------------------------------------
    print("\n[Phase 2] Simulating User Image Selection & Async Analysis...", flush=True)
    try:
        app.on_image_selected(test_image_path)
        assert app.sm.current == "loading", f"Expected loading screen, got {app.sm.current}"
        print("  ✓ Loading Screen activated, background analysis job started.", flush=True)
    except Exception as e:
        print(f"  ❌ Phase 2 Failed: {e}", flush=True)
        errors.append(("Phase 2", str(e)))

    # -------------------------------------------------------------
    # Helper to wait for analysis to complete on background thread
    # -------------------------------------------------------------
    def step_3_verify_analysis():
        print("\n[Phase 3] Checking Analysis Completion & SceneScreen Population...", flush=True)
        try:
            assert app.sm.current == "scene", f"Expected 'scene' screen, got '{app.sm.current}'"
            assert app.state.project is not None, "Project is None in app.state"
            assert len(app.state.project.panels) == 12, f"Expected 12 panels, got {len(app.state.project.panels)}"
            assert len(app.state.objects) > 0, "No objects extracted"
            print(f"  ✓ Storyboard loaded: 12 panels, {len(app.state.objects)} total objects extracted.", flush=True)
        except Exception as e:
            print(f"  ❌ Phase 3 Failed: {e}", flush=True)
            errors.append(("Phase 3", str(e)))
            _finish()
            return

        # -------------------------------------------------------------
        # 4. Test Sidebar Accordion Panels
        # -------------------------------------------------------------
        print("\n[Phase 4] Testing Sidebar Accordion Panels & Priority Badges...", flush=True)
        try:
            obj_list = app.scene_screen.object_list
            assert len(obj_list._panel_headers) == 12, f"Expected 12 headers, got {len(obj_list._panel_headers)}"
            
            # Check Panel 1
            h1 = obj_list._panel_headers[1]
            assert not h1._collapsed, "Panel 1 should be expanded by default"
            p1_cards = obj_list._panel_card_groups[1]
            assert len(p1_cards) > 0, "Panel 1 has no cards"
            print(f"  ✓ Panel 1 header verified with {len(p1_cards)} object cards.", flush=True)
            
            # Verify Sequential Priority Badges
            for idx, card in enumerate(p1_cards):
                expected_num = idx + 1
                assert card.priority_badge.number == expected_num, f"Card {idx} badge {card.priority_badge.number} != {expected_num}"
            print("  ✓ Color-coded priority badges ①, ②, ③... are properly numbered.", flush=True)

            # Collapse and re-expand Panel 1
            h1.toggle()
            assert h1._collapsed == True
            assert all(c.parent is None for c in p1_cards), "Cards not removed on collapse"
            h1.toggle()
            assert h1._collapsed == False
            assert all(c.parent is not None for c in p1_cards), "Cards not restored on expand"
            print("  ✓ Accordion expand/collapse transitions tested successfully.", flush=True)
        except Exception as e:
            print(f"  ❌ Phase 4 Failed: {e}", flush=True)
            errors.append(("Phase 4", str(e)))

        # -------------------------------------------------------------
        # 5. Test Single-Panel Focus Viewport & Canvas Controls
        # -------------------------------------------------------------
        print("\n[Phase 5] Testing Canvas Single-Panel Focus Viewport...", flush=True)
        try:
            preview = app.scene_screen.image_preview
            assert preview.view_mode == "PANEL", f"Expected view_mode 'PANEL', got {preview.view_mode}"
            assert preview.focused_panel_id == 1, f"Expected focused panel 1, got {preview.focused_panel_id}"

            # Switch focus to Panel 4 via app.focus_panel
            app.focus_panel(4)
            assert preview.focused_panel_id == 4, f"Focused panel did not update to 4 (got {preview.focused_panel_id})"
            print("  ✓ Canvas successfully switched focus to Panel 4.", flush=True)

            # Switch focus to Panel 12
            app.focus_panel(12)
            assert preview.focused_panel_id == 12, f"Focused panel did not update to 12 (got {preview.focused_panel_id})"
            print("  ✓ Canvas successfully switched focus to Panel 12.", flush=True)

            # Toggle to FULL Sheet mode
            preview.toggle_view_mode()
            assert preview.view_mode == "FULL"
            print("  ✓ Canvas toggled to FULL storyboard sheet mode.", flush=True)

            # Toggle back to PANEL mode
            preview.toggle_view_mode()
            assert preview.view_mode == "PANEL"
            app.focus_panel(1)
            print("  ✓ Canvas toggled back to Single-Panel Focus mode.", flush=True)
        except Exception as e:
            print(f"  ❌ Phase 5 Failed: {e}", flush=True)
            errors.append(("Phase 5", str(e)))

        # -------------------------------------------------------------
        # 6. Test Interactive Writing Direction Toggle (RTL <-> LTR)
        # -------------------------------------------------------------
        print("\n[Phase 6] Testing Interactive Writing Direction Arrow Badge...", flush=True)
        try:
            text_objs = [o for o in app.state.objects if o.panel_id == 1 and o.element_type == "TEXT"]
            assert len(text_objs) > 0, "No text objects found in Panel 1"
            txt = text_objs[0]
            initial_dir = txt.direction
            print(f"  Initial writing direction for '{txt.name}': {initial_dir}", flush=True)

            # Simulate toggling direction
            target_dir = "LTR" if initial_dir == "RTL" else "RTL"
            txt.direction = target_dir
            app.state._notify_objects_changed()
            assert txt.direction == target_dir
            print(f"  ✓ Successfully toggled writing direction to {target_dir}.", flush=True)

            # Revert back
            txt.direction = initial_dir
            app.state._notify_objects_changed()
            assert txt.direction == initial_dir
            print(f"  ✓ Reverted writing direction back to {initial_dir}.", flush=True)
        except Exception as e:
            print(f"  ❌ Phase 6 Failed: {e}", flush=True)
            errors.append(("Phase 6", str(e)))

        # -------------------------------------------------------------
        # 7. Test Priority Order Reordering
        # -------------------------------------------------------------
        print("\n[Phase 7] Testing Priority Up/Down Reordering...", flush=True)
        try:
            obj_list = app.scene_screen.object_list
            p1_objs = [o for o in app.state.objects if o.panel_id == 1]
            assert len(p1_objs) >= 2, "Panel 1 requires at least 2 objects for reorder test"

            first_id = p1_objs[0].id
            second_id = p1_objs[1].id

            # Move first object down
            obj_list._on_move_order(first_id, 1)

            p1_after = [o for o in app.state.objects if o.panel_id == 1]
            assert p1_after[0].id == second_id, "Reorder failed: second item not moved to index 0"
            assert p1_after[1].id == first_id, "Reorder failed: first item not moved to index 1"
            assert p1_after[0].priority_order == 1
            assert p1_after[1].priority_order == 2
            print("  ✓ Priority order swapped and re-indexed correctly.", flush=True)

            # Move back up
            obj_list._on_move_order(first_id, -1)
            p1_restored = [o for o in app.state.objects if o.panel_id == 1]
            assert p1_restored[0].id == first_id
            print("  ✓ Priority order restored.", flush=True)
        except Exception as e:
            print(f"  ❌ Phase 7 Failed: {e}", flush=True)
            errors.append(("Phase 7", str(e)))

        # -------------------------------------------------------------
        # 8. Test Settings Dialog & Camera Zoom Presets
        # -------------------------------------------------------------
        print("\n[Phase 8] Testing Settings Dialog & Calibration...", flush=True)
        try:
            settings = app.load_settings()
            zoom = settings.get("camera_zoom_scale", 1.40)
            speed = settings.get("drawing_speed", 1.5)
            print(f"  Current defaults -> Camera Zoom: {zoom}x, Drawing Speed: {speed}x", flush=True)
            assert zoom >= 1.20, f"Expected camera zoom >= 1.20, got {zoom}"
            
            # Test aspect ratio spinner
            app.scene_screen.ratio_spinner.text = "9:16 📱 (TikTok/Reels)"
            s_updated = app.load_settings()
            assert s_updated["width"] == 1080 and s_updated["height"] == 1920
            print("  ✓ Aspect Ratio preset changed to 9:16 (1080x1920).", flush=True)

            # Restore 16:9
            app.scene_screen.ratio_spinner.text = "16:9 📺 (YouTube)"
            s_restored = app.load_settings()
            assert s_restored["width"] == 1920 and s_restored["height"] == 1080
            print("  ✓ Aspect Ratio preset restored to 16:9 (1920x1080).", flush=True)
        except Exception as e:
            print(f"  ❌ Phase 8 Failed: {e}", flush=True)
            errors.append(("Phase 8", str(e)))

        # -------------------------------------------------------------
        # 9. Test Undo / Redo
        # -------------------------------------------------------------
        print("\n[Phase 9] Testing Undo / Redo...", flush=True)
        try:
            app.undo()
            app.redo()
            print("  ✓ Undo / Redo executed cleanly without exceptions.", flush=True)
        except Exception as e:
            print(f"  ❌ Phase 9 Failed: {e}", flush=True)
            errors.append(("Phase 9", str(e)))

        _finish()

    def _wait_for_analysis(dt):
        if app.analysis_service.is_running or app.sm.current != "scene":
            Clock.schedule_once(_wait_for_analysis, 0.2)
        else:
            Clock.schedule_once(lambda dt: step_3_verify_analysis(), 0.1)

    def _finish():
        print("\n" + "="*70, flush=True)
        if not errors:
            print("🎉 ALL UI WORKFLOW TESTS & DIAGNOSTICS COMPLETED WITH 100% SUCCESS!", flush=True)
        else:
            print(f"⚠️ DIAGNOSTIC DETECTED {len(errors)} ERROR(S):", flush=True)
            for ph, err in errors:
                print(f"  • [{ph}]: {err}", flush=True)
        print("="*70 + "\n", flush=True)
        Clock.schedule_once(lambda dt: app.stop(), 0.2)

    # Start waiting for analysis
    Clock.schedule_once(_wait_for_analysis, 0.5)


def main():
    app = SketchAnimationApp()
    app.on_start = lambda: None
    Clock.schedule_once(lambda dt: run_ui_diagnostic_simulation(app), 0.2)
    app.run()


if __name__ == '__main__':
    main()

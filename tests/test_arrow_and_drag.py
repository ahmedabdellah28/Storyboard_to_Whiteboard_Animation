"""
Test Canvas Direction Arrow Direct Toggle & Drag-and-Drop Layer Reordering.
"""
import os
import sys
import numpy as np

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_root, 'kivy'))

from kivy.clock import Clock
from main import SketchAnimationApp

class TouchMock:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.pos = (x, y)
        self.grab_current = None
        self.ud = {}

    def grab(self, widget):
        self.grab_current = widget

    def ungrab(self, widget):
        if self.grab_current is widget:
            self.grab_current = None

    def collide_point(self, x, y):
        return True

def run():
    app = SketchAnimationApp()

    def step1(dt):
        test_img = os.path.join(_root, 'test_images', 'arabic_12_panel_storyboard.jpg')
        print('[TEST] Loading image in app...', flush=True)
        app.on_image_selected(test_img)
        Clock.schedule_interval(check_scene_loaded, 0.5)

    def check_scene_loaded(dt):
        if app.sm.current == 'scene':
            Clock.unschedule(check_scene_loaded)
            print('[TEST] SceneScreen active! Running feature tests...', flush=True)
            Clock.schedule_once(test_features, 0.5)
            return False

    def test_features(dt):
        scene = app.scene_screen
        canvas_view = scene.image_preview
        objects = app.state.objects
        
        # ── TEST 1: Direct Canvas Arrow Hit-Test Toggle ──
        print('\n--- [TEST 1] Canvas Direction Arrow Direct Hit Toggle ---')
        text_objs = [o for o in objects if getattr(o, "element_type", "TEXT") in ("TEXT", "UNDERLINE")]
        assert len(text_objs) > 0, "No text objects found!"
        target_obj = text_objs[0]
        initial_dir = getattr(target_obj, "direction", "RTL")
        print(f"Target object: {target_obj.name}, initial direction: {initial_dir}")

        # Calculate exact arrow position on screen
        bbox = target_obj.bbox if canvas_view.view_mode == "PANEL" else (target_obj.global_bbox or target_obj.bbox)
        rect = canvas_view.image_to_widget_coords(*bbox)
        assert rect is not None, "Failed to map coordinates"
        sx, sy, sw, sh = rect
        arr_w, arr_h = 22, 22
        arr_x = sx + sw - arr_w - 2 if initial_dir == "RTL" else sx + 2
        arr_y = sy + sh - arr_h - 2

        # Simulate click directly on the arrow badge
        touch = TouchMock(arr_x + 5, arr_y + 5)
        img_pt = canvas_view.widget_to_image_coords(touch.x, touch.y)
        canvas_view.active_tool_instance.on_touch_down(touch, img_pt)

        new_dir = getattr(target_obj, "direction", "RTL")
        print(f"Direction after direct arrow click: {new_dir}")
        assert new_dir != initial_dir, f"Direction failed to toggle! Still {initial_dir}"
        print("-> Arrow Toggle Test 1 (RTL -> LTR): PASSED!")

        # Click arrow a second time to toggle back
        touch2 = TouchMock(arr_x + 5, arr_y + 5)
        img_pt2 = canvas_view.widget_to_image_coords(touch2.x, touch2.y)
        canvas_view.active_tool_instance.on_touch_down(touch2, img_pt2)
        final_dir = getattr(target_obj, "direction", "RTL")
        print(f"Direction after second arrow click: {final_dir}")
        assert final_dir == initial_dir, "Direction failed to toggle back!"
        print("-> Arrow Toggle Test 2 (LTR -> RTL): PASSED!")

        # ── TEST 2: Drag & Drop Layer Reordering ──
        print('\n--- [TEST 2] Panel Layer Drag-and-Drop Reordering ---')
        p1_objs_before = [o for o in app.state.objects if getattr(o, "panel_id", 1) == 1]
        assert len(p1_objs_before) >= 2, "Panel 1 should have at least 2 objects"
        first_id = p1_objs_before[0].id
        second_id = p1_objs_before[1].id
        print(f"Panel 1 Before: #1={p1_objs_before[0].name} (id={first_id}), #2={p1_objs_before[1].name} (id={second_id})")

        # Simulate drag & drop first item down to second position
        cards = scene.object_list._panel_card_groups.get(1, [])
        if not cards:
            scene.object_list._panel_headers[1].toggle()
            cards = scene.object_list._panel_card_groups.get(1, [])
        
        scene.object_list._on_drag_drop(first_id, 1, None, 1)

        p1_objs_after = [o for o in app.state.objects if getattr(o, "panel_id", 1) == 1]
        print(f"Panel 1 After:  #1={p1_objs_after[0].name} (id={p1_objs_after[0].id}), #2={p1_objs_after[1].name} (id={p1_objs_after[1].id})")
        assert p1_objs_after[0].id == second_id, "Item reordering failed!"
        assert p1_objs_after[1].id == first_id, "Item reordering failed!"
        assert p1_objs_after[0].priority_order == 1, "Priority not updated!"
        assert p1_objs_after[1].priority_order == 2, "Priority not updated!"
        print("-> Drag-and-Drop Reordering Test: PASSED!")

        print('\n===============================================================')
        print('ALL TESTS PASSED: ARROW DIRECT TOGGLE & DRAG REORDER VERIFIED!')
        print('===============================================================')
        Clock.schedule_once(lambda dt: app.stop(), 0.5)

    Clock.schedule_once(step1, 0.5)
    app.run()

if __name__ == '__main__':
    run()

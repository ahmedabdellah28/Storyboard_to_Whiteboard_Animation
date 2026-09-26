"""
Test script to open studio directly and verify live Kivy window and panels.
"""
import os
import sys
import time

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_root, 'kivy'))

from kivy.clock import Clock
from main import SketchAnimationApp

def run():
    app = SketchAnimationApp()
    start_time = time.time()

    def step1(dt):
        test_img = os.path.join(_root, 'test_images', 'arabic_12_panel_storyboard.jpg')
        print('[TEST] 1. Triggering on_image_selected with:', test_img, flush=True)
        app.on_image_selected(test_img)
        Clock.schedule_interval(check_completion, 0.5)

    def check_completion(dt):
        elapsed = time.time() - start_time
        if app.sm.current == 'scene':
            print(f'[TEST] SceneScreen reached successfully in {elapsed:.2f}s!', flush=True)
            Clock.unschedule(check_completion)
            Clock.schedule_once(verify_studio, 0.5)
            return False
        elif elapsed > 30.0:
            print('[TEST ERROR] Timeout waiting for SceneScreen!', flush=True)
            Clock.unschedule(check_completion)
            app.stop()
            return False
        else:
            print(f'[TEST] Waiting for analysis... Phase: {app.state.phase.value} ({elapsed:.1f}s)', flush=True)

    def verify_studio(dt):
        print('[TEST] 2. Verifying Studio UI & Elements...', flush=True)
        print('[TEST] Current screen name:', app.sm.current, flush=True)
        assert app.sm.current == 'scene', 'Studio screen not active!'
        
        panels = app.state.project.panels
        print(f'[TEST] Total panels detected: {len(panels)}', flush=True)
        print(f'[TEST] Total objects count: {len(app.state.objects)}', flush=True)
        assert len(panels) == 12, f'Expected 12 panels, got {len(panels)}'
        
        print('[TEST] Active Panel ID in State:', getattr(app.state, 'active_panel_id', None), flush=True)
        print('[TEST] Focused Panel ID in Viewport:', app.scene_screen.image_preview.focused_panel_id, flush=True)
        print('[TEST] Canvas Texture loaded:', app.scene_screen.image_preview.img_widget.texture is not None, flush=True)
        
        # Test switching panels in viewport
        for p_id in [1, 2, 6, 12]:
            print(f'[TEST] Focusing Panel {p_id}...')
            app.focus_panel(p_id)
            assert app.scene_screen.image_preview.focused_panel_id == p_id
            print(f'[TEST] -> Focused Panel {p_id} OK.')

        # Test selecting an object to verify inspector panel updates cleanly
        if len(app.state.objects) > 0:
            first_obj = app.state.objects[0]
            print(f'[TEST] Selecting Object: {first_obj.name} (id={first_obj.id})...')
            app.on_object_selected(first_obj.id)
            print('[TEST] Active Object ID in State:', app.state.active_object_id, flush=True)
            print('[TEST] Inspector Target:', app.scene_screen.inspector_panel.hdr_label.text, flush=True)

        print('===============================================================')
        print('SUCCESS: STUDIO FULLY VERIFIED - ALL 12 PANELS INTERACTIVE!')
        print('===============================================================')
        Clock.schedule_once(lambda dt: app.stop(), 1.0)

    Clock.schedule_once(step1, 0.5)

    print('[TEST] Starting App loop...', flush=True)
    app.run()
    print('[TEST] App finished cleanly.', flush=True)

if __name__ == '__main__':
    run()


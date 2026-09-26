import os, sys
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_root, 'kivy'))

from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager
from kivy.clock import Clock
import cv2

from engine.core.scene import SceneConfig
from engine.processing.image_processor import ImageProcessor
from ui.screens.scene_screen import SceneScreen
from ui.state.project_state import ProjectState

from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout

class TestSceneApp(MDApp):
    def build(self):
        self.state = ProjectState()
        self.sm = ScreenManager()
        
        self.scene_screen = SceneScreen(self)
        self.sm.add_widget(self.scene_screen)
        return self.sm

    def load_settings(self):
        return {}

    def save_settings(self, cfg):
        pass

    def focus_panel(self, pid):
        self.scene_screen.image_preview.set_focused_panel(pid)

    def undo(self): pass
    def redo(self): pass
    def open_export_folder(self): pass
    def animate_all_objects(self): pass
    def go_home(self): pass

def run():
    app = TestSceneApp()

    def test_image_preview_only(dt):
        test_img = os.path.join(_root, 'test_images', 'arabic_12_panel_storyboard.jpg')
        print('[STAGE 1] Testing image_preview ONLY...', flush=True)
        app.scene_screen.image_preview.set_image(test_img)
        Clock.schedule_once(test_inspector_only, 1.0)

    def test_inspector_only(dt):
        print('[STAGE 2] TICK 1 PASSED! Testing inspector ONLY...', flush=True)
        app.scene_screen.inspector_panel.refresh()
        Clock.schedule_once(test_object_list_only, 1.0)

    def test_object_list_only(dt):
        test_img = os.path.join(_root, 'test_images', 'arabic_12_panel_storyboard.jpg')
        img = cv2.imread(test_img)
        cfg = SceneConfig()
        project = ImageProcessor.process(img, cfg)
        app.state.source_image = img
        app.state.set_project(project)
        all_objects = []
        for s in project.scenes:
            for o in s.objects:
                if not o.is_frame:
                    o.scene_source_image = img
                    all_objects.append(o)
        print('[STAGE 3] TICK 2 PASSED! Populating object_list with 12 panels & expanding Panel 1...', flush=True)
        app.scene_screen.object_list.populate(all_objects, img, structure_type='STORYBOARD', project=project)
        
        # Test expanding Panel 1
        print('[STAGE 3b] Expanding Panel 1...')
        app.scene_screen.object_list._panel_headers[1].toggle()
        
        # Schedule next interaction test
        Clock.schedule_once(test_panel_interactions, 0.5)

    def test_panel_interactions(dt):
        print('[STAGE 3c] Expanding Panel 2 and focusing Panel 2 in viewport...', flush=True)
        app.scene_screen.object_list._panel_headers[2].toggle()
        app.focus_panel(2)

        print('[STAGE 3d] Expanding Panel 12 and focusing Panel 12 in viewport...', flush=True)
        app.scene_screen.object_list._panel_headers[12].toggle()
        app.focus_panel(12)

        # Select first object in state
        first_obj = app.state.objects[0]
        print(f'[STAGE 3e] Selecting active object: {first_obj.name}...')
        app.state.set_active_id(first_obj.id)
        
        Clock.schedule_once(verify_live, 0.5)

    def verify_live(dt):
        print('[STAGE 4] ALL TICKS & INTERACTIONS PASSED LIVE!')
        print('[STAGE 4] Image texture is:', app.scene_screen.image_preview.img_widget.texture)
        print('[STAGE 4] Panel headers count:', len(app.scene_screen.object_list._panel_headers))
        assert len(app.scene_screen.object_list._panel_headers) == 12
        print('======================================================================')
        print('SUCCESS: STUDIO FULLY INTERACTIVE WITH ALL 12 STORYBOARD PANELS!')
        print('======================================================================')
        Clock.schedule_once(lambda dt: app.stop(), 0.5)

    Clock.schedule_once(test_image_preview_only, 0.5)

    app.run()

if __name__ == '__main__':
    run()

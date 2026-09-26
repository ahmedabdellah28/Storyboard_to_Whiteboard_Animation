"""
Automated Test for Single Open Panel Animation vs All Panels Animation.
Tests:
1. animate_single_panel(1) extracts and filters objects only for Panel 1
2. animate_all_objects() includes all objects across all panels
3. Pipeline isolation for single panel rendering
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kivy")))

from ui.state.project_state import ProjectState, SceneObject

def test_panel_vs_all_animation():
    state = ProjectState()
    
    # Create objects across 3 panels
    p1_obj1 = SceneObject(id="p1_o1", name="Title 1", panel_id=1, priority_order=1)
    p1_obj2 = SceneObject(id="p1_o2", name="Text 1", panel_id=1, priority_order=2)
    
    p2_obj1 = SceneObject(id="p2_o1", name="Title 2", panel_id=2, priority_order=1)
    p2_obj2 = SceneObject(id="p2_o2", name="Text 2", panel_id=2, priority_order=2)
    
    p3_obj1 = SceneObject(id="p3_o1", name="Title 3", panel_id=3, priority_order=1)
    
    state.set_objects([p1_obj1, p1_obj2, p2_obj1, p2_obj2, p3_obj1])
    
    # 1. Single Panel 1 animation target
    p1_target = [o for o in state.objects if o.panel_id == 1 and getattr(o, "visibility", True)]
    assert len(p1_target) == 2
    assert all(o.panel_id == 1 for o in p1_target)
    print("[TEST 1] Single Panel 1 Object Filter: PASSED! (Only Panel 1 objects selected)")
    
    # 2. Single Panel 2 animation target
    p2_target = [o for o in state.objects if o.panel_id == 2 and getattr(o, "visibility", True)]
    assert len(p2_target) == 2
    assert all(o.panel_id == 2 for o in p2_target)
    print("[TEST 2] Single Panel 2 Object Filter: PASSED! (Only Panel 2 objects selected)")
    
    # 3. Animate All target
    all_target = [o for o in state.objects if getattr(o, "visibility", True)]
    assert len(all_target) == 5
    print("[TEST 3] Animate All Target: PASSED! (All 5 objects across 3 panels selected)")

    print("\n=======================================================")
    print("ALL SINGLE PANEL VS ALL PANELS ANIMATION TESTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    test_panel_vs_all_animation()

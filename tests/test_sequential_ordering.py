"""
Automated Test for Sequential Click-Ordering and Panel Priority Deselection.
Tests:
1. Clearing panel priorities (تفريغ الترتيب)
2. Sequential selection (Clicking items assigns 1, 2, 3...)
3. Deselecting an assigned item (Unassigns and automatically decrements higher priority items)
4. Re-assigning a deselected item (Appends to sequence without gaps)
5. Auto-sequencing 1..N
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kivy")))

from ui.state.project_state import ProjectState, SceneObject

def test_sequential_ordering():
    state = ProjectState()
    
    # Create mock objects in Panel 1
    obj1 = SceneObject(id="obj_1", name="Title", panel_id=1, priority_order=1)
    obj2 = SceneObject(id="obj_2", name="Subtitle", panel_id=1, priority_order=2)
    obj3 = SceneObject(id="obj_3", name="Paragraph", panel_id=1, priority_order=3)
    obj4 = SceneObject(id="obj_4", name="Button", panel_id=1, priority_order=4)
    
    state.set_objects([obj1, obj2, obj3, obj4])
    print("[TEST 1] Initial state: 4 objects with priority 1, 2, 3, 4")
    
    # 1. Clear Panel Priority
    state.clear_panel_priority(1)
    p_objs = [o for o in state.objects if o.panel_id == 1]
    for o in p_objs:
        assert o.priority_order is None, f"Expected None for {o.name}, got {o.priority_order}"
    print("-> Clear Panel Priority: PASSED! All objects are unassigned.")
    
    # 2. Sequential Click Ordering: Click obj3 first, then obj1, then obj4
    is_assigned, p_num = state.toggle_panel_object_priority(1, "obj_3")
    assert is_assigned is True and p_num == 1, f"Expected obj3 to be #1, got {p_num}"
    assert obj3.priority_order == 1
    print("-> Click obj3 -> Assigned #1: PASSED!")
    
    is_assigned, p_num = state.toggle_panel_object_priority(1, "obj_1")
    assert is_assigned is True and p_num == 2, f"Expected obj1 to be #2, got {p_num}"
    assert obj1.priority_order == 2
    print("-> Click obj1 -> Assigned #2: PASSED!")
    
    is_assigned, p_num = state.toggle_panel_object_priority(1, "obj_4")
    assert is_assigned is True and p_num == 3, f"Expected obj4 to be #3, got {p_num}"
    assert obj4.priority_order == 3
    print("-> Click obj4 -> Assigned #3: PASSED!")
    
    # Verify current panel order in state
    current_assigned = [o.id for o in state.objects if o.priority_order is not None]
    assert current_assigned == ["obj_3", "obj_1", "obj_4"], f"Wrong order: {current_assigned}"
    assert obj2.priority_order is None
    print("-> Sequence order verified: obj3(#1), obj1(#2), obj4(#3), obj2(unassigned): PASSED!")
    
    # 3. Deselect/Unassign an assigned item: Click obj1 (#2)
    is_assigned, p_num = state.toggle_panel_object_priority(1, "obj_1")
    assert is_assigned is False and p_num is None, "Expected obj1 to be unassigned"
    assert obj1.priority_order is None
    # obj4 should have shifted from #3 to #2
    assert obj4.priority_order == 2, f"Expected obj4 to shift to #2, got {obj4.priority_order}"
    assert obj3.priority_order == 1, f"Expected obj3 to remain #1, got {obj3.priority_order}"
    print("-> Deselect obj1 -> obj4 automatically shifted from #3 to #2: PASSED!")
    
    # 4. Re-assign obj1 -> should become #3
    is_assigned, p_num = state.toggle_panel_object_priority(1, "obj_1")
    assert is_assigned is True and p_num == 3, f"Expected obj1 to be assigned #3, got {p_num}"
    assert obj1.priority_order == 3
    print("-> Re-click obj1 -> Assigned #3: PASSED!")
    
    # 5. Auto Sequence 1..N
    state.reset_panel_priority_auto(1)
    p_objs = [o for o in state.objects if o.panel_id == 1]
    for idx, o in enumerate(p_objs):
        assert o.priority_order == idx + 1, f"Expected {idx+1} for {o.name}, got {o.priority_order}"
    print("-> Reset Auto 1..N: PASSED!")

    print("\n=======================================================")
    print("ALL SEQUENTIAL CLICK-ORDERING TESTS PASSED PERFECTLY!")
    print("=======================================================")

if __name__ == "__main__":
    test_sequential_ordering()

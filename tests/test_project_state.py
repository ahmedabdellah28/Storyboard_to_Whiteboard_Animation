"""
Unit Tests for Pure Python ProjectState & Command History (Phase 3).
Executes entirely in pure Python with zero Kivy dependency.
"""
import sys
import unittest
import numpy as np
from pathlib import Path

kivy_dir = Path(__file__).resolve().parent.parent / "kivy"
sys.path.insert(0, str(kivy_dir))

from engine.core.scene import SceneObject, Scene, SceneConfig
from engine.core.project import Project, StructureType
from ui.state.commands import (
    AppPhase,
    MoveOrResizeCommand,
    AddObjectCommand,
    DeleteObjectCommand,
    ReorderCommand,
    RenameCommand,
    PropertyChangeCommand
)
from ui.state.project_state import ProjectState


class TestProjectStatePurePython(unittest.TestCase):
    def setUp(self):
        self.state = ProjectState()

    def test_01_initial_state_and_tool(self):
        self.assertEqual(self.state.phase, AppPhase.EMPTY)
        self.assertEqual(self.state.active_tool, "SELECT")
        self.assertIsNone(self.state.active_object_id)
        self.assertEqual(len(self.state.objects), 0)

        # Set tool
        self.state.set_active_tool("ADD_BOX")
        self.assertEqual(self.state.active_tool, "ADD_BOX")

    def test_02_add_object_and_selection(self):
        obj1 = SceneObject(id="obj-001", name="Element 1", bbox=(10, 20, 100, 150))
        self.state.add_object(obj1, record_undo=True)

        self.assertEqual(len(self.state.objects), 1)
        self.assertEqual(self.state.active_object_id, "obj-001")
        self.assertEqual(self.state.active_object.name, "Element 1")

        # Single Source of Truth assertions
        self.assertEqual(self.state.active_object.id, "obj-001")
        self.assertEqual(self.state.get_object_index(self.state.active_object_id), 0)

    def test_03_undo_redo_add_object(self):
        obj1 = SceneObject(id="obj-001", name="Element 1", bbox=(10, 20, 100, 150))
        self.state.add_object(obj1, record_undo=True)
        self.assertEqual(len(self.state.objects), 1)

        # Undo
        self.assertTrue(self.state.undo())
        self.assertEqual(len(self.state.objects), 0)
        self.assertIsNone(self.state.active_object_id)

        # Redo
        self.assertTrue(self.state.redo())
        self.assertEqual(len(self.state.objects), 1)
        self.assertEqual(self.state.active_object_id, "obj-001")

    def test_04_move_or_resize_command(self):
        obj1 = SceneObject(id="obj-001", name="Element 1", bbox=(10, 20, 100, 150))
        self.state.add_object(obj1, record_undo=False)

        # Move/Resize
        new_bbox = (50, 60, 200, 250)
        self.state.update_object_bbox("obj-001", new_bbox, record_undo=True)
        self.assertEqual(self.state.active_object.bbox, new_bbox)

        # Undo
        self.state.undo()
        self.assertEqual(self.state.active_object.bbox, (10, 20, 100, 150))

        # Redo
        self.state.redo()
        self.assertEqual(self.state.active_object.bbox, new_bbox)

    def test_05_reorder_objects_with_undo(self):
        o1 = SceneObject(id="o1", name="First")
        o2 = SceneObject(id="o2", name="Second")
        self.state.add_object(o1, record_undo=False)
        self.state.add_object(o2, record_undo=False)

        self.assertEqual([o.id for o in self.state.objects], ["o1", "o2"])

        # Reorder (from 0 to 1)
        self.state.reorder(0, 1, record_undo=True)
        self.assertEqual([o.id for o in self.state.objects], ["o2", "o1"])

        # Undo
        self.state.undo()
        self.assertEqual([o.id for o in self.state.objects], ["o1", "o2"])

    def test_06_observer_event_emission(self):
        events_received = []

        def listener(event_name, data):
            events_received.append((event_name, data))

        self.state.subscribe(listener)

        self.state.set_active_tool("PAN")
        self.state.set_phase(AppPhase.READY)

        obj = SceneObject(id="o1", name="Observed")
        self.state.add_object(obj, record_undo=False)

        event_names = [e[0] for e in events_received]
        self.assertIn("TOOL_CHANGED", event_names)
        self.assertIn("PHASE_CHANGED", event_names)
        self.assertIn("ACTIVE_OBJECT_CHANGED", event_names)
        self.assertIn("OBJECTS_CHANGED", event_names)


if __name__ == "__main__":
    unittest.main()

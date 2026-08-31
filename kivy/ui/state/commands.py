"""
Command Pattern and Phase Definitions for Project State (Pure Python).
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Any
from engine.core.scene import SceneObject


class AppPhase(Enum):
    EMPTY = "empty"
    ANALYZING = "analyzing"
    READY = "ready"
    ANIMATING = "animating"
    PREVIEW = "preview"
    EXPORTING = "exporting"


class Command(ABC):
    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def undo(self):
        pass


class MoveOrResizeCommand(Command):
    def __init__(self, state: Any, obj_id: str, old_bbox: tuple, new_bbox: tuple):
        self.state = state
        self.obj_id = obj_id
        self.old_bbox = old_bbox
        self.new_bbox = new_bbox

    def execute(self):
        self.state.update_object_bbox(self.obj_id, self.new_bbox, record_undo=False)

    def undo(self):
        self.state.update_object_bbox(self.obj_id, self.old_bbox, record_undo=False)


class AddObjectCommand(Command):
    def __init__(self, state: Any, obj: SceneObject):
        self.state = state
        self.obj = obj

    def execute(self):
        self.state.add_object(self.obj, record_undo=False)

    def undo(self):
        self.state.remove_object_by_id(self.obj.id, record_undo=False)


class DeleteObjectCommand(Command):
    def __init__(self, state: Any, obj: SceneObject, index: int):
        self.state = state
        self.obj = obj
        self.index = index

    def execute(self):
        self.state.remove_object_by_id(self.obj.id, record_undo=False)

    def undo(self):
        self.state.insert_object(self.index, self.obj, record_undo=False)


class ReorderCommand(Command):
    def __init__(self, state: Any, from_idx: int, to_idx: int):
        self.state = state
        self.from_idx = from_idx
        self.to_idx = to_idx

    def execute(self):
        self.state.reorder(self.from_idx, self.to_idx, record_undo=False)

    def undo(self):
        self.state.reorder(self.to_idx, self.from_idx, record_undo=False)


class RenameCommand(Command):
    def __init__(self, state: Any, obj_id: str, old_name: str, new_name: str):
        self.state = state
        self.obj_id = obj_id
        self.old_name = old_name
        self.new_name = new_name

    def execute(self):
        self.state.update_object_name(self.obj_id, self.new_name, record_undo=False)

    def undo(self):
        self.state.update_object_name(self.obj_id, self.old_name, record_undo=False)


class PropertyChangeCommand(Command):
    def __init__(self, state: Any, obj_id: str, prop_name: str, old_val: Any, new_val: Any):
        self.state = state
        self.obj_id = obj_id
        self.prop_name = prop_name
        self.old_val = old_val
        self.new_val = new_val

    def execute(self):
        self.state.update_object_property(self.obj_id, self.prop_name, self.new_val, record_undo=False)

    def undo(self):
        self.state.update_object_property(self.obj_id, self.prop_name, self.old_val, record_undo=False)


class CommandHistory:
    def __init__(self, max_history: int = 50):
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_history = max_history

    def push(self, cmd: Command):
        self._undo_stack.append(cmd)
        self._redo_stack.clear()
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        cmd = self._redo_stack.pop()
        cmd.execute()
        self._undo_stack.append(cmd)
        return True

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()

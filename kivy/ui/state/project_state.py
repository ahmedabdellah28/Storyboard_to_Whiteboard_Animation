"""
Central Project State (Pure Python — Zero Kivy Dependency).
Single Source of Truth for the entire Visual Animation Studio.
Includes robust Command-based Undo / Redo system.
"""
import uuid
from typing import List, Optional, Callable, Dict, Any, Tuple
import numpy as np

from engine.core.scene import SceneObject
from .commands import (
    AppPhase,
    Command,
    MoveOrResizeCommand,
    AddObjectCommand,
    DeleteObjectCommand,
    ReorderCommand,
    RenameCommand,
    PropertyChangeCommand,
    CommandHistory
)


class ProjectState:
    def __init__(self):
        self.phase: AppPhase = AppPhase.EMPTY

        # Source Asset
        self.source_image_path: str = ""
        self.source_image: Optional[np.ndarray] = None

        # Engine Project reference
        self.project = None
        self.current_scene_index: int = 0

        # Unified Scene Objects Collection (Auto & Manual unified)
        self.objects: List[SceneObject] = []
        
        # Unified Single Source of Truth for Active Selection
        self.active_object_id: Optional[str] = None
        
        # Active Canvas Tool: "SELECT" | "ADD_BOX" | "PAN"
        self.active_tool: str = "SELECT"

        # Undo / Redo Manager
        self.command_history = CommandHistory()

        # Analysis Progress
        self.analysis_progress: float = 0.0
        self.analysis_stage: str = ""

        # Event Listeners (Pure Python Observers)
        self._listeners: List[Callable[[str, Any], None]] = []

        # Direct Observers & Callbacks (for backwards compatibility)
        self._on_phase_change: Optional[Callable] = None
        self._on_progress: Optional[Callable] = None
        self._on_objects_changed: Optional[Callable] = None
        self._on_active_object_changed: Optional[Callable] = None
        self._on_tool_changed: Optional[Callable] = None

    # ── Observer Subscription API ──

    def subscribe(self, listener: Callable[[str, Any], None]):
        """Subscribe a pure callback to all state events."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: Callable[[str, Any], None]):
        """Unsubscribe a callback."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _emit(self, event_name: str, payload: Any = None):
        """Emit state mutation event to all registered observers."""
        for listener in self._listeners:
            try:
                listener(event_name, payload)
            except Exception as e:
                print(f"[ProjectState Observer Error] on '{event_name}': {e}")

    # ── Phase ──

    def set_phase(self, phase: AppPhase):
        self.phase = phase
        if self._on_phase_change:
            self._on_phase_change(phase)
        self._emit("PHASE_CHANGED", phase)

    # ── Tool ──

    def set_active_tool(self, tool: str):
        if tool in ("SELECT", "ADD_BOX", "PAN"):
            self.active_tool = tool
            if self._on_tool_changed:
                self._on_tool_changed(tool)
            self._emit("TOOL_CHANGED", tool)

    # ── Analysis Progress ──

    def set_progress(self, progress: float, stage: str):
        self.analysis_progress = progress
        self.analysis_stage = stage
        if self._on_progress:
            self._on_progress(progress, stage)
        self._emit("PROGRESS_CHANGED", (progress, stage))

    # ── Project & Scenes ──
    
    def set_project(self, project):
        self.project = project
        self.current_scene_index = 0
        self.command_history.clear()
        if project and project.scenes:
            all_objects = []
            for s in project.scenes:
                for o in s.objects:
                    if not o.is_frame:
                        if not getattr(o, "id", None):
                            o.id = str(uuid.uuid4())[:8]
                        all_objects.append(o)
            self.set_objects(all_objects)
        else:
            self.set_objects([])
        self._emit("PROJECT_CHANGED", project)

    @property
    def scene(self):
        if self.project and self.project.scenes and 0 <= self.current_scene_index < len(self.project.scenes):
            return self.project.scenes[self.current_scene_index]
        return None
        
    @property
    def all_scenes(self):
        if self.project:
            return self.project.scenes
        return []

    # ── Objects Management (Unified CRUD) ──

    def set_objects(self, objects: list):
        """Set objects, ensure IDs exist, and preserve or reset active selection."""
        self.objects = []
        for o in objects:
            if not o.is_frame:
                if not getattr(o, "id", None):
                    o.id = str(uuid.uuid4())[:8]
                self.objects.append(o)

        # Validate active_object_id
        if self.active_object_id and not any(o.id == self.active_object_id for o in self.objects):
            self.set_active_id(self.objects[0].id if self.objects else None)
        elif not self.active_object_id and self.objects:
            self.set_active_id(self.objects[0].id)
        else:
            self._notify_active_changed()

        self._notify_objects_changed()

    def get_object_by_id(self, obj_id: Optional[str]) -> Optional[SceneObject]:
        if not obj_id:
            return None
        for o in self.objects:
            if o.id == obj_id:
                return o
        return None

    def get_object_index(self, obj_id: Optional[str]) -> int:
        if not obj_id:
            return -1
        for idx, o in enumerate(self.objects):
            if o.id == obj_id:
                return idx
        return -1

    def set_active_id(self, obj_id: Optional[str]):
        """Sets the single active object ID and notifies all listening components."""
        if self.active_object_id == obj_id:
            return
        self.active_object_id = obj_id
        self._notify_active_changed()

    def _notify_active_changed(self):
        active_obj = self.get_object_by_id(self.active_object_id)
        if self._on_active_object_changed:
            self._on_active_object_changed(active_obj)
        self._emit("ACTIVE_OBJECT_CHANGED", active_obj)

    def _notify_objects_changed(self):
        if self._on_objects_changed:
            self._on_objects_changed(self.objects)
        self._emit("OBJECTS_CHANGED", self.objects)

    @property
    def active_object(self) -> Optional[SceneObject]:
        return self.get_object_by_id(self.active_object_id)

    # ── CRUD Operations with Undo ──

    def add_object(self, obj: SceneObject, record_undo: bool = True):
        if not getattr(obj, "id", None):
            obj.id = str(uuid.uuid4())[:8]

        self.objects.append(obj)
        if self.project and self.project.scenes:
            target_scene = next((s for s in self.project.scenes if s.panel_id == getattr(obj, "panel_id", 1)), self.project.scenes[0])
            if obj not in target_scene.objects:
                target_scene.objects.append(obj)

        if record_undo:
            self.command_history.push(AddObjectCommand(self, obj))

        self.set_active_id(obj.id)
        self._notify_objects_changed()

    def insert_object(self, index: int, obj: SceneObject, record_undo: bool = True):
        if not getattr(obj, "id", None):
            obj.id = str(uuid.uuid4())[:8]

        idx = max(0, min(len(self.objects), index))
        self.objects.insert(idx, obj)

        if self.project and self.project.scenes:
            target_scene = next((s for s in self.project.scenes if s.panel_id == getattr(obj, "panel_id", 1)), self.project.scenes[0])
            if obj not in target_scene.objects:
                target_scene.objects.append(obj)

        if record_undo:
            self.command_history.push(AddObjectCommand(self, obj))

        self.set_active_id(obj.id)
        self._notify_objects_changed()

    def remove_object_by_id(self, obj_id: str, record_undo: bool = True):
        idx = self.get_object_index(obj_id)
        if idx == -1:
            return

        removed = self.objects.pop(idx)

        if self.project and self.project.scenes:
            for sc in self.project.scenes:
                if removed in sc.objects:
                    sc.objects.remove(removed)

        if record_undo:
            self.command_history.push(DeleteObjectCommand(self, removed, idx))

        # Update active selection cleanly
        if self.active_object_id == obj_id:
            if self.objects:
                new_idx = min(idx, len(self.objects) - 1)
                self.set_active_id(self.objects[new_idx].id)
            else:
                self.set_active_id(None)

        self._notify_objects_changed()

    def update_object_bbox(self, obj_id: str, new_bbox: tuple, record_undo: bool = True):
        obj = self.get_object_by_id(obj_id)
        if not obj:
            return

        old_bbox = obj.global_bbox or obj.bbox
        if old_bbox == new_bbox:
            return

        if record_undo:
            self.command_history.push(MoveOrResizeCommand(self, obj_id, old_bbox, new_bbox))

        obj.bbox = new_bbox
        obj.global_bbox = new_bbox
        obj.width = new_bbox[2]
        obj.height = new_bbox[3]
        obj.center = np.array([new_bbox[0] + new_bbox[2] / 2.0, new_bbox[1] + new_bbox[3] / 2.0], dtype=np.float64)

        # Update crop if image available
        if self.source_image is not None:
            bx, by, bw, bh = new_bbox
            ih, iw = self.source_image.shape[:2]
            bx = max(0, min(iw - 1, bx))
            by = max(0, min(ih - 1, by))
            bw = max(4, min(iw - bx, bw))
            bh = max(4, min(ih - by, bh))
            obj.crop = self.source_image[by:by+bh, bx:bx+bw].copy()

        self._notify_active_changed()
        self._notify_objects_changed()

    def update_object_name(self, obj_id: str, new_name: str, record_undo: bool = True):
        obj = self.get_object_by_id(obj_id)
        if not obj or obj.name == new_name:
            return

        if record_undo:
            self.command_history.push(RenameCommand(self, obj_id, obj.name, new_name))

        obj.name = new_name
        self._notify_active_changed()
        self._notify_objects_changed()

    def update_object_property(self, obj_id: str, prop_name: str, new_val: Any, record_undo: bool = True):
        obj = self.get_object_by_id(obj_id)
        if not obj:
            return

        old_val = getattr(obj, prop_name, None)
        if old_val == new_val:
            return

        if record_undo:
            self.command_history.push(PropertyChangeCommand(self, obj_id, prop_name, old_val, new_val))

        setattr(obj, prop_name, new_val)
        self._notify_active_changed()
        self._notify_objects_changed()

    def duplicate_object(self, obj_id: str):
        src_obj = self.get_object_by_id(obj_id)
        if not src_obj:
            return

        bx, by, bw, bh = src_obj.global_bbox or src_obj.bbox
        new_bbox = (bx + 20, by + 20, bw, bh)

        dup = SceneObject(
            id=str(uuid.uuid4())[:8],
            name=f"{src_obj.name} Copy",
            bbox=new_bbox,
            global_bbox=new_bbox,
            panel_id=src_obj.panel_id,
            width=bw,
            height=bh,
            visibility=src_obj.visibility,
            speed_multiplier=src_obj.speed_multiplier,
            camera_zoom_override=src_obj.camera_zoom_override,
            crop=src_obj.crop.copy() if src_obj.crop is not None else None
        )
        self.add_object(dup, record_undo=True)

    def reorder(self, from_idx: int, to_idx: int, record_undo: bool = True):
        if 0 <= from_idx < len(self.objects) and 0 <= to_idx < len(self.objects) and from_idx != to_idx:
            if record_undo:
                self.command_history.push(ReorderCommand(self, from_idx, to_idx))
            obj = self.objects.pop(from_idx)
            self.objects.insert(to_idx, obj)
            self._notify_objects_changed()

    def undo(self) -> bool:
        res = self.command_history.undo()
        if res:
            self._notify_objects_changed()
            self._notify_active_changed()
        return res

    def redo(self) -> bool:
        res = self.command_history.redo()
        if res:
            self._notify_objects_changed()
            self._notify_active_changed()
        return res

    # ── Reset ──

    def reset(self):
        self.phase = AppPhase.EMPTY
        self.source_image_path = ""
        self.source_image = None
        self.project = None
        self.current_scene_index = 0
        self.objects = []
        self.active_object_id = None
        self.active_tool = "SELECT"
        self.command_history.clear()
        self.analysis_progress = 0.0
        self.analysis_stage = ""
        self._emit("RESET", None)

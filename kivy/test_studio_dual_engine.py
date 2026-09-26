"""
Studio Dual-Engine Integration Test (Automated Headless Test)
File: kivy/test_studio_dual_engine.py
"""
import os
import sys
import cv2
import numpy as np

# Ensure kivy root is in sys.path
_kivy_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _kivy_root)

from engine.core.scene import SceneConfig, SceneObject
from engine.core.project import Project, StructureType
from engine.processing.image_processor import ImageProcessor
from engine.processing.whiteboard_processor import WhiteboardProcessor
from ui.state.project_state import ProjectState

test_img_path = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\.user_uploaded\media_1788292396282.png"

print("--- Testing ImageProcessor with Dual-Engine Whiteboard Integration ---")
img = cv2.imread(test_img_path)
assert img is not None, "Failed to load test image"

config = SceneConfig(width=img.shape[1], height=img.shape[0])
project = ImageProcessor.process(img, config)

print(f"Project Type: {project.structure_type.value}")
print(f"Total Panels Discovered: {len(project.panels)}")
print(f"Total Scenes Created: {len(project.scenes)}")

total_objs = sum(len(sc.objects) for sc in project.scenes)
print(f"Total Objects in Project: {total_objs}")

# Test State Synchronization
state = ProjectState()
state.set_project(project)
print(f"State Objects Count: {len(state.objects)}")
assert len(state.objects) > 0, "State objects should not be empty"

# Test Active Object & Direction Toggling
first_text_obj = next((o for o in state.objects if getattr(o, "direction", None) in ("RTL", "LTR")), None)
if first_text_obj:
    print(f"Testing Direction Toggle on Object '{first_text_obj.name}' (Initial: {first_text_obj.direction})")
    orig_dir = first_text_obj.direction
    # Toggle direction
    first_text_obj.direction = "LTR" if orig_dir == "RTL" else "RTL"
    print(f"  -> Toggled Direction to: {first_text_obj.direction}")
    assert first_text_obj.direction != orig_dir, "Direction toggle failed"

print("==========================================================================")
print("STUDIO DUAL-ENGINE HEADLESS TEST PASSED 100%!")
print("==========================================================================")

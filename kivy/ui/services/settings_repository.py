"""
Settings Repository for Application Configuration Persistence (Pure Python / JSON).
"""
import os
import json
from typing import Dict, Any
from engine.core.scene import SceneConfig


class SettingsRepository:
    def __init__(self, settings_file_path: str = None):
        if settings_file_path is None:
            home_dir = os.path.expanduser("~")
            self.settings_file = os.path.join(home_dir, ".image_to_animation", "settings.json")
        else:
            self.settings_file = settings_file_path
            
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)

    def get_default_settings(self) -> Dict[str, Any]:
        return {
            "width": 1280, "height": 720, "fps": 30,
            "detail_level": "HIGH", "color_palette_size": 28,
            "drawing_speed": 1.5,
            "character_drawing_speed": 1.5,
            "text_drawing_speed": 1.5,
            "camera_zoom_scale": 1.40, "transition_duration": 0.5,
            "show_hand": True, "hand_scale": 0.95, "element_spacing": 24,
            "drawing_direction": "OUTSIDE_IN",
            "ring_step": 5, "brush_radius": 8, "sample_interval": 3.0,
            "end_hold_seconds": 1.5,
            "deep_mode": True,
            "deep_min_parts": 4,
            "deep_max_parts": 6,
            "suppress_borders": True
        }

    def load_settings(self) -> Dict[str, Any]:
        """Load user settings from JSON with fallback to defaults."""
        defaults = self.get_default_settings()
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Backward compatibility: inherit from drawing_speed if specific keys are absent
                    if "drawing_speed" in data:
                        if "character_drawing_speed" not in data:
                            data["character_drawing_speed"] = data["drawing_speed"]
                        if "text_drawing_speed" not in data:
                            data["text_drawing_speed"] = data["drawing_speed"]
                    defaults.update(data)
            except Exception as e:
                print(f"[SettingsRepository] Could not load settings: {e}")
        return defaults

    def save_settings(self, config: SceneConfig) -> bool:
        """Save SceneConfig to JSON."""
        data = {
            "width": config.width,
            "height": config.height,
            "fps": config.fps,
            "detail_level": config.detail_level,
            "color_palette_size": config.color_palette_size,
            "drawing_speed": config.drawing_speed,
            "character_drawing_speed": getattr(config, "character_drawing_speed", config.drawing_speed),
            "text_drawing_speed": getattr(config, "text_drawing_speed", config.drawing_speed),
            "camera_zoom_scale": getattr(config, "camera_zoom_scale", 2.10),
            "transition_duration": config.transition_duration,
            "show_hand": getattr(config, "show_hand", True),
            "hand_scale": getattr(config, "hand_scale", 0.95),
            "element_spacing": getattr(config, "element_spacing", 24),
            "drawing_direction": getattr(config, "drawing_direction", "OUTSIDE_IN"),
            "ring_step": getattr(config, "ring_step", 5),
            "brush_radius": getattr(config, "brush_radius", 8),
            "sample_interval": getattr(config, "sample_interval", 3.0),
            "end_hold_seconds": getattr(config, "end_hold_seconds", 1.5),
            "deep_mode": getattr(config, "deep_mode", True),
            "deep_min_parts": getattr(config, "deep_min_parts", 4),
            "deep_max_parts": getattr(config, "deep_max_parts", 6),
            "suppress_borders": getattr(config, "suppress_borders", True)
        }
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"[SettingsRepository] Could not save settings: {e}")
            return False

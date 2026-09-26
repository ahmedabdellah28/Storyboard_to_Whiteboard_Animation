import uuid
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any, Dict
from .stroke import Stroke
from .region import ColorRegion


@dataclass
class SceneConfig:
    width: int = 1280
    height: int = 720
    fps: int = 30
    detail_level: str = "MEDIUM"               # "LOW", "MEDIUM", "HIGH"
    color_palette_size: int = 28               # Palette size for K-Means quantization (rich colors)
    min_stroke_length: float = 12.0            # Minimum stroke length in pixels
    min_region_area: int = 8                   # Minimum pixel area for discrete color regions
    end_hold_seconds: float = 1.5              # Hold final composition duration
    drawing_order: str = "AUTO"                # "AUTO", "TOP_TO_BOTTOM", "LEFT_TO_RIGHT", "CENTER_OUT", "SPATIAL"
    camera_preset: str = "SEQUENTIAL_OBJECT_FOCUS"  # "SEQUENTIAL_OBJECT_FOCUS", "STATIC", "SLOW_ZOOM"
    camera_intensity: float = 0.65             # 0.0 (static) to 1.0 (deep focus)
    camera_zoom_scale: float = 1.40            # Default 1.40x balanced whiteboard focus zoom
    fill_mode: str = "FOLLOW_OUTLINE"          # Default fill reveal strategy
    establishing_duration: float = 0.7         # Initial wide shot duration (seconds)
    transition_duration: float = 0.5           # Camera transition between objects (seconds)
    drawing_speed: float = 1.5                 # Multiplier for drawing animation speed
    character_drawing_speed: float = 1.5       # Multiplier for character/artwork drawing speed
    text_drawing_speed: float = 1.5            # Multiplier for text/typography handwriting speed
    show_hand: bool = True                     # Visual drawing hand & pencil overlay toggle
    hand_scale: float = 0.95                   # Scale factor for drawing hand sprite
    hand_target_h: int = 340                   # Target hand sprite height in pixels
    hand_opacity: float = 1.0                  # Hand overlay opacity
    hand_tilt_enabled: bool = True             # Dynamic pencil angle tilt along stroke paths
    element_spacing: int = 24                  # Spacing between storyboard panels (px)
    drawing_direction: str = "OUTSIDE_IN"      # "OUTSIDE_IN" or "INSIDE_OUT"
    ring_step: int = 5                         # Distance between concentric orbital rings (px)
    brush_radius: int = 8                      # Pencil/Marker reveal brush radius (px)
    sample_interval: float = 3.0               # Path sampling distance (px)
    deep_mode: bool = True                     # Deep Dynamic Organic 6-Stage Pipeline Engine Toggle
    deep_min_parts: int = 4                    # Minimum dynamic anatomical organic parts per subject
    deep_max_parts: int = 6                    # Maximum dynamic anatomical organic parts per subject
    suppress_borders: bool = True              # Automatically suppress outer rectangular panel borders


@dataclass
class SceneObject:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Object"
    strokes: List[Stroke] = field(default_factory=list)
    fills: List[ColorRegion] = field(default_factory=list)
    details: List[Stroke] = field(default_factory=list)
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0) # (x, y, w, h)
    global_bbox: Optional[Tuple[int, int, int, int]] = None # Bbox relative to full parent storyboard image
    panel_id: int = 1
    center: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=np.float64))
    width: int = 0
    height: int = 0
    area: int = 0
    z_index: int = 0
    priority_order: int = 1                    # Execution priority (1, 2, 3...)
    visibility: bool = True
    speed_multiplier: float = 1.0
    camera_zoom_override: Optional[float] = None
    importance: float = 0.0
    is_frame: bool = False
    animation_start: float = 0.0
    animation_end: float = 0.0
    duration: float = 0.0
    crop: Optional[np.ndarray] = None
    mask: Optional[np.ndarray] = None
    sub_elements: List[Dict[str, Any]] = field(default_factory=list)
    direction: str = "RTL"                     # "RTL" (Arabic ⬅), "LTR" (English ➡), "CIRCUIT" (Geometry)
    element_type: str = "TEXT"                 # "CHARACTER", "TEXT", "MATH", "DIAGRAM", "EMOJI", "ICON", "UNDERLINE"
    comp_ids: List[int] = field(default_factory=list)

    def compute_bounds_and_importance(self, scene_width: int, scene_height: int):
        all_pts = []
        for s in self.strokes + self.details:
            if len(s.points) > 0:
                all_pts.append(s.points)
        for f in self.fills:
            if f.mask is not None and f.area > 0:
                y_idx, x_idx = np.where(f.mask > 0)
                if len(x_idx) > 0:
                    pts = np.column_stack([x_idx, y_idx])
                    all_pts.append(pts)

        if len(all_pts) > 0:
            stacked = np.vstack(all_pts)
            min_x = max(0, int(np.min(stacked[:, 0])))
            min_y = max(0, int(np.min(stacked[:, 1])))
            max_x = min(scene_width, int(np.max(stacked[:, 0])))
            max_y = min(scene_height, int(np.max(stacked[:, 1])))
            self.width = max(1, max_x - min_x)
            self.height = max(1, max_y - min_y)
            self.bbox = (min_x, min_y, self.width, self.height)
            self.area = self.width * self.height
            self.center = np.array([(min_x + max_x) / 2.0, (min_y + max_y) / 2.0], dtype=np.float64)

        # Check if full-scene border frame (only if it has no rich internal strokes or fills)
        has_rich_content = (len(self.strokes) + len(self.details) >= 8) or len(self.fills) >= 4
        if not has_rich_content and self.width > 0.90 * scene_width and self.height > 0.90 * scene_height:
            self.is_frame = True
            self.name = "Scene_Frame"

        # Geometric importance computation
        total_scene_area = max(1.0, float(scene_width * scene_height))
        norm_area = min(1.0, self.area / total_scene_area)

        total_outline_len = sum(s.length for s in self.strokes)
        norm_outline = min(1.0, total_outline_len / max(1.0, (scene_width + scene_height) * 2.0))

        detail_count = len(self.details)
        norm_details = min(1.0, detail_count / 50.0)

        fill_area = sum(f.area for f in self.fills)
        norm_fill = min(1.0, fill_area / total_scene_area)

        scene_center = np.array([scene_width / 2.0, scene_height / 2.0], dtype=np.float64)
        dist_to_center = float(np.linalg.norm(self.center - scene_center))
        max_dist = float(np.linalg.norm(scene_center))
        center_proximity = max(0.0, 1.0 - (dist_to_center / max(1.0, max_dist)))

        # Weighted score
        self.importance = float(
            0.25 * norm_area +
            0.25 * norm_outline +
            0.15 * norm_details +
            0.20 * center_proximity +
            0.15 * norm_fill
        )


@dataclass
class Scene:
    config: SceneConfig
    objects: List[SceneObject] = field(default_factory=list)
    background_color: Tuple[int, int, int] = (255, 255, 255)
    source_image: Optional[np.ndarray] = None
    canvas_width: int = 1920
    canvas_height: int = 1080
    panel_id: int = 1
    panel_bbox: Optional[Tuple[int, int, int, int]] = None
    interior_bbox: Optional[Tuple[int, int, int, int]] = None   # Interior content area within panel
    original_bbox: Optional[Tuple[int, int, int, int]] = None   # Bbox relative to full parent image
    is_empty: bool = False                                       # True if panel has no meaningful content
    structure_info: str = ""                                     # "STORYBOARD" or "SINGLE_SCENE"


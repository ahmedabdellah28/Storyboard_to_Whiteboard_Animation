"""
Canvas Viewport Controller — Pure Mathematics & Viewport State (Zoom & Pan).
"""

class ViewportController:
    def __init__(self):
        self.zoom_level: float = 1.0
        self.pan_offset_x: float = 0.0
        self.pan_offset_y: float = 0.0

    def adjust_zoom(self, factor: float):
        self.zoom_level = max(0.25, min(4.0, self.zoom_level * factor))

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0

    def pan(self, dx: float, dy: float):
        self.pan_offset_x += dx
        self.pan_offset_y += dy

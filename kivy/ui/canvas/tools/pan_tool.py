"""
Pan Viewport Tool — Smooth Drag-to-Pan across Canvas Viewport.
"""
from .base_tool import BaseCanvasTool


class PanTool(BaseCanvasTool):
    def __init__(self, canvas_view):
        super().__init__(canvas_view)
        self._is_dragging = False

    def on_touch_down(self, touch, img_pt) -> bool:
        self._is_dragging = False
        touch.grab(self.canvas_view)
        return True

    def on_touch_move(self, touch, img_pt) -> bool:
        if touch.grab_current is not self.canvas_view:
            return False

        self._is_dragging = True
        self.canvas_view.viewport.pan(touch.dx, touch.dy)
        self.canvas_view.redraw_overlays()
        return True

    def on_touch_up(self, touch, img_pt) -> bool:
        if touch.grab_current is not self.canvas_view:
            return False

        touch.ungrab(self.canvas_view)
        self._is_dragging = False
        self.canvas_view.redraw_overlays()
        return True

"""
Base Canvas Tool Interface.
All interaction tools (Select, AddBox, Pan, future Lasso/Pen) inherit from this class.
"""
from abc import ABC, abstractmethod


class BaseCanvasTool(ABC):
    def __init__(self, canvas_view):
        self.canvas_view = canvas_view

    @abstractmethod
    def on_touch_down(self, touch, img_pt) -> bool:
        pass

    @abstractmethod
    def on_touch_move(self, touch, img_pt) -> bool:
        pass

    @abstractmethod
    def on_touch_up(self, touch, img_pt) -> bool:
        pass

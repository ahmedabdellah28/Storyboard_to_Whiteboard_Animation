"""
Coordinate Transformer — Maps between Image Pixel Coordinates and Kivy Widget Screen Coordinates.
"""
from typing import Optional, Tuple


class CoordinateTransformer:
    @staticmethod
    def get_image_render_geometry(
        tex_w: float,
        tex_h: float,
        widget_pos: Tuple[float, float],
        widget_size: Tuple[float, float],
        zoom_level: float,
        pan_offset_x: float,
        pan_offset_y: float,
        source_image_shape: Optional[Tuple[int, int]] = None
    ) -> Optional[Tuple[float, float, float, float, float, float, float]]:
        """
        Returns (img_w, img_h, scale, off_x, off_y, disp_w, disp_h) or None.
        """
        if tex_w <= 0 or tex_h <= 0:
            return None

        if source_image_shape is not None:
            img_h = float(source_image_shape[0])
            img_w = float(source_image_shape[1])
        else:
            img_w = float(tex_w)
            img_h = float(tex_h)

        ww, wh = widget_size
        wx, wy = widget_pos

        base_scale = min(ww / max(1.0, img_w), wh / max(1.0, img_h))
        scale = base_scale * zoom_level
        disp_w = img_w * scale
        disp_h = img_h * scale

        off_x = wx + (ww - disp_w) / 2.0 + pan_offset_x
        off_y = wy + (wh - disp_h) / 2.0 + pan_offset_y

        return img_w, img_h, scale, off_x, off_y, disp_w, disp_h

    @staticmethod
    def widget_to_image_coords(
        wx: float,
        wy: float,
        geom: Optional[Tuple[float, float, float, float, float, float, float]]
    ) -> Optional[Tuple[float, float]]:
        if not geom:
            return None
        img_w, img_h, scale, off_x, off_y, disp_w, disp_h = geom

        if off_x <= wx <= off_x + disp_w and off_y <= wy <= off_y + disp_h:
            ix = (wx - off_x) / scale
            iy = img_h - (wy - off_y) / scale
            return max(0.0, min(img_w, ix)), max(0.0, min(img_h, iy))
        return None

    @staticmethod
    def image_to_widget_coords(
        bx: float,
        by: float,
        bw: float,
        bh: float,
        geom: Optional[Tuple[float, float, float, float, float, float, float]]
    ) -> Optional[Tuple[float, float, float, float]]:
        if not geom:
            return None
        img_w, img_h, scale, off_x, off_y, disp_w, disp_h = geom

        sx = off_x + bx * scale
        sy = off_y + (img_h - by - bh) * scale
        sw = max(2.0, bw * scale)
        sh = max(2.0, bh * scale)
        return sx, sy, sw, sh

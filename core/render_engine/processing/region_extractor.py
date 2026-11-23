import cv2
import numpy as np
from typing import List, Tuple
from ..core.region import ColorRegion, FillMode
from ..core.scene import SceneConfig


class RegionExtractor:
    """
    V3.1 Region Extractor.
    Extracts discrete color regions for spatial/timing analysis only.
    - Preserves micro-features down to 8px (highlights, glints, eye reflections, fine buttons)
    - Applies soft 2px morphological dilation so fills smoothly cover anti-aliasing under stroke outlines
    - Assigns intelligent geometry-aware FillMode
    - Note: extracted color is for clustering/sorting only; rendering strictly uses source_image pixels.
    """

    @staticmethod
    def extract(
        quantized_bgr: np.ndarray,
        palette: List[Tuple[int, int, int]],
        background_color: Tuple[int, int, int],
        config: SceneConfig
    ) -> List[ColorRegion]:
        h, w = quantized_bgr.shape[:2]
        regions: List[ColorRegion] = []
        
        # Micro-details preserved down to 8px
        min_area = max(8, config.min_region_area // 2 if config.min_region_area > 0 else 8)

        bg_array = np.array(background_color, dtype=np.float32)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

        for color_bgr in palette:
            color_arr = np.array(color_bgr, dtype=np.float32)
            is_bg_like = np.linalg.norm(color_arr - bg_array) < 18.0

            # Create binary mask for this cluster
            raw_mask = np.all(quantized_bgr == color_bgr, axis=2).astype(np.uint8) * 255
            if cv2.countNonZero(raw_mask) < min_area:
                continue

            # Connected components
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(raw_mask, connectivity=8)

            for label in range(1, num_labels):
                area = stats[label, cv2.CC_STAT_AREA]
                if area < min_area:
                    continue

                bx = int(stats[label, cv2.CC_STAT_LEFT])
                by = int(stats[label, cv2.CC_STAT_TOP])
                bw = int(stats[label, cv2.CC_STAT_WIDTH])
                bh = int(stats[label, cv2.CC_STAT_HEIGHT])
                cx, cy = centroids[label]

                # Robust outer canvas background check:
                # Must be color-similar AND touch at least 3 perimeter borders AND occupy massive area (>35% of total canvas)
                touches_top = (by <= 2)
                touches_bottom = (by + bh >= h - 2)
                touches_left = (bx <= 2)
                touches_right = (bx + bw >= w - 2)
                edge_touches = sum([touches_top, touches_bottom, touches_left, touches_right])

                if is_bg_like and edge_touches >= 3 and area > 0.35 * (w * h):
                    continue

                # Create binary mask for this component
                comp_mask = cv2.compare(labels, label, cv2.CMP_EQ)
                
                # Soft dilation (2 iterations of 3x3 ellipse) so color coverage seamlessly extends under
                # stroke outlines and captures subtle edge anti-aliasing without white gaps
                dilated_comp_mask = cv2.dilate(comp_mask, kernel, iterations=2)

                # Determine Fill Mode based on geometry
                fill_mode = RegionExtractor._determine_fill_mode(bw, bh, area)

                region = ColorRegion(
                    color=color_bgr,
                    mask=dilated_comp_mask,
                    bbox=(bx, by, bw, bh),
                    area=int(area),
                    center=np.array([cx, cy], dtype=np.float64),
                    fill_mode=fill_mode
                )
                regions.append(region)

        # Sort largest background/body fills first, smallest detail fills last
        regions.sort(key=lambda r: r.area, reverse=True)
        return regions

    @staticmethod
    def _determine_fill_mode(bw: int, bh: int, area: int) -> FillMode:
        aspect = bw / float(max(1, bh))
        if aspect < 0.5:  # Tall vertical element (Legs, Torso, Arms)
            return FillMode.TOP_TO_BOTTOM
        elif aspect > 2.0:  # Wide horizontal element
            return FillMode.LEFT_TO_RIGHT
        elif area > 10000:  # Large block
            return FillMode.CENTER_OUT
        else:  # Details, faces, icons, shield
            return FillMode.FOLLOW_OUTLINE

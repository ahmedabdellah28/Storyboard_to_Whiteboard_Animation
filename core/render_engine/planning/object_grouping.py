import cv2
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from ..core.stroke import Stroke, StrokeType
from ..core.region import ColorRegion
from ..core.scene import SceneObject, SceneConfig


class MajorObjectGrouper:
    @staticmethod
    def is_box_or_frame_stroke(s: Stroke, scene_w: int, scene_h: int) -> bool:
        if getattr(s, "stroke_type", None) == StrokeType.FRAME_STROKE or getattr(s, "is_frame", False):
            return True
        bx, by, bw, bh = s.bbox
        # True outer full-canvas border frame (must cover > 85% of width/height or align with margins)
        if (bw >= 0.85 * scene_w and bh >= 0.85 * scene_h):
            return True
        if bx <= 20 and by <= 20 and (bx + bw >= scene_w - 20) and (by + bh >= scene_h - 20):
            return True
        return False

    @staticmethod
    def group_into_major_objects(
        strokes: List[Stroke],
        regions: List[ColorRegion],
        scene_w: int,
        scene_h: int,
        config: SceneConfig
    ) -> List[SceneObject]:
        """
        Groups strokes and color regions into coherent Major SceneObjects:
        1. Separates outer canvas border frame & inner rectangular panel box frames
        2. Filters out giant canvas backdrops & panel white backdrops
        3. Rasterizes foreground occupancy map focused exclusively on the characters
        4. Discovers discrete Character objects and tightly computes bounding boxes
        5. Absorbs effects, icons, and minor details into the parent character
        """
        if not strokes and not regions:
            return []

        # Step 1: Separate frame/box strokes from character strokes
        frame_strokes = []
        regular_strokes = []
        for s in strokes:
            if MajorObjectGrouper.is_box_or_frame_stroke(s, scene_w, scene_h):
                frame_strokes.append(s)
            else:
                regular_strokes.append(s)

        # Step 2: Filter out giant scene backdrops and panel white backdrops
        # V3: All thresholds are RELATIVE to panel/scene dimensions
        scene_area = scene_w * scene_h
        filtered_regions = []
        backdrop_regions = []
        for r in regions:
            bx, by, bw, bh = r.bbox
            is_giant = (bw > 0.80 * scene_w and bh > 0.80 * scene_h) or r.area > 0.40 * scene_area
            # Sliver: very thin strip near top/bottom edge (relative thresholds)
            edge_margin = max(10, int(scene_h * 0.06))
            sliver_height = max(4, int(scene_h * 0.015))
            sliver_width = max(20, int(scene_w * 0.10))
            is_border_sliver = ((by <= edge_margin and bh <= sliver_height and bw > sliver_width) or
                                (by + bh >= scene_h - edge_margin and bh <= sliver_height and bw > sliver_width))
            if is_giant or is_border_sliver:
                backdrop_regions.append(r)
            else:
                filtered_regions.append(r)

        # Step 3: Build native-resolution foreground occupancy map (characters only)
        occupancy = np.zeros((scene_h, scene_w), dtype=np.uint8)

        for s in regular_strokes:
            if len(s.points) >= 2:
                pts = s.points.astype(np.int32)
                cv2.polylines(occupancy, [pts], False, 255, 3)

        for r in filtered_regions:
            if r.mask is not None and r.area > 0:
                occupancy = cv2.bitwise_or(occupancy, r.mask)

        # Step 4: Morphological closing with adaptive kernel to connect related body/object parts
        fuse_k_size = max(9, int(round(min(scene_w, scene_h) * 0.015)) | 1)
        fuse_k = cv2.getStructuringElement(cv2.MORPH_RECT, (fuse_k_size, fuse_k_size))
        dilated = cv2.morphologyEx(occupancy, cv2.MORPH_CLOSE, fuse_k)

        # Step 5: Connected Components Analysis
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(dilated, connectivity=8)

        major_clusters: Dict[int, Dict[str, Any]] = {}
        # V3: min_cluster_area is RELATIVE to scene dimensions (0.2% of scene area)
        min_cluster_area = max(100, int(0.002 * (scene_w * scene_h)))

        for label in range(1, num_labels):
            area = stats[label, cv2.CC_STAT_AREA]
            if area < min_cluster_area:
                continue

            bx = int(stats[label, cv2.CC_STAT_LEFT])
            by = int(stats[label, cv2.CC_STAT_TOP])
            bw = int(stats[label, cv2.CC_STAT_WIDTH])
            bh = int(stats[label, cv2.CC_STAT_HEIGHT])
            cx = float(centroids[label][0])
            cy = float(centroids[label][1])

            # Skip narrow border slivers (relative thresholds)
            sliver_margin = max(10, int(scene_h * 0.05))
            sliver_max_h = max(4, int(scene_h * 0.015))
            if (by <= sliver_margin and bh <= sliver_max_h) or (by + bh >= scene_h - sliver_margin and bh <= sliver_max_h):
                continue

            major_clusters[label] = {
                'bbox': (bx, by, bw, bh),
                'center': np.array([cx, cy], dtype=np.float64),
                'strokes': [],
                'details': [],
                'fills': [],
                'area': area
            }

        # Step 6: Assign strokes to character clusters
        unassigned_strokes = []
        for s in regular_strokes:
            cx = int(np.clip(s.center[0], 0, scene_w - 1))
            cy = int(np.clip(s.center[1], 0, scene_h - 1))
            assigned_label = labels[cy, cx]

            if assigned_label in major_clusters:
                if s.stroke_type == StrokeType.MICRO_DETAIL:
                    major_clusters[assigned_label]['details'].append(s)
                else:
                    major_clusters[assigned_label]['strokes'].append(s)
            else:
                # V3: max_dist is relative to scene diagonal
                max_assign_dist = max(30.0, float(np.sqrt(scene_w**2 + scene_h**2)) * 0.10)
                best_label = MajorObjectGrouper._find_closest_cluster(s.center, major_clusters, max_dist=max_assign_dist)
                if best_label is not None:
                    if s.stroke_type == StrokeType.MICRO_DETAIL:
                        major_clusters[best_label]['details'].append(s)
                    else:
                        major_clusters[best_label]['strokes'].append(s)
                else:
                    unassigned_strokes.append(s)

        # Step 7: Assign color regions to character clusters
        unassigned_regions = []
        for r in filtered_regions:
            cx = int(np.clip(r.center[0], 0, scene_w - 1))
            cy = int(np.clip(r.center[1], 0, scene_h - 1))
            assigned_label = labels[cy, cx]

            if assigned_label in major_clusters:
                major_clusters[assigned_label]['fills'].append(r)
            else:
                max_assign_dist = max(30.0, float(np.sqrt(scene_w**2 + scene_h**2)) * 0.10)
                best_label = MajorObjectGrouper._find_closest_cluster(r.center, major_clusters, max_dist=max_assign_dist)
                if best_label is not None:
                    major_clusters[best_label]['fills'].append(r)
                else:
                    unassigned_regions.append(r)

        # Step 8: Build Coherent Major Objects & Absorb satellite fragments (arms, glow, props, text)
        raw_objects: List[SceneObject] = []
        for idx, (label, data) in enumerate(major_clusters.items()):
            # Filter out empty clusters that have no strokes and no fills
            if not data['strokes'] and not data['fills'] and not data['details']:
                continue
            obj = SceneObject(
                name=f"Object_{len(raw_objects) + 1}",
                strokes=data['strokes'],
                details=data['details'],
                fills=data['fills']
            )
            obj.compute_bounds_and_importance(scene_w, scene_h)
            raw_objects.append(obj)

        # Merge secondary effects / detached fragments into the closest primary object
        # V3: primary object threshold is relative to scene area
        primary_area_threshold = max(200, int(scene_w * scene_h * 0.005))
        primary_objects = [o for o in raw_objects if o.area >= primary_area_threshold or (len(o.strokes) + len(o.details)) >= 10]
        sub_elements = [o for o in raw_objects if o not in primary_objects]

        # V3: proximity limit is relative to scene diagonal
        proximity_limit = max(30.0, float(np.sqrt(scene_w**2 + scene_h**2)) * 0.12)

        if primary_objects:
            for p in primary_objects:
                px, py, pw, ph = p.bbox
                for s in list(sub_elements):
                    # Proximity / Enclosure check
                    dist_x = max(0, max(px - s.center[0], s.center[0] - (px + pw)))
                    dist_y = max(0, max(py - s.center[1], s.center[1] - (py + ph)))
                    dist = float(np.sqrt(dist_x * dist_x + dist_y * dist_y))
                    
                    if dist <= proximity_limit:
                        p.strokes.extend(s.strokes)
                        p.details.extend(s.details)
                        p.fills.extend(s.fills)
                        sub_elements.remove(s)
                p.compute_bounds_and_importance(scene_w, scene_h)
            final_objects = list(primary_objects)
            final_objects.extend(sub_elements)
        else:
            final_objects = raw_objects

        # Rename objects cleanly
        for i, obj in enumerate(final_objects):
            obj.name = f"Object_{i + 1}"

        # Handle unassigned leftovers (details / fine lines)
        if unassigned_strokes or unassigned_regions:
            leftover_obj = SceneObject(
                name="Scene_Details",
                strokes=[s for s in unassigned_strokes if s.stroke_type != StrokeType.MICRO_DETAIL],
                details=[s for s in unassigned_strokes if s.stroke_type == StrokeType.MICRO_DETAIL],
                fills=unassigned_regions
            )
            leftover_obj.compute_bounds_and_importance(scene_w, scene_h)
            if leftover_obj.strokes or leftover_obj.fills or leftover_obj.details:
                final_objects.append(leftover_obj)

        # Diagnostic logging matching architectural specifications
        char_count = sum(1 for o in final_objects if not o.is_frame and o.name.startswith("Object") or o.name.startswith("Character"))
        prop_count = sum(1 for o in final_objects if not o.is_frame and not o.name.startswith("Object") and not o.name.startswith("Character") and o.name != "Scene_Details")
        detail_count = sum(len(o.details) for o in final_objects)
        frame_stroke_count = len(frame_strokes)

        print("==================================================")
        print("OBJECT DETECTION")
        print("----------------")
        print(f"object_count: {len(final_objects)}")
        print(f"character_count: {char_count}")
        print(f"prop_count: {prop_count}")
        print(f"detail_count: {detail_count}")
        print(f"frame_stroke_count: {frame_stroke_count}")
        print("==================================================")

        return final_objects

    @staticmethod
    def _find_closest_cluster(center: np.ndarray, clusters: Dict[int, Dict[str, Any]], max_dist: float = 90.0) -> Optional[int]:
        best_label = None
        min_d = max_dist
        for label, data in clusters.items():
            bx, by, bw, bh = data['bbox']
            dx = max(0, max(bx - center[0], center[0] - (bx + bw)))
            dy = max(0, max(by - center[1], center[1] - (by + bh)))
            d = float(np.sqrt(dx*dx + dy*dy))
            if d < min_d:
                min_d = d
                best_label = label
        return best_label

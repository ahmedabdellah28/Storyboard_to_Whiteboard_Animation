import numpy as np
from typing import List, Tuple
from ..core.scene import Scene, SceneObject
from ..core.stroke import Stroke, StrokeType
from ..core.region import ColorRegion
from ..core.timeline import Timeline, StrokeEvent, FillEvent


class DrawingOrder:
    @staticmethod
    def build_timeline(scene: Scene) -> Timeline:
        """
        Constructs a complete temporal Timeline with sequenced StrokeEvents and FillEvents:
        1. Sequences SceneObjects using the configured drawing_order mode
        2. Within each SceneObject, orders: Outer Outline -> Internal Details -> Color Boundaries -> Fills -> Micro Details
        3. Allocates natural durations proportional to length and area
        4. Inserts brief object transitions and final hold
        """
        config = scene.config
        objects = list(scene.objects)
        if not objects:
            return Timeline(duration=config.end_hold_seconds)

        # Step 1: Sequence SceneObjects
        ordered_objects = DrawingOrder._sequence_objects(objects, config.drawing_order, scene.canvas_width, scene.canvas_height)

        stroke_events: List[StrokeEvent] = []
        fill_events: List[FillEvent] = []
        current_time = 0.5  # Brief initial canvas establishing pause (0.5s)

        # Drawing speeds (pixels per second)
        stroke_speed = 700.0   # Drawing stroke speed
        fill_speed_factor = 45.0 # Speed factor for progressive flood fills

        for obj_idx, obj in enumerate(ordered_objects):
            # Sort internal strokes by category
            outlines = [s for s in obj.strokes if s.stroke_type == StrokeType.OUTER_OUTLINE]
            internals = [s for s in obj.strokes if s.stroke_type == StrokeType.INTERNAL_DETAIL]
            color_bounds = [s for s in obj.strokes if s.stroke_type == StrokeType.COLOR_BOUNDARY]
            micro_details = list(obj.details)

            # Sort outlines descending by length
            outlines.sort(key=lambda s: s.length, reverse=True)
            # Sort internals from top to bottom
            internals.sort(key=lambda s: s.center[1])
            # Sort fills from largest to smallest
            sorted_fills = sorted(obj.fills, key=lambda f: f.area, reverse=True)

            # Phase A: Draw Outlines
            for s in outlines:
                dur = max(0.18, min(1.8, s.length / stroke_speed))
                stroke_events.append(StrokeEvent(
                    start_time=current_time,
                    end_time=current_time + dur,
                    stroke=s,
                    easing="ease_in_out"
                ))
                current_time += dur * 0.85  # Slight overlap for fluid sketch feeling

            # Phase B: Draw Internal Details
            for s in internals:
                dur = max(0.12, min(1.2, s.length / stroke_speed))
                stroke_events.append(StrokeEvent(
                    start_time=current_time,
                    end_time=current_time + dur,
                    stroke=s,
                    easing="ease_out"
                ))
                current_time += dur * 0.80

            # Phase C: Draw Color Boundary lines
            for s in color_bounds:
                dur = max(0.10, min(0.9, s.length / stroke_speed))
                stroke_events.append(StrokeEvent(
                    start_time=current_time,
                    end_time=current_time + dur,
                    stroke=s,
                    easing="ease_out"
                ))
                current_time += dur * 0.75

            # Phase D: Progressive Color Fills
            for f in sorted_fills:
                # Duration proportional to sqrt(area)
                eff_len = float(np.sqrt(f.area))
                dur = max(0.25, min(1.4, eff_len / fill_speed_factor))
                fill_events.append(FillEvent(
                    start_time=current_time,
                    end_time=current_time + dur,
                    region=f,
                    easing="ease_in_out"
                ))
                current_time += dur * 0.80

            # Phase E: Micro Details (hatching/texture on top)
            for s in micro_details:
                dur = max(0.08, min(0.6, s.length / stroke_speed))
                stroke_events.append(StrokeEvent(
                    start_time=current_time,
                    end_time=current_time + dur,
                    stroke=s,
                    easing="linear"
                ))
                current_time += dur * 0.60

            # Brief transition pause to next object
            if obj_idx < len(ordered_objects) - 1:
                current_time += 0.35

        # Add final holding duration
        total_duration = current_time + config.end_hold_seconds

        timeline = Timeline(
            duration=total_duration,
            stroke_events=stroke_events,
            fill_events=fill_events,
            camera_shots=[]
        )
        return timeline

    @staticmethod
    def _sequence_objects(
        objects: List[SceneObject],
        mode: str,
        canvas_w: int,
        canvas_h: int
    ) -> List[SceneObject]:
        mode = str(mode).upper()

        if mode == "TOP_TO_BOTTOM":
            return sorted(objects, key=lambda o: o.center[1])
        elif mode == "LEFT_TO_RIGHT":
            return sorted(objects, key=lambda o: o.center[0])
        elif mode == "CENTER_OUT":
            center = np.array([canvas_w / 2.0, canvas_h / 2.0])
            return sorted(objects, key=lambda o: np.linalg.norm(o.center - center))
        elif mode == "SPATIAL":
            # Greedy nearest neighbor trajectory
            remaining = list(objects)
            ordered = []
            curr_pos = np.array([canvas_w / 2.0, canvas_h / 4.0])
            while remaining:
                nearest_idx = int(np.argmin([np.linalg.norm(o.center - curr_pos) for o in remaining]))
                chosen = remaining.pop(nearest_idx)
                ordered.append(chosen)
                curr_pos = chosen.center
            return ordered
        else:  # AUTO (Default)
            # Sequence: Separate background frame, then top-level high-importance objects in top-to-bottom spatial order
            frame_objs = [o for o in objects if o.bbox[2] > 0.85 * canvas_w and o.bbox[3] > 0.85 * canvas_h]
            content_objs = [o for o in objects if o not in frame_objs]

            # Content objects sorted primarily from top to bottom (y) then importance
            content_objs.sort(key=lambda o: (round(o.center[1] / 150.0), -o.importance))

            # Frame object draws first (or last)
            return frame_objs + content_objs

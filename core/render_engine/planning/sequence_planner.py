import numpy as np
from typing import List, Tuple
from ..core.scene import Scene, SceneObject, SceneConfig
from ..core.stroke import Stroke, StrokeType
from ..core.region import ColorRegion
from ..core.timeline import Timeline, StrokeEvent, FillEvent


class SequencePlanner:
    @staticmethod
    def plan_sequence_and_timeline(
        scene: Scene,
        major_objects: List[SceneObject],
        config: SceneConfig
    ) -> Tuple[List[SceneObject], Timeline]:
        """
        Plans the narrative drawing sequence and constructs a strictly partitioned Timeline:
        - Filters out frame/box strokes from character animation
        - Sequentially focuses and draws each character (Outlines -> Internals -> Fills -> Details)
        - Transitions smoothly between characters
        - Concludes with full composition hold
        """
        # Step 1: Filter and classify objects
        frame_objs = [o for o in major_objects if o.is_frame]
        non_frame_objs = [o for o in major_objects if not o.is_frame]

        primary_objs = [o for o in non_frame_objs if o.area >= 2000 or len(o.strokes) > 5]
        minor_objs = [o for o in non_frame_objs if o not in primary_objs]

        # Order primary objects in visual reading order (Row by row, Left to Right)
        ordered_primary = SequencePlanner._order_objects(
            primary_objs, config.drawing_order, scene.canvas_width, scene.canvas_height
        )

        # Clean semantic names
        is_multi_panel = len(ordered_primary) >= 4
        for idx, obj in enumerate(ordered_primary):
            if is_multi_panel:
                obj.name = f"Character_{idx+1}"
            elif "Lock" in obj.name or (obj.center[1] < 400 and len(ordered_primary) == 2):
                obj.name = "Lock"
            elif "Character" in obj.name or (obj.center[1] >= 400 and len(ordered_primary) == 2):
                obj.name = "Character"
            else:
                obj.name = f"Object_{idx+1}"

        stroke_events: List[StrokeEvent] = []
        fill_events: List[FillEvent] = []

        # 1. Establishing phase (0.0 -> establishing_duration)
        est_dur = float(config.establishing_duration)
        current_time = est_dur + float(config.transition_duration)

        # Step 2: Schedule each Major Character's complete animation strictly sequentially
        for obj_idx, obj in enumerate(ordered_primary):
            obj_start_time = current_time

            # Order strokes by geometric proximity for smooth continuous drawing flow (exclude FRAME_STROKE)
            valid_strokes = [s for s in obj.strokes if not getattr(s, "is_frame", False) and s.stroke_type != StrokeType.FRAME_STROKE]
            outlines = SequencePlanner.order_strokes_by_proximity([s for s in valid_strokes if s.stroke_type == StrokeType.OUTER_OUTLINE])
            internals = SequencePlanner.order_strokes_by_proximity([s for s in valid_strokes if s.stroke_type == StrokeType.INTERNAL_DETAIL])
            color_bounds = SequencePlanner.order_strokes_by_proximity([s for s in valid_strokes if s.stroke_type == StrokeType.COLOR_BOUNDARY])
            combined_internals = internals + color_bounds
            micro_details = SequencePlanner.order_strokes_by_proximity([s for s in obj.details if not getattr(s, "is_frame", False) and s.stroke_type != StrokeType.FRAME_STROKE])
            fills = sorted(obj.fills, key=lambda f: f.area, reverse=True)

            # Target character duration budget (3.2s to 4.8s per character at 1.0x speed)
            total_stroke_len = sum(s.length for s in outlines + combined_internals + micro_details)
            total_fill_area = sum(f.area for f in fills)
            char_budget = (3.2 + min(1.6, (total_stroke_len * 0.0003) + (np.sqrt(total_fill_area) * 0.002))) / max(0.2, config.drawing_speed)

            # Phase shares
            w_out = 0.35 if outlines else 0.0
            w_int = 0.20 if combined_internals else 0.0
            w_fill = 0.35 if fills else 0.0
            w_micro = 0.10 if micro_details else 0.0
            total_w = max(1e-4, w_out + w_int + w_fill + w_micro)

            t_out_budget = char_budget * (w_out / total_w)
            t_int_budget = char_budget * (w_int / total_w)
            t_fill_budget = char_budget * (w_fill / total_w)
            t_micro_budget = char_budget * (w_micro / total_w)

            cur_t = obj_start_time

            # ── 1. Outlines of this Character ──
            if outlines:
                tot_l = max(1.0, sum(s.length for s in outlines))
                for s in outlines:
                    s_dur = t_out_budget * (s.length / tot_l)
                    stroke_events.append(StrokeEvent(cur_t, cur_t + s_dur, s, "ease_in_out"))
                    cur_t += s_dur

            # ── 2. Internals & Boundaries of this Character ──
            if combined_internals:
                tot_l = max(1.0, sum(s.length for s in combined_internals))
                for s in combined_internals:
                    s_dur = t_int_budget * (s.length / tot_l)
                    stroke_events.append(StrokeEvent(cur_t, cur_t + s_dur, s, "ease_out"))
                    cur_t += s_dur

            # ── 3. Color Fills of this Character (Drawn after outlines and internals are complete) ──
            if fills:
                tot_a = max(1.0, sum(np.sqrt(f.area) for f in fills))
                for f in fills:
                    f_dur = t_fill_budget * (np.sqrt(f.area) / tot_a)
                    fill_events.append(FillEvent(cur_t, cur_t + f_dur, f, "ease_in_out"))
                    cur_t += f_dur

            # ── 4. Micro Details of this Character (Eyes, expressions, fine lines) ──
            if micro_details:
                tot_l = max(1.0, sum(s.length for s in micro_details))
                for s in micro_details:
                    s_dur = t_micro_budget * (s.length / tot_l)
                    stroke_events.append(StrokeEvent(cur_t, cur_t + s_dur, s, "linear"))
                    cur_t += s_dur

            # Character is now 100% finished!
            obj.animation_start = obj_start_time
            obj.animation_end = cur_t
            obj.duration = cur_t - obj_start_time

            current_time = cur_t

            # ── 5. Transition to next Character ONLY AFTER current character is 100% done ──
            if obj_idx < len(ordered_primary) - 1:
                current_time += max(0.5, float(config.transition_duration) * 0.7)

        # Final transition to wide view + final composition hold
        final_transition_start = current_time
        final_transition_end = final_transition_start + float(config.transition_duration)
        total_duration = final_transition_end + float(config.end_hold_seconds)

        timeline = Timeline(
            duration=total_duration,
            stroke_events=stroke_events,
            fill_events=fill_events,
            camera_shots=[]
        )

        all_ordered = ordered_primary + minor_objs + frame_objs
        return all_ordered, timeline

    @staticmethod
    def _order_objects(
        objects: List[SceneObject],
        mode: str,
        canvas_w: int,
        canvas_h: int
    ) -> List[SceneObject]:
        mode = str(mode).upper()
        if mode == "LEFT_TO_RIGHT":
            return sorted(objects, key=lambda o: o.center[0])
        elif mode == "CENTER_OUT":
            center = np.array([canvas_w / 2.0, canvas_h / 2.0])
            return sorted(objects, key=lambda o: np.linalg.norm(o.center - center))
        else:  # AUTO / 2D Smart Flow
            if len(objects) <= 1:
                return objects

            import functools

            def compare_scene_objects(a, b):
                ab = a.global_bbox or a.bbox or (0, 0, 0, 0)
                bb = b.global_bbox or b.bbox or (0, 0, 0, 0)
                ax, ay, aw, ah = ab
                bx, by, bw, bh = bb

                # تداخل المحور الأفقي X
                x_overlap = max(0, min(ax + aw, bx + bw) - max(ax, bx))
                min_w = max(1, min(aw, bw))
                x_overlap_ratio = x_overlap / float(min_w)

                # تداخل المحور الرأسي Y
                y_overlap = max(0, min(ay + ah, by + bh) - max(ay, by))
                min_h = max(1, min(ah, bh))
                y_overlap_ratio = y_overlap / float(min_h)

                # 1. عناصر عمودية مكدسة فوق بعضها -> الأعلى يسبق الأسفل
                if x_overlap_ratio > 0.30 and y_overlap_ratio < 0.40:
                    return -1 if ay < by else 1

                # 2. عناصر أفقية متجاورة -> اليسار يسبق اليمين دائماً
                if y_overlap_ratio > 0.30 and x_overlap_ratio < 0.40:
                    return -1 if ax < bx else 1

                # 3. ترتيب شبكي عام
                if (ay + ah * 0.5) + (min_h * 0.5) < (by + bh * 0.5):
                    return -1
                elif (by + bh * 0.5) + (min_h * 0.5) < (ay + ah * 0.5):
                    return 1
                else:
                    return -1 if ax < bx else 1

            return sorted(objects, key=functools.cmp_to_key(compare_scene_objects))

    @staticmethod
    def order_strokes_by_proximity(strokes: List[Stroke]) -> List[Stroke]:
        """
        Orders strokes using a continuous nearest-neighbor path search so the hand
        flows smoothly from line to line without chaotic jumping across the character.
        """
        valid = [s for s in strokes if len(s.points) >= 2]
        if len(valid) <= 1:
            return valid

        remaining = list(valid)
        # Start with the highest (top-most) stroke
        remaining.sort(key=lambda s: float(np.min(s.points[:, 1])))
        ordered = [remaining.pop(0)]

        while remaining:
            curr_end = ordered[-1].points[-1].astype(np.float64)
            best_idx = 0
            best_dist = float("inf")
            flip = False

            for idx, s in enumerate(remaining):
                p_start = s.points[0].astype(np.float64)
                p_end = s.points[-1].astype(np.float64)
                d_start = float(np.linalg.norm(p_start - curr_end))
                d_end = float(np.linalg.norm(p_end - curr_end))

                if d_start < best_dist:
                    best_dist = d_start
                    best_idx = idx
                    flip = False
                if d_end < best_dist:
                    best_dist = d_end
                    best_idx = idx
                    flip = True

            next_s = remaining.pop(best_idx)
            if flip:
                # Reverse stroke points so the pen connects seamlessly
                next_s = Stroke(
                    points=next_s.points[::-1].copy(),
                    stroke_type=next_s.stroke_type,
                    color=next_s.color,
                    width=next_s.width,
                    is_closed=next_s.is_closed
                )
            ordered.append(next_s)

        return ordered

import numpy as np
from typing import List, Tuple
from ..core.scene import Scene, SceneObject, SceneConfig
from ..core.timeline import Timeline, CameraShot


class ShotPlanner:
    @staticmethod
    def plan_shots(
        scene: Scene,
        ordered_objects: List[SceneObject],
        timeline: Timeline,
        config: SceneConfig
    ) -> List[CameraShot]:
        """
        Director's Camera Shot Planner:
        Generates a clean sequence of distinct cinematic CameraShots:
        1. ESTABLISHING: Full scene wide view (0.0 -> 0.7s)
        2. For each Major Object:
           - TRANSITION: Smooth Ease-In-Out pan & zoom from previous shot to object
           - OBJECT_FOCUS: 100% Rock-solid static framing on the object during its drawing
        3. FINAL_TRANSITION: Smooth zoom-out back to full scene
        4. FINAL_WIDE_HOLD: Static presentation of the complete final composition
        """
        scene_w = scene.canvas_width
        scene_h = scene.canvas_height
        full_center = np.array([scene_w / 2.0, scene_h / 2.0], dtype=np.float64)

        shots: List[CameraShot] = []

        # Filter primary focal content objects (major characters and props only, excluding minor number indicators)
        focal_objects = [
            o for o in ordered_objects
            if not o.is_frame and o.animation_start >= (config.establishing_duration - 1e-4)
            and o.duration >= 1.0 and o.area >= 10000 and (len(o.strokes) + len(o.details)) >= 8
        ]

        if config.camera_preset == "STATIC" or not focal_objects:
            shots.append(CameraShot(
                start_time=0.0,
                end_time=timeline.duration,
                target_bbox=(0, 0, scene_w, scene_h),
                target_center=full_center,
                zoom=1.0,
                shot_name="STATIC_FULL_SCENE"
            ))
            return shots

        # 1. Establishing Shot
        shots.append(CameraShot(
            start_time=0.0,
            end_time=config.establishing_duration,
            target_bbox=(0, 0, scene_w, scene_h),
            target_center=full_center,
            zoom=1.0,
            shot_name="01_ESTABLISHING_WIDE"
        ))

        # 2. Sequential Object Focus & Multi-Phase Storyteller Transitions
        for idx, obj in enumerate(focal_objects):
            target_cx, target_cy, target_zoom = ShotPlanner.calculate_auto_frame(
                obj, scene_w, scene_h, config.camera_intensity
            )
            target_center = np.array([target_cx, target_cy], dtype=np.float64)

            if idx == 0:
                # Transition Shot to First Object (Zoom In)
                shots.append(CameraShot(
                    start_time=config.establishing_duration,
                    end_time=obj.animation_start,
                    target_bbox=obj.bbox,
                    target_center=target_center,
                    zoom=target_zoom,
                    easing="ease_in_out",
                    shot_name=f"TRANSITION_ZOOM_IN_{obj.name}"
                ))
            else:
                prev_obj = focal_objects[idx - 1]
                t_inter_start = prev_obj.animation_end
                t_inter_end = obj.animation_start
                total_inter = max(0.6, t_inter_end - t_inter_start)

                # Phase 1: Zoom Out / Reveal the finished previous character
                t_reveal_end = t_inter_start + (total_inter * 0.35)
                shots.append(CameraShot(
                    start_time=t_inter_start,
                    end_time=t_reveal_end,
                    target_bbox=(0, 0, scene_w, scene_h),
                    target_center=full_center,
                    zoom=1.0,
                    easing="ease_in_out",
                    shot_name=f"ZOOM_OUT_REVEAL_{prev_obj.name}"
                ))

                # Phase 2: Pan across the canvas to the empty area of the next character
                t_pan_end = t_inter_start + (total_inter * 0.70)
                shots.append(CameraShot(
                    start_time=t_reveal_end,
                    end_time=t_pan_end,
                    target_bbox=(int(target_cx - (scene_w / 2)), int(target_cy - (scene_h / 2)), scene_w, scene_h),
                    target_center=target_center,
                    zoom=1.0,
                    easing="ease_in_out",
                    shot_name=f"PAN_TO_EMPTY_AREA_{obj.name}"
                ))

                # Phase 3: Zoom In onto the new character to begin drawing
                shots.append(CameraShot(
                    start_time=t_pan_end,
                    end_time=obj.animation_start,
                    target_bbox=obj.bbox,
                    target_center=target_center,
                    zoom=target_zoom,
                    easing="ease_in_out",
                    shot_name=f"ZOOM_IN_ON_{obj.name}"
                ))

            # Focus Shot on this Major Object (Rock-solid static during drawing)
            shots.append(CameraShot(
                start_time=obj.animation_start,
                end_time=obj.animation_end,
                target_bbox=obj.bbox,
                target_center=target_center,
                zoom=target_zoom,
                easing="linear",
                shot_name=f"FOCUS_{obj.name}"
            ))

        # 3. Final Zoom Out / Reveal to Wide View
        last_obj_end = focal_objects[-1].animation_end
        final_trans_end = last_obj_end + max(0.8, float(config.transition_duration))
        shots.append(CameraShot(
            start_time=last_obj_end,
            end_time=final_trans_end,
            target_bbox=(0, 0, scene_w, scene_h),
            target_center=full_center,
            zoom=1.0,
            easing="ease_in_out",
            shot_name="FINAL_ZOOM_OUT_WIDE"
        ))

        # 4. Final Wide Hold
        shots.append(CameraShot(
            start_time=final_trans_end,
            end_time=timeline.duration,
            target_bbox=(0, 0, scene_w, scene_h),
            target_center=full_center,
            zoom=1.0,
            shot_name="FINAL_WIDE_HOLD"
        ))

        return shots

    @staticmethod
    def calculate_auto_frame(
        obj: SceneObject,
        scene_w: int,
        scene_h: int,
        intensity: float = 0.65
    ) -> Tuple[float, float, float]:
        """
        Calculates optimal camera center (cx, cy) and zoom with safe margins:
        - Incorporates 35% comfortable breathing room around object
        - Subtle, natural zoom (1.05x to 1.35x max) to preserve pristine sharpness
        - Clamps viewport cleanly to avoid blurry pixelation
        """
        bx, by, bw, bh = obj.bbox
        margin_pct = 0.35  # 35% safe breathing room

        fit_w = bw * (1.0 + 2.0 * margin_pct)
        fit_h = bh * (1.0 + 2.0 * margin_pct)

        zoom_x = scene_w / max(10.0, float(fit_w))
        zoom_y = scene_h / max(10.0, float(fit_h))
        base_zoom = min(zoom_x, zoom_y)

        # V3: Scale by camera intensity — subtle zoom between 1.0 and 1.05
        # Panel is the primary composition frame
        zoom = 1.0 + (base_zoom - 1.0) * (intensity * 0.25)
        clamped_zoom = max(1.0, min(1.05, float(zoom)))

        # Viewport dimensions on canvas
        vp_w = scene_w / clamped_zoom
        vp_h = scene_h / clamped_zoom

        # Clamp center to ensure the camera never leaves canvas boundary
        min_x = vp_w / 2.0
        max_x = scene_w - vp_w / 2.0
        min_y = vp_h / 2.0
        max_y = scene_h - vp_h / 2.0

        raw_cx, raw_cy = obj.center[0], obj.center[1]
        cx = max(min_x, min(max_x, raw_cx)) if max_x >= min_x else (scene_w / 2.0)
        cy = max(min_y, min(max_y, raw_cy)) if max_y >= min_y else (scene_h / 2.0)

        return float(cx), float(cy), float(clamped_zoom)

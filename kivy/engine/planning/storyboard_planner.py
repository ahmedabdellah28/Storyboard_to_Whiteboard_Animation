import cv2
import numpy as np
from typing import List, Tuple, Optional
from ..core.stroke import Stroke, StrokeType
from ..core.region import ColorRegion
from ..core.scene import Scene, SceneObject, SceneConfig
from ..core.timeline import Timeline, StrokeEvent, FillEvent, CameraShot
from ..core.project import Project, PanelStructure, StructureType
from .sequence_planner import SequencePlanner


class StoryboardPlanner:
    """
    Constructs a unified Master Storyboard Scene and seamless storytelling timeline.
    The camera navigates across the unified storyboard canvas:
    Panel 1 -> Panel 2 -> Panel 3 -> Panel 4 -> Panel 5 -> Panel 6 -> Master Reveal.
    """

    @staticmethod
    def build_master_storyboard_scene(
        project: Project,
        config: SceneConfig
    ) -> Tuple[Scene, Timeline, List[CameraShot]]:
        """
        Builds the unified master scene where all panels exist in their true global positions.
        """
        src_img = project.source_image
        if src_img is None:
            raise ValueError("Project source image is missing.")
            
        master_h, master_w = src_img.shape[:2]
        full_center = np.array([master_w / 2.0, master_h / 2.0], dtype=np.float64)

        master_objects: List[SceneObject] = []
        stroke_events: List[StrokeEvent] = []
        fill_events: List[FillEvent] = []
        camera_shots: List[CameraShot] = []

        # ── 1. Initial Establishing Wide Shot ──
        est_duration = 0.8
        camera_shots.append(CameraShot(
            start_time=0.0,
            end_time=est_duration,
            target_bbox=(0, 0, master_w, master_h),
            target_center=full_center,
            zoom=1.0,
            shot_name="01_STORYBOARD_ESTABLISHING"
        ))

        current_time = est_duration

        # Sort panels left-to-right, top-to-bottom
        valid_panels = [p for p in project.panels if not p.is_empty]
        valid_panels.sort(key=lambda p: (p.bbox[1] // 100, p.bbox[0]))

        prev_panel_center = full_center
        prev_panel_zoom = 1.0

        for p_idx, panel in enumerate(valid_panels):
            px, py, pw, ph = panel.interior_bbox
            panel_center = np.array([px + pw / 2.0, py + ph / 2.0], dtype=np.float64)
            
            # V3: Subtle zoom only — panel IS the primary composition frame
            zoom_x = master_w / max(10.0, float(pw * 1.08))
            zoom_y = master_h / max(10.0, float(ph * 1.08))
            panel_zoom = float(max(1.0, min(1.05, min(zoom_x, zoom_y))))

            # Find matching scene for this panel
            scene_match = next((s for s in project.scenes if getattr(s, "panel_id", -1) == panel.id), None)
            if scene_match is None and p_idx < len(project.scenes):
                scene_match = project.scenes[p_idx]

            # ── A. Camera Pan & Zoom Transition to this Panel ──
            trans_duration = 1.0 if p_idx > 0 else 0.8
            t_trans_start = current_time
            t_trans_end = t_trans_start + trans_duration

            camera_shots.append(CameraShot(
                start_time=t_trans_start,
                end_time=t_trans_end,
                target_bbox=(px, py, pw, ph),
                target_center=panel_center,
                zoom=panel_zoom,
                easing="ease_in_out",
                shot_name=f"TRANSITION_TO_PANEL_{panel.id}"
            ))

            current_time = t_trans_end
            panel_draw_start = current_time

            # ── B. Map and Schedule Panel Objects onto Master Canvas ──
            if scene_match and scene_match.objects:
                local_sw = float(scene_match.canvas_width)
                local_sh = float(scene_match.canvas_height)
                scale_x = pw / local_sw
                scale_y = ph / local_sh

                panel_focal_objs = [o for o in scene_match.objects if not o.is_frame]
                
                panel_cur_t = panel_draw_start
                for o_idx, local_obj in enumerate(panel_focal_objs):
                    obj_start = panel_cur_t

                    # Map strokes to master canvas
                    master_strokes = []
                    for s in local_obj.strokes:
                        m_pts = s.points.astype(np.float64)
                        m_pts[:, 0] = (m_pts[:, 0] * scale_x) + px
                        m_pts[:, 1] = (m_pts[:, 1] * scale_y) + py
                        m_pts = np.clip(m_pts, [0, 0], [master_w - 1, master_h - 1]).astype(np.int32)
                        
                        m_stroke = Stroke(
                            points=m_pts,
                            stroke_type=s.stroke_type,
                            color=s.color,
                            width=max(1.0, s.width * ((scale_x + scale_y) / 2.0)),
                            is_closed=s.is_closed
                        )
                        m_stroke.panel_bbox = (px, py, pw, ph)
                        m_stroke.panel_id = panel.id
                        master_strokes.append(m_stroke)

                    # Map details to master canvas
                    master_details = []
                    for s in local_obj.details:
                        m_pts = s.points.astype(np.float64)
                        m_pts[:, 0] = (m_pts[:, 0] * scale_x) + px
                        m_pts[:, 1] = (m_pts[:, 1] * scale_y) + py
                        m_pts = np.clip(m_pts, [0, 0], [master_w - 1, master_h - 1]).astype(np.int32)
                        
                        m_stroke = Stroke(
                            points=m_pts,
                            stroke_type=s.stroke_type,
                            color=s.color,
                            width=max(1.0, s.width * ((scale_x + scale_y) / 2.0)),
                            is_closed=s.is_closed
                        )
                        m_stroke.panel_bbox = (px, py, pw, ph)
                        m_stroke.panel_id = panel.id
                        master_details.append(m_stroke)

                    # Map fills to master canvas
                    master_fills = []
                    for f in local_obj.fills:
                        if f.mask is not None and f.area > 0:
                            # Resize local fill mask to panel ROI
                            resized_roi_mask = cv2.resize(f.mask, (pw, ph), interpolation=cv2.INTER_NEAREST)
                            
                            # Place on master canvas mask
                            g_mask = np.zeros((master_h, master_w), dtype=np.uint8)
                            y2 = min(master_h, py + ph)
                            x2 = min(master_w, px + pw)
                            roi_h = y2 - py
                            roi_w = x2 - px
                            g_mask[py:y2, px:x2] = resized_roi_mask[:roi_h, :roi_w]
                            y_indices, x_indices = np.where(g_mask > 0)
                            if len(x_indices) > 0:
                                min_x, max_x = int(np.min(x_indices)), int(np.max(x_indices))
                                min_y, max_y = int(np.min(y_indices)), int(np.max(y_indices))
                                g_bbox = (min_x, min_y, max(1, max_x - min_x + 1), max(1, max_y - min_y + 1))
                                g_center = np.array([np.mean(x_indices), np.mean(y_indices)], dtype=np.float64)
                                g_area = len(x_indices)
                                g_fill = ColorRegion(
                                    color=f.color,
                                    mask=g_mask,
                                    bbox=g_bbox,
                                    area=g_area,
                                    center=g_center,
                                    fill_mode=f.fill_mode
                                )
                                g_fill.panel_bbox = (px, py, pw, ph)
                                g_fill.panel_id = panel.id
                                master_fills.append(g_fill)

                    # Schedule stroke & fill events strictly sequentially for this Character
                    ordered_strokes = SequencePlanner.order_strokes_by_proximity(master_strokes)
                    ordered_details = SequencePlanner.order_strokes_by_proximity(master_details)
                    ordered_fills = sorted(master_fills, key=lambda f: f.area, reverse=True)
                    # Target character duration budget inside this panel
                    panel_budget = 4.2 / max(0.2, config.drawing_speed)
                    char_budget = panel_budget / max(1, len(panel_focal_objs))

                    w_out = 0.35 if ordered_strokes else 0.0
                    w_int = 0.20 if ordered_details else 0.0
                    w_fill = 0.45 if ordered_fills else 0.0
                    total_w = max(1e-4, w_out + w_int + w_fill)

                    t_out_budget = char_budget * (w_out / total_w)
                    t_int_budget = char_budget * (w_int / total_w)
                    t_fill_budget = char_budget * (w_fill / total_w)

                    cur_t = obj_start

                    # 1. Outlines of this Character
                    if ordered_strokes:
                        tot_l = max(1.0, sum(s.length for s in ordered_strokes))
                        for s in ordered_strokes:
                            s_dur = t_out_budget * (s.length / tot_l)
                            stroke_events.append(StrokeEvent(cur_t, cur_t + s_dur, s, "ease_in_out"))
                            cur_t += s_dur

                    # 2. Internals & Details of this Character
                    if ordered_details:
                        tot_l = max(1.0, sum(s.length for s in ordered_details))
                        for s in ordered_details:
                            s_dur = t_int_budget * (s.length / tot_l)
                            stroke_events.append(StrokeEvent(cur_t, cur_t + s_dur, s, "ease_out"))
                            cur_t += s_dur

                    # 3. Color Fills of this Character (Drawn after lines are complete)
                    if ordered_fills:
                        tot_a = max(1.0, sum(np.sqrt(f.area) for f in ordered_fills))
                        for f in ordered_fills:
                            f_dur = t_fill_budget * (np.sqrt(f.area) / tot_a)
                            fill_events.append(FillEvent(cur_t, cur_t + f_dur, f, "ease_in_out"))
                            cur_t += f_dur

                    obj_end = cur_t
                    obj_t_total = obj_end - obj_start

                    # Create master SceneObject
                    master_obj = SceneObject(
                        name=f"Panel {panel.id} - {local_obj.name}",
                        strokes=master_strokes,
                        fills=master_fills,
                        details=master_details,
                        bbox=(px, py, pw, ph),
                        global_bbox=(px, py, pw, ph),
                        panel_id=panel.id,
                        animation_start=obj_start,
                        animation_end=obj_end,
                        duration=obj_t_total
                    )
                    master_objects.append(master_obj)

                    panel_cur_t = obj_end
                    if o_idx < len(panel_focal_objs) - 1:
                        panel_cur_t += max(0.4, float(config.transition_duration) * 0.5)

                current_time = panel_cur_t

            # ── C. Focus Camera Shot on Panel during Drawing ──
            panel_draw_end = current_time
            camera_shots.append(CameraShot(
                start_time=panel_draw_start,
                end_time=panel_draw_end,
                target_bbox=(px, py, pw, ph),
                target_center=panel_center,
                zoom=panel_zoom,
                easing="linear",
                shot_name=f"FOCUS_PANEL_{panel.id}"
            ))

            # ── D. Subtle Reveal Pull-back on Completed Panel ──
            reveal_duration = 0.4
            camera_shots.append(CameraShot(
                start_time=panel_draw_end,
                end_time=panel_draw_end + reveal_duration,
                target_bbox=(px, py, pw, ph),
                target_center=panel_center,
                zoom=float(max(1.0, panel_zoom * 0.96)),
                easing="ease_in_out",
                shot_name=f"REVEAL_PANEL_{panel.id}"
            ))

            current_time = panel_draw_end + reveal_duration
            prev_panel_center = panel_center
            prev_panel_zoom = float(max(1.0, panel_zoom * 0.96))

        # ── 3. Final Master Pull-Back & Hold ──
        final_trans_start = current_time
        final_trans_end = final_trans_start + 1.5

        camera_shots.append(CameraShot(
            start_time=final_trans_start,
            end_time=final_trans_end,
            target_bbox=(0, 0, master_w, master_h),
            target_center=full_center,
            zoom=1.0,
            easing="ease_in_out",
            shot_name="FINAL_MASTER_PULL_BACK"
        ))

        # ── 4. Master Full Storyboard Presentation Hold ──
        master_hold_end = final_trans_end + 2.0
        camera_shots.append(CameraShot(
            start_time=final_trans_end,
            end_time=master_hold_end,
            target_bbox=(0, 0, master_w, master_h),
            target_center=full_center,
            zoom=1.0,
            shot_name="FINAL_MASTER_HOLD"
        ))

        timeline = Timeline(
            duration=master_hold_end,
            stroke_events=stroke_events,
            fill_events=fill_events,
            camera_shots=camera_shots
        )

        # V3: Background color from actual source image, not hardcoded white
        border_top = src_img[0, :]
        border_bottom = src_img[-1, :]
        border_left = src_img[:, 0]
        border_right = src_img[:, -1]
        border_pixels = np.concatenate([border_top, border_bottom, border_left, border_right], axis=0)
        median_bg = np.median(border_pixels, axis=0).astype(np.uint8)
        bg_color = (int(median_bg[0]), int(median_bg[1]), int(median_bg[2]))

        master_scene = Scene(
            config=config,
            objects=master_objects,
            background_color=bg_color,
            source_image=src_img,
            canvas_width=master_w,
            canvas_height=master_h,
            structure_info="STORYBOARD"
        )
        master_scene.panel_structures = project.panels

        return master_scene, timeline, camera_shots

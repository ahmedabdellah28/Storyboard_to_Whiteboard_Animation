"""
Dynamic SRT Choreographer & Element Timeline Synchronizer
Links word-level subtitles with storyboard panels and constituent elements.
Choreographs natural artist strokes, RTL handwriting, and exact speech-synchronized speed multipliers.
"""
import math
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple

from dev_separator.natural_artist_choreographer import NaturalArtistChoreographer


def morphological_skeleton(bin_img):
    skeleton = np.zeros(bin_img.shape, np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    img_c = bin_img.copy()
    while True:
        eroded = cv2.erode(img_c, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(img_c, temp)
        skeleton = cv2.bitwise_or(skeleton, temp)
        img_c = eroded.copy()
        if cv2.countNonZero(img_c) == 0:
            break
    return skeleton


def extract_ordered_skeleton_strokes(ink_roi, direction="RTL", step_stride=3):
    skel = morphological_skeleton(ink_roi)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(skel)
    if num_labels <= 1:
        ys, xs = np.where(ink_roi > 0)
        if len(xs) == 0:
            return []
        if direction == "RTL":
            return [[(float(x), float(ys[xs == x].mean())) for x in range(xs.max(), xs.min()-1, -step_stride) if len(ys[xs == x]) > 0]]
        else:
            return [[(float(x), float(ys[xs == x].mean())) for x in range(xs.min(), xs.max()+1, step_stride) if len(ys[xs == x]) > 0]]

    comps = []
    for i in range(1, num_labels):
        cx = stats[i, cv2.CC_STAT_LEFT]
        cy = stats[i, cv2.CC_STAT_TOP]
        area = stats[i, cv2.CC_STAT_AREA]
        comps.append((cx, cy, area, i))

    if direction == "RTL":
        comps.sort(key=lambda c: -c[0])
    else:
        comps.sort(key=lambda c: c[0])

    all_strokes = []
    for cx, cy, area, idx in comps:
        comp_mask = (labels == idx).astype(np.uint8)
        ys, xs = np.where(comp_mask > 0)
        if len(xs) == 0:
            continue
        pts_set = set(zip(xs, ys))
        start_pt = max(pts_set, key=lambda p: (p[0], -p[1])) if direction == "RTL" else min(pts_set, key=lambda p: (p[0], p[1]))
        path = [start_pt]
        pts_set.remove(start_pt)
        curr = start_pt
        while pts_set:
            cx_pt, cy_pt = curr
            neighbors = [(cx_pt+dx, cy_pt+dy) for dx in [-1,0,1] for dy in [-1,0,1] if (dx!=0 or dy!=0) and (cx_pt+dx, cy_pt+dy) in pts_set]
            if neighbors:
                next_pt = min(neighbors, key=lambda p: (p[0], p[1])) if direction == "RTL" else max(neighbors, key=lambda p: (p[0], -p[1]))
            else:
                next_pt = min(pts_set, key=lambda p: (p[0]-cx_pt)**2 + (p[1]-cy_pt)**2)
            path.append(next_pt)
            pts_set.remove(next_pt)
            curr = next_pt
        sampled_path = path[::step_stride]
        if len(sampled_path) > 0:
            all_strokes.append(sampled_path)
    return all_strokes


def extract_object_strokes(obj: Dict[str, Any], scale_x: float, scale_y: float) -> List[Tuple[float, float]]:
    cat = obj.get("category", "TEXT")
    mask = obj.get("mask")
    crop = obj.get("crop")
    bx, by, bw, bh = obj.get("bbox", (0, 0, 10, 10))

    if mask is None or crop is None or cv2.countNonZero(mask) == 0:
        return []

    stroke_pts = []

    if cat == "CHARACTER":
        # Outside-In boundary and contour drawing (draws outer borders first, then peels inward smoothly)
        try:
            from core.render_engine.render.concentric_engine import build_gapless_orbital_path
        except ImportError:
            from engine.render.concentric_engine import build_gapless_orbital_path
        orbital_strokes = build_gapless_orbital_path(
            crop,
            ring_step=4,
            sample_interval=2.0,
            brush_radius=10,
            drawing_direction="OUTSIDE_IN",
            mask=mask
        )
        
        # Test canvas to track covered pixels
        h_c, w_c = crop.shape[:2]
        drawn_coverage = np.zeros((h_c, w_c), dtype=np.uint8)
        brush_r = 10
        
        if orbital_strokes:
            # Rotate closed contour loops to minimize transit distance from previous contour endpoint
            # Completely eliminates cross-body jumps and teleportation
            last_p = orbital_strokes[0][0]
            for s in orbital_strokes:
                if len(s) >= 3:
                    is_closed = math.hypot(s[0][0] - s[-1][0], s[0][1] - s[-1][1]) < 10.0
                    loop_pts = s[:-1] if is_closed else s
                    best_idx = min(range(len(loop_pts)), key=lambda i: (loop_pts[i][0] - last_p[0])**2 + (loop_pts[i][1] - last_p[1])**2)
                    rotated = loop_pts[best_idx:] + loop_pts[:best_idx]
                    if is_closed:
                        rotated.append(rotated[0])
                    for pt in rotated:
                        stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))
                        cv2.circle(drawn_coverage, (int(round(pt[0])), int(round(pt[1]))), brush_r, 255, -1)
                    last_p = rotated[-1]
                else:
                    for pt in s:
                        stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))
                        cv2.circle(drawn_coverage, (int(round(pt[0])), int(round(pt[1]))), brush_r, 255, -1)
                    if s:
                        last_p = s[-1]

            # Infill passes for remaining uncovered pixels (ensures 100% stroke coverage with zero pop-in)
            uncovered = cv2.bitwise_and(mask, cv2.bitwise_not(drawn_coverage))
            if cv2.countNonZero(uncovered) > 0:
                cnts, _ = cv2.findContours(uncovered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for c in cnts:
                    if cv2.contourArea(c) >= 6:
                        pts = c.reshape(-1, 2)
                        for pt in pts:
                            stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))
        else:
            plan = NaturalArtistChoreographer.generate_character_drawing_plan(crop, mask, step_dist=3.0)
            for s in plan.get("linework_strokes", []):
                for pt in s:
                    stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))
            for s in plan.get("shading_strokes", []):
                for pt in s:
                    stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))

    elif cat in ("TITLE", "TEXT_LINE") or cat == "TEXT":
        # Smooth Arabic handwriting trajectory
        raw_strokes = extract_ordered_skeleton_strokes(mask, direction="RTL", step_stride=2)
        for s in raw_strokes:
            for pt in s:
                stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))

    elif cat == "CONTAINER_CARD":
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            pts = c.reshape(-1, 2)
            for pt in pts[::2]:
                stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))
            # Close the loop smoothly
            stroke_pts.append((float(bx + pts[0][0]) * scale_x, float(by + pts[0][1]) * scale_y))
        # Dense internal lines without teleporting
        for y in range(8, bh - 8, 14):
            xs = np.where(mask[y, :] > 0)[0]
            if len(xs) > 6:
                for x in range(xs[0], xs[-1] + 1, 3):
                    stroke_pts.append((float(bx + x) * scale_x, float(by + y) * scale_y))

    else:
        cnts, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        for c in cnts:
            if len(c) >= 4:
                pts = c.reshape(-1, 2)
                for pt in pts[::2]:
                    stroke_pts.append((float(bx + pt[0]) * scale_x, float(by + pt[1]) * scale_y))

    return stroke_pts


class DynamicSRTChoreographer:
    @classmethod
    def choreograph_timeline(
        cls, 
        panels: List[Dict[str, Any]], 
        srt_entries: List[Dict[str, Any]],
        total_audio_sec: float,
        use_visual_beats: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Choreographs timeline across all panels.
        If use_visual_beats=True: Uses the advanced ASATE Visual Beat Layer
        (SpeechBeat -> VisualBeat -> BeatTimingSolver -> Semantic Emphasis & Overlap).
        If use_visual_beats=False: Falls back to legacy proportional percentage slicing.
        """
        if use_visual_beats:
            try:
                try:
                    from core.render_engine.beat.beat_mapper import BeatMapper
                    from core.render_engine.beat.beat_solver import BeatTimingSolver
                    from core.render_engine.beat.beat_debugger import BeatTimelineVisualizer
                except ImportError:
                    from engine.beat.beat_mapper import BeatMapper
                    from engine.beat.beat_solver import BeatTimingSolver
                    from engine.beat.beat_debugger import BeatTimelineVisualizer

                # 1. Dynamically group SRT entries into Speech Beats
                speech_beats = BeatMapper.create_speech_beats_from_srt(srt_entries)

                # 2. Dynamically map panels to Visual Beats
                visual_beats = BeatMapper.map_panels_to_visual_beats(
                    panels=panels,
                    speech_beats=speech_beats,
                    total_audio_sec=total_audio_sec
                )

                # 3. Solve timing constrained within each Visual Beat
                solved_beats = BeatTimingSolver.solve_storyboard(
                    visual_beats=visual_beats,
                    total_audio_duration=total_audio_sec
                )

                scheduled_panels = []
                for vb in solved_beats:
                    # Find matching original panel
                    orig_panel = next((p for p in panels if p.get("global_id") == vb.panel_id), None)
                    if orig_panel is None:
                        orig_panel = panels[len(scheduled_panels)] if len(scheduled_panels) < len(panels) else {}

                    panel_copy = dict(orig_panel)
                    panel_copy["start_time"] = round(vb.start, 2)
                    panel_copy["end_time"] = round(vb.end, 2)
                    panel_copy["duration"] = round(vb.duration, 2)
                    panel_copy["spoken_text"] = vb.narrative_text
                    panel_copy["objects"] = vb.elements
                    panel_copy["visual_beat"] = vb
                    scheduled_panels.append(panel_copy)

                return scheduled_panels

            except Exception as e:
                print(f"[DynamicSRTChoreographer] Warning: Visual Beat Solver encountered {e}, falling back to legacy mode.")

        # -----------------------------------------------------------------------------------
        # LEGACY MODE FALLBACK
        # -----------------------------------------------------------------------------------
        num_panels = len(panels)
        total_words = len(srt_entries)

        words_per_panel = total_words / float(max(1, num_panels))
        word_ranges = []
        curr_w = 1
        for i in range(num_panels):
            next_w = int(round((i + 1) * words_per_panel))
            next_w = min(total_words, next_w)
            word_ranges.append((curr_w, next_w))
            curr_w = next_w + 1

        # Assign time windows to panels
        scheduled_panels = []
        for p_idx, panel in enumerate(panels):
            p_id = panel["global_id"]
            w_st, w_en = word_ranges[min(p_idx, len(word_ranges) - 1)]

            p_entries = [e for e in srt_entries if w_st <= e["index"] <= w_en]
            if p_entries:
                p_start = p_entries[0]["start"]
                p_end = p_entries[-1]["end"]
                spoken_text = " ".join(e["text"] for e in p_entries)
            else:
                p_start = (p_idx / float(num_panels)) * total_audio_sec
                p_end = ((p_idx + 1) / float(num_panels)) * total_audio_sec
                spoken_text = ""

            p_dur = max(0.8, p_end - p_start)
            panel_copy = dict(panel)
            panel_copy["start_time"] = round(p_start, 2)
            panel_copy["end_time"] = round(p_end, 2)
            panel_copy["duration"] = round(p_dur, 2)
            panel_copy["spoken_text"] = spoken_text

            # Schedule individual elements
            objs = panel_copy.get("objects", [])
            scheduled_objs = []
            t_curr = p_start

            for o_i, obj in enumerate(objs):
                obj_c = dict(obj)
                cat = obj_c["category"]
                name = obj_c.get("name", "").lower()

                if "title" in name or cat == "TITLE":
                    o_dur = min(1.8, max(0.4, p_dur * 0.28))
                elif cat == "CHARACTER":
                    o_dur = min(3.5, max(0.8, p_dur * 0.40))
                elif cat == "CONTAINER_CARD":
                    o_dur = min(2.0, max(0.5, p_dur * 0.30))
                elif cat in ("EMOJI", "ICON_GRAPHIC"):
                    o_dur = min(1.5, max(0.4, p_dur * 0.22))
                else:
                    o_dur = min(2.0, max(0.4, p_dur * 0.25))

                st = round(t_curr, 2)
                en = round(min(p_end, t_curr + o_dur), 2)
                dur = round(max(0.15, en - st), 2)

                obj_c["sync_start"] = st
                obj_c["sync_end"] = en
                obj_c["sync_duration"] = dur
                obj_c["hold_duration"] = 0.30
                obj_c["tier"] = "PRIMARY" if cat == "CHARACTER" else "SECONDARY"
                obj_c["speed_multiplier"] = round(max(0.5, 2.0 / max(0.1, dur)), 2)

                t_curr = min(p_end - 0.1, t_curr + o_dur * 0.75)
                scheduled_objs.append(obj_c)

            panel_copy["objects"] = scheduled_objs
            scheduled_panels.append(panel_copy)

        return scheduled_panels


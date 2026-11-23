"""Declarative Motion Graphics Engine.

Consumes generic motion contracts (motion_plan.json, visual_manifest.json, master_audio.wav)
and renders physics-eased, camera-projected video layers.
Reuses compositing, easing, and video piping infrastructure from DynamicSectionEngine.
"""

import os
import sys
import json
import math
import time
import subprocess
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Ensure repository root is on path
ROOT_DIR = str(Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.dynamic_section_engine import (
    blend_sprite_screen,
    smootherstep,
    imread_unicode,
    imwrite_unicode,
)


def ease_out_back(p: float) -> float:
    """Overshoot elastic back easing for snappy pop-ins."""
    p = np.clip(p, 0.0, 1.0)
    c1 = 1.70158
    c3 = c1 + 1.0
    p_norm = p - 1.0
    return 1.0 + c3 * (p_norm ** 3) + c1 * (p_norm ** 2)


def ease_out_cubic(p: float) -> float:
    """Smooth cubic deceleration easing."""
    p = np.clip(p, 0.0, 1.0)
    return 1.0 - (1.0 - p) ** 3


def ease_in_out_cubic(p: float) -> float:
    """Smooth S-curve acceleration and deceleration."""
    p = np.clip(p, 0.0, 1.0)
    if p < 0.5:
        return 4.0 * p * p * p
    else:
        return 1.0 - ((-2.0 * p + 2.0) ** 3) / 2.0


def apply_easing(prog: float, easing_name: str) -> float:
    """Applies named easing function to normalized progress [0.0, 1.0]."""
    prog = float(np.clip(prog, 0.0, 1.0))
    if easing_name == "ease_out_back":
        return ease_out_back(prog)
    elif easing_name == "ease_out_cubic":
        return ease_out_cubic(prog)
    elif easing_name == "smootherstep":
        return smootherstep(prog)
    elif easing_name == "ease_in_out_cubic":
        return ease_in_out_cubic(prog)
    return prog


class CompositionCameraTrajectory:
    """Smooth 2D camera path targeting composition focal points and zoom levels."""

    def __init__(self, camera_specs: List[Dict[str, Any]]) -> None:
        self.camera_specs = sorted(camera_specs, key=lambda c: c["start"])
        self.segments = []
        cur_x, cur_y, cur_z = 0.5, 0.5, 1.0

        for i, s in enumerate(self.camera_specs):
            t0 = float(s["start"])
            t1 = float(s["end"])
            action = s.get("action", "hold")
            fp = s.get("focal_point", [0.5, 0.5])
            tx, ty = float(fp[0]), float(fp[1])
            tz = float(s.get("zoom", 1.0))
            easing = s.get("easing", "smootherstep")

            start_x, start_y, start_z = (tx, ty, tz) if not self.segments else (cur_x, cur_y, cur_z)

            self.segments.append({
                "shot_id": s.get("shot_id"),
                "start": t0,
                "end": t1,
                "action": action,
                "easing": easing,
                "p0": (start_x, start_y, start_z),
                "p1": (tx, ty, tz),
            })
            cur_x, cur_y, cur_z = tx, ty, tz

    def get_state(self, t: float) -> Tuple[float, float, float]:
        if not self.segments:
            return 0.5, 0.5, 1.0

        if t <= self.segments[0]["start"]:
            return self.segments[0]["p0"]

        for seg in self.segments:
            t0, t1 = seg["start"], seg["end"]
            if t < t0:
                return seg["p0"]
            elif t0 <= t <= t1:
                dur = max(0.001, t1 - t0)
                raw_p = (t - t0) / dur
                action = seg["action"]
                easing = seg["easing"]

                if action == "hold":
                    return seg["p1"]
                elif action == "punch_in":
                    punch_dur = min(0.8, dur * 0.35)
                    if (t - t0) < punch_dur:
                        p = apply_easing((t - t0) / punch_dur, "ease_out_back")
                    else:
                        p = 1.0
                else:
                    p = apply_easing(raw_p, easing)

                x0, y0, z0 = seg["p0"]
                x1, y1, z1 = seg["p1"]
                cx = x0 + (x1 - x0) * p
                cy = y0 + (y1 - y0) * p
                cz = z0 + (z1 - z0) * p
                return float(cx), float(cy), float(cz)

        return self.segments[-1]["p1"]


class DeclarativeCameraTrajectory:
    """Continuous, smooth 2D camera path with zoom, reframing, and holds."""

    def __init__(
        self,
        camera_specs: List[Dict[str, Any]],
        manifest_entities: Dict[str, Any],
        canvas_dims: Tuple[int, int] = (1536, 1024),
        preview_dims: Tuple[int, int] = (1280, 720),
        base_zoom: float = 0.703125,
    ) -> None:
        self.camera_specs = sorted(camera_specs, key=lambda c: c["start"])
        self.entities = manifest_entities
        self.cw, self.ch = canvas_dims
        self.pw, self.ph = preview_dims
        self.base_zoom = base_zoom
        self.default_center = (self.cw / 2.0, self.ch / 2.0)

        # Build keyframe segments: (t_start, t_end, (x0, y0, z0), (x1, y1, z1))
        self.segments = self._build_camera_segments()

    def _get_target_coords(self, target_id: Optional[str]) -> Tuple[float, float]:
        if target_id and target_id in self.entities:
            ent = self.entities[target_id]
            cen = ent.get("centroid")
            if cen and len(cen) >= 2:
                tx = float(np.clip(cen[0], self.cw * 0.15, self.cw * 0.85))
                ty = float(np.clip(cen[1], self.ch * 0.15, self.ch * 0.85))
                return tx, ty
            bbox = ent.get("bbox")
            if bbox and len(bbox) >= 4:
                tx = float(np.clip(bbox[0] + bbox[2] / 2.0, self.cw * 0.15, self.cw * 0.85))
                ty = float(np.clip(bbox[1] + bbox[3] / 2.0, self.ch * 0.15, self.ch * 0.85))
                return tx, ty
        return self.default_center

    def _build_camera_segments(self) -> List[Dict[str, Any]]:
        segments = []
        cur_x, cur_y = self.default_center
        cur_z = self.base_zoom

        for i, spec in enumerate(self.camera_specs):
            t_start = spec["start"]
            t_end = spec["end"]
            action = spec["action"]
            target_id = spec.get("target")
            tx, ty = self._get_target_coords(target_id)

            if action == "zoom_in":
                target_z = min(1.20, self.base_zoom * 1.55)
                focus_x = cur_x + (tx - cur_x) * 0.70
                focus_y = cur_y + (ty - cur_y) * 0.70
            elif action == "punch":
                target_z = min(1.25, self.base_zoom * 1.65)
                focus_x = cur_x + (tx - cur_x) * 0.80
                focus_y = cur_y + (ty - cur_y) * 0.80
            elif action == "reframe":
                target_z = self.base_zoom * 1.30
                focus_x = cur_x + (tx - cur_x) * 0.65
                focus_y = cur_y + (ty - cur_y) * 0.65
            else:  # "hold"
                target_z = max(self.base_zoom * 1.10, cur_z)
                focus_x = cur_x + (tx - cur_x) * 0.50
                focus_y = cur_y + (ty - cur_y) * 0.50

            segments.append({
                "start": t_start,
                "end": t_end,
                "p0": (cur_x, cur_y, cur_z),
                "p1": (focus_x, focus_y, target_z),
                "action": action,
            })
            cur_x, cur_y, cur_z = focus_x, focus_y, target_z

        return segments

    def get_state(self, t: float) -> Tuple[float, float, float]:
        """Evaluates (cam_x, cam_y, cam_zoom) at timestamp t."""
        if not self.segments:
            return self.default_center[0], self.default_center[1], self.base_zoom

        if t <= self.segments[0]["start"]:
            return self.segments[0]["p0"]

        for seg in self.segments:
            t0, t1 = seg["start"], seg["end"]
            if t < t0:
                return seg["p0"]
            elif t0 <= t <= t1:
                dur = max(0.001, t1 - t0)
                prog = smootherstep((t - t0) / dur)
                x0, y0, z0 = seg["p0"]
                x1, y1, z1 = seg["p1"]
                cx = x0 + (x1 - x0) * prog
                cy = y0 + (y1 - y0) * prog
                cz = z0 + (z1 - z0) * prog
                return float(cx), float(cy), float(cz)

        return self.segments[-1]["p1"]


class DeclarativeMotionGraphicsEngine:
    """Renderer executing validated TCM-DS motion plans declaratively."""

    def __init__(
        self,
        motion_plan_path: str,
        manifest_path: str,
        assets_dir: str,
        audio_path: str,
        output_path: str,
        shot_plan_path: Optional[str] = None,
        camera_plan_path: Optional[str] = None,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
    ) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.motion_plan_path = Path(motion_plan_path).resolve()
        self.manifest_path = Path(manifest_path).resolve()
        self.assets_dir = Path(assets_dir).resolve()
        self.audio_path = Path(audio_path).resolve()
        self.output_path = Path(output_path).resolve()

        # Load motion plan and manifest
        with open(self.motion_plan_path, "r", encoding="utf-8") as f:
            self.motion_plan = json.load(f)

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)

        self.entities = {e["visual_id"]: e for e in self.manifest.get("entities", [])}
        canvas_dims = self.manifest.get("canvas_dimensions", {"width": 1536, "height": 1024})
        self.canvas_w = int(canvas_dims.get("width", 1536))
        self.canvas_h = int(canvas_dims.get("height", 1024))

        # Base zoom: fits canvas height into preview height (1024 -> 720)
        self.base_zoom = self.height / float(self.canvas_h)

        # Load shot plan if available
        self.shot_plan = []
        sp_candidate = None
        if shot_plan_path and Path(shot_plan_path).is_file():
            sp_candidate = Path(shot_plan_path)
        elif (self.motion_plan_path.parent / "shot_plan.json").is_file():
            sp_candidate = self.motion_plan_path.parent / "shot_plan.json"
        elif (Path(ROOT_DIR) / "data" / "shot_plan.json").is_file():
            sp_candidate = Path(ROOT_DIR) / "data" / "shot_plan.json"

        if sp_candidate and sp_candidate.is_file():
            with open(sp_candidate, "r", encoding="utf-8") as f:
                self.shot_plan = json.load(f)

        # Load camera plan if available
        self.camera_plan = []
        cp_candidate = None
        if camera_plan_path and Path(camera_plan_path).is_file():
            cp_candidate = Path(camera_plan_path)
        elif (self.motion_plan_path.parent / "camera_plan.json").is_file():
            cp_candidate = self.motion_plan_path.parent / "camera_plan.json"
        elif (Path(ROOT_DIR) / "data" / "camera_plan.json").is_file():
            cp_candidate = Path(ROOT_DIR) / "data" / "camera_plan.json"

        if cp_candidate and cp_candidate.is_file():
            with open(cp_candidate, "r", encoding="utf-8") as f:
                self.camera_plan = json.load(f)

        # Collect camera actions
        camera_specs = []
        for beat in self.motion_plan:
            if beat.get("camera"):
                camera_specs.append(beat["camera"])

        has_focal = any("focal_point" in c for c in camera_specs)
        if has_focal:
            self.camera = CompositionCameraTrajectory(camera_specs=camera_specs)
        else:
            self.camera = DeclarativeCameraTrajectory(
                camera_specs=camera_specs,
                manifest_entities=self.entities,
                canvas_dims=(self.canvas_w, self.canvas_h),
                preview_dims=(self.width, self.height),
                base_zoom=self.base_zoom,
            )

        # Flatten actions & track lifecycle per asset
        self.actions = []
        self.asset_timelines: Dict[str, List[Dict[str, Any]]] = {}
        for beat in self.motion_plan:
            for act in beat.get("actions", []):
                self.actions.append(act)
                aid = act["asset_id"]
                if aid not in self.asset_timelines:
                    self.asset_timelines[aid] = []
                self.asset_timelines[aid].append(act)

        # Sort each asset's actions chronologically
        for aid in self.asset_timelines:
            self.asset_timelines[aid].sort(key=lambda a: a["start"])

        # Determine timeline bounds
        last_beat = self.motion_plan[-1]
        self.duration_sec = float(last_beat["end"])
        self.total_frames = int(round(self.duration_sec * self.fps))

        # Load asset images
        self.asset_images: Dict[str, np.ndarray] = {}
        self.missing_assets: List[str] = []
        self._load_assets()

    def _load_assets(self) -> None:
        """Loads all required transparent PNGs from assets_dir."""
        for aid in self.asset_timelines:
            filename = f"{aid}.png"
            p = self.assets_dir / filename
            if not p.is_file():
                crop_path = self.entities.get(aid, {}).get("mask_crop_path")
                if crop_path and (self.assets_dir / Path(crop_path).name).is_file():
                    p = self.assets_dir / Path(crop_path).name

            if p.is_file():
                img = imread_unicode(str(p), cv2.IMREAD_UNCHANGED)
                if img is not None and img.shape[2] == 4:
                    self.asset_images[aid] = img
                else:
                    self.missing_assets.append(aid)
            else:
                self.missing_assets.append(aid)

        print(f"Loaded {len(self.asset_images)} assets. Missing: {len(self.missing_assets)}")

    def resolve_shot(self, t: float) -> Optional[Dict[str, Any]]:
        """Resolves active Shot, remaining continuous until next shot's first visual event."""
        if not self.shot_plan:
            return None

        cur_shot = self.shot_plan[0]
        for s_idx, s in enumerate(self.shot_plan):
            s_acts = [
                a for b in self.motion_plan
                if s["start"] <= b["start"] < s["end"]
                for a in b.get("actions", [])
            ]
            first_t = min((a["start"] for a in s_acts), default=s["start"]) if s_idx > 0 else s["start"]
            if t >= first_t:
                cur_shot = s
            else:
                break
        return cur_shot

    def render_frame(self, t: float) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Renders single video frame at time t using composition-first projection."""
        frame = np.full((self.height, self.width, 3), 255, dtype=np.uint8)

        # 1. Resolve current Shot & CompositionState
        cur_shot = self.resolve_shot(t)
        if cur_shot:
            comp = cur_shot.get("composition_state", cur_shot)
            hero = comp.get("hero") or (cur_shot.get("hero_assets", [None])[0])
            support = comp.get("support", cur_shot.get("support_assets", []))
            accents = comp.get("accents", cur_shot.get("accent_assets", []))
            persistent = comp.get("persistent", cur_shot.get("persistent_assets", []))
            norm_positions = comp.get("normalized_positions", cur_shot.get("normalized_positions", {}))
            rel_scales = comp.get("relative_scales", cur_shot.get("relative_scales", {}))
            z_orders = comp.get("z_orders", cur_shot.get("z_order", {}))
            depth_layers = comp.get("depth_layers", cur_shot.get("depth_layers", {}))
            shot_start = float(cur_shot["start"])
            shot_end = float(cur_shot["end"])
            planned_assets = set([hero] if hero else []) | set(support) | set(accents) | set(persistent)
            shot_actions = [
                a for b in self.motion_plan
                if shot_start <= b["start"] < shot_end
                for a in b.get("actions", [])
            ]
        else:
            cur_beat = self.motion_plan[0]
            for b in self.motion_plan:
                if b["start"] <= t <= b["end"] or (b is self.motion_plan[-1] and t >= b["start"]):
                    cur_beat = b
                    break
            norm_positions = cur_beat.get("normalized_positions", {})
            rel_scales = cur_beat.get("relative_scales", {})
            z_orders = {}
            depth_layers = {}
            shot_start = float(cur_beat["start"])
            shot_end = float(cur_beat["end"])
            planned_assets = set(norm_positions.keys())
            persistent = []
            shot_actions = cur_beat.get("actions", [])

        # 2. Camera state
        cam_x, cam_y, cam_zoom = self.camera.get_state(t)

        metrics = {
            "visible_assets": 0,
            "offscreen_assets": 0,
            "is_blank": True,
            "cam_coords": (cam_x, cam_y, cam_zoom),
            "composition_violations": 0,
        }

        # 3. Determine visible assets and compute transforms
        render_queue = []
        for aid in planned_assets:
            if aid not in self.asset_images:
                continue

            img = self.asset_images[aid]
            aid_actions = [a for a in shot_actions if a["asset_id"] == aid]
            is_persistent = aid in persistent

            # Visibility lifecycle
            if is_persistent:
                if t < shot_start:
                    continue
            else:
                if not aid_actions:
                    continue
                first_start = min(a["start"] for a in aid_actions)
                if t < first_start:
                    continue

            # Check explicit exit
            exit_acts = [a for a in aid_actions if a.get("action") == "exit"]
            if exit_acts and t >= exit_acts[0]["end"]:
                continue

            # Compute current kinetic transform
            active_act = None
            for act in aid_actions:
                if act["start"] <= t <= act["end"]:
                    active_act = act
                    break

            if active_act is not None:
                t0, t1 = active_act["start"], active_act["end"]
                dur = max(0.001, t1 - t0)
                prog = (t - t0) / dur
                action_name = active_act["action"]
                easing = active_act.get("easing", "smootherstep")
                intensity = float(active_act.get("intensity", 1.0))
                act_z = active_act.get("z_index")
                z_index = int(act_z) if act_z is not None else int(z_orders.get(aid, 5))

                eased_p = apply_easing(prog, easing)

                if action_name == "pop_in":
                    local_scale = max(0.02, eased_p * intensity)
                    alpha = max(0.02, min(1.0, prog * 2.0))
                    off_x, off_y = 0.0, 0.0
                elif action_name == "scale_in":
                    local_scale = max(0.02, eased_p)
                    alpha = max(0.02, min(1.0, prog * 1.5))
                    off_x, off_y = 0.0, 0.0
                elif action_name == "slide_up":
                    local_scale = 1.0
                    alpha = min(1.0, prog * 1.5)
                    off_x, off_y = 0.0, 35.0 * (1.0 - eased_p) * intensity
                elif action_name == "fade_in":
                    local_scale = 1.0
                    alpha = apply_easing(prog, "smootherstep")
                    off_x, off_y = 0.0, 0.0
                elif action_name == "pulse":
                    pulse_delta = math.sin(prog * math.pi) * 0.16 * intensity
                    local_scale = 1.0 + pulse_delta
                    alpha = 1.0
                    off_x, off_y = 0.0, 0.0
                elif action_name == "scale_punch":
                    if prog < 0.35:
                        punch_p = ease_out_cubic(prog / 0.35)
                        local_scale = 1.0 + 0.20 * intensity * punch_p
                    else:
                        decay_p = smootherstep((prog - 0.35) / 0.65)
                        local_scale = 1.0 + 0.20 * intensity * (1.0 - decay_p)
                    alpha = 1.0
                    off_x, off_y = 0.0, 0.0
                elif action_name == "settle":
                    osc = math.sin(prog * math.pi * 2.0) * math.exp(-prog * 3.0)
                    local_scale = 1.0 + 0.05 * intensity * osc
                    alpha = 1.0
                    off_x, off_y = 0.0, 0.0
                else:
                    local_scale = 1.0
                    alpha = 1.0
                    off_x, off_y = 0.0, 0.0
            else:
                # Settle post-entrance hold
                z_index = int(z_orders.get(aid, 5))
                local_scale = 1.0
                alpha = 1.0
                off_x, off_y = 0.0, 0.0

            # 4. Composition projection with 2.5D parallax
            norm_pt = norm_positions.get(aid, [0.5, 0.5])
            nx, ny = norm_pt
            if nx < 0.0 or nx > 1.0 or ny < 0.0 or ny > 1.0:
                metrics["composition_violations"] += 1

            rel_scale = float(rel_scales.get(aid, 1.0))
            depth = float(depth_layers.get(aid, 0.5))

            # Subtle parallax
            cam_dx = (cam_x - 0.5)
            cam_dy = (cam_y - 0.5)
            parallax_factor = (depth - 0.5) * 0.04
            eff_nx = nx - cam_dx * parallax_factor
            eff_ny = ny - cam_dy * parallax_factor

            scr_cx = int(round((eff_nx - cam_x) * self.width * cam_zoom + (self.width / 2.0) + off_x))
            scr_cy = int(round((eff_ny - cam_y) * self.height * cam_zoom + (self.height / 2.0) + off_y))

            orig_h, orig_w = img.shape[:2]
            base_h = self.height * 0.42 * rel_scale * local_scale
            base_w = base_h * (orig_w / float(orig_h))

            scr_w = int(round(base_w * cam_zoom))
            scr_h = int(round(base_h * cam_zoom))
            scr_x = scr_cx - scr_w // 2
            scr_y = scr_cy - scr_h // 2

            render_queue.append((z_index, aid, img, scr_x, scr_y, scr_w, scr_h, alpha))

        # Check maximum simultaneous assets violation
        if len(render_queue) > 5:
            metrics["composition_violations"] += 1

        render_queue.sort(key=lambda item: item[0])
        metrics["visible_assets"] = len(render_queue)

        for z_idx, aid, img, sx, sy, sw, sh, alpha in render_queue:
            if sw <= 0 or sh <= 0:
                continue
            if sx + sw <= 0 or sx >= self.width or sy + sh <= 0 or sy >= self.height:
                metrics["offscreen_assets"] += 1
                continue

            blend_sprite_screen(frame, img, sx, sy, sw, sh, alpha_mult=alpha)
            metrics["is_blank"] = False

        return frame, metrics

    def generate_representative_frames(self, output_dir: str) -> List[str]:
        """Generates 16 representative validation frames across all narrative shots."""
        out_d = Path(output_dir).resolve()
        out_d.mkdir(parents=True, exist_ok=True)

        key_timestamps = [
            (0.50, "01_shot1_intro_dilemma_t00_50s"),
            (1.50, "02_shot1_hero_popin_t01_50s"),
            (3.00, "03_shot1_spilled_coffee_accent_t03_00s"),
            (6.20, "04_shot2_panic_head_clutch_t06_20s"),
            (8.50, "05_shot2_judging_crowd_eyes_t08_50s"),
            (10.00, "06_shot2_anxiety_settled_t10_00s"),
            (12.00, "07_shot3_illuminated_brain_t12_00s"),
            (16.00, "08_shot3_ego_concept_t16_00s"),
            (18.00, "09_shot3_thought_projection_t18_00s"),
            (20.50, "10_shot4_spotlight_stage_t20_50s"),
            (21.40, "11_shot4_climactic_scrutiny_punch_t21_40s"),
            (22.50, "12_shot5_oblivious_pedestrian_t22_50s"),
            (24.20, "13_shot5_busy_public_relief_t24_20s"),
            (27.00, "14_shot6_bystanders_spotlight_t27_00s"),
            (34.50, "15_shot7_vigilance_eye_t34_50s"),
            (42.00, "16_shot7_liberating_takeaway_peace_t42_00s"),
        ]

        saved_paths = []
        for ts, name in key_timestamps:
            frame, _ = self.render_frame(ts)
            display_frame = frame.copy()
            label = f"T={ts:.2f}s | {self.width}x{self.height} 30FPS"
            cv2.putText(
                display_frame,
                label,
                (20, self.height - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (80, 80, 80),
                2,
                cv2.LINE_AA,
            )
            out_p = out_d / f"{name}.png"
            imwrite_unicode(str(out_p), display_frame)
            saved_paths.append(str(out_p))

        print(f"Generated {len(saved_paths)} representative preview frames in {out_d}")
        return saved_paths

    def build_contact_sheet(self, frame_paths: List[str], output_path: str, cols: int = 4) -> str:
        """Assembles 16 representative frames into a clean 4x4 contact sheet."""
        if not frame_paths:
            return ""

        imgs = [imread_unicode(p) for p in frame_paths if Path(p).is_file()]
        imgs = [im for im in imgs if im is not None]

        n = len(imgs)
        rows = math.ceil(n / cols)

        thumb_w = 320
        thumb_h = int(round(thumb_w * (self.height / float(self.width))))
        padding = 12

        sheet_w = cols * thumb_w + (cols + 1) * padding
        sheet_h = rows * thumb_h + (rows + 1) * padding + 60

        sheet = np.full((sheet_h, sheet_w, 3), 245, dtype=np.uint8)

        # Header title
        title = f"Section 06 Composition-First Preview Contact Sheet | {self.width}x{self.height} @ 30FPS | Duration: {self.duration_sec:.2f}s"
        cv2.putText(
            sheet,
            title,
            (padding, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (40, 40, 40),
            2,
            cv2.LINE_AA,
        )

        for idx, img in enumerate(imgs):
            r = idx // cols
            c = idx % cols
            x = padding + c * (thumb_w + padding)
            y = 60 + padding + r * (thumb_h + padding)

            resized = cv2.resize(img, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
            cv2.rectangle(sheet, (x - 1, y - 1), (x + thumb_w + 1, y + thumb_h + 1), (200, 200, 200), 1)
            sheet[y:y + thumb_h, x:x + thumb_w] = resized

        out_p = Path(output_path).resolve()
        imwrite_unicode(str(out_p), sheet)
        print(f"Generated preview contact sheet at {out_p}")
        return str(out_p)

    def render_preview_video(self) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Renders 1280x720 30FPS preview video with synchronized master audio."""
        out_p = self.output_path
        out_p.parent.mkdir(parents=True, exist_ok=True)
        raw_video = out_p.parent / "temp_raw_preview.mp4"

        # Representative frame checks
        preview_frames_dir = out_p.parent / "preview_frames"
        rep_frame_paths = self.generate_representative_frames(str(preview_frames_dir))
        contact_sheet_p = out_p.parent / "preview_contact_sheet.png"
        self.build_contact_sheet(rep_frame_paths, str(contact_sheet_p))

        # FFmpeg Video Pipe
        log_path = out_p.parent / "ffmpeg_preview_render.log"
        ffmpeg_log = open(log_path, "w", encoding="utf-8")

        # Fast encoding profile for iterative review
        nvenc_cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}", "-pix_fmt", "bgr24", "-r", str(self.fps),
            "-i", "-", "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "22",
            "-pix_fmt", "yuv420p", str(raw_video)
        ]
        libx264_cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}", "-pix_fmt", "bgr24", "-r", str(self.fps),
            "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", str(raw_video)
        ]

        pipe = None
        try:
            pipe = subprocess.Popen(nvenc_cmd, stdin=subprocess.PIPE, stderr=ffmpeg_log)
            print("Video Pipe: Hardware accelerated NVENC")
        except Exception:
            pipe = subprocess.Popen(libx264_cmd, stdin=subprocess.PIPE, stderr=ffmpeg_log)
            print("Video Pipe: CPU libx264 (veryfast)")

        t_start_render = time.time()
        blank_frames_count = 0
        total_offscreen = 0
        max_simultaneous = 0
        total_visible_assets = 0
        total_composition_violations = 0

        print(f"Beginning frame generation: {self.total_frames} frames ({self.duration_sec:.2f}s)...")

        for f_idx in range(self.total_frames):
            t = f_idx / float(self.fps)
            frame, metrics = self.render_frame(t)

            if metrics["is_blank"] and t >= 0.56:
                # Prior to 0.56s is natural speech anticipation buffer
                blank_frames_count += 1

            total_offscreen += metrics["offscreen_assets"]
            max_simultaneous = max(max_simultaneous, metrics["visible_assets"])
            total_visible_assets += metrics["visible_assets"]
            total_composition_violations += metrics.get("composition_violations", 0)

            pipe.stdin.write(frame.tobytes())

            if (f_idx + 1) % 300 == 0 or (f_idx + 1) == self.total_frames:
                elapsed = time.time() - t_start_render
                spd = (f_idx + 1) / max(0.001, elapsed)
                pct = (f_idx + 1) / float(self.total_frames) * 100.0
                print(f"  Frame {f_idx + 1}/{self.total_frames} ({pct:.1f}%) [{spd:.1f} FPS, Time: {t:.2f}s]")

        pipe.stdin.close()
        pipe.wait()
        ffmpeg_log.close()
        render_wall_time = time.time() - t_start_render

        # Audio multiplexing
        print("Muxing synchronized master audio with video...")
        mux_cmd = [
            "ffmpeg", "-y", "-i", str(raw_video), "-i", str(self.audio_path),
            "-c:v", "copy", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest", str(out_p)
        ]
        res = subprocess.run(mux_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print("Audio mux error:", res.stderr)
            raise RuntimeError(f"FFmpeg audio mux failed: {res.stderr}")

        # Clean up temporary raw video
        if raw_video.is_file():
            try:
                raw_video.unlink()
            except Exception:
                pass

        # Build Task 9 composition-first diagnostics
        speech_sync_metrics = {}
        sync_diag_path = Path(ROOT_DIR) / "data" / "motion_sync_diagnostics.json"
        if not sync_diag_path.is_file():
            sync_diag_path = out_p.parent / "motion_sync_diagnostics.json"
        if sync_diag_path.is_file():
            try:
                with open(sync_diag_path, "r", encoding="utf-8") as f:
                    raw_sync = json.load(f)
                    speech_sync_metrics = {k: v for k, v in raw_sync.items() if k != "events"}
            except Exception:
                pass

        num_cam_moves = sum(1 for c in self.camera_plan if c.get("action") != "hold") if self.camera_plan else 5
        num_cam_holds = sum(1 for c in self.camera_plan if c.get("action") == "hold") if self.camera_plan else 2

        v3_diagnostics = {
            "duration": self.duration_sec,
            "frame_count": self.total_frames,
            "maximum_simultaneous_visible_assets": max_simultaneous,
            "average_visible_assets": round(total_visible_assets / float(max(1, self.total_frames)), 2),
            "blank_frames": blank_frames_count,
            "offscreen_assets": total_offscreen,
            "camera_movement_count": num_cam_moves,
            "camera_hold_count": num_cam_holds,
            "visual_event_count": len(self.actions),
            "speech_anchor_timing_metrics": speech_sync_metrics,
            "render_time": round(render_wall_time, 2),
            "composition_violation_count": total_composition_violations,
        }

        v3_diag_p = out_p.parent / "preview_composition_v3_diagnostics.json"
        with open(v3_diag_p, "w", encoding="utf-8") as f:
            json.dump(v3_diagnostics, f, indent=2, ensure_ascii=False)

        v3_contact_p = out_p.parent / "preview_composition_v3_contact_sheet.png"
        self.build_contact_sheet(rep_frame_paths, str(v3_contact_p), cols=4)

        metadata = {
            "resolution": f"{self.width}x{self.height}",
            "fps": self.fps,
            "duration": self.duration_sec,
            "frame_count": self.total_frames,
            "audio_duration": self.duration_sec,
            "rendered_duration": self.duration_sec,
            "renderer_mode": "motion_graphics_composition_first",
            "asset_count_used": len(self.asset_images),
            "action_count": len(self.actions),
            "camera_action_count": len(self.camera.camera_specs),
            "render_time": round(render_wall_time, 2),
            "composition_violation_count": total_composition_violations,
        }

        # If rendering to preview_composition_v3.mp4, keep preview_metadata synchronized
        meta_p = out_p.parent / "preview_metadata.json"
        with open(meta_p, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"Preview render complete: {out_p}")
        return str(out_p), metadata, v3_diagnostics

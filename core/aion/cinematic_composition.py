"""Cinematic Composition & 2.5D Cinematography Engine (Phase 4 of AION Creative Studio V5).

Computes adaptive 2.5D spatial layouts with safe-margin enforcement,
Z-depth parallax compensation, camera choreography (push, pan, orbit,
rack focus), and targeted Spot/Ambient lighting rigs for EffectCraft.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


# Depth plane Z offsets (comp camera sits near z = -1600 with zoom ~ 1600)
DEPTH_PLANES_Z: Dict[str, float] = {
    "far_backdrop": 520.0,
    "mid_stage": 140.0,
    "hero": 0.0,
    "foreground_callout": -140.0,
    "atmosphere": -280.0,
}


def apparent_scale_for_depth(z_layer: float, camera_z: float = -1600.0, zoom: float = 1600.0) -> float:
    """Scale compensation factor so a 3D layer at `z_layer` preserves intended screen framing."""
    dist = max(200.0, float(z_layer) - float(camera_z))
    return round((dist / max(200.0, float(zoom))) * 100.0, 2)


class CinematicCompositionEngine:
    """Plans safe layouts, 2.5D planes, camera moves, and lighting setups."""

    def __init__(self, width: int = 1920, height: int = 1080, safe_margin_px: int = 96):
        self.width = int(width)
        self.height = int(height)
        self.safe_margin_px = int(safe_margin_px)
        self.cx = self.width / 2.0
        self.cy = self.height / 2.0

    def clamp_to_safe_zone(
        self,
        pos_xy: Tuple[float, float],
        elem_w: float = 240.0,
        elem_h: float = 160.0,
    ) -> List[float]:
        """Clamp an element's center coordinate inside safe visible canvas margins."""
        half_w = min(elem_w * 0.5, self.width * 0.35)
        half_h = min(elem_h * 0.5, self.height * 0.35)
        min_x = self.safe_margin_px + half_w
        max_x = self.width - self.safe_margin_px - half_w
        min_y = self.safe_margin_px + half_h
        max_y = self.height - self.safe_margin_px - half_h
        x = max(min_x, min(max_x, float(pos_xy[0])))
        y = max(min_y, min(max_y, float(pos_xy[1])))
        return [round(x, 1), round(y, 1)]

    def layout_slots(self, mode: str, count: int) -> List[List[float]]:
        """Compute balanced composition coordinates cleanly inside safe margins."""
        w, h = self.width, self.height
        if mode == "split_polarity":
            return [[round(w * 0.28, 1), round(h * 0.50, 1)], [round(w * 0.72, 1), round(h * 0.50, 1)]]
        if mode == "hero_left_diagram_right":
            slots = [[round(w * 0.30, 1), round(h * 0.50, 1)]]
            n_r = max(1, count - 1)
            for i in range(n_r):
                frac = (i + 0.5) / n_r
                slots.append([round(w * 0.68, 1), round(h * (0.28 + 0.44 * frac), 1)])
            return slots[:count]
        if mode == "radial_hub":
            slots = [[round(self.cx, 1), round(self.cy, 1)]]
            satellites = max(1, count - 1)
            rx, ry = w * 0.30, h * 0.28
            for i in range(satellites):
                ang = (2.0 * math.pi * i) / satellites - math.pi / 2.0
                slots.append(self.clamp_to_safe_zone((self.cx + math.cos(ang) * rx, self.cy + math.sin(ang) * ry), 220, 160))
            return slots[:count]
        # Default adaptive horizontal / grid spread
        n = max(1, count)
        if n == 1:
            return [[round(self.cx, 1), round(self.cy, 1)]]
        cols = min(3, n)
        rows = (n + cols - 1) // cols
        slots: List[List[float]] = []
        x_span = w - 2 * self.safe_margin_px - 260
        y_span = h - 2 * self.safe_margin_px - 220
        for idx in range(n):
            r, c = idx // cols, idx % cols
            fx = (c + 0.5) / cols
            fy = (r + 0.5) / rows
            slots.append([
                round(self.safe_margin_px + 130 + x_span * fx, 1),
                round(self.safe_margin_px + 110 + y_span * fy, 1),
            ])
        return slots

    def build_camera_choreography(
        self,
        profile: str,
        t_start: float,
        t_end: float,
        *,
        focus_poi: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Generate smooth 3D camera keyframes tuned to the narrative profile."""
        cx, cy = self.cx, self.cy
        poi = list(focus_poi) if focus_poi else [cx, cy, 0.0]
        base_z = -1650.0
        t_mid = round((t_start + t_end) * 0.5, 3)

        if profile in ("dramatic_push_in", "slow_push_in", "tension_tighten_release"):
            keys = [
                {"time": round(t_start, 3), "pos": [cx - 40.0, cy + 15.0, base_z - 140.0], "poi": poi},
                {"time": t_mid, "pos": [poi[0], poi[1], base_z + 180.0], "poi": poi},
                {"time": round(t_end, 3), "pos": [poi[0] + 25.0, poi[1] - 10.0, base_z + 320.0], "poi": poi},
            ]
        elif profile in ("lateral_pan_track", "follow_vector_pan"):
            keys = [
                {"time": round(t_start, 3), "pos": [cx - 180.0, cy, base_z], "poi": [cx - 110.0, cy, 0.0]},
                {"time": t_mid, "pos": [cx, cy - 20.0, base_z + 110.0], "poi": [cx, cy, 0.0]},
                {"time": round(t_end, 3), "pos": [cx + 180.0, cy, base_z + 40.0], "poi": [cx + 110.0, cy, 0.0]},
            ]
        elif profile in ("establishing_orbit", "orbital_drift", "slow_cinematic_drift"):
            keys = [
                {"time": round(t_start, 3), "pos": [cx - 190.0, cy - 60.0, base_z - 90.0], "poi": poi},
                {"time": t_mid, "pos": [cx + 40.0, cy + 25.0, base_z + 160.0], "poi": poi},
                {"time": round(t_end, 3), "pos": [cx + 170.0, cy - 35.0, base_z + 80.0], "poi": poi},
            ]
        elif profile == "pull_back_resolve":
            keys = [
                {"time": round(t_start, 3), "pos": [cx, cy, base_z + 260.0], "poi": poi},
                {"time": round(t_end, 3), "pos": [cx, cy, base_z - 180.0], "poi": poi},
            ]
        else:
            keys = [
                {"time": round(t_start, 3), "pos": [cx - 35.0, cy, base_z], "poi": poi},
                {"time": round(t_end, 3), "pos": [cx + 35.0, cy, base_z + 120.0], "poi": poi},
            ]

        return {
            "enabled": True,
            "mode": profile,
            "zoom": 1650.0,
            "preset": "35mm",
            "keyframes": keys,
        }

    def build_lighting_rig(
        self,
        profile: str,
        t_start: float,
        t_end: float,
        *,
        accent_color: str = "#FFD400",
        is_light_bg: bool = False,
        target_xy: Optional[Tuple[float, float]] = None,
    ) -> Dict[str, Any]:
        """Design Spot/Ambient light rig + sweep schedule tailored to dark vs warm stages."""
        tx, ty = target_xy if target_xy else (self.cx, self.cy)
        if is_light_bg:
            # Bright warm surfaces avoid overexposed washout: rely on directional soft sweep & shadow relief
            return {
                "enabled": False,
                "lights": [],
                "sweeps": [
                    {"time": round(t_start + 0.45, 3), "duration": 0.65, "color": accent_color, "intensity": 18.0}
                ],
                "drop_shadows": True,
            }

        intensity = 150.0 if profile in ("dramatic_key_spot", "high_contrast_spot", "target_spotlight_shift") else 120.0
        lights = [
            {
                "name": "KeySpot",
                "kind": "Spot",
                "color": "#FFFFFF",
                "intensity": intensity,
                "coneAngle": 118.0,
                "coneFeather": 80.0,
                "castsShadows": True,
                "shadowDarkness": 74.0,
                "keyframes": [
                    {"time": round(t_start, 3), "pos": [round(tx - 240.0, 1), round(ty - 220.0, 1), -860.0], "poi": [round(tx, 1), round(ty, 1), 0.0]},
                    {"time": round(t_end, 3), "pos": [round(tx + 200.0, 1), round(ty - 180.0, 1), -820.0], "poi": [round(tx, 1), round(ty, 1), 0.0]},
                ],
            },
            {
                "name": "FillAmbient",
                "kind": "Ambient",
                "color": "#FFFFFF",
                "intensity": 72.0,
                "castsShadows": False,
            },
        ]
        return {
            "enabled": True,
            "lights": lights,
            "sweeps": [{"time": round(t_start + 0.5, 3), "duration": 0.6, "color": accent_color, "intensity": 24.0}],
            "drop_shadows": True,
        }

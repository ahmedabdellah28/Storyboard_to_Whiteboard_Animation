"""Procedural Graphics Engine (Phase 3 of AION Creative Studio V5).

Generates native EffectCraft vector geometry descriptors, SVG icon imports
(reusing `creative_v3/asset_factory`), infographics, timelines, flowcharts,
comparison panels, network node maps, scientific/tech/historical emblems,
animated Bezier arrows, and kinetic typography specs (RTL Arabic & LTR).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from creative_v3.asset_factory.factory import BRAND_ICONS_40, PROPS_20, normalize_icon_svg
except Exception:
    BRAND_ICONS_40 = {}
    PROPS_20 = {}

    def normalize_icon_svg(icon_id: str, inner_svg: str) -> str:
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">{inner_svg}</svg>'


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ASSET_FACTORY_DIR = ROOT_DIR / "creative_v3" / "asset_factory"


def _to_shape_local(pt: Tuple[float, float], comp_w: int, comp_h: int) -> List[float]:
    """Convert composition pixel coordinates (x, y) to EffectCraft Shape layer center-relative coords."""
    return [round(float(pt[0]) - comp_w / 2.0, 2), round(float(pt[1]) - comp_h / 2.0, 2)]


def is_rtl_text(text: str) -> bool:
    """Detect presence of Arabic / Hebrew RTL characters."""
    for ch in text or "":
        code = ord(ch)
        if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F or 0xFB50 <= code <= 0xFDFF or 0xFE70 <= code <= 0xFEFF:
            return True
    return False


# Additional procedural SVG icons beyond asset_factory's 40 icons + 20 props.
_DOMAIN_SVG_ICONS: Dict[str, str] = {
    "neuron_network": (
        '<circle cx="16" cy="18" r="6" fill="#00D4C0" stroke="#F8FAFC" stroke-width="2.5"/>'
        '<circle cx="48" cy="18" r="6" fill="#38BDF8" stroke="#F8FAFC" stroke-width="2.5"/>'
        '<circle cx="32" cy="48" r="7" fill="#FFD400" stroke="#F8FAFC" stroke-width="2.5"/>'
        '<path d="M21 21 L42 19 M19 23 L29 42 M45 23 L35 42" stroke="#F8FAFC" stroke-width="2.8" fill="none" stroke-linecap="round"/>'
    ),
    "wave_signal": (
        '<path d="M6 34 C14 14, 22 52, 32 32 C42 12, 50 50, 58 30" fill="none" stroke="#00D4C0" stroke-width="4.5" stroke-linecap="round"/>'
        '<circle cx="58" cy="30" r="4" fill="#FFD400"/>'
    ),
    "dna_helix": (
        '<path d="M18 10 C46 22, 18 42, 46 54 M46 10 C18 22, 46 42, 18 54" fill="none" stroke="#38BDF8" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="22" y1="20" x2="42" y2="20" stroke="#FFD400" stroke-width="3"/>'
        '<line x1="22" y1="44" x2="42" y2="44" stroke="#FFD400" stroke-width="3"/>'
    ),
    "circuit_chip": (
        '<rect x="18" y="18" width="28" height="28" rx="4" fill="#1E293B" stroke="#00D4C0" stroke-width="3.5"/>'
        '<rect x="26" y="26" width="12" height="12" rx="2" fill="#FFD400"/>'
        '<path d="M26 10v8 M38 10v8 M26 46v8 M38 46v8 M10 26h8 M10 38h8 M46 26h8 M46 38h8" stroke="#38BDF8" stroke-width="3" stroke-linecap="round"/>'
    ),
    "archival_scroll": (
        '<rect x="14" y="12" width="36" height="40" rx="5" fill="#EDE8E0" stroke="#F59E0B" stroke-width="3.5"/>'
        '<path d="M22 24h20 M22 33h20 M22 42h14" stroke="#1E293B" stroke-width="3" stroke-linecap="round"/>'
    ),
    "balance_scale": (
        '<path d="M32 12v40 M18 52h28 M14 22l36-4" stroke="#F8FAFC" stroke-width="3.5" stroke-linecap="round"/>'
        '<path d="M10 36 L14 22 L18 36 Z M46 32 L50 18 L54 32 Z" fill="#00D4C0" stroke="#F8FAFC" stroke-width="2"/>'
    ),
}


class ProceduralGraphicsEngine:
    """Produces parametric vector geometry, diagrams, icons, and typography specs."""

    def __init__(self, comp_width: int = 1920, comp_height: int = 1080):
        self.comp_width = comp_width
        self.comp_height = comp_height

    @staticmethod
    def available_icons() -> List[str]:
        return sorted(set(BRAND_ICONS_40.keys()) | set(_DOMAIN_SVG_ICONS.keys()))

    def get_svg_icon_markup(
        self,
        icon_id: str,
        *,
        stroke_override: Optional[str] = None,
        fill_override: Optional[str] = None,
    ) -> Optional[str]:
        """Resolve an editable SVG markup string from `asset_factory` or domain icon set."""
        key = (icon_id or "").strip().lower()
        if key in _DOMAIN_SVG_ICONS:
            svg = normalize_icon_svg(key, _DOMAIN_SVG_ICONS[key])
        elif key in BRAND_ICONS_40:
            svg = normalize_icon_svg(key, BRAND_ICONS_40[key])
        elif key in PROPS_20:
            inner = PROPS_20[key]["svg"]
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-50 -60 120 120" width="120" height="120">{inner}</svg>'
        else:
            svg_file = ASSET_FACTORY_DIR / "icons" / f"{key}.svg"
            if not svg_file.exists():
                return None
            svg = svg_file.read_text(encoding="utf-8")

        if stroke_override:
            svg = svg.replace("#0B0C10", stroke_override)
        if fill_override:
            svg = svg.replace("#0072CE", fill_override)
        return svg

    def build_bezier_connector(
        self,
        element_id: str,
        start_xy: Tuple[float, float],
        end_xy: Tuple[float, float],
        *,
        curvature: float = 0.25,
        stroke_color: str = "#38BDF8",
        stroke_width: float = 8.0,
        start_time: float = 0.0,
        draw_duration: float = 0.75,
        end_time: float = 5.0,
        with_arrow: bool = False,
        dashed: bool = False,
        layer_3d: bool = False,
        z_depth: float = 0.0,
    ) -> Dict[str, Any]:
        """Build a native EffectCraft curved Bezier stroke (+ optional synced arrowhead)."""
        x0, y0 = float(start_xy[0]), float(start_xy[1])
        x1, y1 = float(end_xy[0]), float(end_xy[1])
        dx, dy = x1 - x0, y1 - y0
        dist = max(1.0, math.hypot(dx, dy))
        nx, ny = -dy / dist, dx / dist
        mx, my = (x0 + x1) * 0.5 + nx * dist * curvature, (y0 + y1) * 0.5 + ny * dist * curvature

        p0 = _to_shape_local((x0, y0), self.comp_width, self.comp_height)
        pm = _to_shape_local((mx, my), self.comp_width, self.comp_height)
        p1 = _to_shape_local((x1, y1), self.comp_width, self.comp_height)

        tan_len = dist * 0.18
        ux, uy = dx / dist, dy / dist
        head_vertices: Optional[List[List[float]]] = None
        if with_arrow:
            # Tangent near end_xy from midpoint -> end_xy
            tx, ty = x1 - mx, y1 - my
            tlen = max(1.0, math.hypot(tx, ty))
            ax, ay = tx / tlen, ty / tlen
            px_n, py_n = -ay, ax
            ah_len = max(20.0, stroke_width * 2.4)
            ah_half = max(12.0, stroke_width * 1.45)
            tip = (x1 + ax * (ah_len * 0.35), y1 + ay * (ah_len * 0.35))
            base_l = (x1 - ax * (ah_len * 0.65) + px_n * ah_half, y1 - ay * (ah_len * 0.65) + py_n * ah_half)
            base_r = (x1 - ax * (ah_len * 0.65) - px_n * ah_half, y1 - ay * (ah_len * 0.65) - py_n * ah_half)
            head_vertices = [
                _to_shape_local(base_l, self.comp_width, self.comp_height),
                _to_shape_local(tip, self.comp_width, self.comp_height),
                _to_shape_local(base_r, self.comp_width, self.comp_height),
            ]

        return {
            "kind": "bezier_arrow" if with_arrow else "bezier_connector",
            "id": element_id,
            "start": round(start_time, 3),
            "end": round(end_time, 3),
            "draw_duration": round(draw_duration, 3),
            "vertices": [p0, pm, p1],
            "in_tangents": [[0.0, 0.0], [round(-ux * tan_len, 2), round(-uy * tan_len, 2)], [0.0, 0.0]],
            "out_tangents": [[round(ux * tan_len * 0.6, 2), round(uy * tan_len * 0.6, 2)], [round(ux * tan_len, 2), round(uy * tan_len, 2)], [0.0, 0.0]],
            "stroke_color": stroke_color,
            "stroke_width": stroke_width,
            "dashed": dashed,
            "with_arrow": with_arrow,
            "arrow_head_vertices": head_vertices,
            "three_d": layer_3d,
            "z": z_depth,
        }

    def build_network_diagram(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Tuple[int, int]],
        *,
        palette: Dict[str, Any],
        t_start: float,
        t_end: float,
        prefix: str = "net",
    ) -> List[Dict[str, Any]]:
        """Generate interconnected procedural network nodes + animated Bezier arrows."""
        specs: List[Dict[str, Any]] = []
        n_count = max(1, len(nodes))
        # Nodes
        for idx, node in enumerate(nodes):
            st = t_start + idx * min(0.22, max(0.08, (t_end - t_start) / (n_count * 3.0)))
            pos = node.get("position", [self.comp_width * 0.5, self.comp_height * 0.5])
            r = float(node.get("radius", 62))
            specs.append({
                "kind": "shape_node",
                "id": f"{prefix}_node_{idx}",
                "shape": node.get("shape", "ellipse"),
                "size": [r * 2.0, r * 2.0],
                "position": [float(pos[0]), float(pos[1])],
                "fill": node.get("fill", palette.get("surface", "#162033")),
                "stroke": node.get("stroke", palette.get("primary", "#00D4C0")),
                "stroke_width": float(node.get("stroke_width", 5.0)),
                "start": round(st, 3),
                "end": round(t_end, 3),
                "icon": node.get("icon"),
                "label": node.get("label", ""),
                "label_color": palette.get("text", "#F8FAFC"),
                "three_d": bool(node.get("three_d", False)),
                "z": float(node.get("z", 0.0)),
            })
        # Directed edges with curved Trim Arrows
        edge_base = t_start + 0.35
        for eidx, (u, v) in enumerate(edges):
            if 0 <= u < len(nodes) and 0 <= v < len(nodes):
                p_u = nodes[u].get("position", [400, 400])
                p_v = nodes[v].get("position", [800, 400])
                curve = 0.22 if eidx % 2 == 0 else -0.22
                specs.append(
                    self.build_bezier_connector(
                        f"{prefix}_edge_{eidx}",
                        (p_u[0], p_u[1]),
                        (p_v[0], p_v[1]),
                        curvature=curve,
                        stroke_color=palette.get("accent", "#F59E0B") if eidx % 2 else palette.get("primary", "#00D4C0"),
                        stroke_width=7.0,
                        start_time=edge_base + eidx * 0.18,
                        draw_duration=0.65,
                        end_time=t_end,
                        with_arrow=True,
                    )
                )
        return specs

    def build_timeline_diagram(
        self,
        milestones: List[Dict[str, Any]],
        *,
        palette: Dict[str, Any],
        t_start: float,
        t_end: float,
        y_center: Optional[float] = None,
        rtl: bool = True,
    ) -> List[Dict[str, Any]]:
        """Generate an animated horizontal timeline spine with milestone pins and callout cards."""
        specs: List[Dict[str, Any]] = []
        yc = float(y_center if y_center is not None else self.comp_height * 0.62)
        margin_x = self.comp_width * 0.14
        x_start = self.comp_width - margin_x if rtl else margin_x
        x_end = margin_x if rtl else self.comp_width - margin_x

        specs.append(
            self.build_bezier_connector(
                "timeline_spine",
                (x_start, yc),
                (x_end, yc),
                curvature=0.0,
                stroke_color=palette.get("primary", "#38BDF8"),
                stroke_width=8.0,
                start_time=t_start,
                draw_duration=min(0.9, max(0.35, (t_end - t_start) * 0.3)),
                end_time=t_end,
                with_arrow=True,
            )
        )

        m_count = max(1, len(milestones))
        for i, ms in enumerate(milestones):
            frac = (i + 0.5) / m_count if m_count > 1 else 0.5
            x = x_start + (x_end - x_start) * frac
            dy = -135.0 if i % 2 == 0 else 135.0
            st = t_start + 0.25 + i * min(0.35, max(0.12, (t_end - t_start) / (m_count * 2.5)))
            specs.append({
                "kind": "shape_node",
                "id": f"timeline_pin_{i}",
                "shape": "ellipse",
                "size": [34.0, 34.0],
                "position": [round(x, 1), round(yc, 1)],
                "fill": palette.get("accent", "#FFD400"),
                "stroke": palette.get("surface", "#1E293B"),
                "stroke_width": 5.0,
                "start": round(st, 3),
                "end": round(t_end, 3),
            })
            specs.append({
                "kind": "badge_card",
                "id": f"timeline_card_{i}",
                "title": str(ms.get("label", f"Step {i + 1}")),
                "subtitle": str(ms.get("detail", "")),
                "position": [round(x, 1), round(yc + dy, 1)],
                "size": [270.0, 108.0],
                "fill": palette.get("surface", "#1E293B"),
                "stroke": palette.get("primary", "#38BDF8"),
                "text_color": palette.get("text", "#F8FAFC"),
                "start": round(st + 0.08, 3),
                "end": round(t_end, 3),
            })
        return specs

    def build_comparison_panel(
        self,
        left_item: Dict[str, Any],
        right_item: Dict[str, Any],
        *,
        palette: Dict[str, Any],
        t_start: float,
        t_end: float,
    ) -> List[Dict[str, Any]]:
        """Generate a split two-column editorial comparison panel with animated divider."""
        cx, cy = self.comp_width * 0.5, self.comp_height * 0.52
        col_w = self.comp_width * 0.34
        col_h = self.comp_height * 0.52
        offset_x = self.comp_width * 0.22
        return [
            {
                "kind": "badge_card",
                "id": "compare_left",
                "title": str(left_item.get("title", "A")),
                "subtitle": str(left_item.get("subtitle", "")),
                "position": [round(cx - offset_x, 1), round(cy, 1)],
                "size": [round(col_w, 1), round(col_h, 1)],
                "fill": palette.get("surface", "#1E293B"),
                "stroke": left_item.get("color", palette.get("secondary", "#00A99D")),
                "text_color": palette.get("text", "#F8FAFC"),
                "start": round(t_start, 3),
                "end": round(t_end, 3),
            },
            {
                "kind": "badge_card",
                "id": "compare_right",
                "title": str(right_item.get("title", "B")),
                "subtitle": str(right_item.get("subtitle", "")),
                "position": [round(cx + offset_x, 1), round(cy, 1)],
                "size": [round(col_w, 1), round(col_h, 1)],
                "fill": palette.get("surface", "#1E293B"),
                "stroke": right_item.get("color", palette.get("accent", "#FFD400")),
                "text_color": palette.get("text", "#F8FAFC"),
                "start": round(t_start + 0.22, 3),
                "end": round(t_end, 3),
            },
            self.build_bezier_connector(
                "compare_divider",
                (cx, cy - col_h * 0.48),
                (cx, cy + col_h * 0.48),
                curvature=0.0,
                stroke_color=palette.get("accent", "#FFD400"),
                stroke_width=5.0,
                start_time=t_start + 0.1,
                draw_duration=0.45,
                end_time=t_end,
                with_arrow=False,
            ),
        ]

    def build_bar_chart(
        self,
        bars: List[Dict[str, Any]],
        *,
        palette: Dict[str, Any],
        t_start: float,
        t_end: float,
        origin_xy: Optional[Tuple[float, float]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate animated vertical bar-chart infographic with axis line and labels."""
        ox, oy = origin_xy if origin_xy else (self.comp_width * 0.26, self.comp_height * 0.74)
        chart_w = self.comp_width * 0.48
        max_h = self.comp_height * 0.36
        specs: List[Dict[str, Any]] = [
            self.build_bezier_connector(
                "chart_axis_x",
                (ox, oy),
                (ox + chart_w, oy),
                curvature=0.0,
                stroke_color=palette.get("text_muted", "#94A3B8"),
                stroke_width=5.0,
                start_time=t_start,
                draw_duration=0.4,
                end_time=t_end,
            )
        ]
        n = max(1, len(bars))
        bar_w = min(96.0, (chart_w / n) * 0.56)
        max_val = max([float(b.get("value", 1.0)) for b in bars] + [1.0])
        for idx, b in enumerate(bars):
            val = max(0.0, float(b.get("value", 1.0)))
            h = max(24.0, (val / max_val) * max_h)
            bx = ox + (idx + 0.5) * (chart_w / n)
            specs.append({
                "kind": "chart_bar",
                "id": f"chart_bar_{idx}",
                "position": [round(bx, 1), round(oy - h * 0.5, 1)],
                "size": [round(bar_w, 1), round(h, 1)],
                "fill": b.get("color", palette.get("primary", "#38BDF8") if idx % 2 == 0 else palette.get("accent", "#FFD400")),
                "stroke": palette.get("text", "#F8FAFC"),
                "label": str(b.get("label", "")),
                "value_text": str(b.get("display", int(val) if val.is_integer() else round(val, 1))),
                "text_color": palette.get("text", "#F8FAFC"),
                "start": round(t_start + 0.2 + idx * 0.14, 3),
                "end": round(t_end, 3),
            })
        return specs

    def build_concentric_rings(
        self,
        element_id: str,
        center_xy: Tuple[float, float],
        *,
        copies: int = 4,
        base_size: float = 120.0,
        stroke_color: str = "#00D4C0",
        t_start: float = 0.0,
        t_end: float = 4.0,
    ) -> Dict[str, Any]:
        """Build an EffectCraft native Repeater concentric geometric halo."""
        return {
            "kind": "repeater_rings",
            "id": element_id,
            "center": [float(center_xy[0]), float(center_xy[1])],
            "copies": max(2, int(copies)),
            "base_size": float(base_size),
            "stroke_color": stroke_color,
            "start": round(t_start, 3),
            "end": round(t_end, 3),
        }

    def build_kinetic_typography_block(
        self,
        element_id: str,
        text: str,
        *,
        position: Tuple[float, float],
        palette: Dict[str, Any],
        t_start: float,
        t_end: float,
        font_size: int = 68,
        font_family: str = "Cairo",
        with_backdrop: bool = True,
        animation_mode: str = "word_slide",
    ) -> Dict[str, Any]:
        """Create a safe kinetic typography block respecting RTL/Arabic shaping rules."""
        rtl = is_rtl_text(text)
        return {
            "kind": "kinetic_typography",
            "id": element_id,
            "text": text,
            "direction": "rtl" if rtl else "ltr",
            "font": font_family if rtl else "Cairo",
            "size": int(font_size),
            "position": [round(float(position[0]), 1), round(float(position[1]), 1)],
            "color": palette.get("text", "#F8FAFC"),
            "with_backdrop": bool(with_backdrop),
            "backdrop_fill": palette.get("surface", "#1E293B"),
            "backdrop_stroke": palette.get("accent", "#FFD400"),
            "animation_mode": animation_mode,
            # Force word-based selection on RTL Arabic to keep ligatures connected (verified in capability probe!)
            "animator_based_on": 2 if rtl else 0,
            "start": round(t_start, 3),
            "end": round(t_end, 3),
        }

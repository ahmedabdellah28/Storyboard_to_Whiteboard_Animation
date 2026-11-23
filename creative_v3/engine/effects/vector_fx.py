"""
Parametric SVG vector FX, props, tethers, typography, portals, and background
scene layers for Creative Stickman Studio V3.
All effects stay genuinely vector-based and attach to live world anchors.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple


def _glow_cube_svg(x: float, y: float, size: float = 48.0, t_norm: float = 0.5) -> str:
    s = size * 0.5
    return (
        f'<g transform="translate({x:.1f},{y:.1f}) rotate({math.sin(t_norm*6)*8:.1f})">'
        f'<polygon points="0,{-s:.1f} {s:.1f},{-s*0.45:.1f} {s:.1f},{s*0.55:.1f} 0,{s:.1f} {-s:.1f},{s*0.55:.1f} {-s:.1f},{-s*0.45:.1f}" '
        f'fill="#5CE1E6" fill-opacity="0.85" stroke="#0072CE" stroke-width="3.5" stroke-linejoin="round"/>'
        f'<polyline points="{-s:.1f},{-s*0.45:.1f} 0,{0:.1f} {s:.1f},{-s*0.45:.1f}" fill="none" stroke="#FFFFFF" stroke-width="2.5"/>'
        f'<line x1="0" y1="0" x2="0" y2="{s:.1f}" stroke="#FFFFFF" stroke-width="2.5"/>'
        f'</g>'
    )


def _energy_web_beam_svg(x1: float, y1: float, x2: float, y2: float, t_norm: float) -> str:
    dx = (x2 - x1) * min(1.0, t_norm * 1.4)
    dy = (y2 - y1) * min(1.0, t_norm * 1.4)
    out = []
    for fan in (-32, -16, 0, 16, 32):
        ex = x1 + dx
        ey = y1 + dy + fan * min(1.0, t_norm * 1.5)
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#00C4FF" stroke-width="3.2" stroke-linecap="round"/>')
    for step in (0.35, 0.65, 0.92):
        px = x1 + dx * step
        py1 = y1 + dy * step - 28 * step
        py2 = y1 + dy * step + 28 * step
        out.append(f'<line x1="{px:.1f}" y1="{py1:.1f}" x2="{px:.1f}" y2="{py2:.1f}" stroke="#7DF9FF" stroke-width="2.5"/>')
    return "".join(out)


def _vortex_portal_svg(cx: float, cy: float, t_norm: float) -> str:
    sc = min(1.0, t_norm * 1.6)
    rings = []
    for k, (rx, ry, col) in enumerate(((46, 118, "#0072CE"), (34, 92, "#00A99D"), (22, 62, "#5CE1E6"), (12, 34, "#0B0C10"))):
        rot = t_norm * 360 * (1 if k % 2 == 0 else -1)
        rings.append(
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx*sc:.1f}" ry="{ry*sc:.1f}" '
            f'fill="{"#0B0C10" if k==3 else "none"}" stroke="{col}" stroke-width="5" stroke-dasharray="22 10" '
            f'transform="rotate({rot*0.15:.1f} {cx:.1f} {cy:.1f})"/>'
        )
    return "".join(rings)


def _hologram_ring_svg(cx: float, cy: float, t_norm: float) -> str:
    r = 68.0 * min(1.0, t_norm * 1.5)
    return (
        f'<g transform="translate({cx:.1f},{cy:.1f}) rotate({t_norm*180:.1f})">'
        f'<circle cx="0" cy="0" r="{r:.1f}" fill="#5CE1E6" fill-opacity="0.18" stroke="#00A99D" stroke-width="4" stroke-dasharray="14 8"/>'
        f'<circle cx="0" cy="0" r="{r*0.72:.1f}" fill="none" stroke="#0072CE" stroke-width="3"/>'
        f'<polygon points="{r*0.45:.1f},0 {-r*0.28:.1f},{-r*0.36:.1f} {-r*0.28:.1f},{r*0.36:.1f}" fill="none" stroke="#5CE1E6" stroke-width="3.5"/>'
        f'</g>'
    )


def _card_svg(x: float, y: float, w: float, h: float, title: str, fill: str = "#0072CE", accent: str = "#FFD400", rot: float = 0.0, sx: float = 1.0, sy: float = 1.0, opacity: float = 1.0) -> str:
    return (
        f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({sx:.3f},{sy:.3f})" opacity="{opacity:.2f}">'
        f'<rect x="{-w/2:.1f}" y="{-h/2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4.5"/>'
        f'<rect x="{-w/2+8:.1f}" y="{-h/2+8:.1f}" width="{w-16:.1f}" height="18" rx="4" fill="{fill}"/>'
        f'<circle cx="{-w/2+24:.1f}" cy="{12:.1f}" r="11" fill="{accent}" stroke="#0B0C10" stroke-width="2.5"/>'
        f'<line x1="{-w/2+44:.1f}" y1="8" x2="{w/2-14:.1f}" y2="8" stroke="#1A1C22" stroke-width="4" stroke-linecap="round"/>'
        f'<line x1="{-w/2+44:.1f}" y1="20" x2="{w/2-26:.1f}" y2="20" stroke="#7A869A" stroke-width="3.5" stroke-linecap="round"/>'
        f'<text x="0" y="{-h/2+21:.1f}" text-anchor="middle" font-family="Arial,sans-serif" font-size="11" font-weight="bold" fill="#FFFFFF">{title}</text>'
        f'</g>'
    )


def render_action_fx(
    action_id: str,
    number: int,
    category: str,
    t_norm: float,
    anchors: Dict[str, Tuple[float, float]],
    params: dict,
) -> Tuple[str, str]:
    """
    Return (scene_svg_behind, scene_svg_front) for the given action at t_norm in [0, 1].
    """
    rp = anchors.get("right_palm", (480.0, 320.0))
    lp = anchors.get("left_palm", (360.0, 420.0))
    ft = anchors.get("fingertips", (520.0, 310.0))
    eyes = anchors.get("eyes", (440.0, 180.0))
    foot = anchors.get("foot", (470.0, 690.0))
    tc = (float(params.get("target_x", 720.0)), float(params.get("target_y", 320.0)))
    label = str(params.get("label", f"A{number:03d}"))

    behind = ""
    front = ""

    # Category A: Expressive Performance (001-010)
    if 1 <= number <= 10:
        if number == 2:
            # Target indicator & eye-track reticle
            front += f'<circle cx="{tc[0]:.1f}" cy="{tc[1]:.1f}" r="{22 + 6*math.sin(t_norm*12):.1f}" fill="none" stroke="#00A99D" stroke-width="4" stroke-dasharray="8 6"/>'
            front += f'<line x1="{eyes[0]:.1f}" y1="{eyes[1]:.1f}" x2="{tc[0]:.1f}" y2="{tc[1]:.1f}" stroke="#00A99D" stroke-width="2.5" stroke-dasharray="6 6" opacity="0.55"/>'
        elif number == 4 and t_norm > 0.45:
            # Epiphany lightbulb with rays (matches pose 23)
            sc = min(1.0, (t_norm - 0.45) * 4.0)
            front += (
                f'<g transform="translate({eyes[0]+55:.1f},{eyes[1]-110:.1f}) scale({sc:.2f})">'
                f'<circle cx="0" cy="0" r="22" fill="#FFD400" stroke="#0B0C10" stroke-width="4"/>'
                f'<path d="M -8,18 L 8,18 L 6,28 L -6,28 Z" fill="#CBD5E1" stroke="#0B0C10" stroke-width="3"/>'
                f'<line x1="0" y1="-34" x2="0" y2="-46" stroke="#FFD400" stroke-width="4" stroke-linecap="round"/>'
                f'<line x1="-26" y1="-22" x2="-36" y2="-30" stroke="#FFD400" stroke-width="4" stroke-linecap="round"/>'
                f'<line x1="26" y1="-22" x2="36" y2="-30" stroke="#FFD400" stroke-width="4" stroke-linecap="round"/>'
                f'</g>'
            )
        elif number == 5:
            # Hovering card to peek behind
            behind += _card_svg(tc[0] - 90, tc[1] + 20, 140, 190, "SECRET", "#1A1C22", "#00A99D")
        elif number == 6:
            # Surprise exclamation marks (matches pose 19)
            front += (
                f'<g transform="translate({eyes[0]+85:.1f},{eyes[1]-75:.1f})">'
                f'<line x1="0" y1="0" x2="12" y2="-28" stroke="#FFD400" stroke-width="6" stroke-linecap="round"/>'
                f'<line x1="16" y1="8" x2="36" y2="-14" stroke="#FFD400" stroke-width="6" stroke-linecap="round"/>'
                f'<line x1="24" y1="22" x2="48" y2="10" stroke="#FFD400" stroke-width="6" stroke-linecap="round"/>'
                f'</g>'
            )
        elif number in (7, 8):
            # Shock / landing / skid motion lines
            for k in range(4):
                yy = 220 + k * 75
                front += f'<line x1="80" y1="{yy}" x2="{140 + 40*math.sin(t_norm*10+k):.1f}" y2="{yy}" stroke="#0072CE" stroke-width="4" stroke-linecap="round" opacity="0.6"/>'
        elif number == 10:
            front += f'<path d="M 320,685 Q 460,{705+10*math.sin(t_norm*6):.1f} 600,685" fill="none" stroke="#FFD400" stroke-width="4" stroke-linecap="round" opacity="0.7"/>'

    # Category B: Physical Object Interaction (011-020)
    elif 11 <= number <= 20:
        if number == 11:
            sc = min(1.0, t_norm * 2.2)
            front += _card_svg(rp[0] + 60, rp[1] - 40 * t_norm, 120, 84, label, "#0072CE", "#FFD400", rot=-10 + 10 * t_norm, sx=sc, sy=sc)
        elif number == 12:
            cx = tc[0] * (1 - t_norm) + (rp[0] + 50) * t_norm
            front += _card_svg(cx, tc[1], 124, 86, "GRAB", "#00A99D", "#FFD400")
        elif number == 13:
            ang = t_norm * 2 * math.pi
            ox = tc[0] - 70 + 120 * math.cos(ang)
            oy = tc[1] - 80 + 90 * math.sin(ang)
            front += _card_svg(ox, oy, 110, 78, "ORBIT", "#0072CE", "#FFD400", rot=math.degrees(ang))
        elif number == 14:
            a1 = t_norm * 2 * math.pi
            front += _card_svg(560 + 90 * math.cos(a1), 240 + 70 * math.sin(a1), 100, 72, "A", "#0072CE", "#FFD400")
            front += _card_svg(560 - 90 * math.cos(a1), 240 - 70 * math.sin(a1), 100, 72, "B", "#00A99D", "#FFD400")
        elif number == 15:
            sx = max(0.25, 1.0 - 0.7 * t_norm)
            front += _card_svg(tc[0], tc[1], 220, 150, "FOLD", "#0072CE", "#FFD400", sx=sx, sy=max(0.35, sx))
        elif number == 16:
            sx = abs(math.cos(t_norm * math.pi))
            col = "#0072CE" if t_norm < 0.5 else "#00A99D"
            front += _card_svg(tc[0], tc[1], 150, 105, "FLIP" if t_norm < 0.5 else "REVEAL", col, "#FFD400", sx=max(0.08, sx))
        elif number == 17:
            for k in range(5):
                tilt = min(75.0, max(0.0, (t_norm - k * 0.14) * 260.0))
                front += _card_svg(540 + k * 65, 420, 56, 120, f"D{k+1}", "#0072CE", "#FFD400", rot=tilt)
        elif number == 18:
            for k in range(4):
                dx = (k - 1.5) * 85 * t_norm
                front += _card_svg(670 + dx, 310 + abs(k - 1.5) * 14 * t_norm, 95, 70, f"S{k+1}", "#0072CE", "#FFD400", rot=(k - 1.5) * 12 * t_norm)
        elif number == 19:
            arc_x = foot[0] + (tc[0] - foot[0]) * t_norm
            arc_y = foot[1] - 340 * math.sin(t_norm * math.pi)
            front += _card_svg(arc_x, arc_y, 110, 78, "KICK", "#FFD400", "#0072CE", rot=t_norm * 360)
        elif number == 20:
            for k in range(4):
                ang = k * 1.57 + t_norm * 6.0
                rad = 180 * (1.0 - t_norm) + 20
                front += _card_svg(rp[0] + 90 + rad * math.cos(ang), rp[1] + rad * math.sin(ang), 80, 58, f"V{k+1}", "#00A99D", "#FFD400")

    # Category C: Tethers, Thread, Grappling & Webs (021-030)
    elif 21 <= number <= 30:
        cx = tc[0] * (1.0 - 0.45 * t_norm)
        cy = tc[1] - 30 * math.sin(t_norm * math.pi)
        if number == 22:
            front += f'<circle cx="{tc[0]:.1f}" cy="{tc[1]:.1f}" r="58" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5"/>'
            front += f'<path d="M {rp[0]:.1f},{rp[1]:.1f} Q 580,210 {tc[0]:.1f},{tc[1]-62:.1f}" fill="none" stroke="#FFD400" stroke-width="5" stroke-dasharray="{int(300*t_norm)+10} 400"/>'
            front += f'<circle cx="{tc[0]:.1f}" cy="{tc[1]:.1f}" r="66" fill="none" stroke="#FFD400" stroke-width="5" stroke-dasharray="{int(420*t_norm)} 450"/>'
        elif number == 29:
            front += _energy_web_beam_svg(rp[0], rp[1], tc[0], tc[1], t_norm)
            front += _card_svg(tc[0], tc[1], 140, 96, "WEB", "#0072CE", "#FFD400", sx=min(1.0, t_norm * 1.6), sy=min(1.0, t_norm * 1.6))
        elif number == 30:
            front += _vortex_portal_svg(tc[0], tc[1], t_norm)
        elif number == 21:
            front += _energy_web_beam_svg(rp[0], rp[1], cx, cy, t_norm)
            front += _glow_cube_svg(cx, cy, 58.0, t_norm)
        else:
            front += f'<path d="M {rp[0]:.1f},{rp[1]:.1f} Q {(rp[0]+cx)/2:.1f},{(rp[1]+cy)/2 - 40*math.sin(t_norm*9):.1f} {cx:.1f},{cy:.1f}" fill="none" stroke="#00A99D" stroke-width="5" stroke-linecap="round"/>'
            front += _card_svg(cx, cy, 120, 84, f"T{number}", "#0072CE", "#FFD400")

    # Category D: Gadgets & Remote Controls (031-040)
    elif 31 <= number <= 40:
        # IR wave rings from hand
        if t_norm > 0.2:
            r = ((t_norm - 0.2) * 180) % 90 + 12
            front += f'<circle cx="{rp[0]+15:.1f}" cy="{rp[1]-20:.1f}" r="{r:.1f}" fill="none" stroke="#FF4757" stroke-width="3.5" opacity="{1.0 - r/110:.2f}"/>'
        if number == 32:
            behind += f'<rect x="40" y="30" width="{880*t_norm:.1f}" height="650" rx="22" fill="#E6F4FA" stroke="#0072CE" stroke-width="4"/>'
        elif number == 35:
            front += _hologram_ring_svg(rp[0] + 64, rp[1] - 32, t_norm)
        elif number == 36:
            sy = 200 + 220 * abs(math.sin(t_norm * math.pi))
            front += _card_svg(tc[0], tc[1], 150, 105, "SCAN", "#1A1C22", "#00A99D")
            front += f'<line x1="{tc[0]-85:.1f}" y1="{sy:.1f}" x2="{tc[0]+85:.1f}" y2="{sy:.1f}" stroke="#00FFCC" stroke-width="5"/>'
        elif number == 40 and 0.45 <= t_norm <= 0.65:
            front += '<circle cx="680" cy="300" r="140" fill="#FFFFFF" opacity="0.75"/>'
        else:
            sc = 0.6 + 0.6 * math.sin(t_norm * math.pi) if number == 38 else 1.0
            front += _card_svg(tc[0], tc[1], 128, 88, f"G{number}", "#0072CE", "#FFD400", sx=sc, sy=sc)

    # Category E: Magic & Creative Summoning (041-050)
    elif 41 <= number <= 50:
        for ring in range(3):
            rr = max(4.0, (t_norm * 130 - ring * 22))
            front += f'<circle cx="{tc[0]:.1f}" cy="{tc[1]:.1f}" r="{rr:.1f}" fill="none" stroke="#00A99D" stroke-width="4" opacity="{max(0.1, 1.0 - rr/140):.2f}"/>'
        sc = min(1.0, max(0.05, t_norm * 1.4))
        front += _card_svg(tc[0], tc[1], 124, 88, f"MAGIC {number}", "#6C5CE7", "#FFD400", sx=sc, sy=sc)

    # Category F: Typography Choreography (051-060)
    elif 51 <= number <= 60:
        word = str(params.get("text", "CREATIVE"))
        vis_n = max(1, int(len(word) * min(1.0, t_norm * 1.3)))
        shown = word[:vis_n]
        if number == 60:
            front += f'<line x1="480" y1="360" x2="{480 + 360*t_norm:.1f}" y2="360" stroke="#FFD400" stroke-width="8" stroke-linecap="round"/>'
        front += f'<g transform="translate({tc[0]-20:.1f},{tc[1]:.1f})"><rect x="-130" y="-44" width="260" height="84" rx="14" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4.5"/><text x="0" y="12" text-anchor="middle" font-family="Arial,sans-serif" font-size="36" font-weight="900" fill="#0072CE">{shown}</text></g>'

    # Category G: Background & Scene-World Transformations (061-070)
    elif 61 <= number <= 70:
        w = int(880 * t_norm)
        col = ["#E8F4FD", "#FFF8E1", "#E0F7FA", "#EDE7F6"][number % 4]
        behind += f'<rect x="40" y="40" width="{w}" height="640" rx="24" fill="{col}" stroke="#0B0C10" stroke-width="5"/>'
        behind += f'<circle cx="{120 + 600*t_norm:.1f}" cy="160" r="46" fill="#FFD400" opacity="0.5"/>'

    # Category H: Object Transformation & Destruction (071-080)
    elif 71 <= number <= 80:
        rx = max(4.0, 56.0 * (1.0 - t_norm)) if number == 71 else 16.0
        col = "#0072CE" if t_norm < 0.5 else "#00A99D"
        front += f'<rect x="{tc[0]-56:.1f}" y="{tc[1]-56:.1f}" width="112" height="112" rx="{rx:.1f}" fill="{col}" stroke="#0B0C10" stroke-width="5"/>'
        if number in (72, 78):
            for k in range(6):
                ang = k * 1.04
                dist = 65 * math.sin(t_norm * math.pi)
                front += f'<rect x="{tc[0]+dist*math.cos(ang)-10:.1f}" y="{tc[1]+dist*math.sin(ang)-10:.1f}" width="20" height="20" fill="#FFD400" stroke="#0B0C10" stroke-width="2.5"/>'

    # Category I: Unexpected Funny Cause-and-Effect (081-090)
    elif 81 <= number <= 90:
        if number == 85:
            # Tiny clone helper
            front += f'<g transform="translate({tc[0]-40:.1f},{tc[1]+80:.1f}) scale(0.32)"><circle cx="0" cy="-60" r="40" fill="#FFFFFF" stroke="#0B0C10" stroke-width="8"/><rect x="-32" y="-16" width="64" height="80" rx="10" fill="#0072CE" stroke="#0B0C10" stroke-width="8"/></g>'
        front += _card_svg(tc[0], tc[1] - 40 * math.sin(t_norm * math.pi), 120, 84, f"GAG {number}", "#FFD400", "#0072CE", rot=18 * math.sin(t_norm * 10))

    # Category J: Cinematic Scene-Control Choreography (091-100)
    else:
        if number == 97:
            front += f'<rect x="{tc[0]-75:.1f}" y="{tc[1]-55:.1f}" width="150" height="110" fill="none" stroke="#00FFCC" stroke-width="4" stroke-dasharray="14 8"/>'
        if number in (99, 100):
            behind += f'<polygon points="{rp[0]:.1f},{rp[1]:.1f} {tc[0]-80:.1f},{tc[1]+160:.1f} {tc[0]+140:.1f},{tc[1]+160:.1f}" fill="#FFD400" opacity="0.22"/>'
        front += _card_svg(tc[0], tc[1], 136, 94, f"CINE {number}", "#0072CE", "#FFD400", sx=0.85 + 0.2 * t_norm, sy=0.85 + 0.2 * t_norm)

    return behind, front

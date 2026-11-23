"""
V3.2 Asset Factory:
- 40 Original Brand Thematic SVG Icons (genuine vector paths, 64x64 canonical viewBox)
- 20 Interactive Editable SVG Props with grasp anchors & physics metadata
- 24 Parametrically Animated 2D VFX Primitives
- IconNormalizer & Searchable Asset Manifest
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional

FACTORY_DIR = Path(__file__).resolve().parent

# 40 Thematic Brand Icons (id -> inner SVG vector shapes in 64x64 viewBox)
BRAND_ICONS_40: Dict[str, str] = {
    "experiment": '<path d="M24 10h16M28 10v14l-12 24a4 4 0 0 0 3.6 6h24.8a4 4 0 0 0 3.6-6L36 24V10" fill="none" stroke="#0B0C10" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><path d="M20 42h24l4 8H16z" fill="#00A99D"/>',
    "brain": '<path d="M26 14a10 10 0 0 0-12 10 8 8 0 0 0-2 14 10 10 0 0 0 14 12V14zm12 0a10 10 0 0 1 12 10 8 8 0 0 1 2 14 10 10 0 0 1-14 12V14z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/>',
    "eyes": '<ellipse cx="21" cy="32" rx="10" ry="12" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8"/><circle cx="22" cy="32" r="5" fill="#00A99D"/><ellipse cx="43" cy="32" rx="10" ry="12" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8"/><circle cx="44" cy="32" r="5" fill="#00A99D"/>',
    "watch": '<rect x="22" y="8" width="20" height="10" rx="2" fill="#0072CE" stroke="#0B0C10" stroke-width="3"/><rect x="22" y="46" width="20" height="10" rx="2" fill="#0072CE" stroke="#0B0C10" stroke-width="3"/><circle cx="32" cy="32" r="15" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8"/><path d="M32 23v10l7 4" fill="none" stroke="#0B0C10" stroke-width="3.5" stroke-linecap="round"/>',
    "cards": '<rect x="12" y="16" width="26" height="36" rx="4" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.5"/><rect x="26" y="12" width="26" height="36" rx="4" fill="#0072CE" stroke="#0B0C10" stroke-width="3.5"/><circle cx="39" cy="30" r="6" fill="#FFD400"/>',
    "lab": '<path d="M14 52h36M22 52V20l10-8 10 8v32" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/><circle cx="32" cy="32" r="6" fill="#00A99D"/>',
    "book": '<path d="M12 16h18a4 4 0 0 1 4 4v32H14a4 4 0 0 1-4-4V16zm40 0H34a4 4 0 0 0-4 4v32h20a4 4 0 0 0 4-4V16z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/>',
    "crystal": '<polygon points="32,8 50,24 44,54 20,54 14,24" fill="#00A99D" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/><polyline points="14,24 32,32 50,24" fill="none" stroke="#FFFFFF" stroke-width="3"/>',
    "remote": '<rect x="20" y="8" width="24" height="48" rx="6" fill="#1A1C22" stroke="#0B0C10" stroke-width="3.8"/><circle cx="32" cy="18" r="4" fill="#FF4757"/><rect x="26" y="28" width="12" height="6" rx="2" fill="#00A99D"/>',
    "camera": '<rect x="10" y="20" width="44" height="30" rx="5" fill="#0072CE" stroke="#0B0C10" stroke-width="3.8"/><path d="M22 20l4-8h12l4 8" fill="#0072CE" stroke="#0B0C10" stroke-width="3.5"/><circle cx="32" cy="35" r="9" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.5"/>',
    "lightbulb": '<path d="M24 42h16M26 50h12M32 10a14 14 0 0 0-10 24c2 2 4 5 4 8h12c0-3 2-6 4-8a14 14 0 0 0-10-24z" fill="#FFD400" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/>',
    "logic": '<rect x="12" y="14" width="16" height="16" rx="3" fill="#0072CE" stroke="#0B0C10" stroke-width="3.5"/><rect x="36" y="34" width="16" height="16" rx="3" fill="#00A99D" stroke="#0B0C10" stroke-width="3.5"/><path d="M28 22h8v12h8" fill="none" stroke="#0B0C10" stroke-width="3.5"/>',
    "arrow": '<path d="M12 32h34M34 18l14 14-14 14" fill="none" stroke="#0B0C10" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>',
    "question": '<path d="M24 22a8 8 0 1 1 12 7c-3 2-4 4-4 8" fill="none" stroke="#0B0C10" stroke-width="5" stroke-linecap="round"/><circle cx="32" cy="48" r="3.5" fill="#0072CE"/>',
    "target": '<circle cx="32" cy="32" r="22" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8"/><circle cx="32" cy="32" r="13" fill="#0072CE"/><circle cx="32" cy="32" r="5" fill="#FFD400"/>',
    "magnifier": '<circle cx="27" cy="27" r="15" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4"/><line x1="38" y1="38" x2="54" y2="54" stroke="#0B0C10" stroke-width="6" stroke-linecap="round"/>',
    "magnet": '<path d="M18 14v18a14 14 0 0 0 28 0V14h-8v18a6 6 0 0 1-12 0V14h-8z" fill="#FF4757" stroke="#0B0C10" stroke-width="3.8"/><rect x="18" y="14" width="8" height="8" fill="#FFFFFF"/><rect x="38" y="14" width="8" height="8" fill="#FFFFFF"/>',
    "fire": '<path d="M32 8c6 10 16 18 16 30a16 16 0 1 1-32 0c0-8 4-14 8-18 0 6 4 8 6 8 0-8 2-14 2-20z" fill="#FF6B2C" stroke="#0B0C10" stroke-width="3.5" stroke-linejoin="round"/>',
    "electricity": '<polygon points="36,8 16,34 30,34 26,56 48,28 34,28" fill="#FFD400" stroke="#0B0C10" stroke-width="3.5" stroke-linejoin="round"/>',
    "portal": '<ellipse cx="32" cy="32" rx="14" ry="22" fill="#00A99D" stroke="#0B0C10" stroke-width="4"/><ellipse cx="32" cy="32" rx="7" ry="13" fill="#1A1C22"/>',
    "key": '<circle cx="22" cy="32" r="10" fill="#FFD400" stroke="#0B0C10" stroke-width="3.8"/><path d="M32 32h22v8M46 32v6" fill="none" stroke="#0B0C10" stroke-width="4.2" stroke-linecap="round"/>',
    "speech_bubble": '<path d="M12 16h40a4 4 0 0 1 4 4v22a4 4 0 0 1-4 4H26l-10 8v-8h-4a4 4 0 0 1-4-4V20a4 4 0 0 1 4-4z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/>',
    "chart": '<path d="M12 50h40M18 50V34h8v16M29 50V22h8v28M40 50V14h8v36" fill="#0072CE" stroke="#0B0C10" stroke-width="3.2"/>',
    "clock": '<circle cx="32" cy="32" r="22" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4"/><path d="M32 18v14l10 6" fill="none" stroke="#0B0C10" stroke-width="4" stroke-linecap="round"/>',
    "lock": '<rect x="16" y="28" width="32" height="24" rx="4" fill="#FFD400" stroke="#0B0C10" stroke-width="3.8"/><path d="M22 28v-8a10 10 0 0 1 20 0v8" fill="none" stroke="#0B0C10" stroke-width="4"/>',
    "atom": '<circle cx="32" cy="32" r="4.5" fill="#0072CE"/><ellipse cx="32" cy="32" rx="22" ry="9" fill="none" stroke="#0B0C10" stroke-width="3" transform="rotate(30 32 32)"/><ellipse cx="32" cy="32" rx="22" ry="9" fill="none" stroke="#0B0C10" stroke-width="3" transform="rotate(-30 32 32)"/>',
    "gear": '<circle cx="32" cy="32" r="14" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5" stroke-dasharray="7 5"/><circle cx="32" cy="32" r="6" fill="#0072CE" stroke="#0B0C10" stroke-width="3"/>',
    "rocket": '<path d="M32 8c10 10 12 24 8 36H24c-4-12-2-26 8-36z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8"/><circle cx="32" cy="26" r="4.5" fill="#0072CE"/><path d="M26 44l-6 10M38 44l6 10" stroke="#FF6B2C" stroke-width="4" stroke-linecap="round"/>',
    "compass": '<circle cx="32" cy="32" r="22" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8"/><polygon points="32,16 38,32 32,48 26,32" fill="#0072CE" stroke="#0B0C10" stroke-width="2.5"/>',
    "shield": '<path d="M32 10l18 6v14c0 12-8 20-18 24-10-4-18-12-18-24V16z" fill="#0072CE" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/>',
    "trophy": '<path d="M18 14h28v12a14 14 0 0 1-28 0V14zM26 40v12M20 52h24" fill="#FFD400" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/>',
    "puzzle": '<path d="M14 20h14a5 5 0 0 1 8 0h14v14a5 5 0 0 1 0 8v10H14V20z" fill="#00A99D" stroke="#0B0C10" stroke-width="3.5" stroke-linejoin="round"/>',
    "mic": '<rect x="24" y="10" width="16" height="26" rx="8" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8"/><path d="M16 30a16 16 0 0 0 32 0M32 46v8" fill="none" stroke="#0B0C10" stroke-width="3.8" stroke-linecap="round"/>',
    "speaker": '<polygon points="14,24 26,24 38,14 38,50 26,40 14,40" fill="#0072CE" stroke="#0B0C10" stroke-width="3.5" stroke-linejoin="round"/><path d="M44 24a10 10 0 0 1 0 16" fill="none" stroke="#0B0C10" stroke-width="3.8" stroke-linecap="round"/>',
    "folder": '<path d="M10 18h16l6 6h22v26H10z" fill="#FFD400" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/>',
    "cloud": '<path d="M20 46h26a10 10 0 0 0 2-19.8A13 13 0 0 0 22 22a11 11 0 0 0-2 24z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/>',
    "star": '<polygon points="32,8 39,24 56,26 43,38 46,55 32,46 18,55 21,38 8,26 25,24" fill="#FFD400" stroke="#0B0C10" stroke-width="3.5" stroke-linejoin="round"/>',
    "heart": '<path d="M32 52S12 39 12 24a10 10 0 0 1 20-4 10 10 0 0 1 20 4c0 15-20 28-20 28z" fill="#FF4757" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/>',
    "diamond": '<polygon points="32,10 54,28 32,54 10,28" fill="#00A99D" stroke="#0B0C10" stroke-width="3.8" stroke-linejoin="round"/>',
    "flag": '<line x1="16" y1="10" x2="16" y2="54" stroke="#0B0C10" stroke-width="4.5" stroke-linecap="round"/><polygon points="16,12 50,20 16,32" fill="#0072CE" stroke="#0B0C10" stroke-width="3.5" stroke-linejoin="round"/>',
}

# 20 Interactive Editable SVG Props
PROPS_20: Dict[str, dict] = {
    "remote": {"anchor": [12, 32], "mass": "light", "svg": '<rect x="0" y="-24" width="22" height="48" rx="5" fill="#1A1C22" stroke="#0B0C10" stroke-width="3.5"/><circle cx="11" cy="-14" r="4" fill="#FF4757"/>'},
    "gem": {"anchor": [0, 0], "mass": "light", "svg": '<polygon points="0,-20 16,-4 0,20 -16,-4" fill="#00A99D" stroke="#0B0C10" stroke-width="3.5"/>'},
    "magic_ring": {"anchor": [0, 0], "mass": "light", "svg": '<circle cx="0" cy="0" r="18" fill="none" stroke="#FFD400" stroke-width="5"/><circle cx="0" cy="-18" r="5" fill="#00A99D" stroke="#0B0C10" stroke-width="2.5"/>'},
    "pen": {"anchor": [0, 0], "mass": "light", "svg": '<rect x="-4" y="-32" width="8" height="46" rx="2" fill="#0072CE" stroke="#0B0C10" stroke-width="3"/><polygon points="-4,14 4,14 0,24" fill="#FFD400" stroke="#0B0C10" stroke-width="2.5"/>'},
    "cable": {"anchor": [0, 0], "mass": "flexible", "svg": '<path d="M0,0 C20,-20 40,20 60,0" fill="none" stroke="#1A1C22" stroke-width="5" stroke-linecap="round"/>'},
    "grappling_nozzle": {"anchor": [0, 0], "mass": "medium", "svg": '<rect x="-6" y="-10" width="22" height="20" rx="4" fill="#0072CE" stroke="#0B0C10" stroke-width="3.5"/><polygon points="16,-12 30,0 16,12" fill="#FFD400" stroke="#0B0C10" stroke-width="3"/>'},
    "lasso": {"anchor": [0, 0], "mass": "flexible", "svg": '<ellipse cx="24" cy="0" rx="20" ry="12" fill="none" stroke="#FFD400" stroke-width="4"/>'},
    "tether_hook": {"anchor": [0, 0], "mass": "light", "svg": '<path d="M0,0 L20,0 C28,0 28,14 18,14" fill="none" stroke="#0B0C10" stroke-width="4.5" stroke-linecap="round"/>'},
    "pointer": {"anchor": [0, 0], "mass": "light", "svg": '<line x1="0" y1="0" x2="54" y2="-36" stroke="#0B0C10" stroke-width="4.5" stroke-linecap="round"/><circle cx="54" cy="-36" r="5" fill="#FF4757"/>'},
    "magnifier": {"anchor": [0, 0], "mass": "light", "svg": '<line x1="0" y1="0" x2="18" y2="-18" stroke="#0B0C10" stroke-width="5" stroke-linecap="round"/><circle cx="28" cy="-28" r="14" fill="#FFFFFF" fill-opacity="0.7" stroke="#0B0C10" stroke-width="4"/>'},
    "megaphone": {"anchor": [0, 0], "mass": "medium", "svg": '<polygon points="0,-8 36,-22 36,22 0,8" fill="#0072CE" stroke="#0B0C10" stroke-width="3.5"/>'},
    "wand": {"anchor": [0, 0], "mass": "light", "svg": '<line x1="0" y1="0" x2="40" y2="-40" stroke="#1A1C22" stroke-width="5" stroke-linecap="round"/><polygon points="40,-50 43,-42 51,-42 45,-37 47,-29 40,-34 33,-29 35,-37 29,-42 37,-42" fill="#FFD400" stroke="#0B0C10" stroke-width="2"/>'},
    "switch": {"anchor": [0, 0], "mass": "static", "svg": '<rect x="-14" y="-20" width="28" height="40" rx="4" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.5"/><rect x="-8" y="-10" width="16" height="14" fill="#00A99D" stroke="#0B0C10" stroke-width="2.5"/>'},
    "knob": {"anchor": [0, 0], "mass": "static", "svg": '<circle cx="0" cy="0" r="18" fill="#1A1C22" stroke="#0B0C10" stroke-width="3.5"/><line x1="0" y1="0" x2="0" y2="-14" stroke="#FFD400" stroke-width="4" stroke-linecap="round"/>'},
    "lever": {"anchor": [0, 0], "mass": "medium", "svg": '<rect x="-16" y="10" width="32" height="10" rx="3" fill="#1A1C22"/><line x1="0" y1="10" x2="18" y2="-22" stroke="#0B0C10" stroke-width="5"/><circle cx="18" cy="-22" r="7" fill="#FF4757" stroke="#0B0C10" stroke-width="3"/>'},
    "flashlight": {"anchor": [0, 0], "mass": "light", "svg": '<rect x="-8" y="-8" width="28" height="16" rx="3" fill="#1A1C22" stroke="#0B0C10" stroke-width="3"/><polygon points="20,-12 30,-16 30,16 20,12" fill="#FFD400" stroke="#0B0C10" stroke-width="3"/>'},
    "door": {"anchor": [0, 0], "mass": "heavy", "svg": '<rect x="-24" y="-44" width="48" height="88" rx="3" fill="#0072CE" stroke="#0B0C10" stroke-width="4"/><circle cx="14" cy="0" r="4" fill="#FFD400"/>'},
    "curtain_handle": {"anchor": [0, 0], "mass": "light", "svg": '<line x1="0" y1="-30" x2="0" y2="10" stroke="#FFD400" stroke-width="4"/><circle cx="0" cy="14" r="7" fill="#FFD400" stroke="#0B0C10" stroke-width="3"/>'},
    "portal_key": {"anchor": [0, 0], "mass": "light", "svg": '<circle cx="0" cy="-12" r="10" fill="#00A99D" stroke="#0B0C10" stroke-width="3.5"/><path d="M0,-2v26h8" fill="none" stroke="#0B0C10" stroke-width="4"/>'},
    "springboard": {"anchor": [0, 0], "mass": "heavy", "svg": '<rect x="-28" y="-6" width="56" height="10" rx="3" fill="#FFD400" stroke="#0B0C10" stroke-width="3.5"/><path d="M-16,4l32,10-32,10 32,10" fill="none" stroke="#0B0C10" stroke-width="3.5"/>'},
}

# 24 Parametrically Animated VFX Primitives
FX_PRIMITIVES_24: List[str] = [
    "spark_burst", "electric_branch", "flare", "energy_thread",
    "glowing_circle", "energy_pulse", "small_stars", "smoke_curl",
    "cartoon_flame", "ash_disintegration", "circular_portal", "water_ripple",
    "shockwave", "streak", "speed_line", "confetti",
    "shatter_tiles", "radial_spokes", "particles_to_shape", "dissolve_mask",
    "ink_splash", "glow_outline", "soft_impact_smear", "zigzag_burst",
]


def render_fx_primitive_svg(fx_name: str, cx: float = 100.0, cy: float = 100.0, t: float = 0.5) -> str:
    """Render any of the 24 parametric VFX primitives at normalized time t in [0, 1]."""
    r = 14.0 + 42.0 * t
    op = max(0.15, 1.0 - 0.7 * t)
    if fx_name in ("spark_burst", "radial_spokes", "zigzag_burst"):
        spokes = []
        for k in range(8):
            ang = k * math.pi / 4.0
            x1 = cx + math.cos(ang) * (r * 0.4)
            y1 = cy + math.sin(ang) * (r * 0.4)
            x2 = cx + math.cos(ang) * r
            y2 = cy + math.sin(ang) * r
            spokes.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#FFD400" stroke-width="3.5" stroke-linecap="round" opacity="{op:.2f}"/>')
        return "".join(spokes)
    if fx_name in ("circular_portal", "glowing_circle", "energy_pulse", "water_ripple", "shockwave"):
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="none" stroke="#00A99D" stroke-width="4.5" opacity="{op:.2f}"/><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r*0.6:.1f}" fill="none" stroke="#0072CE" stroke-width="2.5" opacity="{op:.2f}"/>'
    if fx_name in ("cartoon_flame", "flare", "soft_impact_smear"):
        return f'<path d="M{cx:.1f},{cy-r:.1f} C{cx+r*0.6:.1f},{cy:.1f} {cx+r*0.4:.1f},{cy+r*0.5:.1f} {cx:.1f},{cy+r*0.5:.1f} C{cx-r*0.4:.1f},{cy+r*0.5:.1f} {cx-r*0.6:.1f},{cy:.1f} {cx:.1f},{cy-r:.1f} Z" fill="#FF6B2C" stroke="#0B0C10" stroke-width="2.5" opacity="{op:.2f}"/>'
    if fx_name in ("electric_branch", "energy_thread", "streak", "speed_line"):
        return f'<polyline points="{cx-r:.1f},{cy:.1f} {cx-r*0.3:.1f},{cy-14:.1f} {cx+r*0.3:.1f},{cy+14:.1f} {cx+r:.1f},{cy:.1f}" fill="none" stroke="#00A99D" stroke-width="4" stroke-linecap="round" opacity="{op:.2f}"/>'
    # Particles, confetti, smoke, shatter, ink, stars
    dots = []
    for k in range(6):
        ang = k * math.pi / 3.0 + t * 1.5
        px = cx + math.cos(ang) * r * 0.7
        py = cy + math.sin(ang) * r * 0.7
        col = "#FFD400" if k % 2 == 0 else "#0072CE"
        dots.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{4.0 + 2.0*(1-t):.1f}" fill="{col}" opacity="{op:.2f}"/>')
    return "".join(dots)


def normalize_icon_svg(icon_id: str, inner_svg: str) -> str:
    """Wrap icon shapes in canonical 64x64 viewBox SVG."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" id="icon_{icon_id}" viewBox="0 0 64 64" width="64" height="64">\n'
        f'  {inner_svg}\n'
        '</svg>\n'
    )


def build_asset_factory() -> dict:
    (FACTORY_DIR / "icons").mkdir(parents=True, exist_ok=True)
    (FACTORY_DIR / "props").mkdir(parents=True, exist_ok=True)
    (FACTORY_DIR / "fx").mkdir(parents=True, exist_ok=True)

    for icon_id, inner in BRAND_ICONS_40.items():
        (FACTORY_DIR / "icons" / f"{icon_id}.svg").write_text(normalize_icon_svg(icon_id, inner), encoding="utf-8")

    for prop_id, meta in PROPS_20.items():
        psvg = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" id="prop_{prop_id}" viewBox="-50 -60 120 120" width="120" height="120">\n'
            f'  {meta["svg"]}\n'
            '</svg>\n'
        )
        (FACTORY_DIR / "props" / f"{prop_id}.svg").write_text(psvg, encoding="utf-8")

    for fx_name in FX_PRIMITIVES_24:
        fsvg = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" id="fx_{fx_name}" viewBox="0 0 200 200" width="200" height="200">\n'
            f'  {render_fx_primitive_svg(fx_name, 100.0, 100.0, 0.5)}\n'
            '</svg>\n'
        )
        (FACTORY_DIR / "fx" / f"{fx_name}.svg").write_text(fsvg, encoding="utf-8")

    manifest = {
        "schema_version": "3.2.0",
        "license": "Original Brand Vector Art (MIT-compatible internal asset pack)",
        "icon_count": len(BRAND_ICONS_40),
        "prop_count": len(PROPS_20),
        "fx_primitive_count": len(FX_PRIMITIVES_24),
        "icons": sorted(BRAND_ICONS_40.keys()),
        "props": {k: {"anchor": v["anchor"], "mass": v["mass"]} for k, v in PROPS_20.items()},
        "fx_primitives": FX_PRIMITIVES_24,
    }
    (FACTORY_DIR / "asset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Asset Factory: {manifest['icon_count']} icons, {manifest['prop_count']} props, {manifest['fx_primitive_count']} FX primitives")
    return manifest


if __name__ == "__main__":
    build_asset_factory()

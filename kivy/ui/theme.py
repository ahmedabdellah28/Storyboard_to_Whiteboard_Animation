"""
Sketch Animation Studio — Clean Minimal Theme
Professional dark theme. No glow, no neon, no glassmorphism.
"""


class Theme:
    # ── Core Backgrounds ──
    BG_ROOT = [0.055, 0.063, 0.082, 1.0]         # #0E1015 Deep Charcoal
    BG_PANEL = [0.086, 0.098, 0.125, 1.0]         # #161920
    BG_CARD = [0.129, 0.149, 0.196, 1.0]          # #212632
    BG_CARD_HOVER = [0.169, 0.192, 0.251, 1.0]    # #2B3140
    BG_CARD_SELECTED = [0.20, 0.16, 0.32, 1.0]    # Subtle violet tint
    BG_INPUT = [0.075, 0.086, 0.110, 1.0]         # #13161C
    BG_DROP_ZONE = [0.10, 0.11, 0.14, 1.0]        # Drop area

    # ── Accents ──
    ACCENT = [0.486, 0.302, 1.0, 1.0]             # #7C4DFF Electric Violet
    ACCENT_HOVER = [0.588, 0.439, 1.0, 1.0]       # #9670FF
    ACCENT_CYAN = [0.0, 0.898, 1.0, 1.0]          # #00E5FF Cyan
    ACCENT_SUCCESS = [0.0, 0.902, 0.463, 1.0]     # #00E676 Green
    ACCENT_DANGER = [1.0, 0.322, 0.322, 1.0]      # #FF5252 Red

    # ── Text ──
    TEXT = [1.0, 1.0, 1.0, 1.0]                   # White
    TEXT_SECONDARY = [0.616, 0.643, 0.690, 1.0]    # #9DA4B0 Muted
    TEXT_DIM = [0.376, 0.408, 0.467, 1.0]          # #606877 Dim
    TEXT_ACCENT = [0.702, 0.533, 1.0, 1.0]         # #B388FF

    # ── Borders ──
    BORDER = [0.149, 0.173, 0.220, 1.0]            # #262C38
    BORDER_FOCUS = [0.486, 0.302, 1.0, 1.0]        # Violet
    BORDER_DASHED = [0.3, 0.33, 0.40, 1.0]         # Drop zone dashed

    # ── Dimensions ──
    TOP_BAR_HEIGHT = 52
    CARD_RADIUS = 8
    CARD_SPACING = 8
    BORDER_RADIUS = 8

    # ── Priority Color Palette ──
    PRIORITY_COLORS = [
        [1.0, 0.78, 0.0, 1.0],      # 1: Gold / Amber
        [0.0, 0.85, 0.50, 1.0],     # 2: Emerald Green
        [0.0, 0.75, 1.0, 1.0],      # 3: Cyan / Sky Blue
        [0.65, 0.35, 1.0, 1.0],     # 4: Indigo / Violet
        [1.0, 0.40, 0.55, 1.0],     # 5: Rose / Coral
        [1.0, 0.55, 0.0, 1.0],      # 6: Vivid Orange
        [0.30, 0.90, 0.90, 1.0],     # 7: Teal
        [0.85, 0.30, 0.85, 1.0]      # 8: Magenta
    ]

    @classmethod
    def get_priority_color(cls, priority_idx) -> list:
        if priority_idx is None or str(priority_idx).strip() in ("", "0", "None"):
            return [0.45, 0.48, 0.55, 0.8]  # Dim neutral gray for unassigned
        try:
            p_int = int(priority_idx)
            idx = max(0, p_int - 1) % len(cls.PRIORITY_COLORS)
            return cls.PRIORITY_COLORS[idx]
        except Exception:
            return [0.45, 0.48, 0.55, 0.8]

    # ── Hex shortcuts (for KivyMD color strings) ──
    HEX_ACCENT = "#7C4DFF"
    HEX_BG_ROOT = "#0E1015"
    HEX_TEXT = "#FFFFFF"
    HEX_TEXT_SEC = "#9DA4B0"
    HEX_TEXT_DIM = "#606877"
    HEX_CYAN = "#00E5FF"
    HEX_SUCCESS = "#00E676"
    HEX_DANGER = "#FF5252"


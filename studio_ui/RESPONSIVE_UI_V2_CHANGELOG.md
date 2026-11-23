# Responsive UI V2

This archive contains the responsive/light-theme refactor applied to the current PySide6 Widgets UI.

## What changed

- Logical-pixel responsive metrics. Normal layout dimensions are no longer multiplied by screen DPR.
- Breakpoints are based on the actual Whiteboard Studio window width.
- Relevant monitor DPI is taken from the screen associated with the actual window when available.
- Compact mode converts Shots and Inspector into real toolbar drawer toggles.
- Medium/compact toolbars use a `More ▾` overflow menu instead of forcing every control into one row.
- The main Studio splitter keeps Canvas primary and adapts Shots/Inspector widths.
- Timeline painter labels use readable 12+ logical px fonts.
- Global and local UI styling has been migrated toward the approved Light 2026 palette.
- Canvas/background surfaces are light, while the 1920×1080 working canvas remains 16:9.
- Scrollbars are thin, unobtrusive and `AsNeeded` at application level.
- Dialog sizing and minimum sizes are being normalized toward screen-safe logical dimensions.
- Main window starts at 1440×900 and retains a 960×640 minimum.

## Important

Qt 6 already handles Windows High-DPI for logical widgets. The old implementation multiplied layout sizes by `devicePixelRatio`, which could double-scale the UI at 125%/150%/200%. The new responsive system avoids that.

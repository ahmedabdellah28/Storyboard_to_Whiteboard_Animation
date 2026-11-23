# Whiteboard Studio — Editor UX Guidelines

> **Experience Principle:** "Select → Edit → See → Hear → Adjust → Play"  

---

## 1. Direct Visual Manipulation
- Assets on the canvas can be dragged directly to set positioning.
- Corner selection handles enable immediate scaling.
- The Canvas is the primary hero component; no modal dialogs for basic geometric transforms.

## 2. Multi-track Direct Editing
- Dragging element bars horizontally adjusts start timing.
- Dragging the right edge adjusts draw and hold durations.
- Clicking on a spoken word in the Voice track automatically navigates the playhead to that exact audio beat and highlights the corresponding asset.

## 3. Ownership & Creative Protection
- Every editable item clearly indicates its ownership (`AUTO` / `USER_OVERRIDE` / `LOCKED`).
- Manual modifications are flagged as `USER_OVERRIDE` and protected from background overwriting.
- The `[Reset to Automatic]` button enables one-click restoration of AI layout defaults.

# Camera Editor V3 — Whiteboard Studio

This package keeps the existing PySide6/Qt Widgets Studio architecture and changes the Camera workspace to behave like an editor rather than a gallery of camera previews.

## User experience

### 1. Cameras are explicit
The Camera workspace shows:
- camera count
- camera order
- selected camera
- add camera
- delete camera
- move camera earlier/later

Only one selected camera is rendered in the main viewport.

Camera order is the shot order. Moving a camera changes the stored camera order and resequences its start times so the camera list and timeline remain consistent.

### 2. A camera owns a set of visual assets
The Camera workspace has an `Elements in Camera` panel.

The user can:
- add an already extracted asset to the selected camera
- remove an asset from the selected camera without deleting the global asset
- move the asset up/down in the camera layer order
- select an asset from the list and immediately manipulate it on the canvas

An asset can exist in multiple cameras.

### 3. Position is per camera
Each camera can store `element_overrides` for X/Y/scale.

Dragging an element in Camera 01 does not force the same position in Camera 02.

### 4. Timeline-driven visual preview
The selected camera is driven by the existing Studio playhead.

The viewport previews animation styles without invoking a production render:
- Outside-In / contour-like draw
- fade
- slide from left/right
- pop / bounce

Assets that have not reached their start time remain as a subtle editing ghost so the user can still select and position them.

### 5. Audio preview
The Studio Play button now attempts to play the section voice through Qt Multimedia and seeks the audio when the playhead is scrubbed.

The preview remains lightweight and uses the same Studio playhead as the visual camera editor.

Audio sources are searched in this order:
1. `voice/section.wav`
2. `voiceover.wav`
3. `master_audio.wav`

### 6. Focused workspace
The global Shots navigator is hidden while the Camera or Extraction tab is active. This gives the selected workspace the available width and avoids duplicated camera navigation.

## Persistence

The Studio saves camera membership and per-camera layout using the existing `placed_elements_layout.json` camera objects:

```json
{
  "name": "Camera 01",
  "element_ids": ["r1_01_elem", "r1_02_elem"],
  "element_order": ["r1_01_elem", "r1_02_elem"],
  "element_overrides": {
    "r1_02_elem": {
      "x": 1200,
      "y": 420,
      "scale": 1.15
    }
  }
}
```

Existing layouts without these fields are upgraded in memory using camera/asset timing, with a safe first-camera fallback so legacy assets do not silently disappear.

## Renderer integration note

The UI writes the camera membership and per-camera override state. The final production renderer must consume these camera fields for final video output to exactly match the interactive Camera workspace. This package intentionally does not rewrite the production renderer.

## Validation in the packaging environment

- Python `compileall`: passed.
- ZIP integrity: passed.
- Live Qt GUI test: not possible in this environment because PySide6/PyQt6 are not installed here.

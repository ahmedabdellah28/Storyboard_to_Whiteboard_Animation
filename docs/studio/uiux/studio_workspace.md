# Whiteboard Studio — Unified Studio Workspace & Live Video Preview

> **Document Class:** UX Architecture & Interaction Blueprint  
> **Status:** CANONICAL USER WORKSPACE SPECIFICATION  
> **Core Principle:** Editing and Preview are ONE unified user workspace.  

---

## 1. Unified Studio Philosophy

In Whiteboard Studio, there is **no separate "Preview screen"** in the creative editing flow.

The user must NEVER be subjected to the fragmented loop:
$$\text{Edit} \longrightarrow \text{Leave Studio} \longrightarrow \text{Open Preview} \longrightarrow \text{Return to Editor} \longrightarrow \text{Edit Again}$$

Instead, **the Studio itself IS the editing and preview environment**:
- Direct visual manipulation (drag, resize, rotate, restyle).
- Instant live playback with playhead scrubbing.
- Simultaneous auditioning of original voice narration and independent SFX cues.
- Real-time inking and camera viewport updates.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Project: Fiercest Warriors / Section: 01_section               [Shot|Section|Project]  │
├───────────────┬────────────────────────────────────────────────────────┬───────────────┤
│ SHOTS         │                                                        │ INSPECTOR     │
│               │                      LIVE CANVAS                       │               │
│ 🎥 Camera 01  │                                                        │ VISUAL ASSET  │
│ 🎥 Camera 02  │                   1080p VIDEO PREVIEW                  │ ID: char_01   │
│ 🎥 Camera 03  │                                                        │ Pos: (420,380)│
│               │           (Direct manipulation + Real-time Inking)     │ Anim: Pen     │
│ + Add Shot    │                                                        │ Start: 0.5s   │
│               │                                                        │ Draw: 0.8s    │
│               │                                                        │ Hold: 2.0s    │
│               │                                                        │ Ownership:    │
│               │                                                        │ [USER_OVERRIDE]│
├───────────────┴────────────────────────────────────────────────────────┴───────────────┤
│ TIMELINE SEQUENCER                                            [▶ Play] [⏸ Pause] [⏹]   │
│                                                                                        │
│ VOICE   🎙 ━━━━━━━━━━━━━━━━━━ "رفع سيفه" ━━━━━━━━━━━━ "فانطلق" ━━━━━━━━━━━━━━━━━━━━   │
│ VISUALS    ██████ char_01 (draw:0.8s|hold:2.0s)       ██████ sword_02                   │
│ SFX                ◆ pop (AUTO)            ◆ whoosh (USER)              ◆ pop          │
│ CAMERA     ──────────[ Camera 01 ]───────────┬──────────────[ Camera 02 ]────────────  │
│                                              ● PLAYHEAD (00:04.20)                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Four Canonical Timeline Tracks

DO NOT conflate the timeline into a single pre-rendered `master_audio.wav`. The editable timeline exposes the source production components independently:

| Track | Group | Data Source | Behavior | Ownership Policy |
|:---|:---|:---|:---|:---|
| **Track 1** | **VOICE** | `section_voice.wav` + `whisper_words.json` | Displays audio waveform & word anchors. Clicking a word jumps the playhead to that exact timestamp and highlights the linked asset. | **LOCKED by default** to preserve Whisper alignment. |
| **Track 2** | **VISUALS** | `placed_elements_layout.json` | Shows draw duration (inking) and hold duration. Draggable along timeline to change trigger time; right edge resizable to alter duration. | `AUTO` initially, transitions to `USER_OVERRIDE` upon edit. |
| **Track 3** | **SFX** | `sfx_cues.json` | Independent cue markers (pop, whoosh, pencil write) with diamond markers `◆`. Draggable to reposition audio beats. | `AUTO` vs `USER_OVERRIDE`. Protected from auto-overwrite. |
| **Track 4** | **CAMERA** | `zones` / `camera_trajectory.json` | Shot boundaries (`Camera 01`, `Camera 02`) and camera pan intervals. Selecting a shot focuses the canvas viewport. | Interactive camera framing. |

---

## 3. Data Ownership & Override Protection

To prevent automated pipelines from obliterating user creative decisions:
1. **`AUTO`**: Generated deterministically by the layout planner, Whisper aligner, or SFX solver.
2. **`USER_OVERRIDE`**: The user manually adjusted timing, position, scale, or animation style.
3. **`LOCKED`**: Read-only source timing (e.g. original voice narration).

### Reset to Automatic
When an item is modified, the Inspector displays `[USER_OVERRIDE]` and provides a **`[Reset to Automatic]`** button. Clicking this restores the AI-generated default timing and positioning without affecting other manual edits.

---

## 4. Live Scrubbing & Real-Time Inking

When the user drags the timeline playhead:
- **Zero Full-Render Overhead**: Does not call FFmpeg or execute background video pipelines.
- **Dynamic Asset Opacity & Inking**:
  - $t < t_{\text{start}}$: Element hidden (or 35% faint in edit mode).
  - $t_{\text{start}} \le t < t_{\text{start}} + t_{\text{draw}}$: Progressive inking preview.
  - $t \ge t_{\text{start}} + t_{\text{draw}}$: Fully drawn and held.
- **Camera Frame Alignment**: The viewport frustum smoothly updates to reflect the active shot and pan trajectory.

---

## 5. Preview Scopes Inside the Same Studio

The user toggles playback scopes seamlessly via the top toolbar:
- **`[ Shot ]`**: Loops playback within the boundaries of the currently active camera shot.
- **`[ Section ]`**: Plays the entire section from 0.0s to total duration.
- **`[ Selection ]`**: Focuses playback only across the selected assets.
- **`[ Project ]`**: Sequences playback across all project sections sequentially.

# Whiteboard Studio — UI Architecture

> **Architecture:** PySide6 Desktop Workstation  
> **Key View:** `StudioEditorView` as the Unified Creative & Preview Hub  

---

## 1. UI Hierarchy & Component Architecture

```
StudioMainWindow (QStackedWidget)
│
├── Page 0: ProjectBrowser (Projects list, recent projects, new project dialog)
├── Page 1: WorkspaceView (Section cards, status badges, task telemetry)
├── Page 2: ProcessingMonitorView (Live DAG pipeline execution monitor)
└── Page 3: StudioEditorView (THE UNIFIED CREATIVE WORKSPACE)
     │
     ├── Top: StudioToolbar
     │    ├── Transport (Jump Start, Play/Pause, Stop)
     │    ├── Scope Selector ([Shot] [Section] [Selection] [Project])
     │    ├── Tool Actions (+Text, +SFX, Fit 1080p, Zoom)
     │    └── Pipeline (Save Layout, Render Section)
     │
     ├── Center Splitter (Horizontal):
     │    ├── Left: ShotsPanel (Camera shot list, +Add Shot)
     │    ├── Center: StudioCanvasView & StudioCanvasScene (1080p Interactive View)
     │    └── Right: StudioInspectorPanel (Contextual properties, AUTO/USER ownership)
     │
     └── Bottom Splitter (Vertical):
          └── StudioTimelineView & TimelineCanvasWidget (4-Track Sequencer)
               ├── Track 1: VOICE (Whisper words, locked)
               ├── Track 2: VISUALS (Asset draw & hold bars)
               ├── Track 3: SFX (Diamond cue markers)
               └── Track 4: CAMERA (Shot intervals)
```

---

## 2. Signal & Event Flow

1. **Canvas Manipulation** $\longrightarrow$ `element_geometry_changed` $\longrightarrow$ Updates `elements_data` $\longrightarrow$ Updates Inspector $\longrightarrow$ Marks `is_dirty = True`.
2. **Timeline Dragging** $\longrightarrow$ `element_timing_changed` $\longrightarrow$ Updates start time & duration $\longrightarrow$ Updates Inspector $\longrightarrow$ Marks `is_dirty = True`.
3. **Playhead Scrubbing** $\longrightarrow$ `time_scrubbed(sec)` $\longrightarrow$ `canvas_scene.update_playhead(sec)` $\longrightarrow$ Instant opacity & inking update across all canvas items.
4. **Playback Timer (30 FPS)** $\longrightarrow$ `_on_playback_tick` $\longrightarrow$ Advances playhead smoothly $\longrightarrow$ Loops based on active `preview_scope`.

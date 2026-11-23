# Whiteboard Studio — Preview Architecture

> **Architecture:** Integrated Live Canvas & Video Preview Engine  
> **Key Rule:** Preview is an integrated capability of `StudioEditorView`, NOT a separate application screen.  

---

## 1. Preview Capabilities Inside Studio

1. **Interactive Inking & Animation Simulation**:
   - As the playhead advances, visual elements transition through pre-draw (faint), drawing (inking progress), and hold states.
2. **Camera Motion Visualization**:
   - The active camera frustum dynamically updates to mirror keyframe zooms and pan trajectories.
3. **Auditory Preview**:
   - Original voice narration (`section_voice.wav`) is auditioned alongside positioned SFX cues (`pop`, `whoosh`).
4. **Scope-Aware Playback**:
   - **`[ Shot ]`**: Isolates and loops current camera shot for precise staging.
   - **`[ Section ]`**: Auditions the entire section sequence.
   - **`[ Selection ]`**: Focuses on selected element range.
   - **`[ Project ]`**: Sequences playback across all project sections.

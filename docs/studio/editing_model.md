# Whiteboard Studio — Editing Model & Invalidation Architecture

> **Principle:** Direct Manipulation with Selective, Minimal Invalidation  

---

## 1. Single Authoritative State

The application maintains **one single authoritative editable state**:
$$\text{Editable Section State} \longrightarrow \text{Live Preview Engine} \longrightarrow \text{Render Plan} \longrightarrow \text{Final 1080p Video}$$

There are no separate copies for "Editor State" vs "Preview State". Live playback reflects the current editable state directly in memory.

---

## 2. Invalidation Granularity

Local visual edits must never trigger redundant full pipeline rebuilds:

| User Edit | What is Invalidated | What is Preserved |
|:---|:---|:---|
| **Asset Position (X, Y)** | Canvas Viewport, Render Plan | TTS Audio, Whisper Timing, SFX mix |
| **Asset Scale / Size** | Canvas Viewport, Render Plan | TTS Audio, Whisper Timing, SFX mix |
| **Animation Style** | Element Inking Engine, Render Plan | Audio and Camera trajectories |
| **Asset Timing (Start/Dur)** | Timeline tracks, Inking intervals | TTS Audio, Whisper Timing |
| **SFX Cue Timing** | SFX Cue list, Audio Mix step | TTS Audio, Visual Staging, Inking |
| **Camera Shot Framing** | Camera Viewport Frustum, Camera Trajectory | Visual element placement, Inking frames |
| **Script Text Mutation** | TTS, Whisper, Downstream Layout | Visual assets (unless regenerated) |

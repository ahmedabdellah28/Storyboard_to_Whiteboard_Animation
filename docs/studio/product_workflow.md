# Whiteboard Studio — Product Workflow

> **Status:** APPROVED & CANONICAL  
> **Workflow:** One-Studio User Journey (Voice Generation → Unified Studio → Render)  

---

## 1. The Unified Operating Workflow

```
[Create Project]
       │
[Add Sections] (Storyboard Images + Script Text)
       │
[Automated Processing]
   ├── 01. Storyboard Asset Extraction & Masking
   ├── 02. Voice Narration TTS & Whisper Alignment
   └── 03. Dynamic Layout & Camera Micro-zoning
       │
[Human Review Gates] (Optional fine-tuning of assets or voice)
       │
┌─────────────────────────────────────────────────────────────┐
│                 WHITEBOARD STUDIO WORKSPACE                 │
│                                                             │
│  • Visual Composition & Direct Manipulation                 │
│  • Synchronized Live Video Preview (Inking + Camera Pans)   │
│  • 4-Track Timeline (Voice, Visuals, SFX, Camera)           │
│  • Real-time Playhead Scrubbing & Transport Controls        │
│  • Scope-Aware Playback (Shot / Section / Project)          │
│  • Direct Render Triggering                                 │
└─────────────────────────────────────────────────────────────┘
       │
[1080p Production Render & Master Delivery]
```

---

## 2. Key Workflow Rules

1. **No Disjointed Preview Screen**:
   The user does not "finish editing" and then "open a preview player". The Studio itself contains the interactive playback engine and preview canvas.
2. **Immediate Feedback**:
   Moving an asset, changing timing, or adjusting a camera frame instantly updates the canvas and playback without requiring a background render.
3. **Master Audio Decoupling**:
   `master_audio.wav` is an output artifact. The creative workflow operates directly on independent voice narration and editable SFX cues.

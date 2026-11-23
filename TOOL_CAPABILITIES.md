# Verified Host Tool & Engine Capabilities (`TOOL_CAPABILITIES.md`)

All tools below were probed and verified directly on this host (`pipeline_cli.py doctor --json` + direct CLI inspection + golden production runs).

---

## 1. EffectCraft CLI (`craftApp/effectcraft/target/release/effectcraft-cli.exe`)
- **Backend:** GPU accelerated (`--gpu`) + software fallback, H.264 + AAC 48kHz stereo MP4 export.
- **Editable Project Format:** `.ecproj` (JSON readable/editable), compiled via `run --commands <commands.json> --save-as <file.ecproj>`.
- **Verified Features & Parameter Rules:**
  - `layer.timing`: use `{"layers": [name], "in": st, "out": en}` (NOT legacy `trimInToTime`).
  - `4-Color Gradient` (`effect/4-Color Gradient/color1..4`, `point1..4`) & `Vignette` (`effect/Vignette/amount`, `feather`) on solid `Backdrop` layers.
  - `Drop Shadow` (`opacity`, `distance`, `softness`), `Light Sweep` (`intensity`, `width`, `color`, `center`), `Glow` (`radius`, `intensity`), `Radio Waves` (`waveStroke/color`, `frequency`, `expansion`).
  - Native vector Bezier paths (`shape.newPath`) with Trim Paths (`layer.addShapeItem {kind: "trim"}` -> `contents/trim/start|end`).
  - Camera 2.5D (`layer.newCamera` `twoNode`, `transform/position`, `transform/poi`) + `layer.setSwitch {switch: "threeD", value: true}` + `keys.easyEase`.
  - Native Typography (`layer.newText`): supports **Arabic RTL** (`font: "Cairo"`, `direction: "rtl"`) and **English LTR** (`font: "Segoe UI"` / `"Cairo"`, `direction: "ltr"`). Use word-mode RangeSelector (`basedOn=2`) on Arabic layers to preserve cursive ligatures.
  - Empirical V5 Matrix (`config/effectcraft_capabilities.json`): `studio capabilities --probe` empirically verifies all 20 capabilities via real build/reopen/render-frame/MP4 pixel-diff checks (`19 VERIFIED`: Shape Layers, Bezier Paths, Trim Paths, Arrow Paths, Masks, Track Mattes, Text Animators, Expressions, Repeaters, Particles `ec.sim.ccparticlesystems2`, Glow, Blur, Distortion, 2.5D Depth Layers, Camera Motion, Lights & Shadows, Nested Compositions, SVG `edit.pasteSvg`, Render & Reopen `.ecproj`; `1 PARTIAL`: `arabic_rtl_text` with word-mode `basedOn=2` verified).
- **Host Benchmark / Pitfall Guard:** Avoid high `Glow` (`intensity >= 1.0`) on bright white/yellow typography cards (use `ec.generate.cclightsweep` instead); apply `threeD=true` consistently to vector connectors/icons/labels belonging to 3D diagram planes so camera push/orbit keeps labels locked to nodes.

---

## 2. PhotoCraft CLI (`craftApp/photocraft/target/release/photocraft-cli.exe`)
- **Command Mode:** `batch --actions <_pc_3x_actions.json> --in <raw_dir> --out <assets_dir> --format png`
- **Verified Action Pipeline:** `removeWhiteMatte -> defringe(width=1) -> reduceNoise(removeJpegArtifact=True) -> imageSize(300%, preserveDetails) -> smartSharpen`.
- **Companion Host Cleaning:** `core/aion/extract_stage.py` follows PhotoCraft with `<60px` isolated dot removal and neighbor-cell edge sliver stripping.

---

## 3. FFmpeg & Hardware Encoders
- **Probed Version:** FFmpeg 9.0.1 (`ffmpeg`, `ffprobe` on `PATH`).
- **Detected Encoders (`doctor --json`):** `h264_nvenc` (primary hardware encoder), `h264_qsv`, `h264_amf`, `libx264`.
- **Used For:** `-15 LUFS / -1.0 dBTP` 48kHz mono PCM audio mastering, EN `6.8kHz` light de-essing, MP4 concat/merge, and 10-frame QA thumbnail extraction.

---

## 4. Speech Synthesis & Alignment
- **TTS Engine:** `gemini-3.8-flash-tts` via `google-genai` SDK + 15-key `core.api.key_pool.APIKeyPool` (automatic daily-quota blacklisting + 429 cooldown rotation).
  - **Arabic Default:** voice `Fenrir`, profile `SAUDI_YOUTH_CREATOR`, note `HIGH_ENERGY_YOUTUBE`.
  - **English Viral Default:** voice `Puck`, profile `US_CASUAL_STORYTELLER`, note `VIRAL_PSYCHOLOGY_ENGLISH_YT`.
- **Alignment & Verification:** `FasterWhisperEngine(model_size="small", language="ar"|"en")` + `ScriptAudioAligner` + per-chunk duplicate 4-gram & word-ratio verifier + isolated tail-glitch RMS trimmer.

---

## 5. Audio SFX Assets (`core/aion/motion_and_audio.py`)
- **Basic SFX:** `assets/sfx/` (`pop`, `whoosh`, `card_snap`, `glint`, `thud`, `heartbeat`, `suspense_riser`, `sword_slash`).
- **Studio Stems:** `creative_v3/studio_pro_sfx_and_audio_stems_v3/`.
- **Mixer:** Pure NumPy stereo RMS envelope ducking (`0.42x` during speech, smooth 60ms attack/release window, `np.tanh` soft limiting).

---

## 6. Validation & Recovery Engines
- `EnvironmentDoctor` (`core/validation/environment_doctor.py`): FFmpeg, GPU encoders, disk space (`doctor --json`).
- `PostRenderQAEngine` (`core/validation/post_render_qa.py`): Resolution `1920x1080`, 16:9 ratio, black frame bursts, A/V drift (`<0.35s`), audio clipping, plus 10-frame `qa_contact_sheet.png`.
- `CrashReconciliationEngine` & `IsolatedRunManager` (`core/aion/run_manager.py`): Stage checkpoints in `run_manifest.json` + `StateStore`, resume (`--resume`), and pre-stage file snapshots for rollback on failure.

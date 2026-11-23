# AION Studio V6 — Whiteboard Motion Graphics & Shorts Production Engine

Automated CLI-first studio pipeline for producing **16:9 Whiteboard Motion Graphics Explain Videos** and **9:16 Viral Shorts** using `pipeline_cli.py`, **EffectCraft GPU Compiler**, **PhotoCraft 3x HD Extractor**, **Faster-Whisper Word Alignment**, and **Gemini TTS**.

---

## Documentation & Governance Map

- **[AGENTS.md](AGENTS.md)** — Mandatory Studio Constitution & safety rules (CLI-first workflow, zero pre-render image reading, isolated run directories, golden integrity).
- **[SKILL.md](SKILL.md)** & **[.agents/skills/whiteboard_motion_graphics/SKILL.md](.agents/skills/whiteboard_motion_graphics/SKILL.md)** — Production creative directing skill & Typography/Motion V6 standards.
- **[CLI_REFERENCE.md](CLI_REFERENCE.md)** — Auto-generated live CLI command specification (`python pipeline_cli.py cli-spec --write-docs`).

---

## Quickstart (Fresh Windows Machine)

### 1. Python Environment
Requires **Python 3.11 – 3.13 (64-bit)** on Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. FFmpeg & CraftApp Binaries
- **FFmpeg & FFprobe:** Install FFmpeg and ensure `ffmpeg` and `ffprobe` are on your system `PATH` (or place `ffmpeg.exe` / `ffprobe.exe` inside `bin/`).
- **EffectCraft & PhotoCraft:**
  - Included pre-placed in the **Portable ZIP** (`craftApp/effectcraft/target/release/effectcraft-cli.exe`, `craftApp/photocraft/target/release/photocraft-cli.exe`, `openh264-2.5.0-win64.dll`).
  - If cloning from GitHub, copy those release binaries into `bin/` or `craftApp/<app>/target/release/` (or set `EFFECTCRAFT_CLI` / `PHOTOCRAFT_CLI` in `.env`).

### 3. API Keys Setup
```powershell
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY (plus optional GEMINI_API_KEY2..N for rotation)
```

### 4. Verify Installation
```powershell
python pipeline_cli.py doctor --json
python pipeline_cli.py studio doctor --json
python pipeline_cli.py studio fonts --verify-sha --json
```

---

## Standard Production Workflow

```powershell
# 1. Create / switch active project
python pipeline_cli.py init my_video
python pipeline_cli.py use my_video

# 2. Check project status
python pipeline_cli.py status --detailed --project my_video

# 3. Voiceover + Faster-Whisper Word Alignment
python pipeline_cli.py voice --project my_video --section section_01
python pipeline_cli.py timing --project my_video --section section_01

# 4. Storyboard Extraction (PhotoCraft 3x HD) + Semantic Brief
python pipeline_cli.py extract --project my_video --section section_01
python pipeline_cli.py brief --project my_video --section section_01

# 5. Render GPU Video (Default: 720p — pass `--resolution 1080p` for Full HD) + QA + Merge
python pipeline_cli.py studio compile --project my_video --section section_01
# Optional 1080p Full HD:
# python pipeline_cli.py studio compile --project my_video --section section_01 --resolution 1080p
python pipeline_cli.py qa --project my_video --section section_01
python pipeline_cli.py merge --project my_video

# 6. 9:16 Shorts Pipeline (reuses mastered audio + shared CTA; default 720x1280)
python pipeline_cli.py studio shorts --action inspect --project my_video
python pipeline_cli.py studio shorts --action compile --project my_video --all

# 7. Export existing 1080p MP4s down to 720p if needed
python pipeline_cli.py studio export-720p --input projects/my_video/exports/runs/run_01
```

---

## Project Structure (Clean Repository Layout)

```text
├── pipeline_cli.py                 # Main unified CLI entrypoint
├── requirements.txt                # Verified Python package requirements
├── .env.example                    # Safe environment variable template
├── AGENTS.md / SKILL.md            # Studio rules & creative direction skill
├── CLI_REFERENCE.md                # Live CLI specification
├── .agents/skills/                 # Agent skill playbooks
├── core/                           # AION pipeline core, compilers, typography, shorts, QA
├── core_engine/                    # EffectCraft motion studio, SFX director, compositor
├── voice_studio/                   # Gemini TTS & voice profiles
├── section_timing/                 # Faster-Whisper transcription & word-script aligner
├── production_engine/              # Dynamic section, motion & audio mixing engines
├── dev_separator/                  # Panel/choreographer utilities
├── creative_v3/
│   ├── asset_factory/              # Procedural SVG icons & props
│   └── studio_pro_sfx_and_audio_stems_v3/  # Pro SFX stems
├── assets/
│   ├── typography/                 # Commercial-safe OFL Arabic & Latin fonts + registry
│   ├── sfx/ & gifs/ & audio/cta/   # Studio SFX, micro-overlays & shared CTA tracks
├── config/                         # Capabilities registry, semantic & typography rules
└── tests/aion_cli/                 # Automated non-regression CLI & creative quality suite
```

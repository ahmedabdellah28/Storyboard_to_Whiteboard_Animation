# AI Agent Rules & Repository Protection Policy (`AGENTS.md`)

Any AI coding or directing agent operating inside `e:\image_to_animate` MUST enforce these non-negotiable rules:

## 1. CLI-First Discipline
- Check `SKILL.md` and `CLI_REFERENCE.md` before reading pipeline internals or writing any code.
- Always inspect existing project state first:
  `python pipeline_cli.py status --detailed --project <name>`
- Execute standard production stages (`script`, `voice`, `timing`, `extract`, `semantic-map`, `brief`, `direct`, `motion`, `sfx`, `render`, `qa`, `merge`) exclusively through `pipeline_cli.py`.
- Never write per-video duplicate Python scripts for voice synthesis, Whisper alignment, storyboard cropping, audio ducking, or FFmpeg merging. If a reusable capability is genuinely missing, extend `core/aion/*` and wire it cleanly into `pipeline_cli.py` with tests first.

## 2. Golden Reference Immutability (`projects/mind_glitches_ar`)
- `projects/mind_glitches_ar` is the **immutable golden reference project**.
- **NEVER** modify, overwrite, rename, or delete any file inside `projects/mind_glitches_ar/`.
- Never set `.active_project` permanently to a temporary test project (`use` / test fixtures must restore original `.active_project`).
- Verify golden integrity before and after changes:
  `python tests/aion_cli/golden_snapshot.py verify --project mind_glitches_ar`

## 3. Non-Destructive Isolated Runs & Rollback
- All new AION renders and merges MUST write into isolated run directories under:
  `projects/<project_name>/exports/runs/<run_id>/`
- Never overwrite outputs from an earlier completed run unless explicitly re-targeting the same `--run-id` with `--force`.
- Always keep rollback enabled (default) so a failing stage restores prior snapshots and removes half-written outputs while keeping earlier successful stages resumable via `--resume`.

## 4. Directing Quality & Visual QA Rules
- Validate `scene_graph.json` against dark/warm `card_style` contrast rules and avoid intense additive `Glow` (`>= 1.0`) over bright white/yellow typography cards (use `Light Sweep` instead).
- Never feed placeholder template text (`[اكتب هنا نص السكربت الصوتي ...]`) to TTS.
- Never truncate Gemini TTS narration; mix SFX exclusively via RMS ducking.
- Always run `python pipeline_cli.py qa` and inspect `qa_contact_sheet.png` visually before declaring any render ready.

## 5. Studio Constitution: Mechanical CLI vs. JSON-Driven Model Creativity
- **CLI for Mechanical Execution (No Model Guessing):** Always use `pipeline_cli.py` for deterministic operations: script splitting, TTS synthesis, Faster-Whisper word/sentence alignment, 4-row contour extraction, audio slicing + reusable CTA concatenation (`cta_channel_ar_fenrir.wav`), `.ecproj` compilation, GPU rendering, SFX ducking, QA contact-sheet generation, and FFmpeg master merging.
- **AI Model for Creative Direction (Pure JSON + Audio Timing Context):** The AI model's role is creative directing, narrative structuring, typography pairing, and motion choreography using **JSON data only**:
  - `sections/section_XX/timing/section_XX_timing_master.json` (exact word & sentence timestamps)
  - Visual asset JSON catalogs (`inputs/storyboard_catalog/*.json`, `semantic_manifest.json`, `assets/metadata.json`, or `python pipeline_cli.py studio shorts --action inspect --project <name>`)
  - Mastered audio durations and sentence boundaries (`voice/section_XX.wav`)
- **Zero Pre-Render Image Reading Rule:** **NEVER** read or analyze raw storyboard sheets (`inputs/storyboards/*.png`) or individual extracted PNGs (`entity_*.png`) during planning, scripting, or directing (whether for Long-Form 16:9 or Shorts 9:16). Understand all visual elements strictly from their JSON descriptions and roles.
- **Post-Render Visual Inspection Only:** Only open rendered QA contact sheets (`qa/creative_contact_sheet.png`, `qa/mobile_preview.png`, `qa_contact_sheet.png`) **after production** to verify final visual quality or when diagnosing a post-production error.
- **Audio Reuse First for Shorts:** When producing Shorts from an existing long-form project, never re-synthesize narrative voiceover if the mastered audio is usable; slice at clean sentence boundaries from `timing_master.json` and append the shared channel CTA (`assets/audio/cta/cta_channel_ar_fenrir.wav`).

## 6. Pre-Change Regression Rule
- Run non-regression checks before and after any change to `pipeline_cli.py` or `core/aion/*`:
  `pytest tests/aion_cli/ -v`
- Whenever CLI flags or subcommands change, regenerate `CLI_REFERENCE.md` from the live parser:
  `python pipeline_cli.py cli-spec --write-docs`

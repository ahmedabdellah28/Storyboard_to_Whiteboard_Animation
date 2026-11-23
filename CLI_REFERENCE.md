# AION CLI Command Reference (`CLI_REFERENCE.md`)

> Auto-generated directly from the live `argparse` tree inside `pipeline_cli.py` via `python pipeline_cli.py cli-spec --write-docs`.

## Global Invocation

```bash
python pipeline_cli.py [--project <name>] <subcommand> [options]
```

### Global Options

| Flag | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `--project` | No | `None` | Specify project name (overrides active project) |
| `--strict` | No | `False` | Exit non-zero if any stage fails or reports errors |

## Pipeline Stage Sequence

`script -> voice -> timing -> extract -> semantic-map -> brief -> direct -> motion -> sfx -> render -> qa -> merge`

## Subcommands

### `init` (aliases: `new`)
_Initialize a new isolated video project_

```bash
python pipeline_cli.py init <name> [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `name` | Yes | — | — | Project name (e.g. quantum_physics, alexander_the_great) |
| `--sections` | No | — | `10` | Number of sections to scaffold (default: 10) |
| `--desc` | No | — | `` | Short description of the video |
| `--lang` | No | `ar`, `en` | `ar` | Project language (ar or en; default: ar) |
| `--dialect` | No | — | `` | Accent/dialect tag (e.g. us_casual, saudi_white) |
| `--voice` | No | — | `` | Override TTS voice name (e.g. Puck, Fenrir) |

### `use` (aliases: `switch`)
_Switch active working project_

```bash
python pipeline_cli.py use <name>
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `name` | Yes | — | — | Name of project to activate |

### `projects` (aliases: `list`)
_List all video projects_

```bash
python pipeline_cli.py projects
```

### `paths` (aliases: `info`)
_Show exact input/output paths for project_

```bash
python pipeline_cli.py paths [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--project` | No | — | — | Project name (overrides active project) |

### `script`
_Split and validate section scripts from master_script_

```bash
python pipeline_cli.py script [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01) |
| `--all` | No | — | `False` | Process all sections |
| `--no-split` | No | — | `False` | Validate without splitting master_script |
| `--project` | No | — | — | Project name (overrides active project) |

### `voice`
_Generate Voiceover_

```bash
python pipeline_cli.py voice [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01, 02, 03) |
| `--all` | No | — | `False` | Generate all sections |
| `--model` | No | — | — | TTS model override (default: gemini-3.1-flash-tts-preview) |
| `--dialect` | No | — | — | Optional dialect override (e.g. saudi_white, egyptian, egyptian_female, us_casual) |
| `--voice` | No | — | — | Optional Gemini prebuilt voice override (e.g. Fenrir, Kore, Puck) |
| `--force` | No | — | `False` | Regenerate cached TTS chunks |
| `--no-verify` | No | — | `False` | Skip per-chunk Faster-Whisper QA verification |
| `--pipeline` | No | `aion`, `legacy` | `aion` | Voice backend (default: aion) |
| `--project` | No | — | — | Project name (overrides active project) |

### `timing`
_Generate Timing & SRT_

```bash
python pipeline_cli.py timing [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01, 02, 03) |
| `--all` | No | — | `False` | Align all sections and build timing index |
| `--force` | No | — | `False` | Force Whisper re-transcription |
| `--project` | No | — | — | Project name (overrides active project) |

### `extract`
_Topological Asset Extractor_

```bash
python pipeline_cli.py extract [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01, 02, 03) |
| `--all` | No | — | `False` | Extract all sections |
| `--mode` | No | `grid`, `contour` | `grid` | Extraction mode (default: grid) |
| `--rows` | No | — | `4` | Grid rows for grid mode (default: 4) |
| `--cols` | No | — | `5` | Grid cols for grid mode (default: 5) |
| `--from-zip` | No | — | — | Import pre-extracted section assets & manifest.json from a ZIP archive |
| `--project` | No | — | — | Project name (overrides active project) |

### `semantic-map` (aliases: `map`)
_Map storyboard assets to timing sentences_

```bash
python pipeline_cli.py semantic-map [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01) |
| `--all` | No | — | `False` | Map all sections |
| `--force` | No | — | `False` | Overwrite existing semantic_map.json |
| `--project` | No | — | — | Project name (overrides active project) |

### `brief`
_Generate/validate AION Creative Brief_

```bash
python pipeline_cli.py brief [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01) |
| `--all` | No | — | `False` | Generate briefs for all sections |
| `--force` | No | — | `False` | Overwrite existing creative_brief.json |
| `--project` | No | — | — | Project name (overrides active project) |

### `direct`
_Generate or validate AION scene_graph.json_

```bash
python pipeline_cli.py direct [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01) |
| `--all` | No | — | `False` | Direct all sections |
| `--force` | No | — | `False` | Regenerate existing scene_graph.json |
| `--project` | No | — | — | Project name (overrides active project) |

### `motion`
_Prepare exhibit cards / soft-bottom asset derivatives_

```bash
python pipeline_cli.py motion [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01) |
| `--all` | No | — | `False` | Prepare all sections |
| `--run-id` | No | — | — | Isolated run ID |
| `--project` | No | — | — | Project name (overrides active project) |

### `sfx`
_Mix narration WAV with RMS-ducked studio SFX_

```bash
python pipeline_cli.py sfx [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01) |
| `--all` | No | — | `False` | Mix all sections |
| `--run-id` | No | — | — | Isolated run ID |
| `--project` | No | — | — | Project name (overrides active project) |

### `render`
_Render Master Video (720p default, or --resolution 1080p)_

```bash
python pipeline_cli.py render [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01, 02, 03) |
| `--all` | No | — | `False` | Render all sections |
| `--engine` | No | `python`, `effectcraft` | `effectcraft` | Render engine (default: effectcraft) |
| `--pipeline` | No | `auto`, `aion`, `legacy` | `auto` | Pipeline mode (default: auto) |
| `--resolution` | No | `720p`, `1080p`, `full`, `half`, `third`, `quarter` | `720p` | Output resolution (default: 720p; pass 1080p or full for 1920x1080) |
| `--run-id` | No | — | — | Isolated run ID (prevents overwriting previous runs) |
| `--no-gpu` | No | — | `False` | Disable GPU rendering flag |
| `--no-rollback` | No | — | `False` | Keep partial outputs on render failure |
| `--project` | No | — | — | Project name (overrides active project) |

### `qa`
_Run PostRender QA + 10-frame Contact Sheet + Scene Graph Audit_

```bash
python pipeline_cli.py qa [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01) |
| `--all` | No | — | `False` | QA all sections |
| `--run-id` | No | — | — | Isolated run ID to inspect |
| `--project` | No | — | — | Project name (overrides active project) |

### `effects`
_EffectCraft Motion Effects Studio_

```bash
python pipeline_cli.py effects [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--list` | No | — | `False` | List all 15 available effects |
| `--demo` | No | — | — | Render specific effect demo |
| `--all` | No | — | `False` | Render all 15 effect demos |

### `status`
_Show pipeline status matrix_

```bash
python pipeline_cli.py status [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--detailed` | No | — | `False` | Show isolated run & resume stage state |
| `--project` | No | — | — | Project name (overrides active project) |

### `merge`
_Merge rendered sections into master documentary_

```bash
python pipeline_cli.py merge [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--run-id` | No | — | — | Isolated run ID to merge |
| `--pipeline` | No | `auto`, `aion`, `legacy` | `auto` | Merge mode (default: auto) |
| `--out` | No | — | — | Optional explicit output MP4 path |
| `--project` | No | — | — | Project name (overrides active project) |

### `enhance`
_Apply Micro-Retention GIF Overlays with Pure Voiceover (Zero-BGM Policy)_

```bash
python pipeline_cli.py enhance [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--section` | No | — | — | Section number (e.g. 01, 02) |
| `--all` | No | — | `False` | Enhance all sections in project |
| `--project` | No | — | — | Project name (overrides active project) |

### `doctor`
_Check FFmpeg, CraftApp binaries, GPU, storage & Gemini keys_

```bash
python pipeline_cli.py doctor [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--json` | No | — | `False` | Print JSON diagnostic output |

### `keys-check`
_Probe Gemini API key limits/quotas for TTS or Gemini models_

```bash
python pipeline_cli.py keys-check [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--model` | No | — | `gemini-3.1-flash-tts-preview` | Target Gemini model (default: gemini-3.1-flash-tts-preview) |
| `--json` | No | — | `False` | Print JSON key health report |

### `cli-spec`
_Print live CLI schema JSON and optionally generate CLI_REFERENCE.md_

```bash
python pipeline_cli.py cli-spec [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--write-docs` | No | — | `False` | Regenerate root CLI_REFERENCE.md from live parser |

### `studio`
_AION Creative Studio V5 (ECGC compiler, capabilities & visual QA)_

```bash
python pipeline_cli.py studio
```

#### `studio doctor`
_Check Studio V5 readiness, capabilities registry & golden integrity (read-only)_

```bash
python pipeline_cli.py studio doctor [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--json` | No | — | `False` | Print JSON diagnostic payload |

#### `studio capabilities`
_Inspect or empirically probe EffectCraft capabilities_

```bash
python pipeline_cli.py studio capabilities [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--probe` | No | — | `False` | Run live EffectCraft probes & refresh config/effectcraft_capabilities.json |
| `--only` | No | — | — | Comma-separated subset of capability IDs to probe |
| `--gpu` | No | — | `False` | Request GPU backend during live probe |
| `--json` | No | — | `False` | Output capabilities JSON |

#### `studio fonts`
_Inspect/verify licensed studio fonts, SHA-256 & EffectCraft render status_

```bash
python pipeline_cli.py studio fonts [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--probe` | No | — | `False` | Run live EffectCraft RTL/Tashkeel/mobile font & kinetic render probe |
| `--verify-sha` | No | — | `False` | Verify downloaded font & license SHA-256 checksums on disk |
| `--json` | No | — | `False` | Output font registry JSON |

#### `studio graphics-test`
_Verify Motion Grammar, Procedural Vectors & Scene Graph V2_

```bash
python pipeline_cli.py studio graphics-test [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--mode` | No | `all`, `scientific_explanation`, `cinematic_2_5d`, `editorial_motion_graphics` | `all` | Graphic test blueprint mode |
| `--out-dir` | No | — | — | Optional scratch directory for test specs & previews |
| `--render-preview` | No | — | `False` | Render live EffectCraft preview PNGs during test |

#### `studio compile`
_Direct Scene Graph V2 + ECGC compile + MP4 render inside isolated run dir_

```bash
python pipeline_cli.py studio compile [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--project` | No | — | — | Project name (overrides active project) |
| `--section` | No | — | — | Section number or ID (e.g. 01 or section_01) |
| `--all` | No | — | `False` | Compile all sections sequentially inside shared isolated run |
| `--style-mode` | No | `auto`, `scientific_explanation`, `cinematic_2_5d`, `editorial_motion_graphics` | `auto` | Visual treatment style mode |
| `--format` | No | `educational`, `narrative`, `workflow_montage`, `auto`, `legacy` | `educational` | Video montage format (default: educational / Mehmed V8 Master Edu; also narrative, workflow_montage for ANKARA_PRODUCTION staged scenes, auto, or legacy) |
| `--aspect` | No | `16:9`, `9:16` | `16:9` | Composition aspect ratio (default: 16:9) |
| `--story-genre` | No | `auto`, `psychological_cinematic`, `historical_documentary`, `shorts_viral_9x16`, `scientific_explanation`, `english_editorial` | `auto` | Typography & kinetic pacing story genre |
| `--run-id` | No | — | — | Isolated run ID under exports/runs/ |
| `--duration` | No | — | — | Optional duration override in seconds |
| `--resolution` | No | `720p`, `1080p`, `full`, `half`, `third`, `quarter` | `720p` | Output resolution (default: 720p -> 1280x720 / 720x1280; pass 1080p or full for Full HD) |
| `--no-gpu` | No | — | `False` | Disable GPU rendering flag |
| `--director-v4` | No | — | `True` | Enable AION v2+v3+v4 Adaptive Director, Motion Plan V3 & FTS5 Resource Registry (DEFAULT: ON) |
| `--no-director-v4` | No | — | `True` | Disable AION Director v4 layer (revert to raw V7 scene graph) |
| `--force` | No | — | `False` | Overwrite explicit --run-id if already populated |

#### `studio preview`
_Fast multi-frame ECGC preview & QA check inside isolated run dir_

```bash
python pipeline_cli.py studio preview [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--project` | No | — | — | Project name (overrides active project) |
| `--section` | No | — | — | Section number or ID |
| `--all` | No | — | `False` | Preview all sections |
| `--style-mode` | No | `auto`, `scientific_explanation`, `cinematic_2_5d`, `editorial_motion_graphics` | `auto` | Visual treatment style mode |
| `--format` | No | `educational`, `narrative`, `workflow_montage`, `auto`, `legacy` | `educational` | Video montage format (default: educational / Mehmed V8 Master Edu; also narrative, workflow_montage for ANKARA_PRODUCTION staged scenes, auto, or legacy) |
| `--aspect` | No | `16:9`, `9:16` | `16:9` | Composition aspect ratio (default: 16:9) |
| `--story-genre` | No | `auto`, `psychological_cinematic`, `historical_documentary`, `shorts_viral_9x16`, `scientific_explanation`, `english_editorial` | `auto` | Typography & kinetic pacing story genre |
| `--run-id` | No | — | — | Isolated run ID |
| `--duration` | No | — | — | Optional duration override in seconds |
| `--director-v4` | No | — | `True` | Enable AION v2+v3+v4 Adaptive Director & Motion Plan V3 (DEFAULT: ON) |
| `--no-director-v4` | No | — | `True` | Disable AION Director v4 layer |
| `--force` | No | — | `False` | Overwrite explicit --run-id |

#### `studio resources`
_Search & inspect real AION v4 Resource Registry (SQLite FTS5)_

```bash
python pipeline_cli.py studio resources [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--project` | No | — | — | Project name (overrides active project) |
| `--query` | No | — | `` | Arabic/English semantic query (e.g. 'سفينة', 'glow', 'قفل') |
| `--kind` | No | `icon`, `background`, `sfx`, `effect`, `font`, `asset` | — | Filter by resource kind |
| `--section` | No | — | — | Optional section ID to include project assets |
| `--rebuild` | No | — | `False` | Rebuild FTS5 index from scratch |
| `--limit` | No | — | `12` | Max top-k candidates (default: 12) |
| `--json` | No | — | `False` | Output JSON |

#### `studio qa`
_Run Visual Intelligence QA & build creative_contact_sheet.png_

```bash
python pipeline_cli.py studio qa [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--project` | No | — | — | Project name (overrides active project) |
| `--section` | Yes | — | — | Section number or ID |
| `--run-id` | No | — | — | Specific run ID to inspect |
| `--out-dir` | No | — | — | Optional QA output directory |

#### `studio merge`
_Merge rendered Studio V5 section MP4s inside isolated run into final master_

```bash
python pipeline_cli.py studio merge [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--project` | No | — | — | Project name (overrides active project) |
| `--run-id` | No | — | — | Run ID to merge (defaults to latest run) |
| `--out` | No | — | — | Optional output master MP4 path |

#### `studio shorts`
_Autonomous 9:16 Shorts Director (inspect, plan, compile, package)_

```bash
python pipeline_cli.py studio shorts [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--project` | No | — | — | Project name (overrides active project) |
| `--action` | No | `inspect`, `plan`, `compile`, `package` | `plan` | Shorts Director workflow action |
| `--short` | No | — | — | Target Short ID (e.g. short_01) |
| `--all` | No | — | `False` | Compile all planned Shorts cleanly into isolated run |
| `--run-id` | No | — | `shorts_v6` | Isolated run ID under exports/runs/ |
| `--preview-only` | No | — | `False` | Render half-res preview.mp4 + QA only without final.mp4 |
| `--resolution` | No | `720p`, `1080p`, `full`, `half`, `third`, `quarter` | `720p` | Final render resolution (default: 720p -> 720x1280; pass 1080p or full for 1080x1920) |
| `--no-gpu` | No | — | `False` | Disable GPU acceleration flag |
| `--force` | No | — | `False` | Overwrite explicit --run-id if already populated |

#### `studio export-720p`
_Downscale rendered 1080p landscape/portrait MP4s cleanly to 720p_

```bash
python pipeline_cli.py studio export-720p [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--input` | Yes | — | — | One or more MP4 files, globs, or folders |
| `--out-dir` | No | — | — | Output folder (default: <input_parent>/720p/) |
| `--crf` | No | — | `18` | x264 visual quality CRF (default: 18) |
| `--force` | No | — | `False` | Overwrite existing 720p output files |

### `auto` (aliases: `loop`, `run-all`, `run`)
_Autonomous production loop across stages 1..12_

```bash
python pipeline_cli.py auto [options]
```

| Argument / Flag | Required | Choices | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| `--project` | No | — | — | Project name (overrides active project) |
| `--start` | No | — | `1` | Starting section number (default: 1) |
| `--end` | No | — | — | Ending section number (default: auto-detect) |
| `--engine` | No | `python`, `effectcraft` | `effectcraft` | Render engine (default: effectcraft) |
| `--pipeline` | No | `auto`, `aion`, `legacy` | `auto` | Pipeline architecture (default: auto) |
| `--from-stage` | No | `script`, `voice`, `timing`, `extract`, `semantic-map`, `brief`, `direct`, `motion`, `sfx`, `render`, `qa`, `merge` | — | Start execution at this stage |
| `--to-stage` | No | `script`, `voice`, `timing`, `extract`, `semantic-map`, `brief`, `direct`, `motion`, `sfx`, `render`, `qa`, `merge` | — | Stop execution after this stage |
| `--resume` | No | — | `False` | Resume isolated run from last successful stage |
| `--run-id` | No | — | — | Explicit isolated run ID |
| `--mode` | No | `grid`, `contour` | `grid` | Extraction mode (default: grid) |
| `--resolution` | No | `720p`, `1080p`, `full`, `half`, `third`, `quarter` | `720p` | Output resolution (default: 720p -> 1280x720; pass 1080p or full for 1920x1080) |
| `--no-gpu` | No | — | `False` | Disable GPU rendering flag |
| `--no-rollback` | No | — | `False` | Disable rollback on failure |
| `--skip-voice` | No | — | `False` | Skip voice generation |
| `--skip-timing` | No | — | `False` | Skip timing alignment |
| `--skip-extract` | No | — | `False` | Skip extraction |
| `--skip-render` | No | — | `False` | Skip rendering |
| `--skip-merge` | No | — | `False` | Skip final merge |
| `--force` | No | — | `False` | Force regeneration of all stages |

أنت الآن تعمل كـ Principal Architect + Senior Desktop Application Engineer + Production Pipeline Engineer + UX Architect لمشروع Python احترافي متخصص في إنتاج فيديوهات Whiteboard Animation.

مهمتك ليست تصميم واجهة جميلة فقط، وليست إعادة كتابة المشروع بالكامل.

مهمتك هي تصميم وتنفيذ "Whiteboard Studio" كمنصة إنتاج تفاعلية قوية، سريعة، قابلة للاسترداد بعد الأخطاء، قليلة استهلاك الموارد، وتعمل على أجهزة ضعيفة ومتوسطة وقوية، مع الحفاظ الكامل على محرك الإنتاج الحالي وعدم تكرار وظائفه.

============================================================
1. PRODUCT MISSION
============================================================

حوّل المشروع الحالي إلى Desktop Studio احترافي يشبه برامج المونتاج من حيث سهولة الاستخدام والـ Preview، لكن مخصص بالكامل لـ Whiteboard Animation.

المستخدم النهائي يجب أن يشعر أن workflow بسيط:

1. فتح البرنامج
2. إنشاء Project
3. إضافة Section
4. إدخال Storyboard + Script
5. الضغط على Process
6. البرنامج ينفذ المراحل تلقائيًا
7. إذا حدث خطأ:
   - يعالج الخطأ تلقائيًا إذا كان deterministic/retryable
   - أو يعرضه بطريقة مفهومة ويوجه المستخدم إلى مكان المشكلة
8. مراجعة استخراج العناصر
9. مراجعة الصوت
10. مراجعة الربط الدلالي
11. تعديل Camera/Shot والعناصر
12. Preview للكاميرا
13. Preview للـ Section
14. Preview لعدة Sections
15. Preview للمشروع كاملًا
16. Render
17. Post-render QA
18. إضافة Sections أخرى
19. Master Preview
20. Master Assembly
21. Master QA
22. Final Deliverable

لكن تحت هذه التجربة البسيطة يجب أن توجد بنية Production قوية.

============================================================
2. SOURCE OF TRUTH
============================================================

استخدم الملفات والarchitecture الحالية في المشروع كمصدر أساسي.

يجب احترام الإنتاج الحالي والمواصفات الحالية، خاصة:

- core/orchestration/
- core/state/
- core/artifacts/
- core/contracts/
- core/vision/
- core/narrative/
- core/scheduling/
- production_engine/
- kivy/engine/render/

المسار canonical الحالي هو:

ProductionOrchestrator
→ SectionWorker
→ TaskDAGExecutor
→ pipeline stages

ويجب عدم إنشاء Pipeline ثانية داخل UI.

الواجهة مجرد Client/Director Layer فوق Core.

يجب الحفاظ على:

- TTS
- zero-truncation handling
- Whisper timing
- adaptive extraction
- semantic mapping
- choreography
- layout
- camera logic
- SFX
- ducking
- inking
- hand compositor
- NVENC
- fallback rendering
- section rendering
- master assembly
- reels/export
- artifact cache
- state
- resume
- retries
- resource pools

لا تستبدل هذه الأنظمة بدون سبب واضح.

لا تعيد كتابة renderer الحالي لمجرد بناء UI جديد.

============================================================
3. VERY IMPORTANT: ARCHITECTURAL MINDSET
============================================================

لا تتعامل مع المشروع كبرنامج مونتاج تقليدي.

لا تبدأ من:

UI
→ Timeline
→ Render

ابدأ من:

Product Workflow
→ State
→ Artifacts
→ Dependencies
→ Validation
→ Recovery
→ Resource Governance
→ Editing Model
→ Preview
→ Render
→ Master

الهدف هو أن يكون UI انعكاسًا لهذه المنظومة وليس مصدر الحقيقة الخاص بها.

============================================================
4. FIRST TASK: FORENSIC REPOSITORY AUDIT
============================================================

قبل تعديل أي ملف:

افحص المشروع الحالي بالكامل بالقدر اللازم لفهم:

- current UI
- entry points
- canonical orchestrator
- section lifecycle
- task DAG
- artifact identity
- state store
- extraction
- TTS
- Whisper
- semantic mapping
- layout
- pre-render director
- rendering
- SFX
- master assembly
- legacy wrappers
- existing tests
- current configuration
- current logging
- resource pools
- cache behavior

لا تفترض وجود شيء لم تتحقق منه.

أنشئ قبل التنفيذ:

docs/studio/current_architecture_audit.md

يحتوي:

1. Current architecture
2. Current runtime path
3. Existing reusable modules
4. Existing duplicated modules
5. Current state behavior
6. Current cache behavior
7. Current resource management
8. Existing failure points
9. Existing rendering path
10. UI replacement boundaries
11. Risks
12. Migration strategy

لا تغير behavior الإنتاجي في مرحلة الـ audit.

============================================================
5. ARCHITECTURAL RULE:
#1
============================================================

UI MUST NOT directly call:

- Whisper
- TTS provider
- OpenCV extraction
- FFmpeg
- NVENC
- SFX mixer
- low-level renderer

UI calls Core Services only.

Example:

UI:
process_section(section_id)

Core:
WorkflowManager
→ Orchestrator
→ DAG
→ workers

UI:
preview_camera(section_id, shot_id)

Core:
PreviewService

UI:
update_asset_position(...)

Core:
EditingService
→ revision
→ patch
→ invalidation
→ preview invalidation

============================================================
6. NEW ARCHITECTURE
============================================================

أنشئ طبقات واضحة:

core/
    workflow/
    validation/
    recovery/
    editing/
    preview/
    runtime/

ui/
    app/
    models/
    services/
    qml/
    theme/

مع الحفاظ على الوحدات الحالية.

المكونات الرئيسية المطلوبة:

A. Workflow Engine

core/workflow/
- project_workflow.py
- section_workflow.py
- stage_state.py
- transitions.py
- workflow_events.py

B. Validation

core/validation/
- project_validator.py
- storyboard_validator.py
- script_validator.py
- extraction_validator.py
- audio_validator.py
- whisper_validator.py
- semantic_validator.py
- choreography_validator.py
- camera_validator.py
- audio_mix_validator.py
- render_preflight_validator.py
- post_render_validator.py
- master_validator.py

C. Recovery

core/recovery/
- recovery_action.py
- recovery_registry.py
- recovery_policy.py
- handlers/

D. Editing

core/editing/
- command.py
- undo_redo.py
- project_patch.py
- revision_manager.py
- invalidation.py

E. Preview

core/preview/
- preview_service.py
- preview_plan.py
- preview_cache.py
- preview_session.py

F. Runtime / Performance

core/runtime/
- resource_governor.py
- worker_manager.py
- task_priority.py
- memory_budget.py
- process_manager.py
- cancellation.py
- runtime_profile.py

============================================================
7. DATA MODEL
============================================================

صمم نماذج قوية وواضحة.

Project:

- id
- name
- slug
- created_at
- updated_at
- version
- sections
- master_state

Section:

- id
- name
- order
- storyboard_ref
- script_ref
- source_revision
- processing_state
- assets_state
- voice_state
- whisper_state
- semantic_state
- choreography_state
- preview_state
- render_state
- publish_state

Asset:

- id
- sheet_order
- source_bbox
- source_revision
- artifact_ref
- role
- required
- semantic_refs
- draw_demand
- complexity
- crop metadata
- validation state

Shot / Camera:

- id
- order
- speech_range
- asset_refs
- overlay_refs
- viewport
- camera_motion
- event_refs
- revision

Audio:

- source
- chunks
- duration
- voice config
- artifact hash
- verification state

Text Overlay:

- id
- text
- direction
- position
- size
- rotation
- font
- weight
- alignment
- visibility
- animation
- shot_ref

Every object that can change must be versionable/revision-aware.

============================================================
8. USER SOURCE VS DERIVED DATA
============================================================

افصل بوضوح بين:

SOURCE TRUTH

- original storyboard
- original script
- original user project structure

USER INTENT

- accepted/rejected asset
- merge/split
- semantic anchor edits
- shot grouping
- camera edits
- element timing edits
- position
- scale
- animation
- text overlays

DERIVED DATA

- extracted assets
- TTS
- Whisper
- semantic candidates
- layout
- choreography
- final render plan

DELIVERABLES

- previews
- section videos
- master
- reels

لا تسمح أبدًا بأن يتم تعديل الـ Source Storyboard نفسه عند editing.

============================================================
9. STATE MACHINE
============================================================

لا تعتمد على file existence لتحديد نجاح المرحلة.

لكل Stage حالات:

PENDING
RUNNING
READY
NEEDS_REVIEW
FAILED
CANCELLED

مع lifecycle واضح:

PENDING
→ RUNNING
→ READY

أو:

RUNNING
→ NEEDS_REVIEW

أو:

RUNNING
→ FAILED

يجب أن تكون transitions validated.

لا تسمح بتغيير state عشوائي من UI.

============================================================
10. SECTION WORKFLOW
============================================================

من أول إنشاء Section:

STEP 0:
Create Section

STEP 1:
Preflight

STEP 2:
Parallel initial processing:

EXTRACTION
and
TTS

STEP 3:
Audio validation

STEP 4:
Whisper

STEP 5:
Extraction validation/review

STEP 6:
Semantic mapping

STEP 7:
Choreography

STEP 8:
Layout / Shot planning

STEP 9:
Camera validation

STEP 10:
Audio mix + SFX

STEP 11:
Preview readiness

STEP 12:
User review/edit

STEP 13:
Preview

STEP 14:
Render preflight

STEP 15:
Production render

STEP 16:
Post-render QA

STEP 17:
Publish

Section = READY only after all mandatory gates pass.

============================================================
11. CRITICAL:
EXTRACTION AND TTS ARE NOT THE SAME KIND OF STEP
============================================================

Extraction:

Possible problems:
- merged elements
- over-segmentation
- tiny crop
- empty crop
- clipped crop
- broken alpha
- duplicate candidate
- wrong ordering
- missing candidate
- neighboring bleed
- unexpected component

TTS:

Possible problems:
- API timeout
- rate limit
- authentication failure
- malformed output
- corrupt audio
- truncated ending
- missing chunk
- wrong duration
- chunk mismatch
- provider unavailable

The system must distinguish these problems.

Do not show generic:

"Processing failed."

Instead provide:

- stage
- exact issue
- severity
- affected artifact
- why it matters
- automated recovery if available
- user action if required
- direct navigation to problem

============================================================
12. ERROR CLASSIFICATION
============================================================

Use exactly these broad categories:

AUTO_RECOVERABLE
USER_REVIEW_REQUIRED
BLOCKING_FAILURE
CANCELLED

Examples AUTO_RECOVERABLE:

- transient network failure
- temporary API error
- failed TTS chunk
- stale temporary file
- recoverable worker crash
- temporary FFmpeg startup failure

Examples USER_REVIEW_REQUIRED:

- suspicious merge
- uncertain crop
- semantic ambiguity
- camera overcrowding
- missing visual trigger
- unusual asset
- visual mapping ambiguity

Examples BLOCKING_FAILURE:

- invalid storyboard
- invalid audio
- corrupted artifact
- schema mismatch
- impossible render plan
- missing renderer dependency
- unrecoverable output failure

============================================================
13. RECOVERY SCOPE
============================================================

Every error must specify scope:

RETRY_UNIT
RETRY_TASK
REBUILD_DOWNSTREAM
EDIT_INPUT
MANUAL_REVIEW
ABORT

Never use "rerun everything" by default.

Examples:

TTS chunk 7 failed:
→ Retry chunk 7

Whisper failed:
→ Retry Whisper

User changed position of Asset 5:
→ invalidate Preview + Render only

User changed Script:
→ invalidate TTS and downstream
but do not rerun Storyboard Extraction

User replaced Storyboard:
→ invalidate Extraction and downstream
but keep Script

============================================================
14. REVISION SYSTEM
============================================================

Every meaningful user modification creates a revision.

Example:

Section revision 17
user edits
→ revision 18

Every task must be tied to an input revision/hash.

Prevent stale task completion from overwriting newer data.

Example:

Task starts using revision 17.
User changes section to revision 18.
Task 17 finishes.

Result MUST NOT become current.

It can remain a stale artifact.

Current pointer must continue to revision 18.

This is mandatory to prevent race conditions.

============================================================
15. INVALIDATION GRAPH
============================================================

Implement explicit dependency-aware invalidation.

Rules:

Project name change:
→ metadata only

Script change:
→ TTS
→ Whisper
→ semantic mapping
→ choreography
→ layout
→ preview
→ audio mix
→ render

Storyboard change:
→ extraction
→ visual manifest
→ semantic mapping
→ choreography
→ layout
→ preview
→ render

Voice setting change:
→ TTS
→ Whisper
→ downstream timing

Asset crop change:
→ visual manifest / affected visual contracts
→ choreography if needed
→ layout if needed
→ preview
→ render

Asset position:
→ preview
→ render

Animation type:
→ SFX staging
→ audio mix
→ preview
→ render

Camera change:
→ preview
→ render

Text overlay:
→ preview
→ render

The implementation must not perform unnecessary recomputation.

============================================================
16. ARTIFACT SYSTEM
============================================================

Use existing ArtifactStore + ArtifactIdentity.

Do not treat:

"file exists"

as equivalent to valid artifact.

Artifact validity requires:

- exists
- readable
- schema valid
- correct identity/hash
- dependencies valid
- not stale
- compatible revision

Every output should be represented in the artifact system where appropriate.

============================================================
17. STARTUP PERFORMANCE
============================================================

This is a HARD requirement.

Opening the application must be lightweight.

On startup:

DO:
- load configuration
- load theme
- initialize UI shell
- load project index
- load lightweight metadata
- detect basic hardware capabilities

DO NOT:
- load Whisper model
- initialize TTS clients for everything
- start FFmpeg
- initialize NVENC renderer
- initialize heavy GPU pipeline
- load all assets
- decode all storyboards
- load all WAV files
- preload all videos
- run recursive full-project validation
- run production tasks

Heavy services must be lazy-loaded.

============================================================
18. LAZY LOADING
============================================================

Assets:

thumbnail first
→ full asset on demand
→ large preview on demand

Projects:

index first
→ metadata
→ detailed section data only when needed

Services:

TTS = lazy
Whisper = lazy
Renderer = lazy
Preview renderer = lazy
Heavy workers = lazy

Unload idle services where beneficial.

============================================================
19. RESOURCE GOVERNOR
============================================================

Implement:

core/runtime/resource_governor.py

It must manage:

- CPU concurrency
- RAM budget
- GPU usage
- GPU concurrency
- worker lifecycle
- task priority
- background throttling
- cancellation
- memory pressure
- preview priority
- render priority

Hardware-aware behavior.

Do not hardcode:

"8 CPU cores = 8 workers"

Detect available resources.

Support:

LOW
BALANCED
PERFORMANCE

and AUTO mode.

AUTO should be default.

============================================================
20. USER INTERACTION HAS PRIORITY
============================================================

When user is:

- dragging an asset
- resizing an asset
- editing text
- scrubbing
- previewing
- navigating the editor

interactive responsiveness gets higher priority than background tasks.

Background work can be throttled/deprioritized.

Example:

User opens Preview
→ GPU preview gets priority
→ background render pauses/deprioritizes

User closes Preview
→ background processing may resume

============================================================
21. NEVER BLOCK THE UI THREAD
============================================================

No heavy work on Qt UI thread.

No blocking:

- TTS
- Whisper
- OpenCV
- image extraction
- ffmpeg
- render
- master assembly
- large file IO

Use appropriate worker/process architecture.

============================================================
22. PROCESS ISOLATION
============================================================

Heavy/crash-prone workloads should be isolated when appropriate.

If renderer crashes:

UI must stay alive.

Expected:

Render Worker
→ crash

UI:
Render = FAILED
Project = SAFE
State preserved
Logs available
Retry action available

Do not let a renderer/process crash kill the Studio application.

============================================================
23. CANCELLATION
============================================================

Cancellation must be real.

User presses Stop:

- stop accepting new work
- propagate cancellation
- terminate safe child processes
- release resources
- clean temporary state
- mark task CANCELLED
- never mark partial artifact READY

UI must show cancellation progress when needed.

============================================================
24. PROJECT CREATION UX
============================================================

Startup screen:

WHITEBOARD STUDIO

[New Project]
[Open Project]
[Recent Projects]

New Project:

Project Name
[................]

[Create]

After creation:

Project
No Sections

[+ Add Section]

============================================================
25. ADD SECTION UX
============================================================

Dialog:

Section Name
Storyboard
Script

Storyboard + Script constitute one Section.

Before processing:
show summary:

Storyboard ✓
Script ✓

[Start Processing]

Do not automatically launch heavy work merely because the files were selected.

============================================================
26. PREFLIGHT
============================================================

Before processing, validate:

Storyboard:
- exists
- readable
- supported format
- non-empty
- dimensions valid
- no obvious corruption

Script:
- exists
- readable
- non-empty
- encoding valid

Environment:
- output writable
- dependencies available
- TTS configuration
- Whisper availability
- renderer availability

Preflight must be cheap.

============================================================
27. PROCESSING UI
============================================================

Do not use one generic progress bar.

Show stage cards:

Storyboard Validation
Asset Extraction
Voice Generation
Whisper
Semantic Mapping
Choreography
Layout
Audio Mix
Preview Preparation
Render

Each stage has:

- status
- progress if measurable
- elapsed
- cache hit/miss
- issue state
- action if needed

User can navigate to other Sections while processing continues.

============================================================
28. EXTRACTION REVIEW UI
============================================================

Show:

left:
original storyboard

right:
extracted assets

Asset actions:

- Accept
- Reject
- Recrop
- Split
- Merge
- Replace

Never destroy the original storyboard.

When editing extraction:
create user edit/revision.

============================================================
29. TTS REVIEW UI
============================================================

After generation:

- Play
- Pause
- waveform/duration
- chunk status
- verification status

Display:

✓ Full audio verified

or:

⚠ Chunk 7 needs attention

Actions:

[Retry Chunk]
[Retry Voice]
[Edit Script]
[Change Voice]

Do not regenerate successful chunks unnecessarily.

============================================================
30. WHISPER REVIEW
============================================================

Show:

- duration
- transcription status
- timing status
- word-level timing availability

Failure:
Retry Whisper only where possible.

Do not rerun extraction unnecessarily.

============================================================
31. SEMANTIC REVIEW
============================================================

Asset mapping UI:

Asset
→ linked phrase
→ anchor
→ trigger

User may:

- select different phrase
- remove mapping
- mark decorative
- exclude
- manually define association

Whisper remains timing truth.

Script sentence index is contextual only.
Do NOT use sentence position as timestamp.

Do NOT interpolate unknown timestamps silently.

============================================================
32. SHOT / CAMERA MODEL
============================================================

Use internal name:

SHOT

UI can display:

Camera 01
Camera 02
...

A Shot contains:

- speech range
- asset refs
- asset order
- camera viewport
- camera movement
- animation events
- text overlays

Storyboard order is immutable narrative order.

AI/system may recommend grouping but MUST NOT silently reorder the user's storyboard order.

============================================================
33. CAMERA EDITOR
============================================================

Main screen:

CENTER:
Canvas

BOTTOM:
Shots / Cameras

RIGHT:
Inspector

When Camera selected:

show:
- speech associated
- visible assets
- timing
- animations
- camera position
- zoom
- overlays

User can control how many elements are visible in that shot.

Do not force an absolute number of elements.

2–4 elements is a production guideline/default heuristic, not a hard rule.

============================================================
34. TIMELINE UX
============================================================

Do NOT build a Premiere clone.

Use a contextual timeline for selected Shot.

Show:

VOICE
Asset 1
Asset 2
Asset 3
Camera

Timeline must remain simple.

Default behavior is speech-aware.

User can manually adjust:

- anchor
- start
- draw duration
- hold

But do not require manual timestamp entry for normal workflow.

============================================================
35. TEXT TOOL
============================================================

Support:

- add text anywhere
- RTL
- LTR
- font
- size
- weight
- alignment
- position
- scale
- rotation
- optional animation

Mouse:
- drag
- resize
- reposition

Text is an independent overlay object.

Do not bake it into extracted assets.

============================================================
36. PREVIEW SYSTEM
============================================================

Implement four levels.

LEVEL 1:
Interactive Canvas Preview

No FFmpeg render on every mouse movement.

Use QML/Qt rendering.

LEVEL 2:
Camera/Shot Preview

Actual voice
Actual timing
Actual assets
Actual animation
Actual camera

LEVEL 3:
Section Preview

Complete section with:
voice
visuals
camera
SFX
transitions

LEVEL 4:
Project Preview

Multiple selected Sections or entire Project.

============================================================
37. PREVIEW MUST SHARE THE SAME LOGIC
============================================================

Do not create a completely different timing engine for Preview.

Both Preview and Final Render must consume the same semantic/choreography/render contracts where practical.

Architecture:

FINAL_RENDER_PLAN
      |
      +---- Preview
      |
      +---- Final Render

Preview can differ in:
- resolution
- encoding
- quality
- effects fidelity

But NOT:
- semantic order
- timing logic
- asset identity
- camera semantics
- animation schedule

Avoid Preview/Final mismatch.

============================================================
38. PREVIEW CACHE
============================================================

Use dependency-aware preview caching.

If user changes Asset 07 position:

Do NOT rebuild:

- TTS
- Whisper
- extraction
- semantic mapping

Only invalidate affected preview/render artifacts.

If user changes Script:

invalidate appropriate downstream stages.

Use existing ArtifactStore/Identity mechanisms.

============================================================
39. RENDER
============================================================

Before render:

Render Preflight

Validate:

- all required assets available
- camera valid
- timing valid
- viewport safe
- audio valid
- SFX valid
- output writable
- renderer available
- no unresolved blocking errors

Then:

Render
→ production renderer
→ NVENC where available
→ fallback when required

Do not rebuild a new rendering engine.

============================================================
40. POST-RENDER QA
============================================================

Do not consider:

FFmpeg exit code 0

sufficient.

Validate:

- file exists
- file readable
- video duration
- audio duration
- resolution
- frame count where applicable
- video stream exists
- audio stream exists
- sample frames
- black frames
- unexplained blank frames
- missing major visual content
- output integrity

On failure:
show direct action.

Example:

Render failed:
Camera 03
Asset 07 outside viewport

[Open Camera 03]

============================================================
41. MASTER PROJECT
============================================================

Project contains ordered Sections.

User can:

- reorder Sections
- add Sections
- open/edit Sections
- preview one
- preview selected
- preview all

Master assembly only when mandatory sections are valid.

Use existing master merger.

============================================================
42. MASTER PREVIEW
============================================================

Master Preview must use:

section outputs / preview artifacts

and allow:

- play
- pause
- seek
- jump to section
- jump to camera/shot where possible

============================================================
43. ERROR CENTER
============================================================

Create a persistent but lightweight:

Needs Attention

Example:

⚠ Section 03
Asset 07 requires review
[Review]

⚠ Section 05
Voice verification failed
[Fix]

Every problem must have:

- severity
- source
- location
- recovery options

Avoid repeated modal popups.

============================================================
44. LOGGING / DIAGNOSTICS
============================================================

Every task should have:

- task id
- section id
- revision id
- artifact id
- start time
- end time
- duration
- resource type
- cache hit/miss
- retry count
- failure category

Provide:
[Technical Details]

but hide noisy logs from normal users.

============================================================
45. AUTOSAVE
============================================================

User edits must be autosaved.

Need:

- atomic saves
- crash-safe state
- no partial project corruption
- revision-aware updates

The user should not lose edits because:
- app crashed
- renderer crashed
- system restarted
- worker failed

============================================================
46. UNDO / REDO
============================================================

Use command-based editing.

Commands:

- MoveAsset
- ResizeAsset
- ChangeAnimation
- ChangeAnchor
- ChangeTiming
- MergeAssets
- SplitAsset
- RejectAsset
- RestoreAsset
- ChangeCamera
- AddText
- EditText
- DeleteText

Undo/Redo must operate on project state, not raw file hacks.

============================================================
47. UI TECHNOLOGY
============================================================

Use:

PySide6 + Qt Quick/QML

Use QML for:
- modern desktop shell
- canvas interaction
- inspector
- cards
- transitions
- responsive UI
- preview controls

Python:
- business logic
- Core bridge
- models
- workflow
- services
- worker communication

Do NOT put production logic inside QML.

============================================================
48. UI STYLE
============================================================

Use a professional light 2026 desktop style.

Characteristics:

- light
- clean
- calm
- professional
- subtle surfaces
- restrained shadows
- clear hierarchy
- high readability
- no neon
- no excessive glass
- no visual clutter

Suggested palette:

Background:
#F6F7F9

Surface:
#FFFFFF

Secondary Surface:
#F0F2F5

Border:
#E2E5EA

Primary Text:
#172033

Secondary Text:
#667085

Accent:
#4F46E5

Success:
#16A34A

Warning:
#D97706

Danger:
#DC2626

============================================================
49. MAIN UI
============================================================

Desktop shell:

TOP:
Project name
Save state
Preview
Render

LEFT:
Tools / project sections navigation

CENTER:
Canvas / Preview

RIGHT:
Contextual Inspector

BOTTOM:
Shot / Camera navigation
Contextual timeline

The UI must adapt cleanly to different resolutions.

============================================================
50. MAIN SCREENS
============================================================

1. Project Browser
2. New Project
3. Project Overview
4. New Section
5. Preflight
6. Processing Monitor
7. Extraction Review
8. Voice Review
9. Semantic Review
10. Studio Editor
11. Camera/Shot Editor
12. Preview
13. Render Monitor
14. Render QA
15. Master Studio
16. Settings
17. Diagnostics

============================================================
51. SETTINGS
============================================================

Settings should include only meaningful controls initially:

- performance mode:
  Auto / Efficiency / Balanced / Performance

- preview quality
- cache size/budget
- worker concurrency when advanced mode enabled
- TTS configuration
- renderer options
- output location
- logging level

Avoid exposing dangerous low-level settings to normal users.

============================================================
52. PERFORMANCE RULES
============================================================

Opening application:
NO heavy task.

Opening project:
metadata first.

Opening Section:
load what is needed.

Opening Asset:
load full image lazily.

Dragging:
interactive rendering only.

Preview:
prioritize responsiveness.

Render:
use worker/process and ResourceGovernor.

Background tasks:
lower priority than interaction.

Do not consume all CPU/GPU/RAM merely because they are available.

============================================================
53. MEMORY MANAGEMENT
============================================================

Implement:

- thumbnail cache
- full asset cache
- LRU eviction
- preview cache management
- memory budgets

Do not load all project media into memory.

============================================================
54. DISK MANAGEMENT
============================================================

Separate:

SOURCE
ARTIFACT
CACHE
SCRATCH
DELIVERABLE

Temporary files must be cleaned safely.

Do not delete artifacts that are still referenced.

Use atomic writes.

============================================================
55. WORKER MANAGER
============================================================

Workers should be:

- lazy
- reusable where useful
- disposable when idle
- cancellable
- isolated where appropriate

Do not spawn unlimited workers.

============================================================
56. TASK PRIORITY
============================================================

Suggested priority:

CRITICAL USER INTERACTION
HIGH PREVIEW
HIGH USER-REQUESTED PROCESSING
NORMAL SECTION PRODUCTION
LOW BACKGROUND PREFETCH
LOW CACHE MAINTENANCE

ResourceGovernor must enforce this.

============================================================
57. AI BOUNDARIES
============================================================

Do NOT use AI/LLM for:

- state transitions
- retry logic
- cache
- invalidation
- file validation
- audio duration checks
- timing arithmetic
- resource management
- task scheduling
- crash recovery
- deterministic layout constraints
- frame validation
- basic extraction integrity checks

AI MAY be used where it already belongs:

- visual understanding
- semantic interpretation
- narrative/visual mapping
- visual review suggestions
- semantic QA
- pre-render visual director

AI suggestions must not silently mutate user truth.

============================================================
58. STORYBOARD ORDER
============================================================

This is CRITICAL:

The user's storyboard ordering is AUTHOR-DEFINED NARRATIVE TRUTH.

AI/system must NOT silently reorder assets to "improve" the story.

AI can:
- classify
- describe
- map
- suggest grouping
- flag issues

But:
sheet_order remains immutable unless the user explicitly edits it.

============================================================
59. SEMANTIC MAPPING RULES
============================================================

Support:

one sentence → multiple assets

one asset → multiple sentences

long explanation:
draw once
hold visible

Do not require one asset per sentence.

Whisper provides temporal truth.

Do not use sentence index as timestamp.

Do not silently invent timestamp for unresolved anchor.

============================================================
60. CAMERA RULES
============================================================

Current production guidelines should be treated as defaults/heuristics, not hardcoded UX limitations.

Examples:
- 2–4 related elements per visual scene
- one hero pen element
- varied secondary animations
- calm camera
- limited pans
- safe viewport margins

These are composition defaults.

The user may intentionally override them.

============================================================
61. NO BLANK SCREEN RULE
============================================================

Use current production rules:

- visuals remain visible
- no premature fade
- camera movement carries the visual story where applicable
- avoid unexplained blank intervals

But do NOT implement a simplistic global "no blank frame ever" rule without respecting intentional transitions.

Blank/empty visual regions must be interpreted according to shot intent.

============================================================
62. TESTING STRATEGY
============================================================

Every phase must add tests.

Unit:
- states
- transitions
- invalidation
- revisions
- recovery
- resource governor
- preview plans

Integration:
- create project
- create section
- process section
- TTS failure
- extraction review
- Whisper failure
- edit asset
- edit script
- resume
- cancel
- renderer failure
- post-render failure
- master assembly

Race tests:
- task finishes after revision
- user edits while processing
- cancellation while task running
- preview while background render running

Resource tests:
- low RAM simulation
- reduced CPU
- no GPU
- GPU available
- concurrent preview/render
- worker crash

UI tests:
- startup
- section creation
- processing
- navigation
- asset editing
- preview
- render monitor

============================================================
63. PERFORMANCE ACCEPTANCE TESTS
============================================================

Measure:

- app startup time
- RAM after startup
- CPU at idle
- GPU at idle
- RAM after opening project
- RAM after opening Studio
- time to display first project
- time to display first storyboard
- preview interaction latency
- camera preview startup
- section preview startup
- worker startup
- cancellation latency

Test representative hardware classes.

Never optimize based on assumptions.

Measure first.

============================================================
64. MIGRATION STRATEGY
============================================================

Do not destroy the old system immediately.

First:
- identify old UI boundary
- create new UI shell
- connect Core
- prove feature parity
- migrate workflow
- migrate preview
- migrate rendering controls

Legacy production entry points may remain temporarily as compatibility adapters.

The new UI becomes canonical only after parity and tests pass.

Do not duplicate production algorithms.

============================================================
65. DOCUMENTATION
============================================================

Create:

docs/studio/
    architecture.md
    product_workflow.md
    state_machine.md
    error_recovery.md
    resource_governance.md
    editing_model.md
    preview_architecture.md
    ui_architecture.md
    migration_plan.md
    test_strategy.md
    performance_strategy.md

Also create:

docs/studio/decision_log.md

Every major architectural decision must be documented with:
- decision
- reason
- alternatives rejected
- consequences

============================================================
66. IMPLEMENTATION PHASES
============================================================

Do NOT implement everything in one uncontrolled change.

PHASE 0
Repository audit
Architecture specification
No behavior changes

PHASE 1
Data contracts
State machine
Workflow events
Tests

PHASE 2
Invalidation + revision system
Artifact integration
Tests

PHASE 3
Validation system
Recovery system
Tests

PHASE 4
ResourceGovernor
WorkerManager
cancellation
process isolation
tests

PHASE 5
PySide6 application shell
Project browser
New Project
New Section

PHASE 6
Core Bridge
Processing monitor
section lifecycle

PHASE 7
Extraction review

PHASE 8
Voice review

PHASE 9
Semantic review

PHASE 10
Studio editor
Canvas
Shots
Assets
Inspector
Text tool

PHASE 11
Preview system

PHASE 12
Render integration
Post-render QA

PHASE 13
Master Studio

PHASE 14
Performance hardening

PHASE 15
Migration cleanup

============================================================
67. PHASE EXECUTION RULE
============================================================

For every phase:

1. inspect existing code
2. write design
3. implement smallest safe increment
4. add tests
5. run tests
6. verify integration
7. inspect regressions
8. update documentation
9. report files changed
10. report risks
11. move to next phase

Never make massive changes without validation.

============================================================
68. DEFINITION OF DONE
============================================================

The system is only considered complete when:

PROJECT:
✓ create/open/save works
✓ crash-safe

SECTION:
✓ storyboard + script
✓ preflight
✓ automatic processing
✓ parallel extraction/TTS
✓ resume
✓ retry
✓ recovery
✓ review

EXTRACTION:
✓ validation
✓ manual review
✓ merge
✓ split
✓ recrop
✓ reject
✓ no source mutation

AUDIO:
✓ TTS
✓ chunk retry
✓ truncation verification
✓ Whisper
✓ timing integrity

SEMANTIC:
✓ mapping
✓ manual correction
✓ no silent timestamp guessing

EDITOR:
✓ camera/shot selection
✓ assets
✓ timing
✓ animation
✓ positioning
✓ resizing
✓ text overlays
✓ undo/redo

PREVIEW:
✓ camera
✓ section
✓ multi-section
✓ full project
✓ same render logic/contracts

RENDER:
✓ preflight
✓ NVENC if available
✓ fallback
✓ cancellation
✓ crash isolation
✓ post-render QA

MASTER:
✓ section ordering
✓ master preview
✓ assembly
✓ master QA

PERFORMANCE:
✓ no heavy startup
✓ lazy loading
✓ memory budgets
✓ adaptive workers
✓ preview priority
✓ background throttling

ARCHITECTURE:
✓ no second production pipeline
✓ no duplicated TTS/Whisper/render logic
✓ deterministic recovery
✓ revision-safe
✓ artifact-aware
✓ test coverage
✓ documentation

============================================================
69. FORBIDDEN IMPLEMENTATION PATTERNS
============================================================

NEVER:

- rewrite the entire repository
- create a second renderer
- create a second orchestration engine
- put business logic in QML
- block UI thread
- load all assets at startup
- load Whisper at startup
- initialize renderer at startup
- render full video for every mouse movement
- rerun whole section after every edit
- rerun extraction after position change
- rerun TTS after crop edit
- use file existence as cache validity
- silently ignore errors
- silently demote required assets to decorative
- silently reorder storyboard
- silently guess timestamps
- silently overwrite newer revisions
- silently continue after a blocking validation failure
- spawn unlimited workers
- consume all CPU/GPU just because available

============================================================
70. MOST IMPORTANT PRODUCT PRINCIPLE
============================================================

The application should feel SIMPLE,
while the architecture remains COMPLEX underneath.

User sees:

Project
→ Sections
→ Processing
→ Review
→ Edit
→ Preview
→ Render
→ Master

Core handles:

State
→ DAG
→ Dependencies
→ Artifacts
→ Validation
→ Recovery
→ Resource Governance
→ Rendering

Never force the user to understand the internal architecture.

============================================================
71. REQUIRED FIRST RESPONSE FROM THE AGENT
============================================================

Before writing production code, provide:

A. Current repository architecture audit
B. Gap analysis
C. Target architecture
D. Full workflow state machine
E. Error/recovery matrix
F. Invalidation matrix
G. Resource governance design
H. UI architecture
I. Preview architecture
J. Data contracts
K. Migration plan
L. Test plan
M. Performance plan
N. File/module change map
O. Phase-by-phase implementation plan

Do not start implementation until this design is internally consistent.

After the design is produced, begin Phase 0 and then proceed sequentially.

The final implementation must preserve all existing production functionality while replacing the legacy UI with the new Whiteboard Studio architecture.

============================================================
72. FINAL ENGINEERING PRINCIPLE
============================================================

Do not optimize for:
"the UI looks modern"

Optimize for:

- correctness
- recoverability
- responsiveness
- resource efficiency
- deterministic behavior
- artifact reuse
- revision safety
- feature parity
- predictable UX
- maintainability
- production reliability

Design as though this application will eventually process hundreds of Sections across machines with very different hardware.

Think through failure before implementation.

Think through invalidation before editing.

Think through resource usage before starting workers.

Think through recovery before showing an error dialog.

Think through preview before creating a second renderer.

Think through data contracts before creating the UI.

Think through migration before deleting legacy code.

Do not agree with assumptions merely because they came from the user.
Challenge them when necessary and replace them with a technically stronger design while preserving the actual product goals.
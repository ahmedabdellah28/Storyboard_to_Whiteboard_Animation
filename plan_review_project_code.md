# ROLE

Act as the Senior Team Lead, Principal Software Architect, Distributed Systems Architect, Performance Engineer, Media Pipeline Architect, and AI Infrastructure Architect responsible for auditing the ENTIRE project.

This is NOT a dubbing-focused review.

Dubbing is only ONE feature inside a much larger production platform.

The objective is to understand, optimize, connect, and harden the ENTIRE system from project ingestion to final video delivery.

Do not optimize isolated features before understanding the whole architecture.

---

# PRIMARY OBJECTIVE

Analyze the repository as a complete production platform.

The platform may contain:

* Script ingestion
* Script analysis
* Section generation
* Storyboard processing
* Visual asset extraction
* Asset classification
* Asset metadata
* Layout planning
* Audio generation
* TTS
* ASR
* Timing
* SRT
* Visual beat synchronization
* SFX
* Audio mixing
* AI pre-render direction
* Video rendering
* GPU/NVENC processing
* Master video assembly
* Multilingual dubbing
* API/provider management
* Caching
* State management
* Configuration
* CLI/UI
* Tests
* Logging
* Temporary files
* Deliverables

Treat all of these as parts of ONE production system.

---

# PHASE 1 — COMPLETE REPOSITORY DISCOVERY

Inspect the entire repository.

Identify every:

* entry point
* pipeline
* subsystem
* provider
* service
* worker
* scheduler
* cache
* database/state store
* storage layer
* configuration source
* API client
* renderer
* audio processor
* image processor
* test suite

Do not assume architecture from filenames.

Infer the actual architecture from imports, function calls, execution flow, shared files, and data dependencies.

Produce an inventory of every major module.

---

# PHASE 2 — SYSTEM ARCHITECTURE MAP

Construct the real architecture of the complete system.

Map:

SCRIPT
↓
PROJECT
↓
SECTIONS
↓
AUDIO
↓
TIMING
↓
VISUAL PROCESSING
↓
STAGING
↓
QUALITY GATE
↓
RENDER
↓
SECTION DELIVERABLES
↓
MASTER ASSEMBLY
↓
FINAL VIDEO

Also map independent branches such as:

DUBBING
ALTERNATE LANGUAGES
RE-RENDER
PREVIEW
QUALITY CHECKS

Do not force this exact structure.

Replace it with the real structure discovered in the repository.

---

# PHASE 3 — CREATE THE REAL DEPENDENCY DAG

Identify all dependencies between tasks.

For every task determine:

* Inputs
* Outputs
* Dependencies
* Resource type
* API requirements
* CPU requirements
* GPU requirements
* Disk requirements
* Network requirements

Classify each task:

MUST BE SEQUENTIAL
PARALLELIZABLE
PARTIALLY PARALLELIZABLE
BATCHABLE
CACHEABLE
REUSABLE
RETRYABLE

Find all places where the implementation unnecessarily serializes work.

---

# PHASE 4 — PROJECT ORCHESTRATION AUDIT

Identify who currently owns:

* project creation
* section creation
* task scheduling
* task dependencies
* retries
* checkpoints
* artifact discovery
* failure recovery
* finalization

Determine whether the project has:

A REAL CENTRAL ORCHESTRATOR

or:

MULTIPLE DISCONNECTED PIPELINES.

Identify conflicts between:

* master pipeline
* section pipeline
* voice pipeline
* dubbing pipeline
* rendering pipeline
* timing pipeline

---

# PHASE 5 — SECTION ARCHITECTURE AUDIT

Treat every section as a production unit.

Map:

SECTION
├── script
├── voice
├── ASR
├── timing
├── storyboard
├── assets
├── layout
├── AI director
├── render
├── mix
└── deliverable

Determine which sections are independent.

Identify unnecessary cross-section blocking.

Determine how sections can run concurrently without exceeding system resources.

---

# PHASE 6 — AUDIO SUBSYSTEM AUDIT

Audit the entire audio architecture.

Not just dubbing.

Analyze:

* TTS
* ASR
* transcription
* alignment
* SRT
* timing
* duration matching
* SFX
* ducking
* mixing
* audio normalization
* resampling
* encoding

Detect duplicated implementations.

Detect repeated processing of the same audio.

Identify canonical audio artifacts.

Determine whether multiple systems independently run ASR on identical audio.

Design a shared audio artifact architecture.

---

# PHASE 7 — VISUAL SUBSYSTEM AUDIT

Audit:

* storyboard generation
* image generation
* storyboard extraction
* CV processing
* asset extraction
* asset classification
* asset metadata
* layout planning
* speech synchronization
* visual beats
* camera movement
* staging

Determine:

* which visual analysis is repeated
* which assets can be cached
* which asset metadata can be reused
* where AI is unnecessarily called
* where CPU processing is repeated

---

# PHASE 8 — AI LAYER AUDIT

Inventory EVERY AI/API call in the project.

For each call determine:

* provider
* model
* purpose
* prompt
* input size
* output size
* frequency
* latency
* retries
* cacheability
* dependencies
* token cost

Create:

CURRENT CALL GRAPH

and:

MINIMUM NECESSARY CALL GRAPH

Find unnecessary AI calls across the entire platform.

Do not focus only on dubbing.

Include:

* script analysis
* translation
* TTS
* image generation
* multimodal director
* classification
* validation
* any other AI call

---

# PHASE 9 — GLOBAL API INFRASTRUCTURE AUDIT

Find every API client and API-key loader.

Identify duplicated implementations.

Determine whether different subsystems independently handle:

* key rotation
* rate limiting
* retries
* cooldown
* model fallback
* circuit breaking
* connection reuse

Design ONE shared API infrastructure layer.

It must support multiple providers and models.

Do not make a giant monolithic class.

Separate:

Provider Registry
Key Pool
Rate Limiter
Scheduler
Circuit Breaker
Client Manager
Health Manager

---

# PHASE 10 — RESOURCE MANAGEMENT AUDIT

Classify workloads:

NETWORK_BOUND
CPU_BOUND
GPU_BOUND
DISK_BOUND

Examples:

API calls → NETWORK
Whisper → CPU/GPU
OpenCV → CPU
Rendering → GPU
FFmpeg → CPU/DISK
Muxing → DISK

Determine whether the current implementation allows these resource classes to overlap efficiently.

Design resource-aware worker pools.

---

# PHASE 11 — GLOBAL CACHING AUDIT

Find all existing caching.

Identify weak checks such as:

file exists
file size > X

Replace conceptual behavior with deterministic artifact identity.

Use:

SHA256(
component
+
inputs
+
configuration
+
model
+
version
)

Determine dependencies between artifacts.

Build an artifact graph.

Example:

SCRIPT
↓
ANALYSIS
↓
AUDIO
↓
ASR
↓
TIMING

and:

SCRIPT
↓
TRANSLATION
↓
TTS

and:

STORYBOARD
↓
ASSETS
↓
LAYOUT
↓
RENDER PLAN

A change must invalidate only its dependent descendants.

---

# PHASE 12 — STATE MANAGEMENT

Design a durable project state model.

The state must exist at:

PROJECT
SECTION
TASK
ARTIFACT

levels.

Possible states:

PENDING
QUEUED
RUNNING
COMPLETED
FAILED
RETRYING
BLOCKED
CANCELLED
INVALIDATED

A project restart must resume from the last valid completed artifact.

Never rerun expensive work unnecessarily.

---

# PHASE 13 — ERROR ARCHITECTURE

Create global error classification.

Classify failures by:

* task
* segment
* batch
* key
* model
* provider
* worker
* GPU
* filesystem
* network
* project

Distinguish:

TRANSIENT
PERMANENT
DEPENDENCY_FAILURE
RESOURCE_FAILURE
VALIDATION_FAILURE

Define correct recovery behavior for each.

---

# PHASE 14 — PARALLEL EXECUTION

Identify every unnecessary sequential loop.

Examples:

Section 01
wait
Section 02
wait
Section 03

should become:

Section 01 ─┐
Section 02 ─┼→ scheduler
Section 03 ─┘

when dependencies permit.

Within sections, also identify parallelizable work.

Never use unlimited concurrency.

Respect:

* provider rate limits
* API key capacity
* CPU
* RAM
* GPU
* VRAM
* disk bandwidth
* NVENC limits

---

# PHASE 15 — RENDERING ARCHITECTURE

Audit the complete rendering path.

Analyze:

* frame preparation
* asset compositing
* animation generation
* canvas rendering
* Python loops
* OpenCV operations
* FFmpeg pipes
* NVENC
* muxing
* section rendering
* master rendering

Separate:

Render Planning
Frame Preparation
Compositing
Encoding
Muxing
Publishing

Do not allow the renderer to become coupled to API orchestration.

---

# PHASE 16 — MASTER ASSEMBLY

Audit final assembly.

Determine whether:

* sections can be validated independently
* concat can be performed without re-encoding
* audio can be reused
* chapters can be regenerated independently
* one failed section forces unnecessary reconstruction of the whole film

Implement incremental master assembly where appropriate.

---

# PHASE 17 — MULTILINGUAL / DUBBING AS A SUBSYSTEM

Only after the core architecture is understood, audit dubbing.

Dubbing must consume canonical project artifacts.

It should not regenerate:

* original script analysis
* storyboard
* assets
* original TTS
* original rendering

unless explicitly required.

Languages should be modeled as production variants of the audio/output layer.

Example:

PROJECT
├── original
├── en
├── fr
└── es

rather than separate disconnected pipelines.

---

# PHASE 18 — OBSERVABILITY

Introduce global structured telemetry.

Every task should record:

project_id
section_id
task_id
artifact_id
provider
model
worker_id
start_time
end_time
duration
queue_wait
status
retry_count
cache_hit
input_size
output_size
resource_class

The system must be able to answer:

Why is the project slow?

Why did the API usage increase?

Which stage is blocking?

Which provider is slow?

Which task is repeatedly failing?

Where is CPU/GPU idle?

---

# PHASE 19 — PERFORMANCE BASELINE

Before optimization:

Measure the complete project.

Record:

* total project duration
* section durations
* audio generation
* ASR
* translation
* image processing
* asset extraction
* AI director
* rendering
* muxing
* master assembly
* API wait
* retry time
* queue wait

Create an end-to-end baseline.

Then optimize one subsystem at a time.

---

# PHASE 20 — ARCHITECTURAL COUPLING

Find modules that know too much about each other.

Identify:

* circular dependencies
* duplicated business logic
* duplicate configuration
* duplicate API handling
* duplicated file formats
* hardcoded paths
* hidden global state

Recommend clear boundaries between:

Core
Orchestration
AI
Audio
Visual
Rendering
Storage
Infrastructure
UI

---

# PHASE 21 — BUILD / INCREMENTAL PRODUCTION MODEL

Treat the system as a production build engine.

Every output is an artifact.

Every artifact has:

identity
inputs
dependencies
configuration
version
status

When one input changes, only dependent artifacts should rebuild.

This is a critical requirement.

---

# PHASE 22 — FINAL ARCHITECTURE

Produce the target architecture as:

CORE INFRASTRUCTURE
↓
PROJECT ORCHESTRATOR
↓
TASK DAG
↓
RESOURCE SCHEDULER
↓
┌───────────────┬────────────────┬───────────────┐
│ AI SERVICES   │ MEDIA SERVICES │ DATA SERVICES │
└───────────────┴────────────────┴───────────────┘
↓
ARTIFACT STORE
↓
DELIVERABLES

Clearly define responsibilities of every layer.

---

# REQUIRED OUTPUT

Before changing code, provide:

1. Complete repository architecture
2. Complete production pipeline
3. Complete dependency DAG
4. Section execution model
5. Audio architecture
6. Visual architecture
7. AI/API architecture
8. Rendering architecture
9. State architecture
10. Artifact architecture
11. Caching architecture
12. Resource/concurrency model
13. Error/retry model
14. Master assembly model
15. Dubbing as an integrated subsystem
16. Duplicated functionality
17. Unnecessary dependencies
18. Unnecessary API calls
19. Unnecessary serial execution
20. Current bottlenecks
21. Proposed target architecture
22. Exact files requiring changes
23. Migration phases
24. Tests for every phase
25. Performance benchmarks before and after

---

# CRITICAL RULE

Do NOT optimize one feature in isolation.

Do NOT treat dubbing as the center of the architecture.

The goal is to transform the entire repository into a unified production platform.

The final architecture should make it possible to add:

* new languages
* new TTS providers
* new translation providers
* new image providers
* new renderers
* new AI directors
* new output formats

without creating another independent pipeline.

The system must become:

ORCHESTRATED
PARALLEL
CACHE-AWARE
STATEFUL
RESUMABLE
RESOURCE-AWARE
FAULT-TOLERANT
OBSERVABLE
INCREMENTAL
MODULAR
EXTENSIBLE

============================================================
UI/UX DESIGN SYSTEM ADDENDUM
WHITEBOARD STUDIO — 2026 LIGHT PROFESSIONAL UX
============================================================

هذا القسم امتداد إلزامي للـ Architecture/Implementation Prompt السابق.

أنت الآن مسؤول أيضًا عن UI/UX Architecture وDesign System وInteraction Design.

لا تنفذ UI على أساس "اجعلها جميلة".
صمم تجربة استخدام احترافية كاملة لتطبيق Desktop Production Studio في 2026.

الهدف:

إنشاء واجهة Light Theme احترافية، هادئة، سريعة، واضحة، واسعة بصريًا، ومناسبة لساعات العمل الطويلة.

التطبيق ليس:
- Gaming UI
- Dashboard مليء بالبطاقات
- Neon UI
- Glassmorphism UI
- Mobile UI مكبر
- Premiere clone

التطبيق هو:

A focused creative production studio for whiteboard video creation.

============================================================
1. CORE UX PHILOSOPHY
============================================================

اعتمد المبادئ التالية:

1. Clarity over decoration
2. Canvas over controls
3. Contextual controls over permanent controls
4. Progressive disclosure
5. Minimal cognitive load
6. Stable spatial relationships
7. Strong information hierarchy
8. Fast interaction feedback
9. Consistent components
10. Calm visual language
11. Resource-aware UI
12. Error recovery instead of error interruption
13. User intent must remain explicit
14. Advanced functionality must remain accessible without clutter

لا تجعل كل الوظائف ظاهرة طوال الوقت.

اعرض الأدوات التي يحتاجها المستخدم في السياق الحالي فقط.

============================================================
2. VISUAL IDENTITY
============================================================

Create a custom design language named:

WHITEBOARD STUDIO LIGHT

Personality:

- Professional
- Calm
- Precise
- Modern
- Creative
- Technical
- Premium
- Focused

Visual impression:

"Professional creative software"

وليس:

"Developer tool"

ولا:

"Gaming application"

ولا:

"Generic SaaS dashboard"

============================================================
3. LIGHT THEME IS MANDATORY
============================================================

The primary application theme MUST be Light.

Do NOT design a dark-first interface.

Do NOT automatically introduce dark mode during the initial implementation.

The entire visual hierarchy must be designed around a light workspace.

Recommended tokens:

APP BACKGROUND
#F5F6F8

PRIMARY SURFACE
#FFFFFF

SECONDARY SURFACE
#FAFBFC

SUBTLE SURFACE
#F0F2F5

HOVER SURFACE
#F7F8FA

SELECTED SURFACE
#EEF2FF

PRIMARY TEXT
#101828

SECONDARY TEXT
#475467

TERTIARY TEXT
#667085

DISABLED TEXT
#98A2B3

BORDER
#E4E7EC

STRONG BORDER
#D0D5DD

BRAND
#4F46E5

BRAND HOVER
#4338CA

BRAND SOFT
#EEF2FF

SUCCESS
#16A34A

SUCCESS SOFT
#ECFDF3

WARNING
#D97706

WARNING SOFT
#FFFAEB

DANGER
#DC2626

DANGER SOFT
#FEF3F2

INFO
#2563EB

INFO SOFT
#EFF6FF

CANVAS
#FFFFFF

Use semantic tokens.
Do NOT scatter raw colors throughout QML.

============================================================
4. DESIGN TOKENS
============================================================

Create a centralized design-token system.

Required groups:

colors
spacing
typography
radius
elevation
motion
icons
control sizes
panel sizes
timeline sizes

Example:

color.background
color.surface
color.surface.subtle

color.text.primary
color.text.secondary
color.text.tertiary

color.brand
color.brand.soft

color.border
color.border.strong
color.border.focus

spacing.xs
spacing.sm
spacing.md
spacing.lg
spacing.xl

radius.sm
radius.md
radius.lg
radius.xl

motion.fast
motion.normal
motion.slow

Do not hardcode visual values inside individual screens unless they are truly local.

============================================================
5. TYPOGRAPHY
============================================================

Desktop typography must be highly readable.

Prefer the Windows-native visual language.

Primary UI font:

Segoe UI / Segoe UI Variable

Use a consistent Arabic fallback chain.

Typography hierarchy:

Display
Title
Subtitle
Body Large
Body
Body Small
Caption

Suggested sizes:

Display: 28–32
Title: 22–24
Subtitle: 17–19
Body Large: 15–16
Body: 14–15
Body Small: 13
Caption: 12

Do not create excessive font-size variants.

Typography must support RTL correctly.

============================================================
6. RTL ARCHITECTURE
============================================================

The application must be RTL-aware.

However:

IMPORTANT:

The UI direction and the Canvas coordinate system are NOT the same thing.

UI:
RTL

Canvas:
geometric coordinate system

Timeline:
time always progresses semantically from left to right unless there is a specific reason to expose an RTL visual representation.

Text objects:
support independent direction:

RTL
LTR

Do not reverse canvas coordinates simply because the UI is Arabic.

============================================================
7. SPACING SYSTEM
============================================================

Use an 8-point-based spacing system.

Suggested:

4
8
12
16
20
24
32
40
48

Avoid arbitrary values everywhere.

Whitespace is an active part of the visual language.

Do NOT fill empty space merely to make screens look "full".

============================================================
8. BORDER STRATEGY
============================================================

Do NOT place a visible border around every card.

Use hierarchy through:

- spacing
- surface contrast
- typography
- grouping
- subtle elevation

Use borders only when they communicate:

- containment
- input boundary
- selection
- focus
- timeline separation
- dialog boundary
- structural division

Avoid "boxed UI everywhere".

============================================================
9. RADIUS
============================================================

Use restrained desktop corner radii.

Suggested:

4px
6px
8px
10px
12px

Avoid extremely rounded UI.

Do not make every component pill-shaped.

Pills are reserved for:
- status badges
- compact tags
- filters
- compact states

============================================================
10. ELEVATION
============================================================

Use very subtle elevation.

Default:

flat / no shadow

Elevated:

very subtle shadow

Floating:

only for dialogs/popovers/context menus

Do not use heavy shadows.

The application should feel grounded and professional.

============================================================
11. MAIN APPLICATION COMPOSITION
============================================================

Primary layout:

┌────────────────────────────────────────────────────────────┐
│ TOP BAR                                                    │
├────────────┬───────────────────────────────────┬───────────┤
│ PROJECT /  │                                   │           │
│ SECTIONS   │                                   │ INSPECTOR │
│            │              CANVAS               │           │
│            │                                   │           │
│            │                                   │           │
├────────────┴───────────────────────────────────┴───────────┤
│ SHOT / CAMERA STRIP                                       │
├────────────────────────────────────────────────────────────┤
│ CONTEXTUAL TIMELINE                                       │
└────────────────────────────────────────────────────────────┘

CENTER CANVAS is the visual priority.

============================================================
12. RESPONSIVE PANEL BEHAVIOR
============================================================

Desktop is primary.

Support:

Wide
Medium
Compact

Wide:
left navigation visible
right inspector visible
large canvas

Medium:
reduce panel widths

Compact:
panels become collapsible

Never sacrifice Canvas first.

When horizontal space is limited:
collapse secondary UI before shrinking the Canvas excessively.

============================================================
13. TOP BAR
============================================================

Keep Top Bar extremely clean.

Primary elements:

Project Name
Save/Sync state
Preview
Render
More

Example:

Project: Warriors
Saved ✓

                           Preview   Render   ⋯

Do not place every action in the top bar.

============================================================
14. PROJECT NAVIGATION
============================================================

Left navigation is project-centric.

Display:

PROJECT

Sections

01 Introduction
02 Warrior
03 Battle
04 Ending

+ Add Section

Each section item should show:

- number
- title
- compact state
- optional duration

Avoid giant cards.

============================================================
15. SECTION STATUS DESIGN
============================================================

Use compact semantic statuses.

Examples:

✓ Ready
◉ Processing
⚠ Needs Review
✕ Failed
○ Draft

Use:

icon + text

Never rely only on color.

Examples:

✓ Ready
⚠ Needs Review
✕ Failed

============================================================
16. PROCESSING SCREEN UX
============================================================

Processing is NOT an editor screen.

Design it as an operational workspace.

Example:

Section 03

✓ Storyboard Validation
✓ Asset Extraction
◉ Voice Generation
○ Whisper
○ Visual Mapping
○ Choreography
○ Audio Mix
○ Preview
○ Render

Show only useful metadata:

Current task
Elapsed
Progress when measurable
Cache status
Issue status

Do not display internal engineering noise.

============================================================
17. PROCESSING MUST NOT LOCK THE UI
============================================================

While processing:

- user can switch sections
- user can inspect other projects where safe
- user can open logs
- user can continue non-conflicting work

Show system state unobtrusively.

Do NOT use a full-screen blocking overlay for normal background processing.

Only block the exact action that depends on the running task.

============================================================
18. ERROR UX
============================================================

Do not use modal error dialogs for every error.

Use:

Needs Attention

Example:

⚠ 2 items need attention

Section 03
Asset 07 may contain merged drawings
[Review]

Section 05
Voice verification failed
[Fix]

The user should be taken directly to the source of the problem.

Errors are actionable.

Never display:

"Something went wrong."

without:
- what
- where
- consequence
- next action

============================================================
19. ERROR SEVERITY VISUAL LANGUAGE
============================================================

INFO:
neutral/blue

WARNING:
amber

ERROR:
red

SUCCESS:
green

Do not turn the entire UI red/green.

Use local emphasis only.

============================================================
20. EMPTY STATES
============================================================

Empty states must be helpful.

Example:

No Sections Yet

Add your first storyboard and script
to begin production.

[+ Add Section]

No generic illustrations unless there is a clear usability benefit.

============================================================
21. CANVAS-FIRST UX
============================================================

When inside Studio:

Canvas gets the largest amount of space.

Do not sacrifice Canvas for oversized sidebars.

The Canvas should visually read as the "work surface".

Canvas background:
#FFFFFF

Application background:
#F5F6F8

This creates immediate separation.

============================================================
22. CANVAS TOOLBAR
============================================================

Keep Canvas controls minimal.

Show:

Fit
Zoom
100%
Snap
Grid
Safe Area

Advanced controls can be inside a menu.

Do not clutter the Canvas with permanent toolbars.

============================================================
23. ASSET SELECTION
============================================================

Selected Asset must have a precise but restrained visual indicator.

Use:
- thin accent outline
- subtle handles
- optional bounding area

Avoid thick black boxes.

Avoid decorative glow.

Selection must be immediately obvious.

============================================================
24. INSPECTOR DESIGN
============================================================

Inspector is contextual.

If nothing is selected:
show helpful empty state.

If Asset selected:
show Asset controls.

If Camera selected:
show Camera controls.

If Text selected:
show Typography controls.

Use collapsible groups:

Asset

Appearance

Animation

Timing

Semantic

Advanced

Do not expose all advanced controls by default.

============================================================
25. PROGRESSIVE DISCLOSURE
============================================================

Default controls:
common operations

Advanced:
rare operations

Examples:

Normal:
Position
Scale
Animation
Timing

Advanced:
rotation
opacity
custom easing
manual offsets
low-level rendering parameters

Never make normal users navigate through engineering terminology.

============================================================
26. CAMERA / SHOT UX
============================================================

Represent Shots as compact cards in the bottom strip.

Example:

Camera 01
00:00–00:06
3 assets

Camera 02
00:06–00:14
4 assets

Camera 03
00:14–00:21
2 assets

Selected Shot:
clear accent state

Do not create large visual cards.

============================================================
27. CAMERA INSPECTOR
============================================================

When Shot is selected:

SHOT 03

Speech
00:12.4–00:18.2

Assets
3

Camera
Position
Zoom
Motion

Composition
Visible Elements

Advanced

Keep the primary workflow understandable.

============================================================
28. CONTEXTUAL TIMELINE
============================================================

Do NOT build a full nonlinear editing timeline.

The Timeline exists only to clarify the selected Shot.

Show:

VOICE

Asset 01
Asset 02
Asset 03

Camera

Keep it compact.

Do not introduce:
- dozens of tracks
- nested sequences
- complex keyframe editors
- Premiere-style track management

unless future requirements explicitly demand them.

============================================================
29. TIMELINE INTERACTION
============================================================

Timeline must visually communicate:

- speech timing
- asset reveal
- draw duration
- hold
- camera movement

Use direct manipulation.

Dragging an asset's timing should be intuitive.

Do not force users to type timestamps for normal operations.

============================================================
30. PREVIEW UX
============================================================

Preview must feel like a first-class workspace.

Support:

Preview Camera
Preview Section
Preview Selected Sections
Preview Full Project

The user can:

Play
Pause
Seek
Jump to Shot
Jump to Section

Do not open a tiny temporary preview window for the main workflow.

============================================================
31. PREVIEW MODE SWITCHING
============================================================

Use a simple selector:

Camera
Section
Selection
Project

The user should immediately understand the preview scope.

============================================================
32. LIVE EDITING + PREVIEW
============================================================

When the user changes:

- position
- scale
- text
- animation
- camera

the Canvas preview must update immediately where possible.

Do not force a full production render for interactive edits.

============================================================
33. PREVIEW PERFORMANCE UX
============================================================

Show preview quality when necessary:

Draft
Standard
Production

Draft should prioritize responsiveness.

Production should prioritize fidelity.

The UI must make the difference understandable.

============================================================
34. TEXT EDITOR UX
============================================================

Text tool must feel natural.

When Text is selected:

Content
Direction
Font
Size
Weight
Alignment
Color
Position
Animation

Support direct manipulation:

drag
resize
move

The user should not need to understand coordinates.

============================================================
35. ADD SECTION UX
============================================================

The + Add Section action should always be easy to find.

Preferred:

+ Add Section

Dialog:

Section Name
Storyboard
Script

Then:

Storyboard ✓
Script ✓

[Create Section]

After creation:

[Start Processing]

Keep creation separate from processing.

============================================================
36. CREATIVE VS OPERATIONAL UX
============================================================

The product has two interaction modes.

CREATIVE MODE:
- Canvas
- Shot editing
- Asset editing
- Text
- Timing
- Camera
- Preview

OPERATIONAL MODE:
- processing
- errors
- retries
- render
- master assembly
- system resources

Do not visually mix them excessively.

============================================================
37. RESOURCE STATUS UX
============================================================

Resource usage must be visible only when useful.

Do not permanently show:

CPU
RAM
GPU
Threads

to normal users.

Instead:

main UI:
simple status

Advanced Diagnostics:
full resource information

Example:

Ready

Advanced:
CPU 34%
Memory 4.2 GB
GPU 18%

============================================================
38. PERFORMANCE SETTINGS UX
============================================================

Provide:

Performance Mode

Auto
Efficiency
Balanced
Performance

Auto is default.

Advanced settings should be behind:

Advanced Performance

Do not expose dangerous concurrency controls to normal users.

============================================================
39. AUTOSAVE INDICATOR
============================================================

Show a tiny state indicator:

Saving…
Saved ✓

Do not use large notifications for routine autosaving.

If unsaved changes exist:

Unsaved changes

If the user loses connection or another external issue occurs:
show clear actionable status.

============================================================
40. UNDO / REDO
============================================================

Primary shortcuts:

Ctrl/Cmd + Z
Ctrl/Cmd + Shift + Z

Also provide visible controls in the Editor.

Tooltips must show keyboard shortcut.

============================================================
41. KEYBOARD UX
============================================================

Support keyboard-first actions where practical:

Space:
Play/Pause

Delete:
Delete selected

Ctrl/Cmd + Z:
Undo

Ctrl/Cmd + Shift + Z:
Redo

Ctrl/Cmd + S:
Save

Arrow keys:
small movement

Shift + Arrow:
larger movement

Do not create conflicting shortcuts.

============================================================
42. MOUSE INTERACTION
============================================================

Canvas:

single click:
select

drag:
move

resize handles:
resize

double click:
context-specific editing

right click:
context menu where useful

Mouse interactions should feel standard and predictable.

============================================================
43. CONTEXT MENUS
============================================================

Use context menus for secondary actions.

Example:

Asset:

Edit
Duplicate
Merge
Split
Replace
Delete

Do not crowd the main inspector with every action.

============================================================
44. DRAG AND DROP
============================================================

Support where useful:

Storyboard → Section
Asset → Shot
Text → Canvas
Section → reorder
Asset → shot

Feedback must show what will happen before drop.

============================================================
45. DRAG SAFETY
============================================================

Never allow drag interactions to accidentally:

- delete
- overwrite
- merge
- reorder source truth

Destructive operations require confirmation or an undo path.

============================================================
46. DESTRUCTIVE ACTIONS
============================================================

Delete:
use Undo

Permanent deletion:
confirmation

Reject Asset:
should mean exclude from production, not destroy source

Replacing Storyboard:
must explain downstream invalidation when relevant

============================================================
47. NOTIFICATION SYSTEM
============================================================

Use three levels:

Inline:
for local state

Toast:
for lightweight completed actions

Modal:
only for decisions that genuinely block or require confirmation

Never use modal dialogs for routine success messages.

============================================================
48. COMMAND FEEDBACK
============================================================

Every user action should produce immediate feedback.

Example:

Move Asset
→ immediate visual movement

Save
→ Saved ✓

Preview
→ Preview starting…

Render
→ Render started

Retry
→ Retry queued

Avoid delayed silent actions.

============================================================
49. LOADING STATES
============================================================

Use skeletons or placeholders for UI content loading.

Use progress for measurable operations.

Use indeterminate indicators only when progress genuinely cannot be measured.

Never fake a progress percentage.

============================================================
50. ACCESSIBILITY
============================================================

Design for:

- strong contrast
- keyboard navigation
- visible focus
- readable font sizes
- clear states
- non-color-only status communication

Every important state should have:

icon + text + color where appropriate.

============================================================
51. DENSITY
============================================================

Support:

Comfortable
Compact

Default:
Comfortable

Compact:
for advanced users with many Sections/assets.

Do not shrink typography excessively in Compact mode.

Reduce spacing first.

============================================================
52. WINDOW BEHAVIOR
============================================================

Support standard desktop behavior:

- resizable window
- maximize
- restore
- minimum safe dimensions

Panels:
resizable
collapsible
persistent where appropriate

Remember user panel preferences.

============================================================
53. PERSISTENT LAYOUT PREFERENCES
============================================================

Remember:

- window size
- panel widths
- collapsed/expanded state
- last project
- last selected Section
- last selected Shot

Do NOT remember transient selections that could cause confusion after a crash unless safe.

============================================================
54. STUDIO NAVIGATION
============================================================

The user should always understand:

Where am I?

Project:
Warriors

Section:
03 — Khalid

Shot:
02

Asset:
Phone

Use compact breadcrumbs where helpful.

Example:

Warriors / Section 03 / Camera 02 / Phone

============================================================
55. NO USER DEAD ENDS
============================================================

Every important screen must answer:

1. What am I looking at?
2. What is the current state?
3. What can I do next?

Example:

Extraction Review

12 Assets
2 Need Review

[Review Asset 07]

============================================================
56. REVIEW-FIRST ERROR DESIGN
============================================================

When a stage requires review:

do NOT send user back to a generic dashboard.

Deep-link them directly:

Processing
→ Needs Review
→ Asset 07
→ Extraction Editor

Same for:

TTS
→ Failed Chunk

Render
→ Failed Camera

Semantic
→ Unresolved Asset

============================================================
57. MASTER WORKSPACE
============================================================

Master workspace should prioritize:

Section order
Section status
Preview
Assembly

Avoid turning Master screen into a giant timeline.

Example:

01 Intro ✓
02 Warrior ✓
03 Battle ⚠
04 Ending ✓

[Preview Full Project]

[Assemble Master]

============================================================
58. VISUAL HIERARCHY
============================================================

Priority:

1. Canvas / active content
2. current task
3. primary action
4. selected object
5. status
6. secondary properties
7. advanced controls

Do not allow secondary controls to visually dominate the content.

============================================================
59. COLOR DISCIPLINE
============================================================

Brand color should not dominate the entire application.

Use brand color for:

- primary action
- selection
- focus where appropriate
- active navigation
- important visual anchors

Do not color every component.

============================================================
60. MOTION DESIGN
============================================================

UI motion must be subtle.

Suggested:

hover:
100–150ms

press:
80–120ms

panel:
180–220ms

dialog:
180–240ms

Avoid:
- excessive bounce
- giant scale animations
- neon glow
- blur transitions everywhere
- decorative animations

The video itself is animated.
The UI must remain calm.

============================================================
61. REDUCED MOTION
============================================================

Respect operating-system reduced-motion preferences when possible.

Reduce decorative UI animation.

Never sacrifice functional feedback.

============================================================
62. COMPONENT LIBRARY
============================================================

Build reusable QML components before creating the entire application.

Required:

StudioButton
StudioIconButton
StudioTextField
StudioTextArea
StudioComboBox
StudioSlider
StudioToggle
StudioBadge
StudioChip
StudioCard
StudioPanel
StudioDialog
StudioToast
StudioTooltip
StudioProgress
StudioStatus
StudioListItem
StudioSectionCard
StudioShotCard
StudioAssetCard
StudioInspectorSection
StudioTimeline
StudioCanvas

Every component must support consistent:

normal
hover
pressed
focused
disabled
selected
error
loading

states where applicable.

============================================================
63. COMPONENT ARCHITECTURE
============================================================

Do not copy/paste UI styling into screens.

Screens compose components.

Components consume design tokens.

Tokens define visual language.

This creates:

Tokens
→ Components
→ Patterns
→ Screens

Do not reverse this dependency.

============================================================
64. SCREEN SYSTEM
============================================================

Design these screens:

1. Startup
2. Project Browser
3. New Project
4. Project Overview
5. Add Section
6. Preflight
7. Processing
8. Extraction Review
9. Voice Review
10. Semantic Review
11. Studio
12. Shot Editor
13. Preview
14. Render Monitor
15. Render QA
16. Master Studio
17. Settings
18. Diagnostics

Each screen must have:

Purpose
Primary action
Secondary actions
Empty state
Loading state
Error state
Success state
Navigation path

============================================================
65. DESIGN DOCUMENTATION
============================================================

Create:

docs/studio/uiux/
    design_system.md
    design_tokens.md
    typography.md
    colors.md
    spacing.md
    components.md
    navigation.md
    editor_ux.md
    preview_ux.md
    error_ux.md
    accessibility.md
    motion.md
    responsive.md

Also create:

docs/studio/uiux/screen_specs/

with one specification file per major screen.

============================================================
66. SCREEN SPEC FORMAT
============================================================

Every screen specification must describe:

- Purpose
- User goal
- Layout
- hierarchy
- components
- states
- interactions
- keyboard behavior
- mouse behavior
- loading
- errors
- empty state
- responsive behavior
- RTL behavior
- accessibility
- performance considerations

============================================================
67. UX CONSISTENCY CHECK
============================================================

Before considering a screen complete, verify:

Does it use shared tokens?
Does it use shared components?
Is the primary action obvious?
Can the user understand the current state?
Is there unnecessary visual noise?
Is information grouped spatially?
Are advanced controls hidden appropriately?
Does the screen work in RTL?
Can keyboard users navigate it?
Does it remain usable at smaller window sizes?
Does it avoid blocking the UI?
Does it preserve the Canvas as the primary focus where applicable?

============================================================
68. UX PERFORMANCE REQUIREMENTS
============================================================

UI must remain responsive during:

- TTS
- Whisper
- extraction
- semantic processing
- preview generation
- rendering
- master assembly

Do not create heavy bindings or constantly recomputing QML models.

Avoid unnecessary image decoding.

Use thumbnails.

Use lazy loading.

Avoid full-resolution images when thumbnails are sufficient.

============================================================
69. CANVAS PERFORMANCE
============================================================

The Canvas must not reload all assets whenever one object changes.

Use model-level updates.

Example:

Move Asset 07

Only Asset 07 visual state changes.

Do not:
rebuild entire Section UI
reload all images
regenerate all preview data

============================================================
70. PREVIEW PERFORMANCE
============================================================

Interactive preview must be separate from production rendering.

Never invoke a full FFmpeg render for every:

- drag
- resize
- text change
- camera movement

Use lightweight interactive composition.

Only generate proxy/production preview when needed.

============================================================
71. VISUAL QA FOR THE UI
============================================================

Before declaring the UI complete:

Test:

- 1280x720
- 1366x768
- 1920x1080
- 2560x1440
- 4K if practical

Test:
- RTL
- long Arabic project names
- long section names
- many sections
- many assets
- long scripts
- long error messages
- no internet
- processing in background
- render failure
- worker crash
- reopened project

============================================================
72. DO NOT OVERDESIGN
============================================================

When uncertain between:

more UI
or
less UI

prefer less UI.

When uncertain between:

another panel
or
contextual inspector

prefer contextual inspector.

When uncertain between:

modal dialog
or
inline action

prefer inline action.

When uncertain between:

manual configuration
or
smart defaults

prefer smart defaults with an Advanced override.

============================================================
73. CRITICAL PRODUCT RULE
============================================================

The interface must hide complexity without hiding control.

The user should be able to accomplish common tasks without understanding:

DAG
ArtifactStore
Whisper
TTS chunks
resource pools
hashes
invalidation
worker processes
render internals

But advanced users must still have a path to:

inspect
edit
diagnose
override
retry
rebuild
review

============================================================
74. FINAL VISUAL STANDARD
============================================================

The final UI should communicate:

"Professional creative production software"

within the first few seconds.

Visual keywords:

Light
Clean
Precise
Calm
Focused
Spacious
Premium
Desktop-native
Modern 2026
Consistent
Fast

Avoid:

Dark
Neon
Glass-heavy
Game-like
Dashboard-heavy
Over-rounded
Overshadowed Canvas
Excessive borders
Excessive cards
Excessive animations
Visual clutter

============================================================
75. IMPLEMENTATION ORDER FOR UI/UX
============================================================

Do NOT start by building all screens.

Build in this order:

1. Design Tokens
2. Typography
3. Icon system
4. Base layout primitives
5. Button/Input primitives
6. Status components
7. Cards
8. Panels
9. Inspector primitives
10. Navigation primitives
11. Canvas primitives
12. Timeline primitives
13. Preview controls
14. Project Browser
15. Project Overview
16. Add Section
17. Processing
18. Extraction Review
19. Voice Review
20. Semantic Review
21. Studio Editor
22. Preview Workspace
23. Render Monitor
24. Master Workspace
25. Settings
26. Diagnostics

Do not bypass the component system.

============================================================
76. REQUIRED UI/UX DESIGN REVIEW BEFORE CODING
============================================================

Before implementing QML screens, produce:

A. Complete Design System
B. Color token map
C. Typography map
D. Spacing scale
E. Component inventory
F. Main shell layout
G. Project Browser design
H. Section workflow screens
I. Processing screen
J. Extraction Review
K. Voice Review
L. Semantic Review
M. Studio Editor
N. Camera/Shot Editor
O. Preview Workspace
P. Master Workspace
Q. Error/Recovery UX
R. Responsive behavior
S. RTL behavior
T. Accessibility
U. Performance strategy

Then implement the component foundation first.

============================================================
77. DESIGN QUALITY GATE
============================================================

Do NOT declare the UI finished because:

- all buttons work
- all screens exist
- QML compiles

The UI is complete only when:

- visual hierarchy is consistent
- spacing is consistent
- interactions are predictable
- Canvas is dominant
- controls are contextual
- errors are actionable
- RTL works
- keyboard navigation works
- performance remains responsive
- UI does not consume unnecessary resources
- no screen feels like a different product
- all screens use the same Design System

============================================================
78. FINAL DESIGN PRINCIPLE
============================================================

Build a UI that is:

Simple at first glance.
Powerful when needed.
Fast during interaction.
Quiet when working.
Clear when something fails.
Precise when editing.
Visual when previewing.
Professional when delivering.

The user should feel like a director/editor,
not like an engineer operating a pipeline.

Do not confuse visual simplicity with architectural simplicity.

The implementation underneath may be sophisticated.

The user's experience must remain simple.
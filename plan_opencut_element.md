نعم. وبعد تتبع المستودع، الصورة أصبحت أوضح بكثير، وخصوصًا بالنسبة لهدفك أنت: **استخراج نظام الخطوط + الـEffects + الـMasks + الـKeyframes + الـGPU rendering واستخدامها داخل محرك الـMotion Graphics الخاص بك**.

أول تصحيح مهم: الرابط الذي أرسلته `OpenCut-app/OpenCut` هو **إعادة كتابة جديدة**. أما الكود الذي يحتوي على المحرر المكتمل نسبيًا فهو `OpenCut-app/opencut-classic`، وقد تم أرشفته في 17 مايو 2026. الـREADME الرسمي نفسه يقول إن Classic هو النسخة التي ينبغي استخدامها حاليًا. [GitHub](https://github.com/OpenCut-app/OpenCut/blob/main/README.md?utm_source=chatgpt.com)



# 1. الخريطة الكاملة للمشروع

الجزء الذي يهمنا في Classic يمكن اختصاره هكذا:

```text
opencut-classic/
│
├── apps/
│   │
│   ├── web/
│   │   ├── src/
│   │   │   ├── timeline/
│   │   │   ├── preview/
│   │   │   ├── masks/
│   │   │   ├── effects/
│   │   │   ├── actions/
│   │   │   ├── commands/
│   │   │   ├── services/
│   │   │   └── ...
│   │   │
│   │   └── scripts/
│   │       └── generate-font-sprites.ts
│   │
│   └── desktop/
│
├── rust/
│   │
│   ├── crates/
│   │   ├── bridge/
│   │   ├── compositor/
│   │   ├── effects/
│   │   ├── gpu/
│   │   ├── masks/
│   │   └── time/
│   │
│   └── wasm/
│
├── docs/
│
└── package.json
```

وهذه ليست مجرد تقسيمة شكلية؛ الـRust workspace يحتوي فعليًا على:

```text
bridge
compositor
effects
gpu
masks
time
wasm
```

وهذا مثبت في `Cargo.toml`. [GitHub](https://github.com/OpenCut-app/opencut-classic/blob/main/Cargo.toml?utm_source=chatgpt.com)

---

# 2. أهم شيء بالنسبة لك: نظام الـEffects

المسار الأساسي:

```text
rust/crates/effects/
```

وأهم ملف وصلنا إليه:

```text
rust/crates/effects/src/pipeline.rs
```

وهذا الملف مهم جدًا.

فيه:

```rust
pub struct EffectPipeline
```

و:

```rust
pub struct ApplyEffectsOptions
```

والـpipeline يستقبل:

```text
source texture
      ↓
EffectPass[]
      ↓
EffectPass
      ↓
Shader
      ↓
Output Texture
```

أي أن OpenCut لا يتعامل مع Effect كـ"Animation جاهزة"، بل كـ **GPU shader pass**. [GitHub](https://raw.githubusercontent.com/OpenCut-app/opencut-classic/main/rust/crates/effects/src/pipeline.rs)

---

# 3. الـEffect الموجود فعليًا

في النسخة التي قمنا بتتبعها، أهم Effect فعلي هو:

```text
Gaussian Blur
```

ويوجد له:

```text
rust/crates/effects/src/shaders/gaussian_blur.wgsl
```

والـpipeline يعرف:

```text
GAUSSIAN_BLUR_SHADER_ID
GAUSSIAN_BLUR_SHADER_SOURCE
```

ويحوّل الـshader إلى:

```text
wgpu::RenderPipeline
``` :chatgpt-content-reference{index="4"}


والـshader نفسه يعمل Gaussian blur على الـGPU.

الفكرة تقريبًا:

```text
Input Texture
      ↓
Blur Pass X
      ↓
Blur Pass Y
      ↓
Output
```

والـshader يستخدم:

```text
sigma
step
direction
resolution
```

ويأخذ samples عبر نافذة تصل إلى ±30 sample. [GitHub](https://raw.githubusercontent.com/OpenCut-app/opencut-classic/main/rust/crates/effects/src/shaders/gaussian_blur.wgsl)

---

# 4. لماذا هذا مهم جدًا لمشروعك؟

لأننا نستطيع بناء:

```text
Motion Graphics Effect Engine
```

بنفس الفكرة:

```text
Asset
  ↓
Texture
  ↓
Effect Pipeline
  ├── Blur
  ├── Glow
  ├── Shadow
  ├── Brightness
  ├── Contrast
  ├── Saturation
  ├── Chromatic Aberration
  ├── Noise
  ├── Grain
  ├── Vignette
  └── ...
```

كل واحد يصبح:

```text
WGSL Shader
+
Uniform Parameters
+
Animation
```

وهنا OpenCut يعطيك **البنية الصحيحة** أكثر من كونه يعطيك عددًا كبيرًا من المؤثرات.

---

# 5. Effect Pipeline عند OpenCut

لاحظ هذه النقطة في `pipeline.rs`.

كل Effect عبارة عن:

```text
EffectPass
```

والـpipeline يستطيع تنفيذ عدة passes:

```text
Input
  ↓
Pass 1
  ↓
Texture
  ↓
Pass 2
  ↓
Texture
  ↓
Pass 3
  ↓
Output
```

أي يمكننا بناء Effect مركب:

```text
Glow

Original
   ↓
Blur
   ↓
Color Boost
   ↓
Screen Blend
   ↓
Original
```

وهذا بالضبط ما نحتاجه للـMotion Graphics.

---

# 6. الـMasks

وهنا OpenCut أقوى مما يبدو.

المسارات المهمة:

```text
apps/web/src/masks/
```

وتحديدًا:

```text
apps/web/src/masks/
│
├── index.ts
├── registry.ts
├── types.ts
├── snap.ts
├── use-mask-handles.ts
│
├── builtin/
│   ├── box-like.ts
│   └── definitions/
│       ├── cinematic-bars.ts
│       ├── diamond.ts
│       └── index.ts
│
└── freeform/
    ├── definition.ts
    └── path.ts
```

وهذه الملفات موثقة في تحليل بنية Classic. [DeepWiki](https://deepwiki.com/opencut-app/opencut-classic/4.4-masks-system?utm_source=chatgpt.com)

---

# 7. الـMasks التي يوفرها

لدينا:

```text
Rectangle
Ellipse
Heart
Diamond
Star
Split
Cinematic Bars
Text
Freeform
```

والـFreeform يعتمد على:

```text
Bezier curves
Anchor points
In/Out handles
```

أي أنك تستطيع رسم Mask مثل Pen Tool. [DeepWiki](https://deepwiki.com/opencut-app/opencut-classic/4.4-masks-system?utm_source=chatgpt.com)

---

# 8. لكن الجزء الأقوى هو Feather

OpenCut لا يعمل:

```text
alpha = 0/1
```

فقط.

بل يستخدم:

```text
Signed Distance Field
```

ثم:

```text
Jump Flood Algorithm
```

على الـGPU.

المسارات:

```text
rust/crates/masks/src/feather.rs
rust/crates/masks/src/sdf.rs
```

والـShaders:

```text
rust/crates/masks/src/shaders/jfa_init.wgsl
rust/crates/masks/src/shaders/jfa_step.wgsl
``` :chatgpt-content-reference{index="8"}


---

# 9. ماذا يفعل JFA؟

بشكل مبسط:

```text
Mask Boundary
      ↓
Seed Pixels
      ↓
JFA
      ↓
Distance Field
      ↓
Feather
      ↓
Smooth Alpha
```

بدل أن يكون لديك:

```text
████████
████████
```

يصبح:

```text
██████▓▒░
██████▓▒░
██████▓▒░
```

وهذا يعطي Edge ناعم جدًا.

والكود فعليًا يحسب الـSDF من خلال مرحلتي inside/outside، ثم يستخدم الـfeather لإنتاج النتيجة النهائية. [GitHub](https://raw.githubusercontent.com/OpenCut-app/opencut-classic/main/rust/crates/masks/src/feather.rs)

---

# 10. هذا مفيد جدًا لمشروعك

تخيل Asset:

```text
Apple.png
```

نريد:

### دخول

```text
0.0s
Mask = 0%
Scale = 0.7
Opacity = 0

0.5s
Mask = 100%
Scale = 1
Opacity = 1
```

ثم:

```text
Glow
+
Shadow
+
Motion Blur
```

يمكن تنفيذ كل هذا على GPU.

---

# 11. الـCompositor

المسار:

```text
rust/crates/compositor/
```

والـentry point:

```text
rust/crates/compositor/src/lib.rs
```

ويكشف:

```rust
Compositor
CompositorError
RenderFrameOptions
FrameDescriptor
FrameItemDescriptor
LayerDescriptor
LayerMaskDescriptor
QuadTransformDescriptor
EffectPassDescriptor
CanvasClearDescriptor
CanvasTextureDescriptor
``` :chatgpt-content-reference{index="10"}


وهذا تقريبًا هو **قلب الـMotion Renderer**.

---

# 12. ماذا يعني FrameDescriptor؟

الفكرة المعمارية:

```text
Frame
 │
 ├── Layer 1
 │     ├── Texture
 │     ├── Transform
 │     ├── Opacity
 │     ├── Blend
 │     ├── Mask
 │     └── Effects
 │
 ├── Layer 2
 │
 ├── Layer 3
 │
 └── Layer N
```

ثم:

```text
FrameDescriptor
      ↓
Compositor
      ↓
GPU
      ↓
Final Frame
```

وهذا **مناسب جدًا** لفكرة الـAsset Sheets التي تعمل عليها.

---

# 13. الـBlend Modes

OpenCut يدعم:

```text
GlobalCompositeOperation
```

ويدخل ضمن الـCompositor.

والإصدار 0.1 أضاف دعمًا للـblend modes للعناصر المرئية. [GitHub](https://github.com/OpenCut-app/OpenCut/releases?utm_source=chatgpt.com)

وهذا يعني أنك تستطيع بناء:

```text
Normal
Multiply
Screen
Overlay
...
```

وبالتالي:

```text
Glow
```

يمكن مثلًا أن يكون:

```text
Blurred White/Colored Layer
        ↓
Screen
        ↓
Original
```

بدون أن نحتاج فيديو جاهز.

---

# 14. الـGPU Layer

المسار:

```text
rust/crates/gpu/
```

والـWASM bridge يستخدم:

```text
GpuContext
```

مع:

```text
wgpu
```

ويدعم WebGPU مع fallback إلى WebGL في بيئة الويب. [DeepWiki](https://deepwiki.com/opencut-app/opencut-classic/7.2-wasm-package-and-desktop-app?utm_source=chatgpt.com)

---

# 15. WASM

هذه نقطة شديدة الأهمية.

المشروع لا يجعل React يتعامل مباشرة مع GPU.

لدينا:

```text
React / TypeScript
        ↓
rust/wasm
        ↓
Rust
        ↓
wgpu
        ↓
GPU
```

الملف:

```text
rust/wasm/src/compositor.rs
```

يحتوي على وظائف مثل:

```text
initCompositor
renderFrame
uploadTexture
``` :chatgpt-content-reference{index="13"}


---

# 16. الـrenderFrame

هذه أهم نقطة في النظام كله تقريبًا.

الـJS يرسل:

```text
FrameDescriptor
```

إلى WASM.

ثم Rust يقوم:

```text
deserialize
      ↓
configure surface
      ↓
Compositor::render_frame()
      ↓
GPU
``` :chatgpt-content-reference{index="14"}


---

# 17. Fonts — وهنا يوجد شيء مهم جدًا

المسار:

```text
apps/web/scripts/generate-font-sprites.ts
```

هذا الملف لا يحتوي على الخطوط نفسها.

بل يقوم بإنشائها.

العملية:

```text
Fontsource API
      ↓
Google Fonts
      ↓
Download WOFF2
      ↓
@napi-rs/canvas
      ↓
Render Font Name
      ↓
Pack
      ↓
AVIF
      ↓
font-chunk-N.avif
```

ويتم إنشاء:

```text
font-atlas.json
``` :chatgpt-content-reference{index="15"}


---

# 18. شكل الـFont Atlas

كل Font يحصل على:

```json
{
  "family": "...",
  "x": 100,
  "y": 40,
  "w": 200,
  "ch": 2,
  "s": ["400", "700", "400i"]
}
```

الفكرة:

```text
font-atlas.json
       │
       ├── Font A → x/y/w/ch
       ├── Font B → x/y/w/ch
       ├── Font C → x/y/w/ch
       └── ...
```

ثم:

```text
font-chunk-0.avif
font-chunk-1.avif
font-chunk-2.avif
...
```

بدل تحميل 1000 صورة منفصلة.

---

# 19. كم Font؟

النظام يستخرج Google Fonts التي:

```text
type = google
subset = latin
weight = 400
```

ثم ينزّلها من Fontsource. [GitHub](https://raw.githubusercontent.com/OpenCut-app/opencut-classic/main/apps/web/scripts/generate-font-sprites.ts)

وفي الـUI يتم عرض أكثر من **1000 خط**، مع دعم System Fonts أيضًا. [GitHub](https://github.com/OpenCut-app/OpenCut/releases?utm_source=chatgpt.com)

---

# 20. لكن انتبه جدًا

الـFont Atlas **ليس هو ملفات الخطوط التي تريدها لاستخدامها في الفيديو**.

Atlas:

```text
font-chunk.avif
```

هو فقط:

> صورة تحتوي أسماء الخطوط مرسومة.

أي:

```text
Font Picker Preview
```

وليس:

```text
Actual Font Rendering
```

وهذه نقطة مهمة جدًا.

---

# 21. إذا أردنا أخذ Fonts لمشروعنا

لا أنصحك باستخراج:

```text
font-chunk-*.avif
```

ثم استخدامها.

الأفضل:

```text
Fontsource
     ↓
Download WOFF2
     ↓
Convert/keep WOFF2
     ↓
Font Registry
```

وبالنسبة للعربية، نحتاج تحديدًا:

```text
Arabic subset
```

وليس Latin فقط.

وهنا يمكننا إنشاء مكتبة مثل:

```text
fonts/
├── Cairo/
├── Tajawal/
├── IBM-Plex-Sans-Arabic/
├── Noto-Kufi-Arabic/
├── Noto-Sans-Arabic/
├── Almarai/
└── ...
```

ثم محركنا يتعامل معها.

---

# 22. الـKeyframes

في OpenCut تمت إضافة نظام Keyframe في الإصدار 0.2.0. [GitHub](https://github.com/OpenCut-app/OpenCut/blob/main/changelog/0.2.0.md?utm_source=chatgpt.com)

ثم في 0.3.0 تمت إضافة:

```text
Graph Editor
Bezier Handles
Position X
Position Y
Copy/Paste Keyframes
Property Lanes
``` :chatgpt-content-reference{index="19"}


أي أن الـtimeline يستطيع أن يظهر:

```text
Asset
 ├── Position X
 ├── Position Y
 ├── Scale
 ├── Rotation
 └── Opacity
```

كل Property له lane.

---

# 23. وهذا بالضبط ما نحتاجه

بدل:

```python
element.x = ...
```

نريد:

```text
Property
   ↓
Animation Curve
   ↓
Keyframes
   ↓
Evaluator
   ↓
Value at time t
```

مثل:

```text
Position X

0s      -500
1s         0
2s        100
4s          0
```

---

# 24. الـGraph Editor

OpenCut أضاف Bezier handles.

أي:

```text
Keyframe A
      ╲
       ╲____
            ╲
             Keyframe B
```

بدل الحركة الخطية:

```text
A ───────── B
```

يمكنك الحصول على:

```text
A ___
     ╲
      ╲____ B
```

وهذا مهم جدًا في Motion Graphics.

---

# 25. أهم ملاحظة: OpenCut ليس Motion Graphics Engine كامل

هذه نقطة أريد أن تكون واضحة جدًا.

OpenCut Classic قوي في:

```text
Timeline
+
Transforms
+
Keyframes
+
Masks
+
Blur
+
Compositing
```

لكن ليس لديه مكتبة ضخمة من:

```text
Text Presets
Character Animations
Shape Animations
Particles
Advanced Transitions
Lottie
3D
Camera Rig
Spring Physics
```

والـEffect system نفسه بدأ بـBlur. [GitHub](https://github.com/OpenCut-app/OpenCut/blob/main/changelog/0.2.0.md?utm_source=chatgpt.com)

لذلك لا نريد نسخ OpenCut باعتباره "مكتبة تأثيرات جاهزة".

نريد نسخ **Architecture**.

---

# 26. ماذا يحتوي OpenCut فعليًا من ناحية Motion؟

يمكن تصورها هكذا:

```text
                 OpenCut Motion
                       │
       ┌───────────────┼───────────────┐
       ↓               ↓               ↓
   Transform       Keyframes        Effects
       │               │               │
   Position        Bezier           Blur
   Scale           Graph
   Rotation        Easing
   Opacity
       │
       └───────────────┐
                       ↓
                    Masks
                       │
              Rectangle / Ellipse
              Star / Heart
              Diamond / Split
              Cinematic Bars
              Freeform
                       │
                       ↓
                  Compositor
                       │
                       ↓
                    wgpu
                       │
                       ↓
                     GPU
```

وهذه البنية هي التي أرى أنها تستحق النقل إلى مشروعك.

---

# 27. الـStickers

في 0.3.0 تمت إضافة Sticker panel يحتوي على:

```text
Logos
Flags
Shapes
```

والـrepository يحتوي أيضًا على assets مثل flags. [GitHub](https://github.com/OpenCut-app/OpenCut/releases?utm_source=chatgpt.com)

والمهم هنا أن الـSticker system أصبح Provider-based.

أي يمكن أن يصبح:

```text
StickerProvider
      │
      ├── Flags
      ├── Logos
      ├── Shapes
      ├── Icons
      └── Custom Assets
```

وهذا مناسب جدًا لمحركك.

---

# 28. Shapes

يمكننا الاستفادة من فكرة الـShapes كـvector primitives:

```text
Circle
Rectangle
Star
Heart
Diamond
```

لكن بالنسبة لمشروعك، سأوسعها إلى:

```text
Circle
RoundedRect
Line
Arrow
Triangle
Star
Polygon
Blob
SpeechBubble
Underline
Bracket
```

ثم نضيف:

```text
Stroke
Fill
Gradient
Shadow
Glow
```

---

# 29. Canvas Background

OpenCut يدعم:

```text
Solid
Gradient
Blurred background
``` :chatgpt-content-reference{index="22"}


وهذا يمكن أخذه مباشرة كمفهوم:

```text
Canvas
 ├── background color
 ├── gradient
 └── background blur
```

---

# 30. Time Engine

هذا أيضًا شيء أنصحك بأخذه من OpenCut من ناحية التصميم.

بدل:

```python
time = 1.333333
```

يستخدم النظام:

```text
MediaTime
```

مع integer ticks.

تم اختيار:

```text
120,000 ticks / second
```

والسبب أنه يتعامل بدقة مع:

```text
23.976
29.97
30
```

وغيرها. [GitHub](https://github.com/OpenCut-app/OpenCut/releases?utm_source=chatgpt.com)

---

# 31. هذا مهم جدًا لمشكلة الـSRT التي تعمل عليها

أنت عندك:

```text
Audio
+
SRT
+
Visual Beats
+
Asset durations
```

لو استخدمت floating point فقط:

```text
0.033333
0.066666
0.099999
```

ستظهر أخطاء صغيرة مع الزمن.

الأفضل:

```text
MediaTime
```

مثلاً:

```text
1 second = 120000 ticks

0.5 sec = 60000
1 sec   = 120000
2 sec   = 240000
```

ثم:

```text
Speech Beat
      ↓
MediaTime
      ↓
Visual Beat
      ↓
Keyframe
```

---

# 32. ماذا أنصحك أن نأخذ منه؟

ليس كل OpenCut.

أنا أقترح هذه البنية:

## المرحلة A — Font Engine

نأخذ فكرة:

```text
Fontsource
Font Registry
Font Metadata
Font Preview Atlas
```

لكن نبني:

```text
Arabic Font Registry
```

لدعم:

```text
TTF
OTF
WOFF
WOFF2
```

---

# 33. المرحلة B — Animation Engine

نأخذ:

```text
Keyframes
Bezier
Graph
Property Lanes
```

لكن نوسعها إلى:

```text
Position
Scale
Rotation
Opacity
Anchor
Blur
Glow
Shadow
Color
Mask
Effect Parameters
```

---

# 34. المرحلة C — GPU Effects

نأخذ فكرة:

```text
EffectPipeline
EffectPass
WGSL
Uniforms
```

ثم نضيف:

```text
Blur
Glow
Drop Shadow
Inner Shadow
Brightness
Contrast
Saturation
Hue
Grayscale
Sepia
Vignette
Noise
Film Grain
Chromatic Aberration
RGB Split
Motion Blur
Sharpen
```

---

# 35. المرحلة D — Masks

نأخذ:

```text
Mask Registry
Mask Definition
Mask Parameters
Mask Handles
SDF
JFA
Feather
```

ثم نضيف:

```text
Circle
Rectangle
Ellipse
Polygon
Freeform
Text
Image Alpha
Luma
Gradient
```

---

# 36. المرحلة E — Compositor

وهنا نستخدم:

```text
Frame
  ↓
Layers
  ↓
Transforms
  ↓
Masks
  ↓
Effects
  ↓
Blend
  ↓
GPU
```

والـLayer عندنا يصبح:

```json
{
  "id": "apple",
  "texture": "apple.png",
  "transform": {},
  "animation": {},
  "mask": {},
  "effects": [],
  "blend_mode": "normal",
  "opacity": 1
}
```

---

# 37. ثم نضيف الشيء الذي OpenCut لا يملكه بالشكل الذي تحتاجه

وهذا هو:

# Semantic Motion Planner

وهذا أهم جزء في مشروعك.

مثلاً:

```text
النص:

"المخ أحيانًا يشوف وجه في الأشياء العادية"
```

النظام يقرر:

```text
Main Asset:
Face

Secondary:
Brain

Motion:
Face → Pop In
Brain → Slow Scale
Face → Slight Bounce
```

ثم يولد:

```text
Keyframes
+
Effects
+
Camera
```

---

# 38. وهنا يصبح مشروعك أقوى من OpenCut

OpenCut:

```text
User
 ↓
ضع العنصر
 ↓
حرّكه
 ↓
ضع Keyframes
```

مشروعك:

```text
Script
 ↓
Semantic Analysis
 ↓
Visual Beat
 ↓
Asset
 ↓
Motion Role
 ↓
Motion Template
 ↓
Keyframes
 ↓
GPU Effects
 ↓
Camera
 ↓
Render
```

وهذا يتوافق تمامًا مع النظام الذي كنا نبنيه عندك:

```text
Narrative Semantic Beat Binder
+
Asset Sheet
+
Visual Beat Timing
+
Dynamic SRT
+
Motion Renderer
```

---

# 39. شيء آخر مهم اكتشفته

هناك مشروع خارجي مبني حول OpenCut اسمه:

[opencut-video-effects](https://github.com/Shuozeli/opencut-video-effects?utm_source=chatgpt.com)

وهو مفيد جدًا لنا لأنه يوضح **قيود OpenCut Classic الحقيقية**.

صاحبه يذكر أن Classic يستطيع عمل Keyframes على:

```text
transform.*
opacity
```

لكن الـMasks ليست Keyframeable في النظام الحالي، ولذلك بعض الـEffects يتم تجهيزها مسبقًا بدل بنائها ديناميكيًا. [GitHub](https://github.com/Shuozeli/opencut-video-effects?utm_source=chatgpt.com)

وهذه ملاحظة مهمة جدًا:

> **لا ينبغي أن ننقل قيود OpenCut إلى محركنا.**

نأخذ architecture ونوسعها.

---

# 40. ما الذي يمكن نسخه مباشرة؟

بما أن OpenCut Classic تحت MIT، فالكود نفسه يمكن إعادة استخدامه وفق شروط MIT، مع الحفاظ على إشعارات الترخيص وحقوق النشر. [GitHub](https://github.com/OpenCut-app/opencut-classic/blob/main/README.md?utm_source=chatgpt.com)

لكن:

| المكون | النقل |
|---|---|
| Rust Effects Pipeline | ✅ ممتاز |
| WGSL Gaussian Blur | ✅ |
| Mask SDF/JFA | ✅ ممتاز |
| Compositor architecture | ✅ ممتاز |
| WASM bridge | ⚠️ حسب هدفك |
| Keyframe concepts | ✅ |
| Font generator | ✅ |
| Font files | ⚠️ كل Font حسب ترخيصه |
| Flags | ⚠️ راجع المصدر |
| Logos | ⚠️ لا تفترض MIT |
| Icons | ⚠️ حسب provider |
| UI | ❌ لا نحتاجه |
| Timeline UI | ❌ لا نحتاجه |

---

# 41. ماذا أريد أن أبنيه لك فعليًا؟

بدل أن يصبح مشروعك نسخة من OpenCut، أقترح:

```text
motion_engine/
│
├── core/
│   ├── timeline
│   ├── media_time
│   ├── layer
│   ├── frame
│   └── scene
│
├── animation/
│   ├── keyframe
│   ├── curve
│   ├── bezier
│   ├── easing
│   ├── spring
│   └── evaluator
│
├── effects/
│   ├── pipeline
│   ├── blur
│   ├── glow
│   ├── shadow
│   ├── color
│   ├── grain
│   └── chromatic
│
├── masks/
│   ├── registry
│   ├── rectangle
│   ├── ellipse
│   ├── polygon
│   ├── freeform
│   ├── sdf
│   └── feather
│
├── compositor/
│   ├── layers
│   ├── blend
│   ├── transforms
│   ├── masks
│   └── effects
│
├── fonts/
│   ├── registry
│   ├── metadata
│   ├── arabic
│   └── atlas
│
├── motion/
│   ├── entrance
│   ├── exit
│   ├── emphasis
│   ├── reveal
│   ├── pop
│   ├── slide
│   ├── zoom
│   └── camera
│
└── semantic/
    ├── beat
    ├── asset_role
    ├── motion_role
    └── planner
```

وهذا سيكون **Motion Graphics Engine حقيقي** وليس Video Editor فقط.

---

## الخلاصة المهمة

إذا كان هدفك تحديدًا:

> **أريد أخذ الخطوط والتأثيرات من OpenCut واستخدامها في مشروع الـMotion Graphics الخاص بي**

فلا أنصح بأخذ المشروع كاملًا.

**الأجزاء الذهبية التي تستحق الاستخراج هي:**

```text
① Font generation / registry
        ↓
② Keyframe + Bezier concept
        ↓
③ EffectPass + GPU shader pipeline
        ↓
④ Mask Registry
        ↓
⑤ SDF + JFA Feather
        ↓
⑥ Compositor
        ↓
⑦ wgpu GPU Context
        ↓
⑧ MediaTime
```

والأهم أن `EffectPipeline` بالفعل مبني بطريقة تسمح لنا بإضافة Shaders جديدة، والـMask system مبني Registry + Definitions، والـCompositor يستقبل Layers/Transforms/Masks/Effects كبيانات منفصلة. هذه الثلاثة بالذات هي التي أرى أنها تصلح كأساس لمحركك. [GitHub](https://raw.githubusercontent.com/OpenCut-app/opencut-classic/main/rust/crates/effects/src/pipeline.rs)

**الخطوة التالية التي أوصي بها:** نبدأ باستخراج **حزمة مستقلة من OpenCut** وليس نسخ المشروع: `fonts + effects + masks + keyframes + compositor`، ونصممها كـ`Motion Engine` يمكن لمحرك الـAsset Sheet عندك استدعاؤه. والأفضل أن تكون **Rust + wgpu** في قلب الـrenderer، بينما Python يبقى مسؤولًا عن الـsemantic planning والـSRT والـasset orchestration.
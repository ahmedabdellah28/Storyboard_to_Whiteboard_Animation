# الخطة الرئيسية الشاملة لتطوير `Image-to-Animate` إلى نظام `AI-Directed Motion Graphics`

> **الإصدار:** 1.0  
> **التاريخ:** 5 أكتوبر 2026  
> **الهدف:** تحويل مشروع `image_to_animate` الحالي إلى محرك موشن جرافيك ثنائي الأبعاد موجه بالذكاء الاصطناعي، مع الحفاظ على وضع الـWhiteboard 
---

# 0. الملخص التنفيذي

المشروع الحالي يمتلك أساسًا قويًا بالفعل:

- استخراج العناصر بشكل تكيفي بدل التقطيع الشبكي الثابت.
- `Visual Manifest`.
- `Narrative Visual Map`.
- `Final Render Plan`.
- `Demand Estimator`.
- `DynamicSectionEngine`.
- `Whisper` للتوقيت الصوتي.
- نظام `DAG` وإدارة الموارد والحالة والـArtifacts.
- Camera system.
- SFX وAudio mixing.
- Whiteboard inking engine.

هذه المنظومة **لا يجب هدمها**.

الهدف هو إضافة طبقة Motion Graphics ذكية فوقها.

المعماريّة المستهدفة:

```text
                    INPUT
         ┌───────────┴───────────┐
         │                       │
     Storyboard               Script
         │                       │
         └───────────┬───────────┘
                     ↓
             VISUAL UNDERSTANDING
                     ↓
             VISUAL MANIFEST
                     ↓
        MOTION INTENT / DECOMPOSITION
                     ↓
             MOTION ASSET GRAPH
                     ↓
            NARRATIVE VISUAL MAP
                     ↓
              MOTION GRAPH
                     ↓
          CAMERA CHOREOGRAPHY
                     ↓
          DETERMINISTIC SCHEDULER
                     ↓
             FINAL RENDER PLAN
                     ↓
          EXISTING RENDER ENGINE
                     ↓
                  VIDEO
```

المبدأ الأساسي:

> **لا نفصل كل ما يوجد في الصورة. نفصل فقط ما يحتاج استقلالًا حقيقيًا في الحركة.**

والمبدأ الثاني:

> **الذكاء الاصطناعي يقرر ويفهم ويبحث ويقترح ويسأل، بينما الـRuntime ينفذ العمليات الحتمية بدقة.**

---

# 1. النتيجة النهائية المطلوبة

النتيجة النهائية ليست مجرد:

```text
صورة → فيديو
```

بل:

```text
صورة + نص + صوت
        ↓
فهم بصري
        ↓
فهم سردي
        ↓
تحديد العناصر المهمة
        ↓
تحديد ما يجب عزله
        ↓
استخراج/إعادة بناء الطبقات
        ↓
تحديد العلاقات بين العناصر
        ↓
تحديد دور كل عنصر
        ↓
اختيار أسلوب الحركة
        ↓
بناء Motion Graph
        ↓
بناء Camera Choreography
        ↓
ربط الحركة بالكلام
        ↓
رندر
        ↓
QA
        ↓
فيديو موشن جرافيك احترافي
```

يجب أن يستطيع النظام التعامل مع صور مختلفة جدًا دون اعتماد على عدد ثابت من الأعمدة أو العناصر أو المشاهد.

---

# 2. ما لا نريد بناءه

## 2.1 لا نريد HTML/CSS للرندر

لا تستخدم:

- HTML كـRenderer.
- CSS animations كمحرك الفيديو.
- DOM layers لتحريك عشرات العناصر.
- Browser recording كحل إنتاجي.

HTML/CSS يمكن أن يكون مناسبًا مستقبلًا لبعض أدوات الـStudio فقط، لكن **ليس هو محرك Motion Graphics**.

---

## 2.2 لا نريد Image-to-Video Black Box

لا نريد نموذجًا يأخذ الصورة ويقول:

> "حركتها."

لأننا نحتاج:

- قابلية التحرير.
- Layer ownership.
- Timeline.
- Camera.
- SFX.
- تزامن صوتي.
- إعادة الرندر.
- التحكم اليدوي.
- تتبع الأخطاء.
- حفظ الحالة.
- استبدال Tool بأخرى.
- إمكانية إعادة بناء المشهد.

---

## 2.3 لا نريد فصلًا حرفيًا لكل بكسل أو كل بتلة

الفصل يجب أن يكون قائمًا على **وظيفة الحركة**.

مثال:

```text
Flower
```

إذا كانت ستقوم بـ:

```text
gentle sway
```

يكفي Layer واحدة.

أما إذا كانت ستقوم بـ:

```text
petals opening
```

فقد نحتاج:

```text
petals
center
stem
```

---

## 2.4 لا نريد Presets عشوائية

غير مقبول:

```text
كل Object → fade_in
كل Object → slide
```

المطلوب:

```text
Object semantic type
+
Narrative role
+
Motion intent
+
Relations
+
Scene context
→
Motion behavior
```

---

# 3. الوضعان الأساسيان للمشروع

يجب الحفاظ على:

```text
render_mode = whiteboard
```

وإضافة:

```text
render_mode = motion_graphics
```

ويمكن إضافة:

```text
render_mode = hybrid
```

---

## 3.1 Whiteboard Mode

يبقى قريبًا من النظام الحالي:

- Inking.
- Outside-in pen.
- Hero element.
- Secondary animations.
- Camera pans الهادئة.
- قواعد 2–4 عناصر في المشهد.
- Whisper timing.
- SFX الحالي.
- NVENC / FFmpeg.
- Existing `DynamicSectionEngine`.

المواصفات الحالية للمشروع تنص على 2–4 عناصر لكل مشهد، Hero واحد للـinking والعناصر الثانوية تستخدم حركات متنوعة، مع عدد محدود من الـcamera pans. يجب الحفاظ على ذلك في Whiteboard Mode.

---

## 3.2 Motion Graphics Mode

لا يلزم أن يلتزم بالقيود الخاصة بالـWhiteboard.

يمكن أن يحتوي على:

- Continuous motion.
- Character motion.
- Object travel.
- Follow path.
- Parallax.
- Local deformation.
- Camera tracking.
- Impact.
- Reaction.
- Particles.
- Motion blur.
- Match motion.
- Whip transitions.
- Object transitions.
- Depth simulation.
- Layer interactions.
- Procedural effects.

---

## 3.3 Hybrid Mode

مثال:

```text
Hero:
    whiteboard inking

Secondary:
    motion graphics

Camera:
    cinematic

Particles:
    procedural

Audio:
    narrative synchronized
```

---

# 4. القاعدة المعمارية الأساسية

النظام يجب أن يفصل بين أربعة أشياء:

```text
1. Semantic Understanding
2. Motion Planning
3. Deterministic Scheduling
4. Rendering
```

الذكاء الاصطناعي ليس مسؤولًا عن الحساب الفيزيائي الدقيق لكل Frame.

بل:

```text
AI:
    ماذا يحدث؟
    لماذا؟
    ما الذي يتحرك؟
    ما العلاقة؟
    ما الحركة المقترحة؟

Runtime:
    متى؟
    أين؟
    كم Frame؟
    هل يوجد Collision؟
    هل العنصر خارج Viewport؟
    كيف يتحول إلى Pixels؟
```

---

# 5. التكوين المستهدف للـAI

يجب أن يتصرف AI كمنظومة أدوار:

```text
AI Supervisor
│
├── Senior Software Architect
├── Computer Vision Engineer
├── Motion Graphics Director
├── Research Engineer
├── Coding Agent
├── Test Engineer
├── Visual QA Reviewer
└── Performance / GPU Engineer
```

لكن هذه الأدوار **ليست Agents مستقلة بالضرورة**. يمكن تنفيذها داخل وكيل واحد مع حالات داخلية واضحة.

---

# 6. بروتوكول عمل الـAI

هذا البروتوكول إلزامي.

```text
OBSERVE
  ↓
AUDIT
  ↓
ANALYZE
  ↓
RESEARCH
  ↓
COMPARE
  ↓
PROPOSE
  ↓
ASK USER WHEN NEEDED
  ↓
WAIT
  ↓
DESIGN
  ↓
IMPLEMENT
  ↓
TEST
  ↓
RENDER PREVIEW
  ↓
VISUAL QA
  ↓
BENCHMARK
  ↓
REPORT
  ↓
ASK ACCEPTANCE
  ↓
INTEGRATE
```

---

# 7. متى يجب على الـAI أن يسأل؟

## 7.1 يسأل إلزاميًا عند

- تغيير Architecture.
- إضافة dependency كبيرة.
- اختيار Model أساسي.
- وجود License غير واضحة.
- احتياج GPU/VRAM جديد.
- وجود أكثر من حل صالح مع trade-off واضح.
- تعديل سلوك قد يكسر Whiteboard Mode.
- قرار إبداعي لا يمكن حسمه آليًا.
- عدم التأكد من تقسيم عنصر معقد.
- تعارض بين النص والصورة.
- الحاجة إلى إعادة بناء أجزاء قد تغير شكل العمل.
- وجود تكلفة API أو خدمة خارجية.
- اقتراح حذف/استبدال مكون يعمل حاليًا.

---

## 7.2 لا يسأل في الحالات الروتينية

- إنشاء Unit Test.
- إصلاح typo.
- تحسين logging.
- Refactor داخلي صغير لا يغير contract.
- إصلاح crash واضح.
- تحسين exception handling.
- إضافة validation.
- إضافة test fixtures.
- استخدام utility موجودة داخل المشروع.

---

# 8. شكل سؤال الـAI للمستخدم

يجب ألا يسأل:

> ماذا أفعل؟

بل يجب أن يعطي قرارًا قابلًا للاختيار.

مثال:

```text
وجدت أن فصل الدبور يحتاج segmentation.

الخيارات:

A — استخدام SAM 3.1
ميزة: open-vocabulary segmentation + tracking
ملاحظة: يحتاج التحقق من الوصول وشروط استخدام checkpoint.

B — استخدام SAM 2.1
ميزة: أكثر نضجًا وأسهل دمجًا.

C — Grounding DINO → SAM 2
ميزة: تحكم أفضل في اختيار object بالاسم.

أوصي بـ C كبداية لأنه يتوافق مع الـobject-by-text workflow.

هل أعتمد C؟
```

ثم:

```text
WAIT
```

ولا يقوم بتغيير المشروع قبل الإجابة.

---

# 9. مرحلة 0 — Repository Audit

## الهدف

فهم المشروع الحالي بالكامل قبل كتابة أي كود.

## المدخلات

- Repository.
- Project tree.
- Existing Python modules.
- Contracts.
- Tests.
- Rendering code.
- Config.
- Requirements.
- Cached models.
- GPU information.
- Existing scripts.

## يجب فحص

```text
core/
production_engine/
kivy/
scripts/
tests/
configuration/
dependencies/
artifacts/
state/
```

## النتيجة

إنشاء:

```text
docs/AI_MOTION_GRAPHICS_ARCHITECTURE_AUDIT.md
```

ويحتوي:

```text
Existing Modules
Reusable Modules
Unsafe Modules
Missing Capabilities
Duplicate Logic
Potential Conflicts
Renderer assumptions
Dependency risks
Performance risks
```

## ممنوع

البدء في Coding قبل اكتمال Audit.

---

# 10. Stage 1 — Research Program

يبدأ الـAI بإنشاء قائمة احتياجات:

```text
R-001 Object Detection
R-002 Segmentation
R-003 Mask Refinement
R-004 Background Reconstruction
R-005 Text/OCR
R-006 Human/Character Decomposition
R-007 Local Deformation
R-008 Path Animation
R-009 Particle Rendering
R-010 Camera Composition
R-011 GPU Rendering
R-012 Video Encoding
R-013 QA / Visual Comparison
```

كل Research Task يجب أن يحتوي:

```yaml
research_id:
problem:
candidate_tools:
official_source:
github:
license:
checkpoint_license:
python_compatibility:
cuda_compatibility:
vrAM_estimate:
speed:
quality:
integration_complexity:
commercial_constraints:
maintenance_status:
benchmark_status:
recommendation:
confidence:
fallback:
```

---

# 11. أداة الاختيار لا تكون ثابتة

يجب بناء:

```text
core/research/tool_registry.py
```

ومخزن:

```text
research/tool_registry.json
```

مثلاً:

```json
{
  "tool": "sam2",
  "category": "segmentation",
  "approved": true,
  "tested": true,
  "quality_score": 8.7,
  "speed_score": 8.2,
  "integration_score": 9.1,
  "license_status": "reviewed",
  "fallback": "classical_cv"
}
```

---

# 12. Research Results الحالية

## 12.1 SAM 3 / SAM 3.1

المشروع الرسمي يصف SAM 3 بأنه نموذج موحد لـpromptable segmentation في الصور والفيديو، ويمكنه detection/segmentation/tracking باستخدام text أو visual prompts. إصدار SAM 3.1 يضيف Object Multiplex لتتبع عدة كائنات بمشاركة الذاكرة. الصفحة الرسمية الحالية تشير إلى إصدار SAM 3.1 في مارس 2026، ومتطلبات تشغيل حديثة تشمل Python 3.12+ وPyTorch 2.7+ وCUDA 12.6+ على GPU متوافق.

المصدر الرسمي:

- https://github.com/facebookresearch/sam3

**قرار المشروع:** مرشح قوي، لكن لا يعتمد نهائيًا قبل benchmark والتحقق من checkpoint access/license.

---

## 12.2 SAM 2.1

SAM 2 يدعم segmentation للصور والفيديو ويمكن تدريبه أو fine-tune باستخدام بيانات مخصصة. المشروع الرسمي يذكر أن الـmodel checkpoints والـdemo code وtraining code متاحة تحت Apache 2.0.

المصدر:

- https://github.com/facebookresearch/sam2

**قرار المشروع:** يجب أن يكون fallback أساسيًا قويًا.

---

## 12.3 Grounding DINO

Grounding DINO مناسب كطبقة open-set/open-vocabulary detection لتحديد عناصر بمسمى لغوي قبل تمريرها إلى segmentation. تنفيذ المستودع الرسمي يحمل Apache 2.0 للكود، مع ضرورة مراجعة تراخيص checkpoints/datasets بشكل منفصل قبل التوزيع التجاري.

المصدر:

- https://github.com/IDEA-Research/GroundingDINO

---

## 12.4 Grounded-SAM 2

Grounded-SAM 2 يوفر pipeline تجمع Grounding DINO وSAM 2 ويمكن أن تتضمن Florence-2، ويدعم Grounding/Segmentation/Tracking. هذا المشروع مفيد جدًا كمرجع تكاملي وحتى عند بناء Adapters خاصة بالمشروع.

المصدر:

- https://github.com/IDEA-Research/Grounded-SAM-2

يجب الانتباه إلى أن المشروع المركب يحتوي على أكثر من مكوّن وترخيص؛ لا يجوز افتراض أن ترخيص المستودع الواحد يعني تلقائيًا أن كل checkpoint/data component له نفس الشروط.

---

## 12.5 LaMa

LaMa مفيد كمصدر بحثي/تقني لأعمال inpainting وإعادة بناء الخلفية، لكن الترخيص الظاهر للمستودع الأصلي هو CC BY-NC 4.0، ولذلك **لا يعتمد كمكون إنتاج تجاري افتراضي** بدون مراجعة قانونية وترخيصية مناسبة.

المصادر:

- https://github.com/advimman/lama
- https://github.com/facebookresearch/LAMA

---

## 12.6 Kornia

Kornia يوفر عمليات هندسية وغير هندسية على الصور، بما في ذلك affine/perspective/elastic/thin-plate-spline transforms، ويمكن استخدامه لتجارب deformation وmotion warping، مع ضرورة الانتباه إلى حدود نقل boxes/keypoints مع بعض non-rigid transforms.

المصدر:

- https://kornia.readthedocs.io/

---

## 12.7 PyAV

PyAV يوفر Python bindings لـFFmpeg، وهو مناسب للوصول إلى frames وstreams والـcontainers داخل Python.

المصدر:

- https://pyav.org/

---

## 12.8 FFmpeg

FFmpeg يجب أن يبقى جزءًا من مسار الإنتاج النهائي، خصوصًا للتجميع والـencoding والـmux والـfilters. وثائق FFmpeg الرسمية تتضمن `overlay` بمواضع ديناميكية وغيرها من عمليات الـvideo compositing.

المصدر:

- https://ffmpeg.org/ffmpeg-filters.html

---

# 13. Stage 2 — Visual Understanding

بعد Audit والبحث:

```text
Storyboard
    ↓
Candidate Extraction
    ↓
Visual Review
    ↓
Semantic Objects
```

يجب ألا يكون هدف هذه المرحلة extraction كامل.

هدفها:

```text
What exists?
What matters?
Which objects interact?
Which objects may need independent motion?
```

---

# 14. Visual Manifest الجديد

الحالة الحالية `Visual Manifest` تبقى، لكن في Motion Graphics يجب توسيع metadata.

مثال:

```json
{
  "visual_id": "cand_007",
  "bbox": [120, 240, 520, 700],
  "complexity": 0.71,
  "semantic": {
    "category": "animal",
    "subcategory": "wasp",
    "role": "actor"
  },
  "motion": {
    "likely_to_move": true,
    "likely_independent": true,
    "preferred_motion": [
      "fly",
      "hover",
      "rotate",
      "recoil"
    ]
  }
}
```

---

# 15. Stage 3 — Motion Intent Analysis

هذه أهم طبقة جديدة.

اسمها المقترح:

```text
Motion Intent Analyzer
```

وظيفتها تحويل:

```text
Visual Manifest
+
Narrative Map
```

إلى:

```text
Motion Intent
```

مثلاً:

```json
{
  "object": "wasp",
  "intent": "approach_target",
  "target": "orchid",
  "reaction_after_contact": "recoil",
  "importance": 0.96
}
```

---

# 16. Minimum Sufficient Decomposition

هذا Contract أساسي.

```text
الهدف:
العثور على أقل تقسيم Layer يسمح بتنفيذ الحركة المطلوبة.
```

الـAI يجب أن يحدد:

```text
decomposition_level:
    whole
    object
    subgroup
    subpart
    procedural
```

---

## 16.1 مثال

إذا كانت:

```text
flower → sway
```

النتيجة:

```text
one layer
```

إذا:

```text
flower → petals open
```

النتيجة:

```text
petals
center
stem
```

إذا:

```text
bee → fly across scene
```

النتيجة:

```text
bee independent layer
```

إذا:

```text
pollen → burst
```

النتيجة:

```text
procedural particle system
```

---

# 17. Stage 4 — Adaptive Segmentation Router

لا نستخدم Model واحدًا دائمًا.

```text
                    OBJECT
                       │
             ┌─────────┴─────────┐
             ↓                   ↓
       Easy classical?      Semantic object?
             ↓                   ↓
       OpenCV methods       Detector / Grounding
                                 ↓
                           Segmentation
                                 ↓
                            Mask Refiner
```

الـRouter يجب أن يختار استنادًا إلى:

```text
background
contrast
object size
object overlap
edge complexity
semantic confidence
required motion
GPU budget
tool availability
license
```

---

# 18. مستويات segmentation

## Level A — Classical

مناسب لـ:

- white gaps
- simple colors
- connected components
- contours
- threshold
- flood fill

وهذا يتوافق مع الـNatural White-Gap pipeline الموجود حاليًا.

---

## Level B — Prompted Segmentation

عندما نعرف اسم العنصر:

```text
"bee"
"flower"
"map"
"person"
```

نستخدم detector/segmenter.

---

## Level C — Interactive Refinement

عندما الـmask غير نظيف:

```text
positive points
negative points
box
mask prompt
```

---

## Level D — Human Review

إذا confidence منخفض:

```text
ASK USER
```

ولا يتم إنتاج Layer سيئة تلقائيًا.

---

# 19. Mask Quality Gate

لكل Mask:

```text
edge_quality
leakage
hole_ratio
halo_ratio
confidence
foreground_coverage
background_contamination
```

يتم إنتاج:

```json
{
  "mask_quality": {
    "confidence": 0.93,
    "halo_score": 0.04,
    "leakage_score": 0.01,
    "holes_score": 0.02,
    "status": "PASS"
  }
}
```

---

# 20. Mask Refinement

يجب أن تدعم:

- Morphological close/open.
- Hole filling.
- Edge smoothing.
- Alpha feathering.
- Small component removal.
- Interior preservation.
- Edge decontamination.
- Anti-halo handling.

لا تستخدم smoothing قويًا لدرجة تدمير التفاصيل.

---

# 21. Background Reconstruction

عندما يصبح Object مستقلاً:

```text
Original
 ↓
Object Mask
 ↓
Object removed
 ↓
Background reconstruction
 ↓
Clean background
```

اختيار طريقة reconstruction يكون Router أيضًا:

```text
simple flat area
→ OpenCV

repeated/simple texture
→ patch-based

complex texture
→ approved inpainting backend

uncertain
→ ask user / preserve grouped scene
```

---

# 22. الأصل لا يجب أن يختفي

يجب حفظ:

```text
original_storyboard.png
original_coordinates
original_bbox
original_mask
clean_background
isolated_asset
```

ولا يتم تدمير المصدر.

---

# 23. Layer Reconstruction

كل Layer يحتاج:

```text
asset_id
source_candidate_id
bbox
original_position
anchor_point
z_index
mask
alpha
semantic_type
semantic_role
motion_capabilities
relationships
```

---

# 24. Coordinate Integrity

هذه نقطة إلزامية.

كل Layer يجب أن يحتفظ بالإحداثيات الأصلية.

مثال:

```json
{
  "asset_id": "bee_01",
  "source_bbox": [740, 390, 1040, 640],
  "world_position": [740, 390],
  "normalized_center": [0.71, 0.41]
}
```

عند الحركة:

```text
Original position
→ offset
→ transformation
```

ولا يعاد وضع العنصر عشوائيًا بناءً على crop dimensions.

---

# 25. Z-Order

يجب أن يكون لكل Layer:

```text
z_index
```

ومجموعات:

```text
background
midground
main actors
foreground
effects
camera overlays
```

---

# 26. Asset Graph

بعد الاستخراج نحتاج Graph بدل قائمة PNGs فقط.

```text
Asset Graph
│
├── Nodes
│   ├── bee
│   ├── orchid
│   ├── pollen
│   └── arrow
│
└── Edges
    ├── approaches
    ├── collides
    ├── attached_to
    └── points_to
```

---

# 27. Relationship Graph

أمثلة للعلاقات:

```text
approaches
moves_toward
collides_with
attaches_to
carries
points_to
surrounds
contains
emerges_from
follows
reacts_to
transforms_into
```

العلاقات مهمة لأن Motion Planner يستطيع الاستفادة منها.

---

# 28. Motion Role Classification

كل عنصر يجب تصنيفه إلى أحد الأدوار:

```text
hero
primary_actor
target
secondary_actor
context
decoration
direction_cue
reaction
effect
background
generated_effect
text
camera_anchor
```

---

# 29. Stage 5 — Narrative Visual Map

يجب الحفاظ على الفكرة الحالية:

```text
script concept
→ visual candidate
→ anchor phrase
```

ولكن Motion Graphics يضيف:

```text
concept
→ visual
→ action
→ relation
→ expected reaction
```

مثال:

```json
{
  "concept": "يطير نحو الزهرة",
  "visual_id": "bee_01",
  "target": "orchid_01",
  "action": "approach",
  "anchor": "يطير نحو"
}
```

---

# 30. Stage 6 — Motion Graph

الـMotion Graph هو أهم Contract جديد.

مثال:

```json
{
  "graph_id": "mg_001",
  "nodes": [
    {
      "id": "bee",
      "action": "enter"
    },
    {
      "id": "bee_approach",
      "action": "fly_to",
      "target": "orchid"
    },
    {
      "id": "contact",
      "action": "impact"
    },
    {
      "id": "bee_recoil",
      "action": "recoil"
    }
  ]
}
```

---

# 31. Motion Graph يجب أن يدعم Dependencies

مثلاً:

```text
bee_enter
    ↓
bee_approach
    ↓
hover
    ↓
impact
    ↓
pollen_attach
    ↓
recoil
    ↓
exit
```

لا يمكن أن يبدأ:

```text
pollen_attach
```

قبل:

```text
impact
```

---

# 32. Motion Behavior Engine

المسار:

```text
Motion Graph
   ↓
Behavior Resolver
   ↓
Behavior Parameters
   ↓
Frame Evaluation
```

---

# 33. Behavior Library

## Transform

```text
scale_pop
settle
overshoot
float
rotate
tilt
```

## Path

```text
bezier_follow
arc
orbit
chase
escape
```

## Organic

```text
sway
breathing
leaf_flutter
body_bob
wing_flap
wobble
```

## Character

```text
head_turn
gesture
body_shift
recoil
anticipation
```

## Impact

```text
anticipation
contact
shake
flash
deformation
particle_burst
```

## Reveal

```text
wipe
draw
mask_reveal
radial
stroke_reveal
```

## Transition

```text
match_motion
push
whip
object_wipe
camera_pass
```

---

# 34. الحركات لا يجب أن تكون منفصلة دائمًا

مثلاً:

```text
flying_wasp
=
bezier_follow
+
body_tilt
+
wing_flutter
+
velocity_bob
```

والضربة:

```text
impact
=
anticipation
+
acceleration
+
contact
+
camera_shake
+
particle_burst
+
recoil
```

---

# 35. Motion Profiles

لكل semantic type يمكن وجود profile.

مثال:

```json
{
  "profile": "flying_insect",
  "behaviors": [
    "path_follow",
    "body_tilt",
    "wing_flutter",
    "micro_bob",
    "acceleration"
  ]
}
```

أخرى:

```json
{
  "profile": "flower",
  "behaviors": [
    "organic_sway",
    "petal_micro_motion",
    "growth"
  ]
}
```

---

# 36. Procedural Effects

بعض الأشياء لا ينبغي استخراجها من الصورة.

أمثلة:

```text
pollen
dust
spark
glow
smoke
motion streak
impact particles
tiny debris
```

هذه يتم توليدها برمجيًا.

---

# 37. Particle Engine

يجب أن يدعم:

```text
position
velocity
acceleration
rotation
scale
life
opacity
spawn_rate
gravity
drag
noise
```

ويجب أن يكون deterministic عند الحاجة:

```text
random_seed
```

حتى تكون النتائج قابلة لإعادة الإنتاج.

---

# 38. Local Deformation Engine

عندما لا نحتاج فصل عنصر كامل:

```text
Original layer
+
Local warp
```

أمثلة:

```text
flower petal sway
fabric movement
breathing
soft squash
bounce
```

الـAI يقرر هل نحتاج:

```text
cutout
```

أم:

```text
local deformation
```

---

# 39. Deformation Safety

أي Deformation يجب ألا:

- يكسر حدود الـMask.
- يخلق شفافية سوداء.
- يترك holes.
- يغير الشكل بشكل غير منطقي.
- يطمس التفاصيل الرئيسية.

يجب وجود QA بعد deformation.

---

# 40. Path Engine

يجب أن يكون لدينا:

```text
Bezier
Catmull-Rom
Arc
Polyline
Custom
```

والعنصر يستطيع:

```text
follow path
orient to tangent
bank
accelerate
decelerate
```

---

# 41. Stage 7 — Camera Choreographer

الكاميرا يجب أن تفهم:

```text
target
reason
importance
motion relationship
scene bounds
```

أنواع:

```text
hold
push
pull
pan
track
follow
focus
match_move
whip
impact_shake
parallax
```

---

# 42. Camera لا تتحرك بدون سبب

مثال صالح:

```json
{
  "type": "follow",
  "target": "bee",
  "reason": "actor_crosses_scene"
}
```

مثال غير صالح:

```json
{
  "type": "pan",
  "reason": "new_asset_appeared"
}
```

ظهور عنصر وحده ليس سببًا كافيًا لتحريك الكاميرا.

---

# 43. Camera Planning

الـAI يجب أن يحدد:

```text
scene centers
camera targets
target object
start
end
duration
easing
```

ثم الـscheduler يتحقق من:

```text
collision
viewport
safe margins
timing
```

---

# 44. Transition Engine

الانتقالات لا تكون Fade دائمًا.

نحتاج:

```text
match_motion
directional_move
camera_push
camera_pull
whip
object_wipe
foreground_block
parallax_pass
scale_through
```

---

# 45. Match Motion

إذا خرج عنصر من المشهد A إلى اليمين:

```text
scene A:
bee → right

scene B:
next visual enters from right
```

تكون الحركة نفسها bridge.

---

# 46. Timeline

Timeline لا تكون فقط:

```text
asset start
asset duration
```

بل:

```text
start
anticipation
action
impact
reaction
hold
exit
```

مثال:

```json
{
  "start": 3.20,
  "anticipation": [3.20, 3.50],
  "action": [3.50, 3.75],
  "impact": [3.75, 3.90],
  "reaction": [3.90, 4.40],
  "hold": [4.40, 5.10]
}
```

---

# 47. Audio Ground Truth

الـAudio يبقى هو المرجع الزمني.

المشروع الحالي يعتمد على Faster-Whisper لاستخراج word-level timestamps، ويستخدم lead-in قبل الكلمة. يجب الحفاظ على مبدأ أن التوقيت الصوتي هو الـground truth.

Motion Graphics يضيف فوق ذلك:

```text
anticipation window
impact window
reaction window
```

لكن لا يجوز تغيير timestamp الأساسي للكلمة.

---

# 48. Semantic Timing

لا يكفي:

```text
element starts at sentence start
```

يجب:

```text
keyword
→ action
→ motion
```

مثلاً:

```text
"يطير الدبور"
→ flight starts slightly before/at phrase

"يحاول يتزاوج"
→ attraction/approach

"تضربه"
→ impact

"يلزق عليه كيس لقاح"
→ pollen attach
```

---

# 49. SFX

يجب توسيع نظام SFX الحالي.

حركات مثل:

```text
fly
→ soft_whoosh

impact
→ light_hit

pollen attach
→ soft_tick / sparkle

reaction
→ subtle accent
```

مع الحفاظ على الـducking.

المكس النهائي يبقى 48kHz stereo ويجب ألا تغطي المؤثرات على الـvoiceover.

---

# 50. Rendering Engine

لا نبني Renderer جديدًا إذا كان الموجود قادرًا على التوسع.

نفضل:

```text
DynamicSectionEngine
        ↓
Motion Graphics Adapter
        ↓
Existing compositor
```

بدل:

```text
DynamicSectionEngine
+
Completely unrelated second renderer
```

---

# 51. Render Abstractions

يجب فصل:

```text
Scene State
Motion State
Camera State
Compositor
Encoder
```

مثال:

```python
frame = renderer.render(
    scene_state=scene_state,
    camera_state=camera_state,
    frame_index=frame_index
)
```

---

# 52. Frame Evaluation

كل Frame يمكن أن يمر:

```text
time
 ↓
MotionGraph.evaluate(time)
 ↓
Camera.evaluate(time)
 ↓
LayerState
 ↓
Effects
 ↓
Composite
```

---

# 53. Determinism

لأجل الـQA وإعادة التجربة:

```text
seed
version
model version
asset hash
motion graph hash
render plan hash
```

يجب تخزينها.

---

# 54. Contract Architecture

النسخة المستهدفة:

```text
Contract 1:
visual_manifest.json

Contract 1.5:
decomposition_plan.json

Contract 2:
narrative_visual_map.json

Contract 2.5:
motion_graph.json

Contract 3:
final_render_plan.json
```

---

# 55. Contract 1 — Visual Manifest

مسؤول عن الحقيقة البصرية فقط.

يجب ألا يحتوي:

- Audio timestamps.
- Whisper data.
- render scheduling.

ويحتوي:

- Candidates.
- Geometry.
- Complexity.
- Semantic interpretation.
- confidence.
- extraction candidates.

---

# 56. Contract 1.5 — Decomposition Plan

يحتوي:

```text
object
required_motion
decomposition_level
preferred_method
dependencies
confidence
fallback
```

مثال:

```json
{
  "object": "bee",
  "motion_required": "fly",
  "decomposition": "independent_layer",
  "method": "semantic_segmentation",
  "confidence": 0.94
}
```

---

# 57. Contract 2 — Narrative Visual Map

يحتوي:

```text
script concept
visual_id
anchor phrase
semantic role
relationship
```

---

# 58. Contract 2.5 — Motion Graph

يحتوي:

```text
nodes
edges
behaviors
parameters
dependencies
camera intents
effects
```

---

# 59. Contract 3 — Final Render Plan

الـscheduler هو المسؤول عن تحويل:

```text
Motion Graph
+
Whisper
+
Constraints
+
Viewport
+
Demand
```

إلى:

```text
start
end
duration
position
scale
z
camera
effect
render layer
```

بدون LLM.

---

# 60. لماذا يجب أن يبقى Scheduling Deterministic؟

حتى لا يحدث:

```text
نفس الإدخال
→ AI يعطي توقيتًا مختلفًا
→ فيديو مختلف
```

المطلوب:

```text
AI:
    semantic decisions

Scheduler:
    deterministic physics/timing constraints
```

---

# 61. Motion Demand

النظام الحالي لديه `DemandEstimator` يعتمد على عوامل مثل:

```text
pixel mass
contour
edge density
complexity
```

يجب توسيعه.

في Motion Graphics يمكن أن يكون:

```text
Motion Demand =
    visual complexity
  + action complexity
  + path length
  + interaction complexity
  + effect complexity
```

مثلاً:

```text
simple pop
→ low demand

complex flying + rotation + reaction
→ high demand
```

---

# 62. Motion Timing Estimator

يجب أن يحسب:

```text
base duration
motion complexity
narrative importance
audio constraint
minimum readable duration
```

مع حدود:

```text
min_duration
max_duration
```

---

# 63. AI لا يحدد milliseconds النهائية

AI يقترح:

```text
impact should be fast
reaction should last longer
```

والـscheduler يحولها إلى توقيت حتمي ضمن الـaudio window.

---

# 64. Collision System

يجب تطوير collision من مجرد layout إلى motion collision.

يجب فحص:

```text
layer/layer overlap
intentional overlap
unintentional overlap
camera clipping
effect clipping
```

ويجب أن يعرف النظام أن بعض التداخلات صحيحة:

```text
bee overlaps orchid
```

إذا كانت العلاقة:

```text
collides_with
```

فهي:

```text
INTENTIONAL_OVERLAP
```

---

# 65. Viewport QA

يجب الاحتفاظ بقواعد الـsafe margins الحالية.

يجب التأكد أن:

```text
hero
actor
critical effect
text
```

لا يخرج من الشاشة بدون سبب سردي.

---

# 66. Motion QA

فحوصات جديدة:

```text
[ ] jitter
[ ] teleport
[ ] sudden acceleration
[ ] wrong rotation
[ ] broken path
[ ] object clipping
[ ] mask leak
[ ] halo
[ ] layer ordering
[ ] effect explosion
[ ] camera jump
[ ] visual dead-time
```

---

# 67. Visual Regression

كل Feature جديدة يجب أن تولد:

```text
golden frames
```

مثلاً:

```text
tests/golden/
    scene_001_frame_000.png
    scene_001_frame_030.png
    scene_001_frame_060.png
```

وتقارن مع output الجديد.

---

# 68. Motion Regression

اختبارات غير بصرية:

```python
assert bee.x(t1) < bee.x(t2)
assert impact_time > approach_end
assert pollen_time >= impact_time
```

---

# 69. Model Benchmark

كل Model جديد يجب اختباره على Dataset داخلي صغير.

مثلاً:

```text
benchmarks/decomposition/
    001_simple
    002_overlap
    003_character
    004_illustration
    005_text
    006_whiteboard
    007_multiple_objects
```

---

# 70. Benchmark Metrics

## Segmentation

```text
IoU
Boundary F1
Leakage
Halo score
Background contamination
```

## Motion

```text
smoothness
path error
timing error
camera jerk
collision count
```

## Performance

```text
latency
VRAM
RAM
CPU
GPU utilization
```

---

# 71. Research Gate

لا يتم إدخال Tool إلى Production مباشرة.

المراحل:

```text
DISCOVERED
 ↓
RESEARCHED
 ↓
LICENSE_REVIEW
 ↓
PROTOTYPED
 ↓
BENCHMARKED
 ↓
APPROVED
 ↓
PRODUCTION
```

---

# 72. License Gate

يجب الفصل بين:

```text
repository license
model checkpoint license
training data license
dependency licenses
API terms
```

لا يجوز كتابة:

> المشروع Apache لذلك كل شيء Apache.

يجب فحص كل جزء.

---

# 73. Current tooling decision principle

لا تعتمد أي Model لمجرد أنه أحدث.

استخدم:

```text
Quality
+
Accuracy
+
VRAM
+
Latency
+
Integration
+
License
+
Stability
+
Maintenance
```

مثلاً:

```text
score =
0.30 quality
+ 0.20 accuracy
+ 0.15 performance
+ 0.15 integration
+ 0.10 stability
+ 0.10 license/operational fit
```

يتم تعديل الأوزان بعد benchmark.

---

# 74. AI Research Reports

كل تقرير يجب أن ينتهي بـ:

```text
RECOMMENDATION:
WHY:
RISKS:
ALTERNATIVE:
BENCHMARK NEEDED:
USER DECISION REQUIRED:
```

---

# 75. Stage 7 — Example: Bee + Orchid

هذه الصورة الحالية هي Benchmark ممتاز.

## Visual Objects

```text
Thinking Character
Flower Group
Bee
Orchid
Australia Map
Hearts
Arrows
Pollen
```

لكن ليس كل عنصر مستقل.

---

## Required decomposition

```text
Character
→ independent

Flower Group
→ grouped asset

Bee
→ independent actor

Orchid
→ independent actor

Australia map
→ contextual asset

Hearts
→ separate support elements

Pollen
→ procedural

Arrows
→ vector/procedural if appropriate
```

---

# 76. مثال Motion Graph لهذه القصة

```text
character_think
    ↓
flowers
    ↓
bee_enters
    ↓
bee_approaches_flowers
    ↓
narrative_turn
    ↓
orchid_reveal
    ↓
bee_approaches_orchid
    ↓
hover
    ↓
impact
    ↓
pollen_attach
    ↓
bee_recoil
    ↓
bee_exits
    ↓
second_approach
    ↓
second_impact
```

---

# 77. لا نريد جعل الـ12 Panels = 12 Camera Scenes

يمكن أن توجد عدة panels داخل نفس visual sequence.

الهدف:

```text
beats
≠
camera cuts
```

يمكن:

```text
3 beats
→ 1 scene
```

والـcamera تتحرك فقط عندما يكون ذلك مفيدًا.

---

# 78. Main Actor Principle

في كل visual sequence:

```text
حدد عنصرًا واحدًا يقود عين المشاهد
```

ثم:

```text
Primary actor
+
supporting elements
+
camera
```

مثلاً:

```text
bee = main actor
orchid = target
pollen = effect
camera = follower
```

---

# 79. Secondary Motion

العناصر الثانوية لا يجب أن تكون static بالكامل دائمًا.

يمكن أن يكون لديها:

```text
micro sway
subtle float
ambient movement
highlight pulse
```

لكن بمستوى منخفض.

---

# 80. Hierarchy of Motion

كل Scene:

```text
1. Primary motion
2. Secondary motion
3. Ambient motion
4. Camera motion
5. Effects
```

ولا تبدأ كلها في نفس الـFrame.

---

# 81. Motion Density

نحتاج metric:

```text
motion_density
```

حتى لا تصبح كل ثانية مليئة بالحركة.

مثلاً:

```text
low
medium
high
impact
```

المشهد العادي:

```text
medium
```

لحظة الضربة:

```text
high / impact
```

ثم:

```text
recovery
```

---

# 82. Rhythm

الـAI يجب أن يفهم:

```text
setup
build
anticipation
action
reaction
resolution
transition
```

هذه أهم من أي preset.

---

# 83. Anticipation

أي حركة مهمة يجب أن تملك إمكانية:

```text
anticipation
```

قبل الفعل.

مثلاً ضربة الأوركيد:

```text
neutral
→ compress
→ strike
```

وليس:

```text
neutral
→ teleport strike
```

---

# 84. Follow-through

بعد الحركة الرئيسية:

```text
impact
→ recoil
→ settle
```

أو:

```text
flight
→ slow
→ hover
```

هذا يرفع الإحساس بالاحتراف.

---

# 85. Easing

يجب أن تكون easing جزءًا من الـBehavior.

أمثلة:

```text
linear
ease_in
ease_out
smootherstep
ease_out_back
spring
critically_damped
```

لا تستخدم easing واحدًا لكل شيء.

---

# 86. Physics-lite

محرك الحركة يحتاج:

```text
velocity
acceleration
damping
spring
gravity
drag
angular_velocity
```

لا نحتاج Physics Engine عام، بل مجموعة عمليات deterministic خفيفة.

---

# 87. Asset Parenting

يجب أن يدعم:

```text
parent
child
```

مثلاً:

```text
bee
 ├── wing_L
 └── wing_R
```

أو:

```text
character
 └── hand
```

لكن لا ننفذ هذا إلا عند الحاجة.

---

# 88. Anchor Points

كل asset يجب أن يحتوي:

```text
center
top
bottom
left
right
custom anchor
```

مثلاً:

```text
bee:
    anchor = body_center

arm:
    anchor = shoulder

flower:
    anchor = stem_base
```

هذا يجعل الحركة أكثر طبيعية.

---

# 89. Occlusion / Overlap

يجب أن يدعم النظام حالات:

```text
A behind B
B in front A
A passes behind C
```

وليس مجرد global z-index ثابت.

يمكن أن يتغير الـz-order عبر الزمن إذا كان الـmotion يحتاج ذلك.

---

# 90. Temporal Layer State

Layer يجب أن يكون:

```text
visible
hidden
entering
active
reacting
exiting
```

بدل opacity فقط.

---

# 91. Motion State Machine

مثال:

```text
HIDDEN
 ↓
ENTERING
 ↓
ACTIVE
 ↓
INTERACTING
 ↓
REACTING
 ↓
ACTIVE
 ↓
EXITING
 ↓
COMPLETE
```

---

# 92. AI State

الـAgent نفسه يحتاج state.

مثلاً:

```text
PROJECT_AUDIT
RESEARCH
WAITING_FOR_APPROVAL
IMPLEMENTATION
TESTING
VISUAL_REVIEW
WAITING_FOR_ACCEPTANCE
DONE
```

---

# 93. Human Approval State

أي قرار يحتاج المستخدم:

```text
AWAITING_USER
```

يجب ألا يتم تجاوزه تلقائيًا.

---

# 94. Artifact System

يجب أن يحفظ:

```text
audit
research
benchmarks
manifests
decomposition plans
motion graphs
render plans
preview videos
QA reports
decisions
```

---

# 95. Cache Strategy

يجب عدم إعادة:

```text
segmentation
background reconstruction
Whisper
model inference
```

إذا لم تتغير المدخلات.

هوية Cache يجب تعتمد على hashes.

مثلاً:

```text
source_image_hash
model_hash
prompt_hash
parameters_hash
```

---

# 96. Invalidation

إذا تغير:

```text
image
```

أعد:

```text
segmentation
decomposition
motion
render
```

أما إذا تغير:

```text
camera
```

فلا تعيد:

```text
segmentation
```

---

# 97. Versioning

لكل Contract:

```text
schema_version
```

مثلاً:

```text
visual_manifest v2
decomposition_plan v1
motion_graph v1
render_plan v3
```

---

# 98. ADR

كل قرار معماري مهم يجب أن ينتج:

```text
docs/adr/ADR-XXXX-title.md
```

ويحتوي:

```text
Context
Decision
Alternatives
Why
Consequences
Rollback
```

---

# 99. Coding Rules للـAI

يجب أن يلتزم الوكيل بـ:

1. لا يعيد كتابة Module موجود إذا كان Adapter كافيًا.
2. لا يضيف Dependency دون بحث ومبرر.
3. لا يغير Contract دون Versioning.
4. لا يكسر Whiteboard Mode.
5. كل Module جديد يحتاج tests.
6. كل algorithm بصري يحتاج golden test.
7. كل Renderer change يحتاج sample frames.
8. كل Model integration يحتاج benchmark.
9. لا حذف ملفات دون موافقة عند وجود خطر فقدان البيانات.
10. لا duplicate logic.

---

# 100. Development Loop

كل Feature:

```text
Issue
 ↓
Research
 ↓
Design
 ↓
User Approval
 ↓
Implementation
 ↓
Unit tests
 ↓
Integration tests
 ↓
Preview render
 ↓
Visual QA
 ↓
Benchmark
 ↓
Acceptance
```

---

# 101. Phase 1 الفعلية — Foundation

المطلوب:

```text
Motion contracts
Research registry
Agent state
Tool router interfaces
```

الملفات المقترحة:

```text
core/contracts/decomposition_plan.py
core/contracts/motion_graph.py
core/research/tool_registry.py
core/research/research_report.py
core/agent/decision_state.py
```

النتيجة:

```text
لا توجد حركة جديدة بعد.
لكن البنية أصبحت جاهزة.
```

---

# 102. Phase 2 — Dynamic Decomposition

المطلوب:

```text
decomposition planner
semantic object classifier
segmentation router
mask quality gate
```

النتيجة:

```text
صورة
→ required layers
```

---

# 103. Phase 3 — Reconstruction

المطلوب:

```text
clean background
isolated assets
coordinate preservation
mask refinement
```

النتيجة:

```text
background_clean.png
+
isolated object assets
+
metadata
```

---

# 104. Phase 4 — Motion Graph

المطلوب:

```text
behaviors
relations
dependencies
states
```

النتيجة:

```text
motion_graph.json
```

---

# 105. Phase 5 — Behavior Engine

المطلوب:

```text
path
transform
physics-lite
organic
impact
procedural effects
```

النتيجة:

```text
Motion Graph
→ frame states
```

---

# 106. Phase 6 — Camera

المطلوب:

```text
camera targets
follow
push
pull
transition
shake
parallax
```

النتيجة:

```text
camera_trajectory
```

---

# 107. Phase 7 — Renderer Integration

المطلوب:

```text
DynamicSectionEngine adapter
```

يجب أن يستطيع:

```text
render_mode=motion_graphics
```

دون التأثير على:

```text
render_mode=whiteboard
```

---

# 108. Phase 8 — Audio Synchronization

المطلوب:

```text
Whisper
→ semantic anchors
→ motion windows
```

النتيجة:

```text
speech-synchronized motion
```

---

# 109. Phase 9 — SFX

المطلوب:

```text
behavior → SFX mapping
```

مثلاً:

```text
fly → whoosh
pop → soft_pop
impact → light_hit
reveal → reveal_whoosh
camera_push → zoom_whoosh
```

---

# 110. Phase 10 — QA

المطلوب:

```text
frame QA
mask QA
motion QA
timing QA
camera QA
audio QA
```

---

# 111. Phase 11 — Studio

بعد نجاح الـBackend:

```text
Scene viewer
Layer list
Motion inspector
Camera inspector
Timeline
Manual position
Manual scale
Manual rotation
Motion enable/disable
Behavior parameters
```

---

# 112. Manual Override

هذه نقطة أساسية.

أي قرار AI يجب أن يستطيع المستخدم تعديله:

```text
AI position
→ user can change

AI motion
→ user can replace

AI timing
→ user can adjust

AI camera
→ user can override
```

بعد override:

```text
user_override = true
```

والـAI لا يعكس التعديل في rerun إلا بطلب المستخدم.

---

# 113. User vs AI Ownership

كل خاصية يجب أن تحمل:

```text
source = ai
source = user
source = system
```

مثلاً:

```json
{
  "scale": {
    "value": 1.28,
    "source": "user"
  }
}
```

---

# 114. AI Replanning

إذا طلب المستخدم:

> اجعل الدبور أسرع.

الـAI لا يعيد كل النظام.

بل:

```text
Identify affected node
→ update motion behavior
→ update downstream timing
→ rerender affected segment
```

---

# 115. Partial Re-render

لا نعيد فيديو كامل كل مرة إن أمكن.

نستخدم:

```text
scene cache
motion cache
background cache
asset cache
```

ثم render segment.

---

# 116. Preview tiers

يجب أن توجد:

```text
Draft
Preview
Production
```

## Draft

- Resolution منخفضة.
- FPS أقل.
- مؤثرات reduced.

## Preview

- 1080p.
- أغلب المؤثرات.

## Production

- 1080p.
- 30 FPS.
- NVENC.
- Audio master.

---

# 117. Performance Strategy

يجب ألا يُعاد تشغيل AI models لكل عنصر.

يفضل:

```text
Model session
→ load once
→ batch objects
→ reuse
```

وإذا كانت GPU memory محدودة:

```text
router
→ CPU fallback
→ sequential batches
```

---

# 118. Model Lifecycle

لكل Model:

```text
download
verify
load
warmup
inference
unload
cache
```

ولا يتم تحميل 3 نماذج ثقيلة في وقت واحد دون سبب.

---

# 119. Fallback Strategy

كل Tool يجب أن تحتوي:

```text
primary
fallback
safe fallback
```

مثلاً:

```text
SAM3.1
↓
SAM2.1
↓
OpenCV/manual refinement
```

---

# 120. Human-in-the-loop fallback

إذا فشل الجميع:

```text
ASK USER
```

مثلاً:

> لا أستطيع الحصول على Mask نظيف للنحلة دون اقتطاع جزء من الزهرة. هل تريد إبقاءهما Grouped Layer أم استخدام interactive point refinement؟

---

# 121. Auto-Question Policy

لا ترسل 20 سؤالًا دفعة واحدة.

رتب:

```text
BLOCKING QUESTIONS
IMPORTANT QUESTIONS
OPTIONAL PREFERENCES
```

اسأل الـBlocking فقط.

---

# 122. AI Research Memory

يجب ألا يعيد البحث عن نفس الأداة بلا سبب.

يحفظ:

```text
Tool
Version
Last checked
Benchmark
License review
Decision
```

---

# 123. Tool Update Policy

عند صدور إصدار جديد:

```text
new version detected
→ research delta
→ benchmark
→ ask user if production-impacting
```

لا يتم التحديث تلقائيًا لمجرد توفر إصدار أحدث.

---

# 124. Security / Reliability

لا تسمح للـAI:

- بتشغيل ملفات مجهولة دون sandbox.
- بتحميل model executables غير موثوقة.
- بتثبيت dependencies عشوائيًا.
- بإلغاء checksums.
- بتجاوز license gates.
- بحذف artifacts دون retention policy.

---

# 125. Artifact retention

الاحتفاظ بـ:

```text
original
previous approved
current candidate
QA-failed candidate
```

حتى يمكن الرجوع.

---

# 126. Error Categories

الأخطاء يجب تصنيفها:

```text
VISION_ERROR
SEGMENTATION_ERROR
RECONSTRUCTION_ERROR
SEMANTIC_ERROR
MOTION_ERROR
TIMING_ERROR
CAMERA_ERROR
RENDER_ERROR
AUDIO_ERROR
DEPENDENCY_ERROR
LICENSE_ERROR
PERFORMANCE_ERROR
```

---

# 127. Error recovery

مثلاً:

```text
SEGMENTATION_ERROR
→ refine mask

إذا فشل:
→ alternate model

إذا فشل:
→ user review
```

---

# 128. لا يجب إخفاء الفشل

يجب أن يظهر:

```text
status
confidence
fallback_used
```

وليس output مزيفًا.

---

# 129. Visual Review Panel

الـAI يجب أن يستطيع تقديم:

```text
Original
Candidate Masks
Layer Result
Background Reconstruction
Motion Preview
```

لكي يستطيع المستخدم المقارنة.

---

# 130. Contact Sheet

يبقى `contact_sheet` مهمًا.

ويجب توسيعه ليظهر:

```text
candidate
semantic label
confidence
decomposition level
motion role
```

---

# 131. Motion Contact Sheet

يجب أن يكون هناك أيضًا:

```text
motion_contact_sheet
```

يحتوي:

```text
Asset
Role
Motion
Target
Duration
Confidence
```

---

# 132. Golden Example

يجب أن يكون لدينا على الأقل مثال مرجعي كامل:

```text
Bee + Orchid
```

ويجب أن يختبر:

- segmentation.
- object interaction.
- path movement.
- camera follow.
- impact.
- procedural particles.
- reaction.
- second interaction.
- narrative timing.

---

# 133. Acceptance Test للصورة الحالية

النتيجة المقبولة:

```text
1. النحلة تتحرك في مسار طبيعي.
2. الأجنحة تتحرك بشكل خفيف.
3. الأوركيد لا تتحرك بشكل عشوائي.
4. الاقتراب واضح.
5. هناك anticipation قبل الضربة.
6. impact سريع.
7. camera reaction موجودة لكن ليست مبالغًا فيها.
8. pollen يظهر منطقياً.
9. الدبور يتفاعل بعد الضربة.
10. الانتقال للمشهد التالي يستخدم movement وليس fade فقط.
```

---

# 134. المطلوب من الـAI في كل Preview

أن يعرض:

```text
WHAT CHANGED
WHY
FILES CHANGED
TESTS
QA STATUS
KNOWN LIMITATIONS
NEXT DECISION
```

---

# 135. Example AI report

```text
Phase: Dynamic Decomposition

Completed:
- analyzed 12 candidates
- identified 8 semantic objects
- marked 3 as independent motion layers
- marked 2 as grouped assets
- marked 1 as procedural
- preserved 2 as background/context

Research:
- compared 3 segmentation strategies

Blocking decision:
هل نعتمد SAM2.1 + Grounding DINO كبداية؟

Status:
WAITING_FOR_USER
```

---

# 136. Prompt Protocol للـAI

يجب أن تكون تعليماته الداخلية على مستوى:

```text
You are the lead engineer and motion graphics director
for the existing image_to_animate project.

You MUST:
- inspect before changing
- research before introducing unfamiliar tools
- ask before architecture-impacting decisions
- wait for user approval
- preserve existing whiteboard behavior
- never use HTML/CSS as production renderer
- reuse existing contracts
- write tests
- benchmark new models
- run visual QA
- report failures honestly
```

ويجب إضافة:

```text
When multiple valid solutions exist:
1. research
2. compare
3. recommend one
4. explain tradeoffs
5. ask for decision
6. wait
```

---

# 137. Coding Prompt Rules

قبل الكود:

```text
Implementation Plan
```

يحتوي:

```text
Files to create
Files to modify
APIs
Contracts
Tests
Rollback
```

بعد الكود:

```text
Changed files
Tests executed
Results
Preview rendered?
QA results
```

---

# 138. Code Review Agent

بعد implementation:

```text
Diff
 ↓
Architecture review
 ↓
Performance review
 ↓
Test review
 ↓
Visual review
```

ويبحث عن:

```text
dead code
duplicate logic
race conditions
memory leaks
GPU memory problems
silent exceptions
hardcoded paths
hardcoded candidate counts
```

---

# 139. ممنوع Hardcoding

غير مقبول:

```python
for i in range(12):
```

إذا كان عدد العناصر ديناميكيًا.

غير مقبول:

```python
SCENES = [scene_1, scene_2, ...]
```

لـproduction إذا كانت الصورة متغيرة.

يجب أن تكون الـscenes والـobjects ناتجة عن analysis.

---

# 140. ممنوع Fixed Grid

الـwhiteboard extractor الحالي قائم على Natural White-Gap projection وRecursive XY-cut بدل تقسيم العرض إلى خلايا متساوية. يجب الحفاظ على هذا المبدأ وعدم الرجوع إلى Mechanical Grid Slicing.

---

# 141. ممنوع إسقاط العناصر بسبب limit ثابت

لا يوجد:

```text
max 10 candidates
```

إلا إذا كان هناك policy واضح.

يجب اكتشاف كل candidates ثم تصنيفها.

---

# 142. Scene Composition

في Whiteboard:

```text
2–4 elements
```

في Motion Graphics:

```text
ديناميكي
```

لكن ليس:

```text
20 moving objects simultaneously
```

يجب استخدام hierarchy.

---

# 143. Motion Scene Builder

يجب أن يأخذ:

```text
Asset Graph
+
Motion Graph
+
Narrative Map
```

ويولد:

```text
scene groups
```

تجمع العناصر حسب:

```text
semantic context
spatial coherence
narrative relation
motion compatibility
```

---

# 144. Camera Scene vs Narrative Beat

يجب الفصل:

```text
Narrative Beat
≠
Motion Beat
≠
Camera Scene
```

مثلاً:

```text
Narrative:
"يطير الدبور"

Motion:
enter + accelerate + fly

Camera:
follow
```

ثلاث طبقات مختلفة.

---

# 145. AI Visual Director

يجب أن يكون هناك مفهوم:

```text
Visual Director
```

قبل Final Render Plan.

وظيفته:

```text
review composition
review pacing
review motion density
review camera
review hierarchy
```

ويشبه الـAI Director Gate الحالي ولكن مخصص لـMotion Graphics.

---

# 146. Director Gate

قبل الرندر:

```text
PASS
```

أو:

```text
REVISE
```

مثلاً:

```text
REVISE:
- too many simultaneous motions
- camera changes too frequently
- main actor unclear
- transition not motivated
```

---

# 147. Director لا يغير timestamps

الـAudio timing Ground Truth.

Director يقترح choreography فقط.

Scheduler ينفذ ضمن القيود.

---

# 148. Camera + Motion Relationship

يجب أن يعرف الـAI:

```text
target moves
→ camera follows

target impacts
→ camera reacts

target stops
→ camera settles
```

لا:

```text
camera random zoom every 1 second
```

---

# 149. Parallax

يمكن استخدام:

```text
background
midground
foreground
```

مع اختلاف movement scale.

مثلاً:

```text
background = 0.2
midground = 0.5
foreground = 1.0
```

لكن فقط عندما توجد طبقات مناسبة.

لا نخلق fake depth إذا كان غير آمن بصريًا.

---

# 150. Depth Reconstruction

اختياري.

إذا احتجنا:

```text
foreground
midground
background
```

يتم تحديده من:

```text
semantic
occlusion
spatial context
```

ولا يجب أن يصبح prerequisite لكل صورة.

---

# 151. Text Handling

النصوص يمكن أن تكون:

```text
raster text asset
vectorized text
regenerated text
```

الاختيار يعتمد على:

```text
motion need
font availability
original fidelity
```

إذا كان النص يحتاج handwriting reveal، قد نحتاج path extraction.

---

# 152. OCR

OCR يجب أن يكون مساعدًا وليس authority مطلقًا.

إذا كان النص غير واضح:

```text
ASK USER
```

خصوصًا إذا كان التعديل النصي قد يغير المحتوى.

---

# 153. Character Decomposition

الشخصية لا تفصل تلقائيًا إلى الرأس والعين واليد والجسم دائمًا.

نستخدم:

```text
required_motion analysis
```

مثلاً:

```text
character thinking
→ full character + micro tilt
```

بينما:

```text
character waves
→ arm separation
```

---

# 154. Semantic Motion Capabilities

كل asset يحتفظ بقائمة:

```text
motion_capabilities
```

مثلاً:

```json
[
  "translate",
  "rotate",
  "scale",
  "follow_path",
  "sway",
  "recoil"
]
```

ثم Motion Planner لا يطلب capability غير موجودة إلا إذا قرر أن layer decomposition يحتاج ذلك.

---

# 155. Motion Capability Expansion

إذا احتجنا:

```text
wing_flap
```

وليس موجودًا:

```text
AI:
research whether procedural deformation is sufficient
or subpart extraction is needed
```

ثم يسأل عند الحاجة.

---

# 156. Procedural vs Extracted Decision

قاعدة:

```text
if effect is generated by motion:
    procedural

if effect exists in original and must preserve exact design:
    extracted

if object only needs global movement:
    whole object

if internal movement required:
    subpart
```

---

# 157. Asset Fidelity

كل Layer يجب أن تقيم:

```text
visual_fidelity
```

إذا انخفضت بعد extraction:

```text
FAIL
```

ولا يكفي أن يكون mask جميلًا.

---

# 158. Transparency and Edge Handling

يجب تجنب:

```text
white halo
black halo
fringing
semi-transparent background pixels
```

خصوصًا عند:

```text
white background
bright colors
hair
wings
semi-transparent objects
```

---

# 159. Edge-aware Extraction

للأجنحة مثل النحلة:

```text
thin structures
```

يجب أن يكون لديها policy خاصة.

مثلاً:

```text
thin-structure preservation
```

ولا نستخدم morphological operations قوية تقتل التفاصيل.

---

# 160. High-resolution Working Copy

إذا كانت الصورة صغيرة:

```text
analysis resolution
```

يمكن استخدام upscale داخلي فقط عند الحاجة.

لكن لا يتم الادعاء أنه يخلق معلومات أصلية غير موجودة.

---

# 161. Multi-resolution Strategy

```text
low-res
→ candidate discovery

mid-res
→ segmentation

high-res
→ mask refinement

native/full-res
→ final asset extraction
```

---

# 162. Model Router by Object Size

```text
small object
→ high-res crop inference

large object
→ full image inference
```

هذا يقلل التكلفة ويحسن التفاصيل.

---

# 163. Crop + Reproject

عند استخدام model على crop:

```text
crop coordinates
→ inference
→ original canvas coordinates
```

يجب إعادة إسقاط الـmask إلى الـsource coordinates بدقة.

---

# 164. No coordinate drift

بعد سلسلة transformations:

```text
crop
→ scale
→ mask
→ warp
```

يجب الحفاظ على:

```text
source_transform
```

حتى لا يحدث drift.

---

# 165. Asset Provenance

كل asset يعرف:

```text
source image
source candidate
source method
model
model version
mask version
reconstruction version
```

---

# 166. Example Provenance

```json
{
  "asset_id": "bee_01",
  "source": "storyboard.png",
  "candidate_id": "cand_007",
  "segmentation": {
    "tool": "sam2",
    "version": "...",
    "prompt": "bee"
  },
  "refinement": {
    "method": "edge_refine_v2"
  }
}
```

---

# 167. Rendering Quality Targets

الوضع الإنتاجي:

```text
1920 × 1080
30 FPS
48 kHz stereo audio
hardware encoding preferred
```

وهذا متوافق مع مواصفات الإنتاج الحالية للمشروع.

---

# 168. GPU Rendering

يفضل:

```text
NVIDIA NVENC
```

مع:

```text
libx264 fallback
```

والـAI لا يقرر encoder عشوائيًا؛ يقرأ capabilities.

---

# 169. Frame Pipeline

```text
Frame N
 ↓
Camera state
 ↓
Layer states
 ↓
Deformation
 ↓
Effects
 ↓
Composite
 ↓
Color / finishing
 ↓
Encoder
```

---

# 170. Preview Rendering

يفضل أن يكون قادرًا على:

```text
render specific range
```

مثلاً:

```text
00:03 → 00:08
```

للمراجعة.

---

# 171. Debug Overlays

وضع Debug يجب أن يستطيع إظهار:

```text
bbox
mask
anchor
motion path
velocity vector
camera target
z-index
semantic role
```

ويمكن إخفاؤه في Production.

---

# 172. Motion Trace

عناصر الحركة المهمة يجب أن تملك:

```text
trajectory visualization
```

حتى يراجعها المستخدم.

---

# 173. Motion Path Editor

في Studio مستقبلًا:

```text
path points
handles
speed profile
orientation
```

---

# 174. Behavior Inspector

مثلاً:

```text
Bee
Behavior: flying_insect

Path:
Bezier

Wing:
0.08 amplitude
8 Hz

Body tilt:
12°

Speed:
1.15
```

---

# 175. Motion Graph Editor

المستخدم يستطيع رؤية:

```text
ENTER
 ↓
APPROACH
 ↓
HOVER
 ↓
IMPACT
 ↓
RECOIL
 ↓
EXIT
```

---

# 176. Camera Inspector

يعرض:

```text
target
position
zoom
rotation
easing
duration
```

---

# 177. Timeline

يجب أن يرى المستخدم:

```text
Audio
│──────────────────────────────

Bee
   ███████████

Orchid
       █████████████

Pollen
               ██

Camera
      ─────────╱──────
```

---

# 178. AI Suggestions في Studio

يمكن للمستخدم أن يقول:

> اجعل دخول الدبور أكثر سرعة.

الـAI يجب أن يقترح:

```text
Increase acceleration
Shorten anticipation
Preserve impact timing
```

ثم:

```text
Apply
```

أو:

```text
Ask / preview
```

---

# 179. User can reject

كل اقتراح:

```text
Accept
Reject
Modify
```

ولا يعتبر AI override.

---

# 180. Multi-pass Generation

لا نريد الوصول للإخراج النهائي من أول محاولة.

المراحل:

```text
Pass 1:
Composition

Pass 2:
Motion

Pass 3:
Camera

Pass 4:
Effects

Pass 5:
Audio/SFX

Pass 6:
Final QA
```

---

# 181. AI should know current pass

مثلاً:

```text
CURRENT_PASS = MOTION
```

حتى لا يعيد كل شيء عندما المشكلة فقط في particles.

---

# 182. Scope-limited Repair

إذا فشل:

```text
mask
```

لا تعيد:

```text
TTS
Whisper
motion
camera
```

إلا إذا كانت dependencies تقول ذلك.

---

# 183. Dependency Graph

كل Artifact يجب أن يكون جزءًا من DAG.

مثال:

```text
storyboard
 ↓
candidates
 ↓
semantic manifest
 ↓
decomposition
 ↓
assets
 ↓
motion graph
 ↓
render plan
 ↓
video
```

---

# 184. Resume

عند انقطاع العمل:

```text
resume from last valid artifact
```

وهذا يتوافق مع فلسفة `StateStore/ArtifactStore` الموجودة حاليًا.

---

# 185. Atomic Completion

كل Stage يجب أن ينتج:

```text
artifact
metadata
hash
status
```

ولا يعتبر مكتملًا إلا بعد validation.

---

# 186. Observability

يجب تسجيل:

```text
model time
segmentation time
render time
GPU memory
cache hit
fallback
QA result
```

---

# 187. AI Cost Awareness

إذا استخدمنا API:

```text
estimated cost
```

يجب أن يظهر قبل تنفيذ تكلفة كبيرة.

---

# 188. Offline-first

الأفضل قدر الإمكان:

```text
local inference
local rendering
local cache
```

وتستخدم API فقط عند الحاجة.

---

# 189. External AI usage

عند استخدام API:

```text
purpose
input
provider
cost
privacy implications
```

ويجب أن يعرف المستخدم.

---

# 190. Research Source Policy

الأولوية:

```text
official documentation
official GitHub
official paper/project page
reputable technical docs
community evidence
```

ولا تعتمد مدونة مجهولة كمرجع وحيد لاختيار نموذج.

---

# 191. Research Freshness

قبل اعتماد Tool حديثة يجب التحقق من:

```text
latest release
maintenance
compatibility
license
checkpoint status
known issues
```

ولا يتم اعتبار المعلومات القديمة حقيقة حالية دون تحقق.

---

# 192. Coding Agent Tool Search

عندما يحتاج Library:

```text
search
→ compare
→ prototype
→ benchmark
→ user approval
→ integrate
```

---

# 193. لا يتم إنشاء Custom Code بلا حاجة

لكن عندما لا توجد Library مناسبة:

```text
AI must build a project-specific module
```

مثل:

```text
Motion Behavior Engine
Motion Graph Evaluator
Minimum Decomposition Planner
Camera Choreographer
Motion QA
```

---

# 194. Custom code quality

كل Custom Engine:

```text
typed
tested
documented
deterministic
configurable
logged
```

---

# 195. Tests Required

## Unit

```text
motion math
easing
path
camera
mask operations
contracts
```

## Integration

```text
image
→ segmentation
→ asset
→ motion
→ render
```

## Golden

```text
visual output
```

## Performance

```text
VRAM
latency
```

---

# 196. Test Fixtures

يجب إنشاء:

```text
fixtures/
    simple_white
    character
    multiple_objects
    overlapping
    text
    transparent_edge
    tiny_objects
    complex_illustration
```

---

# 197. Quality thresholds

كل threshold يجب أن يكون configurable.

مثلاً:

```yaml
mask:
  min_confidence: 0.80
  max_halo: 0.08
  max_leakage: 0.03
```

ولا ندفنها داخل الكود.

---

# 198. Config System

كل policy يجب أن يكون في:

```text
config/motion_graphics.yaml
```

مثلاً:

```yaml
render:
  width: 1920
  height: 1080
  fps: 30

motion:
  max_simultaneous_primary: 2
  max_camera_jerk: 0.15

qa:
  mask_confidence: 0.80
```

---

# 199. No Magic Numbers

أي رقم مهم يجب أن يكون:

```text
named constant
or config
or contract field
```

---

# 200. Migration Strategy

لا نغير المشروع دفعة واحدة.

## Stage M0

Audit only.

## Stage M1

Contracts only.

## Stage M2

Segmentation router prototype.

## Stage M3

One-object animation prototype.

## Stage M4

Interaction prototype.

## Stage M5

Camera prototype.

## Stage M6

Full scene prototype.

## Stage M7

Production integration.

---

# 201. Prototype 1

اختبار:

```text
Bee
```

المطلوب:

```text
extract
→ fly
→ rotate
→ render
```

بدون صوت.

---

# 202. Prototype 2

اختبار:

```text
Bee + Orchid
```

المطلوب:

```text
approach
→ hover
→ contact
→ recoil
```

---

# 203. Prototype 3

إضافة:

```text
pollen
camera
SFX
Whisper
```

---

# 204. Prototype 4

اختبار Storyboard كامل.

النتيجة:

```text
narrative synchronized motion graphic
```

---

# 205. Prototype 5

اختبار 5–10 صور متنوعة.

هدفه:

```text
generalization
```

---

# 206. Definition of Done — Extraction

Extraction تعتبر مكتملة عندما:

```text
[ ] all required motion objects identified
[ ] no critical object missing
[ ] masks pass quality gate
[ ] coordinates preserved
[ ] original preserved
[ ] background reconstructed where required
[ ] provenance saved
```

---

# 207. Definition of Done — Motion

```text
[ ] motion graph valid
[ ] no impossible dependency
[ ] primary hierarchy clear
[ ] secondary motion controlled
[ ] no random teleport
[ ] anticipation for key actions
[ ] reaction for key impacts
```

---

# 208. Definition of Done — Camera

```text
[ ] camera has explicit reason
[ ] target valid
[ ] no clipping
[ ] no nervous pans
[ ] motion supports story
```

---

# 209. Definition of Done — Audio

```text
[ ] Whisper complete
[ ] visual anchors mapped
[ ] impact aligned
[ ] SFX ducked
[ ] final mix valid
```

---

# 210. Definition of Done — Rendering

```text
[ ] 1920x1080
[ ] 30 FPS
[ ] no black frames
[ ] no blank frames
[ ] no missing assets
[ ] output decodes correctly
```

---

# 211. Definition of Done — Product

```text
[ ] user can preview
[ ] user can manually override
[ ] AI respects overrides
[ ] project can resume
[ ] artifacts reproducible
[ ] failures are inspectable
```

---

# 212. Final folder architecture

```text
image_to_animate/
│
├── core/
│   ├── agent/
│   │   ├── supervisor.py
│   │   ├── decision_state.py
│   │   ├── approval_gate.py
│   │   └── task_planner.py
│   │
│   ├── contracts/
│   │   ├── visual_manifest.py
│   │   ├── decomposition_plan.py
│   │   ├── narrative_map.py
│   │   ├── motion_graph.py
│   │   └── render_plan.py
│   │
│   ├── vision/
│   │   ├── adaptive_candidate_extractor.py
│   │   ├── semantic_detector.py
│   │   ├── segmentation_router.py
│   │   ├── sam_adapter.py
│   │   ├── grounding_adapter.py
│   │   ├── mask_refiner.py
│   │   ├── background_reconstructor.py
│   │   ├── decomposition_planner.py
│   │   └── visual_quality_gate.py
│   │
│   ├── semantics/
│   │   ├── scene_graph.py
│   │   ├── object_relationships.py
│   │   ├── motion_roles.py
│   │   └── semantic_registry.py
│   │
│   ├── narrative/
│   │   └── narrative_director.py
│   │
│   ├── motion_graphics/
│   │   ├── motion_graph.py
│   │   ├── motion_planner.py
│   │   ├── behavior_engine.py
│   │   ├── path_engine.py
│   │   ├── deformation_engine.py
│   │   ├── particle_engine.py
│   │   ├── transition_engine.py
│   │   ├── camera_choreographer.py
│   │   ├── motion_profiles.py
│   │   └── behaviors/
│   │
│   ├── scheduling/
│   │   └── constraint_scheduler.py
│   │
│   ├── research/
│   │   ├── tool_registry.py
│   │   ├── research_runner.py
│   │   ├── benchmark_runner.py
│   │   └── license_checker.py
│   │
│   └── qa/
│       ├── visual_qa.py
│       ├── motion_qa.py
│       ├── camera_qa.py
│       └── regression.py
│
├── production_engine/
│   ├── dynamic_section_engine.py
│   └── ...
│
├── research/
│   ├── reports/
│   ├── benchmarks/
│   └── tool_registry.json
│
├── experiments/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── golden/
│   └── performance/
│
├── docs/
│   ├── architecture/
│   ├── adr/
│   └── ai_reports/
│
└── config/
    └── motion_graphics.yaml
```

---

# 213. تسلسل التنفيذ الإلزامي النهائي

لا يتم القفز بين المراحل.

```text
PHASE 0
Repository Audit
       ↓
PHASE 1
Research & Tool Registry
       ↓
PHASE 2
Contracts
       ↓
PHASE 3
Visual Semantic Understanding
       ↓
PHASE 4
Minimum Sufficient Decomposition
       ↓
PHASE 5
Segmentation Router
       ↓
PHASE 6
Mask Refinement
       ↓
PHASE 7
Background Reconstruction
       ↓
PHASE 8
Rich Asset Graph
       ↓
PHASE 9
Narrative Mapping
       ↓
PHASE 10
Motion Graph
       ↓
PHASE 11
Motion Behavior Engine
       ↓
PHASE 12
Procedural Effects
       ↓
PHASE 13
Camera Choreography
       ↓
PHASE 14
Deterministic Scheduling
       ↓
PHASE 15
Renderer Integration
       ↓
PHASE 16
Audio/SFX Integration
       ↓
PHASE 17
Visual/Motion QA
       ↓
PHASE 18
Benchmark
       ↓
PHASE 19
Studio Integration
       ↓
PHASE 20
Production Hardening
```

---

# 214. شروط الانتقال بين المراحل

لا ينتقل Stage إلى الذي يليه إلا إذا:

```text
tests pass
AND
artifacts valid
AND
quality gate pass
AND
no blocking issue
```

وإذا كان القرار يحتاج مستخدمًا:

```text
WAIT
```

---

# 215. شكل موافقة المستخدم

يفضل:

```text
DECISION D-001

Decision:
Segmentation backend

Recommendation:
Grounding DINO → SAM 2.1

Alternatives:
SAM 3.1
Classical CV

Reason:
...
Risk:
...

Answer:
[ APPROVE ]
[ CHOOSE SAM 3.1 ]
[ RUN BENCHMARK ]
```

---

# 216. Change Management

أي تغيير مؤثر:

```text
Decision
→ ADR
→ implementation
→ tests
→ benchmark
→ acceptance
```

---

# 217. Release Levels

```text
Experimental
Beta
Production
```

## Experimental

قد يفشل.

## Beta

مستقر نسبيًا على benchmark.

## Production

كل gates ناجحة.

---

# 218. Final Product Behavior

عند إدخال:

```text
storyboard.png
script.txt
audio.wav
```

يجب أن يعمل:

```text
1. inspect assets
2. understand scene
3. map narrative
4. identify motion-worthy objects
5. determine decomposition
6. research if capability missing
7. ask blocking questions
8. extract required layers
9. reconstruct backgrounds
10. generate asset graph
11. generate motion graph
12. generate camera choreography
13. synchronize with audio
14. generate render plan
15. render preview
16. perform QA
17. ask user acceptance
18. render final
19. store artifacts
20. publish
```

---

# 219. تعريف النجاح الحقيقي

المشروع ناجح عندما يستطيع أخذ Storyboard جديد لم يره من قبل، ويقوم بالآتي:

```text
لا يعتمد على grid ثابت
لا يعتمد على عدد ثابت من العناصر
لا يفصل كل شيء
لا يحرّك كل شيء بنفس الطريقة
لا يستخدم fade/slide كحل افتراضي
لا يحتاج تدخلًا يدويًا لكل Layer
لا يفقد العناصر المهمة
لا يكسر التكوين الأصلي
لا يكسر وضع Whiteboard
```

وفي الوقت نفسه:

```text
يفهم العلاقات
يختار ما يحتاج فصلًا
يختار طريقة الاستخراج
يختار السلوك الحركي
يختار الكاميرا
يربط الحركة بالنص
يولد المؤثرات
يفحص الجودة
يسأل الإنسان عندما تكون هناك حالة غامضة
وينتظر الإجابة
```

---

# 220. فلسفة المشروع النهائية

الهدف ليس:

```text
AI Image Animator
```

بل:

```text
AI Motion Graphics Director
+
Computer Vision Layer Builder
+
Deterministic 2D Motion Engine
+
Cinematic Camera System
+
Narrative Synchronization System
+
Human-in-the-loop Studio
```

---

# 221. قاعدة أخيرة غير قابلة للتفاوض

**إذا لم نعرف لماذا يجب أن يتحرك العنصر، فلا نحركه.**

**إذا لم نعرف لماذا يجب فصله، فلا نفصله.**

**إذا كان الـAI غير واثق، لا يخمن.**

**إذا كان القرار مؤثرًا على architecture أو الجودة أو التكلفة أو الترخيص، يسأل وينتظر.**

**إذا كان الحساب حتميًا، لا نستخدم LLM لتنفيذه.**

**إذا كانت الحركة لا تخدم القصة، لا نضيفها لمجرد أن النظام قادر عليها.**

---

# 222. المراجع الرسمية البحثية المستخدمة في إعداد الخطة

## SAM 3 / SAM 3.1
https://github.com/facebookresearch/sam3

## SAM 2
https://github.com/facebookresearch/sam2

## Grounding DINO
https://github.com/IDEA-Research/GroundingDINO

## Grounded-SAM 2
https://github.com/IDEA-Research/Grounded-SAM-2

## Kornia
https://kornia.readthedocs.io/

## FFmpeg
https://ffmpeg.org/ffmpeg-filters.html

## PyAV
https://pyav.org/

## LaMa / Inpainting reference
https://github.com/advimman/lama

---

# 223. ملاحظات مرجعية من المشروع الحالي

الـpipeline الحالي يعتمد على:

```text
Adaptive Candidate Extraction
Visual Manifest
Narrative Visual Map
Final Render Plan
Demand Estimator
DynamicSectionEngine
Whisper synchronization
Camera planning
SFX generation
NVENC/FFmpeg rendering
```

ويجب أن تكون إضافة Motion Graphics **امتدادًا** لهذا التصميم لا استبدالًا كاملًا له.

كما أن الـNatural White-Gap extraction الحالي يمنع Mechanical Grid Slicing ويعتمد على projection/flood-fill/connected components/feathering/tight crop، ولذلك يجب الحفاظ عليه كمسار baseline للصور التي يستطيع التعامل معها بكفاءة.

---

# 224. أول مهمة يجب أن ينفذها وكيل البرمجة بعد قراءة هذا الملف

يجب ألا يبدأ بإنشاء:

```text
sam_adapter.py
```

ولا:

```text
motion_engine.py
```

مباشرة.

بل يجب أن يبدأ برسالة:

```text
PHASE 0 — REPOSITORY AUDIT

سأقوم أولًا بفحص المشروع الحالي.

سأحدد:
1. ما الموجود فعلًا.
2. ما يمكن إعادة استخدامه.
3. ما ينقص.
4. ما قد يتعارض مع Motion Graphics.
5. ما الذي يحتاج Research.
6. ما هي القرارات التي تحتاج موافقتك.

لن أعدل كودًا قبل اكتمال هذا التدقيق.
```

ثم:

```text
WAIT FOR USER
```

بعد إكمال الـAudit، ينتقل إلى:

```text
PHASE 1 — RESEARCH
```

ثم يعرض:

```text
Tool Candidates
Benchmark Plan
License Notes
Recommendation
Blocking Decisions
```

ثم:

```text
WAIT FOR USER
```

ثم يبدأ التنفيذ.

---

# 225. المخرج النهائي للمشروع

بعد اكتمال كل المراحل، يجب أن يكون لدينا:

```text
Image-to-Animate
│
├── Whiteboard Mode
│
├── Motion Graphics Mode
│
└── Hybrid Mode
```

والـMotion Graphics Mode قادر على:

```text
Image
 ↓
Semantic Scene
 ↓
Required Decomposition
 ↓
Independent Layers
 ↓
Procedural Effects
 ↓
Motion Graph
 ↓
Camera Choreography
 ↓
Narrative Timing
 ↓
Deterministic Render
 ↓
Professional Video
```

مع:

```text
AI suggestions
AI research
AI questions
Human approval
Manual override
QA
Benchmarks
Cache
Resume
Versioning
```

---

# 226. معيار الجودة النهائي

لا نقيس النجاح فقط بأن:

```text
الفيديو يعمل
```

بل:

```text
Narrative Quality
Visual Fidelity
Motion Naturalness
Camera Quality
Timing Accuracy
Layer Integrity
Asset Fidelity
Performance
Reproducibility
Editability
```

والهدف النهائي هو أن تكون الحركة **مبررة بصريًا وسرديًا، سلسة، متنوعة، قابلة للتعديل، ومتناسقة مع الصورة الأصلية والصوت**.

---

# 227. END STATE

```text
                         ┌───────────────────────┐
                         │       USER            │
                         │ Storyboard + Script   │
                         │ Audio + Decisions     │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │      AI SUPERVISOR    │
                         └───────────┬───────────┘
                                     │
             ┌───────────────────────┼───────────────────────┐
             │                       │                       │
             ▼                       ▼                       ▼
       Vision Research          Motion Direction        Code/QA
             │                       │                       │
             └───────────────────────┼───────────────────────┘
                                     ▼
                           Visual + Motion Contracts
                                     │
                                     ▼
                               Asset Graph
                                     │
                                     ▼
                               Motion Graph
                                     │
                                     ▼
                              Camera Graph
                                     │
                                     ▼
                              Render Plan
                                     │
                                     ▼
                         DynamicSectionEngine
                                     │
                                     ▼
                                  VIDEO
```

**هذه الوثيقة هي Master Specification. لا تعتبر أي Tool أو Model أو Library قرارًا نهائيًا لمجرد وجوده في هذه الخطة؛ القرار النهائي يجب أن يمر عبر Research → Benchmark → License Review → Approval.**

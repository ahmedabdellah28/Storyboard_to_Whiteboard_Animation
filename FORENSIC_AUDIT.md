# تقرير التدقيق الجنائي للبكسلات والمعمارية الهندسية الشاملة
# Forensic Pixel Audit & V3 Engineering Architecture Report

**تاريخ التدقيق:** 2026-08-29  
**الدور الهندسي:** Senior Software Architect + Computer Vision Engineer + 2D Animation Engine Engineer  
**المبدأ المعماري الصارم:**  
$$\mathbf{SOURCE\ IMAGE = SOURCE\ OF\ TRUTH}$$
$$\text{Analysis may be imperfect. Rendering must NEVER destroy source information.}$$

---

## 1. ملخص تنفيذي ونتائج القياسات الرقمية (Executive Summary & Forensic Data)

تم إجراء تدقيق جنائي رقمي (*Forensic Pixel Audit*) على مسار معالجة الصور ومقارنته بالبكسلات الحقيقية الأصلية عبر عدة صور اختبارية في المستودع. أظهرت القياسات الرياضية بالأرقام ما يلي:

### جدول القياسات الجنائية الموثقة (Empirical Forensic Matrix)

| اسم صورة الاختبار | دقة المصدر | الألوان الأصلية | ألوان الـ Quantized | نسبة البكسلات المفقودة (Residual) | عدد البكسلات المختلفة في الإطار النهائي | خطأ البكسلات (MAE) | خطأ التربيع (MSE) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`Man_unlocking_glowing_padlock`** (القصة المصورة التخطيطية) | $1024 \times 571$ | **175,366** لوناً | 16 لوناً | **45.42%** | **183,017** بكسل (19.86%) | **18.42** | **3,053.77** |
| **`Man_interacting_with_magical_obj`** (رسم غني بالتظليل والتوهج) | $1376 \times 768$ | **61,057** لوناً | 16 لوناً | **17.96%** | **261,282** بكسل (28.35%) | **23.51** | **3,503.06** |
| **`Storyboard_showing_Zaid_building`** (لوحات الشخصية الست) | $1376 \times 768$ | **54,337** لوناً | 16 لوناً | **78.20%** | **102,880** بكسل (11.16%) | **14.22** | **2,514.24** |
| **`Man_looking_at_floating_padlock`** (شخص وقفل منفرد) | $1376 \times 768$ | **30,717** لوناً | 16 لوناً | **15.33%** | **54,090** بكسل (5.87%) | **5.87** | **940.58** |

> [!CAUTION]
> **الحقيقة الرقمية الصادمة:**  
> في المسار الحالي، ما بين **15.3% إلى 78.2% من مساحة الصورة الأصلية** تفشل في الدخول إلى أي قناع رسمي (Stroke أو Region)، ويتم استبدالها بلون أبيض صناعي أو مسحها في الإطار النهائي! كما يتم ضغط ما يصل إلى **175,000 لون حقيقي وتدرج وظل** إلى **16 لوناً مصمتة فقط**!

---

## 2. مقارنة تفصيلية بين الإصدار القديم والمحرك الحالي (Old vs Current Comparison)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    OLD PIPELINE (sketchApi.py)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Input Image BGR (Immutable).                                             │
│ 2. CLAHE + Adaptive Gaussian Thresholding لتوليد خارطة كتل ثنائية فقط.      │
│ 3. Grid-Tile Nearest Neighbor Spatial Traversal لكشف البلاطات.              │
│ 4. Rendering: رسم اليد والقلم فوق الصورة الأصلية تدريجياً.                 │
│ 5. النتيجة: في نهاية الفيديو تظهر الصورة الأصلية 100% بكامل بكسلاتها وألوانها. │
└─────────────────────────────────────────────────────────────────────────────┘
                                      VS
┌─────────────────────────────────────────────────────────────────────────────┐
│                   CURRENT ENGINE (kivy/engine/)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Input Image -> Resize with Pad.                                          │
│ 2. Color Quantization: K-Means (K=16..32) وضغط الألوان وافتراض خلفية بيضاء.  │
│ 3. EdgeExtractor: Canny + Open + Min Length (حذف الخطوط < 12px والنقاط).    │
│ 4. StrokeClassifier: حذف الـ MICRO_DETAIL < 18px في الوضع الافتراضي.        │
│ 5. RegionExtractor: حذف المساحات الفاتحة باعتبارها "خلفية بيضاء".            │
│ 6. ObjectGrouping: تشتيت الكائنات إلى عشرات الكتل (40 Character).          │
│ 7. Renderer: صب ألوان K-Means فوق كانفاس أبيض فارغ.                        │
│ 8. النتيجة: فقدان بين 15% إلى 78% من بكسلات وتدرجات وملامح الصورة الأصلية!    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. التحليل الجذري الموثق بالملفات والأسطر البرمجية (Root Cause Analysis)

### 3.1. أول نقطة يبدأ عندها فقدان المعلومات (First Point of Loss)
* **الملف:** `kivy/engine/processing/color_processor.py` (السطر 34 و 80).
* **الكود:** `K = max(4, min(32, config.color_palette_size))` و `background_color = (255, 255, 255)`.
* **الخلل:** يتم استبدال 175,000 لون حقيقي بـ 16-32 لوناً، وفرض خلفية بيضاء صناعية تلغي الخلفيات الحقيقية الملونة والداكنة.

### 3.2. حذف الملامح والنقاط الدقيقة (Micro Details & Thin Line Deletion)
* **الملف:** `kivy/engine/processing/edge_extractor.py` (الأسطر 29، 39، 61، 98).
* **الكود:** `min_len = max(config.min_stroke_length, 12.0)` و `cv2.morphologyEx(..., cv2.MORPH_OPEN, kernel_2)` و `occupied_grid > 4`.
* **الخلل:** أي خط أو نقطة طولها أقل من 12 بكسل (بؤبؤ العين، الملامح، النقاط، الرموز، الحروف، التظليل) تُحذف نهائياً، كما يمسح `MORPH_OPEN` أي تفصيل حجمه 1-2 بكسل!

### 3.3. الإسقاط التلقائي للخطوط الدقيقة في الوضع الافتراضي
* **الملف:** `kivy/engine/processing/stroke_classifier.py` (الأسطر 86-90).
* **الكود:** `elif config.detail_level == "MEDIUM": if s.stroke_type != StrokeType.MICRO_DETAIL: classified.append(s)`.
* **الخلل:** في الوضع المتوسط الافتراضي، يتم إسقاط جميع الخطوط المصنفة كـ `MICRO_DETAIL` التي يقل طولها عن 18 بكسل!

### 3.4. حذف الملابس والمساحات البيضاء الداخلية
* **الملف:** `kivy/engine/processing/region_extractor.py` (الأسطر 54-55).
* **الكود:** `if is_bg_like and (area > 0.08 * (w * h) ...): continue`.
* **الخلل:** اعتبار أي مساحة لونها يقترب من الأبيض "خلفية فارغة" وتجاهلها، مما يمسح الملابس البيضاء أو الأوراق داخل الرسم.

### 3.5. انفجار عدد الكائنات (مشكلة الـ 40 شخصية)
* **الملف:** `kivy/engine/planning/object_grouping.py` (الأسطر 84، 152، 169).
* **الكود:** `min_cluster_area = 200` و `name = f"Character_{idx+1}"` و شرط المسافة `80px`.
* **الخلل:** اعتبار أي رقعة فارغة بمساحة $14 \times 14$ بكسل كائناً قائماً بذاته وتسميته `Character_N` حتى مع $\text{strokes}=0$، وفشل دمج بقع الزوايا لأنها تبعد أكثر من 80px عن المركز.

### 3.6. تسطيح القوائم في القصة المصورة (Storyboard Flattening)
* **الملف:** `kivy/ui/screens/scene_screen.py` (السطر 138).
* **الكود:** `all_objects.extend([o for o in scene.objects if not o.is_frame])`.
* **الخلل:** دمج كائنات كافة اللوحات في قائمة خطية واحدة، مما أفقد القصة المصورة تسلسلها الهرمي.

---

## 4. معمارية المستوى المزدوج المقترحة (Dual-Plane V3 Architecture)

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        IMMUTABLE SOURCE IMAGE                          │
│                 (100% TrueColor, Uncompressed BGR)                     │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
       ┌────────────────────────┐       ┌────────────────────────┐
       │     ANALYSIS PLANE     │       │    RENDERING PLANE     │
       │   (Vector & Topology)  │       │     (Pixel-Exact)      │
       ├────────────────────────┤       ├────────────────────────┤
       │ • Multi-scale Contours │       │ • Exact Source Pixels  │
       │ • Adaptive Canny/Sobel │       │ • True Texture/Shading │
       │ • Spatial Traversal    │       │ • True Gradients & Glow│
       │ • Timing & Easing Order│       │ • Real Background Tint │
       └────────────┬───────────┘       └────────────┬───────────┘
                    │                                │
                    └───────────────┬────────────────┘
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │             PROGRESSIVE TRUECOLOR COMPOSITING           │
       │   canvas[revealed_mask] = source_image[revealed_mask]   │
       │   + Exact Stroke Rendering with Original Source Chroma  │
       │   + UNIVERSAL RESIDUAL FALLBACK (Coverage = 100%)       │
       └─────────────────────────────────────────────────────────┘
```

---

## 5. استراتيجية الإصلاح الأدنى والآمن (Minimal Safe Fix Strategy)

1. **اعتماد `source_image` كمصدر وحيد للبكسلات في التصيير:**
   * تعديل `FillAnimator` و `Renderer` ليقوما حصرياً بكشف البكسلات الحقيقية:
     $$\text{canvas}[\text{mask} > 0] = \text{source\_image}[\text{mask} > 0]$$
2. **إضافة طبقة المتبقيات الشاملة (Universal Residual Layer):**
   * حساب قناع البكسلات غير المصنفة:
     $$\text{residual\_mask} = \neg (\text{Union of all stroke \& region masks})$$
   * كشف المتبقيات تدريجياً في طبقة الأساس ليصبح تطابق الإطار النهائي مع المصدر مساوياً لـ **100%** ($\text{MAE} \approx 0.00$).
3. **التحول إلى العتبات التكيفية (Adaptive Thresholds):**
   * استبدال الأرقام الثابتة (`min_len=12`, `area=200`) بنسب ديناميكية تعتمد على أبعاد الصورة وكثافة الحواف.
   * تصنيف الخطوط القصيرة كـ `MICRO_DETAIL` ورسمها في مرحلة التفاصيل دون حذفها.
4. **التجميع الهرمي للكائنات (Hierarchical Grouping):**
   * الكائن الرئيسي يشترط وجود خطوط هيكلية ($\text{strokes} \ge 10$) ومساحة حقيقية.
   * امتصاص الهالات والدرع والتأثيرات والتظليل الملاصق داخل الكائن الأقرب.
   * استبعاد الفراغات البيضاء واعتبارها خلفية موحدة.
5. **الفصل التام بين اللوحات في الـ Storyboard:**
   * عزل خطوط الإطار الخارجي (`is_frame=True`).
   * الحفاظ على الهيكل الهرمي: `Project -> Scenes -> Objects` بدون أي Flattening.

---

## 6. حصر الملفات المستهدفة والمحمية (File Modification Scope)

### الملفات التي سيتم تعديلها (Files to Modify):
1. `kivy/engine/core/project.py`
2. `kivy/engine/core/scene.py`
3. `kivy/engine/core/stroke.py`
4. `kivy/engine/core/region.py`
5. `kivy/engine/processing/color_processor.py`
6. `kivy/engine/processing/edge_extractor.py`
7. `kivy/engine/processing/stroke_classifier.py`
8. `kivy/engine/processing/region_extractor.py`
9. `kivy/engine/processing/panel_detector.py`
10. `kivy/engine/processing/image_processor.py`
11. `kivy/engine/planning/object_grouping.py`
12. `kivy/engine/planning/sequence_planner.py`
13. `kivy/engine/planning/shot_planner.py`
14. `kivy/engine/animation/fill_animator.py`
15. `kivy/engine/animation/stroke_animator.py`
16. `kivy/engine/render/renderer.py`
17. `kivy/engine/debug/preview.py`
18. `kivy/ui/screens/scene_screen.py`
19. `kivy/ui/state/project_state.py`
20. `kivy/ui/widgets/object_list.py` & `object_card.py`
21. `kivy/main.py`

### الملفات المحظور تعديلها تماماً (Files That Must NOT Be Modified):
1. `kivy/sketchApi.py` (المرجع التاريخي والمعيار الأساسي).
2. `kivy/engine/video/encoder.py` (غلاف التشفير النظيف لـ PyAV / NVENC).
3. `kivy/engine/camera/camera.py` (كلاس تحويل مصفوفات العرض والـ Viewport).
4. `kivy/engine/camera/camera_animator.py` (كلاس الاستيفاء الحركي للكاميرا).
5. `kivy/engine/animation/easing.py` (معادلات التنعيم الرياضية).
6. `kivy/engine/animation/drawing_order.py` (خوارزميات المسح المكاني).
7. `kivy/ui/screens/home_screen.py`, `loading_screen.py`, `theme.py`, `settings_dialog.py`.
8. ملفات الحزم والبناء (`buildozer.spec`, `dlDesktop.spec`, `img2sketch.iss`, `recipes/`).

---

## 7. خطة البوابات المرحلية والتنفيذ (Implementation Gates)

* **GATE 0: Forensic Audit & Test Baseline (مكتملة الآن)**
* **GATE 1: Pixel Preservation & Dual-Plane Renderer (`renderer.py`, `fill_animator.py`, `image_processor.py`)**
  * تحقيق $\text{Coverage} \approx 100\%$ و $\text{MAE} \le 0.05$ عبر الـ Residual Fallback.
* **GATE 2: Detail & Stroke Preservation (`edge_extractor.py`, `stroke_classifier.py`)**
  * إلغاء حذف الـ `MICRO_DETAIL` والتخلص من فلاتر الحذف القسري للخطوط الدقيقة.
* **GATE 3: Color & Background Fidelity (`color_processor.py`, `region_extractor.py`)**
  * إزالة سقف الـ 32 لوناً، الحفاظ على المساحات الفاتحة، واكتشاف الخلفية الحقيقية مكانياً.
* **GATE 4: Hierarchical Object Grouping (`object_grouping.py`)**
  * القضاء على خطأ الـ 40 شخصية وتجميع التأثيرات والملامح ضمن الكائن الأساسي.
* **GATE 5: Universal Storyboard & Panel Isolation (`panel_detector.py`)**
  * عزل خطوط الإطارات، استبعاد اللوحات الفارغة، ومنع الـ Flattening بين المشاهد.
* **GATE 6: Sequence Planning & Cinematic Camera (`sequence_planner.py`, `shot_planner.py`)**
* **GATE 7: Renderer ROI & Performance Optimization (Bounding-Box ROI, Memoization)**
* **GATE 8: Studio UI & Drag & Drop Reordering (`scene_screen.py`, `object_list.py`)**
* **GATE 9: Full Regression Matrix Execution (17 اختباراً شاملاً)**

---

> [!IMPORTANT]
> **حالة التوقف التام:**  
> تم حفظ هذا التقرير الجنائي في [FORENSIC_AUDIT.md](file:///e:/image_to_animate/FORENSIC_AUDIT.md).  
> **لم يتم إجراء أي تعديل على كود الإنتاج.**  
> أنا بانتظار إشارتك وموافقتك الصريحة لبدء تنفيذ **GATE 1 (Pixel Preservation & Dual-Plane Renderer)**.

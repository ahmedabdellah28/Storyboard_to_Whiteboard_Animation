# 🏗️ هيكل المحرك — Engine Architecture

يُمثّل مجلد `kivy/engine/` قلب المشروع. هذا الملف يوثّق كل وحدة (Module) والعلاقات بينها.

---

## 📐 المخطط المعماري

```
┌─────────────────────────────────────────────────────────────────────┐
│                         main.py (KivyMD App)                        │
│                      SketchAnimationApp v0.7.0                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌───────────┐   ┌────────────┐  ┌───────────┐
     │ UI Layer  │   │  Services  │  │ Licensing  │
     │ (Screens) │   │ (Workflow) │  │  (Guard)   │
     └─────┬─────┘   └──────┬─────┘  └───────────┘
           │                │
           └────────┬───────┘
                    ▼
    ┌───────────────────────────────────┐
    │        engine/ (Core Engine)       │
    ├───────────────────────────────────┤
    │                                   │
    │  ┌─────────┐    ┌──────────────┐ │
    │  │  core/   │    │ processing/  │ │
    │  │ (Models) │◄───│ (Analysis)   │ │
    │  └────┬────┘    └──────┬───────┘ │
    │       │                │          │
    │       ▼                ▼          │
    │  ┌──────────┐   ┌───────────┐   │
    │  │planning/ │   │ animation/│   │
    │  │(Sequence)│   │ (Timing)  │   │
    │  └────┬─────┘   └─────┬─────┘   │
    │       │               │          │
    │       └───────┬───────┘          │
    │               ▼                  │
    │        ┌────────────┐            │
    │        │   render/   │            │
    │        │ (Drawing)   │            │
    │        └──────┬─────┘            │
    │               ▼                  │
    │        ┌────────────┐            │
    │        │   camera/   │            │
    │        │(Cinematics) │            │
    │        └──────┬─────┘            │
    │               ▼                  │
    │        ┌────────────┐            │
    │        │   video/    │            │
    │        │ (Encoding)  │            │
    │        └────────────┘            │
    └───────────────────────────────────┘
```

---

## 📦 engine/core/ — النماذج الأساسية (Data Models)

هذه الطبقة تحتوي على هياكل البيانات الأساسية التي تتشاركها جميع الوحدات.

### `scene.py`
| الكلاس | الوصف |
|--------|-------|
| `SceneConfig` | إعدادات المشهد الكاملة (الأبعاد، FPS، سرعة الرسم، مستوى التفصيل، إعدادات الكاميرا، اليد، إلخ) |
| `SceneObject` | كائن واحد داخل المشهد (يحتوي على strokes + fills + details + bbox) |
| `Scene` | المشهد الكامل: مجموعة كائنات + صورة المصدر + أبعاد الكانفاس |

### `stroke.py`
| الكلاس | الوصف |
|--------|-------|
| `StrokeType` | تصنيف الخطوط: `OUTER_OUTLINE`, `INTERNAL_DETAIL`, `COLOR_BOUNDARY`, `MICRO_DETAIL`, `FRAME_STROKE` |
| `Stroke` | خط رسم واحد: مصفوفة نقاط (N,2) + لون + عرض + طول + bbox |

### `region.py`
| الكلاس | الوصف |
|--------|-------|
| `FillMode` | طريقة التعبئة: `TOP_TO_BOTTOM`, `LEFT_TO_RIGHT`, `CENTER_OUT`, `FOLLOW_OUTLINE` |
| `ColorRegion` | منطقة لون واحدة: لون BGR + قناع + مساحة + bbox (مُحسّنة للذاكرة بتخزين القص فقط) |

### `timeline.py`
| الكلاس | الوصف |
|--------|-------|
| `Keyframe` | إطار مفتاحي: طابع زمني + قيمة + نوع التخفيف (easing) |
| `CameraShot` | لقطة كاميرا: وقت البداية/النهاية + هدف التركيز + zoom |
| `StrokeEvent` | حدث رسم خط: فترة زمنية + الخط المرتبط |
| `FillEvent` | حدث تعبئة لون: فترة زمنية + المنطقة المرتبطة |
| `Timeline` | الخط الزمني الكامل: مجموعة أحداث الرسم + التعبئة + مدة الإجمالية |

### `project.py`
| الكلاس | الوصف |
|--------|-------|
| `StructureType` | نوع الهيكل: `STORYBOARD`, `SINGLE_SCENE`, `SINGLE_FRAMED_SCENE`, إلخ |
| `PanelStructure` | لوحة واحدة: bbox + interior_bbox + border_mask + بيانات التحليل |
| `Project` | المشروع الكامل: نوع الهيكل + قائمة اللوحات + قائمة المشاهد |

### `image_io.py`
- `read_image_unicode(path)` — قراءة الصور بمسارات Unicode (عربية/يابانية/إلخ)

---

## 🔬 engine/processing/ — معالجة الصور (Image Analysis)

تحليل الصورة المدخلة واستخراج العناصر القابلة للرسم.

### `image_processor.py` — المعالج الرئيسي
```python
ImageProcessor.process(image_bgr, config, progress_cb) → Project
```
- خط أنابيب عالمي V3: يكتشف تلقائياً نوع الصورة (Storyboard / Single Scene)
- يدعم اللوحات المخصصة عبر `custom_panels`
- يوجه المعالجة إلى `WhiteboardProcessor` أو `PanelDetector` حسب الحاجة

### `panel_detector.py` — كاشف اللوحات
- `PanelDetector.detect(image_bgr)` — يكتشف اللوحات المتعددة في صور Storyboard
- `StoryboardConfidenceAnalyzer` — يحلل 10 معايير هيكلية لتحديد درجة الثقة (≥0.80 للقبول)
- يدعم الشبكات المنتظمة M×N والتخطيطات غير المنتظمة

### `whiteboard_processor.py` — معالج السبورة
- متخصص في الأوراق التعليمية (نصوص + رياضيات + رسومات + شخصيات)
- يستخدم المحرك المزدوج (Dual Engine)

### `dynamic_border_detector.py`
- `DynamicBorderDetector.detect_and_trim_panel_border(crop)` — كشف وإزالة حدود اللوحات
- يعالج الحدود السوداء والملونة والجزئية

### `edge_extractor.py` — مستخرج الحواف
- استخراج حواف Canny + تعزيز بـ Bilateral Filter
- تصفية الضوضاء والخطوط الصغيرة

### `stroke_classifier.py` — مصنف الخطوط
- يصنف الـ contours إلى أنواع StrokeType حسب الحجم والموقع والشكل

### `color_processor.py` — معالج الألوان
- K-Means تكميم الألوان (palette_size configurable)
- استخراج مناطق الألوان المنفصلة

### `region_extractor.py` — مستخرج المناطق
- يحول مناطق الألوان إلى كائنات `ColorRegion` مع أقنعة

### `dynamic_decomposition.py`
- تفكيك ديناميكي للصورة إلى مكونات
- `detect_panels_dynamically()` + `suppress_outer_frame_borders()`

### الوحدات المعيارية (Modular Pipeline)
| الملف | الوصف |
|-------|-------|
| `m1_panel_extractor.py` | `DynamicPanelExtractor` — استخراج اللوحات |
| `m2_layer_splitter.py` | `MethodALayerSplitter` — فصل الطبقات (نص / رسم) |
| `m3_text_line_auditor.py` | `TextLineAuditor` — تحليل وتدقيق أسطر النص |

---

## 🎨 engine/render/ — محركات التصيير (Rendering Engines)

### `renderer.py` — المصيّر V3.1
```python
Renderer(scene, timeline, camera, camera_shots, camera_animator)
```
**القواعد الذهبية:**
1. الصورة المصدر = مصدر الحقيقة الوحيد
2. لا يظهر أي بكسل قبل حدث رسمه
3. الكانفاس يبدأ فارغاً 100%
4. اليد + القلم متزامنان مع المسار
5. لا كشف مسبق للبقايا
6. لا رسم لإطارات اللوحات
7. **صفر فقدان في التفاصيل**

### `concentric_engine.py` — المحرك المداري
```python
render_concentric_orbital_whiteboard(image_bgr, ...) → output_path
```
- مسارات مدارية 360° متحدة المركز (Gapless Orbital Paths)
- `build_gapless_orbital_path()` — بناء مسار الرسم بدون فجوات
- `extract_storyboard_panels_and_entities()` — استخراج اللوحات والكيانات
- دمج علامات الترقيم القريبة (`merge_nearby_punctuation`)

### `deep_pipeline_engine.py` — المحرك العميق السينمائي
```python
render_deep_storyboard_pipeline(image_bgr, ...) → output_path
```
- **6 مراحل**: تحليل → تفكيك → استخراج النص → ترتيب الرسم → تصيير → تصدير
- كاميرا سينمائية مع Smootherstep (6t⁵ - 15t⁴ + 10t³)
- محرك خط عربي RTL (هياكل عظمية مورفولوجية)
- دعم 4K UHD (3840×2160)

### `hand_compositor.py` + `hand_overlay.py` — تركيب اليد
- `load_hand_asset_bgra()` — تحميل صورة اليد بقناة ألفا
- `composite_hand_on_canvas_fast()` — تركيب سريع بنقطة PEN_TIP
- `HandOverlay` — نظام يد متقدم مع إمالة ديناميكية

### `viewport_transform.py`
- `render_camera_viewport()` — تحويل إحداثيات الكانفاس إلى viewport الكاميرا

---

## 🎬 engine/animation/ — نظام التحريك

### `drawing_order.py`
```python
DrawingOrder.build_timeline(scene) → Timeline
```
- ترتيب الرسم: `AUTO`, `TOP_TO_BOTTOM`, `LEFT_TO_RIGHT`, `CENTER_OUT`, `SPATIAL`
- الترتيب الداخلي: Outline → Details → Color Boundaries → Fills → Micro Details
- مدة طبيعية متناسبة مع الطول والمساحة

### `stroke_animator.py`
- تحريك تدريجي لنقاط الخط عبر الزمن

### `fill_animator.py`
- تحريك تعبئة المناطق اللونية (FOLLOW_OUTLINE / TOP_TO_BOTTOM / إلخ)

### `easing.py`
- منحنيات التخفيف: `linear`, `ease_in`, `ease_out`, `ease_in_out`

---

## 🎥 engine/camera/ — نظام الكاميرا

### `camera.py`
| الكلاس | الوصف |
|--------|-------|
| `CameraState` | حالة الكاميرا: x, y, zoom, rotation |
| `Camera` | الكاميرا الافتراضية: تحويل الكانفاس → viewport مع zoom + rotation |

### `camera_animator.py`
- `CameraAnimator` — تحريك سلس بين لقطات الكاميرا عبر interpolation

---

## 📼 engine/video/ — ترميز الفيديو

### `encoder.py`
```python
VideoEncoder(output_path, width, height, fps, crf)
```
- H.264 عبر PyAV (أساسي) مع fallback إلى OpenCV VideoWriter
- اكتشاف تلقائي لـ NVENC (تسريع GPU)
- ضغط CRF قابل للتعديل (افتراضي: 20)

---

## 📋 engine/planning/ — تخطيط المشاهد

### `storyboard_planner.py`
```python
StoryboardPlanner.build_master_storyboard_scene(project, config) → (Scene, Timeline, CameraShots)
```
- بناء مشهد رئيسي موحد لجميع اللوحات
- الكاميرا تتنقل: Panel 1 → 2 → 3 → ... → Master Reveal

### `sequence_planner.py`
- ترتيب الكائنات في تسلسل الرسم

### `shot_planner.py`
- تخطيط لقطات الكاميرا لكل كائن/لوحة

### `object_grouping.py`
- `MajorObjectGrouper` — تجميع العناصر الصغيرة في مجموعات كبيرة ذات معنى

---

## 🖥️ UI Layer — طبقة الواجهة

### `ui/screens/`
| الشاشة | الوصف |
|--------|-------|
| `HomeScreen` | الشاشة الرئيسية: رفع الصورة أو اختيار المجلد |
| `LoadingScreen` | شاشة التحميل مع شريط تقدم |
| `GridSetupScreen` | إعداد شبكة اللوحات يدوياً |
| `SceneScreen` | عرض المشهد ومعاينة الأنيميشن |

### `ui/services/`
| الخدمة | الوصف |
|--------|-------|
| `SettingsRepository` | حفظ/تحميل الإعدادات |
| `NativeDialogService` | نوافذ حوار النظام الأصلية |
| `AnalysisWorkflowService` | سير عمل تحليل الصورة |
| `RenderWorkflowService` | سير عمل التصيير والتصدير |

### `ui/state/project_state.py`
- `ProjectState` + `AppPhase` — إدارة حالة التطبيق

### `ui/theme.py`
- `Theme` — سمة التطبيق (ألوان، خطوط)

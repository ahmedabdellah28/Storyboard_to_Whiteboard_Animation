# 🧪 خط الأنابيب — كيف تتحول الصورة إلى فيديو

هذا الملف يشرح خطوة بخطوة كيف يعمل المحرك لتحويل صورة ثابتة إلى فيديو أنيميشن.

---

## 📊 المخطط الانسيابي

```
 الصورة المدخلة (JPG/PNG)
         │
         ▼
 ┌───────────────────────┐
 │   1. تحليل الهيكل     │  ImageProcessor / PanelDetector
 │   (Structural Analysis)│  → هل هي Storyboard أم Single Scene؟
 └──────────┬────────────┘
            │
     ┌──────┴──────┐
     ▼             ▼
 Storyboard    Single Scene
 (لوحات       (صورة واحدة)
  متعددة)         │
     │             │
     ▼             ▼
 ┌─────────────────────────┐
 │  2. استخراج اللوحات     │  DynamicPanelExtractor (M1)
 │  (Panel Extraction)     │  → bbox, interior, borders
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │  3. فصل الطبقات        │  MethodALayerSplitter (M2)
 │  (Layer Splitting)      │  → نص / رسومات / خلفية
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │  4. استخراج العناصر     │  EdgeExtractor + StrokeClassifier
 │  (Entity Extraction)    │  + ColorProcessor + RegionExtractor
 │                         │  → Strokes + ColorRegions + SceneObjects
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │  5. تحليل النص          │  TextLineAuditor (M3)
 │  (Text Analysis)        │  → أسطر النص RTL/LTR
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │  6. ترتيب الرسم        │  DrawingOrder / SequencePlanner
 │  (Drawing Sequence)     │  → Timeline (StrokeEvents + FillEvents)
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │  7. تخطيط الكاميرا     │  ShotPlanner / StoryboardPlanner
 │  (Camera Planning)      │  → CameraShots + Establishing + Outro
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │  8. التصيير             │  Renderer (V3.1)
 │  (Frame-by-Frame Render)│  → كانفاس أبيض → كشف تدريجي
 │                         │  + تركيب اليد + viewport الكاميرا
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │  9. ترميز الفيديو      │  VideoEncoder (PyAV H.264)
 │  (Video Encoding)       │  → MP4 output
 └─────────────────────────┘
```

---

## 📝 شرح تفصيلي لكل مرحلة

### المرحلة 1: تحليل الهيكل
```python
# في ImageProcessor.process()
detected_project = PanelDetector.detect(image_bgr)
is_storyboard = detected_project.structure_type.is_storyboard and len(detected_project.panels) >= 2
```
- يستخدم `StoryboardConfidenceAnalyzer` مع 10 معايير
- عتبة الثقة: **0.80** للقبول كـ Storyboard
- يفحص: عدد المستطيلات، تشابه الأبعاد، التباعد، الشبكة، الحدود

### المرحلة 2: استخراج اللوحات
- **Storyboard**: يقطع الصورة إلى لوحات فردية مع حدود داخلية آمنة
- **Single Scene**: يعامل الصورة الكاملة كلوحة واحدة
- `DynamicBorderDetector` يكتشف ويزيل حدود اللوحات تلقائياً

### المرحلة 3: فصل الطبقات
```python
splitter = MethodALayerSplitter()
text_mask, graphics_mask = splitter.split(panel_image)
```
- يفصل النص عن الرسومات باستخدام تقنيات مورفولوجية
- يحدد مناطق النص (عادةً أحرف صغيرة متكررة) vs الرسومات (أشكال كبيرة)

### المرحلة 4: استخراج العناصر
1. **الحواف**: Canny Edge Detection مع تصفية ثنائية
2. **الخطوط**: تحويل Contours إلى `Stroke` objects مع تصنيف:
   - `OUTER_OUTLINE` — الخطوط الخارجية الكبيرة
   - `INTERNAL_DETAIL` — التفاصيل الداخلية
   - `COLOR_BOUNDARY` — حدود مناطق الألوان
   - `MICRO_DETAIL` — تفاصيل دقيقة
   - `FRAME_STROKE` — إطارات اللوحات (تُستبعد من الرسم)
3. **الألوان**: K-Means quantization → `ColorRegion` objects
4. **التجميع**: `MajorObjectGrouper` يجمع العناصر في كائنات ذات معنى

### المرحلة 5: تحليل النص
```python
auditor = TextLineAuditor()
text_lines = auditor.audit(text_mask, panel_image)
```
- يكتشف أسطر النص ويحدد اتجاهها (RTL للعربية / LTR)
- يستخرج هياكل عظمية مورفولوجية لمحاكاة الكتابة اليدوية

### المرحلة 6: ترتيب الرسم
```python
timeline = DrawingOrder.build_timeline(scene)
```
أوضاع الترتيب المتاحة:

| الوضع | الوصف |
|-------|-------|
| `AUTO` | ترتيب ذكي تلقائي |
| `TOP_TO_BOTTOM` | من الأعلى إلى الأسفل |
| `LEFT_TO_RIGHT` | من اليسار إلى اليمين |
| `CENTER_OUT` | من المركز إلى الخارج |
| `SPATIAL` | حسب القرب المكاني |

**الترتيب الداخلي لكل كائن:**
1. الخطوط الخارجية (الأكبر أولاً)
2. التفاصيل الداخلية (من الأعلى إلى الأسفل)
3. حدود الألوان
4. التعبئات اللونية (الأكبر أولاً)
5. التفاصيل الدقيقة

### المرحلة 7: تخطيط الكاميرا

**لـ Storyboard:**
```
Establishing Wide Shot → Panel 1 Focus → Panel 2 Focus → ... → Grand Master Outro Reveal
```

**حركات الكاميرا:**
| الحركة | الوصف |
|--------|-------|
| Focus Zoom | تكبير 1.40x على اللوحة الحالية |
| Parallax Pullback | تصغير 1.10x أثناء الانتقال |
| Banking Tilt | إمالة ±1.4° أثناء التحرك |
| Smootherstep | منحنى 6t⁵ - 15t⁴ + 10t³ للسلاسة |

### المرحلة 8: التصيير
```python
# إطار بإطار (30 FPS افتراضياً)
for frame_idx in range(total_frames):
    t = frame_idx / fps
    
    # 1. تحديث الكانفاس: كشف البكسلات المجدولة في الوقت t
    # 2. تركيب اليد: وضع يد الرسم عند نقطة القلم الحالية
    # 3. تطبيق الكاميرا: warpAffine للـ viewport
    # 4. تسجيل الإطار: إرسال إلى VideoEncoder
```

**ضمانات الجودة:**
- البكسلات تُنسخ مباشرة من الصورة الأصلية (لا إعادة رسم)
- في الإطار النهائي: MAE=0, MSE=0, Coverage=100%

### المرحلة 9: ترميز الفيديو
```python
encoder = VideoEncoder("output.mp4", width=1920, height=1080, fps=30, crf=20)
encoder.write_frame(frame_bgr)  # لكل إطار
encoder.close()
```
- يحاول NVENC أولاً (GPU) → libx264 (CPU) → OpenCV fallback
- خرج MP4 مع H.264 codec

---

## 🔧 المحرك العميق — Deep Pipeline Engine

المحرك العميق هو نسخة متطورة تعمل مباشرة بدون طبقة الـ V3 Renderer:

```python
# animate_storyboard.py أو deep_pipeline_engine.py
render_deep_storyboard_pipeline(
    image_bgr,
    output_path="output.mp4",
    fps=30,
    zoom_scale=1.40,
    show_hand=True,
    suppress_borders=True,
    ...
)
```

### 6 مراحل داخلية:
1. **استقبال**: تحميل وتحسين الصورة (Super-sampling + Bilateral + Unsharp)
2. **تحليل**: كشف اللوحات + فصل النص/الرسومات
3. **تخطيط**: ترتيب الرسم + لقطات الكاميرا
4. **رسم النص**: محرك الخط العربي (سطر بسطر، RTL)
5. **رسم الرسومات**: مسارات مدارية متحدة المركز
6. **تجميع**: Outro + تصدير MP4

---

## ⚡ خط الأنابيب المعياري (Modular Pipeline)

يقع في `experiments/modular_pipeline/` وهو نسخة بحثية:

```
M1: DynamicPanelExtractor    → استخراج اللوحات
M2: MethodALayerSplitter     → فصل الطبقات
M3: TextLineAuditor          → تحليل النص
M4: TypographyEngine         → محرك الطباعة
M5: CameraDirector           → مخرج الكاميرا
```

يُشغّل عبر:
```bash
python experiments/modular_pipeline/run_scene_pipeline.py --image path/to/image.jpg
```

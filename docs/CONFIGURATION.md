# ⚙️ دليل الإعدادات — Configuration Reference

جميع إعدادات محرك الأنيميشن مُعرّفة في `SceneConfig` (ملف `kivy/engine/core/scene.py`).

---

## 📐 إعدادات الأبعاد والجودة

| الإعداد | النوع | القيمة الافتراضية | الوصف |
|---------|-------|-------------------|-------|
| `width` | `int` | `1280` | عرض الكانفاس بالبكسل |
| `height` | `int` | `720` | ارتفاع الكانفاس بالبكسل |
| `fps` | `int` | `30` | معدل الإطارات في الثانية |
| `detail_level` | `str` | `"MEDIUM"` | مستوى التفصيل: `"LOW"`, `"MEDIUM"`, `"HIGH"` |
| `element_spacing` | `int` | `24` | التباعد بين لوحات Storyboard (بكسل) |

---

## 🎨 إعدادات معالجة الصورة

| الإعداد | النوع | القيمة الافتراضية | الوصف |
|---------|-------|-------------------|-------|
| `color_palette_size` | `int` | `28` | عدد ألوان K-Means (حجم الباليت) |
| `min_stroke_length` | `float` | `12.0` | الحد الأدنى لطول الخط (بكسل) |
| `min_region_area` | `int` | `8` | الحد الأدنى لمساحة منطقة اللون (بكسل²) |
| `suppress_borders` | `bool` | `True` | إزالة حدود اللوحات الخارجية تلقائياً |

---

## 🖊️ إعدادات الرسم

| الإعداد | النوع | القيمة الافتراضية | الوصف |
|---------|-------|-------------------|-------|
| `drawing_speed` | `float` | `1.5` | مُضاعف سرعة الرسم العامة |
| `character_drawing_speed` | `float` | `1.5` | مُضاعف سرعة رسم الشخصيات |
| `text_drawing_speed` | `float` | `1.5` | مُضاعف سرعة كتابة النص |
| `drawing_direction` | `str` | `"OUTSIDE_IN"` | اتجاه الرسم: `"OUTSIDE_IN"` أو `"INSIDE_OUT"` |
| `drawing_order` | `str` | `"AUTO"` | ترتيب رسم العناصر |
| `fill_mode` | `str` | `"FOLLOW_OUTLINE"` | استراتيجية كشف التعبئة |
| `ring_step` | `int` | `5` | المسافة بين الحلقات المدارية (بكسل) |
| `brush_radius` | `int` | `8` | نصف قطر فرشاة الكشف (بكسل) |
| `sample_interval` | `float` | `3.0` | مسافة أخذ العينات على المسار (بكسل) |

### أوضاع ترتيب الرسم (`drawing_order`)

| الوضع | الوصف |
|-------|-------|
| `AUTO` | ترتيب ذكي تلقائي حسب الموقع والأهمية |
| `TOP_TO_BOTTOM` | من الأعلى إلى الأسفل |
| `LEFT_TO_RIGHT` | من اليسار إلى اليمين |
| `CENTER_OUT` | من مركز الصورة نحو الأطراف |
| `SPATIAL` | حسب القرب المكاني (nearest neighbor) |

### أوضاع التعبئة (`fill_mode`)

| الوضع | الوصف |
|-------|-------|
| `FOLLOW_OUTLINE` | تعبئة تتبع حدود الشكل (الأكثر واقعية) |
| `TOP_TO_BOTTOM` | تعبئة من الأعلى إلى الأسفل |
| `LEFT_TO_RIGHT` | تعبئة من اليسار إلى اليمين |
| `CENTER_OUT` | تعبئة من المركز للخارج |

---

## ✋ إعدادات يد الرسم

| الإعداد | النوع | القيمة الافتراضية | الوصف |
|---------|-------|-------------------|-------|
| `show_hand` | `bool` | `True` | إظهار/إخفاء يد الرسم |
| `hand_scale` | `float` | `0.95` | مقياس حجم اليد |
| `hand_target_h` | `int` | `340` | ارتفاع اليد المستهدف (بكسل) |
| `hand_opacity` | `float` | `1.0` | شفافية اليد (0.0 → 1.0) |
| `hand_tilt_enabled` | `bool` | `True` | تفعيل إمالة القلم الديناميكية مع المسار |

---

## 🎥 إعدادات الكاميرا

| الإعداد | النوع | القيمة الافتراضية | الوصف |
|---------|-------|-------------------|-------|
| `camera_preset` | `str` | `"SEQUENTIAL_OBJECT_FOCUS"` | نمط حركة الكاميرا |
| `camera_intensity` | `float` | `0.65` | شدة حركة الكاميرا (0.0 ثابت → 1.0 عميق) |
| `camera_zoom_scale` | `float` | `1.40` | مقياس التكبير الافتراضي |
| `establishing_duration` | `float` | `0.7` | مدة اللقطة الافتتاحية (ثانية) |
| `transition_duration` | `float` | `0.5` | مدة الانتقال بين الكائنات (ثانية) |
| `end_hold_seconds` | `float` | `1.5` | مدة الثبات على الإطار النهائي (ثانية) |

### أنماط الكاميرا (`camera_preset`)

| النمط | الوصف |
|-------|-------|
| `SEQUENTIAL_OBJECT_FOCUS` | تركيز متتابع على كل كائن أثناء رسمه |
| `STATIC` | كاميرا ثابتة (بدون حركة) |
| `SLOW_ZOOM` | تكبير بطيء تدريجي |

---

## 🧠 إعدادات المحرك العميق

| الإعداد | النوع | القيمة الافتراضية | الوصف |
|---------|-------|-------------------|-------|
| `deep_mode` | `bool` | `True` | تفعيل المحرك العميق ذو الـ 6 مراحل |
| `deep_min_parts` | `int` | `4` | الحد الأدنى لأجزاء التفكيك التشريحي |
| `deep_max_parts` | `int` | `6` | الحد الأقصى لأجزاء التفكيك التشريحي |

---

## 💡 أمثلة على التخصيص

### فيديو سريع (معاينة)
```python
config = SceneConfig(
    fps=24,
    drawing_speed=3.0,
    text_drawing_speed=3.0,
    detail_level="LOW",
    show_hand=False,
    camera_preset="STATIC"
)
```

### فيديو سينمائي عالي الجودة
```python
config = SceneConfig(
    width=1920,
    height=1080,
    fps=30,
    drawing_speed=1.0,
    character_drawing_speed=1.0,
    text_drawing_speed=1.2,
    detail_level="HIGH",
    camera_preset="SEQUENTIAL_OBJECT_FOCUS",
    camera_zoom_scale=1.50,
    camera_intensity=0.80,
    show_hand=True,
    hand_tilt_enabled=True,
    deep_mode=True,
    color_palette_size=40
)
```

### كاميرا ثابتة بدون يد
```python
config = SceneConfig(
    show_hand=False,
    camera_preset="STATIC",
    camera_intensity=0.0
)
```

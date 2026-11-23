# 🚀 دليل الاستخدام — Usage Guide

---

## 📱 طريقة 1: تطبيق واجهة المستخدم (GUI — Kivy)

### التثبيت
```bash
git clone https://github.com/ahmedabdellah28/Storyboard_to_Whiteboard_Animation.git
cd Storyboard_to_Whiteboard_Animation/kivy/
pip install -r requirements.txt
```

### التشغيل
```bash
cd kivy/
python main.py
```

### استخدام التطبيق
1. **الشاشة الرئيسية**: اضغط `Upload` لاختيار صورة أو مجلد
2. **تحليل**: التطبيق يحلل الصورة ويكتشف اللوحات تلقائياً
3. **إعداد الشبكة**: (اختياري) عدّل شبكة اللوحات يدوياً
4. **المشهد**: شاهد معاينة الكائنات المستخرجة
5. **التصدير**: اضغط لتوليد الفيديو

### الإعدادات من الواجهة
- **سرعة الرسم**: تعديل عبر `Preference`
- **إظهار اليد**: تفعيل/تعطيل من الإعدادات
- **دقة الفيديو**: حتى 1080p (Full HD)
- **معالجة جماعية**: اختر مجلداً لمعالجة صور متعددة (سطح المكتب فقط)

---

## 💻 طريقة 2: سطر الأوامر — CLI (سكربت السينمائي)

### الاستخدام الأساسي
```bash
python animate_storyboard.py --image path/to/image.jpg
```

### جميع الخيارات
```bash
python animate_storyboard.py \
    --image path/to/storyboard.jpg \     # مسار الصورة (مطلوب)
    --output output_video.mp4 \           # مسار الخرج (اختياري)
    --zoom 1.40 \                         # مقياس التكبير (افتراضي: 1.40)
    --fps 30                              # معدل الإطارات (افتراضي: 30)
```

### مثال
```bash
# تحويل صورة storyboard إلى فيديو سينمائي
python animate_storyboard.py --image test_images/storyboard_6panels.png --output my_animation.mp4

# فيديو بتكبير أعلى و FPS أقل
python animate_storyboard.py --image test_images/scene.jpg --zoom 1.60 --fps 24
```

---

## 🧪 طريقة 3: خط الأنابيب المعياري (للباحثين)

```bash
cd experiments/modular_pipeline/
python run_scene_pipeline.py --image path/to/image.jpg
```

يُشغّل المراحل M1→M5 بالتتابع مع خرج مفصّل لكل مرحلة.

---

## 🐍 طريقة 4: استخدام كـ API في Python

### المحرك المداري (Concentric Engine)
```python
import cv2
from engine.render.concentric_engine import render_concentric_orbital_whiteboard

image = cv2.imread("my_image.jpg")
output_path = render_concentric_orbital_whiteboard(
    image,
    output_path="output.mp4",
    fps=30,
    show_hand=True
)
print(f"Video saved to: {output_path}")
```

### المحرك العميق (Deep Pipeline Engine)
```python
import cv2
from engine.render.deep_pipeline_engine import render_deep_storyboard_pipeline

image = cv2.imread("my_storyboard.jpg")
output_path = render_deep_storyboard_pipeline(
    image,
    output_path="output.mp4",
    fps=30,
    zoom_scale=1.40,
    show_hand=True,
    suppress_borders=True
)
```

### واجهة SketchAPI المبسطة
```python
import sys
sys.path.insert(0, "kivy")

from sketchApi import (
    render_concentric_orbital_whiteboard,
    render_deep_storyboard_pipeline,
    read_image_unicode,
    DirectVideoWriter
)

# قراءة صورة بمسار عربي
image = read_image_unicode("صور/المشهد_الأول.jpg")

# توليد الفيديو
render_deep_storyboard_pipeline(image, output_path="الخرج.mp4")
```

---

## 🔊 أداة تقسيم الصوت

### الاستخدام
```bash
python split_audio.py --input "audio_file.m4a" --minutes 3 --output-dir audio_chunks
```

### جميع الخيارات
| الخيار | الاختصار | الافتراضي | الوصف |
|--------|----------|-----------|-------|
| `--input` | `-i` | `videoplayback (1).m4a` | مسار الملف الصوتي |
| `--minutes` | `-m` | `3.0` | مدة كل قطعة (بالدقائق) |
| `--output-dir` | `-o` | `audio_chunks` | مجلد الخرج |
| `--prefix` | `-p` | `part` | بادئة أسماء الملفات |

### مثال
```bash
# تقسيم إلى قطع 5 دقائق
python split_audio.py -i lecture.m4a -m 5 -o output_parts

# تقسيم إلى قطع دقيقة واحدة مع بادئة مخصصة
python split_audio.py -i podcast.m4a -m 1 -p segment
```

---

## 🏗️ بناء التطبيقات

### بناء EXE لـ Windows
```bash
cd kivy/
pip install pyinstaller
pyinstaller dlDesktop.spec
# الملف في: dist/dlDesktop.exe
```

### بناء APK لـ Android
```bash
cd kivy/
pip install -r req_android.txt
buildozer android debug
# الملف في: bin/
```

> ⚠️ بناء Android يتطلب Linux أو WSL. راجع README.md للتعليمات الكاملة.

---

## 🧪 تشغيل الاختبارات

```bash
# جميع الاختبارات
pytest tests/

# اختبار محدد
pytest tests/test_panel_animation.py -v

# اختبارات البنية
pytest tests/test_architecture_fitness.py -v

# اختبار الجودة (Golden Baseline)
pytest tests/test_golden_baseline.py -v
```

---

## 📂 هيكل الخرج

```
output_animations/
├── scene_1_animation.mp4      ← فيديو الأنيميشن
└── ...

step_inspection_images/
├── panel_1_extracted.png       ← صور التصحيح (debug)
├── panel_2_strokes.png
└── ...
```

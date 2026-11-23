# 🛠️ دليل التطوير — Developer Guide

هذا الدليل موجه للمطورين الذين يريدون المساهمة أو تطوير المشروع.

---

## 📋 المتطلبات

### Python
- **الإصدار**: Python 3.11+ (مُختبر على 3.11 و 3.13)

### المكتبات الأساسية
```
kivymd==1.2.0          # واجهة Material Design
kivy[base]==2.3.1      # إطار واجهة المستخدم
numpy                  # عمليات المصفوفات
opencv-python          # معالجة الصور
av (PyAV)              # ترميز/فك ترميز الفيديو
ffpyplayer             # تشغيل الفيديو داخل التطبيق
plyer                  # خدمات النظام (مدير الملفات)
```

### تثبيت بيئة التطوير
```bash
# إنشاء بيئة افتراضية
python -m venv .venv

# تفعيل (Windows)
.venv\Scripts\activate

# تفعيل (Linux/Mac)
source .venv/bin/activate

# تثبيت المتطلبات
cd kivy/
pip install -r req_desktop.txt
```

---

## 🏛️ مبادئ البنية

### 1. فصل الاهتمامات
```
UI Layer (screens, widgets)
    ↓ يستدعي
Services Layer (workflow, settings)
    ↓ يستدعي
Engine Layer (processing, render, animation, camera, video)
    ↓ يستخدم
Core Models (scene, stroke, region, timeline, project)
```

### 2. القواعد الذهبية للمصيّر
1. **الصورة المصدر = مصدر الحقيقة** — لا إعادة رسم أو تعديل على البكسلات
2. **لا بكسل قبل حدثه** — كل بكسل يظهر فقط عند رسمه
3. **الكانفاس يبدأ فارغاً** — خلفية بيضاء 100%
4. **تزامن اليد والقلم** — البكسلات تحت رأس القلم فقط
5. **لا كشف مسبق** — Residual فقط بعد اكتمال جميع الأحداث
6. **لا رسم للإطارات** — حدود اللوحات تبقى خلفية نظيفة
7. **صفر فقدان** — MAE=0, MSE=0, Coverage=100%

### 3. اتجاه التبعيات
```
core ← لا يعتمد على شيء
processing ← يعتمد على core
animation ← يعتمد على core
planning ← يعتمد على core
camera ← يعتمد على core
render ← يعتمد على core + animation + camera
video ← يعتمد على core
```

> ⚠️ **قاعدة مهمة**: `core/` لا يستورد من أي وحدة أخرى في `engine/`.

---

## 🔧 إضافة محرك تصيير جديد

### 1. أنشئ الملف
```python
# kivy/engine/render/my_custom_engine.py

import cv2
import numpy as np
from ..video.encoder import VideoEncoder
from .hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast


def render_custom_animation(
    image_bgr: np.ndarray,
    output_path: str = "output.mp4",
    fps: int = 30,
    show_hand: bool = True,
    progress_cb=None
) -> str:
    """My custom rendering engine."""
    h, w = image_bgr.shape[:2]
    
    encoder = VideoEncoder(output_path, w, h, fps)
    
    # تحميل اليد
    hand_bgra = None
    if show_hand:
        hand_bgra = load_hand_asset_bgra()
    
    # حلقة التصيير
    total_frames = fps * 10  # 10 ثوان
    canvas = np.full((h, w, 3), 255, dtype=np.uint8)
    
    for frame_idx in range(total_frames):
        t = frame_idx / total_frames
        
        # كشف تدريجي
        reveal_h = int(h * t)
        canvas[:reveal_h, :] = image_bgr[:reveal_h, :]
        
        # تركيب اليد
        frame = canvas.copy()
        if hand_bgra is not None:
            pen_x, pen_y = w // 2, reveal_h
            composite_hand_on_canvas_fast(frame, hand_bgra, pen_x, pen_y)
        
        encoder.write_frame(frame)
        
        if progress_cb:
            progress_cb(t * 100, f"Frame {frame_idx}/{total_frames}")
    
    encoder.close()
    return output_path
```

### 2. صدّره من `sketchApi.py`
```python
from engine.render.my_custom_engine import render_custom_animation
```

### 3. (اختياري) أضفه للواجهة
عدّل `ui/services/render_service.py` لإضافة خيار المحرك الجديد.

---

## 🔧 إضافة معالج صور جديد

### 1. أنشئ الملف
```python
# kivy/engine/processing/my_processor.py

import cv2
import numpy as np
from ..core.project import Project, StructureType
from ..core.scene import SceneConfig


class MyProcessor:
    @staticmethod
    def process(image_bgr: np.ndarray, config: SceneConfig) -> Project:
        """Custom image processor."""
        # ... التحليل
        return Project(structure_type=StructureType.SINGLE_SCENE)
```

### 2. ادمجه في `ImageProcessor`
```python
# في image_processor.py
from .my_processor import MyProcessor

# في دالة process():
result = MyProcessor.process(image_bgr, config)
```

---

## 🔧 إضافة وضع ترتيب رسم جديد

### في `engine/animation/drawing_order.py`:
```python
# في _sequence_objects():
elif mode == "MY_CUSTOM_ORDER":
    # ترتيبك المخصص
    ordered = sorted(objects, key=lambda o: my_custom_key(o))
```

### في `engine/core/scene.py`:
أضف الوضع في تعليق `drawing_order`.

---

## 🧪 كتابة الاختبارات

### اختبار وحدة جديد
```python
# tests/test_my_feature.py
import pytest
import numpy as np
from engine.core.scene import SceneConfig
from engine.processing.my_processor import MyProcessor


class TestMyProcessor:
    def test_basic_processing(self):
        """Test basic image processing."""
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        config = SceneConfig()
        
        project = MyProcessor.process(image, config)
        
        assert project is not None
        assert project.structure_type is not None
    
    def test_empty_image(self):
        """Test with blank white image."""
        image = np.full((480, 640, 3), 255, dtype=np.uint8)
        config = SceneConfig()
        
        project = MyProcessor.process(image, config)
        assert len(project.scenes) >= 0
```

### تشغيل الاختبارات
```bash
# اختبار ملف واحد
pytest tests/test_my_feature.py -v

# مع تغطية
pytest tests/ --cov=engine -v

# اختبار سريع (بدون اختبارات بطيئة)
pytest tests/ -v -k "not golden and not interactive"
```

---

## 📏 معايير الكود

### التنسيق
- **المسافات**: 4 مسافات (لا tabs)
- **طول السطر**: حد أقصى 120 حرف
- **السلسلة التوثيقية**: Docstrings لكل كلاس ودالة عامة
- **Type Hints**: مطلوبة لدوال API العامة

### التسمية
```python
# كلاسات: PascalCase
class MyProcessor:

# دوال/متغيرات: snake_case
def process_image(image_bgr: np.ndarray) -> Project:

# ثوابت: UPPER_SNAKE_CASE
DEFAULT_HAND_PATH = "..."
PEN_TIP_ANCHOR_X = 62

# ملفات: snake_case
my_processor.py
```

### الاستيراد
```python
# 1. مكتبات النظام
import os
import sys
import math

# 2. مكتبات خارجية
import cv2
import numpy as np

# 3. وحدات المحرك (نسبية)
from ..core.scene import Scene, SceneConfig
from ..processing.image_processor import ImageProcessor
```

---

## 📐 هيكل الوحدة الجديدة

```python
"""
Module docstring explaining purpose.
"""
import ...

# Constants
SOME_CONSTANT = 42

# Internal helpers (private)
def _helper_function():
    ...

# Public API
class MyClass:
    """Class docstring."""
    
    @staticmethod
    def public_method(param: Type) -> ReturnType:
        """Method docstring."""
        ...
```

---

## 🐛 التصحيح (Debugging)

### تفعيل التسجيل
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### حفظ صور تشخيصية
```python
# صور المراحل الوسيطة تُحفظ في step_inspection_images/
cv2.imwrite("step_inspection_images/debug_panel_1.png", panel_image)
```

### التشغيل التفاعلي
```bash
python tests/interactive_manual_run.py
```

---

## 🔄 سير العمل (Git Workflow)

```bash
# 1. أنشئ فرعاً جديداً
git checkout -b feature/my-new-feature

# 2. اعمل تغييراتك
# ...

# 3. شغّل الاختبارات
pytest tests/ -v

# 4. أنشئ commit
git add .
git commit -m "feat: add my new feature"

# 5. ادفع الفرع
git push origin feature/my-new-feature
```

### صيغ رسائل Commit
```
feat: ميزة جديدة
fix: إصلاح خطأ
refactor: إعادة هيكلة بدون تغيير السلوك
docs: تحديث الوثائق
test: إضافة/تعديل اختبارات
perf: تحسين أداء
```

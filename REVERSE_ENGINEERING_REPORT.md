# تقرير الهندسة العكسية والتحليل المعماري والتقني لمشروع `image-to-animation-offline`

---

## 1. Executive Summary (الملخص التنفيذي)

مشروع **`image-to-animation-offline`** هو تطبيق مفتوح المصدر مبني بلغة Python وإطار العمل **Kivy / KivyMD** (للواجهة الرسومية)، ومخصص لتحويل الصور الثابتة إلى فيديو يحاكي أسلوب الرسم اليدوي (Whiteboard / Sketch Animation) محلياً وبشكل غير متصل بالإنترنت (Offline).

### الحقيقة التقنية الأساسية لآلية عمل المشروع:
خلافاً لما قد يوحي به اسم "Sketch Animation" أو الشائع في محركات الرسم المتجهي (Vector Stroke Engines):
1. **لا يستخدم المشروع أي خوارزميات لاستخراج المسارات المتجهة (Vector Paths)، ولا منحنيات Bézier، ولا Canny Edge Detection، ولا Contours (`cv2.findContours`)، ولا Skeletonization.**
2. يعتمد المشروع على **خوارزمية تقسيم شبكي مكاني (Grid-Tile Nearest-Neighbor Spatial Traversal)**:
   - يتم تحويل الصورة إلى صورة ثنائية (Binary) عبر **Adaptive Gaussian Thresholding**.
   - يتم تقطيع الصورة إلى شبكة من المربعات/البلاطات الصغيرة (Tiles/Grids) بحجم $N \times N$ بكسل (حيث $N = \text{split\_len}$).
   - يتم ترشيح المربعات التي تحتوي على بكسلات داكنة (خطوط الرسم).
   - يتم التنقل بين هذه المربعات باستخدام خوارزمية **الجار الأقرب إقليدياً (Greedy Nearest Neighbor)** لتحديد ترتيب كشف المربعات.
   - في كل خطوة، يتم كشف المربع بالكامل ولصق صورة يد وقلم فوقه، ثم كتابة الإطار إلى الفيديو كل عدد محدد من الخطوات (`skip_rate`).
3. بعد انتهاء الرسم، يتم تثبيت الصورة الأصلية (ملونة أو رمادية) لعدة ثوانٍ، ثم يتم تحويل الفيديو الخام الناتج عبر مكتبة **PyAV (FFmpeg API)** إلى كوديك **H.264** وحاوية **MP4**.

---

## 2. Current Architecture (المعمارية الحالية)

الهيكلية الطبقية الحالية للمشروع كما هي منفذة في الكود:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        UI Layer (Kivy / KivyMD)                         │
│  - main.py (DlImg2SktchApp)                                            │
│  - main_layout.kv                                                       │
│  - screens/divider.py (MyMDDivider)                                     │
│  [File Selection, Parameter Input, Settings Popups, Video Preview]     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Thread(target=initiate_sketch, daemon=True)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Processing & Orchestration Layer                     │
│  - sketchApi.py (initiate_sketch)                                       │
│  [Resolution Clamping, Padding, AllVariables State Management]          │
└───────────────────┬─────────────────────────────────┬───────────────────┘
                    │                                 │
                    ▼                                 ▼
┌──────────────────────────────────────┐  ┌───────────────────────────────┐
│      Image Preprocessing Engine      │  │    Hand Asset Preprocessing   │
│  - sketchApi.py (preprocess_image)   │  │  - preprocess_hand_image      │
│  [Resize, Gray, CLAHE, AdpThresh]   │  │  [Crop to Mask, Alpha Mask]   │
└───────────────────┬──────────────────┘  └───────────────┬───────────────┘
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 Animation & Spatial Traversal Engine                    │
│  - sketchApi.py (draw_whiteboard_animations -> draw_masked_object)      │
│  [Grid Splitting, Euclidean Distance Matrix, Patch Revealing]           │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Rendering & Compositing Layer                         │
│  - sketchApi.py (draw_hand_on_img)                                      │
│  [Alpha Blending of Hand onto Canvas, Subsampling by skip_rate]         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ cv2.VideoWriter (Raw AVI / MP4)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 Transcoding / Video Encoding Layer                      │
│  - sketchApi.py (ffmpeg_convert)                                        │
│  - PyAV (av.open, libx264 / h264, yuv420p, CRF 20)                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Complete Image Processing Pipeline (مسار المعالجة الكامل)

تتبع تفصيلي لمسار البيانات من لحظة اختيار المستخدم للصورة حتى تصدير الفيديو النهائي:

```text
1. اختيار الصورة والبارامترات
   └── الملف: kivy/main.py | الكلاس: DlImg2SktchApp | الدالة: submit_sketch_req()

2. إطلاق خيط معالجة منفصل (Background Thread)
   └── الدالة: initiate_sketch(...) في kivy/sketchApi.py

3. تسوية الأبعاد والـ Padding (Dimension Normalization)
   └── الدالة: resize_with_padding(...) أو find_nearest_res(...)

4. المعالجة الأولية للصورة (Preprocessing & Binarization)
   └── الدالة: preprocess_image(img, variables)

5. تجهيز أصل اليد والقناع (Hand Mask Extraction)
   └── الدالة: preprocess_hand_image(hand_path, hand_mask_path, variables)

6. إنشاء كائن الكاتب الفيديو الأولي (OpenCV VideoWriter Initialization)
   └── cv2.VideoWriter(save_video_path, fourcc, frame_rate, (resize_wd, resize_ht))

7. تقسيم الصورة إلى شبكة كتل ومربعات (Spatial Grid Splitting)
   └── الدالة: draw_masked_object(...) -> np.split(...)

8. تصفية كتل الرسم وحساب المسافات الإقليدية وترتيب الكشف
   └── الدالة: draw_masked_object(...) -> euc_dist(...) + np.argmin(...)

9. تركيب اليد على الإطار وتوليد الإطارات (Compositing & Subsampling)
   └── الدالة: draw_hand_on_img(...) مع شرط (counter % skip_rate == 0)

10. إضافة إطارات النهاية الثابتة (Holding Frames)
    └── حلقة تكرار: frame_rate * end_gray_img_duration_in_sec

11. إغلاق ملف الفيديو الأولي
    └── variables.video_object.release()

12. إعادة الترميز وضغط الفيديو النهائي (PyAV / FFmpeg Transcoding)
    └── الدالة: ffmpeg_convert(source_vid, dest_vid, platform)
```

---

## 4. Image Processing Algorithm (الخوارزميات المستخدمة فعلياً)

تفصيل دقيق للعمليات الحسابية والمعالجة داخل كل مرحلة:

### أ. تسوية الدقة والأبعاد (`sketchApi.py:548-566` & `382-416`):
1. **التحقق من الحد الأقصى `max_1080p`**:
   - إذا كانت الدقة أكبر من $1920$:
     - إذا كانت الصورة أفقية ($W > H$): تُحدد الأبعاد بـ $1920 \times 1080$.
     - إذا كانت الصورة رأسية ($H \ge W$): تُحدد الأبعاد بـ $1080 \times 1920$.
   - تستدعى دالة `resize_with_padding`:
     $$\text{scale} = \min\left(\frac{\text{target\_w}}{w}, \frac{\text{target\_h}}{h}\right)$$
     $$\text{new\_w} = \lfloor w \times \text{scale} \rfloor, \quad \text{new\_h} = \lfloor h \times \text{scale} \rfloor$$
     - يتم التحجيم عبر: `cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)`.
     - يتم حساب الحواف الناقصة وإضافتها باللون الأبيض `(255, 255, 255)` عبر: `cv2.copyMakeBorder(..., cv2.BORDER_CONSTANT)`.
2. **في حال عدم تفعيل `max_1080p` أو كانت الصورة أصغر**:
   - تستدعى دالة `find_nearest_res` للبحث عن أقرب دقة قياسية من المصفوفة:
     `[640, 360, 480, 1280, 720, 1920, 1080, 2560, 1440, 3840, 2160, 7680, 4320]`.

### ب. المعالجة وتحويل الألوان وتحديد العتبة (`sketchApi.py:32-54`):
1. تحويل BGR إلى Grayscale:
   - `img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)`
2. تطبيق CLAHE (Contrast Limited Adaptive Histogram Equalization):
   - `clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(3, 3))`
   - `cl1 = clahe.apply(img_gray)`
   - *(ملاحظة تدقيقية: تم حساب `cl1` في السطر 40 ولكن لم يُستخدم في السطر التالي حيث تم تمرير `img_gray` مباشرة للخطوة التالية).*
3. العتبة التكيفية (Adaptive Gaussian Thresholding):
   - `img_thresh = cv2.adaptiveThreshold(img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 10)`
   - **المدخل**: مصفوفة Grayscale ثنائية الأبعاد `(H, W)`.
   - **العملية**: تحسب العتبة لكل بكسل بناءً على المتوسط المرجح بدالة غاوس لجوار بحجم $15 \times 15$ مطروحاً منه الثابت $C=10$.
   - **المخرج**: صورة ثنائية `(H, W)` حيث البكسلات الداكنة والحدود تأخذ القيمة $0$ (Black) والمناطق المسطحة والفاتحة تأخذ القيمة $255$ (White).

---

## 5. Stroke/Contour Generation (كيف تتحول الصورة إلى خطوط)

**الإجابة الحاسمة من فحص الكود:**
الصورة **لا تتحول إلى خطوط (Strokes) أو مسارات (Contours)** إطلاقاً.
النموذج المتبع هو **كشف تدريجي لبلاطات ثنائية الأبعاد (Patch / Block Revelation)**:

1. **التقطيع الشبكي (`sketchApi.py:186-192`):**
   - يتم حساب عدد القطوع الرأسية والأفقية:
     $$N_v = \lceil \text{resize\_ht} / \text{split\_len} \rceil, \quad N_h = \lceil \text{resize\_wd} / \text{split\_len} \rceil$$
   - يتم تقسيم مصفوفة `img_thresh` إلى شبكة مربعات باستخدام `np.split`:
     - المحور الأفقي أولاً: `np.split(img_thresh_copy, n_cuts_horizontal, axis=-1)`
     - المحور الرأسي ثانياً: `np.split(..., n_cuts_vertical, axis=-2)`
   - تصبح النتيجة مصفوفة رباعية الأبعاد `grid_of_cuts` بأبعاد:
     $$(N_v, N_h, \text{split\_len}, \text{split\_len})$$

2. **تحديد الكتل التي تحتوي على رسم (`sketchApi.py:196-198`):**
   - يتم فحص كل كتلة: هل تحتوي على بكسلات سوداء تقل قيمتها عن `black_pixel_threshold` (الافتراضي: 10)؟
     `cut_having_black = (grid_of_cuts < black_pixel_threshold) * 1`
   - يتم جمع البكسلات السوداء داخل كل كتلة:
     `cut_having_black = np.sum(np.sum(cut_having_black, axis=-1), axis=-1)`
   - استخراج إحداثيات الشبكة للكتل الفعالة فقط:
     `cut_black_indices = np.array(np.where(cut_having_black > 0)).T`
     ينتج مصفوفة من الإحداثيات الشبكية:
     $$\text{cut\_black\_indices} = \begin{bmatrix} r_0 & c_0 \\ r_1 & c_1 \\ \vdots & \vdots \end{bmatrix}$$

---

## 6. Drawing Order (خوارزمية ترتيب الرسم)

كيف تحدد الأداة الترتيب الزمني لظهور أجزاء الصورة؟

تستخدم الأداة خوارزمية **Greedy Nearest Neighbor Heuristic** في فضاء إحداثيات الشبكة:

1. **نقطة البداية (`sketchApi.py:185`):**
   - تبدأ من الفهرس `selected_ind = 0`، وهو أول عنصر في المصفوفة (عادة المربع الذي يحتوي على سواد في أقصى أعلى-يسار الصورة).

2. **حلقة الترتيب والانتقال (`sketchApi.py:206-248`):**
   - يتم أخذ إحداثي الكتلة الحالية: $\mathbf{P}_{\text{current}} = (r_c, c_c)$.
   - يتم استخراج محتوى هذه الكتلة ولصقه في الإطار الأبيض التراكمي `variables.drawn_frame`.
   - يتم حذف الكتلة الحالية من قائمة الكتل المتبقية بطريقة الاستبدال السريع مع العنصر الأخير:
     ```python
     cut_black_indices[selected_ind] = cut_black_indices[-1]
     cut_black_indices = cut_black_indices[:-1]
     ```
   - **حساب المسافة الإقليدية إلى جميع الكتل المتبقية (`sketchApi.py:28-30, 246`):**
     $$\text{dist}_i = \sqrt{(r_i - r_c)^2 + (c_i - c_c)^2}$$
     يتم تنفيذ ذلك عبر الدالة:
     ```python
     def euc_dist(arr1, point):
         square_sub = (arr1 - point) ** 2
         return np.sqrt(np.sum(square_sub, axis=1))
     ```
   - **اختيار الكتلة التالية (`sketchApi.py:247`):**
     $$\text{next\_index} = \arg\min (\mathbf{dist})$$
     يتم اختيار أقرب كتلة جغرافياً على الشبكة للكتلة الحالية.

3. **النتيجة الحركية لهذا الترتيب:**
   - يبدأ "الرسم" في منطقة معينة، ثم ينتقل نقطة بنقطة إلى أقرب منطقة مجاورة لها، مما يعطي إيحاءً بأن اليد ترسم في منطقة واحدة متصلة حتى تنتهي منها، ثم "تقفز" إلى أقرب منطقة أخرى تحتوي على خطوط.

---

## 7. Animation Algorithm (خوارزمية توليد الحركة والتوقيت)

كيف تتحول الصورة الثابتة إلى حركة؟

1. **اللوحة التراكمية (Accumulator Canvas):**
   - يتم البدء بلوحة بيضاء بالكامل:
     `variables.drawn_frame = np.zeros(img.shape, np.uint8) + [255, 255, 255]`
2. **الكشف التدريجي:**
   - في كل تكرار للحلقة، يتم استبدال المربع بحجم $\text{split\_len} \times \text{split\_len}$ في اللوحة البيضاء بمحتواه الحقيقي من `img_thresh` (القنوات الثلاث متطابقة للرسم الأبيض والأسود).
3. **أخذ العينات الفرعية للإطارات (Subsampling via `skip_rate`):**
   - ليس كل مربع يتم رسمه ينتج إطار فيديو، بل يتم الاعتماد على عداد:
     ```python
     counter += 1
     if counter % skip_rate == 0:
         variables.video_object.write(drawn_frame_with_hand)
     ```
   - هذا يعني أنه يتم رسم `skip_rate` من المربعات على اللوحة التراكمية قبل التقاط إطار واحد وكتابته في الفيديو.

---

## 8. Frame Generation (توليد وتركيب الإطارات)

كيف يتم إنشاء الإطار الفردي وما هي التقنية المستخدمة؟

* **المكتبات المستخدمة**: **NumPy + OpenCV (`cv2`)**.
* **الذاكرة والتخزين**:
  - **لا يتم تخزين الإطارات كملفات صور على القرص**.
  - يتم توليد الإطار مباشرة في ذاكرة الرام كـ `numpy.ndarray` وتمريره مباشرة إلى كائن الفيديو:
    `variables.video_object.write(drawn_frame_with_hand)`
* **تركيب الإطار (Frame Composition)**:
  1. الإطار الأساسي: `variables.drawn_frame` (أبعاد: `H x W x 3`, نوع: `uint8`).
  2. إذا كان خيار اليد مفعلاً (`variables.draw_hand == True`):
     - يُستدعى التابع `draw_hand_on_img`.
     - يُحدد موقع اليد عند منتصف المربع الحالي:
       $$\text{hand\_x} = \text{range\_h\_start} + \lfloor \text{split\_len} / 2 \rfloor$$
       $$\text{hand\_y} = \text{range\_v\_start} + \lfloor \text{split\_len} / 2 \rfloor$$
     - يتم دمج صورة اليد مع الإطار عبر القناع العكسي لليد (`hand_mask_inv`).
  3. إذا كان خيار اليد معطلاً:
     - يتم كتابة `variables.drawn_frame.copy()` مباشرة.

---

## 9. Video Encoding (ترميز الفيديو و FFmpeg)

تتم عملية إنتاج الفيديو على مرحلتين منفصلتين:

### المرحلة الأولى: توليد الفيديو الخام بواسطة OpenCV
* **الدالة**: `cv2.VideoWriter(save_video_path, fourcc, fps, (width, height))`
* **FourCC Codec**:
  - على Android: `*"MJPG"` والحاوية `.avi` (أو `.mpg`).
  - على Windows / Linux: `*"mp4v"` والحاوية `.mp4`.
* **Pixel Format**: BGR (افتراضي OpenCV).

### المرحلة الثانية: إعادة الضغط والترميز عبر PyAV (`sketchApi.py:468-521`)
لا يتم استدعاء سطر أوامر FFmpeg التنفيذي (`subprocess`)، بل يتم استخدام **مكتبة `av` (Python Bindings لـ FFmpeg Libraries)**:

```python
input_container = av.open(src_path, mode="r")
output_container = av.open(dest_vid, mode="w")

# تحديد الكوديك
if platform == "android":
    out_stream = output_container.add_stream("libx264", rate=fps)
else:
    out_stream = output_container.add_stream("h264", rate=fps)

out_stream.width = width
out_stream.height = height
out_stream.pix_fmt = "yuv420p"
out_stream.options = {"crf": "20"}

for frame in input_container.decode(video=0):
    packet = out_stream.encode(frame)
    if packet:
        output_container.mux(packet)
```

### معايير الترميز الدقيقة:
* **Codec**: `h264` (أو `libx264` على Android).
* **Pixel Format**: `yuv420p` (لضمان التوافق مع مشغلات الفيديو القياسية والمتصفحات).
* **Container**: `MP4` (`vid_YYYYMMDD_HHMMSS_h264.mp4`).
* **Quality/Bitrate Control**: `CRF = 20` (Constant Rate Factor).
* **Audio**: لا يوجد مسار صوتي نهائياً (Audio is None).
* **Hardware Acceleration**: غير مفعل إطلاقاً (يستخدم ترميز CPU فقط، لا يوجد NVENC أو QuickSync أو VAAPI).
* **سلوك الفشل**: في حال حدوث خطأ في `ffmpeg_convert`، يلتقط الكود الاستثناء ويعتمد ملف الفيديو الخام الأولي بدون حذف.

---

## 10. Hand / Pen System (نظام اليد والقلم)

* **طبيعة اليد في المشروع**:
  - اليد ليست محرك فيزيائي أو مسار محرك ديناميكي، بل هي **أصل رسومي ثابت (Static 2D Sprite Overlay)**.
  - الملفات:
    - صورة اليد: `kivy/data/images/drawing-hand.png`
    - قناع اليد: `kivy/data/images/hand-mask.png`
* **معالجة اليد عند البدء (`preprocess_hand_image` في `sketchApi.py:56-82`):**
  1. قراءة صورة وقناع اليد.
  2. استخراج حدود القناع وقص الصورة والقناع لتقليص المساحات الفارغة غير المستخدمة (`get_extreme_coordinates`).
  3. تحويل القناع إلى أرقام عشرية: `hand_mask = hand_mask / 255.0` و `hand_mask_inv = (255 - hand_mask) / 255.0`.
* **عملية الدمج (Alpha Compositing) في `draw_hand_on_img` (`sketchApi.py:97-164`):**
  1. قص اليد إذا تجاوزت حواف إطار الصورة (`remaining_ht`, `remaining_wd`).
  2. تصفير بكسلات اللوحة في مكان اليد عبر ضرب القنوات الثلاث في `hand_mask_inv_cropped`:
     $$\text{Canvas}[y:y+h, x:x+w] = \text{Canvas}[y:y+h, x:x+w] \times \text{hand\_mask\_inv}$$
  3. إضافة بكسلات اليد:
     $$\text{Canvas}[y:y+h, x:x+w] = \text{Canvas}[y:y+h, x:x+w] + \text{hand\_cropped}$$
* **إمكانية التعطيل/الحذف**:
  - اليد اختيارية بالكامل ومربوطة بمتغير منطقي `draw_hand`.
  - عند ضبط `draw_hand = False` من الإعدادات، يتم تجاوز دالة دمج اليد ويكتفي المحرك بكتابة اللوحة `drawn_frame` مباشرة. يمكن حذف ملفات اليد دون أن يتأثر المحرك الرياضي لكشف البلاطات.

---

## 11. Parameters Analysis (تأثير وسائط التحكم والمعادلات الرياضية)

### 1. المتغيرات ومعانيها في الكود:
* **`split_len` (حجم المربع/الكتلة)**:
  - يحدد أبعاد كل كتلة ($\text{split\_len} \times \text{split\_len}$).
  - كلما كبرت القيمة (مثلاً 20 أو 40)، قل إجمالي عدد الكتل، وزادت سرعة الرسم، وأصبح الرسم خشناً كأنه مربعات تظهر فجأة.
  - كلما صغرت (مثلاً 5 أو 10)، زاد عدد الكتل وأصبح الرسم أدق وأبطأ.
  - يتم اختيار `split_len` من القواسم المشتركة (`common_divisors`) لدقة الصورة لمنع حدوث كسور في أبعاد الشبكة.
* **`frame_rate` (FPS)**:
  - معدل إطارات الفيديو الناتج (الافتراضي: 25).
* **`obj_skip_rate` / `bg_object_skip_rate` (`skip_rate`)**:
  - يحدد وتيرة التقاط الإطارات. كل `skip_rate` كتلة يتم رسمها، يتم تصدير إطار واحد إلى الفيديو.
* **`main_img_duration` (`end_gray_img_duration_in_sec`)**:
  - عدد الثواني لعرض الصورة الأصلية الثابتة في نهاية الفيديو (الافتراضي: 2 ثانية).

### 2. المعادلات الرياضية الدقيقة لحساب عدد الإطارات ومدة الفيديو:

1. **إجمالي عدد كتل الرسم ($N_{\text{draw}}$):**
   $$N_{\text{draw}} = \text{count of blocks in } \text{cut\_black\_indices}$$
2. **عدد إطارات مرحلة الرسم ($F_{\text{draw}}$):**
   $$F_{\text{draw}} = \left\lfloor \frac{N_{\text{draw}}}{\text{skip\_rate}} \right\rfloor$$
3. **عدد إطارات المشهد النهائي الثابت ($F_{\text{end}}$):**
   $$F_{\text{end}} = \text{frame\_rate} \times \text{main\_img\_duration}$$
4. **إجمالي عدد إطارات الفيديو ($F_{\text{total}}$):**
   $$F_{\text{total}} = F_{\text{draw}} + F_{\text{end}} = \left\lfloor \frac{N_{\text{draw}}}{\text{skip\_rate}} \right\rfloor + (\text{frame\_rate} \times \text{main\_img\_duration})$$
5. **مدة الفيديو الإجمالية بالثواني ($T_{\text{video}}$):**
   $$T_{\text{video}} = \frac{F_{\text{total}}}{\text{frame\_rate}} = \frac{\lfloor N_{\text{draw}} / \text{skip\_rate} \rfloor}{\text{frame\_rate}} + \text{main\_img\_duration}$$

---

## 12. Performance & Bottlenecks (اختناقات الأداء)

من خلال الفحص الدقيق لكود المعالجة، تم تشخيص الاختناقات كالتالي:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Performance Diagnostics                         │
├────────────────────────┬───────────────────────────────────────────────┤
│ Bottleneck Type        │ Exact Cause in Code                           │
├────────────────────────┼───────────────────────────────────────────────┤
│ 1. CPU / Algorithmic   │ الدالة `euc_dist` وحساب المسافات الإقليدية:  │
│    (الأشد وطأة)        │ في كل كتلة يتم حساب المسافة لجميع الكتل       │
│                        │ المتبقية عبر حلقة `while len(...) > 1`.       │
│                        │ التعقيد الزمني هو: $O(K^2)$ حيث $K$ عدد الكتل. │
│                        │ في الصور ذات الدقة العالية (1080p) وقيم       │
│                        │ `split_len` صغيرة (مثل 5 أو 10)، يصل $K$      │
│                        │ إلى عشرات الآلاف، مما يسبب ملايين العمليات.    │
├────────────────────────┼───────────────────────────────────────────────┤
│ 2. Rendering / Copying │ تكرار نسخ المصفوفات الكبيرة:                 │
│    (CPU-Memory Bandwidth) `variables.drawn_frame.copy()` و `hand.copy()` │
│                        │ في كل خطوة مع دمج القنوات الثلاث يدوياً عبر   │
│                        │ تعيين الشرائح `[:, :, 0]`, `[:, :, 1]`.      │
├────────────────────────┼───────────────────────────────────────────────┤
│ 3. Two-Pass Encoding   │ دورة كتابة الفيديو المزدوجة (Disk I/O):       │
│    (Disk & Transcoding)│ أولاً: كتابة فيديو كامل غير مضغوط عبر OpenCV. │
│                        │ ثانياً: إعادة قراءته بالكامل وفك ضغطه وضغطه   │
│                        │ مجدداً وحفظه عبر PyAV، ثم حذف الملف الأول.   │
├────────────────────────┼───────────────────────────────────────────────┤
│ 4. Single-Thread Core  │ تنفيذ خوارزمية المسار والرسم بالكامل داخل     │
│    (No Parallelism)    │ خيط واحد (Single CPU Thread) دون استخدام       │
│                        │ SIMD أو Multiprocessing أو تسريع بالعتاد.     │
└────────────────────────┴───────────────────────────────────────────────┘
```

---

## 13. Component Responsibilities & Dependencies (جدول المكونات المعمارية)

| المكون / الملف | المسؤولية البرمجية | الاعتماديات (Dependencies) | يُستدعى بواسطة | يستدعي |
| :--- | :--- | :--- | :--- | :--- |
| **`kivy/main.py`** | إدارة دورة حياة التطبيق، واجهة المستخدم KivyMD، إدارة الأذونات، معالجة الدفعات (Batch Processing)، استدعاء خيوط المعالجة | `kivy`, `kivymd`, `plyer`, `sketchApi`, `threading`, `queue` | نقطة الدخول `__main__` | `initiate_sketch`, `get_split_lens` |
| **`kivy/sketchApi.py`** | النواة الحسابية: تجهيز الصورة، التقسيم الشبكي، حساب المسار، توليد الإطارات، تحويل الفيديو | `cv2`, `numpy`, `av` (PyAV), `math`, `time`, `pathlib` | `main.py` (`DlImg2SktchApp`) | `preprocess_image`, `draw_masked_object`, `ffmpeg_convert` |
| **`kivy/main_layout.kv`** | التصميم التخطيطي لشاشات وعناصر واجهة المستخدم بلغة KV | `kivymd.uix.*`, `screens.divider` | `main.py` عبر `Builder.load_file` | ربط الأحداث بـ `app.*` |
| **`kivy/screens/divider.py`** | عنصر واجهة رسومي مخصص (فاصل مرئي) | `kivy`, `kivymd` | `main_layout.kv`, `main.py` | لا شيء |
| **`kivy/data/images/*`** | أصول رسومية (يد الرسم والقناع والأيقونات) | أصول ثابتة (PNG / ICO) | `sketchApi.py`, `main.py` | لا شيء |

---

## 14. Full Call Graph (مخطط استدعاء العمليات الأساسي)

المسار التنفيذي الدقيق لاستدعاء الدوال بالأسماء الحقيقية الموجودة في الكود:

```text
DlImg2SktchApp.run()  [kivy/main.py]
 │
 ├── DlImg2SktchApp.build()
 │     └── Builder.load_file('main_layout.kv')
 │
 ├── [UI Event] DlImg2SktchApp.open_img_file_manager() -> handle_img_selection()
 │     └── DlImg2SktchApp.select_img_path(path)
 │           ├── get_split_lens(path, max_1080p)  [kivy/sketchApi.py]
 │           │     ├── cv2.imread(path)
 │           │     ├── find_nearest_res(dim)
 │           │     └── common_divisors(img_ht, img_wd)
 │           └── تحديث القائمة المنسدلة للسرعات في الواجهة
 │
 └── [UI Event] DlImg2SktchApp.submit_sketch_req()
       └── Thread(target=initiate_sketch, kwargs={...}).start()
             │
             ▼
       initiate_sketch(...)  [kivy/sketchApi.py]
         ├── cv2.imread(image_path)
         ├── resize_with_padding(...) [إذا تطلب max_1080p]
         ├── AllVariables(...) [تهيئة كائن الحالة]
         │
         ├── draw_whiteboard_animations(...)
         │     ├── preprocess_image(img, variables)
         │     │     ├── cv2.resize(...)
         │     │     ├── cv2.cvtColor(..., COLOR_BGR2GRAY)
         │     │     ├── cv2.createCLAHE(...)
         │     │     └── cv2.adaptiveThreshold(..., ADAPTIVE_THRESH_GAUSSIAN_C, THRESH_BINARY)
         │     │
         │     ├── preprocess_hand_image(hand_path, hand_mask_path, variables)
         │     │     ├── cv2.imread(...)
         │     │     └── get_extreme_coordinates(hand_mask)
         │     │
         │     ├── cv2.VideoWriter(save_video_path, fourcc, frame_rate, (resize_wd, resize_ht))
         │     │
         │     ├── draw_masked_object(variables, skip_rate=...)
         │     │     ├── np.split(img_thresh, n_cuts_horizontal, axis=-1)
         │     │     ├── np.split(..., n_cuts_vertical, axis=-2)
         │     │     ├── np.where(cut_having_black > 0)
         │     │     │
         │     │     └── while len(cut_black_indices) > 1:
         │     │           ├── [لصق المربع في variables.drawn_frame]
         │     │           ├── draw_hand_on_img(...) [إذا variables.draw_hand == True]
         │     │           ├── euc_dist(cut_black_indices, selected_ind_val)
         │     │           ├── np.argmin(euc_arr) [تحديد المربع التالي]
         │     │           ├── if counter % skip_rate == 0:
         │     │           │     └── variables.video_object.write(drawn_frame_with_hand)
         │     │           └── Clock.schedule_once(progress_updater)
         │     │
         │     ├── [إضافة إطارات النهاية الثابتة]
         │     │     └── for i in range(...): variables.video_object.write(end_img)
         │     │
         │     └── variables.video_object.release()
         │
         ├── ffmpeg_convert(save_video_path, ffmpeg_video_path, platform)
         │     ├── av.open(source_vid, "r")
         │     ├── av.open(dest_vid, "w")
         │     ├── out_stream.encode(frame) -> output_container.mux(packet)
         │     └── os.unlink(save_video_path) [حذف الملف المؤقت]
         │
         └── Clock.schedule_once(callback) -> DlImg2SktchApp.task_complete_callback()
               └── DlImg2SktchApp.set_video_player()
```

---

## 15. Critical Files Matrix (جدول تصنيف الملفات)

| اسم الملف | المسار | درجة الأهمية | المسؤولية البرمجية | المكونات التي تستخدمه |
| :--- | :--- | :--- | :--- | :--- |
| **`sketchApi.py`** | `kivy/sketchApi.py` | **CRITICAL** | النواة الحركية والرياضية الكاملة لمعالجة الصورة، التقطيع الشبكي، حساب مسار الرسم، دمج اليد، وتشفير الفيديو | `main.py` |
| **`main.py`** | `kivy/main.py` | **CRITICAL** | المحرك الرئيسي للتطبيق، ربط واجهة المستخدم، إدارة سلاسل التنفيذ، ومعالجة أحداث المنصات | Kivy Runtime / المستخدم |
| **`main_layout.kv`** | `kivy/main_layout.kv` | **UI** | توصيف الواجهة الرسومية وهيكلية العناصر والتحكم بالخصائص | `main.py` |
| **`drawing-hand.png`** | `kivy/data/images/drawing-hand.png` | **Important** | صورة اليد المستخدمة للدمج فوق إطارات الرسم | `sketchApi.py` |
| **`hand-mask.png`** | `kivy/data/images/hand-mask.png` | **Important** | قناع الشفافية الخاص بأصل اليد | `sketchApi.py` |
| **`divider.py`** | `kivy/screens/divider.py` | **UI / Utility** | فاصل رسومي مخصص لواجهة KivyMD | `main_layout.kv` |
| **`req_desktop.txt`** | `kivy/req_desktop.txt` | **Important** | تعريف حزم بايثون المطلوبة لبيئة سطح المكتب | نظام التثبيت (pip) |
| **`buildozer.spec`** | `kivy/buildozer.spec` | **Optional** | إعدادات بناء حزمة أندرويد APK | Buildozer Tool |
| **`dlDesktop.spec`** | `kivy/dlDesktop.spec` | **Optional** | إعدادات حزم التطبيق التنفيذي عبر PyInstaller | PyInstaller |

---

## 16. Behavior under Different Image Types (تحليل استجابة الخوارزمية لأنواع الصور)

بناءً على المعمارية المكتشفة (العتبة التكيفية + التقطيع الشبكي):

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                    Image Type Behavioral Expectations                     │
├──────────────────────────┬────────────────────────────────────────────────┤
│ نوع الصورة               │ السلوك البرمجي والنتيجة الفعلية المتوقعة       │
├──────────────────────────┼────────────────────────────────────────────────┤
│ A. Line Art نظيفة        │ - أداء مثالي: العتبة التكيفية تعزل الخطوط       │
│    (خلفية بيضاء وخطوط سوداء)│   السوداء بدقة.                                 │
│                          │ - الرسم يظهر كأنه تتبع حقيقي للخطوط.           │
├──────────────────────────┼────────────────────────────────────────────────┤
│ B. صورة فوتوغرافية       │ - ضعف شديد: الـ Adaptive Threshold سينتج       │
│    (Natural Photo)       │   ضوضاء بصرية هائلة (Salt-and-Pepper noise) في  │
│                          │   المناطق ذات التدرجات الناعمة.                 │
│                          │ - ستعتبر معظم الكتل "محتوية على سواد"، مما     │
│                          │   يجعل اليد ترسم كل نقطة في الصورة وتتحول      │
│                          │   النتيجة إلى كتل فوضوية ومربعات مشوشة.        │
├──────────────────────────┼────────────────────────────────────────────────┤
│ C. صورة تحتوي على نصوص   │ - أداء جيد جداً: النصوص تكون واضحة ومتباينة.    │
│    (Text / Typography)   │ - ترتيب الرسم سيعتمد على قرب الحروف، فينتقل     │
│                          │   من حرف لأقرب حرف مجاور له.                   │
├──────────────────────────┼────────────────────────────────────────────────┤
│ D. كائنات متعددة منفصلة  │ - سيتم رسم الكائن الأول بالكامل، ثم تنتقل اليد │
│    (Multiple Objects)    │   بقفزة مستقيمة (Jump) إلى أقرب كائن مجاور     │
│                          │   بسبب خوارزمية الجار الأقرب.                  │
├──────────────────────────┼────────────────────────────────────────────────┤
│ E. خلفية معقدة           │ - انهيار جمالي: الخلفية المعقدة ستنتج آلاف     │
│    (Complex Background)  │   البقع الداكنة في `img_thresh`، وستقضي اليد   │
│                          │   معظم الوقت ترسم تشويش الخلفية.               │
├──────────────────────────┼────────────────────────────────────────────────┤
│ F. رسم Sketch جاهز       │ - أداء ممتاز: الصورة مهيأة بطبيعتها لمطابقة     │
│    (Clean Sketch)        │   افتراضات الخوارزمية.                         │
└──────────────────────────┴────────────────────────────────────────────────┘
```

---

## 17. What We Now Know (ما تم إثباته بالدليل القاطع من الكود)

1. **الآلية الحقيقية**: المشروع لا يستخرج Strokes ولا مسارات متجهة، بل يعتمد على تقطيع شبكي ثنائي الأبعاد لمصفوفة العتبة التكيفية (Adaptive Threshold Grid).
2. **محرك الحركة**: الحركة تتولد عبر كشف تدريجي لبلاطات المربعات ($N \times N$) بترتيب الجار الأقرب، مع حفظ إطار كل `skip_rate` خطوة.
3. **تشفير الفيديو**: يتم عبر مرحلتين؛ الأولى تسجيل BGR خام بواسطة `cv2.VideoWriter`، والثانية إعادة ضغط بـ H.264 عبر مكتبة `PyAV`.
4. **عنصر اليد**: مجرد صورة شفافة ثابتة مقتطعة تُركب فوق الإطار عبر مصفوفة ألفا رياضية عند إحداثيات مركز المربع الحالي، وهي قابلة للتعطيل بالكامل.
5. **الذاكرة والأداء**: لا يتم استهلاك مساحة القرص لحفظ إطارات فردية (Images Sequence)، بل يتم البث المباشر للإطار من الرام إلى كائن الفيديو.

---

## 18. Unknowns & Inactive Code in Current Repository (النقاط الملتبسة والأكواد الخاملة)

أثناء فحص الأسطر البرمجية بدقة، تم رصد الملاحظات التقنية التالية:

1. **كود غير فعال (Dead Code - CLAHE)**:
   في `sketchApi.py:39-45`، يتم استدعاء CLAHE وحساب `cl1` من `img_gray`، لكن في السطر 44 يتم تمرير `img_gray` الأصلي إلى `cv2.adaptiveThreshold` وليس `cl1`، مما يعني أن عملية موازنة الهيستوجرام لا تؤثر إطلاقاً على النتيجة النهائية.
2. **ميزة الأقنعة وتجزئة الكائنات (`mask_path` / `object_mask`)**:
   في `sketchApi.py:303-354`، توجد بنية لمعالجة الأقنعة المخصصة (`object_mask`) من ملفات JSON (`object_masks["shapes"]`) ورسم الكائنات ثم الخلفية؛ ومع ذلك، تم تثبيت `mask_path = None` في السطر 532 ولم يتم تفعيل أي واجهة لاختيار أو تمرير ملفات الأقنعة من واجهة Kivy في الإصدار الحالي.

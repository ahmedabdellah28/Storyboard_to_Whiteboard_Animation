# تقرير فحص التوقيت الحقيقي لطبقة Visual Beat (Real-World Timing Audit Report)

تم تشغيل هذا الفحص الشامل باستخدام **الملفات الحقيقية للمشروع** (صور الاستوري بورد الفعلية + ملف الصوت الموحد Master Audio + ملف الترجمة الحقيقي SRT)، لاستخراج تقرير التوقيت الدقيق لكل نبضة بصرية (Visual Beat) على النحو التالي:

## 1. 12-Panel Storyboard (Sheet 1 - Characters & Text Cards)
- **ملف الصورة:** `ChatGPT Image Sep 17, 2026, 06_05_13 PM.png`
- **عدد البانلات المكتشفة:** 12
- **المدة الصوتية المخصصة:** 84.30 ثانية
- **عدد النبضات البصرية المنفذة:** 12

### 📍 Visual Beat: `vbeat_01` (Panel 1)
- **Speech Window:** `[00.00s -> 04.20s]` (المدة: **4.20s**)
- **Visual Window:** `[00.00s -> 08.10s]` (المدة: **8.10s**)
- **النص المنطوق:** *"خلينا نبدا من أول مستوى، المستوى التأسيسي، اللي يكون فيه معدل الذكاء أ..."*
- **Primary Elements:** `['Panel 01 - Character / Person', 'Panel 01 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `['Panel 01 - Title', 'Panel 01 - Text_line', 'Panel 01 - Text_line', 'Panel 01 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 01 - Character / Person** | `PRIMARY` | `00.00s` | `01.78s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 01 - Character / Person** | `PRIMARY` | `01.28s` | `03.06s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 01 - Title** | `DECORATIVE` | `02.56s` | `02.98s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 01 - Text_line** | `DECORATIVE` | `02.87s` | `03.29s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 01 - Text_line** | `DECORATIVE` | `03.17s` | `03.59s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 01 - Text_line** | `DECORATIVE` | `03.47s` | `03.89s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_02` (Panel 2)
- **Speech Window:** `[08.10s -> 11.40s]` (المدة: **3.30s**)
- **Visual Window:** `[08.10s -> 19.20s]` (المدة: **11.10s**)
- **النص المنطوق:** *"لكن بعيداً عن الأرقام، كيف تكون الحياة من داخل هذا المستوى؟ ببساطة الد..."*
- **Primary Elements:** `['Panel 02 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `[]`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 02 - Character / Person** | `PRIMARY` | `08.10s` | `09.88s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |

---
### 📍 Visual Beat: `vbeat_03` (Panel 3)
- **Speech Window:** `[19.20s -> 23.40s]` (المدة: **4.20s**)
- **Visual Window:** `[19.20s -> 30.60s]` (المدة: **11.40s**)
- **النص المنطوق:** *"له نكتة فيها تلاعب بالكلمات، ممكن يطالع فيك كأن مخه للتو قال لك إيرور...."*
- **Primary Elements:** `['Panel 03 - Title']`
- **Secondary Elements:** `['Panel 03 - Text Box / Card', 'Panel 03 - Text Box / Card', 'Panel 03 - Text Box / Card', 'Panel 03 - Text Box / Card', 'Panel 03 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 03 - Text_line', 'Panel 03 - Card Text Line 1', 'Panel 03 - Card Text Line 2', 'Panel 03 - Card Text Line 1', 'Panel 03 - Card Text Line 2', 'Panel 03 - Card Text Line 3', 'Panel 03 - Card Text Line 1', 'Panel 03 - Card Text Line 2', 'Panel 03 - Card Text Line 3', 'Panel 03 - Card Text Line 4', 'Panel 03 - Card Text Line 1', 'Panel 03 - Card Text Line 2', 'Panel 03 - Card Text Line 3']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 03 - Title** | `PRIMARY` | `19.20s` | `20.12s` | `0.92s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 03 - Text Box / Card** | `SECONDARY` | `19.86s` | `20.76s` | `0.90s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 03 - Text Box / Card** | `SECONDARY` | `20.51s` | `21.41s` | `0.90s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 03 - Text Box / Card** | `SECONDARY` | `21.16s` | `22.06s` | `0.90s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 03 - Text Box / Card** | `SECONDARY` | `21.81s` | `22.71s` | `0.90s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 03 - Icon / Graphic** | `SECONDARY` | `22.45s` | `23.05s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 03 - Text_line** | `DECORATIVE` | `22.89s` | `23.31s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 1** | `DECORATIVE` | `23.19s` | `23.61s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 2** | `DECORATIVE` | `23.49s` | `23.91s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 1** | `DECORATIVE` | `23.79s` | `24.21s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 2** | `DECORATIVE` | `24.10s` | `24.52s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 3** | `DECORATIVE` | `24.40s` | `24.82s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 1** | `DECORATIVE` | `24.70s` | `25.12s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 2** | `DECORATIVE` | `25.00s` | `25.42s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 3** | `DECORATIVE` | `25.31s` | `25.73s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 4** | `DECORATIVE` | `25.61s` | `26.03s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 1** | `DECORATIVE` | `25.91s` | `26.33s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 2** | `DECORATIVE` | `26.21s` | `26.63s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Card Text Line 3** | `DECORATIVE` | `26.52s` | `26.94s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_04` (Panel 4)
- **Speech Window:** `[30.60s -> 34.80s]` (المدة: **4.20s**)
- **Visual Window:** `[30.60s -> 41.70s]` (المدة: **11.10s**)
- **النص المنطوق:** *"لكن اذا نزل المستوى تحت 35، هنا يصير الشخص معتمداً بشكل كبير على غيره ..."*
- **Primary Elements:** `['Panel 04 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `['Panel 04 - Title', 'Panel 04 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 04 - Character / Person** | `PRIMARY` | `30.60s` | `32.38s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 04 - Title** | `DECORATIVE` | `31.88s` | `32.30s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 04 - Text_line** | `DECORATIVE` | `32.18s` | `32.60s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_05` (Panel 5)
- **Speech Window:** `[41.70s -> 42.30s]` (المدة: **0.60s**)
- **Visual Window:** `[41.70s -> 50.10s]` (المدة: **8.40s**)
- **النص المنطوق:** *"مختلف تماماً. هؤلاء يعيشون بعيداً عن كثير من التعقيدات اللي تستهلكنا ا..."*
- **Primary Elements:** `['Panel 05 - Character / Person', 'Panel 05 - Character / Person']`
- **Secondary Elements:** `['Panel 05 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 05 - Title', 'Panel 05 - Text_line', 'Panel 05 - Text_line', 'Panel 05 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 05 - Character / Person** | `PRIMARY` | `41.70s` | `43.48s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 05 - Character / Person** | `PRIMARY` | `42.98s` | `44.76s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 05 - Icon / Graphic** | `SECONDARY` | `44.26s` | `44.86s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 05 - Title** | `DECORATIVE` | `44.70s` | `45.12s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 05 - Text_line** | `DECORATIVE` | `45.00s` | `45.42s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 05 - Text_line** | `DECORATIVE` | `45.30s` | `45.72s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 05 - Text_line** | `DECORATIVE` | `45.60s` | `46.02s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_06` (Panel 6)
- **Speech Window:** `[50.10s -> 54.00s]` (المدة: **3.90s**)
- **Visual Window:** `[50.10s -> 56.10s]` (المدة: **6.00s**)
- **النص المنطوق:** *"الرسالة، ولا يشيل هم بعد عشر سنين، ولا يدخل نفسه في الف احتمال. هو ببس..."*
- **Primary Elements:** `['Panel 06 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `['Panel 06 - Title', 'Panel 06 - Text_line', 'Panel 06 - Text_line', 'Panel 06 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 06 - Character / Person** | `PRIMARY` | `50.10s` | `51.88s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 06 - Title** | `DECORATIVE` | `51.38s` | `51.80s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 06 - Text_line** | `DECORATIVE` | `51.68s` | `52.10s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 06 - Text_line** | `DECORATIVE` | `51.99s` | `52.41s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 06 - Text_line** | `DECORATIVE` | `52.29s` | `52.71s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_07` (Panel 7)
- **Speech Window:** `[56.10s -> 58.80s]` (المدة: **2.70s**)
- **Visual Window:** `[56.10s -> 64.20s]` (المدة: **8.10s**)
- **النص المنطوق:** *"من 70 الى 84، ندخل على مستوى ذكاء الشوارع. هذول يمثلون تقريباً 14% من ..."*
- **Primary Elements:** `['Panel 07 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `['Panel 07 - Title', 'Panel 07 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 07 - Character / Person** | `PRIMARY` | `56.10s` | `57.88s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 07 - Title** | `DECORATIVE` | `57.38s` | `57.80s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 07 - Text_line** | `DECORATIVE` | `57.68s` | `58.10s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_08` (Panel 8)
- **Speech Window:** `[64.20s -> 66.90s]` (المدة: **2.70s**)
- **Visual Window:** `[64.20s -> 71.10s]` (المدة: **6.90s**)
- **النص المنطوق:** *"رياضيات، فيزياء، معادلات طويلة، نص أدبي من ثلاث صفحات... يعطى هالكتاب ..."*
- **Primary Elements:** `['Panel 08 - Character / Person', 'Panel 08 - Character / Person']`
- **Secondary Elements:** `['Panel 08 - Icon / Graphic', 'Panel 08 - Icon / Graphic']`
- **Decorative Elements:** `[]`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 08 - Character / Person** | `PRIMARY` | `64.20s` | `65.98s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 08 - Character / Person** | `PRIMARY` | `65.48s` | `67.26s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 08 - Icon / Graphic** | `SECONDARY` | `66.76s` | `67.36s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 08 - Icon / Graphic** | `SECONDARY` | `67.20s` | `67.80s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |

---
### 📍 Visual Beat: `vbeat_09` (Panel 9)
- **Speech Window:** `[71.10s -> 72.30s]` (المدة: **1.20s**)
- **Visual Window:** `[71.10s -> 74.40s]` (المدة: **3.30s**)
- **النص المنطوق:** *"تعطلت سيارتك في البر؟ هنا يبدأ السحر. ما عنده القطعة المناسبة؟..."*
- **Primary Elements:** `['Panel 09 - Character / Person', 'Panel 09 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `['Panel 09 - Title', 'Panel 09 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 09 - Character / Person** | `PRIMARY` | `71.10s` | `72.62s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 09 - Character / Person** | `PRIMARY` | `72.19s` | `73.71s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 09 - Title** | `DECORATIVE` | `73.29s` | `73.64s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 09 - Text_line** | `DECORATIVE` | `73.54s` | `73.89s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_10` (Panel 10)
- **Speech Window:** `[74.40s -> 74.70s]` (المدة: **0.30s**)
- **Visual Window:** `[74.40s -> 80.40s]` (المدة: **6.00s**)
- **النص المنطوق:** *"عادي! ما عنده الادوات الكاملة، ما يفرق. يلفها بشطرطون، يربطها بمغاط، ي..."*
- **Primary Elements:** `['Panel 10 - Text_line']`
- **Secondary Elements:** `['Panel 10 - Icon / Graphic', 'Panel 10 - Icon / Graphic', 'Panel 10 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 10 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 10 - Text_line** | `PRIMARY` | `74.40s` | `75.32s` | `0.92s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 10 - Text_line** | `PRIMARY` | `75.06s` | `75.98s` | `0.92s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 10 - Icon / Graphic** | `SECONDARY` | `75.72s` | `76.32s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 10 - Icon / Graphic** | `SECONDARY` | `76.16s` | `76.76s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 10 - Icon / Graphic** | `SECONDARY` | `76.59s` | `77.19s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |

---
### 📍 Visual Beat: `vbeat_11` (Panel 11)
- **Speech Window:** `[80.40s -> 81.90s]` (المدة: **1.50s**)
- **Visual Window:** `[80.40s -> 88.80s]` (المدة: **8.40s**)
- **النص المنطوق:** *"وانت فعلا تشغل السيارة وتمشي. هو ممكن ما يقدر يكتب لك مقال اكاديمي مرت..."*
- **Primary Elements:** `['Panel 11 - Character / Person', 'Panel 11 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `[]`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 11 - Character / Person** | `PRIMARY` | `80.40s` | `82.18s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 11 - Character / Person** | `PRIMARY` | `81.68s` | `83.46s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |

---
### 📍 Visual Beat: `vbeat_12` (Panel 12)
- **Speech Window:** `[88.80s -> 91.80s]` (المدة: **3.00s**)
- **Visual Window:** `[88.80s -> 89.30s]` (المدة: **0.50s**)
- **النص المنطوق:** *"هذي عقول مبرمجة على المشاكل اللي تنشاف بالعين وتلمس باليد. ما يهمه كثي..."*
- **Primary Elements:** `['Panel 12 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `['Panel 12 - Title', 'Panel 12 - Text_line', 'Panel 12 - Text_line', 'Panel 12 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 12 - Character / Person** | `PRIMARY` | `88.80s` | `89.30s` | `0.50s` | `0.20s` | `0.00s` | `2.00x` | Primary focal subject drawing |
| **Panel 12 - Title** | `DECORATIVE` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 12 - Text_line** | `DECORATIVE` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 12 - Text_line** | `DECORATIVE` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 12 - Text_line** | `DECORATIVE` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |

---
## 2. 16-Panel Storyboard (Test Archive Sheet - Multi-Grid)
- **ملف الصورة:** `ChatGPT Image Sep 5, 2026, 03_23_52 PM.png`
- **عدد البانلات المكتشفة:** 16
- **المدة الصوتية المخصصة:** 60.00 ثانية
- **عدد النبضات البصرية المنفذة:** 16

### 📍 Visual Beat: `vbeat_01` (Panel 1)
- **Speech Window:** `[00.00s -> 04.20s]` (المدة: **4.20s**)
- **Visual Window:** `[00.00s -> 04.50s]` (المدة: **4.50s**)
- **النص المنطوق:** *"خلينا نبدا من أول مستوى، المستوى التأسيسي، اللي يكون فيه معدل الذكاء أ..."*
- **Primary Elements:** `['Panel 01 - Character / Person', 'Panel 01 - Character / Person']`
- **Secondary Elements:** `['Panel 01 - Icon / Graphic', 'Panel 01 - Question Mark / Symbol']`
- **Decorative Elements:** `['Panel 01 - Title', 'Panel 01 - Text_line', 'Panel 01 - Text_line', 'Panel 01 - Text_line', 'Panel 01 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 01 - Character / Person** | `PRIMARY` | `00.00s` | `01.52s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 01 - Character / Person** | `PRIMARY` | `01.09s` | `02.61s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 01 - Icon / Graphic** | `SECONDARY` | `02.19s` | `02.64s` | `0.45s` | `0.28s` | `0.00s` | `1.33x` | Secondary context drawing with NATURAL overlap |
| **Panel 01 - Question Mark / Symbol** | `SECONDARY` | `02.51s` | `02.96s` | `0.45s` | `0.28s` | `0.00s` | `1.33x` | Secondary context drawing with NATURAL overlap |
| **Panel 01 - Title** | `DECORATIVE` | `02.84s` | `03.19s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 01 - Text_line** | `DECORATIVE` | `03.09s` | `03.44s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 01 - Text_line** | `DECORATIVE` | `03.34s` | `03.69s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 01 - Text_line** | `DECORATIVE` | `03.59s` | `03.94s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 01 - Text_line** | `DECORATIVE` | `03.84s` | `04.19s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_02` (Panel 2)
- **Speech Window:** `[04.50s -> 08.10s]` (المدة: **3.60s**)
- **Visual Window:** `[04.50s -> 11.40s]` (المدة: **6.90s**)
- **النص المنطوق:** *"طبياً، هل فئة تدخل ضمن الإعاقة الفكرية وتمثل تقريباً 2% من البشر. لكن ..."*
- **Primary Elements:** `['Panel 02 - Character / Person', 'Panel 02 - Character / Person']`
- **Secondary Elements:** `['Panel 02 - Emoji / Expression']`
- **Decorative Elements:** `['Panel 02 - Title', 'Panel 02 - Text_line', 'Panel 02 - Text_line', 'Panel 02 - Text_line', 'Panel 02 - Text_line', 'Panel 02 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 02 - Character / Person** | `PRIMARY` | `04.50s` | `06.28s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 02 - Character / Person** | `PRIMARY` | `05.78s` | `07.56s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 02 - Emoji / Expression** | `SECONDARY` | `07.06s` | `07.66s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 02 - Title** | `DECORATIVE` | `07.50s` | `07.92s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 02 - Text_line** | `DECORATIVE` | `07.80s` | `08.22s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 02 - Text_line** | `DECORATIVE` | `08.10s` | `08.52s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 02 - Text_line** | `DECORATIVE` | `08.40s` | `08.82s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 02 - Text_line** | `DECORATIVE` | `08.70s` | `09.12s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 02 - Text_line** | `DECORATIVE` | `09.01s` | `09.43s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_03` (Panel 3)
- **Speech Window:** `[11.40s -> 15.00s]` (المدة: **3.60s**)
- **Visual Window:** `[11.40s -> 19.20s]` (المدة: **7.80s**)
- **النص المنطوق:** *"ببساطة الدماغ هنا يواجه صعوبة كبيرة في معالجة المعلومات المعقدة والمفا..."*
- **Primary Elements:** `['Panel 03 - Text_line']`
- **Secondary Elements:** `['Panel 03 - Icon / Graphic', 'Panel 03 - Icon / Graphic', 'Panel 03 - Icon / Graphic', 'Panel 03 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 03 - Title', 'Panel 03 - Text_line', 'Panel 03 - Text_line', 'Panel 03 - Text_line', 'Panel 03 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 03 - Text_line** | `PRIMARY` | `11.40s` | `12.32s` | `0.92s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 03 - Text_line** | `PRIMARY` | `12.06s` | `12.98s` | `0.92s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 03 - Text_line** | `PRIMARY` | `12.72s` | `13.64s` | `0.92s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 03 - Text_line** | `PRIMARY` | `13.39s` | `14.31s` | `0.92s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 03 - Text_line** | `PRIMARY` | `14.05s` | `14.97s` | `0.92s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 03 - Icon / Graphic** | `SECONDARY` | `14.71s` | `15.31s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 03 - Icon / Graphic** | `SECONDARY` | `15.14s` | `15.74s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 03 - Icon / Graphic** | `SECONDARY` | `15.58s` | `16.18s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 03 - Icon / Graphic** | `SECONDARY` | `16.01s` | `16.61s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 03 - Title** | `DECORATIVE` | `16.44s` | `16.86s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_04` (Panel 4)
- **Speech Window:** `[19.20s -> 23.40s]` (المدة: **4.20s**)
- **Visual Window:** `[19.20s -> 30.60s]` (المدة: **11.40s**)
- **النص المنطوق:** *"له نكتة فيها تلاعب بالكلمات، ممكن يطالع فيك كأن مخه للتو قال لك إيرور...."*
- **Primary Elements:** `['Panel 04 - Character / Person']`
- **Secondary Elements:** `['Panel 04 - Icon / Graphic', 'Panel 04 - Icon / Graphic', 'Panel 04 - Emoji / Expression']`
- **Decorative Elements:** `['Panel 04 - Title', 'Panel 04 - Text_line', 'Panel 04 - Text_line', 'Panel 04 - Text_line', 'Panel 04 - Text_line', 'Panel 04 - Text_line', 'Panel 04 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 04 - Character / Person** | `PRIMARY` | `19.20s` | `20.98s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 04 - Icon / Graphic** | `SECONDARY` | `20.48s` | `21.08s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 04 - Icon / Graphic** | `SECONDARY` | `20.91s` | `21.51s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 04 - Emoji / Expression** | `SECONDARY` | `21.35s` | `21.95s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 04 - Title** | `DECORATIVE` | `21.78s` | `22.20s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 04 - Text_line** | `DECORATIVE` | `22.08s` | `22.50s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 04 - Text_line** | `DECORATIVE` | `22.38s` | `22.80s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 04 - Text_line** | `DECORATIVE` | `22.68s` | `23.10s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 04 - Text_line** | `DECORATIVE` | `22.99s` | `23.41s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 04 - Text_line** | `DECORATIVE` | `23.29s` | `23.71s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 04 - Text_line** | `DECORATIVE` | `23.59s` | `24.01s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_05` (Panel 5)
- **Speech Window:** `[30.60s -> 34.80s]` (المدة: **4.20s**)
- **Visual Window:** `[30.60s -> 37.50s]` (المدة: **6.90s**)
- **النص المنطوق:** *"لكن اذا نزل المستوى تحت 35، هنا يصير الشخص معتمداً بشكل كبير على غيره ..."*
- **Primary Elements:** `['Panel 05 - Character / Person']`
- **Secondary Elements:** `['Panel 05 - Text Box / Card', 'Panel 05 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 05 - Title', 'Panel 05 - Text_line', 'Panel 05 - Text_line', 'Panel 05 - Text_line', 'Panel 05 - Card Text Line 1']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 05 - Character / Person** | `PRIMARY` | `30.60s` | `32.38s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 05 - Text Box / Card** | `SECONDARY` | `31.88s` | `32.78s` | `0.90s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 05 - Icon / Graphic** | `SECONDARY` | `32.53s` | `33.13s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 05 - Title** | `DECORATIVE` | `32.96s` | `33.38s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 05 - Text_line** | `DECORATIVE` | `33.26s` | `33.68s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 05 - Text_line** | `DECORATIVE` | `33.57s` | `33.99s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 05 - Text_line** | `DECORATIVE` | `33.87s` | `34.29s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 05 - Card Text Line 1** | `DECORATIVE` | `34.17s` | `34.59s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_06` (Panel 6)
- **Speech Window:** `[37.50s -> 41.70s]` (المدة: **4.20s**)
- **Visual Window:** `[37.50s -> 42.30s]` (المدة: **4.80s**)
- **النص المنطوق:** *"والغريب ان البعض يشوف ان هذا المستوى ما فيه الا سلبيات، لكن في جانب مخ..."*
- **Primary Elements:** `['Panel 06 - Character / Person']`
- **Secondary Elements:** `['Panel 06 - Text Box / Card', 'Panel 06 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 06 - Title', 'Panel 06 - Text_line', 'Panel 06 - Text_line', 'Panel 06 - Text_line', 'Panel 06 - Text_line', 'Panel 06 - Text_line', 'Panel 06 - Card Text Line 1']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 06 - Character / Person** | `PRIMARY` | `37.50s` | `39.02s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 06 - Text Box / Card** | `SECONDARY` | `38.59s` | `39.36s` | `0.77s` | `0.28s` | `0.00s` | `1.17x` | Secondary context drawing with NATURAL overlap |
| **Panel 06 - Icon / Graphic** | `SECONDARY` | `39.15s` | `39.66s` | `0.51s` | `0.28s` | `0.00s` | `1.18x` | Secondary context drawing with NATURAL overlap |
| **Panel 06 - Title** | `DECORATIVE` | `39.52s` | `39.87s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 06 - Text_line** | `DECORATIVE` | `39.77s` | `40.12s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 06 - Text_line** | `DECORATIVE` | `40.02s` | `40.37s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 06 - Text_line** | `DECORATIVE` | `40.27s` | `40.62s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 06 - Text_line** | `DECORATIVE` | `40.52s` | `40.87s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 06 - Text_line** | `DECORATIVE` | `40.78s` | `41.13s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 06 - Card Text Line 1** | `DECORATIVE` | `41.03s` | `41.38s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_07` (Panel 7)
- **Speech Window:** `[42.30s -> 45.90s]` (المدة: **3.60s**)
- **Visual Window:** `[42.30s -> 50.10s]` (المدة: **7.80s**)
- **النص المنطوق:** *"هؤلاء يعيشون بعيداً عن كثير من التعقيدات اللي تستهلكنا احنا كل يوم. ما..."*
- **Primary Elements:** `['Panel 07 - Character / Person']`
- **Secondary Elements:** `['Panel 07 - Emoji / Expression', 'Panel 07 - Emoji / Expression']`
- **Decorative Elements:** `['Panel 07 - Title', 'Panel 07 - Text_line', 'Panel 07 - Text_line', 'Panel 07 - Text_line', 'Panel 07 - Text_line', 'Panel 07 - Text_line', 'Panel 07 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 07 - Character / Person** | `PRIMARY` | `42.30s` | `44.08s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 07 - Emoji / Expression** | `SECONDARY` | `43.58s` | `44.18s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 07 - Emoji / Expression** | `SECONDARY` | `44.01s` | `44.61s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 07 - Title** | `DECORATIVE` | `44.45s` | `44.87s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 07 - Text_line** | `DECORATIVE` | `44.75s` | `45.17s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 07 - Text_line** | `DECORATIVE` | `45.05s` | `45.47s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 07 - Text_line** | `DECORATIVE` | `45.35s` | `45.77s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 07 - Text_line** | `DECORATIVE` | `45.66s` | `46.08s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 07 - Text_line** | `DECORATIVE` | `45.96s` | `46.38s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 07 - Text_line** | `DECORATIVE` | `46.26s` | `46.68s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_08` (Panel 8)
- **Speech Window:** `[50.10s -> 54.00s]` (المدة: **3.90s**)
- **Visual Window:** `[50.10s -> 56.10s]` (المدة: **6.00s**)
- **النص المنطوق:** *"الرسالة، ولا يشيل هم بعد عشر سنين، ولا يدخل نفسه في الف احتمال. هو ببس..."*
- **Primary Elements:** `['Panel 08 - Character / Person', 'Panel 08 - Character / Person']`
- **Secondary Elements:** `['Panel 08 - Icon / Graphic', 'Panel 08 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 08 - Title', 'Panel 08 - Text_line', 'Panel 08 - Text_line', 'Panel 08 - Text_line', 'Panel 08 - Text_line', 'Panel 08 - Text_line', 'Panel 08 - Text_line', 'Panel 08 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 08 - Character / Person** | `PRIMARY` | `50.10s` | `51.62s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 08 - Character / Person** | `PRIMARY` | `51.19s` | `52.71s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 08 - Icon / Graphic** | `SECONDARY` | `52.29s` | `52.80s` | `0.51s` | `0.28s` | `0.00s` | `1.18x` | Secondary context drawing with NATURAL overlap |
| **Panel 08 - Icon / Graphic** | `SECONDARY` | `52.66s` | `53.17s` | `0.51s` | `0.28s` | `0.00s` | `1.18x` | Secondary context drawing with NATURAL overlap |
| **Panel 08 - Title** | `DECORATIVE` | `53.02s` | `53.37s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 08 - Text_line** | `DECORATIVE` | `53.28s` | `53.63s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 08 - Text_line** | `DECORATIVE` | `53.53s` | `53.88s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 08 - Text_line** | `DECORATIVE` | `53.78s` | `54.13s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 08 - Text_line** | `DECORATIVE` | `54.03s` | `54.38s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 08 - Text_line** | `DECORATIVE` | `54.28s` | `54.63s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 08 - Text_line** | `DECORATIVE` | `54.54s` | `54.89s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 08 - Text_line** | `DECORATIVE` | `54.79s` | `55.14s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_09` (Panel 9)
- **Speech Window:** `[56.10s -> 58.80s]` (المدة: **2.70s**)
- **Visual Window:** `[56.10s -> 62.70s]` (المدة: **6.60s**)
- **النص المنطوق:** *"من 70 الى 84، ندخل على مستوى ذكاء الشوارع. هذول يمثلون تقريباً 14% من ..."*
- **Primary Elements:** `['Panel 09 - Character / Person', 'Panel 09 - Character / Person']`
- **Secondary Elements:** `['Panel 09 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 09 - Title', 'Panel 09 - Underline', 'Panel 09 - Text_line', 'Panel 09 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 09 - Character / Person** | `PRIMARY` | `56.10s` | `57.88s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 09 - Character / Person** | `PRIMARY` | `57.38s` | `59.16s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 09 - Icon / Graphic** | `SECONDARY` | `58.66s` | `59.26s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 09 - Title** | `DECORATIVE` | `59.10s` | `59.52s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 09 - Underline** | `DECORATIVE` | `59.40s` | `59.82s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 09 - Text_line** | `DECORATIVE` | `59.70s` | `60.12s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 09 - Text_line** | `DECORATIVE` | `60.00s` | `60.42s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_10` (Panel 10)
- **Speech Window:** `[62.70s -> 64.20s]` (المدة: **1.50s**)
- **Visual Window:** `[62.70s -> 66.90s]` (المدة: **4.20s**)
- **النص المنطوق:** *"في المدرسة، هنا تبدأ المعاناة. رياضيات، فيزياء، معادلات طويلة، نص أدبي..."*
- **Primary Elements:** `['Panel 10 - Character / Person']`
- **Secondary Elements:** `['Panel 10 - Text Box / Card', 'Panel 10 - Icon / Graphic', 'Panel 10 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 10 - Title', 'Panel 10 - Underline', 'Panel 10 - Text_line', 'Panel 10 - Text_line', 'Panel 10 - Text_line', 'Panel 10 - Text_line', 'Panel 10 - Text_line', 'Panel 10 - Text_line', 'Panel 10 - Text_line', 'Panel 10 - Card Text Line 1']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 10 - Character / Person** | `PRIMARY` | `62.70s` | `64.22s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 10 - Text Box / Card** | `SECONDARY` | `63.79s` | `64.38s` | `0.59s` | `0.28s` | `0.00s` | `1.53x` | Secondary context drawing with NATURAL overlap |
| **Panel 10 - Icon / Graphic** | `SECONDARY` | `64.22s` | `64.61s` | `0.39s` | `0.28s` | `0.00s` | `1.54x` | Secondary context drawing with NATURAL overlap |
| **Panel 10 - Icon / Graphic** | `SECONDARY` | `64.50s` | `64.89s` | `0.39s` | `0.28s` | `0.00s` | `1.54x` | Secondary context drawing with NATURAL overlap |
| **Panel 10 - Title** | `DECORATIVE` | `64.78s` | `65.13s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 10 - Underline** | `DECORATIVE` | `65.03s` | `65.38s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 10 - Text_line** | `DECORATIVE` | `65.28s` | `65.63s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 10 - Text_line** | `DECORATIVE` | `65.54s` | `65.89s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 10 - Text_line** | `DECORATIVE` | `65.79s` | `66.14s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 10 - Text_line** | `DECORATIVE` | `66.04s` | `66.39s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 10 - Text_line** | `DECORATIVE` | `66.29s` | `66.64s` | `0.35s` | `0.26s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 10 - Text_line** | `DECORATIVE` | `66.54s` | `66.89s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 10 - Text_line** | `DECORATIVE` | `66.55s` | `66.90s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 10 - Card Text Line 1** | `DECORATIVE` | `66.55s` | `66.90s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_11` (Panel 11)
- **Speech Window:** `[66.90s -> 69.00s]` (المدة: **2.10s**)
- **Visual Window:** `[66.90s -> 71.10s]` (المدة: **4.20s**)
- **النص المنطوق:** *"يعطى هالكتاب ويمكن يقفله بعد أول فقرة. لكن في الحياة الواقعية، هذول مل..."*
- **Primary Elements:** `['Panel 11 - Character / Person', 'Panel 11 - Character / Person']`
- **Secondary Elements:** `['Panel 11 - Icon / Graphic', 'Panel 11 - Icon / Graphic', 'Panel 11 - Icon / Graphic', 'Panel 11 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 11 - Title', 'Panel 11 - Underline', 'Panel 11 - Text_line', 'Panel 11 - Text_line', 'Panel 11 - Text_line', 'Panel 11 - Text_line', 'Panel 11 - Text_line', 'Panel 11 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 11 - Character / Person** | `PRIMARY` | `66.90s` | `68.42s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 11 - Character / Person** | `PRIMARY` | `67.99s` | `69.51s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 11 - Icon / Graphic** | `SECONDARY` | `69.09s` | `69.48s` | `0.39s` | `0.28s` | `0.00s` | `1.54x` | Secondary context drawing with NATURAL overlap |
| **Panel 11 - Icon / Graphic** | `SECONDARY` | `69.37s` | `69.76s` | `0.39s` | `0.28s` | `0.00s` | `1.54x` | Secondary context drawing with NATURAL overlap |
| **Panel 11 - Icon / Graphic** | `SECONDARY` | `69.65s` | `70.04s` | `0.39s` | `0.28s` | `0.00s` | `1.54x` | Secondary context drawing with NATURAL overlap |
| **Panel 11 - Icon / Graphic** | `SECONDARY` | `69.93s` | `70.32s` | `0.39s` | `0.28s` | `0.00s` | `1.54x` | Secondary context drawing with NATURAL overlap |
| **Panel 11 - Title** | `DECORATIVE` | `70.21s` | `70.56s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 11 - Underline** | `DECORATIVE` | `70.46s` | `70.81s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 11 - Text_line** | `DECORATIVE` | `70.72s` | `71.07s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 11 - Text_line** | `DECORATIVE` | `70.75s` | `71.10s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 11 - Text_line** | `DECORATIVE` | `70.75s` | `71.10s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 11 - Text_line** | `DECORATIVE` | `70.75s` | `71.10s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 11 - Text_line** | `DECORATIVE` | `70.75s` | `71.10s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 11 - Text_line** | `DECORATIVE` | `70.75s` | `71.10s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_12` (Panel 12)
- **Speech Window:** `[71.10s -> 72.30s]` (المدة: **1.20s**)
- **Visual Window:** `[71.10s -> 74.40s]` (المدة: **3.30s**)
- **النص المنطوق:** *"تعطلت سيارتك في البر؟ هنا يبدأ السحر. ما عنده القطعة المناسبة؟..."*
- **Primary Elements:** `['Panel 12 - Character / Person']`
- **Secondary Elements:** `['Panel 12 - Emoji / Expression', 'Panel 12 - Icon / Graphic', 'Panel 12 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 12 - Title', 'Panel 12 - Underline', 'Panel 12 - Text_line', 'Panel 12 - Text_line', 'Panel 12 - Text_line', 'Panel 12 - Text_line', 'Panel 12 - Text_line', 'Panel 12 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 12 - Character / Person** | `PRIMARY` | `71.10s` | `72.62s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 12 - Emoji / Expression** | `SECONDARY` | `72.19s` | `72.58s` | `0.39s` | `0.28s` | `0.00s` | `1.54x` | Secondary context drawing with NATURAL overlap |
| **Panel 12 - Icon / Graphic** | `SECONDARY` | `72.48s` | `72.87s` | `0.39s` | `0.28s` | `0.00s` | `1.54x` | Secondary context drawing with NATURAL overlap |
| **Panel 12 - Icon / Graphic** | `SECONDARY` | `72.76s` | `73.15s` | `0.39s` | `0.28s` | `0.00s` | `1.54x` | Secondary context drawing with NATURAL overlap |
| **Panel 12 - Title** | `DECORATIVE` | `73.04s` | `73.39s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 12 - Underline** | `DECORATIVE` | `73.29s` | `73.64s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 12 - Text_line** | `DECORATIVE` | `73.54s` | `73.89s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 12 - Text_line** | `DECORATIVE` | `73.79s` | `74.14s` | `0.35s` | `0.26s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 12 - Text_line** | `DECORATIVE` | `74.04s` | `74.39s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 12 - Text_line** | `DECORATIVE` | `74.05s` | `74.40s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 12 - Text_line** | `DECORATIVE` | `74.05s` | `74.40s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 12 - Text_line** | `DECORATIVE` | `74.05s` | `74.40s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_13` (Panel 13)
- **Speech Window:** `[74.40s -> 74.70s]` (المدة: **0.30s**)
- **Visual Window:** `[74.40s -> 76.50s]` (المدة: **2.10s**)
- **النص المنطوق:** *"عادي! ما عنده الادوات الكاملة، ما يفرق...."*
- **Primary Elements:** `['Panel 13 - Character / Person']`
- **Secondary Elements:** `['Panel 13 - Icon / Graphic', 'Panel 13 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 13 - Title', 'Panel 13 - Text_line', 'Panel 13 - Text_line', 'Panel 13 - Text_line', 'Panel 13 - Text_line', 'Panel 13 - Text_line', 'Panel 13 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 13 - Character / Person** | `PRIMARY` | `74.40s` | `75.92s` | `1.52s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 13 - Icon / Graphic** | `SECONDARY` | `75.49s` | `75.88s` | `0.39s` | `0.28s` | `0.00s` | `1.54x` | Secondary context drawing with NATURAL overlap |
| **Panel 13 - Icon / Graphic** | `SECONDARY` | `75.78s` | `76.17s` | `0.39s` | `0.28s` | `0.00s` | `1.54x` | Secondary context drawing with NATURAL overlap |
| **Panel 13 - Title** | `DECORATIVE` | `76.06s` | `76.41s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 13 - Text_line** | `DECORATIVE` | `76.15s` | `76.50s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 13 - Text_line** | `DECORATIVE` | `76.15s` | `76.50s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 13 - Text_line** | `DECORATIVE` | `76.15s` | `76.50s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 13 - Text_line** | `DECORATIVE` | `76.15s` | `76.50s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 13 - Text_line** | `DECORATIVE` | `76.15s` | `76.50s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 13 - Text_line** | `DECORATIVE` | `76.15s` | `76.50s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_14` (Panel 14)
- **Speech Window:** `[76.50s -> 80.40s]` (المدة: **3.90s**)
- **Visual Window:** `[76.50s -> 81.90s]` (المدة: **5.40s**)
- **النص المنطوق:** *"يلفها بشطرطون، يربطها بمغاط، يركب حل مؤقت من ثلاث قطع ويقول لك: شغل. و..."*
- **Primary Elements:** `['Panel 14 - Icon / Graphic']`
- **Secondary Elements:** `['Panel 14 - Icon / Graphic', 'Panel 14 - Icon / Graphic', 'Panel 14 - Emoji / Expression', 'Panel 14 - Emoji / Expression', 'Panel 14 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 14 - Title', 'Panel 14 - Underline', 'Panel 14 - Text_line', 'Panel 14 - Text_line', 'Panel 14 - Text_line', 'Panel 14 - Text_line', 'Panel 14 - Text_line', 'Panel 14 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 14 - Icon / Graphic** | `PRIMARY` | `76.50s` | `77.09s` | `0.59s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 14 - Icon / Graphic** | `PRIMARY` | `76.92s` | `77.51s` | `0.59s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 14 - Icon / Graphic** | `PRIMARY` | `77.35s` | `77.94s` | `0.59s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 14 - Icon / Graphic** | `PRIMARY` | `77.77s` | `78.36s` | `0.59s` | `0.55s` | `0.00s` | `1.17x` | Primary focal subject drawing |
| **Panel 14 - Emoji / Expression** | `SECONDARY` | `78.20s` | `78.70s` | `0.50s` | `0.28s` | `0.00s` | `1.20x` | Secondary context drawing with NATURAL overlap |
| **Panel 14 - Emoji / Expression** | `SECONDARY` | `78.56s` | `79.06s` | `0.50s` | `0.28s` | `0.00s` | `1.20x` | Secondary context drawing with NATURAL overlap |
| **Panel 14 - Title** | `DECORATIVE` | `78.92s` | `79.27s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 14 - Underline** | `DECORATIVE` | `79.17s` | `79.52s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 14 - Text_line** | `DECORATIVE` | `79.42s` | `79.77s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 14 - Text_line** | `DECORATIVE` | `79.68s` | `80.03s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 14 - Text_line** | `DECORATIVE` | `79.93s` | `80.28s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 14 - Text_line** | `DECORATIVE` | `80.18s` | `80.53s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 14 - Text_line** | `DECORATIVE` | `80.43s` | `80.78s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 14 - Text_line** | `DECORATIVE` | `80.68s` | `81.03s` | `0.35s` | `0.28s` | `0.00s` | `1.49x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_15` (Panel 15)
- **Speech Window:** `[81.90s -> 86.10s]` (المدة: **4.20s**)
- **Visual Window:** `[81.90s -> 88.80s]` (المدة: **6.90s**)
- **النص المنطوق:** *"هو ممكن ما يقدر يكتب لك مقال اكاديمي مرتب، لكنه يعرف كيف يفك المكينة، ..."*
- **Primary Elements:** `['Panel 15 - Character / Person', 'Panel 15 - Character / Person']`
- **Secondary Elements:** `['Panel 15 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 15 - Title', 'Panel 15 - Underline', 'Panel 15 - Text_line', 'Panel 15 - Text_line', 'Panel 15 - Text_line', 'Panel 15 - Text_line', 'Panel 15 - Text_line', 'Panel 15 - Text_line', 'Panel 15 - Text_line', 'Panel 15 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 15 - Character / Person** | `PRIMARY` | `81.90s` | `83.58s` | `1.68s` | `0.55s` | `0.00s` | `1.06x` | Primary focal subject drawing |
| **Panel 15 - Character / Person** | `PRIMARY` | `83.11s` | `84.79s` | `1.68s` | `0.55s` | `0.00s` | `1.06x` | Primary focal subject drawing |
| **Panel 15 - Icon / Graphic** | `SECONDARY` | `84.32s` | `84.89s` | `0.57s` | `0.28s` | `0.00s` | `1.05x` | Secondary context drawing with NATURAL overlap |
| **Panel 15 - Title** | `DECORATIVE` | `84.73s` | `85.12s` | `0.39s` | `0.28s` | `0.00s` | `1.33x` | Decorative background accent |
| **Panel 15 - Underline** | `DECORATIVE` | `85.01s` | `85.40s` | `0.39s` | `0.28s` | `0.00s` | `1.33x` | Decorative background accent |
| **Panel 15 - Text_line** | `DECORATIVE` | `85.29s` | `85.68s` | `0.39s` | `0.28s` | `0.00s` | `1.33x` | Decorative background accent |
| **Panel 15 - Text_line** | `DECORATIVE` | `85.57s` | `85.96s` | `0.39s` | `0.28s` | `0.00s` | `1.33x` | Decorative background accent |
| **Panel 15 - Text_line** | `DECORATIVE` | `85.85s` | `86.24s` | `0.39s` | `0.28s` | `0.00s` | `1.33x` | Decorative background accent |
| **Panel 15 - Text_line** | `DECORATIVE` | `86.13s` | `86.52s` | `0.39s` | `0.28s` | `0.00s` | `1.33x` | Decorative background accent |
| **Panel 15 - Text_line** | `DECORATIVE` | `86.41s` | `86.80s` | `0.39s` | `0.28s` | `0.00s` | `1.33x` | Decorative background accent |
| **Panel 15 - Text_line** | `DECORATIVE` | `86.70s` | `87.09s` | `0.39s` | `0.28s` | `0.00s` | `1.33x` | Decorative background accent |
| **Panel 15 - Text_line** | `DECORATIVE` | `86.98s` | `87.37s` | `0.39s` | `0.28s` | `0.00s` | `1.33x` | Decorative background accent |
| **Panel 15 - Text_line** | `DECORATIVE` | `87.26s` | `87.65s` | `0.39s` | `0.28s` | `0.00s` | `1.33x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_16` (Panel 16)
- **Speech Window:** `[88.80s -> 91.80s]` (المدة: **3.00s**)
- **Visual Window:** `[88.80s -> 89.30s]` (المدة: **0.50s**)
- **النص المنطوق:** *"هذي عقول مبرمجة على المشاكل اللي تنشاف بالعين وتلمس باليد. ما يهمه كثي..."*
- **Primary Elements:** `['Panel 16 - Character / Person']`
- **Secondary Elements:** `['Panel 16 - Icon / Graphic', 'Panel 16 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 16 - Title', 'Panel 16 - Text_line', 'Panel 16 - Text_line', 'Panel 16 - Text_line', 'Panel 16 - Text_line', 'Panel 16 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 16 - Character / Person** | `PRIMARY` | `88.80s` | `89.30s` | `0.50s` | `0.20s` | `0.00s` | `2.00x` | Primary focal subject drawing |
| **Panel 16 - Icon / Graphic** | `SECONDARY` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.71x` | Secondary context drawing with NATURAL overlap |
| **Panel 16 - Icon / Graphic** | `SECONDARY` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.71x` | Secondary context drawing with NATURAL overlap |
| **Panel 16 - Title** | `DECORATIVE` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 16 - Text_line** | `DECORATIVE` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 16 - Text_line** | `DECORATIVE` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 16 - Text_line** | `DECORATIVE` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 16 - Text_line** | `DECORATIVE` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |
| **Panel 16 - Text_line** | `DECORATIVE` | `88.95s` | `89.30s` | `0.35s` | `0.20s` | `0.00s` | `1.49x` | Decorative background accent |

---
## 3. Visually Distinct Storyboard (Sheet 2 - Tools, Cars, Direction Arrows)
- **ملف الصورة:** `ChatGPT Image Sep 17, 2026, 06_05_24 PM.png`
- **عدد البانلات المكتشفة:** 12
- **المدة الصوتية المخصصة:** 66.90 ثانية
- **عدد النبضات البصرية المنفذة:** 12

### 📍 Visual Beat: `vbeat_01` (Panel 1)
- **Speech Window:** `[00.00s -> 04.20s]` (المدة: **4.20s**)
- **Visual Window:** `[00.00s -> 08.10s]` (المدة: **8.10s**)
- **النص المنطوق:** *"خلينا نبدا من أول مستوى، المستوى التأسيسي، اللي يكون فيه معدل الذكاء أ..."*
- **Primary Elements:** `['Panel 01 - Text_line']`
- **Secondary Elements:** `['Panel 01 - Icon / Graphic', 'Panel 01 - Icon / Graphic', 'Panel 01 - Icon / Graphic', 'Panel 01 - Emoji / Expression']`
- **Decorative Elements:** `['Panel 01 - Title', 'Panel 01 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 01 - Text_line** | `PRIMARY` | `00.00s` | `00.92s` | `0.92s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 01 - Text_line** | `PRIMARY` | `00.66s` | `01.58s` | `0.92s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 01 - Icon / Graphic** | `SECONDARY` | `01.32s` | `01.92s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 01 - Icon / Graphic** | `SECONDARY` | `01.76s` | `02.36s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 01 - Icon / Graphic** | `SECONDARY` | `02.19s` | `02.79s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 01 - Emoji / Expression** | `SECONDARY` | `02.62s` | `03.22s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 01 - Title** | `DECORATIVE` | `03.05s` | `03.47s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_02` (Panel 2)
- **Speech Window:** `[08.10s -> 11.40s]` (المدة: **3.30s**)
- **Visual Window:** `[08.10s -> 19.20s]` (المدة: **11.10s**)
- **النص المنطوق:** *"لكن بعيداً عن الأرقام، كيف تكون الحياة من داخل هذا المستوى؟ ببساطة الد..."*
- **Primary Elements:** `['Panel 02 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `['Panel 02 - Title', 'Panel 02 - Text_line', 'Panel 02 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 02 - Character / Person** | `PRIMARY` | `08.10s` | `09.88s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 02 - Title** | `DECORATIVE` | `09.38s` | `09.80s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 02 - Text_line** | `DECORATIVE` | `09.68s` | `10.10s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 02 - Text_line** | `DECORATIVE` | `09.99s` | `10.41s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_03` (Panel 3)
- **Speech Window:** `[19.20s -> 23.40s]` (المدة: **4.20s**)
- **Visual Window:** `[19.20s -> 30.60s]` (المدة: **11.40s**)
- **النص المنطوق:** *"له نكتة فيها تلاعب بالكلمات، ممكن يطالع فيك كأن مخه للتو قال لك إيرور...."*
- **Primary Elements:** `['Panel 03 - Title']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `['Panel 03 - Text_line', 'Panel 03 - Text_line', 'Panel 03 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 03 - Title** | `PRIMARY` | `19.20s` | `20.12s` | `0.92s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 03 - Text_line** | `DECORATIVE` | `19.86s` | `20.28s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Text_line** | `DECORATIVE` | `20.16s` | `20.58s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 03 - Text_line** | `DECORATIVE` | `20.47s` | `20.89s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_04` (Panel 4)
- **Speech Window:** `[30.60s -> 34.80s]` (المدة: **4.20s**)
- **Visual Window:** `[30.60s -> 41.70s]` (المدة: **11.10s**)
- **النص المنطوق:** *"لكن اذا نزل المستوى تحت 35، هنا يصير الشخص معتمداً بشكل كبير على غيره ..."*
- **Primary Elements:** `['Panel 04 - Character / Person', 'Panel 04 - Character / Person', 'Panel 04 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `['Panel 04 - Title', 'Panel 04 - Text_line', 'Panel 04 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 04 - Character / Person** | `PRIMARY` | `30.60s` | `32.38s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 04 - Character / Person** | `PRIMARY` | `31.88s` | `33.66s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 04 - Character / Person** | `PRIMARY` | `33.16s` | `34.94s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 04 - Title** | `DECORATIVE` | `34.44s` | `34.86s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 04 - Text_line** | `DECORATIVE` | `34.75s` | `35.17s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 04 - Text_line** | `DECORATIVE` | `35.05s` | `35.47s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_05` (Panel 5)
- **Speech Window:** `[41.70s -> 42.30s]` (المدة: **0.60s**)
- **Visual Window:** `[41.70s -> 50.10s]` (المدة: **8.40s**)
- **النص المنطوق:** *"مختلف تماماً. هؤلاء يعيشون بعيداً عن كثير من التعقيدات اللي تستهلكنا ا..."*
- **Primary Elements:** `['Panel 05 - Character / Person', 'Panel 05 - Character / Person']`
- **Secondary Elements:** `['Panel 05 - Icon / Graphic']`
- **Decorative Elements:** `['Panel 05 - Text_line', 'Panel 05 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 05 - Character / Person** | `PRIMARY` | `41.70s` | `43.48s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 05 - Character / Person** | `PRIMARY` | `42.98s` | `44.76s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 05 - Icon / Graphic** | `SECONDARY` | `44.26s` | `44.86s` | `0.60s` | `0.28s` | `0.00s` | `1.00x` | Secondary context drawing with NATURAL overlap |
| **Panel 05 - Text_line** | `DECORATIVE` | `44.70s` | `45.12s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 05 - Text_line** | `DECORATIVE` | `45.00s` | `45.42s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_06` (Panel 6)
- **Speech Window:** `[50.10s -> 54.00s]` (المدة: **3.90s**)
- **Visual Window:** `[50.10s -> 56.10s]` (المدة: **6.00s**)
- **النص المنطوق:** *"الرسالة، ولا يشيل هم بعد عشر سنين، ولا يدخل نفسه في الف احتمال. هو ببس..."*
- **Primary Elements:** `['Panel 06 - Character / Person', 'Panel 06 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `[]`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 06 - Character / Person** | `PRIMARY` | `50.10s` | `51.88s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 06 - Character / Person** | `PRIMARY` | `51.38s` | `53.16s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |

---
### 📍 Visual Beat: `vbeat_07` (Panel 7)
- **Speech Window:** `[56.10s -> 58.80s]` (المدة: **2.70s**)
- **Visual Window:** `[56.10s -> 64.20s]` (المدة: **8.10s**)
- **النص المنطوق:** *"من 70 الى 84، ندخل على مستوى ذكاء الشوارع. هذول يمثلون تقريباً 14% من ..."*
- **Primary Elements:** `['Panel 07 - Character / Person', 'Panel 07 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `['Panel 07 - Title', 'Panel 07 - Text_line']`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 07 - Character / Person** | `PRIMARY` | `56.10s` | `57.88s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 07 - Character / Person** | `PRIMARY` | `57.38s` | `59.16s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 07 - Title** | `DECORATIVE` | `58.66s` | `59.08s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |
| **Panel 07 - Text_line** | `DECORATIVE` | `58.97s` | `59.39s` | `0.42s` | `0.28s` | `0.00s` | `1.24x` | Decorative background accent |

---
### 📍 Visual Beat: `vbeat_08` (Panel 8)
- **Speech Window:** `[64.20s -> 66.90s]` (المدة: **2.70s**)
- **Visual Window:** `[64.20s -> 71.10s]` (المدة: **6.90s**)
- **النص المنطوق:** *"رياضيات، فيزياء، معادلات طويلة، نص أدبي من ثلاث صفحات... يعطى هالكتاب ..."*
- **Primary Elements:** `['Panel 08 - Character / Person', 'Panel 08 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `[]`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 08 - Character / Person** | `PRIMARY` | `64.20s` | `65.98s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 08 - Character / Person** | `PRIMARY` | `65.48s` | `67.26s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |

---
### 📍 Visual Beat: `vbeat_09` (Panel 9)
- **Speech Window:** `[71.10s -> 72.30s]` (المدة: **1.20s**)
- **Visual Window:** `[71.10s -> 74.40s]` (المدة: **3.30s**)
- **النص المنطوق:** *"تعطلت سيارتك في البر؟ هنا يبدأ السحر. ما عنده القطعة المناسبة؟..."*
- **Primary Elements:** `['Panel 09 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `[]`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 09 - Character / Person** | `PRIMARY` | `71.10s` | `72.88s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |

---
### 📍 Visual Beat: `vbeat_10` (Panel 10)
- **Speech Window:** `[74.40s -> 74.70s]` (المدة: **0.30s**)
- **Visual Window:** `[74.40s -> 80.40s]` (المدة: **6.00s**)
- **النص المنطوق:** *"عادي! ما عنده الادوات الكاملة، ما يفرق. يلفها بشطرطون، يربطها بمغاط، ي..."*
- **Primary Elements:** `['Panel 10 - Character / Person', 'Panel 10 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `[]`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 10 - Character / Person** | `PRIMARY` | `74.40s` | `76.18s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |
| **Panel 10 - Character / Person** | `PRIMARY` | `75.68s` | `77.46s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |

---
### 📍 Visual Beat: `vbeat_11` (Panel 11)
- **Speech Window:** `[80.40s -> 81.90s]` (المدة: **1.50s**)
- **Visual Window:** `[80.40s -> 88.80s]` (المدة: **8.40s**)
- **النص المنطوق:** *"وانت فعلا تشغل السيارة وتمشي. هو ممكن ما يقدر يكتب لك مقال اكاديمي مرت..."*
- **Primary Elements:** `['Panel 11 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `[]`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 11 - Character / Person** | `PRIMARY` | `80.40s` | `82.18s` | `1.78s` | `0.55s` | `0.00s` | `1.00x` | Primary focal subject drawing |

---
### 📍 Visual Beat: `vbeat_12` (Panel 12)
- **Speech Window:** `[88.80s -> 91.80s]` (المدة: **3.00s**)
- **Visual Window:** `[88.80s -> 89.30s]` (المدة: **0.50s**)
- **النص المنطوق:** *"هذي عقول مبرمجة على المشاكل اللي تنشاف بالعين وتلمس باليد. ما يهمه كثي..."*
- **Primary Elements:** `['Panel 12 - Character / Person']`
- **Secondary Elements:** `[]`
- **Decorative Elements:** `[]`
- **Overlap Policy:** `NATURAL` | **Hold Time:** `0.55s`

| العنصر | المستوى | البداية | النهاية | مدة الرسم | مدة الثبات | الاستباق | معامل السرعة | سبب وتبرير القرار |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Panel 12 - Character / Person** | `PRIMARY` | `88.80s` | `89.30s` | `0.50s` | `0.20s` | `0.00s` | `2.00x` | Primary focal subject drawing |

---
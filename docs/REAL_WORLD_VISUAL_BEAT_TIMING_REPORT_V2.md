# تقرير فحص التوقيت الحقيقي V2: محرك التوقيت البصري القائم على المحتوى (Content-Aware Timing Engine V2)

> هذا التقرير يوثق نتائج تشغيل **Visual Beat Engine V2** على **ثلاث لوحات استوري بورد حقيقية** باستخدام ملف الصوت الفعلي وملف الترجمة SRT الحقيقي.
> تم الانتقال بالكامل من مجرد تقريب المدد (Preset Timing) إلى **نموذج فيزيائي معاير** يعتمد على الجهد الفيزيائي الحقيقي للرسم (`DrawingDemand`)، وفحص الجدوى (`Speed Feasibility`)، وإدارة التعارضات (`Timing Conflict Model`)، وعلاقات الانتقال المستقلة بين النبضات (`BeatTransition`).

---

## الفروقات الجوهرية (BEFORE V1 vs AFTER V2)

| المعيار المعماري | النظام السابق (Preset Timing V1) | النظام الجديد (Content-Aware V2) |
| :--- | :--- | :--- |
| **تحديد زمن الرسم** | مدد ثابتة وفق الفئة (شخصية 1.78s، أيقونة 0.60s، نص 0.42s) | **نموذج فيزيائي معاير**: $\text{Demand} = \sum \|\Delta p\| \to T = \text{Effort} / v_{pen}$ |
| **DrawingDemand** | كان مدمجاً في Duration | **مفصول تماماً**: $L_{arc}$, عدد الخطوط، النقاط، التعقيد، الكثافة $\neq$ زمن الرسم |
| **تصنيف العناصر (Tiers)** | كان يحدد مدة الرسم مسبقاً (Primary أطول دائماً) | **يحدد الأهمية السردية والحماية والـ Hold**؛ زمن الرسم يتبع الجهد الفيزيائي فقط |
| **إدارة الانتقال (Transition)** | كان ملكية داخلية للنبضة تؤدي لتضارب النوافذ | **كيان مستقل (`BeatTransition`)** يربط بين Beat $A$ و Beat $B$ باستراتيجيات واضحة |
| **فحص السرعة والجدوى** | تسريع غير مقيد عند ضيق الوقت (سرعات خيالية) | **Speed Feasibility** (`NORMAL`, `FAST`, `LIMITED`, `INFEASIBLE`) + 6 خطوات للحل |
| **التعارضات المستحيلة** | محاولة إجبار الـ Timeline أو انهيار النظام | **كائنات `TimingConflict` موثقة** بالخطورة والحل المقترح |

---

## 1. 12-Panel Storyboard (Sheet 1 - Characters & Text Cards)
- **ملف الصورة:** `ChatGPT Image Sep 17, 2026, 06_05_13 PM.png`
- **عدد البانلات المكتشفة:** 12
- **المدة الصوتية:** 84.30 ثانية
- **عدد النبضات البصرية المنفذة:** 12
- **عدد روابط الانتقال بين النبضات (`BeatTransitions`):** 11

### 📊 جدول ملخص النبضات البصرية والنوافذ الزمنية الثلاث
| Beat ID | Panel | Speech Window | Drawing Window | Hold Window | Total Effort (px) | Feasibility | Conflicts |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `vbeat_01` | 1 | [0.00s - 8.10s] (8.10s) | [0.00s - 8.07s] (8.07s) | [8.07s - 8.62s] (0.55s) | 10312 | `NORMAL/LIMITED` | ✅ 0 |
| `vbeat_02` | 2 | [8.10s - 19.20s] (11.10s) | [8.10s - 18.50s] (10.40s) | [18.50s - 19.20s] (0.70s) | 5357 | `NORMAL` | ✅ 0 |
| `vbeat_03` | 3 | [19.20s - 30.60s] (11.40s) | [19.20s - 30.60s] (11.40s) | [30.60s - 31.15s] (0.55s) | 39061 | `FAST/NORMAL` | ⚠️ 10 Conflicts |
| `vbeat_04` | 4 | [30.60s - 41.70s] (11.10s) | [30.60s - 39.91s] (9.31s) | [39.91s - 41.70s] (1.79s) | 7607 | `NORMAL` | ✅ 0 |
| `vbeat_05` | 5 | [41.70s - 50.10s] (8.40s) | [41.70s - 50.10s] (8.40s) | [50.10s - 50.65s] (0.55s) | 13796 | `FAST/NORMAL/LIMITED` | ⚠️ 2 Conflicts |
| `vbeat_06` | 6 | [50.10s - 56.10s] (6.00s) | [50.10s - 56.10s] (6.00s) | [56.10s - 56.65s] (0.55s) | 10292 | `FAST/NORMAL/LIMITED` | ⚠️ 2 Conflicts |
| `vbeat_07` | 7 | [56.10s - 64.20s] (8.10s) | [56.10s - 64.10s] (8.00s) | [64.10s - 64.65s] (0.55s) | 7732 | `FAST/NORMAL` | ✅ 0 |
| `vbeat_08` | 8 | [64.20s - 71.10s] (6.90s) | [64.20s - 71.10s] (6.90s) | [71.10s - 71.65s] (0.55s) | 8051 | `FAST/NORMAL` | ✅ 0 |
| `vbeat_09` | 9 | [71.10s - 74.40s] (3.30s) | [71.10s - 74.40s] (3.30s) | [74.40s - 74.95s] (0.55s) | 10938 | `FAST/NORMAL/LIMITED` | ⚠️ 1 Conflicts |
| `vbeat_10` | 10 | [74.40s - 80.40s] (6.00s) | [74.40s - 80.40s] (6.00s) | [80.40s - 80.95s] (0.55s) | 7395 | `FAST/NORMAL` | ✅ 0 |
| `vbeat_11` | 11 | [80.40s - 88.80s] (8.40s) | [80.40s - 88.80s] (8.40s) | [88.80s - 89.35s] (0.55s) | 7450 | `NORMAL` | ✅ 0 |
| `vbeat_12` | 12 | [88.80s - 89.30s] (0.50s) | [88.80s - 89.30s] (0.50s) | [89.30s - 89.85s] (0.55s) | 10955 | `FAST/NORMAL/LIMITED` | ⚠️ 4 Conflicts |

### 🔍 تفاصيل العناصر وقرارات التوقيت الفيزيائي في كل نبضة
#### 📍 `vbeat_01` (Panel 1)
- **النص المنطوق:** *"خلينا نبدا من أول مستوى، المستوى التأسيسي، اللي يكون فيه معدل الذكاء أقل من 70. ..."*
- **Speech Window:** `[0.00s -> 8.10s]` (مدة الكلام: **8.10s**)
- **Drawing Window:** `[0.00s -> 8.07s]` (مدة الرسم الفعلية: **8.07s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[8.07s -> 8.62s]` (مدة الثبات: **0.55s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `الذكاء` (OBJECT) @ `3.30s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `70.` (OBJECT) @ `4.20s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `2%` (NUMBER) @ `7.20s` -> Type: `DURING`, Confidence: `0.92`
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 0.00s | 0.97s | **0.97s** | 0.28s | 2.09x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 1402 | 2102 | 0.82s | 3.57s | **2.75s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `PRIMARY` | 1293 | 1939 | 2.89s | 5.43s | **2.54s** | 0.55s | 1.17x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `DECORATIVE` | 1100 | 1650 | 5.05s | 6.26s | **1.21s** | 0.28s | 2.10x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 5.95s | 7.16s | **1.21s** | 0.28s | 2.10x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 6.86s | 8.07s | **1.21s** | 0.28s | 2.10x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |

#### 📍 `vbeat_02` (Panel 2)
- **النص المنطوق:** *"لكن بعيداً عن الأرقام، كيف تكون الحياة من داخل هذا المستوى؟ ببساطة الدماغ هنا يو..."*
- **Speech Window:** `[8.10s -> 19.20s]` (مدة الكلام: **11.10s**)
- **Drawing Window:** `[8.10s -> 18.50s]` (مدة الرسم الفعلية: **10.40s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[18.50s -> 19.20s]` (مدة الثبات: **0.70s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `الدماغ` (OBJECT) @ `11.70s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `خطورة` (OBJECT) @ `17.40s` -> Type: `DURING`, Confidence: `0.80`
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 3571 | 5357 | 8.10s | 18.50s | **10.40s** | 0.55s | 0.77x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |

#### 📍 `vbeat_03` (Panel 3)
- **النص المنطوق:** *"له نكتة فيها تلاعب بالكلمات، ممكن يطالع فيك كأن مخه للتو قال لك إيرور. اللي معدل..."*
- **Speech Window:** `[19.20s -> 30.60s]` (مدة الكلام: **11.40s**)
- **Drawing Window:** `[19.20s -> 30.60s]` (مدة الرسم الفعلية: **11.40s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[30.60s -> 31.15s]` (مدة الثبات: **0.55s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `إيرور.` (OBJECT) @ `23.10s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `50` (NUMBER) @ `24.30s` -> Type: `DURING`, Confidence: `0.92`
  - 🎯 `70` (NUMBER) @ `24.90s` -> Type: `DURING`, Confidence: `0.92`
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_03' for element 'Panel 03 - Card Text Line 1' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_03' for element 'Panel 03 - Card Text Line 2' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_03' for element 'Panel 03 - Card Text Line 3' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_03' for element 'Panel 03 - Card Text Line 1' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_03' for element 'Panel 03 - Card Text Line 2' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_03' for element 'Panel 03 - Card Text Line 3' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_03' for element 'Panel 03 - Card Text Line 4' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_03' for element 'Panel 03 - Card Text Line 1' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_03' for element 'Panel 03 - Card Text Line 2' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_03' for element 'Panel 03 - Card Text Line 3' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 880 | 1320 | 19.20s | 20.93s | **1.73s** | 0.55s | 1.17x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_2` | `SECONDARY` | 1430 | 2145 | 20.32s | 22.47s | **2.15s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_3` | `SECONDARY` | 1430 | 2145 | 21.94s | 24.09s | **2.15s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_4` | `SECONDARY` | 1430 | 2145 | 23.55s | 25.70s | **2.15s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `SECONDARY` | 1430 | 2145 | 25.16s | 27.31s | **2.15s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_6` | `SECONDARY` | 521 | 781 | 26.77s | 27.55s | **0.78s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 27.44s | 29.34s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_8` | `DECORATIVE` | 1485 | 2228 | 28.87s | 30.60s | **1.73s** | 0.28s | 1.98x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_9` | `DECORATIVE` | 1485 | 2228 | 30.17s | 30.60s | **0.43s** | 0.28s | 2.20x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_10` | `DECORATIVE` | 1485 | 2228 | 30.25s | 30.60s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_11` | `DECORATIVE` | 1485 | 2228 | 30.25s | 30.60s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_12` | `DECORATIVE` | 1485 | 2228 | 30.25s | 30.60s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_13` | `DECORATIVE` | 1485 | 2228 | 30.25s | 30.60s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_14` | `DECORATIVE` | 1485 | 2228 | 30.25s | 30.60s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_15` | `DECORATIVE` | 1485 | 2228 | 30.25s | 30.60s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_16` | `DECORATIVE` | 1485 | 2228 | 30.25s | 30.60s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_17` | `DECORATIVE` | 1485 | 2228 | 30.25s | 30.60s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_18` | `DECORATIVE` | 1485 | 2228 | 30.25s | 30.60s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_19` | `DECORATIVE` | 1485 | 2228 | 30.25s | 30.60s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_04` (Panel 4)
- **النص المنطوق:** *"لكن اذا نزل المستوى تحت 35، هنا يصير الشخص معتمداً بشكل كبير على غيره في احتياجا..."*
- **Speech Window:** `[30.60s -> 41.70s]` (مدة الكلام: **11.10s**)
- **Drawing Window:** `[30.60s -> 39.91s]` (مدة الرسم الفعلية: **9.31s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[39.91s -> 41.70s]` (مدة الثبات: **1.79s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `35،` (OBJECT) @ `32.10s` -> Type: `DURING`, Confidence: `0.80`
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 30.60s | 32.43s | **1.83s** | 0.28s | 1.11x | `NORMAL` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 3091 | 4637 | 32.16s | 38.59s | **6.43s** | 0.55s | 1.11x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `DECORATIVE` | 1100 | 1650 | 37.62s | 39.91s | **2.29s** | 0.28s | 1.11x | `NORMAL` | *Physical demand schedule (DECORATIVE, ef* |

#### 📍 `vbeat_05` (Panel 5)
- **النص المنطوق:** *"مختلف تماماً. هؤلاء يعيشون بعيداً عن كثير من التعقيدات اللي تستهلكنا احنا كل يوم..."*
- **Speech Window:** `[41.70s -> 50.10s]` (مدة الكلام: **8.40s**)
- **Drawing Window:** `[41.70s -> 50.10s]` (مدة الرسم الفعلية: **8.40s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[50.10s -> 50.65s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_05' for element 'Panel 05 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_05' for element 'Panel 05 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 41.70s | 42.51s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 2176 | 3264 | 42.39s | 46.66s | **4.27s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `PRIMARY` | 2170 | 3254 | 45.59s | 49.85s | **4.26s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `SECONDARY` | 672 | 1008 | 48.36s | 49.37s | **1.01s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 49.22s | 50.10s | **0.88s** | 0.28s | 2.20x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 49.75s | 50.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 49.75s | 50.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_06` (Panel 6)
- **النص المنطوق:** *"الرسالة، ولا يشيل هم بعد عشر سنين، ولا يدخل نفسه في الف احتمال. هو ببساطة، يعيش ..."*
- **Speech Window:** `[50.10s -> 56.10s]` (مدة الكلام: **6.00s**)
- **Drawing Window:** `[50.10s -> 56.10s]` (مدة الرسم الفعلية: **6.00s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[56.10s -> 56.65s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_06' for element 'Panel 06 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_06' for element 'Panel 06 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 50.10s | 50.91s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 2682 | 4022 | 50.79s | 56.05s | **5.26s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `DECORATIVE` | 1100 | 1650 | 55.26s | 56.10s | **0.84s** | 0.28s | 2.20x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_4` | `DECORATIVE` | 1100 | 1650 | 55.75s | 56.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 55.75s | 56.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_07` (Panel 7)
- **النص المنطوق:** *"من 70 الى 84، ندخل على مستوى ذكاء الشوارع. هذول يمثلون تقريباً 14% من المجتمع، ي..."*
- **Speech Window:** `[56.10s -> 64.20s]` (مدة الكلام: **8.10s**)
- **Drawing Window:** `[56.10s -> 64.10s]` (مدة الرسم الفعلية: **8.00s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[64.10s -> 64.65s]` (مدة الثبات: **0.55s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `70` (NUMBER) @ `56.40s` -> Type: `LEAD_IN`, Confidence: `0.92`
  - 🎯 `84،` (OBJECT) @ `57.00s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `ذكاء` (OBJECT) @ `58.20s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `14%` (NUMBER) @ `59.70s` -> Type: `DURING`, Confidence: `0.92`
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 56.10s | 57.39s | **1.29s** | 0.28s | 1.57x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 3174 | 4762 | 57.20s | 63.43s | **6.23s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `DECORATIVE` | 1100 | 1650 | 62.49s | 64.10s | **1.61s** | 0.28s | 1.58x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |

#### 📍 `vbeat_08` (Panel 8)
- **النص المنطوق:** *"رياضيات، فيزياء، معادلات طويلة، نص أدبي من ثلاث صفحات... يعطى هالكتاب ويمكن يقفل..."*
- **Speech Window:** `[64.20s -> 71.10s]` (مدة الكلام: **6.90s**)
- **Drawing Window:** `[64.20s -> 71.10s]` (مدة الرسم الفعلية: **6.90s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[71.10s -> 71.65s]` (مدة الثبات: **0.55s**)
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 1798 | 2698 | 64.20s | 67.73s | **3.53s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_2` | `PRIMARY` | 2355 | 3533 | 66.85s | 71.10s | **4.25s** | 0.55s | 1.28x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `SECONDARY` | 689 | 1033 | 69.61s | 70.64s | **1.03s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_4` | `SECONDARY` | 525 | 788 | 70.38s | 71.10s | **0.72s** | 0.28s | 1.69x | `FAST` | *Physical demand schedule (SECONDARY, eff* |

#### 📍 `vbeat_09` (Panel 9)
- **النص المنطوق:** *"تعطلت سيارتك في البر؟ هنا يبدأ السحر. ما عنده القطعة المناسبة؟..."*
- **Speech Window:** `[71.10s -> 74.40s]` (مدة الكلام: **3.30s**)
- **Drawing Window:** `[71.10s -> 74.40s]` (مدة الرسم الفعلية: **3.30s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[74.40s -> 74.95s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_09' for element 'Panel 09 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 71.10s | 71.91s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 1760 | 2640 | 71.79s | 74.40s | **2.61s** | 0.55s | 1.56x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `PRIMARY` | 3552 | 5328 | 73.75s | 74.40s | **0.65s** | 0.55s | 2.20x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `DECORATIVE` | 1100 | 1650 | 74.05s | 74.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_10` (Panel 10)
- **النص المنطوق:** *"عادي! ما عنده الادوات الكاملة، ما يفرق. يلفها بشطرطون، يربطها بمغاط، يركب حل مؤق..."*
- **Speech Window:** `[74.40s -> 80.40s]` (مدة الكلام: **6.00s**)
- **Drawing Window:** `[74.40s -> 80.40s]` (مدة الرسم الفعلية: **6.00s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[80.40s -> 80.95s]` (مدة الثبات: **0.55s**)
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `SECONDARY` | 966 | 1449 | 74.40s | 75.85s | **1.45s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_2` | `SECONDARY` | 878 | 1317 | 75.49s | 76.81s | **1.32s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_3` | `SECONDARY` | 886 | 1329 | 76.48s | 77.81s | **1.33s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_4` | `PRIMARY` | 1100 | 1650 | 77.61s | 79.77s | **2.16s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_5` | `PRIMARY` | 1100 | 1650 | 79.23s | 80.40s | **1.17s** | 0.55s | 2.17x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |

#### 📍 `vbeat_11` (Panel 11)
- **النص المنطوق:** *"وانت فعلا تشغل السيارة وتمشي. هو ممكن ما يقدر يكتب لك مقال اكاديمي مرتب، لكنه يع..."*
- **Speech Window:** `[80.40s -> 88.80s]` (مدة الكلام: **8.40s**)
- **Drawing Window:** `[80.40s -> 88.80s]` (مدة الرسم الفعلية: **8.40s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[88.80s -> 89.35s]` (مدة الثبات: **0.55s**)
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 1997 | 2995 | 80.40s | 84.32s | **3.92s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_2` | `PRIMARY` | 2970 | 4454 | 83.34s | 88.80s | **5.46s** | 0.55s | 1.26x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |

#### 📍 `vbeat_12` (Panel 12)
- **النص المنطوق:** *"هذي عقول مبرمجة على المشاكل اللي تنشاف بالعين وتلمس باليد. ما يهمه كثير الكلام ا..."*
- **Speech Window:** `[88.80s -> 89.30s]` (مدة الكلام: **0.50s**)
- **Drawing Window:** `[88.80s -> 89.30s]` (مدة الرسم الفعلية: **0.50s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[89.30s -> 89.85s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[HIGH] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Character / Person' (3123px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 88.80s | 89.30s | **0.50s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 3123 | 4685 | 88.95s | 89.30s | **0.35s** | 0.55s | 2.20x | `NORMAL` | *Budget compressed schedule (PRIMARY, DRA* |
  | `elem_3` | `DECORATIVE` | 1100 | 1650 | 88.95s | 89.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_4` | `DECORATIVE` | 1100 | 1650 | 88.95s | 89.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 88.95s | 89.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

### 🔗 روابط الانتقال بين النبضات (`BeatTransitions`)
| From Beat | To Beat | Start Time | End Time | Transition Type | Strategy |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `vbeat_01` | `vbeat_02` | 8.07s | 8.10s | `KEEP` | Additive hold: canvas retained as vbeat_02 commences |
| `vbeat_02` | `vbeat_03` | 18.50s | 19.20s | `KEEP` | Additive hold: canvas retained as vbeat_03 commences |
| `vbeat_03` | `vbeat_04` | 30.60s | 30.60s | `KEEP` | Additive hold: canvas retained as vbeat_04 commences |
| `vbeat_04` | `vbeat_05` | 39.91s | 41.70s | `KEEP` | Additive hold: canvas retained as vbeat_05 commences |
| `vbeat_05` | `vbeat_06` | 50.10s | 50.10s | `KEEP` | Additive hold: canvas retained as vbeat_06 commences |
| `vbeat_06` | `vbeat_07` | 56.10s | 56.10s | `KEEP` | Additive hold: canvas retained as vbeat_07 commences |
| `vbeat_07` | `vbeat_08` | 64.10s | 64.20s | `KEEP` | Additive hold: canvas retained as vbeat_08 commences |
| `vbeat_08` | `vbeat_09` | 71.10s | 71.10s | `KEEP` | Additive hold: canvas retained as vbeat_09 commences |
| `vbeat_09` | `vbeat_10` | 74.40s | 74.40s | `KEEP` | Additive hold: canvas retained as vbeat_10 commences |
| `vbeat_10` | `vbeat_11` | 80.40s | 80.40s | `KEEP` | Additive hold: canvas retained as vbeat_11 commences |
| `vbeat_11` | `vbeat_12` | 88.80s | 88.80s | `KEEP` | Additive hold: canvas retained as vbeat_12 commences |

---

## 2. 16-Panel Storyboard (Test Archive Sheet - Multi-Grid)
- **ملف الصورة:** `ChatGPT Image Sep 5, 2026, 03_23_52 PM.png`
- **عدد البانلات المكتشفة:** 16
- **المدة الصوتية:** 60.00 ثانية
- **عدد النبضات البصرية المنفذة:** 16
- **عدد روابط الانتقال بين النبضات (`BeatTransitions`):** 15

### 📊 جدول ملخص النبضات البصرية والنوافذ الزمنية الثلاث
| Beat ID | Panel | Speech Window | Drawing Window | Hold Window | Total Effort (px) | Feasibility | Conflicts |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `vbeat_01` | 1 | [0.00s - 4.50s] (4.50s) | [0.00s - 4.50s] (4.50s) | [4.50s - 5.05s] (0.55s) | 14886 | `FAST/NORMAL/LIMITED` | ⚠️ 5 Conflicts |
| `vbeat_02` | 2 | [4.50s - 11.40s] (6.90s) | [4.50s - 11.40s] (6.90s) | [11.40s - 11.95s] (0.55s) | 14427 | `FAST/NORMAL/LIMITED` | ⚠️ 3 Conflicts |
| `vbeat_03` | 3 | [11.40s - 19.20s] (7.80s) | [11.40s - 19.20s] (7.80s) | [19.20s - 19.75s] (0.55s) | 12027 | `FAST/NORMAL/LIMITED` | ⚠️ 1 Conflicts |
| `vbeat_04` | 4 | [19.20s - 30.60s] (11.40s) | [19.20s - 30.60s] (11.40s) | [30.60s - 31.15s] (0.55s) | 15711 | `FAST/NORMAL` | ⚠️ 1 Conflicts |
| `vbeat_05` | 5 | [30.60s - 37.50s] (6.90s) | [30.60s - 37.50s] (6.90s) | [37.50s - 38.05s] (0.55s) | 14546 | `FAST/NORMAL/LIMITED` | ⚠️ 3 Conflicts |
| `vbeat_06` | 6 | [37.50s - 42.30s] (4.80s) | [37.50s - 42.30s] (4.80s) | [42.30s - 42.85s] (0.55s) | 17241 | `FAST/NORMAL/LIMITED` | ⚠️ 6 Conflicts |
| `vbeat_07` | 7 | [42.30s - 50.10s] (7.80s) | [42.30s - 50.10s] (7.80s) | [50.10s - 50.65s] (0.55s) | 14981 | `FAST/NORMAL/LIMITED` | ⚠️ 3 Conflicts |
| `vbeat_08` | 8 | [50.10s - 56.10s] (6.00s) | [50.10s - 56.10s] (6.00s) | [56.10s - 56.65s] (0.55s) | 18094 | `FAST/NORMAL/LIMITED` | ⚠️ 6 Conflicts |
| `vbeat_09` | 9 | [56.10s - 62.70s] (6.60s) | [56.10s - 62.70s] (6.60s) | [62.70s - 63.25s] (0.55s) | 11421 | `FAST/NORMAL/LIMITED` | ⚠️ 2 Conflicts |
| `vbeat_10` | 10 | [62.70s - 66.90s] (4.20s) | [62.70s - 66.90s] (4.20s) | [66.90s - 67.45s] (0.55s) | 22720 | `FAST/NORMAL/LIMITED` | ⚠️ 10 Conflicts |
| `vbeat_11` | 11 | [66.90s - 71.10s] (4.20s) | [66.90s - 71.10s] (4.20s) | [71.10s - 71.65s] (0.55s) | 21800 | `FAST/NORMAL/LIMITED` | ⚠️ 10 Conflicts |
| `vbeat_12` | 12 | [71.10s - 74.40s] (3.30s) | [71.10s - 74.40s] (3.30s) | [74.40s - 74.95s] (0.55s) | 16959 | `FAST/NORMAL/LIMITED` | ⚠️ 8 Conflicts |
| `vbeat_13` | 13 | [74.40s - 76.50s] (2.10s) | [74.40s - 76.50s] (2.10s) | [76.50s - 77.05s] (0.55s) | 17135 | `FAST/NORMAL/LIMITED` | ⚠️ 7 Conflicts |
| `vbeat_14` | 14 | [76.50s - 81.90s] (5.40s) | [76.50s - 81.90s] (5.40s) | [81.90s - 82.45s] (0.55s) | 17809 | `FAST/NORMAL/LIMITED` | ⚠️ 6 Conflicts |
| `vbeat_15` | 15 | [81.90s - 88.80s] (6.90s) | [81.90s - 88.80s] (6.90s) | [88.80s - 89.35s] (0.55s) | 20224 | `FAST/NORMAL/LIMITED` | ⚠️ 7 Conflicts |
| `vbeat_16` | 16 | [88.80s - 89.30s] (0.50s) | [88.80s - 89.30s] (0.50s) | [89.30s - 89.85s] (0.55s) | 14959 | `FAST/NORMAL/LIMITED` | ⚠️ 8 Conflicts |

### 🔍 تفاصيل العناصر وقرارات التوقيت الفيزيائي في كل نبضة
#### 📍 `vbeat_01` (Panel 1)
- **النص المنطوق:** *"خلينا نبدا من أول مستوى، المستوى التأسيسي، اللي يكون فيه معدل الذكاء أقل من 70...."*
- **Speech Window:** `[0.00s -> 4.50s]` (مدة الكلام: **4.50s**)
- **Drawing Window:** `[0.00s -> 4.50s]` (مدة الرسم الفعلية: **4.50s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[4.50s -> 5.05s]` (مدة الثبات: **0.55s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `الذكاء` (OBJECT) @ `3.30s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `70.` (OBJECT) @ `4.20s` -> Type: `EMPHASIS`, Confidence: `0.80`
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_01' for element 'Panel 01 - Question Mark / Symbol' (407px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_01' for element 'Panel 01 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_01' for element 'Panel 01 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_01' for element 'Panel 01 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_01' for element 'Panel 01 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 0.00s | 0.81s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 1818 | 2726 | 0.69s | 4.25s | **3.56s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `PRIMARY` | 2125 | 3187 | 3.36s | 4.50s | **1.14s** | 0.55s | 2.20x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `SECONDARY` | 294 | 441 | 4.10s | 4.50s | **0.40s** | 0.28s | 1.70x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `SECONDARY` | 407 | 611 | 4.15s | 4.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 4.15s | 4.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 4.15s | 4.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_8` | `DECORATIVE` | 1100 | 1650 | 4.15s | 4.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 4.15s | 4.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_02` (Panel 2)
- **النص المنطوق:** *"طبياً، هل فئة تدخل ضمن الإعاقة الفكرية وتمثل تقريباً 2% من البشر. لكن بعيداً عن ..."*
- **Speech Window:** `[4.50s -> 11.40s]` (مدة الكلام: **6.90s**)
- **Drawing Window:** `[4.50s -> 11.40s]` (مدة الرسم الفعلية: **6.90s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[11.40s -> 11.95s]` (مدة الثبات: **0.55s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `2%` (NUMBER) @ `7.20s` -> Type: `DURING`, Confidence: `0.92`
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_02' for element 'Panel 02 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_02' for element 'Panel 02 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_02' for element 'Panel 02 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 4.50s | 5.31s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 1747 | 2621 | 5.19s | 8.62s | **3.43s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `PRIMARY` | 1197 | 1795 | 7.76s | 10.11s | **2.35s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `SECONDARY` | 294 | 441 | 9.29s | 9.73s | **0.44s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 9.66s | 11.40s | **1.74s** | 0.28s | 1.46x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 10.97s | 11.40s | **0.43s** | 0.28s | 2.20x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 11.05s | 11.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_8` | `DECORATIVE` | 1100 | 1650 | 11.05s | 11.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 11.05s | 11.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_03` (Panel 3)
- **النص المنطوق:** *"ببساطة الدماغ هنا يواجه صعوبة كبيرة في معالجة المعلومات المعقدة والمفاهيم المجرد..."*
- **Speech Window:** `[11.40s -> 19.20s]` (مدة الكلام: **7.80s**)
- **Drawing Window:** `[11.40s -> 19.20s]` (مدة الرسم الفعلية: **7.80s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[19.20s -> 19.75s]` (مدة الثبات: **0.55s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `الدماغ` (OBJECT) @ `11.70s` -> Type: `LEAD_IN`, Confidence: `0.80`
  - 🎯 `خطورة` (OBJECT) @ `17.40s` -> Type: `DURING`, Confidence: `0.80`
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[HIGH] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_03' for element 'Panel 03 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 11.40s | 12.21s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `SECONDARY` | 290 | 435 | 12.09s | 12.52s | **0.43s** | 0.28s | 1.56x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_3` | `SECONDARY` | 466 | 699 | 12.41s | 13.11s | **0.70s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_4` | `SECONDARY` | 441 | 662 | 12.94s | 13.60s | **0.66s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `SECONDARY` | 441 | 662 | 13.43s | 14.09s | **0.66s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_6` | `PRIMARY` | 1100 | 1650 | 13.99s | 16.15s | **2.16s** | 0.55s | 1.17x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_7` | `PRIMARY` | 1100 | 1650 | 15.61s | 17.77s | **2.16s** | 0.55s | 1.17x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_8` | `PRIMARY` | 1100 | 1650 | 17.23s | 19.20s | **1.97s** | 0.55s | 1.29x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_9` | `PRIMARY` | 1100 | 1650 | 18.71s | 19.20s | **0.49s** | 0.55s | 2.20x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_10` | `PRIMARY` | 1100 | 1650 | 18.85s | 19.20s | **0.35s** | 0.55s | 2.20x | `NORMAL` | *Budget compressed schedule (PRIMARY, DRA* |

#### 📍 `vbeat_04` (Panel 4)
- **النص المنطوق:** *"له نكتة فيها تلاعب بالكلمات، ممكن يطالع فيك كأن مخه للتو قال لك إيرور. اللي معدل..."*
- **Speech Window:** `[19.20s -> 30.60s]` (مدة الكلام: **11.40s**)
- **Drawing Window:** `[19.20s -> 30.60s]` (مدة الرسم الفعلية: **11.40s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[30.60s -> 31.15s]` (مدة الثبات: **0.55s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `إيرور.` (OBJECT) @ `23.10s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `50` (NUMBER) @ `24.30s` -> Type: `DURING`, Confidence: `0.92`
  - 🎯 `70` (NUMBER) @ `24.90s` -> Type: `DURING`, Confidence: `0.92`
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_04' for element 'Panel 04 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 19.20s | 20.11s | **0.91s** | 0.28s | 2.20x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 1696 | 2544 | 19.97s | 23.30s | **3.33s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `SECONDARY` | 290 | 435 | 22.14s | 22.57s | **0.43s** | 0.28s | 1.56x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_4` | `SECONDARY` | 521 | 781 | 22.46s | 23.24s | **0.78s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `SECONDARY` | 487 | 731 | 23.05s | 23.78s | **0.73s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 23.67s | 25.57s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 25.09s | 27.00s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_8` | `DECORATIVE` | 1100 | 1650 | 26.52s | 28.42s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 27.95s | 29.85s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_10` | `DECORATIVE` | 1100 | 1650 | 29.38s | 30.60s | **1.22s** | 0.28s | 2.07x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_11` | `DECORATIVE` | 1100 | 1650 | 30.25s | 30.60s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_05` (Panel 5)
- **النص المنطوق:** *"لكن اذا نزل المستوى تحت 35، هنا يصير الشخص معتمداً بشكل كبير على غيره في احتياجا..."*
- **Speech Window:** `[30.60s -> 37.50s]` (مدة الكلام: **6.90s**)
- **Drawing Window:** `[30.60s -> 37.50s]` (مدة الرسم الفعلية: **6.90s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[37.50s -> 38.05s]` (مدة الثبات: **0.55s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `35،` (OBJECT) @ `32.10s` -> Type: `DURING`, Confidence: `0.80`
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_05' for element 'Panel 05 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_05' for element 'Panel 05 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_05' for element 'Panel 05 - Card Text Line 1' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 30.60s | 31.41s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 2304 | 3456 | 31.29s | 35.81s | **4.52s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `SECONDARY` | 1430 | 2145 | 34.23s | 36.38s | **2.15s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_4` | `SECONDARY` | 298 | 447 | 35.84s | 36.29s | **0.45s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 36.22s | 37.50s | **1.28s** | 0.28s | 1.99x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 37.15s | 37.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 37.15s | 37.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_8` | `DECORATIVE` | 1485 | 2228 | 37.15s | 37.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_06` (Panel 6)
- **النص المنطوق:** *"والغريب ان البعض يشوف ان هذا المستوى ما فيه الا سلبيات، لكن في جانب مختلف تماماً..."*
- **Speech Window:** `[37.50s -> 42.30s]` (مدة الكلام: **4.80s**)
- **Drawing Window:** `[37.50s -> 42.30s]` (مدة الرسم الفعلية: **4.80s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[42.30s -> 42.85s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_06' for element 'Panel 06 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_06' for element 'Panel 06 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_06' for element 'Panel 06 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_06' for element 'Panel 06 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_06' for element 'Panel 06 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_06' for element 'Panel 06 - Card Text Line 1' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 37.50s | 38.31s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 1901 | 2851 | 38.19s | 41.92s | **3.73s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `SECONDARY` | 1430 | 2145 | 40.61s | 42.30s | **1.69s** | 0.28s | 1.96x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_4` | `SECONDARY` | 298 | 447 | 41.88s | 42.30s | **0.42s** | 0.28s | 1.63x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 41.95s | 42.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 41.95s | 42.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 41.95s | 42.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_8` | `DECORATIVE` | 1100 | 1650 | 41.95s | 42.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 41.95s | 42.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_10` | `DECORATIVE` | 1485 | 2228 | 41.95s | 42.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_07` (Panel 7)
- **النص المنطوق:** *"هؤلاء يعيشون بعيداً عن كثير من التعقيدات اللي تستهلكنا احنا كل يوم. ما عنده خبث ..."*
- **Speech Window:** `[42.30s -> 50.10s]` (مدة الكلام: **7.80s**)
- **Drawing Window:** `[42.30s -> 50.10s]` (مدة الرسم الفعلية: **7.80s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[50.10s -> 50.65s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_07' for element 'Panel 07 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_07' for element 'Panel 07 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_07' for element 'Panel 07 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 42.30s | 43.11s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 1626 | 2438 | 42.99s | 46.18s | **3.19s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `SECONDARY` | 290 | 435 | 45.06s | 45.49s | **0.43s** | 0.28s | 1.56x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_4` | `SECONDARY` | 592 | 888 | 45.38s | 46.27s | **0.89s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 46.14s | 48.04s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 47.57s | 49.47s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 49.00s | 50.10s | **1.10s** | 0.28s | 2.20x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_8` | `DECORATIVE` | 1100 | 1650 | 49.75s | 50.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 49.75s | 50.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_10` | `DECORATIVE` | 1100 | 1650 | 49.75s | 50.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_08` (Panel 8)
- **النص المنطوق:** *"الرسالة، ولا يشيل هم بعد عشر سنين، ولا يدخل نفسه في الف احتمال. هو ببساطة، يعيش ..."*
- **Speech Window:** `[50.10s -> 56.10s]` (مدة الكلام: **6.00s**)
- **Drawing Window:** `[50.10s -> 56.10s]` (مدة الرسم الفعلية: **6.00s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[56.10s -> 56.65s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_08' for element 'Panel 08 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_08' for element 'Panel 08 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_08' for element 'Panel 08 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_08' for element 'Panel 08 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_08' for element 'Panel 08 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_08' for element 'Panel 08 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 50.10s | 50.91s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 1645 | 2467 | 50.79s | 54.02s | **3.23s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `PRIMARY` | 1107 | 1661 | 53.21s | 55.38s | **2.17s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `SECONDARY` | 294 | 441 | 54.62s | 55.06s | **0.44s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `SECONDARY` | 437 | 655 | 54.95s | 55.61s | **0.66s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 55.51s | 56.10s | **0.59s** | 0.28s | 2.20x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 55.75s | 56.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_8` | `DECORATIVE` | 1100 | 1650 | 55.75s | 56.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 55.75s | 56.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_10` | `DECORATIVE` | 1100 | 1650 | 55.75s | 56.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_11` | `DECORATIVE` | 1100 | 1650 | 55.75s | 56.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_12` | `DECORATIVE` | 1100 | 1650 | 55.75s | 56.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_09` (Panel 9)
- **النص المنطوق:** *"من 70 الى 84، ندخل على مستوى ذكاء الشوارع. هذول يمثلون تقريباً 14% من المجتمع، ي..."*
- **Speech Window:** `[56.10s -> 62.70s]` (مدة الكلام: **6.60s**)
- **Drawing Window:** `[56.10s -> 62.70s]` (مدة الرسم الفعلية: **6.60s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[62.70s -> 63.25s]` (مدة الثبات: **0.55s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `70` (NUMBER) @ `56.40s` -> Type: `LEAD_IN`, Confidence: `0.92`
  - 🎯 `84،` (OBJECT) @ `57.00s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `ذكاء` (OBJECT) @ `58.20s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `14%` (NUMBER) @ `59.70s` -> Type: `DURING`, Confidence: `0.92`
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_09' for element 'Panel 09 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_09' for element 'Panel 09 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 56.10s | 56.91s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `DECORATIVE` | 1100 | 1650 | 56.71s | 58.61s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_3` | `PRIMARY` | 1632 | 2448 | 58.33s | 61.53s | **3.20s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `PRIMARY` | 1504 | 2256 | 60.73s | 62.70s | **1.97s** | 0.55s | 1.76x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_5` | `SECONDARY` | 298 | 447 | 62.01s | 62.46s | **0.45s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 62.35s | 62.70s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 62.35s | 62.70s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_10` (Panel 10)
- **النص المنطوق:** *"في المدرسة، هنا تبدأ المعاناة. رياضيات، فيزياء، معادلات طويلة، نص أدبي من ثلاث ص..."*
- **Speech Window:** `[62.70s -> 66.90s]` (مدة الكلام: **4.20s**)
- **Drawing Window:** `[62.70s -> 66.90s]` (مدة الرسم الفعلية: **4.20s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[66.90s -> 67.45s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_10' for element 'Panel 10 - Icon / Graphic' (298px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_10' for element 'Panel 10 - Icon / Graphic' (1037px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_10' for element 'Panel 10 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_10' for element 'Panel 10 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_10' for element 'Panel 10 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_10' for element 'Panel 10 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_10' for element 'Panel 10 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_10' for element 'Panel 10 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_10' for element 'Panel 10 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_10' for element 'Panel 10 - Card Text Line 1' (1485px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 62.70s | 63.51s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `DECORATIVE` | 1100 | 1650 | 63.31s | 65.21s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_3` | `PRIMARY` | 1216 | 1824 | 64.93s | 66.90s | **1.97s** | 0.55s | 1.42x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `SECONDARY` | 1430 | 2145 | 66.21s | 66.90s | **0.69s** | 0.28s | 2.20x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `SECONDARY` | 298 | 447 | 66.55s | 66.90s | **0.35s** | 0.28s | 1.97x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_6` | `SECONDARY` | 1037 | 1556 | 66.55s | 66.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 66.55s | 66.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_8` | `DECORATIVE` | 1100 | 1650 | 66.55s | 66.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 66.55s | 66.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_10` | `DECORATIVE` | 1100 | 1650 | 66.55s | 66.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_11` | `DECORATIVE` | 1100 | 1650 | 66.55s | 66.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_12` | `DECORATIVE` | 1100 | 1650 | 66.55s | 66.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_13` | `DECORATIVE` | 1100 | 1650 | 66.55s | 66.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_14` | `DECORATIVE` | 1485 | 2228 | 66.55s | 66.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_11` (Panel 11)
- **النص المنطوق:** *"يعطى هالكتاب ويمكن يقفله بعد أول فقرة. لكن في الحياة الواقعية، هذول ملوك التصرف...."*
- **Speech Window:** `[66.90s -> 71.10s]` (مدة الكلام: **4.20s**)
- **Drawing Window:** `[66.90s -> 71.10s]` (مدة الرسم الفعلية: **4.20s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[71.10s -> 71.65s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_11' for element 'Panel 11 - Icon / Graphic' (298px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_11' for element 'Panel 11 - Icon / Graphic' (1361px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_11' for element 'Panel 11 - Icon / Graphic' (508px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_11' for element 'Panel 11 - Icon / Graphic' (592px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_11' for element 'Panel 11 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_11' for element 'Panel 11 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_11' for element 'Panel 11 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_11' for element 'Panel 11 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_11' for element 'Panel 11 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_11' for element 'Panel 11 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 66.90s | 67.71s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `DECORATIVE` | 1100 | 1650 | 67.51s | 69.41s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_3` | `PRIMARY` | 2138 | 3206 | 69.13s | 71.10s | **1.97s** | 0.55s | 2.20x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `PRIMARY` | 1056 | 1584 | 70.61s | 71.10s | **0.49s** | 0.55s | 2.20x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_5` | `SECONDARY` | 298 | 447 | 70.75s | 71.10s | **0.35s** | 0.28s | 1.97x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_6` | `SECONDARY` | 1361 | 2041 | 70.75s | 71.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_7` | `SECONDARY` | 508 | 762 | 70.75s | 71.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_8` | `SECONDARY` | 592 | 888 | 70.75s | 71.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 70.75s | 71.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_10` | `DECORATIVE` | 1100 | 1650 | 70.75s | 71.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_11` | `DECORATIVE` | 1100 | 1650 | 70.75s | 71.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_12` | `DECORATIVE` | 1100 | 1650 | 70.75s | 71.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_13` | `DECORATIVE` | 1100 | 1650 | 70.75s | 71.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_14` | `DECORATIVE` | 1100 | 1650 | 70.75s | 71.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_12` (Panel 12)
- **النص المنطوق:** *"تعطلت سيارتك في البر؟ هنا يبدأ السحر. ما عنده القطعة المناسبة؟..."*
- **Speech Window:** `[71.10s -> 74.40s]` (مدة الكلام: **3.30s**)
- **Drawing Window:** `[71.10s -> 74.40s]` (مدة الرسم الفعلية: **3.30s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[74.40s -> 74.95s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Icon / Graphic' (374px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Icon / Graphic' (1235px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_12' for element 'Panel 12 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 71.10s | 71.91s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `DECORATIVE` | 1100 | 1650 | 71.71s | 73.61s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_3` | `PRIMARY` | 819 | 1229 | 73.33s | 74.40s | **1.07s** | 0.55s | 1.76x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `SECONDARY` | 298 | 447 | 74.02s | 74.40s | **0.38s** | 0.28s | 1.83x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `SECONDARY` | 374 | 561 | 74.05s | 74.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_6` | `SECONDARY` | 1235 | 1852 | 74.05s | 74.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 74.05s | 74.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_8` | `DECORATIVE` | 1100 | 1650 | 74.05s | 74.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 74.05s | 74.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_10` | `DECORATIVE` | 1100 | 1650 | 74.05s | 74.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_11` | `DECORATIVE` | 1100 | 1650 | 74.05s | 74.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_12` | `DECORATIVE` | 1100 | 1650 | 74.05s | 74.40s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_13` (Panel 13)
- **النص المنطوق:** *"عادي! ما عنده الادوات الكاملة، ما يفرق...."*
- **Speech Window:** `[74.40s -> 76.50s]` (مدة الكلام: **2.10s**)
- **Drawing Window:** `[74.40s -> 76.50s]` (مدة الرسم الفعلية: **2.10s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[76.50s -> 77.05s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_13' for element 'Panel 13 - Icon / Graphic' (1252px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_13' for element 'Panel 13 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_13' for element 'Panel 13 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_13' for element 'Panel 13 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_13' for element 'Panel 13 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_13' for element 'Panel 13 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_13' for element 'Panel 13 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 74.40s | 75.21s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 2394 | 3590 | 75.09s | 76.50s | **1.41s** | 0.55s | 2.20x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `SECONDARY` | 298 | 447 | 76.01s | 76.46s | **0.45s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_4` | `SECONDARY` | 1252 | 1877 | 76.15s | 76.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 76.15s | 76.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 76.15s | 76.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 76.15s | 76.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_8` | `DECORATIVE` | 1100 | 1650 | 76.15s | 76.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 76.15s | 76.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_10` | `DECORATIVE` | 1100 | 1650 | 76.15s | 76.50s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_14` (Panel 14)
- **النص المنطوق:** *"يلفها بشطرطون، يربطها بمغاط، يركب حل مؤقت من ثلاث قطع ويقول لك: شغل. وانت فعلا ت..."*
- **Speech Window:** `[76.50s -> 81.90s]` (مدة الكلام: **5.40s**)
- **Drawing Window:** `[76.50s -> 81.90s]` (مدة الرسم الفعلية: **5.40s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[81.90s -> 82.45s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_14' for element 'Panel 14 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_14' for element 'Panel 14 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_14' for element 'Panel 14 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_14' for element 'Panel 14 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_14' for element 'Panel 14 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_14' for element 'Panel 14 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 76.50s | 77.31s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `DECORATIVE` | 1100 | 1650 | 77.11s | 79.01s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_3` | `PRIMARY` | 294 | 441 | 78.73s | 79.31s | **0.58s** | 0.55s | 1.17x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `PRIMARY` | 454 | 680 | 79.16s | 80.05s | **0.89s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_5` | `SECONDARY` | 470 | 706 | 79.74s | 80.45s | **0.71s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_6` | `SECONDARY` | 479 | 718 | 80.27s | 80.99s | **0.72s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_7` | `PRIMARY` | 437 | 655 | 80.88s | 81.74s | **0.86s** | 0.55s | 1.17x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_8` | `PRIMARY` | 1159 | 1739 | 81.53s | 81.90s | **0.37s** | 0.55s | 2.20x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 81.55s | 81.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_10` | `DECORATIVE` | 1100 | 1650 | 81.55s | 81.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_11` | `DECORATIVE` | 1100 | 1650 | 81.55s | 81.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_12` | `DECORATIVE` | 1100 | 1650 | 81.55s | 81.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_13` | `DECORATIVE` | 1100 | 1650 | 81.55s | 81.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_14` | `DECORATIVE` | 1100 | 1650 | 81.55s | 81.90s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_15` (Panel 15)
- **النص المنطوق:** *"هو ممكن ما يقدر يكتب لك مقال اكاديمي مرتب، لكنه يعرف كيف يفك المكينة، كيف يطلع م..."*
- **Speech Window:** `[81.90s -> 88.80s]` (مدة الكلام: **6.90s**)
- **Drawing Window:** `[81.90s -> 88.80s]` (مدة الرسم الفعلية: **6.90s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[88.80s -> 89.35s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_15' for element 'Panel 15 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_15' for element 'Panel 15 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_15' for element 'Panel 15 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_15' for element 'Panel 15 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_15' for element 'Panel 15 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_15' for element 'Panel 15 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_15' for element 'Panel 15 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 81.90s | 82.71s | **0.81s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `DECORATIVE` | 1100 | 1650 | 82.51s | 84.41s | **1.90s** | 0.28s | 1.33x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_3` | `PRIMARY` | 1165 | 1747 | 84.13s | 86.41s | **2.28s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `PRIMARY` | 1235 | 1853 | 85.84s | 88.26s | **2.42s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_5` | `SECONDARY` | 302 | 454 | 87.41s | 87.86s | **0.45s** | 0.28s | 1.55x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 87.79s | 88.80s | **1.01s** | 0.28s | 2.20x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 88.45s | 88.80s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_8` | `DECORATIVE` | 1100 | 1650 | 88.45s | 88.80s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 88.45s | 88.80s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_10` | `DECORATIVE` | 1100 | 1650 | 88.45s | 88.80s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_11` | `DECORATIVE` | 1100 | 1650 | 88.45s | 88.80s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_12` | `DECORATIVE` | 1100 | 1650 | 88.45s | 88.80s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_13` | `DECORATIVE` | 1100 | 1650 | 88.45s | 88.80s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_16` (Panel 16)
- **النص المنطوق:** *"هذي عقول مبرمجة على المشاكل اللي تنشاف بالعين وتلمس باليد. ما يهمه كثير الكلام ا..."*
- **Speech Window:** `[88.80s -> 89.30s]` (مدة الكلام: **0.50s**)
- **Drawing Window:** `[88.80s -> 89.30s]` (مدة الرسم الفعلية: **0.50s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[89.30s -> 89.85s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[HIGH] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_16' for element 'Panel 16 - Character / Person' (2131px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_16' for element 'Panel 16 - Icon / Graphic' (311px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_16' for element 'Panel 16 - Icon / Graphic' (1151px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_16' for element 'Panel 16 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_16' for element 'Panel 16 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_16' for element 'Panel 16 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_16' for element 'Panel 16 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_16' for element 'Panel 16 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 88.80s | 89.30s | **0.50s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 2131 | 3197 | 88.95s | 89.30s | **0.35s** | 0.55s | 2.20x | `NORMAL` | *Budget compressed schedule (PRIMARY, DRA* |
  | `elem_3` | `SECONDARY` | 311 | 466 | 88.95s | 89.30s | **0.35s** | 0.28s | 2.05x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_4` | `SECONDARY` | 1151 | 1726 | 88.95s | 89.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (SECONDARY, D* |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 88.95s | 89.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 88.95s | 89.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_7` | `DECORATIVE` | 1100 | 1650 | 88.95s | 89.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_8` | `DECORATIVE` | 1100 | 1650 | 88.95s | 89.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |
  | `elem_9` | `DECORATIVE` | 1100 | 1650 | 88.95s | 89.30s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

### 🔗 روابط الانتقال بين النبضات (`BeatTransitions`)
| From Beat | To Beat | Start Time | End Time | Transition Type | Strategy |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `vbeat_01` | `vbeat_02` | 4.50s | 4.50s | `KEEP` | Additive hold: canvas retained as vbeat_02 commences |
| `vbeat_02` | `vbeat_03` | 11.40s | 11.40s | `KEEP` | Additive hold: canvas retained as vbeat_03 commences |
| `vbeat_03` | `vbeat_04` | 19.20s | 19.20s | `KEEP` | Additive hold: canvas retained as vbeat_04 commences |
| `vbeat_04` | `vbeat_05` | 30.60s | 30.60s | `KEEP` | Additive hold: canvas retained as vbeat_05 commences |
| `vbeat_05` | `vbeat_06` | 37.50s | 37.50s | `KEEP` | Additive hold: canvas retained as vbeat_06 commences |
| `vbeat_06` | `vbeat_07` | 42.30s | 42.30s | `KEEP` | Additive hold: canvas retained as vbeat_07 commences |
| `vbeat_07` | `vbeat_08` | 50.10s | 50.10s | `KEEP` | Additive hold: canvas retained as vbeat_08 commences |
| `vbeat_08` | `vbeat_09` | 56.10s | 56.10s | `KEEP` | Additive hold: canvas retained as vbeat_09 commences |
| `vbeat_09` | `vbeat_10` | 62.70s | 62.70s | `KEEP` | Additive hold: canvas retained as vbeat_10 commences |
| `vbeat_10` | `vbeat_11` | 66.90s | 66.90s | `KEEP` | Additive hold: canvas retained as vbeat_11 commences |
| `vbeat_11` | `vbeat_12` | 71.10s | 71.10s | `KEEP` | Additive hold: canvas retained as vbeat_12 commences |
| `vbeat_12` | `vbeat_13` | 74.40s | 74.40s | `KEEP` | Additive hold: canvas retained as vbeat_13 commences |
| `vbeat_13` | `vbeat_14` | 76.50s | 76.50s | `KEEP` | Additive hold: canvas retained as vbeat_14 commences |
| `vbeat_14` | `vbeat_15` | 81.90s | 81.90s | `KEEP` | Additive hold: canvas retained as vbeat_15 commences |
| `vbeat_15` | `vbeat_16` | 88.80s | 88.80s | `KEEP` | Additive hold: canvas retained as vbeat_16 commences |

---

## 3. Visually Distinct Storyboard (Sheet 2 - Tools, Cars, Direction Arrows)
- **ملف الصورة:** `ChatGPT Image Sep 17, 2026, 06_05_24 PM.png`
- **عدد البانلات المكتشفة:** 12
- **المدة الصوتية:** 66.90 ثانية
- **عدد النبضات البصرية المنفذة:** 12
- **عدد روابط الانتقال بين النبضات (`BeatTransitions`):** 11

### 📊 جدول ملخص النبضات البصرية والنوافذ الزمنية الثلاث
| Beat ID | Panel | Speech Window | Drawing Window | Hold Window | Total Effort (px) | Feasibility | Conflicts |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `vbeat_01` | 1 | [0.00s - 8.10s] (8.10s) | [0.00s - 7.34s] (7.34s) | [7.34s - 8.10s] (0.76s) | 7808 | `FAST/NORMAL` | ✅ 0 |
| `vbeat_02` | 2 | [8.10s - 19.20s] (11.10s) | [8.10s - 18.03s] (9.93s) | [18.03s - 19.20s] (1.17s) | 9574 | `FAST/NORMAL` | ✅ 0 |
| `vbeat_03` | 3 | [19.20s - 30.60s] (11.40s) | [19.20s - 28.14s] (8.94s) | [28.14s - 30.60s] (2.46s) | 6270 | `NORMAL` | ✅ 0 |
| `vbeat_04` | 4 | [30.60s - 41.70s] (11.10s) | [30.60s - 41.70s] (11.10s) | [41.70s - 42.25s] (0.55s) | 14777 | `NORMAL/LIMITED` | ⚠️ 1 Conflicts |
| `vbeat_05` | 5 | [41.70s - 50.10s] (8.40s) | [41.70s - 50.10s] (8.40s) | [50.10s - 50.65s] (0.55s) | 11716 | `FAST/NORMAL` | ⚠️ 1 Conflicts |
| `vbeat_06` | 6 | [50.10s - 56.10s] (6.00s) | [50.10s - 56.10s] (6.00s) | [56.10s - 56.65s] (0.55s) | 7162 | `NORMAL` | ✅ 0 |
| `vbeat_07` | 7 | [56.10s - 64.20s] (8.10s) | [56.10s - 64.20s] (8.10s) | [64.20s - 64.75s] (0.55s) | 10055 | `NORMAL/LIMITED` | ✅ 0 |
| `vbeat_08` | 8 | [64.20s - 71.10s] (6.90s) | [64.20s - 71.10s] (6.90s) | [71.10s - 71.65s] (0.55s) | 7430 | `NORMAL` | ✅ 0 |
| `vbeat_09` | 9 | [71.10s - 74.40s] (3.30s) | [71.10s - 74.40s] (3.30s) | [74.40s - 74.95s] (0.55s) | 5962 | `NORMAL` | ✅ 0 |
| `vbeat_10` | 10 | [74.40s - 80.40s] (6.00s) | [74.40s - 80.40s] (6.00s) | [80.40s - 80.95s] (0.55s) | 9994 | `NORMAL` | ✅ 0 |
| `vbeat_11` | 11 | [80.40s - 88.80s] (8.40s) | [80.40s - 88.25s] (7.85s) | [88.25s - 88.80s] (0.55s) | 6221 | `NORMAL` | ✅ 0 |
| `vbeat_12` | 12 | [88.80s - 89.30s] (0.50s) | [88.80s - 89.30s] (0.50s) | [89.30s - 89.85s] (0.55s) | 4867 | `NORMAL` | ✅ 0 |

### 🔍 تفاصيل العناصر وقرارات التوقيت الفيزيائي في كل نبضة
#### 📍 `vbeat_01` (Panel 1)
- **النص المنطوق:** *"خلينا نبدا من أول مستوى، المستوى التأسيسي، اللي يكون فيه معدل الذكاء أقل من 70. ..."*
- **Speech Window:** `[0.00s -> 8.10s]` (مدة الكلام: **8.10s**)
- **Drawing Window:** `[0.00s -> 7.34s]` (مدة الرسم الفعلية: **7.34s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[7.34s -> 8.10s]` (مدة الثبات: **0.76s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `الذكاء` (OBJECT) @ `3.30s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `70.` (OBJECT) @ `4.20s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `2%` (NUMBER) @ `7.20s` -> Type: `DURING`, Confidence: `0.92`
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 0.00s | 1.28s | **1.28s** | 0.28s | 1.59x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `SECONDARY` | 546 | 819 | 1.09s | 1.91s | **0.82s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_3` | `SECONDARY` | 542 | 813 | 1.70s | 2.51s | **0.81s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_4` | `SECONDARY` | 504 | 756 | 2.31s | 3.07s | **0.76s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_5` | `SECONDARY` | 533 | 800 | 2.88s | 3.68s | **0.80s** | 0.28s | 1.54x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_6` | `PRIMARY` | 1100 | 1650 | 3.56s | 5.72s | **2.16s** | 0.55s | 1.17x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_7` | `PRIMARY` | 1100 | 1650 | 5.18s | 7.34s | **2.16s** | 0.55s | 1.17x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |

#### 📍 `vbeat_02` (Panel 2)
- **النص المنطوق:** *"لكن بعيداً عن الأرقام، كيف تكون الحياة من داخل هذا المستوى؟ ببساطة الدماغ هنا يو..."*
- **Speech Window:** `[8.10s -> 19.20s]` (مدة الكلام: **11.10s**)
- **Drawing Window:** `[8.10s -> 18.03s]` (مدة الرسم الفعلية: **9.93s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[18.03s -> 19.20s]` (مدة الثبات: **1.17s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `الدماغ` (OBJECT) @ `11.70s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `خطورة` (OBJECT) @ `17.40s` -> Type: `DURING`, Confidence: `0.80`
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 8.10s | 9.55s | **1.45s** | 0.28s | 1.40x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 3302 | 4954 | 9.33s | 15.81s | **6.48s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `DECORATIVE` | 1100 | 1650 | 14.84s | 16.66s | **1.82s** | 0.28s | 1.39x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_4` | `DECORATIVE` | 1100 | 1650 | 16.21s | 18.03s | **1.82s** | 0.28s | 1.39x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |

#### 📍 `vbeat_03` (Panel 3)
- **النص المنطوق:** *"له نكتة فيها تلاعب بالكلمات، ممكن يطالع فيك كأن مخه للتو قال لك إيرور. اللي معدل..."*
- **Speech Window:** `[19.20s -> 30.60s]` (مدة الكلام: **11.40s**)
- **Drawing Window:** `[19.20s -> 28.14s]` (مدة الرسم الفعلية: **8.94s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[28.14s -> 30.60s]` (مدة الثبات: **2.46s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `إيرور.` (OBJECT) @ `23.10s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `50` (NUMBER) @ `24.30s` -> Type: `DURING`, Confidence: `0.92`
  - 🎯 `70` (NUMBER) @ `24.90s` -> Type: `DURING`, Confidence: `0.92`
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 880 | 1320 | 19.20s | 21.48s | **2.28s** | 0.55s | 0.89x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_2` | `DECORATIVE` | 1100 | 1650 | 21.14s | 23.94s | **2.80s** | 0.28s | 0.91x | `NORMAL` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_3` | `DECORATIVE` | 1100 | 1650 | 23.24s | 26.04s | **2.80s** | 0.28s | 0.91x | `NORMAL` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_4` | `DECORATIVE` | 1100 | 1650 | 25.34s | 28.14s | **2.80s** | 0.28s | 0.91x | `NORMAL` | *Physical demand schedule (DECORATIVE, ef* |

#### 📍 `vbeat_04` (Panel 4)
- **النص المنطوق:** *"لكن اذا نزل المستوى تحت 35، هنا يصير الشخص معتمداً بشكل كبير على غيره في احتياجا..."*
- **Speech Window:** `[30.60s -> 41.70s]` (مدة الكلام: **11.10s**)
- **Drawing Window:** `[30.60s -> 41.70s]` (مدة الرسم الفعلية: **11.10s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[41.70s -> 42.25s]` (مدة الثبات: **0.55s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `35،` (OBJECT) @ `32.10s` -> Type: `DURING`, Confidence: `0.80`
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_04' for element 'Panel 04 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 30.60s | 31.54s | **0.94s** | 0.28s | 2.16x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 2438 | 3658 | 31.40s | 36.18s | **4.78s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `PRIMARY` | 2016 | 3024 | 34.98s | 38.93s | **3.95s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `PRIMARY` | 2317 | 3475 | 37.95s | 41.70s | **3.75s** | 0.55s | 1.42x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 41.14s | 41.70s | **0.56s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_6` | `DECORATIVE` | 1100 | 1650 | 41.35s | 41.70s | **0.35s** | 0.28s | 2.20x | `LIMITED` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_05` (Panel 5)
- **النص المنطوق:** *"مختلف تماماً. هؤلاء يعيشون بعيداً عن كثير من التعقيدات اللي تستهلكنا احنا كل يوم..."*
- **Speech Window:** `[41.70s -> 50.10s]` (مدة الكلام: **8.40s**)
- **Drawing Window:** `[41.70s -> 50.10s]` (مدة الرسم الفعلية: **8.40s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[50.10s -> 50.65s]` (مدة الثبات: **0.55s**)
- **⚠️ تعارضات التوقيت المكتشفة ومحاولات الحل (`Timing Conflicts`):**
  - **[MEDIUM] DRAWING_BUDGET_CONFLICT:** Drawing budget exhausted in beat 'vbeat_05' for element 'Panel 05 - Text_line' (1100px linework).
    - *محاولة الحل:* Compressed and overlapped into final slot of beat window.
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 2093 | 3139 | 41.70s | 45.81s | **4.11s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_2` | `PRIMARY` | 2707 | 4061 | 44.78s | 50.09s | **5.31s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `SECONDARY` | 811 | 1216 | 48.23s | 49.45s | **1.22s** | 0.28s | 1.53x | `FAST` | *Physical demand schedule (SECONDARY, eff* |
  | `elem_4` | `DECORATIVE` | 1100 | 1650 | 49.27s | 50.10s | **0.83s** | 0.28s | 2.20x | `FAST` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_5` | `DECORATIVE` | 1100 | 1650 | 49.75s | 50.10s | **0.35s** | 0.28s | 2.20x | `FAST` | *Budget compressed schedule (DECORATIVE, * |

#### 📍 `vbeat_06` (Panel 6)
- **النص المنطوق:** *"الرسالة، ولا يشيل هم بعد عشر سنين، ولا يدخل نفسه في الف احتمال. هو ببساطة، يعيش ..."*
- **Speech Window:** `[50.10s -> 56.10s]` (مدة الكلام: **6.00s**)
- **Drawing Window:** `[50.10s -> 56.10s]` (مدة الرسم الفعلية: **6.00s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[56.10s -> 56.65s]` (مدة الثبات: **0.55s**)
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 2598 | 3898 | 50.10s | 55.20s | **5.10s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_2` | `PRIMARY` | 2176 | 3264 | 53.93s | 56.10s | **2.17s** | 0.55s | 2.20x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |

#### 📍 `vbeat_07` (Panel 7)
- **النص المنطوق:** *"من 70 الى 84، ندخل على مستوى ذكاء الشوارع. هذول يمثلون تقريباً 14% من المجتمع، ي..."*
- **Speech Window:** `[56.10s -> 64.20s]` (مدة الكلام: **8.10s**)
- **Drawing Window:** `[56.10s -> 64.20s]` (مدة الرسم الفعلية: **8.10s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[64.20s -> 64.75s]` (مدة الثبات: **0.55s**)
- **النقاط الدلالية الثابتة (`Semantic Anchors`):**
  - 🎯 `70` (NUMBER) @ `56.40s` -> Type: `LEAD_IN`, Confidence: `0.92`
  - 🎯 `84،` (OBJECT) @ `57.00s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `ذكاء` (OBJECT) @ `58.20s` -> Type: `DURING`, Confidence: `0.80`
  - 🎯 `14%` (NUMBER) @ `59.70s` -> Type: `DURING`, Confidence: `0.92`
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `DECORATIVE` | 880 | 1320 | 56.10s | 57.09s | **0.99s** | 0.28s | 2.05x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |
  | `elem_2` | `PRIMARY` | 1613 | 2419 | 56.94s | 60.10s | **3.16s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_3` | `PRIMARY` | 3110 | 4666 | 59.31s | 64.20s | **4.89s** | 0.55s | 1.47x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_4` | `DECORATIVE` | 1100 | 1650 | 63.47s | 64.20s | **0.73s** | 0.28s | 2.20x | `LIMITED` | *Physical demand schedule (DECORATIVE, ef* |

#### 📍 `vbeat_08` (Panel 8)
- **النص المنطوق:** *"رياضيات، فيزياء، معادلات طويلة، نص أدبي من ثلاث صفحات... يعطى هالكتاب ويمكن يقفل..."*
- **Speech Window:** `[64.20s -> 71.10s]` (مدة الكلام: **6.90s**)
- **Drawing Window:** `[64.20s -> 71.10s]` (مدة الرسم الفعلية: **6.90s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[71.10s -> 71.65s]` (مدة الثبات: **0.55s**)
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 2259 | 3389 | 64.20s | 68.63s | **4.43s** | 0.55s | 1.18x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_2` | `PRIMARY` | 2694 | 4042 | 67.52s | 71.10s | **3.58s** | 0.55s | 1.74x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |

#### 📍 `vbeat_09` (Panel 9)
- **النص المنطوق:** *"تعطلت سيارتك في البر؟ هنا يبدأ السحر. ما عنده القطعة المناسبة؟..."*
- **Speech Window:** `[71.10s -> 74.40s]` (مدة الكلام: **3.30s**)
- **Drawing Window:** `[71.10s -> 74.40s]` (مدة الرسم الفعلية: **3.30s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[74.40s -> 74.95s]` (مدة الثبات: **0.55s**)
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 3974 | 5962 | 71.10s | 74.40s | **3.30s** | 0.55s | 2.20x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |

#### 📍 `vbeat_10` (Panel 10)
- **النص المنطوق:** *"عادي! ما عنده الادوات الكاملة، ما يفرق. يلفها بشطرطون، يربطها بمغاط، يركب حل مؤق..."*
- **Speech Window:** `[74.40s -> 80.40s]` (مدة الكلام: **6.00s**)
- **Drawing Window:** `[74.40s -> 80.40s]` (مدة الرسم الفعلية: **6.00s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[80.40s -> 80.95s]` (مدة الثبات: **0.55s**)
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 3686 | 5530 | 74.40s | 80.40s | **6.00s** | 0.55s | 1.33x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |
  | `elem_2` | `PRIMARY` | 2976 | 4464 | 78.90s | 80.40s | **1.50s** | 0.55s | 2.20x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |

#### 📍 `vbeat_11` (Panel 11)
- **النص المنطوق:** *"وانت فعلا تشغل السيارة وتمشي. هو ممكن ما يقدر يكتب لك مقال اكاديمي مرتب، لكنه يع..."*
- **Speech Window:** `[80.40s -> 88.80s]` (مدة الكلام: **8.40s**)
- **Drawing Window:** `[80.40s -> 88.25s]` (مدة الرسم الفعلية: **7.85s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[88.25s -> 88.80s]` (مدة الثبات: **0.55s**)
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 4147 | 6221 | 80.40s | 88.25s | **7.85s** | 0.55s | 1.02x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |

#### 📍 `vbeat_12` (Panel 12)
- **النص المنطوق:** *"هذي عقول مبرمجة على المشاكل اللي تنشاف بالعين وتلمس باليد. ما يهمه كثير الكلام ا..."*
- **Speech Window:** `[88.80s -> 89.30s]` (مدة الكلام: **0.50s**)
- **Drawing Window:** `[88.80s -> 89.30s]` (مدة الرسم الفعلية: **0.50s**)
- **Hold Window (بقاء العنصر في نظر المشاهد):** `[89.30s -> 89.85s]` (مدة الثبات: **0.55s**)
- **تفاصيل العناصر والجهد الفيزيائي:**
  | Element ID | Tier | Arc Length (px) | Physical Effort | Start | End | Draw Dur | Hold Dur | Speed Mult | Feasibility | Rationale |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
  | `elem_1` | `PRIMARY` | 3245 | 4867 | 88.80s | 89.30s | **0.50s** | 0.55s | 2.20x | `NORMAL` | *Physical demand schedule (PRIMARY, effor* |

### 🔗 روابط الانتقال بين النبضات (`BeatTransitions`)
| From Beat | To Beat | Start Time | End Time | Transition Type | Strategy |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `vbeat_01` | `vbeat_02` | 7.34s | 8.10s | `KEEP` | Additive hold: canvas retained as vbeat_02 commences |
| `vbeat_02` | `vbeat_03` | 18.03s | 19.20s | `KEEP` | Additive hold: canvas retained as vbeat_03 commences |
| `vbeat_03` | `vbeat_04` | 28.14s | 30.60s | `KEEP` | Additive hold: canvas retained as vbeat_04 commences |
| `vbeat_04` | `vbeat_05` | 41.70s | 41.70s | `KEEP` | Additive hold: canvas retained as vbeat_05 commences |
| `vbeat_05` | `vbeat_06` | 50.10s | 50.10s | `KEEP` | Additive hold: canvas retained as vbeat_06 commences |
| `vbeat_06` | `vbeat_07` | 56.10s | 56.10s | `KEEP` | Additive hold: canvas retained as vbeat_07 commences |
| `vbeat_07` | `vbeat_08` | 64.20s | 64.20s | `KEEP` | Additive hold: canvas retained as vbeat_08 commences |
| `vbeat_08` | `vbeat_09` | 71.10s | 71.10s | `KEEP` | Additive hold: canvas retained as vbeat_09 commences |
| `vbeat_09` | `vbeat_10` | 74.40s | 74.40s | `KEEP` | Additive hold: canvas retained as vbeat_10 commences |
| `vbeat_10` | `vbeat_11` | 80.40s | 80.40s | `KEEP` | Additive hold: canvas retained as vbeat_11 commences |
| `vbeat_11` | `vbeat_12` | 88.25s | 88.80s | `KEEP` | Additive hold: canvas retained as vbeat_12 commences |

---

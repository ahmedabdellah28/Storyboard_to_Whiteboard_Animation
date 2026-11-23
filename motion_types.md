بما أنك تبني **نظام Motion Graphic يعتمد على عناصر منفصلة ثم يقرر كيف تدخل وتتحرك وتخرج من الشاشة**، فلا أنصح أن نتعامل مع الـTransition كـ«Effect» فقط. الأفضل أن نبني **Motion Templates / Motion Behaviors** قابلة لإعادة الاستخدام، لكل واحدة قواعد دخول وحركة وخروج وـEasing وارتباط بالسرد.

والترتيب التالي هو ترتيبي العملي بناءً على **الحداثة + الاحتراف + قابلية إعادة الاستخدام + ملاءمتها للـExplainer/Motion Graphics + سهولة تحويلها إلى نظام برمجي**. اتجاهات 2026 تميل إلى الحركة الهادفة، الـ2D النظيف، الـmorphing والـprocedural motion، مع تقليل الاستعراض ثلاثي الأبعاد غير الضروري. [advids.co](https://advids.co/blog/ui-animation-motion-design-trends?utm_source=chatgpt.com)



# أفضل Motion Transition Templates — بالترتيب

| الترتيب | Template | الفكرة الأساسية | أفضل استخدام |
|---|---|---|---|
| **1** | **Morph Transition** | العنصر A يتحول بصريًا إلى B بدل اختفائه وظهور الآخر | انتقال مفهوم → مفهوم |
| **2** | **Match Cut Transition** | نفس الشكل/الحركة تستمر ثم تتحول إلى عنصر آخر | ربط الأفكار بسلاسة |
| **3** | **Camera Push / Pull** | الكاميرا تقترب من عنصر ثم تكشف العنصر/المشهد التالي | التركيز والانتقال بين مستويات |
| **4** | **Directional Flow** | العناصر تتحرك في اتجاه واحد وتدفع العنصر التالي | Explainer سريع |
| **5** | **Mask Reveal / Wipe** | عنصر جديد يظهر من خلف مسار أو شكل هندسي | كشف المحتوى |
| **6** | **Object Push Transition** | العنصر الجديد يدخل ويدفع القديم خارج الشاشة | UI / Cards / Objects |
| **7** | **Whip Motion** | حركة سريعة جدًا للكاميرا أو العنصر مع Motion Blur ثم استقرار | انتقالات حماسية |
| **8** | **Scale Punch** | تكبير سريع لعنصر → انتقال → تصغير على العنصر الجديد | إبراز كلمة أو Object |
| **9** | **Orbit / Arc Motion** | العناصر تدور حول نقطة/عنصر مركزي ثم يتغير المشهد | Infographics |
| **10** | **Parallax Depth** | طبقات مختلفة تتحرك بسرعات مختلفة لإحساس العمق | مشاهد متعددة العناصر |
| **11** | **Kinetic Typography Transition** | الكلمة نفسها تصبح Transition وتتحول إلى العنصر التالي | Narration-heavy |
| **12** | **Shape Transform** | دائرة → مستطيل → خط → Icon → Object | Motion Graphics هندسي |
| **13** | **Line Path Transition** | خط مرسوم يقود العين إلى العنصر التالي | Whiteboard / Explainer |
| **14** | **Liquid / Organic Flow** | كتلة عضوية تتمدد وتتقلص وتكشف المشهد التالي | Creative / modern branding |
| **15** | **Card Stack Transition** | العناصر تدخل كطبقات/بطاقات متتابعة | UI / SaaS / Dashboard |
| **16** | **Split Screen Transition** | الشاشة تنقسم إلى أجزاء وكل جزء يكشف معلومة | مقارنة / Before & After |
| **17** | **Blur Speed Transition** | Blur + Scale/Translate سريع ثم Focus | انتقال سريع احترافي |
| **18** | **Trail / Echo Transition** | العنصر يترك آثارًا متتابعة أثناء الحركة | Energy / Speed |
| **19** | **Rotation / Spin Reveal** | دوران العنصر يكشف الوجه/العنصر التالي | Icons / Objects |
| **20** | **Elastic / Overshoot Transition** | العنصر يصل إلى موضعه ويتجاوزه قليلًا ثم يستقر | Friendly / playful |

---

# 1. Morph Transition — الأهم في نظامك

هذه بالنسبة لي **رقم 1**.

بدل:

`Element A → Fade Out → Element B`

نريد:

`Element A → Transform → Element B`

مثلاً:

**Apple → دائرة حمراء → Kiwi**

أو:

**Phone → Dashboard → Chart**

أو:

**Brain → Network → Neural Nodes**

الميزة أنها تجعل الانتقال يبدو وكأن **الفكرة نفسها تتطور** وليس مجرد تغيير مشهد.

وهذا يتماشى جدًا مع اتجاه الـshape morphing والـorganic/generative motion الحالي. [Ezgi Ergül](https://ezgiergul.com/journal/motion-design-trends-2026?utm_source=chatgpt.com)

---

# 2. Match Cut

واحدة من أكثر التقنيات الاحترافية.

مثلاً:

```text
دائرة صغيرة
    ↓
تكبر
    ↓
تصبح تفاحة
```

أو:

```text
سهم
 ↓
يتحرك لليمين
 ↓
يتحول إلى خط رسم
 ↓
الخط يصبح Chart
```

الفكرة ليست في الـEffect، بل في:

**آخر شكل من المشهد السابق = أول حركة في المشهد التالي.**

وهذا يجعل الانتقال شبه غير محسوس.

---

# 3. Camera Push / Pull

بدل تحريك العنصر، تحرك **الكاميرا**.

مثلاً:

```text
Scene
 └── عدة عناصر

Camera Zoom In
        ↓
Icon
        ↓
Zoom In
        ↓
Detail
```

وهذا ممتاز جدًا عندما يكون عندك:

- Main Element
- Secondary Elements
- Background
- Callout

لأن الكاميرا تصبح هي التي تقود عين المشاهد.

---

# 4. Directional Flow

من أقوى القوالب للـExplainer.

العناصر تتحرك في مسار واحد:

```text
A → B → C → D
```

مثلاً:

```text
Problem
   →
Process
   →
Solution
   →
Result
```

بدل أن يظهر كل عنصر بشكل مستقل، يصبح هناك **Flow بصري مستمر**.

وهذا مناسب جدًا للموشن المبني على السرد الصوتي.

---

# 5. Mask Reveal

العنصر لا يظهر فجأة.

مثلاً:

```text
────────────
      │
      │ Mask
      ▼
  [ ELEMENT ]
```

يمكن للـMask أن يكون:

- Circle
- Rectangle
- Line
- Organic blob
- Existing object

والميزة أنه بسيط جدًا برمجيًا، لكنه يعطي نتيجة احترافية.

---

# 6. Object Push

مثلاً:

```text
[ Old Element ] 
       →
             [ New Element ]
```

العنصر الجديد يدخل ويدفع القديم.

مفيد جدًا عندما يكون عندك:

```text
Icon 1
Icon 2
Icon 3
```

وتريد الانتقال بينها دون Cut واضح.

---

# 7. Whip Motion

حركة شديدة السرعة:

```text
Scene A
████████████

      >>>>>>>>

Scene B
████████████
```

مع:

- Position
- Motion Blur
- Slight Scale
- Directional Blur
- Fast easing

وهي مناسبة جدًا للمقاطع السريعة، لكن لا أنصح بجعلها الـdefault لكل انتقال.

---

# 8. Scale Punch

مثلاً:

```text
Icon
 ↓
Scale 100%
 ↓
150%
 ↓
250%
 ↓
Transition
 ↓
100%
```

يمكن استخدامها لإعطاء أهمية شديدة لعنصر معين.

مثلاً عند سماع كلمة:

**"مهم جدًا"**

يقوم العنصر بعمل:

`Scale Punch`

ثم ننتقل.

---

# 9. Orbit / Arc

العنصر لا يتحرك في خط مستقيم، وإنما على قوس.

```text
       ●
     ↗
   ↗
 ●
```

أو:

```text
     Secondary
        ●
       ↗
 Main ●
       ↘
        ●
     Secondary
```

ممتاز للـ:

- Infographics
- Networks
- Circular processes
- Systems
- Relationships

---

# 10. Parallax Depth

لو عندك:

```text
Background
Midground
Main Element
Foreground
```

لا تحركهم بنفس السرعة.

مثلاً:

```text
Background     0.2x
Midground      0.5x
Main Element   1.0x
Foreground     1.4x
```

فيظهر إحساس العمق بدون الحاجة إلى 3D حقيقي.

وهذا مهم خصوصًا لأن الـflat 2D أصبح حاضرًا بقوة في تصميمات 2026، بينما الاستخدام غير الضروري للـ3D بدأ يتراجع في بعض سياقات الـproduct/UI motion. [advids.co](https://advids.co/blog/ui-animation-motion-design-trends?utm_source=chatgpt.com)

---

# 11. Kinetic Typography

هنا **النص نفسه يصبح عنصر Motion**.

مثلاً:

```text
"سرعة"
```

الكلمة:

`Scale → Stretch → Move → Transform`

ثم تتحول إلى:

```text
⚡
```

أو:

```text
PROBLEM
```

تنقسم حروفها وتصبح:

```text
P R O B L E M
```

ثم تتحول إلى عناصر.

المهم ألا نستخدمها طوال الفيديو؛ الاتجاه الحديث يميل إلى جعل الـkinetic type **beat داخل العمل** بدل أن يكون شكل الفيديو بالكامل. [advids.co](https://advids.co/blog/ui-animation-motion-design-trends?utm_source=chatgpt.com)

---

# 12. Shape Transform

هذا ممتاز جدًا لمحركك.

مثلاً:

```text
Circle
  ↓
Rounded Rectangle
  ↓
Rectangle
  ↓
Arrow
  ↓
Icon
```

أي أنك تستطيع بناء مكتبة:

```text
circle_to_square
square_to_line
line_to_arrow
circle_to_icon
shape_to_text
```

وبذلك يصبح عندك **Motion Grammar** وليس مجرد Effects.

---

# 13. Line Path

مهم جدًا بالنسبة لأسلوب الـWhiteboard الذي تعمل عليه.

مثلاً:

```text
✏️ Line Draw
       ↓
      Arrow
       ↓
     Object
```

الخط نفسه يصبح Transition.

يمكن أن:

`Draw → Move → Connect → Reveal`

وهو مثالي للـ:

- Whiteboard
- Explainer
- Infographic
- Process
- Diagram

---

# 14. Liquid / Organic

بدل الأشكال الهندسية الصلبة:

```text
████
```

تظهر كتلة عضوية:

```text
   ~~~~~
 ~~~~~~~~
   ~~~~~
```

تتمدد وتغطي الشاشة ثم تكشف المشهد التالي.

استخدام الـorganic minimalism من الاتجاهات التي تظهر في 2026، خصوصًا عندما يكون الهدف إعطاء حركة أكثر حسية بدون المبالغة في المؤثرات. [Ezgi Ergül](https://ezgiergul.com/journal/motion-design-trends-2026?utm_source=chatgpt.com)

---

# 15. Card Stack

مثلاً:

```text
        ┌─────┐
        │ C   │
     ┌──┴─────┤
     │ B      │
  ┌──┴────────┤
  │ A         │
  └───────────┘
```

ثم:

```text
A → B → C
```

ممتاز جدًا للـ:

- Applications
- Dashboard
- SaaS
- Mobile UI
- Screens
- Features

---

# 16. Split Screen

مثلاً:

```text
┌──────────┬──────────┐
│          │          │
│    A     │    B     │
│          │          │
└──────────┴──────────┘
```

ثم يتحرك أحد الجزأين ليكشف المشهد التالي.

ممتاز للمقارنة:

```text
Before | After
Old    | New
Bad    | Good
```

---

# 17. Blur Speed

الحركة:

```text
Position
   +
Scale
   +
Blur
```

العنصر يدخل بسرعة ثم:

`Blur → Focus`

بدل:

`Fade → Show`

وهذا يعطي إحساسًا أكثر احترافية بالحركة.

---

# 18. Motion Trail / Echo

العنصر الرئيسي يتحرك ويترك وراءه نسخًا خفيفة:

```text
●
  ●
    ●
      ●
        ●
```

ثم تستقر النسخة الأخيرة.

ممتاز لـ:

- Speed
- Growth
- Technology
- Sports
- Energy

وهو من أساليب الحركة التي تظهر ضمن أنماط 2026 المتداولة. [DEmotion](https://www.trydemotion.com/blog/trending-motion-graphic-styles?utm_source=chatgpt.com)

---

# 19. Spin Reveal

العنصر يدور حول محور:

```text
Front
  ↓
Rotate
  ↓
Back
```

مثلاً:

```text
Icon
 ↓
Rotate 90°
 ↓
Different Icon
```

لكن يجب استخدامه باعتدال؛ كثرة الـSpin تعطي إحساسًا بقوالب جاهزة بسرعة.

---

# 20. Elastic / Overshoot

بدل:

```text
A ──────────────→ B
```

تكون:

```text
A ───────────────→ B
                    ↗
                  B+
                    ↓
                    B
```

أي:

`Approach → Overshoot → Settle`

وهذا من أهم أسرار جعل الـmotion يبدو حيًا بدل أن يكون مجرد Transform عادي.

---

# الأهم: لا أنصحك ببناء 20 Template منفصلة

الأفضل لمحركك أن نحولها إلى **Motion Template System**.

مثلاً:

```text
MotionTemplate
│
├── Entrance
│   ├── Slide
│   ├── Pop
│   ├── Reveal
│   ├── Scale
│   └── Draw
│
├── Transition
│   ├── Morph
│   ├── MatchCut
│   ├── CameraPush
│   ├── Whip
│   ├── ShapeTransform
│   └── Mask
│
├── Emphasis
│   ├── ScalePunch
│   ├── Shake
│   ├── Orbit
│   └── Pulse
│
├── Exit
│   ├── SlideOut
│   ├── ScaleOut
│   ├── MaskOut
│   └── MorphOut
│
└── Camera
    ├── Push
    ├── Pull
    ├── Pan
    ├── Orbit
    └── Parallax
```

ثم يكون لكل Template **Parameters**:

```text
duration
direction
distance
scale
rotation
easing
overshoot
blur
stagger
anchor_point
camera_influence
importance
energy
```

وبالتالي الـAI لا يقول:

> "استخدم Transition رقم 7"

بل يقول مثلًا:

```text
Main Element:
Morph → Camera Push

Secondary Elements:
Stagger → Directional Flow

Text:
Kinetic Accent

Exit:
Mask Reveal
```

وهنا يبدأ النظام فعليًا في التصرف كـ**Motion Director** وليس كمولد Effects.

والاتجاه الحالي في أنظمة الـmotion يميل أصلًا إلى بناء **مكتبات وقواعد motion قابلة لإعادة الاستخدام** بدل إنشاء كل حركة يدويًا من الصفر. [DigitalSilk](https://www.digitalsilk.com/digital-trends/kinetic-typography/?utm_source=chatgpt.com)

### الترتيب الذي أنصح أن نبدأ ببنائه في مشروعك

```text
01 Morph
02 Match Cut
03 Camera Push
04 Directional Flow
05 Mask Reveal
06 Object Push
07 Scale Punch
08 Whip
09 Shape Transform
10 Parallax
11 Line Draw
12 Kinetic Text
```

هذه الـ12 وحدها يمكن أن تغطي نسبة كبيرة جدًا من الانتقالات التي تحتاجها في نظام **AI Motion Graphic Generator**، وبعدها نضيف الـLiquid والـTrail والـOrbit والـ3D behaviors كطبقة متقدمة.

والنقطة المهمة: **الانتقال لا ينبغي اختياره عشوائيًا**؛ يجب أن يعتمد على معنى العنصر، نوعه، موقعه، أهميته، اتجاه الحركة السابقة، الـaudio beat، والـsemantic relationship بين العنصرين. وهذا بالضبط الجزء الذي يمكن أن نجعله Intelligent داخل محركك.
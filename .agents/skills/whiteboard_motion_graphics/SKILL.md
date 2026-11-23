---
name: whiteboard-motion-graphics
description: Comprehensive production guide and automated pipeline for viral whiteboard motion graphics explainer videos. Standardized workflow from multi-project CLI, script & storyboard input to Gemini TTS voiceover, Faster-Whisper alignment, 4-row chronological organic contour extraction, 100% 20-asset semantic manifest choreography, multi-word viral typography cards, active mid-hold motion & synchronized studio SFX, EffectCraft GPU rendering, micro-retention GIF overlays, and 1080p master merging.
---

# 🎬 Whiteboard Motion Graphics Master Production Guide (EffectCraft & Viral Retention Engine)
## الدستور الإرشادي الموحد لإنتاج ومونتاج موشن جرافيك الوايت بورد الفيرال الاحترافي (AI Agent Master Standard)

> [!NOTE]
> **دستور الاستوديو الموحد (`AION Studio V6 Constitution`):**
> 1. **الأدوات الميكانيكية عبر `pipeline_cli.py` فقط:** استخراج الصوت، محاذاة التوقيت (Whisper)، قص عناصر الـ Storyboard، تقطيع الصوت وإلحاق الـ CTA، بناء `.ecproj`، الرندر بالـ GPU، مزج الـ SFX، وتوليد ألواح الـ QA تتم حصرياً بأوامر الـ CLI.
> 2. **الإبداع والتفكير للمودل عبر ملفات التوقيت والـ JSON فقط (حظر قراءة الصور قبل الإنتاج):** يُمنع فتح صور الـ Storyboard الخام أو الصور المفرغة أثناء التخطيط أو كتابة المشاهد أو إعداد الشورتس. يفهم المودل العناصر من ملفات الـ JSON (`storyboard_catalog/*.json`, `semantic_manifest.json`, `assets/metadata.json`, أو أمر `python pipeline_cli.py studio shorts --action inspect --project <name>`) مع توقيت الجمل في `timing_master.json`.
> 3. **قراءة الصور بعد الإنتاج فقط (`Post-Render QA Only`):** لا تُفتح الصور إلا بعد الرندر لمعاينة `creative_contact_sheet.png` / `mobile_preview.png` / `qa_contact_sheet.png` أو عند تشخيص خطأ ظهر بعد الإنتاج.
> 4. راجع [SKILL.md](file:///e:/image_to_animate/SKILL.md) و[AGENTS.md](file:///e:/image_to_animate/AGENTS.md) و[CLI_REFERENCE.md](file:///e:/image_to_animate/CLI_REFERENCE.md) كمرجعية أولى دائماً.

> **الهدف الاستراتيجي**: تحويل النص المكتوب ولوحة القصة (Storyboard) إلى فيديو موشن جرافيك فيرال احترافي بنمط السبورة البيضاء الاستوديوية (تخطيط هندسي على إحداثيات `1920x1080` مع رندر افتراضي بدقة **`720p / 30 FPS`** — ويُرفع إلى `1080p` فقط عند تمرير `--resolution 1080p` صراحةً) على خلفية ورقية عاجية مريحة للعين (`#EDE8E0`)، مع:
> 1. **استيعاب كامل ودقيق لجميع عناصر لوحة القصة (20/20 عنصراً)** في توقيتها المنطوق بالمللي ثانية.
> 2. **كروت تايبوجرافي فيرال متعددة الكلمات (3 إلى 5 كلمات لكل كارت)** تلخص الحدث الدرامي في أعلى الشاشة (`Y = 220`).
> 3. **مؤثرات صوتية تفاعلية متزامنة (`Synchronized Studio SFX`)** مع كل حركة دخول، نبضة، لمعة، وتفتح كارت (مع حظر الموسيقى التصويرية `Zero-BGM`).
> 4. **حياة حركية مستمرة (`Active Mid-Hold Choreography`)** تمنع جمود العناصر بين الدخول والخروج عبر نبضات الصدمة (`scale_punches`)، وزوم الكاميرا الزاحف، والمؤثرات الدرامية (`tint_flash`, `wiggle`, `light_sweep`, `radio_waves`, `border_flash`).

---

## 📌 الفهرس الشامل (Table of Contents)
-1. [المرحلة الصفرية الإلزامية: طبيب السكربت الفيرال والتعديل الجراحي (Step 0: Viral Script Doctor & Surgical Polisher)](#-1-المرحلة-الصفرية-الإلزامية-طبيب-السكربت-الفيرال-والتعديل-الجراحي-step-0-viral-script-doctor--surgical-polisher)
0. [دستور المخرج الفيرال المحترف: القوانين الأربعة الحاسمة لمنع الرص العشوائي والجمود](#0-دستور-المخرج-الفيرال-المحترف-القوانين-الأربعة-الحاسمة-لمنع-الرص-العشوائي-والجمود)
1. [الأعمدة الأربعة لمنظومة CraftApp في خط الإنتاج](#1-الأعمدة-الأربعة-لمنظومة-craftapp-في-خط-الإنتاج)
2. [الهيكل التنظيمي وإدارة المشاريع المعزولة (Multi-Project Architecture)](#2-الهيكل-التنظيمي-وإدارة-المشاريع-المعزولة-multi-project-architecture)
3. [البروتوكول الصارم للعمليات — نظام اللوب الإنتاجي المستقل (Autonomous Production Loop)](#3-البروتوكول-الصارم-للعمليات--نظام-اللوب-الإنتاجي-المستقل-autonomous-production-loop)
4. [الهندسة المكانية، التأريض، وهندسة الـ Viral Hook (Spatial Grid, Grounding & Viral Hook)](#4-الهندسة-المكانية-التأريض-وهندسة-الـ-viral-hook-spatial-grid-grounding--viral-hook)
5. [كوريغرافيا المقارنات الاحترافية وخط التقسيم المتحرك (Comparison Motion Graphics)](#5-كوريغرافيا-المقارنات-الاحترافية-وخط-التقسيم-المتحرك-comparison-motion-graphics)
6. [محرك الرندر المعتمد وهندسة المؤثرات الصوتية (EffectCraft GPU & SFX Synchronizer)](#6-محرك-الرندر-المعتمد-وهندسة-المؤثرات-الصوتية-effectcraft-gpu--sfx-synchronizer)
7. [كتالوج التأثيرات البصرية والقالب القياسي لـ `manifest.json` (VFX Suite & Master JSON Schema)](#7-كتالوج-التأثيرات-البصرية-والقالب-القياسي-لـ-manifestjson-vfx-suite--master-json-schema)
8. [نظام التايبوجرافي الفيرال متعدد الكلمات (Style 1 Viral Headline Card Lifecycle)](#8-نظام-التايبوجرافي-الفيرال-متعدد-الكلمات-style-1-viral-headline-card-lifecycle)
9. [مؤثرات الـ GIF التجميلية وقانون الحظر التام للموسيقى التصويرية (Micro-Retention GIFs & Zero-BGM Policy)](#9-مؤثرات-الـ-gif-التجميلية-وقانون-الحظر-التام-للموسيقى-التصويرية-micro-retention-gifs--zero-bgm-policy)
10. [دمج الفيلم الوثائقي الكامل (Full Documentary Master Merge)](#10-دمج-الفيلم-الوثائقي-الكامل-full-documentary-master-merge)
11. [قائمة الفحص الإلزامية قبل التسليم (Pre-Flight QA Checklist)](#11-قائمة-الفحص-الإلزامية-قبل-التسليم-pre-flight-qa-checklist)

---

## -1. المرحلة الصفرية الإلزامية: طبيب السكربت الفيرال والتعديل الجراحي (`Step 0: Viral Script Doctor & Surgical Polisher`)

> [!IMPORTANT]
> **متى تعمل هذه المرحلة؟**
> تعمل هذه المرحلة **قبل** تشغيل `pipeline_cli.py voice` (أو عند مراجعة وتدقيق ملفات `inputs/script/sections/section_XX.txt`).
> مهمتك هي فحص نص كل سيكشن بعين "صانع محتوى فيرال محترف" وتعديله جراحياً لعلاج عيوب السرد التي تطرد المشاهد، **مع الالتزام بالقيد المقدس: ممنوع تغيير ترتيب الأحداث الـ 20 أو حذف أي تفصيلة مرسومة في لوحة الـ Storyboard (`section_XX.png`) حتى لا يختل التزامن البصري (`20/20 Asset Sync`)!**

### 🔍 القواعد الخمس للتشخيص والتعديل الجراحي للنص (`The 5 Surgical Script Fixes`):
1. **علاج "حرق القصة الكامل في أول جملة" (`Anti-Spoiler Hook Rewrite`):**
   * اجعل الجملة الأولى تكشف **"غرابة الفعل أو حجم الصدمة"** مع إخفاء **"سر الطريقة أو التفصيلة المرعبة"** إلى نهاية السيكشن (تقنية `Open Loop`) دون حرق المفاجأة.
2. **القضاء على تكرار لازمة التحول (`Kill the Repetitive Pivot Cliché`):**
   * يُمنع تكرار عبارتي `"وهنا كانت الصدمة.."` و`"بس فجأة.."` في كل سيكشن. استبدلها بعبارات درامية مشتعلة تناسب سياق كل قصة (مثل: *"لكن اللي سواه بعدها تجاوز كل حدود الانتقام.."*، *"وهنا انقلب السحر على الساحر بطريقة مرعبة.."*، *"لكن الخطة اللي طبخها في الظلام كانت أدهى وأمر.."*).
3. **حقن "التفاصيل الحسية والتوتر الزمني" في الجمل الباردة (`Sensory & Ticking-Clock Injection`):**
   * استبدال السرد التقريري الجاف بعبارات توتر حسية وزمنية ضاغطة ومشدودة.
4. **زرع "خطافات الجسور الانتقالية" في نهاية كل سيكشن (`Micro-Bridge Cliffhangers`):**
   * إنهاء السيكشن بضربة خاطفة دون تمطيط تجعل المشاهد متشوقاً للقصة التالية.
5. **ضبط الإيقاع الصوتي ليتوافق مع الـ 20 رسمة (`3.2-Second Beat Alignment`):**
   * الطول الذهبي لكل سيكشن بعد التعديل يتراوح بين **135 إلى 165 كلمة** (`58` إلى `68` ثانية)، ليتوافق بدقة مع الـ 20 عنصراً بصرياً بمعدل `3.0` إلى `3.4` ثانية لكل عنصر.

---

## 0. دستور المخرج الفيرال المحترف: القوانين الأربعة الحاسمة لمنع الرص العشوائي والجمود

> [!CRITICAL]
> **المرجعية العليا للوكيل (The Viral Motion Director Mandate):**
> دورك ليس "رص صور على الشاشة"، بل أنت **خبير مونتاج وموشن جرافيك ومنشئ فيديوهات فيرال احترافي**. يُحظر تماماً الوقوع في الأخطاء الأربعة التالية تحت أي ظرف:

### 1. القانون الأول: التزامن الدلالي الكامل واستخدام كافة أصول الاستوريبورد من الـ JSON (`100% Asset Coverage & JSON-Driven Sync`)
* **فهم العناصر من الـ JSON بدون قراءة الصور الخام:**
  يعتمد المودل في التخطيط والإخراج على أوصاف العناصر وأدوارها السردية في ملفات الـ JSON (`inputs/storyboard_catalog/*.json` أو `semantic_manifest.json` أو `assets/metadata.json` أو أمر `python pipeline_cli.py studio shorts --action inspect --project <name>`) مع قراءة ملف التوقيت `timing/section_XX_timing_master.json` جملة بجملة، دون فتح صور الاستوريبورد أو الصور المفرغة قبل الرندر.
* **فحص ألواح الجودة بعد الرندر فقط (`Post-Render Visual QA`):**
  لا يفتح الوكيل الصور إلا **بعد انتهاء الرندر** لمعاينة `qa/creative_contact_sheet.png` و`qa/mobile_preview.png` (أو `qa_contact_sheet.png`) والتحقق من جودة الإخراج أو تشخيص أي خطأ بصري طارئ.
* **استيعاب جميع العناصر الـ 20 في القصة (للفيديو الطويل 16:9):**
  * لوحة القصة المكونة من 20 مشهداً صُممت بحيث تغطي كل تفصيلة في السكربت (بمعدل عنصر جديد كل `3.0` إلى `3.5` ثانية).
  * **يُحظر تماماً** استخدام 8 أو 10 عناصر فقط وإهمال بقية العناصر!
  * يُقسم السيكشن (البالغ ~65 ثانية) إلى **10 مشاهد (`scene_01` إلى `scene_10`)** أو **5 مشاهد مزدوجة النبضات (`Phase A` + `Phase B`)** بحيث يظهر في كل نبضة عنصران متكاملان (يمين ويسار) في **اللحظة الدقيقة بالثانية التي ينطق فيها الراوي الحدث الخاص بكل عنصر**.

### 2. القانون الثاني: حظر الكروت ذات الكلمة الواحدة — عناوين فيرال من 3 إلى 5 كلمات (`Multi-Word Viral Headline Cards`)
* **خطأ محظور قطعياً:** يُمنع منعاً باتاً كتابة كلمة واحدة مفردة في الكارت النصي (مثل `"الدر:"` أو `"المماليك"` أو `"قطز"` بمفردها)! الكلمة الواحدة تفقد المعنى وتبدو كخطأ برمجي.
* **القاعدة الإخراجية المعتمدة:**
  * كل كارت نصي (`words`) يجب أن يكون **عنواناً فرعياً مكثفاً وجذاباً من 3 إلى 5 كلمات (15 إلى 35 حرفاً)** يلخص الفكرة الدرامية أو الرقم التاريخي المنطوق في تلك اللحظة!
  * **أمثلة صحيحة واحترافية:**
    * ✅ `"أخطر كذبة بيضاء في التاريخ"` (بدلاً من ❌ `"كذبة"`)
    * ✅ `"حملة لويس التاسع على دمياط 1249"` (بدلاً من ❌ `"دمياط"`)
    * ✅ `"وفاة السلطان في عز المعركة!"` (بدلاً من ❌ `"السلطان"`)
    * ✅ `"أوامر عسكرية باسم سلطان ميت"` (بدلاً من ❌ `"أوامر"`)
    * ✅ `"نهاية درامية فوق سور القلعة"` (بدلاً من ❌ `"القلعة"`)
  * يُوضع في كل مشهد (مدته 6–8 ثوانٍ) **كارتان نصيان متعاقبان** في أعلى الشاشة (`Y = 220`): الكارت الأول مع النبضة الأولى في اليمين (`[1340, 220]`)، والكارت الثاني مع النبضة الثانية في اليسار (`[580, 220]`).

### 3. القانون الثالث: المؤثرات الصوتية التفاعلية المدمجة (`100% Synchronized Studio SFX + Zero-BGM`)
* **لا يوجد موشن جرافيك فيرال بدون صوت حركة (Motion SFX)!**
* بينما تُحظر الموسيقى التصويرية الخلفية (`Strict Zero-BGM Policy`)، فإن **مؤثرات الحركة الصوتية (`SFX`) إلزامية بنسبة 100%** في كل ثانية من الفيديو:
  * يقوم محرك [core_engine/sfx_director.py](file:///e:/image_to_animate/core_engine/sfx_director.py) بقراءة `manifest.json` وتوليد ملف `section_XX_master_sfx.wav` الذي يمزج صوت الراوي النقي مع مؤثرات استوديوية متزامنة بالمللي ثانية:
    1. **`whoosh` (هواء خاطف):** مع كل دخول منزلق أو سريع (`whip_motion`, `slide_in`, `zoom_in`, `speed_blur`, `mask_wipe`) ومع انطلاق النقطة المشعة للكارت النصي.
    2. **`pop` (انبثاق ناعم):** مع كل دخول مرن (`pop_bounce`, `elastic_overshoot`, `rotation_spin`) ومع هزة الانتباه (`wiggle`) وعند الانكماش للخروج (`shrink_out`).
    3. **`thud` (ارتطام درامي عميق):** مع كل سقوط بالجاذبية (`squash_drop`)، ومع كل نبضة تضخيم (`scale_punches`)، ومع ومضات الخطر (`border_flash`, `tint_flash`).
    4. **`card_snap` (طقطقة بطاقة تكتيكية):** في لحظة تفتح البطاقة النصية (`start + 0.26s`) ومع دخول `card_stack`.
    5. **`glint` (رنين بريق كريستالي):** مع كل مسح ضوئي (`light_sweep`) وموجات رادار (`radio_waves`).
* عند تشغيل `pipeline_cli.py enhance`، يحتفظ المحرك بملف `section_XX_master_sfx.wav` كاملاً داخل `section_XX_master_v7.mp4` لضمان بقاء كافة مؤثرات الـ SFX واضحة ومسموعة.

### 4. القانون الرابع: التوازن الاحترافي في الموشن جرافيك — قاعدة التأثير المميز الواحد (`Professional Editorial Restraint — One Signature Effect per Element`)
* **لا تفراط ولا إفراط:** يُحظر أن يدخل العنصر إلى الشاشة ثم يتجمد كصورة صامتة، كما **يُحظر تماماً تكديس 3 أو 4 تأثيرات فوق عنصر واحد** (مثل وضع `neon_glow` + `lightning` + `radio_waves` + `white_strobe` معاً على نفس الرسمة) لأن ذلك يسبب إزعاجاً وتشتيتاً بصرياً للمشاهد!
* يفكر خبير المونتاج المحترف بمنطق **"التركيز البصري الموجه" (`Guided Eye Focus`)**، بحيث يمتلك كل عنصر في `manifest.json` دورة حياة متزنة وأنيقة من 3 مراحل:
  1. **دخول فيزيائي واحد يناسب كتلة العنصر (`1 Contextual Entrance`):**
     * الأجسام الثقيلة/الحاسمة (توابيت، مراسيم، قلوب، مشانق) ⬅️ `"squash_drop"` أو `"card_stack"`.
     * الفرسان والشخصيات المندفعة ⬅️ `"whip_motion"` أو `"slide_in"`.
     * الشارات الملكية والرموز ⬅️ `"pop_bounce"` أو `"elastic_overshoot"` أو `"rotation_spin"`.
     * المشاهد السرية/الليلية ⬅️ `"mask_wipe"` أو `"zoom_in"`.
  2. **حركة وسطية واحدة نظيفة ومرتبطة بالكلمة المنطوقة (`1 Signature Mid-Hold Effect + 1 Scale Punch`):**
     * **نبضة تأكيد صوتي واحدة (`1 scale_punch`، أو بحد أقصى 2 للعنصر الطويل):** تتزامن بدقة مع الكلمة المفتاحية في صوت الراوي.
     * **تأثير بصري مميز واحد فقط (`Max 1 Effect in "effects"` لكل عنصر):** يُختار حسب معنى اللقطة:
       * **الملوك والذهب والتيجان والسيوف والمراسيم:** `{"type": "light_sweep", "time": X, "intensity": 18.0, "width": 22, "color": "gold"}` (لمعة ذهبية ناعمة تمر مرة واحدة فقط).
       * **الخوف، الارتجاف، التردد، الصدمة البشرية، أو الجنون:** `{"type": "wiggle", "time": X, "duration": 0.42}` (هزة تعبيرية خفيفة).
       * **القتل، الذبح، السم، أو نزع القلب:** `{"type": "tint_flash", "time": X, "color": "crimson", "duration": 0.20}` (ومضة قرمزية خاطفة لـ 0.2 ثانية فقط دون تشويه الرسمة).
     * **وميض حواف الكاميرا (`camera_effects: border_flash`):** يُستخدم **مرتين فقط في السيكشن بالكامل** (مرة في الـ Hook الافتتاحي، ومرة في ذروة الصدمة الكبرى `"وهنا كانت الصدمة"`).
     * **الـ GIF التجميلي (`overlays`):** بحد أقصى **1 إلى 2 GIF فقط في السيكشن** وفي مساحة فارغة تماماً (`[960, 310]`) عند عدم وجود عنصر وسطي تحتها.
  3. **خروج سلس ومفرغ للوحة (`1 Clean Exit`):** يخرج العنصر بـ `"shrink_out"` أو `"slide_out"` فور انتهاء فكرته ليفسح المسرح للمشهد التالي.

---

### الثوابت الهندسية الصارمة لإحداثيات الشاشة (`1920x1080` Master Coordinate Constants)

| الطبقة / الفئة البصرية | الإحداثي الرأسي الثابت ($Y$) | الإحداثي الأفقي الموصى به ($X$) | قاعدة الارتكاز والقيود الصارمة |
| :--- | :--- | :--- | :--- |
| **الكروت النصية (`words` - 3..5 كلمات)** | **`Y = 220`** (أعلى الشاشة دائماً) | `X = 1340` (يمين) أو `X = 580` (يسار) | **توازن الأوزان المضادة:** يوضع الكارت في الجهة المعاكسة للعنصر البصري الرئيسي، أو يتبادل اليمين واليسار. **يُحظر وضع الكروت عند `Y = 780`**. |
| **مؤثرات الـ GIF التجميلية (`overlays`)** | **`Y = 310 - 360`** (الفضاء العلوي الحر) | `X = 960` أو `X = 1340` | مقاس أيقوني (`160-200px`)، من 2 إلى 3 مؤثرات للسيكشن، بعيداً عن الوجوه والنصوص. |
| **الشارات الدائرية واللفائف والرموز العلوية** | **`Y = 420 - 500`** | `X = 560` أو `960` أو `1380` | دوائر المستويات، لفائف التواريخ، التيجان الطافية، علامات الاستفهام (`grounded: false`). |
| **المشاهد المؤطرة والبيئات الوسطية (`Mid`)** | **`Y = 520 - 560`** | `X = 560` أو `1380` | المشاهد الدائرية/البيضاوية، الخيام، الأسوار، السفن (`grounded: false`). |
| **الشخصيات والكائنات الحية والمعدات الأرضية** | **`Y = 840`** (خط الأرض الإلزامي) | `X = 560` (يسار) أو `960` (وسط) أو `1380` (يمين) | **تأريض كعب الحذاء (`grounded: true`):** تستقر قواعد الشخصيات والفرسان والتوابيت على خط المسرح `Y = 840` دون غوص أو طفو. |

---

## 1. الأعمدة الأربعة لمنظومة CraftApp في خط الإنتاج

| التطبيق / المحرك | دوره المتخصص في البايبلاين | الملف التنفيذي المعتمد |
|---|---|---|
| **EffectCraft** | محرك الرندر بالـ GPU، التايم لاين، الكاميرا الزاحفة، نبضات `scale_punches`، وتوليد بطاقات الموشن (`Cairo-Bold`) | [core_engine/effectcraft_director.py](file:///e:/image_to_animate/core_engine/effectcraft_director.py) |
| **PhotoCraft** | خوارزمية التفريغ اللوني الدقيقة (`Color-to-Alpha Unmixing`) والتطهير من الهالات البيضاء (`Fringe Decontamination`) | [core_engine/photocraft_extractor.py](file:///e:/image_to_animate/core_engine/photocraft_extractor.py) |
| **VectorCraft** | تتبع الحدود الكنتورية العضوية وترتيب الصفوف الأفقي الدقيق (`Row-Clustered Contours`) وتوليد `contact_sheet.png` | [core_engine/universal_craft_extractor.py](file:///e:/image_to_animate/core_engine/universal_craft_extractor.py) |
| **FilmCraft & SFXDirector** | هندسة المؤثرات الصوتية التفاعلية المزامنة للحركة (`pop`, `whoosh`, `thud`, `card_snap`, `glint`) + تركيب الـ GIFs (`Zero-BGM`) | [core_engine/sfx_director.py](file:///e:/image_to_animate/core_engine/sfx_director.py) و [core_engine/media_compositor.py](file:///e:/image_to_animate/core_engine/media_compositor.py) |

---

## 2. الهيكل التنظيمي وإدارة المشاريع المعزولة (Multi-Project Architecture)

```text
e:\image_to_animate\
├── 📄 .active_project                                   # يحفظ اسم المشروع المفعل حالياً
├── 📄 pipeline_cli.py                                   # الأوركستريتور الموحد للمشاريع والعمليات
├── 📁 core_engine/                                      # محركات الرندر والاستخراج والـ SFX والتدقيق
├── 📁 assets/gifs/                                      # مستودع الـ 26 مؤثر GIF مفرغ
├── 📁 assets/sfx/                                       # المؤثرات الصوتية الاستوديوية (pop, whoosh, thud, card_snap, glint)
│
└── 📁 projects/<project_name>/                          # مساحة المشروع المعزولة كلياً
    ├── 📄 project.json                                  # إعدادات المشروع وعدد السكاشن
    ├── 📁 inputs/
    │   ├── 📁 script/
    │   │   ├── master_script.txt                        # النص الكامل الموحد لجميع السكاشن
    │   │   └── 📁 sections/                             # نصوص السكاشن منفصلة (section_01.txt ...)
    │   └── 📁 storyboards/                              # صور لوحات القصة (section_01.png ...)
    ├── 📁 sections/
    │   └── 📁 section_XX/
    │       ├── 📁 voice/                                # الصوت الخام (section_XX.wav) + الممزوج بالـ SFX (section_XX_master_sfx.wav)
    │       ├── 📁 timing/                               # التوقيت الدقيق (section_XX_timing_master.json, word_by_word.srt)
    │       ├── 📁 assets/                               # الأصول الـ 20 + contact_sheet.png + connectivity_and_separation_map.png
    │       └── manifest.json                            # كوريغرافيا الإخراج الشاملة لجميع الـ 20 أصلاً
    └── 📁 exports/
        ├── section_XX_master_v6.mp4                     # الرندر الأساسي من محرك EffectCraft (مع SFX)
        ├── section_XX_master_v7.mp4                     # الماستر المحسّن (مع الـ GIFs + الصوت الممزوج بالـ SFX بدون موسيقى)
        └── <project_name>_full_movie_master.mp4         # الفيلم الوثائقي الكامل المدمج
```

---

## 3. البروتوكول الصارم للعمليات — نظام اللوب الإنتاجي المستقل (Autonomous Production Loop)

> [!CAUTION]
> **دستور التخطيط الدلالي عبر الـ JSON بدون قراءة الصور قبل الرندر (`JSON-First Semantic Choreography`):**
> يجب على الوكيل في كل سيكشن:
> 1. تشغيل المراحل الميكانيكية عبر `pipeline_cli.py` (`voice` ⬅️ `timing` ⬅️ `extract` ⬅️ `semantic-map`).
> 2. **عدم فتح صور الـ Storyboard أو صور العناصر المفرغة أثناء التخطيط:** بدلاً من ذلك، يقرأ الوكيل كتالوج العناصر بصيغة JSON (`inputs/storyboard_catalog/*.json` أو `semantic_manifest.json` أو `assets/metadata.json` أو عبر `python pipeline_cli.py studio shorts --action inspect --project <name>`) مع توقيت الجمل في `timing/section_XX_timing_master.json`.
> 3. **تأليف الكوريغرافيا الإبداعية (`scene_graph.v2.json` أو `manifest.json` أو `shorts_specs.json`)** بحيث يربط كل عنصر بالثانية الدقيقة التي يُذكر فيها في الصوت، مع عناوين تحريرية مكثفة من 3–5 كلمات، ورسوم متجهية إجرائية، ومؤثرات متزنة.
> 4. **فتح الصور بعد الرندر فقط (`Post-Render QA Gate`):** معاينة `qa/creative_contact_sheet.png` و`qa/mobile_preview.png` بعد انتهاء الرندر للتأكد من جودة الإخراج أو تشخيص أي خطأ بصري.

### الخطوات التنفيذية لكل سيكشن (`section_01` إلى `section_N`):

1. **توليد الصوت (`Voice`):**
   ```bash
   python pipeline_cli.py voice --section <XX> --project <project_name>
   ```
2. **محاذاة التوقيت والتحقق من عدم البتر (`Timing`):**
   ```bash
   python pipeline_cli.py timing --section <XX> --project <project_name>
   ```
3. **الاستخراج الكنتوري وتوليد البيانات (`Extract`):**
   ```bash
   python pipeline_cli.py extract --section <XX> --project <project_name>
   ```
   * يولد تلقائياً 20 أصلاً مرتباً بصفوف أفقية متسلسلة (`entity_01` .. `entity_20`) + `metadata.json`.
4. **قراءة سياق الـ JSON وبناء الكوريغرافيا (`JSON Semantic Choreography`):**
   * يستعرض الوكيل التوقيت والعناصر عبر `studio shorts --action inspect` أو قراءة `section_XX_timing_master.json` وملفات الـ JSON للعناصر البصرية، ويصمم المشاهد دون قراءة الصور الخام.
5. **الرندر بالـ GPU مع مزج المؤثرات الصوتية (`Studio Compile / Render`):**
   ```bash
   python pipeline_cli.py studio compile --project <project_name> --section <XX> --run-id <run_id> --force
   ```
6. **دمج الماستر النهائي (`Studio Merge`):**
   ```bash
   python pipeline_cli.py studio merge --project <project_name> --run-id <run_id>
   ```
7. **بوابة الفحص البصري بعد الرندر (`Post-Render Visual QA Gate`):**
   * فتح `qa/creative_contact_sheet.png` بـ `read_file` بعد الرندر فقط للتأكد من التزامن الدلالي، وجمال الكروت متعددة الكلمات، وعدم وجود أي تداخل نصي.

---

## 4. الهندسة المكانية، التأريض، وهندسة الـ Viral Hook (Spatial Grid, Grounding & Viral Hook)

### 1. بروتوكول خطاف الثواني الخمس الأولى (`The 0–5s Viral Hook`)
* في المشهد الأول (`0.0s -> 6.5s`)، يدخل العنصر الأول (شارة المستوى/اللقب) في الثانية `0.10s` بحركة `"pop_bounce"` مع لمعة ذهبية `"light_sweep"`، ويدخل العنصر الثاني (الشخصية البطلة) في الثانية `1.50s` بحركة خاطفة `"whip_motion"` مؤرضاً عند `[1380, 840]` مع نبضة `"scale_punches"` وإطار `"border_flash"` عند ذكر اللقب الصادم، مع كارت نصي قوي من 4 كلمات في أعلى اليسار (`[580, 220]`).

### 2. هندسة استيعاب الـ 20 عنصراً عبر النبضات القصصية (`20-Asset Phased Beat Architecture`)
بما أن كل لوحة استوريبورد تحتوي على **20 رسماً متسلسلاً** ومدة السيكشن حوالي **60 إلى 70 ثانية**:
* يُقسم السيكشن إلى **10 مشاهد متعاقبة (`scene_01` إلى `scene_10`)**، مدة كل مشهد حوالي `6.0` إلى `7.0` ثوانٍ (أو 5 مشاهد يحتوي كل منها على نبضتين `Phase A` و`Phase B`).
* في كل مشهد (`6.5s`):
  * **العنصر الأيسر (`X = 560`):** يدخل عند بداية الجملة الأولى (`st_1`) ويخرج عند نهاية المشهد (`sc_end`).
  * **العنصر الأيمن (`X = 1380`):** يدخل عند بداية الجملة المكملة (`st_2 ≈ st_1 + 2.2s`) ويخرج عند نهاية المشهد (`sc_end`).
  * **الكارت النصي الأول (`[1340, 220]`):** يظهر مع العنصر الأيسر من `st_1 + 0.3s` إلى `st_2 + 0.2s` (عبارة من 3–5 كلمات).
  * **الكارت النصي الثاني (`[580, 220]`):** يظهر مع العنصر الأيمن من `st_2 + 0.3s` إلى `sc_end - 0.25s` (عبارة من 3–5 كلمات).
* بهذه الهندسة القياسية:
  1. تظهر **جميع الـ 20 رسمة** في توقيتها المنطوق بالضبط (2 رسمة × 10 مشاهد = 20 رسمة كاملة!).
  2. يظهر **20 كارتاً نصياً غنياً** (عناوين من 3–5 كلمات) متزامنة مع كل فكرة دون أي تداخل بصري!
  3. لا يبقى أي عنصر جامداً على الشاشة لأكثر من 3–4 ثوانٍ، وخلال بقائه ينبض بـ `scale_punches` و`light_sweep` / `tint_flash` / `wiggle` مع مؤثرات صوتية متزامنة!

---

## 5. كوريغرافيا المقارنات الاحترافية وخط التقسيم المتحرك (Comparison Motion Graphics)

عند مقارنة طرفين في مشهد واحد:
* الطرف الأول في اليسار (`[540, 840]` للأرضي أو `[540, 520]` للوسطي) وكارته النصي فوقه (`[580, 220]`).
* الطرف الثاني في اليمين (`[1380, 840]` للأرضي أو `[1380, 520]` للوسطي) وكارته النصي فوقه (`[1340, 220]`).

---

## 6. محرك الرندر المعتمد وهندسة المؤثرات الصوتية (EffectCraft GPU & SFX Synchronizer)

1. **المزج الصوتي التفاعلي الآلي (`SFXDirector`):**
   عند تشغيل `render` أو `enhance`، يقوم [core_engine/sfx_director.py](file:///e:/image_to_animate/core_engine/sfx_director.py) بمسح جميع المشاهد والعناصر والكروت في `manifest.json` وتركيب المؤثرات الصوتية (`whoosh`, `pop`, `thud`, `card_snap`, `glint`) في ملف `voice/section_XX_master_sfx.wav`.
2. **الرندر العتادي السريع (`EffectCraftMotionEngine`):**
   يقوم [core_engine/effectcraft_director.py](file:///e:/image_to_animate/core_engine/effectcraft_director.py) بتوليد keyframes متسلسلة زمنياً (`Entrance` ⬅️ `Mid-Hold Scale Punches & Camera Push-in & VFX` ⬅️ `Exit`) ورندر الفيديو بدقة `1080p / 30fps`.

---

## 7. كتالوج التأثيرات البصرية والقالب القياسي لـ `manifest.json` (VFX Suite & Master JSON Schema)

### أولاً: جدول الحركات والمؤثرات والـ SFX المرافقة لها تلقائياً

| المفتاح في العنصر | القيم المدعومة | الأثر البصري في الفيديو | المؤثر الصوتي المزامن تلقائياً (SFX) |
| :--- | :--- | :--- | :--- |
| **`"entrance"`** | `"whip_motion"`, `"slide_in"`, `"speed_blur"`, `"mask_wipe"` | انزلاق/كشف خاطف مع تمويه سرعة اتجاهي | `whoosh.wav` (صوت اندفاع هوائي) |
| **`"entrance"`** | `"pop_bounce"`, `"elastic_overshoot"`, `"rotation_spin"` | انبثاق مرن مع ارتداد فيزيائي ناعم | `pop.wav` (صوت انبثاق استوديوي) |
| **`"entrance"`** | `"squash_drop"` | سقوط بالجاذبية من الأعلى مع انضغاط أرضي | `whoosh.wav` + `thud.wav` (ارتطام) |
| **`"entrance"`** | `"card_stack"` | صعود بميلان زاوي كبطاقة توضع على المسرح | `card_snap.wav` (طقطقة تكتيكية) |
| **`"entrance"`** | `"zoom_in"` | تقريب تدريجي من عمق الكادر | `whoosh.wav` + `pop.wav` |
| **`"scale_punches"`** | `[{"time": 12.40}]` | نبضة تضخيم (`1.18x`) وهزة صدمية أثناء البقاء | `thud.wav` + `pop.wav` |
| **`"effects"`** | `{"type": "light_sweep", "time": X, "intensity": 20, "color": "gold"}` | بريق ضوئي مائل يمسح العنصر | `glint.wav` (رنين كريستالي) |
| **`"effects"`** | `{"type": "tint_flash", "time": X, "color": "crimson"}` | وميض لوني درامي خاطف (`0.22s`) | `thud.wav` (نبضة صدمة) |
| **`"effects"`** | `{"type": "wiggle", "time": X, "duration": 0.45}` | هزة زاوية للفت الانتباه أو تجسيد الغضب/الخوف | `pop.wav` |
| **`"effects"`** | `{"type": "radio_waves", "time": X, "color": "cyan"}` | حلقات صدمية متوسعة حول العنصر | `glint.wav` |
| **`"camera_effects"`** | `{"type": "border_flash", "time": X, "color": "red", "pulses": 2}` | وميض تحذيري يحيط بحواف الشاشة 16:9 | `thud.wav` |
| **`"words"`** | `{"word": "عبارة من 3 إلى 5 كلمات", "start": st, "end": en, "pos": [1340, 220]}` | انطلاق النقطة المشعة + تفتح الكارت + كتابة RTL | `whoosh.wav` + `card_snap.wav` |

---

### ثانياً: القالب القياسي الإلزامي لـ `manifest.json` (Master Reference Schema)

```json
{
  "section_id": "section_01",
  "project": "mamluk_sultans",
  "title": "المستوى 1: شجر الدر — الخدعة السرية 1250",
  "total_duration": 66.50,
  "fps": 30,
  "resolution": [1920, 1080],
  "theme": {
    "name": "eye_comfort_paper",
    "background_color": "#EDE8E0"
  },
  "enable_sfx": true,
  "overlays": [
    {
      "gif": "question_mark_pulse.gif",
      "start": 16.50,
      "end": 21.00,
      "pos": [960, 320],
      "scale_w": 170
    },
    {
      "gif": "danger_hazard.gif",
      "start": 54.00,
      "end": 59.50,
      "pos": [960, 320],
      "scale_w": 170
    }
  ],
  "scenes": [
    {
      "id": "scene_01_viral_hook",
      "start": 0.0,
      "end": 7.80,
      "description": "الافتتاحية الفيرال: شارة المستوى الأول وبورتريه السلطانة شجر الدر",
      "camera": {
        "zoom_start": 1.0,
        "zoom_end": 1.08,
        "duration": 7.80
      },
      "camera_effects": [
        {
          "type": "border_flash",
          "time": 3.40,
          "color": "red",
          "opacity": 42.0,
          "pulses": 2
        }
      ],
      "elements": [
        {
          "asset_key": "entity_01_composite",
          "start": 0.10,
          "end": 7.60,
          "pos": [540, 480],
          "grounded": false,
          "target_size": 440,
          "entrance": "pop_bounce",
          "exit": "shrink_out",
          "scale_punches": [
            { "time": 1.80 }
          ],
          "effects": [
            { "type": "light_sweep", "time": 2.60, "intensity": 22.0, "width": 24, "color": "gold" }
          ]
        },
        {
          "asset_key": "entity_02_composite",
          "start": 3.20,
          "end": 7.60,
          "pos": [1380, 840],
          "grounded": true,
          "target_size": 560,
          "entrance": "whip_motion",
          "exit": "shrink_out",
          "scale_punches": [
            { "time": 5.20 }
          ],
          "effects": [
            { "type": "light_sweep", "time": 6.00, "intensity": 22.0, "width": 24, "color": "gold" }
          ]
        }
      ],
      "words": [
        {
          "word": "أقوى سلاطين المماليك ونهاياتهم الصادمة",
          "theme": "amber",
          "start": 1.20,
          "end": 4.20,
          "pos": [1340, 220]
        },
        {
          "word": "شجر الدر: أخطر كذبة بيضاء!",
          "theme": "crimson",
          "start": 4.50,
          "end": 7.55,
          "pos": [580, 220]
        }
      ]
    }
  ]
}
```

---

## 8. نظام التايبوجرافي الفيرال متعدد الكلمات (Style 1 Viral Headline Card Lifecycle)

1. **طول العبارة الإلزامي:** من **3 إلى 5 كلمات (15 إلى 35 حرفاً)** تلخص الحدث أو الرقم التاريخي. يُحظر وضع كلمة مفردة.
2. **التوقيت الصوتي الدقيق:** يبدأ الكارت (`start`) في نفس لحظة نطق أول كلمة من العبارة في `timing_master.json`، ويستمر لـ `2.5s - 3.6s` لتمكين القراءة المريحة.
3. **الموضع العلوي المتوازن (`Y = 220`):** يتناوب الكارت بين يمين الشاشة (`[1340, 220]`) ويسار الشاشة (`[580, 220]`) في الجهة المعاكسة للعنصر البصري النشط.

---

## 9. مؤثرات الـ GIF التجميلية وقانون الحظر التام للموسيقى التصويرية (Micro-Retention GIFs & Zero-BGM Policy)

* **حظر الموسيقى التصويرية (`Zero-BGM`) مع الإبقاء الكامل على مؤثرات الـ SFX (`100% Motion SFX`):**
  يُمنع خلط أي موسيقى خلفية، ولكن يجب دمج مسار `section_XX_master_sfx.wav` (الذي يحتوي على صوت الراوي النقي + مؤثرات `pop`, `whoosh`, `thud`, `card_snap`, `glint`) في الفيديو النهائي `section_XX_master_v7.mp4`.
* **قفل مدة الفيديو (`-t exact_audio_dur` و`eof_action=pass`):**
  للقضاء على أي فريم متجمد بعد انتهاء الصوت.

---

## 10. دمج الفيلم الوثائقي الكامل (Full Documentary Master Merge)

```bash
python pipeline_cli.py merge --project <project_name>
```
يدمج جميع ملفات `section_*_master_v7.mp4` داخل `projects/<project_name>/exports/<project_name>_full_movie_master.mp4`.

---

## 11. قائمة الفحص الإلزامية قبل التسليم (Pre-Flight QA Checklist)

- [ ] **1. استيعاب الـ 20 عنصراً بالتزامن الدلالي من الـ JSON:** تم توزيع جميع عناصر الاستوريبورد (20/20) على التوقيت الفعلي المنطوق في `timing_master.json` بالاعتماد على أوصاف الـ JSON دون قراءة الصور الخام قبل الرندر.
- [ ] **2. عناوين الكروت النصية (3–5 كلمات):** لا يوجد أي كارت بكلمة واحدة؛ جميع الكروت عبارات قوية ومكثفة من 3 إلى 5 كلمات مع ثنائية خطوط متناسقة (`Typography Director`).
- [ ] **3. المؤثرات الصوتية التفاعلية (`Synchronized SFX`):** تم تضمين المؤثرات الصوتية المتزامنة مع كل حركة دون موسيقى خلفية (`Zero-BGM`).
- [ ] **4. الحياة الحركية والرسوم الإجرائية:** كل مشهد يوظف رسوماً متجهية هادفة (`spotlight_cone`, `bezier_connector`, `concentric_rings`, `chart_bar` مع `direction: "rtl"`) وزوم كاميرا مستمر.
- [ ] **5. الفحص البصري بعد الرندر (`Post-Render Contact Sheet QA`):** تمت معاينة `creative_contact_sheet.png` و`mobile_preview.png` بعد الرندر للتأكد من خلو الفيديو من أي فريم فارغ أو تداخل نصي.

---

## 12. منظومة إخراج الشورتس الفيرال المستقلة (`AION Shorts Director V6 — 9:16 Vertical Studio`)

لإنتاج سلسلة YouTube Shorts عمودية (`1080x1920`) من أي مشروع طويل دون إعادة قراءة صور الـ Storyboard ودون إعادة توليد الفويس أوفر:

1. **فحص بيانات التوقيت والعناصر JSON بأمر واحد (`0` قراءة صور):**
   ```bash
   python pipeline_cli.py studio shorts --action inspect --project <isolated_project>
   ```
   * يستخرج جميع الجمل بتوقيتاتها الدقيقة (`start`, `end`) وكتالوج الـ 20 عنصراً لكل سيكشن في `shorts/creative_context_digest.json`.
2. **التصميم الإبداعي للمودل عبر `shorts/shorts_specs.json`:**
   * يختار المودل أقوى القصص المستقلة، ويحدد نقطة القطع النظيفة عند بداية الجملة الفعالة (`"trim_source_window": [start_sec, null]`) لإعادة استخدام الصوت الماستر المعتمد مباشرة من الثانية `0.00`.
   * يتم إلحاق الـ CTA الصوتي الموحد للقناة تلقائياً من [`assets/audio/cta/cta_channel_ar_fenrir.wav`](file:///e:/image_to_animate/assets/audio/cta/cta_channel_ar_fenrir.wav) (`"اعمل لايك، واشترك في القناة، وكمل الفيديو كامل من الفيديو المرتبط تحت اسم القناة!"`) مع حركة أيقونات اللايك والاشتراك وسهم الفيديو المرتبط.
   * يحدد المودل لكل شورت هوية لونية وتايبوجرافية مميزة (`Cairo`/`Alyamama`, `Cairo`/`Readex Pro`, `IBM Plex Sans Arabic`/`Amiri`, `Alexandria`/`Changa`) وتخطيطات عمودية آمنة للهاتف (`radar_focus`, `diagonal_duet`, `vertical_causal_chain`, `vertical_split_compare`, `chart_clash_bars`, `triangle_climax`).
3. **التجميع والرندر والفحص بأمر واحد:**
   ```bash
   python pipeline_cli.py studio shorts --action compile --project <isolated_project> --all --run-id shorts_v6_master --force
   ```
4. **معاينة ألواح الجودة بعد الرندر فقط:**
   * يتم فحص `exports/runs/<run_id>/shorts/short_XX/qa/creative_contact_sheet.png` بعد الإنتاج للتأكد من جودة الإخراج النهائي قبل التسليم.

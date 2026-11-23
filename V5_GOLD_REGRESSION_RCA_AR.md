# تقرير تحليل السبب الجذري لتراجع الجودة الإخراجية في V5 (`Root Cause Analysis`)

> **النطاق:** تتبع مسار البيانات الكامل في AION V5 عبر السلسلة:
> `Creative Plan -> Scene Graph V2 -> ECGC Compiler -> EffectCraft Project (.ecproj) -> Render (MP4)`
> ومقارنته بالمسار المرجعي الذهبي `projects/mind_glitches_ar` (`effectcraft_adapter.py` + `director/section_XX/scene_graph.json`).

---

## ملخص تنفيذي

الخلل في مخرجات V5 (`cache/mind_glitches_ar_v5/exports/runs/v5_ar_grounded/`) ليس ضعفاً في محرك EffectCraft نفسه (فمحرك EffectCraft يُظهر 19 قدرة `VERIFIED` و1 `PARTIAL`، وتقارير QA الفردية سجّلت `PASS`)، بل يرجع إلى **8 أعطال هيكلية محددة** في طبقة التوجيه الإبداعي (`semantic_storyboard_director.py`, `creative_director.py`, `studio_cli.py`) وطبقة الترجمة (`ecgc_compiler.py`) وطبقة العقد (`contracts.py`)، أدّت إلى تحويل الإخراج السردي المتدرج إلى قالب مسطح متكرر على مستوى الـ beat.

---

## تتبع الثغرات الثماني بالأدلة والأمثلة الفعلية

### 1. ضياع المشاهد المستقلة (`Independent Scenes`)
- **المصدر الفعلي:**
  - `core/aion/creative_director.py:255` داخل `AICreativeDirector.direct_scene()`:
    ```python
    "scenes": [{"scene_id": f"{section_id}_main", "time": {"start": 0.0, "end": round(dur, 3)}, "assets": []}]
    ```
    يتجاهل المخرج التوزيع المشهدي بالكامل ويضع مشهداً وحيداً صوريّاً فارغ الأصول (`assets: []`)، ثم يُسقط كل العناصر والرسومات في قوائم مسطحة عامة على مستوى القسم.
  - `core/aion/studio_cli.py:138-144` داخل `_collect_brief_from_project()`: يمرر `timing_master["sentences"]` الخام مباشرةً كـ `beats` دون تجميع سردي أو قراءة `narrative_beats.json`.
  - `core/aion/semantic_storyboard_director.py:438-492`: دالة `_merge_short_beats(beats, min_dur=2.0)` تدمج الجمل الأقصر من ثانيتين فقط.
- **مثال واقعي:**
  - في `section_07`، أنتج Whisper 10 جمل قصيرة (بعضها 2.01 ث–2.6 ث)، فبنَى V5 عشرة مقاطع متلاحقة متوترة (10 ألوان/أيقونات)، مقابل **5 مشاهد سردية متماسكة** في الجولد (`sc_01_intro`, `sc_02_bank_robbery`, `sc_03_police_description`, `sc_04_schooler_1990_trial`, `sc_05_memory_erased`).
  - في `section_03` (`scene_graph.v2.json:255` مقابل `projects/mind_glitches_ar/director/section_03/scene_graph.json:146-449`)، يمتلك الجولد 6 مشاهد بأصول مجمعة داخل كل مشهد، بينما يمتلك V5 `scene_id: "section_03_main"` و`assets: []`.

---

### 2. ضياع تجميع العناصر داخل المشاهد وتأطيرها (`Asset Grouping, Staging & Framing`)
- **المصدر الفعلي:**
  - `core/aion/creative_director.py:564-572, 646-668`: دالة `_grounded_slots(count)` تحجز مسبقاً مواقع أفقية ثابتة حسب العدد الإجمالي (`count=2 -> [31%, 69%]`، `count=3 -> [22%, 50%, 78%]`) منذ لحظة دخول أول عنصر.
  - `core/aion/semantic_storyboard_director.py:674` (مع `creative_director.py:674`): يضيف `exhibit_card` فقط إذا كان `role in ("research_context", "data_callout")`، متجاهلاً فحص الحواف السفلية المقصوصة (`_detect_cropped_bottom` الموجود في `core/aion/director_stages.py:15-26`) لأصول الشخصيات (`human_example`).
  - `core/aion/ecgc_compiler.py:300-360` (`VectorGeometryBuilder`): يحدد سقف التحجيم بـ `min(135.0, ...)` (سطر 310)، ويتجاهل `grounded` (نقطة الارتكاز السفلية)، ويرسم `GroundShadow` و`Stage_GroundDeck` كطبقات **2D** (أسطر 262-291, 633-652) تحت أصول **3D**، مما يسبب انزلاق الظل عن العنصر أثناء حركة الكاميرا.
  - بنية `asset_references` تفتقر إلى فصل `asset_id` المصدري عن `instance_id` المشهدي لإعادة الاستخدام دون تكرار التعريفات.
- **مثال واقعي:**
  - في `section_01` عند `t = 7.80s` (`sec_0.png` أسفل اليسار): ظهر `b1_w0_entity_06` وحيداً وصغيراً في أقصى اليسار (`x = 422.4`) و75% من الشاشة فارغة بانتظار دخول `entity_11` (`7.98s`) و`entity_12` (`8.40s`)، وبقي مقصوص الصدر بلا `exhibit_card` (عكس الجولد الذي يضعه داخل بطاقة `dark_crimson` في المنتصف `[960, 620]` بارتفاع `450px`).
  - في `section_03` (`sec_2.png`): يضع الجولد العنصر الأول في المنتصف ثم يزيحه بالـ keyframes عند دخول المرافق (`960 -> 600` كما في `section_02/05/06/07/08`)، بينما يرميه V5 مباشرةً إلى الجانب.

---

### 3. ضياع العناوين التحريرية وتشوه الكابشن (`Editorial Headlines vs Broken Captions`)
- **المصدر الفعلي:**
  - `core/aion/creative_director.py:516-525, 777-788`: دالة `_concise_headline(b["text"], max_words=6)` تقتطع **أول 6 كلمات حرفياً من السرد الصوتي** وتضعها في أسفل الشاشة (`position=(w*0.5, h*0.875)` = `y=945`) كبديل مشوه للـ subtitle.
  - `core/aion/ecgc_compiler.py:813-820` (`TypographyCompiler`): يفرض `layer.addTextAnimator` مع `opacity=0`, `position=[0, 28, 0]` و`rangeSelector/start` من `0` إلى `100` خلال `0.35..0.85s` على كل نص، بينما تتوسع خلفية البطاقة (`TextCard`, سطر 794) بالكامل خلال `0.25s`.
  - `core/aion/ecgc_compiler.py:526-579` (`badge_card`): يطبّق `Track Matte` متحركاً على المستطيل فقط دون النص، مع تقسيم العرض إلى 380px جانب الشاشة.
- **أمثال واقعية من الإطارات المرصودة:**
  - **انقطاع الجمل:** `"في سنة 1930"` (`sec_01 b3_hl`)، `"أما الخَلَل الثالث فتقدر تجرّبه على"` (`sec_03 b0_hl`)، `"المنطق يقول إن هذا يثبّت الصورة"` (`sec_07 b5_hl`)، `"وعشان ما تحس إنك تنعمي كل"` (`cmp_250.png`). مقابل عناوين الجولد المركزة أعلى الشاشة `[960, 130]`: `"١٩٣٠ — تجربة ميتزغر"`، `"ثالث خلل: وَهْم بِيْنُوكْيُو"`، `"العكس هو اللي يصير تماماً!"`.
  - **شبحية النص (`Ghosting`):** في `cmp_20.png` (`sec_01, t=20.0s`): الكتلة `"في سنة 1930"` بدأت عند `19.37s` بمدة كشف `0.85s`؛ عند `20.0s` ظهرت `"في سنة"` وبقيت `"1930"` في منتصف الـ RangeSelector شبحاً رمادياً باهتاً منزاحاً `+28px` للأسفل!
  - **بطاقات فارغة جزئياً:** في `sec_0.png` (`t=7.80s`) ظهرت كلمة `"بعد"` وحدها داخل صندوق فارغ طويل؛ وفي `sec_6.png` (`t=8.00s`) ظهرت `"تخيل إنك"` وحدها في الأسفل مع `badge_card` مقتطع من اليسار `"تخيل إنك كنت شاهد"` بسبب نصف حركة الـ Track Matte.

---

### 4. ضياع منحنيات الحركة ومعدل الإطارات (`Motion Curves & FPS Drift`)
- **المصدر الفعلي:**
  - `core/aion/creative_director.py:38`: القيمة الافتراضية `fps: int = 24`، ولم يقرأ `studio_cli._collect_brief_from_project()` قيمة `fps` من `project.json` (حيث `fps = 30` في `mind_glitches_ar` وفي `cmd_init`).
  - `core/aion/creative_director.py:694-701`: يفرض حركة آلية موحدة `drift_x = ±14.0px` خلال `2.4s` على كل أصل بلا علاقة بالدور السردي أو الأهمية.
  - `core/aion/ecgc_compiler.py:350-355`: يفرض نفس منحنى `pop_settle` (`scale 0.4 -> 1.07 -> 1.0`) على **100% من الأصول**، متجاهلاً `entrance` (`slide_right`, `slide_down`, `soft_fade`, `pop_settle`) و`entrance_dur` و`keyframes`!
- **مثال واقعي:**
  - الجولد (`section_01..08`) يوزع الدخول دلالياً: `pop_settle` (~45%)، `slide_right` لاتجاه القراءة RTL (~33%)، `soft_fade` للتحولات الهادئة/المرعبة (~15%)، `slide_down` لمصدر الضوء/التاريخ (1/قسم)، مع keyframes انتقائية (تضخم `1.0->1.15` للشاشة الفارغة، إزاحة `960->600` عند قدوم المرافق). بينما V5 يحرك كل عنصر بالوصفة نفسها وبسلاسة أقل (`24 fps`).

---

### 5. ضياع رسومات العلاقات والإفراط في الأيقونات الزخرفية (`Relationship Graphics & Medallion Spam`)
- **المصدر الفعلي:**
  - `core/aion/creative_director.py:616-626`: يولد `icon_medallion` (دائرة بيضاء `112px` + GIF في `[1784, 108]`) في **كل beat** بغض النظر عن الحاجة أو ملاءمة الـ GIF (بعضها من إطارين مثل `question_mark_pulse.gif` أو أبيض على أبيض فيبدو فارغاً كما في `sec_6.png`).
  - `core/aion/creative_director.py:720-775`: يفرض الرسومات حسب **عدد العناصر** لا حسب **المعنى**:
    - موجة من عنصرين ← سهم `bezier_arrow` آلياً حتى دون علاقة سببية.
    - موجة من 3 عناصر ← `concentric_rings` آلياً فوق رأس العنصر الأول (يغطي وجه الشخص في `sec_4.png` أسفل اليسار).
    - موجة من عنصر واحد ← إما `concentric_rings` أو `badge_card` مكرر للنص المبتور.
  - `core/aion/motion_grammar.py` يُعرّف معالجات غنية (`network_signal_diagram`, `chronological_spine`, `dual_polarity_columns`, `animated_infographic_chart`) لكن `_build_multi_beat_section()` في `creative_director.py` لا يستدعي أياً منها!
- **مثال واقعي:**
  - في `section_03` (`scene_graph.v2.json`), رسم V5 أسهم `bezier_arrow` بين `"رأس بينوكيو"` و`"شارة خريطة الجسم"` (`sec_2.png`) بلا علاقة تحويل، بينما في الجولد (`section_03`) اقتصر السهمان (`Nerve_Collision_Link_L/R`) على مشهد `sc_04_nerve_paradox` لشرح تضارب الإشارات العصبية فقط!

---

### 6. ضياع استمرارية الكاميرا والخلفية (`Camera & Background Continuity`)
- **المصدر الفعلي:**
  - `core/aion/creative_director.py:605-611`: الكاميرا تدور دورة ثابتة `b_idx % 3` (`cx-38`, `cx+32`, `cx`) مع تثبيت `poi=[cx, cy, 0.0]` دوماً بلا reset واضح عند القطع السردي وبلا متابعة للبطل.
  - `core/aion/creative_director.py:589-602` + `semantic_storyboard_director.py:317-337`: ينتقل `bg_timeline` في كل beat مع 15 نقطة زمنية (أغلبها تكرار لنفس اللون). وبسبب وضع نقطة التثبيت عند `st - 0.12` والانتقال إلى `st + 0.35` بين ألوان متضادة (`#EFEAE1` -> `#421019`)، تظهر اللحظات الأولى من المشاهد بلون رمادي طيني باهت (`sec_0.png` أسفل اليسار، `t=7.80s`).

---

### 7. فقدان التحكم بالمؤثرات الصوتية (`SFX Flooding & Missing Ducking`)
- **المصدر الفعلي (عطلان متراكبان):**
  1. `core/aion/creative_director.py:627-628, 713-717`: يضيف `beat_sfx` + `"pop"` (بعد `0.10s`) لكل beat، إضافة إلى SFX لكل أصل `j >= 1` و`"whoosh"` لكل موجة، فينتج **28–30 SFX في القسم الواحد** (مقابل 5–16 في الجولد).
  2. `core/aion/ecgc_compiler.py:921-944` (`AudioCueCompiler`): يحوّل cues V2 إلى `SFXDirector.create_synchronized_audio()` في `core_engine/sfx_director.py:194-262`. هذا المحرك القديم يفترض أن كل عنصر يملك `entrance="pop_bounce"` فيحقن **صوتي `"pop"` إضافيين (`st+0.05` و`et-0.28`) على كل cue**، ويجمع الصوتين دون RMS voice-ducking، ويتجاهل `pan` و`max_duration`، ولا يرى مكتبة `creative_v3/studio_pro_sfx_and_audio_stems_v3/` رغم وجود المحرك المعتمد `core/aion/motion_and_audio.mix_scene_graph_audio()` في نفس الحزمة!
- **النتيجة:** في `section_03` (`28` cue) يتحول الخلط فعلياً إلى ~84 ضربة صوتية متداخلة مع الراوي بلا ducking.

---

### 8. ضياع وظيفة المؤثرات البصرية (`VFX Inflation & Bad Timing`)
- **المصدر الفعلي:**
  - `core/aion/semantic_storyboard_director.py:401-435`: يفعّل `"drop_shadow": True` على **100% من الأصول** (حتى فوق البطاقات التي تملك ظلاً مسبقاً) ويحقن `blur` / `distortion` / `mask_reveal` / `Light Sweep` بتطابق نصوص جزئي، فينتج **24–32 VFX/قسم** (مقابل **1–6 VFX/قسم** في الجولد).
  - `core/aion/ecgc_compiler.py:879-890` (`VFXCompiler`): عند تطبيق `Light Sweep` يبدأ المسح من `st` مباشرةً (أثناء تكبير الدخول) بدلاً من لحظة التأكيد بعد الثبات، ويتجاهل معاملات `duration` و`width` و`color` في مواصفة المؤثر.

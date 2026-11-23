# دليل خط الإنتاج الكامل — Whiteboard Motion Graphics Pipeline

يوثق هذا الملف الخطوات العملية والتقنية المعتمدة لإنتاج مقاطع الموشن جرافيك الاحترافية بنمط السبورة البيضاء (Whiteboard Animation) فائقة الجودة (1080p) من النص وحتى الفيديو النهائي، مع بيان **ما تم إنجازه** و**كيف تم تنفيذه تقنياً**.

---

## 🏗️ نظرة عامة على معمارية خط الإنتاج (Pipeline Architecture)

```
[1. النص الأصلي] ➡️ [2. توليد الصوت البشري (Gemini TTS)] ➡️ [3. المحاذاة الصوتية الدقيقة (Faster-Whisper)]
                                                                          ⬇️
[6. الفيديو النهائي (1080p)] ⬅️ [5. محرك الإخراج الحركي (V6 Engine)] ⬅️ [4. استخراج وتجهيز العناصر البصرية]
```

---

## المرحلة 1: إعداد النص وتقسيم المقاطع (Script Ingestion & Sectioning)

### ما تم تنفيذه:
- استلام النص الكامل للفيلم الوثائقي في ملف [transcript_to_speech.txt](file:///e:/image_to_animate/project_content/transcript_to_speech.txt).
- تقسيم النص إلى مقاطع موضوعية مستقلة:
  - **Section 01:** أوركيد المطرقة (النباتات المخادعة) — 136 كلمة.
  - **Section 02:** أوركيد الدلو (غرفة التعذيب) — 126 كلمة.
  - **Sections 03-09:** باقي أقسام الوثائقي (دبور التين، زهرة الجثة، التين الخانق، شجرة الديناميت، إلخ).

### كيف تم تنفيذه:
- استخدام خوارزميات ريجكس منتظمة في السكربتات لعزل كل مقطع بنصه وتشكيله الكامل:
  ```python
  pattern = r"SECTION 02[^\n]*\n+(.*?)(?=\n+SECTION 03|\Z)"
  ```

---

## المرحلة 2: هندسة وتوليد الصوت بالذكاء الاصطناعي (AI Voiceover Generation)

### ما تم تنفيذه:
- إنتاج التعليق الصوتي البشري عالي الحماسة للمقطعين 1 و 2 بلهجة سعودية يوتيوبية متقنة.
  - ملف صوت سيكشن 1: [section_01.wav](file:///e:/image_to_animate/project_content/audio/section_01.wav) (المدة: 56.28 ثانية).
  - ملف صوت سيكشن 2: [section_02.wav](file:///e:/image_to_animate/project_content/audio/section_02.wav) (المدة: 43.76 ثانية).

### كيف تم تنفيذه تقنياً:
1. **المحرك المستخدم:** [VoiceStudioEngine](file:///e:/image_to_animate/voice_studio/engine.py) المرتبط بـ Google GenAI API (`gemini-3.1-flash-tts-preview`).
2. **المعايير الصوتية المعتمدة:**
   - **الصوت:** `Fenrir`
   - **بروفايل الأداء:** `SAUDI_YOUTH_CREATOR` (طاقة يوتيوبية شابة وسريعة).
   - **ملاحظة المخرج:** `HIGH_ENERGY_YOUTUBE`.
   - **المعاملات الصوتية:** `temperature=0.8`, `speed=1.0`, جودة RIFF/WAVE نقية بمعدل أخذ عينات `24,000 Hz`.
3. **سكربتات التنفيذ:**
   - سيكشن 1: [generate_section_01_audio.py](file:///e:/image_to_animate/scripts/generate_section_01_audio.py)
   - سيكشن 2: [generate_section_02_audio.py](file:///e:/image_to_animate/scripts/generate_section_02_audio.py)

---

## المرحلة 3: التوقيت والمحاذاة الصوتية الدقيقة (Deterministic Acoustic Timing & Alignment)

### ما تم تنفيذه:
- استخراج الطوابع الزمنية الدقيقة لكل كلمة منطوقة بأجزاء الألف من الثانية دون أي اعتماد على التخمين.
- إنتاج 4 أنواع من ملفات التوقيت لكل مقطع:
  1. **ملف الكلمات المفردة (`word_by_word.srt`):** توقيت بداية ونهاية كل كلمة.
  2. **ملف ومضات الموشن جرافيك (`motion_graphics.srt`):** عبارات إيقاعية قصيرة (2-4 كلمات) لظهور بطاقات الشاشة.
  3. **ملف الجمل الكاملة (`sentences.srt` / `standard_sentences.srt`):** جمل نحوية متكاملة.
  4. **ملف الماستر الشامل (`timing_master.json` و `motion_graphics_data.json`):** كائن JSON متكامل يربط الكلمات بالجمل والمدد الزمنية.

### كيف تم تنفيذه تقنياً:
1. **التعرف الصوتي (Acoustic Transcription):**
   - استخدام محرك [FasterWhisperEngine](file:///e:/image_to_animate/section_timing/transcription/faster_whisper_engine.py) محلياً مع خيار `word_timestamps=True` و `vad_filter=True` لعزل الصمت بدقة.
2. **المحاذاة مع النص القانوني الأصلي (Canonical Script Alignment):**
   - استخدام خوارزمية [ScriptAudioAligner](file:///e:/image_to_animate/section_timing/alignment/script_audio_aligner.py) و [TokenAligner](file:///e:/image_to_animate/section_timing/alignment/token_aligner.py) لمقارنة الكلمات الصوتية بالنص الأصلي عبر `SequenceMatcher`.
   - الهدف: الحفاظ على تشكيل النص الصحيح (Diacritics)، تصحيح أي كلمة سمعها النموذج الصوتي بطريقة عامية، وضمان عدم ضياع الترقيم أو علامات التعجب.
3. **سكربتات التنفيذ:**
   - سيكشن 1: [generate_motion_graphics_srt.py](file:///e:/image_to_animate/tools/generate_motion_graphics_srt.py)
   - سيكشن 2: [generate_section_02_timing.py](file:///e:/image_to_animate/scripts/generate_section_02_timing.py)

---

## المرحلة 4: استخراج وتجهيز العناصر البصرية (Visual Asset Extraction)

### ما تم تنفيذه:
- تقطيع لوحات القصة (Storyboard Panels) إلى عناصر منفردة معزولة الخلفية (Transparent PNGs).
- في سيكشن 1: تم استخراج أكثر من 20 عنصراً في مجلد [extracted_assets/section_01](file:///e:/image_to_animate/project_content/extracted_assets/section_01/):
  - تعابير الراوي (مفكر، مصدوم، متفاجئ).
  - الزهور اللطيفة والنحلة الساذجة.
  - النباتات المفترسة (فينوس، دروسيرا، القراب).
  - النبتة قاذفة البذور وانفجارها.
  - خريطة أستراليا وزهرة أوركيد المطرقة والدبور المخدوع.

### كيف تم تنفيذه تقنياً:
- استخدام تقنيات معالجة الصور الرقمية والقص الذكي وعزل قنوات الشفافية (Alpha Masking) بدقة أطراف فائقة النعومة.

---

## المرحلة 5: محرك الإخراج البصري للموشن جرافيك V6 (Master Staged Motion Director)

### ما تم تنفيذه:
- تطوير المحرك الإخراجي الشامل في [master_staged_motion_director.py](file:///e:/image_to_animate/production_engine/master_staged_motion_director.py) وتطبيق القواعد الذهبية:

1. **الخلفية النقية (Pure Whiteboard Canvas):**
   - خلفية بيضاء استوديو ثابتة تماماً `#FFFFFF` بدون تدرجات داكنة تشوه النقاء.
   - إلغاء شريط الترجمة السفلي لإتاحة مساحة الرؤية الكاملة للحركة.

2. **التبديل المكاني التبادلي (Left ↔ Right Staged Alternation):**
   - توزيع المشاهد على نمط إيقاعي يتبادل فيه تموضع العناصر والنصوص:
     - مشهد 1: الراوي في **اليمين** — النص في **اليسار**.
     - مشهد 2: الزهور والنحلة في **اليسار** — النص في **اليمين**.
     - مشهد 3: الراوي في **اليمين** — النص في **أعلى الوسط** (بانر علوي).
     - مشهد 4: النبات المفترس في **اليسار** — بطاقة الخطف في **اليمين**.
     - وهكذا مع تنويع الزوايا (أعلى اليسار، أسفل اليسار) لكسر أي رتابة بصرية.

3. **التزامن الصوتي الصارم (Audio-Triggered Typography):**
   - ظهور الكلمات المفتاحية **بعد أو أثناء نطق الصوت لها مباشرة** بالاعتماد على ملف `word_by_word.srt`، وليس قبل الصوت أبداً.

4. **تنويع حركات النصوص (Multiple Typography Animations):**
   - **الكتابة الحية من اليمين لليسار (`write_rtl`):** ماسك تدريجي يظهر الحروف كأنها تُكتب بقلم فوري متوهج (Neon Nib Cursor) مع الحفاظ على اتصال الحروف العربية.
   - **الصدمة العنيفة (`slam_bounce`):** هبوط سريع مع ارتداد في لحظات الذروة والمفاجأة مثل "طاخ!".
   - **الظهور المرن (`pop_bounce`):** تمدد وتقلص إيقاعي سلس.
   - **الانزلاق (`slide_down` / `slide_right`):** دخول سلس من أطراف الشاشة.

5. **فيزياء الظلال الانتقائية (Selective Elevation Physics):**
   - **العناصر المتجذرة والمثبتة** (الزهور، النباتات، الخريطة، الراوي): تلتصق باللوحة بظل تلامس ناعم وخفيف (`offset=(1,3), blur=4, opacity=0.10`).
   - **العناصر الطائرة والمتحركة** (النحل الطائر، الدبابير، القذائف): تكتسب ظلاً هوائياً عميقاً ثلاثي الأبعاد يُبرز ارتفاعها عن سطح اللوحة (`offset=(10,22), blur=24, opacity=0.38`).

---

## المرحلة 6: الرندر النهائي والدمج الصوتي (Rendering & Composition)

### ما تم تنفيذه:
- تجميع كافة طبقات المشهد (الخلفية + العناصر المستقرة + بطاقات ونصوص الموشن جرافيك + المؤشرات) بمعدل 30 إطار/ثانية بدقة Full HD (1920x1080).
- دمج المسار الصوتي الرسمي المتزامن بالكامل مع الفيديو في حاوية MP4 باستخدام FFmpeg مع كوديك H.264 عالي التوافق.

### الملفات الناتجة:
- فيديو سيكشن 1 النهائي: [section1_master_staged_motion_v6.mp4](file:///e:/image_to_animate/output_animations/master_section1_production/section1_master_staged_motion_v6.mp4)
- سكربت تشغيل الرندر: [run_master_production_section1.py](file:///e:/image_to_animate/run_master_production_section1.py)

---

## 📋 مصفوفة ملخص الخطوات والحالة الراهنة

| الخطوة | المكون / المرحلة | الحالة | المخرجات الرئيسية |
| :---: | :--- | :---: | :--- |
| **01** | تقسيم النص واستخراج النصوص | **مكتمل ✅** | [transcript_to_speech.txt](file:///e:/image_to_animate/project_content/transcript_to_speech.txt) |
| **02** | هندسة وتوليد الصوت (Section 01) | **مكتمل ✅** | [section_01.wav](file:///e:/image_to_animate/project_content/audio/section_01.wav) (56.28s) |
| **03** | هندسة وتوليد الصوت (Section 02) | **مكتمل ✅** | [section_02.wav](file:///e:/image_to_animate/project_content/audio/section_02.wav) (43.76s) |
| **04** | التوقيت الصوتي والمحاذاة (Section 01) | **مكتمل ✅** | [section_01_word_by_word.srt](file:///e:/image_to_animate/project_content/srt/section_01/section_01_word_by_word.srt) |
| **05** | التوقيت الصوتي والمحاذاة (Section 02) | **مكتمل ✅** | [section_02_word_by_word.srt](file:///e:/image_to_animate/project_content/srt/section_02/section_02_word_by_word.srt) |
| **06** | استخراج عناصر سيكشن 1 | **مكتمل ✅** | مجلد [extracted_assets/section_01](file:///e:/image_to_animate/project_content/extracted_assets/section_01/) |
| **07** | محرك إخراج V6 وإنتاج سيكشن 1 | **مكتمل ✅** | [section1_master_staged_motion_v6.mp4](file:///e:/image_to_animate/output_animations/master_section1_production/section1_master_staged_motion_v6.mp4) |
| **08** | تجهيز عناصر سيكشن 2 واستخراجها | **مكتمل ✅** | 33 عنصراً معزولاً بخلفية شفافة في [extracted_assets/section_02](file:///e:/image_to_animate/project_content/extracted_assets/section_02/) |
| **09** | إخراج ورندر فيديو سيكشن 2 (V6 Engine) | **مكتمل ✅** | [section2_master_staged_motion_v1.mp4](file:///e:/image_to_animate/output_animations/master_section2_production/section2_master_staged_motion_v1.mp4) (43.76s) |
| **10** | تجهيز سيكشن 3 (دبور التين ومقبرة التين) | **المرحلة التالية ⏳** | توليد الصوت، التوقيت، استخراج العناصر، والرندر |

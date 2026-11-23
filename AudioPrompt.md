# Section-Based Professional TTS Generator

أريد منك بناء **Python Production-Grade TTS Engine** مسؤول عن إنشاء الصوت الاحترافي لكل Video Section بشكل مستقل.

هذا النظام جزء من Pipeline أكبر لإنشاء فيديوهات Whiteboard / Explainer متزامنة مع الصوت.

---

# 1. الفكرة الأساسية

الـ Script الكامل للفيديو مقسم مسبقًا إلى Sections صغيرة.

مثال:

```text
project/
├── sections/
│   ├── 001/
│   │   └── script.txt
│   ├── 002/
│   │   └── script.txt
│   ├── 003/
│   │   └── script.txt
│   └── ...
```

كل Section يجب أن تتم معالجته بشكل مستقل.

إذا كان لدينا:

```text
Section 001
Section 002
Section 003
```

فإن النظام ينشئ:

```text
001/voice/section.wav
002/voice/section.wav
003/voice/section.wav
```

ولا يجب إعادة توليد Section آخر إذا تم تعديل Section واحد فقط.

---

# 2. الـ Section هو وحدة الإنتاج

يجب اعتبار:

```text
SECTION
```

هو Production Unit.

وليس:

```text
TTS Chunk
```

الـ Chunk مجرد وحدة تقنية داخلية تستخدم فقط عندما يكون النص طويلًا بالنسبة لطلب TTS.

مثال:

```text
SECTION 003
     │
     ├── Chunk 001 → Gemini TTS
     ├── Chunk 002 → Gemini TTS
     └── Chunk 003 → Gemini TTS
                 ↓
          Stitch / Validate
                 ↓
          section_003.wav
```

بالنسبة لبقية النظام:

```text
section_003.wav
```

هو الصوت الوحيد الذي يهمه.

---

# 3. الهدف النهائي

إذا أعطيت النظام:

```text
sections/003/script.txt
```

يجب أن ينتج:

```text
sections/003/
│
├── script.txt
│
└── voice/
    ├── chunks/
    │   ├── 000.wav
    │   ├── 001.wav
    │   └── ...
    │
    ├── section.wav
    └── metadata.json
```

---

# 4. Voice Identity

يجب أن يكون لدينا Voice Profile مركزي وثابت.

الصوت المطلوب:

```text
Male young adult narrator
Neutral / White Saudi Arabic
Fast-paced
Energetic
Highly engaging
Clear articulation
Confident
Intelligent
Modern YouTube documentary/explainer style
Natural Saudi pronunciation
Controlled excitement
Continuous forward momentum
```

استخدم Performance Profile مثل:

```text
VOICE PERFORMANCE PROFILE:

Young Saudi male narrator speaking in neutral, widely understandable Saudi Arabic.

Fast-paced, energetic and highly engaging YouTube documentary/explainer delivery.

Maintain high but controlled energy throughout the entire section.

Speak quickly while keeping every word clearly understandable.

Use natural pitch variation and subtle emphasis on important facts, discoveries, contrasts and surprising information.

Maintain a continuous forward-moving rhythm.

Use short natural pauses between ideas.

Use slightly longer pauses only when a major idea changes or emphasis is naturally required.

Avoid slow dramatic narration.

Avoid theatrical acting.

Avoid exaggerated emotions.

Avoid sleepy or relaxed delivery.

Do not rush pronunciation.

Do not sacrifice clarity for speed.

Maintain the same voice identity, dialect, energy, pacing philosophy and vocal character across every TTS chunk belonging to the same section.
```

اجعل هذا الـ profile configurable، ولا تكرره داخل كل module.

---

# 5. أهم مشكلة: عدة TTS Requests داخل Section واحد

قد يكون الـ Section مثلًا:

```text
120 كلمة
```

ولا يمكن أو لا يُفضّل إرساله في Request واحد.

يجب أن يقوم النظام تلقائيًا بعمل:

```text
Section Text
      ↓
Semantic Chunker
      ↓
Chunk 1
Chunk 2
Chunk 3
Chunk 4
```

لكن هذه الـ chunks يجب أن تبدو للمستمع كأنها **تسجيل واحد متصل**.

---

# 6. لا تستخدم تقسيمًا ثابتًا كل 25 كلمة

ممنوع تنفيذ:

```python
text.split_every_25_words()
```

بدلًا من ذلك أنشئ:

```python
SemanticChunker
```

ويأخذ في الاعتبار:

* نهاية الجملة.
* علامات الترقيم.
* الفواصل.
* الوحدات الدلالية.
* الانتقال بين الأفكار.
* طول الطلب.
* الحد الآمن للنموذج.
* السياق بين الجمل.

الأولوية:

```text
Natural Sentence Boundary
        ↓
Semantic Boundary
        ↓
Natural Pause
        ↓
Maximum Safe Chunk Size
```

ولا تقطع الجملة في المنتصف إلا كحل أخير.

---

# 7. مثال

بدل:

```text
Chunk 1:
الكيوي أصله الحقيقي من
```

و:

```text
Chunk 2:
الصين وكان اسمه القديم...
```

استخدم:

```text
Chunk 1:
الكيوي أصله الحقيقي من الصين،

Chunk 2:
وكان اسمه القديم عنب الثعلب الصيني،
```

حتى لو أدى ذلك إلى اختلاف بسيط في عدد الكلمات.

---

# 8. Chunk Context

كل Chunk يجب أن يحصل على Context من:

```text
Previous Chunk
Current Chunk
Next Chunk
```

مثال:

```python
ChunkContext(
    previous_text,
    current_text,
    next_text
)
```

الغرض من الـ context هو المحافظة على:

* pacing
* energy
* pronunciation
* intonation
* sentence flow
* vocal continuity

لكن:

**ممنوع أن يضيف النموذج كلمات إلى النص.**

النص المنطوق يجب أن يكون مطابقًا للنص الأصلي.

---

# 9. Script Integrity

قبل التوليد احفظ:

```text
original_text
```

ثم بعد التوليد لا تسمح لأي مرحلة بإعادة كتابة الـ script.

ممنوع:

```text
paraphrasing
summarization
rewriting
adding words
removing words
changing facts
changing sentence order
```

تعليمات الأداء منفصلة عن النص.

---

# 10. Performance Planner

أنشئ:

```python
PerformancePlanner
```

يحلل Section ويحدد الأداء المطلوب لكل جزء.

مثال:

```text
HOOK
energy = high
pace = fast
curiosity = high

FACT
energy = high
pace = fast
clarity = very_high

SURPRISE
energy = high
emphasis = stronger
pause_before = short

TRANSITION
energy = high
pace = continuous
pause = short
```

لكن Performance Planner **لا يغير Voice Identity**.

الهدف:

```text
Stable Voice Identity
+
Dynamic Natural Performance
```

---

# 11. Gemini TTS Provider

أنشئ abstraction:

```python
class TTSProvider:
    def generate(
        self,
        text: str,
        voice_profile: VoiceProfile,
        performance: PerformanceCue
    ) -> AudioResult:
        ...
```

ثم:

```python
class GeminiTTSProvider(TTSProvider):
    ...
```

يجب ألا يكون باقي النظام مرتبطًا مباشرة بـ Gemini API.

---

# 12. Model Configuration

ضع الإعدادات في:

```text
.env
config.yaml
```

مثل:

```yaml
tts:
  provider: gemini
  model: ...
  voice: ...
  sample_rate: 24000
```

ولا تضع API key داخل الكود.

استخدم:

```text
GEMINI_API_KEY
```

من environment variables.

---

# 13. Consistency داخل Section

هذه نقطة أساسية.

بعد إنشاء كل Chunk، قم بتسجيل metadata:

```json
{
  "chunk_id": 2,
  "duration": 4.82,
  "estimated_wpm": 168,
  "energy": 0.87,
  "voice": "...",
  "model": "..."
}
```

ثم استخدم النتائج لمراقبة consistency.

مثال:

```text
Chunk 1 → 166 WPM
Chunk 2 → 169 WPM
Chunk 3 → 167 WPM
Chunk 4 → 168 WPM
```

جيد.

لكن:

```text
Chunk 1 → 168
Chunk 2 → 130
Chunk 3 → 171
```

يجب تسجيل:

```text
PACING_INCONSISTENCY
```

---

# 14. Audio Analysis لكل Chunk

أنشئ:

```python
AudioAnalyzer
```

ويحسب:

```text
duration
sample_rate
channels
RMS
peak
silence_ratio
speech_ratio
estimated_WPM
```

إذا أمكن، استخدم تحليلًا أكثر دقة للـ speech/pause بدل الاعتماد فقط على waveform amplitude.

---

# 15. إعادة توليد Chunk سيئ

إذا فشل Chunk في validation:

```text
Generate
   ↓
Analyze
   ↓
Validation
   ↓
FAIL
   ↓
Retry
```

ولا تعيد إنشاء الـ Section كله.

مثال:

```text
Section 004

Chunk 0 ✓
Chunk 1 ✓
Chunk 2 ✗
Chunk 3 ✓

→ regenerate Chunk 2 only
```

ثم أعد بناء:

```text
section_004.wav
```

---

# 16. Retry

أنشئ:

```python
RetryManager
```

مع:

```text
MAX_RETRIES = 3
```

ويدعم:

* timeout
* API failure
* empty response
* invalid audio
* corrupted audio
* transient errors
* exponential backoff

---

# 17. Audio Stitching

بعد نجاح جميع Chunks:

```text
Chunk 0
Chunk 1
Chunk 2
Chunk 3
       ↓
AudioStitcher
       ↓
section.wav
```

قبل الدمج:

* نفس sample rate
* نفس channels
* نفس format
* نفس bit depth

يجب الحفاظ على الوقفات الطبيعية.

لا تحذف pauses تلقائيًا.

لا تضف cinematic silence.

لا تستخدم crossfade كبير.

إذا احتجت micro-crossfade لمنع clicks:

```text
5–10 ms
```

ويكون configurable.

---

# 18. لا تستخدم atempo كحل أساسي

لا تفعل:

```text
Generate all audio
→ atempo=1.20
```

كحل افتراضي.

السرعة يجب أن تأتي أساسًا من TTS performance.

Post-processing يمكن استخدامه فقط لتصحيح فروق صغيرة.

مثال:

```yaml
post_processing:
  speed_adjustment:
    enabled: false
    min: 0.98
    max: 1.08
```

---

# 19. Loudness Consistency

كل Chunks داخل Section يجب أن تكون متقاربة في مستوى الصوت.

أنشئ:

```python
LoudnessNormalizer
```

ثم:

```text
Chunks
 ↓
Loudness Matching
 ↓
Stitching
 ↓
Final Section Audio
```

مع منع clipping.

---

# 20. Final Section Validation

بعد إنتاج:

```text
section.wav
```

قم بعمل validation كامل.

تحقق من:

```text
✓ file exists
✓ valid WAV
✓ duration > 0
✓ correct sample rate
✓ correct channels
✓ no clipping
✓ no missing chunks
✓ correct chunk order
✓ acceptable silence
✓ acceptable pacing
✓ acceptable loudness
✓ all chunks accounted for
```

---

# 21. Section Metadata

يجب أن ينتج النظام:

```text
section.wav
metadata.json
```

مثال:

```json
{
  "section_id": "003",
  "script_file": "script.txt",
  "text": "...",
  "model": "...",
  "voice": "...",
  "duration": 18.42,
  "sample_rate": 24000,
  "chunks": [
    {
      "id": 0,
      "text": "...",
      "file": "chunks/000.wav",
      "duration": 4.81,
      "estimated_wpm": 167,
      "global_start": 0.0,
      "global_end": 4.81
    },
    {
      "id": 1,
      "text": "...",
      "file": "chunks/001.wav",
      "duration": 5.02,
      "estimated_wpm": 169,
      "global_start": 4.81,
      "global_end": 9.83
    }
  ]
}
```

---

# 22. مهم جدًا: Metadata ليست مصدر التوقيت النهائي

الـ:

```text
global_start
global_end
```

الخاصة بالـ chunks هي metadata داخلية.

لا تستخدمها لاحقًا لتوقيت الرسم على مستوى الكلمات.

بعد اكتمال:

```text
section.wav
```

ستأتي مرحلة مستقلة:

```text
section.wav
      ↓
Speech Alignment
      ↓
Word Timestamps
      ↓
Sentence Timestamps
      ↓
Pause Detection
      ↓
Visual Beats
```

الصوت النهائي هو **Source of Truth** للتوقيت.

---

# 23. Section ID

يجب أن يكون لكل Section ID ثابت.

مثال:

```text
001
002
003
```

ويجب أن يحتوي metadata على:

```json
{
  "section_id": "003"
}
```

حتى يمكن للنظام الأكبر معرفة أن:

```text
003.wav
```

ينتمي إلى:

```text
Section 003
```

---

# 24. Cache System

هذه ميزة مهمة جدًا.

إذا لم يتغير:

```text
section text
voice profile
model
voice
generation settings
```

فلا تعيد توليد الصوت.

أنشئ hash:

```python
generation_hash = hash(
    section_text
    + voice_profile
    + model
    + voice
    + settings
)
```

إذا كان:

```text
old_hash == new_hash
```

استخدم الـ cached audio.

---

# 25. Incremental Regeneration

إذا تغير:

```text
Section 005
```

يجب إعادة إنشاء:

```text
005 فقط
```

ولا تلمس:

```text
001
002
003
004
006
007
...
```

وإذا تغير Chunk داخلي فقط:

```text
005 / Chunk 2
```

أعد توليد Chunk 2 فقط ثم أعد بناء Section 005.

---

# 26. CLI

أريد CLI بسيطًا:

```bash
python main.py \
    --section sections/003 \
    --output sections/003/voice
```

ويجب دعم:

```bash
--model
--voice
--debug
--force
--max-retries
```

مثال:

```bash
python main.py \
    --section sections/003 \
    --output sections/003/voice \
    --force
```

---

# 27. Project Architecture

استخدم:

```text
section_tts/
│
├── main.py
├── config.py
├── config.yaml
│
├── core/
│   ├── pipeline.py
│   ├── semantic_chunker.py
│   ├── performance_planner.py
│   ├── cache_manager.py
│   └── consistency_manager.py
│
├── providers/
│   ├── base.py
│   └── gemini.py
│
├── audio/
│   ├── analyzer.py
│   ├── stitcher.py
│   ├── normalizer.py
│   └── validator.py
│
├── models/
│   ├── section.py
│   ├── chunk.py
│   ├── voice.py
│   └── metadata.py
│
├── utils/
│   ├── retry.py
│   ├── hashing.py
│   └── logging.py
│
└── tests/
    ├── test_chunker.py
    ├── test_cache.py
    ├── test_stitcher.py
    ├── test_validator.py
    └── test_pipeline.py
```

---

# 28. Requirements

استخدم Python 3.11+.

يفضل:

```text
google-genai
numpy
soundfile
pydantic
ffmpeg
```

استخدم أقل عدد ممكن من dependencies.

لا تستخدم ML ثقيل إلا إذا كان ضروريًا.

---

# 29. Logging

أريد logs واضحة مثل:

```text
[SECTION] Loading section 003
[SCRIPT] 87 words
[CHUNKER] Created 3 chunks
[TTS] Generating chunk 1/3
[TTS] Chunk 1 completed: 4.82s
[TTS] Generating chunk 2/3
[TTS] Chunk 2 completed: 5.11s
[ANALYZER] Chunk 2 WPM: 168
[VALIDATOR] Chunk 2: PASS
[STITCH] Combining 3 chunks
[LOUDNESS] Normalizing
[VALIDATOR] Final section: PASS
[OUTPUT] section.wav
```

---

# 30. Debug Output

عند استخدام:

```bash
--debug
```

أنشئ:

```text
debug/
├── chunks.json
├── performance.json
├── metrics.json
├── validation.json
└── generation_report.json
```

---

# 31. Tests

يجب اختبار:

### Script

* نص قصير
* نص طويل
* نص عربي
* punctuation
* جمل طويلة
* Sections صغيرة

### Chunking

* عدم كسر الجمل بدون سبب
* semantic boundaries
* maximum chunk size
* minimum chunk size

### TTS

* successful generation
* API failure
* timeout
* retry
* empty audio

### Audio

* invalid WAV
* different sample rates
* clipping
* loudness mismatch
* missing chunk
* wrong order

### Cache

* unchanged section → no regeneration
* changed text → regeneration
* changed voice → regeneration
* changed model → regeneration
* changed settings → regeneration

---

# 32. قاعدة ذهبية

لا تحاول جعل كل TTS Chunk مثاليًا بشكل مستقل.

الهدف هو:

```text
Chunk 1
     +
Chunk 2
     +
Chunk 3
     ↓
ONE NATURAL SECTION
```

وليس:

```text
Perfect Chunk 1
Perfect Chunk 2
Perfect Chunk 3
```

إذا كان كل Chunk ممتازًا لكن الانتقال بينها واضح، فالنظام فشل.

---

# 33. النتيجة النهائية

النظام يجب أن يحول:

```text
sections/003/script.txt
```

إلى:

```text
sections/003/voice/
│
├── chunks/
│   ├── 000.wav
│   ├── 001.wav
│   └── 002.wav
│
├── section.wav
└── metadata.json
```

بحيث:

```text
section.wav
```

هو **الصوت النهائي الاحترافي للقسم**.

ثم يمكن لنظام آخر مستقل أن يأخذ:

```text
section.wav
```

ويقوم بتحليل:

```text
words
sentences
pauses
speech beats
visual beats
```

ثم يستخدم هذه البيانات لإنشاء الفيديو الخاص بنفس الـ Section.

---

# 34. ممنوع دمج مسؤولية الرسم داخل هذا المشروع

هذا المشروع مسؤول فقط عن:

```text
SCRIPT SECTION
      ↓
PROFESSIONAL VOICE
      ↓
section.wav
      ↓
metadata
```

لا تنشئ:

* storyboard
* image prompts
* animation assets
* visual beats
* drawing timeline
* video rendering

هذه ستكون مراحل منفصلة.

---

# المطلوب منك

قم الآن بإنشاء **الكود الكامل القابل للتشغيل** لهذا النظام.

لا تكتب pseudo-code.

لا تختصر الملفات.

اكتب architecture أولًا باختصار، ثم جميع الملفات والكلاسات المطلوبة، مع type hints وlogging وerror handling وtests.

صممه بحيث يمكن دمجه لاحقًا بسهولة مع نظام:

```text
Audio Alignment
→ Visual Beat Solver
→ Whiteboard Renderer
```

والأهم:

**Section هو وحدة الإنتاج، وTTS Chunk هو وحدة داخلية مؤقتة فقط.**

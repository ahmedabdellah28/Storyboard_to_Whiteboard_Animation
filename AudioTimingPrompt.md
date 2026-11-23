# Professional Audio-to-Visual Timing Engine

أريد منك بناء نظام Python احترافي مسؤول عن تحويل **Section Audio النهائي** إلى Timeline دقيق يمكن استخدامه لربط:

* الصوت
* الكلمات
* الجمل
* الوقفات
* العناصر البصرية
* مدة رسم العناصر
* المؤثرات الصوتية SFX
* Camera movements
* Visual Beats

هذا النظام هو **المركز الأساسي للمزامنة** في مشروع Whiteboard Animation.

لا يقوم النظام بإنشاء الصوت.

الصوت أصبح جاهزًا مسبقًا.

---

# 1. المدخلات

النظام يستقبل Section واحد:

```text
section/
├── script.txt
├── voice/
│   └── section.wav
└── assets/
    └── asset_plan.json
```

وقد يتوفر لاحقًا:

```text
assets/
└── asset_sheet.json
```

المدخلات الأساسية هي:

```text
1. section.wav
2. script.txt
3. asset_plan.json
```

---

# 2. المخرجات

يجب إنتاج:

```text
section/
└── timing/
    ├── whisper.json
    ├── words.json
    ├── sentences.json
    ├── pauses.json
    ├── speech_beats.json
    ├── semantic_beats.json
    ├── visual_beats.json
    ├── drawing_timeline.json
    ├── sfx_timeline.json
    ├── camera_timeline.json
    └── master_timeline.json
```

---

# 3. المبدأ الأساسي

يجب الفصل بين:

```text
WHEN SPEECH HAPPENS
```

و:

```text
WHEN VISUAL SHOULD APPEAR
```

الصوت يحدد الحقيقة الزمنية.

لكن الرسم يتم تحديده بواسطة Solver.

لذلك:

```text
Speech Timing ≠ Drawing Timing
```

---

# 4. Faster-Whisper

استخدم Faster-Whisper لاستخراج:

```text
segments
words
start
end
probability
```

ويجب استخدام:

```python
word_timestamps=True
```

إن كان متاحًا مع النموذج المستخدم.

يفضل دعم نماذج مثل:

```text
small
medium
large-v3
turbo
```

ويكون النموذج configurable.

---

# 5. Whisper Configuration

أنشئ:

```yaml
whisper:
  model: large-v3
  language: ar
  device: auto
  compute_type: auto
  word_timestamps: true
  vad_filter: true
```

لا تجعل الإعدادات hard-coded.

---

# 6. Raw Whisper Layer

احتفظ بنتيجة Whisper الخام بدون تعديل:

```text
timing/whisper.json
```

مثال:

```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 2.31,
      "text": "الكيوي أصله الحقيقي من الصين",
      "words": [
        {
          "word": "الكيوي",
          "start": 0.02,
          "end": 0.48,
          "probability": 0.98
        }
      ]
    }
  ]
}
```

ممنوع تعديل هذه البيانات.

هي:

```text
RAW AUDIO EVIDENCE
```

---

# 7. Arabic Normalization

أنشئ طبقة:

```python
ArabicTextNormalizer
```

تقوم بتطبيع النص لأغراض المطابقة فقط.

مثلاً التعامل مع:

* التشكيل
* اختلافات الهمزات
* المسافات
* علامات الترقيم
* Unicode normalization
* التطويل
* اختلافات بسيطة في الكتابة

لكن:

**لا تغير النص الأصلي.**

احتفظ دائمًا بـ:

```text
original_text
normalized_text
```

---

# 8. Script ↔ Whisper Alignment

هذه من أهم مراحل المشروع.

نملك:

```text
Original Script
```

و:

```text
Whisper Transcript
```

يجب إنشاء:

```python
ScriptAudioAligner
```

يقوم بربط النص الأصلي بالتوقيت الصوتي.

مثال:

```json
{
  "text": "أصله الحقيقي من الصين",
  "script_start": 1,
  "script_end": 5,
  "audio_start": 0.52,
  "audio_end": 2.10,
  "words": [...]
}
```

لا تعتمد على:

```python
substring search
```

فقط.

استخدم token alignment مناسبًا للعربية.

---

# 9. Word Timeline

أنشئ:

```text
words.json
```

مثال:

```json
{
  "words": [
    {
      "id": "w001",
      "text": "الكيوي",
      "start": 0.02,
      "end": 0.48
    },
    {
      "id": "w002",
      "text": "أصله",
      "start": 0.52,
      "end": 0.83
    }
  ]
}
```

كل كلمة يجب أن تحتوي على:

```text
id
text
start
end
duration
sentence_id
semantic_span_id
```

---

# 10. Sentence Timeline

لا تعتمد على Whisper segments باعتبارها الجمل النهائية.

أنشئ:

```python
SentenceSegmenter
```

يعتمد على:

* النص الأصلي
* punctuation
* semantic boundaries
* Whisper timestamps

والناتج:

```json
{
  "sentence_id": "s001",
  "text": "الكيوي أصله الحقيقي من الصين",
  "start": 0.02,
  "end": 2.10,
  "duration": 2.08
}
```

---

# 11. Pause Detection

أنشئ:

```python
PauseDetector
```

يحلل:

```text
word gaps
+
audio energy
+
VAD
```

لا تعتمد على silence threshold واحد فقط.

صنف الوقفات:

```text
micro_pause
short_pause
medium_pause
long_pause
```

مثلاً:

```json
{
  "start": 2.10,
  "end": 2.42,
  "duration": 0.32,
  "type": "short_pause"
}
```

---

# 12. لا تعتبر كل Pause فراغًا

الـ Pause مورد زمني يمكن استخدامه للرسم.

مثلاً:

```text
Speech
───────

Pause
      ─────

Speech
             ─────────
```

يمكن أن يبدأ رسم عنصر جديد أثناء الـ Pause.

لكن لا يجب استغلال كل pause.

يجب الحفاظ على الإيقاع الطبيعي.

---

# 13. Speech Beat Layer

أنشئ:

```python
SpeechBeatDetector
```

يحول الصوت إلى:

```text
Speech Beats
```

مثلاً:

```text
0.00 → Hook
1.20 → Main Fact
2.10 → Pause
2.42 → New Idea
4.80 → Important Fact
```

كل Speech Beat يحتوي:

```text
start
end
type
importance
sentence_id
```

---

# 14. Semantic Beat Layer

هذه طبقة مستقلة عن Whisper.

إذا كانت الجملة:

> الكيوي أصله الحقيقي من الصين.

فالـ semantic beat هو:

```text
SUBJECT = Kiwi
RELATION = originated_in
OBJECT = China
```

إذا كانت:

> وكان يستخدم كغذاء وحتى كدواء.

تصبح:

```text
SUBJECT = Kiwi
ACTION = used_as
OBJECTS = Food + Medicine
```

هذه المعلومات تأتي من:

```text
asset_plan.json
```

أو Visual Planning Layer.

---

# 15. Asset Plan

افترض أن لدينا:

```json
{
  "assets": [
    {
      "id": "A01",
      "name": "Kiwi",
      "role": "subject"
    },
    {
      "id": "A02",
      "name": "China",
      "role": "location"
    }
  ]
}
```

لا تقم بتخمين Assets جديدة.

الـ Timing Engine يجب أن يعمل فقط مع Assets الموجودة في Asset Plan.

---

# 16. Visual Beat Mapper

أنشئ:

```python
VisualBeatMapper
```

وظيفته:

```text
Semantic Beat
       +
Speech Timing
       +
Asset Plan
       ↓
Visual Beat
```

مثال:

```json
{
  "visual_beat_id": "VB001",
  "asset_id": "A01",
  "semantic_role": "subject",
  "speech_anchor": {
    "text": "الكيوي",
    "start": 0.02,
    "end": 0.48
  }
}
```

---

# 17. لا تبدأ الرسم دائمًا عند بداية الكلمة

هذه قاعدة أساسية.

إذا كانت:

```text
speech_start = 1.55
speech_end = 2.10
```

و:

```text
drawing_duration = 0.90
```

فلا يمكن رسم العنصر كاملًا داخل نافذة الكلام.

لذلك يجب أن يستطيع Solver بدء الرسم قبل الـ speech anchor:

```text
drawing_start = 1.20
drawing_end = 2.10
```

بحيث يصل العنصر إلى اكتماله عند اللحظة المناسبة.

---

# 18. DrawingDemand

أنشئ:

```python
DrawingDemand
```

ولا تستخدم مدة ثابتة مثل:

```text
every asset = 1 second
```

بل احسب:

```text
stroke_length
point_count
geometric_complexity
number_of_strokes
pen_velocity
```

مثلاً:

```json
{
  "asset_id": "A01",
  "drawing_demand": 0.72
}
```

---

# 19. Drawing Duration Estimator

أنشئ:

```python
DrawingDurationEstimator
```

يحول:

```text
DrawingDemand
```

إلى:

```text
estimated_drawing_duration
```

مثال:

```text
Simple Arrow → 0.35s
Circle       → 0.45s
Kiwi         → 1.20s
Complex Map  → 2.10s
```

لكن هذه ليست durations ثابتة.

هي estimates مبنية على geometry.

---

# 20. Beat Solver

هذه أهم طبقة.

أنشئ:

```python
BeatSolver
```

مدخلاته:

```text
Speech Timeline
Pause Timeline
Semantic Beats
Assets
DrawingDemand
Drawing Duration
```

ويخرج:

```text
Actual Drawing Timeline
```

---

# 21. Solver Objective

الـ Solver يجب أن يحاول:

1. جعل العنصر يظهر متزامنًا مع المعنى.
2. إنهاء الرسم قرب نهاية الـ semantic event.
3. استغلال الوقفات.
4. تجنب ازدحام الرسم.
5. عدم تجاوز Speech Windows.
6. السماح بالتداخل عندما يكون منطقيًا.
7. الحفاظ على continuous visual flow.
8. عدم إجبار الرسم على كلمة واحدة.
9. عدم ترك فترات طويلة بلا حركة بصرية.

---

# 22. مثال Solver

الصوت:

```text
0.00 → 0.50
"الكيوي"

0.50 → 2.10
"أصله الحقيقي من الصين"
```

Asset:

```text
Kiwi = 0.80s
China = 0.90s
Arrow = 0.30s
```

Solver قد ينتج:

```json
{
  "drawings": [
    {
      "asset_id": "A01",
      "start": 0.00,
      "end": 0.80
    },
    {
      "asset_id": "A02",
      "start": 1.10,
      "end": 2.00
    },
    {
      "asset_id": "A03",
      "start": 1.70,
      "end": 2.00
    }
  ]
}
```

لاحظ أن:

```text
Speech timing
```

لم يتم نسخه حرفيًا.

تم استخدامه كـ:

```text
Temporal Constraint
```

---

# 23. Drawing Actions

كل Asset يجب أن يحتوي على Action:

```text
draw
reveal
write
connect
transform
highlight
erase
replace
move
zoom
```

مثال:

```json
{
  "asset_id": "A03",
  "action": "draw",
  "start": 1.70,
  "end": 2.00
}
```

---

# 24. SFX Timing

الـ Timing Engine يجب أن يدعم SFX.

لكن لا يخترع SFX عشوائيًا.

إذا كان Asset Plan أو SFX Plan يحتوي:

```json
{
  "asset_id": "A02",
  "sfx": "marker_draw"
}
```

يقوم النظام بتحديد:

```text
SFX start
SFX end
```

بناءً على Drawing Timeline.

مثلاً:

```json
{
  "sfx": "marker_draw",
  "start": 1.10,
  "end": 2.00,
  "anchor": "A02"
}
```

---

# 25. SFX Rules

لا تجعل SFX يبدأ مع كل Asset.

استخدم SFX عندما يكون هناك:

```text
reveal
important drawing
transition
impact
highlight
transformation
```

ولا تملأ الفيديو بالمؤثرات.

---

# 26. Camera Timing

يجب أن يدعم النظام لاحقًا:

```text
camera_pan
camera_zoom
camera_focus
camera_reveal
```

مثلاً:

```json
{
  "type": "camera_zoom",
  "start": 2.0,
  "end": 2.6,
  "target": "A02"
}
```

---

# 27. Master Timeline

في النهاية أنشئ:

```text
master_timeline.json
```

ويجمع:

```text
speech
words
sentences
pauses
visual_beats
drawings
sfx
camera
```

مثال:

```json
{
  "section_id": "003",

  "duration": 12.48,

  "speech": [...],

  "visual": [
    {
      "asset_id": "A01",
      "action": "draw",
      "start": 0.0,
      "end": 0.8
    }
  ],

  "sfx": [
    {
      "type": "marker_draw",
      "start": 0.2,
      "end": 0.7
    }
  ],

  "camera": [
    {
      "type": "zoom",
      "start": 1.8,
      "end": 2.5,
      "target": "A02"
    }
  ]
}
```

---

# 28. Timeline يجب أن يكون Event-Based

لا أريد Timeline مبنيًا فقط على frames.

استخدم seconds كمرجع أساسي:

```text
start_s
end_s
```

ثم يستطيع Renderer لاحقًا تحويلها إلى:

```text
frames
```

حسب:

```text
FPS
```

مثلاً:

```python
frame = round(time_s * fps)
```

---

# 29. Precision

احتفظ بالدقة الأصلية:

```text
float seconds
```

ولا تقرب التوقيت مبكرًا.

ممنوع:

```python
round(time, 1)
```

في المراحل الداخلية.

التقريب يحدث فقط عند الـ rendering إذا احتاجه الـ renderer.

---

# 30. Timeline Confidence

كل event يجب أن يحتوي على confidence.

مثلاً:

```json
{
  "start": 1.42,
  "end": 2.30,
  "confidence": 0.94
}
```

ويجب التمييز بين:

```text
whisper_confidence
alignment_confidence
semantic_confidence
solver_confidence
```

---

# 31. Uncertainty Handling

إذا كانت كلمة غير واضحة في Whisper:

```text
confidence < threshold
```

لا تجعل النظام يتصرف وكأن التوقيت مؤكد.

سجل:

```text
needs_review = true
```

---

# 32. Timing Debugger

أنشئ:

```python
TimingDebugger
```

ويولد تقريرًا:

```text
timing/debug_report.json
```

ويجب أن يستطيع عرض:

```text
Sentence
Start
End
Words
Pause
Visual Beat
Asset
Drawing Start
Drawing End
SFX
```

---

# 33. Visualization

أنشئ optional debug output مثل:

```text
timing/timeline_debug.json
```

ويمكن لاحقًا تحويله إلى:

```text
HTML Timeline
```

لرؤية:

```text
VOICE
████████████████████

WORDS
██ ██ ███ ███

PAUSES
        ░░░

DRAWING
   █████
          ███████

SFX
      ▲       ▲
```

---

# 34. Architecture

أنشئ المشروع:

```text
section_timing/
│
├── main.py
├── config.yaml
│
├── transcription/
│   ├── faster_whisper_engine.py
│   └── whisper_parser.py
│
├── alignment/
│   ├── arabic_normalizer.py
│   ├── token_aligner.py
│   └── script_audio_aligner.py
│
├── speech/
│   ├── sentence_segmenter.py
│   ├── pause_detector.py
│   └── speech_beat_detector.py
│
├── visual/
│   ├── semantic_beat_mapper.py
│   ├── drawing_demand.py
│   ├── drawing_duration.py
│   └── beat_solver.py
│
├── effects/
│   ├── sfx_mapper.py
│   └── camera_mapper.py
│
├── timeline/
│   ├── models.py
│   ├── builder.py
│   └── exporter.py
│
├── debug/
│   └── debugger.py
│
└── tests/
    ├── test_whisper.py
    ├── test_alignment.py
    ├── test_pauses.py
    ├── test_visual_beats.py
    ├── test_solver.py
    └── test_timeline.py
```

---

# 35. مهم جدًا: لا تجعل Faster-Whisper مسؤولًا عن Semantic Understanding

Faster-Whisper مسؤول عن:

```text
WHAT WORD WAS SPOKEN
WHEN WAS IT SPOKEN
```

وليس:

```text
WHAT SHOULD BE DRAWN
```

هذه مسؤولية:

```text
Asset Plan
+
Semantic Beat Mapper
```

---

# 36. لا تستخدم Word Timing بشكل حرفي

مثلاً:

```text
"والكيوي يستخدم كغذاء وحتى كدواء"
```

لا تنتج:

```text
والـ → draw
كيوي → draw
يستخدم → draw
كغذاء → draw
وحتى → draw
كدواء → draw
```

بل:

```text
Semantic Beat 1
Kiwi → Food

Semantic Beat 2
Kiwi → Medicine
```

ثم Solver يحدد الحركة.

---

# 37. Semantic Importance

كل Visual Beat يمكن أن يحتوي:

```text
importance
```

مثلاً:

```text
subject = 0.8
main_fact = 1.0
transition = 0.3
minor_detail = 0.2
```

لكن:

**Semantic Importance لا تساوي Drawing Duration.**

العنصر المهم ليس بالضرورة أصعب في الرسم.

---

# 38. Drawing Demand

افصل تمامًا:

```text
Semantic Importance
```

عن:

```text
Drawing Demand
```

مثلاً:

```text
China Map
importance = 1.0
demand = 0.7

Simple Arrow
importance = 0.5
demand = 0.1
```

---

# 39. Solver Constraints

يجب أن يدعم Solver:

```text
hard constraints
soft constraints
```

Hard:

```text
start >= 0
end <= section_duration
end > start
dependency ordering
```

Soft:

```text
semantic synchronization
speech synchronization
pause utilization
visual continuity
drawing overlap
```

---

# 40. Dependencies

إذا كان:

```text
A01 = Kiwi
A02 = China
A03 = Arrow
```

والـ Arrow يحتاج الاثنين:

```json
{
  "asset_id": "A03",
  "depends_on": ["A01", "A02"]
}
```

فلا يسمح Solver برسم Arrow قبل ظهور العناصر المطلوبة.

---

# 41. Final Output

الملف الأهم:

```text
drawing_timeline.json
```

مثال:

```json
{
  "section_id": "003",

  "events": [

    {
      "id": "D001",
      "type": "draw",
      "asset_id": "A01",
      "start_s": 0.00,
      "end_s": 0.82,
      "trigger": "semantic",
      "anchor_text": "الكيوي",
      "confidence": 0.96
    },

    {
      "id": "D002",
      "type": "draw",
      "asset_id": "A02",
      "start_s": 1.10,
      "end_s": 2.02,
      "trigger": "semantic",
      "anchor_text": "الصين",
      "confidence": 0.93
    },

    {
      "id": "D003",
      "type": "connect",
      "asset_id": "A03",
      "start_s": 1.72,
      "end_s": 2.02,
      "trigger": "dependency",
      "confidence": 0.91
    }

  ]
}
```

---

# 42. Master Timeline Schema

استخدم schema واضحًا وقابلًا للتوسع:

```text
section
├── audio
├── speech
│   ├── words
│   ├── sentences
│   └── pauses
│
├── semantic
│   └── beats
│
├── visual
│   ├── beats
│   └── drawings
│
├── sfx
│
└── camera
```

---

# 43. Reproducibility

نفس:

```text
audio
+
script
+
asset_plan
+
config
```

يجب أن يعطي نفس Timeline قدر الإمكان.

احفظ:

```text
config_hash
audio_hash
script_hash
asset_plan_hash
whisper_model
```

في metadata.

---

# 44. Performance

يجب ألا يعيد Faster-Whisper التحليل إذا لم يتغير:

```text
section.wav
```

استخدم:

```text
audio_hash
```

للـ cache.

إذا لم يتغير الصوت:

```text
reuse whisper.json
```

وإذا تغير Asset Plan فقط:

```text
لا تعيد Whisper
```

بل أعد:

```text
Semantic Mapping
+
Beat Solver
```

وهذا مهم جدًا لتقليل التكلفة والزمن.

---

# 45. Pipeline

نفذ الـ pipeline بهذا الترتيب:

```text
1. Load Section
       ↓
2. Load Audio
       ↓
3. Load Script
       ↓
4. Load Asset Plan
       ↓
5. Faster-Whisper
       ↓
6. Word Timeline
       ↓
7. Script ↔ Audio Alignment
       ↓
8. Sentence Segmentation
       ↓
9. Pause Detection
       ↓
10. Speech Beats
       ↓
11. Semantic Beats
       ↓
12. Asset Mapping
       ↓
13. Drawing Demand
       ↓
14. Drawing Duration
       ↓
15. Beat Solver
       ↓
16. SFX Mapping
       ↓
17. Camera Mapping
       ↓
18. Validation
       ↓
19. Export Master Timeline
```

---

# 46. أهم مبدأ في المشروع

لا تجعل النظام:

```text
Whisper → Drawing
```

بل:

```text
Whisper
   ↓
Audio Truth
   ↓
Alignment
   ↓
Semantic Beats
   ↓
Asset Mapping
   ↓
Drawing Demand
   ↓
Beat Solver
   ↓
Drawing Timeline
```

---

# 47. الهدف النهائي

عندما ينتهي النظام من Section واحد، أريد أن أستطيع إعطاء Renderer:

```text
section.wav
+
drawing_timeline.json
+
sfx_timeline.json
+
camera_timeline.json
```

فيستطيع Renderer إنتاج الفيديو بدون الحاجة إلى فهم النص أو استخدام Whisper مرة أخرى.

بمعنى أن:

**Timing Engine هو العقل الزمني.**

و:

**Renderer هو المنفذ فقط.**

---

# المطلوب

أنشئ المشروع كاملًا وقابلًا للتشغيل.

لا تستخدم pseudo-code.

اكتب جميع الملفات والكلاسات.

استخدم:

* Python 3.11+
* Faster-Whisper
* Pydantic models
* Type hints
* Logging
* JSON schemas
* Caching
* Unit tests
* Error handling

واجعل التصميم Modular بحيث يمكن لاحقًا استبدال:

```text
Faster-Whisper
```

بمحرك Alignment آخر بدون إعادة كتابة بقية النظام.

والأهم:

**لا تجعل التوقيت مجرد Word Timestamps.**

أريد نظامًا حقيقيًا يحول:

```text
Audio
+
Script
+
Visual Assets
```

إلى:

```text
Speech Timeline
+
Semantic Timeline
+
Drawing Timeline
+
SFX Timeline
+
Camera Timeline
=
MASTER VISUAL TIMELINE
```

وهذا الـ `MASTER VISUAL TIMELINE` سيكون المصدر الوحيد الذي يعتمد عليه Video Renderer.

# 🎙️ Voice Studio — محرك التعليق الصوتي الذكي

نظام مستقل ومتكامل داخل المشروع لتوليد التعليق الصوتي الاحترافي بالذكاء الاصطناعي عبر Google GenAI (`gemini-3.1-flash-tts-preview`)، مخصص لإنتاج تعليق صوتي فائق الواقعية متزامن مع الوايت بورد أنيميشن.

---

## 📂 هيكلية المجلد:
```text
voice_studio/
├── __init__.py       # تصدير الحزمة
├── engine.py         # المحرك الأساسي وتحويل الصوت الخام إلى WAV
├── profiles.py       # بروفايلات الشخصيات الصوتية وتوجيهات المخرج (Director Notes)
├── generate.py       # نقطة الانطلاق وأداة التشغيل المباشرة
├── vyond_story.py    # قسم القصص الدرامية بأسلوب فيوند (راوية مصرية بصوت Kore/Aoede)
└── README.md         # دليل الاستخدام
```

---

## ⚡ طريقة التشغيل السريعة:

### 1. كتابة النص:
اكتب أو عدّل النص في الملف:
`project_content/transcript_to_speech.txt`

### 2. توليد الصوت:
شغّل الأمر التالي من سطر الأوامر:
```powershell
python voice_studio/generate.py
```

### ✨ ميزات النظام:
- **تسمية ذكية وتلقائية:** يقوم النظام بقراءة أول جملة منطوقة من ملف النص (متجاهلاً وسوم الإخراج مثل `[emphasis]`)، ويسمي ملف الـ WAV بها تلقائياً في `project_content/audio/`.
- **جودة استوديو:** حفظ الصوت بصيغة WAV نقية ومعدل عينة 24kHz Mono متوافق تماماً مع محرك أنيميشن الوايت بورد.
- **بروفايل اليوتيوبر السعودي:** أداء سريع، حماسي، عفوي وغير رتيب.

---

## 🎭 قسم القصص الدرامية بأسلوب فيوند (`vyond_story.py`):

مخصص لإنتاج القصص الدرامية باللهجة المصرية القاهرية بصوت راوية نسائي واحد ثابت (`Kore` أو `Aoede`) مع توجيه المشاعر لكل مقطع، وتنظيف الصمت (`-42 dBFS`)، وتطبيع الصوت (`headroom=2.0 dB`)، وإضافة فواصل زمنية (`180ms` بين المقاطع و`450ms` عند انتقال المشاهد)، والتصدير بصيغة MP3 (`192k`) أو WAV.

### التشغيل من سطر الأوامر:
```powershell
python -m voice_studio.vyond_story --story-file story.json --output project_content/audio/full_story_kore.mp3
```

### التشغيل من بايثون:
```python
from voice_studio import VyondStoryEngine

engine = VyondStoryEngine(voice_name="Kore")
story_chunks = [
    {"emotion": "تشويق وغموض", "text": "اللي حصل في الليلة دي محدش كان يصدقه...", "scene_break": False},
    {"emotion": "صدمة وانفعال", "text": "وفجأة الباب اتفتح!", "scene_break": True},
]
engine.render_full_story(story_chunks, output_file="full_story_kore.mp3")
```

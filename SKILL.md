---
name: aion-production-cli
description: Central CLI skill for AI models producing motion-graphics explainer videos through `pipeline_cli.py` across all 12 unified AION stages without rewriting scripts or mutating protected projects.
---

# AION Video Production CLI Skill (`SKILL.md`)

> **Studio Constitution (دستور الاستوديو الإبداعي والتقني):**
> 1. **المهام الميكانيكية لأدوات الـ CLI فقط (`pipeline_cli.py`):** توليد الصوت، محاذاة التوقيت بالكلمة والجملة (Whisper)، قص عناصر الاستوريبورد، تقطيع الصوت ودمج الـ CTA الموحد، بناء ملفات `.ecproj`، الرندر عبر الـ GPU، مزج الـ SFX، توليد ألواح الفحص (`QA`)، والتجميع النهائي (`merge`) تتم حصرياً عبر أوامر `pipeline_cli.py`.
> 2. **التفكير والإبداع للمودل من ملفات الـ JSON والتوقيت والصوت فقط:** يقرأ المودل نصوص السكربت، وملفات التوقيت (`*_timing_master.json`)، وكتالوجات العناصر البصرية بصيغة JSON (`storyboard_catalog/*.json` أو `semantic_manifest.json` أو مخرجات `studio shorts --action inspect`) ليبتكر الهوية البصرية، اختيار الخطوط، كوريغرافيا المشاهد (`Scene Graph V2`)، الرسوم الإجرائية، وهيكلة الشورتس (`shorts_specs.json`).
> 3. **حظر قراءة الصور قبل الإنتاج (Zero Pre-Render Image Reads):** يُمنع فتح أو تحليل صور الـ Storyboard الخام أو صور العناصر المفرغة (`entity_*.png`) أثناء التخطيط أو الإخراج أو صناعة الشورتس. تُفهم العناصر من الـ JSON فقط، وتُستخدم الصور للتنفيذ داخل المحرك فقط.
> 4. **الفحص البصري بعد الرندر فقط (Post-Render QA Only):** لا تُفتح الصور إلا بعد انتهاء الرندر لفحص ألواح الجودة النهائية (`creative_contact_sheet.png`، `mobile_preview.png`، `qa_contact_sheet.png`) أو عند تشخيص خطأ ظهر بعد الإنتاج.

## 1. Mandatory First Check (Inspect Before Acting)

```bash
python pipeline_cli.py doctor --json
python pipeline_cli.py projects
python pipeline_cli.py status --detailed --project <project_name>
```

Check `CLI_REFERENCE.md` for live parser-generated flags, `AGENTS.md` for protected projects & rollback rules, and `PIPELINE_CONTRACTS.md` for every stage's exact inputs/outputs.

## 2. Unified 12-Stage Production Sequence

`Script -> Voice -> Timing -> Assets (Extract) -> Semantic Mapping -> Creative Brief -> AI Director -> Motion Graphics -> SFX -> EffectCraft -> Render -> QA -> Merge`

### Quick Full-Pipeline Execution (Resumable + Isolated Run Folder)
```bash
# Run full pipeline cleanly into a new isolated folder under exports/runs/<run_id>/
python pipeline_cli.py auto --pipeline aion --project <project_name> --start 1 --end 8

# Resume an interrupted or partially failed run from the last successful stage:
python pipeline_cli.py auto --pipeline aion --resume --project <project_name>

# Run a targeted stage window cleanly (e.g. only stages 5..12 after storyboards arrive):
python pipeline_cli.py run --from-stage semantic-map --to-stage merge --project <project_name> --run-id <run_id>
```

### Step-by-Step Single-Stage Execution

1. **Initialize New Project (`ar` or `en`):**
   ```bash
   python pipeline_cli.py init <project_name> --sections 8 --lang en --voice Puck
   ```
2. **Script Split & Validation (`script`):**
   ```bash
   python pipeline_cli.py script --all --project <project_name>
   ```
3. **Gemini 3.8 Flash TTS Voiceover (`voice`):**
   ```bash
   python pipeline_cli.py voice --all --project <project_name>
   ```
   _Includes automatic Faster-Whisper duplicate/truncation verification, key-pool rotation, tail-glitch trimming, and `-15 LUFS` 48kHz PCM mastering._
4. **Word & Sentence Alignment (`timing`):**
   ```bash
   python pipeline_cli.py timing --all --project <project_name>
   ```
5. **Storyboard Asset Extraction (`extract`):**
   ```bash
   python pipeline_cli.py extract --all --mode grid --project <project_name>
   ```
   _Produces `entity_01..20.png` (3x PhotoCraft HD + edge-sliver strip) + `metadata.json` + `contact_sheet.png`._
6. **Semantic Mapping (`semantic-map`):**
   ```bash
   python pipeline_cli.py semantic-map --all --project <project_name>
   ```
7. **Creative Brief (`brief`):**
   ```bash
   python pipeline_cli.py brief --all --project <project_name>
   ```
8. **AI Director Scene Graph (`direct`):**
   - Synthesize default grounded `scene_graph.json` (and auto-audit Glow/card contrast), OR author custom semantic `director/section_XX/scene_graph.json` and run `direct` (without `--force`) to validate it in-place:
   ```bash
   python pipeline_cli.py direct --all --project <project_name>
   ```
9. **Motion Derivatives (`motion`) & Studio SFX Mixing (`sfx`):**
   ```bash
   python pipeline_cli.py motion --all --project <project_name> --run-id <run_id>
   python pipeline_cli.py sfx --all --project <project_name> --run-id <run_id>
   ```
10. **GPU EffectCraft Compile & Render (`render`):**
    ```bash
    python pipeline_cli.py render --all --pipeline aion --project <project_name> --run-id <run_id>
    ```
11. **Automated + Visual QA (`qa`) & Master Merge (`merge`):**
    ```bash
    python pipeline_cli.py qa --all --project <project_name> --run-id <run_id>
    python pipeline_cli.py merge --pipeline aion --project <project_name> --run-id <run_id>
    ```
    **Mandatory Human/Agent Visual Gate:** Always inspect the generated `qa_contact_sheet.png` images via image viewer / `read_file` before final delivery.

---

## 3. EffectCraft Creative Studio (`studio` V5 — ECGC Compiler)

AION Creative Studio V5 (`core/aion/ecgc_compiler.py`, `creative_director.py`, `motion_grammar.py`, `procedural_graphics.py`, `visual_qa.py`) upgrades AION with generative vector motion graphics, 15 narrative grammar treatments, `asset_factory` SVG icons (`edit.pasteSvg`), curved Bezier trim paths & arrows, repeaters, 2.5D depth/lighting, and Creative Scene Graph V2 (`aion.scene_graph.v2`).

### Studio CLI Commands (Read-Only Checks Never Modify Reference Projects)
```bash
# 1. Inspect V5 readiness, empirical EffectCraft capability coverage, fonts & golden integrity
python pipeline_cli.py studio doctor --json

# 2. View cached capability matrix (config/effectcraft_capabilities.json) or re-run 20 live probes
python pipeline_cli.py studio capabilities
python pipeline_cli.py studio capabilities --probe

# 3. Verify Motion Grammar (15 intents), Procedural Vectors & live EffectCraft preview compilation
python pipeline_cli.py studio graphics-test --render-preview

# 4. Compile & render an isolated V5 Creative Studio run (auto-refuses writes to mind_glitches_ar)
python pipeline_cli.py studio compile --project <project_name> --section 01 --style-mode scientific_explanation --aspect 16:9 --story-genre psychological_cinematic --run-id <run_id>

# 5. Fast preview PNG render or Visual Intelligence QA audit (creative_quality_report.json + creative_contact_sheet.png + mobile_preview.png)
python pipeline_cli.py studio preview --project <project_name> --section 01 --style-mode cinematic_2_5d
python pipeline_cli.py studio qa --project <project_name> --section 01 --run-id <run_id>

# 6. Inspect licensed typography registry, verify SHA-256 checksums, or run live EffectCraft font/kinetic probe
python pipeline_cli.py studio fonts --verify-sha --json
python pipeline_cli.py studio fonts --probe

# 7. Inspect all sections' scripts, sentence timings & visual JSON catalogs (0 image reads!)
python pipeline_cli.py studio shorts --action inspect --project <project_name>

# 8. Plan, compile & package native 9:16 Shorts reusing existing project assets/timing & shared CTA
python pipeline_cli.py studio shorts --action plan --project <isolated_project>
python pipeline_cli.py studio shorts --action compile --project <isolated_project> --all --run-id shorts_v6 --force
```

---

## 4. الدليل العملي للإخراج النهائي (Long-Form 16:9 & Viral Shorts 9:16 Playbook)

### أولاً: إخراج الفيديو الطويل (`16:9` — الافتراضي `720p / 1280x720`، ولـ `1080p` أضف `--resolution 1080p`)
1. **تجهيز البيانات الميكانيكية بالـ CLI (إن لم تكن جاهزة):**
   ```bash
   python pipeline_cli.py script --all --project <project_name>
   python pipeline_cli.py voice --all --project <project_name>
   python pipeline_cli.py timing --all --project <project_name>
   python pipeline_cli.py extract --all --mode grid --project <project_name>
   python pipeline_cli.py semantic-map --all --project <project_name>
   ```
2. **قراءة سياق الإبداع من الـ JSON (بدون قراءة أي صورة PNG):**
   - استعرض ملخص التوقيت والعناصر البصرية لكافة السكاشن بأمر واحد:
     ```bash
     python pipeline_cli.py studio shorts --action inspect --project <project_name>
     ```
   - يعتمد المودل على:
     - `sections/section_XX/timing/section_XX_timing_master.json` (توقيت الجمل والكلمات بالثانية).
     - كتالوج العناصر البصرية JSON (`name_ar`, `description_ar`, `narrative_role`) لتوظيف جميع العناصر (`entity_01..entity_20`) في مكانها الدرامي الصحيح.
3. **التأليف الإبداعي لـ `scene_graph.v2.json` أو التشغيل عبر `studio compile`:**
   - يختار المودل:
     - **ثنائية الخطوط (Typography Director):** بحد أقصى عائلتين لكل فيديو حسب النوع (`psychological_cinematic` ⬅️ `Cairo` + `Alyamama`، `historical_documentary` ⬅️ `IBM Plex Sans Arabic` + `Amiri`، `scientific_explanation` ⬅️ `Cairo` + `Readex Pro`).
     - **العناوين التحريرية المكثفة (`editorial_headline`):** عبارات من 3–5 كلمات متزامنة مع المعنى (وليس تفريغاً حرفياً لكلام الراوي)، بأنماط حركية متنوعة (`impact_title`, `word_emphasis`, `data_callout`, `documentary_card`, `mask_reveal`).
     - **الرسوم المتجهية الإجرائية (`procedural_graphics`):** مخاريط الإضاءة (`spotlight_cone`)، الأسهم المنحنية (`bezier_connector`)، حلقات الرادار (`concentric_rings`)، الأعمدة الإحصائية (`chart_bar` مع `direction: "rtl"`).
   - الرندر والتجميع في مسار معزول (`exports/runs/<run_id>/`):
     ```bash
     python pipeline_cli.py studio compile --project <project_name> --all --run-id <run_id> --force
     python pipeline_cli.py studio merge --project <project_name> --run-id <run_id>
     ```

### ثانياً: إخراج الشورتس الفيرال المستقلة (`9:16` — الافتراضي `720p / 720x1280`، ولـ `1080p` أضف `--resolution 1080p`) بدون قراءة الصور
1. **استخراج خريطة التوقيت والعناصر JSON بأمر واحد:**
   ```bash
   python pipeline_cli.py studio shorts --action inspect --project <isolated_project>
   ```
   - يُنتج ملف `<project>/shorts/creative_context_digest.json` متضمناً الجمل مرقمة بتوقيتاتها الدقيقة (`start`, `end`) ووصف الـ 20 عنصراً لكل سيكشن دون قراءة أي صورة.
2. **التصميم الإبداعي للشورتس (`shorts/shorts_specs.json`):**
   - يقيّم المودل السكاشن حسب قوة الخطاف في أول ثانية، وضوح الفكرة، المفاجأة، وتوفر العناصر البصرية، ويختار أقوى 3 إلى 8 شورتس.
   - **إعادة استخدام الصوت المعتمد (Zero Duplicate TTS):** يحدد المودل نافذة القطع النظيفة عند بداية الجملة الفعالة (`"trim_source_window": [start_sec, null]`) لقص مقدمة الترتيب في الفيديو الطويل (مثل `"أما الخلل الثالث..."`) والدخول فوراً في الحدث من الثانية `0.00` بنفس الصوت الماستر المعتمد.
   - **دمج الـ CTA الموحد للقناة تلقائياً:** يقوم المحرك بإلحاق ملف [`assets/audio/cta/cta_channel_ar_fenrir.wav`](file:///e:/image_to_animate/assets/audio/cta/cta_channel_ar_fenrir.wav) (`"اعمل لايك، واشترك في القناة، وكمل الفيديو كامل من الفيديو المرتبط تحت اسم القناة!"`) بعد وقفة تنفس `0.24s`، مع تمديد المشهد الأخير حتى `cta_start` لمنع أي فريم أسود فارغ، وعرض أيقونات اللايك والجرس وسهم الفيديو المرتبط متجهياً.
   - يكتب المودل أو يعدّل `<project>/shorts/shorts_specs.json` (أو `<project>/shorts/short_XX/short_spec.json`) لتخصيص المشاهد، الألوان، التخطيطات العمودية (`radar_focus`, `diagonal_duet`, `vertical_causal_chain`, `vertical_split_compare`, `chart_clash_bars`, `triangle_climax`)، والرسوم الإجرائية.
3. **التوليد والرندر والتغليف النهائي بأمر واحد:**
   ```bash
   python pipeline_cli.py studio shorts --action compile --project <isolated_project> --all --run-id shorts_v6_master --force
   ```
   - يُنتج لكل شورت: `script.json`, `timing.json`, `creative_plan.json`, `scene_graph.json`, `seo.json`, `short_XX.ecproj`, `preview.mp4`, `final.mp4`, `qa_report.json`، بالإضافة إلى الفهرس الشامل `shorts_package.json`.
4. **بوابة الفحص البصري بعد الإنتاج (Post-Render Visual QA):**
   - بعد انتهاء الرندر فقط، افتح `exports/runs/<run_id>/shorts/short_XX/qa/creative_contact_sheet.png` و`mobile_preview.png` عبر `read_file` للتحقق من عدم وجود أي تداخل نصي أو فريم فارغ قبل التسليم.

### Empirical Engine Notes Verified on This Host
- Check `config/effectcraft_capabilities.json` before targeting EffectCraft effects (`VERIFIED`: 19, `PARTIAL`: 1).
- Shared studio fonts live under `assets/typography/fonts` (SHA-256 + `OFL.txt` tracked in `assets/typography/font_registry.json`) and are auto-injected via `EFFECTCRAFT_FONT_DIRS` (`config/typography_settings.json`). Commercial fonts (`Fit Arabic`, `Panton Arabic`, `Khareef`, `Sakkal Saad Poster`, `Druk`) stay `LICENSE_REQUIRED` and fall back to documented open families.
- `arabic_rtl_text` renders and animates crisply in `Cairo`/`Alexandria`/`Alyamama`/`Amiri`/`IBM Plex Sans Arabic`/`Readex Pro` RTL with Track Matte (`mask_reveal`), whole-word `layer.setText {range}` (`word_emphasis`), `impact_title`, `documentary_card`, `data_callout`, word-mode RangeSelector (`basedOn=2`), or pre-shaped Arabic vector SVG (`core/aion/kinetic_typography.py`); per-character splitting on Arabic strings is banned to preserve connected cursive ligatures.
- Keep `use_character: false` unless explicitly requested in the project brief; preserve ZERO-BGM and full un-truncated voiceover timing.

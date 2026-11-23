# 📁 دليل الملفات — File Reference

مرجع سريع لجميع ملفات المشروع مع وصف مختصر لكل ملف.

---

## 📦 الجذر (`/`)

| الملف | الوصف |
|-------|-------|
| `animate_storyboard.py` | سكربت CLI للأنيميشن السينمائي (4K UHD، كاميرا سينمائية، خط عربي) |
| `split_audio.py` | أداة تقسيم ملفات الصوت إلى قطع بمدة محددة (PyAV lossless) |
| `README.md` | الوثيقة الرئيسية للمشروع الأصلي |
| `CHANGELOG.md` | سجل التغييرات لجميع الإصدارات (0.0.14 → 0.6.2) |
| `TODO.md` | الخطط المستقبلية |
| `LICENSE` | رخصة MIT — Ahmed Abdellah 2026 |
| `FORENSIC_AUDIT.md` | تقرير تدقيق جنائي للمشروع |
| `REVERSE_ENGINEERING_REPORT.md` | تقرير هندسة عكسية مفصّل |
| `.gitignore` | استثناءات Git |
| `openh264-2.5.0-win64.dll` | مكتبة OpenH264 لترميز الفيديو على Windows |

---

## 🖥️ تطبيق Kivy (`kivy/`)

### الملفات الرئيسية
| الملف | الوصف |
|-------|-------|
| `main.py` | نقطة الدخول — `SketchAnimationApp` (KivyMD v0.7.0) |
| `main_layout.kv` | تخطيط واجهة المستخدم (Kivy Language) |
| `sketchApi.py` | واجهة API مبسطة — تعيد تصدير الوظائف من المحرك |
| `buildozer.spec` | إعدادات بناء Android (Buildozer) |
| `dlDesktop.spec` | إعدادات بناء سطح المكتب (PyInstaller) |
| `build_exe.py` | سكربت بناء EXE |
| `build_nuitka.py` | سكربت بناء Nuitka |
| `img2sketch.iss` | سكربت Inno Setup Installer |
| `requirements.txt` | متطلبات Python العامة |
| `req_android.txt` | متطلبات Android |
| `req_desktop.txt` | متطلبات سطح المكتب |

---

### المحرك — `kivy/engine/`

#### `engine/core/` — النماذج الأساسية
| الملف | الكلاسات | الوصف |
|-------|----------|-------|
| `scene.py` | `SceneConfig`, `SceneObject`, `Scene` | إعدادات المشهد والكائنات |
| `stroke.py` | `StrokeType`, `Stroke` | أنواع وبيانات الخطوط |
| `region.py` | `FillMode`, `ColorRegion` | مناطق الألوان والتعبئة |
| `timeline.py` | `Keyframe`, `CameraShot`, `StrokeEvent`, `FillEvent`, `Timeline` | الخط الزمني والأحداث |
| `project.py` | `StructureType`, `PanelStructure`, `Project` | هيكل المشروع واللوحات |
| `image_io.py` | — | قراءة الصور بمسارات Unicode |

#### `engine/processing/` — المعالجة والتحليل
| الملف | الكلاسات | الوصف |
|-------|----------|-------|
| `image_processor.py` | `ImageProcessor` | المعالج الرئيسي (خط الأنابيب العالمي V3) |
| `panel_detector.py` | `PanelDetector`, `StoryboardConfidenceAnalyzer` | كشف لوحات Storyboard |
| `whiteboard_processor.py` | `WhiteboardProcessor` | معالج السبورة التعليمية |
| `edge_extractor.py` | `EdgeExtractor` | استخراج الحواف (Canny) |
| `stroke_classifier.py` | `StrokeClassifier` | تصنيف الخطوط حسب النوع |
| `color_processor.py` | `ColorProcessor` | تكميم الألوان (K-Means) |
| `region_extractor.py` | `RegionExtractor` | استخراج مناطق الألوان |
| `dynamic_border_detector.py` | `DynamicBorderDetector` | كشف وإزالة حدود اللوحات |
| `dynamic_decomposition.py` | — | تفكيك ديناميكي للصورة |
| `m1_panel_extractor.py` | `DynamicPanelExtractor` | وحدة M1: استخراج اللوحات |
| `m2_layer_splitter.py` | `MethodALayerSplitter` | وحدة M2: فصل الطبقات |
| `m3_text_line_auditor.py` | `TextLineAuditor` | وحدة M3: تحليل النص |

#### `engine/render/` — التصيير
| الملف | الكلاسات | الوصف |
|-------|----------|-------|
| `renderer.py` | `Renderer` | المصيّر V3.1 (Progressive Reveal) |
| `concentric_engine.py` | — | المحرك المداري (360° Orbital) |
| `deep_pipeline_engine.py` | — | المحرك العميق السينمائي (6-Stage) |
| `hand_compositor.py` | — | تركيب سريع ليد الرسم |
| `hand_overlay.py` | `HandOverlay` | نظام يد متقدم مع إمالة |
| `viewport_transform.py` | — | تحويل viewport الكاميرا |

#### `engine/animation/` — التحريك
| الملف | الكلاسات | الوصف |
|-------|----------|-------|
| `drawing_order.py` | `DrawingOrder` | بناء الخط الزمني للرسم |
| `stroke_animator.py` | `StrokeAnimator` | تحريك الخطوط تدريجياً |
| `fill_animator.py` | `FillAnimator` | تحريك التعبئة اللونية |
| `easing.py` | — | منحنيات التخفيف |

#### `engine/camera/` — الكاميرا
| الملف | الكلاسات | الوصف |
|-------|----------|-------|
| `camera.py` | `CameraState`, `Camera` | الكاميرا الافتراضية |
| `camera_animator.py` | `CameraAnimator` | تحريك الكاميرا بين اللقطات |

#### `engine/planning/` — التخطيط
| الملف | الكلاسات | الوصف |
|-------|----------|-------|
| `storyboard_planner.py` | `StoryboardPlanner` | بناء مشهد Storyboard موحد |
| `sequence_planner.py` | `SequencePlanner` | ترتيب تسلسل الرسم |
| `shot_planner.py` | `ShotPlanner` | تخطيط لقطات الكاميرا |
| `object_grouping.py` | `MajorObjectGrouper` | تجميع العناصر |

#### `engine/video/` — الفيديو
| الملف | الكلاسات | الوصف |
|-------|----------|-------|
| `encoder.py` | `VideoEncoder` | ترميز H.264 (PyAV + NVENC fallback) |

---

### واجهة المستخدم — `kivy/ui/`

#### `ui/screens/`
| الملف | الكلاسات | الوصف |
|-------|----------|-------|
| `home_screen.py` | `HomeScreen` | الشاشة الرئيسية (رفع الصور) |
| `loading_screen.py` | `LoadingScreen` | شاشة التحميل |
| `grid_setup_screen.py` | `GridSetupScreen` | إعداد شبكة اللوحات |
| `scene_screen.py` | `SceneScreen` | عرض ومعاينة المشهد |

#### `ui/services/`
| الملف | الكلاسات | الوصف |
|-------|----------|-------|
| `settings_repository.py` | `SettingsRepository` | حفظ/تحميل الإعدادات |
| `dialog_service.py` | `NativeDialogService` | حوارات النظام |
| `analysis_service.py` | `AnalysisWorkflowService` | سير تحليل الصورة |
| `render_service.py` | `RenderWorkflowService` | سير التصيير والتصدير |

#### `ui/state/`
| الملف | الكلاسات | الوصف |
|-------|----------|-------|
| `project_state.py` | `ProjectState`, `AppPhase` | إدارة حالة التطبيق |

#### أخرى
| الملف | الوصف |
|-------|-------|
| `ui/theme.py` | سمة التطبيق (ألوان، خطوط) |
| `ui/canvas/` | عناصر الرسم على الكانفاس |
| `ui/widgets/` | ودجات مخصصة |

---

### التراخيص — `kivy/licensing/`

| الملف | الكلاسات | الوصف |
|-------|----------|-------|
| `license_guard.py` | `LicenseGuard` | حارس التراخيص الرئيسي |
| `activation_dialog.py` | `ActivationDialog` | حوار التفعيل |
| `license_client.py` | — | عميل API التراخيص |
| `crypto.py` | — | التشفير وفك التشفير |
| `fingerprint.py` | — | بصمة الجهاز |
| `heartbeat.py` | — | نبض التحقق الدوري |
| `local_cache.py` | — | التخزين المؤقت المحلي |
| `constants.py` | — | ثوابت التراخيص |

---

## 🧪 الاختبارات (`tests/`)

| الملف | الوصف |
|-------|-------|
| `test_architecture_fitness.py` | اختبارات ملاءمة البنية المعمارية |
| `test_golden_baseline.py` | اختبار الخط الأساسي الذهبي (مرجعي) |
| `test_v3_suite.py` | مجموعة اختبارات V3 الشاملة |
| `test_panel_animation.py` | اختبار أنيميشن اللوحات |
| `test_scene_render.py` | اختبار تصيير المشاهد |
| `test_sequential_ordering.py` | اختبار الترتيب التتابعي |
| `test_resolution_quality.py` | اختبار جودة الدقة |
| `test_drawing_speed_settings.py` | اختبار إعدادات سرعة الرسم |
| `test_project_state.py` | اختبار حالة المشروع |
| `test_licensing.py` | اختبار نظام التراخيص |
| `test_zero_trust_security.py` | اختبار أمان عدم الثقة |
| `test_studio_open.py` | اختبار فتح الاستوديو |
| `test_full_ui_interaction.py` | اختبار تفاعل واجهة كامل |
| `test_interactive_ui_complete.py` | اختبار واجهة تفاعلية شامل |
| `test_arrow_and_drag.py` | اختبار السهم والسحب |
| `test_activation_dialog.py` | اختبار حوار التفعيل |
| `test_video_player.py` | اختبار مشغل الفيديو |
| `capture_golden_baseline.py` | التقاط بيانات الخط المرجعي |
| `interactive_manual_run.py` | تشغيل تفاعلي يدوي |

---

## 🔬 التجارب (`experiments/`)

### `experiments/modular_pipeline/`
| الملف | الوصف |
|-------|-------|
| `m1_panel_extractor.py` | وحدة M1: استخراج اللوحات |
| `m2_layer_splitter.py` | وحدة M2: فصل الطبقات |
| `m3_character_engine.py` | وحدة M3: محرك الشخصيات |
| `m3_text_line_auditor.py` | وحدة M3: تدقيق النص |
| `m4_camera_transition_stitcher.py` | وحدة M4: تخييط انتقالات الكاميرا |
| `m4_typography_engine.py` | وحدة M4: محرك الطباعة |
| `m5_camera_director.py` | وحدة M5: مخرج الكاميرا |
| `run_scene_pipeline.py` | تشغيل الخط الكامل |

### تجارب أخرى
| الملف | الوصف |
|-------|-------|
| `end_to_end_storyboard_to_videos.py` | تحويل كامل من Storyboard إلى فيديوهات |
| `test_cinematic_storyboard_2026.py` | اختبار Storyboard السينمائي |
| `text_graphics_separation_benchmark.py` | معيار فصل النص/الرسومات |
| `test_step*_*.py` | اختبارات مرحلية متعددة |

---

## 🛠️ الأدوات (`tools/`)

مجلد يحتوي على **بروتوتايبات بحثية** (prototype_3 → prototype_9) تتضمن:
- تجارب اكتشاف الأقاليم
- اكتشاف الحدود الديناميكية
- تصنيف الخطوط
- محركات التصميم الإيقاعي
- تحليل الطبقات والكيانات

---

## 📁 مجلدات البيانات

| المجلد | الوصف |
|--------|-------|
| `kivy/data/images/` | أصول الصور (يد الرسم، قناع اليد) |
| `test_images/` | صور اختبارية |
| `output_animations/` | فيديوهات الأنيميشن المولّدة |
| `step_inspection_images/` | صور تصحيح وتشخيص |
| `audio_chunks/` | قطع الصوت المقسمة |
| `docs/images/` | صور الوثائق |

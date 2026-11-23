# 🎬 EffectCraft Motion Effects Catalog (معرض تأثيرات إفكت كرافت)

> **دليل الاستخدام الشامل للمستخدم والذكاء الاصطناعي**: قائمة بجميع التأثيرات البصرية والحركية المدعومة في محرك EffectCraft مع نماذج الكود الجاهزة للاستخدام في ملف `manifest.json`.

---

## 📌 جدول التأثيرات الكامل ونماذج الاستخدام

| التأثير | الاسم بالعربية | التصنيف | المعاينة | كود الاستدعاء في المانيفست |
|:---|:---|:---:|:---:|:---|
| `pop_bounce` | **ظهور ارتدادي نابض (Pop & Bounce)** | `entrance` | [pop_bounce preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_pop_bounce_emerald_1_8s.png) | `"anim_type": "pop_bounce"` |
| `directional_slide` | **انزلاق خاطف باتجاه معين (Directional Slide)** | `entrance` | [directional_slide preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_directional_slide_crimson_1_8s.png) | `"anim_type": "directional_slide"` |
| `camera_zoom` | **تقريب الكاميرا السينمائية (3D Camera Zoom)** | `camera` | [camera_zoom preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_camera_zoom_royal_1_8s.png) | `"anim_type": "camera_zoom"` |
| `scale_punch` | **نبضة تضخيم الكلمة (Audio Scale Punch)** | `emphasis` | [scale_punch preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_scale_punch_amber_1_8s.png) | `"anim_type": "scale_punch"` |
| `orbit_arc` | **حركة مدارية منحنية (Orbit Arc)** | `motion` | [orbit_arc preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_orbit_arc_cyan_1_8s.png) | `"anim_type": "orbit_arc"` |
| `gravity_drop` | **سقوط حر بجاذبية (Gravity Drop)** | `physics` | [gravity_drop preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_gravity_drop_purple_1_8s.png) | `"anim_type": "gravity_drop"` |
| `light_sweep` | **مسح ضوئي نيون متوهج (CC Light Sweep)** | `stylize` | [light_sweep preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_light_sweep_emerald_1_8s.png) | `"anim_type": "light_sweep"` |
| `radio_waves` | **أمواج دائرية متوسعة (Radio Waves)** | `simulation` | [radio_waves preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_radio_waves_royal_1_8s.png) | `"anim_type": "radio_waves"` |
| `magnify_lens` | **عدسة مكبرة تفاعلية (Magnify Lens)** | `distort` | [magnify_lens preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_magnify_lens_cyan_1_8s.png) | `"anim_type": "magnify_lens"` |
| `glow_shimmer` | **وهج ساطع مشع (Stylized Glow)** | `stylize` | [glow_shimmer preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_glow_shimmer_amber_1_8s.png) | `"anim_type": "glow_shimmer"` |
| `turbulent_ripple` | **تموج عضوي غلياني (Turbulent Displace)** | `distort` | [turbulent_ripple preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_turbulent_ripple_crimson_1_8s.png) | `"anim_type": "turbulent_ripple"` |
| `echo_trail` | **أثر شبحي متكرر (Echo Ghost Trail)** | `time` | [echo_trail preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_echo_trail_purple_1_8s.png) | `"anim_type": "echo_trail"` |
| `shatter_burst` | **انفجار وشظايا متناثرة (Shatter Burst)** | `simulation` | [shatter_burst preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_shatter_burst_crimson_1_8s.png) | `"anim_type": "shatter_burst"` |
| `page_turn` | **قلب صفحة الكتاب (CC Page Turn)** | `transition` | [page_turn preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_page_turn_royal_1_8s.png) | `"anim_type": "page_turn"` |
| `split_screen` | **تقسيم شاشة المقارنة (Split Screen)** | `transition` | [split_screen preview](E:/image_to_animate/exports/effectcraft_studio/previews/demo_split_screen_teal_1_8s.png) | `"anim_type": "split_screen"` |

---

## 🤖 كيف يستخدم الذكاء الاصطناعي / المخرج التأثيرات في `manifest.json`؟

ببساطة شديدة وبدون أي تعقيد، عند كتابة أي عنصر داخل أي مشهد، يكفي كتابة اسم التأثير مباشرة في حقل `"anim_type"`:

```json
{
  "id": "scene_01",
  "start": 0.0,
  "end": 4.5,
  "elements": [
    {
      "asset_key": "r1_01_orchid_plant",
      "start": 0.0,
      "end": 4.5,
      "pos": [1350, 560],
      "target_size": 580,
      "anim_type": "light_sweep"
    }
  ],
  "words": [
    {
      "start": 1.2,
      "end": 3.8,
      "word": "بريق واكتشاف!",
      "theme": "emerald",
      "pos": [580, 540]
    }
  ]
}
```

---

## 🚀 أوامر التشغيل السريعة

```bash
# 1. رندر ومعاينة أي تأثير فورياً:
python core_engine/effectcraft_motion_studio.py --effect light_sweep --word 'سر رهيب!'

# 2. تصدير جميع عروض التأثيرات الـ 15 دفعة واحدة:
python core_engine/effectcraft_motion_studio.py --all

# 3. استعراض قائمة التأثيرات في الطرفية:
python core_engine/effectcraft_motion_studio.py --list
```

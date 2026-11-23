#!/usr/bin/env python3
"""
Automated Manifest Builder & EffectCraft Renderer for 3 YouTube Shorts.
Produces vertical 9:16 (1080x1920) videos at 30 FPS.
"""

import os
import sys
import core_engine.dns_patch

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ROOT_DIR / "projects" / "ottoman_sultans"
SHORTS_DIR = PROJECT_DIR / "shorts"
EXPORTS_DIR = PROJECT_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


MANIFEST_SHORT_01 = {
  "section_id": "short_01",
  "title": "الشورت 1: لعنة وزراء السلطان سليم الأول",
  "total_duration": 41.56,
  "fps": 30,
  "resolution": [1080, 1920],
  "ground_y": 1520,
  "theme": {"name": "eye_comfort_paper"},
  "enable_sfx": True,
  "scenes": [
    {
      "id": "scene_01",
      "start": 0.0,
      "end": 10.02,
      "camera": {"zoom_start": 1.0, "zoom_end": 1.04, "duration": 10.02},
      "elements": [
        {
          "asset_key": "10_selim_angry_point",
          "start": 0.0,
          "end": 9.9,
          "pos": [540, 1050],
          "target_size": 640,
          "entrance": "whip_motion",
          "exit": "shrink_out",
          "effects": [{"type": "border_flash", "color": "red", "time": 2.5}],
          "light_sweeps": [{"time": 5.2, "duration": 0.45, "intensity": 20.0}]
        },
        {
          "asset_key": "12_bloody_scimitar",
          "start": 3.4,
          "end": 9.9,
          "pos": [540, 750],
          "target_size": 420,
          "entrance": "pop_bounce",
          "exit": "shrink_out"
        },
        {
          "asset_key": "11_seven_severed_turbans",
          "start": 6.8,
          "end": 9.9,
          "pos": [540, 1380],
          "target_size": 460,
          "entrance": "squash_drop",
          "exit": "shrink_out"
        }
      ],
      "words": [
        {
          "start": 6.5,
          "end": 9.8,
          "word": "أعدم 7 من كبار وزرائه!",
          "theme": "crimson",
          "pos": [540, 360]
        }
      ]
    },
    {
      "id": "scene_02",
      "start": 10.02,
      "end": 24.2,
      "camera": {"zoom_start": 1.0, "zoom_end": 1.05, "duration": 14.18},
      "elements": [
        {
          "asset_key": "03_vizier_shroud",
          "start": 10.1,
          "end": 17.5,
          "pos": [540, 1050],
          "target_size": 580,
          "entrance": "card_stack",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 13.5, "duration": 0.45, "intensity": 18.0}]
        },
        {
          "asset_key": "06_vizier_will",
          "start": 15.5,
          "end": 24.0,
          "pos": [540, 1020],
          "target_size": 550,
          "entrance": "pop_bounce",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 19.5, "duration": 0.45, "intensity": 18.0}]
        },
        {
          "asset_key": "17_vizier_farewell_family",
          "start": 18.5,
          "end": 24.0,
          "pos": [540, 1400],
          "target_size": 460,
          "entrance": "slide_in",
          "exit": "shrink_out"
        }
      ],
      "words": [
        {
          "start": 11.2,
          "end": 15.0,
          "word": "الوزير لا يدري: لبيته أم للمقصلة؟",
          "theme": "amber",
          "pos": [540, 360]
        },
        {
          "start": 17.5,
          "end": 23.5,
          "word": "يلبسون أكفانهم ويكتبون وصاياهم!",
          "theme": "crimson",
          "pos": [540, 360]
        }
      ]
    },
    {
      "id": "scene_03",
      "start": 24.2,
      "end": 31.86,
      "camera": {"zoom_start": 1.0, "zoom_end": 1.04, "duration": 7.66},
      "elements": [
        {
          "asset_key": "18_istanbul_citizens_curse",
          "start": 24.3,
          "end": 31.6,
          "pos": [540, 1100],
          "target_size": 580,
          "entrance": "slide_in",
          "exit": "shrink_out"
        },
        {
          "asset_key": "21_famous_curse_scroll",
          "start": 27.0,
          "end": 31.6,
          "pos": [540, 800],
          "target_size": 500,
          "entrance": "elastic_overshoot",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 29.5, "duration": 0.45, "intensity": 20.0}]
        }
      ],
      "words": [
        {
          "start": 24.8,
          "end": 27.5,
          "word": "أشهر شتيمة في إسطنبول:",
          "theme": "amber",
          "pos": [540, 360]
        },
        {
          "start": 27.8,
          "end": 31.6,
          "word": "جعلك الله وزيراً عند سليم!",
          "theme": "crimson",
          "pos": [540, 360]
        }
      ]
    },
    {
      "id": "scene_04",
      "start": 31.86,
      "end": 41.56,
      "camera": {"zoom_start": 1.0, "zoom_end": 1.05, "duration": 9.7},
      "elements": [
        {
          "asset_key": "15_malignant_boil_back",
          "start": 31.9,
          "end": 35.3,
          "pos": [540, 1050],
          "target_size": 540,
          "entrance": "pop_bounce",
          "exit": "shrink_out"
        },
        {
          "asset_key": "01_master_roster_8sultans",
          "start": 35.2,
          "end": 41.5,
          "pos": [540, 950],
          "target_size": 640,
          "entrance": "pop_bounce",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 38.0, "duration": 0.45, "intensity": 22.0}]
        },
        {
          "asset_key": "11_two_video_screens_clicking",
          "start": 37.5,
          "end": 41.5,
          "pos": [540, 1420],
          "target_size": 420,
          "entrance": "whip_motion",
          "exit": "shrink_out"
        }
      ],
      "words": [
        {
          "start": 32.0,
          "end": 35.0,
          "word": "وفاة سليم الغريبة الصادمة!",
          "theme": "amber",
          "pos": [540, 360]
        },
        {
          "start": 36.0,
          "end": 41.2,
          "word": "شاهد الوثائقي الكامل في الأسفل!",
          "theme": "emerald",
          "pos": [540, 360]
        }
      ]
    }
  ]
}


MANIFEST_SHORT_02 = {
  "section_id": "short_02",
  "title": "الشورت 2: إخفاء جثة سليمان القانوني 48 يوماً",
  "total_duration": 32.24,
  "fps": 30,
  "resolution": [1080, 1920],
  "ground_y": 1520,
  "theme": {"name": "eye_comfort_paper"},
  "enable_sfx": True,
  "scenes": [
    {
      "id": "scene_01",
      "start": 0.0,
      "end": 13.8,
      "camera": {"zoom_start": 1.0, "zoom_end": 1.05, "duration": 13.8},
      "elements": [
        {
          "asset_key": "09_suleiman_death_bed_72",
          "start": 0.0,
          "end": 7.3,
          "pos": [540, 1050],
          "target_size": 600,
          "entrance": "pop_bounce",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 3.5, "duration": 0.45, "intensity": 18.0}]
        },
        {
          "asset_key": "20_calendar_48_days_hidden",
          "start": 7.2,
          "end": 13.6,
          "pos": [540, 1020],
          "target_size": 550,
          "entrance": "elastic_overshoot",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 10.5, "duration": 0.45, "intensity": 20.0}]
        }
      ],
      "words": [
        {
          "start": 2.0,
          "end": 6.5,
          "word": "مات في خيمته وعمره 72 سنة!",
          "theme": "amber",
          "pos": [540, 360]
        },
        {
          "start": 8.5,
          "end": 13.5,
          "word": "أخفى الجثة 48 يوماً كاملة!",
          "theme": "crimson",
          "pos": [540, 360]
        }
      ]
    },
    {
      "id": "scene_02",
      "start": 13.8,
      "end": 24.2,
      "camera": {"zoom_start": 1.0, "zoom_end": 1.04, "duration": 10.4},
      "elements": [
        {
          "asset_key": "15_forging_tughra_signature",
          "start": 13.8,
          "end": 18.2,
          "pos": [540, 1020],
          "target_size": 520,
          "entrance": "draw_stroke",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 16.0, "duration": 0.45, "intensity": 18.0}]
        },
        {
          "asset_key": "16_suspicious_soldiers",
          "start": 16.5,
          "end": 20.5,
          "pos": [540, 1400],
          "target_size": 420,
          "entrance": "slide_in",
          "exit": "shrink_out"
        },
        {
          "asset_key": "17_dressing_lookalike",
          "start": 18.0,
          "end": 24.0,
          "pos": [340, 980],
          "target_size": 450,
          "entrance": "card_stack",
          "exit": "shrink_out"
        },
        {
          "asset_key": "18_lookalike_waving_carriage",
          "start": 19.5,
          "end": 24.0,
          "pos": [740, 1050],
          "target_size": 500,
          "entrance": "whip_motion",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 22.0, "duration": 0.45, "intensity": 18.0}]
        }
      ],
      "words": [
        {
          "start": 14.2,
          "end": 17.8,
          "word": "تزوير التوقيع وأوامر الحرب!",
          "theme": "royal",
          "pos": [540, 360]
        },
        {
          "start": 19.2,
          "end": 23.8,
          "word": "شبيه يلوح للجيش في الظلام!",
          "theme": "emerald",
          "pos": [540, 360]
        }
      ]
    },
    {
      "id": "scene_03",
      "start": 24.2,
      "end": 32.24,
      "camera": {"zoom_start": 1.0, "zoom_end": 1.05, "duration": 8.04},
      "elements": [
        {
          "asset_key": "14_broken_heart_minarets",
          "start": 24.2,
          "end": 27.9,
          "pos": [540, 1020],
          "target_size": 520,
          "entrance": "draw_stroke",
          "exit": "shrink_out"
        },
        {
          "asset_key": "01_master_roster_8sultans",
          "start": 27.8,
          "end": 32.2,
          "pos": [540, 950],
          "target_size": 640,
          "entrance": "pop_bounce",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 30.0, "duration": 0.45, "intensity": 20.0}]
        },
        {
          "asset_key": "11_two_video_screens_clicking",
          "start": 28.5,
          "end": 32.2,
          "pos": [540, 1420],
          "target_size": 420,
          "entrance": "whip_motion",
          "exit": "shrink_out"
        }
      ],
      "words": [
        {
          "start": 24.5,
          "end": 27.5,
          "word": "المأساة التي كسرت قلب القانوني!",
          "theme": "crimson",
          "pos": [540, 360]
        },
        {
          "start": 28.0,
          "end": 32.0,
          "word": "شاهد القصة الكاملة في الأسفل!",
          "theme": "emerald",
          "pos": [540, 360]
        }
      ]
    }
  ]
}


MANIFEST_SHORT_03 = {
  "section_id": "short_03",
  "title": "الشورت 3: سجن القفص الذهبي للأمراء",
  "total_duration": 50.89,
  "fps": 30,
  "resolution": [1080, 1920],
  "ground_y": 1520,
  "theme": {"name": "eye_comfort_paper"},
  "enable_sfx": True,
  "scenes": [
    {
      "id": "scene_01",
      "start": 0.0,
      "end": 9.5,
      "camera": {"zoom_start": 1.0, "zoom_end": 1.04, "duration": 9.5},
      "elements": [
        {
          "asset_key": "01_palace_lock_kafes",
          "start": 0.0,
          "end": 4.8,
          "pos": [540, 1020],
          "target_size": 540,
          "entrance": "pop_bounce",
          "exit": "shrink_out"
        },
        {
          "asset_key": "04_princes_locked_room",
          "start": 3.5,
          "end": 9.4,
          "pos": [540, 1020],
          "target_size": 580,
          "entrance": "card_stack",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 6.5, "duration": 0.45, "intensity": 18.0}]
        },
        {
          "asset_key": "09_heavy_door_guards",
          "start": 5.5,
          "end": 9.4,
          "pos": [540, 1400],
          "target_size": 440,
          "entrance": "slide_up",
          "exit": "shrink_out"
        }
      ],
      "words": [
        {
          "start": 0.5,
          "end": 3.5,
          "word": "وش هو نظام القفص الذهبي؟",
          "theme": "amber",
          "pos": [540, 360]
        },
        {
          "start": 4.0,
          "end": 9.0,
          "word": "حبس مؤبد للأمراء داخل القصر!",
          "theme": "crimson",
          "pos": [540, 360]
        }
      ]
    },
    {
      "id": "scene_02",
      "start": 9.5,
      "end": 24.8,
      "camera": {"zoom_start": 1.0, "zoom_end": 1.05, "duration": 15.3},
      "elements": [
        {
          "asset_key": "06_forbidden_street",
          "start": 9.5,
          "end": 15.8,
          "pos": [540, 950],
          "target_size": 500,
          "entrance": "draw_stroke",
          "exit": "shrink_out"
        },
        {
          "asset_key": "08_imprisoned_prince_years",
          "start": 12.0,
          "end": 17.0,
          "pos": [540, 1380],
          "target_size": 420,
          "entrance": "pop_bounce",
          "exit": "shrink_out"
        },
        {
          "asset_key": "02_terrified_prince_choice",
          "start": 16.5,
          "end": 24.6,
          "pos": [540, 1050],
          "target_size": 620,
          "entrance": "whip_motion",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 20.0, "duration": 0.45, "intensity": 20.0}]
        }
      ],
      "words": [
        {
          "start": 10.5,
          "end": 15.5,
          "word": "عزلة تامة وخدم صم وبكم!",
          "theme": "amber",
          "pos": [540, 360]
        },
        {
          "start": 17.0,
          "end": 24.0,
          "word": "رعب يومي: ذبح أم خلافة؟!",
          "theme": "crimson",
          "pos": [540, 360]
        }
      ]
    },
    {
      "id": "scene_03",
      "start": 24.8,
      "end": 43.2,
      "camera": {"zoom_start": 1.0, "zoom_end": 1.05, "duration": 18.4},
      "elements": [
        {
          "asset_key": "14_wall_tally_40_years",
          "start": 24.8,
          "end": 31.8,
          "pos": [540, 1020],
          "target_size": 520,
          "entrance": "pop_bounce",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 28.0, "duration": 0.45, "intensity": 18.0}]
        },
        {
          "asset_key": "17_prince_stepping_into_light",
          "start": 29.0,
          "end": 35.8,
          "pos": [340, 1020],
          "target_size": 460,
          "entrance": "whip_motion",
          "exit": "shrink_out"
        },
        {
          "asset_key": "20_naive_prince_map_3continents",
          "start": 31.0,
          "end": 35.8,
          "pos": [740, 1020],
          "target_size": 460,
          "entrance": "elastic_overshoot",
          "exit": "shrink_out"
        },
        {
          "asset_key": "13_mad_sultan_panic_throne",
          "start": 35.5,
          "end": 42.8,
          "pos": [540, 1020],
          "target_size": 580,
          "entrance": "pop_bounce",
          "exit": "shrink_out",
          "effects": [{"type": "border_flash", "color": "red", "time": 39.0}],
          "light_sweeps": [{"time": 38.5, "duration": 0.45, "intensity": 20.0}]
        },
        {
          "asset_key": "15_broken_brain_breakdown",
          "start": 38.5,
          "end": 42.8,
          "pos": [540, 1420],
          "target_size": 420,
          "entrance": "squash_drop",
          "exit": "shrink_out"
        }
      ],
      "words": [
        {
          "start": 26.0,
          "end": 32.5,
          "word": "40 سنة في غرفة ثم حكم 3 قارات!",
          "theme": "amber",
          "pos": [540, 360]
        },
        {
          "start": 36.5,
          "end": 42.5,
          "word": "نوبات هلع وعزلة تامة عن الواقع!",
          "theme": "crimson",
          "pos": [540, 360]
        }
      ]
    },
    {
      "id": "scene_04",
      "start": 43.2,
      "end": 50.89,
      "camera": {"zoom_start": 1.0, "zoom_end": 1.04, "duration": 7.69},
      "elements": [
        {
          "asset_key": "01_master_roster_8sultans",
          "start": 43.2,
          "end": 50.7,
          "pos": [540, 950],
          "target_size": 640,
          "entrance": "pop_bounce",
          "exit": "shrink_out",
          "light_sweeps": [{"time": 47.0, "duration": 0.45, "intensity": 20.0}]
        },
        {
          "asset_key": "11_two_video_screens_clicking",
          "start": 45.5,
          "end": 50.7,
          "pos": [540, 1420],
          "target_size": 420,
          "entrance": "whip_motion",
          "exit": "shrink_out"
        }
      ],
      "words": [
        {
          "start": 43.5,
          "end": 46.5,
          "word": "قرار غيّر مصير إمبراطورية كاملة!",
          "theme": "royal",
          "pos": [540, 360]
        },
        {
          "start": 47.0,
          "end": 50.5,
          "word": "شاهد الوثائقي الكامل في الأسفل!",
          "theme": "emerald",
          "pos": [540, 360]
        }
      ]
    }
  ]
}


def build_and_render_short(short_id: str, manifest_data: dict):
    from core_engine.effectcraft_director import EffectCraftMotionEngine
    
    short_dir = SHORTS_DIR / short_id
    manifest_path = short_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Wrote manifest for {short_id} -> {manifest_path}")

    # Output master MP4 path
    out_mp4 = EXPORTS_DIR / f"{short_id}_master.mp4"
    print(f"[*] Rendering {short_id} via EffectCraft to {out_mp4}...")
    
    engine = EffectCraftMotionEngine(
        section_dir=short_dir,
        output_dir=EXPORTS_DIR
    )
    rendered_path = engine.render(out_mp4=out_mp4)
    print(f"✅ Finished rendering: {rendered_path} (Size: {out_mp4.stat().st_size / 1024 / 1024:.2f} MB)")
    return rendered_path


def main():
    print("=" * 70)
    print("🎬 RENDERING ALL 3 YOUTUBE SHORTS (1080x1920 VERTICAL)")
    print("=" * 70)

    # 1. Short 1
    build_and_render_short("short_01", MANIFEST_SHORT_01)

    # 2. Short 2
    build_and_render_short("short_02", MANIFEST_SHORT_02)

    # 3. Short 3
    build_and_render_short("short_03", MANIFEST_SHORT_03)

    print("\n🎉 ALL 3 SHORTS RENDERED SUCCESSFULLY!")


if __name__ == "__main__":
    main()

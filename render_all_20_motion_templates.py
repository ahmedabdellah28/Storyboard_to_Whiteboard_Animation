"""Master Generator & Renderer for All 20 Motion Graphics Templates.
References: motion_types.md

Renders 20 isolated videos and preview comparison frames in exports/motion_templates/
"""

import sys
import os
import json
import time
import math
import subprocess
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core_engine.motion_templates import MotionTemplates, blend_patch
from core_engine.universal_staged_director_v2 import create_staged_popup_card_v2, create_traveling_dot, ease

ASSETS_DIR = ROOT_DIR / "sections" / "section_08" / "assets"
AUDIO_PATH = ROOT_DIR / "sections" / "section_08" / "voice" / "section_08.wav"
OUTPUT_DIR = ROOT_DIR / "exports" / "motion_templates"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PREVIEWS_DIR = OUTPUT_DIR / "previews"
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

# Load raw PNG assets
LOADED_ASSETS = {}
for p in ASSETS_DIR.glob("*.png"):
    if p.stem not in ("contact_sheet", "connectivity_and_separation_map"):
        LOADED_ASSETS[p.stem] = np.array(Image.open(p).convert("RGBA"))

TEMPLATES_CATALOG = [
    {
        "id": "01_morph",
        "num": 1,
        "name_en": "Morph Transition",
        "name_ar": "التحول البصري المباشر",
        "render_func": MotionTemplates.render_01_morph,
        "asset_a": "r1_05_genetic_clone_100_percent",
        "asset_b": "r2_03_counter_40k_trees_one_organism",
        "text_a": "نبتة منفردة؟",
        "text_b": "غابة كاملة ككائن واحد!",
        "theme_a": "teal",
        "theme_b": "forest"
    },
    {
        "id": "02_match_cut",
        "num": 2,
        "name_en": "Match Cut Transition",
        "name_ar": "الانتقال بالتطابق الحركي",
        "render_func": MotionTemplates.render_02_match_cut,
        "asset_a": "r1_06_tree_sprout_symbol",
        "asset_b": "r4_04_immortality_infinity_victory",
        "text_a": "شيفرة الوراثة الدائرية",
        "text_b": "خلود جيني أبدي!",
        "theme_a": "cyan",
        "theme_b": "teal"
    },
    {
        "id": "03_camera_push_pull",
        "num": 3,
        "name_en": "Camera Push Pull",
        "name_ar": "الاقتراب والابتعاد السينمائي",
        "render_func": MotionTemplates.render_03_camera_push_pull,
        "asset_a": "r2_01_stickman_walking_aspen_forest",
        "asset_b": "r2_02_massive_interconnected_root_system",
        "text_a": "ما تراه على السطح...",
        "text_b": "...العملاق الخفي بالأسفل!",
        "theme_a": "forest",
        "theme_b": "amber"
    },
    {
        "id": "04_directional_flow",
        "num": 4,
        "name_en": "Directional Flow",
        "name_ar": "التدفق الحركي المستمر",
        "render_func": MotionTemplates.render_04_directional_flow,
        "asset_a": "r1_04_solution_cloning_dna",
        "asset_b": "r1_07_utah_pando_forest_map",
        "text_a": "فشل التكاثر التقليدي",
        "text_b": "ظهور أعجوبة يوتا!",
        "theme_a": "crimson",
        "theme_b": "forest"
    },
    {
        "id": "05_mask_reveal_wipe",
        "num": 5,
        "name_en": "Mask Reveal Wipe",
        "name_ar": "الكشف بالماسك المقصوص",
        "render_func": MotionTemplates.render_05_mask_reveal_wipe,
        "asset_a": "r1_03_headache_useless_question",
        "asset_b": "r3_01_weight_gauge_6000_tons",
        "text_a": "لغز معقد وحائر؟",
        "text_b": "الوزن: 6000 طن صلب!",
        "theme_a": "amber",
        "theme_b": "teal"
    },
    {
        "id": "06_object_push",
        "num": 6,
        "name_en": "Object Push Transition",
        "name_ar": "الدفع الفيزيائي للعنصر",
        "render_func": MotionTemplates.render_06_object_push,
        "asset_a": "r1_02_rejection_seeds_insects",
        "asset_b": "r1_01_final_boss_gaming_banner",
        "text_a": "استبعاد المنافسين",
        "text_b": "دخول الزعيم الأخير!",
        "theme_a": "crimson",
        "theme_b": "crimson"
    },
    {
        "id": "07_whip_motion",
        "num": 7,
        "name_en": "Whip Motion",
        "name_ar": "الحركة السريعة الخاطفة",
        "render_func": MotionTemplates.render_07_whip_motion,
        "asset_a": "r3_02_ancient_age_80k_years",
        "asset_b": "r3_03_ice_age_mammoth_extinction",
        "text_a": "قبل 80 ألف عام...",
        "text_b": "...عبر العصر الجليدي!",
        "theme_a": "amber",
        "theme_b": "cyan"
    },
    {
        "id": "08_scale_punch",
        "num": 8,
        "name_en": "Scale Punch",
        "name_ar": "النبض التكبيري التوكيدي",
        "render_func": MotionTemplates.render_08_scale_punch,
        "asset_a": "r1_01_final_boss_gaming_banner",
        "asset_b": "r4_04_immortality_infinity_victory",
        "text_a": "المواجهة الكبرى",
        "text_b": "انتصار بيولوجي كاسح!",
        "theme_a": "crimson",
        "theme_b": "forest"
    },
    {
        "id": "09_orbit_arc",
        "num": 9,
        "name_en": "Orbit Arc Motion",
        "name_ar": "المسار القوسي المنحني",
        "render_func": MotionTemplates.render_09_orbit_arc,
        "asset_a": "r4_03_ignoring_insects_birds",
        "asset_b": "r4_02_stickman_serene_golden_canopy",
        "text_a": "أجيال تعبر وترحل...",
        "text_b": "...وهدوء أبدي مستقر!",
        "theme_a": "teal",
        "theme_b": "forest"
    },
    {
        "id": "10_parallax_depth",
        "num": 10,
        "name_en": "Parallax Depth",
        "name_ar": "العمق الحركي متعدد الطبقات",
        "render_func": MotionTemplates.render_10_parallax_depth,
        "asset_a": "r2_02_massive_interconnected_root_system",
        "asset_b": "r2_01_stickman_walking_aspen_forest",
        "text_a": "عمق الجذور في الخلفية",
        "text_b": "الراوي في صدارة المشهد",
        "theme_a": "amber",
        "theme_b": "forest"
    },
    {
        "id": "11_kinetic_typography",
        "num": 11,
        "name_en": "Kinetic Typography",
        "name_ar": "حركية النص والتحول البصري",
        "render_func": MotionTemplates.render_11_kinetic_typography,
        "asset_a": "r1_03_headache_useless_question",
        "asset_b": "r1_06_tree_sprout_symbol",
        "text_a": "ما هو الحل الحاسم؟",
        "text_b": "شريط الـ DNA المعجزة!",
        "theme_a": "amber",
        "theme_b": "cyan"
    },
    {
        "id": "12_shape_transform",
        "num": 12,
        "name_en": "Shape Transform",
        "name_ar": "التحول الهندسي للأشكال",
        "render_func": MotionTemplates.render_12_shape_transform,
        "asset_a": "r1_06_tree_sprout_symbol",
        "asset_b": "r3_01_weight_gauge_6000_tons",
        "text_a": "وحدة بناء صغيرة",
        "text_b": "كتلة صناعية جبارة!",
        "theme_a": "cyan",
        "theme_b": "teal"
    },
    {
        "id": "13_line_path",
        "num": 13,
        "name_en": "Line Path Transition",
        "name_ar": "المسار المرسوم الموجه للعين",
        "render_func": MotionTemplates.render_13_line_path,
        "asset_a": "r1_07_utah_pando_forest_map",
        "asset_b": "r2_02_massive_interconnected_root_system",
        "text_a": "نقطة البداية على الخريطة",
        "text_b": "امتداد الجذور العملاقة",
        "theme_a": "forest",
        "theme_b": "amber"
    },
    {
        "id": "14_liquid_organic",
        "num": 14,
        "name_en": "Liquid Organic Flow",
        "name_ar": "التدفق العضوي السائل",
        "render_func": MotionTemplates.render_14_liquid_organic,
        "asset_a": "r4_01_sleeping_underground_leviathan",
        "asset_b": "r4_04_immortality_infinity_victory",
        "text_a": "تدفق نبضات الكائن",
        "text_b": "طاقة خلود متجددة!",
        "theme_a": "forest",
        "theme_b": "teal"
    },
    {
        "id": "15_card_stack",
        "num": 15,
        "name_en": "Card Stack Transition",
        "name_ar": "انتقال تعاقب البطاقات",
        "render_func": MotionTemplates.render_15_card_stack,
        "asset_a": "r3_01_weight_gauge_6000_tons",
        "asset_b": "r3_02_ancient_age_80k_years",
        "text_a": "الرقم القياسي: 6000 طن",
        "text_b": "الرقم القياسي: 80,000 سنة!",
        "theme_a": "teal",
        "theme_b": "amber"
    },
    {
        "id": "16_split_screen",
        "num": 16,
        "name_en": "Split Screen Transition",
        "name_ar": "انقسام الشاشة والمقارنة",
        "render_func": MotionTemplates.render_16_split_screen,
        "asset_a": "r1_04_solution_cloning_dna",
        "asset_b": "r2_03_counter_40k_trees_one_organism",
        "text_a": "الموت بالجفاف",
        "text_b": "الخلود بالاستنساخ!",
        "theme_a": "crimson",
        "theme_b": "forest"
    },
    {
        "id": "17_blur_speed",
        "num": 17,
        "name_en": "Blur Speed Transition",
        "name_ar": "السرعة الضبابية مع التركيز",
        "render_func": MotionTemplates.render_17_blur_speed,
        "asset_a": "r3_03_ice_age_mammoth_extinction",
        "asset_b": "r4_02_stickman_serene_golden_canopy",
        "text_a": "عصور انقراض سريعة",
        "text_b": "ثبات باهر واستقرار!",
        "theme_a": "cyan",
        "theme_b": "forest"
    },
    {
        "id": "18_trail_echo",
        "num": 18,
        "name_en": "Trail Echo Transition",
        "name_ar": "أثر الحركة التتابعي (Echo)",
        "render_func": MotionTemplates.render_18_trail_echo,
        "asset_a": "r1_06_tree_sprout_symbol",
        "asset_b": "r2_03_counter_40k_trees_one_organism",
        "text_a": "تكرار الشيفرة الوراثية",
        "text_b": "40 ألف نسخة حية مطابقة!",
        "theme_a": "cyan",
        "theme_b": "forest"
    },
    {
        "id": "19_rotation_spin",
        "num": 19,
        "name_en": "Rotation Spin Reveal",
        "name_ar": "الدوران المحوري ثلاثي الأبعاد",
        "render_func": MotionTemplates.render_19_rotation_spin,
        "asset_a": "r1_01_final_boss_gaming_banner",
        "asset_b": "r4_04_immortality_infinity_victory",
        "text_a": "وجه التحدي الصعب",
        "text_b": "وجه النصر المؤكد!",
        "theme_a": "crimson",
        "theme_b": "teal"
    },
    {
        "id": "20_elastic_overshoot",
        "num": 20,
        "name_en": "Elastic Overshoot",
        "name_ar": "الارتداد الفيزيائي المرن",
        "render_func": MotionTemplates.render_20_elastic_overshoot,
        "asset_a": "r1_05_genetic_clone_100_percent",
        "asset_b": "r1_01_final_boss_gaming_banner",
        "text_a": "ترقب في صمت...",
        "text_b": "هبوط الزعيم الأخير بقوة!",
        "theme_a": "teal",
        "theme_b": "crimson"
    }
]

def render_template_video(cfg: dict) -> str:
    tid = cfg["id"]
    print(f"🎬 Rendering Template #{cfg['num']:02d}: {cfg['name_en']} ({cfg['name_ar']})...", flush=True)

    raw_a = LOADED_ASSETS[cfg["asset_a"]]
    raw_b = LOADED_ASSETS[cfg["asset_b"]]

    # Timeline: 5.0 seconds total (150 frames @ 30fps)
    # 0.0 - 1.8s: Beat 1 (Element A + Card A)
    # 1.8 - 2.5s: Motion Transition Window (0.70s pure focus)
    # 2.5 - 5.0s: Beat 2 (Element B + Card B)
    total_dur = 5.0
    fps = 30
    total_frames = int(total_dur * fps)
    w_res, h_res = 1920, 1080
    center_pos = (520, 600)
    card_pos = (1220, 540)
    trans_st = 1.8
    trans_en = 2.5
    trans_dur = trans_en - trans_st

    out_mp4 = OUTPUT_DIR / f"{cfg['num']:02d}_{cfg['name_en'].lower().replace(' ', '_')}.mp4"
    temp_v = OUTPUT_DIR / f"temp_{cfg['num']:02d}.mp4"

    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-s", f"{w_res}x{h_res}",
           "-pix_fmt", "bgr24", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "fast",
           "-crf", "18", "-pix_fmt", "yuv420p", str(temp_v)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    preview_frame = None

    for f in range(total_frames):
        t = f / float(fps)

        # 1. Background studio whiteboard
        frame = np.full((h_res, w_res, 3), 255, dtype=np.uint8)
        # Stage baseline at Y = 840
        cv2.line(frame, (80, 840), (1840, 840), (225, 230, 235), 2, cv2.LINE_AA)

        # 2. Transition Layer
        if t < trans_st:
            # Beat 1: Pure Element A sitting grounded
            trans_patch = cfg["render_func"](raw_a, raw_b, 0.0, size=480)
        elif t > trans_en:
            # Beat 2: Pure Element B sitting grounded
            trans_patch = cfg["render_func"](raw_a, raw_b, 1.0, size=480)
        else:
            # Transition Window: Procedural interpolation
            p_trans = (t - trans_st) / trans_dur
            trans_patch = cfg["render_func"](raw_a, raw_b, p_trans, size=480)

        # Save preview at midpoint (t = 2.15s)
        if preview_frame is None and t >= 2.15:
            preview_frame = frame.copy()

        # Blend transition patch onto frame centered at center_pos
        ph, pw = trans_patch.shape[:2]
        bx = center_pos[0] - pw // 2
        by = center_pos[1] - ph // 2
        blend_patch(frame, trans_patch, bx, by)

        # 3. Text Card Timing
        # Card A (0.3s - 1.6s)
        if 0.3 <= t <= 1.6:
            p_card = (t - 0.3) / 1.3
            card_img = create_staged_popup_card_v2(cfg["text_a"], theme_name=cfg["theme_a"], bloom_p=1.0, write_p=min(1.0, p_card * 2.5))
            ch, cw = card_img.shape[:2]
            blend_patch(frame, card_img, card_pos[0] - cw // 2, card_pos[1] - ch // 2)

        # Card B (2.8s - 4.8s)
        elif 2.8 <= t <= 4.8:
            p_card = (t - 2.8) / 2.0
            # Dot travel (2.8 - 3.08)
            if t < 3.08:
                dot_p = (t - 2.8) / 0.28
                dot_x = int(center_pos[0] + (card_pos[0] - center_pos[0]) * ease(dot_p, "out_cubic"))
                dot_y = int(center_pos[1] - 80 * math.sin(dot_p * math.pi) + (card_pos[1] - center_pos[1]) * dot_p)
                dot = create_traveling_dot(theme_name=cfg["theme_b"])
                blend_patch(frame, dot, dot_x - dot.shape[1] // 2, dot_y - dot.shape[0] // 2)
            else:
                write_p = min(1.0, (t - 3.24) / 0.30)
                card_img = create_staged_popup_card_v2(cfg["text_b"], theme_name=cfg["theme_b"], bloom_p=1.0, write_p=write_p)
                ch, cw = card_img.shape[:2]
                blend_patch(frame, card_img, card_pos[0] - cw // 2, card_pos[1] - ch // 2)

        proc.stdin.write(frame.tobytes())

        if preview_frame is not None and f == int(2.15 * fps):
            preview_frame = frame.copy()

    proc.stdin.close()
    proc.wait()

    # Save preview image
    if preview_frame is not None:
        cv2.imwrite(str(PREVIEWS_DIR / f"{cfg['num']:02d}_{cfg['name_en'].lower().replace(' ', '_')}.png"), preview_frame)

    # Mux audio snippet
    mux = ["ffmpeg", "-y", "-i", str(temp_v), "-i", str(AUDIO_PATH), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out_mp4)]
    subprocess.run(mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if temp_v.exists():
        temp_v.unlink()

    print(f"  ✅ Exported: {out_mp4.name}", flush=True)
    return str(out_mp4)

def run_all():
    print(f"🚀 Starting Master Generation for all 20 Motion Transition Templates...")
    t0 = time.time()
    for cfg in TEMPLATES_CATALOG:
        render_template_video(cfg)
    print(f"\n🎉 ALL 20 MOTION TEMPLATES EXPORTED SUCCESSFULLY in {time.time() - t0:.1f}s!")
    print(f"📂 Output directory: {OUTPUT_DIR}")

if __name__ == "__main__":
    run_all()

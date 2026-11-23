#!/usr/bin/env python3
"""
Dedicated Production Pipeline for Ottoman Sultans YouTube Shorts (Vertical 9:16, 1080x1920).
Zero-BGM Policy, high-energy Saudi Youth voiceover (Fenrir), 
organic whitespace contours, and EffectCraft hardware acceleration.
"""

import os
import sys
import core_engine.dns_patch
import json
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ROOT_DIR / "projects" / "ottoman_sultans"
SHORTS_DIR = PROJECT_DIR / "shorts"
EXPORTS_DIR = PROJECT_DIR / "exports"

SHORTS_CONFIG = {
    "short_01": {
        "title_ar": "لماذا كان وزراء هذا السلطان يلبسون أكفانهم قبل الدخول عليه؟ 😱⚔️",
        "description": "قصة السلطان سليم الأول (القاطع) الذي ضاعف مساحة الدولة 3 مرات وأعدم 7 من وزرائه حتى ظهرت أشهر دعوة في إسطنبول! #سليم_الأول #الدولة_العثمانية #تاريخ #قصص #شورتس",
        "script": """[dramatic] بس الوجه المرعب لسليم كان داخل قصره؛ كان شخصية شكاكة وغضوبة لأقصى درجة، وخلال فترة حكمه القصيرة، أعدم سبعة من كبار وزرائه! [curiosity] كان الوزير يدخل عنده في الصباح وما يدري هل بيطلع لبيته ولا للمقصلة، [anticipation] لدرجة إن وزراء الدولة العثمانية في عصره كانوا يكتبون وصاياهم ويلبسون أكفانهم تحت ملابسهم الرسمية قبل ما يدخلون عليه! [dramatic] وصارت أشهر دعوة وشتيمة في إسطنبول بين الناس لما يدعون على شخص يكرهونه، يقوله: جعلك الله وزيراً عند السلطان سليم! [curiosity] وفاة سليم نفسها كانت مفاجأة غريبة.. وفي الفيديو الكامل تحت، شرحنا أغرب 8 سلاطين ونهاياتهم الصادمة! اضغط على الرابط أسفل الشاشة.""",
        "clean_text": "بس الوجه المرعب لسليم كان داخل قصره؛ كان شخصية شكاكة وغضوبة لأقصى درجة، وخلال فترة حكمه القصيرة، أعدم سبعة من كبار وزرائه! كان الوزير يدخل عنده في الصباح وما يدري هل بيطلع لبيته ولا للمقصلة، لدرجة إن وزراء الدولة العثمانية في عصره كانوا يكتبون وصاياهم ويلبسون أكفانهم تحت ملابسهم الرسمية قبل ما يدخلون عليه! وصارت أشهر دعوة وشتيمة في إسطنبول بين الناس لما يدعون على شخص يكرهونه، يقوله: جعلك الله وزيراً عند السلطان سليم! وفاة سليم نفسها كانت مفاجأة غريبة.. وفي الفيديو الكامل تحت، شرحنا أغرب 8 سلاطين ونهاياتهم الصادمة! اضغط على الرابط أسفل الشاشة.",
        "source_sections": ["section_03", "section_09"],
        "assets_to_copy": {
            "section_03": [
                "04_selim_portrait.png",
                "10_selim_angry_point.png",
                "12_bloody_scimitar.png",
                "11_seven_severed_turbans.png",
                "13_execution_7_viziers.png",
                "03_vizier_shroud.png",
                "06_vizier_will.png",
                "17_vizier_farewell_family.png",
                "18_istanbul_citizens_curse.png",
                "21_famous_curse_scroll.png",
                "15_malignant_boil_back.png"
            ],
            "section_09": [
                "01_master_roster_8sultans.png",
                "09_video_player_next.png",
                "11_two_video_screens_clicking.png"
            ]
        }
    },
    "short_02": {
        "title_ar": "كيف حكم سلطان عثماني جيشه لمدة 48 يوماً وهو ميت؟ 👑🤫",
        "description": "الخدعة العبقرية التي نفذها الوزير محمد باشا لإخفاء وفاة السلطان سليمان القانوني باستخدام شبيه يلوح للجيش! #سليمان_القانوني #تاريخ #معلومات #وثائقي #شورتس",
        "script": """[anticipation] وفي آخر حملة له وعمره فوق السبعين، مات في خيمته قبل ما تسقط القلعة بيومين، [dramatic] فخاف وزيره الذكي محمد باشا إن الجيش ينهار لو عرفوا، فأخفى جثة السلطان ثمانية وأربعين يوماً كاملة! [curiosity] كان يزور توقيعه، ويرسل أوامر باسمه، ولما شك الجنود، [anticipation] لبّسوا شخص يشبه السلطان ملابسه وخلوه يلوح للجيش من بعيد في عربة مظلمة لين رجعوا للعاصمة بسلام! [dramatic] وقبل موته عاش سليمان مأساة قتلت قلبه داخل خيمته.. شاهد القصة الكاملة للسلاطين الثمانية من الرابط أسفل الفيديو الآن!""",
        "clean_text": "وفي آخر حملة له وعمره فوق السبعين، مات في خيمته قبل ما تسقط القلعة بيومين، فخاف وزيره الذكي محمد باشا إن الجيش ينهار لو عرفوا، فأخفى جثة السلطان ثمانية وأربعين يوماً كاملة! كان يزور توقيعه، ويرسل أوامر باسمه، ولما شك الجنود، لبّسوا شخص يشبه السلطان ملابسه وخلوه يلوح للجيش من بعيد في عربة مظلمة لين رجعوا للعاصمة بسلام! وقبل موته عاش سليمان مأساة قتلت قلبه داخل خيمته.. شاهد القصة الكاملة للسلاطين الثمانية من الرابط أسفل الفيديو الآن!",
        "source_sections": ["section_04", "section_09"],
        "assets_to_copy": {
            "section_04": [
                "03_suleiman_grief_old.png",
                "04_suleiman_magnificent.png",
                "09_suleiman_death_bed_72.png",
                "20_calendar_48_days_hidden.png",
                "15_forging_tughra_signature.png",
                "16_suspicious_soldiers.png",
                "17_dressing_lookalike.png",
                "18_lookalike_waving_carriage.png",
                "19_return_to_istanbul.png",
                "14_broken_heart_minarets.png"
            ],
            "section_09": [
                "01_master_roster_8sultans.png",
                "09_video_player_next.png",
                "11_two_video_screens_clicking.png"
            ]
        }
    },
    "short_03": {
        "title_ar": "الغرفة السرية التي دمرت عقول أمراء الدولة العثمانية لـ 40 سنة! 🔒🏰",
        "description": "كيف تحول قرار إلغاء قتل الإخوة إلى نظام \"القفص الذهبي\" داخل قصر طوب قابي، وكيف أثر على عقول السلاطين؟ #القفص_الذهبي #الدولة_العثمانية #تاريخ #شورتس",
        "script": """[curiosity] وش هو القفص؟ جناح معزول ومقفل داخل القصر، يُحبس فيه كل الأمراء إخوة السلطان وأولادهم طول حياتهم تحت حراسة مشددة! [dramatic] ممنوع يطلعون للشارع، ممنوع يكلمون أحد من برا، وممنوع حتى يجيبون أولاد، والخدم اللي عندهم صُمّ وبُكْم، [anticipation] ويعيش الأمير في رعب يومي ينتظر: هل الباب بينفتح اليوم عشان يذبحوني، ولا عشان يقولون لي السلطان مات وأنت صرت الخليفة؟ [curiosity] تخيل أمير مثل إبراهيم الأول أو سليمان الثاني يقعد محبوس في غرفة أربعين سنة متواصلة، وفجأة يطلعونه ويحطونه حاكم لإمبراطورية تحكم ثلاث قارات! [dramatic] النتيجة كانت إن أغلب السلاطين المتأخرين طلعوا وهم يعانون من نوبات هلع وانهيار عصبي وعزلة تامة عن الواقع. [anticipation] هذا القرار البسيط غير مصير إمبراطورية كاملة.. شاهد شرح جميع السلاطين الثمانية في الحلقة الكاملة من الرابط بالأسفل!""",
        "clean_text": "وش هو القفص؟ جناح معزول ومقفل داخل القصر، يُحبس فيه كل الأمراء إخوة السلطان وأولادهم طول حياتهم تحت حراسة مشددة! ممنوع يطلعون للشارع، ممنوع يكلمون أحد من برا، وممنوع حتى يجيبون أولاد، والخدم اللي عندهم صُمّ وبُكْم، ويعيش الأمير في رعب يومي ينتظر: هل الباب بينفتح اليوم عشان يذبحوني، ولا عشان يقولون لي السلطان مات وأنت صرت الخليفة؟ تخيل أمير مثل إبراهيم الأول أو سليمان الثاني يقعد محبوس في غرفة أربعين سنة متواصلة، وفجأة يطلعونه ويحطونه حاكم لإمبراطورية تحكم ثلاث قارات! النتيجة كانت إن أغلب السلاطين المتأخرين طلعوا وهم يعانون من نوبات هلع وانهيار عصبي وعزلة تامة عن الواقع. هذا القرار البسيط غير مصير إمبراطورية كاملة.. شاهد شرح جميع السلاطين الثمانية في الحلقة الكاملة من الرابط بالأسفل!",
        "source_sections": ["section_05", "section_09"],
        "assets_to_copy": {
            "section_05": [
                "01_palace_lock_kafes.png",
                "04_princes_locked_room.png",
                "09_heavy_door_guards.png",
                "06_forbidden_street.png",
                "08_imprisoned_prince_years.png",
                "02_terrified_prince_choice.png",
                "14_wall_tally_40_years.png",
                "17_prince_stepping_into_light.png",
                "20_naive_prince_map_3continents.png",
                "13_mad_sultan_panic_throne.png",
                "15_broken_brain_breakdown.png"
            ],
            "section_09": [
                "01_master_roster_8sultans.png",
                "09_video_player_next.png",
                "11_two_video_screens_clicking.png"
            ]
        }
    }
}


def prepare_short_folders(short_id: str) -> Dict[str, Path]:
    s_dir = SHORTS_DIR / short_id
    v_dir = s_dir / "voice"
    t_dir = s_dir / "timing"
    a_dir = s_dir / "assets"
    
    for d in [s_dir, v_dir, t_dir, a_dir]:
        d.mkdir(parents=True, exist_ok=True)
        
    cfg = SHORTS_CONFIG[short_id]
    
    # Copy assets
    for sec_name, asset_list in cfg["assets_to_copy"].items():
        sec_assets_dir = PROJECT_DIR / "sections" / sec_name / "assets"
        for a_file in asset_list:
            src = sec_assets_dir / a_file
            dst = a_dir / a_file
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
                
    return {
        "short_dir": s_dir,
        "voice_dir": v_dir,
        "timing_dir": t_dir,
        "assets_dir": a_dir,
        "wav": v_dir / f"{short_id}.wav",
        "timing_json": t_dir / f"{short_id}_timing_master.json",
        "manifest": s_dir / "manifest.json"
    }


def generate_short_voice(short_id: str, paths: Dict[str, Path]) -> float:
    from voice_studio.engine import VoiceStudioEngine
    cfg = SHORTS_CONFIG[short_id]
    
    if paths["wav"].exists() and paths["wav"].stat().st_size > 5000:
        print(f"[*] Voice already generated: {paths['wav']}")
        import wave
        with wave.open(str(paths["wav"]), "rb") as wf:
            dur = wf.getnframes() / float(wf.getframerate())
        return dur

    print(f"[*] Generating Gemini TTS voice for {short_id}...")
    v_engine = VoiceStudioEngine()
    res = v_engine.generate_segmented_speech(
        transcript=cfg["script"],
        output_wav_path=str(paths["wav"]),
        voice_name="Fenrir",
        profile_key="SAUDI_YOUTH_CREATOR",
        director_note_key="HIGH_ENERGY_YOUTUBE",
        temperature=0.8,
        speed=1.0
    )
    print(f"[+] Voice generated: {res['duration']:.2f}s ({res['sample_rate']} Hz)")
    return res["duration"]


def generate_short_timing(short_id: str, paths: Dict[str, Path]) -> List[Dict[str, Any]]:
    from section_timing.transcription.faster_whisper_engine import FasterWhisperEngine
    from section_timing.transcription.whisper_parser import WhisperParser
    from section_timing.alignment.script_audio_aligner import ScriptAudioAligner
    
    cfg = SHORTS_CONFIG[short_id]
    whisper_cache = paths["timing_dir"] / "whisper.json"
    
    print(f"[*] Running Faster-Whisper alignment for {short_id}...")
    engine = FasterWhisperEngine(model_size="small", language="ar")
    w_out = engine.transcribe(audio_path=paths["wav"], cache_file=whisper_cache, force=False)
    
    raw_words = WhisperParser.extract_word_items(w_out)
    aligner = ScriptAudioAligner()
    aligned_words = aligner.align(cfg["clean_text"], raw_words)
    
    clean_words = [
        {"word": item.text, "start": round(item.start, 3), "end": round(item.end, 3), "duration": round(item.duration, 3)}
        for item in aligned_words
    ]
    
    with open(paths["timing_json"], "w", encoding="utf-8") as f:
        json.dump({
            "section_id": short_id,
            "audio_path": str(paths["wav"]),
            "duration": round(w_out.duration, 3),
            "words": clean_words
        }, f, indent=2, ensure_ascii=False)
        
    print(f"[+] Timing generated: {len(clean_words)} words aligned over {w_out.duration:.2f}s")
    return clean_words


if __name__ == "__main__":
    print("Shorts production helper loaded.")

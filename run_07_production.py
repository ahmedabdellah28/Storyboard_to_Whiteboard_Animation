"""
Section 07: Comfortable Rich (الطبقة السابعة: الغني المرتاح) - High-Impact Whiteboard Production Pipeline
Synchronized with Faster-Whisper ground truth, authentic Arabic handwriting title banner,
high-impact micro-zoning (12 zones, scale 3.4x-3.8x, CAM_ZOOM=0.68, FIXED_Y=800.0),
zero blank screens, ducked stereo master audio, and hardware-accelerated NVENC rendering.
"""
import os
import sys
import shutil

sys.stdout.reconfigure(encoding='utf-8')

from core.config.settings import PROJECT_ROOT
ROOT_DIR = str(PROJECT_ROOT)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.universal_section_pipeline import UniversalSectionPipeline

def run():
    sec_dir = os.path.join(ROOT_DIR, "sections", "07_comfortable_rich")
    
    # 35 verified assets mapped to exact Whisper word-level timestamps and 12 micro-zones
    custom_manifest = [
        # Zone 01: Title Banner + Waking up in quiet luxury house
        ("r0_00_title_banner", 0.00, 2.80, "الطبقة السابعة: الغني المرتاح", "zone_01", "outside_in_pen", 5),
        ("r1_01_waking_bed", 4.40, 7.50, "مليونير لكن حياته مو بالضرورة استعراض", "zone_01", "outside_in_pen", 5),
        ("r1_02_luxury_house", 7.60, 11.50, "تصحى في بيت هادي تملكه في حي مرغوب والرهن بسيط", "zone_01", "outside_in_pen", 5),

        # Zone 02: Smart Home & Home Office
        ("r1_03_smart_control", 11.80, 14.50, "الإضاءة والحرارة والأمان كلها تعمل بشكل ذكي", "zone_02", "outside_in_pen", 5),
        ("r1_04_home_office", 14.80, 17.00, "عندك مكتب منزلي", "zone_02", "slide_down", 4),
        ("r1_05_guest_bedroom", 17.10, 19.80, "غرفة ضيوف", "zone_02", "outside_in_pen", 5),

        # Zone 03: Yard, Housekeeper & Gardener (Buying Time)
        ("r1_06_yard_robot", 20.00, 22.00, "وحوش والحديقة لها شركة صيانة وروبوت", "zone_03", "outside_in_pen", 5),
        ("r1_07_housekeeper", 22.10, 23.50, "عاملة نظافة تجي كل أسبوع أو أسبوعين", "zone_03", "outside_in_pen", 5),
        ("r1_08_gardener", 23.60, 24.80, "أنت هنا تشتري وقتك وتفوض المهام", "zone_03", "slide_down", 4),

        # Zone 04: Diversified Portfolio
        ("r2_01_real_estate_wealth", 24.90, 26.60, "ثروتك موزعة بين قيمة البيت", "zone_04", "outside_in_pen", 5),
        ("r2_02_retirement_jar", 26.70, 28.30, "وحسابات التقاعد ومحفظة استثمارية", "zone_04", "outside_in_pen", 5),
        ("r2_03_portfolio_tablet", 28.40, 29.80, "محفظة استثمارية وعقار أو بزنس صغير", "zone_04", "slide_down", 4),
        ("r2_04_commercial_property", 29.90, 31.80, "عقار وبزنس واستثمارات مستقرة", "zone_04", "outside_in_pen", 5),

        # Zone 05: Emergency Fund, Insurance & Financial Automation
        ("r2_05_emergency_safe", 31.90, 33.30, "وعندك صندوق طوارئ كبير وتأمين قوي", "zone_05", "outside_in_pen", 5),
        ("r2_06_insurance_shield", 33.40, 34.80, "تأمين قوي وحماية مالية شاملة", "zone_05", "slide_down", 4),
        ("r2_07_accountant_advisor", 34.90, 37.20, "محاسب يضبط الضرائب ومستشار مالي وخطة واضحة", "zone_05", "outside_in_pen", 5),
        ("r2_08_monthly_transfer", 37.30, 39.00, "والفلوس نفسها تتحرك تلقائياً كل شهر جزء للاستثمار", "zone_05", "outside_in_pen", 5),

        # Zone 06: Luxury Paid Car & Instant Phone Replacement
        ("r3_01_luxury_suv", 39.10, 42.40, "السيارة فخمة وحديثة ومدفوعة أو عليها قرض صغير", "zone_06", "outside_in_pen", 5),
        ("r2_09_iphone_replacement", 42.50, 48.50, "جوالك انكسر تبدله نفس اليوم ما تمسك شيء خربان", "zone_06", "outside_in_pen", 5),

        # Zone 07: High-Level Work & Controlled Calendar
        ("r3_03_executive_meeting", 48.70, 54.00, "في الشغل أنت في مستوى أعلى تدير فريق أو عيادة أو شركتك", "zone_07", "outside_in_pen", 5),
        ("r3_02_private_jet", 54.20, 57.50, "وجدولك تتحكم فيه وتملك السيطرة على وقتك", "zone_07", "outside_in_pen", 5),

        # Zone 08: Real Vacation & Preventative Healthcare
        ("r3_04_beach_work", 57.60, 60.00, "تقدر تأخذ إجازة حقيقية ودخلك ما يختفي لو توقفت", "zone_08", "outside_in_pen", 5),
        ("r3_05_beach_vacation", 60.10, 62.00, "استمتاع حقيقي وإجازة مريحة", "zone_08", "slide_down", 4),
        ("r3_06_preventative_doctor", 62.10, 64.80, "الصحة وقائية فحوصات وأطباء متخصصون", "zone_08", "outside_in_pen", 5),
        ("r3_07_dental_checkup", 64.90, 67.40, "ولا تنتظر الألم عشان تبدأ تتحرك", "zone_08", "outside_in_pen", 5),

        # Zone 09: Easy Home Repair & Family Travel & Charity
        ("r3_08_plumber_repair", 67.50, 70.40, "توافق على إصلاح بالبيت بدون ما تقارن عشرين عرض سعر", "zone_09", "outside_in_pen", 5),
        ("r4_06_family_travel", 70.50, 73.20, "وتحجز رحلة قبلها بوقت وتختار مقعد مريح", "zone_09", "outside_in_pen", 5),
        ("r4_08_charity_donation", 73.30, 75.80, "وتقدر تتبرع لمدرسة أو قضية تهمك وعطاء مجتمعي", "zone_09", "outside_in_pen", 5),

        # Zone 10: Elite Education & Children's Flourishing
        ("r4_01_private_school", 75.90, 77.80, "إذا عندك أطفال تقدر على أنشطتهم ودروسهم", "zone_10", "outside_in_pen", 5),
        ("r4_02_soccer_boy", 77.90, 79.20, "رياضة وأنشطة أسبوعية", "zone_10", "slide_down", 4),
        ("r4_04_piano_lesson", 79.30, 81.00, "وحتى مدرسة خاصة إذا اخترت وتطوير مهارات", "zone_10", "outside_in_pen", 5),

        # Zone 11: Night Investment Review, Accountant Signing & Gift Ordering
        ("r5_01_night_investments", 81.10, 83.00, "وبالليل تراجع استثماراتك في هدوء", "zone_11", "outside_in_pen", 5),
        ("r5_02_accountant_signing", 83.10, 85.00, "توقع ورقة من المحاسب المالي", "zone_11", "slide_down", 4),
        ("r5_03_gift_ordering", 85.10, 87.00, "وتطلب هدية بدون ما تشيك رصيدك", "zone_11", "outside_in_pen", 5),
        ("r5_04_year_planning", 87.10, 89.10, "تخطط للسنة الجاية: سفر واستثمار وتطوير", "zone_11", "outside_in_pen", 5),

        # Zone 12: Renovation & Peaceful Future Sunset
        ("r5_05_home_renovation", 89.20, 91.00, "تجديد للبيت أو استثمار جديد جاهز لليوم", "zone_12", "slide_down", 4),
        ("r5_06_peaceful_sunset", 91.10, 94.10, "لكن الأهم إن عندك مساحة تخطط للمستقبل وأنت مرتاح", "zone_12", "outside_in_pen", 5),
    ]

    pipeline = UniversalSectionPipeline(sec_dir, title="الطبقة السابعة: الغني المرتاح")
    published_video = pipeline.run(force_whisper=False, custom_manifest=custom_manifest)
    
    # Also publish with exact PascalCase name for concat_master_documentary.py
    deliv_dir = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables", "sections")
    pascal_video = os.path.join(deliv_dir, "07_Comfortable_Rich_Whiteboard_1080p.mp4")
    pascal_audio = os.path.join(deliv_dir, "07_Comfortable_Rich_Master_Audio.wav")
    
    deliv_audio = os.path.join(deliv_dir, "07_comfortable_rich_Master_Audio.wav")
    
    if os.path.normcase(published_video) != os.path.normcase(pascal_video):
        shutil.copyfile(published_video, pascal_video)
    if os.path.exists(deliv_audio) and os.path.normcase(deliv_audio) != os.path.normcase(pascal_audio):
        shutil.copyfile(deliv_audio, pascal_audio)

    print(f"\n🎬 Finished Section 07! Published to:")
    print(f"  • {published_video}")
    print(f"  • {pascal_video}")

if __name__ == "__main__":
    run()

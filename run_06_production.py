"""
Section 06: Upper Middle Class (الطبقة المتوسطة العليا) - High-Impact Whiteboard Production Pipeline
Synchronized with Faster-Whisper ground truth, authentic Arabic handwriting title banner,
high-impact micro-zoning (11 zones, scale 3.4x-3.8x, CAM_ZOOM=0.68, FIXED_Y=800.0),
zero blank screens, ducked stereo master audio, and hardware-accelerated NVENC rendering.
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.universal_section_pipeline import UniversalSectionPipeline

def run():
    sec_dir = os.path.join(ROOT_DIR, "sections", "06_upper_middle_class")
    
    # 23 verified assets mapped to exact Whisper word-level timestamps and 11 micro-zones
    custom_manifest = [
        # Zone 01: Title Banner + Waking up happily
        ("r0_00_title_banner", 0.00, 2.80, "الطبقة السادسة: الطبقة المتوسطة العليا", "zone_01", "outside_in_pen", 5),
        ("r1_01_waking_happy", 4.80, 7.50, "تصحى في بيت هادي تملكه في حي ممتاز", "zone_01", "outside_in_pen", 5),

        # Zone 02: Upscale Villa + Smart Home
        ("r1_02_upscale_villa", 7.60, 10.00, "أو في منزل مستقر جداً", "zone_02", "outside_in_pen", 5),
        ("r1_03_smart_home", 10.10, 13.50, "المكيف ضبط نفسه ومكنسة روبوت تتحرك في الممر", "zone_02", "slide_down", 4),

        # Zone 03: Home Office + Housekeeper Schedule
        ("r1_04_home_office", 13.80, 16.00, "ماكينة القهوة شغالة بجدول وتشتغل من البيت", "zone_03", "outside_in_pen", 5),
        ("r2_01_housekeeper", 16.20, 19.50, "تفتح جوالك: تقويم العمل وعاملة النظافة بتجي الجمعة", "zone_03", "slide_down", 4),

        # Zone 04: Investment Growth + Financial Advisor
        ("r2_02_investment_growth", 20.20, 24.50, "أغلب الفواتير مسددة تلقائياً والفلوس تتحول للتوفير والاستثمار", "zone_04", "outside_in_pen", 5),
        ("r2_03_financial_advisor", 32.20, 35.00, "التأمين والضرائب والصيانة صارت تكاليف متوقعة مو أزمات", "zone_04", "outside_in_pen", 5),

        # Zone 05: Master Bedroom + Luxury Mercedes SUV
        ("r1_05_master_bedroom", 25.40, 28.50, "الفطور متنوع: فواكه طازجة، بيض، زبادي", "zone_05", "outside_in_pen", 5),
        ("r2_04_mercedes_suv", 29.00, 31.80, "السيارة حديثة ومدفوعة أو قريب تخلص أقساطها", "zone_05", "outside_in_pen", 5),

        # Zone 06: Executive Boardroom + Schedule Notepad
        ("r3_01_executive_boardroom", 35.50, 39.50, "وظيفتك احترافية تدير فريق أو مشاريع معقدة", "zone_06", "outside_in_pen", 5),
        ("r3_02_executive_schedule", 41.50, 44.50, "وعندك تحكم أكبر في جدولك اليومي", "zone_06", "slide_down", 4),

        # Zone 07: Medical Specialist Checkup + Flight Vacation Booking
        ("r3_03_medical_specialist", 45.00, 48.00, "التأمين الصحي قوي وتروح فحوصات دورية وما تؤجل الأسنان", "zone_07", "outside_in_pen", 5),
        ("r2_06_flight_vacation", 51.80, 54.50, "مدخرات التقاعد تمشي تلقائياً وتحجز رحلة قبلها بشهور", "zone_07", "outside_in_pen", 5),

        # Zone 08: Value of Time / iPhone Replacement + Gardener Hedge Trimming
        ("r2_05_iphone_replacement", 54.60, 58.00, "إذا خرب شيء تتصل بمحترف، وقتك أغلى من تصليح الأشياء بنفسك", "zone_08", "outside_in_pen", 5),
        ("r1_06_gardener_hedge", 60.00, 62.80, "تدفع للعناية بالحديقة وعاملة نظافة تزورك بانتظام", "zone_08", "outside_in_pen", 5),

        # Zone 09: Personal Trainer Gym + Private School Kids Sports
        ("r4_01_trainer_gym", 63.20, 66.00, "بعد الدوام تروح جيم مع مدرب أو تاخذ كلاس", "zone_09", "outside_in_pen", 5),
        ("r3_04_private_school_kids", 66.40, 68.80, "العيال عندهم دروس ورياضة وأنت تقدر على الرسوم", "zone_09", "outside_in_pen", 5),

        # Zone 10: Family Movie Night Popcorn + Global Charity Donation
        ("r4_02_family_movie_night", 69.00, 71.20, "في الليل تراجع أجندة بكرة وتشوف مسلسل مع العائلة", "zone_10", "outside_in_pen", 5),
        ("r3_05_global_charity", 71.50, 74.50, "تطلب هدية أونلاين وتتبرع لقضية تهمك وعطاء مجتمعي", "zone_10", "outside_in_pen", 5),

        # Zone 11: Next Year Plans + Infinity Pool + Peaceful Sleep
        ("r4_03_next_year_plans", 75.20, 76.80, "تحس بالأمان", "zone_11", "slide_down", 4),
        ("r4_04_infinity_pool", 76.80, 78.40, "تقدر تفكر في المستقبل وأنت مرتاح", "zone_11", "outside_in_pen", 5),
        ("r4_05_peaceful_sleep", 78.40, 79.23, "تنام مرتاح من ضغط اليوم", "zone_11", "outside_in_pen", 5),
    ]

    pipeline = UniversalSectionPipeline(sec_dir, title="الطبقة السادسة: الطبقة المتوسطة العليا")
    published_video = pipeline.run(force_whisper=False, custom_manifest=custom_manifest)
    print(f"\n🎬 Finished Section 06! Published to: {published_video}")

if __name__ == "__main__":
    run()

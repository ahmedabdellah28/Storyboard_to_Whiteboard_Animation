"""
Section 05: Middle Class (الطبقة المتوسطة) - High-Impact Whiteboard Production Pipeline
Synchronized with Faster-Whisper ground truth, authentic Arabic handwriting title banner,
high-impact micro-zoning (12 zones, scale 3.4x-3.8x, CAM_ZOOM=0.68, FIXED_Y=800.0),
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
    sec_dir = os.path.join(ROOT_DIR, "sections", "05_middle_class")
    
    # 24 verified assets mapped to exact Whisper word-level timestamps and 12 micro-zones
    custom_manifest = [
        # Zone 01: Title Banner + Waking up happily
        ("r0_00_title_banner", 0.00, 2.80, "الطبقة الخامسة: الطبقة المتوسطة", "zone_01", "outside_in_pen", 5),
        ("r1_01_waking_happy", 4.80, 8.20, "هنا تبدأ الحياة تدخل في مرحلة الاستقرار... تصحى في بيت ثلاث غرف", "zone_01", "outside_in_pen", 5),

        # Zone 02: Suburban luxury house + Robot vacuum
        ("r1_02_suburban_house", 14.50, 16.80, "عندك رهن عقاري أو عقد إيجار مستقر", "zone_02", "outside_in_pen", 5),
        ("r1_03_robot_vacuum", 17.00, 19.20, "التدفئة والمكيف والأجهزة شغالة", "zone_02", "slide_down", 4),

        # Zone 03: Espresso machine + Shared family calendar
        ("r1_04_espresso_machine", 19.40, 22.20, "والقهوة جاهزة تقريباً كأنها جزء من الروتين الرسمي", "zone_03", "outside_in_pen", 5),
        ("r1_05_shared_calendar", 22.50, 24.50, "تشيك تقويم مشترك بينك وبين العائلة", "zone_03", "slide_down", 4),

        # Zone 04: Auto-pay bills + Fresh healthy breakfast buffet
        ("r1_06_autopay_bills", 24.60, 27.50, "الرواتب ثابتة، الفواتير تنخصم تلقائياً، وعندك صندوق طوارئ", "zone_04", "outside_in_pen", 5),
        ("r2_01_fresh_breakfast", 29.80, 32.50, "الفطور بسيط لكن طازج: بيض، توست، فاكهة", "zone_04", "outside_in_pen", 5),

        # Zone 05: Kids lunch prep + Modern Volvo SUV
        ("r2_02_kids_lunch_prep", 33.00, 36.00, "وإذا عندك أطفال، تجهز غداهم وتراجع واجباتهم", "zone_05", "outside_in_pen", 5),
        ("r2_03_luxury_suv", 40.00, 43.50, "السيارة مستعملة لكن نظيفة... مصاريف محسوبة مو مفاجآت", "zone_05", "outside_in_pen", 5),

        # Zone 06: Team management desk + Sunny corner office
        ("r2_04_team_management", 47.50, 51.00, "في الدوام، عندك دور واضح مع مساحة أكبر... اجتماعات، رسائل، مشاريع", "zone_06", "outside_in_pen", 5),
        ("r2_05_corner_office", 54.30, 58.00, "وعندك إجازات مدفوعة... مساهمة التقاعد والتأمين صاروا شيء طبيعي", "zone_06", "outside_in_pen", 5),

        # Zone 07: Investment app + Vacation dream
        ("r3_04_investment_app", 60.00, 63.50, "تحط جزء من دخلك للتقاعد، 10 إلى 15 بالمئة", "zone_07", "slide_down", 4),
        ("r3_03_vacation_dream", 64.50, 66.80, "وبرضه عندك مدخرات لأهداف ثانية", "zone_07", "outside_in_pen", 5),

        # Zone 08: Home garden maintenance + Gym workout
        ("r3_06_gardener_hedge", 71.50, 74.50, "وإذا احتجت تصليح بيت أو كفرات سيارة، عندك صندوق مخصص له", "zone_08", "outside_in_pen", 5),
        ("r3_02_gym_weights", 75.50, 78.00, "بعد الدوام تروح نادي، تلعب كورة، أو تطلع مع الشباب", "zone_08", "outside_in_pen", 5),

        # Zone 09: Housekeeper services + Plumber repair
        ("r4_01_housekeeper", 78.20, 80.50, "تطبخ أغلب الليالي، وتطلب من برا بدون ما تحسب كل ريال", "zone_09", "outside_in_pen", 5),
        ("r3_05_plumber_repair", 82.30, 85.50, "إذا صار تسريب في البيت، ممكن تجيب سباك بدال ما تقضي ثلاث ساعات في يوتيوب", "zone_09", "outside_in_pen", 5),

        # Zone 10: Preventive dental checkup + Kids activities (soccer & ballet)
        ("r3_01_doctor_checkup", 86.30, 88.00, "وتحجز فحص الأسنان قبل الألم", "zone_10", "outside_in_pen", 5),
        ("r4_02_kids_activities", 88.10, 90.20, "في المساء تساعد العيال في واجباتهم، تشوف مسلسل", "zone_10", "outside_in_pen", 5),

        # Zone 11: Birthday gift online + Charity box donation
        ("r4_03_online_gift", 91.80, 94.20, "وتقدر تطلب هدية عيد ميلاد أونلاين بدون ما تفتح تطبيق البنك أول", "zone_11", "outside_in_pen", 5),
        ("r4_04_charity_donation", 94.20, 95.20, "العطاء والمشاركة المجتمعية", "zone_11", "slide_down", 4),

        # Zone 12: Tomorrow's agenda checklist + Peaceful sleep finale
        ("r4_05_tomorrow_agenda", 95.20, 96.20, "هنا الاستقرار صار عادة", "zone_12", "slide_down", 4),
        ("r4_06_peaceful_sleep", 95.60, 96.81, "وهامش أمان", "zone_12", "outside_in_pen", 5),
    ]

    pipeline = UniversalSectionPipeline(sec_dir, title="الطبقة الخامسة: الطبقة المتوسطة")
    published_video = pipeline.run(force_whisper=False, custom_manifest=custom_manifest)
    print(f"\n🎬 Finished Section 05! Published to: {published_video}")

if __name__ == "__main__":
    run()

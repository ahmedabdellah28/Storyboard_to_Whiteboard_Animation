"""
Section 03: The Working Poor (الفقر العامل) - High-Impact Whiteboard Production Pipeline
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
    sec_dir = os.path.join(ROOT_DIR, "sections", "03_working_poor")
    
    # 27 verified assets mapped to exact Whisper word-level timestamps and 12 micro-zones
    custom_manifest = [
        # Zone 01: Title Banner + Waking up before dawn
        ("r0_00_title_banner", 0.00, 2.70, "الطبقة الثالثة: الفقر العامل", "zone_01", "outside_in_pen", 5),
        ("r1_01_alarm_wake", 4.80, 8.20, "هنا عندك وظيفة ودخل... تصحى قبل الشمس على منبه جوالك", "zone_01", "outside_in_pen", 5),

        # Zone 02: Small apartment + Bank app
        ("r1_02_small_apartment", 11.30, 13.90, "تسكن في شقة صغيرة بعقد شهري أو سنوي", "zone_02", "outside_in_pen", 5),
        ("r1_03_check_bank_app", 16.60, 18.50, "أول شيء تسويه: تشيك تطبيق البنك", "zone_02", "outside_in_pen", 5),

        # Zone 03: Home coffee/meal prep + Bus + Old car
        ("r1_04_coffee_meal_prep", 19.55, 22.00, "تسوي قهوتك في البيت وتجهز غداك", "zone_03", "outside_in_pen", 5),
        ("r1_05_bus_commute", 24.20, 25.50, "تروح الدوام بباص", "zone_03", "slide_down", 4),
        ("r1_06_old_car_fuel", 25.55, 27.75, "أو سيارة قديمة، البنزين محسوب بالريال", "zone_03", "outside_in_pen", 5),

        # Zone 04: The 4 Service Jobs (Cashier, Warehouse, Restaurant, Caregiver)
        ("r2_01_cashier_job", 29.50, 30.70, "وظيفتك ممكن تكون في محل", "zone_04", "outside_in_pen", 5),
        ("r2_02_warehouse_job", 30.75, 31.70, "أو مستودع", "zone_04", "slide_down", 4),
        ("r2_03_restaurant_job", 31.75, 32.35, "أو مطعم", "zone_04", "slide_down", 4),
        ("r2_04_caregiver_job", 32.38, 33.65, "أو رعاية", "zone_04", "outside_in_pen", 5),

        # Zone 05: Standing shift checklist + Eating packed lunch
        ("r2_05_shift_checklist", 34.00, 37.50, "واقف أغلب الشفت، تتحرك بسرعة، وتتبع تعليمات المدير", "zone_05", "outside_in_pen", 5),
        ("r2_06_eating_lunchbox", 42.00, 44.00, "في الغداء تاكل اللي جبته معك", "zone_05", "outside_in_pen", 5),

        # Zone 06: Shift schedule + Doctor visit
        ("r2_07_shifts_schedule", 44.15, 46.50, "ثم تشيك تطبيق الجدول وتشوف شفتات الأسبوع الجاي", "zone_06", "outside_in_pen", 5),
        ("r3_01_doctor_visit", 47.00, 50.00, "تحاول تبدل يوم إذا عندك موعد دكتور", "zone_06", "outside_in_pen", 5),

        # Zone 07: Family/schedule thinking + Discount shopping
        ("r3_02_family_thinking", 57.10, 59.50, "وتحسب الساعات لأن كل ساعة إضافية ممكن تفرق", "zone_07", "outside_in_pen", 5),
        ("r3_03_shopping_discounts", 60.90, 63.20, "وفي الطريق للبيت توقف عند محل فيه عروض", "zone_07", "outside_in_pen", 5),

        # Zone 08: Loyalty card & coupons + Utility bills
        ("r3_04_loyalty_card", 63.30, 65.10, "تستخدم بطاقة الولاء وكوبونات الخصم", "zone_08", "slide_down", 4),
        ("r3_05_utility_bills", 65.30, 67.50, "تدفع فاتورة اليوم، وتأجل الثانية للأسبوع الجاي", "zone_08", "outside_in_pen", 5),

        # Zone 09: $20 Savings jar + Cooking simple dinner
        ("r3_06_savings_jar", 68.20, 71.00, "وتحاول تحول حتى عشرين دولار للتوفير", "zone_09", "outside_in_pen", 5),
        ("r4_01_cooking_dinner", 75.00, 77.00, "في البيت تطبخ عشاء بسيط", "zone_09", "outside_in_pen", 5),

        # Zone 10: Laundry & uniform + Mail notices
        ("r4_02_laundry_hanging", 77.00, 79.20, "تغسل الملابس وتنشر الزي الرسمي عشان يكون جاهز", "zone_10", "outside_in_pen", 5),
        ("r4_03_mail_notices", 79.30, 82.00, "تفتح البريد: فاتورة خدمات، رصيد فيزا صغير، إشعار إيجار", "zone_10", "outside_in_pen", 5),

        # Zone 11: Side job message + Watching series + Online course
        ("r4_04_side_job_msg", 82.80, 85.00, "وبين كل هذا ترسل رسالة عن شغل جانبي في الويكند", "zone_11", "outside_in_pen", 5),
        ("r4_05a_watch_series", 85.40, 87.10, "يمكن تتابع مسلسل على حساب مشترك", "zone_11", "outside_in_pen", 5),
        ("r4_05b_online_course", 87.20, 89.40, "ويمكن تبدأ كورس أونلاين لشهادة تساعدك تطلع خطوة", "zone_11", "outside_in_pen", 5),

        # Zone 12: Sleeping 6 hours
        ("r4_06_sleep_night", 90.00, 92.50, "وبعدها تنام ست ساعات إذا مشت الأمور وبكرة نفس الموال", "zone_12", "outside_in_pen", 5),
    ]

    pipeline = UniversalSectionPipeline(sec_dir, title="الطبقة الثالثة: الفقر العامل")
    published_video = pipeline.run(force_whisper=False, custom_manifest=custom_manifest)
    print(f"\n🎬 Finished Section 03! Published to: {published_video}")

if __name__ == "__main__":
    run()

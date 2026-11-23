"""
Section 04: Lower Middle Class (الطبقة المتوسطة الدنيا) - High-Impact Whiteboard Production Pipeline
Synchronized with Faster-Whisper ground truth, authentic Arabic handwriting title banner,
high-impact micro-zoning (11 zones, scale 3.4x-3.8x, CAM_ZOOM=0.68, FIXED_Y=800.0),
zero blank screens, ducked stereo master audio, and hardware-accelerated NVENC rendering.
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

from core.config.settings import PROJECT_ROOT
ROOT_DIR = str(PROJECT_ROOT)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.universal_section_pipeline import UniversalSectionPipeline

def run():
    sec_dir = os.path.join(ROOT_DIR, "sections", "04_lower_middle_class")
    
    # 26 verified assets mapped to exact Whisper word-level timestamps and 11 micro-zones
    custom_manifest = [
        # Zone 01: Title Banner + Waking up happily
        ("r0_00_title_banner", 0.00, 2.80, "الطبقة الرابعة: الطبقة المتوسطة الدنيا", "zone_01", "outside_in_pen", 5),
        ("r1_01_waking_happy", 4.80, 7.80, "هنا تبدأ الحياة صير أهدا شوي... تصحى في شقة غرفتين وصالة", "zone_01", "outside_in_pen", 5),

        # Zone 02: Modest house + Clean bedroom
        ("r1_05_modest_house", 10.10, 11.80, "أو بيت صغير متواضع", "zone_02", "outside_in_pen", 5),
        ("r1_02_modest_bedroom", 11.90, 13.50, "المكان نظيف وبسيط", "zone_02", "outside_in_pen", 5),

        # Zone 03: Bills calendar + Morning coffee
        ("r1_04_calendar_bills", 13.60, 16.00, "وعلى الثلاجة قائمة للفواتير ومواعيدها", "zone_03", "slide_down", 4),
        ("r1_03_coffee_morning", 16.50, 18.60, "القهوة تتجهز وأنت تشيك التقويم", "zone_03", "outside_in_pen", 5),

        # Zone 04: Stable job + Healthcare insurance + Smart budgeting + Healthy breakfast
        ("r2_01_stable_job_checklist", 18.80, 21.50, "عندك وظيفة ثابتة بساعات واضحة... الراتب ينزل كل أسبوعين", "zone_04", "outside_in_pen", 5),
        ("r4_03_dental_checkup", 21.80, 24.20, "وعندك تأمين ونسبة بسيطة للتقاعد", "zone_04", "slide_down", 4),
        ("r4_05_online_shopping", 24.50, 27.20, "تستخدم تطبيق للميزانية وتحط الأساسيات في خصم تلقائي", "zone_04", "slide_down", 4),
        ("r2_02_healthy_breakfast", 27.60, 29.80, "الفطور بسيط: بيض، توست، فاكهة", "zone_04", "outside_in_pen", 5),

        # Zone 05: Kids lunch prep + Used clean car + Commuter train
        ("r2_03_kids_lunch_prep", 30.20, 32.80, "وإذا عندك أطفال، تجهز غداهم وتشيك واجباتهم", "zone_05", "outside_in_pen", 5),
        ("r2_04_used_clean_car", 36.40, 38.40, "سيارة مستعملة ونظيفة، عليها أقساط", "zone_05", "outside_in_pen", 5),
        ("r2_05_commuter_train", 38.60, 40.50, "أو تستخدم قطار باشتراك شهري", "zone_05", "slide_down", 4),

        # Zone 06: Office desk tasks + Paid break dream vacation
        ("r3_01_office_desk_tasks", 43.80, 46.50, "في الدوام دورك واضح: ترد إيميلات، تدير طلبات", "zone_06", "outside_in_pen", 5),
        ("r3_02_paid_break_dream", 48.80, 51.50, "لك بريك مدفوع ووقت غداء، وغالباً تعرف جدولك لأسابيع قدام", "zone_06", "outside_in_pen", 5),

        # Zone 07: Retirement savings + Emergency maintenance + Bank app
        ("r3_04_retirement_jar", 52.60, 54.80, "تحاول تحفظ جزء بسيط للتقاعد", "zone_07", "outside_in_pen", 5),
        ("r3_05_home_maintenance", 54.90, 57.00, "وما تلمس صندوق الطوارئ إلا إذا اضطريت", "zone_07", "outside_in_pen", 5),
        ("r3_03_banking_app", 57.30, 59.80, "في الغداء تفتح تطبيق البنك: قسط قرض الدراسة والتوفير", "zone_07", "slide_down", 4),

        # Zone 08: Gym workout + Family dinner
        ("r4_01_gym_treadmill", 63.60, 66.00, "بعد الدوام تمر نادي رخيص، أو تمشي في الحارة", "zone_08", "outside_in_pen", 5),
        ("r4_02_family_dinner", 66.20, 68.20, "العشاء غالباً طبخ بيت", "zone_08", "outside_in_pen", 5),

        # Zone 09: Streaming TV
        ("r4_04_streaming_tv", 68.20, 70.80, "والترفيه؟ نتفليكس وأخواتها، اشتراك أو اشتراكين وتبديل بينهم", "zone_09", "outside_in_pen", 5),

        # Zone 10: Annual roadtrip + Evening study & reading
        ("r5_02_roadtrip_mountains", 71.00, 73.50, "تخطط لرحلة برية قصيرة مرة في السنة، وتجمع لها من بدري", "zone_10", "outside_in_pen", 5),
        ("r5_01_desk_studying", 74.00, 75.80, "وبالليل تجهز ملابس بكرة، وتشحن الجوال", "zone_10", "slide_down", 4),
        ("r5_03_reading_armchair", 76.00, 77.80, "وتشيك التقويم مرة ثانية... تحس إنك منظم", "zone_10", "outside_in_pen", 5),

        # Zone 11: Peaceful sleep + Margin of safety checklist
        ("r5_04_peaceful_sleep", 78.50, 81.20, "وتنام وعندك شيء ما كان موجود في المستويات اللي تحت", "zone_11", "outside_in_pen", 5),
        ("r5_05_safety_checklist", 81.50, 83.36, "هامش بسيط للأمان", "zone_11", "outside_in_pen", 5),
    ]

    pipeline = UniversalSectionPipeline(sec_dir, title="الطبقة الرابعة: الطبقة المتوسطة الدنيا")
    published_video = pipeline.run(force_whisper=False, custom_manifest=custom_manifest)
    print(f"\n🎬 Finished Section 04! Published to: {published_video}")

if __name__ == "__main__":
    run()

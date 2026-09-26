import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.dynamic_speech_synchronizer import DynamicSpeechSynchronizer
from production_engine.dynamic_layout_planner import DynamicLayoutPlanner

sec_dir = os.path.join(ROOT_DIR, "sections", "04_lower_middle_class")

custom_manifest = [
    # Zone 01: Title Banner + Waking up happily
    ("r0_00_title_banner", 0.00, 2.80, "الطبقة الرابعة: الطبقة المتوسطة الدنيا", "zone_01", "outside_in_pen", 5),
    ("r1_01_waking_happy", 4.80, 7.80, "هنا تبدأ الحياة صير أهدا شوي... تصحى في شقة غرفتين وصالة", "zone_01", "outside_in_pen", 5),

    # Zone 02: Modest house + Clean bedroom
    ("r1_05_modest_house", 9.80, 11.80, "أو بيت صغير متواضع", "zone_02", "outside_in_pen", 5),
    ("r1_02_modest_bedroom", 11.80, 13.50, "المكان نظيف وبسيط", "zone_02", "outside_in_pen", 5),

    # Zone 03: Bills calendar + Morning coffee
    ("r1_04_calendar_bills", 13.60, 16.00, "وعلى الثلاجة قائمة للفواتير ومواعيدها", "zone_03", "slide_down", 4),
    ("r1_03_coffee_morning", 16.40, 18.60, "القهوة تتجهز وأنت تشيك التقويم", "zone_03", "outside_in_pen", 5),

    # Zone 04: Stable job checklist + Healthy breakfast
    ("r2_01_stable_job_checklist", 18.90, 22.20, "عندك وظيفة ثابتة بساعات واضحة... الراتب ينزل كل أسبوعين", "zone_04", "outside_in_pen", 5),
    ("r2_02_healthy_breakfast", 27.60, 29.80, "الفطور بسيط: بيض، توست، فاكهة", "zone_04", "outside_in_pen", 5),

    # Zone 05: Kids lunch prep + Used reliable car + Commuter train
    ("r2_03_kids_lunch_prep", 30.20, 32.80, "وإذا عندك أطفال، تجهز غداهم وتشيك واجباتهم", "zone_05", "outside_in_pen", 5),
    ("r2_04_used_clean_car", 36.40, 38.40, "سيارة مستعملة ونظيفة، عليها أقساط", "zone_05", "outside_in_pen", 5),
    ("r2_05_commuter_train", 38.60, 40.50, "أو تستخدم قطار باشتراك شهري", "zone_05", "slide_down", 4),

    # Zone 06: Office desk tasks + Paid break dream vacation
    ("r3_01_office_desk_tasks", 43.80, 46.50, "في الدوام دورك واضح: ترد إيميلات، تدير طلبات", "zone_06", "outside_in_pen", 5),
    ("r3_02_paid_break_dream", 48.80, 51.50, "لك بريك مدفوع ووقت غداء، وغالباً تعرف جدولك لأسابيع قدام", "zone_06", "outside_in_pen", 5),

    # Zone 07: Retirement savings + Emergency maintenance + Bank app
    ("r3_04_retirement_jar", 52.60, 54.80, "تحاول تحفظ جزء بسيط للتقاعد", "zone_07", "outside_in_pen", 5),
    ("r3_05_home_maintenance", 54.90, 57.00, "وما تلمس صندوق الطوارئ إلا إذا اضطريت", "zone_07", "outside_in_pen", 5),
    ("r3_03_banking_app", 57.30, 59.80, "في الغداء تفتح تطبيق البنك: قسط قرض الدراسة", "zone_07", "slide_down", 4),

    # Zone 08: Gym workout + Family dinner
    ("r4_01_gym_treadmill", 63.60, 66.00, "بعد الدوام تمر نادي رخيص، أو تمشي في الحارة", "zone_08", "outside_in_pen", 5),
    ("r4_02_family_dinner", 66.20, 68.20, "العشاء غالباً طبخ بيت", "zone_08", "outside_in_pen", 5),

    # Zone 09: Streaming TV + Dental checkup + Online budgeting
    ("r4_04_streaming_tv", 68.20, 70.80, "والترفيه؟ نتفليكس وأخواتها، اشتراك أو اشتراكين", "zone_09", "outside_in_pen", 5),
    ("r4_03_dental_checkup", 70.90, 72.40, "رعاية صحية وتأمين منظم", "zone_09", "slide_down", 4),
    ("r4_05_online_shopping", 72.50, 74.00, "إدارة الميزانية الذكية", "zone_09", "slide_down", 4),

    # Zone 10: Roadtrip + Evening reading & study
    ("r5_02_roadtrip_mountains", 71.00, 73.50, "تخطط لرحلة برية قصيرة مرة في السنة، وتجمع لها من بدري", "zone_10", "outside_in_pen", 5),
    ("r5_01_desk_studying", 74.20, 76.00, "وبالليل تجهز ملابس بكرة، وتشحن الجوال", "zone_10", "slide_down", 4),
    ("r5_03_reading_armchair", 76.20, 78.00, "وتشيك التقويم مرة ثانية... تحس إنك منظم", "zone_10", "outside_in_pen", 5),

    # Zone 11: Peaceful sleep + Margin of safety checklist
    ("r5_04_peaceful_sleep", 78.50, 81.20, "وتنام وعندك شيء ما كان موجود في المستويات اللي تحت", "zone_11", "outside_in_pen", 5),
    ("r5_05_safety_checklist", 81.50, 83.36, "هامش بسيط للأمان", "zone_11", "outside_in_pen", 5),
]

# Wait, check Zone 09 and Zone 10 overlap!
# In Zone 09: r4_04 is 68.20 to 70.80.
# In Zone 10: r5_02_roadtrip_mountains is spoken at [70.98 - 73.50] ("تخطط لرحلة برية قصيرة")!
# So r4_03 & r4_05 can be placed earlier or in Zone 08/09.
# Let's adjust so that Zone 09 is JUST Streaming TV (68.20 - 70.80),
# then Zone 10 has Roadtrip (71.00 - 73.50), Desk studying (74.20 - 76.00), and Reading armchair (76.20 - 78.00)!

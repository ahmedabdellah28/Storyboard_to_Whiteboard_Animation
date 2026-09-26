import shutil
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

sec = r'sections\01_homeless\assets'
meta_path = os.path.join(sec, 'metadata.json')
m = json.load(open(meta_path, encoding='utf-8'))

# Copy asset images with descriptive names
shutil.copyfile(os.path.join(sec, 'r3_09_extra.png'), os.path.join(sec, 'r3_09_no_kitchen_home.png'))
shutil.copyfile(os.path.join(sec, 'r5_08_extra.png'), os.path.join(sec, 'r5_08_free_clinic.png'))
shutil.copyfile(os.path.join(sec, 'r5_09_extra.png'), os.path.join(sec, 'r5_09_medicine_treatment.png'))

m['r3_09_no_kitchen_home'] = dict(m['r3_09_extra'])
m['r3_09_no_kitchen_home'].update({
    'file': 'r3_09_no_kitchen_home.png',
    'desc': 'انعدام المطبخ والمنزل للطبخ',
    'anchor_text': 'إنت ما تملك مطبخ فتاكل اللي تقدر تشيلة معك',
    'drawing_demand': 1.5
})

m['r5_08_free_clinic'] = dict(m['r5_08_extra'])
m['r5_08_free_clinic'].update({
    'file': 'r5_08_free_clinic.png',
    'desc': 'الانتظار في العيادة المجانية',
    'anchor_text': 'أو تنتظر عيادة مجانية ساعات',
    'drawing_demand': 1.5
})

m['r5_09_medicine_treatment'] = dict(m['r5_09_extra'])
m['r5_09_medicine_treatment'].update({
    'file': 'r5_09_medicine_treatment.png',
    'desc': 'حفظ العلاج والأدوية',
    'anchor_text': 'حتى الأدوية تحتاج تحفظها والنوم نفسه صعب تحفظه',
    'drawing_demand': 1.5
})

with open(meta_path, 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)

print("Successfully added r3_09_no_kitchen_home, r5_08_free_clinic, r5_09_medicine_treatment to metadata.json")

import os
import sys
import json

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine
from google import genai
from google.genai import types

engine = VoiceStudioEngine()
client = genai.Client(api_key=engine.api_key)

audio_path = "project_content/audio/kiwi_voiceover_sweetspot.wav"

audio_file = client.files.upload(file=audio_path)
print("Uploaded audio for alignment analysis...")

prompt = """
Listen carefully to this 58.24-second Arabic audio file.
Extract the exact start and end timestamps (in seconds, e.g. 12.4s) for each of the following specific phrases:

1. "الكيوي"
2. "الكيوي أصله الحقيقي من الصين"
3. "وكان اسمه القديم عنب الثعلب الصيني"
4. "وكان يستخدم كغذاء وحتى كدواء"
5. "لكن في أوائل القرن العشرين"
6. "المزارعين في نيوزيلندا حصلوا على بذوره"
7. "وبدأوا يطورون النوع اللي نعرفه اليوم"
8. "وحتى غيروا اسمه إلى الكيوي"
9. "نسبة لطائر الكيوي النيوزيلندي"
10. "عشان يكون تسويقه أسهل حول العالم"
11. "والأغرب؟"
12. "الكيوي علمياً يعتبر نوعاً من التوت"
13. "وحتى القشرة تقدر تأكلها، لأنها مليانة ألياف"
14. "وأغلب الناس يعرفون الكيوي الأخضر"
15. "لكن عندك أنواع ثانية مثل الكيوي الذهبي والأحمر"
16. "الذهبي قشرته أنعم وطعمه أحلى"
17. "والأحمر نادر أكثر، ومن الداخل شكله فعلاً كأنه تصميم فني"
18. "والكيوي فيه إنزيم طبيعي يساعد على تكسير البروتين"
19. "وفوق هذا غني بفيتامين سي"
20. "يعني مو بس شكله غريب، حتى تركيبه الغذائي مختلف"

Return the result as a clean JSON list of objects with keys: "phrase", "start_s", "end_s".
"""

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=[audio_file, prompt]
)

print("\n--- TIMESTAMPS FROM GEMINI ---")
print(response.text)

os.makedirs("scratch", exist_ok=True)
with open("scratch/kiwi_sweetspot_timestamps.json", "w", encoding="utf-8") as f:
    f.write(response.text)

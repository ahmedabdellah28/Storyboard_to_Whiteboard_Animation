import os
import sys
import time

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine

audio_dir = r"sections/11_jabuticaba/scratch/row_audio"
os.makedirs(audio_dir, exist_ok=True)

rows_text = [
    (1, "الجابوتيكابا... أو مثل ما يسمونها أحياناً: العنب البرازيلي! وهذي من أغرب الفواكه في العالم، لأن أزهارها وثمارها تنمو مباشرة على الجذع الرئيسي والفروع السميكة، في ظاهرة نباتية مذهلة."),
    (2, "تخيل شجرة، وفجأة جذعها نفسه صار مغطى بالكامل بحبات سوداء لامعة! طعمها لذيذ وقريب من العنب، وقشرتها سميكة لما تعضها تفرقع في فمك بانفجار منعش من العصير."),
    (3, "لكن عندها نقطة ضعف كبيرة: تخرب وتتخمر بسرعة فائقة خلال ثلاثة إلى أربعة أيام فقط من قطفها! عشان كذا تصديرها طازجة شبه مستحيل، ونادر تشوفها خارج موطنها الأصلي في البرازيل."),
    (4, "والأغرب إن شجرة الجابوتيكابا بطيئة النمو، وتحتاج سنوات طويلة من الرعاية قبل أن تثمر... لكن لما تبدأ؟ تكسو جذعها بآلاف الثمار اللذيذة وعصيرها البنفسجي الساحر.")
]

engine = VoiceStudioEngine()

for r_idx, text in rows_text:
    out_wav = os.path.join(audio_dir, f"row_{r_idx}.wav")
    if os.path.exists(out_wav) and os.path.getsize(out_wav) > 10000:
        print(f"\n--- Row {r_idx} already exists ({os.path.getsize(out_wav)} bytes), skipping ---")
        continue

    print(f"\n--- Synthesizing Row {r_idx} with fresh key ---")
    print(f"Text: {text}")
    try:
        res = engine.generate_speech(
            transcript=text,
            output_wav_path=out_wav,
            voice_name="Fenrir",
            profile_key="SAUDI_YOUTH_CREATOR",
            director_note_key="DYNAMIC_WHITEBOARD_SWEETSPOT",
            speed=1.0,
            auto_chunk=False
        )
        print(f"Row {r_idx} generated: {res['output_path']} ({res['duration']:.2f}s)")
        time.sleep(5)  # Safe pause between requests
    except Exception as e:
        print(f"Error generating Row {r_idx}: {e}")

print("\nSpeech synthesis script completed!")

import os
import sys

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine

audio_dir = r"sections/09_dragon_fruit/scratch/row_audio"
os.makedirs(audio_dir, exist_ok=True)

rows_text = [
    (1, "فاكهة التنين، أو البيتايا... تنمو على نبات من الصباريات، وتتفتح بأزهار ليلية عملاقة مع ثمار حمراء خلابة."),
    (2, "وأصلها يرجع إلى أمريكا الوسطى، قبل أن تبدأ رحلتها وتنتشر زراعتها وتُحصد ثمارها الاستوائية الفريدة."),
    (3, "انتقلت إلى جنوب شرق آسيا واشتهرت بألوانها الجذابة بين اللب الأبيض والأحمر والأصفر، وتعتبر فيتنام اليوم من أكبر منتجيها في العالم."),
    (4, "وفيها مضادات أكسدة وفيتامينات وألياف تدعم صحة الجسم، لتصبح فاكهة أساسية في أشهى العصائر والأطباق العصرية.")
]

engine = VoiceStudioEngine()

for r_idx, text in rows_text:
    out_wav = os.path.join(audio_dir, f"row_{r_idx}.wav")
    print(f"\n--- Synthesizing Row {r_idx} ---")
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
    except Exception as e:
        print(f"Error generating Row {r_idx}: {e}")

print("\nSpeech synthesis script finished.")

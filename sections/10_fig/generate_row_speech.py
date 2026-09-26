import os
import sys

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine

audio_dir = r"sections/10_fig/scratch/row_audio"
os.makedirs(audio_dir, exist_ok=True)

rows_text = [
    (1, "التين... التين أغرب مما يبدو. وفيه فرضيات وأدلة أثرية تخليه من أقدم النباتات اللي زرعها الإنسان، ويمكن حتى أقدم من الحبوب، حيث عثر علماء الآثار في وادي الأردن على أدلة تعود لأكثر من أحد عشر ألف سنة."),
    (2, "لكن المفاجأة الحقيقية: التين اللي نأكله مو فاكهة بالمعنى التقليدي! هو في الحقيقة بنية تحتوي على أزهار كثيرة من الداخل، والحبات المقرمشة داخله مرتبطة بتلك الأزهار، وتتحول بالتجفيف لحلاوة مركزة."),
    (3, "وفي التين البري، فيه علاقة غريبة مع دبابير متخصصة تدخل من فتحة صغيرة لتلقيح الأزهار، وينتج التين إنزيمات تفكك المواد العضوية، بينما معظم أصناف التين التجاري اليوم تثمر بدون دبابير أصلاً."),
    (4, "وتتنوع أصناف التين بألوانها ومذاقاتها العسلية بين الأسود والأخضر والأصفر، لتبدأ من شتلة فتية وتنمو إلى شجرة معمرة عظيمة تجود بأطيب الثمار.")
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

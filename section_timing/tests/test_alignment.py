from section_timing.alignment.arabic_normalizer import ArabicTextNormalizer
from section_timing.alignment.token_aligner import TokenAligner
from section_timing.timeline.models import WordItem

def test_arabic_normalization():
    norm = ArabicTextNormalizer.normalize
    # Tashkeel removal
    assert norm("الْكِيوِي") == "الكيوي"
    # Alef normalization
    assert norm("أصله") == "اصله"
    assert norm("إلى") == "الي"
    assert norm("آسيا") == "اسيا"
    # Taa marbouta
    assert norm("حديقة") == "حديقه"
    # Tatweel
    assert norm("كـــنز") == "كنز"

def test_token_aligner_interpolation():
    aligner = TokenAligner()
    script = ["الكيوي", "أصله", "الحقيقي", "من", "الصين"]
    
    # Simulate Whisper missing the word "الحقيقي"
    whisper_words = [
        WordItem(id="w1", text="الكيوي", start=0.0, end=0.5, duration=0.5),
        WordItem(id="w2", text="أصله", start=0.6, end=1.0, duration=0.4),
        WordItem(id="w3", text="من", start=1.5, end=1.8, duration=0.3),
        WordItem(id="w4", text="الصين", start=1.9, end=2.4, duration=0.5),
    ]

    aligned = aligner.align_tokens(script, whisper_words)
    assert len(aligned) == 5
    # Word "الحقيقي" should have interpolated timestamps between 1.0 and 1.5
    real_word = aligned[2]
    assert real_word.text == "الحقيقي"
    assert real_word.start >= 1.0
    assert real_word.end <= 1.5
    assert real_word.needs_review is True

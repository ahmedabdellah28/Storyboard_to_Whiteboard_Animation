import pytest
from section_tts.core.semantic_chunker import SemanticChunker
from section_tts.config import ChunkingConfig

def test_short_arabic_text():
    chunker = SemanticChunker(ChunkingConfig(max_words_per_chunk=28, min_words_per_chunk=6))
    text = "الكيوي فاكهة لذيذة ومفيدة جداً للصحة."
    chunks = chunker.split_script(text)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_word_integrity_preservation():
    """Ensure that chunking never loses, adds, or mutates any words."""
    chunker = SemanticChunker(ChunkingConfig(max_words_per_chunk=15, min_words_per_chunk=4))
    text = (
        "الكيوي أصله الحقيقي من الصين، وكان اسمه القديم عنب الثعلب الصيني، "
        "لكن المزارعين في نيوزيلندا قرروا تغيير اسمه التجاري ليصبح الكيوي "
        "نسبة إلى طائر الكيوي الشهير هناك."
    )
    chunks = chunker.split_script(text)
    assert len(chunks) >= 2

    # Reconstitute and compare word by word
    original_words = text.replace("،", " ").replace(".", " ").split()
    chunked_words = " ".join(chunks).replace("،", " ").replace(".", " ").split()
    assert original_words == chunked_words

def test_long_sentence_natural_clause_splitting():
    chunker = SemanticChunker(ChunkingConfig(max_words_per_chunk=18, min_words_per_chunk=5))
    text = (
        "في بداية القرن العشرين، هاجرت بذور هذه الفاكهة من آسيا إلى قارة أوقيانوسيا، "
        "وهناك اكتشف العلماء أن التربة البركانية الرطبة تمنح الثمار حلاوة استثنائية تفوق نظيرتها الآسيوية، "
        "مما أدى إلى ازدهار صناعة التصدير العالمية."
    )
    chunks = chunker.split_script(text)
    for c in chunks:
        words = c.split()
        assert len(words) <= 22  # Safe ceiling around max_words
    assert len(chunks) >= 3

def test_question_and_exclamation_boundaries():
    chunker = SemanticChunker(ChunkingConfig(max_words_per_chunk=25))
    text = "هل تعلم من أين جاء الكيوي؟ الإجابة ستصدمك تماماً! لم يكن اسمه هكذا في الماضي."
    chunks = chunker.split_script(text)
    assert len(chunks) >= 2
    assert "هل تعلم من أين جاء الكيوي؟" in chunks[0]

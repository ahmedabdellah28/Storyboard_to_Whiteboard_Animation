import re
from typing import List, Tuple
from ..timeline.models import WordItem
from .token_aligner import TokenAligner
from .arabic_normalizer import ArabicTextNormalizer
from .english_normalizer import EnglishTextNormalizer

class ScriptAudioAligner:
    """Master aligner linking original section script to acoustic truth."""
    def __init__(self, language: str = "ar"):
        self.language = (language or "ar").lower()
        if self.language.startswith("en"):
            self.normalizer = EnglishTextNormalizer()
        else:
            self.normalizer = ArabicTextNormalizer()
        self.token_aligner = TokenAligner(self.normalizer)

    def extract_script_words(self, script_text: str) -> List[str]:
        """Extracts words from script while preserving original word forms."""
        # Split on whitespace but strip standalone punctuation
        raw_words = re.split(r'\s+', script_text.strip())
        return [w.strip() for w in raw_words if w.strip()]

    def align(
        self,
        script_text: str,
        whisper_words: List[WordItem]
    ) -> List[WordItem]:
        """Aligns script words with Whisper audio timestamps."""
        script_words = self.extract_script_words(script_text)
        return self.token_aligner.align_tokens(script_words, whisper_words)

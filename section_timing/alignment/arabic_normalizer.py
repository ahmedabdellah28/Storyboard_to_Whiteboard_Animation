import re
import unicodedata
from typing import Tuple

class ArabicTextNormalizer:
    """Normalizes Arabic text solely for robust phonetic and token alignment."""
    
    # Tashkeel regex
    TASHKEEL_REGEX = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
    TATWEEL = '\u0640'

    @classmethod
    def normalize(cls, text: str) -> str:
        """Returns normalized string for matching while preserving the original separately."""
        if not text:
            return ""
        
        # Unicode normalization (NFKC)
        norm = unicodedata.normalize("NFKC", text)

        # Remove diacritics / tashkeel
        norm = cls.TASHKEEL_REGEX.sub('', norm)

        # Remove tatweel
        norm = norm.replace(cls.TATWEEL, '')

        # Normalize Alef forms (إ, أ, آ, ٱ -> ا)
        norm = re.sub(r'[إأآٱ]', 'ا', norm)

        # Normalize Taa Marbouta (ة -> ه)
        norm = re.sub(r'ة', 'ه', norm)

        # Normalize Yaa forms (ى -> ي)
        norm = re.sub(r'ى', 'ي', norm)

        # Strip all punctuation except spaces
        norm = re.sub(r'[.,?!؟،:;\-—_()\[\]"\'`~*#&^%$@/\\|]', ' ', norm)

        # Collapse whitespace
        norm = re.sub(r'\s+', ' ', norm).strip()

        return norm.lower()

    @classmethod
    def pair(cls, text: str) -> Tuple[str, str]:
        """Returns (original_text, normalized_text)."""
        return text, cls.normalize(text)

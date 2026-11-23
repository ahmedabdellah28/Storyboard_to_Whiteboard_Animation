import re
import unicodedata
from typing import Tuple


class EnglishTextNormalizer:
    """Normalizes colloquial English text for robust Whisper-to-script token alignment."""

    COLLOQUIAL_MAP = {
        "gonna": "going to",
        "wanna": "want to",
        "gotta": "got to",
        "kinda": "kind of",
        "sorta": "sort of",
        "outta": "out of",
        "lotta": "lot of",
        "dunno": "do not know",
        "lemme": "let me",
        "gimme": "give me",
        "cuz": "because",
        "cause": "because",
        "yall": "you all",
        "ya": "you",
        "em": "them",
        "im": "i am",
        "ive": "i have",
        "id": "i would",
        "ill": "i will",
        "dont": "do not",
        "didnt": "did not",
        "doesnt": "does not",
        "cant": "can not",
        "wont": "will not",
        "isnt": "is not",
        "arent": "are not",
        "wasnt": "was not",
        "werent": "were not",
        "hes": "he is",
        "shes": "she is",
        "its": "it is",
        "thats": "that is",
        "whats": "what is",
        "wheres": "where is",
        "theres": "there is",
        "theyre": "they are",
        "youre": "you are",
    }

    @classmethod
    def normalize(cls, text: str) -> str:
        """Returns normalized lowercase string for matching while preserving original separately."""
        if not text:
            return ""

        norm = unicodedata.normalize("NFKC", text).lower()
        # Normalize curly apostrophes and dashes
        norm = norm.replace("’", "'").replace("‘", "'").replace("`", "'")
        # Remove apostrophes inside contractions so don't -> dont
        norm = norm.replace("'", "")
        # Strip punctuation except spaces
        norm = re.sub(r'[.,?!:;—\-_()\[\]"{}~*#&^%$@/\\|]', " ", norm)
        # Collapse whitespace
        norm = re.sub(r"\s+", " ", norm).strip()

        # Expand common colloquial contractions if single token matches
        if norm in cls.COLLOQUIAL_MAP:
            return cls.COLLOQUIAL_MAP[norm]
        return norm

    @classmethod
    def pair(cls, text: str) -> Tuple[str, str]:
        """Returns (original_text, normalized_text)."""
        return text, cls.normalize(text)


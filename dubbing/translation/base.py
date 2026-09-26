"""
Translation Base Interface
===========================
Abstract interface for translation providers.
"""
from abc import ABC, abstractmethod
from typing import List

from ..models.dubbing_models import SourceSegment, TranslatedSegment


class TranslationProvider(ABC):
    """Abstract base class for text translation providers."""

    @abstractmethod
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """
        Translate a single string.

        Args:
            text: Source text.
            source_language: BCP-47 code of the source language (e.g. "ar").
            target_language: BCP-47 code of the target language (e.g. "en").

        Returns:
            Translated text string.
        """
        ...

    def translate_segments(
        self,
        segments: List[SourceSegment],
        source_language: str,
        target_language: str,
    ) -> List[TranslatedSegment]:
        """
        Translate a list of segments, preserving IDs and timestamps.

        The default implementation translates each segment individually.
        Subclasses may override for batch/context-aware translation.
        """
        results = []
        for seg in segments:
            translated_text = self.translate(
                seg.text,
                source_language,
                target_language,
            )
            results.append(
                TranslatedSegment(
                    id=seg.id,
                    source=seg,
                    language=target_language,
                    text=translated_text.strip(),
                )
            )
        return results

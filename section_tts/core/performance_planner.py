import re
from typing import List
from ..models.voice import PerformanceCue

class PerformancePlanner:
    """
    Analyzes semantic role of each chunk within a section and assigns tailored performance dynamics.
    Maintains fixed Voice Identity while ensuring lively, natural YouTube explainer flow.
    """
    def plan(self, chunks: List[str]) -> List[PerformanceCue]:
        total_chunks = len(chunks)
        cues: List[PerformanceCue] = []

        for idx, text in enumerate(chunks):
            # Detection heuristics based on position and markers
            is_first = (idx == 0)
            is_last = (idx == total_chunks - 1)
            
            # Look for surprises, questions, contrasts, discoveries
            has_question = bool(re.search(r'[؟?]', text))
            has_numbers = bool(re.search(r'\d+', text))
            has_surprise_words = bool(re.search(r'(لكن|المفاجأة|الصدمة|الغريب|تخيل|أغرب|الحقيقة|في الواقع|تصدق)', text))
            has_contrast = bool(re.search(r'(بينما|على عكس|بدل|غير أن|رغم ذلك)', text))

            if is_first:
                # Section hook / opening statement
                cues.append(PerformanceCue(
                    segment_type="HOOK",
                    energy="high",
                    pace="fast",
                    curiosity="high",
                    emphasis="subtle",
                    pause_before_ms=0,
                    pause_after_ms=60,
                    instruction="خاطف، مثير للفضول، إيقاع سريع وثابت بدون تباطؤ."
                ))
            elif has_surprise_words or (has_contrast and idx > 0):
                cues.append(PerformanceCue(
                    segment_type="SURPRISE",
                    energy="high",
                    pace="fast",
                    curiosity="high",
                    emphasis="strong",
                    pause_before_ms=60,
                    pause_after_ms=80,
                    instruction="نبرة كشف معلومة غير متوقعة، تشديد ذكي على الكلمات المحورية."
                ))
            elif is_last:
                cues.append(PerformanceCue(
                    segment_type="OUTRO",
                    energy="high",
                    pace="continuous",
                    curiosity="normal",
                    emphasis="subtle",
                    pause_before_ms=40,
                    pause_after_ms=100,
                    instruction="اختتام قوي وواضح للجملة الأخيرة دون ترهل أو تباطؤ درامي."
                ))
            elif has_numbers or has_question:
                cues.append(PerformanceCue(
                    segment_type="FACT",
                    energy="high",
                    pace="fast",
                    curiosity="normal",
                    emphasis="strong",
                    pause_before_ms=40,
                    pause_after_ms=70,
                    instruction="وضوح مخارج الحروف، تأكيد سريع على الأرقام والحقائق."
                ))
            else:
                cues.append(PerformanceCue(
                    segment_type="TRANSITION",
                    energy="high",
                    pace="continuous",
                    curiosity="normal",
                    emphasis="subtle",
                    pause_before_ms=40,
                    pause_after_ms=60,
                    instruction="تدفق سلس ومستمر يربط الفكرة بالسياق القادم."
                ))

        return cues

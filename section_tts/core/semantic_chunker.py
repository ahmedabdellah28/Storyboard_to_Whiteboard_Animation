import re
from typing import List
from ..config import ChunkingConfig

class SemanticChunker:
    """
    Intelligent semantic chunker for Arabic & multi-lingual video scripts:
    1. Splits on sentence boundaries (. ! ؟ ? \n).
    2. Splits long sentences on natural semantic pauses (، , ؛ : dashes).
    3. Groups clauses into natural rhythmic units respecting max_words_per_chunk.
    4. Guarantees 100% word integrity (no missing words, no hallucinations, no rewrites).
    """
    def __init__(self, config: ChunkingConfig = None):
        self.config = config or ChunkingConfig()
        self.max_words = self.config.max_words_per_chunk
        self.min_words = self.config.min_words_per_chunk

    def split_script(self, text: str) -> List[str]:
        """Splits section script into coherent semantic chunks."""
        clean_text = text.strip()
        if not clean_text:
            return []

        # Step 1: Split into paragraphs & major sentence units
        # Preserve sentence punctuation by capturing delimiters
        raw_lines = [p.strip() for p in clean_text.splitlines() if p.strip()]
        
        sentence_units = []
        for line in raw_lines:
            # Match sentence endings: . ! ؟ ? or double newlines
            parts = re.split(r'([.?!؟]+)', line)
            for i in range(0, len(parts), 2):
                phrase = parts[i].strip()
                punct = parts[i + 1].strip() if i + 1 < len(parts) else ""
                combined = f"{phrase}{punct}".strip()
                if combined:
                    sentence_units.append(combined)

        # Step 2: Break sentences that exceed max_words on semantic sub-clauses (commas, semicolons)
        clauses: List[str] = []
        for unit in sentence_units:
            words = [w for w in unit.split() if w]
            if len(words) <= self.max_words:
                clauses.append(unit)
            else:
                # Sub-split on Arabic/English commas, colons, semicolons
                sub_parts = re.split(r'([،,؛:\-]+)', unit)
                sub_combined = []
                for j in range(0, len(sub_parts), 2):
                    sub_phrase = sub_parts[j].strip()
                    sub_punct = sub_parts[j + 1].strip() if j + 1 < len(sub_parts) else ""
                    c = f"{sub_phrase}{sub_punct}".strip()
                    if c:
                        sub_combined.append(c)
                
                # If still too long or no punctuation, break on natural Arabic conjunctions (و، ف، ثم، لكن)
                for sc in sub_combined:
                    sc_words = [w for w in sc.split() if w]
                    if len(sc_words) <= self.max_words:
                        clauses.append(sc)
                    else:
                        conj_parts = re.split(r'(\s+(?:و|ثم|لكن|ف|بل)\s+)', sc)
                        temp_phrase = ""
                        for cp in conj_parts:
                            if not cp:
                                continue
                            test_words = len((temp_phrase + " " + cp).split())
                            if test_words > self.max_words and temp_phrase:
                                clauses.append(temp_phrase.strip())
                                temp_phrase = cp
                            else:
                                temp_phrase = f"{temp_phrase} {cp}".strip()
                        if temp_phrase:
                            clauses.append(temp_phrase.strip())

        # Step 3: Combine adjacent small clauses up to max_words without breaking ideas
        final_chunks: List[str] = []
        current_chunk_words: List[str] = []
        current_chunk_str: List[str] = []

        for clause in clauses:
            clause_words = [w for w in clause.split() if w]
            if not clause_words:
                continue

            potential_len = len(current_chunk_words) + len(clause_words)
            
            # Prefer breaking at strong question marks (؟, ?) if the preceding part has sufficient words
            ends_with_strong_punct = clause.endswith(("؟", "?", "!", ".")) and len(clause_words) >= self.min_words

            if potential_len > self.max_words and current_chunk_words:
                final_chunks.append(" ".join(current_chunk_str).strip())
                current_chunk_words = list(clause_words)
                current_chunk_str = [clause]
            else:
                current_chunk_words.extend(clause_words)
                current_chunk_str.append(clause)
                # If clause ends with a strong question or exclamation mark and already has enough words, yield as boundary
                if ends_with_strong_punct and len(current_chunk_words) >= self.min_words and clause.endswith(("؟", "?", "!")):
                    final_chunks.append(" ".join(current_chunk_str).strip())
                    current_chunk_words = []
                    current_chunk_str = []

        if current_chunk_str:
            final_chunks.append(" ".join(current_chunk_str).strip())

        # Safety Check: If the last chunk is too small (< min_words) and we have a preceding chunk,
        # merge it if total doesn't blow past (max_words + 4)
        if len(final_chunks) > 1:
            last_words = len(final_chunks[-1].split())
            prev_words = len(final_chunks[-2].split())
            if last_words < self.min_words and (last_words + prev_words) <= (self.max_words + 6):
                merged = f"{final_chunks[-2]} {final_chunks[-1]}"
                final_chunks = final_chunks[:-2] + [merged]

        return final_chunks

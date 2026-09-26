from typing import List, Dict, Any, Optional, Tuple
from ..timeline.models import SentenceItem, WordItem, SemanticBeatItem, VisualBeatItem, SpeechAnchor
from ..alignment.arabic_normalizer import ArabicTextNormalizer

class SemanticBeatMapper:
    """Maps existing Asset Plan entities to speech anchors and semantic beats."""
    def __init__(self):
        self.normalizer = ArabicTextNormalizer()

    def map_visual_beats(
        self,
        assets: List[Dict[str, Any]],
        sentences: List[SentenceItem],
        words: List[WordItem],
        total_duration: float
    ) -> Tuple[List[SemanticBeatItem], List[VisualBeatItem]]:
        """
        Maps each asset from the asset plan to a precise speech anchor.
        Only uses assets explicitly declared in the asset plan.
        """
        if not assets:
            return [], []

        semantic_beats: List[SemanticBeatItem] = []
        visual_beats: List[VisualBeatItem] = []
        
        # Step through assets chronologically
        total_assets = len(assets)
        for idx, asset in enumerate(assets):
            aid = str(asset.get("aid", asset.get("id", f"A{idx+1:02d}")))
            role = str(asset.get("role", "subject"))
            keywords = asset.get("keywords", [])
            # Also derive potential keywords from file or aid name (e.g. "waking_street" -> ["waking", "street"])
            name_hints = aid.replace("_", " ").split()

            # Attempt to anchor to a sentence or word
            matched_sentence: Optional[SentenceItem] = None
            matched_word: Optional[WordItem] = None

            # 1. Check if asset specifies a target sentence or timestamp
            if "target_time" in asset:
                t_time = float(asset["target_time"])
                anchor_text = aid
                anchor_start = max(0.0, t_time)
                anchor_end = min(total_duration, t_time + 1.5)
            elif "sentence_id" in asset:
                for s in sentences:
                    if s.id == asset["sentence_id"]:
                        matched_sentence = s
                        break
                if matched_sentence:
                    anchor_text = matched_sentence.text
                    anchor_start = matched_sentence.start
                    anchor_end = matched_sentence.end
                else:
                    anchor_text = aid
                    anchor_start = (idx / float(total_assets)) * total_duration
                    anchor_end = min(total_duration, anchor_start + 1.5)
            else:
                # Distribute evenly across sentences if not matched by keyword
                target_s_idx = min(len(sentences) - 1, int((idx / float(total_assets)) * len(sentences))) if sentences else 0
                if sentences:
                    s = sentences[target_s_idx]
                    anchor_text = s.text
                    anchor_start = s.start
                    anchor_end = s.end
                else:
                    anchor_text = aid
                    anchor_start = (idx / float(total_assets)) * total_duration
                    anchor_end = min(total_duration, anchor_start + 1.5)

            # Determine action
            action = asset.get("action", "draw")
            if "connect" in aid or "arrow" in aid:
                action = "connect"
            elif "title" in aid or "banner" in aid:
                action = "reveal"

            # Create SemanticBeatItem
            sem_id = f"sb_{idx+1:03d}"
            semantic_beats.append(SemanticBeatItem(
                id=sem_id,
                sentence_id=matched_sentence.id if matched_sentence else None,
                subject=aid,
                action=action,
                anchor_text=anchor_text,
                importance=float(asset.get("importance", 0.8))
            ))

            # Create VisualBeatItem
            vb_id = f"vb_{idx+1:03d}"
            visual_beats.append(VisualBeatItem(
                id=vb_id,
                asset_id=aid,
                semantic_role=role,
                speech_anchor=SpeechAnchor(
                    text=anchor_text,
                    start=round(anchor_start, 3),
                    end=round(anchor_end, 3)
                ),
                importance=float(asset.get("importance", 0.8)),
                action=action
            ))

        return semantic_beats, visual_beats

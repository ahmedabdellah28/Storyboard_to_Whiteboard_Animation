"""Evaluates candidate assets and prevents arbitrary wrong selections."""

from typing import List, Dict, Any, Optional, Tuple
from ..models.input import AssetCatalog, AssetMetadata
from ..models.output import SemanticMatchScore

class AssetMatchValidator:
    """Ranks and selects candidate assets, or identifies MISSING_ASSET."""

    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog

    def find_best_asset(
        self,
        anchor_text: str,
        speech_tags: List[str]
    ) -> Tuple[Optional[AssetMetadata], float, str]:
        """Finds the best matching asset from catalog.
        
        Returns:
            (best_asset, score, decision_reason)
        """
        if not self.catalog.assets:
            return None, 0.0, "NO_VALID_ASSET"

        norm_anchor = anchor_text.lower()
        scored: List[Tuple[AssetMetadata, float]] = []

        for aid, asset in self.catalog.assets.items():
            tags = f"{asset.asset_id} {asset.semantic_description} {asset.visual_role} {' '.join(asset.objects)}".lower()
            score = 0.0

            # Match against anchor text
            for word in norm_anchor.split():
                if len(word) > 2 and word in tags:
                    score += 0.3

            # Match against speech tags
            for tag in speech_tags:
                if tag.lower() in tags:
                    score += 0.4

            if score > 0.2:
                scored.append((asset, min(1.0, score)))

        if not scored:
            return None, 0.0, "NO_VALID_ASSET"

        scored.sort(key=lambda x: x[1], reverse=True)
        best_asset, best_score = scored[0]

        if best_score < 0.3:
            return None, best_score, "NO_VALID_ASSET"

        return best_asset, best_score, "MATCH_FOUND"

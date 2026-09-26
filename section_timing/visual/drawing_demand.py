from typing import Dict, Any

class DrawingDemandCalculator:
    """Calculates geometric and graphic drawing demand (0.0 to 1.0) independent of semantic importance."""
    
    BASE_TYPE_DEMANDS = {
        "title_banner": 0.55,
        "banner": 0.50,
        "arrow": 0.15,
        "connector": 0.20,
        "box": 0.25,
        "circle": 0.25,
        "icon": 0.35,
        "character": 0.75,
        "complex_scene": 0.90,
        "map": 0.85,
        "label": 0.30
    }

    def compute_demand(self, asset: Dict[str, Any]) -> float:
        """
        Computes drawing demand using dimensions, stroke metadata, or type heuristics.
        Returns a float between 0.10 and 1.0.
        """
        # If asset explicitly declares drawing_demand
        if "drawing_demand" in asset:
            return float(asset["drawing_demand"])

        # Check asset id or name for type indicators
        aid = str(asset.get("aid", asset.get("id", ""))).lower()
        role = str(asset.get("role", "")).lower()

        base_demand = 0.50
        for k, v in self.BASE_TYPE_DEMANDS.items():
            if k in aid or k in role:
                base_demand = v
                break

        # Dimension-based scaling if w and h exist
        w = float(asset.get("w", 0))
        h = float(asset.get("h", 0))
        if w > 0 and h > 0:
            area = w * h
            # Normalization scale around standard whiteboard area (e.g. 800x600 = 480k)
            size_factor = min(0.35, (area / 1_000_000.0) * 0.35)
            base_demand = min(1.0, max(0.10, base_demand + size_factor))

        return round(base_demand, 2)

"""Asset Semantics Contract.

Defines rich semantic metadata for extracted visual assets, replacing
purely geometric extraction diagnostics with narrative and compositional role.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class AssetSemanticMetadata(BaseModel):
    """Semantic metadata describing an asset's narrative identity and animation role."""
    asset_id: str = Field(..., description="Unique asset ID (e.g. asset_001)")
    semantic_name: str = Field(..., description="Descriptive slug (e.g. hero_stained_shirt)")
    category: str = Field(..., description="Broad visual category: character, prop, graphic, symbol, environment")
    tags: List[str] = Field(default_factory=list, description="Descriptive semantic tags")
    identity_group: str = Field(default="general", description="Narrative cluster/entity (e.g. main_character)")
    variant_group: str = Field(default="", description="State or pose variant (e.g. panic, thinking)")
    visual_role: str = Field(default="support", description="Default role: hero, support, accent, context")
    animation_capabilities: List[str] = Field(
        default_factory=lambda: ["pop_in", "scale_in", "pulse", "fade_in", "slide_up", "settle"],
        description="Supported kinetic actions for this asset",
    )

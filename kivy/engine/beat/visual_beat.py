"""
Visual Beat Data Models (Level 2: Visual Rhythm & Semantic Container)
Visual Beat acts as the atomic semantic container for drawing choreography.
Engine V2: Content-Aware Timing with Calibrated Physical Modeling,
Semantic Anchors, Speed Feasibility Analysis, and Timing Conflict Handling.
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


class TransitionPolicy(Enum):
    KEEP = "KEEP"            # Keep previous elements on canvas (additive storytelling)
    REPLACE = "REPLACE"      # Clear/fade previous panel before starting new beat
    OVERLAP = "OVERLAP"      # Begin new beat drawing before previous beat completely finishes
    CLEAR = "CLEAR"          # Explicit wipe/erase of previous content
    TRANSFORM = "TRANSFORM"  # Dynamic morphing or camera zoom shift


class OverlapPolicy(Enum):
    NONE = "NONE"            # Strict sequential drawing: next element starts after previous finishes
    LIMITED = "LIMITED"      # Subtle overlap: next element starts when previous reaches ~85%
    NATURAL = "NATURAL"      # Natural overlap: next element starts when previous reaches ~65-75%


class ElementTier(Enum):
    PRIMARY = "PRIMARY"        # Core focal point (character, central statistic, main subject) - semantic protection & prominent hold
    SECONDARY = "SECONDARY"    # Explanatory graphics, speech bubbles, text cards, icons - physical demand driven
    DECORATIVE = "DECORATIVE"  # Underlines, arrows, background textures, minor badges - accent drawing


class AnchorType(Enum):
    LEAD_IN = "LEAD_IN"        # Drawing anticipates keyword, begins before speech
    DURING = "DURING"          # Drawing unfolds concurrently with speech phrase
    EMPHASIS = "EMPHASIS"      # Drawing completes precisely at keyword instant
    TRAILING = "TRAILING"      # Drawing completes slightly after speech concludes


class AnchorSourceType(Enum):
    NUMBER = "NUMBER"          # Quantities, statistics, percentages (e.g. "2%", "70")
    OBJECT = "OBJECT"          # Tangible entities (e.g. "سيارة", "character", "icon")
    CONCEPT = "CONCEPT"        # Abstract concepts / states (e.g. "إيرور", "خطورة", "ذكاء")
    ACTION = "ACTION"          # Verbs or state changes (e.g. "تتحرك", "انفجار")


class SpeedFeasibility(Enum):
    NORMAL = "NORMAL"          # 0.70x to 1.25x calibrated pen velocity
    FAST = "FAST"              # 1.25x to 1.75x calibrated pen velocity
    LIMITED = "LIMITED"        # 1.75x to 2.20x calibrated pen velocity (near physical limit)
    INFEASIBLE = "INFEASIBLE"  # > 2.20x calibrated pen velocity (requires resolution search)


class ConflictType(Enum):
    ANCHOR_CONFLICT = "ANCHOR_CONFLICT"                    # Anchor time cannot be met physically
    DRAWING_BUDGET_CONFLICT = "DRAWING_BUDGET_CONFLICT"    # Drawing workload exceeds total available time
    SPEED_CONFLICT = "SPEED_CONFLICT"                      # Pen speed exceeds physical safety limit
    TRANSITION_CONFLICT = "TRANSITION_CONFLICT"            # Inter-beat overlap clashes with hold requirement
    SEMANTIC_CONFLICT = "SEMANTIC_CONFLICT"                # Low confidence or contradictory semantic mapping


class ConflictSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class DrawingDemand:
    """
    Physical drawing workload of a visual element.
    Decoupled strictly from DrawingDuration (DrawingDemand != DrawingDuration).
    """
    arc_length_px: float = 0.0            # Total Euclidean stroke length: sum ||Δp||
    stroke_count: int = 1                 # Number of continuous stroke contours
    point_count: int = 100                # Total trajectory points
    geometric_complexity: float = 1.0     # Curvature and density factor: L_arc / sqrt(w * h)
    spatial_density: float = 1.0          # Stroke density across bounding box
    estimated_physical_effort: float = 0.0 # Non-dimensional physical effort score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arc_length_px": round(self.arc_length_px, 1),
            "stroke_count": self.stroke_count,
            "point_count": self.point_count,
            "geometric_complexity": round(self.geometric_complexity, 2),
            "spatial_density": round(self.spatial_density, 2),
            "estimated_physical_effort": round(self.estimated_physical_effort, 1)
        }


@dataclass
class TimingAllocation:
    """
    Temporal assignment produced by the Timing Solver for an element.
    """
    draw_duration: float = 0.0
    start: float = 0.0
    end: float = 0.0
    speed_multiplier: float = 1.0
    feasibility_status: SpeedFeasibility = SpeedFeasibility.NORMAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "draw_duration": round(self.draw_duration, 2),
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "speed_multiplier": round(self.speed_multiplier, 2),
            "feasibility_status": self.feasibility_status.value
        }


@dataclass
class SemanticAnchor:
    """
    Explicit anchor binding speech keywords to visual element reveals.
    """
    source: str = "speech"                              # Origin (speech / srt / script)
    source_text: str = ""                               # Complete context phrase
    source_token: str = ""                              # Exact target keyword/number (e.g. "2%")
    source_type: AnchorSourceType = AnchorSourceType.OBJECT
    target_element: str = ""                            # Element ID or name to reveal
    target_time: float = 0.0                            # Absolute time in seconds
    anchor_type: AnchorType = AnchorType.DURING
    confidence: float = 1.0                             # 0.0 to 1.0
    tolerance: float = 0.15                             # Permissible delta in seconds (+/-)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "source_text": self.source_text,
            "source_token": self.source_token,
            "source_type": self.source_type.value,
            "target_element": self.target_element,
            "target_time": round(self.target_time, 2),
            "anchor_type": self.anchor_type.value,
            "confidence": round(self.confidence, 2),
            "tolerance": round(self.tolerance, 2)
        }


@dataclass
class TimingConflict:
    """
    Explicit model for unresolvable or compromised timing situations.
    """
    conflict_type: ConflictType
    severity: ConflictSeverity = ConflictSeverity.MEDIUM
    affected_elements: List[str] = field(default_factory=list)
    description: str = ""
    resolution_attempted: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_type": self.conflict_type.value,
            "severity": self.severity.value,
            "affected_elements": self.affected_elements,
            "description": self.description,
            "resolution_attempted": self.resolution_attempted
        }


@dataclass
class BeatTransition:
    """
    Inter-Beat relationship governing the handoff between Beat A and Beat B.
    Decoupled from internal VisualBeat windows.
    """
    from_beat_id: str
    to_beat_id: str
    start: float
    end: float
    transition_type: TransitionPolicy = TransitionPolicy.KEEP
    strategy: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end - self.start, 3))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_beat_id": self.from_beat_id,
            "to_beat_id": self.to_beat_id,
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "duration": round(self.duration, 2),
            "transition_type": self.transition_type.value,
            "strategy": self.strategy
        }


@dataclass
class EmphasisPoint:
    """Backwards-compatible wrapper for keyword emphasis."""
    text: str                                    # Target word or number (e.g. "2%", "70", "خطورة")
    target_time: Optional[float] = None          # Absolute time in seconds when this keyword occurs
    element_id: Optional[str] = None             # ID of element that must be revealed at this point
    weight: float = 1.0                          # Semantic importance weight (1.0 to 3.0)


@dataclass
class TimingDecision:
    """
    Comprehensive record of solver's decision for each visual element.
    """
    element_id: str
    element_name: str
    tier: str
    start: float
    end: float
    duration: float
    hold_duration: float
    reason: str
    anticipation: float = 0.0
    speed_multiplier: float = 1.0
    demand: Optional[DrawingDemand] = None
    feasibility: SpeedFeasibility = SpeedFeasibility.NORMAL

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "element_id": self.element_id,
            "element_name": self.element_name,
            "tier": self.tier,
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "duration": round(self.duration, 2),
            "hold_duration": round(self.hold_duration, 2),
            "speed_multiplier": round(self.speed_multiplier, 2),
            "anticipation": round(self.anticipation, 2),
            "feasibility": self.feasibility.value,
            "reason": self.reason
        }
        if self.demand:
            res["demand"] = self.demand.to_dict()
        return res


@dataclass
class VisualBeat:
    id: str
    speech_beat_id: Optional[str] = None
    start: float = 0.0
    end: float = 0.0
    panel_id: Optional[int] = None
    elements: List[Dict[str, Any]] = field(default_factory=list)
    primary_elements: List[str] = field(default_factory=list)      # Names or IDs of primary objects
    secondary_elements: List[str] = field(default_factory=list)    # Names or IDs of secondary objects
    decorative_elements: List[str] = field(default_factory=list)   # Names or IDs of decorative objects
    emphasis_points: List[EmphasisPoint] = field(default_factory=list)
    semantic_anchors: List[SemanticAnchor] = field(default_factory=list)
    overlap_policy: OverlapPolicy = OverlapPolicy.NATURAL
    anticipation_window: float = 0.35                              # Seconds (0.0 to 0.6)
    hold_duration: float = 0.60                                    # Visibility rest period after draw
    transition_policy: TransitionPolicy = TransitionPolicy.KEEP
    timing_decisions: List[TimingDecision] = field(default_factory=list)
    timing_conflicts: List[TimingConflict] = field(default_factory=list)
    drawing_demands: Dict[str, DrawingDemand] = field(default_factory=dict)
    narrative_text: str = ""

    # Explicit 3-window model
    speech_window: Tuple[float, float] = (0.0, 0.0)
    drawing_window: Tuple[float, float] = (0.0, 0.0)
    hold_window: Tuple[float, float] = (0.0, 0.0)

    def __post_init__(self):
        self.start = float(round(self.start, 3))
        self.end = float(round(max(self.start + 0.1, self.end), 3))
        
        # Initialize 3-window model if not set
        if self.speech_window == (0.0, 0.0):
            self.speech_window = (self.start, self.end)
        if self.drawing_window == (0.0, 0.0):
            self.drawing_window = (self.start, self.end)
        if self.hold_window == (0.0, 0.0):
            self.hold_window = (self.end, round(self.end + self.hold_duration, 3))

    @property
    def duration(self) -> float:
        return max(0.1, round(self.end - self.start, 3))

    def get_element_tier(self, elem: Dict[str, Any]) -> ElementTier:
        """Determines tier dynamically based on lists or category heuristics."""
        e_id = elem.get("id", "")
        e_name = elem.get("name", "").lower()
        cat = elem.get("category", "").upper()

        if e_id in self.primary_elements or e_name in [p.lower() for p in self.primary_elements]:
            return ElementTier.PRIMARY
        if e_id in self.secondary_elements or e_name in [s.lower() for s in self.secondary_elements]:
            return ElementTier.SECONDARY
        if e_id in self.decorative_elements or e_name in [d.lower() for d in self.decorative_elements]:
            return ElementTier.DECORATIVE

        # Dynamic fallback by semantic category
        if cat in ("CHARACTER", "PORTRAIT", "FIGURE") or "character" in e_name or "person" in e_name:
            return ElementTier.PRIMARY
        if cat in ("TITLE", "CONTAINER_CARD", "EMOJI", "ICON_GRAPHIC", "TEXT_LINE") or "title" in e_name:
            return ElementTier.SECONDARY
        return ElementTier.DECORATIVE

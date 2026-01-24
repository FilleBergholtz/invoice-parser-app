"""Quality score model."""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class QualityScore:
    """Quality score for an invoice (0-100).
    
    Attributes:
        score: Overall quality score (0-100)
        status_penalty: Penalty from validation status
        missing_fields_penalty: Penalty from missing required/optional fields
        reconciliation_penalty: Penalty from sum mismatches
        wrap_complexity_penalty: Penalty from wrapped text complexity
        breakdown: Detailed breakdown of score components
    """
    
    score: float
    status_penalty: float = 0.0
    missing_fields_penalty: float = 0.0
    reconciliation_penalty: float = 0.0
    wrap_complexity_penalty: float = 0.0
    breakdown: Dict[str, Any] = None
    
    def __post_init__(self):
        """Validate score range."""
        if not 0.0 <= self.score <= 100.0:
            raise ValueError(f"score must be between 0.0 and 100.0, got {self.score}")
        
        if self.breakdown is None:
            self.breakdown = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "score": round(self.score, 2),
            "status_penalty": round(self.status_penalty, 2),
            "missing_fields_penalty": round(self.missing_fields_penalty, 2),
            "reconciliation_penalty": round(self.reconciliation_penalty, 2),
            "wrap_complexity_penalty": round(self.wrap_complexity_penalty, 2),
            "breakdown": self.breakdown
        }

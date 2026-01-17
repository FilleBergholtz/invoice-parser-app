"""Traceability evidence structure for critical fields."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Traceability:
    """Represents traceability evidence for extracted critical fields.
    
    Stores evidence (page number, bbox, text excerpt, tokens) for invoice number
    and total amount fields, enabling verification and trust.
    
    Attributes:
        field: Field name ("invoice_no" or "total")
        value: Extracted value as string
        confidence: Confidence score (0.0-1.0)
        evidence: Dict with page_number, bbox, row_index, text_excerpt, tokens
    """
    
    field: str
    value: str
    confidence: float
    evidence: Dict[str, Any]
    
    def __post_init__(self):
        """Validate traceability fields."""
        if self.field not in ["invoice_no", "total"]:
            raise ValueError(
                f"field must be 'invoice_no' or 'total', got '{self.field}'"
            )
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
        
        # Validate evidence structure
        required_keys = ["page_number", "bbox", "row_index", "text_excerpt", "tokens"]
        for key in required_keys:
            if key not in self.evidence:
                raise ValueError(f"evidence must contain '{key}'")
        
        # Validate bbox (list of 4 floats: x, y, width, height)
        bbox = self.evidence.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"evidence.bbox must be list of 4 floats [x, y, width, height]")
        
        # Validate tokens (list of dicts)
        tokens = self.evidence.get("tokens")
        if not isinstance(tokens, list):
            raise ValueError(f"evidence.tokens must be a list")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict matching 02-CONTEXT.md format.
        
        Returns:
            Dict with field, value, confidence, evidence structure
        """
        return {
            "field": self.field,
            "value": self.value,
            "confidence": self.confidence,
            "evidence": self.evidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Traceability:
        """Create Traceability from JSON dict.
        
        Args:
            data: Dict with field, value, confidence, evidence
            
        Returns:
            Traceability object
        """
        return cls(
            field=data["field"],
            value=data["value"],
            confidence=data["confidence"],
            evidence=data["evidence"]
        )

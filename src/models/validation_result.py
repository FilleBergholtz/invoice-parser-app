"""ValidationResult data model representing invoice validation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ValidationResult:
    """Validation result for an invoice.
    
    Attributes:
        status: Invoice status ("OK", "PARTIAL", or "REVIEW")
        lines_sum: Sum of all InvoiceLine.total_amount
        diff: total_amount - lines_sum (signed, None if total_amount is None)
        tolerance: Validation tolerance (1.0 SEK)
        hard_gate_passed: True if both confidences >= 0.95
        invoice_number_confidence: Confidence score for invoice number
        total_confidence: Confidence score for total amount
        errors: List of validation error messages
        warnings: List of validation warning messages
    """
    
    status: str
    lines_sum: float
    diff: Optional[float]
    tolerance: float = 1.0
    hard_gate_passed: bool = False
    invoice_number_confidence: float = 0.0
    total_confidence: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate ValidationResult fields."""
        if self.status not in ["OK", "PARTIAL", "REVIEW"]:
            raise ValueError(
                f"status must be 'OK', 'PARTIAL', or 'REVIEW', got '{self.status}'"
            )
        
        if self.lines_sum < 0:
            raise ValueError(
                f"lines_sum must be >= 0, got {self.lines_sum}"
            )
        
        if not 0.0 <= self.invoice_number_confidence <= 1.0:
            raise ValueError(
                f"invoice_number_confidence must be between 0.0 and 1.0, "
                f"got {self.invoice_number_confidence}"
            )
        
        if not 0.0 <= self.total_confidence <= 1.0:
            raise ValueError(
                f"total_confidence must be between 0.0 and 1.0, "
                f"got {self.total_confidence}"
            )

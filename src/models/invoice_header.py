"""InvoiceHeader data model representing extracted header data from invoice."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .segment import Segment
    from .traceability import Traceability


@dataclass
class InvoiceHeader:
    """Represents extracted header data from invoice.
    
    Attributes:
        segment: Reference to header segment
        invoice_number: Extracted invoice number or None
        invoice_number_confidence: Confidence score for invoice number (0.0-1.0)
        invoice_number_traceability: Traceability evidence for invoice number
        invoice_date: Extracted invoice date (normalized to ISO format) or None
        supplier_name: Vendor/company name or None (address out of scope Phase 2)
        supplier_address: Supplier address or None (deferred to later phase)
        customer_name: Customer name or None
        customer_address: Customer address or None
        reference: Fakturareferens/betalningsreferens or None (REF-01)
        raw_text: Concatenated text from header segment rows
        total_amount: Extracted total amount or None
        total_confidence: Confidence score for total amount (0.0-1.0)
        total_traceability: Traceability evidence for total amount
    """
    
    segment: Segment
    invoice_number: Optional[str] = None
    invoice_number_confidence: float = 0.0
    invoice_number_traceability: Optional[Traceability] = None
    invoice_date: Optional[date] = None
    supplier_name: Optional[str] = None
    supplier_address: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    reference: Optional[str] = None  # Fakturareferens/betalningsreferens (REF-01)
    raw_text: str = ""
    total_amount: Optional[float] = None
    total_confidence: float = 0.0
    total_traceability: Optional[Traceability] = None
    total_candidates: Optional[List[Dict[str, Any]]] = None
    
    def __post_init__(self):
        """Validate InvoiceHeader fields."""
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
        
        # Generate raw_text from segment rows if not provided
        if not self.raw_text and self.segment and self.segment.rows:
            self.raw_text = " ".join(row.text for row in self.segment.rows)
    
    def meets_hard_gate(self) -> bool:
        """Check if invoice meets hard gate requirements.
        
        Hard gate: invoice_number_confidence >= 0.95 AND total_confidence >= 0.95
        Returns True if both conditions met (OK status), False otherwise (REVIEW).
        
        Returns:
            True if hard gate passed (OK), False otherwise (REVIEW)
        """
        return (
            self.invoice_number_confidence >= 0.95 and
            self.total_confidence >= 0.95
        )

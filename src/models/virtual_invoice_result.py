"""VirtualInvoiceResult data model representing a single invoice extracted from a PDF."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .invoice_header import InvoiceHeader
from .invoice_line import InvoiceLine
from .validation_result import ValidationResult


@dataclass
class VirtualInvoiceResult:
    """Result for a single virtual invoice extracted from a PDF.
    
    Attributes:
        virtual_invoice_id: Unique identifier; extraherade fakturanummer när det finns, annars "{file_stem}__{index}"
        source_pdf: Source PDF filename
        virtual_invoice_index: Index of this invoice within the PDF (1-based)
        page_start: Starting page number for this invoice
        page_end: Ending page number for this invoice (inclusive)
        status: Invoice status ("OK", "PARTIAL", "REVIEW", or "FAILED")
        invoice_header: InvoiceHeader with extracted fields
        invoice_lines: List of InvoiceLine objects
        validation_result: ValidationResult with validation data
        error: Error message if processing failed
        extraction_source: When compare-extraction was used, "pdfplumber" or "ocr" for the chosen source
    """
    
    virtual_invoice_id: str
    source_pdf: str
    virtual_invoice_index: int
    page_start: int
    page_end: int
    status: str
    invoice_header: Optional[InvoiceHeader] = None
    invoice_lines: List[InvoiceLine] = field(default_factory=list)
    validation_result: Optional[ValidationResult] = None
    error: Optional[str] = None
    extraction_source: Optional[str] = None  # "pdfplumber" | "ocr" when --compare-extraction chose one
    
    @property
    def line_count(self) -> int:
        """Get number of invoice lines."""
        return len(self.invoice_lines)
    
    def __post_init__(self):
        """Validate VirtualInvoiceResult fields."""
        if self.status not in ["OK", "PARTIAL", "REVIEW", "FAILED"]:
            raise ValueError(
                f"status must be 'OK', 'PARTIAL', 'REVIEW', or 'FAILED', got '{self.status}'"
            )
        
        if self.virtual_invoice_index < 1:
            raise ValueError(
                f"virtual_invoice_index must be >= 1, got {self.virtual_invoice_index}"
            )
        
        if self.page_start < 1:
            raise ValueError(f"page_start must be >= 1, got {self.page_start}")
        
        if self.page_end < self.page_start:
            raise ValueError(
                f"page_end ({self.page_end}) must be >= page_start ({self.page_start})"
            )

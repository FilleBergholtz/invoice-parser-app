"""InvoiceLine data model representing a product row on an invoice."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .row import Row
    from .segment import Segment


@dataclass
class InvoiceLine:
    """Represents a product row on an invoice.
    
    Important: rows is KÄLLSANING (source of truth) for traceability.
    total_amount is the key identifier - rule: "rad med belopp = produktrad".
    
    Attributes:
        rows: List of Row objects that belong to this line item (KÄLLSANING)
        description: Product/service description
        quantity: Optional quantity
        unit: Optional unit (e.g., "st", "kg", "h", "m²")
        unit_price: Optional unit price
        discount: Optional discount (as decimal or amount)
        total_amount: Total amount for the line (REQUIRED - identifies product rows)
        vat_rate: Optional VAT rate for this line
        line_number: Line number for ordering
        segment: Reference to items segment
    """
    
    rows: List[Row]
    description: str
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    total_amount: Decimal = Decimal("0")
    vat_rate: Optional[Decimal] = None
    line_number: int = 0
    segment: Optional[Segment] = None
    
    def __post_init__(self):
        """Validate that InvoiceLine has required fields."""
        if not self.rows:
            raise ValueError("InvoiceLine must have at least one row")
        
        if self.total_amount <= 0:
            raise ValueError(
                f"InvoiceLine total_amount must be > 0 (rule: 'rad med belopp = produktrad'), "
                f"got {self.total_amount}"
            )

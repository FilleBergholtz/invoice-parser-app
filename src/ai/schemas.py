"""Request and response schemas for AI enrichment API."""

from dataclasses import dataclass, asdict
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any


@dataclass
class AIInvoiceLineRequest:
    """Invoice line item for AI request."""
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    discount: Optional[float] = None
    total_amount: Optional[float] = None
    line_number: Optional[int] = None


@dataclass
class AIInvoiceRequest:
    """Request payload for AI enrichment."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None  # ISO format date string
    supplier_name: Optional[str] = None
    customer_name: Optional[str] = None
    total_amount: Optional[float] = None
    line_items: List[AIInvoiceLineRequest] = None
    
    def __post_init__(self):
        if self.line_items is None:
            self.line_items = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert date to string if present
        if data.get('invoice_date') and isinstance(data['invoice_date'], date):
            data['invoice_date'] = data['invoice_date'].isoformat()
        return _sanitize_decimals(data)


def _sanitize_decimals(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_decimals(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_decimals(v) for v in value]
    if isinstance(value, Decimal):
        return float(value)
    return value


@dataclass
class AIInvoiceLineResponse:
    """AI-enriched invoice line item."""
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    discount: Optional[float] = None
    total_amount: Optional[float] = None
    line_number: Optional[int] = None
    # AI-specific fields
    confidence: Optional[float] = None
    suggestions: Optional[List[str]] = None
    category: Optional[str] = None


@dataclass
class AIInvoiceResponse:
    """Response payload from AI enrichment."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    supplier_name: Optional[str] = None
    customer_name: Optional[str] = None
    total_amount: Optional[float] = None
    line_items: List[AIInvoiceLineResponse] = None
    # AI-specific fields
    confidence: Optional[float] = None
    warnings: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.line_items is None:
            self.line_items = []
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIInvoiceResponse':
        """Create from dictionary (e.g., from JSON response)."""
        line_items = None
        if 'line_items' in data and data['line_items']:
            line_items = [AIInvoiceLineResponse(**item) for item in data['line_items']]
        
        return cls(
            invoice_number=data.get('invoice_number'),
            invoice_date=data.get('invoice_date'),
            supplier_name=data.get('supplier_name'),
            customer_name=data.get('customer_name'),
            total_amount=data.get('total_amount'),
            line_items=line_items,
            confidence=data.get('confidence'),
            warnings=data.get('warnings'),
            suggestions=data.get('suggestions')
        )

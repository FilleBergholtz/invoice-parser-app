"""API request and response models."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class InvoiceProcessResponse(BaseModel):
    """Response model for invoice processing endpoint."""
    
    invoice_id: str = Field(..., description="Unique invoice identifier")
    status: str = Field(..., description="Processing status: OK, PARTIAL, REVIEW, or FAILED")
    line_count: int = Field(..., description="Number of line items extracted")
    message: Optional[str] = Field(None, description="Optional message or error description")


class InvoiceStatusResponse(BaseModel):
    """Response model for invoice status endpoint."""
    
    invoice_id: str
    status: str
    invoice_number: Optional[str] = None
    total_amount: Optional[float] = None
    line_count: int
    invoice_number_confidence: float = 0.0
    total_confidence: float = 0.0


class InvoiceLineResponse(BaseModel):
    """Response model for a single invoice line item."""
    
    line_number: int
    description: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    discount: Optional[float] = None
    total_amount: float
    vat_rate: Optional[float] = None


class InvoiceResultResponse(BaseModel):
    """Response model for invoice result endpoint."""
    
    invoice_id: str
    status: str
    filename: str
    
    # Header fields
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    vendor_name: Optional[str] = None
    total_amount: Optional[float] = None
    invoice_number_confidence: float = 0.0
    total_confidence: float = 0.0
    
    # Validation
    lines_sum: float = 0.0
    diff: Optional[float] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # Line items
    line_items: List[InvoiceLineResponse] = Field(default_factory=list)
    
    # Error (if failed)
    error: Optional[str] = None


class BatchProcessResponse(BaseModel):
    """Response model for batch processing endpoint."""
    
    total: int = Field(..., description="Total number of invoices processed")
    results: List[InvoiceProcessResponse] = Field(..., description="Results for each invoice")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Optional error details")

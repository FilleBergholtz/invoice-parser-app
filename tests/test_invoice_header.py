"""Unit tests for InvoiceHeader model."""

import pytest
from datetime import date
from src.models.document import Document
from src.models.page import Page
from src.models.row import Row
from src.models.segment import Segment
from src.models.token import Token
from src.models.traceability import Traceability
from src.models.invoice_header import InvoiceHeader


@pytest.fixture
def sample_segment():
    """Create a sample header Segment for testing."""
    doc = Document(
        filename="test.pdf",
        filepath="/path/to/test.pdf",
        page_count=1,
        pages=[],
        metadata={}
    )
    
    page = Page(
        page_number=1,
        document=doc,
        width=595.0,
        height=842.0,
        tokens=[],
        rendered_image_path=None
    )
    
    doc.pages = [page]
    
    # Create header rows
    token1 = Token(text="Fakturanummer", x=10, y=50, width=80, height=12, page=page)
    token2 = Token(text="INV-001", x=100, y=50, width=60, height=12, page=page)
    
    row1 = Row(
        tokens=[token1, token2],
        y=50,
        x_min=10,
        x_max=160,
        text="Fakturanummer INV-001",
        page=page
    )
    
    segment = Segment(
        segment_type="header",
        rows=[row1],
        y_min=50,
        y_max=50,
        page=page
    )
    
    return segment


def test_invoice_header_creation(sample_segment):
    """Test InvoiceHeader creation with segment reference."""
    header = InvoiceHeader(segment=sample_segment)
    
    assert header.segment == sample_segment
    assert header.invoice_number is None
    assert header.invoice_number_confidence == 0.0
    assert header.total_confidence == 0.0
    assert header.raw_text == "Fakturanummer INV-001"  # Generated from segment rows


def test_invoice_header_confidence_defaults(sample_segment):
    """Test that confidence scores default to 0.0."""
    header = InvoiceHeader(segment=sample_segment)
    
    assert header.invoice_number_confidence == 0.0
    assert header.total_confidence == 0.0


def test_invoice_header_traceability_optional(sample_segment):
    """Test that traceability fields are Optional (can be None)."""
    header = InvoiceHeader(segment=sample_segment)
    
    assert header.invoice_number_traceability is None
    assert header.total_traceability is None


def test_invoice_header_with_extracted_fields(sample_segment):
    """Test InvoiceHeader with extracted invoice number and confidence."""
    evidence = {
        "page_number": 1,
        "bbox": [100.0, 50.0, 90.0, 12.0],
        "row_index": 0,
        "text_excerpt": "Fakturanummer INV-001",
        "tokens": []
    }
    
    traceability = Traceability(
        field="invoice_no",
        value="INV-001",
        confidence=0.98,
        evidence=evidence
    )
    
    header = InvoiceHeader(
        segment=sample_segment,
        invoice_number="INV-001",
        invoice_number_confidence=0.98,
        invoice_number_traceability=traceability
    )
    
    assert header.invoice_number == "INV-001"
    assert header.invoice_number_confidence == 0.98
    assert header.invoice_number_traceability == traceability


def test_invoice_header_meets_hard_gate(sample_segment):
    """Test hard gate evaluation (≥0.95 for both invoice number and total)."""
    # Both meet threshold → OK
    header1 = InvoiceHeader(
        segment=sample_segment,
        invoice_number_confidence=0.96,
        total_confidence=0.97
    )
    assert header1.meets_hard_gate() is True
    
    # Invoice number below threshold → REVIEW
    header2 = InvoiceHeader(
        segment=sample_segment,
        invoice_number_confidence=0.90,
        total_confidence=0.97
    )
    assert header2.meets_hard_gate() is False
    
    # Total below threshold → REVIEW
    header3 = InvoiceHeader(
        segment=sample_segment,
        invoice_number_confidence=0.97,
        total_confidence=0.92
    )
    assert header3.meets_hard_gate() is False
    
    # Both below threshold → REVIEW
    header4 = InvoiceHeader(
        segment=sample_segment,
        invoice_number_confidence=0.90,
        total_confidence=0.92
    )
    assert header4.meets_hard_gate() is False


def test_invoice_header_confidence_range_validation(sample_segment):
    """Test that confidence scores must be between 0.0 and 1.0."""
    # Valid confidence
    header1 = InvoiceHeader(segment=sample_segment, invoice_number_confidence=0.5)
    assert header1.invoice_number_confidence == 0.5
    
    # Invalid confidence (> 1.0)
    with pytest.raises(ValueError, match="invoice_number_confidence must be between"):
        InvoiceHeader(segment=sample_segment, invoice_number_confidence=1.5)
    
    # Invalid confidence (< 0.0)
    with pytest.raises(ValueError, match="invoice_number_confidence must be between"):
        InvoiceHeader(segment=sample_segment, invoice_number_confidence=-0.1)
    
    # Invalid total_confidence
    with pytest.raises(ValueError, match="total_confidence must be between"):
        InvoiceHeader(segment=sample_segment, total_confidence=1.5)


def test_invoice_header_date_normalization(sample_segment):
    """Test that invoice_date can be set as datetime.date."""
    header = InvoiceHeader(
        segment=sample_segment,
        invoice_date=date(2024, 1, 15)
    )
    
    assert header.invoice_date == date(2024, 1, 15)
    assert header.invoice_date.isoformat() == "2024-01-15"  # ISO format

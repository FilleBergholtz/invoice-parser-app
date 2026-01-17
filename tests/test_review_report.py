"""Unit tests for review report generation."""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.export.review_report import create_review_report
from src.models.invoice_header import InvoiceHeader
from src.models.validation_result import ValidationResult


@pytest.fixture
def mock_segment():
    """Create a mock segment for InvoiceHeader."""
    from src.models.page import Page
    from src.models.document import Document
    from src.models.token import Token
    from src.models.row import Row
    from src.models.segment import Segment
    
    doc = Document(filename="test.pdf", filepath="test.pdf", page_count=0, pages=[])
    page = Page(page_number=1, width=612, height=792, document=doc)
    doc.pages.append(page)
    doc.page_count = 1
    
    token = Token(text="Header", x=0, y=50, width=60, height=12, page=page)
    row = Row(tokens=[token], text="Header row", x_min=0, x_max=200, y=50, page=page)
    segment = Segment(segment_type="header", rows=[row], page=page, y_min=0.0, y_max=237.6)
    return segment


@pytest.fixture
def sample_invoice_header(mock_segment):
    """Create sample InvoiceHeader for testing."""
    from datetime import date
    
    header = InvoiceHeader(
        segment=mock_segment,
        invoice_number="INV-001",
        invoice_number_confidence=0.90,
        total_amount=100.0,
        total_confidence=0.85,
        supplier_name="Test Company",
        invoice_date=date(2024, 1, 15)
    )
    return header


@pytest.fixture
def sample_validation_result():
    """Create sample ValidationResult for testing."""
    return ValidationResult(
        status="REVIEW",
        lines_sum=100.0,
        diff=0.0,
        hard_gate_passed=False,
        invoice_number_confidence=0.90,
        total_confidence=0.85,
        errors=["Hard gate failed"],
        warnings=[]
    )


def test_review_folder_creation(sample_invoice_header, sample_validation_result, tmp_path):
    """Test that review folder is created at correct path."""
    pdf_path = tmp_path / "test_invoice.pdf"
    pdf_path.write_bytes(b"fake pdf content")
    
    review_folder = create_review_report(
        sample_invoice_header,
        sample_validation_result,
        [],
        str(pdf_path),
        tmp_path
    )
    
    assert review_folder.exists()
    assert review_folder.name == "test_invoice"
    assert review_folder.parent == tmp_path / "review"


def test_pdf_copying(sample_invoice_header, sample_validation_result, tmp_path):
    """Test that PDF is copied to review folder."""
    pdf_path = tmp_path / "test_invoice.pdf"
    pdf_path.write_bytes(b"fake pdf content")
    
    review_folder = create_review_report(
        sample_invoice_header,
        sample_validation_result,
        [],
        str(pdf_path),
        tmp_path
    )
    
    review_pdf = review_folder / "test_invoice.pdf"
    assert review_pdf.exists()
    assert review_pdf.read_bytes() == b"fake pdf content"


def test_metadata_json_structure(sample_invoice_header, sample_validation_result, tmp_path):
    """Test that metadata.json has correct structure."""
    pdf_path = tmp_path / "test_invoice.pdf"
    pdf_path.write_bytes(b"fake pdf content")
    
    review_folder = create_review_report(
        sample_invoice_header,
        sample_validation_result,
        [],
        str(pdf_path),
        tmp_path
    )
    
    metadata_path = review_folder / "metadata.json"
    assert metadata_path.exists()
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Verify structure
    assert "invoice_header" in metadata
    assert "validation" in metadata
    assert "timestamp" in metadata
    
    # Verify invoice_header fields
    header = metadata["invoice_header"]
    assert header["invoice_number"] == "INV-001"
    assert header["invoice_number_confidence"] == 0.90
    assert header["total_amount"] == 100.0
    assert header["supplier_name"] == "Test Company"
    assert header["invoice_date"] == "2024-01-15"
    
    # Verify validation fields
    validation = metadata["validation"]
    assert validation["status"] == "REVIEW"
    assert validation["lines_sum"] == 100.0
    assert validation["errors"] == ["Hard gate failed"]


def test_date_serialization(sample_invoice_header, sample_validation_result, tmp_path):
    """Test that invoice_date is serialized as ISO format string."""
    pdf_path = tmp_path / "test_invoice.pdf"
    pdf_path.write_bytes(b"fake pdf content")
    
    review_folder = create_review_report(
        sample_invoice_header,
        sample_validation_result,
        [],
        str(pdf_path),
        tmp_path
    )
    
    metadata_path = review_folder / "metadata.json"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Verify date is ISO format string
    assert metadata["invoice_header"]["invoice_date"] == "2024-01-15"
    assert isinstance(metadata["invoice_header"]["invoice_date"], str)


def test_date_none_handling(mock_segment, sample_validation_result, tmp_path):
    """Test that None invoice_date is handled correctly."""
    header = InvoiceHeader(
        segment=mock_segment,
        invoice_number="INV-001",
        invoice_number_confidence=0.90,
        total_amount=100.0,
        total_confidence=0.85,
        invoice_date=None
    )
    
    pdf_path = tmp_path / "test_invoice.pdf"
    pdf_path.write_bytes(b"fake pdf content")
    
    review_folder = create_review_report(
        header,
        sample_validation_result,
        [],
        str(pdf_path),
        tmp_path
    )
    
    metadata_path = review_folder / "metadata.json"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    assert metadata["invoice_header"]["invoice_date"] is None


def test_traceability_serialization(mock_segment, sample_validation_result, tmp_path):
    """Test that Traceability objects are serialized using to_dict()."""
    from src.models.traceability import Traceability
    
    traceability = Traceability(
        field="invoice_no",
        value="INV-001",
        confidence=0.90,
        evidence={
            "page_number": 1,
            "bbox": [10, 20, 100, 12],
            "row_index": 0,
            "text_excerpt": "Fakturanummer INV-001",
            "tokens": []
        }
    )
    
    header = InvoiceHeader(
        segment=mock_segment,
        invoice_number="INV-001",
        invoice_number_confidence=0.90,
        invoice_number_traceability=traceability,
        total_amount=100.0,
        total_confidence=0.85
    )
    
    pdf_path = tmp_path / "test_invoice.pdf"
    pdf_path.write_bytes(b"fake pdf content")
    
    review_folder = create_review_report(
        header,
        sample_validation_result,
        [],
        str(pdf_path),
        tmp_path
    )
    
    metadata_path = review_folder / "metadata.json"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Verify traceability is serialized
    assert metadata["invoice_header"]["invoice_number_traceability"] is not None
    assert metadata["invoice_header"]["invoice_number_traceability"]["field"] == "invoice_no"
    assert metadata["invoice_header"]["invoice_number_traceability"]["value"] == "INV-001"


def test_line_count_in_metadata(sample_invoice_header, sample_validation_result, tmp_path):
    """Test that line_count is included in validation metadata."""
    from src.models.invoice_line import InvoiceLine
    from src.models.row import Row
    from src.models.token import Token
    from src.models.segment import Segment
    
    # Create sample invoice lines
    doc = sample_invoice_header.segment.page.document
    page = sample_invoice_header.segment.page
    token1 = Token(text="Product", x=0, y=100, width=60, height=12, page=page)
    row1 = Row(tokens=[token1], text="Product 1", x_min=0, x_max=200, y=100, page=page)
    segment = Segment(segment_type="items", rows=[row1], page=page, y_min=237.6, y_max=554.4)
    line1 = InvoiceLine(rows=[row1], description="Product 1", total_amount=60.0, line_number=1, segment=segment)
    line2 = InvoiceLine(rows=[row1], description="Product 2", total_amount=40.0, line_number=2, segment=segment)
    
    pdf_path = tmp_path / "test_invoice.pdf"
    pdf_path.write_bytes(b"fake pdf content")
    
    review_folder = create_review_report(
        sample_invoice_header,
        sample_validation_result,
        [line1, line2],
        str(pdf_path),
        tmp_path
    )
    
    metadata_path = review_folder / "metadata.json"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    assert metadata["validation"]["line_count"] == 2


def test_pdf_copy_error_handling(sample_invoice_header, sample_validation_result, tmp_path):
    """Test that function continues even if PDF copy fails."""
    # Use non-existent PDF path
    pdf_path = tmp_path / "nonexistent.pdf"
    
    # Should not raise exception, just log warning
    review_folder = create_review_report(
        sample_invoice_header,
        sample_validation_result,
        [],
        str(pdf_path),
        tmp_path
    )
    
    # Folder should still be created
    assert review_folder.exists()
    # Metadata should still be written
    metadata_path = review_folder / "metadata.json"
    assert metadata_path.exists()

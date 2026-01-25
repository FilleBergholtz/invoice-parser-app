"""Unit tests for footer extractor and total amount confidence scoring."""

import pytest
from src.models.document import Document
from src.models.page import Page
from src.models.row import Row
from src.models.segment import Segment
from src.models.token import Token
from src.models.invoice_header import InvoiceHeader
from src.models.invoice_line import InvoiceLine
from src.models.traceability import Traceability
from src.pipeline.footer_extractor import extract_total_amount
from src.pipeline.confidence_scoring import score_total_amount_candidate, validate_total_against_line_items


@pytest.fixture
def sample_page():
    """Create a sample Page for testing."""
    doc = Document(
        filename="test.pdf",
        filepath="/path/to/test.pdf",
        page_count=0,
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
    return page


@pytest.fixture
def sample_footer_segment(sample_page):
    """Create a sample footer segment with total amount."""
    # Footer row with "Totalt: 500.00"
    tokens = [
        Token(text="Totalt", x=400, y=750, width=50, height=12, page=sample_page),
        Token(text="500.00", x=500, y=750, width=60, height=12, page=sample_page),
    ]
    
    row = Row(
        tokens=tokens,
        y=750,
        x_min=400,
        x_max=560,
        text="Totalt 500.00",
        page=sample_page
    )
    
    segment = Segment(
        segment_type="footer",
        rows=[row],
        y_min=750,
        y_max=750,
        page=sample_page
    )
    
    return segment


def _make_line_items(sample_page, totals):
    """Bygg minimala InvoiceLine med given total_amount per rad."""
    rows = []
    for i, amount in enumerate(totals, start=1):
        t = Token(text=f"x{i}", x=50, y=200 + i * 20, width=30, height=12, page=sample_page)
        r = Row(tokens=[t], text=f"Rad {i}", x_min=50, x_max=200, y=200 + i * 20, page=sample_page)
        rows.append(r)
    segment = Segment(
        segment_type="items",
        rows=rows,
        y_min=200,
        y_max=200 + len(rows) * 20,
        page=sample_page
    )
    return [
        InvoiceLine(rows=[r], description=f"Rad {i}", total_amount=float(amt), line_number=i, segment=segment)
        for i, (r, amt) in enumerate(zip(rows, totals), start=1)
    ]


@pytest.fixture(autouse=True)
def _disable_calibration_learning_ai(monkeypatch):
    """Disable calibration, learning, and AI so tests verify raw extraction only.
    Avoids dependence on configs/calibration_model.joblib mapping heuristic scores to 0.
    """
    monkeypatch.setenv("CALIBRATION_ENABLED", "false")
    monkeypatch.setenv("LEARNING_ENABLED", "false")
    monkeypatch.setenv("AI_ENABLED", "false")


def test_extract_total_amount_from_footer(sample_footer_segment, sample_page):
    """Test total amount extraction from footer segment."""
    # Create InvoiceHeader with dummy row
    dummy_token = Token(text="dummy", x=0, y=0, width=10, height=10, page=sample_page)
    dummy_row = Row(tokens=[dummy_token], text="dummy", x_min=0, x_max=0, y=0, page=sample_page)
    header_segment = Segment(
        segment_type="header",
        rows=[dummy_row],
        y_min=0,
        y_max=100,
        page=sample_page
    )
    invoice_header = InvoiceHeader(segment=header_segment)
    
    # Extract total amount
    extract_total_amount(sample_footer_segment, [], invoice_header)
    
    # Should extract total amount
    assert invoice_header.total_amount == 500.00
    assert invoice_header.total_confidence > 0.0
    assert invoice_header.total_traceability is not None


def test_mathematical_validation(sample_page):
    """Test mathematical validation against line item sums."""
    # Ingen radsumma ger False
    assert validate_total_against_line_items(100.0, [], tolerance=1.0) is False

    # Summa 60+40=100, total 100 → inom tolerance 1.0
    line_items = _make_line_items(sample_page, [60.0, 40.0])
    assert validate_total_against_line_items(100.0, line_items, tolerance=1.0) is True
    assert validate_total_against_line_items(100.0, line_items, tolerance=0.0) is True

    # Total 99 eller 101 inom tolerance 1.0
    assert validate_total_against_line_items(99.0, line_items, tolerance=1.0) is True
    assert validate_total_against_line_items(101.0, line_items, tolerance=1.0) is True

    # Total 98 utanför tolerance 1.0
    assert validate_total_against_line_items(98.0, line_items, tolerance=1.0) is False


def test_traceability_created_for_total(sample_footer_segment, sample_page):
    """Test that traceability evidence is created for total amount."""
    dummy_token = Token(text="dummy", x=0, y=0, width=10, height=10, page=sample_page)
    dummy_row = Row(tokens=[dummy_token], text="dummy", x_min=0, x_max=0, y=0, page=sample_page)
    header_segment = Segment(
        segment_type="header",
        rows=[dummy_row],
        y_min=0,
        y_max=100,
        page=sample_page
    )
    invoice_header = InvoiceHeader(segment=header_segment)
    
    extract_total_amount(sample_footer_segment, [], invoice_header)
    
    # Check traceability structure
    assert invoice_header.total_traceability is not None
    assert invoice_header.total_traceability.field == "total"
    assert invoice_header.total_traceability.evidence["page_number"] == 1
    assert "bbox" in invoice_header.total_traceability.evidence
    assert "text_excerpt" in invoice_header.total_traceability.evidence
    assert "tokens" in invoice_header.total_traceability.evidence


def test_no_footer_segment_review(sample_page):
    """Test that missing footer segment results in REVIEW (confidence = 0.0)."""
    dummy_token = Token(text="dummy", x=0, y=0, width=10, height=10, page=sample_page)
    dummy_row = Row(tokens=[dummy_token], text="dummy", x_min=0, x_max=0, y=0, page=sample_page)
    header_segment = Segment(
        segment_type="header",
        rows=[dummy_row],
        y_min=0,
        y_max=100,
        page=sample_page
    )
    invoice_header = InvoiceHeader(segment=header_segment)
    
    # No footer segment
    extract_total_amount(None, [], invoice_header)
    
    assert invoice_header.total_confidence == 0.0
    assert invoice_header.total_amount is None
    assert invoice_header.total_traceability is None

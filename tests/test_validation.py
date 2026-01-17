"""Unit tests for validation logic."""

import pytest

from src.models.invoice_header import InvoiceHeader
from src.models.invoice_line import InvoiceLine
from src.models.row import Row
from src.models.segment import Segment
from src.models.validation_result import ValidationResult
from src.pipeline.validation import calculate_validation_values, validate_invoice


@pytest.fixture
def mock_segment():
    """Create a mock segment for InvoiceHeader."""
    from src.models.page import Page
    from src.models.document import Document
    
    doc = Document(filename="test.pdf", filepath="test.pdf", page_count=0, pages=[])
    page = Page(page_number=1, width=612, height=792, document=doc)
    doc.pages.append(page)
    doc.page_count = 1
    from src.models.token import Token
    token = Token(text="Header", x=0, y=50, width=60, height=12, page=page)
    row = Row(tokens=[token], text="Header row", x_min=0, x_max=200, y=50, page=page)
    segment = Segment(segment_type="header", rows=[row], page=page, y_min=0.0, y_max=237.6)
    return segment


@pytest.fixture
def invoice_header_high_confidence(mock_segment):
    """Create InvoiceHeader with high confidence (passes hard gate)."""
    header = InvoiceHeader(
        segment=mock_segment,
        invoice_number="INV-001",
        invoice_number_confidence=0.96,
        total_amount=100.0,
        total_confidence=0.97
    )
    return header


@pytest.fixture
def invoice_header_low_confidence(mock_segment):
    """Create InvoiceHeader with low confidence (fails hard gate)."""
    header = InvoiceHeader(
        segment=mock_segment,
        invoice_number="INV-001",
        invoice_number_confidence=0.90,
        total_amount=100.0,
        total_confidence=0.92
    )
    return header


@pytest.fixture
def invoice_header_no_total(mock_segment):
    """Create InvoiceHeader with no total_amount."""
    header = InvoiceHeader(
        segment=mock_segment,
        invoice_number="INV-001",
        invoice_number_confidence=0.96,
        total_amount=None,
        total_confidence=0.97
    )
    return header


@pytest.fixture
def invoice_lines_valid():
    """Create invoice lines that sum correctly."""
    from src.models.page import Page
    from src.models.document import Document
    
    doc = Document(filename="test.pdf", filepath="test.pdf", page_count=0, pages=[])
    page = Page(page_number=1, width=612, height=792, document=doc)
    doc.pages.append(page)
    doc.page_count = 1
    from src.models.token import Token
    token1 = Token(text="Product", x=0, y=100, width=60, height=12, page=page)
    token2 = Token(text="Product", x=0, y=120, width=60, height=12, page=page)
    row1 = Row(tokens=[token1], text="Product 1", x_min=0, x_max=200, y=100, page=page)
    row2 = Row(tokens=[token2], text="Product 2", x_min=0, x_max=200, y=120, page=page)
    segment = Segment(segment_type="items", rows=[row1, row2], page=page, y_min=237.6, y_max=554.4)
    
    return [
        InvoiceLine(rows=[row1], description="Product 1", total_amount=60.0, line_number=1, segment=segment),
        InvoiceLine(rows=[row2], description="Product 2", total_amount=40.0, line_number=2, segment=segment),
    ]


@pytest.fixture
def invoice_lines_mismatch():
    """Create invoice lines that don't sum correctly."""
    from src.models.page import Page
    from src.models.document import Document
    
    doc = Document(filename="test.pdf", filepath="test.pdf", page_count=0, pages=[])
    page = Page(page_number=1, width=612, height=792, document=doc)
    doc.pages.append(page)
    doc.page_count = 1
    from src.models.token import Token
    token1 = Token(text="Product", x=0, y=100, width=60, height=12, page=page)
    row1 = Row(tokens=[token1], text="Product 1", x_min=0, x_max=200, y=100, page=page)
    segment = Segment(segment_type="items", rows=[row1], page=page, y_min=237.6, y_max=554.4)
    
    return [
        InvoiceLine(rows=[row1], description="Product 1", total_amount=60.0, line_number=1, segment=segment),
    ]


class TestValidationResult:
    """Tests for ValidationResult model."""
    
    def test_creation_with_all_fields(self):
        """Test ValidationResult creation with all fields."""
        result = ValidationResult(
            status="OK",
            lines_sum=100.0,
            diff=0.0,
            tolerance=1.0,
            hard_gate_passed=True,
            invoice_number_confidence=0.96,
            total_confidence=0.97,
            errors=[],
            warnings=[]
        )
        
        assert result.status == "OK"
        assert result.lines_sum == 100.0
        assert result.diff == 0.0
        assert result.tolerance == 1.0
        assert result.hard_gate_passed is True
        assert result.invoice_number_confidence == 0.96
        assert result.total_confidence == 0.97
        assert result.errors == []
        assert result.warnings == []
    
    def test_default_values(self):
        """Test ValidationResult default values."""
        result = ValidationResult(
            status="OK",
            lines_sum=100.0,
            diff=0.0
        )
        
        assert result.tolerance == 1.0
        assert result.hard_gate_passed is False
        assert result.invoice_number_confidence == 0.0
        assert result.total_confidence == 0.0
        assert result.errors == []
        assert result.warnings == []
    
    def test_status_validation(self):
        """Test that status must be OK, PARTIAL, or REVIEW."""
        with pytest.raises(ValueError, match="status must be 'OK', 'PARTIAL', or 'REVIEW'"):
            ValidationResult(status="INVALID", lines_sum=100.0, diff=0.0)
    
    def test_lines_sum_validation(self):
        """Test that lines_sum must be >= 0."""
        with pytest.raises(ValueError, match="lines_sum must be >= 0"):
            ValidationResult(status="OK", lines_sum=-10.0, diff=0.0)
    
    def test_confidence_validation(self):
        """Test that confidence scores must be 0.0-1.0."""
        with pytest.raises(ValueError, match="invoice_number_confidence must be between 0.0 and 1.0"):
            ValidationResult(status="OK", lines_sum=100.0, diff=0.0, invoice_number_confidence=1.5)
        
        with pytest.raises(ValueError, match="total_confidence must be between 0.0 and 1.0"):
            ValidationResult(status="OK", lines_sum=100.0, diff=0.0, total_confidence=-0.1)


class TestCalculateValidationValues:
    """Tests for calculate_validation_values helper."""
    
    def test_with_total_and_lines(self, invoice_lines_valid):
        """Test calculation with total_amount and line_items."""
        lines_sum, diff, validation_passed = calculate_validation_values(
            100.0,
            invoice_lines_valid,
            tolerance=1.0
        )
        
        assert lines_sum == 100.0  # 60 + 40
        assert diff == 0.0  # 100 - 100
        assert validation_passed is True
    
    def test_with_total_none(self, invoice_lines_valid):
        """Test calculation with total_amount None."""
        lines_sum, diff, validation_passed = calculate_validation_values(
            None,
            invoice_lines_valid,
            tolerance=1.0
        )
        
        assert lines_sum == 100.0
        assert diff is None
        assert validation_passed is False
    
    def test_with_empty_line_items(self):
        """Test calculation with empty line_items."""
        lines_sum, diff, validation_passed = calculate_validation_values(
            100.0,
            [],
            tolerance=1.0
        )
        
        assert lines_sum == 0.0
        assert diff == 100.0  # 100 - 0
        assert validation_passed is False
    
    def test_with_tolerance(self, invoice_lines_valid):
        """Test tolerance handling."""
        # Within tolerance (±1.0)
        _, diff, validation_passed = calculate_validation_values(
            100.5,
            invoice_lines_valid,
            tolerance=1.0
        )
        assert abs(diff) == 0.5
        assert validation_passed is True
        
        # Outside tolerance
        _, diff, validation_passed = calculate_validation_values(
            102.0,
            invoice_lines_valid,
            tolerance=1.0
        )
        assert abs(diff) == 2.0
        assert validation_passed is False


class TestValidateInvoice:
    """Tests for validate_invoice function."""
    
    def test_ok_status(self, invoice_header_high_confidence, invoice_lines_valid):
        """Test OK status: hard gate pass + diff <= ±1 SEK."""
        result = validate_invoice(invoice_header_high_confidence, invoice_lines_valid)
        
        assert result.status == "OK"
        assert result.hard_gate_passed is True
        assert result.lines_sum == 100.0
        assert result.diff == 0.0
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_partial_status(self, invoice_header_high_confidence, invoice_lines_mismatch):
        """Test PARTIAL status: hard gate pass + diff > ±1 SEK."""
        # Set total to 100 but lines sum to 60 (diff = 40)
        invoice_header_high_confidence.total_amount = 100.0
        
        result = validate_invoice(invoice_header_high_confidence, invoice_lines_mismatch)
        
        assert result.status == "PARTIAL"
        assert result.hard_gate_passed is True
        assert result.lines_sum == 60.0
        assert result.diff == 40.0
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert "Sum mismatch" in result.warnings[0]
    
    def test_review_status_hard_gate_fail(self, invoice_header_low_confidence, invoice_lines_valid):
        """Test REVIEW status: hard gate fail (low confidence)."""
        result = validate_invoice(invoice_header_low_confidence, invoice_lines_valid)
        
        assert result.status == "REVIEW"
        assert result.hard_gate_passed is False
        assert len(result.errors) == 1
        assert "Hard gate failed" in result.errors[0]
    
    def test_review_status_total_none(self, invoice_header_no_total, invoice_lines_valid):
        """Test REVIEW status: total_amount None (cannot validate)."""
        result = validate_invoice(invoice_header_no_total, invoice_lines_valid)
        
        assert result.status == "REVIEW"
        assert result.diff is None
        assert len(result.errors) == 1
        assert "Total amount not extracted" in result.errors[0]
    
    def test_review_status_no_lines(self, invoice_header_high_confidence):
        """Test REVIEW status: no line_items (cannot validate)."""
        result = validate_invoice(invoice_header_high_confidence, [])
        
        assert result.status == "REVIEW"
        assert result.lines_sum == 0.0
        assert len(result.errors) == 1
        assert "No invoice lines extracted" in result.errors[0]
    
    def test_review_status_invoice_number_low(self, mock_segment, invoice_lines_valid):
        """Test REVIEW: invoice_number confidence >= 0.95 but total < 0.95."""
        header = InvoiceHeader(
            segment=mock_segment,
            invoice_number="INV-001",
            invoice_number_confidence=0.96,
            total_amount=100.0,
            total_confidence=0.92  # Below 0.95
        )
        
        result = validate_invoice(header, invoice_lines_valid)
        
        assert result.status == "REVIEW"
        assert result.hard_gate_passed is False
    
    def test_review_status_total_low(self, mock_segment, invoice_lines_valid):
        """Test REVIEW: total confidence >= 0.95 but invoice_number < 0.95."""
        header = InvoiceHeader(
            segment=mock_segment,
            invoice_number="INV-001",
            invoice_number_confidence=0.92,  # Below 0.95
            total_amount=100.0,
            total_confidence=0.96
        )
        
        result = validate_invoice(header, invoice_lines_valid)
        
        assert result.status == "REVIEW"
        assert result.hard_gate_passed is False

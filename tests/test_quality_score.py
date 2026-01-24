"""Unit tests for quality score calculation."""

import pytest

from src.models.invoice_header import InvoiceHeader
from src.models.invoice_line import InvoiceLine
from src.models.validation_result import ValidationResult
from src.models.segment import Segment
from src.models.page import Page
from src.models.row import Row
from src.quality.score import (
    calculate_quality_score,
    count_missing_fields,
    calculate_wrap_complexity
)


class TestCountMissingFields:
    """Test missing fields counting."""
    
    def test_no_missing_fields(self):
        """Test with all fields present."""
        from datetime import date
        from unittest.mock import Mock
        
        segment = Mock(spec=Segment)
        segment.rows = []
        header = InvoiceHeader(
            segment=segment,
            invoice_number="INV-123",
            invoice_date=date(2024, 1, 15),
            supplier_name="Test Supplier",
            customer_name="Test Customer",
            total_amount=1000.0,
            raw_text="Test"
        )
        
        required, optional = count_missing_fields(header)
        assert required == 0
        assert optional == 0
    
    def test_missing_required_fields(self):
        """Test with missing required fields."""
        from unittest.mock import Mock
        
        segment = Mock(spec=Segment)
        segment.rows = []
        header = InvoiceHeader(
            segment=segment,
            invoice_number=None,  # Missing
            invoice_date=None,  # Missing
            total_amount=None,  # Missing
            raw_text=""
        )
        
        required, optional = count_missing_fields(header)
        assert required == 3
        assert optional == 2  # supplier_name and customer_name also missing
    
    def test_missing_optional_fields(self):
        """Test with missing optional fields only."""
        from datetime import date
        from unittest.mock import Mock
        
        segment = Mock(spec=Segment)
        segment.rows = []
        header = InvoiceHeader(
            segment=segment,
            invoice_number="INV-123",
            invoice_date=date(2024, 1, 15),
            total_amount=1000.0,
            supplier_name=None,  # Optional, missing
            customer_name=None,  # Optional, missing
            raw_text="Test"
        )
        
        required, optional = count_missing_fields(header)
        assert required == 0
        assert optional == 2


class TestWrapComplexity:
    """Test wrap complexity calculation."""
    
    def test_no_wraps(self):
        """Test with no wrapped lines."""
        from unittest.mock import Mock
        
        row1 = Mock(spec=Row)
        row2 = Mock(spec=Row)
        
        line1 = InvoiceLine(rows=[row1], description="Item 1", total_amount=100.0, line_number=1)
        line2 = InvoiceLine(rows=[row2], description="Item 2", total_amount=200.0, line_number=2)
        
        complexity = calculate_wrap_complexity([line1, line2])
        assert complexity == 0.0
    
    def test_some_wraps(self):
        """Test with some wrapped lines."""
        from unittest.mock import Mock
        
        row1 = Mock(spec=Row)
        row2a = Mock(spec=Row)
        row2b = Mock(spec=Row)
        row3 = Mock(spec=Row)
        
        line1 = InvoiceLine(rows=[row1], description="Item 1", total_amount=100.0, line_number=1)
        line2 = InvoiceLine(rows=[row2a, row2b], description="Item 2 wrapped", total_amount=200.0, line_number=2)
        line3 = InvoiceLine(rows=[row3], description="Item 3", total_amount=300.0, line_number=3)
        
        complexity = calculate_wrap_complexity([line1, line2, line3])
        assert complexity > 0.0
        assert complexity <= 20.0
    
    def test_empty_list(self):
        """Test with empty line items."""
        complexity = calculate_wrap_complexity([])
        assert complexity == 0.0


class TestQualityScore:
    """Test quality score calculation."""
    
    def test_perfect_score(self):
        """Test perfect invoice (OK status, all fields, no diff, no wraps)."""
        from datetime import date
        from unittest.mock import Mock
        
        segment = Mock(spec=Segment)
        segment.rows = []
        header = InvoiceHeader(
            segment=segment,
            invoice_number="INV-123",
            invoice_date=date(2024, 1, 15),
            supplier_name="Test Supplier",
            customer_name="Test Customer",
            total_amount=1000.0,
            invoice_number_confidence=0.98,
            total_confidence=0.97,
            raw_text="Test"
        )
        
        row1 = Mock(spec=Row)
        row2 = Mock(spec=Row)
        line1 = InvoiceLine(rows=[row1], description="Item 1", total_amount=500.0, line_number=1)
        line2 = InvoiceLine(rows=[row2], description="Item 2", total_amount=500.0, line_number=2)
        
        validation = ValidationResult(
            status="OK",
            lines_sum=1000.0,
            diff=0.0,
            hard_gate_passed=True,
            invoice_number_confidence=0.98,
            total_confidence=0.97
        )
        
        score = calculate_quality_score(validation, header, [line1, line2])
        
        assert score.score >= 90.0  # Should be very high
        assert score.status_penalty == 0.0
        assert score.missing_fields_penalty == 0.0
        assert score.reconciliation_penalty == 0.0
    
    def test_review_status_penalty(self):
        """Test that REVIEW status gives large penalty."""
        from datetime import date
        from unittest.mock import Mock
        
        segment = Mock(spec=Segment)
        segment.rows = []
        header = InvoiceHeader(
            segment=segment,
            invoice_number="INV-123",
            invoice_date=date(2024, 1, 15),
            total_amount=1000.0,
            invoice_number_confidence=0.50,  # Low confidence
            total_confidence=0.50,
            raw_text="Test"
        )
        
        row1 = Mock(spec=Row)
        line1 = InvoiceLine(rows=[row1], description="Item 1", total_amount=1000.0, line_number=1)
        
        validation = ValidationResult(
            status="REVIEW",
            lines_sum=1000.0,
            diff=0.0,
            hard_gate_passed=False,
            invoice_number_confidence=0.50,
            total_confidence=0.50,
            errors=["Hard gate failed"]
        )
        
        score = calculate_quality_score(validation, header, [line1])
        
        assert score.status_penalty == 40.0
        assert score.score < 60.0  # Should be significantly lower
    
    def test_missing_fields_penalty(self):
        """Test penalty for missing fields."""
        from unittest.mock import Mock
        
        segment = Mock(spec=Segment)
        segment.rows = []
        header = InvoiceHeader(
            segment=segment,
            invoice_number=None,  # Missing
            invoice_date=None,  # Missing
            total_amount=None,  # Missing
            raw_text=""
        )
        
        validation = ValidationResult(
            status="REVIEW",
            lines_sum=0.0,
            diff=None,
            hard_gate_passed=False
        )
        
        score = calculate_quality_score(validation, header, [])
        
        assert score.missing_fields_penalty > 0.0
        assert score.missing_fields_penalty <= 30.0
    
    def test_reconciliation_penalty(self):
        """Test penalty for reconciliation differences."""
        from datetime import date
        from unittest.mock import Mock
        
        segment = Mock(spec=Segment)
        segment.rows = []
        header = InvoiceHeader(
            segment=segment,
            invoice_number="INV-123",
            invoice_date=date(2024, 1, 15),
            total_amount=1000.0,
            invoice_number_confidence=0.98,
            total_confidence=0.97,
            raw_text="Test"
        )
        
        row1 = Mock(spec=Row)
        line1 = InvoiceLine(rows=[row1], description="Item 1", total_amount=950.0, line_number=1)
        
        validation = ValidationResult(
            status="PARTIAL",
            lines_sum=950.0,
            diff=50.0,  # Large difference
            hard_gate_passed=True,
            invoice_number_confidence=0.98,
            total_confidence=0.97,
            warnings=["Sum mismatch"]
        )
        
        score = calculate_quality_score(validation, header, [line1])
        
        assert score.reconciliation_penalty > 0.0
        assert score.reconciliation_penalty <= 20.0
        assert score.status_penalty == 15.0  # PARTIAL status
    
    def test_wrap_complexity_penalty(self):
        """Test penalty for wrap complexity."""
        from datetime import date
        from unittest.mock import Mock
        
        segment = Mock(spec=Segment)
        segment.rows = []
        header = InvoiceHeader(
            segment=segment,
            invoice_number="INV-123",
            invoice_date=date(2024, 1, 15),
            total_amount=1000.0,
            invoice_number_confidence=0.98,
            total_confidence=0.97,
            raw_text="Test"
        )
        
        # Create lines with many wrapped rows
        row1a = Mock(spec=Row)
        row1b = Mock(spec=Row)
        row1c = Mock(spec=Row)
        row2a = Mock(spec=Row)
        row2b = Mock(spec=Row)
        
        line1 = InvoiceLine(rows=[row1a, row1b, row1c], description="Item 1 wrapped", total_amount=500.0, line_number=1)
        line2 = InvoiceLine(rows=[row2a, row2b], description="Item 2 wrapped", total_amount=500.0, line_number=2)
        
        validation = ValidationResult(
            status="OK",
            lines_sum=1000.0,
            diff=0.0,
            hard_gate_passed=True,
            invoice_number_confidence=0.98,
            total_confidence=0.97
        )
        
        score = calculate_quality_score(validation, header, [line1, line2])
        
        assert score.wrap_complexity_penalty > 0.0
        assert score.wrap_complexity_penalty <= 10.0
    
    def test_score_range(self):
        """Test that score is always in valid range (0-100)."""
        from datetime import date
        from unittest.mock import Mock
        
        segment = Mock(spec=Segment)
        segment.rows = []
        header = InvoiceHeader(
            segment=segment,
            invoice_number=None,
            invoice_date=None,
            total_amount=None,
            invoice_number_confidence=0.0,
            total_confidence=0.0,
            raw_text=""
        )
        
        validation = ValidationResult(
            status="REVIEW",
            lines_sum=0.0,
            diff=None,
            hard_gate_passed=False,
            errors=["Multiple errors"]
        )
        
        score = calculate_quality_score(validation, header, [])
        
        assert 0.0 <= score.score <= 100.0
        assert score.score < 30.0  # Should be very low with all penalties
    
    def test_score_breakdown(self):
        """Test that breakdown contains expected fields."""
        from datetime import date
        from unittest.mock import Mock
        
        segment = Mock(spec=Segment)
        segment.rows = []
        header = InvoiceHeader(
            segment=segment,
            invoice_number="INV-123",
            invoice_date=date(2024, 1, 15),
            total_amount=1000.0,
            invoice_number_confidence=0.98,
            total_confidence=0.97,
            raw_text="Test"
        )
        
        row1 = Mock(spec=Row)
        line1 = InvoiceLine(rows=[row1], description="Item 1", total_amount=1000.0, line_number=1)
        
        validation = ValidationResult(
            status="OK",
            lines_sum=1000.0,
            diff=0.0,
            hard_gate_passed=True,
            invoice_number_confidence=0.98,
            total_confidence=0.97
        )
        
        score = calculate_quality_score(validation, header, [line1])
        
        assert "base_score" in score.breakdown
        assert "status" in score.breakdown
        assert "line_count" in score.breakdown
        assert "invoice_number_confidence" in score.breakdown
        assert score.breakdown["status"] == "OK"
        assert score.breakdown["line_count"] == 1

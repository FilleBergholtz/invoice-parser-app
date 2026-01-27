"""Performance benchmarks for Phase 22 (validation-driven re-extraction)."""

import time
from decimal import Decimal

import pytest

from src.models.document import Document
from src.models.page import Page
from src.models.row import Row
from src.models.segment import Segment
from src.models.token import Token
from src.pipeline.column_detection import (
    assign_tokens_to_columns,
    detect_columns_gap_based
)
from src.pipeline.invoice_line_parser import extract_invoice_lines_mode_b
from src.pipeline.validation import validate_netto_sum


@pytest.fixture
def sample_page():
    """Create a sample page for testing."""
    doc = Document(filename="test.pdf", filepath="test.pdf", page_count=0, pages=[])
    page = Page(page_number=1, width=612, height=792, document=doc)
    doc.pages.append(page)
    doc.page_count = 1
    return page


@pytest.fixture
def large_table(sample_page):
    """Create a large table with 50 rows for performance testing."""
    rows = []
    
    # Header row
    header_tokens = [
        Token(text="Benämning", x=50, y=250, width=200, height=12, page=sample_page),
        Token(text="Antal", x=300, y=250, width=50, height=12, page=sample_page),
        Token(text="Pris", x=450, y=250, width=50, height=12, page=sample_page),
        Token(text="Nettobelopp", x=550, y=250, width=100, height=12, page=sample_page),
    ]
    header_row = Row(
        tokens=header_tokens,
        y=250,
        x_min=50,
        x_max=650,
        text="Benämning Antal Pris Nettobelopp",
        page=sample_page
    )
    rows.append(header_row)
    
    # Create 50 data rows
    for i in range(50):
        y_pos = 280 + (i * 20)
        row_tokens = [
            Token(text=f"Product{i}", x=50, y=y_pos, width=200, height=12, page=sample_page),
            Token(text="5", x=300, y=y_pos, width=20, height=12, page=sample_page),
            Token(text="100.00", x=450, y=y_pos, width=60, height=12, page=sample_page),
            Token(text="25.00", x=520, y=y_pos, width=40, height=12, page=sample_page),  # VAT%
            Token(text="500.00", x=550, y=y_pos, width=60, height=12, page=sample_page),  # Netto
        ]
        row = Row(
            tokens=row_tokens,
            y=y_pos,
            x_min=50,
            x_max=610,
            text=f"Product{i} 5 100.00 25.00 500.00",
            page=sample_page
        )
        rows.append(row)
    
    return rows


@pytest.fixture
def medium_table(sample_page):
    """Create a medium table with 20 rows for performance testing."""
    rows = []
    
    # Header row
    header_tokens = [
        Token(text="Benämning", x=50, y=250, width=200, height=12, page=sample_page),
        Token(text="Nettobelopp", x=550, y=250, width=100, height=12, page=sample_page),
    ]
    header_row = Row(
        tokens=header_tokens,
        y=250,
        x_min=50,
        x_max=650,
        text="Benämning Nettobelopp",
        page=sample_page
    )
    rows.append(header_row)
    
    # Create 20 data rows
    for i in range(20):
        y_pos = 280 + (i * 20)
        row_tokens = [
            Token(text=f"Product{i}", x=50, y=y_pos, width=200, height=12, page=sample_page),
            Token(text="500.00", x=550, y=y_pos, width=60, height=12, page=sample_page),
        ]
        row = Row(
            tokens=row_tokens,
            y=y_pos,
            x_min=50,
            x_max=610,
            text=f"Product{i} 500.00",
            page=sample_page
        )
        rows.append(row)
    
    return rows


class TestColumnDetectionPerformance:
    """Performance tests for column detection."""
    
    def test_column_detection_performance_medium_table(self, medium_table):
        """Test that column detection is <5ms for medium table (20 rows)."""
        # Warmup
        detect_columns_gap_based(medium_table)
        
        # Measure
        start = time.perf_counter()
        for _ in range(100):  # Run 100 times for better accuracy
            detect_columns_gap_based(medium_table)
        end = time.perf_counter()
        
        avg_time_ms = ((end - start) / 100) * 1000
        
        # Should be <5ms per table
        assert avg_time_ms < 5.0, f"Column detection took {avg_time_ms:.2f}ms (target: <5ms)"
        print(f"Column detection (20 rows): {avg_time_ms:.2f}ms")
    
    def test_column_detection_performance_large_table(self, large_table):
        """Test that column detection is <5ms for large table (50 rows)."""
        # Warmup
        detect_columns_gap_based(large_table)
        
        # Measure
        start = time.perf_counter()
        for _ in range(100):
            detect_columns_gap_based(large_table)
        end = time.perf_counter()
        
        avg_time_ms = ((end - start) / 100) * 1000
        
        # Should be <5ms per table (even for large tables)
        assert avg_time_ms < 5.0, f"Column detection took {avg_time_ms:.2f}ms (target: <5ms)"
        print(f"Column detection (50 rows): {avg_time_ms:.2f}ms")


class TestTokenAssignmentPerformance:
    """Performance tests for token-to-column assignment."""
    
    def test_token_assignment_performance(self, sample_page):
        """Test that token assignment is <2ms per row."""
        # Create a row with multiple tokens
        row_tokens = [
            Token(text="Product", x=50, y=300, width=200, height=12, page=sample_page),
            Token(text="5", x=300, y=300, width=20, height=12, page=sample_page),
            Token(text="100.00", x=450, y=300, width=60, height=12, page=sample_page),
            Token(text="500.00", x=550, y=300, width=60, height=12, page=sample_page),
        ]
        row = Row(
            tokens=row_tokens,
            y=300,
            x_min=50,
            x_max=610,
            text="Product 5 100.00 500.00",
            page=sample_page
        )
        
        column_centers = [100.0, 310.0, 480.0, 580.0]
        
        # Warmup
        assign_tokens_to_columns(row, column_centers)
        
        # Measure
        start = time.perf_counter()
        for _ in range(1000):  # Run 1000 times for better accuracy
            assign_tokens_to_columns(row, column_centers)
        end = time.perf_counter()
        
        avg_time_ms = ((end - start) / 1000) * 1000
        
        # Should be <2ms per row
        assert avg_time_ms < 2.0, f"Token assignment took {avg_time_ms:.3f}ms (target: <2ms)"
        print(f"Token assignment per row: {avg_time_ms:.3f}ms")


class TestModeBPerformance:
    """Performance tests for Mode B parsing."""
    
    def test_mode_b_performance_medium_table(self, sample_page, medium_table):
        """Test that Mode B parsing is <50ms for medium table (20 rows)."""
        segment = Segment(
            segment_type="items",
            rows=medium_table,
            y_min=250,
            y_max=680,
            page=sample_page
        )
        
        # Warmup
        extract_invoice_lines_mode_b(segment)
        
        # Measure
        start = time.perf_counter()
        for _ in range(10):  # Run 10 times
            extract_invoice_lines_mode_b(segment)
        end = time.perf_counter()
        
        avg_time_ms = ((end - start) / 10) * 1000
        
        # Should be <50ms per invoice
        assert avg_time_ms < 50.0, f"Mode B parsing took {avg_time_ms:.2f}ms (target: <50ms)"
        print(f"Mode B parsing (20 rows): {avg_time_ms:.2f}ms")
    
    def test_mode_b_performance_large_table(self, sample_page, large_table):
        """Test that Mode B parsing is <50ms for large table (50 rows)."""
        segment = Segment(
            segment_type="items",
            rows=large_table,
            y_min=250,
            y_max=1280,
            page=sample_page
        )
        
        # Warmup
        extract_invoice_lines_mode_b(segment)
        
        # Measure
        start = time.perf_counter()
        for _ in range(10):
            extract_invoice_lines_mode_b(segment)
        end = time.perf_counter()
        
        avg_time_ms = ((end - start) / 10) * 1000
        
        # Should be <50ms per invoice (even for large tables)
        assert avg_time_ms < 50.0, f"Mode B parsing took {avg_time_ms:.2f}ms (target: <50ms)"
        print(f"Mode B parsing (50 rows): {avg_time_ms:.2f}ms")


class TestValidationPerformance:
    """Performance tests for validation."""
    
    def test_validation_performance(self, sample_page):
        """Test that validation is <5ms per invoice."""
        from src.models.invoice_line import InvoiceLine
        
        # Create a dummy row for segment
        dummy_row = Row(
            tokens=[Token(text="Dummy", x=50, y=300, width=50, height=12, page=sample_page)],
            y=300,
            x_min=50,
            x_max=100,
            text="Dummy",
            page=sample_page
        )
        
        # Create 20 invoice lines
        segment = Segment(
            segment_type="items",
            rows=[dummy_row],
            y_min=300,
            y_max=700,
            page=sample_page
        )
        
        invoice_lines = []
        for i in range(20):
            row = Row(
                tokens=[Token(text=f"Product{i}", x=50, y=300 + i * 20, width=100, height=12, page=sample_page)],
                y=300 + i * 20,
                x_min=50,
                x_max=150,
                text=f"Product{i}",
                page=sample_page
            )
            line = InvoiceLine(
                rows=[row],
                description=f"Product{i}",
                total_amount=Decimal("500.00"),
                line_number=i + 1,
                segment=segment
            )
            invoice_lines.append(line)
        
        netto_total = Decimal("10000.00")
        
        # Warmup
        validate_netto_sum(invoice_lines, netto_total)
        
        # Measure
        start = time.perf_counter()
        for _ in range(1000):  # Run 1000 times
            validate_netto_sum(invoice_lines, netto_total)
        end = time.perf_counter()
        
        avg_time_ms = ((end - start) / 1000) * 1000
        
        # Should be <5ms per invoice
        assert avg_time_ms < 5.0, f"Validation took {avg_time_ms:.3f}ms (target: <5ms)"
        print(f"Validation (20 lines): {avg_time_ms:.3f}ms")


class TestModeBOverhead:
    """Test Mode B overhead compared to Mode A."""
    
    def test_mode_b_overhead_acceptable(self, sample_page, medium_table):
        """Test that Mode B overhead is acceptable (<50ms)."""
        from src.pipeline.invoice_line_parser import extract_invoice_lines
        
        segment = Segment(
            segment_type="items",
            rows=medium_table,
            y_min=250,
            y_max=680,
            page=sample_page
        )
        
        # Measure Mode A
        start_a = time.perf_counter()
        for _ in range(10):
            extract_invoice_lines(segment)
        end_a = time.perf_counter()
        avg_time_a = ((end_a - start_a) / 10) * 1000
        
        # Measure Mode B
        start_b = time.perf_counter()
        for _ in range(10):
            extract_invoice_lines_mode_b(segment)
        end_b = time.perf_counter()
        avg_time_b = ((end_b - start_b) / 10) * 1000
        
        overhead = avg_time_b - avg_time_a
        
        # Overhead should be <50ms
        assert overhead < 50.0, f"Mode B overhead is {overhead:.2f}ms (target: <50ms)"
        print(f"Mode A: {avg_time_a:.2f}ms, Mode B: {avg_time_b:.2f}ms, Overhead: {overhead:.2f}ms")

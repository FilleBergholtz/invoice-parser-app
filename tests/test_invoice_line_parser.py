"""Unit tests for line item extraction."""

from decimal import Decimal

import pytest
from src.models.document import Document
from src.models.page import Page
from src.models.row import Row
from src.models.segment import Segment
from src.models.token import Token
from src.models.invoice_line import InvoiceLine
from src.pipeline.invoice_line_parser import extract_invoice_lines


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
def sample_items_segment(sample_page):
    """Create a sample items segment with product rows."""
    # Row with product: description, quantity, unit_price, total_amount
    tokens_row1 = [
        Token(text="Product", x=10, y=300, width=60, height=12, page=sample_page),
        Token(text="2", x=100, y=300, width=20, height=12, page=sample_page),  # quantity
        Token(text="st", x=130, y=300, width=20, height=12, page=sample_page),  # unit
        Token(text="150.00", x=200, y=300, width=50, height=12, page=sample_page),  # unit_price
        Token(text="300.00", x=300, y=300, width=60, height=12, page=sample_page),  # total_amount
    ]
    
    row1 = Row(
        tokens=tokens_row1,
        y=300,
        x_min=10,
        x_max=360,
        text="Product 2 st 150.00 300.00",
        page=sample_page
    )
    
    # Row with product (no quantity/unit, just description and amount)
    tokens_row2 = [
        Token(text="Service", x=10, y=350, width=60, height=12, page=sample_page),
        Token(text="500,50", x=300, y=350, width=60, height=12, page=sample_page),  # total_amount with comma
    ]
    
    row2 = Row(
        tokens=tokens_row2,
        y=350,
        x_min=10,
        x_max=360,
        text="Service 500,50",
        page=sample_page
    )
    
    # Row without amount (should be skipped)
    tokens_row3 = [
        Token(text="Header", x=10, y=400, width=60, height=12, page=sample_page),
        Token(text="text", x=100, y=400, width=40, height=12, page=sample_page),
    ]
    
    row3 = Row(
        tokens=tokens_row3,
        y=400,
        x_min=10,
        x_max=140,
        text="Header text",
        page=sample_page
    )
    
    segment = Segment(
        segment_type="items",
        rows=[row1, row2, row3],
        y_min=300,
        y_max=400,
        page=sample_page
    )
    
    return segment


def test_extract_invoice_lines_from_items_segment(sample_items_segment):
    """Test extraction from items segment."""
    lines = extract_invoice_lines(sample_items_segment)
    
    # Should extract 2 line items (row3 has no amount, should be skipped)
    assert len(lines) == 2


def test_rad_med_belopp_rule(sample_items_segment):
    """Test 'rad med belopp = produktrad' rule."""
    lines = extract_invoice_lines(sample_items_segment)
    
    # All extracted lines must have total_amount > 0
    assert all(line.total_amount > 0 for line in lines)
    
    # Row without amount should not create InvoiceLine
    assert len(lines) == 2  # Only rows with amounts


def test_field_extraction(sample_items_segment):
    """Test field extraction (description, quantity, unit_price, total_amount)."""
    lines = extract_invoice_lines(sample_items_segment)
    
    # First line should have quantity, unit, unit_price
    line1 = lines[0]
    # Note: Current implementation might keep quantity/price in description string if position based cleaning is conservative
    assert "Product" in line1.description
    assert line1.quantity == Decimal("2")
    assert isinstance(line1.quantity, Decimal)
    assert line1.unit == "st"
    assert line1.unit_price == Decimal("150.00")
    assert isinstance(line1.unit_price, Decimal)
    assert line1.total_amount == Decimal("300.00")
    assert isinstance(line1.total_amount, Decimal)
    
    # Second line may not have quantity/unit_price
    line2 = lines[1]
    assert "Service" in line2.description
    assert line2.total_amount > 0
    assert isinstance(line2.total_amount, Decimal)


def test_amount_parsing_swedish_separators(sample_page):
    """Ensure Swedish separators parse without dropping decimal dots."""
    tokens_row1 = [
        Token(text="Service", x=10, y=300, width=60, height=12, page=sample_page),
        Token(text="9.345,67", x=300, y=300, width=80, height=12, page=sample_page),
    ]
    row1 = Row(
        tokens=tokens_row1,
        y=300,
        x_min=10,
        x_max=380,
        text="Service 9.345,67",
        page=sample_page
    )
    tokens_row2 = [
        Token(text="Fee", x=10, y=330, width=40, height=12, page=sample_page),
        Token(text="12.50", x=300, y=330, width=50, height=12, page=sample_page),
    ]
    row2 = Row(
        tokens=tokens_row2,
        y=330,
        x_min=10,
        x_max=350,
        text="Fee 12.50",
        page=sample_page
    )
    segment = Segment(
        segment_type="items",
        rows=[row1, row2],
        y_min=300,
        y_max=330,
        page=sample_page
    )

    lines = extract_invoice_lines(segment)

    assert len(lines) == 2
    assert lines[0].total_amount == Decimal("9345.67")
    assert lines[1].total_amount == Decimal("12.50")
    assert isinstance(lines[0].total_amount, Decimal)
    assert isinstance(lines[1].total_amount, Decimal)


def test_table_block_and_moms_column_rule(sample_page):
    """Ensure table block filtering and moms% column rule are applied."""
    header_tokens = [
        Token(text="Artikelnr", x=10, y=250, width=60, height=12, page=sample_page),
        Token(text="Benämning", x=90, y=250, width=70, height=12, page=sample_page),
        Token(text="Moms", x=300, y=250, width=40, height=12, page=sample_page),
        Token(text="Nettobelopp", x=360, y=250, width=80, height=12, page=sample_page),
    ]
    header_row = Row(
        tokens=header_tokens,
        y=250,
        x_min=10,
        x_max=440,
        text="Artikelnr Benämning Moms % Nettobelopp",
        page=sample_page
    )

    row1_tokens = [
        Token(text="A123", x=10, y=300, width=40, height=12, page=sample_page),
        Token(text="Filter", x=60, y=300, width=50, height=12, page=sample_page),
        Token(text="35.1", x=220, y=300, width=40, height=12, page=sample_page),
        Token(text="38.9", x=260, y=300, width=40, height=12, page=sample_page),
        Token(text="25.00", x=320, y=300, width=40, height=12, page=sample_page),
        Token(text="1 187,50", x=380, y=300, width=60, height=12, page=sample_page),
    ]
    row1 = Row(
        tokens=row1_tokens,
        y=300,
        x_min=10,
        x_max=440,
        text="A123 Filter 35.1 38.9 25.00 1 187,50",
        page=sample_page
    )

    continuation_tokens = [
        Token(text="LUFTRENARE", x=10, y=320, width=80, height=12, page=sample_page),
        Token(text="1100", x=95, y=320, width=40, height=12, page=sample_page),
    ]
    continuation_row = Row(
        tokens=continuation_tokens,
        y=320,
        x_min=10,
        x_max=140,
        text="LUFTRENARE 1100",
        page=sample_page
    )

    row2_tokens = [
        Token(text="B234", x=10, y=340, width=40, height=12, page=sample_page),
        Token(text="Service", x=60, y=340, width=60, height=12, page=sample_page),
        Token(text="25,00", x=320, y=340, width=40, height=12, page=sample_page),
        Token(text="250,00", x=380, y=340, width=60, height=12, page=sample_page),
    ]
    row2 = Row(
        tokens=row2_tokens,
        y=340,
        x_min=10,
        x_max=440,
        text="B234 Service 25,00 250,00",
        page=sample_page
    )

    end_tokens = [
        Token(text="Nettobelopp", x=10, y=400, width=90, height=12, page=sample_page),
        Token(text="exkl.", x=105, y=400, width=40, height=12, page=sample_page),
        Token(text="moms:", x=150, y=400, width=50, height=12, page=sample_page),
        Token(text="1 437,50", x=380, y=400, width=60, height=12, page=sample_page),
    ]
    end_row = Row(
        tokens=end_tokens,
        y=400,
        x_min=10,
        x_max=440,
        text="Nettobelopp exkl. moms: 1 437,50",
        page=sample_page
    )

    footer_tokens = [
        Token(text="Att", x=10, y=430, width=20, height=12, page=sample_page),
        Token(text="betala", x=35, y=430, width=40, height=12, page=sample_page),
        Token(text="1 796,88", x=380, y=430, width=60, height=12, page=sample_page),
    ]
    footer_row = Row(
        tokens=footer_tokens,
        y=430,
        x_min=10,
        x_max=440,
        text="Att betala 1 796,88",
        page=sample_page
    )

    segment = Segment(
        segment_type="items",
        rows=[header_row, row1, continuation_row, row2, end_row, footer_row],
        y_min=250,
        y_max=430,
        page=sample_page
    )

    lines = extract_invoice_lines(segment)

    assert len(lines) == 2
    assert lines[0].total_amount == Decimal("1187.50")
    assert lines[1].total_amount == Decimal("250.00")


def test_invoice_line_rows_traceability(sample_items_segment):
    """Test that InvoiceLine.rows maintains traceability."""
    lines = extract_invoice_lines(sample_items_segment)
    
    for line in lines:
        assert len(line.rows) > 0
        for row in line.rows:
            assert row.page is not None
            assert len(row.tokens) > 0


def test_line_numbers_assigned(sample_items_segment):
    """Test that line numbers are assigned correctly."""
    lines = extract_invoice_lines(sample_items_segment)
    
    for i, line in enumerate(lines, start=1):
        assert line.line_number == i


def test_rows_without_amounts_skipped(sample_items_segment):
    """Test that rows without amounts are skipped."""
    lines = extract_invoice_lines(sample_items_segment)
    
    # Should only have 2 lines (rows with amounts)
    # Row 3 has no amount, should be skipped
    assert len(lines) == 2


def test_missing_fields_optional(sample_items_segment):
    """Test that missing fields (quantity/unit_price) are optional."""
    lines = extract_invoice_lines(sample_items_segment)
    
    # Find line without quantity/unit_price
    line_without_qty = next((l for l in lines if l.quantity is None), None)
    
    if line_without_qty:
        # Should still have description and total_amount
        assert line_without_qty.description
        assert line_without_qty.total_amount > 0


def test_footer_rows_filtered(sample_page):
    """Test that footer rows (summa/total/att betala) are filtered out."""
    from src.pipeline.invoice_line_parser import extract_invoice_lines
    
    # Product row
    product_tokens = [
        Token(text="Product", x=10, y=300, width=60, height=12, page=sample_page),
        Token(text="100.00", x=300, y=300, width=60, height=12, page=sample_page),
    ]
    product_row = Row(
        tokens=product_tokens,
        y=300,
        x_min=10,
        x_max=360,
        text="Product 100.00",
        page=sample_page
    )
    
    # Footer row (should be filtered out)
    footer_tokens = [
        Token(text="Att", x=10, y=400, width=30, height=12, page=sample_page),
        Token(text="betala", x=50, y=400, width=50, height=12, page=sample_page),
        Token(text="1000.00", x=300, y=400, width=60, height=12, page=sample_page),
    ]
    footer_row = Row(
        tokens=footer_tokens,
        y=400,
        x_min=10,
        x_max=360,
        text="Att betala 1000.00",
        page=sample_page
    )
    
    segment = Segment(
        segment_type="items",
        rows=[product_row, footer_row],
        y_min=300,
        y_max=400,
        page=sample_page
    )
    
    lines = extract_invoice_lines(segment)
    
    # Should only extract product row, footer row should be filtered out
    assert len(lines) == 1
    assert "Product" in lines[0].description
    assert lines[0].total_amount == Decimal("100.00")


# ============================================================================
# Phase 21 Regression Tests: Multi-line items (wrap detection)
# ============================================================================

def test_line_items_with_wrapped_descriptions(sample_page):
    """Test wrapped items extracted correctly with full description."""
    # Product row with amount
    product_tokens = [
        Token(text="Product", x=10, y=300, width=50, height=12, page=sample_page),
        Token(text="description", x=70, y=300, width=80, height=12, page=sample_page),
        Token(text="100.00", x=300, y=300, width=60, height=12, page=sample_page),
    ]
    product_row = Row(
        tokens=product_tokens,
        y=300,
        x_min=10,
        x_max=360,
        text="Product description 100.00",
        page=sample_page
    )
    product_row.y_min = 300
    product_row.y_max = 312
    
    # Wrapped row 1 (no amount, close Y-distance)
    wrap1_tokens = [
        Token(text="Continuation", x=10, y=315, width=80, height=12, page=sample_page),
        Token(text="line", x=95, y=315, width=30, height=12, page=sample_page),
    ]
    wrap1_row = Row(
        tokens=wrap1_tokens,
        y=315,
        x_min=10,
        x_max=125,
        text="Continuation line 1",
        page=sample_page
    )
    wrap1_row.y_min = 315
    wrap1_row.y_max = 327
    
    # Wrapped row 2 (no amount, close Y-distance)
    wrap2_tokens = [
        Token(text="Continuation", x=10, y=330, width=80, height=12, page=sample_page),
        Token(text="line", x=95, y=330, width=30, height=12, page=sample_page),
        Token(text="2", x=130, y=330, width=10, height=12, page=sample_page),
    ]
    wrap2_row = Row(
        tokens=wrap2_tokens,
        y=330,
        x_min=10,
        x_max=140,
        text="Continuation line 2",
        page=sample_page
    )
    wrap2_row.y_min = 330
    wrap2_row.y_max = 342
    
    segment = Segment(
        segment_type="items",
        rows=[product_row, wrap1_row, wrap2_row],
        y_min=300,
        y_max=342,
        page=sample_page
    )
    
    lines = extract_invoice_lines(segment)
    
    # Should extract 1 line with wrapped description
    assert len(lines) == 1
    assert "Product description" in lines[0].description
    assert "Continuation line 1" in lines[0].description
    assert "Continuation line 2" in lines[0].description
    assert lines[0].total_amount == Decimal("100.00")
    # Verify traceability: InvoiceLine.rows should contain all 3 rows
    assert len(lines[0].rows) == 3


def test_wrapped_items_with_start_patterns(sample_page):
    """Test that article numbers start new items even with tight spacing."""
    # First product row
    product1_tokens = [
        Token(text="ABC123", x=10, y=300, width=50, height=12, page=sample_page),
        Token(text="Product", x=70, y=300, width=50, height=12, page=sample_page),
        Token(text="50.00", x=300, y=300, width=50, height=12, page=sample_page),
    ]
    product1_row = Row(
        tokens=product1_tokens,
        y=300,
        x_min=10,
        x_max=350,
        text="ABC123 Product One 50.00",
        page=sample_page
    )
    product1_row.y_min = 300
    product1_row.y_max = 312
    
    # Second product row with article number (tight spacing - only 3pt gap)
    product2_tokens = [
        Token(text="XYZ789", x=10, y=315, width=50, height=12, page=sample_page),
        Token(text="Product", x=70, y=315, width=50, height=12, page=sample_page),
        Token(text="75.00", x=300, y=315, width=50, height=12, page=sample_page),
    ]
    product2_row = Row(
        tokens=product2_tokens,
        y=315,
        x_min=10,
        x_max=350,
        text="XYZ789 Product Two 75.00",
        page=sample_page
    )
    product2_row.y_min = 315
    product2_row.y_max = 327
    
    segment = Segment(
        segment_type="items",
        rows=[product1_row, product2_row],
        y_min=300,
        y_max=327,
        page=sample_page
    )
    
    lines = extract_invoice_lines(segment)
    
    # Should extract 2 separate items (start-pattern prevents merge)
    assert len(lines) == 2
    # Article numbers are skipped from description (separate field)
    assert "Product" in lines[0].description
    assert lines[0].total_amount == Decimal("50.00")
    assert "Product" in lines[1].description
    assert lines[1].total_amount == Decimal("75.00")


def test_no_false_wraps_from_footer(sample_page):
    """Test footer rows are not wrapped to items."""
    # Product row
    product_tokens = [
        Token(text="Product", x=10, y=300, width=50, height=12, page=sample_page),
        Token(text="100.00", x=300, y=300, width=60, height=12, page=sample_page),
    ]
    product_row = Row(
        tokens=product_tokens,
        y=300,
        x_min=10,
        x_max=360,
        text="Product 100.00",
        page=sample_page
    )
    product_row.y_min = 300
    product_row.y_max = 312
    
    # Footer row (close spacing, but should not be wrapped)
    footer_tokens = [
        Token(text="Summa", x=10, y=320, width=50, height=12, page=sample_page),
        Token(text="100.00", x=300, y=320, width=60, height=12, page=sample_page),
    ]
    footer_row = Row(
        tokens=footer_tokens,
        y=320,
        x_min=10,
        x_max=360,
        text="Summa 100.00",
        page=sample_page
    )
    footer_row.y_min = 320
    footer_row.y_max = 332
    
    segment = Segment(
        segment_type="items",
        rows=[product_row, footer_row],
        y_min=300,
        y_max=332,
        page=sample_page
    )
    
    lines = extract_invoice_lines(segment)
    
    # Should extract 1 line (footer filtered out)
    assert len(lines) == 1
    assert "Product" in lines[0].description
    assert "Summa" not in lines[0].description
    assert lines[0].total_amount == Decimal("100.00")
    # Verify no footer row wrapped
    assert len(lines[0].rows) == 1


def test_phase_20_backward_compatibility(sample_page):
    """Test Phase 20 functionality still works with Phase 21 enhancements."""
    # Table header
    header_tokens = [
        Token(text="Artikelnr", x=10, y=250, width=60, height=12, page=sample_page),
        Token(text="Benämning", x=90, y=250, width=70, height=12, page=sample_page),
        Token(text="Moms", x=300, y=250, width=40, height=12, page=sample_page),
        Token(text="Nettobelopp", x=360, y=250, width=80, height=12, page=sample_page),
    ]
    header_row = Row(
        tokens=header_tokens,
        y=250,
        x_min=10,
        x_max=440,
        text="Artikelnr Benämning Moms % Nettobelopp",
        page=sample_page
    )
    
    # Product row with VAT% (Phase 20 requirement)
    row1_tokens = [
        Token(text="A123", x=10, y=300, width=40, height=12, page=sample_page),
        Token(text="Product", x=60, y=300, width=60, height=12, page=sample_page),
        Token(text="25.00", x=320, y=300, width=40, height=12, page=sample_page),
        Token(text="500.00", x=380, y=300, width=60, height=12, page=sample_page),
    ]
    row1 = Row(
        tokens=row1_tokens,
        y=300,
        x_min=10,
        x_max=440,
        text="A123 Product 25.00 500.00",
        page=sample_page
    )
    row1.y_min = 300
    row1.y_max = 312
    
    # Footer
    end_tokens = [
        Token(text="Nettobelopp", x=10, y=350, width=90, height=12, page=sample_page),
        Token(text="exkl.", x=105, y=350, width=40, height=12, page=sample_page),
        Token(text="moms:", x=150, y=350, width=50, height=12, page=sample_page),
        Token(text="500.00", x=380, y=350, width=60, height=12, page=sample_page),
    ]
    end_row = Row(
        tokens=end_tokens,
        y=350,
        x_min=10,
        x_max=440,
        text="Nettobelopp exkl. moms: 500.00",
        page=sample_page
    )
    
    segment = Segment(
        segment_type="items",
        rows=[header_row, row1, end_row],
        y_min=250,
        y_max=350,
        page=sample_page
    )
    
    lines = extract_invoice_lines(segment)
    
    # Phase 20 functionality: VAT%-anchored extraction
    assert len(lines) == 1
    assert lines[0].total_amount == Decimal("500.00")

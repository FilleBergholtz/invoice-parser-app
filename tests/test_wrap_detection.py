"""Unit tests for wrap detection."""

from decimal import Decimal

import pytest
from src.models.document import Document
from src.models.page import Page
from src.models.row import Row
from src.models.token import Token
from src.pipeline.wrap_detection import (
    _calculate_adaptive_y_threshold,
    _matches_start_pattern,
    detect_wrapped_rows,
    consolidate_wrapped_description
)


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


# ============================================================================
# Unit Tests: Adaptive Y-threshold calculation
# ============================================================================

def test_adaptive_y_threshold_calculation(sample_page):
    """Test adaptive Y-threshold calculation with typical line heights."""
    # Create rows with consistent 12pt line height (typical spacing)
    rows = []
    y_positions = [100, 114, 128, 142, 156]  # 14pt spacing (12pt font + 2pt leading)
    
    for i, y in enumerate(y_positions):
        tokens = [Token(text=f"Row{i}", x=10, y=y, width=50, height=12, page=sample_page)]
        row = Row(
            tokens=tokens,
            y=y,
            x_min=10,
            x_max=60,
            text=f"Row {i}",
            page=sample_page
        )
        row.y_min = y
        row.y_max = y + 12
        rows.append(row)
    
    threshold = _calculate_adaptive_y_threshold(rows)
    
    # Expected: 1.5× median line height
    # Line heights: 14 - 12 = 2pt spacing between rows
    # Median: 2.0
    # Threshold: 2.0 × 1.5 = 3.0
    # But we're measuring y_min to y_max distance, which is the gap between rows
    # Gap = next.y_min - prev.y_max = 114 - 112 = 2
    assert threshold == pytest.approx(3.0, abs=0.5)


def test_adaptive_y_threshold_fallback(sample_page):
    """Test fallback threshold when no rows provided."""
    threshold = _calculate_adaptive_y_threshold([])
    assert threshold == 15.0  # Fallback value


def test_adaptive_y_threshold_single_row(sample_page):
    """Test fallback threshold with single row."""
    tokens = [Token(text="Row", x=10, y=100, width=50, height=12, page=sample_page)]
    row = Row(tokens=tokens, y=100, x_min=10, x_max=60, text="Row", page=sample_page)
    row.y_min = 100
    row.y_max = 112
    
    threshold = _calculate_adaptive_y_threshold([row])
    assert threshold == 15.0  # Fallback value


def test_adaptive_y_threshold_variable_spacing(sample_page):
    """Test adaptive threshold with variable line heights."""
    # Create rows with variable spacing (mixed font sizes)
    rows = []
    y_positions = [100, 120, 135, 155, 170]  # Variable spacing: 20, 15, 20, 15
    heights = [12, 12, 14, 12, 12]
    
    for i, (y, h) in enumerate(zip(y_positions, heights)):
        tokens = [Token(text=f"Row{i}", x=10, y=y, width=50, height=h, page=sample_page)]
        row = Row(
            tokens=tokens,
            y=y,
            x_min=10,
            x_max=60,
            text=f"Row {i}",
            page=sample_page
        )
        row.y_min = y
        row.y_max = y + h
        rows.append(row)
    
    threshold = _calculate_adaptive_y_threshold(rows)
    
    # Line heights: (120-112)=8, (135-132)=3, (155-149)=6, (170-182)=-12 (skip negative)
    # Actually: next.y_min - prev.y_max
    # 120 - 112 = 8, 135 - 132 = 3, 155 - 149 = 6, 170 - 167 = 3
    # Median of [8, 3, 6, 3] = 4.5
    # Threshold: 4.5 × 1.5 = 6.75
    assert threshold > 5.0
    assert threshold < 12.0


# ============================================================================
# Unit Tests: Start-pattern detection
# ============================================================================

def test_start_pattern_article_number_numeric(sample_page):
    """Test article number detection: numeric (5+ digits)."""
    tokens = [Token(text="12345", x=10, y=100, width=50, height=12, page=sample_page)]
    row = Row(tokens=tokens, y=100, x_min=10, x_max=60, text="12345 Product", page=sample_page)
    
    assert _matches_start_pattern(row) is True


def test_start_pattern_article_number_alphanumeric(sample_page):
    """Test article number detection: alphanumeric (ABC123)."""
    tokens = [Token(text="ABC123", x=10, y=100, width=50, height=12, page=sample_page)]
    row = Row(tokens=tokens, y=100, x_min=10, x_max=60, text="ABC123 Product", page=sample_page)
    
    assert _matches_start_pattern(row) is True


def test_start_pattern_date_iso(sample_page):
    """Test date pattern: ISO format (YYYY-MM-DD)."""
    tokens = [Token(text="2026-01-26", x=10, y=100, width=70, height=12, page=sample_page)]
    row = Row(tokens=tokens, y=100, x_min=10, x_max=80, text="2026-01-26 Service", page=sample_page)
    
    assert _matches_start_pattern(row) is True


def test_start_pattern_date_swedish(sample_page):
    """Test date pattern: Swedish format (DD/MM)."""
    tokens = [Token(text="26/01", x=10, y=100, width=40, height=12, page=sample_page)]
    row = Row(tokens=tokens, y=100, x_min=10, x_max=50, text="26/01 Service", page=sample_page)
    
    assert _matches_start_pattern(row) is True


def test_start_pattern_individnr(sample_page):
    """Test individnr pattern: YYYYMMDD-XXXX."""
    tokens = [Token(text="19900101-1234", x=10, y=100, width=90, height=12, page=sample_page)]
    row = Row(tokens=tokens, y=100, x_min=10, x_max=100, text="19900101-1234 Person Name", page=sample_page)
    
    assert _matches_start_pattern(row) is True


def test_start_pattern_account_code(sample_page):
    """Test account code pattern: 4 digits + space."""
    tokens = [Token(text="1234", x=10, y=100, width=40, height=12, page=sample_page)]
    row = Row(tokens=tokens, y=100, x_min=10, x_max=50, text="1234 Account Name", page=sample_page)
    
    assert _matches_start_pattern(row) is True


def test_start_pattern_no_match(sample_page):
    """Test no start pattern match for regular description."""
    tokens = [Token(text="Description", x=10, y=100, width=80, height=12, page=sample_page)]
    row = Row(tokens=tokens, y=100, x_min=10, x_max=90, text="Description text", page=sample_page)
    
    assert _matches_start_pattern(row) is False


def test_start_pattern_short_number(sample_page):
    """Test that short numbers (< 5 digits) don't match article number pattern."""
    tokens = [Token(text="123", x=10, y=100, width=30, height=12, page=sample_page)]
    row = Row(tokens=tokens, y=100, x_min=10, x_max=40, text="123 text", page=sample_page)
    
    # Should not match article number pattern (requires 5+ digits)
    # But might match account code if followed by space
    assert _matches_start_pattern(row) is False


# ============================================================================
# Unit Tests: X-alignment with right-indent
# ============================================================================

def test_x_alignment_base_tolerance(sample_page):
    """Test X-alignment within base tolerance (±2%)."""
    # Product row at x=10
    product_tokens = [
        Token(text="Product", x=10, y=100, width=50, height=12, page=sample_page),
        Token(text="100.00", x=300, y=100, width=50, height=12, page=sample_page)
    ]
    product_row = Row(
        tokens=product_tokens,
        y=100,
        x_min=10,
        x_max=350,
        text="Product 100.00",
        page=sample_page
    )
    product_row.y_min = 100
    product_row.y_max = 112
    
    # Continuation row at x=11 (within ±2% of 595 = ±11.9)
    continuation_tokens = [
        Token(text="Continuation", x=11, y=115, width=80, height=12, page=sample_page)
    ]
    continuation_row = Row(
        tokens=continuation_tokens,
        y=115,
        x_min=11,
        x_max=91,
        text="Continuation text",
        page=sample_page
    )
    continuation_row.y_min = 115
    continuation_row.y_max = 127
    
    wraps = detect_wrapped_rows(product_row, [continuation_row], sample_page)
    
    assert len(wraps) == 1
    assert wraps[0] == continuation_row


def test_x_alignment_right_indent_allowance(sample_page):
    """Test X-alignment with right-indent allowance (+5%)."""
    # Product row at x=10
    product_tokens = [
        Token(text="Product", x=10, y=100, width=50, height=12, page=sample_page),
        Token(text="100.00", x=300, y=100, width=50, height=12, page=sample_page)
    ]
    product_row = Row(
        tokens=product_tokens,
        y=100,
        x_min=10,
        x_max=350,
        text="Product 100.00",
        page=sample_page
    )
    product_row.y_min = 100
    product_row.y_max = 112
    
    # Indented continuation row at x=30 (within +5% of 595 = +29.75)
    continuation_tokens = [
        Token(text="• Specification", x=30, y=115, width=100, height=12, page=sample_page)
    ]
    continuation_row = Row(
        tokens=continuation_tokens,
        y=115,
        x_min=30,
        x_max=130,
        text="• Specification 1",
        page=sample_page
    )
    continuation_row.y_min = 115
    continuation_row.y_max = 127
    
    wraps = detect_wrapped_rows(product_row, [continuation_row], sample_page)
    
    assert len(wraps) == 1
    assert wraps[0] == continuation_row


def test_x_alignment_too_far_right(sample_page):
    """Test X-alignment rejection when indented too far right (> +5%)."""
    # Product row at x=10
    product_tokens = [
        Token(text="Product", x=10, y=100, width=50, height=12, page=sample_page),
        Token(text="100.00", x=300, y=100, width=50, height=12, page=sample_page)
    ]
    product_row = Row(
        tokens=product_tokens,
        y=100,
        x_min=10,
        x_max=350,
        text="Product 100.00",
        page=sample_page
    )
    product_row.y_min = 100
    product_row.y_max = 112
    
    # Too far right: x=50 (exceeds +5% of 595 = +29.75)
    continuation_tokens = [
        Token(text="Far right", x=50, y=115, width=60, height=12, page=sample_page)
    ]
    continuation_row = Row(
        tokens=continuation_tokens,
        y=115,
        x_min=50,
        x_max=110,
        text="Far right text",
        page=sample_page
    )
    continuation_row.y_min = 115
    continuation_row.y_max = 127
    
    wraps = detect_wrapped_rows(product_row, [continuation_row], sample_page)
    
    assert len(wraps) == 0


# ============================================================================
# Unit Tests: No arbitrary wrap limit
# ============================================================================

def test_no_arbitrary_wrap_limit(sample_page):
    """Test that 10+ wraps are allowed (no hard limit)."""
    # Product row
    product_tokens = [
        Token(text="Product", x=10, y=100, width=50, height=12, page=sample_page),
        Token(text="100.00", x=300, y=100, width=50, height=12, page=sample_page)
    ]
    product_row = Row(
        tokens=product_tokens,
        y=100,
        x_min=10,
        x_max=350,
        text="Product 100.00",
        page=sample_page
    )
    product_row.y_min = 100
    product_row.y_max = 112
    
    # Create 12 continuation rows
    continuation_rows = []
    for i in range(12):
        y_pos = 115 + (i * 14)  # 14pt spacing
        tokens = [Token(text=f"Line{i}", x=10, y=y_pos, width=60, height=12, page=sample_page)]
        row = Row(
            tokens=tokens,
            y=y_pos,
            x_min=10,
            x_max=70,
            text=f"Continuation line {i}",
            page=sample_page
        )
        row.y_min = y_pos
        row.y_max = y_pos + 12
        continuation_rows.append(row)
    
    all_rows = [product_row] + continuation_rows
    wraps = detect_wrapped_rows(product_row, continuation_rows, sample_page, all_rows=all_rows)
    
    # Should collect all 12 wraps (no hard limit)
    assert len(wraps) == 12


# ============================================================================
# Edge Case Tests
# ============================================================================

def test_indented_sub_items(sample_page):
    """Test bullet points and indented sub-items."""
    # Product row
    product_tokens = [
        Token(text="Product", x=10, y=100, width=50, height=12, page=sample_page),
        Token(text="100.00", x=300, y=100, width=50, height=12, page=sample_page)
    ]
    product_row = Row(
        tokens=product_tokens,
        y=100,
        x_min=10,
        x_max=350,
        text="Product Description 100.00",
        page=sample_page
    )
    product_row.y_min = 100
    product_row.y_max = 112
    
    # Bullet point rows (indented +20pt)
    bullet_rows = []
    bullet_texts = ["• Specification 1", "• Specification 2", "• Specification 3"]
    for i, text in enumerate(bullet_texts):
        y_pos = 115 + (i * 14)
        tokens = [Token(text=text, x=30, y=y_pos, width=100, height=12, page=sample_page)]
        row = Row(
            tokens=tokens,
            y=y_pos,
            x_min=30,
            x_max=130,
            text=text,
            page=sample_page
        )
        row.y_min = y_pos
        row.y_max = y_pos + 12
        bullet_rows.append(row)
    
    all_rows = [product_row] + bullet_rows
    wraps = detect_wrapped_rows(product_row, bullet_rows, sample_page, all_rows=all_rows)
    
    # Should collect all bullet points (right-indent allowance)
    assert len(wraps) == 3


def test_footer_proximity(sample_page):
    """Test that continuation stops at footer row."""
    # Product row
    product_tokens = [
        Token(text="Product", x=10, y=100, width=50, height=12, page=sample_page),
        Token(text="100.00", x=300, y=100, width=50, height=12, page=sample_page)
    ]
    product_row = Row(
        tokens=product_tokens,
        y=100,
        x_min=10,
        x_max=350,
        text="Product 100.00",
        page=sample_page
    )
    product_row.y_min = 100
    product_row.y_max = 112
    
    # Continuation row
    continuation_tokens = [
        Token(text="Continuation", x=10, y=115, width=80, height=12, page=sample_page)
    ]
    continuation_row = Row(
        tokens=continuation_tokens,
        y=115,
        x_min=10,
        x_max=90,
        text="Continuation text",
        page=sample_page
    )
    continuation_row.y_min = 115
    continuation_row.y_max = 127
    
    # Footer row (has amount, will stop wrap detection)
    footer_tokens = [
        Token(text="Summa", x=10, y=130, width=50, height=12, page=sample_page),
        Token(text="200.00", x=300, y=130, width=50, height=12, page=sample_page)
    ]
    footer_row = Row(
        tokens=footer_tokens,
        y=130,
        x_min=10,
        x_max=350,
        text="Summa 200.00",
        page=sample_page
    )
    footer_row.y_min = 130
    footer_row.y_max = 142
    
    all_rows = [product_row, continuation_row, footer_row]
    wraps = detect_wrapped_rows(product_row, [continuation_row, footer_row], sample_page, all_rows=all_rows)
    
    # Should collect continuation but stop at footer (footer has amount)
    assert len(wraps) == 1
    assert wraps[0] == continuation_row


def test_tightly_spaced_separate_items(sample_page):
    """Test start-pattern prevents merging tightly-spaced items."""
    # Product row
    product_tokens = [
        Token(text="Product", x=10, y=100, width=50, height=12, page=sample_page),
        Token(text="100.00", x=300, y=100, width=50, height=12, page=sample_page)
    ]
    product_row = Row(
        tokens=product_tokens,
        y=100,
        x_min=10,
        x_max=350,
        text="Product 100.00",
        page=sample_page
    )
    product_row.y_min = 100
    product_row.y_max = 112
    
    # Next row starts with article number (should not be wrapped)
    next_item_tokens = [
        Token(text="12345", x=10, y=115, width=50, height=12, page=sample_page),
        Token(text="Next", x=70, y=115, width=40, height=12, page=sample_page)
    ]
    next_item_row = Row(
        tokens=next_item_tokens,
        y=115,
        x_min=10,
        x_max=110,
        text="12345 Next Product",
        page=sample_page
    )
    next_item_row.y_min = 115
    next_item_row.y_max = 127
    
    all_rows = [product_row, next_item_row]
    wraps = detect_wrapped_rows(product_row, [next_item_row], sample_page, all_rows=all_rows)
    
    # Should NOT wrap next item (start-pattern override)
    assert len(wraps) == 0


def test_mixed_wrapped_nonwrapped_items(sample_page):
    """Test invoice with both wrapped and single-line items."""
    # Single-line item
    single_tokens = [
        Token(text="Single", x=10, y=100, width=50, height=12, page=sample_page),
        Token(text="50.00", x=300, y=100, width=50, height=12, page=sample_page)
    ]
    single_row = Row(
        tokens=single_tokens,
        y=100,
        x_min=10,
        x_max=350,
        text="Single item 50.00",
        page=sample_page
    )
    single_row.y_min = 100
    single_row.y_max = 112
    
    # Multi-line item (product + wrap)
    multi_tokens = [
        Token(text="Multi", x=10, y=120, width=50, height=12, page=sample_page),
        Token(text="100.00", x=300, y=120, width=50, height=12, page=sample_page)
    ]
    multi_row = Row(
        tokens=multi_tokens,
        y=120,
        x_min=10,
        x_max=350,
        text="Multi-line item 100.00",
        page=sample_page
    )
    multi_row.y_min = 120
    multi_row.y_max = 132
    
    wrap_tokens = [
        Token(text="Continuation", x=10, y=135, width=80, height=12, page=sample_page)
    ]
    wrap_row = Row(
        tokens=wrap_tokens,
        y=135,
        x_min=10,
        x_max=90,
        text="Continuation text",
        page=sample_page
    )
    wrap_row.y_min = 135
    wrap_row.y_max = 147
    
    # Single-line should collect no wraps
    all_rows = [single_row, multi_row, wrap_row]
    wraps_single = detect_wrapped_rows(single_row, [multi_row, wrap_row], sample_page, all_rows=all_rows)
    assert len(wraps_single) == 0  # Multi-line has amount, stops wrap detection
    
    # Multi-line should collect wrap
    wraps_multi = detect_wrapped_rows(multi_row, [wrap_row], sample_page, all_rows=all_rows)
    assert len(wraps_multi) == 1


def test_variable_font_sizes(sample_page):
    """Test adaptive threshold with 10pt and 14pt fonts."""
    # Create rows with variable font sizes
    rows = []
    
    # 10pt font rows (12pt line height)
    for i in range(3):
        y = 100 + (i * 13)  # 13pt spacing for 10pt font
        tokens = [Token(text=f"Row{i}", x=10, y=y, width=50, height=10, page=sample_page)]
        row = Row(tokens=tokens, y=y, x_min=10, x_max=60, text=f"Row {i}", page=sample_page)
        row.y_min = y
        row.y_max = y + 10
        rows.append(row)
    
    # 14pt font rows (16pt line height)
    for i in range(3, 6):
        y = 140 + ((i-3) * 17)  # 17pt spacing for 14pt font
        tokens = [Token(text=f"Row{i}", x=10, y=y, width=50, height=14, page=sample_page)]
        row = Row(tokens=tokens, y=y, x_min=10, x_max=60, text=f"Row {i}", page=sample_page)
        row.y_min = y
        row.y_max = y + 14
        rows.append(row)
    
    threshold = _calculate_adaptive_y_threshold(rows)
    
    # Should adapt to mixed font sizes
    assert threshold > 2.0  # Not too small
    assert threshold < 20.0  # Not too large


# ============================================================================
# Integration Tests
# ============================================================================

def test_consolidate_wrapped_description(sample_page):
    """Test description consolidation with space separator."""
    # Product row
    product_tokens = [
        Token(text="Product", x=10, y=100, width=50, height=12, page=sample_page)
    ]
    product_row = Row(
        tokens=product_tokens,
        y=100,
        x_min=10,
        x_max=60,
        text="Product description",
        page=sample_page
    )
    
    # Wrapped rows
    wrapped_rows = []
    for i, text in enumerate(["line 1", "line 2", "line 3"]):
        y = 115 + (i * 14)
        tokens = [Token(text=text, x=10, y=y, width=40, height=12, page=sample_page)]
        row = Row(tokens=tokens, y=y, x_min=10, x_max=50, text=text, page=sample_page)
        wrapped_rows.append(row)
    
    consolidated = consolidate_wrapped_description(product_row, wrapped_rows)
    
    assert consolidated == "Product description line 1 line 2 line 3"


def test_empty_following_rows(sample_page):
    """Test wrap detection with no following rows."""
    product_tokens = [
        Token(text="Product", x=10, y=100, width=50, height=12, page=sample_page),
        Token(text="100.00", x=300, y=100, width=50, height=12, page=sample_page)
    ]
    product_row = Row(
        tokens=product_tokens,
        y=100,
        x_min=10,
        x_max=350,
        text="Product 100.00",
        page=sample_page
    )
    product_row.y_min = 100
    product_row.y_max = 112
    
    wraps = detect_wrapped_rows(product_row, [], sample_page)
    
    assert len(wraps) == 0

"""Unit tests for wrap detection logic."""

import pytest
from src.models.document import Document
from src.models.page import Page
from src.models.row import Row
from src.models.token import Token
from src.pipeline.wrap_detection import detect_wrapped_rows, consolidate_wrapped_description


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


def test_wrap_detection_with_x_tolerance(sample_page):
    """Test wrap detection with X-position tolerance (±2% page width)."""
    # Product row: description starts at x=10
    product_tokens = [
        Token(text="Product", x=10, y=300, width=60, height=12, page=sample_page),
        Token(text="100.00", x=500, y=300, width=60, height=12, page=sample_page),
    ]
    product_row = Row(
        tokens=product_tokens,
        y=300,
        x_min=10,
        x_max=560,
        text="Product 100.00",
        page=sample_page
    )
    
    # Wrap row: starts at similar X (within tolerance)
    # Tolerance = 0.02 * 595 = 11.9 points
    wrap_tokens = [
        Token(text="Description", x=12, y=320, width=70, height=12, page=sample_page),  # X=12 (within 11.9 tolerance)
        # No amount token
    ]
    wrap_row = Row(
        tokens=wrap_tokens,
        y=320,
        x_min=12,
        x_max=82,
        text="Description",
        page=sample_page
    )
    
    # Following row with amount (should stop wrap detection)
    next_product_tokens = [
        Token(text="Next", x=10, y=340, width=40, height=12, page=sample_page),
        Token(text="200.00", x=500, y=340, width=60, height=12, page=sample_page),
    ]
    next_product_row = Row(
        tokens=next_product_tokens,
        y=340,
        x_min=10,
        x_max=560,
        text="Next 200.00",
        page=sample_page
    )
    
    following_rows = [wrap_row, next_product_row]
    wraps = detect_wrapped_rows(product_row, following_rows, sample_page)
    
    # Should detect wrap_row as wrap, stop at next_product_row (has amount)
    assert len(wraps) == 1
    assert wraps[0] == wrap_row


def test_wrap_detection_stop_on_amount(sample_page):
    """Test that wrap detection stops on row with amount."""
    product_tokens = [
        Token(text="Product", x=10, y=300, width=60, height=12, page=sample_page),
        Token(text="100.00", x=500, y=300, width=60, height=12, page=sample_page),
    ]
    product_row = Row(
        tokens=product_tokens,
        y=300,
        x_min=10,
        x_max=560,
        text="Product 100.00",
        page=sample_page
    )
    
    # Row with amount (should stop)
    next_row_tokens = [
        Token(text="Next", x=10, y=320, width=40, height=12, page=sample_page),
        Token(text="200.00", x=500, y=320, width=60, height=12, page=sample_page),
    ]
    next_row = Row(
        tokens=next_row_tokens,
        y=320,
        x_min=10,
        x_max=560,
        text="Next 200.00",
        page=sample_page
    )
    
    wraps = detect_wrapped_rows(product_row, [next_row], sample_page)
    
    # Should not detect wrap (stopped on amount-containing row)
    assert len(wraps) == 0


def test_wrap_detection_max_wraps(sample_page):
    """Test that max 3 wraps per line item is enforced."""
    product_tokens = [
        Token(text="Product", x=10, y=300, width=60, height=12, page=sample_page),
        Token(text="100.00", x=500, y=300, width=60, height=12, page=sample_page),
    ]
    product_row = Row(
        tokens=product_tokens,
        y=300,
        x_min=10,
        x_max=560,
        text="Product 100.00",
        page=sample_page
    )
    
    # Create 5 wrap rows (should only take first 3)
    wrap_rows = []
    for i in range(5):
        wrap_tokens = [
            Token(text=f"Wrap{i}", x=10, y=320 + i*20, width=60, height=12, page=sample_page),
        ]
        wrap_row = Row(
            tokens=wrap_tokens,
            y=320 + i*20,
            x_min=10,
            x_max=70,
            text=f"Wrap{i}",
            page=sample_page
        )
        wrap_rows.append(wrap_row)
    
    wraps = detect_wrapped_rows(product_row, wrap_rows, sample_page)
    
    # Should only return max 3 wraps
    assert len(wraps) == 3
    assert wraps == wrap_rows[:3]


def test_wrap_consolidation_space_separator(sample_page):
    """Test that wrap text is consolidated with space separator."""
    product_tokens = [
        Token(text="Product", x=10, y=300, width=60, height=12, page=sample_page),
        Token(text="100.00", x=500, y=300, width=60, height=12, page=sample_page),
    ]
    product_row = Row(
        tokens=product_tokens,
        y=300,
        x_min=10,
        x_max=560,
        text="Product 100.00",
        page=sample_page
    )
    
    wrap_tokens = [
        Token(text="Description", x=10, y=320, width=70, height=12, page=sample_page),
    ]
    wrap_row = Row(
        tokens=wrap_tokens,
        y=320,
        x_min=10,
        x_max=80,
        text="Description",
        page=sample_page
    )
    
    consolidated = consolidate_wrapped_description(product_row, [wrap_row])
    
    # Should be space-separated (not newline)
    assert " " in consolidated
    assert "\n" not in consolidated
    assert "Product" in consolidated
    assert "Description" in consolidated

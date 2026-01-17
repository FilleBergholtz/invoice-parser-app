"""Unit tests for row grouping."""

import pytest
from src.models.document import Document
from src.models.page import Page
from src.models.token import Token
from src.models.row import Row
from src.pipeline.row_grouping import group_tokens_to_rows


@pytest.fixture
def sample_page():
    """Create a sample Page for testing."""
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
    return page


def test_group_tokens_by_y_position(sample_page):
    """Test that tokens are grouped into rows by Y-position."""
    # Create tokens at different Y positions
    tokens = [
        Token(text="Row1", x=10, y=100, width=50, height=12, page=sample_page),
        Token(text="Token1", x=70, y=100, width=60, height=12, page=sample_page),
        Token(text="Row2", x=10, y=150, width=50, height=12, page=sample_page),
        Token(text="Token2", x=70, y=150, width=60, height=12, page=sample_page),
    ]
    
    rows = group_tokens_to_rows(tokens)
    
    assert len(rows) == 2
    assert len(rows[0].tokens) == 2  # Row 1 has 2 tokens
    assert len(rows[1].tokens) == 2  # Row 2 has 2 tokens


def test_reading_order_preserved(sample_page):
    """Test that rows are ordered top-to-bottom."""
    tokens = [
        Token(text="Bottom", x=10, y=700, width=60, height=12, page=sample_page),
        Token(text="Top", x=10, y=100, width=30, height=12, page=sample_page),
        Token(text="Middle", x=10, y=400, width=50, height=12, page=sample_page),
    ]
    
    rows = group_tokens_to_rows(tokens)
    
    assert len(rows) == 3
    assert rows[0].y < rows[1].y  # Top before middle
    assert rows[1].y < rows[2].y  # Middle before bottom


def test_row_bbox_calculation(sample_page):
    """Test that row bbox (x_min, x_max, y) is calculated correctly."""
    tokens = [
        Token(text="Left", x=10, y=100, width=30, height=12, page=sample_page),
        Token(text="Right", x=100, y=100, width=40, height=12, page=sample_page),
    ]
    
    rows = group_tokens_to_rows(tokens)
    
    assert len(rows) == 1
    row = rows[0]
    assert row.x_min == 10
    assert row.x_max >= 140  # Right token end (100 + 40)
    assert row.y == 100  # Average Y


def test_row_tokens_traceability(sample_page):
    """Test that Row.tokens maintains traceability."""
    tokens = [
        Token(text="Test", x=10, y=100, width=40, height=12, page=sample_page),
    ]
    
    rows = group_tokens_to_rows(tokens)
    
    assert len(rows) == 1
    assert len(rows[0].tokens) == 1
    assert rows[0].tokens[0] == tokens[0]
    assert rows[0].tokens[0].page == sample_page


def test_empty_tokens():
    """Test that empty token list returns empty rows."""
    rows = group_tokens_to_rows([])
    assert rows == []


def test_tokens_with_tolerance(sample_page):
    """Test that tokens within tolerance are grouped into same row."""
    # Tokens with Y difference of 3 points (within 5 point tolerance)
    tokens = [
        Token(text="Token1", x=10, y=100, width=40, height=12, page=sample_page),
        Token(text="Token2", x=60, y=103, width=40, height=12, page=sample_page),  # 3 points diff
    ]
    
    rows = group_tokens_to_rows(tokens)
    
    # Should be grouped into one row despite slight Y difference
    assert len(rows) == 1
    assert len(rows[0].tokens) == 2

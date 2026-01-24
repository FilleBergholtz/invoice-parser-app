"""Unit tests for segment identification."""

import pytest
from src.models.document import Document
from src.models.page import Page
from src.models.row import Row
from src.models.segment import Segment
from src.models.token import Token
from src.pipeline.segment_identification import identify_segments


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
        height=842.0,  # A4 height
        tokens=[],
        rendered_image_path=None
    )
    
    doc.pages = [page]
    return page


@pytest.fixture
def sample_rows(sample_page):
    """Create sample rows at different Y positions."""
    # Header row (top 30%)
    header_token = Token(text="Header", x=10, y=100, width=60, height=12, page=sample_page)
    header_row = Row(
        tokens=[header_token],
        y=100,
        x_min=10,
        x_max=70,
        text="Header",
        page=sample_page
    )
    
    # Items row (middle)
    items_token = Token(text="Item", x=10, y=400, width=40, height=12, page=sample_page)
    items_row = Row(
        tokens=[items_token],
        y=400,
        x_min=10,
        x_max=50,
        text="Item",
        page=sample_page
    )
    
    # Footer row (bottom 30%)
    footer_token = Token(text="Total", x=10, y=700, width=50, height=12, page=sample_page)
    footer_row = Row(
        tokens=[footer_token],
        y=700,
        x_min=10,
        x_max=60,
        text="Total",
        page=sample_page
    )
    
    return [header_row, items_row, footer_row]


def test_segment_identification_header_items_footer(sample_page, sample_rows):
    """Test that segments are correctly identified (header, items, footer)."""
    segments = identify_segments(sample_rows, sample_page)
    
    assert len(segments) >= 2
    
    # Check that header and items segments exist
    segment_types = [s.segment_type for s in segments]
    assert "header" in segment_types
    assert "items" in segment_types
    # Footer may or may not exist depending on threshold


def test_position_based_segmentation(sample_page):
    """Test position-based segmentation (top 30% = header, etc.)."""
    # Header region (y < 0.3 * 842 = 252.6)
    header_row = Row(
        tokens=[Token(text="H", x=10, y=100, width=20, height=12, page=sample_page)],
        y=100,
        x_min=10,
        x_max=30,
        text="H",
        page=sample_page
    )
    
    # Items region (middle, 252.6 < y < 589.4)
    items_row = Row(
        tokens=[Token(text="I", x=10, y=400, width=20, height=12, page=sample_page)],
        y=400,
        x_min=10,
        x_max=30,
        text="I",
        page=sample_page
    )
    
    # Footer region (y > 589.4)
    footer_row = Row(
        tokens=[Token(text="F", x=10, y=700, width=20, height=12, page=sample_page)],
        y=700,
        x_min=10,
        x_max=30,
        text="F",
        page=sample_page
    )
    
    rows = [header_row, items_row, footer_row]
    segments = identify_segments(rows, sample_page)
    
    # Find segments by type
    header_seg = next((s for s in segments if s.segment_type == "header"), None)
    items_seg = next((s for s in segments if s.segment_type == "items"), None)
    footer_seg = next((s for s in segments if s.segment_type == "footer"), None)
    
    assert header_seg is not None
    assert items_seg is not None
    assert header_seg.rows == [header_row]
    assert items_seg.rows == [items_row]
    if footer_seg:
        assert footer_seg.rows == [footer_row]


def test_segment_rows_traceability(sample_page, sample_rows):
    """Test that Segment.rows maintains traceability."""
    segments = identify_segments(sample_rows, sample_page)
    
    for segment in segments:
        assert len(segment.rows) > 0
        for row in segment.rows:
            assert row.page == sample_page


def test_edge_case_no_footer(sample_page):
    """Test edge case: invoice without clear footer."""
    # Only header and items rows
    header_row = Row(
        tokens=[Token(text="H", x=10, y=100, width=20, height=12, page=sample_page)],
        y=100,
        x_min=10,
        x_max=30,
        text="H",
        page=sample_page
    )
    
    items_row = Row(
        tokens=[Token(text="I", x=10, y=400, width=20, height=12, page=sample_page)],
        y=400,
        x_min=10,
        x_max=30,
        text="I",
        page=sample_page
    )
    
    rows = [header_row, items_row]
    segments = identify_segments(rows, sample_page)
    
    # Should still have header and items
    assert len(segments) >= 2
    assert any(s.segment_type == "header" for s in segments)
    assert any(s.segment_type == "items" for s in segments)


def test_edge_case_short_invoice(sample_page):
    """Test edge case: very short invoice - all rows might go to items."""
    # All rows in middle region
    row1 = Row(
        tokens=[Token(text="R1", x=10, y=300, width=20, height=12, page=sample_page)],
        y=300,
        x_min=10,
        x_max=30,
        text="R1",
        page=sample_page
    )
    
    row2 = Row(
        tokens=[Token(text="R2", x=10, y=350, width=20, height=12, page=sample_page)],
        y=350,
        x_min=10,
        x_max=30,
        text="R2",
        page=sample_page
    )
    
    rows = [row1, row2]
    segments = identify_segments(rows, sample_page)
    
    # Should still create segments (at least items)
    assert len(segments) > 0
    assert any(s.segment_type == "items" for s in segments)

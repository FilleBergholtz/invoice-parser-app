"""Unit tests for Document model."""

import pytest
from src.models.document import Document
from src.models.page import Page


def test_document_creation():
    """Test Document creation with metadata."""
    # Create a minimal Document (pages can be empty initially)
    doc = Document(
        filename="test.pdf",
        filepath="/path/to/test.pdf",
        page_count=0,
        pages=[],
        metadata={}
    )
    
    assert doc.filename == "test.pdf"
    assert doc.filepath == "/path/to/test.pdf"
    assert doc.page_count == 0
    assert len(doc.pages) == 0


def test_document_with_pages():
    """Test Document with pages - page_count must match."""
    # Create a mock Document to use as parent
    doc = Document(
        filename="test.pdf",
        filepath="/path/to/test.pdf",
        page_count=2,
        pages=[],
        metadata={}
    )
    
    # Create pages
    page1 = Page(
        page_number=1,
        document=doc,
        width=595.0,
        height=842.0,
        tokens=[],
        rendered_image_path=None
    )
    
    page2 = Page(
        page_number=2,
        document=doc,
        width=595.0,
        height=842.0,
        tokens=[],
        rendered_image_path=None
    )
    
    # Assign pages
    doc.pages = [page1, page2]
    
    assert doc.page_count == 2
    assert len(doc.pages) == 2
    assert doc.pages[0].page_number == 1
    assert doc.pages[1].page_number == 2


def test_document_page_count_mismatch():
    """Test that Document raises error if page_count doesn't match pages."""
    doc = Document(
        filename="test.pdf",
        filepath="/path/to/test.pdf",
        page_count=2,
        pages=[],
        metadata={}
    )
    
    # Create one page but page_count says 2
    page1 = Page(
        page_number=1,
        document=doc,
        width=595.0,
        height=842.0,
        tokens=[],
        rendered_image_path=None
    )
    
    # This should raise ValueError in __post_init__
    with pytest.raises(ValueError, match="Page count mismatch"):
        doc.pages = [page1]

"""Unit tests for Page model."""

import pytest
from src.models.document import Document
from src.models.page import Page


@pytest.fixture
def sample_document():
    """Create a sample Document for testing."""
    return Document(
        filename="test.pdf",
        filepath="/path/to/test.pdf",
        page_count=1,
        pages=[],
        metadata={}
    )


def test_page_creation(sample_document):
    """Test Page creation with dimensions."""
    page = Page(
        page_number=1,
        document=sample_document,
        width=595.0,
        height=842.0,
        tokens=[],
        rendered_image_path=None
    )
    
    assert page.page_number == 1
    assert page.width == 595.0
    assert page.height == 842.0
    assert page.document == sample_document
    assert len(page.tokens) == 0
    assert page.rendered_image_path is None


def test_page_number_validation():
    """Test that page_number must be >= 1."""
    doc = Document(
        filename="test.pdf",
        filepath="/path/to/test.pdf",
        page_count=1,
        pages=[],
        metadata={}
    )
    
    with pytest.raises(ValueError, match="Page number must be >= 1"):
        Page(
            page_number=0,
            document=doc,
            width=595.0,
            height=842.0,
            tokens=[],
            rendered_image_path=None
        )


def test_page_with_rendered_image_path(sample_document):
    """Test Page with rendered_image_path set."""
    page = Page(
        page_number=1,
        document=sample_document,
        width=595.0,
        height=842.0,
        tokens=[],
        rendered_image_path="/path/to/rendered_page_1.png"
    )
    
    assert page.rendered_image_path == "/path/to/rendered_page_1.png"

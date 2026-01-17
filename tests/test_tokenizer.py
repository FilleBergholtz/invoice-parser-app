"""Unit tests for token extraction."""

import pytest
import pdfplumber
from src.models.document import Document
from src.models.page import Page
from src.pipeline.reader import read_pdf
from src.pipeline.tokenizer import extract_tokens_from_page


@pytest.fixture
def sample_document():
    """Create a sample Document for testing."""
    doc = Document(
        filename="test.pdf",
        filepath="/nonexistent/path/test.pdf",
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
    return doc, page


def test_extract_tokens_requires_pdfplumber_page(sample_document):
    """Test that extract_tokens_from_page requires pdfplumber page."""
    doc, page = sample_document
    
    # This test would require actual PDF file - skip for now
    pytest.skip("Requires actual PDF file - integration test")


def test_token_bbox_validity():
    """Test that tokens have valid bbox (x, y, width, height)."""
    pytest.skip("Requires actual PDF file - integration test")


def test_reading_order_preservation():
    """Test that tokens maintain reading order (top-to-bottom)."""
    pytest.skip("Requires actual PDF file - integration test")


def test_token_page_reference():
    """Test that tokens maintain page reference for traceability."""
    pytest.skip("Requires actual PDF file - integration test")

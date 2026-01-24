"""Unit tests for PDF type detection."""

import pytest
from src.models.document import Document
from src.pipeline.pdf_detection import (
    detect_pdf_type,
    route_extraction_path,
    get_detection_info,
    PDFType
)


@pytest.fixture
def mock_document_searchable(tmp_path):
    """Create a mock searchable PDF document for testing.
    
    Note: This is a placeholder - real tests would need actual PDF files.
    """
    # For now, we'll skip tests that require actual PDF files
    # These would be integration tests with real PDFs
    pytest.skip("Requires actual PDF file - integration test")


@pytest.fixture
def mock_document_scanned(tmp_path):
    """Create a mock scanned PDF document for testing."""
    pytest.skip("Requires actual PDF file - integration test")


def test_detect_pdf_type_returns_valid_value():
    """Test that detect_pdf_type returns valid PDF type string."""
    # Create minimal document
    doc = Document(
        filename="test.pdf",
        filepath="/nonexistent/path/test.pdf",
        page_count=0,
        pages=[],
        metadata={}
    )
    
    # Should default to "scanned" if file doesn't exist
    pdf_type = detect_pdf_type(doc)
    assert pdf_type in [PDFType.SEARCHABLE.value, PDFType.SCANNED.value]


def test_route_extraction_path():
    """Test that route_extraction_path returns valid path identifier."""
    doc = Document(
        filename="test.pdf",
        filepath="/nonexistent/path/test.pdf",
        page_count=0,
        pages=[],
        metadata={}
    )
    
    path = route_extraction_path(doc)
    assert path in ["pdfplumber", "ocr"]


def test_get_detection_info():
    """Test that get_detection_info returns structured information."""
    doc = Document(
        filename="test.pdf",
        filepath="/nonexistent/path/test.pdf",
        page_count=0,
        pages=[],
        metadata={}
    )
    
    info = get_detection_info(doc)
    
    assert "pdf_type" in info
    assert "confidence" in info
    assert "text_layer_info" in info
    assert info["pdf_type"] in [PDFType.SEARCHABLE.value, PDFType.SCANNED.value]
    assert info["confidence"] in ["HIGH", "MEDIUM", "LOW"]

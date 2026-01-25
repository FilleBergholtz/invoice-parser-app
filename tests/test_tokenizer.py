"""Unit tests for token extraction."""

import pytest
import pdfplumber
from pathlib import Path

from src.models.document import Document
from src.models.page import Page
from src.pipeline.reader import read_pdf
from src.pipeline.tokenizer import extract_tokens_from_page


def _make_minimal_pdf(path: Path) -> None:
    """Skapa en minimal PDF med text som pdfplumber kan extrahera (pymupdf)."""
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 72), "Faktura", fontsize=12)
    page.insert_text((72, 100), "Total 100 SEK", fontsize=11)
    page.insert_text((72, 128), "Artikel A", fontsize=10)
    doc.save(str(path))
    doc.close()


@pytest.fixture
def minimal_pdf_path(tmp_path):
    """En minimal PDF-fil med extraherbar text (skapas med pymupdf)."""
    pdf_path = tmp_path / "minimal.pdf"
    _make_minimal_pdf(pdf_path)
    return pdf_path


@pytest.fixture
def doc_and_pdfplumber_page(minimal_pdf_path):
    """Document (från read_pdf) och pdfplumber-sida för sida 1."""
    doc = read_pdf(str(minimal_pdf_path))
    assert len(doc.pages) >= 1
    page = doc.pages[0]
    with pdfplumber.open(minimal_pdf_path) as pdf:
        pp_page = pdf.pages[0]
        yield doc, page, pp_page


@pytest.fixture
def sample_document():
    """Create a sample Document for testing (utan PDF-fil)."""
    doc = Document(
        filename="test.pdf",
        filepath="/nonexistent/path/test.pdf",
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
    return doc, page


def test_extract_tokens_requires_pdfplumber_page(doc_and_pdfplumber_page):
    """Test att extract_tokens_from_page kräver pdfplumber-sida och returnerar tokens."""
    _, page, pdfplumber_page = doc_and_pdfplumber_page
    tokens = extract_tokens_from_page(page, pdfplumber_page)
    assert isinstance(tokens, list)
    assert len(tokens) >= 1
    assert all(t.text for t in tokens)


def test_token_bbox_validity(doc_and_pdfplumber_page):
    """Test att tokens har giltig bbox (x,y,w,h >= 0, w,h > 0)."""
    _, page, pdfplumber_page = doc_and_pdfplumber_page
    tokens = extract_tokens_from_page(page, pdfplumber_page)
    for t in tokens:
        assert t.x >= 0, f"token {t.text!r}: x must be >= 0"
        assert t.y >= 0, f"token {t.text!r}: y must be >= 0"
        assert t.width > 0, f"token {t.text!r}: width must be > 0"
        assert t.height > 0, f"token {t.text!r}: height must be > 0"


def test_reading_order_preservation(doc_and_pdfplumber_page):
    """Test att tokens är i läsordning (top-to-bottom, sedan left-to-right)."""
    _, page, pdfplumber_page = doc_and_pdfplumber_page
    tokens = extract_tokens_from_page(page, pdfplumber_page)
    if len(tokens) < 2:
        pytest.skip("Behöver minst 2 tokens för att kontrollera ordning")
    # tokenizer använder _tokens_reading_order: först y, sedan x
    for i in range(len(tokens) - 1):
        a, b = tokens[i], tokens[i + 1]
        # antingen lägre y, eller samma rad (närma y) och då lägre x
        assert (a.y < b.y) or (abs(a.y - b.y) < 20 and a.x <= b.x), (
            f"Ordning bryts: {a.text!r} (y={a.y}, x={a.x}) vs {b.text!r} (y={b.y}, x={b.x})"
        )


def test_token_page_reference(doc_and_pdfplumber_page):
    """Test att alla tokens har page-referens till den sida som användes."""
    _, page, pdfplumber_page = doc_and_pdfplumber_page
    tokens = extract_tokens_from_page(page, pdfplumber_page)
    for t in tokens:
        assert t.page is page
        assert t.page.page_number == page.page_number

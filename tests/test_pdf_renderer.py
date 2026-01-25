"""Unit tests for PDF page to image rendering."""

import pytest
from pathlib import Path
from unittest.mock import patch

from src.pipeline.reader import read_pdf
from src.pipeline.pdf_renderer import render_page_to_image


def _make_minimal_pdf(path: Path) -> None:
    """Skapa en minimal PDF som pymupdf/fitz kan rendera."""
    import fitz
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(str(path))
    doc.close()


@pytest.fixture
def minimal_pdf_path(tmp_path):
    """En minimal PDF-fil (skapas med pymupdf)."""
    p = tmp_path / "minimal.pdf"
    _make_minimal_pdf(p)
    return p


@pytest.fixture
def page_for_render(minimal_pdf_path):
    """En Page som pekar på minimal_pdf_path, redo för render_page_to_image."""
    doc = read_pdf(str(minimal_pdf_path))
    return doc.pages[0]


def test_render_page_to_image_requires_pymupdf(page_for_render, tmp_path):
    """Kräver pymupdf; om det finns ska rendering lyckas och returnera sökväg."""
    out = tmp_path / "out"
    out.mkdir()
    path = render_page_to_image(page_for_render, str(out), dpi=72)
    assert path
    assert Path(path).exists()
    assert path.endswith(".png")


def test_rendered_image_path_set(page_for_render, tmp_path):
    """Page.rendered_image_path sätts efter rendering."""
    out = tmp_path / "out"
    out.mkdir()
    assert page_for_render.rendered_image_path is None
    path = render_page_to_image(page_for_render, str(out), dpi=72)
    assert page_for_render.rendered_image_path == path
    assert Path(path).exists()


def test_image_file_exists(page_for_render, tmp_path):
    """Renderad fil finns och är giltig PNG."""
    out = tmp_path / "out"
    out.mkdir()
    path = render_page_to_image(page_for_render, str(out), dpi=72)
    p = Path(path)
    assert p.exists()
    assert p.stat().st_size > 0
    # Giltig PNG: magiska bytes 89 50 4E 47
    with open(p, "rb") as f:
        header = f.read(4)
    assert header == b"\x89PNG"


def test_coordinate_system_consistency(page_for_render, tmp_path):
    """Bildens pixelstorlek stämmer med sidans storlek i punkter vid given DPI."""
    dpi = 72
    out = tmp_path / "out"
    out.mkdir()
    render_page_to_image(page_for_render, str(out), dpi=dpi)
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("PIL/Pillow krävs för att läsa bildstorlek")
    img_path = Path(page_for_render.rendered_image_path)
    with Image.open(img_path) as img:
        w, h = img.size
    # Sidan är 595x842 punkter; vid 72 DPI => 595x842 pixlar (scale 1)
    expected_w = int(page_for_render.width * dpi / 72)
    expected_h = int(page_for_render.height * dpi / 72)
    assert w == expected_w
    assert h == expected_h


@patch("src.pipeline.pdf_renderer.fitz", None)
def test_render_page_to_image_missing_dependencies(page_for_render, tmp_path):
    """Om pymupdf saknas ska ImportError höjas."""
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(ImportError, match="pymupdf.*required"):
        render_page_to_image(page_for_render, str(out))

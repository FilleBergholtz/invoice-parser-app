"""PDF page to image conversion with configurable DPI and consistent coordinates.

R1 (14-RESEARCH): Baseline 300 DPI; retry at 400 DPI only when ocr_mean_conf < 55
after first OCR, max 1 retry per page. Orchestration (14-06) decides when to retry.
"""

import os
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    fitz = None

from ..models.page import Page

# R1 constants for orchestration (14-RESEARCH): when to use RETRY_DPI
BASELINE_DPI = 300
RETRY_DPI = 400
OCR_MEAN_CONF_RETRY_THRESHOLD = 55  # retry at RETRY_DPI when ocr_mean_conf < this
MAX_DPI_RETRIES_PER_PAGE = 1


class PDFRenderError(Exception):
    """Raised when PDF rendering fails."""
    pass


def render_page_to_image(page: Page, output_dir: str, dpi: int = 300) -> str:
    """Convert PDF page to image with given DPI and consistent coordinate system.
    
    Default 300 DPI is baseline per R1. Use dpi=RETRY_DPI (400) for OCR retry when
    ocr_mean_conf < OCR_MEAN_CONF_RETRY_THRESHOLD after first pass; max 1 retry per page.
    
    Args:
        page: Page object to render
        output_dir: Directory to save rendered image
        dpi: Resolution in dots per inch (default 300; 400 for OCR retry per R1).
        
    Returns:
        Path to saved image file
        
    Raises:
        PDFRenderError: If rendering fails (corrupt page, missing dependencies)
        ImportError: If pymupdf (fitz) is not installed
    """
    if fitz is None:
        raise ImportError(
            "pymupdf (fitz) is required for PDF rendering. "
            "Install with: pip install pymupdf"
        )
    
    try:
        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename: {document_filename}_page_{page_number}.png
        doc_filename = Path(page.document.filename).stem  # Remove extension
        image_filename = f"{doc_filename}_page_{page.page_number}.png"
        image_path = output_path / image_filename
        
        # Open PDF document with fitz
        pdf_doc = fitz.open(page.document.filepath)
        
        # Get the specific page (page_number is 1-indexed, fitz uses 0-indexed)
        fitz_page = pdf_doc[page.page_number - 1]
        
        # Render page to pixmap at requested DPI (default 300; 400 for OCR retry)
        # Matrix: scale factor for DPI (dpi / 72)
        zoom = float(dpi) / 72.0
        mat = fitz.Matrix(zoom, zoom)
        
        pix = fitz_page.get_pixmap(matrix=mat)
        
        # Save as PNG
        pix.save(str(image_path))
        
        # Clean up
        pix = None
        pdf_doc.close()
        
        # Set rendered_image_path on page for traceability
        page.rendered_image_path = str(image_path)
        
        return str(image_path)
        
    except Exception as e:
        raise PDFRenderError(
            f"Failed to render page {page.page_number} from {page.document.filename}: {str(e)}"
        ) from e

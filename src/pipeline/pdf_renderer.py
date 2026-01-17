"""PDF page to image conversion with standardized DPI (300) and consistent coordinates."""

import os
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    fitz = None

from ..models.page import Page


class PDFRenderError(Exception):
    """Raised when PDF rendering fails."""
    pass


def render_page_to_image(page: Page, output_dir: str) -> str:
    """Convert PDF page to image with standardized DPI (300) and consistent coordinate system.
    
    Args:
        page: Page object to render
        output_dir: Directory to save rendered image
        
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
        
        # Render page to pixmap at 300 DPI
        # Matrix: scale factor for DPI (300 DPI / 72 DPI = 4.1667)
        zoom = 300.0 / 72.0
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

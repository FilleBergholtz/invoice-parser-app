"""PDF reading functionality using pdfplumber."""

import pdfplumber
from typing import List, cast

from ..models.document import Document
from ..models.page import Page


class PDFReadError(Exception):
    """Raised when PDF reading fails."""
    pass


def read_pdf(filepath: str) -> Document:
    """Read a PDF file and create Document object with all pages.
    
    Args:
        filepath: Path to PDF file
        
    Returns:
        Document object with all pages extracted
        
    Raises:
        PDFReadError: If PDF cannot be read or is corrupt
        FileNotFoundError: If filepath does not exist
    """
    try:
        # Open PDF with pdfplumber
        pdf = pdfplumber.open(filepath)
        
        # Extract metadata
        filename = filepath.split('/')[-1].split('\\')[-1]  # Handle both / and \
        page_count = len(pdf.pages)
        
        # Extract all pages first (before creating Document)
        # We need to create pages list, then Document, then link them
        pages = []
        # Create a placeholder doc reference first (we'll update it after)
        # Use a temporary object pattern to avoid circular dependency
        temp_doc = cast(Document, object())  # Placeholder; document set on pages after Document creation

        for i, pdfplumber_page in enumerate(pdf.pages, start=1):
            # Get page dimensions (width, height in points)
            width = float(pdfplumber_page.width)
            height = float(pdfplumber_page.height)

            # Create Page object (document reference updated after Document creation below)
            page = Page(
                page_number=i,
                document=temp_doc,
                width=width,
                height=height,
                tokens=[],  # Initially empty, populated later
                rendered_image_path=None  # Initially None, set if OCR needed
            )
            pages.append(page)
        
        # Create Document with pages already populated
        doc = Document(
            filename=filename,
            filepath=filepath,
            page_count=page_count,
            pages=pages,
            metadata={}
        )
        
        # Set document reference for all pages (using object.__setattr__ to bypass dataclass frozen if needed)
        for page in pages:
            object.__setattr__(page, 'document', doc)
        
        pdf.close()
        
        return doc
        
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {filepath}")
    except Exception as e:
        raise PDFReadError(f"Failed to read PDF {filepath}: {str(e)}") from e


def extract_pages(document: Document) -> List[Page]:
    """Extract all pages from a Document.
    
    Args:
        document: Document object
        
    Returns:
        List of Page objects from the document
    """
    return document.pages

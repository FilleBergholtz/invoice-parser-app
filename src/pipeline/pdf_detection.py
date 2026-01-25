"""PDF type detection and routing logic."""

from enum import Enum
from typing import Any, Dict, Optional

from ..models.document import Document
from ..pipeline.reader import read_pdf
import pdfplumber


class PDFType(str, Enum):
    """PDF type classification."""
    SEARCHABLE = "searchable"
    SCANNED = "scanned"


class DetectionConfidence(str, Enum):
    """Confidence level for PDF type detection."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def detect_pdf_type(document: Document) -> str:
    """Detect whether PDF is searchable (has text layer) or scanned (image-only).
    
    Args:
        document: Document object to analyze
        
    Returns:
        "searchable" or "scanned"
        
    Note:
        Defaults to "scanned" if detection fails (safer fallback - OCR can handle both,
        but pdfplumber cannot handle image-only).
    """
    try:
        # Open PDF with pdfplumber to check for text layer
        pdf = pdfplumber.open(document.filepath)
        
        total_text_chars = 0
        pages_with_text = 0
        
        # Check each page for extractable text
        for page in pdf.pages:
            try:
                # Extract text - if PDF is searchable, this will return text
                page_text = page.extract_text()
                
                if page_text and len(page_text.strip()) > 0:
                    # Page has extractable text
                    total_text_chars += len(page_text.strip())
                    pages_with_text += 1
                    
            except Exception:
                # Page extraction failed, assume no text
                pass
        
        pdf.close()
        
        # Decision logic:
        # - If majority of pages have substantial text (>50 chars) → searchable
        # - If no pages have text or minimal text → scanned
        text_ratio = pages_with_text / document.page_count if document.page_count > 0 else 0
        
        if text_ratio >= 0.5 and total_text_chars > 50:
            return PDFType.SEARCHABLE.value
        elif text_ratio >= 0.3 and total_text_chars > 20:
            # Medium confidence case - likely searchable but some ambiguity
            return PDFType.SEARCHABLE.value
        else:
            # Minimal or no text → scanned
            return PDFType.SCANNED.value
            
    except Exception:
        # If detection fails, default to "scanned" (safer fallback)
        return PDFType.SCANNED.value


def route_extraction_path(document: Document) -> str:
    """Route to appropriate extraction path based on PDF type.
    
    Args:
        document: Document object
        
    Returns:
        Extraction path identifier: "pdfplumber" or "ocr"
    """
    pdf_type = detect_pdf_type(document)
    
    if pdf_type == PDFType.SEARCHABLE.value:
        return "pdfplumber"
    else:
        return "ocr"


def get_detection_info(document: Document) -> Dict[str, Any]:
    """Get detailed detection information.
    
    Args:
        document: Document object
        
    Returns:
        Dictionary with:
        - pdf_type: "searchable" or "scanned"
        - confidence: "HIGH", "MEDIUM", or "LOW"
        - text_layer_info: percentage of pages with extractable text
    """
    try:
        pdf = pdfplumber.open(document.filepath)
        
        pages_with_text = 0
        total_chars = 0
        
        for page in pdf.pages:
            try:
                text = page.extract_text()
                if text and len(text.strip()) > 0:
                    pages_with_text += 1
                    total_chars += len(text.strip())
            except Exception:
                pass
        
        pdf.close()
        
        text_percentage = (pages_with_text / document.page_count * 100) if document.page_count > 0 else 0
        pdf_type = detect_pdf_type(document)
        
        # Determine confidence
        if text_percentage >= 80 and total_chars > 200:
            confidence = DetectionConfidence.HIGH.value
        elif text_percentage >= 50 and total_chars > 50:
            confidence = DetectionConfidence.MEDIUM.value
        else:
            confidence = DetectionConfidence.LOW.value
        
        return {
            "pdf_type": pdf_type,
            "confidence": confidence,
            "text_layer_info": f"{text_percentage:.1f}% of pages have extractable text",
            "pages_with_text": pages_with_text,
            "total_chars": total_chars
        }
        
    except Exception:
        return {
            "pdf_type": PDFType.SCANNED.value,
            "confidence": DetectionConfidence.LOW.value,
            "text_layer_info": "Detection failed, defaulting to scanned",
            "pages_with_text": 0,
            "total_chars": 0
        }

"""OCR abstraction layer with Tesseract implementation."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

from ..models.page import Page
from ..models.token import Token


class OCRException(Exception):
    """Raised when OCR processing fails."""
    pass


class OCREngine(ABC):
    """Abstract base class for OCR engines."""
    
    @abstractmethod
    def extract_tokens(self, page: Page) -> List[Token]:
        """Extract tokens from a rendered page image.
        
        Args:
            page: Page object with rendered_image_path set
            
        Returns:
            List of Token objects with spatial information and confidence
            
        Raises:
            OCRException: If OCR processing fails
        """
        pass


class TesseractOCREngine(OCREngine):
    """Tesseract OCR engine implementation.
    
    Uses pytesseract wrapper with Swedish language support.
    Returns tokens with bbox and confidence from TSV/HOCR output.
    """
    
    def __init__(self, lang: str = 'swe'):
        """Initialize Tesseract OCR engine.
        
        Args:
            lang: Language code (default: 'swe' for Swedish)
        """
        if pytesseract is None:
            raise ImportError(
                "pytesseract is required for OCR. "
                "Install with: pip install pytesseract pillow. "
                "Also ensure Tesseract OCR is installed on system with Swedish language data."
            )
        
        if Image is None:
            raise ImportError(
                "Pillow (PIL) is required for image handling. "
                "Install with: pip install pillow"
            )
        
        self.lang = lang
        self._verify_tesseract()
    
    def _verify_tesseract(self):
        """Verify Tesseract is installed and language data is available."""
        try:
            # Try to get version
            version = pytesseract.get_tesseract_version()
            
            # Try to get available languages
            try:
                langs = pytesseract.get_languages()
                if self.lang not in langs:
                    raise OCRException(
                        f"Tesseract language '{self.lang}' not found. "
                        f"Available languages: {', '.join(langs)}. "
                        f"Install Swedish language data for Tesseract."
                    )
            except Exception as e:
                if "not found" in str(e).lower():
                    raise OCRException(
                        f"Tesseract language '{self.lang}' not found. "
                        f"Install Swedish language data for Tesseract."
                    ) from e
                # If we can't check languages, continue anyway
                pass
                
        except Exception as e:
            raise OCRException(
                f"Tesseract OCR not found or not accessible: {str(e)}. "
                f"Install Tesseract OCR and ensure it's in PATH."
            ) from e
    
    def extract_tokens(self, page: Page) -> List[Token]:
        """Extract tokens from rendered page image using Tesseract.
        
        Args:
            page: Page object with rendered_image_path set
            
        Returns:
            List of Token objects with bbox and confidence
            
        Raises:
            OCRException: If rendered_image_path is missing or OCR fails
        """
        if page.rendered_image_path is None:
            raise OCRException(
                f"Page {page.page_number} does not have rendered_image_path set. "
                f"Render page to image first using render_page_to_image()."
            )
        
        if not Path(page.rendered_image_path).exists():
            raise OCRException(
                f"Rendered image not found: {page.rendered_image_path}"
            )
        
        try:
            # Load image
            img = Image.open(page.rendered_image_path)
            
            # Use TSV output to get bbox + confidence
            # TSV format: level page_num block_num par_num line_num word_num left top width height conf text
            tsv_data = pytesseract.image_to_data(
                img,
                lang=self.lang,
                output_type=pytesseract.Output.TSV,
                config='--psm 6'  # Assume uniform block of text
            )
            
            tokens = []
            
            # Parse TSV data
            lines = tsv_data.strip().split('\n')
            headers = lines[0].split('\t')
            
            # Find column indices
            try:
                text_idx = headers.index('text')
                left_idx = headers.index('left')
                top_idx = headers.index('top')
                width_idx = headers.index('width')
                height_idx = headers.index('height')
                conf_idx = headers.index('conf')
            except ValueError as e:
                raise OCRException(f"Unexpected TSV format: {str(e)}") from e
            
            # Process each word (level 5 in TSV)
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                fields = line.split('\t')
                
                # Get word text
                text = fields[text_idx].strip()
                if not text:
                    continue
                
                # Get bounding box
                try:
                    x = float(fields[left_idx])
                    y = float(fields[top_idx])
                    width = float(fields[width_idx])
                    height = float(fields[height_idx])
                    confidence = float(fields[conf_idx])
                except (ValueError, IndexError):
                    continue  # Skip invalid rows
                
                # Convert confidence from 0-100 to 0.0-1.0
                confidence_normalized = confidence / 100.0 if confidence > 0 else 0.0
                
                # Convert Tesseract coordinates to Page coordinate system
                # Tesseract uses image coordinates (pixels), Page uses points
                # Scale factor depends on DPI: 300 DPI / 72 DPI = 4.1667
                # But we need to match to Page.width/height
                # For now, assume image matches page dimensions (rendered at same scale)
                # TODO: Proper coordinate transformation if needed
                
                # Create Token object
                token = Token(
                    text=text,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    page=page,
                    font_size=None,  # Not available from Tesseract TSV
                    font_name=None
                )
                
                tokens.append(token)
            
            # Sort tokens by reading order (top-to-bottom, left-to-right)
            tokens.sort(key=lambda t: (t.y, t.x))
            
            return tokens
            
        except Exception as e:
            raise OCRException(
                f"OCR processing failed for page {page.page_number}: {str(e)}"
            ) from e


def extract_tokens_with_ocr(page: Page, engine: Optional[OCREngine] = None) -> List[Token]:
    """Extract tokens from page using OCR.
    
    Args:
        page: Page object with rendered_image_path set
        engine: Optional OCR engine (defaults to TesseractOCREngine)
        
    Returns:
        List of Token objects with spatial information
    """
    if engine is None:
        engine = TesseractOCREngine()
    
    return engine.extract_tokens(page)


# Convenience: Create default engine instance
_default_ocr_engine: Optional[OCREngine] = None


def get_default_ocr_engine() -> OCREngine:
    """Get or create default OCR engine instance."""
    global _default_ocr_engine
    if _default_ocr_engine is None:
        _default_ocr_engine = TesseractOCREngine()
    return _default_ocr_engine

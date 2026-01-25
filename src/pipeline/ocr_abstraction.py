"""OCR abstraction layer with Tesseract implementation."""

import statistics
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
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

# Vanlig installationssökväg på Windows; används om Tesseract inte finns i PATH
TESSERACT_DEFAULT_WIN_PATH = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def _apply_tesseract_default_path() -> None:
    """Sätt tesseract_cmd till C:\\Program Files\\Tesseract-OCR om den filen finns (Windows)."""
    if sys.platform != "win32" or pytesseract is None:
        return
    if TESSERACT_DEFAULT_WIN_PATH.is_file():
        pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_DEFAULT_WIN_PATH)


class OCRException(Exception):
    """Raised when OCR processing fails."""
    pass


@dataclass
class OCRPageMetrics:
    """Per-page OCR confidence metrics for routing.
    
    Mean is used for DPI retry sensitivity, median for routing robustness.
    All values use 0–100 scale (Tesseract native).
    """
    mean_conf: float
    median_conf: float
    low_conf_fraction: float  # fraction of word tokens with confidence < 50


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
        _apply_tesseract_default_path()
        self._verify_tesseract()
    
    def _verify_tesseract(self) -> None:
        """Verify Tesseract is installed and language data is available."""
        assert pytesseract is not None  # ensured by __init__ guard
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
        
        assert pytesseract is not None and Image is not None  # ensured by __init__ guards
        try:
            # Load image
            img = Image.open(page.rendered_image_path)
            img_width, img_height = img.size  # pixels

            # Scale OCR pixel coordinates to page space (points).
            # Render is 300 DPI; page dimensions are in points (72 DPI).
            # scale = page_points / image_pixels.
            if img_width > 0 and img_height > 0 and getattr(page, 'width', None) and getattr(page, 'height', None):
                scale_x = float(page.width) / img_width
                scale_y = float(page.height) / img_height
            else:
                scale_x = 72.0 / 300.0
                scale_y = 72.0 / 300.0

            # Use TSV output to get bbox + confidence (output_type 4 = TSV, robust across pytesseract versions)
            # TSV format: level page_num block_num par_num line_num word_num left top width height conf text
            output_tsv = getattr(getattr(pytesseract, "Output", None), "TSV", 4)
            out_type: str | int = output_tsv if isinstance(output_tsv, (str, int)) else 4
            tsv_data = pytesseract.image_to_data(
                img,
                lang=self.lang,
                output_type=out_type,  # type: ignore[arg-type]
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
                
                # Get bounding box (pixels) and confidence
                try:
                    x_px = float(fields[left_idx])
                    y_px = float(fields[top_idx])
                    w_px = float(fields[width_idx])
                    h_px = float(fields[height_idx])
                    conf = float(fields[conf_idx])
                except (ValueError, IndexError):
                    continue  # Skip invalid rows
                # Exclude layout rows: conf == -1 for level 1–4; only level 5 (word) has conf 0–100.
                # Mean is used for DPI retry sensitivity, median for routing robustness.
                if conf < 0:
                    continue
                confidence = conf  # 0–100 scale, stored on Token for aggregation
                # Scale to page coordinates (points) for segment_identification
                x = x_px * scale_x
                y = y_px * scale_y
                width = w_px * scale_x
                height = h_px * scale_y
                token = Token(
                    text=text,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    page=page,
                    font_size=None,
                    font_name=None,
                    confidence=confidence,
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
        List of Token objects with spatial information and confidence (0–100)
    """
    if engine is None:
        engine = TesseractOCREngine()
    
    return engine.extract_tokens(page)


# R2: thresholds for routing (14-RESEARCH)
OCR_EXCLUDE_CONF_BELOW = 0
OCR_MEDIAN_CONF_ROUTING_THRESHOLD = 70
OCR_LOW_CONF_FRACTION_THRESHOLD = 0.25
OCR_LOW_CONF_WORD_THRESHOLD = 50  # tokens with confidence < 50 count as "low conf"


def ocr_page_metrics(tokens: List[Token]) -> OCRPageMetrics:
    """Compute per-page OCR confidence metrics from tokens with confidence set.
    
    Only tokens with confidence is not None and >= OCR_EXCLUDE_CONF_BELOW (0) are
    included. Mean is used for DPI retry sensitivity, median for routing robustness.
    
    Args:
        tokens: List of Token from OCR (token.confidence in 0–100)
        
    Returns:
        OCRPageMetrics with mean_conf, median_conf, low_conf_fraction
    """
    confs = [t.confidence for t in tokens if t.confidence is not None and t.confidence >= OCR_EXCLUDE_CONF_BELOW]
    if not confs:
        return OCRPageMetrics(mean_conf=0.0, median_conf=0.0, low_conf_fraction=1.0)
    n = len(confs)
    low = sum(1 for c in confs if c < OCR_LOW_CONF_WORD_THRESHOLD)
    return OCRPageMetrics(
        mean_conf=statistics.mean(confs),
        median_conf=statistics.median(confs),
        low_conf_fraction=low / n,
    )


# Convenience: Create default engine instance
_default_ocr_engine: Optional[OCREngine] = None


def get_default_ocr_engine() -> OCREngine:
    """Get or create default OCR engine instance."""
    global _default_ocr_engine
    if _default_ocr_engine is None:
        _default_ocr_engine = TesseractOCREngine()
    return _default_ocr_engine

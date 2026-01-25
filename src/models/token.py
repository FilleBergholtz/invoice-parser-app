"""Token data model representing a text unit with spatial information."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .page import Page


@dataclass
class Token:
    """Represents a text unit with spatial information (position and dimensions).
    
    Coordinate system:
    - Origin (0, 0) is top-left corner
    - X increases rightward
    - Y increases downward
    
    Attributes:
        text: The text content
        x: X-coordinate (left edge)
        y: Y-coordinate (top edge)
        width: Token width
        height: Token height
        page: Reference to parent Page for traceability
        font_size: Optional font size (if available from source)
        font_name: Optional font name (if available from source)
        confidence: Optional confidence 0–100 (e.g. from OCR TSV); None for pdfplumber tokens
    """
    
    text: str
    x: float
    y: float
    width: float
    height: float
    page: Page
    font_size: Optional[float] = None
    font_name: Optional[str] = None
    confidence: Optional[float] = None  # 0–100 from Tesseract; None when from pdfplumber
    
    def __post_init__(self):
        """Validate bbox dimensions are non-negative."""
        if self.width < 0 or self.height < 0:
            raise ValueError(
                f"Token dimensions must be non-negative: "
                f"width={self.width}, height={self.height}"
            )

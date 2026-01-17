"""Page data model representing a single page from a PDF document."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .document import Document
    from .token import Token


@dataclass
class Page:
    """Represents a single page from a PDF document.
    
    Attributes:
        page_number: Page number (starts at 1)
        document: Reference to parent Document
        width: Page width in points
        height: Page height in points
        tokens: List of Token objects on this page (initially empty)
        rendered_image_path: Optional path to rendered image (for OCR path)
    """
    
    page_number: int
    document: Document
    width: float
    height: float
    tokens: List[Token] = field(default_factory=list)
    rendered_image_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate page number is positive."""
        if self.page_number < 1:
            raise ValueError(f"Page number must be >= 1, got {self.page_number}")

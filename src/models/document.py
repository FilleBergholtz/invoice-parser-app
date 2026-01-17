"""Document data model representing a PDF invoice."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .page import Page


@dataclass
class Document:
    """Represents a PDF document.
    
    Attributes:
        filename: PDF filename
        filepath: Full path to PDF file
        page_count: Number of pages in document
        pages: List of Page objects
        metadata: Optional additional metadata
    """
    
    filename: str
    filepath: str
    page_count: int
    pages: List[Page] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate that page_count matches actual pages."""
        if len(self.pages) != self.page_count:
            raise ValueError(
                f"Page count mismatch: expected {self.page_count}, "
                f"got {len(self.pages)} pages"
            )

"""Segment data model representing a logical document section (header, items, footer)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .page import Page
    from .row import Row


@dataclass
class Segment:
    """Represents a logical document section (header, items, footer).
    
    Attributes:
        segment_type: Type of segment - "header", "items", or "footer"
        rows: List of Row objects in this segment
        y_min: Minimum Y-coordinate
        y_max: Maximum Y-coordinate
        page: Reference to parent Page
    """
    
    segment_type: str
    rows: List[Row]
    y_min: float
    y_max: float
    page: Page
    
    def __post_init__(self):
        """Validate segment type and coordinates."""
        if self.segment_type not in ["header", "items", "footer"]:
            raise ValueError(
                f"segment_type must be 'header', 'items', or 'footer', "
                f"got '{self.segment_type}'"
            )
        
        if self.y_min > self.y_max:
            raise ValueError(
                f"Segment y_min ({self.y_min}) must be <= y_max ({self.y_max})"
            )
        
        # Ensure segment has rows
        if not self.rows:
            raise ValueError(f"Segment '{self.segment_type}' must have at least one row")

"""Row data model representing a logical row with tokens grouped by Y-position."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .page import Page
    from .token import Token


@dataclass
class Row:
    """Represents a logical row with tokens grouped by Y-position.
    
    Important: tokens is KÄLLSANING (source of truth) for traceability.
    text is CONVENIENCE only - use tokens/bbox for exact positioning.
    
    Attributes:
        tokens: List of Token objects in this row (KÄLLSANING)
        y: Y-coordinate for the row (median or first token's Y)
        x_min: Minimum X-coordinate in row
        x_max: Maximum X-coordinate in row
        text: Concatenated text from all tokens (CONVENIENCE only)
        page: Reference to parent Page
    """
    
    tokens: List[Token]
    y: float
    x_min: float
    x_max: float
    text: str
    page: Page
    
    def __post_init__(self):
        """Validate that row has tokens."""
        if not self.tokens:
            raise ValueError("Row must have at least one token")
        
        # Ensure x_min <= x_max
        if self.x_min > self.x_max:
            raise ValueError(
                f"Row x_min ({self.x_min}) must be <= x_max ({self.x_max})"
            )

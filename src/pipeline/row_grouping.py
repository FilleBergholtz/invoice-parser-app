"""Token-to-row grouping based on Y-position alignment."""

from typing import List

from ..models.row import Row
from ..models.token import Token


def group_tokens_to_rows(tokens: List[Token]) -> List[Row]:
    """Group tokens into rows based on Y-position alignment.
    
    Args:
        tokens: List of Token objects to group
        
    Returns:
        List of Row objects, ordered top-to-bottom
        
    Algorithm:
    - Sort tokens by Y-position (top-to-bottom)
    - Group tokens with similar Y-coordinates (within tolerance)
    - For each group, create Row with tokens, y, x_min, x_max, text
    - Preserve reading order: rows top-to-bottom, tokens left-to-right within row
    """
    if not tokens:
        return []
    
    # Get page from first token for reference
    page = tokens[0].page
    
    # Calculate tolerance: 5 points or 2% of page height, whichever is smaller
    page_height = page.height if page else 842.0  # Default A4 height
    tolerance = min(5.0, page_height * 0.02)
    
    # Sort tokens by Y-position (top-to-bottom)
    sorted_tokens = sorted(tokens, key=lambda t: (t.y, t.x))
    
    rows = []
    current_row_tokens = []
    current_row_y = None
    
    for token in sorted_tokens:
        if current_row_y is None:
            # First token - start new row
            current_row_tokens = [token]
            current_row_y = token.y
        elif abs(token.y - current_row_y) <= tolerance:
            # Token is within tolerance of current row - add to row
            current_row_tokens.append(token)
        else:
            # Token is beyond tolerance - finalize current row and start new
            if current_row_tokens:
                rows.append(_create_row_from_tokens(current_row_tokens, page))
            current_row_tokens = [token]
            current_row_y = token.y
    
    # Finalize last row
    if current_row_tokens:
        rows.append(_create_row_from_tokens(current_row_tokens, page))
    
    return rows


def _create_row_from_tokens(tokens: List[Token], page) -> Row:
    """Create a Row object from a list of tokens.
    
    Args:
        tokens: List of Token objects (already grouped by Y-position)
        page: Page reference
        
    Returns:
        Row object with tokens, y, x_min, x_max, text
    """
    if not tokens:
        raise ValueError("Cannot create row from empty token list")
    
    # Sort tokens within row by X (left-to-right)
    sorted_tokens = sorted(tokens, key=lambda t: t.x)
    
    # Calculate row properties
    y_coords = [t.y for t in sorted_tokens]
    x_coords = [t.x for t in sorted_tokens]
    x_max_coords = [t.x + t.width for t in sorted_tokens]
    
    y = sum(y_coords) / len(y_coords)  # Average Y (could use median)
    x_min = min(x_coords)
    x_max = max(x_max_coords)
    
    # Concatenate text (CONVENIENCE only - tokens are source of truth)
    text_parts = [t.text for t in sorted_tokens]
    text = " ".join(text_parts)
    
    return Row(
        tokens=sorted_tokens,
        y=y,
        x_min=x_min,
        x_max=x_max,
        text=text,
        page=page
    )

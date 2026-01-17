"""Wrap detection for multi-line invoice items."""

from typing import List

from ..models.page import Page
from ..models.row import Row


def detect_wrapped_rows(
    product_row: Row,
    following_rows: List[Row],
    page: Page
) -> List[Row]:
    """Detect wrapped rows (continuation lines) for a product row.
    
    Args:
        product_row: Product row (InvoiceLine primary row)
        following_rows: List of rows following the product row
        page: Page reference for dimension calculation
        
    Returns:
        List of wrapped Row objects (continuation lines)
        
    Algorithm:
    1. Get description column start position from product_row
    2. Calculate X-position tolerance (±2% of page width)
    3. Iterate through following_rows:
       - Stop if next row contains amount (new product row)
       - Stop if X-start deviates > tolerance (different column)
       - Stop if max 3 wraps reached
    4. Return list of wrapped rows
    """
    if not following_rows:
        return []
    
    # Calculate X-position tolerance (±2% of page width)
    tolerance = 0.02 * page.width
    
    # Get description column start position (first token's X)
    description_start_x = _get_description_column_start(product_row)
    
    wraps = []
    
    for next_row in following_rows:
        # Stop condition 1: Next row contains amount (new product row)
        if _contains_amount(next_row):
            break
        
        # Stop condition 2: X-start deviates beyond tolerance
        next_row_start_x = next_row.x_min
        if abs(next_row_start_x - description_start_x) > tolerance:
            break
        
        # Stop condition 3: Max 3 wraps per line item
        if len(wraps) >= 3:
            break
        
        # Candidate is a wrap row
        wraps.append(next_row)
    
    return wraps


def consolidate_wrapped_description(
    product_row: Row,
    wrapped_rows: List[Row]
) -> str:
    """Consolidate description from product row and wrapped rows.
    
    Args:
        product_row: Primary product row
        wrapped_rows: List of wrapped rows (continuation lines)
        
    Returns:
        Consolidated description with space separator (Excel-friendly)
        
    Note:
        Uses space separator (not newline) for Excel readability.
    """
    # Extract description from product_row (tokens before amount)
    # For consolidation, we'll use row.text for simplicity
    # (In production, might want to extract only description tokens before amount)
    
    description_parts = [product_row.text]
    
    # Add wrap text
    for wrapped_row in wrapped_rows:
        description_parts.append(wrapped_row.text)
    
    # Join with space separator
    consolidated = " ".join(description_parts)
    
    return consolidated.strip()


def _get_description_column_start(row: Row) -> float:
    """Get X-position of description column start.
    
    Args:
        row: Row object
        
    Returns:
        X-coordinate of first token (description start)
    """
    if not row.tokens:
        return row.x_min  # Fallback to row x_min
    
    # First token's X position
    return row.tokens[0].x


def _contains_amount(row: Row) -> bool:
    """Check if row contains a numeric amount.
    
    Args:
        row: Row object to check
        
    Returns:
        True if row contains amount pattern, False otherwise
        
    Note:
        Reuses logic from invoice_line_parser.py for consistency.
    """
    import re
    
    # Amount pattern: numbers with decimal (Swedish format)
    amount_pattern = re.compile(r'[\d\s]+[.,]\d{2}')
    currency_symbols = ['kr', 'SEK', 'sek', ':-']
    
    for token in row.tokens:
        token_text = token.text.strip()
        
        if amount_pattern.search(token_text):
            # Check if it's a valid amount (not just random numbers)
            cleaned = token_text
            for sym in currency_symbols:
                cleaned = cleaned.replace(sym, '')
            cleaned = cleaned.replace(',', '.').replace(' ', '')
            
            try:
                amount = float(cleaned)
                if amount > 0:  # Valid amount
                    return True
            except ValueError:
                continue
    
    return False

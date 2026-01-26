"""Wrap detection for multi-line invoice items."""

import logging
import re
import statistics
from typing import List

from ..models.page import Page
from ..models.row import Row

logger = logging.getLogger(__name__)


def _matches_start_pattern(row: Row) -> bool:
    r"""Check if row matches new item start pattern.
    
    Args:
        row: Row object to check
        
    Returns:
        True if row starts with a pattern indicating a new item, False otherwise
        
    Patterns detected:
    - Article numbers: ^\d{5,} (5+ digits), ^\w{3,}\d+ (alphanumeric)
    - Dates: ^\d{4}-\d{2}-\d{2} (ISO), ^\d{2}/\d{2} (Swedish format)
    - Individnr: ^\d{6,8}-\d{4} (YYYYMMDD-XXXX format)
    - Account codes: ^\d{4}\s (4-digit followed by space)
    """
    if not row.text:
        return False
    
    text = row.text.strip()
    
    # Combined pattern for all start patterns
    # Article numbers, dates, individnr, account codes
    start_pattern = re.compile(
        r'^(?:'
        r'\d{5,}|'                    # Article number: 5+ digits
        r'\w{3,}\d+|'                 # Article number: alphanumeric (ABC123)
        r'\d{4}-\d{2}-\d{2}|'         # Date: ISO format (2026-01-26)
        r'\d{2}/\d{2}|'               # Date: Swedish format (26/01)
        r'\d{6,8}-\d{4}|'             # Individnr: YYYYMMDD-XXXX
        r'\d{4}\s'                    # Account code: 4 digits + space
        r')'
    )
    
    return bool(start_pattern.match(text))


def _calculate_adaptive_y_threshold(rows: List[Row]) -> float:
    """Calculate adaptive Y-distance threshold based on median line height.
    
    Args:
        rows: List of all table rows for analysis
        
    Returns:
        Y-distance threshold (1.5× median line height)
        
    Algorithm:
        1. Calculate Y-distance between consecutive rows
        2. Compute median line height (robust against outliers)
        3. Return 1.5× median (WCAG guideline for line spacing)
        4. Fallback to 15.0 if no line heights available (typical 10-12pt font)
    """
    if not rows or len(rows) < 2:
        return 15.0  # Fallback: ~10-12pt font × 1.5
    
    line_heights = []
    
    for i in range(len(rows) - 1):
        current_row = rows[i]
        next_row = rows[i + 1]
        
        # Calculate y_max for current row (y + token height)
        current_y_max = getattr(current_row, 'y_max', None)
        if current_y_max is None:
            current_y_max = current_row.y
            if current_row.tokens and hasattr(current_row.tokens[0], 'height'):
                current_y_max = current_row.y + current_row.tokens[0].height
            else:
                current_y_max = current_row.y + 12  # Fallback: typical font height
        
        # Get next row's y_min or fallback to y
        next_y_min = getattr(next_row, 'y_min', next_row.y)
        
        # Y-distance between consecutive rows (gap between rows)
        y_distance = next_y_min - current_y_max
        
        if y_distance > 0:  # Skip overlapping rows
            line_heights.append(y_distance)
    
    if not line_heights:
        return 15.0  # Fallback
    
    # Median is more robust than mean (avoids skew from section breaks)
    median_height = statistics.median(line_heights)
    
    # Threshold: 1.5× median line height
    # (Based on WCAG 2.1 line spacing guidelines: 1.5× font size)
    return median_height * 1.5


def detect_wrapped_rows(
    product_row: Row,
    following_rows: List[Row],
    page: Page,
    all_rows: List[Row] = None
) -> List[Row]:
    """Detect wrapped rows (continuation lines) for a product row.
    
    Args:
        product_row: Product row (InvoiceLine primary row)
        following_rows: List of rows following the product row
        page: Page reference for dimension calculation
        all_rows: All table rows for adaptive Y-threshold calculation (optional)
        
    Returns:
        List of wrapped Row objects (continuation lines)
        
    Algorithm:
    1. Calculate adaptive Y-distance threshold (1.5× median line height)
    2. Get description column start position from product_row
    3. Calculate X-position tolerance (±2% of page width)
    4. Iterate through following_rows:
       - Stop if Y-distance > threshold (too far apart)
       - Stop if next row contains amount (new product row)
       - Stop if X-start deviates > tolerance (different column)
    5. Return list of wrapped rows
    """
    if not following_rows:
        return []
    
    # Calculate adaptive Y-distance threshold
    if all_rows is None:
        # Fallback: use product_row + following_rows for threshold calculation
        all_rows = [product_row] + following_rows
    y_threshold = _calculate_adaptive_y_threshold(all_rows)
    
    # Calculate X-position tolerance (±2% of page width for base alignment)
    base_tolerance = 0.02 * page.width
    
    # Right-indent allowance (+5% of page width for indented sub-items)
    right_indent_allowance = 0.05 * page.width
    
    # Get description column start position (first token's X)
    description_start_x = _get_description_column_start(product_row)
    
    wraps = []
    prev_row = product_row
    
    for next_row in following_rows:
        # Stop condition 1: Start-pattern check (override spatial proximity)
        # If row matches article number, date, individnr, or account code pattern,
        # it's a new item regardless of spatial proximity
        if _matches_start_pattern(next_row):
            break  # New item starts here
        
        # Stop condition 2: Y-distance check (adaptive threshold)
        # Calculate y_max for prev_row (handle cases where y_min/y_max not set)
        prev_y_max = getattr(prev_row, 'y_max', None)
        if prev_y_max is None:
            prev_y_max = prev_row.y
            if prev_row.tokens and hasattr(prev_row.tokens[0], 'height'):
                prev_y_max = prev_row.y + prev_row.tokens[0].height
            else:
                prev_y_max = prev_row.y + 12  # Fallback: typical font height
        
        next_y_min = getattr(next_row, 'y_min', next_row.y)
        
        y_distance = next_y_min - prev_y_max
        if y_distance > y_threshold:
            break  # Too far apart = not a continuation
        
        # Stop condition 3: Next row contains amount (new product row)
        if _contains_amount(next_row):
            break
        
        # Stop condition 4: X-alignment check (two-tier tolerance)
        next_row_start_x = getattr(next_row, 'x_min', next_row.tokens[0].x if next_row.tokens else 0)
        delta_x = next_row_start_x - description_start_x
        
        # Allow:
        # 1. Base tolerance: ±2% page width (aligned)
        # 2. Right-indent allowance: +5% page width (indented sub-items, bullet points)
        is_aligned = (abs(delta_x) <= base_tolerance or 
                      (delta_x > 0 and delta_x <= right_indent_allowance))
        
        if not is_aligned:
            break  # Too far left or too far right
        
        # Soft limit: Warn if unusually long wrapped item (anomaly detection)
        if len(wraps) >= 10:
            logger.warning(
                f"Unusually long wrapped item ({len(wraps)} lines) on page {page.page_number}. "
                "This may indicate footer proximity or detection error."
            )
            # Continue collecting wraps - no hard limit
        
        # Candidate is a wrap row
        wraps.append(next_row)
        prev_row = next_row
    
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

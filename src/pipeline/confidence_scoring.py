"""Multi-factor confidence scoring algorithms for field extraction."""

import re
from typing import List, Optional

from ..models.invoice_line import InvoiceLine
from ..models.page import Page
from ..models.row import Row
from ..models.token import Token


def score_total_amount_candidate(
    candidate: float,
    row: Row,
    page: Page,
    line_items: List[InvoiceLine],
    footer_rows: List[Row]
) -> float:
    """Score total amount candidate using multi-factor weighted scoring.
    
    Args:
        candidate: Candidate total amount value
        row: Row containing the candidate
        page: Page reference for position calculation
        line_items: List of InvoiceLine objects for mathematical validation
        footer_rows: List of rows in footer segment for relative size comparison
        
    Returns:
        Confidence score (0.0-1.0)
        
    Score components:
    - Keyword match (0.35 weight): "Att betala" strongest, "Total/Totalt" next
    - Position (0.20 weight): Footer zone + right-aligned
    - Mathematical validation (0.35 weight): If subtotal + VAT + rounding ≈ total → full score
    - Relative size (0.10 weight): Total should be largest amount in summation rows
    """
    score = 0.0
    
    # Keyword match (0.35 weight)
    keyword_scores = {
        "att betala": 0.35,
        "totalt": 0.30,
        "total": 0.30,
        "summa att betala": 0.30
    }
    row_lower = row.text.lower()
    for keyword, kw_score in keyword_scores.items():
        if keyword in row_lower:
            score += kw_score
            break
    
    # Position (0.20 weight)
    if row.y > 0.8 * page.height:
        score += 0.20
    
    # Mathematical validation (0.35 weight)
    if validate_total_against_line_items(candidate, line_items, tolerance=1.0):
        score += 0.35
    elif line_items:
        score += 0.15  # Partial: has line items but doesn't validate
    
    # Relative size (0.10 weight)
    if _is_largest_in_footer(candidate, footer_rows):
        score += 0.10
    
    return min(score, 1.0)  # Normalize to 0.0-1.0


def validate_total_against_line_items(
    total: float,
    line_items: List[InvoiceLine],
    tolerance: float = 1.0
) -> bool:
    """Validate total amount against sum of line item totals.
    
    Args:
        total: Extracted total amount
        line_items: List of InvoiceLine objects
        tolerance: Tolerance in SEK (default 1.0 for rounding/shipping/discounts)
        
    Returns:
        True if total matches line items sum within tolerance, False otherwise
        
    Formula: lines_sum = SUM(all line item totals), diff = |total - lines_sum|
    Validation passes if diff <= tolerance.
    """
    if not line_items:
        return False  # Cannot validate without line items
    
    lines_sum = sum(line.total_amount for line in line_items)
    diff = abs(total - lines_sum)
    return diff <= tolerance


def _is_largest_in_footer(candidate: float, footer_rows: List[Row]) -> bool:
    """Check if candidate is largest amount in footer rows.
    
    Args:
        candidate: Candidate total amount
        footer_rows: List of rows in footer segment
        
    Returns:
        True if candidate is largest numeric value in footer rows
    """
    # Extract all numeric amounts from footer rows
    amounts = []
    amount_pattern = re.compile(r'[\d\s]+[.,]\d{2}')
    
    for footer_row in footer_rows:
        for token in footer_row.tokens:
            token_text = token.text.strip()
            if amount_pattern.search(token_text):
                # Extract numeric value
                cleaned = token_text.replace('kr', '').replace('SEK', '').replace('sek', '').replace(':-', '')
                cleaned = cleaned.replace(',', '.').replace(' ', '')
                try:
                    amount = float(cleaned)
                    amounts.append(amount)
                except ValueError:
                    continue
    
    if not amounts:
        return True  # No other amounts to compare, assume largest
    
    return candidate >= max(amounts)


def score_invoice_number_candidate(
    candidate: str,
    row: Row,
    page: Page,
    all_rows: List[Row]
) -> float:
    """Score invoice number candidate using multi-factor weighted scoring.
    
    Args:
        candidate: Candidate invoice number string
        row: Row containing the candidate
        page: Page reference for position calculation
        all_rows: All rows in document for uniqueness checking
        
    Returns:
        Confidence score (0.0-1.0)
        
    Score components:
    - Position (0.30 weight): Header zone (y < 0.3 * page_height)
    - Keyword proximity (0.35 weight): "fakturanummer/invoice number/nr/no" on same row or adjacent
    - Format validation (0.20 weight): Alphanumeric, length 3-25, not date/amount/org number
    - Uniqueness (0.10 weight): Appears once in document
    - OCR/Token confidence (0.05 weight): Average confidence of tokens in candidate area
    """
    score = 0.0
    
    # Position scoring (0.30 weight)
    if row.y < 0.3 * page.height:
        score += 0.30
    
    # Keyword proximity (0.35 weight)
    keyword_pattern = r"(?:fakturanummer|invoice\s*number|no\.|nr|number)"
    if re.search(keyword_pattern, row.text, re.IGNORECASE):
        score += 0.35
    elif _has_keyword_in_adjacent_row(row, all_rows, keyword_pattern):
        score += 0.25  # Slightly lower for adjacent
    
    # Format validation (0.20 weight)
    if _validate_invoice_number_format(candidate):
        score += 0.20
    
    # Uniqueness (0.10 weight)
    if _appears_once_in_document(candidate, all_rows):
        score += 0.10
    
    # OCR confidence (0.05 weight)
    avg_conf = _average_token_confidence(row.tokens)
    score += 0.05 * avg_conf
    
    return min(score, 1.0)  # Normalize to 0.0-1.0


def _validate_invoice_number_format(candidate: str) -> bool:
    """Validate invoice number format.
    
    Args:
        candidate: Candidate invoice number string
        
    Returns:
        True if format is valid (alphanumeric, length 3-25, not date/amount/org number)
    """
    if not candidate:
        return False
    
    # Length check (3-25 characters)
    if not (3 <= len(candidate) <= 25):
        return False
    
    # Alphanumeric with dashes (common format: INV-2024-001)
    if not re.match(r'^[A-Z0-9\-]+$', candidate, re.IGNORECASE):
        return False
    
    # Not just digits (likely not org number or amount)
    if candidate.isdigit() and len(candidate) > 6:
        return False
    
    # Not a date pattern (YYYY-MM-DD, DD/MM/YYYY, etc.)
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}',  # DD/MM/YYYY variants
    ]
    for pattern in date_patterns:
        if re.match(pattern, candidate):
            return False
    
    return True


def _has_keyword_in_adjacent_row(
    row: Row,
    all_rows: List[Row],
    keyword_pattern: str
) -> bool:
    """Check if keyword exists in row above current row.
    
    Args:
        row: Current row
        all_rows: All rows in document
        keyword_pattern: Regex pattern for keywords
        
    Returns:
        True if keyword found in row directly above
    """
    # Find row index
    try:
        row_index = all_rows.index(row)
        if row_index > 0:
            # Check row above
            row_above = all_rows[row_index - 1]
            if re.search(keyword_pattern, row_above.text, re.IGNORECASE):
                return True
    except ValueError:
        pass  # Row not in list
    
    return False


def _appears_once_in_document(candidate: str, all_rows: List[Row]) -> bool:
    """Check if candidate appears only once in document.
    
    Args:
        candidate: Candidate invoice number string
        all_rows: All rows in document
        
    Returns:
        True if candidate appears exactly once (or is clearly most likely instance)
    """
    count = 0
    for row in all_rows:
        if candidate in row.text:
            count += 1
            if count > 1:
                return False  # Appears multiple times
    
    return count == 1


def _average_token_confidence(tokens: List[Token]) -> float:
    """Calculate average confidence from tokens.
    
    Args:
        tokens: List of Token objects
        
    Returns:
        Average confidence (0.0-1.0), defaults to 1.0 if no confidence available
    """
    if not tokens:
        return 1.0  # Default high confidence if no tokens
    
    # Token model doesn't have confidence field yet (OCR tokens would)
    # For now, return 1.0 (assume high confidence for pdfplumber tokens)
    # TODO: Add confidence to Token model when OCR integration complete
    return 1.0

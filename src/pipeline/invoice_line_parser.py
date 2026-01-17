"""Line item extraction from items segment using layout-driven approach."""

import re
from typing import List, Optional, Tuple

from ..models.invoice_line import InvoiceLine
from ..models.row import Row
from ..models.segment import Segment
from ..pipeline.wrap_detection import detect_wrapped_rows, consolidate_wrapped_description


def _is_footer_row(row: Row) -> bool:
    """Check if a row is a footer row (summary/total row) based on content.
    
    Args:
        row: Row object to check
        
    Returns:
        True if row appears to be a footer/summary row, False otherwise
        
    Footer rows typically contain:
    - "summa", "total", "att betala", "moms", "exkl", "inkl"
    - Summary labels that indicate totals rather than product rows
    - Edge cases: Short descriptions with large amounts that match invoice totals
    """
    if not row.text:
        return False
    
    text_lower = row.text.lower()
    text_stripped = row.text.strip()
    
    # Footer keywords (Swedish + English)
    footer_keywords = [
        'summa',
        'total',
        'totalt',
        'att betala',
        'attbetala',
        'moms',
        'momspliktigt',
        'exkl',
        'inkl',
        'exklusive',
        'inklusive',
        'exkl. moms',
        'inkl. moms',
        'totaltexkl',
        'totaltexkl.',
        'total inkl',
        'total inkl.',
        'forskott',
        'forskottsbetalning',
        'godkänd',
        'godkänd för',
        'f-skatt',
        'fakturafrågor',
        'fakturafrågor skickas',
        'att betala sek',
        'attbetala sek',
        'förf datum',
        'förf. datum',
        'förfallodatum',
        'förfallo datum',
        # Additional keywords for edge cases
        'lista',
        'spec',
        'bifogad',
        'bifogadspec',
        'hyraställning',
        'hyraställningen'
    ]
    
    # Check if row text contains footer keywords
    for keyword in footer_keywords:
        if keyword in text_lower:
            return True
    
    # Heuristic 1: Extract amount to check if it's suspiciously large
    # This helps identify edge cases where description is short but amount is large
    amount_result = _extract_amount_from_row_text(row)
    if amount_result:
        total_amount, _, amount_token_idx = amount_result
        
        # Extract description (text before amount)
        description_tokens = row.tokens[:amount_token_idx] if amount_token_idx else row.tokens
        description = " ".join(t.text for t in description_tokens).strip()
        description_lower = description.lower()
        
        # Heuristic 2: Short description (< 50 chars) with large amount (> 5000 SEK)
        # and description starts with numbers or contains only numbers + short text
        if len(description) < 50 and total_amount > 5000:
            # Check if description starts with numbers (e.g., "4040", "12,1")
            if re.match(r'^\d+[.,]?\d*\s+', description) or re.match(r'^\d+\s+', description):
                # Check if description is mostly numbers and short words
                words = description.split()
                if len(words) <= 5:  # Very short description
                    # Check if it contains suspicious patterns that indicate footer rows
                    # These patterns are more specific to avoid false positives
                    suspicious_patterns = [
                        r'^\d+\s+[a-zåäö]{1,15}\s+(enl|lista)',  # "4040 Maskiner enl Lista"
                        r'lista\s+\d+',  # "Maskiner enl Lista 5"
                        r'(hyraställning|hyraställningen).*bifogad.*spec',  # "Hyraställningenl.bifogadspec"
                        r'^\d+\s+[a-zåäö]{1,10}\s*$',  # Very short: "4040 Maskiner" (no more words)
                    ]
                    for pattern in suspicious_patterns:
                        if re.search(pattern, description_lower):
                            return True
                    
                    # Additional check: If description is extremely short (< 25 chars) 
                    # and starts with numbers, and amount is very large (> 10000)
                    if len(description) < 25 and total_amount > 10000:
                        # Check if it's mostly numbers with minimal text
                        non_numeric = re.sub(r'[\d\s,.-]', '', description)
                        if len(non_numeric) < 10:  # Very few non-numeric characters
                            return True
        
        # Heuristic 3: Description contains only numbers and very short text
        # and amount is large (likely a total row)
        if len(description) < 30 and total_amount > 10000:
            # Check if description is mostly numbers
            non_numeric_chars = re.sub(r'[\d\s,.-]', '', description)
            if len(non_numeric_chars) < 15:  # Very few non-numeric characters
                return True
    
    return False


def _extract_amount_from_row_text(row: Row) -> Optional[Tuple[float, Optional[float], int]]:
    """Extract total amount and discount from row.text with support for thousand separators.
    
    Args:
        row: Row object with text property
        
    Returns:
        Tuple of (total_amount, discount, amount_token_idx) if amount found, None otherwise
        - total_amount: Extracted numeric amount (must be positive)
        - discount: Optional discount amount (if negative amount found before total_amount)
        - amount_token_idx: Index of token containing or closest to total_amount
        
    This function extracts amounts from row.text instead of token-by-token,
    which better handles thousand separators (spaces) that may span multiple tokens.
    Also detects negative amounts (discounts) before the total amount.
    
    Examples: 
    - "1 072,60" → (1072.60, None, idx)
    - "440,00 -88,00 1 672,00" → (1672.00, 88.00, idx)
    - "-2 007,28 10 000,00" → (10000.00, 2007.28, idx)
    """
    currency_symbols = ['kr', 'SEK', 'sek', ':-']
    
    # Pattern for amounts (positive or negative) with thousand separators (spaces)
    # Matches: "123,45", "-123,45", "1 234,56", "-1 234,56", "-2 007,28", etc.
    # Also handles period as decimal: "123.45", "-123.45"
    # Pattern: optional minus sign, then digits with optional thousand separators, then decimal
    amount_pattern = re.compile(r'-?\d{1,3}(?:\s+\d{3})*(?:[.,]\d{2})|-?\d+(?:[.,]\d{2})')
    
    # Find all amount matches in row.text
    matches = list(amount_pattern.finditer(row.text))
    if not matches:
        return None
    
    # Extract all amounts with their positions and values
    amounts = []  # List of (value, is_negative, match_start, match_end)
    
    for match in matches:
        amount_text = match.group(0)
        is_negative = amount_text.startswith('-')
        
        # Clean and convert to float
        cleaned = amount_text
        for sym in currency_symbols:
            cleaned = cleaned.replace(sym, '')
        cleaned = cleaned.replace(' ', '').replace(',', '.').lstrip('-')
        
        try:
            value = float(cleaned)
            if value > 0:  # Only process positive values (we handle sign separately)
                amounts.append((value, is_negative, match.start(), match.end()))
        except ValueError:
            continue
    
    if not amounts:
        return None
    
    # Find rightmost positive amount (this is total_amount)
    total_amount = None
    total_amount_pos = None
    total_amount_match = None
    
    for value, is_negative, start_pos, end_pos in amounts:
        if not is_negative:
            # This is a positive amount - track rightmost one
            if total_amount_pos is None or start_pos > total_amount_pos:
                total_amount = value
                total_amount_pos = start_pos
                total_amount_match = (start_pos, end_pos)
    
    if total_amount is None or total_amount <= 0:
        return None
    
    # Find negative amounts before total_amount (this is discount)
    # Use the rightmost negative amount before total_amount as discount
    discount = None
    discount_pos = None
    for value, is_negative, start_pos, end_pos in amounts:
        if is_negative and start_pos < total_amount_pos:
            # This is a negative amount before total_amount - use rightmost one as discount
            if discount_pos is None or start_pos > discount_pos:
                discount = value
                discount_pos = start_pos
    
    # Map character position back to token index
    # Find which token contains the total amount (or is closest)
    amount_start_pos, amount_end_pos = total_amount_match
    
    # Build character position mapping for tokens (reconstruct row.text)
    # row.text is created as " ".join(token.text for token in sorted_tokens)
    # So we need to map character positions in row.text back to token indices
    char_pos = 0
    token_positions = []  # List of (token_idx, start_pos, end_pos)
    
    sorted_tokens = sorted(row.tokens, key=lambda t: t.x)  # Same order as row.text
    
    for i, token in enumerate(sorted_tokens):
        token_start = char_pos
        token_end = char_pos + len(token.text)
        # Find original token index in row.tokens
        original_idx = row.tokens.index(token)
        token_positions.append((original_idx, token_start, token_end))
        # Add space between tokens (as in row.text: " ".join(...))
        char_pos = token_end + 1
    
    # Find token that contains or is closest to the amount
    amount_token_idx = None
    for token_idx, start_pos, end_pos in token_positions:
        # Check if amount overlaps with this token
        if not (amount_end_pos < start_pos or amount_start_pos > end_pos):
            amount_token_idx = token_idx
            break
    
    # If no overlap, find closest token (shouldn't happen, but fallback)
    if amount_token_idx is None:
        # Find token with minimum distance to amount center
        amount_center = (amount_start_pos + amount_end_pos) / 2
        min_dist = float('inf')
        for token_idx, start_pos, end_pos in token_positions:
            token_center = (start_pos + end_pos) / 2
            dist = abs(amount_center - token_center)
            if dist < min_dist:
                min_dist = dist
                amount_token_idx = token_idx
    
    return (total_amount, discount, amount_token_idx)


def extract_invoice_lines(items_segment: Segment) -> List[InvoiceLine]:
    """Extract line items from items segment using layout-driven approach.
    
    Args:
        items_segment: Segment object with segment_type='items'
        
    Returns:
        List of InvoiceLine objects
        
    Algorithm (layout-driven):
    - Iterate through Segment.rows
    - For each row, check if it contains a numeric amount (total_amount)
    - Rule: "rad med belopp = produktrad" - if row contains amount, it's a product row
    - Extract fields from row tokens using spatial information
    """
    if items_segment.segment_type != "items":
        raise ValueError(
            f"Segment must be of type 'items', got '{items_segment.segment_type}'"
        )
    
    invoice_lines = []
    line_number = 1
    processed_row_indices = set()  # Track rows already processed as wraps
    
    for row_index, row in enumerate(items_segment.rows):
        # Skip rows already processed as wraps
        if row_index in processed_row_indices:
            continue
        
        # Skip footer rows (summary/total rows that shouldn't be product rows)
        if _is_footer_row(row):
            continue
        
        # Try to extract line item from row
        invoice_line = _extract_line_from_row(row, items_segment, line_number)
        
        if invoice_line:
            # Detect wrapped rows
            following_rows = items_segment.rows[row_index + 1:]
            wrapped_rows = detect_wrapped_rows(row, following_rows, items_segment.page)
            
            # Mark wrapped rows as processed
            for wrapped_row in wrapped_rows:
                wrapped_index = items_segment.rows.index(wrapped_row)
                processed_row_indices.add(wrapped_index)
            
            # Update InvoiceLine with wrapped rows
            if wrapped_rows:
                # Add wrapped rows to InvoiceLine.rows (KÄLLSANING for traceability)
                invoice_line.rows.extend(wrapped_rows)
                
                # Consolidate description
                invoice_line.description = consolidate_wrapped_description(row, wrapped_rows)
            
            invoice_lines.append(invoice_line)
            line_number += 1
    
    return invoice_lines


def _extract_line_from_row(
    row: Row,
    segment: Segment,
    line_number: int
) -> Optional[InvoiceLine]:
    """Extract InvoiceLine from a single row.
    
    Args:
        row: Row object to analyze
        segment: Items segment reference
        line_number: Line number for ordering
        
    Returns:
        InvoiceLine if row contains amount (product row), None otherwise
    """
    # Rule: "rad med belopp = produktrad"
    # Check if row contains a numeric amount
    
    # Extract amount and discount from row.text (supports thousand separators across tokens)
    result = _extract_amount_from_row_text(row)
    if result is None:
        return None
    
    total_amount, discount, amount_token_idx = result
    
    # Extract description: leftmost text before amount column
    description_tokens = row.tokens[:amount_token_idx] if amount_token_idx else row.tokens
    description = " ".join(t.text for t in description_tokens).strip()
    
    # Extract quantity and unit_price: look for numeric columns before amount
    # Typically: description | quantity | unit | unit_price | total_amount
    quantity = None
    unit = None
    unit_price = None
    
    # Look for numeric tokens before amount (potential quantity or unit_price)
    numeric_tokens_before_amount = []
    for i, token in enumerate(row.tokens):
        if i >= amount_token_idx:
            break
        
        token_text = token.text.strip()
        # Check if token looks like a number
        if re.match(r'^\d+([.,]\d+)?$', token_text.replace(' ', '')):
            # Convert to float
            cleaned = token_text.replace(',', '.').replace(' ', '')
            try:
                numeric_value = float(cleaned)
                numeric_tokens_before_amount.append((i, numeric_value, token))
            except ValueError:
                pass
    
    # Heuristic: rightmost numeric before amount is likely unit_price
    # Leftmost numeric is likely quantity
    if len(numeric_tokens_before_amount) >= 2:
        # Multiple numerics: assume quantity is first, unit_price is last
        _, quantity, _ = numeric_tokens_before_amount[0]
        _, unit_price, _ = numeric_tokens_before_amount[-1]
    elif len(numeric_tokens_before_amount) == 1:
        # Single numeric: could be quantity or unit_price
        # Prefer quantity if it's a small integer, otherwise unit_price
        idx, value, token = numeric_tokens_before_amount[0]
        if value < 100 and value == int(value):
            quantity = value
        else:
            unit_price = value
    
    # Extract unit: look for common unit strings near quantity
    if quantity is not None:
        # Look for unit tokens after quantity token
        for token in row.tokens:
            token_text = token.text.strip().lower()
            if token_text in ['st', 'kg', 'h', 'm²', 'm2', 'tim', 'timmar', 'pcs', 'pkt']:
                unit = token_text
                break
    
    # Create InvoiceLine
    return InvoiceLine(
        rows=[row],  # In Phase 1, typically one row per line item (wraps come in Phase 2)
        description=description or "Unknown",
        quantity=quantity,
        unit=unit,
        unit_price=unit_price,
        discount=discount,  # Extracted from negative amounts before total_amount
        total_amount=total_amount,
        vat_rate=None,  # Not extracted in Phase 1
        line_number=line_number,
        segment=segment
    )

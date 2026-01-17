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
    # IMPORTANT: For rows with units like EA, LTR, månad, DAY, XPA, use unit position as anchor
    quantity = None
    unit = None
    unit_price = None
    
    # Extended unit list including DAY, dagar, EA, LTR, Liter, månad, XPA
    unit_keywords = [
        'st', 'kg', 'h', 'm²', 'm2', 'tim', 'timmar', 'pcs', 'pkt',
        'day', 'days', 'dagar', 'ea', 'ltr', 'liter', 'liters', 'månad', 'månader',
        'xpa', 'pkt', 'paket', 'box', 'burk', 'flaska', 'flaskor'
    ]
    
    # First, try to find unit token - use it as anchor for quantity/unit_price extraction
    unit_token_idx = None
    for i, token in enumerate(row.tokens):
        if i >= amount_token_idx:
            break
        token_text = token.text.strip().lower()
        if token_text in unit_keywords:
            unit = token_text
            unit_token_idx = i
            break
    
    # Identify potential article numbers in description
    article_number_pattern = re.compile(r'^(\d{1,2}\s+\d{5,8}|\d{6,12})\s+')
    has_article_number = bool(article_number_pattern.match(description))
    first_number_match = re.match(r'^(\d+(?:\s+\d+)*)', description)
    first_number_str = first_number_match.group(1) if first_number_match else ""
    first_number_cleaned = first_number_str.replace(' ', '')
    first_number_value = None
    if first_number_cleaned and first_number_cleaned.isdigit():
        try:
            first_number_value = float(first_number_cleaned)
        except ValueError:
            pass
    
    # Strategy 1: If unit found, use it as anchor
    # Format: ... quantity unit unit_price ... total_amount
    # Example: "2 5220 ELMÄTARE63A 3 EA 13,00" → quantity=3, unit=EA, unit_price=13.00
    # Example: "27 7615 COMBISAFESTÖLBALKSTVING 2 108 EA 1,95" → quantity=2108, unit=EA, unit_price=1.95
    if unit_token_idx is not None:
        # First, try to extract quantity from text (handles thousand separators across tokens)
        # Get text before unit token
        before_unit_tokens = row.tokens[:unit_token_idx]
        before_unit_text = " ".join(t.text for t in before_unit_tokens)
        
        # Pattern for quantity with thousand separators: "2 108", "1 260", "4 708", "1 085"
        # Look for pattern: 1-3 digits, then space, then 3 digits (thousand separator format)
        # This pattern should be right before the unit
        # Try to find the last occurrence of this pattern before unit
        thousand_sep_pattern = re.compile(r'\b(\d{1,3}(?:\s+\d{3})+)\b')
        matches = list(thousand_sep_pattern.finditer(before_unit_text))
        
        if matches:
            # Take the last match (closest to unit) that's not an article number
            # Prioritize matches closer to the unit (higher position in text)
            for match in reversed(matches):
                quantity_text = match.group(1)
                cleaned = quantity_text.replace(' ', '')
                try:
                    numeric_value = float(cleaned)
                    match_start = match.start()
                    match_end = match.end()
                    
                    # Calculate distance from unit (higher = closer to unit)
                    distance_from_unit = len(before_unit_text) - match_end
                    
                    # Check if this looks like an article number
                    # Article numbers are typically at the start (first 30% of text)
                    # and are often part of larger numbers like "27 7615" (277615)
                    is_likely_article_number = False
                    if match_start < len(before_unit_text) * 0.3:
                        # At start - could be article number
                        # If it's part of a larger number pattern (like "27 7615"), skip it
                        # Check if there are more digits right after this match
                        if match_end < len(before_unit_text):
                            next_char = before_unit_text[match_end:match_end+1]
                            if next_char.isdigit():
                                # More digits after, likely part of article number
                                is_likely_article_number = True
                        # Also skip if numeric value is very large (likely article number)
                        if numeric_value >= 100000:
                            is_likely_article_number = True
                    
                    if not is_likely_article_number:
                        # This looks like quantity
                        # Prefer matches closer to unit (within last 50% of text)
                        if distance_from_unit < len(before_unit_text) * 0.5 or numeric_value < 10000:
                            if 1 <= numeric_value <= 100000:  # Reasonable range for quantity
                                quantity = numeric_value
                                break
                except ValueError:
                    pass
        
        # If no thousand-separator quantity found, look for single numeric token
        if quantity is None:
            for i in range(unit_token_idx - 1, -1, -1):  # Go backwards from unit
                if i >= amount_token_idx:
                    break
                token = row.tokens[i]
                token_text = token.text.strip()
                
                # Check if token is a pure number
                if re.match(r'^\d+([.,]\d+)?$', token_text.replace(' ', '')):
                    cleaned = token_text.replace(',', '.').replace(' ', '')
                    try:
                        numeric_value = float(cleaned)
                        
                        # Skip if it looks like article number or line number
                        is_article_or_line_number = False
                        if i < 3:  # First few tokens
                            if first_number_value and abs(numeric_value - first_number_value) < 0.01:
                                is_article_or_line_number = True
                            elif numeric_value >= 10000 or len(str(int(numeric_value))) >= 5:
                                is_article_or_line_number = True
                            elif i == 0 and numeric_value < 100 and numeric_value == int(numeric_value):
                                if len(row.tokens) > 1 and i + 1 < len(row.tokens):
                                    next_token = row.tokens[i + 1].text.strip()
                                    if re.match(r'^\d+', next_token):
                                        is_article_or_line_number = True
                        
                        if not is_article_or_line_number:
                            # This is likely quantity (should be small number, < 1000 typically)
                            if numeric_value < 1000 and numeric_value == int(numeric_value):
                                quantity = numeric_value
                                break
                    except ValueError:
                        pass
        
        # Look for numeric token AFTER unit but BEFORE amount (this is unit_price)
        # Handle amounts with thousand separators (e.g., "1 034,00")
        # Extract text between unit and amount, then find amount pattern
        if unit_token_idx + 1 < amount_token_idx:
            # Get text between unit and amount
            unit_to_amount_tokens = row.tokens[unit_token_idx + 1:amount_token_idx]
            unit_to_amount_text = " ".join(t.text for t in unit_to_amount_tokens)
            
            # Pattern for amounts with thousand separators (spaces)
            # Matches: "123,45", "1 234,56", "1 034,00", etc.
            amount_pattern = re.compile(r'\d{1,3}(?:\s+\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2})')
            match = amount_pattern.search(unit_to_amount_text)
            
            if match:
                amount_text = match.group(0)
                cleaned = amount_text.replace(' ', '').replace(',', '.')
                try:
                    numeric_value = float(cleaned)
                    # Unit price should be reasonable (not too small, not too large)
                    if 0.01 <= numeric_value <= 1000000:  # Reasonable range
                        unit_price = numeric_value
                except ValueError:
                    pass
            else:
                # Fallback: look for single numeric token
                for i in range(unit_token_idx + 1, amount_token_idx):
                    token = row.tokens[i]
                    token_text = token.text.strip()
                    if re.match(r'^\d+([.,]\d+)?$', token_text.replace(' ', '')):
                        cleaned = token_text.replace(',', '.').replace(' ', '')
                        try:
                            numeric_value = float(cleaned)
                            if 0.01 <= numeric_value <= 1000000:
                                unit_price = numeric_value
                                break
                        except ValueError:
                            pass
    
    # Strategy 2: If no unit found, use old heuristic (fallback)
    if unit_token_idx is None:
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
                    
                    # Skip if this looks like an article number
                    is_article_number = False
                    if i < 2:  # First tokens
                        if numeric_value >= 100000:  # 6+ digits
                            is_article_number = True
                        elif first_number_value and abs(numeric_value - first_number_value) < 0.01:
                            is_article_number = True
                        elif len(str(int(numeric_value))) >= 6:  # 6+ digits
                            is_article_number = True
                    
                    if is_article_number:
                        continue  # Skip article number
                        
                    numeric_tokens_before_amount.append((i, numeric_value, token))
                except ValueError:
                    pass
        
        # Heuristic: rightmost numeric before amount is likely unit_price
        # Leftmost numeric (after article number) is likely quantity
        if len(numeric_tokens_before_amount) >= 2:
            start_idx = 0
            if has_article_number and len(numeric_tokens_before_amount) > 2:
                start_idx = 1  # Skip article number
            _, quantity, _ = numeric_tokens_before_amount[start_idx]
            _, unit_price, _ = numeric_tokens_before_amount[-1]
        elif len(numeric_tokens_before_amount) == 1:
            idx, value, token = numeric_tokens_before_amount[0]
            if has_article_number and idx < 2 and value >= 100000:
                pass  # Skip article number
            elif value < 100 and value == int(value):
                quantity = value
            else:
                unit_price = value
        
        # Look for unit tokens after quantity token (fallback)
        if quantity is not None:
            for token in row.tokens:
                token_text = token.text.strip().lower()
                if token_text in unit_keywords:
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

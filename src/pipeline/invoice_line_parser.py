"""Line item extraction from items segment using layout-driven approach."""

import re
from typing import List, Optional

from ..models.invoice_line import InvoiceLine
from ..models.row import Row
from ..models.segment import Segment


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
    
    for row in items_segment.rows:
        # Try to extract line item from row
        invoice_line = _extract_line_from_row(row, items_segment, line_number)
        
        if invoice_line:
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
    
    # Find numeric tokens (potential amounts)
    # Look for patterns: numbers with decimal, currency symbols, etc.
    amount_pattern = re.compile(r'[\d\s]+[.,]\d{2}')  # Matches "123,45" or "123.45"
    currency_symbols = ['kr', 'SEK', 'sek', ':-']
    
    total_amount = None
    amount_token_idx = None
    
    # Search from right to left for amount (usually rightmost numeric)
    for i in range(len(row.tokens) - 1, -1, -1):
        token = row.tokens[i]
        token_text = token.text.strip()
        
        # Check if token text matches amount pattern
        if amount_pattern.search(token_text):
            # Extract numeric value
            # Remove currency symbols, spaces, convert comma to dot
            cleaned = token_text
            for sym in currency_symbols:
                cleaned = cleaned.replace(sym, '')
            cleaned = cleaned.replace(',', '.').replace(' ', '')
            
            try:
                total_amount = float(cleaned)
                amount_token_idx = i
                break
            except ValueError:
                continue
    
    # If no amount found, this is not a product row
    if total_amount is None or total_amount <= 0:
        return None
    
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
        discount=None,  # Rare in Phase 1
        total_amount=total_amount,
        vat_rate=None,  # Not extracted in Phase 1
        line_number=line_number,
        segment=segment
    )

"""Footer extraction for total amount with confidence scoring."""

import re
from typing import List, Optional

from ..models.invoice_header import InvoiceHeader
from ..models.invoice_line import InvoiceLine
from ..models.segment import Segment
from ..models.traceability import Traceability
from ..pipeline.confidence_scoring import score_total_amount_candidate, validate_total_against_line_items


def extract_total_amount(
    footer_segment: Optional[Segment],
    line_items: List[InvoiceLine],
    invoice_header: InvoiceHeader
) -> None:
    """Extract total amount from footer segment using keyword matching and confidence scoring.
    
    Args:
        footer_segment: Footer segment (or None if not found)
        line_items: List of InvoiceLine objects for mathematical validation
        invoice_header: InvoiceHeader to update with extracted total amount
        
    Algorithm:
    1. Extract all amount candidates from footer segment rows
    2. Score each candidate using multi-factor scoring
    3. Select final value (highest score, validation preference)
    4. Create traceability evidence
    5. Update InvoiceHeader with total_amount, total_confidence, total_traceability
    """
    if footer_segment is None or not footer_segment.rows:
        # No footer segment → REVIEW
        invoice_header.total_confidence = 0.0
        invoice_header.total_amount = None
        invoice_header.total_traceability = None
        return
    
    # Step 1: Extract all amount candidates from footer rows
    candidates = []
    keyword_patterns = [
        r"att\s+betala",
        r"totalt",
        r"total",
        r"summa\s+att\s+betala"
    ]
    
    amount_pattern = re.compile(r'[\d\s]+[.,]\d{2}')  # Matches "123,45" or "123.45"
    currency_symbols = ['kr', 'SEK', 'sek', ':-']
    
    for row_index, row in enumerate(footer_segment.rows):
        row_lower = row.text.lower()
        
        # Check if row contains total keywords
        has_keyword = any(re.search(pattern, row_lower, re.IGNORECASE) for pattern in keyword_patterns)
        
        # Extract numeric amounts from row
        for token in row.tokens:
            token_text = token.text.strip()
            if amount_pattern.search(token_text):
                # Extract numeric value
                cleaned = token_text
                for sym in currency_symbols:
                    cleaned = cleaned.replace(sym, '')
                cleaned = cleaned.replace(',', '.').replace(' ', '')
                
                try:
                    amount = float(cleaned)
                    if amount > 0:  # Valid amount
                        candidates.append({
                            'amount': amount,
                            'row': row,
                            'row_index': row_index,
                            'token': token,
                            'has_keyword': has_keyword
                        })
                except ValueError:
                    continue
    
    if not candidates:
        # No candidates found → REVIEW
        invoice_header.total_confidence = 0.0
        invoice_header.total_amount = None
        invoice_header.total_traceability = None
        return
    
    # Step 2: Score each candidate (limit to top 10 for performance)
    scored_candidates = []
    for candidate in candidates[:10]:  # Limit to top 10
        score = score_total_amount_candidate(
            candidate['amount'],
            candidate['row'],
            footer_segment.page,
            line_items,
            footer_segment.rows
        )
        scored_candidates.append({
            **candidate,
            'score': score
        })
    
    # Sort by score descending
    scored_candidates.sort(key=lambda c: c['score'], reverse=True)
    
    # Step 3: Select final value
    if not scored_candidates:
        invoice_header.total_confidence = 0.0
        invoice_header.total_amount = None
        invoice_header.total_traceability = None
        return
    
    top_candidate = scored_candidates[0]
    
    # If two totals compete but only one passes validation → choose validated one
    if len(scored_candidates) > 1:
        validated_candidates = [
            c for c in scored_candidates
            if validate_total_against_line_items(c['amount'], line_items, tolerance=1.0)
        ]
        if validated_candidates:
            top_candidate = validated_candidates[0]  # Choose validated one
    
    final_amount = top_candidate['amount']
    final_score = top_candidate['score']
    final_row = top_candidate['row']
    
    # Step 4: Create traceability evidence
    page_number = footer_segment.page.page_number
    
    # Calculate bbox (union of all tokens in row)
    if final_row.tokens:
        x_coords = [t.x for t in final_row.tokens]
        y_coords = [t.y for t in final_row.tokens]
        x_max_coords = [t.x + t.width for t in final_row.tokens]
        y_max_coords = [t.y + t.height for t in final_row.tokens]
        
        bbox = [
            min(x_coords),  # x
            min(y_coords),  # y
            max(x_max_coords) - min(x_coords),  # width
            max(y_max_coords) - min(y_coords)   # height
        ]
    else:
        bbox = [final_row.x_min, final_row.y, final_row.x_max - final_row.x_min, 12.0]
    
    # Text excerpt (max 120 characters, full row if shorter)
    text_excerpt = final_row.text[:120] if len(final_row.text) > 120 else final_row.text
    
    # Tokens (minimal info for JSON)
    tokens = []
    for token in final_row.tokens:
        tokens.append({
            "text": token.text,
            "bbox": [token.x, token.y, token.width, token.height],
            "conf": 1.0  # Default confidence (pdfplumber tokens have high confidence)
        })
    
    evidence = {
        "page_number": page_number,
        "bbox": bbox,
        "row_index": top_candidate['row_index'],
        "text_excerpt": text_excerpt,
        "tokens": tokens
    }
    
    traceability = Traceability(
        field="total",
        value=str(final_amount),
        confidence=final_score,
        evidence=evidence
    )
    
    # Step 5: Update InvoiceHeader
    invoice_header.total_amount = final_amount
    invoice_header.total_confidence = final_score
    invoice_header.total_traceability = traceability

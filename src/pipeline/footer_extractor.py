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
    invoice_header: InvoiceHeader,
    strategy: Optional[str] = None
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
    
    # Keywords for total WITH VAT (highest priority - this is what customer pays)
    # Support for different layouts:
    # - "ATT BETALA SEK:" (uppercase, with colon)
    # - "Att betala 66 322,00 SEK" (in box)
    # - "SUMMA ATT BETALA" (uppercase)
    # - "Fakturabelopp" (Derome layout)
    total_with_vat_patterns = [
        # "Att betala" variants - with SEK (uppercase and lowercase)
        r"att\s+betala\s+sek\s*:",
        r"att\s+betala\s+sek",
        r"attbetala\s+sek\s*:",
        r"attbetala\s+sek",
        r"att\s+betala\s+sek\s*",
        r"ATT\s+BETALA\s+SEK\s*:",
        r"ATT\s+BETALA\s+SEK",
        # "Att betala" variants - with colon and SEK (Ramirent: "Att betala: SEK 3.717,35")
        r"att\s+betala\s*:\s*sek",
        r"ATT\s+BETALA\s*:\s*SEK",
        # "Att betala" variants - without SEK (may be in box or separate)
        r"att\s+betala\s*:",
        r"att\s+betala",
        r"attbetala\s*:",
        r"attbetala",
        r"ATT\s+BETALA\s*:",
        r"ATT\s+BETALA",
        # "Summa att betala" variants (uppercase)
        r"summa\s+att\s+betala",
        r"SUMMA\s+ATT\s+BETALA",
        r"summa\s+attbetala",
        # "Fakturabelopp" (Derome layout)
        r"fakturabelopp",
        r"Fakturabelopp",
        # "Summa att betala" variants
        r"summa\s+att\s+betala",
        r"summa\s+attbetala",
        r"summa\s+att\s+betala\s+sek",
        # "Belopp att betala" variants
        r"belopp\s+att\s+betala",
        r"belopp\s+attbetala",
        r"belopp\s+att\s+betala\s+sek",
        r"betalningsbelopp",
        r"betalningsbeloppet",
        r"betalningsbelopp\s+sek",
        # "Inkl. moms" variants
        r"totalt\s+inkl\.?\s*moms",
        r"total\s+inkl\.?\s*moms",
        r"totalt\s+inklusive\s+moms",
        r"total\s+inklusive\s+moms",
        r"totalt\s+inkl\.?\s+moms",
        r"total\s+inkl\.?\s+moms",
        r"inkl\.?\s*moms",
        r"inklusive\s+moms",
        r"inkl\s+moms",
        # "Med moms" variants
        r"totalt\s+med\s+moms",
        r"total\s+med\s+moms",
        r"med\s+moms",
        # "Moms inkluderad" variants
        r"totalt\s+moms\s+inkluderad",
        r"total\s+moms\s+inkluderad",
        # "Betalas" variants
        r"betalas",
        r"betalas\s+sek",
        r"belopp\s+betalas",
        # "Slutsumma" (usually includes VAT)
        r"slutsumma",
        r"slutsumma\s+inkl\.?\s*moms",
        # "Netto" (sometimes used for total with VAT in some contexts)
        r"netto\s+att\s+betala",
        r"netto\s+betalas"
    ]
    
    # Keywords for total WITHOUT VAT (lower priority - this is subtotal)
    total_without_vat_patterns = [
        # "Exkl. moms" variants
        r"totalt\s+exkl\.?\s*moms",
        r"total\s+exkl\.?\s*moms",
        r"totalt\s+exklusive\s+moms",
        r"total\s+exklusive\s+moms",
        r"totalt\s+exkl\.?\s+moms",
        r"total\s+exkl\.?\s+moms",
        r"exkl\.?\s*moms",
        r"exklusive\s+moms",
        r"exkl\s+moms",
        # "Utan moms" variants
        r"totalt\s+utan\s+moms",
        r"total\s+utan\s+moms",
        r"utan\s+moms",
        # Subtotal variants
        r"delsumma",
        r"subtotal",
        r"summa\s+exkl\.?\s*moms",
        r"summa\s+exklusive\s+moms",
        # "Momsfri" variants
        r"momsfri\s+summa",
        r"momsfritt\s+belopp",
        # "Netto" (sometimes used for subtotal)
        r"netto",
        r"netto\s+exkl\.?\s*moms"
    ]
    
    # Generic total keywords (medium priority)
    # Support different layouts: "Fakturabelopp" (Derome), "Totalsumma SEK" (Renta)
    generic_total_patterns = [
        r"totalt",
        r"total",
        r"summa",
        r"belopp",
        r"slutsumma",  # Could be with or without VAT, but often with
        r"fakturabelopp",
        r"fakturabeloppet",
        r"Fakturabelopp",  # Uppercase (Derome layout)
        r"totalsumma",
        r"Totalsumma",
        r"totalsumma\s+sek",
        r"Totalsumma\s+SEK"
    ]
    
    # Combined patterns for keyword detection
    keyword_patterns = total_with_vat_patterns + total_without_vat_patterns + generic_total_patterns
    
    # Improved amount pattern: matches amounts with/without decimals, with/without thousand separators
    # Matches: "123,45", "123.45", "1 234,56", "1234", "1 234", "3.717,35" (punkt som tusentalsavgränsare)
    # Support both Swedish format (komma som decimal, punkt/mellanslag som tusentalsavgränsare)
    # and international format (punkt som decimal, komma som tusentalsavgränsare)
    amount_pattern = re.compile(
        r'\d{1,3}(?:\s+\d{3})*(?:[.,]\d{1,2})?|'  # Swedish: "1 234,56" or "3.717,35"
        r'\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|'      # Swedish with dots: "3.717,35"
        r'\d+(?:[.,]\d{1,2})?'                     # Simple: "123,45" or "123.45" or "8302.00"
    )
    currency_symbols = ['kr', 'SEK', 'sek', ':-', '€', '$']
    
    for row_index, row in enumerate(footer_segment.rows):
        row_lower = row.text.lower()
        
        # Check if row contains total keywords and classify type
        has_keyword = False
        keyword_type = None  # 'with_vat', 'without_vat', 'generic'
        
        # Check for "with VAT" keywords first (highest priority)
        if any(re.search(pattern, row_lower, re.IGNORECASE) for pattern in total_with_vat_patterns):
            has_keyword = True
            keyword_type = 'with_vat'
        # Check for "without VAT" keywords
        elif any(re.search(pattern, row_lower, re.IGNORECASE) for pattern in total_without_vat_patterns):
            has_keyword = True
            keyword_type = 'without_vat'
        # Check for generic total keywords
        elif any(re.search(pattern, row_lower, re.IGNORECASE) for pattern in generic_total_patterns):
            has_keyword = True
            keyword_type = 'generic'
        
        # Extract numeric amounts from row text (better than token-by-token for thousand separators)
        row_text = row.text
        amount_matches = amount_pattern.finditer(row_text)
        
        for match in amount_matches:
            amount_text = match.group(0)
            # Clean and convert to float
            # Handle both Swedish format (komma som decimal, punkt som tusentalsavgränsare)
            # and international format (punkt som decimal)
            cleaned = amount_text
            for sym in currency_symbols:
                cleaned = cleaned.replace(sym, '')
            cleaned = cleaned.replace(' ', '')  # Remove spaces (thousand separators)
            
            # Detect format: if contains both comma and dot, assume Swedish format (3.717,35)
            if ',' in cleaned and '.' in cleaned:
                # Swedish format: "3.717,35" -> "3717.35"
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                # Only comma: could be Swedish decimal or international thousand separator
                # If comma is followed by 1-2 digits at end, it's decimal: "123,45" -> "123.45"
                if re.search(r',\d{1,2}$', cleaned):
                    cleaned = cleaned.replace(',', '.')
                else:
                    # Comma as thousand separator: "1,234" -> "1234"
                    cleaned = cleaned.replace(',', '')
            elif '.' in cleaned:
                # Only dot: could be decimal or thousand separator
                # If dot is followed by 1-2 digits at end, it's decimal: "123.45" -> "123.45"
                if re.search(r'\.\d{1,2}$', cleaned):
                    # Already correct decimal format
                    pass
                else:
                    # Dot as thousand separator: "1.234" -> "1234"
                    cleaned = cleaned.replace('.', '')
            
            try:
                amount = float(cleaned)
                if amount > 0:  # Valid amount
                    # Find token that contains this amount (for traceability)
                    match_start = match.start()
                    match_end = match.end()
                    matching_token = None
                    char_pos = 0
                    for token in row.tokens:
                        token_end = char_pos + len(token.text)
                        if match_start >= char_pos and match_end <= token_end:
                            matching_token = token
                            break
                        char_pos = token_end + 1  # +1 for space between tokens
                    
                    candidates.append({
                        'amount': amount,
                        'row': row,
                        'row_index': row_index,
                        'token': matching_token or row.tokens[0] if row.tokens else None,
                        'has_keyword': has_keyword,
                        'keyword_type': keyword_type  # 'with_vat', 'without_vat', 'generic', or None
                    })
            except ValueError:
                continue
    
    if not candidates:
        # No candidates found → REVIEW
        invoice_header.total_confidence = 0.0
        invoice_header.total_amount = None
        invoice_header.total_traceability = None
        invoice_header.total_candidates = None
        return
    
    # Step 2: Score ALL candidates independently (no limit)
    scored_candidates = []
    for candidate in candidates:  # Score all candidates, not just top 10
        score = score_total_amount_candidate(
            candidate['amount'],
            candidate['row'],
            footer_segment.page,
            line_items,
            footer_segment.rows
        )
        
        # Boost score based on keyword type (prioritize "with VAT" totals)
        keyword_type = candidate.get('keyword_type')
        if keyword_type == 'with_vat':
            # Adjust boost based on strategy
            if strategy == 'aggressive':
                boost = 0.20  # Higher boost for aggressive strategy
            elif strategy == 'conservative':
                boost = 0.10  # Lower boost for conservative strategy
            else:
                boost = 0.15  # Default boost
            score = min(score + boost, 1.0)  # Boost for "att betala" / "inkl. moms"
        elif keyword_type == 'without_vat':
            # Adjust penalty based on strategy
            if strategy == 'aggressive':
                penalty = 0.05  # Lower penalty for aggressive (might accept subtotals)
            elif strategy == 'conservative':
                penalty = 0.15  # Higher penalty for conservative (strictly reject subtotals)
            else:
                penalty = 0.10  # Default penalty
            score = max(score - penalty, 0.0)  # Penalize "exkl. moms" (this is subtotal, not total)
        # 'generic' and None get no boost/penalty
        
        scored_candidates.append({
            **candidate,
            'score': score
        })
    
    # Sort by score descending, then by keyword_type priority
    def sort_key(c):
        type_priority = {'with_vat': 3, 'generic': 2, 'without_vat': 1, None: 0}
        return (c['score'], type_priority.get(c.get('keyword_type'), 0))
    
    scored_candidates.sort(key=sort_key, reverse=True)
    
    # Step 3: Store top 5 candidates for UI display
    top_5_candidates = []
    for candidate in scored_candidates[:5]:  # Top 5 only
        top_5_candidates.append({
            'amount': candidate['amount'],
            'score': candidate['score'],
            'row_index': candidate['row_index'],
            'keyword_type': candidate.get('keyword_type')
        })
    
    invoice_header.total_candidates = top_5_candidates if top_5_candidates else None
    
    # Step 4: Select final value
    if not scored_candidates:
        invoice_header.total_confidence = 0.0
        invoice_header.total_amount = None
        invoice_header.total_traceability = None
        return
    
    top_candidate = scored_candidates[0]
    
    # If two totals compete, prefer:
    # 1. "with_vat" keyword type (att betala / inkl. moms)
    # 2. Validated candidates (matches line items)
    # 3. Highest score
    if len(scored_candidates) > 1:
        # First, try to find "with_vat" candidates
        with_vat_candidates = [c for c in scored_candidates if c.get('keyword_type') == 'with_vat']
        if with_vat_candidates:
            # Among "with_vat" candidates, prefer validated ones
            validated_with_vat = [
                c for c in with_vat_candidates
                if validate_total_against_line_items(c['amount'], line_items, tolerance=1.0)
            ]
            if validated_with_vat:
                top_candidate = validated_with_vat[0]
            else:
                top_candidate = with_vat_candidates[0]
        else:
            # No "with_vat" candidates, prefer validated ones
            validated_candidates = [
                c for c in scored_candidates
                if validate_total_against_line_items(c['amount'], line_items, tolerance=1.0)
            ]
            if validated_candidates:
                top_candidate = validated_candidates[0]
    
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
    # total_candidates already set in Step 3

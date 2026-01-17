"""Header extraction for invoice number, vendor, and date with confidence scoring."""

import re
from datetime import date
from typing import List, Optional

from ..models.invoice_header import InvoiceHeader
from ..models.row import Row
from ..models.segment import Segment
from ..models.traceability import Traceability
from ..pipeline.confidence_scoring import score_invoice_number_candidate


def extract_invoice_number(
    header_segment: Optional[Segment],
    invoice_header: InvoiceHeader
) -> None:
    """Extract invoice number from header segment using keyword proximity, regex, and confidence scoring.
    
    Args:
        header_segment: Header segment (or None if not found)
        invoice_header: InvoiceHeader to update with extracted invoice number
        
    Algorithm:
    1. Extract all candidates from header segment rows using regex and keywords
    2. Score each candidate using multi-factor scoring
    3. Select final value (highest score, handle tie-breaking: top-2 within 0.03 → REVIEW)
    4. Create traceability evidence
    5. Update InvoiceHeader with invoice_number, invoice_number_confidence, invoice_number_traceability
    """
    if header_segment is None or not header_segment.rows:
        # No header segment → REVIEW
        invoice_header.invoice_number_confidence = 0.0
        invoice_header.invoice_number = None
        invoice_header.invoice_number_traceability = None
        return
    
    # Step 1: Extract all candidates from header rows
    candidates = []
    
    # Regex pattern for invoice number after keywords (Heuristik 5)
    invoice_pattern = re.compile(
        r'(?:fakturanummer|invoice\s*number|no\.|nr|number)[\s:]*([A-Z0-9\-]+)',
        re.IGNORECASE
    )
    
    # Also search for standalone alphanumeric patterns in header zone (fallback)
    alphanumeric_pattern = re.compile(r'([A-Z0-9\-]{3,25})', re.IGNORECASE)
    
    all_rows = header_segment.rows
    
    for row_index, row in enumerate(all_rows):
        row_text = row.text
        
        # Search for invoice number after keywords
        matches = invoice_pattern.findall(row_text)
        for match in matches:
            if match:
                candidates.append({
                    'candidate': match.strip(),
                    'row': row,
                    'row_index': row_index,
                    'source': 'keyword'
                })
        
        # Fallback: standalone alphanumeric patterns (less confident)
        if not matches:
            alphanumeric_matches = alphanumeric_pattern.findall(row_text)
            for match in alphanumeric_matches:
                # Skip if looks like date, amount, or org number
                if _validate_invoice_number_format(match):
                    candidates.append({
                        'candidate': match.strip(),
                        'row': row,
                        'row_index': row_index,
                        'source': 'fallback'
                    })
    
    if not candidates:
        # No candidates found → REVIEW
        invoice_header.invoice_number_confidence = 0.0
        invoice_header.invoice_number = None
        invoice_header.invoice_number_traceability = None
        return
    
    # Step 2: Score each candidate (limit to top 10 for performance)
    scored_candidates = []
    for candidate in candidates[:10]:  # Limit to top 10
        score = score_invoice_number_candidate(
            candidate['candidate'],
            candidate['row'],
            header_segment.page,
            all_rows
        )
        scored_candidates.append({
            **candidate,
            'score': score
        })
    
    # Sort by score descending
    scored_candidates.sort(key=lambda c: c['score'], reverse=True)
    
    # Step 3: Select final value with tie-breaking logic
    if not scored_candidates:
        invoice_header.invoice_number_confidence = 0.0
        invoice_header.invoice_number = None
        invoice_header.invoice_number_traceability = None
        return
    
    top_candidate = scored_candidates[0]
    
    # Tie-breaking: If top-2 candidates are within 0.03 score difference and have different values → REVIEW
    if len(scored_candidates) > 1:
        top_score = top_candidate['score']
        second_score = scored_candidates[1]['score']
        top_value = top_candidate['candidate']
        second_value = scored_candidates[1]['candidate']
        
        if (abs(top_score - second_score) <= 0.03 and top_value != second_value):
            # Tie → REVIEW (don't store value)
            invoice_header.invoice_number_confidence = max(top_score, second_score)
            invoice_header.invoice_number = None  # Don't store uncertain value
            invoice_header.invoice_number_traceability = None
            return
    
    final_number = top_candidate['candidate']
    final_score = top_candidate['score']
    final_row = top_candidate['row']
    
    # Only store if confidence ≥ 0.95 (hard gate)
    if final_score < 0.95:
        invoice_header.invoice_number_confidence = final_score
        invoice_header.invoice_number = None  # REVIEW
        invoice_header.invoice_number_traceability = None
        return
    
    # Step 4: Create traceability evidence
    page_number = header_segment.page.page_number
    
    # Calculate bbox (union of all tokens matching invoice number)
    matching_tokens = [t for t in final_row.tokens if final_number in t.text]
    if matching_tokens:
        x_coords = [t.x for t in matching_tokens]
        y_coords = [t.y for t in matching_tokens]
        x_max_coords = [t.x + t.width for t in matching_tokens]
        y_max_coords = [t.y + t.height for t in matching_tokens]
        
        bbox = [
            min(x_coords),  # x
            min(y_coords),  # y
            max(x_max_coords) - min(x_coords),  # width
            max(y_max_coords) - min(y_coords)   # height
        ]
    else:
        # Fallback: use row bbox
        bbox = [final_row.x_min, final_row.y, final_row.x_max - final_row.x_min, 12.0]
    
    # Text excerpt (max 120 characters, full row if shorter)
    text_excerpt = final_row.text[:120] if len(final_row.text) > 120 else final_row.text
    
    # Tokens (minimal info for JSON - only matching tokens)
    tokens = []
    for token in matching_tokens:
        tokens.append({
            "text": token.text,
            "bbox": [token.x, token.y, token.width, token.height],
            "conf": 1.0  # Default confidence (pdfplumber tokens)
        })
    
    evidence = {
        "page_number": page_number,
        "bbox": bbox,
        "row_index": top_candidate['row_index'],
        "text_excerpt": text_excerpt,
        "tokens": tokens
    }
    
    traceability = Traceability(
        field="invoice_no",
        value=final_number,
        confidence=final_score,
        evidence=evidence
    )
    
    # Step 5: Update InvoiceHeader
    invoice_header.invoice_number = final_number
    invoice_header.invoice_number_confidence = final_score
    invoice_header.invoice_number_traceability = traceability


def _validate_invoice_number_format(candidate: str) -> bool:
    """Validate invoice number format (helper for fallback matching).
    
    Args:
        candidate: Candidate invoice number string
        
    Returns:
        True if format looks like invoice number (alphanumeric, length 3-25, not date/amount)
    """
    if not candidate:
        return False
    
    # Length check (3-25 characters)
    if not (3 <= len(candidate) <= 25):
        return False
    
    # Alphanumeric with dashes
    if not re.match(r'^[A-Z0-9\-]+$', candidate, re.IGNORECASE):
        return False
    
    # Not just digits (likely not org number or amount)
    if candidate.isdigit() and len(candidate) > 6:
        return False
    
    # Not a date pattern
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',
        r'\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}',
    ]
    for pattern in date_patterns:
        if re.match(pattern, candidate):
            return False
    
    return True


def extract_invoice_date(
    header_segment: Optional[Segment],
    invoice_header: InvoiceHeader
) -> None:
    """Extract invoice date from header segment and normalize to ISO format.
    
    Args:
        header_segment: Header segment (or None if not found)
        invoice_header: InvoiceHeader to update with extracted date
    """
    if header_segment is None or not header_segment.rows:
        invoice_header.invoice_date = None
        return
    
    # Date keywords
    date_keywords = ["datum", "date", "fakturadatum", "invoice date"]
    
    # Date patterns (Heuristik 6)
    date_patterns = [
        (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),  # ISO: YYYY-MM-DD
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', None),  # DD/MM/YYYY or MM/DD/YYYY
        (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', None),  # DD.MM.YYYY
        (r'(\d{1,2})-(\d{1,2})-(\d{4})', None),  # DD-MM-YYYY
    ]
    
    for row in header_segment.rows:
        row_lower = row.text.lower()
        
        # Check if row contains date keywords
        has_keyword = any(keyword in row_lower for keyword in date_keywords)
        
        # Try to extract date
        for pattern, date_format in date_patterns:
            match = re.search(pattern, row.text)
            if match:
                try:
                    if date_format:
                        # ISO format
                        date_obj = date.fromisoformat(match.group(1))
                    else:
                        # DD/MM/YYYY or similar - assume Swedish format (DD/MM/YYYY)
                        groups = match.groups()
                        day = int(groups[0])
                        month = int(groups[1])
                        year = int(groups[2])
                        date_obj = date(year, month, day)
                    
                    invoice_header.invoice_date = date_obj
                    return  # Found date, stop searching
                except (ValueError, AttributeError):
                    continue  # Try next pattern
    
    # No date found
    invoice_header.invoice_date = None


def extract_vendor_name(
    header_segment: Optional[Segment],
    invoice_header: InvoiceHeader
) -> None:
    """Extract vendor/company name from header segment.
    
    Args:
        header_segment: Header segment (or None if not found)
        invoice_header: InvoiceHeader to update with extracted vendor name
        
    Note:
        Company name only (address extraction deferred to later phase).
        Uses heuristics: first substantial text row, largest font size, company suffixes.
    """
    if header_segment is None or not header_segment.rows:
        invoice_header.supplier_name = None
        return
    
    # Keywords to avoid (metadata, not company name)
    skip_keywords = ["faktura", "invoice", "datum", "date", "fakturanummer", "invoice number"]
    
    # Company suffixes
    company_suffixes = ["AB", "Ltd", "Inc", "AB", "Ltd.", "Inc.", "Aktiebolag"]
    
    candidates = []
    
    for row in header_segment.rows[:5]:  # Check first 5 rows (company name usually in top)
        row_lower = row.text.lower()
        
        # Skip rows with metadata keywords
        if any(keyword in row_lower for keyword in skip_keywords):
            continue
        
        # Skip very short rows
        if len(row.text.strip()) < 3:
            continue
        
        # Check for company suffixes
        has_suffix = any(suffix in row.text for suffix in company_suffixes)
        
        # Extract candidate (limit length to 100 characters)
        candidate_text = row.text.strip()[:100]
        
        candidates.append({
            'text': candidate_text,
            'row': row,
            'has_suffix': has_suffix,
            'position': header_segment.rows.index(row)  # Earlier = better
        })
    
    if not candidates:
        invoice_header.supplier_name = None
        return
    
    # Select best candidate: prefer rows with company suffix, then earlier position
    best_candidate = sorted(
        candidates,
        key=lambda c: (not c['has_suffix'], c['position'])  # Has suffix first, then position
    )[0]
    
    invoice_header.supplier_name = best_candidate['text']


def extract_header_fields(
    header_segment: Optional[Segment],
    invoice_header: InvoiceHeader
) -> None:
    """Extract all header fields (invoice number, date, vendor) in one call.
    
    Args:
        header_segment: Header segment (or None if not found)
        invoice_header: InvoiceHeader to update with extracted fields
    """
    extract_invoice_number(header_segment, invoice_header)
    extract_invoice_date(header_segment, invoice_header)
    extract_vendor_name(header_segment, invoice_header)

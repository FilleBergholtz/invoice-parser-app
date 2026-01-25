"""Header extraction for invoice number, vendor, and date with confidence scoring."""

import re
from datetime import date
from typing import List, Optional, Callable

from ..models.invoice_header import InvoiceHeader
from ..models.row import Row
from ..models.segment import Segment
from ..models.traceability import Traceability
from ..pipeline.confidence_scoring import score_invoice_number_candidate


def extract_invoice_number(
    header_segment: Optional[Segment],
    invoice_header: InvoiceHeader,
    strategy: Optional[str] = None
) -> None:
    """Extract invoice number from header segment using extended labels, normalization, and improved search logic.
    
    Args:
        header_segment: Header segment (or None if not found)
        invoice_header: InvoiceHeader to update with extracted invoice number
        strategy: Optional strategy variant ('aggressive', 'conservative', 'extended_patterns', 'broader_search')
        
    Algorithm:
    1. Normalize text and search for invoice number labels (Swedish + English variants)
    2. Extract candidates: same row (highest priority) or 1-2 rows below label
    3. Fallback: header scan for numeric sequences (5-12 digits) in top 25% of page
    4. Score all candidates using multi-factor scoring
    5. Always store best candidate (even if confidence < 0.95) - status will be REVIEW
    6. Create traceability evidence
    
    Strategy variants:
    - None/standard: Default behavior
    - 'aggressive': Use broader patterns, search more rows, lower thresholds
    - 'conservative': Use stricter patterns, only same-row matches
    - 'extended_patterns': Add more label pattern variations
    - 'broader_search': Search larger area (top 40% instead of 25%)
    """
    if header_segment is None or not header_segment.rows:
        # No header segment → REVIEW
        invoice_header.invoice_number_confidence = 0.0
        invoice_header.invoice_number = None
        invoice_header.invoice_number_traceability = None
        return
    
    all_rows = header_segment.rows
    page = header_segment.page
    candidates = []
    
    # Step 1: Extended label patterns (Swedish + English)
    # Normalized patterns (will be applied to normalized text)
    # Support for different invoice layouts:
    # - "Faktnr:" (with colon, top right)
    # - "Fakturanummer" (without colon, left-center)
    # - "Fakturanummer 3799677" (number directly after label)
    label_patterns = [
        # Swedish variants - with colon
        r'fakturanummer\s*:',
        r'faktura\s*nr\s*:',
        r'faktura\s*-\s*nr\s*:',
        r'fakt\.\s*nr\s*:',
        r'fakt\.nr\s*:',
        r'faktnr\s*:',
        r'fakt\s*nr\s*:',
        r'fakt\s*-\s*nr\s*:',
        r'fakt\s*nr\.\s*:',
        r'fakt\.nr\.\s*:',
        r'fakturanr\s*:',  # "Fakturanr:" (K-Bygg, Jicon layout)
        r'fakturanr\.\s*:',  # "Fakturanr.:"
        # Swedish variants - without colon (number may follow directly)
        r'fakturanummer',
        r'faktura\s*nr',
        r'faktura\s*-\s*nr',
        r'fakt\.\s*nr',
        r'fakt\.nr',
        r'faktnr',
        r'fakt\s*nr',
        r'fakt\s*-\s*nr',
        r'fakt\s*nr\.',
        r'fakt\.nr\.',
        r'fakturanr',  # "Fakturanr" (without colon)
        r'fakturanr\.',  # "Fakturanr."
        # "Faktura" followed by number (Ramirent layout: "Faktura 40615472")
        r'faktura\s+\d',  # "Faktura" followed by space and digit
        # English variants
        r'invoice\s*number',
        r'invoice\s*no\s*:',
        r'invoice\s*no\.\s*:',
        r'invoice\s*no',
        r'invoice\s*no\.',
        r'inv\s*no\s*:',
        r'inv\s*no\.\s*:',
        r'inv\s*no',
        r'inv\s*no\.',
        r'inv#',
    ]
    
    # Combined pattern for label matching
    label_pattern = re.compile(
        r'(?:' + '|'.join(label_patterns) + r')',
        re.IGNORECASE
    )
    
    # Primary regex for invoice number: Support different formats
    # - Numeric: 3128536, 001002687 (with leading zeros), 4578138002 (10 digits)
    # - Alphanumeric: CD3013683076, INV-2024-001
    # Adjust based on strategy
    if strategy == 'aggressive':
        # Very broad: alphanumeric with dashes, or 3-15 digits
        primary_number_pattern = re.compile(r'\b([A-Z]{0,3}\d{3,12}[A-Z0-9]{0,3}|[A-Z]+\d+[A-Z0-9]*|\d{3,15})\b')
        fallback_number_pattern = re.compile(r'\b([A-Z0-9\-]{4,20})\b')  # Very broad alphanumeric
    elif strategy == 'conservative':
        # Stricter: 7-10 digits or alphanumeric with specific pattern
        primary_number_pattern = re.compile(r'\b([A-Z]{1,3}\d{6,10}|\d{7,10})\b')
        fallback_number_pattern = re.compile(r'\b([A-Z]{0,2}\d{6,10})\b')
    else:
        # Default: Support alphanumeric (CD3013683076) and numeric (with leading zeros)
        primary_number_pattern = re.compile(r'\b([A-Z]{1,3}\d{4,12}[A-Z0-9]{0,3}|\d{5,12})\b')
        fallback_number_pattern = re.compile(r'\b([A-Z0-9\-]{4,20})\b')  # Alphanumeric with dashes
    
    # Step 2: Search for labels and extract numbers
    for row_index, row in enumerate(all_rows):
        # Normalize row text
        normalized_text = _normalize_text(row.text)
        
        # Check if row contains label
        label_match = label_pattern.search(normalized_text)
        
        if label_match:
            # Label found - search for number on same row (to the right of label)
            label_pos = label_match.end()
            text_after_label = normalized_text[label_pos:]
            
            # Try primary pattern first
            number_match = primary_number_pattern.search(text_after_label)
            if not number_match:
                # Fallback to broader pattern
                number_match = fallback_number_pattern.search(text_after_label)
            
            if number_match:
                candidate = number_match.group(1)
                candidates.append({
                    'candidate': candidate,
                    'row': row,
                    'row_index': row_index,
                    'source': 'label_same_row',
                    'priority': 1  # Highest priority
                })
            
            # Also check 1-2 rows below label
            for offset in [1, 2]:
                if row_index + offset < len(all_rows):
                    below_row = all_rows[row_index + offset]
                    below_normalized = _normalize_text(below_row.text)
                    
                    # Try primary pattern
                    number_match = primary_number_pattern.search(below_normalized)
                    if not number_match:
                        number_match = fallback_number_pattern.search(below_normalized)
                    
                    if number_match:
                        candidate = number_match.group(1)
                        candidates.append({
                            'candidate': candidate,
                            'row': below_row,
                            'row_index': row_index + offset,
                            'source': f'label_below_{offset}',
                            'priority': 2 + offset  # Lower priority than same row
                        })
    
    # Step 3: Fallback - header scan (if no label found)
    if not candidates:
        # Adjust search area based on strategy
        if strategy == 'broader_search':
            page_top_threshold = page.height * 0.40  # Search larger area
        elif strategy == 'conservative':
            page_top_threshold = page.height * 0.20  # Smaller area
        else:
            page_top_threshold = page.height * 0.25  # Default
        header_rows = [r for r in all_rows if r.y < page_top_threshold]
        
        for row_index, row in enumerate(header_rows):
            normalized_text = _normalize_text(row.text)
            
            # Extract all numeric sequences
            number_matches = fallback_number_pattern.findall(normalized_text)
            
            for match in number_matches:
                candidate = match
                # Filter out dates, years, amounts, postal codes
                if _is_valid_invoice_number_candidate(candidate, row, all_rows):
                    candidates.append({
                        'candidate': candidate,
                        'row': row,
                        'row_index': row_index,
                        'source': 'header_scan',
                        'priority': 10  # Lowest priority
                    })
    
    if not candidates:
        # No candidates found → REVIEW
        invoice_header.invoice_number_confidence = 0.0
        invoice_header.invoice_number = None
        invoice_header.invoice_number_traceability = None
        return
    
    # Step 4: Score each candidate (limit to top 20 for performance)
    scored_candidates = []
    for candidate in candidates[:20]:  # Limit to top 20
        score = score_invoice_number_candidate(
            candidate['candidate'],
            candidate['row'],
            page,
            all_rows
        )
        # Boost score based on source priority
        priority_boost = {
            1: 0.1,  # label_same_row
            2: 0.05,  # label_below_1
            3: 0.02,  # label_below_2
            10: 0.0   # header_scan
        }
        score = min(score + priority_boost.get(candidate.get('priority', 10), 0.0), 1.0)
        
        scored_candidates.append({
            **candidate,
            'score': score
        })
    
    # Sort by score descending, then by priority
    scored_candidates.sort(key=lambda c: (c['score'], -c.get('priority', 10)), reverse=True)
    
    # Step 5: Select final value - ALWAYS store best candidate (even if confidence < 0.95)
    if not scored_candidates:
        invoice_header.invoice_number_confidence = 0.0
        invoice_header.invoice_number = None
        invoice_header.invoice_number_traceability = None
        return
    
    top_candidate = scored_candidates[0]
    final_number = top_candidate['candidate']
    final_score = top_candidate['score']
    final_row = top_candidate['row']
    
    # INV-NUM-02: Om ett helt token i headern innehåller valt kandidat och är längre (t.ex. "4061547206" vs "0615472"), använd hela token
    for row in all_rows:
        for t in row.tokens:
            s = t.text
            if not s.isdigit() or final_number not in s or len(s) <= len(final_number):
                continue
            if 5 <= len(s) <= 12:
                # Tokens som "4061547206" (10 siffror) kan vara "40615472" + "06" (år/suffix); använd 8 siffror om suffix ser ut som år
                if len(s) == 10 and s[-2:] in ('06', '24', '25', '26'):
                    final_number = s[:8]
                else:
                    final_number = s
                final_row = row
                break
        else:
            continue
        break
    
    # Note: We no longer have hard gate - always store the best candidate
    # Status will be REVIEW if confidence < 0.95 (handled in validation)
    
    # Step 6: Create traceability evidence
    page_number = page.page_number
    
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
    
    # Step 7: Update InvoiceHeader - ALWAYS store value (even if confidence < 0.95)
    invoice_header.invoice_number = final_number
    invoice_header.invoice_number_confidence = final_score
    invoice_header.invoice_number_traceability = traceability


def _normalize_text(text: str) -> str:
    """Normalize text for matching: lowercase, remove : and #, collapse spaces, keep dots.
    
    Args:
        text: Input text
        
    Returns:
        Normalized text
    """
    # Lowercase
    normalized = text.lower()
    
    # Remove : and #
    normalized = normalized.replace(':', ' ').replace('#', ' ')
    
    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Keep dots (for fakt.nr)
    # Already handled by space collapse
    
    return normalized.strip()


def _is_valid_invoice_number_candidate(candidate: str, row: Row, all_rows: List[Row]) -> bool:
    """Check if candidate is valid invoice number (not date, year, amount, postal code).
    
    Args:
        candidate: Numeric candidate string
        row: Row containing candidate
        all_rows: All rows for context
        
    Returns:
        True if candidate looks like invoice number
    """
    if not candidate or not candidate.isdigit():
        return False
    
    num = int(candidate)
    length = len(candidate)
    
    # Filter out dates (YYYYMMDD = 8 digits, DDMMYYYY = 8 digits)
    if length == 8:
        # Check if could be date
        year = num // 10000
        if 1900 <= year <= 2100:
            return False
    
    # Filter out years (4 digits, 1900-2100)
    if length == 4 and 1900 <= num <= 2100:
        return False
    
    # Filter out amounts (check if row contains currency symbols or decimal patterns)
    row_text = row.text.lower()
    if any(symbol in row_text for symbol in ['kr', 'sek', ':-', '€', '$']):
        # Check if candidate is near decimal pattern
        if re.search(r'\d+[.,]\d{2}', row_text):
            return False
    
    # Filter out postal codes (5 digits, typically 10000-99999 in Sweden)
    if length == 5 and 10000 <= num <= 99999:
        # Check if row contains address keywords
        address_keywords = ['väg', 'gata', 'street', 'road', 'box', 'post', 'postnummer']
        if any(keyword in row_text for keyword in address_keywords):
            return False
    
    # Valid invoice number: 5-12 digits, not filtered out above
    return 5 <= length <= 12


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
    
    # Date patterns (Heuristik 6) - extended with more formats
    date_patterns = [
        (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),  # ISO: YYYY-MM-DD
        (r'(\d{4})\.(\d{2})\.(\d{2})', None),  # YYYY.MM.DD
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', None),  # DD/MM/YYYY or MM/DD/YYYY
        (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', None),  # DD.MM.YYYY
        (r'(\d{1,2})-(\d{1,2})-(\d{4})', None),  # DD-MM-YYYY
        (r'(\d{2})-(\d{2})-(\d{2})', None),  # YY-MM-DD (assume 20YY)
        (r'(\d{2})\.(\d{2})\.(\d{2})', None),  # DD.MM.YY (assume 20YY)
        (r'(\d{2})/(\d{2})/(\d{2})', None),  # DD/MM/YY (assume 20YY)
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
                        if len(groups) == 3:
                            # Check if first group is 4 digits (year) or 2 digits
                            if len(groups[0]) == 4:
                                # YYYY.MM.DD format
                                year = int(groups[0])
                                month = int(groups[1])
                                day = int(groups[2])
                            elif len(groups[2]) == 2:
                                # DD.MM.YY format - assume 20YY
                                day = int(groups[0])
                                month = int(groups[1])
                                year = 2000 + int(groups[2])
                            else:
                                # DD/MM/YYYY format
                                day = int(groups[0])
                                month = int(groups[1])
                                year = int(groups[2])
                            date_obj = date(year, month, day)
                        else:
                            continue
                    
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
    skip_keywords = [
        "faktura", "invoice", "datum", "date", "fakturanummer", "invoice number",
        "sida", "page", "nr:", "betaling", "betalningsreferens", "betalnings referens",
        "betalningsreferens", "lagerplats", "referens", "reference", "sek", "kr"
    ]
    
    # Patterns to skip (metadata patterns) - case insensitive
    skip_patterns = [
        r'sida\s+\d+/\d+',  # "sida 2/2", "Sida 2/2"
        r'^sida\s+\d+/\d+',  # Start with "sida 2/2"
        r'nr:\s*\d+',  # "Nr: xxxxxx"
        r'^nr:\s*\d+',  # Start with "Nr:"
        r'\d{2}-\d{2}-\d{2}',  # Dates like "25-03-11"
        r'\d{4}-\d{2}-\d{2}',  # Dates like "2024-08-22"
        r'\d+\s+\d+\s+\(\d+\)',  # "001002687 1(1)"
        r'\d{5}\s*[A-ZÅÄÖ]+',  # Postcodes like "11798STOCKHOLM"
        r'\d+\s+\d+[.,]\d{2}\s+sek',  # Amounts like "7 517,00 SEK"
        r'^sida\s+\d+/\d+\s*$',  # Only "sida X/Y"
    ]
    
    # Company suffixes
    company_suffixes = ["AB", "Ltd", "Inc", "AB", "Ltd.", "Inc.", "Aktiebolag"]
    
    candidates = []
    
    for row in header_segment.rows[:5]:  # Check first 5 rows (company name usually in top)
        row_lower = row.text.lower()
        row_text = row.text.strip()
        
        # Skip rows with metadata keywords
        if any(keyword in row_lower for keyword in skip_keywords):
            continue
        
        # Skip rows matching metadata patterns (check both full match and start)
        matches_pattern = False
        for pattern in skip_patterns:
            if re.search(pattern, row_text, re.IGNORECASE):
                matches_pattern = True
                break
            # Also check if row starts with pattern (for "Sida 2/2")
            if pattern.startswith('^') and re.match(pattern, row_text, re.IGNORECASE):
                matches_pattern = True
                break
        
        if matches_pattern:
            continue
        
        # Skip very short rows
        if len(row_text) < 3:
            continue
        
        # Skip rows that are mostly numbers/dates/metadata
        # If row contains mostly numbers, dates, or metadata patterns, skip it
        non_alpha_chars = sum(1 for c in row_text if not c.isalpha() and not c.isspace())
        if len(row_text) > 0 and non_alpha_chars / len(row_text) > 0.7:
            continue  # Too many non-alphabetic characters (likely metadata)
        
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


def extract_reference(
    header_segment: Optional[Segment],
    invoice_header: InvoiceHeader
) -> None:
    """Extract reference (fakturareferens/betalningsreferens) from header. REF-01.
    
    Searches for labels like "fakturareferens", "betalningsreferens", "referens", "reference"
    and captures the value on same row or next token.
    """
    if header_segment is None or not header_segment.rows:
        invoice_header.reference = None
        return
    
    label_patterns = [
        r'fakturareferens\s*:?\s*',
        r'betalningsreferens\s*:?\s*',
        r'betalnings\s*referens\s*:?\s*',
        r'referens\s*:?\s*',
        r'reference\s*:?\s*',
    ]
    label_re = re.compile('(?:' + '|'.join(label_patterns) + ')', re.IGNORECASE)
    # Värdet: siffror och eventuellt bokstäver (t.ex. "4061547206" eller "RF 123")
    value_re = re.compile(r'[\d\sA-ZÅÄÖa-zåäö\-]{3,40}')
    
    for row in header_segment.rows:
        norm = _normalize_text(row.text)
        m = label_re.search(norm)
        if not m:
            continue
        after = norm[m.end():].strip()
        val_m = value_re.match(after)
        if val_m:
            ref = val_m.group(0).strip()
            if ref and len(ref) >= 3:
                invoice_header.reference = ref
                return
    
    invoice_header.reference = None


def extract_header_fields(
    header_segment: Optional[Segment],
    invoice_header: InvoiceHeader,
    progress_callback: Optional[Callable[[str, float, int], None]] = None
) -> None:
    """Extract all header fields (invoice number, date, vendor) in one call with retry logic.
    
    Args:
        header_segment: Header segment (or None if not found)
        invoice_header: InvoiceHeader to update with extracted fields
        progress_callback: Optional callback function(status_message, confidence, attempt_num) for progress updates
    """
    from ..pipeline.retry_extraction import extract_with_retry
    
    # Extract invoice number with retry (target: 95% confidence)
    if progress_callback:
        progress_callback("Extraherar fakturanummer...", 0.0, 0)
    
    def extract_inv_num(strategy=None):
        extract_invoice_number(header_segment, invoice_header, strategy=strategy)
        return invoice_header  # Return object with confidence attribute
    
    result, confidence, attempts = extract_with_retry(
        extract_inv_num,
        target_confidence=0.95,
        max_attempts=5,
        progress_callback=progress_callback
    )
    
    # Extract date, vendor, reference (no retry needed, lower priority)
    extract_invoice_date(header_segment, invoice_header)
    extract_vendor_name(header_segment, invoice_header)
    extract_reference(header_segment, invoice_header)

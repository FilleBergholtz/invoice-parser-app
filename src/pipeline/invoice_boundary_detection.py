"""Invoice boundary detection for identifying multiple invoices within a single PDF."""

import re
from typing import List, Optional, Tuple

from ..models.document import Document
from ..models.page import Page
from ..models.row import Row
from ..models.segment import Segment
from ..pipeline.confidence_scoring import score_invoice_number_candidate
from ..pipeline.row_grouping import group_tokens_to_rows
from ..pipeline.segment_identification import identify_segments


def detect_invoice_boundaries(
    doc: Document,
    extraction_path: str,
    verbose: bool = False
) -> List[Tuple[int, int]]:
    """Detect invoice boundaries (page ranges) within a PDF.
    
    Args:
        doc: Document object with all pages loaded
        extraction_path: "pdfplumber" or "ocr"
        verbose: Enable verbose output
        
    Returns:
        List of (page_start, page_end) tuples (1-based, inclusive).
        Each tuple represents one virtual invoice.
        If detection is uncertain, returns [(1, len(doc.pages))] (entire PDF as one invoice).
        
    Boundary Detection Rules (v1):
    - Start: Page with high-confidence invoice number (≥0.95) in header zone
              OR strong "Faktura"-header + invoice number pattern with top score
    - End: Page with high-confidence total (≥0.95) in footer zone, if next page has new header-start
            OR just before next header-start (if new invoice starts without total found)
    - Fail-safe: If uncertain → treat entire PDF as one invoice
    
    Note:
        Requires tokens to be extracted from pages. This function extracts tokens
        for boundary detection only (does not store in page.tokens).
    """
    if not doc.pages:
        return []
    
    # Extract tokens from all pages for boundary detection
    page_segments_map = {}  # page_number -> List[Segment]
    
    import pdfplumber
    pdf = pdfplumber.open(doc.filepath)
    
    try:
        for page in doc.pages:
            if extraction_path == "pdfplumber":
                pdfplumber_page = pdf.pages[page.page_number - 1]
                from ..pipeline.tokenizer import extract_tokens_from_page
                tokens = extract_tokens_from_page(page, pdfplumber_page)
            else:
                # OCR path - skip for now (would require rendering)
                if verbose:
                    print(f"  Warning: OCR path not yet implemented for boundary detection")
                tokens = []
            
            if not tokens:
                continue
            
            # Group tokens to rows
            rows = group_tokens_to_rows(tokens)
            
            # Identify segments
            segments = identify_segments(rows, page)
            page_segments_map[page.page_number] = (segments, rows)
        
        # Detect boundaries based on header/footer patterns
        boundaries = _find_invoice_boundaries(doc, page_segments_map, verbose)
        
        # Fail-safe: If no boundaries found or uncertain, treat entire PDF as one invoice
        if not boundaries:
            if verbose:
                print(f"  Warning: No invoice boundaries detected, treating entire PDF as one invoice")
            return [(1, len(doc.pages))]
        
        return boundaries
        
    finally:
        pdf.close()


def _find_invoice_boundaries(
    doc: Document,
    page_segments_map: dict,  # page_number -> (segments, rows)
    verbose: bool = False
) -> List[Tuple[int, int]]:
    """Find invoice boundaries by analyzing header/footer patterns.
    
    Returns list of (page_start, page_end) tuples.
    """
    boundaries = []
    current_start = 1
    num_pages = len(doc.pages)
    
    for page_num in range(1, num_pages + 1):
        if page_num not in page_segments_map:
            continue
        
        segments, rows = page_segments_map[page_num]
        
        # Check if this page has a strong invoice header (new invoice start)
        header_segment = next((s for s in segments if s.segment_type == "header"), None)
        
        if header_segment and page_num > current_start:
            # Check for high-confidence invoice number (≥0.95) or strong pattern
            has_invoice_header = _has_strong_invoice_header(header_segment, rows, doc.pages[page_num - 1])
            
            if has_invoice_header:
                # This is a new invoice start
                # End previous invoice at page_num - 1
                if current_start <= page_num - 1:
                    # Check if previous page has total
                    prev_segments, prev_rows = page_segments_map.get(page_num - 1, ([], []))
                    footer_segment = next((s for s in prev_segments if s.segment_type == "footer"), None)
                    has_total = _has_high_confidence_total(footer_segment, prev_rows) if footer_segment else False
                    
                    end_page = page_num - 1
                    boundaries.append((current_start, end_page))
                    if verbose:
                        print(f"  Invoice boundary: pages {current_start}-{end_page} (total found: {has_total})")
                
                current_start = page_num
    
    # Handle last invoice
    if current_start <= num_pages:
        boundaries.append((current_start, num_pages))
        if verbose:
            print(f"  Invoice boundary: pages {current_start}-{num_pages} (last invoice)")
    
    return boundaries


def _has_strong_invoice_header(
    header_segment: Segment,
    all_rows: List[Row],
    page: Page
) -> bool:
    """Check if header segment has strong invoice header (high-confidence invoice number).
    
    Returns True if:
    - High-confidence invoice number candidate (≥0.95) found in header zone
    - OR strong "Faktura"-header + invoice number pattern with top score
    """
    if not header_segment.rows:
        return False
    
    # Extract invoice number candidates using same logic as extract_invoice_number
    invoice_pattern = re.compile(
        r'(?:fakturanummer|invoice\s*number|no\.|nr|number)[\s:]*([A-Z0-9\-]+)',
        re.IGNORECASE
    )
    
    candidates = []
    for row in header_segment.rows:
        matches = invoice_pattern.findall(row.text)
        for match in matches:
            if match:
                candidates.append({
                    'candidate': match.strip(),
                    'row': row
                })
    
    # Score candidates and check for high confidence (≥0.95)
    for candidate in candidates[:10]:  # Limit to top 10
        score = score_invoice_number_candidate(
            candidate['candidate'],
            candidate['row'],
            page,
            all_rows
        )
        
        if score >= 0.95:
            return True
    
    # Fallback: Check for strong "Faktura" keyword + alphanumeric pattern
    faktura_pattern = re.compile(r'faktura', re.IGNORECASE)
    for row in header_segment.rows:
        if faktura_pattern.search(row.text):
            # Check for alphanumeric pattern nearby
            alphanumeric_pattern = re.compile(r'([A-Z0-9\-]{3,25})', re.IGNORECASE)
            if alphanumeric_pattern.search(row.text):
                return True  # Strong pattern found
    
    return False


def _has_high_confidence_total(
    footer_segment: Segment,
    all_rows: List[Row]
) -> bool:
    """Check if footer segment has high-confidence total amount (≥0.95).
    
    Simplified check: looks for "Att betala"/"Totalt" keywords + amount pattern.
    Full scoring would require line_items which we don't have during boundary detection.
    """
    if not footer_segment or not footer_segment.rows:
        return False
    
    # Check for total keywords
    total_keywords = ["att betala", "totalt", "total", "summa att betala"]
    
    for row in footer_segment.rows:
        row_lower = row.text.lower()
        for keyword in total_keywords:
            if keyword in row_lower:
                # Check for amount pattern (numbers with SEK/kr or decimal)
                amount_pattern = re.compile(r'\d+(?:[.,]\d{2})?\s*(?:sek|kr|:)?', re.IGNORECASE)
                if amount_pattern.search(row.text):
                    # Strong indication of total (simplified - full scoring requires line_items)
                    return True
    
    return False

"""Invoice boundary detection for identifying multiple invoices within a single PDF."""

import re
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from ..models.document import Document
from ..models.page import Page
from ..models.row import Row
from ..models.segment import Segment
from ..pipeline.confidence_scoring import score_invoice_number_candidate
from ..pipeline.row_grouping import group_tokens_to_rows
from ..pipeline.segment_identification import identify_segments
from ..pipeline.ocr_routing import evaluate_text_layer, get_ocr_routing_config


def _get_pdfplumber_text(
    page_number: int,
    pdfplumber_page: "pdfplumber.page.Page",
    cache: Optional[dict],
    cache_enabled: bool
) -> str:
    """Extract pdfplumber text with optional cache."""
    if cache_enabled and cache is not None and page_number in cache:
        return cache[page_number]
    try:
        text = pdfplumber_page.extract_text() or ""
    except Exception:
        text = ""
    if cache_enabled and cache is not None:
        cache[page_number] = text
    return text


def detect_invoice_boundaries(
    doc: Document,
    extraction_path: str,
    verbose: bool = False,
    output_dir: Optional[str] = None,
) -> List[Tuple[int, int]]:
    """Detect invoice boundaries (page ranges) within a PDF.
    
    Args:
        doc: Document object with all pages loaded
        extraction_path: "pdfplumber" or "ocr"
        verbose: Enable verbose output
        output_dir: Output directory (used for OCR path to store rendered images; if None and ocr, uses temp dir)
        
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
    
    page_segments_map = {}  # page_number -> (segments, rows)
    
    if extraction_path == "pdfplumber":
        import pdfplumber
        pdf = pdfplumber.open(doc.filepath)
        routing_config = get_ocr_routing_config()
        cache_pdf_text = bool(routing_config.get("cache_pdfplumber_text", True))
        text_cache: Optional[dict] = {} if cache_pdf_text else None
        ocr_render_dir: Optional[Path] = None
        try:
            from ..pipeline.tokenizer import extract_tokens_from_page
            from ..pipeline.pdf_renderer import render_page_to_image
            from ..pipeline.ocr_abstraction import extract_tokens_with_ocr, OCRException
            for page in doc.pages:
                pdfplumber_page = pdf.pages[page.page_number - 1]
                page_text = _get_pdfplumber_text(
                    page.page_number,
                    pdfplumber_page,
                    text_cache,
                    cache_pdf_text
                )
                decision = evaluate_text_layer(page_text, [], routing_config)
                if decision["use_text_layer"]:
                    tokens = extract_tokens_from_page(page, pdfplumber_page)
                else:
                    if ocr_render_dir is None:
                        ocr_render_dir = Path(output_dir) / "ocr_render" if output_dir else Path(tempfile.mkdtemp(prefix="ocr_boundary_"))
                        ocr_render_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        render_page_to_image(page, str(ocr_render_dir))
                        tokens = extract_tokens_with_ocr(page)
                    except OCRException as e:
                        if verbose:
                            print(f"  OCR failed for boundary detection page {page.page_number}: {e}")
                        tokens = extract_tokens_from_page(page, pdfplumber_page)
                    except Exception as e:
                        if verbose:
                            print(f"  Render/OCR failed for boundary detection page {page.page_number}: {e}")
                        tokens = extract_tokens_from_page(page, pdfplumber_page)
                if not tokens:
                    continue
                rows = group_tokens_to_rows(tokens)
                segments = identify_segments(rows, page)
                page_segments_map[page.page_number] = (segments, rows)
        finally:
            pdf.close()
    else:
        # OCR path: render each page, then OCR
        from ..pipeline.pdf_renderer import render_page_to_image
        from ..pipeline.ocr_abstraction import extract_tokens_with_ocr, OCRException
        ocr_render_dir = Path(output_dir) / "ocr_render" if output_dir else Path(tempfile.mkdtemp(prefix="ocr_boundary_"))
        ocr_render_dir.mkdir(parents=True, exist_ok=True)
        for page in doc.pages:
            try:
                render_page_to_image(page, str(ocr_render_dir))
                tokens = extract_tokens_with_ocr(page)
            except OCRException as e:
                if verbose:
                    print(f"  OCR failed for boundary detection page {page.page_number}: {e}")
                continue
            except Exception as e:
                if verbose:
                    print(f"  Render/OCR failed for boundary detection page {page.page_number}: {e}")
                continue
            if not tokens:
                continue
            rows = group_tokens_to_rows(tokens)
            segments = identify_segments(rows, page)
            page_segments_map[page.page_number] = (segments, rows)
    
    boundaries = _find_invoice_boundaries(doc, page_segments_map, verbose)
    if not boundaries:
        if verbose:
            print(f"  Warning: No invoice boundaries detected, treating entire PDF as one invoice")
        return [(1, len(doc.pages))]
    return boundaries


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
    best_candidate_score = 0.0
    for candidate in candidates[:10]:  # Limit to top 10
        score = score_invoice_number_candidate(
            candidate['candidate'],
            candidate['row'],
            page,
            all_rows
        )
        best_candidate_score = max(best_candidate_score, score)
        if score >= 0.95:
            return True
    
    # Fallback: "Faktura" + alphanumeric is NOT sufficient alone (15-DISCUSS D5).
    # Require additional signal: label match (we have candidates and score), strong candidate score (≥0.6),
    # or date/amount on same row.
    faktura_pattern = re.compile(r'faktura', re.IGNORECASE)
    alphanumeric_pattern = re.compile(r'[A-Z0-9\-]{3,25}', re.IGNORECASE)
    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}|\d{1,2}[./\-]\d{1,2}[./\-]\d{4}')
    amount_pattern = re.compile(r'\d+(?:[.,]\d{2})?(?:\s*(?:sek|kr|:-)?)', re.IGNORECASE)
    for row in header_segment.rows:
        if not (faktura_pattern.search(row.text) and alphanumeric_pattern.search(row.text)):
            continue
        # Additional signal: strong candidate score (≥0.6) or date/amount on row
        if best_candidate_score >= 0.6:
            return True
        if date_pattern.search(row.text) or amount_pattern.search(row.text):
            return True
    
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


def _select_invoice_number_candidate(
    rows: List[Row],
    page: Page,
    header_segment: Optional[Segment]
) -> Optional[Dict[str, Any]]:
    """Select highest confidence invoice number candidate for a page."""
    if not rows:
        return None
    
    label_patterns = [
        r"fakturanummer",
        r"fakturanr",
        r"faktura\s*nr",
        r"fakt\.?\s*nr",
        r"faktnr",
        r"invoice\s*number",
        r"invoice\s*no",
        r"inv\s*no",
        r"inv#",
    ]
    label_re = re.compile(r"(?:%s)" % "|".join(label_patterns), re.IGNORECASE)
    candidate_re = re.compile(r"\b([A-Z0-9][A-Z0-9\-]{3,19})\b", re.IGNORECASE)
    
    candidates: List[Dict[str, Any]] = []
    header_rows = set(header_segment.rows) if header_segment and header_segment.rows else set()
    
    for idx, row in enumerate(rows):
        if not label_re.search(row.text):
            continue
        row_text = row.text
        label_match = label_re.search(row_text)
        candidate = None
        if label_match:
            after = row_text[label_match.end():]
            match = candidate_re.search(after)
            if match:
                candidate = match.group(1)
        
        if candidate is None:
            # If label-only row, check next row for candidate
            if idx + 1 < len(rows):
                next_row = rows[idx + 1]
                match = candidate_re.search(next_row.text)
                if match:
                    candidate = match.group(1)
                    row = next_row
        
        if not candidate:
            continue
        
        if not _validate_boundary_invoice_number(candidate):
            continue
        
        score = score_invoice_number_candidate(candidate, row, page, rows)
        if row in header_rows:
            score = min(1.0, score + 0.10)
        if row.y < 0.5 * page.height:
            score = min(1.0, score + 0.05)
        
        candidates.append({
            "candidate": candidate.strip(),
            "row": row,
            "score": score
        })
    
    if not candidates:
        return None
    
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[0]


def _validate_boundary_invoice_number(candidate: str) -> bool:
    """Validate candidate format for boundary detection (4-20 alphanumeric, hyphen allowed)."""
    if not candidate:
        return False
    if not (4 <= len(candidate) <= 20):
        return False
    return bool(re.fullmatch(r"[A-Z0-9\-]+", candidate, re.IGNORECASE))


def _parse_page_number(rows: List[Row]) -> Optional[Dict[str, Any]]:
    """Parse page numbering like 'Sida 1/2', 'Sida 2 av 3', 'Page 1/2', or '1/2'."""
    if not rows:
        return None
    
    label_re = re.compile(r"\b(?:sida|page)\s*(\d{1,3})\s*(?:/|av)\s*(\d{1,3})\b", re.IGNORECASE)
    fraction_re = re.compile(r"\b(\d{1,3})\s*/\s*(\d{1,3})\b")
    
    for row in rows:
        m = label_re.search(row.text)
        if m:
            current = int(m.group(1))
            total = int(m.group(2))
            if current >= 1 and total >= 1 and current <= total:
                return {
                    "current": current,
                    "total": total,
                    "raw": m.group(0),
                    "source": "label",
                    "row_text": row.text
                }
        m = fraction_re.search(row.text)
        if m:
            current = int(m.group(1))
            total = int(m.group(2))
            if current >= 1 and total >= 1 and current <= total:
                return {
                    "current": current,
                    "total": total,
                    "raw": m.group(0),
                    "source": "fraction",
                    "row_text": row.text
                }
    return None


def _is_page_number_sequential(prev_info: Dict[str, Any], current_info: Dict[str, Any]) -> bool:
    """Check if page numbering is sequential without jumps."""
    prev_current = prev_info.get("current")
    prev_total = prev_info.get("total")
    current_current = current_info.get("current")
    current_total = current_info.get("total")
    if not isinstance(prev_current, int) or not isinstance(current_current, int):
        return False
    if prev_current + 1 != current_current:
        return False
    if prev_total and current_total and prev_total != current_total:
        return False
    return True

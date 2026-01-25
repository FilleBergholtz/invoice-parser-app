"""Footer extraction for total amount with confidence scoring."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import (
    get_calibration_enabled,
    get_calibration_model_path,
    get_learning_enabled,
    get_learning_db_path,
    get_ai_enabled,
    get_ai_key,
)
from ..models.invoice_header import InvoiceHeader
from ..models.invoice_line import InvoiceLine
from ..models.row import Row
from ..models.segment import Segment
from ..models.traceability import Traceability
from ..pipeline.confidence_calibration import CalibrationModel, calibrate_confidence
from ..pipeline.confidence_scoring import score_total_amount_candidate, validate_total_against_line_items

logger = logging.getLogger(__name__)

# Cache for loaded calibration model (load once, reuse)
_calibration_model_cache: Optional[CalibrationModel] = None
_calibration_model_path: Optional[Path] = None

# Cache for learning database (load once, reuse)
_learning_database_cache = None
_learning_db_path: Optional[Path] = None


def _load_calibration_model() -> Optional[CalibrationModel]:
    """Load calibration model from file (with caching).
    
    Returns:
        CalibrationModel if found and valid, None otherwise
    """
    global _calibration_model_cache, _calibration_model_path
    
    # Check if calibration is enabled
    if not get_calibration_enabled():
        return None
    
    model_path = get_calibration_model_path()
    
    # Check cache first
    if _calibration_model_cache is not None and _calibration_model_path == model_path:
        return _calibration_model_cache
    
    # Try to load model
    model = CalibrationModel.load(model_path)
    
    if model is None:
        # Only log warning once (not for every invoice)
        if _calibration_model_cache is None:
            logger.debug(
                f"Calibration model not found at {model_path}. "
                "Using raw confidence scores (no calibration)."
            )
        return None
    
    # Cache the model
    _calibration_model_cache = model
    _calibration_model_path = model_path
    logger.debug(f"Loaded calibration model from {model_path}")
    
    return model


def _load_learning_database():
    """Load learning database (with caching).
    
    Returns:
        LearningDatabase instance if learning enabled, None otherwise
    """
    global _learning_database_cache, _learning_db_path
    
    if not get_learning_enabled():
        return None
    
    db_path = get_learning_db_path()
    
    # Check if cache is still valid
    if (_learning_database_cache is not None and 
        _learning_db_path == db_path):
        return _learning_database_cache
    
    # Try to load database
    try:
        from ..learning.database import LearningDatabase
        _learning_database_cache = LearningDatabase(db_path)
        _learning_db_path = db_path
        logger.debug(f"Loaded learning database from {db_path}")
    except Exception as e:
        logger.warning(f"Failed to load learning database: {e}")
        _learning_database_cache = None
    
    return _learning_database_cache


def _try_ai_fallback(
    footer_segment: Segment,
    line_items: List[InvoiceLine],
    invoice_header: InvoiceHeader,
    candidates: Optional[List[Dict[str, Any]]] = None,
    page_context: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Try AI fallback for total amount extraction.
    
    Args:
        footer_segment: Footer segment with text
        line_items: Line items for validation
        invoice_header: InvoiceHeader for context
        candidates: Optional heuristic candidates (amount, keyword_type).
        page_context: Full page text (header/items/footer) so AI sees PDF hela data.
        
    Returns:
        AI result dict with total_amount, confidence, reasoning, validation_passed, or None if fails
    """
    try:
        from ..ai.fallback import extract_total_with_ai
        
        footer_text = getattr(footer_segment, "raw_text", None) or " ".join(
            row.text for row in footer_segment.rows
        )
        line_items_sum = sum(line.total_amount for line in line_items) if line_items else None
        cand = None
        if candidates:
            cand = [{"amount": c.get("amount"), "keyword_type": c.get("keyword_type")} for c in candidates[:10]]
        ai_result = extract_total_with_ai(
            footer_text, line_items_sum, candidates=cand, page_context=page_context
        )
        
        if ai_result:
            logger.debug(
                f"AI extracted total: {ai_result.get('total_amount')}, "
                f"confidence: {ai_result.get('confidence'):.2f}"
            )
        
        return ai_result
        
    except Exception as e:
        logger.warning(f"AI fallback failed: {e}")
        return None


def _apply_pattern_boosts(
    scored_candidates: List[dict],
    invoice_header: InvoiceHeader
) -> None:
    """Apply pattern matching boosts to candidate scores.
    
    Args:
        scored_candidates: List of candidate dicts with scores
        invoice_header: InvoiceHeader with supplier and traceability info
    """
    database = _load_learning_database()
    if not database:
        return
    
    try:
        from ..learning.pattern_matcher import PatternMatcher
        from ..learning.pattern_extractor import PatternExtractor
        
        # Use "Unknown" when supplier missing so we match patterns from corrections (often stored as unknown)
        supplier_raw = (invoice_header.supplier_name or "").strip() or "Unknown"
        supplier_for_matching = PatternExtractor.normalize_supplier(supplier_raw)
        
        # Calculate layout hash
        layout_hash = PatternExtractor.calculate_layout_hash(supplier_for_matching)
        
        # Get position from traceability if available
        position = None
        if invoice_header.total_traceability:
            bbox = invoice_header.total_traceability.evidence.get('bbox')
            if bbox and len(bbox) == 4:
                position = {
                    'x': bbox[0],
                    'y': bbox[1],
                    'width': bbox[2],
                    'height': bbox[3]
                }
        
        # Match patterns
        matcher = PatternMatcher(database)
        matched_patterns = matcher.match_patterns(
            supplier_for_matching,
            layout_hash=layout_hash,
            position=position,
            similarity_threshold=0.5
        )
        
        if not matched_patterns:
            logger.debug(f"No patterns matched for supplier {supplier_for_matching}")
            return
        
        # Apply boost to candidates that match patterns
        # For now, boost all candidates if any pattern matches (simplified)
        # Future: Can match specific candidates to patterns based on amount
        best_pattern = matched_patterns[0]  # Highest similarity
        boost = best_pattern.get('confidence_boost', 0.1)
        
        # Apply boost to all candidates (they all benefit from pattern match)
        for candidate in scored_candidates:
            candidate['score'] = min(1.0, candidate['score'] + boost)
        
        # Update pattern usage
        pattern_id = best_pattern.get('id')
        if pattern_id:
            database.update_pattern_usage(pattern_id)
        
        logger.debug(
            f"Applied pattern boost {boost:.2f} to candidates "
            f"(pattern similarity: {best_pattern.get('similarity', 0):.2f})"
        )
        
    except Exception as e:
        logger.warning(f"Failed to apply pattern boosts: {e}")
        # Continue without boost - don't break extraction


def _build_ui_candidates(scored: List[Dict], max_count: int = 10) -> List[Dict]:
    """Build UI candidate list: ai_extracted first (so user can always choose AI), then with_vat, then rest; use raw_score for display."""
    ai_extracted = [c for c in scored if c.get('keyword_type') == 'ai_extracted']
    with_vat = [c for c in scored if c.get('keyword_type') == 'with_vat']
    rest = [c for c in scored if c.get('keyword_type') not in ('ai_extracted', 'with_vat')]
    seen: set = set()
    out: List[Dict] = []
    for c in ai_extracted + with_vat + rest:
        if len(out) >= max_count:
            break
        a = c['amount']
        key = round(a, 2)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            'amount': c['amount'],
            'score': c.get('raw_score', c['score']),
            'row_index': c['row_index'],
            'keyword_type': c.get('keyword_type'),
        })
    return out


def extract_total_amount(
    footer_segment: Optional[Segment],
    line_items: List[InvoiceLine],
    invoice_header: InvoiceHeader,
    strategy: Optional[str] = None,
    rows_above_footer: Optional[List[Row]] = None,
    page_context_for_ai: Optional[str] = None,
) -> None:
    """Extract total amount from footer segment using keyword matching and confidence scoring.
    
    Args:
        footer_segment: Footer segment (or None if not found)
        line_items: List of InvoiceLine objects for mathematical validation
        invoice_header: InvoiceHeader to update with extracted total amount
        rows_above_footer: Optional rows immediately above footer (e.g. last items rows).
            If the first footer row has amounts but no keywords, we check the last row
            here for labels like "Att betala: SEK" / "Nettobelopp" (footer threshold can
            put labels in items and amounts in footer).
        page_context_for_ai: Full page text (header/items/footer) for AI so it sees
            PDF:ens hela data; används vid AI-fallback när kandidater kan vara fel.
        
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
        r"Totalsumma\s+SEK",
        r"nettobelopp",
        r"nettobeloppet",
        r"Nettobelopp",
    ]
    
    # Combined patterns for keyword detection
    keyword_patterns = total_with_vat_patterns + total_without_vat_patterns + generic_total_patterns
    
    # Keyword type from rows immediately above footer (rubrikerna ovanför ramen)
    # If labels like "Att betala: SEK" / "Nettobelopp" sit in items (just above 70%) and
    # amounts in footer, we use the last row above for keyword_type when first footer row
    # has amounts only.
    keyword_type_above: Optional[str] = None
    if rows_above_footer:
        for r in reversed(rows_above_footer):
            t = r.text.lower()
            if any(re.search(p, t, re.IGNORECASE) for p in total_with_vat_patterns):
                keyword_type_above = "with_vat"
                break
            if any(re.search(p, t, re.IGNORECASE) for p in total_without_vat_patterns):
                keyword_type_above = "without_vat"
                break
            if any(re.search(p, t, re.IGNORECASE) for p in generic_total_patterns):
                keyword_type_above = "generic"
                break
    
    # Improved amount pattern. Dot-thousands FIRST (require at least one .XXX) so "2.973,88"
    # matches whole. Then dot-decimal so "743.47" matches whole.
    amount_pattern = re.compile(
        r'\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|'      # Swedish dot thousands: "2.973,88", "3.717,35"
        r'\d+\.\d{1,2}(?!\d)|'                     # Dot decimal only: "743.47", "8302.00"
        r'\d{1,3}(?:\s+\d{3})*(?:[.,]\d{1,2})?|'  # Space thousands: "1 234,56"
        r'\d+(?:,\d{1,2})?'                        # Comma decimal: "123,45"
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
        amount_matches = list(amount_pattern.finditer(row_text))
        use_row, use_idx = row, row_index
        # If keyword row has no amount, check next row (e.g. "Nettobelopp" label, amount below)
        if has_keyword and not amount_matches and row_index + 1 < len(footer_segment.rows):
            next_row = footer_segment.rows[row_index + 1]
            amount_matches = list(amount_pattern.finditer(next_row.text))
            use_row, use_idx = next_row, row_index + 1
        
        # Use keyword from row above footer when first footer row has amounts only (labels in items)
        use_keyword_type = keyword_type
        if not has_keyword and amount_matches and row_index == 0 and keyword_type_above is not None:
            use_keyword_type = keyword_type_above
        
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
                    for token in use_row.tokens:
                        token_end = char_pos + len(token.text)
                        if match_start >= char_pos and match_end <= token_end:
                            matching_token = token
                            break
                        char_pos = token_end + 1  # +1 for space between tokens
                    
                    candidates.append({
                        'amount': amount,
                        'row': use_row,
                        'row_index': use_idx,
                        'token': matching_token or (use_row.tokens[0] if use_row.tokens else None),
                        'has_keyword': has_keyword or (use_keyword_type is not None),
                        'keyword_type': use_keyword_type,
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
            row_lower = candidate['row'].text.lower()
            has_label = any(
                k in row_lower for k in
                ("att betala", "attbetala", "inkl. moms", "inklusive moms", "betalas", "slutsumma")
            )
            # When amount is on next row (label above), row has no keyword → full keyword compensation
            if not has_label:
                boost = 0.32
            elif strategy == 'aggressive':
                boost = 0.20
            elif strategy == 'conservative':
                boost = 0.10
            else:
                boost = 0.15
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
            'score': score,
            'raw_score': score,
        })
    
    # Sort by score descending, then by keyword_type priority
    def sort_key(c):
        type_priority = {'with_vat': 3, 'generic': 2, 'without_vat': 1, None: 0}
        return (c['score'], type_priority.get(c.get('keyword_type'), 0))
    
    scored_candidates.sort(key=sort_key, reverse=True)
    
    # Step 3: Apply pattern matching boost (if learning enabled)
    if get_learning_enabled():
        _apply_pattern_boosts(scored_candidates, invoice_header)
        for c in scored_candidates:
            c['raw_score'] = c['score']
        scored_candidates.sort(key=sort_key, reverse=True)
    
    # Step 4: Apply calibration to all candidate scores (if model exists)
    calibration_model = _load_calibration_model()
    if calibration_model:
        for candidate in scored_candidates:
            candidate['score'] = calibrate_confidence(candidate['score'], calibration_model)
        scored_candidates.sort(key=sort_key, reverse=True)
    
    # Step 5: Build UI candidate list (max 10). Always include all with_vat first, then fill by score.
    # Store raw_score for display (calibration can zero out, making % useless).
    invoice_header.total_candidates = _build_ui_candidates(scored_candidates, 10) or None
    
    # Step 5: Try AI fallback when confidence low or no candidates
    ai_result = None
    if get_ai_enabled():
        if not get_ai_key():
            logger.info("AI fallback skipped: no API key configured")
        elif scored_candidates:
            top_heuristic_score = scored_candidates[0]['score']
            if top_heuristic_score >= 0.95:
                logger.info("AI fallback skipped: confidence >= 0.95")
            else:
                ai_result = _try_ai_fallback(
                    footer_segment, line_items, invoice_header,
                    candidates=scored_candidates[:10],
                    page_context=page_context_for_ai,
                )
                if ai_result:
                    ai_confidence = ai_result.get('confidence', 0.0)
                    validation_passed = ai_result.get('validation_passed', False)
                    use_ai = (
                        ai_confidence > top_heuristic_score or
                        (validation_passed and abs(ai_confidence - top_heuristic_score) <= 0.05)
                    )
                    if use_ai:
                        logger.info(
                            f"AI fallback succeeded: confidence {ai_confidence:.2f} "
                            f"(heuristic: {top_heuristic_score:.2f}), "
                            f"validation: {'passed' if validation_passed else 'failed'}"
                        )
                        ai_candidate = {
                            'amount': ai_result['total_amount'],
                            'score': ai_confidence,
                            'raw_score': ai_confidence,
                            'row_index': -1,
                            'keyword_type': 'ai_extracted',
                            'row': None,
                        }
                        scored_candidates.insert(0, ai_candidate)
                        scored_candidates.sort(key=sort_key, reverse=True)
                        invoice_header.total_candidates = _build_ui_candidates(scored_candidates, 10) or None
                    else:
                        logger.debug(
                            f"AI result not used: confidence {ai_confidence:.2f} <= "
                            f"heuristic {top_heuristic_score:.2f}, validation: {validation_passed}"
                        )
                else:
                    logger.info("AI fallback skipped: no result (extraction failed or invalid response)")
        else:
            ai_result = _try_ai_fallback(
                footer_segment, line_items, invoice_header,
                candidates=None,
                page_context=page_context_for_ai,
            )
            if ai_result:
                logger.info("AI fallback used: no heuristic candidates, AI extracted total")
                ai_candidate = {
                    'amount': ai_result['total_amount'],
                    'score': ai_result.get('confidence', 0.0),
                    'raw_score': ai_result.get('confidence', 0.0),
                    'row_index': -1,
                    'keyword_type': 'ai_extracted',
                    'row': None,
                }
                scored_candidates = [ai_candidate]
                invoice_header.total_candidates = _build_ui_candidates(scored_candidates, 10) or None
            else:
                logger.info("AI fallback skipped: no candidates and AI extraction failed")
    else:
        logger.info("AI fallback skipped: AI not enabled")
    
    # Step 6: Select final value
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
    # 4. Prefer AI over low-scoring heuristics: we used fallback for a reason
    if len(scored_candidates) > 1:
        with_vat_candidates = [c for c in scored_candidates if c.get('keyword_type') == 'with_vat']
        if with_vat_candidates:
            validated_with_vat = [
                c for c in with_vat_candidates
                if validate_total_against_line_items(c['amount'], line_items, tolerance=1.0)
            ]
            if validated_with_vat:
                top_candidate = validated_with_vat[0]
            else:
                top_candidate = with_vat_candidates[0]
        else:
            validated_candidates = [
                c for c in scored_candidates
                if validate_total_against_line_items(c['amount'], line_items, tolerance=1.0)
            ]
            if validated_candidates:
                top_candidate = validated_candidates[0]
        ai_cand = next((c for c in scored_candidates if c.get('keyword_type') == 'ai_extracted'), None)
        if ai_cand and ai_cand.get('score', 0) >= 0.90 and top_candidate.get('score', 0) < 0.50:
            top_candidate = ai_cand
    
    final_amount = top_candidate['amount']
    final_score = top_candidate['score']
    final_row = top_candidate['row']
    
    # Step 4: Create traceability evidence
    page_number = footer_segment.page.page_number
    if final_row is not None:
        if final_row.tokens:
            x_coords = [t.x for t in final_row.tokens]
            y_coords = [t.y for t in final_row.tokens]
            x_max_coords = [t.x + t.width for t in final_row.tokens]
            y_max_coords = [t.y + t.height for t in final_row.tokens]
            bbox = [
                min(x_coords),
                min(y_coords),
                max(x_max_coords) - min(x_coords),
                max(y_max_coords) - min(y_coords)
            ]
        else:
            bbox = [final_row.x_min, final_row.y, final_row.x_max - final_row.x_min, 12.0]
        text_excerpt = final_row.text[:120] if len(final_row.text) > 120 else final_row.text
        tokens = []
        for token in final_row.tokens:
            tokens.append({
                "text": token.text,
                "bbox": [token.x, token.y, token.width, token.height],
                "conf": 1.0
            })
    else:
        bbox = [0.0, 0.0, 0.0, 0.0]
        text_excerpt = f"AI-extracted total: {final_amount}"
        tokens = []
    
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
    
    # Step 8: Update InvoiceHeader
    invoice_header.total_amount = final_amount
    invoice_header.total_confidence = final_score
    invoice_header.total_traceability = traceability
    # total_candidates already set in Step 3

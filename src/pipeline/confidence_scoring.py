"""Multi-factor confidence scoring algorithms for field extraction."""

import re
from decimal import Decimal
from typing import List, Optional, Tuple

from ..models.invoice_line import InvoiceLine
from ..models.page import Page
from ..models.row import Row
from ..models.token import Token
from ..pipeline.number_normalizer import normalize_swedish_decimal

# Amount pattern. Dot-thousands FIRST (require .XXX); then dot-decimal.
_AMOUNT_PATTERN = re.compile(
    r'\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|'      # Swedish dot thousands: "2.973,88", "3.717,35"
    r'\d+\.\d{1,2}(?!\d)|'                     # Dot decimal only: "743.47", "8302.00"
    r'\d{1,3}(?:\s+\d{3})*(?:[.,]\d{1,2})?|'  # Space thousands: "1 234,56"
    r'\d+(?:,\d{1,2})?'                        # Comma decimal: "123,45"
)


def _to_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))

def _parse_amount_str(s: str) -> Optional[float]:
    """Parse amount string to float. Handles dot thousands (3.717,35), space thousands (1 234,56), dot decimal (743.47)."""
    try:
        value = normalize_swedish_decimal(s.strip())
        return float(value) if value > 0 else None
    except ValueError:
        return None


def score_total_amount_candidate(
    candidate: float,
    row: Row,
    page: Page,
    line_items: List[InvoiceLine],
    footer_rows: List[Row]
) -> float:
    """Score total amount candidate using multi-factor weighted scoring.
    
    Args:
        candidate: Candidate total amount value
        row: Row containing the candidate
        page: Page reference for position calculation
        line_items: List of InvoiceLine objects for mathematical validation
        footer_rows: List of rows in footer segment for relative size comparison
        
    Returns:
        Confidence score (0.0-1.0)
        
    Score components (sums to 1.0):
    - Keyword match (0.32 weight): "Att betala" strongest, "Total/Totalt" next
    - Position (0.18 weight): Footer zone + right-aligned
    - Mathematical validation (0.32 weight): If subtotal + VAT + rounding ≈ total → full score
    - Relative size (0.08 weight): Total should be largest amount in summation rows
    - Font size/weight (0.05 weight): Larger/bolder font increases confidence
    - VAT proximity (0.05 weight): Near VAT breakdown rows increases confidence
    - Currency symbol (0.03 weight): SEK/kr/:- symbols increase confidence
    - Row isolation (0.02 weight): Isolated row or in box increases confidence
    """
    score = 0.0
    
    # Keyword match (0.32 weight, reduced from 0.35)
    # Prioritize "with VAT" keywords (what customer actually pays)
    # Check in order of priority (most specific first)
    row_lower = row.text.lower()
    
    # Highest priority: "att betala" / "inkl. moms" (total WITH VAT)
    high_priority_keywords = [
        "att betala", "attbetala", "att betala sek", "attbetala sek",
        "summa att betala", "summa attbetala", "summa att betala sek",
        "belopp att betala", "belopp attbetala", "belopp att betala sek",
        "betalningsbelopp", "betalningsbeloppet", "betalningsbelopp sek",
        "totalt inkl. moms", "total inkl. moms", "totalt inklusive moms",
        "total inklusive moms", "totalt inkl moms", "total inkl moms",
        "inkl. moms", "inklusive moms", "inkl moms",
        "totalt med moms", "total med moms", "med moms",
        "totalt moms inkluderad", "total moms inkluderad",
        "betalas", "betalas sek", "belopp betalas",
        "slutsumma inkl. moms", "netto att betala", "netto betalas"
    ]
    
    # Medium priority: generic totals
    medium_priority_keywords = [
        "totalt", "total", "summa", "belopp", "slutsumma",
        "fakturabelopp", "fakturabeloppet",
        "nettobelopp", "nettobeloppet",
    ]
    
    # Lower priority: "exkl. moms" (subtotal, not final total)
    low_priority_keywords = [
        "totalt exkl. moms", "total exkl. moms", "totalt exklusive moms",
        "total exklusive moms", "totalt exkl moms", "total exkl moms",
        "exkl. moms", "exklusive moms", "exkl moms",
        "totalt utan moms", "total utan moms", "utan moms",
        "delsumma", "subtotal", "summa exkl. moms", "summa exklusive moms",
        "momsfri summa", "momsfritt belopp", "netto exkl. moms"
    ]
    
    # Check in priority order (don't return early - need to continue scoring)
    keyword_found = False
    for keyword in high_priority_keywords:
        if keyword in row_lower:
            score += 0.32  # Reduced from 0.35
            keyword_found = True
            break
    
    if not keyword_found:
        for keyword in medium_priority_keywords:
            if keyword in row_lower:
                score += 0.28  # Reduced from 0.30
                keyword_found = True
                break
    
    if not keyword_found:
        for keyword in low_priority_keywords:
            if keyword in row_lower:
                score += 0.18  # Reduced from 0.20
                break
    
    # Position (0.18 weight, reduced from 0.20)
    # Footer zone is typically bottom 20-30% of page
    if row.y > 0.7 * page.height:  # Bottom 30% of page
        score += 0.18
    elif row.y > 0.6 * page.height:  # Bottom 40% of page (still likely footer)
        score += 0.13  # Partial score (reduced proportionally)
    
    # Mathematical validation (0.32 weight, reduced from 0.35)
    if validate_total_against_line_items(candidate, line_items, tolerance=1.0):
        score += 0.32  # Perfect match - full score
    elif line_items:
        # Partial scoring based on how close the match is
        lines_sum = sum(line.total_amount for line in line_items)
        diff = abs(candidate - lines_sum)
        
        # Use percentage-based thresholds for larger amounts
        if candidate > 1000:
            # For larger amounts, VAT/shipping can cause larger absolute differences
            percentage_diff = (diff / candidate) * 100
            if percentage_diff <= 0.5:  # Within 0.5% - very likely correct (VAT/rounding)
                score += 0.30  # Very high partial score (almost full)
            elif percentage_diff <= 1.0:  # Within 1% - likely VAT/shipping
                score += 0.26  # High partial score
            elif percentage_diff <= 2.0:  # Within 2% - likely VAT/shipping
                score += 0.20  # Medium-high partial score
            elif percentage_diff <= 5.0:  # Within 5% - might be VAT/shipping
                score += 0.14  # Medium partial score
            elif percentage_diff <= 10.0:  # Within 10% - questionable
                score += 0.07  # Low partial score
            else:
                score += 0.03  # Very low partial score - likely wrong
        else:
            # For smaller amounts, use fixed thresholds
            if diff <= 2.0:  # Within 2 SEK - very likely correct with small rounding
                score += 0.28  # Very high partial score
            elif diff <= 5.0:  # Within 5 SEK - likely correct with small rounding/VAT differences
                score += 0.23  # High partial score
            elif diff <= 20.0:  # Within 20 SEK - might be VAT or shipping
                score += 0.16  # Medium partial score
            elif diff <= 50.0:  # Within 50 SEK - questionable
                score += 0.09  # Low-medium partial score
            else:
                score += 0.05  # Low partial score - likely wrong
    
    # Relative size (0.08 weight, reduced from 0.10)
    if footer_rows:
        amounts_in_footer = []
        for footer_row in footer_rows:
            for m in _AMOUNT_PATTERN.finditer(footer_row.text):
                v = _parse_amount_str(m.group(0))
                if v is not None:
                    amounts_in_footer.append(v)
        
        if amounts_in_footer:
            max_amount = max(amounts_in_footer)
            if candidate >= max_amount * 0.98:  # Candidate is largest or very close to largest
                score += 0.08  # Full score (reduced from 0.10)
            elif candidate >= max_amount * 0.90:  # Candidate is close to largest
                score += 0.05  # Partial score (reduced proportionally)
    
    # Font size/weight signal (0.05 weight) - NEW
    if row.tokens:
        # Calculate average font size for candidate row
        candidate_font_sizes = [t.font_size for t in row.tokens if t.font_size is not None]
        if candidate_font_sizes:
            avg_candidate_font = sum(candidate_font_sizes) / len(candidate_font_sizes)
            # Calculate average font size for all footer rows
            all_footer_font_sizes = []
            for footer_row in footer_rows:
                if footer_row.tokens:
                    footer_font_sizes = [t.font_size for t in footer_row.tokens if t.font_size is not None]
                    if footer_font_sizes:
                        all_footer_font_sizes.extend(footer_font_sizes)
            
            if all_footer_font_sizes:
                avg_footer_font = sum(all_footer_font_sizes) / len(all_footer_font_sizes)
                if avg_candidate_font > avg_footer_font * 1.1:  # 10% larger
                    score += 0.05  # Larger font - full score
                elif avg_candidate_font > avg_footer_font * 0.95:  # Similar size
                    score += 0.02  # Average font - partial score
                # Smaller font gets 0.0
    
    # VAT proximity signal (0.05 weight) - NEW
    # Check if candidate row is within 2-3 rows of VAT amount (look for "moms" keywords)
    row_index = None
    for idx, footer_row in enumerate(footer_rows):
        if footer_row == row:
            row_index = idx
            break
    
    if row_index is not None:
        # Look for VAT keywords in nearby rows
        moms_keywords = ['moms', 'vat', 'mervärdesskatt']
        for offset in [-2, -1, 1, 2]:  # Check 2 rows before and after
            check_idx = row_index + offset
            if 0 <= check_idx < len(footer_rows):
                check_row = footer_rows[check_idx]
                check_row_lower = check_row.text.lower()
                if any(keyword in check_row_lower for keyword in moms_keywords):
                    if abs(offset) <= 1:  # Within 1 row (2 rows total)
                        score += 0.05  # Full score
                    elif abs(offset) == 2:  # Within 2 rows (3 rows total)
                        score += 0.03  # Partial score
                    break
    
    # Currency symbol signal (0.03 weight) - NEW
    currency_symbols = ['sek', 'kr', ':-', '€', '$']
    row_lower = row.text.lower()
    if any(symbol in row_lower for symbol in currency_symbols):
        score += 0.03  # Currency symbol present
    
    # Row isolation signal (0.02 weight) - NEW
    # Check if row is separated by blank lines or in visual box
    # Simple heuristic: check if row has significant vertical spacing from adjacent rows
    if row_index is not None and len(footer_rows) > 1:
        # Check spacing to previous row
        if row_index > 0:
            prev_row = footer_rows[row_index - 1]
            spacing = row.y - (prev_row.y + max((t.height for t in prev_row.tokens), default=12.0))
            # If spacing is > 1.5x average row height, consider isolated
            if spacing > 18.0:  # Rough threshold (1.5x typical row height)
                score += 0.02  # Isolated row
        # Check spacing to next row
        if row_index < len(footer_rows) - 1:
            next_row = footer_rows[row_index + 1]
            spacing = next_row.y - (row.y + max((t.height for t in row.tokens), default=12.0))
            if spacing > 18.0:  # Rough threshold
                score += 0.02  # Isolated row (only add once, so this is fine)
    
    return min(score, 1.0)  # Normalize to 0.0-1.0


def validate_total_against_line_items(
    total: float,
    line_items: List[InvoiceLine],
    tolerance: float = 1.0
) -> bool:
    """Validate total amount against sum of line item totals.
    
    Args:
        total: Extracted total amount
        line_items: List of InvoiceLine objects
        tolerance: Tolerance in SEK (default 1.0 for rounding/shipping/discounts)
        
    Returns:
        True if total matches line items sum within tolerance, False otherwise
        
    Formula: lines_sum = SUM(all line item totals), diff = |total - lines_sum|
    Validation passes if diff <= tolerance.
    
    Note: Many invoices have VAT, shipping, or other fees not included in line items.
    For larger amounts, use percentage-based tolerance (e.g., 0.5% of total).
    """
    if not line_items or total is None:
        return False  # Cannot validate without line items

    total_decimal = _to_decimal(total)
    if total_decimal is None:
        return False

    lines_sum = sum((_to_decimal(line.total_amount) or Decimal("0")) for line in line_items)
    diff = abs(total_decimal - lines_sum)
    
    # Use percentage-based tolerance for larger amounts (handles VAT/shipping better)
    # For amounts > 1000 SEK, allow 0.5% difference (for VAT ~25% on subtotal)
    # For amounts <= 1000 SEK, use fixed tolerance
    tolerance_decimal = _to_decimal(tolerance) or Decimal("0")
    if total_decimal > Decimal("1000"):
        percentage_tolerance = total_decimal * Decimal("0.005")  # 0.5% of total
        return diff <= max(tolerance_decimal, percentage_tolerance)
    return diff <= tolerance_decimal


def _is_largest_in_footer(candidate: float, footer_rows: List[Row]) -> bool:
    """Check if candidate is largest amount in footer rows.
    
    Args:
        candidate: Candidate total amount
        footer_rows: List of rows in footer segment
        
    Returns:
        True if candidate is largest numeric value in footer rows
    """
    amounts = []
    for footer_row in footer_rows:
        for m in _AMOUNT_PATTERN.finditer(footer_row.text):
            v = _parse_amount_str(m.group(0))
            if v is not None:
                amounts.append(v)
    if not amounts:
        return True
    return candidate >= max(amounts)


def score_invoice_number_candidate(
    candidate: str,
    row: Row,
    page: Page,
    all_rows: List[Row]
) -> float:
    """Score invoice number candidate using multi-factor weighted scoring.
    
    Args:
        candidate: Candidate invoice number string
        row: Row containing the candidate
        page: Page reference for position calculation
        all_rows: All rows in document for uniqueness checking
        
    Returns:
        Confidence score (0.0-1.0)
        
    Score components:
    - Position (0.30 weight): Header zone (y < 0.3 * page_height)
    - Keyword proximity (0.35 weight): "fakturanummer/invoice number/nr/no" on same row or adjacent
    - Format validation (0.20 weight): Alphanumeric, length 3-25, not date/amount/org number
    - Uniqueness (0.10 weight): Appears once in document
    - OCR/Token confidence (0.05 weight): Average confidence of tokens in candidate area
    """
    score = 0.0
    
    # Position scoring (0.30 weight)
    # Header zone is typically top 20-30% of page
    if row.y < 0.25 * page.height:  # Top 25% of page (strong header signal)
        score += 0.30
    elif row.y < 0.35 * page.height:  # Top 35% of page (still likely header)
        score += 0.20  # Partial score
    
    # Keyword proximity (0.35 weight)
    # Extended pattern to match more invoice number label variations
    keyword_pattern = r"(?:fakturanummer|faktura\s*nr|faktnr|fakt\.nr|invoice\s*number|invoice\s*no|inv\s*no|no\.|nr|number)"
    if re.search(keyword_pattern, row.text, re.IGNORECASE):
        score += 0.35  # Same row - highest confidence
    elif _has_keyword_in_adjacent_row(row, all_rows, keyword_pattern):
        score += 0.28  # Adjacent row - still high confidence
    # Also check if number appears near "Faktura" text (common pattern: "Faktura 123456")
    elif re.search(r'faktura\s+\d', row.text, re.IGNORECASE):
        score += 0.30  # "Faktura" followed by number - high confidence
    
    # Format validation (0.20 weight)
    if _validate_invoice_number_format(candidate):
        score += 0.20
    
    # Uniqueness (0.10 weight)
    if _appears_once_in_document(candidate, all_rows):
        score += 0.10
    
    # OCR confidence (0.05 weight)
    avg_conf = _average_token_confidence(row.tokens)
    score += 0.05 * avg_conf
    
    return min(score, 1.0)  # Normalize to 0.0-1.0


def _validate_invoice_number_format(candidate: str) -> bool:
    """Validate invoice number format.
    
    Args:
        candidate: Candidate invoice number string
        
    Returns:
        True if format is valid (alphanumeric, length 3-25, not date/amount/org number)
    """
    if not candidate:
        return False
    
    # Length check (3-25 characters)
    if not (3 <= len(candidate) <= 25):
        return False
    
    # Alphanumeric with dashes (common format: INV-2024-001)
    if not re.match(r'^[A-Z0-9\-]+$', candidate, re.IGNORECASE):
        return False
    
    # Numeric invoice numbers are valid (6-12 digits are common)
    # Previously rejected >6 digits, but many invoices use 7-12 digit numbers
    # Only reject if it looks like an org number (10 digits starting with 5 or 6)
    if candidate.isdigit():
        if len(candidate) == 10 and candidate[0] in ['5', '6']:
            # Likely Swedish org number (10 digits starting with 5 or 6)
            return False
        # All other numeric sequences are valid invoice numbers
        return True
    
    # Not a date pattern (YYYY-MM-DD, DD/MM/YYYY, etc.)
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}',  # DD/MM/YYYY variants
    ]
    for pattern in date_patterns:
        if re.match(pattern, candidate):
            return False
    
    return True


def _has_keyword_in_adjacent_row(
    row: Row,
    all_rows: List[Row],
    keyword_pattern: str
) -> bool:
    """Check if keyword exists in row above current row.
    
    Args:
        row: Current row
        all_rows: All rows in document
        keyword_pattern: Regex pattern for keywords
        
    Returns:
        True if keyword found in row directly above
    """
    # Find row index
    try:
        row_index = all_rows.index(row)
        if row_index > 0:
            # Check row above
            row_above = all_rows[row_index - 1]
            if re.search(keyword_pattern, row_above.text, re.IGNORECASE):
                return True
    except ValueError:
        pass  # Row not in list
    
    return False


def _appears_once_in_document(candidate: str, all_rows: List[Row]) -> bool:
    """Check if candidate appears only once in document.
    
    Args:
        candidate: Candidate invoice number string
        all_rows: All rows in document
        
    Returns:
        True if candidate appears exactly once (or is clearly most likely instance)
    """
    count = 0
    for row in all_rows:
        if candidate in row.text:
            count += 1
            if count > 1:
                return False  # Appears multiple times
    
    return count == 1


def _average_token_confidence(tokens: List[Token]) -> float:
    """Calculate average confidence from tokens.
    
    Uses Token.confidence when set (OCR tokens, 0–100 scale). Normalized to 0.0–1.0
    for scoring. When no token has confidence (e.g. pdfplumber path), returns 1.0.
    Per 15-DISCUSS D1: no placeholder 1.0 when OCR token confidence is available.
    
    Args:
        tokens: List of Token objects
        
    Returns:
        Average confidence (0.0-1.0). 1.0 if no tokens or no confidence data.
    """
    if not tokens:
        return 1.0
    confs = [t.confidence for t in tokens if t.confidence is not None and t.confidence >= 0]
    if not confs:
        return 1.0  # pdfplumber tokens: no confidence field set
    # OCR uses 0–100; normalize to 0..1 for score weight
    mean_100 = sum(confs) / len(confs)
    return min(1.0, max(0.0, mean_100 / 100.0))


def validate_and_score_invoice_line(line: InvoiceLine) -> Tuple[float, dict]:
    """Validate and calculate confidence score for an InvoiceLine.
    
    Prioritering:
    1. Först säkerställ att summan (total_amount) är korrekt (källsanning)
    2. Sedan validera/beräkna övriga fält (quantity, unit_price, discount) så att de stämmer med summan
    
    Args:
        line: InvoiceLine to validate and score
        
    Returns:
        Tuple of (confidence_score, validation_info)
        - confidence_score: Overall confidence (0.0-1.0)
        - validation_info: Dict with validation details:
            {
                'total_amount_valid': bool,
                'quantity_valid': bool,
                'unit_price_valid': bool,
                'discount_type': Optional[str],  # 'percent', 'amount', or None
                'discount_valid': bool,
                'calculated_fields': dict,  # Suggested values if extraction failed
                'warnings': List[str]
            }
    """
    validation_info = {
        'total_amount_valid': True,  # total_amount is always valid (it's extracted from PDF)
        'quantity_valid': False,
        'unit_price_valid': False,
        'discount_type': None,
        'discount_valid': False,
        'calculated_fields': {},
        'warnings': []
    }
    
    score = 0.0
    max_score = 1.0
    
    # Step 1: Validate total_amount (källsanning - always valid if line exists)
    # total_amount is required and extracted from PDF, so we give it high confidence
    total_amount = line.total_amount
    if total_amount > 0:
        score += 0.40  # 40% weight for having a valid total_amount
        validation_info['total_amount_valid'] = True
    else:
        validation_info['warnings'].append("total_amount <= 0 (invalid line)")
        return 0.0, validation_info
    
    # Step 2: Validate and calculate other fields based on total_amount
    # Formula: total_amount = (quantity × unit_price) - discount_amount
    # Or: total_amount = (quantity × unit_price) × (1 - discount_percent)
    
    quantity = line.quantity
    unit_price = line.unit_price
    discount = line.discount
    
    # Check if we have enough information to validate
    has_quantity = quantity is not None and quantity > 0
    has_unit_price = unit_price is not None and unit_price > 0
    has_discount = discount is not None
    
    # Calculate expected total based on extracted fields
    if has_quantity and has_unit_price and quantity is not None and unit_price is not None:
        # Calculate base total (before discount)
        base_total = quantity * unit_price
        
        # Try to determine discount type and validate
        if has_discount and discount is not None:
            # Check if discount is percentage (0.0-1.0) or amount (SEK)
            # Percentage: typically 0.0-1.0 (e.g., 0.10 = 10%, 1.0 = 100%)
            # Amount: typically > 1.0 (e.g., 50.00 SEK, -474.30 SEK)
            # Note: discount can be negative if extracted as negative amount
            if discount < 0:
                # Negative value = amount in SEK (already extracted as positive from negative amount)
                discount_type = 'amount'
                discount_amount = abs(discount)  # Make positive for calculation
                expected_total = base_total - discount_amount
            elif 0.0 <= discount <= 1.0:
                # Likely percentage (0.0-1.0 range)
                discount_type = 'percent'
                discount_amount = base_total * discount
                expected_total = base_total * (1 - discount)
            else:
                # Value > 1.0 but not negative - could be percentage > 100% (unlikely) or amount
                # Assume amount in SEK if it's reasonable (not > base_total * 2)
                if discount <= base_total * 2:
                    discount_type = 'amount'
                    discount_amount = discount
                    expected_total = base_total - discount_amount
                else:
                    # Very large value, likely extraction error - treat as percentage anyway
                    discount_type = 'percent'
                    discount_amount = base_total * (discount / 100.0)  # Assume it was meant as percentage
                    expected_total = base_total * (1 - discount / 100.0)
            
            validation_info['discount_type'] = discount_type
            
            # Validate: expected_total should match total_amount
            diff = abs(expected_total - total_amount)
            tolerance = 0.01  # 1 öre tolerance for rounding
            
            if diff <= tolerance:
                # Perfect match
                score += 0.30  # 30% weight for correct calculation
                validation_info['quantity_valid'] = True
                validation_info['unit_price_valid'] = True
                validation_info['discount_valid'] = True
            elif diff <= 1.0:
                # Close match (within 1 SEK) - likely rounding or small extraction error
                score += 0.20  # Partial credit
                validation_info['quantity_valid'] = True
                validation_info['unit_price_valid'] = True
                validation_info['discount_valid'] = True
                validation_info['warnings'].append(
                    f"Liten avvikelse: förväntat {expected_total:.2f}, faktiskt {total_amount:.2f} (diff: {diff:.2f} SEK)"
                )
            else:
                # Significant mismatch - suggest corrected values
                validation_info['warnings'].append(
                    f"Stor avvikelse: förväntat {expected_total:.2f}, faktiskt {total_amount:.2f} (diff: {diff:.2f} SEK)"
                )
                # Try to calculate correct values
                if discount_type == 'percent':
                    # Try to solve: total_amount = base_total × (1 - discount)
                    # If discount is correct, recalculate unit_price or quantity
                    if base_total > 0:
                        corrected_discount_percent = 1 - (total_amount / base_total)
                        if 0.0 <= corrected_discount_percent <= 1.0:
                            validation_info['calculated_fields']['discount'] = corrected_discount_percent
                            validation_info['calculated_fields']['discount_type'] = 'percent'
                else:
                    # Try to solve: total_amount = base_total - discount_amount
                    corrected_discount_amount = base_total - total_amount
                    if corrected_discount_amount >= 0:
                        validation_info['calculated_fields']['discount'] = corrected_discount_amount
                        validation_info['calculated_fields']['discount_type'] = 'amount'
        else:
            # No discount: total_amount should equal quantity × unit_price
            diff = abs(base_total - total_amount)
            tolerance = 0.01
            
            if diff <= tolerance:
                # Perfect match
                score += 0.30
                validation_info['quantity_valid'] = True
                validation_info['unit_price_valid'] = True
            elif diff <= 1.0:
                # Close match
                score += 0.20
                validation_info['quantity_valid'] = True
                validation_info['unit_price_valid'] = True
                validation_info['warnings'].append(
                    f"Liten avvikelse: förväntat {base_total:.2f}, faktiskt {total_amount:.2f} (diff: {diff:.2f} SEK)"
                )
            else:
                # Mismatch - one of quantity or unit_price might be wrong
                validation_info['warnings'].append(
                    f"Avvikelse: antal × a-pris ({base_total:.2f}) ≠ summa ({total_amount:.2f})"
                )
                # Try to calculate correct unit_price
                if quantity > 0:
                    corrected_unit_price = total_amount / quantity
                    validation_info['calculated_fields']['unit_price'] = corrected_unit_price
                # Or try to calculate correct quantity
                if unit_price > 0:
                    corrected_quantity = total_amount / unit_price
                    if corrected_quantity > 0 and abs(corrected_quantity - round(corrected_quantity)) < 0.01:
                        # Quantity should be integer-like
                        validation_info['calculated_fields']['quantity'] = round(corrected_quantity)
    else:
        # Missing quantity or unit_price - try to calculate from total_amount
        if has_quantity and not has_unit_price and quantity is not None:
            # Calculate unit_price from total_amount and quantity
            if quantity > 0:
                calculated_unit_price = total_amount / quantity
                validation_info['calculated_fields']['unit_price'] = calculated_unit_price
                validation_info['warnings'].append(
                    f"A-pris saknas, beräknat: {calculated_unit_price:.2f} SEK"
                )
                score += 0.15  # Partial credit for having quantity
        elif has_unit_price and not has_quantity and unit_price is not None:
            # Calculate quantity from total_amount and unit_price
            if unit_price > 0:
                calculated_quantity = total_amount / unit_price
                if calculated_quantity > 0:
                    # Round to reasonable value
                    if abs(calculated_quantity - round(calculated_quantity)) < 0.01:
                        calculated_quantity = round(calculated_quantity)
                    validation_info['calculated_fields']['quantity'] = calculated_quantity
                    validation_info['warnings'].append(
                        f"Antal saknas, beräknat: {calculated_quantity}"
                    )
                    score += 0.15  # Partial credit for having unit_price
        else:
            # Missing both - can't calculate
            validation_info['warnings'].append(
                "Antal och a-pris saknas - kan inte validera mot summa"
            )
    
    # Step 3: Additional validation (field presence and reasonableness)
    if has_quantity and quantity is not None:
        if 0.001 <= quantity <= 1000000:  # Reasonable range
            score += 0.10  # 10% weight for reasonable quantity
        else:
            validation_info['warnings'].append(f"Antal verkar orimligt: {quantity}")
    
    if has_unit_price and unit_price is not None:
        if 0.01 <= unit_price <= 10000000:  # Reasonable range
            score += 0.10  # 10% weight for reasonable unit_price
        else:
            validation_info['warnings'].append(f"A-pris verkar orimligt: {unit_price:.2f}")
    
    if has_discount and discount is not None:
        if discount >= 0:  # Discount should be non-negative
            score += 0.10  # 10% weight for having discount
        else:
            validation_info['warnings'].append(f"Rabatt är negativ: {discount}")
    
    return min(score, max_score), validation_info


def identify_discount_type(discount: float, base_total: float) -> Tuple[str, float]:
    """Identify if discount is percentage or amount, and return normalized amount.
    
    Args:
        discount: Discount value (could be percentage 0.0-1.0 or amount in SEK)
        base_total: Base total before discount (quantity × unit_price)
        
    Returns:
        Tuple of (discount_type, discount_amount)
        - discount_type: 'percent' or 'amount'
        - discount_amount: Discount in SEK
    """
    if base_total <= 0:
        return 'amount', 0.0
    
    # Heuristic: if discount is between 0.0 and 1.0, it's likely a percentage
    # But also check if it makes sense as a percentage (e.g., 0.10 = 10% discount)
    if 0.0 <= discount <= 1.0:
        # Check if this percentage makes sense (discount shouldn't be > 100% of base)
        discount_amount = base_total * discount
        if discount_amount <= base_total:
            return 'percent', discount_amount
        else:
            # Percentage > 100% doesn't make sense, treat as amount
            return 'amount', discount
    else:
        # Discount > 1.0, likely amount in SEK
        return 'amount', discount

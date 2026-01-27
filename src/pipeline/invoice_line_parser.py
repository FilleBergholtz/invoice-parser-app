"""Line item extraction from items segment using layout-driven approach."""

import re
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import logging

from ..models.invoice_line import InvoiceLine
from ..models.row import Row
from ..models.segment import Segment
from ..models.token import Token
# Import get_table_parser_mode with try/except for linter compatibility
try:
    from ..config import get_table_parser_mode 
except ImportError:
    # Fallback for testing
    def get_table_parser_mode() -> str:
        return "auto"
from ..pipeline.number_normalizer import normalize_swedish_decimal
from ..pipeline.wrap_detection import detect_wrapped_rows, consolidate_wrapped_description
from ..pipeline.column_detection import (
    detect_columns_gap_based,
    map_columns_from_header,
    assign_tokens_to_columns
)
from ..pipeline.validation import validate_netto_sum, validate_total_with_vat
from ..pipeline.footer_extractor import (
    extract_netto_total_from_footer,
    extract_total_with_vat_from_footer
)
from ..debug.table_debug import save_table_debug_artifacts

logger = logging.getLogger(__name__)


# HARD footer keywords: always classify as footer (15-DISCUSS D6).
_FOOTER_HARD_KEYWORDS = frozenset([
    'summa att betala', 'SUMMA ATT BETALA', 'att betala', 'attbetala', 'att betala sek', 'attbetala sek',
    'totalt', 'total', 'delsumma', 'nettobelopp', 'fakturabelopp', 'total delsumma',
    'moms', 'momspliktigt', 'exkl. moms', 'inkl. moms', 'totaltexkl', 'totaltexkl.', 'total inkl', 'total inkl.',
])


# SOFT footer keywords: require additional signal (footer zone, amount pattern) before classifying (15-DISCUSS D6).
_FOOTER_SOFT_KEYWORDS = frozenset([
    'summa', 'exkl', 'inkl', 'exklusive', 'inklusive', 'forskott', 'forskottsbetalning',
    'godkänd', 'godkänd för', 'f-skatt', 'fakturafrågor', 'fakturafrågor skickas',
    'förf datum', 'förf. datum', 'förfallodatum', 'förfallo datum',
    'lista', 'spec', 'bifogad', 'bifogadspec', 'hyraställning', 'hyraställningen',
    'fraktavgift', 'avgiftsbeskrivning', 'avgift',
])
_AMOUNT_PATTERN = re.compile(
    r'-?\d{1,3}(?:[ .]\d{3})+(?:[.,]\d{1,2})?-?|-?\d+(?:[.,]\d{1,2})?-?'
)
_TABLE_END_PATTERN = re.compile(r"nettobelopp\s+exkl\.?\s*moms", re.IGNORECASE)

# KNOWN LIMITATION (Phase 20): Only 25% VAT supported
# Invoices with mixed VAT rates (12%, 6%) will have incomplete line item extraction.
# TODO (Phase 21/22): Extend pattern to r"\b(25|12|6)[.,]00\b" to support all Swedish VAT rates
# See: .planning/phases/20-tabellsegment-kolumnregler/20-LIMITATIONS.md
_MOMS_RATE_PATTERN = re.compile(r"\b25[.,]00\b")


def _is_table_header_row(text_lower: str) -> bool:
    if "nettobelopp" not in text_lower:
        return False
    return any(keyword in text_lower for keyword in ("artikelnr", "artikel", "benämning"))


def _get_table_block_rows(rows: List[Row]) -> Tuple[List[Row], bool]:
    start_idx = None
    end_idx = None

    for idx, row in enumerate(rows):
        if not row.text:
            continue
        text_lower = row.text.lower()
        if start_idx is None and _is_table_header_row(text_lower):
            start_idx = idx + 1
            continue
        if start_idx is not None and _TABLE_END_PATTERN.search(text_lower):
            end_idx = idx
            break

    if start_idx is None:
        return rows, False
    if end_idx is None or end_idx <= start_idx:
        return rows[start_idx:], True
    return rows[start_idx:end_idx], True


def _parse_numeric_value(text: str) -> Optional[Decimal]:
    """Parse numeric text via Swedish normalizer."""
    try:
        value = normalize_swedish_decimal(text)
    except ValueError:
        return None
    return value


def _ensure_decimal(value: Optional[Decimal]) -> Optional[Decimal]:
    """Ensure numeric values remain Decimal throughout parsing."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _row_has_total_like_amount(row: Row) -> bool:
    """True if row has an amount pattern typical of totals (extra signal for SOFT footer)."""
    result = _extract_amount_from_row_text(row)
    if not result:
        return False
    total_amount, _, _ = result
    # Total-like: significant amount, or row has SEK/kr/:- nearby
    if total_amount > 0:
        return True
    return False


def _is_footer_row(row: Row) -> bool:
    """Check if a row is a footer row (summary/total row) based on content.
    
    HARD keywords always classify as footer. SOFT keywords require additional
    signal (total-like amount on row) per 15-DISCUSS D6.
    
    Args:
        row: Row object to check
        
    Returns:
        True if row appears to be a footer/summary row, False otherwise
    """
    if not row.text:
        return False
    
    text_lower = row.text.lower()
    
    for keyword in _FOOTER_HARD_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    
    for keyword in _FOOTER_SOFT_KEYWORDS:
        if keyword in text_lower:
            if _row_has_total_like_amount(row):
                return True
    
    # Heuristics: short description + large amount, total-like patterns (unchanged)
    # Heuristic 1: Extract amount to check if it's suspiciously large
    # This helps identify edge cases where description is short but amount is large
    amount_result = _extract_amount_from_row_text(row)
    if amount_result:
        total_amount, _, amount_token_idx = amount_result
        tokens = row.tokens or []
        # Extract description (text before amount)
        description_tokens = tokens[:amount_token_idx] if amount_token_idx is not None else tokens
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


def _extract_amount_from_row_text(
    row: Row,
    require_moms: bool = False
) -> Optional[Tuple[Decimal, Optional[Decimal], Optional[int]]]:
    """Extract total amount and discount from row.text with support for thousand separators.
    
    Args:
        row: Row object with text property
        
    Returns:
        Tuple of (total_amount, discount, amount_token_idx) if amount found, None otherwise
        - total_amount: Extracted numeric amount (must be positive)
        - discount: Optional discount (as percentage 0.0-1.0 or amount in SEK)
        - amount_token_idx: Index of token containing or closest to total_amount
        
    This function extracts amounts from row.text instead of token-by-token,
    which better handles thousand separators (spaces) that may span multiple tokens.
    Also detects:
    - Negative amounts (discounts) before the total amount: "-474,30" → 474.30 SEK
    - Percentage discounts: "100,0%" → 1.0 (100%), "10,5%" → 0.105 (10.5%)
    
    Examples: 
    - "1 072,60" → (1072.60, None, idx)
    - "440,00 -88,00 1 672,00" → (1672.00, 88.00, idx)  # Discount as amount
    - "-2 007,28 10 000,00" → (10000.00, 2007.28, idx)  # Discount as amount
    - "100,0% 0,00" → (0.00, 1.0, idx)  # Discount as percentage (100%)
    - "10,5% 1 200,00" → (1200.00, 0.105, idx)  # Discount as percentage (10.5%)
    """
    row_text = row.text
    
    # Pattern for amounts with thousand separators (spaces or dots), optional decimals,
    # and optional trailing minus (e.g. "1 234,00-", "12.345,67").
    amount_pattern = _AMOUNT_PATTERN
    
    # Pattern for percentage discounts: "100,0%", "10,5%", "25%", etc.
    # Matches: digits with optional decimal, followed by %
    percentage_pattern = re.compile(
        r'(\d{1,3}(?:[ .]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s*%'
    )
    
    moms_match = None
    if require_moms:
        moms_match = _MOMS_RATE_PATTERN.search(row_text)
        if not moms_match:
            return None

    # Find all amount matches in row.text
    amount_matches = list(amount_pattern.finditer(row_text))
    percentage_matches = list(percentage_pattern.finditer(row_text))
    
    if not amount_matches and not percentage_matches:
        return None
    
    # Extract all amounts with their positions and values
    amounts = []  # List of (value, is_negative, is_percentage, match_start, match_end)
    
    # Process amount matches
    for match in amount_matches:
        amount_text = match.group(0)
        try:
            normalized = normalize_swedish_decimal(amount_text)
        except ValueError:
            continue
        
        is_negative = normalized < 0
        value = abs(normalized)
        if value > 0:  # Only process positive values (we handle sign separately)
            amounts.append((value, is_negative, False, match.start(), match.end()))
    
    # Process percentage matches
    for match in percentage_matches:
        # Group 1: percentage with % sign, Group 2: standalone percentage value
        percent_text = match.group(1) if match.group(1) else match.group(2)
        if not percent_text:
            continue
        
        try:
            percent_value = normalize_swedish_decimal(percent_text)
        except ValueError:
            continue
        
        percent_value = abs(percent_value)
        # Convert to decimal (100% = 1.0, 10.5% = 0.105, 67.00% = 0.67)
        decimal_value = percent_value / Decimal("100")
        amounts.append((decimal_value, False, True, match.start(), match.end()))
    
    if require_moms and moms_match:
        amounts = [amount for amount in amounts if amount[3] > moms_match.end()]

    if not amounts:
        return None
    
    # Find rightmost positive amount (this is total_amount)
    # Prioritize non-percentage amounts for total_amount
    total_amount = None
    total_amount_pos = None
    total_amount_match = None
    
    for value, is_negative, is_percentage, start_pos, end_pos in amounts:
        if not is_negative and not is_percentage:
            # This is a positive amount (not percentage) - track rightmost one
            if total_amount_pos is None or start_pos > total_amount_pos:
                total_amount = value
                total_amount_pos = start_pos
                total_amount_match = (start_pos, end_pos)
    
    # If no non-percentage amount found, look for any positive amount
    if total_amount is None:
        for value, is_negative, is_percentage, start_pos, end_pos in amounts:
            if not is_negative:
                if total_amount_pos is None or start_pos > total_amount_pos:
                    total_amount = value
                    total_amount_pos = start_pos
                    total_amount_match = (start_pos, end_pos)
    
    if total_amount is None or total_amount < 0 or total_amount_match is None:
        return None
    
    # Find discount: negative amounts, percentages, or standalone values before total_amount
    # Support different formats:
    # - Percentage: "100,0%", "10,5%", "67.00" (in Rabatt % column)
    # - Negative amount: "-474,30"
    # - Standalone value after price: "283.00 38" (Jicon: "38" could be percentage or amount)
    discount = None
    discount_pos = None
    discount_is_percentage = False
    
    # First, look for percentage discounts (prioritize these)
    for value, is_negative, is_percentage, start_pos, end_pos in amounts:
        if is_percentage and start_pos < total_amount_pos:
            # This is a percentage discount before total_amount
            if discount_pos is None or start_pos > discount_pos:
                discount = value  # Already in decimal form (0.0-1.0)
                discount_pos = start_pos
                discount_is_percentage = True
    
    # If no percentage found, look for negative amounts
    if discount is None:
        for value, is_negative, is_percentage, start_pos, end_pos in amounts:
            if is_negative and start_pos < total_amount_pos:
                # This is a negative amount before total_amount - use rightmost one as discount
                if discount_pos is None or start_pos > discount_pos:
                    discount = value  # Amount in SEK
                    discount_pos = start_pos
                    discount_is_percentage = False
    
    # If still no discount found, check for standalone numeric values between unit_price and total_amount
    # This handles cases like "Pris Per Rab" column with values like "38" (could be percentage or amount)
    # We'll let the validation logic in confidence_scoring.py determine if it's percentage or amount
    if discount is None:
        # Look for numeric values that are not the total_amount and are positioned before it
        # These could be discounts in "Pris Per Rab" or "Rabatt" columns
        for value, is_negative, is_percentage, start_pos, end_pos in amounts:
            if not is_negative and not is_percentage and start_pos < total_amount_pos:
                # Check if this value is reasonable as a discount
                # If it's small (< 100) and close to total_amount, it might be a percentage value
                # If it's larger, it might be a discount amount
                if discount_pos is None or start_pos > discount_pos:
                    # Store as potential discount (validation will determine type)
                    discount = value
                    discount_pos = start_pos
                    discount_is_percentage = False  # Default to amount, validation will correct if needed
    
    # Map character position back to token index
    # Find which token contains the total amount (or is closest)
    amount_start_pos, amount_end_pos = total_amount_match
    
    # Build character position mapping for tokens (reconstruct row.text).
    # Use sort by x (reading order) and enumerate to avoid O(n²) row.tokens.index(token) (15-DISCUSS D6).
    tokens = row.tokens or []
    char_pos = 0
    token_positions = []  # List of (token_idx, start_pos, end_pos)
    by_x = sorted(enumerate(tokens), key=lambda ie: ie[1].x)
    for original_idx, token in by_x:
        token_start = char_pos
        token_end = char_pos + len(token.text)
        token_positions.append((original_idx, token_start, token_end))
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


def extract_invoice_lines(
    items_segment: Segment,
    footer_segment: Optional[Segment] = None,
    rows_above_footer: Optional[List[Row]] = None,
    artifacts_dir: Optional[Path] = None,
    invoice_id: Optional[str] = None
) -> List[InvoiceLine]:
    """Extract line items from items segment using layout-driven approach.
    
    Args:
        items_segment: Segment object with segment_type='items'
        footer_segment: Optional footer segment for validation (Phase 22)
        rows_above_footer: Optional rows immediately above footer for validation
        
    Returns:
        List of InvoiceLine objects
        
    Algorithm (layout-driven):
    - Iterate through Segment.rows
    - For each row, check if it contains a numeric amount (total_amount)
    - Rule: "rad med belopp = produktrad" - if row contains amount, it's a product row
    - Extract fields from row tokens using spatial information
    
    Phase 22: Validation-driven re-extraction (mode B):
    - If table_parser_mode is "auto", validate after mode A extraction
    - If validation fails, fallback to mode B (position-based)
    - If table_parser_mode is "pos", use mode B directly
    - If table_parser_mode is "text", use mode A only (no fallback)
    """
    if items_segment.segment_type != "items":
        raise ValueError(
            f"Segment must be of type 'items', got '{items_segment.segment_type}'"
        )
    
    # Get table parser mode from config
    parser_mode = get_table_parser_mode()
    
    # If mode is "pos", use mode B directly
    if parser_mode == "pos":
        logger.debug("Mode B (position-based) selected via config")
        return extract_invoice_lines_mode_b(items_segment)
    
    # Extract with mode A (text-based)
    invoice_lines = []
    line_number = 1
    processed_row_indices = set()  # Track rows already processed as wraps
    table_rows, use_table_rules = _get_table_block_rows(items_segment.rows)

    for row_index, row in enumerate(table_rows):
        # Skip rows already processed as wraps
        if row_index in processed_row_indices:
            continue
        
        # Skip footer rows (summary/total rows that shouldn't be product rows)
        if _is_footer_row(row):
            continue
        
        # Try to extract line item from row
        invoice_line = _extract_line_from_row(
            row,
            items_segment,
            line_number,
            require_moms=use_table_rules
        )
        
        if invoice_line:
            # Detect wrapped rows with enhanced detection
            following_rows = table_rows[row_index + 1:]
            wrapped_rows = detect_wrapped_rows(
                row, 
                following_rows, 
                items_segment.page,
                all_rows=table_rows  # Pass all table rows for adaptive Y-threshold
            )
            
            # Mark wrapped rows as processed
            for wrapped_row in wrapped_rows:
                wrapped_index = table_rows.index(wrapped_row)
                processed_row_indices.add(wrapped_index)
            
            # Update InvoiceLine with wrapped rows
            if wrapped_rows:
                # Add wrapped rows to InvoiceLine.rows (KÄLLSANING for traceability)
                invoice_line.rows.extend(wrapped_rows)
                
                # Consolidate description
                invoice_line.description = consolidate_wrapped_description(row, wrapped_rows)
            
            invoice_lines.append(invoice_line)
            line_number += 1
    
    # Phase 22: Validation-driven re-extraction (mode B fallback)
    if parser_mode == "auto" and footer_segment is not None:
        # Extract "Nettobelopp exkl. moms" from footer
        netto_total = extract_netto_total_from_footer(footer_segment, rows_above_footer)
        
        if netto_total is not None:
            # Validate nettosumma (VAL-01)
            validation_passed, diff = validate_netto_sum(
                invoice_lines,
                netto_total,
                tolerance=Decimal("0.50")
            )
            
            # Phase 22: Also validate total with VAT (VAL-02) if available
            total_with_vat = extract_total_with_vat_from_footer(footer_segment, rows_above_footer)
            if total_with_vat is not None:
                # Calculate VAT amount (typically 25% of netto_sum)
                netto_sum = sum((line.total_amount for line in invoice_lines), Decimal("0"))
                vat_amount = netto_sum * Decimal("0.25")  # 25% VAT
                
                validation_passed_vat, diff_vat = validate_total_with_vat(
                    netto_sum,
                    vat_amount,
                    total_with_vat,
                    tolerance=Decimal("0.50")
                )
                
                # If VAL-02 fails, also trigger mode B fallback
                if not validation_passed_vat:
                    logger.info(
                        f"Mode A VAL-02 failed: diff={diff_vat:.2f} SEK, "
                        f"falling back to mode B (position-based)"
                    )
                    validation_passed = False  # Trigger mode B fallback
            
            if not validation_passed:
                logger.info(
                    f"Mode A VAL-01 failed: diff={diff:.2f} SEK, "
                    f"falling back to mode B (position-based)"
                )
                # Fallback to mode B
                mode_b_lines = extract_invoice_lines_mode_b(items_segment)
                
                # Validate mode B result
                if mode_b_lines:
                    validation_passed_b, diff_b = validate_netto_sum(
                        mode_b_lines,
                        netto_total,
                        tolerance=Decimal("0.50")
                    )
                    
                    if validation_passed_b:
                        logger.info(
                            f"Mode B VAL-01 passed: diff={diff_b:.2f} SEK, "
                            f"using mode B result"
                        )
                        
                        # Phase 22: Validate total with VAT (VAL-02)
                        total_with_vat = extract_total_with_vat_from_footer(footer_segment, rows_above_footer)
                        if total_with_vat is not None:
                            # Calculate VAT amount (typically 25% of netto_sum)
                            netto_sum_b = sum((line.total_amount for line in mode_b_lines), Decimal("0"))
                            vat_amount = netto_sum_b * Decimal("0.25")  # 25% VAT
                            
                            validation_passed_vat, diff_vat = validate_total_with_vat(
                                netto_sum_b,
                                vat_amount,
                                total_with_vat,
                                tolerance=Decimal("0.50")
                            )
                            
                            if not validation_passed_vat:
                                logger.warning(
                                    f"Mode B VAL-02 failed: diff={diff_vat:.2f} SEK, "
                                    f"but VAL-01 passed, using mode B result"
                                )
                            else:
                                logger.info(
                                    f"Mode B VAL-02 passed: diff={diff_vat:.2f} SEK"
                                )
                        
                        return mode_b_lines
                    else:
                        logger.warning(
                            f"Mode B validation also failed: diff={diff_b:.2f} SEK, "
                            f"keeping mode A result"
                        )
                        
                        # Save debug artifacts if mismatch persists (VAL-04)
                        if artifacts_dir and invoice_id:
                            # Create ValidationResult for debug artifacts
                            from ..models.validation_result import ValidationResult
                            validation_result = ValidationResult(
                                status="REVIEW",
                                lines_sum=sum((line.total_amount for line in mode_b_lines), Decimal("0")),
                                diff=diff_b,
                                tolerance=Decimal("0.50"),
                                hard_gate_passed=False,
                                errors=[f"Mode B validation failed: diff={diff_b:.2f} SEK"],
                                warnings=[f"Mode A also failed: diff={diff:.2f} SEK"]
                            )
                            
                            # Get table rows for debug artifacts
                            table_rows, _ = _get_table_block_rows(items_segment.rows)
                            
                            # Save debug artifacts
                            save_table_debug_artifacts(
                                artifacts_dir=artifacts_dir,
                                invoice_id=invoice_id,
                                table_rows=table_rows,
                                line_items=mode_b_lines,
                                validation_result=validation_result,
                                netto_total=netto_total,
                                mode_used="B"
                            )
                else:
                    logger.warning("Mode B returned no lines, keeping mode A result")
                    
                    # Save debug artifacts for mode A failure if mismatch persists
                    if artifacts_dir and invoice_id:
                        from ..models.validation_result import ValidationResult
                        validation_result = ValidationResult(
                            status="REVIEW",
                            lines_sum=sum((line.total_amount for line in invoice_lines), Decimal("0")),
                            diff=diff,
                            tolerance=Decimal("0.50"),
                            hard_gate_passed=False,
                            errors=[f"Mode A validation failed: diff={diff:.2f} SEK"],
                            warnings=["Mode B returned no lines"]
                        )
                        
                        table_rows, _ = _get_table_block_rows(items_segment.rows)
                        
                        save_table_debug_artifacts(
                            artifacts_dir=artifacts_dir,
                            invoice_id=invoice_id,
                            table_rows=table_rows,
                            line_items=invoice_lines,
                            validation_result=validation_result,
                            netto_total=netto_total,
                            mode_used="A"
                        )
    
    return invoice_lines


def _extract_line_from_row(
    row: Row,
    segment: Segment,
    line_number: int,
    require_moms: bool = False
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
    result = _extract_amount_from_row_text(row, require_moms=require_moms)
    if result is None:
        return None
    
    total_amount, discount, amount_token_idx = result
    tokens = row.tokens or []

    # Extract description: leftmost text before amount column
    # Skip common column headers/prefixes that appear at start:
    # - Line numbers: "1", "001", "Pos 1"
    # - Article numbers: "3838969", "2406CSX1P10.10"
    # - Position markers: "Pos", "Rad"
    description_tokens = tokens[:amount_token_idx] if amount_token_idx is not None else tokens
    
    # Skip leading numeric tokens that look like line numbers or article numbers
    # Line numbers are typically: single digit or 3-digit with leading zeros (001, 002)
    # Article numbers are typically: 6+ digits or alphanumeric codes
    description_start_idx = 0
    for i, token in enumerate(description_tokens[:5]):  # Check first 5 tokens
        token_text = token.text.strip()
        # Skip if it's a simple line number (1-3 digits, possibly with leading zeros)
        if re.match(r'^0?\d{1,3}$', token_text):
            # Could be line number - check if next token is also numeric (likely article number)
            if i + 1 < len(description_tokens):
                next_token = description_tokens[i + 1].text.strip()
                # If next is alphanumeric or long number, first was line number
                if re.match(r'^[A-Z0-9]{4,}', next_token) or re.match(r'^\d{6,}', next_token):
                    description_start_idx = i + 1
                    break
        # Skip if it's an article number (alphanumeric code or 6+ digits)
        elif re.match(r'^[A-Z0-9]{4,}$', token_text) or re.match(r'^\d{6,}$', token_text):
            description_start_idx = i + 1
            break
        # Skip position markers
        elif token_text.lower() in ['pos', 'rad', 'obj']:
            description_start_idx = i + 1
            continue
        else:
            # Found start of actual description
            break
    
    description_tokens = description_tokens[description_start_idx:]
    description = " ".join(t.text for t in description_tokens).strip()
    
    # Extract quantity and unit_price: look for numeric columns before amount
    # Support different column orders:
    # - Standard: description | quantity | unit | unit_price | total_amount
    # - Derome: description | ... | Fsg. kvant. | Enhet | Pris | Nettobelopp
    # - CERTEX: Artikelnr/Beskrivning | ... | Enhet | Pris | Rab% | Belopp
    # - Ahlsell: Art nr | Benämning | Antal | Enhet | á-pris | Rabatt | Total
    quantity = None
    unit = None
    unit_price = None
    
    # Extended unit list including DAY, dagar, EA, LTR, Liter, månad, XPA, bdag, M2, M3, BD, dgr
    # Support for different invoice layouts (e.g., "bdag" = business days, "BD" = Byggdagar, "dgr" = dagar)
    # Note: These are exact string matches (case-insensitive), not regex patterns
    unit_keywords = [
        'st', 'kg', 'h', 'm²', 'm2', 'm3', 'm³', 'tim', 'timmar', 'pcs', 'pkt',
        'day', 'days', 'dagar', 'ea', 'ltr', 'liter', 'liters', 'månad', 'månader',
        'xpa', 'pkt', 'paket', 'box', 'burk', 'flaska', 'flaskor',
        'bdag', 'bdagar', 'businessday', 'businessdays',  # Business days (without space)
        'bd', 'byggdagar', 'byggdag',  # Byggdagar (Ramirent layout)
        'dgr', 'dgr.', 'dagar',  # Dag/dagar (Neglinge: "5 dgr." - with or without period)
        'enh', 'enhet', 'unit', 'units',  # Generic unit labels
        # Volume and area units
        'm²', 'm2', 'kvadratmeter', 'm³', 'm3', 'kubikmeter',
        # Additional common units
        'l', 'liter', 'kg', 'gram', 'g', 'ton', 't',
    ]
    
    # First, try to find unit token - use it as anchor for quantity/unit_price extraction
    # Support "Plockat Enh" format: "10 ST" (quantity + unit together)
    unit_token_idx = None
    for i, token in enumerate(tokens):
        if amount_token_idx is not None and i >= amount_token_idx:
            break
        token_text = token.text.strip()
        token_lower = token_text.lower()
        
        # Check exact match in unit_keywords (case-insensitive)
        if token_lower in unit_keywords:
            unit = token_lower
            unit_token_idx = i
            # Check if previous token is a number (quantity + unit pattern: "10 ST")
            if i > 0:
                prev_token = tokens[i - 1].text.strip()
                if re.match(r'^\d+$', prev_token):
                    potential_quantity = _parse_numeric_value(prev_token)
                    if potential_quantity is not None and 1 <= potential_quantity <= 100000:
                        quantity = potential_quantity
            break
        # Also check if token matches unit pattern (uppercase units like "ST", "EA", "M2", "BD")
        elif re.match(r'^[A-Z]{1,4}$', token_text):
            token_lower_check = token_lower
            if token_lower_check in unit_keywords:
                unit = token_lower_check
                unit_token_idx = i
                # Check if previous token is a number (quantity + unit pattern: "10 ST")
                if i > 0:
                    prev_token = tokens[i - 1].text.strip()
                    if re.match(r'^\d+$', prev_token):
                        potential_quantity = _parse_numeric_value(prev_token)
                        if potential_quantity is not None and 1 <= potential_quantity <= 100000:
                            quantity = potential_quantity
                break
        # Check for units with numbers (M2, M3)
        elif re.match(r'^[Mm][23]$', token_text):
            unit = token_lower
            unit_token_idx = i
            # Check if previous token is a number
            if i > 0:
                prev_token = tokens[i - 1].text.strip()
                if re.match(r'^\d+$', prev_token):
                    potential_quantity = _parse_numeric_value(prev_token)
                    if potential_quantity is not None and 1 <= potential_quantity <= 100000:
                        quantity = potential_quantity
            break
    
    # Identify potential article numbers in description
    # Support different formats:
    # - Numeric: "3838969", "2406CSX1P10.10"
    # - Alphanumeric: "2406CSX1P10.10", "10452L"
    # - With spaces: "27 7615"
    article_number_pattern = re.compile(r'^([A-Z0-9]{4,}(?:\.[A-Z0-9]+)?|\d{1,2}\s+\d{5,8}|\d{6,12})\s+')
    has_article_number = bool(article_number_pattern.match(description))
    
    # Also check for article numbers that might be in separate column (before description)
    # Look at tokens before description_start_idx
    if description_start_idx > 0:
        article_tokens = tokens[:description_start_idx]
        for token in article_tokens:
            token_text = token.text.strip()
            # Check if token looks like article number (alphanumeric 4+ chars or 6+ digits)
            if re.match(r'^[A-Z0-9]{4,}(?:\.[A-Z0-9]+)?$', token_text) or re.match(r'^\d{6,}$', token_text):
                has_article_number = True
                break
    
    first_number_match = re.match(r'^(\d+(?:\s+\d+)*|[A-Z0-9]{4,}(?:\.[A-Z0-9]+)?)', description)
    first_number_str = first_number_match.group(1) if first_number_match else ""
    first_number_cleaned = first_number_str.replace(' ', '').replace('.', '')
    first_number_value = None
    if first_number_cleaned and (first_number_cleaned.isdigit() or re.match(r'^[A-Z0-9]{4,}$', first_number_cleaned)):
        try:
            # Try to extract numeric part if alphanumeric
            numeric_part = re.sub(r'[^0-9]', '', first_number_cleaned)
            if numeric_part:
                first_number_value = _parse_numeric_value(numeric_part)
        except ValueError:
            pass
    
    # Strategy 1: If unit found, use it as anchor
    # Format: ... quantity unit unit_price ... total_amount
    # Example: "2 5220 ELMÄTARE63A 3 EA 13,00" → quantity=3, unit=EA, unit_price=13.00
    # Example: "27 7615 COMBISAFESTÖLBALKSTVING 2 108 EA 1,95" → quantity=2108, unit=EA, unit_price=1.95
    # Special case: "Plockat Enh" column (K-Bygg, Jicon) contains "10 ST" → quantity=10, unit=ST
    # Special case: "Pris Per Rab" column may contain "N" (no discount) or numeric value (discount)
    if unit_token_idx is not None:
        # First, try to extract quantity from text (handles thousand separators across tokens)
        # Get text before unit token
        before_unit_tokens = tokens[:unit_token_idx]
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
                numeric_value = _parse_numeric_value(quantity_text)
                if numeric_value is None:
                    continue

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
        
        # If no thousand-separator quantity found, look for single numeric token
        if quantity is None:
            for i in range(unit_token_idx - 1, -1, -1):  # Go backwards from unit
                if amount_token_idx is not None and i >= amount_token_idx:
                    break
                token = tokens[i]
                token_text = token.text.strip()
                
                # Check if token is a pure number
                if re.match(r'^\d+([.,]\d+)?$', token_text.replace(' ', '')):
                    numeric_value = _parse_numeric_value(token_text)
                    if numeric_value is None:
                        continue
                    
                    # Skip if it looks like article number or line number
                    is_article_or_line_number = False
                    if i < 3:  # First few tokens
                        if first_number_value and abs(numeric_value - first_number_value) < Decimal("0.01"):
                            is_article_or_line_number = True
                        elif numeric_value >= 10000 or len(str(int(numeric_value))) >= 5:
                            is_article_or_line_number = True
                        elif i == 0 and numeric_value < 100 and numeric_value == int(numeric_value):
                            if len(tokens) > 1 and i + 1 < len(tokens):
                                next_token = tokens[i + 1].text.strip()
                                if re.match(r'^\d+', next_token):
                                    is_article_or_line_number = True
                    
                    if not is_article_or_line_number:
                        # This is likely quantity (should be small number, < 1000 typically)
                        if numeric_value < 1000 and numeric_value == int(numeric_value):
                            quantity = numeric_value
                            break
        
        # Look for numeric token AFTER unit but BEFORE amount (this is unit_price)
        # Handle amounts with thousand separators (e.g., "1 034,00")
        # Extract text between unit and amount, then find amount pattern
        if amount_token_idx is not None and unit_token_idx + 1 < amount_token_idx:
            # Get text between unit and amount
            unit_to_amount_tokens = tokens[unit_token_idx + 1:amount_token_idx]
            unit_to_amount_text = " ".join(t.text for t in unit_to_amount_tokens)
            
            # Pattern for amounts with thousand separators (spaces or dots)
            # Matches: "123,45", "1 234,56", "1 034,00", "3.717,35" (punkt som tusentalsavgränsare), "8302.00" (punkt som decimal)
            match = _AMOUNT_PATTERN.search(unit_to_amount_text)
            
            if match:
                amount_text = match.group(0)
                numeric_value = _parse_numeric_value(amount_text)
                if numeric_value is not None:
                    # Unit price should be reasonable (not too small, not too large)
                    if Decimal("0.01") <= numeric_value <= Decimal("1000000"):  # Reasonable range
                        unit_price = numeric_value
            else:
                # Fallback: look for single numeric token
                if amount_token_idx is not None:
                    for i in range(unit_token_idx + 1, amount_token_idx):
                        token = tokens[i]
                        token_text = token.text.strip()
                        if re.match(r'^\d+([.,]\d+)?$', token_text.replace(' ', '')):
                            numeric_value = _parse_numeric_value(token_text)
                            if numeric_value is not None and Decimal("0.01") <= numeric_value <= Decimal("1000000"):
                                unit_price = numeric_value
                                break
    
    # Strategy 2: If no unit found, use old heuristic (fallback)
    if unit_token_idx is None:
        # Look for numeric tokens before amount (potential quantity or unit_price)
        numeric_tokens_before_amount = []
        for i, token in enumerate(tokens):
            if amount_token_idx is not None and i >= amount_token_idx:
                break
            
            token_text = token.text.strip()
            # Check if token looks like a number
            if re.match(r'^\d+([.,]\d+)?$', token_text.replace(' ', '')):
                numeric_value = _parse_numeric_value(token_text)
                if numeric_value is None:
                    continue
                
                # Skip if this looks like an article number
                is_article_number = False
                if i < 2:  # First tokens
                    if numeric_value >= 100000:  # 6+ digits
                        is_article_number = True
                    elif first_number_value and abs(numeric_value - first_number_value) < Decimal("0.01"):
                        is_article_number = True
                    elif len(str(int(numeric_value))) >= 6:  # 6+ digits
                        is_article_number = True
                
                if is_article_number:
                    continue  # Skip article number
                    
                numeric_tokens_before_amount.append((i, numeric_value, token))
        
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
            for token in tokens:
                token_text = token.text.strip().lower()
                if token_text in unit_keywords:
                    unit = token_text
                    break
    
    # Create InvoiceLine
    return InvoiceLine(
        rows=[row],  # In Phase 1, typically one row per line item (wraps come in Phase 2)
        description=description or "Unknown",
        quantity=_ensure_decimal(quantity),
        unit=unit,
        unit_price=_ensure_decimal(unit_price),
        discount=_ensure_decimal(discount),  # Extracted from negative amounts before total_amount
        total_amount=_ensure_decimal(total_amount) or Decimal("0"),
        vat_rate=None,  # Not extracted in Phase 1
        line_number=line_number,
        segment=segment
    )


def extract_invoice_lines_mode_b(items_segment: Segment) -> List[InvoiceLine]:
    """Extract invoice lines using position-based parsing (mode B).
    
    Mode B uses spatial analysis (column detection) combined with content patterns
    (VAT% patterns, unit keywords) for robust field extraction. This is a fallback
    for mode A when validation fails.
    
    Args:
        items_segment: Items segment containing table rows
        
    Returns:
        List of InvoiceLine objects extracted using position-based parsing
        
    Algorithm:
        1. Detect columns via gap-based detection
        2. Map columns to fields via header row (if available)
        3. For each row:
           a. Assign tokens to columns
           b. Extract fields using hybrid approach (position + content)
           c. Use VAT%-anchored net amount extraction (same as mode A)
        4. Apply wrap detection (same as mode A)
        
    Fallback:
        If column detection fails, falls back to mode A (text-based parsing).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Get table block rows (same as mode A)
    table_rows, use_table_rules = _get_table_block_rows(items_segment.rows)
    
    if not table_rows:
        return []
    
    # Step 1: Detect columns via gap-based detection
    column_centers = detect_columns_gap_based(table_rows)
    
    if not column_centers:
        logger.warning("Mode B: Column detection failed, falling back to mode A")
        return extract_invoice_lines(items_segment)
    
    # Step 2: Map columns to fields via header row (if available)
    column_map = None
    header_row = None
    data_rows_start = 0
    
    # Find header row (first row with "nettobelopp" + column keywords)
    for idx, row in enumerate(table_rows):
        if _is_table_header_row(row.text.lower()):
            header_row = row
            data_rows_start = idx + 1
            column_map = map_columns_from_header(header_row, column_centers)
            break
    
    # Step 3: Extract line items row-by-row
    invoice_lines = []
    line_number = 1
    processed_row_indices = set()
    
    for row_index, row in enumerate(table_rows[data_rows_start:], start=data_rows_start):
        # Skip rows already processed as wraps
        if row_index in processed_row_indices:
            continue
        
        # Skip footer rows
        if _is_footer_row(row):
            continue
        
        # Assign tokens to columns
        column_tokens = assign_tokens_to_columns(row, column_centers)
        
        # Extract line item using hybrid approach
        invoice_line = _extract_line_from_row_mode_b(
            row,
            column_tokens,
            column_map,
            items_segment,
            line_number,
            require_moms=use_table_rules
        )
        
        if invoice_line:
            # Detect wrapped rows (same as mode A)
            following_rows = table_rows[row_index + 1:]
            wrapped_rows = detect_wrapped_rows(
                row,
                following_rows,
                items_segment.page,
                all_rows=table_rows
            )
            
            # Mark wrapped rows as processed
            for wrapped_row in wrapped_rows:
                wrapped_index = table_rows.index(wrapped_row)
                processed_row_indices.add(wrapped_index)
            
            # Update InvoiceLine with wrapped rows
            if wrapped_rows:
                invoice_line.rows.extend(wrapped_rows)
                invoice_line.description = consolidate_wrapped_description(row, wrapped_rows)
            
            invoice_lines.append(invoice_line)
            line_number += 1
    
    return invoice_lines


def _extract_line_from_row_mode_b(
    row: Row,
    column_tokens: Dict[int, List[Token]],
    column_map: Optional[Dict[str, int]],
    segment: Segment,
    line_number: int,
    require_moms: bool = False
) -> Optional[InvoiceLine]:
    """Extract InvoiceLine from row using position-based parsing (mode B).
    
    Uses hybrid approach: position (column mapping) + content (VAT% patterns, unit keywords).
    
    Args:
        row: Row object to analyze
        column_tokens: Dict mapping column index to list of tokens in that column
        column_map: Optional dict mapping field names to column indices (from header)
        segment: Items segment reference
        line_number: Line number for ordering
        require_moms: If True, require VAT% pattern for valid line item
        
    Returns:
        InvoiceLine if row contains amount (product row), None otherwise
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Hybrid approach: Use position (column_map) when available, fallback to content
    
    # Step 1: Extract netto amount (VAT%-anchored, same as mode A)
    result = _extract_amount_from_row_text(row, require_moms=require_moms)
    if result is None:
        return None
    
    total_amount, discount, amount_token_idx = result
    
    # Step 2: Extract description
    description = _extract_description_mode_b(row, column_tokens, column_map, amount_token_idx)
    
    # Step 3: Extract quantity, unit, unit_price using hybrid approach
    quantity, unit, unit_price = _extract_quantity_unit_price_mode_b(
        row,
        column_tokens,
        column_map,
        amount_token_idx
    )
    
    # Step 4: Extract VAT rate (if available)
    vat_rate = _extract_vat_rate_mode_b(row, column_tokens, column_map)
    
    # Create InvoiceLine
    return InvoiceLine(
        rows=[row],
        description=description or "Unknown",
        quantity=_ensure_decimal(quantity),
        unit=unit,
        unit_price=_ensure_decimal(unit_price),
        discount=_ensure_decimal(discount),
        total_amount=_ensure_decimal(total_amount) or Decimal("0"),
        vat_rate=_ensure_decimal(vat_rate),
        line_number=line_number,
        segment=segment
    )


def _extract_description_mode_b(
    row: Row,
    column_tokens: Dict[int, List[Token]],
    column_map: Optional[Dict[str, int]],
    amount_token_idx: Optional[int]
) -> str:
    """Extract description using position-based approach.
    
    Uses column mapping if available, otherwise falls back to content-based extraction.
    """
    # Try position-based: use mapped column if available
    if column_map and 'description' in column_map:
        col_idx = column_map['description']
        if col_idx in column_tokens:
            desc_tokens = column_tokens[col_idx]
            # Skip article numbers (same logic as mode A)
            description = _filter_description_tokens(desc_tokens)
            if description:
                return description
    
    # Fallback: content-based (same as mode A)
    tokens = row.tokens or []
    description_tokens = tokens[:amount_token_idx] if amount_token_idx is not None else tokens
    description_start_idx = 0
    
    # Skip leading numeric/article number tokens (same logic as mode A)
    for i, token in enumerate(description_tokens[:5]):
        token_text = token.text.strip()
        if re.match(r'^0?\d{1,3}$', token_text):
            if i + 1 < len(description_tokens):
                next_token = description_tokens[i + 1].text.strip()
                if re.match(r'^[A-Z0-9]{4,}', next_token) or re.match(r'^\d{6,}', next_token):
                    description_start_idx = i + 1
                    break
        elif re.match(r'^[A-Z0-9]{4,}$', token_text) or re.match(r'^\d{6,}$', token_text):
            description_start_idx = i + 1
            break
        elif token_text.lower() in ['pos', 'rad', 'obj']:
            description_start_idx = i + 1
            continue
        else:
            break
    
    description_tokens = description_tokens[description_start_idx:]
    return " ".join(t.text for t in description_tokens).strip()


def _filter_description_tokens(tokens: List[Token]) -> str:
    """Filter tokens to extract description, skipping article numbers and line numbers."""
    if not tokens:
        return ""
    
    description_tokens = []
    for token in tokens:
        token_text = token.text.strip()
        # Skip line numbers, article numbers, position markers
        if (re.match(r'^0?\d{1,3}$', token_text) or
            re.match(r'^[A-Z0-9]{4,}$', token_text) or
            re.match(r'^\d{6,}$', token_text) or
            token_text.lower() in ['pos', 'rad', 'obj']):
            continue
        description_tokens.append(token)
    
    return " ".join(t.text for t in description_tokens).strip()


def _extract_quantity_unit_price_mode_b(
    row: Row,
    column_tokens: Dict[int, List[Token]],
    column_map: Optional[Dict[str, int]],
    amount_token_idx: Optional[int]
) -> Tuple[Optional[Decimal], Optional[str], Optional[Decimal]]:
    """Extract quantity, unit, and unit_price using hybrid approach.
    
    Returns:
        Tuple of (quantity, unit, unit_price)
    """
    quantity = None
    unit = None
    unit_price = None
    
    tokens = row.tokens or []
    
    # Unit keywords (same as mode A)
    unit_keywords = [
        'st', 'kg', 'h', 'm²', 'm2', 'm3', 'm³', 'tim', 'timmar', 'pcs', 'pkt',
        'day', 'days', 'dagar', 'ea', 'ltr', 'liter', 'liters', 'månad', 'månader',
        'xpa', 'pkt', 'paket', 'box', 'burk', 'flaska', 'flaskor',
        'bdag', 'bdagar', 'businessday', 'businessdays',
        'bd', 'byggdagar', 'byggdag',
        'dgr', 'dgr.', 'dagar',
        'enh', 'enhet', 'unit', 'units',
        'm²', 'm2', 'kvadratmeter', 'm³', 'm3', 'kubikmeter',
        'l', 'liter', 'kg', 'gram', 'g', 'ton', 't',
    ]
    
    # Try position-based extraction first (if column_map available)
    if column_map:
        # Extract quantity
        if 'quantity' in column_map:
            col_idx = column_map['quantity']
            if col_idx in column_tokens:
                qty_tokens = column_tokens[col_idx]
                if qty_tokens:
                    qty_text = " ".join(t.text for t in qty_tokens)
                    quantity = _parse_numeric_value(qty_text)
        
        # Extract unit
        if 'unit' in column_map:
            col_idx = column_map['unit']
            if col_idx in column_tokens:
                unit_tokens = column_tokens[col_idx]
                if unit_tokens:
                    unit_text = unit_tokens[0].text.strip().lower()
                    if unit_text in unit_keywords:
                        unit = unit_text
        
        # Extract unit_price
        if 'unit_price' in column_map:
            col_idx = column_map['unit_price']
            if col_idx in column_tokens:
                price_tokens = column_tokens[col_idx]
                if price_tokens:
                    price_text = " ".join(t.text for t in price_tokens)
                    unit_price = _parse_numeric_value(price_text)
    
    # Fallback: content-based extraction (same as mode A)
    # Find unit token first (use as anchor)
    unit_token_idx = None
    for i, token in enumerate(tokens):
        if amount_token_idx is not None and i >= amount_token_idx:
            break
        token_text = token.text.strip()
        token_lower = token_text.lower()
        
        if token_lower in unit_keywords:
            unit = token_lower
            unit_token_idx = i
            # Check if previous token is quantity
            if i > 0:
                prev_token = tokens[i - 1].text.strip()
                if re.match(r'^\d+$', prev_token):
                    potential_quantity = _parse_numeric_value(prev_token)
                    if potential_quantity is not None and 1 <= potential_quantity <= 100000:
                        quantity = potential_quantity
            break
    
    # Extract quantity/unit_price if not found via position
    if unit_token_idx is not None:
        # Look for quantity before unit
        if quantity is None:
            for i in range(unit_token_idx - 1, -1, -1):
                if amount_token_idx is not None and i >= amount_token_idx:
                    break
                token = tokens[i]
                token_text = token.text.strip()
                if re.match(r'^\d+([.,]\d+)?$', token_text.replace(' ', '')):
                    numeric_value = _parse_numeric_value(token_text)
                    if numeric_value is not None and 1 <= numeric_value <= 100000:
                        quantity = numeric_value
                        break
        
        # Look for unit_price after unit
        if unit_price is None and amount_token_idx is not None:
            for i in range(unit_token_idx + 1, amount_token_idx):
                token = tokens[i]
                token_text = token.text.strip()
                if re.match(r'^\d+([.,]\d+)?$', token_text.replace(' ', '')):
                    numeric_value = _parse_numeric_value(token_text)
                    if numeric_value is not None and Decimal("0.01") <= numeric_value <= Decimal("1000000"):
                        unit_price = numeric_value
                        break
    
    return quantity, unit, unit_price


def _extract_vat_rate_mode_b(
    row: Row,
    column_tokens: Dict[int, List[Token]],
    column_map: Optional[Dict[str, int]]
) -> Optional[Decimal]:
    """Extract VAT rate using hybrid approach.
    
    Returns:
        VAT rate as Decimal (e.g., 0.25 for 25%), or None
    """
    # Try position-based: use mapped column if available
    if column_map and 'vat_percent' in column_map:
        col_idx = column_map['vat_percent']
        if col_idx in column_tokens:
            vat_tokens = column_tokens[col_idx]
            if vat_tokens:
                vat_text = " ".join(t.text for t in vat_tokens)
                # Look for VAT% pattern (25.00, 25,00, etc.)
                vat_match = _MOMS_RATE_PATTERN.search(vat_text)
                if vat_match:
                    return Decimal("0.25")  # 25% VAT
    
    # Fallback: content-based (search row text for VAT% pattern)
    row_text = row.text
    vat_match = _MOMS_RATE_PATTERN.search(row_text)
    if vat_match:
        return Decimal("0.25")  # 25% VAT
    
    return None


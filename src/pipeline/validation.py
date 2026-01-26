"""Validation logic for invoice data with status assignment."""

from typing import List, Optional, Tuple

from ..models.invoice_header import InvoiceHeader
from ..models.invoice_line import InvoiceLine
from ..models.validation_result import ValidationResult
from ..pipeline.confidence_scoring import (
    validate_total_against_line_items,
    validate_and_score_invoice_line
)


def validate_line_items(
    line_items: List[InvoiceLine],
    tolerance: float = 0.01
) -> List[str]:
    """Validate each line item using comprehensive validation and confidence scoring.
    
    Prioritering:
    1. Först säkerställ att summan (total_amount) är korrekt (källsanning)
    2. Sedan validera/beräkna övriga fält (quantity, unit_price, discount) så att de stämmer med summan
    
    Args:
        line_items: List of InvoiceLine objects to validate
        tolerance: Validation tolerance in SEK (default 0.01 for rounding)
        
    Returns:
        List of warning messages for lines with validation issues
        
    Note:
        Uses PDF total_amount as primary (source of truth), but validates against
        calculated value to flag extraction errors. Also identifies discount type
        (percentage vs amount) and suggests corrected values if needed.
    """
    warnings = []
    
    for line in line_items:
        # Use comprehensive validation and confidence scoring
        confidence, validation_info = validate_and_score_invoice_line(line)
        
        # Add warnings from validation
        for warning in validation_info.get('warnings', []):
            warnings.append(f"Rad {line.line_number}: {warning}")
        
        # Add information about discount type if identified
        discount_type = validation_info.get('discount_type')
        if discount_type and line.discount is not None:
            if discount_type == 'percent':
                discount_pct = line.discount * 100
                warnings.append(
                    f"Rad {line.line_number}: Rabatt identifierad som procent ({discount_pct:.1f}%)"
                )
            else:
                warnings.append(
                    f"Rad {line.line_number}: Rabatt identifierad som belopp ({line.discount:.2f} SEK)"
                )
        
        # Add calculated field suggestions if available
        calculated_fields = validation_info.get('calculated_fields', {})
        if calculated_fields:
            suggestions = []
            if 'unit_price' in calculated_fields:
                suggestions.append(f"Föreslaget a-pris: {calculated_fields['unit_price']:.2f} SEK")
            if 'quantity' in calculated_fields:
                suggestions.append(f"Föreslaget antal: {calculated_fields['quantity']}")
            if 'discount' in calculated_fields:
                discount_val = calculated_fields['discount']
                discount_type_calc = calculated_fields.get('discount_type', 'amount')
                if discount_type_calc == 'percent':
                    suggestions.append(f"Föreslaget rabatt: {discount_val * 100:.1f}%")
                else:
                    suggestions.append(f"Föreslaget rabatt: {discount_val:.2f} SEK")
            
            if suggestions:
                warnings.append(
                    f"Rad {line.line_number}: Beräknade värden - {', '.join(suggestions)}"
                )
    
    return warnings


def calculate_validation_values(
    total_amount: Optional[float],
    line_items: List[InvoiceLine],
    tolerance: float = 1.0
) -> Tuple[float, Optional[float], bool]:
    """Calculate validation values (lines_sum, diff, validation_passed).
    
    Args:
        total_amount: Extracted total amount (can be None)
        line_items: List of InvoiceLine objects
        tolerance: Validation tolerance in SEK
        
    Returns:
        Tuple of (lines_sum, diff, validation_passed)
        - lines_sum: SUM of all line item totals (always calculated)
        - diff: total_amount - lines_sum (signed difference, None if total_amount is None)
        - validation_passed: True if abs(diff) <= tolerance (False if diff is None)
    """
    lines_sum = sum(line.total_amount for line in line_items) if line_items else 0.0
    
    if total_amount is None:
        return lines_sum, None, False
    
    diff = total_amount - lines_sum
    validation_passed = validate_total_against_line_items(total_amount, line_items, tolerance)
    
    return lines_sum, diff, validation_passed


def validate_invoice(
    invoice_header: InvoiceHeader,
    line_items: List[InvoiceLine]
) -> ValidationResult:
    """Validate invoice and assign status (OK/PARTIAL/REVIEW).
    
    Args:
        invoice_header: InvoiceHeader with extracted fields and confidence scores
        line_items: List of InvoiceLine objects
        
    Returns:
        ValidationResult with status, validation values, errors, and warnings
        
    Status assignment logic:
    1. Check hard gate: invoice_number_confidence >= 0.95 AND total_confidence >= 0.95
    2. Calculate lines_sum and diff
    3. Assign status:
       - Hard gate fail → REVIEW
       - total_amount None → REVIEW (cannot validate)
       - No line_items → REVIEW (cannot validate)
       - Hard gate pass + diff <= ±1 SEK → OK
       - Hard gate pass + diff > ±1 SEK → PARTIAL
    """
    # Step 1: Check hard gate
    hard_gate_passed = invoice_header.meets_hard_gate()
    
    # Step 2: Calculate validation values
    lines_sum, diff, validation_passed = calculate_validation_values(
        invoice_header.total_amount,
        line_items,
        tolerance=1.0
    )
    
    # Step 3: Assign status
    errors = []
    warnings = []
    
    # Step 3a: Validate individual line items (quantity × unit_price ≈ total_amount)
    line_item_warnings = validate_line_items(line_items, tolerance=0.01)
    warnings.extend(line_item_warnings)
    
    if not hard_gate_passed:
        status = "REVIEW"
        errors.append(
            f"Hard gate failed: invoice_number_confidence={invoice_header.invoice_number_confidence:.2f}, "
            f"total_confidence={invoice_header.total_confidence:.2f}"
        )
    elif invoice_header.total_amount is None:
        status = "REVIEW"
        errors.append("Total amount not extracted (confidence < 0.95)")
    elif not line_items:
        status = "REVIEW"
        errors.append("No invoice lines extracted (cannot validate)")
    elif validation_passed:
        status = "OK"
    else:
        status = "PARTIAL"
        warnings.append(f"Sum mismatch: diff={diff:.2f} SEK (tolerance: ±1.0 SEK)")
    
    return ValidationResult(
        status=status,
        lines_sum=lines_sum,
        diff=diff,
        tolerance=1.0,
        hard_gate_passed=hard_gate_passed,
        invoice_number_confidence=invoice_header.invoice_number_confidence,
        total_confidence=invoice_header.total_confidence,
        errors=errors,
        warnings=warnings
    )


def validation_passed(result: Optional[ValidationResult]) -> bool:
    """Return True when total matches line_items_sum within tolerance."""
    if result is None:
        return False
    if result.diff is None:
        return False
    return abs(result.diff) <= result.tolerance

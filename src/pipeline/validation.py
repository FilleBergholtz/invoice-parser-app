"""Validation logic for invoice data with status assignment."""

from typing import List, Optional, Tuple

from ..models.invoice_header import InvoiceHeader
from ..models.invoice_line import InvoiceLine
from ..models.validation_result import ValidationResult
from ..pipeline.confidence_scoring import validate_total_against_line_items


def validate_line_items(
    line_items: List[InvoiceLine],
    tolerance: float = 0.01
) -> List[str]:
    """Validate each line item: quantity × unit_price ≈ total_amount.
    
    Args:
        line_items: List of InvoiceLine objects to validate
        tolerance: Validation tolerance in SEK (default 0.01 for rounding)
        
    Returns:
        List of warning messages for lines where quantity × unit_price ≠ total_amount
        
    Note:
        Uses PDF total_amount as primary (source of truth), but validates against
        calculated value to flag extraction errors.
    """
    warnings = []
    
    # Edge case units that may have complex extraction issues
    edge_case_units = ['ea', 'ltr', 'månad', 'day', 'xpa']
    
    for line in line_items:
        # Only validate if both quantity and unit_price are present
        if line.quantity is not None and line.unit_price is not None:
            calculated_total = line.quantity * line.unit_price
            difference = abs(calculated_total - line.total_amount)
            
            # Flag if difference exceeds tolerance (rounding/rabatt allowed)
            if difference > tolerance:
                # Check if this is an edge case unit that may require manual review
                is_edge_case = line.unit and line.unit.lower() in edge_case_units
                
                # Check if difference is significant (likely extraction error, not just rounding)
                is_significant_error = difference > 1.0
                
                if is_edge_case and is_significant_error:
                    # Large difference with edge case unit - likely requires manual review
                    warnings.append(
                        f"Rad {line.line_number}: "
                        f"Antal × A-pris ({calculated_total:.2f}) ≠ Summa ({line.total_amount:.2f}), "
                        f"avvikelse: {difference:.2f} SEK. "
                        f"⚠️ Kräver manuell granskning (edge case med enhet {line.unit.upper()})"
                    )
                else:
                    warnings.append(
                        f"Rad {line.line_number}: "
                        f"Antal × A-pris ({calculated_total:.2f}) ≠ Summa ({line.total_amount:.2f}), "
                        f"avvikelse: {difference:.2f} SEK"
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

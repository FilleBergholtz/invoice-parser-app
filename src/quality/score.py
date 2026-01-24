"""Quality score calculation for invoices."""

from typing import List, Optional

from ..models.invoice_header import InvoiceHeader
from ..models.invoice_line import InvoiceLine
from ..models.validation_result import ValidationResult
from .model import QualityScore


def count_missing_fields(invoice_header: InvoiceHeader) -> tuple[int, int]:
    """Count missing required and optional fields.
    
    Args:
        invoice_header: InvoiceHeader to check
        
    Returns:
        Tuple of (required_missing, optional_missing)
        
    Required fields:
        - invoice_number
        - invoice_date
        - total_amount
        
    Optional fields:
        - supplier_name
        - customer_name
    """
    required_missing = 0
    optional_missing = 0
    
    # Required fields
    if not invoice_header.invoice_number:
        required_missing += 1
    if not invoice_header.invoice_date:
        required_missing += 1
    if invoice_header.total_amount is None:
        required_missing += 1
    
    # Optional fields
    if not invoice_header.supplier_name:
        optional_missing += 1
    if not invoice_header.customer_name:
        optional_missing += 1
    
    return required_missing, optional_missing


def calculate_wrap_complexity(line_items: List[InvoiceLine]) -> float:
    """Calculate wrap complexity score.
    
    Args:
        line_items: List of InvoiceLine objects
        
    Returns:
        Complexity score (0.0 = no wraps, higher = more complex)
        Based on: average rows per line, max rows per line
    """
    if not line_items:
        return 0.0
    
    total_rows = sum(len(line.rows) for line in line_items)
    avg_rows_per_line = total_rows / len(line_items)
    max_rows_per_line = max(len(line.rows) for line in line_items) if line_items else 1
    
    # Complexity increases with:
    # - Average rows > 1 (wrapped lines)
    # - Max rows > 2 (very long wraps)
    complexity = 0.0
    
    # Penalty for average wraps
    if avg_rows_per_line > 1.0:
        complexity += (avg_rows_per_line - 1.0) * 2.0  # 2 points per extra row on average
    
    # Penalty for max wraps
    if max_rows_per_line > 2:
        complexity += (max_rows_per_line - 2) * 3.0  # 3 points per extra row in max
    
    return min(complexity, 20.0)  # Cap at 20 points


def calculate_quality_score(
    validation_result: ValidationResult,
    invoice_header: InvoiceHeader,
    line_items: List[InvoiceLine]
) -> QualityScore:
    """Calculate quality score for an invoice (0-100).
    
    Args:
        validation_result: ValidationResult with status and validation data
        invoice_header: InvoiceHeader with extracted fields
        line_items: List of InvoiceLine objects
        
    Returns:
        QualityScore with score and breakdown
    """
    # Start with perfect score (100)
    base_score = 100.0
    
    # 1. Status penalty (0-40 points)
    status_penalty = 0.0
    if validation_result.status == "REVIEW":
        status_penalty = 40.0
    elif validation_result.status == "PARTIAL":
        status_penalty = 15.0
    # OK status: no penalty
    
    # 2. Missing fields penalty (0-30 points)
    required_missing, optional_missing = count_missing_fields(invoice_header)
    missing_fields_penalty = (required_missing * 10.0) + (optional_missing * 2.0)
    missing_fields_penalty = min(missing_fields_penalty, 30.0)  # Cap at 30
    
    # 3. Reconciliation penalty (0-20 points)
    reconciliation_penalty = 0.0
    if validation_result.diff is not None:
        abs_diff = abs(validation_result.diff)
        if abs_diff <= 0.01:
            # Perfect match (within rounding tolerance)
            reconciliation_penalty = 0.0
        elif abs_diff <= 1.0:
            # Small difference (within tolerance)
            reconciliation_penalty = abs_diff * 2.0  # 2 points per SEK
        elif abs_diff <= 10.0:
            # Medium difference
            reconciliation_penalty = 2.0 + (abs_diff - 1.0) * 1.5  # 2 + 1.5 per SEK over 1
        else:
            # Large difference
            reconciliation_penalty = 15.5 + min((abs_diff - 10.0) * 0.5, 4.5)  # Cap at 20
        
        reconciliation_penalty = min(reconciliation_penalty, 20.0)
    else:
        # No total_amount extracted - maximum penalty
        reconciliation_penalty = 20.0
    
    # 4. Wrap complexity penalty (0-10 points)
    wrap_complexity_penalty = calculate_wrap_complexity(line_items)
    
    # Calculate final score
    total_penalty = status_penalty + missing_fields_penalty + reconciliation_penalty + wrap_complexity_penalty
    final_score = max(0.0, base_score - total_penalty)
    
    # Create breakdown
    breakdown = {
        "base_score": base_score,
        "status": validation_result.status,
        "required_fields_missing": required_missing,
        "optional_fields_missing": optional_missing,
        "reconciliation_diff": validation_result.diff,
        "reconciliation_diff_abs": abs(validation_result.diff) if validation_result.diff is not None else None,
        "line_count": len(line_items),
        "avg_rows_per_line": sum(len(line.rows) for line in line_items) / len(line_items) if line_items else 0.0,
        "max_rows_per_line": max(len(line.rows) for line in line_items) if line_items else 0,
        "invoice_number_confidence": invoice_header.invoice_number_confidence,
        "total_confidence": invoice_header.total_confidence,
        "hard_gate_passed": validation_result.hard_gate_passed
    }
    
    return QualityScore(
        score=final_score,
        status_penalty=status_penalty,
        missing_fields_penalty=missing_fields_penalty,
        reconciliation_penalty=reconciliation_penalty,
        wrap_complexity_penalty=wrap_complexity_penalty,
        breakdown=breakdown
    )

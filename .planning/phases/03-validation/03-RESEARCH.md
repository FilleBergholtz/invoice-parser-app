# Phase 3: Validation - Research

**Researched:** 2026-01-17  
**Confidence:** HIGH  
**Context:** .planning/phases/03-validation/03-CONTEXT.md

## Executive Summary

Phase 3 implements validation and export features that complete the invoice parsing pipeline. Research focuses on: status assignment logic with hard gates and mathematical validation, ValidationResult data model, Excel export with control columns and percentage formatting, and review report generation with JSON serialization. Key finding: Reuse Phase 2 validation functions, create ValidationResult object to carry all validation data, extend Excel export with control columns, and generate review reports as self-contained JSON + PDF copies.

## Research Questions Addressed

1. **Status assignment:** How to implement OK/PARTIAL/REVIEW logic with hard gates and mathematical validation?
2. **ValidationResult model:** What structure for carrying validation data (status, lines_sum, diff, errors)?
3. **Excel control columns:** How to add control columns with Swedish names and percentage formatting?
4. **Review reports:** How to serialize InvoiceHeader + Traceability to JSON and copy PDFs to review folder?
5. **Integration:** How to integrate validation into CLI pipeline without breaking existing functionality?

## Key Findings

### 1. Status Assignment Logic

**Hard gate + mathematical validation pattern:**

Status assignment requires:
1. Check hard gate (`InvoiceHeader.meets_hard_gate()`)
2. Calculate mathematical validation (lines_sum, diff)
3. Assign status based on both conditions

**Implementation pattern:**
```python
def assign_status(invoice_header: InvoiceHeader, line_items: List[InvoiceLine]) -> ValidationResult:
    # Step 1: Check hard gate
    hard_gate_passed = invoice_header.meets_hard_gate()
    
    # Step 2: Calculate lines_sum
    lines_sum = sum(line.total_amount for line in line_items) if line_items else 0.0
    
    # Step 3: Calculate diff (if total_amount exists)
    if invoice_header.total_amount is not None:
        diff = invoice_header.total_amount - lines_sum
    else:
        diff = None  # Cannot calculate without total
    
    # Step 4: Assign status
    if not hard_gate_passed:
        status = "REVIEW"  # Hard gate failed
    elif invoice_header.total_amount is None:
        status = "REVIEW"  # Cannot validate without total
    elif not line_items:
        status = "REVIEW"  # Cannot validate without lines
    elif abs(diff) <= 1.0:  # Within tolerance
        status = "OK"
    else:
        status = "PARTIAL"  # Header confident, sum mismatch
    
    # Step 5: Generate errors/warnings
    errors = []
    warnings = []
    
    if status == "REVIEW":
        if not hard_gate_passed:
            errors.append(f"Hard gate failed: invoice_number_confidence={invoice_header.invoice_number_confidence:.2f}, total_confidence={invoice_header.total_confidence:.2f}")
        if invoice_header.total_amount is None:
            errors.append("Total amount not extracted (confidence < 0.95)")
        if not line_items:
            errors.append("No invoice lines extracted")
    elif status == "PARTIAL":
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
```

**Edge cases handled:**
- No line items → REVIEW (cannot validate)
- total_amount is None → REVIEW (cannot validate, hard gate likely failed)
- Hard gate pass but no lines → REVIEW (edge case, cannot validate)
- Hard gate pass but total is None → REVIEW (edge case, cannot validate)

**Key insight:** Hard gate must pass for OK/PARTIAL. Mathematical validation required for OK. PARTIAL indicates header confident but sum mismatch.

---

### 2. ValidationResult Data Model

**Dataclass structure for validation data:**

ValidationResult carries all validation data needed for Excel export and reporting:
- Status assignment result
- Mathematical validation values (lines_sum, diff)
- Confidence scores (for Excel)
- Errors/warnings (for reporting)

**Implementation pattern:**
```python
@dataclass
class ValidationResult:
    """Validation result for an invoice.
    
    Attributes:
        status: Invoice status ("OK", "PARTIAL", or "REVIEW")
        lines_sum: Sum of all InvoiceLine.total_amount
        diff: total_amount - lines_sum (signed, None if total_amount is None)
        tolerance: Validation tolerance (1.0 SEK)
        hard_gate_passed: True if both confidences >= 0.95
        invoice_number_confidence: Confidence score for invoice number
        total_confidence: Confidence score for total amount
        errors: List of validation error messages
        warnings: List of validation warning messages
    """
    status: str
    lines_sum: float
    diff: Optional[float]
    tolerance: float = 1.0
    hard_gate_passed: bool
    invoice_number_confidence: float
    total_confidence: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate ValidationResult fields."""
        if self.status not in ["OK", "PARTIAL", "REVIEW"]:
            raise ValueError(f"status must be 'OK', 'PARTIAL', or 'REVIEW', got '{self.status}'")
        
        if self.lines_sum < 0:
            raise ValueError(f"lines_sum must be >= 0, got {self.lines_sum}")
```

**Key insight:** ValidationResult is immutable result object that carries all data needed downstream (Excel export, review reports). Separation of concerns: validation logic separate from data models.

---

### 3. Excel Control Columns Integration

**Extend existing Excel export with control columns:**

Current Excel export uses pandas DataFrame with openpyxl for formatting. Control columns added after existing columns with Swedish names and proper formatting.

**Implementation pattern:**
```python
# Extend invoice_metadata dict (from CLI) with validation fields
invoice_metadata = {
    "fakturanummer": invoice_header.invoice_number or "TBD",
    "foretag": invoice_header.supplier_name or "TBD",
    "fakturadatum": invoice_header.invoice_date.isoformat() if invoice_header.invoice_date else "TBD",
    # NEW: Validation fields
    "status": validation_result.status,
    "lines_sum": validation_result.lines_sum,
    "diff": validation_result.diff if validation_result.diff is not None else "N/A",
    "invoice_number_confidence": invoice_header.invoice_number_confidence,
    "total_confidence": invoice_header.total_confidence,
}

# In export_to_excel(), add control columns after existing columns
row = {
    # Existing columns (unchanged)
    "Fakturanummer": fakturanummer,
    "Referenser": referenser,
    "Företag": foretag,
    "Fakturadatum": fakturadatum,
    "Beskrivning": line.description,
    "Antal": line.quantity if line.quantity is not None else "",
    "Enhet": line.unit if line.unit else "",
    "Á-pris": line.unit_price if line.unit_price is not None else "",
    "Rabatt": line.discount if line.discount is not None else "",
    "Summa": line.total_amount,
    "Hela summan": hela_summan,
    
    # NEW: Control columns (after existing)
    "Status": metadata.get("status", "REVIEW"),
    "Radsumma": metadata.get("lines_sum", 0.0),
    "Avvikelse": metadata.get("diff", "N/A"),
    "Fakturanummer-konfidens": metadata.get("invoice_number_confidence", 0.0) * 100,  # Convert to percentage
    "Totalsumma-konfidens": metadata.get("total_confidence", 0.0) * 100,  # Convert to percentage
}
```

**Excel formatting pattern:**
```python
from openpyxl.styles.numbers import FORMAT_PERCENTAGE_00, FORMAT_NUMBER_00

# Format control columns
for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
    # Status column (text, no formatting needed)
    # Radsumma column (currency)
    radsumma_cell = row[11]  # Column L (after Hela summan)
    radsumma_cell.number_format = FORMAT_NUMBER_00
    
    # Avvikelse column (signed number or text "N/A")
    avvikelse_cell = row[12]  # Column M
    if isinstance(avvikelse_cell.value, (int, float)):
        avvikelse_cell.number_format = FORMAT_NUMBER_00
    # else: text "N/A", no formatting
    
    # Confidence columns (percentage)
    fakturanummer_konfidens_cell = row[13]  # Column N
    totalsumma_konfidens_cell = row[14]  # Column O
    fakturanummer_konfidens_cell.number_format = FORMAT_PERCENTAGE_00
    totalsumma_konfidens_cell.number_format = FORMAT_PERCENTAGE_00
```

**Key insight:** Extend metadata dict (minimal API change). Control columns repeat per row (same value for all rows of same invoice). Percentage formatting: multiply by 100 before writing (0.95 → 95), then use FORMAT_PERCENTAGE_00.

---

### 4. Review Reports Generation

**JSON serialization pattern:**

Review reports need to serialize InvoiceHeader, Traceability objects, and ValidationResult to JSON for review folder export.

**Implementation pattern:**
```python
import json
import shutil
from pathlib import Path

def create_review_report(
    invoice_header: InvoiceHeader,
    validation_result: ValidationResult,
    line_items: List[InvoiceLine],
    pdf_path: str,
    output_dir: Path
) -> Path:
    """Create review report (folder with PDF + metadata.json).
    
    Args:
        invoice_header: InvoiceHeader with extracted fields
        validation_result: ValidationResult with status and validation data
        line_items: List of InvoiceLine objects
        pdf_path: Path to original PDF
        output_dir: Output directory (parent of review folder)
        
    Returns:
        Path to review folder
    """
    # Create review folder
    pdf_filename = Path(pdf_path).stem
    review_folder = output_dir / "review" / pdf_filename
    review_folder.mkdir(parents=True, exist_ok=True)
    
    # Copy PDF
    review_pdf_path = review_folder / f"{pdf_filename}.pdf"
    shutil.copy2(pdf_path, review_pdf_path)
    
    # Serialize InvoiceHeader to dict
    header_dict = {
        "invoice_number": invoice_header.invoice_number,
        "invoice_number_confidence": invoice_header.invoice_number_confidence,
        "total_amount": invoice_header.total_amount,
        "total_confidence": invoice_header.total_confidence,
        "supplier_name": invoice_header.supplier_name,
        "invoice_date": invoice_header.invoice_date.isoformat() if invoice_header.invoice_date else None,
        # Traceability (serialize Traceability objects)
        "invoice_number_traceability": invoice_header.invoice_number_traceability.to_dict() if invoice_header.invoice_number_traceability else None,
        "total_traceability": invoice_header.total_traceability.to_dict() if invoice_header.total_traceability else None,
    }
    
    # Serialize ValidationResult to dict
    validation_dict = {
        "status": validation_result.status,
        "lines_sum": validation_result.lines_sum,
        "diff": validation_result.diff,
        "tolerance": validation_result.tolerance,
        "hard_gate_passed": validation_result.hard_gate_passed,
        "invoice_number_confidence": validation_result.invoice_number_confidence,
        "total_confidence": validation_result.total_confidence,
        "errors": validation_result.errors,
        "warnings": validation_result.warnings,
        "line_count": len(line_items),
    }
    
    # Combine into metadata structure
    metadata = {
        "invoice_header": header_dict,
        "validation": validation_dict,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Write JSON
    metadata_path = review_folder / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return review_folder
```

**PDF copying pattern:**
- Use `shutil.copy2()` (preserves metadata/timestamps)
- Filename: use original PDF filename (stem + .pdf)
- Error handling: Continue even if copy fails (don't break batch)

**Key insight:** JSON serialization uses `to_dict()` methods from InvoiceHeader and Traceability. Review folder structure: one folder per invoice, PDF copy + metadata.json. Self-contained for archiving.

---

### 5. Batch Export Integration

**Multi-invoice batch handling:**

Current batch processing collects all invoice_lines and exports to one Excel file. With validation, each invoice has its own ValidationResult. Control columns must repeat same value for all rows of same invoice.

**Implementation pattern:**
```python
# In process_batch(), track validation results per invoice
invoice_results = []  # List of dicts: {invoice_header, validation_result, invoice_lines, pdf_path}

for pdf_file in pdf_files:
    result = process_invoice(str(pdf_file), str(output_dir), verbose)
    
    # Run validation
    if result["invoice_header"] and result["invoice_lines"]:
        validation_result = validate_invoice(result["invoice_header"], result["invoice_lines"])
        
        invoice_results.append({
            "invoice_header": result["invoice_header"],
            "validation_result": validation_result,
            "invoice_lines": result["invoice_lines"],
            "pdf_path": str(pdf_file),
            "filename": pdf_file.name,
        })
        
        # Create review report if REVIEW status
        if validation_result.status == "REVIEW":
            create_review_report(
                result["invoice_header"],
                validation_result,
                result["invoice_lines"],
                str(pdf_file),
                output_dir_obj
            )

# Flatten invoice_lines with validation data for Excel
all_excel_rows = []
for invoice_result in invoice_results:
    invoice_header = invoice_result["invoice_header"]
    validation_result = invoice_result["validation_result"]
    invoice_lines = invoice_result["invoice_lines"]
    
    # Prepare metadata with validation fields
    invoice_metadata = {
        "fakturanummer": invoice_header.invoice_number or "TBD",
        "foretag": invoice_header.supplier_name or "TBD",
        "fakturadatum": invoice_header.invoice_date.isoformat() if invoice_header.invoice_date else "TBD",
        "status": validation_result.status,
        "lines_sum": validation_result.lines_sum,
        "diff": validation_result.diff if validation_result.diff is not None else "N/A",
        "invoice_number_confidence": invoice_header.invoice_number_confidence,
        "total_confidence": invoice_header.total_confidence,
    }
    
    # Add rows (validation data repeats for all rows of same invoice)
    for line in invoice_lines:
        all_excel_rows.append((line, invoice_metadata))

# Export to Excel (all invoices, one file)
export_to_excel(all_excel_rows, excel_path)  # Modified signature
```

**Key insight:** Group invoice_lines by invoice, attach validation data to metadata dict. Control columns repeat same value for all rows of same invoice. One consolidated Excel file with Status column for filtering.

---

### 6. Mathematical Validation Reuse

**Reuse Phase 2 validation function:**

Mathematical validation already implemented in `confidence_scoring.py:validate_total_against_line_items()`. Reuse this function for Phase 3 status assignment, but also calculate and store lines_sum and diff for reporting.

**Implementation pattern:**
```python
from ..pipeline.confidence_scoring import validate_total_against_line_items

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
        - diff: total_amount - lines_sum (None if total_amount is None)
        - validation_passed: True if abs(diff) <= tolerance (False if diff is None)
    """
    lines_sum = sum(line.total_amount for line in line_items) if line_items else 0.0
    
    if total_amount is None:
        return lines_sum, None, False
    
    diff = total_amount - lines_sum
    validation_passed = validate_total_against_line_items(total_amount, line_items, tolerance)
    
    return lines_sum, diff, validation_passed
```

**Key insight:** Reuse Phase 2 validation function. Calculate lines_sum and diff separately for Excel export (even if validation fails). Diff is signed (can be negative) for Excel reporting.

---

## Architecture Patterns

### Pipeline Integration

**Execution order:**
1. After header/footer extraction (Phase 2)
2. Run validation: `validation_result = validate_invoice(invoice_header, invoice_lines)`
3. Update status in result dict
4. Export Excel with validation data
5. Create review reports for REVIEW status invoices

**Data flow:**
```
Document → Segments → InvoiceHeader + InvoiceLines
  → ValidationResult (status, lines_sum, diff, errors, warnings)
  → Excel Export (with control columns)
  → Review Reports (REVIEW status only)
```

### Validation Module Structure

**New module:** `src/pipeline/validation.py`

**Exports:**
- `ValidationResult` dataclass
- `validate_invoice(invoice_header: InvoiceHeader, line_items: List[InvoiceLine]) -> ValidationResult`
- `calculate_validation_values(total_amount: Optional[float], line_items: List[InvoiceLine], tolerance: float) -> Tuple[float, Optional[float], bool]`

**Dependencies:**
- `InvoiceHeader.meets_hard_gate()` (exists)
- `validate_total_against_line_items()` from `confidence_scoring.py` (exists)

---

## Implementation Recommendations

### Priority 1: Validation Module

1. Create `ValidationResult` dataclass
2. Implement `validate_invoice()` function with status assignment logic
3. Reuse `validate_total_against_line_items()` from Phase 2
4. Handle all edge cases (None values, empty lists, etc.)

### Priority 2: Excel Export Extension

1. Extend `export_to_excel()` to accept validation data via metadata dict
2. Add control columns after existing columns
3. Format control columns (percentage for confidence, currency for amounts)
4. Handle "N/A" for diff when total_amount is None

### Priority 3: Review Reports

1. Create `create_review_report()` function
2. Serialize InvoiceHeader and Traceability to JSON (use `to_dict()` methods)
3. Copy PDF to review folder using `shutil.copy2()`
4. Create folder structure: `review/{invoice_filename}/`

### Priority 4: CLI Integration

1. Integrate validation step in `process_invoice()`
2. Update `process_batch()` to collect validation results
3. Create review reports for REVIEW status invoices
4. Pass validation data to Excel export

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Excel formatting breaks with percentage values | Medium | Test percentage formatting (0.95 → 95%, not 95.00) |
| Review folder creation fails (permissions) | Low | Use `mkdir(parents=True, exist_ok=True)`, continue on error |
| PDF copy fails (file locked, missing) | Low | Use try/except, continue on error, log warning |
| Batch export mixes validation data between invoices | High | Group invoice_lines by invoice, attach validation to metadata per invoice |
| Status assignment logic incorrect | High | Comprehensive edge case testing, validate against 03-CONTEXT.md logic |

---

## Codebase Integration Points

**Existing code to extend:**
- `src/pipeline/confidence_scoring.py` - Reuse `validate_total_against_line_items()`
- `src/export/excel_export.py` - Extend with control columns
- `src/cli/main.py` - Integrate validation step, create review reports
- `src/models/invoice_header.py` - Reuse `meets_hard_gate()` method
- `src/models/traceability.py` - Reuse `to_dict()` method for JSON serialization

**New code to create:**
- `src/pipeline/validation.py` - ValidationResult model and validate_invoice() function
- `src/export/review_report.py` - Review report generation (create_review_report function)
- Tests: `tests/test_validation.py`, `tests/test_review_report.py`

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Status assignment logic | HIGH | Clear logic from 03-CONTEXT.md, all edge cases defined |
| ValidationResult model | HIGH | Standard dataclass pattern, similar to Traceability |
| Excel control columns | HIGH | Extend existing export pattern, percentage formatting standard |
| Review reports | HIGH | JSON serialization pattern established, PDF copying straightforward |
| Batch integration | HIGH | Grouping pattern clear, minimal API changes to Excel export |

**Overall confidence:** HIGH

## Gaps to Address During Planning

- **Excel percentage formatting:** Verify openpyxl percentage format (0.95 → 95% vs 95.00%)
- **Batch grouping:** Ensure invoice_lines are correctly grouped with their validation data (not mixed between invoices)
- **Review folder naming:** Use PDF filename (stem) or invoice number? (Recommendation: PDF filename for uniqueness)

---

## Sources

### Primary (HIGH confidence)
- Phase 3 Context: .planning/phases/03-validation/03-CONTEXT.md (all decisions confirmed)
- Validation rules: docs/05_validation.md (validation patterns, but uses WARNING - we use PARTIAL)
- Phase 2 codebase: src/pipeline/confidence_scoring.py (validation function to reuse)
- Excel export: src/export/excel_export.py (existing export pattern to extend)
- Traceability: src/models/traceability.py (to_dict() method for JSON serialization)

### Secondary (MEDIUM confidence)
- Phase 2 Research: .planning/phases/02-header-wrap/02-RESEARCH.md (confidence scoring patterns)
- CLI patterns: src/cli/main.py (batch processing, JSON error reporting)

---

*Research completed: 2026-01-17*  
*Ready for planning: yes*

"""Review report generation for REVIEW status invoices."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from ..models.invoice_header import InvoiceHeader
from ..models.invoice_line import InvoiceLine
from ..models.validation_result import ValidationResult


def _sanitize_for_json(obj: Any) -> Any:
    """Ensure JSON-serializable; convert numpy.bool_/int64/float64 etc. to Python native."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, (str, int, float, type(None), bool)):
        return obj
    if hasattr(obj, "item") and callable(getattr(obj, "item")):
        return _sanitize_for_json(obj.item())
    return obj


def create_review_report(
    invoice_header: InvoiceHeader,
    validation_result: ValidationResult,
    line_items: List[InvoiceLine],
    pdf_path: str,
    output_dir: Path,
    virtual_invoice_id: Optional[str] = None
) -> Path:
    """Create review report (folder with PDF + metadata.json).
    
    Args:
        invoice_header: InvoiceHeader with extracted fields
        validation_result: ValidationResult with status and validation data
        line_items: List of InvoiceLine objects
        pdf_path: Path to original PDF
        output_dir: Output directory (parent of review folder)
        virtual_invoice_id: Optional virtual invoice ID (format: "{file_stem}__{index}").
                           If provided, used for folder name. Otherwise uses PDF filename stem.
        
    Returns:
        Path to review folder
        
    Creates:
    - review/{virtual_invoice_id or pdf_filename}/ folder
    - {pdf_filename}.pdf (copy of original)
    - metadata.json (InvoiceHeader + Traceability + Validation data)
    """
    # Create review folder (use virtual_invoice_id if provided)
    if virtual_invoice_id:
        folder_name = virtual_invoice_id
    else:
        folder_name = Path(pdf_path).stem
    review_folder = output_dir / "review" / folder_name
    review_folder.mkdir(parents=True, exist_ok=True)
    
    # Copy PDF (use original PDF filename)
    pdf_filename = Path(pdf_path).name
    review_pdf_path = review_folder / pdf_filename
    try:
        shutil.copy2(pdf_path, review_pdf_path)
    except Exception as e:
        # Log warning but continue (don't break batch)
        print(f"Warning: Failed to copy PDF to review folder: {e}")
    
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
    
    metadata = {
        "invoice_header": header_dict,
        "validation": validation_dict,
        "timestamp": datetime.now().isoformat(),
    }
    metadata = _sanitize_for_json(metadata)
    metadata_path = review_folder / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return review_folder

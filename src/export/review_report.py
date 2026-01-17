"""Review report generation for REVIEW status invoices."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from ..models.invoice_header import InvoiceHeader
from ..models.invoice_line import InvoiceLine
from ..models.validation_result import ValidationResult


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
        
    Creates:
    - review/{invoice_filename}/ folder
    - {invoice_filename}.pdf (copy of original)
    - metadata.json (InvoiceHeader + Traceability + Validation data)
    """
    # Create review folder
    pdf_filename = Path(pdf_path).stem
    review_folder = output_dir / "review" / pdf_filename
    review_folder.mkdir(parents=True, exist_ok=True)
    
    # Copy PDF
    review_pdf_path = review_folder / f"{pdf_filename}.pdf"
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

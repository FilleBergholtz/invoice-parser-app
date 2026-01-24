"""Batch processing runner with isolated execution per PDF."""

from pathlib import Path
from typing import Dict, List, Optional
import uuid
from datetime import datetime

# Import process_pdf locally to avoid circular import
# We'll import it inside the function when needed
from ..run_summary import RunSummary
from ..config import get_output_subdirs
from ..quality.score import calculate_quality_score


def process_pdf_isolated(
    pdf_path: Path,
    output_dir: Path,
    verbose: bool = False
) -> Dict:
    """Process a single PDF in isolation with its own artifacts directory.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Base output directory
        verbose: Enable verbose output
        
    Returns:
        Dict with processing results:
        - filename: PDF filename
        - status: Overall status (OK/PARTIAL/REVIEW/FAILED)
        - quality_score: Quality score (0-100)
        - output_path: Path to generated Excel file (if any)
        - error: Error message (if failed)
        - virtual_invoices: List of virtual invoice results
    """
    pdf_stem = pdf_path.stem
    pdf_name = pdf_path.name
    
    # Create isolated artifacts directory for this PDF
    pdf_artifacts_dir = output_dir / "artifacts" / f"{pdf_stem}_{uuid.uuid4().hex[:8]}"
    pdf_artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectory structure for this PDF
    pdf_output_dir = output_dir / "batch" / pdf_stem
    pdf_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process PDF (may return multiple virtual invoices)
    # Import here to avoid circular import
    from ..cli.main import process_pdf
    
    try:
        virtual_results = process_pdf(str(pdf_path), str(pdf_output_dir), verbose)
        
        if not virtual_results:
            return {
                "filename": pdf_name,
                "status": "FAILED",
                "quality_score": 0.0,
                "output_path": None,
                "error": "No invoices found in PDF",
                "virtual_invoices": []
            }
        
        # Process each virtual invoice
        best_status = "OK"
        best_quality_score = 100.0
        output_paths = []
        virtual_invoice_data = []
        
        for virtual_result in virtual_results:
            # Determine status
            if virtual_result.status == "FAILED":
                best_status = "FAILED"
                virtual_invoice_data.append({
                    "virtual_invoice_id": virtual_result.virtual_invoice_id,
                    "status": "FAILED",
                    "quality_score": 0.0,
                    "error": virtual_result.error
                })
                continue
            
            # Calculate quality score if validation result exists
            quality_score = 0.0
            if virtual_result.validation_result and virtual_result.invoice_header:
                quality_score_obj = calculate_quality_score(
                    virtual_result.validation_result,
                    virtual_result.invoice_header,
                    virtual_result.invoice_lines
                )
                quality_score = quality_score_obj.score
                
                # Track best status and quality score
                if virtual_result.validation_result.status == "REVIEW":
                    if best_status == "OK":
                        best_status = "PARTIAL"
                    best_status = "REVIEW"
                elif virtual_result.validation_result.status == "PARTIAL":
                    if best_status == "OK":
                        best_status = "PARTIAL"
                elif virtual_result.validation_result.status == "OK":
                    if best_status not in ["PARTIAL", "REVIEW"]:
                        best_status = "OK"
                
                if quality_score < best_quality_score:
                    best_quality_score = quality_score
            
            virtual_invoice_data.append({
                "virtual_invoice_id": virtual_result.virtual_invoice_id,
                "status": virtual_result.validation_result.status if virtual_result.validation_result else "REVIEW",
                "quality_score": quality_score,
                "error": None
            })
        
        # Find output Excel file (if any)
        excel_files = list(pdf_output_dir.glob("*.xlsx"))
        output_path = str(excel_files[0]) if excel_files else None
        
        return {
            "filename": pdf_name,
            "status": best_status,
            "quality_score": best_quality_score,
            "output_path": output_path,
            "error": None,
            "virtual_invoices": virtual_invoice_data
        }
        
    except Exception as e:
        return {
            "filename": pdf_name,
            "status": "FAILED",
            "quality_score": 0.0,
            "output_path": None,
            "error": str(e),
            "virtual_invoices": []
        }


def run_batch(
    input_dir: Path,
    output_dir: Path,
    fail_fast: bool = False,
    verbose: bool = False
) -> Dict:
    """Run batch processing on a directory of PDFs.
    
    Args:
        input_dir: Directory containing PDF files
        output_dir: Output directory for results
        fail_fast: Stop on first error if True
        verbose: Enable verbose output
        
    Returns:
        Dict with batch results:
        - total_files: Total number of PDFs found
        - processed: Number successfully processed
        - ok: Number with OK status
        - partial: Number with PARTIAL status
        - review: Number with REVIEW status
        - failed: Number that failed
        - results: List of per-PDF results
        - batch_summary_path: Path to batch_summary.xlsx
    """
    # Find all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        raise ValueError(f"No PDF files found in: {input_dir}")
    
    # Setup output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each PDF
    results = []
    stats = {
        "total_files": len(pdf_files),
        "processed": 0,
        "ok": 0,
        "partial": 0,
        "review": 0,
        "failed": 0
    }
    
    for i, pdf_file in enumerate(pdf_files, start=1):
        if verbose:
            print(f"Processing {i}/{stats['total_files']}: {pdf_file.name}")
        
        try:
            result = process_pdf_isolated(pdf_file, output_dir, verbose)
            results.append(result)
            
            # Update statistics
            if result["status"] == "OK":
                stats["ok"] += 1
                stats["processed"] += 1
            elif result["status"] == "PARTIAL":
                stats["partial"] += 1
                stats["processed"] += 1
            elif result["status"] == "REVIEW":
                stats["review"] += 1
                stats["processed"] += 1
            elif result["status"] == "FAILED":
                stats["failed"] += 1
                
                if fail_fast:
                    break
        except Exception as e:
            # Error processing PDF
            results.append({
                "filename": pdf_file.name,
                "status": "FAILED",
                "quality_score": 0.0,
                "output_path": None,
                "error": str(e),
                "virtual_invoices": []
            })
            stats["failed"] += 1
            
            if fail_fast:
                break
    
    return {
        **stats,
        "results": results
    }

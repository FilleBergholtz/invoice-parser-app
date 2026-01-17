"""CLI interface for invoice parser with batch processing."""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber

from ..models.document import Document
from ..models.invoice_line import InvoiceLine
from ..pipeline.invoice_line_parser import extract_invoice_lines
from ..pipeline.pdf_detection import detect_pdf_type, route_extraction_path
from ..pipeline.reader import read_pdf, PDFReadError
from ..pipeline.row_grouping import group_tokens_to_rows
from ..pipeline.segment_identification import identify_segments
from ..pipeline.tokenizer import extract_tokens_from_page
from ..export.excel_export import export_to_excel


class InvoiceProcessingError(Exception):
    """Raised when invoice processing fails."""
    pass


def process_invoice(
    pdf_path: str,
    output_dir: str,
    verbose: bool = False
) -> Dict:
    """Process a single invoice PDF.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Output directory for Excel files
        verbose: Enable verbose output
        
    Returns:
        Dict with status and results:
        - status: "OK", "PARTIAL", "REVIEW", or "FAILED"
        - line_count: Number of line items extracted
        - invoice_lines: List of InvoiceLine objects
        - error: Error message if failed
    """
    try:
        # Step 1: Read PDF
        doc = read_pdf(pdf_path)
        
        # Step 2: Detect PDF type and route
        pdf_type = detect_pdf_type(doc)
        extraction_path = route_extraction_path(doc)
        
        # Step 3: Extract tokens from all pages
        all_invoice_lines = []
        all_segments = []  # Collect segments from all pages
        line_number_global = 1
        
        for page in doc.pages:
            if extraction_path == "pdfplumber":
                # Searchable PDF path
                pdf = pdfplumber.open(doc.filepath)
                pdfplumber_page = pdf.pages[page.page_number - 1]
                tokens = extract_tokens_from_page(page, pdfplumber_page)
                pdf.close()
            else:
                # OCR path - would require rendering and OCR
                # For Phase 1, skip OCR path (requires rendered images)
                if verbose:
                    print(f"  Warning: OCR path not yet implemented for {pdf_path}")
                tokens = []
            
            if not tokens:
                continue
            
            # Step 4: Group tokens to rows
            rows = group_tokens_to_rows(tokens)
            
            # Step 5: Identify segments
            segments = identify_segments(rows, page)
            all_segments.extend(segments)  # Collect for footer extraction
            
            # Step 6: Extract line items from items segment
            items_segment = next((s for s in segments if s.segment_type == "items"), None)
            
            if items_segment:
                invoice_lines = extract_invoice_lines(items_segment)
                
                # Assign global line numbers
                for line in invoice_lines:
                    line.line_number = line_number_global
                    line_number_global += 1
                
                all_invoice_lines.extend(invoice_lines)
        
        # Step 7: Extract header fields and total amount
        # Find header segment (from first page)
        header_segment = None
        if doc.pages:
            first_page_segments = [s for s in all_segments if s.page == doc.pages[0]]
            header_segment = next((s for s in first_page_segments if s.segment_type == "header"), None)
        
        # Find footer segment (from last page, or all pages)
        footer_segment = None
        if doc.pages:
            last_page_segments = [s for s in all_segments if s.page == doc.pages[-1]]
            footer_segment = next((s for s in last_page_segments if s.segment_type == "footer"), None)
        
        # Create InvoiceHeader
        invoice_header = None
        if header_segment:
            invoice_header = InvoiceHeader(segment=header_segment)
        
        # Extract total amount from footer
        if footer_segment and invoice_header:
            extract_total_amount(footer_segment, all_invoice_lines, invoice_header)
        
        return {
            "status": "OK" if all_invoice_lines else "PARTIAL",
            "line_count": len(all_invoice_lines),
            "invoice_lines": all_invoice_lines,
            "invoice_header": invoice_header,
            "error": None
        }
        
    except PDFReadError as e:
        return {
            "status": "FAILED",
            "line_count": 0,
            "invoice_lines": [],
            "error": f"PDF read error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "line_count": 0,
            "invoice_lines": [],
            "error": f"Processing error: {str(e)}"
        }


def process_batch(
    input_path: str,
    output_dir: str,
    fail_fast: bool = False,
    verbose: bool = False
) -> Dict:
    """Process multiple invoice PDFs in batch.
    
    Args:
        input_path: Input directory or file list
        output_dir: Output directory for Excel files and errors
        fail_fast: Stop on first error if True
        verbose: Enable verbose output
        
    Returns:
        Dict with batch processing results
    """
    # Determine input files
    input_path_obj = Path(input_path)
    
    if input_path_obj.is_dir():
        pdf_files = list(input_path_obj.glob("*.pdf"))
    elif input_path_obj.is_file():
        pdf_files = [input_path_obj]
    else:
        raise ValueError(f"Input path does not exist: {input_path}")
    
    if not pdf_files:
        raise ValueError(f"No PDF files found in: {input_path}")
    
    # Setup output directories
    output_dir_obj = Path(output_dir)
    output_dir_obj.mkdir(parents=True, exist_ok=True)
    
    errors_dir = output_dir_obj / "errors"
    errors_dir.mkdir(exist_ok=True)
    
    # Process each invoice
    all_invoice_lines = []
    results = {
        "processed": 0,
        "ok": 0,
        "partial": 0,
        "review": 0,
        "failed": 0,
        "errors": []
    }
    
    total = len(pdf_files)
    
    for i, pdf_file in enumerate(pdf_files, start=1):
        print(f"Processing {i}/{total}...")
        
        result = process_invoice(str(pdf_file), str(output_dir), verbose)
        
        results["processed"] += 1
        
        if result["status"] == "FAILED":
            results["failed"] += 1
            results["errors"].append({
                "filename": pdf_file.name,
                "error": result["error"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Move corrupt PDF to errors directory
            error_pdf_path = errors_dir / pdf_file.name
            try:
                shutil.move(str(pdf_file), str(error_pdf_path))
            except Exception:
                pass  # Continue even if move fails
            
            if fail_fast:
                break
        elif result["status"] == "OK":
            results["ok"] += 1
            all_invoice_lines.extend(result["invoice_lines"])
        elif result["status"] == "PARTIAL":
            results["partial"] += 1
            all_invoice_lines.extend(result["invoice_lines"])
        
        # Status output per invoice
        status_line = f"[{i}/{total}] {pdf_file.name} → {result['status']}"
        if result["line_count"] > 0:
            status_line += f" ({result['line_count']} rader)"
        print(status_line)
    
    # Export consolidated Excel
    if all_invoice_lines:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        excel_filename = f"invoices_{timestamp}.xlsx"
        excel_path = output_dir_obj / excel_filename
        
        export_to_excel(all_invoice_lines, str(excel_path))
        results["excel_path"] = str(excel_path)
    else:
        results["excel_path"] = None
    
    # Export error report if errors occurred
    if results["errors"]:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        errors_filename = f"errors_{timestamp}.json"
        errors_path = output_dir_obj / "errors" / errors_filename
        
        with open(errors_path, 'w', encoding='utf-8') as f:
            json.dump(results["errors"], f, indent=2, ensure_ascii=False)
        
        results["errors_path"] = str(errors_path)
    else:
        results["errors_path"] = None
    
    return results


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Invoice Parser - Extract structured data from Swedish PDF invoices"
    )
    
    parser.add_argument(
        "--input",
        required=True,
        help="Input directory or PDF file path"
    )
    
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for Excel files"
    )
    
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop processing on first error"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug output"
    )
    
    args = parser.parse_args()
    
    try:
        results = process_batch(
            args.input,
            args.output,
            fail_fast=args.fail_fast,
            verbose=args.verbose
        )
        
        # Final summary
        print(f"\nDone: {results['processed']} processed. "
              f"OK={results['ok']}, PARTIAL={results['partial']}, "
              f"REVIEW={results['review']}, failed={results['failed']}.")
        
        if results.get("excel_path"):
            print(f"Excel: {results['excel_path']}")
        
        if results.get("errors_path"):
            print(f"Errors: {results['errors_path']}")
        
        sys.exit(0 if results["failed"] == 0 else 1)
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

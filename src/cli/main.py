"""CLI interface for invoice parser with batch processing."""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Fix encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass  # Python < 3.7 or already configured

import pdfplumber

from ..models.document import Document
from ..models.invoice_header import InvoiceHeader
from ..models.invoice_line import InvoiceLine
from ..models.virtual_invoice_result import VirtualInvoiceResult
from ..pipeline.invoice_line_parser import extract_invoice_lines
from ..pipeline.pdf_detection import detect_pdf_type, route_extraction_path
from ..pipeline.reader import read_pdf, PDFReadError
from ..pipeline.row_grouping import group_tokens_to_rows
from ..pipeline.segment_identification import identify_segments
from ..pipeline.tokenizer import extract_tokens_from_page
from ..pipeline.header_extractor import extract_header_fields
from ..pipeline.footer_extractor import extract_total_amount
from ..pipeline.validation import validate_invoice
from ..pipeline.invoice_boundary_detection import detect_invoice_boundaries
from ..export.excel_export import export_to_excel
from ..export.review_report import create_review_report


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
        
        # Find footer segment (from last page)
        footer_segment = None
        if doc.pages:
            last_page_segments = [s for s in all_segments if s.page == doc.pages[-1]]
            footer_segment = next((s for s in last_page_segments if s.segment_type == "footer"), None)
        
        # Create InvoiceHeader
        invoice_header = None
        if header_segment:
            invoice_header = InvoiceHeader(segment=header_segment)
            # Extract header fields (invoice number, date, vendor)
            extract_header_fields(header_segment, invoice_header)
        
        # Extract total amount from footer
        if footer_segment and invoice_header:
            extract_total_amount(footer_segment, all_invoice_lines, invoice_header)
        
        # Step 8: Run validation
        validation_result = None
        if invoice_header:
            validation_result = validate_invoice(invoice_header, all_invoice_lines)
            # Use ValidationResult.status instead of hardcoded status
            status = validation_result.status
        else:
            # No invoice_header → REVIEW (cannot validate)
            status = "REVIEW"
        
        return {
            "status": status,
            "line_count": len(all_invoice_lines),
            "invoice_lines": all_invoice_lines,
            "invoice_header": invoice_header,
            "validation_result": validation_result,
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


def process_virtual_invoice(
    doc: Document,
    page_start: int,
    page_end: int,
    virtual_invoice_index: int,
    extraction_path: str,
    verbose: bool = False
) -> VirtualInvoiceResult:
    """Process a single virtual invoice within a PDF (given page range).
    
    Args:
        doc: Document object
        page_start: Starting page number (1-based)
        page_end: Ending page number (1-based, inclusive)
        virtual_invoice_index: Index of this invoice within PDF (1-based)
        extraction_path: "pdfplumber" or "ocr"
        verbose: Enable verbose output
        
    Returns:
        VirtualInvoiceResult object
    """
    # Generate virtual_invoice_id
    file_stem = Path(doc.filename).stem
    virtual_invoice_id = f"{file_stem}__{virtual_invoice_index}"
    
    # Extract pages for this virtual invoice
    invoice_pages = [p for p in doc.pages if page_start <= p.page_number <= page_end]
    
    if not invoice_pages:
        return VirtualInvoiceResult(
            virtual_invoice_id=virtual_invoice_id,
            source_pdf=doc.filename,
            virtual_invoice_index=virtual_invoice_index,
            page_start=page_start,
            page_end=page_end,
            status="FAILED",
            error=f"No pages found in range {page_start}-{page_end}"
        )
    
    try:
        # Extract tokens from pages in range
        all_invoice_lines = []
        all_segments = []
        line_number_global = 1
        
        # Open PDF once for all pages (more efficient)
        pdf = None
        if extraction_path == "pdfplumber":
            pdf = pdfplumber.open(doc.filepath)
        
        try:
            for page in invoice_pages:
                if extraction_path == "pdfplumber" and pdf:
                    pdfplumber_page = pdf.pages[page.page_number - 1]
                    tokens = extract_tokens_from_page(page, pdfplumber_page)
                else:
                    if verbose:
                        print(f"  Warning: OCR path not yet implemented")
                    tokens = []
                
                if not tokens:
                    continue
                
                # Group tokens to rows
                rows = group_tokens_to_rows(tokens)
                
                # Identify segments
                segments = identify_segments(rows, page)
                all_segments.extend(segments)
                
                # Extract line items from items segment
                items_segment = next((s for s in segments if s.segment_type == "items"), None)
                
                if items_segment:
                    invoice_lines = extract_invoice_lines(items_segment)
                    
                    for line in invoice_lines:
                        line.line_number = line_number_global
                        line_number_global += 1
                    
                    all_invoice_lines.extend(invoice_lines)
        finally:
            if pdf:
                pdf.close()
        
        # Find header segment (from first page of this invoice)
        header_segment = None
        if invoice_pages:
            first_page = invoice_pages[0]
            first_page_segments = [s for s in all_segments if s.page == first_page]
            header_segment = next((s for s in first_page_segments if s.segment_type == "header"), None)
        
        # Find footer segment (from last page of this invoice)
        footer_segment = None
        if invoice_pages:
            last_page = invoice_pages[-1]
            last_page_segments = [s for s in all_segments if s.page == last_page]
            footer_segment = next((s for s in last_page_segments if s.segment_type == "footer"), None)
        
        # Create InvoiceHeader
        invoice_header = None
        if header_segment:
            invoice_header = InvoiceHeader(segment=header_segment)
            extract_header_fields(header_segment, invoice_header)
        
        # Extract total amount from footer
        if footer_segment and invoice_header:
            extract_total_amount(footer_segment, all_invoice_lines, invoice_header)
        
        # Run validation
        validation_result = None
        if invoice_header:
            validation_result = validate_invoice(invoice_header, all_invoice_lines)
            status = validation_result.status
        else:
            status = "REVIEW"
        
        return VirtualInvoiceResult(
            virtual_invoice_id=virtual_invoice_id,
            source_pdf=doc.filename,
            virtual_invoice_index=virtual_invoice_index,
            page_start=page_start,
            page_end=page_end,
            status=status,
            invoice_header=invoice_header,
            invoice_lines=all_invoice_lines,
            validation_result=validation_result,
            error=None
        )
        
    except Exception as e:
        return VirtualInvoiceResult(
            virtual_invoice_id=virtual_invoice_id,
            source_pdf=doc.filename,
            virtual_invoice_index=virtual_invoice_index,
            page_start=page_start,
            page_end=page_end,
            status="FAILED",
            error=f"Processing error: {str(e)}"
        )


def process_pdf(
    pdf_path: str,
    output_dir: str,
    verbose: bool = False
) -> List[VirtualInvoiceResult]:
    """Process a PDF file that may contain multiple invoices.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Output directory (used for error reporting, not in this function)
        verbose: Enable verbose output
        
    Returns:
        List of VirtualInvoiceResult objects (one per detected invoice, or one if detection fails)
    """
    try:
        # Step 1: Read PDF
        doc = read_pdf(pdf_path)
        
        # Step 2: Detect PDF type and route
        pdf_type = detect_pdf_type(doc)
        extraction_path = route_extraction_path(doc)
        
        # Step 3: Detect invoice boundaries
        boundaries = detect_invoice_boundaries(doc, extraction_path, verbose)
        
        if not boundaries:
            # Fail-safe: treat entire PDF as one invoice
            boundaries = [(1, len(doc.pages))]
        
        # Step 4: Process each virtual invoice
        results = []
        for index, (page_start, page_end) in enumerate(boundaries, start=1):
            result = process_virtual_invoice(
                doc, page_start, page_end, index, extraction_path, verbose
            )
            results.append(result)
        
        return results
        
    except PDFReadError as e:
        # Return single failed result
        file_stem = Path(pdf_path).stem
        return [VirtualInvoiceResult(
            virtual_invoice_id=f"{file_stem}__1",
            source_pdf=Path(pdf_path).name,
            virtual_invoice_index=1,
            page_start=1,
            page_end=1,
            status="FAILED",
            error=f"PDF read error: {str(e)}"
        )]
    except Exception as e:
        file_stem = Path(pdf_path).stem
        return [VirtualInvoiceResult(
            virtual_invoice_id=f"{file_stem}__1",
            source_pdf=Path(pdf_path).name,
            virtual_invoice_index=1,
            page_start=1,
            page_end=1,
            status="FAILED",
            error=f"Processing error: {str(e)}"
        )]


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
    # Note: invoice_lines are collected via invoice_results, not all_invoice_lines
    results = {
        "processed": 0,
        "ok": 0,
        "partial": 0,
        "review": 0,
        "failed": 0,
        "errors": []
    }
    
    total = len(pdf_files)
    
    # Track invoice results per invoice (for grouping validation data)
    invoice_results = []
    
    for i, pdf_file in enumerate(pdf_files, start=1):
        print(f"Processing {i}/{total}...")
        
        # Process PDF (may return multiple virtual invoices)
        virtual_results = process_pdf(str(pdf_file), str(output_dir), verbose)
        
        if not virtual_results:
            # No invoices found
            results["failed"] += 1
            results["errors"].append({
                "filename": pdf_file.name,
                "error": "No invoices found in PDF",
                "timestamp": datetime.now().isoformat()
            })
            continue
        
        # Process each virtual invoice result
        for virtual_result in virtual_results:
            results["processed"] += 1
            
            if virtual_result.status == "FAILED":
                results["failed"] += 1
                results["errors"].append({
                    "filename": pdf_file.name,
                    "virtual_invoice_id": virtual_result.virtual_invoice_id,
                    "error": virtual_result.error or "Processing failed",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Move corrupt PDF to errors directory (only once per PDF file)
                if virtual_result.virtual_invoice_index == 1:
                    error_pdf_path = errors_dir / pdf_file.name
                    try:
                        shutil.move(str(pdf_file), str(error_pdf_path))
                    except Exception:
                        pass  # Continue even if move fails
                
                if fail_fast:
                    break
            else:
                # Collect invoice results (OK/PARTIAL/REVIEW)
                if virtual_result.invoice_header and virtual_result.validation_result:
                    invoice_results.append({
                        "invoice_header": virtual_result.invoice_header,
                        "validation_result": virtual_result.validation_result,
                        "invoice_lines": virtual_result.invoice_lines,
                        "pdf_path": str(pdf_file),
                        "filename": pdf_file.name,
                        "virtual_invoice_id": virtual_result.virtual_invoice_id,
                    })
                    
                    # Create review report if REVIEW status
                    if virtual_result.validation_result.status == "REVIEW":
                        try:
                            create_review_report(
                                virtual_result.invoice_header,
                                virtual_result.validation_result,
                                virtual_result.invoice_lines,
                                str(pdf_file),
                                output_dir_obj,
                                virtual_invoice_id=virtual_result.virtual_invoice_id
                            )
                        except Exception as e:
                            # Log warning but continue batch
                            if verbose:
                                print(f"Warning: Failed to create review report for {virtual_result.virtual_invoice_id}: {e}")
                
                # Update counters
                if virtual_result.status == "OK":
                    results["ok"] += 1
                elif virtual_result.status == "PARTIAL":
                    results["partial"] += 1
                elif virtual_result.status == "REVIEW":
                    results["review"] = results.get("review", 0) + 1
            
            # Status output per virtual invoice
            # Format: [PDF#/total] filename.pdf#invoice_index -> STATUS
            invoice_suffix = f"#{virtual_result.virtual_invoice_index}" if len(virtual_results) > 1 else ""
            status_line = f"[{i}/{total}] {pdf_file.name}{invoice_suffix} -> {virtual_result.status}"
            if virtual_result.validation_result and virtual_result.invoice_header:
                validation = virtual_result.validation_result
                if validation.status == "REVIEW":
                    status_line += f" (InvoiceNoConfidence={virtual_result.invoice_header.invoice_number_confidence:.2f}, TotalConfidence={virtual_result.invoice_header.total_confidence:.2f})"
                elif validation.status == "PARTIAL":
                    if validation.diff is not None:
                        status_line += f" (Diff={validation.diff:.2f} SEK)"
            if virtual_result.line_count > 0:
                status_line += f" ({virtual_result.line_count} rader)"
            print(status_line)
        
        if fail_fast and any(r.status == "FAILED" for r in virtual_results):
            break
    
    # Export consolidated Excel with validation data
    if invoice_results:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        excel_filename = f"invoices_{timestamp}.xlsx"
        excel_path = output_dir_obj / excel_filename
        
        # Prepare invoice results for Excel export (list of dicts with invoice_lines and invoice_metadata)
        excel_invoice_results = []
        for invoice_result in invoice_results:
            invoice_header = invoice_result["invoice_header"]
            validation_result = invoice_result["validation_result"]
            
            # Prepare metadata with validation fields
            invoice_metadata = {
                "fakturanummer": invoice_header.invoice_number or "TBD",
                "foretag": invoice_header.supplier_name or "TBD",
                "fakturadatum": invoice_header.invoice_date.isoformat() if invoice_header.invoice_date else "TBD",
                "virtual_invoice_id": invoice_result.get("virtual_invoice_id", ""),  # Include virtual invoice ID
                "status": validation_result.status,
                "lines_sum": validation_result.lines_sum,
                "diff": validation_result.diff if validation_result.diff is not None else "N/A",
                "invoice_number_confidence": invoice_header.invoice_number_confidence,
                "total_confidence": invoice_header.total_confidence,
            }
            
            excel_invoice_results.append({
                "invoice_lines": invoice_result["invoice_lines"],
                "invoice_metadata": invoice_metadata,
            })
        
        # Export to Excel (using updated function that accepts list of invoice results)
        export_to_excel(excel_invoice_results, str(excel_path))
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
        
        # Final summary with validation statistics
        review_count = results.get("review", 0)
        summary = f"\nDone: {results['processed']} processed. "
        summary += f"OK={results['ok']}, PARTIAL={results['partial']}, REVIEW={review_count}, failed={results['failed']}."
        
        if review_count > 0:
            summary += f"\nReview reports: {review_count} invoice(s) in review/ folder"
        
        print(summary)
        
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

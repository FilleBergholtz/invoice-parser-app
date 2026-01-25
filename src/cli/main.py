"""CLI interface for invoice parser with batch processing."""

import argparse
import json
import logging
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

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
from ..pipeline.pdf_renderer import render_page_to_image
from ..pipeline.ocr_abstraction import extract_tokens_with_ocr, OCRException
from ..pipeline.header_extractor import extract_header_fields
from ..pipeline.footer_extractor import extract_total_amount
from ..pipeline.validation import validate_invoice
from ..pipeline.invoice_boundary_detection import detect_invoice_boundaries
from ..export.excel_export import export_to_excel
from ..export.review_report import create_review_report
from ..review.review_package import create_review_package
from ..config import get_default_output_dir, get_output_subdirs, get_ai_enabled, get_ai_endpoint, get_ai_key, get_app_version, get_calibration_model_path
from ..pipeline.confidence_calibration import (
    CalibrationModel,
    load_ground_truth_data,
    train_calibration_model,
    validate_calibration,
    format_validation_report
)
from ..config.profile_manager import set_profile, get_profile
from ..run_summary import RunSummary
from ..ai.client import AIClient, AIClientError, AIConnectionError, AIAPIError, create_ai_diff, save_ai_artifacts
from ..ai.schemas import AIInvoiceRequest, AIInvoiceLineRequest
from ..debug.artifact_index import create_manifest_for_run
from ..quality.score import calculate_quality_score
from ..versioning.compat import check_artifacts_compatibility, CompatibilityStatus


class InvoiceProcessingError(Exception):
    """Raised when invoice processing fails."""
    pass


def _is_likely_garbled(row_text: str) -> bool:
    """Utelämn rader som ser ut som revers/vattensstämpel (t.ex. |TEKREVSGNINRYTSIMONOKE, nigirO, ecruoS)."""
    import re
    t = row_text.strip()
    if not t:
        return True
    if re.search(r"\|[A-Za-z]{12,}", t) or re.search(r"[A-Za-z]{12,}\|", t):
        return True
    if re.search(r"[a-z]{3,}[A-Z][a-z]*", t):
        return True
    return False


def _build_page_context_for_ai(last_page_segments: list) -> str:
    """Bygg full sidtext (header, items, footer) så AI får PDF:ens hela data för totalsidan.
    
    Filtrerar bort uppenbart skräp (revers, vattensstämplar). AI behöver se hela sidan
    för att hitta rätt totalsumma när heuristiken ger fel kandidater.
    """
    if not last_page_segments:
        return ""
    ordered = sorted(last_page_segments, key=lambda s: s.y_min)
    parts = []
    for seg in ordered:
        parts.append(f"--- {seg.segment_type.upper()} ---")
        for row in seg.rows:
            if _is_likely_garbled(row.text):
                continue
            parts.append(row.text)
    return "\n".join(parts)


def process_invoice(
    pdf_path: str,
    output_dir: str,
    verbose: bool = False,
    progress_callback: Optional[Callable[[str, float, int], None]] = None
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
        if progress_callback:
            progress_callback("Läser PDF-fil...", 0.0, 0)
        doc = read_pdf(pdf_path)
        
        # Step 2: Detect PDF type and route
        if progress_callback:
            progress_callback("Analyserar PDF-typ och struktur...", 0.0, 0)
        pdf_type = detect_pdf_type(doc)
        extraction_path = route_extraction_path(doc)
        
        # Step 3: Extract tokens from all pages
        if progress_callback:
            progress_callback("Extraherar text och tokens från PDF-sidor...", 0.0, 0)
        all_invoice_lines = []
        all_segments = []  # Collect segments from all pages
        all_items_segments = []  # Collect items segments from all pages
        line_number_global = 1
        
        # Open PDF once for all pages (pdfplumber path only)
        pdf = None
        if extraction_path == "pdfplumber":
            pdf = pdfplumber.open(doc.filepath)
        ocr_render_dir = Path(output_dir) / "ocr_render" if extraction_path == "ocr" else None

        try:
            for page in doc.pages:
                if extraction_path == "pdfplumber" and pdf:
                    pdfplumber_page = pdf.pages[page.page_number - 1]
                    tokens = extract_tokens_from_page(page, pdfplumber_page)
                elif extraction_path == "ocr" and ocr_render_dir is not None:
                    try:
                        render_page_to_image(page, str(ocr_render_dir))
                        tokens = extract_tokens_with_ocr(page)
                    except OCRException as e:
                        if verbose:
                            print(f"  OCR failed for page {page.page_number}: {e}")
                        tokens = []
                    except Exception as e:
                        if verbose:
                            print(f"  Render/OCR failed for page {page.page_number}: {e}")
                        tokens = []
                else:
                    tokens = []
                
                if not tokens:
                    continue
                
                # Step 4: Group tokens to rows
                rows = group_tokens_to_rows(tokens)
                
                # Step 5: Identify segments
                segments = identify_segments(rows, page)
                all_segments.extend(segments)  # Collect for header/footer extraction
                
                # Collect items segments from all pages (for multi-page invoices)
                items_segment = next((s for s in segments if s.segment_type == "items"), None)
                if items_segment:
                    all_items_segments.append(items_segment)
        finally:
            if pdf:
                pdf.close()
        
        # Step 6: Extract line items from all items segments (multi-page support)
        if progress_callback:
            progress_callback("Identifierar och extraherar produktrader från alla sidor...", 0.0, 0)
        
        # Combine items segments from all pages into a single virtual segment for extraction
        # This allows line items to span multiple pages
        if all_items_segments:
            # Extract line items from each items segment and combine
            for items_segment in all_items_segments:
                invoice_lines = extract_invoice_lines(items_segment)
                
                # Assign global line numbers
                for line in invoice_lines:
                    line.line_number = line_number_global
                    line_number_global += 1
                
                # Validate and score each line item (prioritize sum, then validate other fields)
                from ..pipeline.confidence_scoring import validate_and_score_invoice_line
                for line in invoice_lines:
                    confidence, validation_info = validate_and_score_invoice_line(line)
                    # Store validation info as metadata (could be added to InvoiceLine model later)
                    # For now, validation warnings will be included in ValidationResult
                
                all_invoice_lines.extend(invoice_lines)
        
        # Step 7: Extract header fields and total amount
        # Find header segment (prefer first page, but search all pages if needed)
        header_segment = None
        if doc.pages:
            # First, try first page (most common case)
            first_page_segments = [s for s in all_segments if s.page == doc.pages[0]]
            header_segment = next((s for s in first_page_segments if s.segment_type == "header"), None)
            
            # If no header found on first page, search all pages (for multi-page invoices)
            if not header_segment:
                header_segment = next((s for s in all_segments if s.segment_type == "header"), None)
        
        # Find footer segment (prefer last page, but search all pages if needed)
        footer_segment = None
        last_page_segments = []
        if doc.pages:
            # First, try last page (most common case - totalsumma is usually on last page)
            last_page_segments = [s for s in all_segments if s.page == doc.pages[-1]]
            footer_segment = next((s for s in last_page_segments if s.segment_type == "footer"), None)
            
            # If no footer found on last page, search all pages (for multi-page invoices)
            if not footer_segment:
                # Search in reverse order (last pages first)
                for page in reversed(doc.pages):
                    page_segments = [s for s in all_segments if s.page == page]
                    footer_segment = next((s for s in page_segments if s.segment_type == "footer"), None)
                    if footer_segment:
                        last_page_segments = page_segments
                        break
        
        # Rows immediately above footer (rubrikerna); labels like "Att betala: SEK" can sit in items
        rows_above_footer = []
        if footer_segment and last_page_segments:
            items_on_footer_page = next((s for s in last_page_segments if s.segment_type == "items"), None)
            if items_on_footer_page and items_on_footer_page.rows:
                rows_above_footer = items_on_footer_page.rows[-2:]  # last 1–2 rows
        
        # Create InvoiceHeader
        invoice_header = None
        if header_segment:
            invoice_header = InvoiceHeader(segment=header_segment)
            # Extract header fields (invoice number, date, vendor) with retry
            # Use provided progress_callback or create one for verbose mode
            if progress_callback:
                header_progress = progress_callback
            elif verbose:
                def header_progress(msg, conf, attempt):
                    print(f"  {msg} (confidence: {conf*100:.1f}%)")
            else:
                header_progress = None
            extract_header_fields(header_segment, invoice_header, progress_callback=header_progress)
        
        # Extract total amount from footer with retry
        if footer_segment and invoice_header:
            from ..pipeline.retry_extraction import extract_with_retry
            
            page_context_for_ai = _build_page_context_for_ai(last_page_segments)
            
            def extract_total(strategy=None):
                extract_total_amount(
                    footer_segment, all_invoice_lines, invoice_header,
                    strategy=strategy, rows_above_footer=rows_above_footer,
                    page_context_for_ai=page_context_for_ai
                )
                return invoice_header
            
            if verbose:
                def total_progress(msg, conf, attempt):
                    print(f"  {msg} (confidence: {conf*100:.1f}%)")
                extract_with_retry(
                    extract_total,
                    target_confidence=0.90,
                    max_attempts=5,
                    progress_callback=total_progress
                )
            else:
                extract_with_retry(
                    extract_total,
                    target_confidence=0.90,
                    max_attempts=5
                )
        
        # Step 7.5: Optional AI enrichment
        ai_enriched = False
        if get_ai_enabled() and invoice_header:
            ai_endpoint = get_ai_endpoint()
            if ai_endpoint:
                try:
                    ai_client = AIClient(ai_endpoint, get_ai_key())
                    
                    # Create AI request
                    ai_request = AIInvoiceRequest(
                        invoice_number=invoice_header.invoice_number,
                        invoice_date=invoice_header.invoice_date.isoformat() if invoice_header.invoice_date else None,
                        supplier_name=invoice_header.supplier_name,
                        customer_name=invoice_header.customer_name,
                        total_amount=invoice_header.total_amount,
                        line_items=[
                            AIInvoiceLineRequest(
                                description=line.description,
                                quantity=line.quantity,
                                unit=line.unit,
                                unit_price=line.unit_price,
                                discount=line.discount,
                                total_amount=line.total_amount,
                                line_number=line.line_number
                            )
                            for line in all_invoice_lines
                        ]
                    )
                    
                    # Call AI service
                    if verbose:
                        print("  Calling AI enrichment service...")
                    ai_response = ai_client.enrich_invoice(ai_request)
                    ai_enriched = True
                    
                    # Apply AI enrichments (update invoice_header and invoice_lines)
                    if ai_response.invoice_number and ai_response.invoice_number != invoice_header.invoice_number:
                        invoice_header.invoice_number = ai_response.invoice_number
                    if ai_response.supplier_name and ai_response.supplier_name != invoice_header.supplier_name:
                        invoice_header.supplier_name = ai_response.supplier_name
                    if ai_response.total_amount and ai_response.total_amount != invoice_header.total_amount:
                        invoice_header.total_amount = ai_response.total_amount
                    
                    # Update line items
                    for i, (line, ai_line) in enumerate(zip(all_invoice_lines, ai_response.line_items)):
                        if ai_line.description and ai_line.description != line.description:
                            line.description = ai_line.description
                        if ai_line.quantity is not None and ai_line.quantity != line.quantity:
                            line.quantity = ai_line.quantity
                        if ai_line.unit_price is not None and ai_line.unit_price != line.unit_price:
                            line.unit_price = ai_line.unit_price
                        if ai_line.total_amount is not None and ai_line.total_amount != line.total_amount:
                            line.total_amount = ai_line.total_amount
                    
                    # Create diff
                    ai_diff = create_ai_diff(ai_request, ai_response)
                    
                    # Save artifacts (if artifacts_dir is available via progress_callback context)
                    # Note: artifacts_dir will be saved later in process_batch
                    if verbose:
                        print("  AI enrichment completed successfully")
                        
                except (AIConnectionError, AIAPIError) as e:
                    # Log warning but continue without AI
                    if verbose:
                        print(f"  Warning: AI enrichment failed: {e}")
                    # Save error artifact if artifacts_dir available
                    # (handled in process_batch)
                except Exception as e:
                    # Unexpected error - log but continue
                    if verbose:
                        print(f"  Warning: Unexpected AI error: {e}")
            else:
                # AI_ENDPOINT används endast för AI-enrichment. AI-fallback (totalsumma) använder API-nyckel.
                if verbose and not get_ai_key():
                    print("  Warning: AI_ENABLED=true but neither AI_ENDPOINT nor API key set")
        
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
            "error": None,
            "ai_enriched": ai_enriched
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
    verbose: bool = False,
    output_dir: Optional[str] = None,
) -> VirtualInvoiceResult:
    """Process a single virtual invoice within a PDF (given page range).
    
    Args:
        doc: Document object
        page_start: Starting page number (1-based)
        page_end: Ending page number (1-based, inclusive)
        virtual_invoice_index: Index of this invoice within PDF (1-based)
        extraction_path: "pdfplumber" or "ocr"
        verbose: Enable verbose output
        output_dir: Output directory (required for OCR path, for ocr_render subdir)
        
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
        
        # Open PDF once for all pages (pdfplumber path only)
        pdf = None
        if extraction_path == "pdfplumber":
            pdf = pdfplumber.open(doc.filepath)
        ocr_render_dir = (Path(output_dir) / "ocr_render") if (extraction_path == "ocr" and output_dir) else None

        try:
            for page in invoice_pages:
                if extraction_path == "pdfplumber" and pdf:
                    pdfplumber_page = pdf.pages[page.page_number - 1]
                    tokens = extract_tokens_from_page(page, pdfplumber_page)
                elif extraction_path == "ocr" and ocr_render_dir is not None:
                    try:
                        render_page_to_image(page, str(ocr_render_dir))
                        tokens = extract_tokens_with_ocr(page)
                    except OCRException as e:
                        if verbose:
                            print(f"  OCR failed for page {page.page_number}: {e}")
                        tokens = []
                    except Exception as e:
                        if verbose:
                            print(f"  Render/OCR failed for page {page.page_number}: {e}")
                        tokens = []
                else:
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
        last_page_segments = []
        if invoice_pages:
            last_page = invoice_pages[-1]
            last_page_segments = [s for s in all_segments if s.page == last_page]
            footer_segment = next((s for s in last_page_segments if s.segment_type == "footer"), None)
        
        rows_above_footer = []
        if footer_segment and last_page_segments:
            items_on_footer_page = next((s for s in last_page_segments if s.segment_type == "items"), None)
            if items_on_footer_page and items_on_footer_page.rows:
                rows_above_footer = items_on_footer_page.rows[-2:]
        
        # Create InvoiceHeader
        invoice_header = None
        if header_segment:
            invoice_header = InvoiceHeader(segment=header_segment)
            # Extract header fields with retry
            def progress_callback(msg, conf, attempt):
                if verbose:
                    print(f"  {msg} (confidence: {conf*100:.1f}%)")
            extract_header_fields(header_segment, invoice_header, progress_callback=progress_callback if verbose else None)
        
        # Extract total amount from footer with retry
        if footer_segment and invoice_header:
            from ..pipeline.retry_extraction import extract_with_retry
            
            page_context_for_ai = _build_page_context_for_ai(last_page_segments)
            
            def extract_total(strategy=None):
                extract_total_amount(
                    footer_segment, all_invoice_lines, invoice_header,
                    strategy=strategy, rows_above_footer=rows_above_footer,
                    page_context_for_ai=page_context_for_ai
                )
                return invoice_header
            
            if verbose:
                def total_progress(msg, conf, attempt):
                    print(f"  {msg} (confidence: {conf*100:.1f}%)")
                extract_with_retry(
                    extract_total,
                    target_confidence=0.90,
                    max_attempts=5,
                    progress_callback=total_progress
                )
            else:
                extract_with_retry(
                    extract_total,
                    target_confidence=0.90,
                    max_attempts=5
                )
        
        # Step 7.5: Optional AI enrichment
        ai_enriched = False
        ai_request_data = None
        ai_response_data = None
        ai_error = None
        
        if get_ai_enabled() and invoice_header:
            ai_endpoint = get_ai_endpoint()
            if ai_endpoint:
                try:
                    ai_client = AIClient(ai_endpoint, get_ai_key())
                    
                    # Create AI request
                    ai_request = AIInvoiceRequest(
                        invoice_number=invoice_header.invoice_number,
                        invoice_date=invoice_header.invoice_date.isoformat() if invoice_header.invoice_date else None,
                        supplier_name=invoice_header.supplier_name,
                        customer_name=invoice_header.customer_name,
                        total_amount=invoice_header.total_amount,
                        line_items=[
                            AIInvoiceLineRequest(
                                description=line.description,
                                quantity=line.quantity,
                                unit=line.unit,
                                unit_price=line.unit_price,
                                discount=line.discount,
                                total_amount=line.total_amount,
                                line_number=line.line_number
                            )
                            for line in all_invoice_lines
                        ]
                    )
                    ai_request_data = ai_request
                    
                    # Call AI service
                    if verbose:
                        print("  Calling AI enrichment service...")
                    ai_response = ai_client.enrich_invoice(ai_request)
                    ai_response_data = ai_response
                    ai_enriched = True
                    
                    # Apply AI enrichments (update invoice_header and invoice_lines)
                    if ai_response.invoice_number and ai_response.invoice_number != invoice_header.invoice_number:
                        invoice_header.invoice_number = ai_response.invoice_number
                    if ai_response.supplier_name and ai_response.supplier_name != invoice_header.supplier_name:
                        invoice_header.supplier_name = ai_response.supplier_name
                    if ai_response.total_amount and ai_response.total_amount != invoice_header.total_amount:
                        invoice_header.total_amount = ai_response.total_amount
                    
                    # Update line items
                    for i, (line, ai_line) in enumerate(zip(all_invoice_lines, ai_response.line_items)):
                        if ai_line.description and ai_line.description != line.description:
                            line.description = ai_line.description
                        if ai_line.quantity is not None and ai_line.quantity != line.quantity:
                            line.quantity = ai_line.quantity
                        if ai_line.unit_price is not None and ai_line.unit_price != line.unit_price:
                            line.unit_price = ai_line.unit_price
                        if ai_line.total_amount is not None and ai_line.total_amount != line.total_amount:
                            line.total_amount = ai_line.total_amount
                    
                    if verbose:
                        print("  AI enrichment completed successfully")
                        
                except (AIConnectionError, AIAPIError) as e:
                    # Log warning but continue without AI
                    ai_error = str(e)
                    if verbose:
                        print(f"  Warning: AI enrichment failed: {e}")
                except Exception as e:
                    # Unexpected error - log but continue
                    ai_error = str(e)
                    if verbose:
                        print(f"  Warning: Unexpected AI error: {e}")
            else:
                if verbose and not get_ai_key():
                    print("  Warning: AI_ENABLED=true but neither AI_ENDPOINT nor API key set")
        
        # Step 8: Run validation
        validation_result = None
        if invoice_header:
            validation_result = validate_invoice(invoice_header, all_invoice_lines)
            status = validation_result.status
        else:
            status = "REVIEW"
        
        result = VirtualInvoiceResult(
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
        
        # Store AI data for later artifact saving
        result.ai_request = ai_request_data
        result.ai_response = ai_response_data
        result.ai_error = ai_error
        
        return result
        
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


def _validation_passed(r: VirtualInvoiceResult) -> bool:
    """True if total ≈ line_items_sum (math validation passed)."""
    if r.status == "FAILED" or r.validation_result is None:
        return False
    vr = r.validation_result
    return vr.diff is not None and abs(vr.diff) <= vr.tolerance


def _total_confidence(r: VirtualInvoiceResult) -> float:
    """Total amount confidence from result."""
    if r.status == "FAILED":
        return 0.0
    if r.validation_result is not None:
        return r.validation_result.total_confidence
    if r.invoice_header is not None:
        return r.invoice_header.total_confidence
    return 0.0


def _invoice_number_confidence(r: VirtualInvoiceResult) -> float:
    """Invoice number confidence from result."""
    if r.status == "FAILED":
        return 0.0
    if r.validation_result is not None:
        return r.validation_result.invoice_number_confidence
    if r.invoice_header is not None:
        return r.invoice_header.invoice_number_confidence
    return 0.0


def _choose_best_extraction_result(
    r_pdf: VirtualInvoiceResult, r_ocr: VirtualInvoiceResult
) -> Tuple[VirtualInvoiceResult, str]:
    """Pick the better of pdfplumber vs OCR result. Returns (result, 'pdfplumber'|'ocr')."""
    vp_p, vp_o = _validation_passed(r_pdf), _validation_passed(r_ocr)
    if vp_p and not vp_o:
        return (r_pdf, "pdfplumber")
    if vp_o and not vp_p:
        return (r_ocr, "ocr")
    tc_p, tc_o = _total_confidence(r_pdf), _total_confidence(r_ocr)
    if tc_p > tc_o:
        return (r_pdf, "pdfplumber")
    if tc_o > tc_p:
        return (r_ocr, "ocr")
    inc_p, inc_o = _invoice_number_confidence(r_pdf), _invoice_number_confidence(r_ocr)
    if inc_p >= inc_o:
        return (r_pdf, "pdfplumber")
    return (r_ocr, "ocr")


def process_pdf(
    pdf_path: str,
    output_dir: str,
    verbose: bool = False,
    compare_extraction: bool = False,
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
        boundaries = detect_invoice_boundaries(doc, extraction_path, verbose, output_dir=output_dir)
        
        if not boundaries:
            # Fail-safe: treat entire PDF as one invoice
            boundaries = [(1, len(doc.pages))]
        
        # Step 4: Process each virtual invoice
        results = []
        for index, (page_start, page_end) in enumerate(boundaries, start=1):
            if compare_extraction:
                r_pdf = process_virtual_invoice(
                    doc, page_start, page_end, index, "pdfplumber", verbose,
                    output_dir=output_dir,
                )
                r_ocr = process_virtual_invoice(
                    doc, page_start, page_end, index, "ocr", verbose,
                    output_dir=output_dir,
                )
                chosen, source = _choose_best_extraction_result(r_pdf, r_ocr)
                chosen.extraction_source = source
                if verbose:
                    vp = _validation_passed(chosen)
                    conf = _total_confidence(chosen)
                    print(
                        f"  [{chosen.virtual_invoice_id}] using {source} "
                        f"(validation_passed={vp}, confidence={conf})"
                    )
                results.append(chosen)
            else:
                result = process_virtual_invoice(
                    doc, page_start, page_end, index, extraction_path, verbose,
                    output_dir=output_dir,
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
    verbose: bool = False,
    artifacts_dir: Optional[str] = None,
    compare_extraction: bool = False,
) -> Dict:
    """Process multiple invoice PDFs in batch.
    
    Args:
        input_path: Input directory or file list
        output_dir: Output directory for Excel files and errors
        fail_fast: Stop on first error if True
        verbose: Enable verbose output
        artifacts_dir: Optional custom directory for run artifacts
        
    Returns:
        Dict with batch processing results
    """
    # Create run summary
    summary = RunSummary.create(input_path, output_dir)
    
    # Set profile name and pipeline version in summary
    try:
        profile = get_profile()
        summary.profile_name = profile.name
    except Exception:
        summary.profile_name = "default"
    
    summary.pipeline_version = get_app_version()
    summary.compare_extraction_used = compare_extraction
    
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
    
    summary.total_files = len(pdf_files)
    
    # Setup output directories with subdirectory structure
    output_dir_obj = Path(output_dir)
    output_dir_obj.mkdir(parents=True, exist_ok=True)
    
    # Setup artifacts directory
    if artifacts_dir:
        run_artifacts_dir = Path(artifacts_dir)
    else:
        # Default: output_dir/artifacts/<run_id>
        run_artifacts_dir = output_dir_obj / "artifacts" / summary.run_id
        
    run_artifacts_dir.mkdir(parents=True, exist_ok=True)
    summary.artifacts_dir = str(run_artifacts_dir)
    
    # Create subdirectory structure (excel/, review/, errors/, temp/)
    subdirs = get_output_subdirs(output_dir_obj)
    errors_dir = subdirs['errors']
    
    # Store subdirs for later use (e.g., Excel export)
    process_batch.subdirs = subdirs  # Store as function attribute
    
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
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        print(f"  AI fallback: enabled={get_ai_enabled()}, API key set={bool(get_ai_key())}")
    
    invoice_results = []
    start_time = time.time()
    
    for i, pdf_file in enumerate(pdf_files, start=1):
        print(f"Processing {i}/{total}...")
        
        # Process PDF (may return multiple virtual invoices)
        virtual_results = process_pdf(
            str(pdf_file), str(output_dir), verbose,
            compare_extraction=compare_extraction,
        )
        
        if not virtual_results:
            # No invoices found
            results["failed"] += 1
            summary.failed_count += 1
            error_info = {
                "filename": pdf_file.name,
                "error": "No invoices found in PDF",
                "timestamp": datetime.now().isoformat()
            }
            results["errors"].append(error_info)
            summary.errors.append(error_info)
            continue
        
        # Process each virtual invoice result (when compare_extraction, each is already the chosen pdfplumber/ocr result)
        for virtual_result in virtual_results:
            results["processed"] += 1
            summary.processed_files += 1
            
            if virtual_result.status == "FAILED":
                results["failed"] += 1
                summary.failed_count += 1
                error_info = {
                    "filename": pdf_file.name,
                    "virtual_invoice_id": virtual_result.virtual_invoice_id,
                    "error": virtual_result.error or "Processing failed",
                    "timestamp": datetime.now().isoformat()
                }
                results["errors"].append(error_info)
                summary.errors.append(error_info)
                
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
                    # Calculate quality score
                    quality_score = calculate_quality_score(
                        virtual_result.validation_result,
                        virtual_result.invoice_header,
                        virtual_result.invoice_lines
                    )
                    
                    # Add quality score to summary (when compare_extraction, each virtual_result is the chosen one)
                    summary.quality_scores.append({
                        "virtual_invoice_id": virtual_result.virtual_invoice_id,
                        "filename": pdf_file.name,
                        "quality_score": quality_score.to_dict(),
                        "extraction_source": getattr(virtual_result, "extraction_source", None),
                    })
                    
                    invoice_results.append({
                        "invoice_header": virtual_result.invoice_header,
                        "validation_result": virtual_result.validation_result,
                        "invoice_lines": virtual_result.invoice_lines,
                        "pdf_path": str(pdf_file),
                        "filename": pdf_file.name,
                        "virtual_invoice_id": virtual_result.virtual_invoice_id,
                        "quality_score": quality_score.score,
                        "extraction_source": getattr(virtual_result, "extraction_source", None),
                    })
                    
                    # Save AI artifacts if AI was attempted
                    # Check if ai_request exists and is not None (avoid MagicMock auto-creation)
                    ai_request = getattr(virtual_result, 'ai_request', None)
                    if ai_request is not None:
                        invoice_artifacts_dir = run_artifacts_dir / virtual_result.virtual_invoice_id
                        invoice_artifacts_dir.mkdir(parents=True, exist_ok=True)
                        
                        ai_diff = None
                        ai_response = getattr(virtual_result, 'ai_response', None)
                        if ai_response:
                            ai_diff = create_ai_diff(ai_request, ai_response)
                        
                        save_ai_artifacts(
                            invoice_artifacts_dir,
                            ai_request,
                            ai_response,
                            ai_diff,
                            getattr(virtual_result, 'ai_error', None)
                        )
                    
                    # Create review report and package if REVIEW status
                    if virtual_result.validation_result.status == "REVIEW":
                        try:
                            # Create review report (folder with PDF + metadata.json)
                            review_folder = create_review_report(
                                virtual_result.invoice_header,
                                virtual_result.validation_result,
                                virtual_result.invoice_lines,
                                str(pdf_file),
                                output_dir_obj,
                                virtual_invoice_id=virtual_result.virtual_invoice_id
                            )
                            
                            # Export Excel for this invoice to review folder
                            invoice_excel_path = review_folder / f"{virtual_result.virtual_invoice_id}.xlsx"
                            invoice_metadata = {
                                "fakturanummer": virtual_result.invoice_header.invoice_number or "TBD",
                                "foretag": virtual_result.invoice_header.supplier_name or "TBD",
                                "fakturadatum": virtual_result.invoice_header.invoice_date.isoformat() if virtual_result.invoice_header.invoice_date else "TBD",
                                "virtual_invoice_id": virtual_result.virtual_invoice_id,
                                "status": virtual_result.validation_result.status,
                                "lines_sum": virtual_result.validation_result.lines_sum,
                                "diff": virtual_result.validation_result.diff if virtual_result.validation_result.diff is not None else "N/A",
                                "invoice_number_confidence": virtual_result.invoice_header.invoice_number_confidence,
                                "total_confidence": virtual_result.invoice_header.total_confidence,
                            }
                            export_to_excel(
                                [{
                                    "invoice_lines": virtual_result.invoice_lines,
                                    "invoice_metadata": invoice_metadata
                                }],
                                str(invoice_excel_path)
                            )
                            
                            # Create complete review package
                            run_summary_path = output_dir_obj / "run_summary.json"
                            artifact_manifest_path = run_artifacts_dir / "artifact_manifest.json" if run_artifacts_dir.exists() else None
                            
                            create_review_package(
                                review_folder,
                                Path(pdf_file),
                                excel_path=invoice_excel_path,
                                run_summary_path=run_summary_path if run_summary_path.exists() else None,
                                artifact_manifest_path=Path(artifact_manifest_path) if artifact_manifest_path and Path(artifact_manifest_path).exists() else None,
                                create_zip=False  # Keep as folder for easy access
                            )
                        except Exception as e:
                            # Log warning but continue batch
                            if verbose:
                                print(f"Warning: Failed to create review package for {virtual_result.virtual_invoice_id}: {e}")
                
                # Update counters
                if virtual_result.status == "OK":
                    results["ok"] += 1
                    summary.ok_count += 1
                elif virtual_result.status == "PARTIAL":
                    results["partial"] += 1
                    summary.partial_count += 1
                elif virtual_result.status == "REVIEW":
                    results["review"] = results.get("review", 0) + 1
                    summary.review_count += 1
            
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
    
    end_time = time.time()
    summary.durations["total_processing_time"] = end_time - start_time
    
    # Export consolidated Excel with validation data
    if invoice_results:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        excel_filename = f"invoices_{timestamp}.xlsx"
        excel_path = subdirs['excel'] / excel_filename
        
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
            if invoice_result.get("extraction_source") is not None:
                invoice_metadata["extraction_source"] = invoice_result["extraction_source"]
            
            excel_invoice_results.append({
                "invoice_lines": invoice_result["invoice_lines"],
                "invoice_metadata": invoice_metadata,
            })
        
        # Export to Excel (using updated function that accepts list of invoice results)
        export_to_excel(excel_invoice_results, str(excel_path))
        results["excel_path"] = str(excel_path)
        summary.excel_path = str(excel_path)
    else:
        results["excel_path"] = None
    
    # Export error report if errors occurred
    if results["errors"]:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        errors_filename = f"errors_{timestamp}.json"
        errors_path = subdirs['errors'] / errors_filename
        
        with open(errors_path, 'w', encoding='utf-8') as f:
            json.dump(results["errors"], f, indent=2, ensure_ascii=False)
        
        results["errors_path"] = str(errors_path)
        summary.errors_path = str(errors_path)
    else:
        results["errors_path"] = None
        
    # Create artifact manifest
    try:
        if run_artifacts_dir.exists():
            manifest = create_manifest_for_run(
                run_artifacts_dir, 
                summary.run_id,
                output_dir=output_dir_obj
            )
            if verbose:
                print(f"Artifact manifest created with {len(manifest.artifacts)} artifacts")
    except Exception as e:
        # Log warning but don't fail the run
        if verbose:
            print(f"Warning: Failed to create artifact manifest: {e}")
    
    # Check backward compatibility of existing artifacts (if any)
    try:
        compatibility_results = check_artifacts_compatibility(run_artifacts_dir)
        for artifact_type, result in compatibility_results.items():
            if result.status == CompatibilityStatus.INCOMPATIBLE:
                print(f"WARNING: {artifact_type} is incompatible: {result.message}")
            elif result.status == CompatibilityStatus.WARNING:
                if verbose:
                    print(f"INFO: {artifact_type} compatibility warning: {result.message}")
    except Exception as e:
        # Log warning but don't fail the run
        if verbose:
            print(f"Warning: Failed to check artifact compatibility: {e}")
    
    # Validation payload for GUI (single-PDF, first REVIEW)
    if len(pdf_files) == 1 and invoice_results:
        processed_pdf_path = str(Path(pdf_files[0]).resolve())
        for ir in invoice_results:
            if ir["validation_result"].status == "REVIEW":
                header = ir["invoice_header"]
                candidates = header.total_candidates or []
                summary.validation = {
                    "pdf_path": processed_pdf_path,
                    "candidates": [
                        {
                            "amount": c.get("amount", 0.0),
                            "score": c.get("score", 0.0),
                            "row_index": c.get("row_index", -1),
                            "keyword_type": c.get("keyword_type", "unknown"),
                        }
                        for c in candidates
                    ],
                    "traceability": header.total_traceability.to_dict() if header.total_traceability else None,
                    "extraction_source": ir.get("extraction_source"),
                }
                break
    
    # Save run summary
    summary.complete(status="FAILED" if summary.failed_count > 0 else "COMPLETED")
    summary_path = output_dir_obj / "run_summary.json"
    summary.save(summary_path)
    print(f"Run summary saved to: {summary_path}")
    
    return results


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="EPG PDF Extraherare - Extract structured data from Swedish PDF invoices"
    )
    
    parser.add_argument(
        "--input",
        required=False,
        help="Input directory or PDF file path (required unless --validate-confidence)"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch processing mode: process all PDFs in input directory with isolated artifacts per PDF"
    )
    
    parser.add_argument(
        "--output",
        required=False,
        help="Output directory for Excel files (default: Documents/EPG PDF Extraherare/output)"
    )
    
    parser.add_argument(
        "--artifacts-dir",
        required=False,
        help="Custom directory for run artifacts (default: output_dir/artifacts/<run_id>)"
    )
    
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop processing on first error"
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code if any invoice requires review"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug output"
    )
    
    parser.add_argument(
        "--compare-extraction",
        action="store_true",
        help="Run both pdfplumber and OCR, compare results, use best."
    )
    
    parser.add_argument(
        "--profile",
        type=str,
        default="default",
        help="Configuration profile name (default: default)"
    )
    
    parser.add_argument(
        "--validate-confidence",
        action="store_true",
        help="Validate confidence calibration against ground truth data"
    )
    
    parser.add_argument(
        "--ground-truth",
        type=str,
        help="Path to ground truth data file (JSON or CSV). Required with --validate-confidence if not using default path"
    )
    
    parser.add_argument(
        "--train",
        action="store_true",
        help="Train new calibration model from ground truth data (use with --validate-confidence)"
    )
    
    parser.add_argument(
        "--consolidate-patterns",
        action="store_true",
        help="Consolidate similar patterns in learning database"
    )
    
    parser.add_argument(
        "--cleanup-patterns",
        action="store_true",
        help="Clean up old and unused patterns from learning database"
    )
    
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=90,
        help="Maximum age in days for pattern cleanup (default: 90)"
    )
    
    parser.add_argument(
        "--query",
        type=str,
        help="Natural language query about invoice data (requires --excel-path)"
    )
    
    parser.add_argument(
        "--excel-path",
        type=str,
        help="Path to Excel file with invoice data (for --query command)"
    )
    
    parser.add_argument(
        "--supplier",
        type=str,
        help="Limit pattern operations to specific supplier name"
    )
    
    args = parser.parse_args()
    
    # Handle --validate-confidence command
    if args.validate_confidence:
        _handle_validate_confidence(args)
        return
    
    # Handle pattern maintenance commands
    if args.consolidate_patterns or args.cleanup_patterns:
        _handle_pattern_maintenance(args)
        return
    
    # Require --input for normal processing
    if not args.input:
        parser.error("--input is required (unless using --validate-confidence or pattern maintenance commands)")
    
    # Use default output directory if not specified
    output_dir = args.output
    if not output_dir:
        output_dir = str(get_default_output_dir())
        print(f"Using default output directory: {output_dir}")
    
    try:
        # Check if batch mode
        if args.batch:
            # Import here to avoid circular import
            from ..batch.runner import run_batch
            from ..batch.batch_summary import create_batch_summary
            
            # Batch processing mode: isolated execution per PDF
            input_path = Path(args.input)
            if not input_path.is_dir():
                raise ValueError(f"Batch mode requires a directory, got: {args.input}")
            
            output_path = Path(output_dir)
            batch_results = run_batch(
                input_path,
                output_path,
                fail_fast=args.fail_fast,
                verbose=args.verbose
            )
            
            # Create batch_summary.xlsx
            batch_summary_path = create_batch_summary(
                batch_results["results"],
                output_path
            )
            
            # Print summary
            print(f"\nBatch processing complete:")
            print(f"  Total files: {batch_results['total_files']}")
            print(f"  Processed: {batch_results['processed']}")
            print(f"  OK: {batch_results['ok']}")
            print(f"  PARTIAL: {batch_results['partial']}")
            print(f"  REVIEW: {batch_results['review']}")
            print(f"  Failed: {batch_results['failed']}")
            print(f"\nBatch summary: {batch_summary_path}")
            
            # Exit code
            exit_code = 0
            if batch_results["failed"] > 0:
                exit_code = 1
            elif args.strict and (batch_results["review"] > 0 or batch_results["partial"] > 0):
                exit_code = 1
            
            sys.exit(exit_code)
        else:
            # Regular batch processing (existing behavior)
            results = process_batch(
                args.input,
                output_dir,
                fail_fast=args.fail_fast,
                verbose=args.verbose,
                artifacts_dir=args.artifacts_dir,
                compare_extraction=args.compare_extraction
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
        
        # Exit code logic
        # Default: 0 if no failures (OK/PARTIAL/REVIEW are successes)
        # Strict: 0 only if all OK (PARTIAL/REVIEW/FAILED trigger error)
        # Actually DoD says: "!=0 vid Review/Failure". So strict should catch Review.
        
        exit_code = 0
        if results["failed"] > 0:
            exit_code = 1
        elif args.strict and (results["review"] > 0 or results["partial"] > 0):
            exit_code = 1
            
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def _handle_query(args: argparse.Namespace) -> None:
    """Handle query CLI command.
    
    Args:
        args: Parsed command-line arguments
    """
    from pathlib import Path
    from ..analysis.data_loader import load_invoices_from_excel
    from ..analysis.query_processor import parse_query
    from ..analysis.query_executor import execute_query, format_results
    from ..config import get_default_output_dir
    
    # Get Excel path
    excel_path = args.excel_path
    if not excel_path:
        # Try to find latest Excel file in output directory
        output_dir = Path(get_default_output_dir())
        excel_dir = output_dir / 'excel'
        if excel_dir.exists():
            excel_files = sorted(excel_dir.glob('*.xlsx'), key=lambda p: p.stat().st_mtime, reverse=True)
            if excel_files:
                excel_path = str(excel_files[0])
                print(f"Using latest Excel file: {excel_path}")
            else:
                print("Error: No Excel files found. Use --excel-path to specify a file.", file=sys.stderr)
                sys.exit(1)
        else:
            print("Error: Excel directory not found. Use --excel-path to specify a file.", file=sys.stderr)
            sys.exit(1)
    
    try:
        # Load invoices from Excel
        print(f"Loading invoices from {excel_path}...")
        data_store = load_invoices_from_excel(excel_path)
        print(f"Loaded {data_store.count()} invoices")
        
        # Parse query
        print(f"\nParsing query: {args.query}")
        query_intent = parse_query(args.query)
        
        # Execute query
        results = execute_query(query_intent, data_store)
        
        # Format and print results
        output = format_results(results, query_intent)
        print(f"\n{output}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _handle_pattern_maintenance(args: argparse.Namespace) -> None:
    """Handle pattern maintenance CLI commands.
    
    Args:
        args: Parsed command-line arguments
    """
    from ..learning.database import LearningDatabase
    from ..learning.pattern_consolidator import (
        consolidate_patterns,
        cleanup_patterns,
        PatternConsolidator
    )
    from ..config import get_learning_db_path
    
    # Initialize database
    db_path = get_learning_db_path()
    database = LearningDatabase(db_path)
    
    consolidator = PatternConsolidator(database)
    
    total_consolidated = 0
    total_removed = 0
    
    # Consolidate patterns
    if args.consolidate_patterns:
        print("Consolidating similar patterns...")
        consolidated = consolidator.consolidate_patterns(supplier=args.supplier)
        total_consolidated = consolidated
        print(f"✓ Consolidated {consolidated} patterns")
    
    # Cleanup patterns
    if args.cleanup_patterns:
        print(f"Cleaning up patterns (max age: {args.max_age_days} days)...")
        removed = consolidator.cleanup_patterns(
            max_age_days=args.max_age_days,
            supplier=args.supplier
        )
        total_removed = removed
        print(f"✓ Removed {removed} old/unused patterns")
    
    # Remove conflicting patterns (always run if doing maintenance)
    if args.consolidate_patterns or args.cleanup_patterns:
        print("Removing conflicting patterns...")
        conflicts_removed = consolidator.remove_conflicting_patterns(supplier=args.supplier)
        total_removed += conflicts_removed
        print(f"✓ Removed {conflicts_removed} conflicting patterns")
    
    # Summary
    print("\n" + "=" * 60)
    print("Pattern Maintenance Summary")
    print("=" * 60)
    print(f"Patterns consolidated: {total_consolidated}")
    print(f"Patterns removed: {total_removed}")
    print("=" * 60)


def _handle_validate_confidence(args: argparse.Namespace) -> None:
    """Handle --validate-confidence CLI command.
    
    Args:
        args: Parsed command-line arguments
    """
    # Determine ground truth data path
    ground_truth_path = args.ground_truth
    if not ground_truth_path:
        # Try default paths
        default_paths = [
            Path("data/ground_truth.json"),
            Path("data/ground_truth.csv"),
        ]
        found = False
        for path in default_paths:
            if path.exists():
                ground_truth_path = str(path)
                found = True
                break
        
        if not found:
            print(
                "Error: Ground truth data file not found.\n"
                "Please provide --ground-truth PATH or place data in data/ground_truth.json or data/ground_truth.csv",
                file=sys.stderr
            )
            sys.exit(1)
    
    try:
        # Load ground truth data
        print(f"Loading ground truth data from {ground_truth_path}...")
        raw_scores, actual_correct = load_ground_truth_data(ground_truth_path)
        
        if args.train:
            # Train new calibration model
            print(f"Training calibration model on {len(raw_scores)} samples...")
            model = train_calibration_model(raw_scores, actual_correct)
            
            # Save model
            model_path = get_calibration_model_path()
            model.save(model_path)
            print(f"Calibration model saved to {model_path}")
            
            # Validate the newly trained model
            print("\nValidating newly trained model...")
            report = validate_calibration(model, raw_scores, actual_correct)
            print(format_validation_report(report))
        else:
            # Validate existing calibration model
            model_path = get_calibration_model_path()
            model = CalibrationModel.load(model_path)
            
            if model is None:
                print(
                    f"Warning: No calibration model found at {model_path}.\n"
                    "Validating raw scores (no calibration applied).\n"
                    "Use --train to train a new model.",
                    file=sys.stderr
                )
            
            print("Validating calibration...")
            report = validate_calibration(model, raw_scores, actual_correct)
            print(format_validation_report(report))
            
            if report['suggest_recalibration']:
                print(
                    "\n💡 Tip: Run with --train flag to recalibrate the model",
                    file=sys.stderr
                )
                sys.exit(1)  # Exit with error code if recalibration needed
        
        sys.exit(0)
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""FastAPI application for invoice parser REST API."""

import tempfile
import uuid
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ..cli.main import process_invoice
from .models import (
    BatchProcessResponse,
    ErrorResponse,
    InvoiceLineResponse,
    InvoiceProcessResponse,
    InvoiceResultResponse,
    InvoiceStatusResponse,
)

app = FastAPI(
    title="Invoice Parser API",
    description="REST API för automatisk fakturabearbetning och extraktion",
    version="1.0.0",
)

# In-memory storage for results (för MVP)
# I produktion skulle detta vara en databas
_invoice_storage: Dict[str, Dict] = {}


def _store_invoice_result(invoice_id: str, result: Dict) -> None:
    """Store invoice processing result in memory."""
    _invoice_storage[invoice_id] = result


def _get_invoice_result(invoice_id: str) -> Dict:
    """Get invoice processing result from storage."""
    if invoice_id not in _invoice_storage:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    return _invoice_storage[invoice_id]


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Invoice Parser API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.post("/api/invoices/process", response_model=InvoiceProcessResponse)
async def process_invoice_endpoint(file: UploadFile = File(...)):
    """Process a single invoice PDF.
    
    Args:
        file: PDF file to process
        
    Returns:
        InvoiceProcessResponse with invoice_id, status, and line_count
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF (.pdf extension required)"
        )
    
    # Generate unique invoice ID
    invoice_id = str(uuid.uuid4())
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_path = tmp_file.name
        content = await file.read()
        tmp_file.write(content)
    
    try:
        # Process invoice using pipeline
        result = process_invoice(
            tmp_path,
            output_dir=str(Path(tmp_path).parent),
            verbose=False
        )
        
        # Extract data from result
        invoice_header = result.get("invoice_header")
        validation_result = result.get("validation_result")
        
        # Prepare stored result
        stored_result = {
            "invoice_id": invoice_id,
            "filename": file.filename,
            "status": result.get("status", "FAILED"),
            "line_count": result.get("line_count", 0),
            "invoice_header": invoice_header,
            "validation_result": validation_result,
            "invoice_lines": result.get("invoice_lines", []),
            "error": result.get("error"),
        }
        
        # Extract additional fields for easy access
        if invoice_header:
            stored_result["invoice_number"] = invoice_header.invoice_number
            stored_result["invoice_date"] = invoice_header.invoice_date
            stored_result["vendor_name"] = invoice_header.supplier_name
            stored_result["total_amount"] = invoice_header.total_amount
            stored_result["invoice_number_confidence"] = invoice_header.invoice_number_confidence
            stored_result["total_confidence"] = invoice_header.total_confidence
        else:
            stored_result["invoice_number"] = None
            stored_result["invoice_date"] = None
            stored_result["vendor_name"] = None
            stored_result["total_amount"] = None
            stored_result["invoice_number_confidence"] = 0.0
            stored_result["total_confidence"] = 0.0
        
        # Store result
        _store_invoice_result(invoice_id, stored_result)
        
        # Return response
        return InvoiceProcessResponse(
            invoice_id=invoice_id,
            status=stored_result["status"],
            line_count=stored_result["line_count"],
            message=stored_result.get("error"),
        )
        
    except Exception as e:
        # Store error result
        error_result = {
            "invoice_id": invoice_id,
            "filename": file.filename,
            "status": "FAILED",
            "line_count": 0,
            "error": str(e),
        }
        _store_invoice_result(invoice_id, error_result)
        
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )
    finally:
        # Cleanup temp file
        try:
            Path(tmp_path).unlink()
        except:
            pass


@app.get("/api/invoices/{invoice_id}/status", response_model=InvoiceStatusResponse)
async def get_invoice_status(invoice_id: str):
    """Get processing status for an invoice.
    
    Args:
        invoice_id: Unique invoice identifier
        
    Returns:
        InvoiceStatusResponse with status and basic information
    """
    result = _get_invoice_result(invoice_id)
    
    return InvoiceStatusResponse(
        invoice_id=invoice_id,
        status=result["status"],
        invoice_number=result.get("invoice_number"),
        total_amount=result.get("total_amount"),
        line_count=result["line_count"],
        invoice_number_confidence=result.get("invoice_number_confidence", 0.0),
        total_confidence=result.get("total_confidence", 0.0),
    )


@app.get("/api/invoices/{invoice_id}/result", response_model=InvoiceResultResponse)
async def get_invoice_result(invoice_id: str):
    """Get full processing result for an invoice.
    
    Args:
        invoice_id: Unique invoice identifier
        
    Returns:
        InvoiceResultResponse with all extracted fields and line items
    """
    result = _get_invoice_result(invoice_id)
    
    # Extract validation data
    validation_result = result.get("validation_result")
    errors = []
    warnings = []
    lines_sum = 0.0
    diff = None
    
    if validation_result:
        errors = validation_result.errors if hasattr(validation_result, "errors") else []
        warnings = validation_result.warnings if hasattr(validation_result, "warnings") else []
        lines_sum = validation_result.lines_sum if hasattr(validation_result, "lines_sum") else 0.0
        diff = validation_result.diff if hasattr(validation_result, "diff") else None
    
    # Convert invoice lines to response models
    invoice_lines = result.get("invoice_lines", [])
    line_items = []
    for line in invoice_lines:
        line_items.append(InvoiceLineResponse(
            line_number=line.line_number,
            description=line.description or "",
            quantity=line.quantity,
            unit=line.unit,
            unit_price=line.unit_price,
            discount=line.discount,
            total_amount=line.total_amount,
            vat_rate=line.vat_rate,
        ))
    
    return InvoiceResultResponse(
        invoice_id=invoice_id,
        status=result["status"],
        filename=result.get("filename", "unknown"),
        invoice_number=result.get("invoice_number"),
        invoice_date=result.get("invoice_date"),
        vendor_name=result.get("vendor_name"),
        total_amount=result.get("total_amount"),
        invoice_number_confidence=result.get("invoice_number_confidence", 0.0),
        total_confidence=result.get("total_confidence", 0.0),
        lines_sum=lines_sum,
        diff=diff,
        errors=errors,
        warnings=warnings,
        line_items=line_items,
        error=result.get("error"),
    )


@app.post("/api/invoices/batch", response_model=BatchProcessResponse)
async def process_batch_endpoint(files: List[UploadFile] = File(...)):
    """Process multiple invoice PDFs in batch.
    
    Args:
        files: List of PDF files to process
        
    Returns:
        BatchProcessResponse with results for each invoice
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    results = []
    
    for file in files:
        # Validate file type
        if not file.filename.endswith(".pdf"):
            results.append(InvoiceProcessResponse(
                invoice_id="",
                status="FAILED",
                line_count=0,
                message=f"File {file.filename} is not a PDF",
            ))
            continue
        
        # Process each file (reuse process_invoice_endpoint logic)
        try:
            # Generate unique invoice ID
            invoice_id = str(uuid.uuid4())
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_path = tmp_file.name
                content = await file.read()
                tmp_file.write(content)
            
            try:
                # Process invoice
                result = process_invoice(
                    tmp_path,
                    output_dir=str(Path(tmp_path).parent),
                    verbose=False
                )
                
                # Extract data
                invoice_header = result.get("invoice_header")
                
                # Prepare stored result
                stored_result = {
                    "invoice_id": invoice_id,
                    "filename": file.filename,
                    "status": result.get("status", "FAILED"),
                    "line_count": result.get("line_count", 0),
                    "invoice_header": invoice_header,
                    "validation_result": result.get("validation_result"),
                    "invoice_lines": result.get("invoice_lines", []),
                    "error": result.get("error"),
                }
                
                if invoice_header:
                    stored_result["invoice_number"] = invoice_header.invoice_number
                    stored_result["invoice_date"] = invoice_header.invoice_date
                    stored_result["vendor_name"] = invoice_header.supplier_name
                    stored_result["total_amount"] = invoice_header.total_amount
                    stored_result["invoice_number_confidence"] = invoice_header.invoice_number_confidence
                    stored_result["total_confidence"] = invoice_header.total_confidence
                else:
                    stored_result["invoice_number"] = None
                    stored_result["invoice_date"] = None
                    stored_result["vendor_name"] = None
                    stored_result["total_amount"] = None
                    stored_result["invoice_number_confidence"] = 0.0
                    stored_result["total_confidence"] = 0.0
                
                # Store result
                _store_invoice_result(invoice_id, stored_result)
                
                # Add to results
                results.append(InvoiceProcessResponse(
                    invoice_id=invoice_id,
                    status=stored_result["status"],
                    line_count=stored_result["line_count"],
                    message=stored_result.get("error"),
                ))
                
            except Exception as e:
                # Store error result
                error_result = {
                    "invoice_id": invoice_id,
                    "filename": file.filename,
                    "status": "FAILED",
                    "line_count": 0,
                    "error": str(e),
                }
                _store_invoice_result(invoice_id, error_result)
                
                results.append(InvoiceProcessResponse(
                    invoice_id=invoice_id,
                    status="FAILED",
                    line_count=0,
                    message=str(e),
                ))
            finally:
                # Cleanup temp file
                try:
                    Path(tmp_path).unlink()
                except:
                    pass
                    
        except Exception as e:
            results.append(InvoiceProcessResponse(
                invoice_id="",
                status="FAILED",
                line_count=0,
                message=f"Error processing {file.filename}: {str(e)}",
            ))
    
    return BatchProcessResponse(
        total=len(results),
        results=results,
    )


@app.get("/api/invoices", response_model=List[str])
async def list_invoices():
    """List all processed invoice IDs.
    
    Returns:
        List of invoice IDs
    """
    return list(_invoice_storage.keys())


@app.delete("/api/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str):
    """Delete an invoice result from storage.
    
    Args:
        invoice_id: Unique invoice identifier
    """
    if invoice_id not in _invoice_storage:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    
    del _invoice_storage[invoice_id]
    return {"message": f"Invoice {invoice_id} deleted"}

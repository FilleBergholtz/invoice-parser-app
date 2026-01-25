"""Excel export functionality with Swedish column names."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

import pandas as pd

from ..models.invoice_line import InvoiceLine


def export_to_excel(
    invoice_data: Union[List[Dict], List[InvoiceLine]],
    output_path: str,
    invoice_metadata: Optional[Dict] = None
) -> str:
    """Export InvoiceLines to Excel file with Swedish column names.
    
    Args:
        invoice_data: Either:
            - List of dicts with "invoice_lines" and "invoice_metadata" (batch mode)
            - List of InvoiceLine objects (legacy single-invoice mode)
        output_path: Path to output Excel file
        invoice_metadata: Optional metadata dict (legacy mode, ignored if invoice_data is list of dicts) with:
            - fakturanummer: Invoice number (or placeholder)
            - foretag: Vendor name (or placeholder)
            - fakturadatum: Invoice date (or placeholder)
            - referenser: Optional reference field
            - status: Validation status (OK/PARTIAL/REVIEW, default: "REVIEW")
            - lines_sum: Sum of all line item totals (default: 0.0)
            - diff: Difference between total and lines_sum, or "N/A" if None (default: "N/A")
            - invoice_number_confidence: Confidence score for invoice number (0.0-1.0, default: 0.0)
            - total_confidence: Confidence score for total amount (0.0-1.0, default: 0.0)
            
    Returns:
        Path to created Excel file
        
    Excel structure:
    - One row per InvoiceLine (product row)
    - Swedish column names: Fakturanummer, Referenser, Företag, Fakturadatum,
      Beskrivning, Antal, Enhet, Á-pris, Rabatt, Summa, Hela summan,
      Faktura-ID, Status, Radsumma, Avvikelse, Fakturanummer-konfidens, Totalsumma-konfidens
    - Invoice metadata repeated per row
    - Line item data from InvoiceLine objects
    - Control columns with validation data (after existing columns)
    - Faktura-ID column shows virtual_invoice_id (extraherade fakturanummer när det finns, annars "{file_stem}__{index}")
    """
    # Determine if invoice_data is batch mode (list of dicts) or legacy mode (list of InvoiceLine)
    if invoice_data and isinstance(invoice_data[0], dict) and "invoice_lines" in invoice_data[0]:
        # Batch mode: list of invoice result dicts
        batch_list = cast(List[Dict[str, Any]], invoice_data)
        all_rows = []
        for invoice_result in batch_list:
            invoice_lines = invoice_result["invoice_lines"]
            meta = invoice_result.get("invoice_metadata") or {}
            
            # Extract metadata
            fakturanummer = meta.get("fakturanummer", "TBD")
            foretag = meta.get("foretag", "TBD")
            fakturadatum = meta.get("fakturadatum", "TBD")
            referenser = meta.get("referenser", "")
            virtual_invoice_id = meta.get("virtual_invoice_id", "")
            
            # Extract validation fields
            status = meta.get("status", "REVIEW")
            lines_sum = meta.get("lines_sum", 0.0)
            diff = meta.get("diff", "N/A")
            invoice_number_confidence = meta.get("invoice_number_confidence", 0.0)
            total_confidence = meta.get("total_confidence", 0.0)
            extraction_source = meta.get("extraction_source") or ""
            
            # Calculate Hela summan (sum of all line totals for this invoice)
            hela_summan = sum(line.total_amount for line in invoice_lines)
            
            # Build rows for this invoice
            for line in invoice_lines:
                row = {
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
                    # Control columns (after existing columns)
                    "Faktura-ID": virtual_invoice_id,  # Virtual invoice ID for multi-invoice PDFs
                    "Status": status,
                    "Radsumma": lines_sum,
                    "Avvikelse": diff,
                    "Fakturanummer-konfidens": invoice_number_confidence,  # Excel format will convert to percentage
                    "Totalsumma-konfidens": total_confidence,  # Excel format will convert to percentage
                    "Extraktionskälla": extraction_source,  # "pdfplumber" | "ocr" when --compare-extraction was used
                }
                all_rows.append(row)
        
        rows = all_rows
    else:
        # Legacy mode: list of InvoiceLine objects with single metadata dict
        invoice_lines = cast(List[InvoiceLine], invoice_data)
        if not invoice_lines:
            raise ValueError("Cannot export empty invoice lines list")
        
        # Extract metadata (use placeholders if not provided)
        metadata = invoice_metadata or {}
        fakturanummer = metadata.get("fakturanummer", "TBD")
        foretag = metadata.get("foretag", "TBD")
        fakturadatum = metadata.get("fakturadatum", "TBD")
        referenser = metadata.get("referenser", "")
        
        # Extract validation fields (defaults for backward compatibility)
        status = metadata.get("status", "REVIEW")
        lines_sum = metadata.get("lines_sum", 0.0)
        diff = metadata.get("diff", "N/A")
        invoice_number_confidence = metadata.get("invoice_number_confidence", 0.0)
        total_confidence = metadata.get("total_confidence", 0.0)
        
        # Calculate Hela summan (sum of all line totals)
        hela_summan = sum(line.total_amount for line in invoice_lines)
        
        # Build DataFrame rows
        rows = []
        for line in invoice_lines:
            row = {
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
                # Control columns (after existing columns)
                "Status": status,
                "Radsumma": lines_sum,
                "Avvikelse": diff,
                "Fakturanummer-konfidens": invoice_number_confidence,  # Excel format will convert to percentage
                "Totalsumma-konfidens": total_confidence,  # Excel format will convert to percentage
            }
            rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Ensure output directory exists
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Invoices')
        
        # Get worksheet for formatting
        worksheet = writer.sheets['Invoices']
        
        # Format numeric columns
        from openpyxl.styles.numbers import FORMAT_NUMBER_00, FORMAT_PERCENTAGE_00
        
        # Format Summa and Hela summan columns (currency)
        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
            # Summa column (index J = 10, 1-indexed = 11)
            summa_cell = row[9]  # Column J (0-indexed)
            summa_cell.number_format = FORMAT_NUMBER_00
            
            # Hela summan column (index K = 11, 1-indexed = 12)
            hela_summan_cell = row[10]  # Column K (0-indexed)
            hela_summan_cell.number_format = FORMAT_NUMBER_00
        
        # Format Á-pris column if exists
        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
            apris_cell = row[7]  # Column H (Á-pris)
            if apris_cell.value:
                try:
                    float(apris_cell.value)
                    apris_cell.number_format = FORMAT_NUMBER_00
                except (ValueError, TypeError):
                    pass
        
        # Format control columns
        # Determine column indices based on whether Faktura-ID exists
        # Batch mode: Fakturanummer(0)...Hela summan(10), Faktura-ID(11), Status(12), Radsumma(13), Avvikelse(14), Fakturanummer-konfidens(15), Totalsumma-konfidens(16)
        # Legacy mode: Fakturanummer(0)...Hela summan(10), Status(11), Radsumma(12), Avvikelse(13), Fakturanummer-konfidens(14), Totalsumma-konfidens(15)
        num_columns = len(df.columns)
        has_faktura_id = "Faktura-ID" in df.columns
        
        if has_faktura_id:
            # Batch mode: Faktura-ID exists
            radsumma_idx = 13
            avvikelse_idx = 14
            fakturanummer_konfidens_idx = 15
            totalsumma_konfidens_idx = 16
        else:
            # Legacy mode: No Faktura-ID
            radsumma_idx = 12
            avvikelse_idx = 13
            fakturanummer_konfidens_idx = 14
            totalsumma_konfidens_idx = 15
        
        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
            # Radsumma column
            radsumma_cell = row[radsumma_idx]
            radsumma_cell.number_format = FORMAT_NUMBER_00
            
            # Avvikelse column
            avvikelse_cell = row[avvikelse_idx]
            # Only format if numeric (not "N/A" or None)
            if isinstance(avvikelse_cell.value, (int, float)) and avvikelse_cell.value != "N/A":
                avvikelse_cell.number_format = FORMAT_NUMBER_00
            
            # Fakturanummer-konfidens column
            fakturanummer_konfidens_cell = row[fakturanummer_konfidens_idx]
            fakturanummer_konfidens_cell.number_format = FORMAT_PERCENTAGE_00
            
            # Totalsumma-konfidens column
            totalsumma_konfidens_cell = row[totalsumma_konfidens_idx]
            totalsumma_konfidens_cell.number_format = FORMAT_PERCENTAGE_00
    
    return str(output_path)

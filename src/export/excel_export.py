"""Excel export functionality with Swedish column names."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

import pandas as pd

from ..models.invoice_line import InvoiceLine

logger = logging.getLogger(__name__)


def _excel_safe_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Convert timezone-aware datetimes to strings so Excel export does not raise."""
    import datetime as _dt
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            if getattr(df[col].dtype, "tz", None) is not None:
                df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Object or any other type: convert cells that are tz-aware datetime-like
            def _cell(value: Any) -> Any:
                if value is None or (isinstance(value, float) and pd.isna(value)):
                    return value
                tz = getattr(value, "tzinfo", None)
                if tz is not None and hasattr(value, "strftime"):
                    return value.strftime("%Y-%m-%d %H:%M:%S")
                return value
            df[col] = df[col].map(_cell, na_action="ignore")
    return df


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
            fakturatotal = meta.get("fakturatotal")  # Header total or validerad totalsumma
            
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
                    "Fakturatotal": fakturatotal,  # Fakturatotal / validerad totalsumma
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
        fakturatotal = metadata.get("fakturatotal")
        
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
                "Fakturatotal": fakturatotal,
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
    df = _excel_safe_dataframe(df)

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
        
        # Column indices by name (robust when columns are added)
        def _idx(name: str) -> int:
            return df.columns.get_loc(name) if name in df.columns else -1
        
        summa_idx = _idx("Summa")
        hela_summan_idx = _idx("Hela summan")
        fakturatotal_idx = _idx("Fakturatotal")
        apris_idx = _idx("Á-pris")
        radsumma_idx = _idx("Radsumma")
        avvikelse_idx = _idx("Avvikelse")
        fakturanummer_konfidens_idx = _idx("Fakturanummer-konfidens")
        totalsumma_konfidens_idx = _idx("Totalsumma-konfidens")
        
        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
            if summa_idx >= 0:
                row[summa_idx].number_format = FORMAT_NUMBER_00
            if hela_summan_idx >= 0:
                row[hela_summan_idx].number_format = FORMAT_NUMBER_00
            if fakturatotal_idx >= 0 and row[fakturatotal_idx].value is not None:
                try:
                    float(row[fakturatotal_idx].value)
                    row[fakturatotal_idx].number_format = FORMAT_NUMBER_00
                except (ValueError, TypeError):
                    pass
            if apris_idx >= 0 and row[apris_idx].value:
                try:
                    float(row[apris_idx].value)
                    row[apris_idx].number_format = FORMAT_NUMBER_00
                except (ValueError, TypeError):
                    pass
            if radsumma_idx >= 0:
                row[radsumma_idx].number_format = FORMAT_NUMBER_00
            if avvikelse_idx >= 0 and isinstance(row[avvikelse_idx].value, (int, float)):
                row[avvikelse_idx].number_format = FORMAT_NUMBER_00
            if fakturanummer_konfidens_idx >= 0:
                row[fakturanummer_konfidens_idx].number_format = FORMAT_PERCENTAGE_00
            if totalsumma_konfidens_idx >= 0:
                row[totalsumma_konfidens_idx].number_format = FORMAT_PERCENTAGE_00
    
    return str(output_path)


def apply_corrections_to_excel(
    excel_path: Union[str, Path],
    corrections: List[Dict[str, Any]],
) -> bool:
    """Update an existing Excel file with validated totals and confidence from corrections.

    For each row whose Faktura-ID matches a correction's invoice_id, sets
    Totalsumma-konfidens = corrected_confidence and Fakturatotal = corrected_total.
    Adds Fakturatotal column if missing.

    Args:
        excel_path: Path to the Excel file (e.g. from run_summary excel_path).
        corrections: List of correction dicts with invoice_id, corrected_total, corrected_confidence.

    Returns:
        True if the file was updated and saved, False if file missing or no changes.
    """
    path = Path(excel_path)
    if not path.exists():
        logger.debug("Excel file not found for corrections: %s", path)
        return False
    if not corrections:
        return False

    by_id: Dict[str, Dict[str, Any]] = {
        str(c.get("invoice_id", "")): c for c in corrections if c.get("invoice_id")
    }
    if not by_id:
        return False

    try:
        df = pd.read_excel(path, sheet_name="Invoices", engine="openpyxl")
    except Exception as e:
        logger.warning("Could not read Excel for corrections %s: %s", path, e)
        return False

    id_col = "Faktura-ID" if "Faktura-ID" in df.columns else None
    if not id_col:
        if df.index.size > 0 and len(corrections) == 1:
            c = corrections[0]
            id_col = df.columns[0]
            by_id[str(df[id_col].iloc[0])] = c
        else:
            logger.debug("Excel has no Faktura-ID column and cannot match corrections")
            return False

    tot_col = "Totalsumma-konfidens"
    fakturatotal_col = "Fakturatotal"
    if tot_col not in df.columns:
        return False

    if fakturatotal_col not in df.columns:
        df.insert(df.columns.get_loc(tot_col), fakturatotal_col, None)

    updated = 0
    for idx, inv_id in enumerate(df[id_col]):
        inv_id_str = str(inv_id).strip() if inv_id is not None else ""
        c = by_id.get(inv_id_str)
        if not c:
            continue
        conf = c.get("corrected_confidence")
        total = c.get("corrected_total")
        if conf is not None:
            df.at[idx, tot_col] = float(conf)
            updated += 1
        if total is not None:
            df.at[idx, fakturatotal_col] = float(total)

    if updated == 0:
        return False

    try:
        df.to_excel(path, index=False, sheet_name="Invoices", engine="openpyxl")
        logger.info("Updated Excel with %d correction(s): %s", updated, path)
        return True
    except Exception as e:
        logger.warning("Could not write Excel after corrections %s: %s", path, e)
        return False

"""Excel export functionality with Swedish column names."""

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from ..models.invoice_line import InvoiceLine


def export_to_excel(
    invoice_lines: List[InvoiceLine],
    output_path: str,
    invoice_metadata: Optional[Dict] = None
) -> str:
    """Export InvoiceLines to Excel file with Swedish column names.
    
    Args:
        invoice_lines: List of InvoiceLine objects to export
        output_path: Path to output Excel file
        invoice_metadata: Optional metadata dict with:
            - fakturanummer: Invoice number (or placeholder)
            - foretag: Vendor name (or placeholder)
            - fakturadatum: Invoice date (or placeholder)
            
    Returns:
        Path to created Excel file
        
    Excel structure:
    - One row per InvoiceLine (product row)
    - Swedish column names: Fakturanummer, Referenser, Företag, Fakturadatum,
      Beskrivning, Antal, Enhet, Á-pris, Rabatt, Summa, Hela summan
    - Invoice metadata repeated per row
    - Line item data from InvoiceLine objects
    """
    if not invoice_lines:
        raise ValueError("Cannot export empty invoice lines list")
    
    # Extract metadata (use placeholders if not provided)
    metadata = invoice_metadata or {}
    fakturanummer = metadata.get("fakturanummer", "TBD")
    foretag = metadata.get("foretag", "TBD")
    fakturadatum = metadata.get("fakturadatum", "TBD")
    referenser = metadata.get("referenser", "")
    
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
        from openpyxl.styles import NamedStyle
        from openpyxl.styles.numbers import FORMAT_NUMBER_00
        
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
    
    return str(output_path)

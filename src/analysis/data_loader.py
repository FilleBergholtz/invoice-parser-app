"""Invoice data loading from Excel files for querying."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class InvoiceDataStore:
    """In-memory store for invoice data."""
    
    def __init__(self):
        """Initialize empty invoice data store."""
        self._invoices: List[Dict[str, Any]] = []
    
    def add_invoice(self, invoice_data: Dict[str, Any]) -> None:
        """Add invoice to store.
        
        Args:
            invoice_data: Dict with invoice data (invoice_number, supplier_name, etc.)
        """
        self._invoices.append(invoice_data)
    
    def get_invoices(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get invoices with optional filters.
        
        Args:
            filters: Optional dict with filter criteria:
                - supplier_name: str or List[str]
                - invoice_number: str or List[str]
                - date_from: date
                - date_to: date
                - amount_min: float
                - amount_max: float
                - status: str or List[str]
        
        Returns:
            List of invoice dicts matching filters
        """
        if not filters:
            return self._invoices.copy()
        
        filtered = []
        for invoice in self._invoices:
            match = True
            
            # Filter by supplier
            if 'supplier_name' in filters:
                supplier_filter = filters['supplier_name']
                if isinstance(supplier_filter, list):
                    if invoice.get('supplier_name') not in supplier_filter:
                        match = False
                else:
                    if invoice.get('supplier_name') != supplier_filter:
                        match = False
            
            # Filter by invoice number
            if match and 'invoice_number' in filters:
                number_filter = filters['invoice_number']
                if isinstance(number_filter, list):
                    if invoice.get('invoice_number') not in number_filter:
                        match = False
                else:
                    if invoice.get('invoice_number') != number_filter:
                        match = False
            
            # Filter by date range
            if match and 'date_from' in filters:
                invoice_date = invoice.get('invoice_date')
                if invoice_date and invoice_date < filters['date_from']:
                    match = False
            
            if match and 'date_to' in filters:
                invoice_date = invoice.get('invoice_date')
                if invoice_date and invoice_date > filters['date_to']:
                    match = False
            
            # Filter by amount range
            if match and 'amount_min' in filters:
                total = invoice.get('total_amount', 0.0)
                if total < filters['amount_min']:
                    match = False
            
            if match and 'amount_max' in filters:
                total = invoice.get('total_amount', 0.0)
                if total > filters['amount_max']:
                    match = False
            
            # Filter by status
            if match and 'status' in filters:
                status_filter = filters['status']
                if isinstance(status_filter, list):
                    if invoice.get('status') not in status_filter:
                        match = False
                else:
                    if invoice.get('status') != status_filter:
                        match = False
            
            if match:
                filtered.append(invoice)
        
        return filtered
    
    def get_all_invoices(self) -> List[Dict[str, Any]]:
        """Get all invoices.
        
        Returns:
            List of all invoice dicts
        """
        return self._invoices.copy()
    
    def clear(self) -> None:
        """Clear all invoices from store."""
        self._invoices.clear()
    
    def count(self) -> int:
        """Get number of invoices in store.
        
        Returns:
            Number of invoices
        """
        return len(self._invoices)


def load_invoices_from_excel(excel_path: str) -> InvoiceDataStore:
    """Load invoices from Excel file created by export_to_excel().
    
    Args:
        excel_path: Path to Excel file
        
    Returns:
        InvoiceDataStore with loaded invoices
        
    Raises:
        FileNotFoundError: If Excel file doesn't exist
        ValueError: If Excel file format is invalid
    """
    path = Path(excel_path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    
    try:
        # Read Excel file
        df = pd.read_excel(excel_path, engine='openpyxl')
        
        # Required columns
        required_columns = ['Fakturanummer', 'Företag', 'Fakturadatum', 'Faktura-ID']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns in Excel file: {missing_columns}")
        
        # Group by invoice (using Faktura-ID or Fakturanummer)
        # Faktura-ID is unique per invoice (handles multi-invoice PDFs)
        # Fallback to Fakturanummer if Faktura-ID is empty
        df['_invoice_key'] = df['Faktura-ID'].fillna('') + '|' + df['Fakturanummer'].fillna('')
        
        # Create data store
        store = InvoiceDataStore()
        
        # Group by invoice
        for invoice_key, group in df.groupby('_invoice_key'):
            # Get first row for metadata (all rows have same metadata)
            first_row = group.iloc[0]
            
            # Parse invoice date
            invoice_date = None
            fakturadatum = first_row.get('Fakturadatum')
            if pd.notna(fakturadatum):
                if isinstance(fakturadatum, str):
                    # Try to parse date string
                    try:
                        invoice_date = datetime.strptime(fakturadatum, '%Y-%m-%d').date()
                    except ValueError:
                        try:
                            invoice_date = datetime.strptime(fakturadatum, '%Y-%m-%d %H:%M:%S').date()
                        except ValueError:
                            logger.warning(f"Could not parse date: {fakturadatum}")
                elif isinstance(fakturadatum, datetime):
                    invoice_date = fakturadatum.date()
                elif isinstance(fakturadatum, date):
                    invoice_date = fakturadatum
            
            # Extract line items
            line_items = []
            for _, row in group.iterrows():
                line_item = {
                    'description': row.get('Beskrivning', ''),
                    'quantity': row.get('Antal') if pd.notna(row.get('Antal')) else None,
                    'unit': row.get('Enhet', '') if pd.notna(row.get('Enhet')) else '',
                    'unit_price': row.get('Á-pris') if pd.notna(row.get('Á-pris')) else None,
                    'discount': row.get('Rabatt') if pd.notna(row.get('Rabatt')) else None,
                    'total_amount': row.get('Summa', 0.0) if pd.notna(row.get('Summa')) else 0.0,
                }
                line_items.append(line_item)
            
            # Calculate total amount (use Hela summan if available, else sum line items)
            hela_summan = first_row.get('Hela summan')
            if pd.notna(hela_summan):
                total_amount = float(hela_summan)
            else:
                total_amount = sum(item['total_amount'] for item in line_items)
            
            # Extract metadata
            invoice_data = {
                'invoice_number': str(first_row.get('Fakturanummer', 'TBD')),
                'supplier_name': str(first_row.get('Företag', 'TBD')),
                'invoice_date': invoice_date,
                'total_amount': total_amount,
                'status': str(first_row.get('Status', 'REVIEW')),
                'line_items': line_items,
                'metadata': {
                    'referenser': str(first_row.get('Referenser', '')) if pd.notna(first_row.get('Referenser')) else '',
                    'faktura_id': str(first_row.get('Faktura-ID', '')) if pd.notna(first_row.get('Faktura-ID')) else '',
                    'lines_sum': float(first_row.get('Radsumma', 0.0)) if pd.notna(first_row.get('Radsumma')) else 0.0,
                    'diff': first_row.get('Avvikelse', 'N/A'),
                    'invoice_number_confidence': float(first_row.get('Fakturanummer-konfidens', 0.0)) if pd.notna(first_row.get('Fakturanummer-konfidens')) else 0.0,
                    'total_confidence': float(first_row.get('Totalsumma-konfidens', 0.0)) if pd.notna(first_row.get('Totalsumma-konfidens')) else 0.0,
                }
            }
            
            store.add_invoice(invoice_data)
        
        logger.info(f"Loaded {store.count()} invoices from {excel_path}")
        return store
        
    except Exception as e:
        logger.error(f"Failed to load invoices from Excel: {e}")
        raise ValueError(f"Invalid Excel file format: {e}") from e

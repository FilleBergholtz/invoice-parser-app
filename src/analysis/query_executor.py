"""Query execution and result formatting for invoice data."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from .data_loader import InvoiceDataStore
from .query_processor import QueryIntent

logger = logging.getLogger(__name__)


def execute_query(
    query_intent: QueryIntent,
    data_store: InvoiceDataStore
) -> Dict[str, Any]:
    """Execute query against invoice data.
    
    Args:
        query_intent: QueryIntent with query structure
        data_store: InvoiceDataStore with invoice data
        
    Returns:
        Dict with query results:
        - invoices: List of invoice dicts (for filter queries)
        - aggregations: Dict with aggregation results (for aggregate queries)
        - summary: Dict with summary statistics (for summarize queries)
        - comparison: Dict with comparison data (for compare queries)
    """
    # Get filtered invoices
    invoices = data_store.get_invoices(query_intent.filters)
    
    # Apply aggregations if specified
    aggregations = {}
    if query_intent.aggregations:
        if 'sum' in query_intent.aggregations:
            aggregations['sum'] = sum(inv.get('total_amount', 0.0) for inv in invoices)
        if 'count' in query_intent.aggregations:
            aggregations['count'] = len(invoices)
        if 'average' in query_intent.aggregations:
            if invoices:
                aggregations['average'] = sum(inv.get('total_amount', 0.0) for inv in invoices) / len(invoices)
            else:
                aggregations['average'] = 0.0
    
    # Group by field if specified
    grouped = None
    if query_intent.group_by:
        grouped = _group_invoices(invoices, query_intent.group_by)
    
    # Sort results if specified
    if query_intent.sort_by:
        invoices = _sort_invoices(invoices, query_intent.sort_by)
    
    # Limit results if specified
    if query_intent.limit:
        invoices = invoices[:query_intent.limit]
    
    # Build result based on query type
    result = {
        'invoices': invoices,
        'count': len(invoices),
    }
    
    if aggregations:
        result['aggregations'] = aggregations
    
    if grouped:
        result['grouped'] = grouped
    
    # Add summary for summarize queries
    if query_intent.query_type == 'summarize':
        result['summary'] = _generate_summary(invoices)
    
    # Add comparison for compare queries
    if query_intent.query_type == 'compare':
        result['comparison'] = _generate_comparison(invoices, query_intent.filters)
    
    return result


def format_results(
    results: Dict[str, Any],
    query_intent: QueryIntent
) -> str:
    """Format query results as readable text.
    
    Args:
        results: Query results dict from execute_query()
        query_intent: QueryIntent with query structure
        
    Returns:
        Formatted string with results
    """
    output = []
    
    if query_intent.query_type == 'filter':
        # List invoices
        invoices = results.get('invoices', [])
        count = results.get('count', 0)
        
        output.append(f"Hittade {count} fakturor:")
        output.append("")
        
        for invoice in invoices:
            invoice_number = invoice.get('invoice_number', 'N/A')
            supplier = invoice.get('supplier_name', 'N/A')
            invoice_date = invoice.get('invoice_date')
            date_str = invoice_date.isoformat() if invoice_date else 'N/A'
            total = invoice.get('total_amount', 0.0)
            status = invoice.get('status', 'N/A')
            
            output.append(f"  • {invoice_number} - {supplier} ({date_str})")
            output.append(f"    Totalsumma: {total:.2f} SEK, Status: {status}")
    
    elif query_intent.query_type == 'aggregate':
        # Show aggregations
        aggregations = results.get('aggregations', {})
        count = results.get('count', 0)
        
        output.append(f"Resultat för {count} fakturor:")
        output.append("")
        
        if 'sum' in aggregations:
            output.append(f"  Totalsumma: {aggregations['sum']:.2f} SEK")
        if 'count' in aggregations:
            output.append(f"  Antal fakturor: {aggregations['count']}")
        if 'average' in aggregations:
            output.append(f"  Genomsnitt: {aggregations['average']:.2f} SEK")
    
    elif query_intent.query_type == 'summarize':
        # Show summary
        summary = results.get('summary', {})
        count = results.get('count', 0)
        
        output.append(f"Sammanfattning för {count} fakturor:")
        output.append("")
        
        if 'total_amount' in summary:
            output.append(f"  Totalsumma: {summary['total_amount']:.2f} SEK")
        if 'suppliers' in summary:
            output.append(f"  Antal leverantörer: {len(summary['suppliers'])}")
            output.append(f"  Leverantörer: {', '.join(summary['suppliers'][:5])}")
            if len(summary['suppliers']) > 5:
                output.append(f"    ... och {len(summary['suppliers']) - 5} fler")
        if 'date_range' in summary:
            date_range = summary['date_range']
            output.append(f"  Datumintervall: {date_range['from']} till {date_range['to']}")
        if 'status_breakdown' in summary:
            output.append("  Status:")
            for status, count in summary['status_breakdown'].items():
                output.append(f"    {status}: {count}")
    
    elif query_intent.query_type == 'compare':
        # Show comparison
        comparison = results.get('comparison', {})
        count = results.get('count', 0)
        
        output.append(f"Jämförelse för {count} fakturor:")
        output.append("")
        
        if 'by_supplier' in comparison:
            output.append("  Per leverantör:")
            for supplier, data in comparison['by_supplier'].items():
                output.append(f"    {supplier}:")
                output.append(f"      Antal: {data.get('count', 0)}")
                output.append(f"      Totalsumma: {data.get('total', 0.0):.2f} SEK")
                if data.get('average'):
                    output.append(f"      Genomsnitt: {data.get('average', 0.0):.2f} SEK")
    
    else:
        # Default: just show count
        count = results.get('count', 0)
        output.append(f"Resultat: {count} fakturor")
    
    return "\n".join(output)


def _group_invoices(invoices: List[Dict[str, Any]], group_by: str) -> Dict[str, List[Dict[str, Any]]]:
    """Group invoices by field.
    
    Args:
        invoices: List of invoice dicts
        group_by: Field to group by ('supplier', 'date', 'month', 'status')
        
    Returns:
        Dict with grouped invoices
    """
    grouped = defaultdict(list)
    
    for invoice in invoices:
        if group_by == 'supplier':
            key = invoice.get('supplier_name', 'Unknown')
        elif group_by == 'date':
            invoice_date = invoice.get('invoice_date')
            key = invoice_date.isoformat() if invoice_date else 'Unknown'
        elif group_by == 'month':
            invoice_date = invoice.get('invoice_date')
            if invoice_date:
                key = f"{invoice_date.year}-{invoice_date.month:02d}"
            else:
                key = 'Unknown'
        elif group_by == 'status':
            key = invoice.get('status', 'Unknown')
        else:
            key = 'Unknown'
        
        grouped[key].append(invoice)
    
    return dict(grouped)


def _sort_invoices(invoices: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
    """Sort invoices by field.
    
    Args:
        invoices: List of invoice dicts
        sort_by: Field to sort by ('date', 'amount', 'supplier')
        
    Returns:
        Sorted list of invoices
    """
    if sort_by == 'date':
        return sorted(invoices, key=lambda inv: inv.get('invoice_date') or date.min, reverse=True)
    elif sort_by == 'amount':
        return sorted(invoices, key=lambda inv: inv.get('total_amount', 0.0), reverse=True)
    elif sort_by == 'supplier':
        return sorted(invoices, key=lambda inv: inv.get('supplier_name', ''))
    else:
        return invoices


def _generate_summary(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary statistics for invoices.
    
    Args:
        invoices: List of invoice dicts
        
    Returns:
        Dict with summary statistics
    """
    if not invoices:
        return {}
    
    total_amount = sum(inv.get('total_amount', 0.0) for inv in invoices)
    suppliers = set(inv.get('supplier_name') for inv in invoices if inv.get('supplier_name'))
    
    dates = [inv.get('invoice_date') for inv in invoices if inv.get('invoice_date')]
    date_range = None
    if dates:
        date_range = {
            'from': min(dates).isoformat(),
            'to': max(dates).isoformat()
        }
    
    status_breakdown = defaultdict(int)
    for inv in invoices:
        status = inv.get('status', 'Unknown')
        status_breakdown[status] += 1
    
    return {
        'total_amount': total_amount,
        'suppliers': sorted(suppliers),
        'date_range': date_range,
        'status_breakdown': dict(status_breakdown)
    }


def _generate_comparison(invoices: List[Dict[str, Any]], filters: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comparison data for invoices.
    
    Args:
        invoices: List of invoice dicts
        filters: Original filters (may contain multiple suppliers for comparison)
        
    Returns:
        Dict with comparison data
    """
    by_supplier = defaultdict(lambda: {'count': 0, 'total': 0.0, 'invoices': []})
    
    for invoice in invoices:
        supplier = invoice.get('supplier_name', 'Unknown')
        by_supplier[supplier]['count'] += 1
        by_supplier[supplier]['total'] += invoice.get('total_amount', 0.0)
        by_supplier[supplier]['invoices'].append(invoice)
    
    # Calculate averages
    for supplier, data in by_supplier.items():
        if data['count'] > 0:
            data['average'] = data['total'] / data['count']
    
    return {
        'by_supplier': dict(by_supplier)
    }

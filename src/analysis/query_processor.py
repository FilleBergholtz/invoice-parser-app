"""Natural language query processing using AI."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..ai.fallback import AIFallback
from ..ai.providers import AIProvider
from ..config import get_ai_enabled, get_ai_key, get_ai_provider, get_ai_model

logger = logging.getLogger(__name__)


class QueryIntent(BaseModel):
    """Structured query intent parsed from natural language."""
    query_type: str = Field(description="Type of query: 'filter', 'aggregate', 'summarize', 'compare'")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filter criteria")
    aggregations: List[str] = Field(default_factory=list, description="Aggregations: 'sum', 'count', 'average'")
    group_by: Optional[str] = Field(None, description="Group by field: 'supplier', 'date', 'month', 'status'")
    sort_by: Optional[str] = Field(None, description="Sort by field: 'date', 'amount', 'supplier'")
    limit: Optional[int] = Field(None, description="Maximum number of results")


def parse_query(query: str, provider: Optional[AIProvider] = None) -> QueryIntent:
    """Parse natural language query into structured QueryIntent.
    
    Args:
        query: Natural language query string
        provider: Optional AIProvider instance (creates from config if None)
        
    Returns:
        QueryIntent object with parsed query structure
        
    Raises:
        ValueError: If AI is not enabled or query parsing fails
    """
    if not get_ai_enabled():
        raise ValueError("AI is not enabled. Set AI_ENABLED=true to use query processing.")
    
    # Create AI fallback for query processing
    if provider is None:
        fallback = AIFallback()
        if not fallback.provider:
            raise ValueError("AI provider not configured. Set AI_KEY and AI_PROVIDER environment variables.")
        provider = fallback.provider
    
    # Build prompt for query parsing
    prompt = f"""Parse this Swedish/English natural language query about invoices into structured format:

Query: {query}

Extract:
1. Query type: "filter" (list invoices), "aggregate" (sum/count/average), "summarize" (summary statistics), "compare" (compare invoices)
2. Filters:
   - supplier_name: Supplier/company name (string)
   - date_from: Start date (YYYY-MM-DD format)
   - date_to: End date (YYYY-MM-DD format)
   - amount_min: Minimum amount (float)
   - amount_max: Maximum amount (float)
   - status: Status filter ("OK", "PARTIAL", "REVIEW", "FAILED")
3. Aggregations: List of aggregations needed ("sum", "count", "average")
4. Group by: Field to group results by ("supplier", "date", "month", "status")
5. Sort by: Field to sort by ("date", "amount", "supplier")
6. Limit: Maximum number of results (integer)

Return JSON format:
{{
  "query_type": "filter",
  "filters": {{"supplier_name": "Acme Corp", "date_from": "2026-01-01", "date_to": "2026-01-31"}},
  "aggregations": [],
  "group_by": null,
  "sort_by": "date",
  "limit": null
}}

Examples:
- "Visa alla fakturor från Acme Corp i januari" → {{"query_type": "filter", "filters": {{"supplier_name": "Acme Corp", "date_from": "2026-01-01", "date_to": "2026-01-31"}}}}
- "Vad är totalsumman för alla fakturor från leverantör X?" → {{"query_type": "aggregate", "filters": {{"supplier_name": "X"}}, "aggregations": ["sum"]}}
- "Sammanfattning av fakturor i januari" → {{"query_type": "summarize", "filters": {{"date_from": "2026-01-01", "date_to": "2026-01-31"}}}}
- "Jämför fakturor från leverantör A och B" → {{"query_type": "compare", "filters": {{"supplier_name": ["A", "B"]}}}}
"""
    
    try:
        # Use AI to parse query
        if hasattr(provider, 'extract_total_amount'):
            # For OpenAI/Claude providers, we need a different approach
            # Use a simple text-based parsing for now, or extend provider
            # For now, use fallback parsing
            result = _parse_query_fallback(query)
        else:
            # Try to use provider's general extraction
            result = _parse_query_fallback(query)
        
        # Parse result into QueryIntent
        return QueryIntent(**result)
        
    except Exception as e:
        logger.warning(f"AI query parsing failed, using fallback: {e}")
        # Fallback to simple pattern matching
        return _parse_query_fallback(query)


def _parse_query_fallback(query: str) -> Dict[str, Any]:
    """Fallback query parser using simple pattern matching.
    
    Args:
        query: Natural language query string
        
    Returns:
        Dict with query intent structure
    """
    query_lower = query.lower()
    
    # Determine query type
    query_type = "filter"
    if any(word in query_lower for word in ["summa", "totalsumma", "total", "sum"]):
        query_type = "aggregate"
    elif any(word in query_lower for word in ["sammanfattning", "summary", "översikt"]):
        query_type = "summarize"
    elif any(word in query_lower for word in ["jämför", "compare", "sammenlign"]):
        query_type = "compare"
    
    # Extract filters
    filters = {}
    
    # Extract supplier name (simple pattern)
    # Look for "från X", "from X", "leverantör X", "supplier X"
    import re
    supplier_patterns = [
        r"från\s+([A-Za-zÅÄÖåäö\s]+?)(?:\s+i\s+|\s+från\s+|$)",
        r"from\s+([A-Za-zÅÄÖåäö\s]+?)(?:\s+in\s+|\s+from\s+|$)",
        r"leverantör\s+([A-Za-zÅÄÖåäö\s]+?)(?:\s+i\s+|$)",
        r"supplier\s+([A-Za-zÅÄÖåäö\s]+?)(?:\s+in\s+|$)",
    ]
    for pattern in supplier_patterns:
        match = re.search(pattern, query_lower)
        if match:
            filters['supplier_name'] = match.group(1).strip()
            break
    
    # Extract date range (simple patterns)
    # "i januari" -> 2026-01-01 to 2026-01-31
    # "i januari 2026" -> 2026-01-01 to 2026-01-31
    month_names = {
        'januari': 1, 'februari': 2, 'mars': 3, 'april': 4, 'maj': 5, 'juni': 6,
        'juli': 7, 'augusti': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    
    for month_name, month_num in month_names.items():
        if month_name in query_lower:
            # Default to current year
            from datetime import date
            year = date.today().year
            # Try to extract year
            year_match = re.search(r'(\d{4})', query)
            if year_match:
                year = int(year_match.group(1))
            
            # Calculate date range
            from calendar import monthrange
            _, last_day = monthrange(year, month_num)
            filters['date_from'] = date(year, month_num, 1)
            filters['date_to'] = date(year, month_num, last_day)
            break
    
    # Extract aggregations
    aggregations = []
    if any(word in query_lower for word in ["summa", "totalsumma", "total", "sum"]):
        aggregations.append("sum")
    if any(word in query_lower for word in ["antal", "count", "number"]):
        aggregations.append("count")
    if any(word in query_lower for word in ["genomsnitt", "average", "medel"]):
        aggregations.append("average")
    
    # Extract sort_by
    sort_by = None
    if any(word in query_lower for word in ["sortera", "sort"]):
        if "datum" in query_lower or "date" in query_lower:
            sort_by = "date"
        elif "belopp" in query_lower or "amount" in query_lower:
            sort_by = "amount"
        elif "leverantör" in query_lower or "supplier" in query_lower:
            sort_by = "supplier"
    
    return {
        'query_type': query_type,
        'filters': filters,
        'aggregations': aggregations,
        'group_by': None,
        'sort_by': sort_by,
        'limit': None
    }

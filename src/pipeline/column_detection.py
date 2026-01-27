"""Column detection for position-based table parsing (mode B).

This module implements gap-based column detection algorithms for identifying
table columns from spatial analysis of token positions.
"""

import logging
import statistics
from typing import Dict, List, Optional

from ..models.row import Row
from ..models.token import Token

logger = logging.getLogger(__name__)


def detect_columns_gap_based(
    rows: List[Row],
    min_gap: float = 20.0
) -> List[float]:
    """Detect columns using gap-based algorithm.
    
    Identifies columns by analyzing gaps (spaces) between token clusters in X-direction.
    Large gaps (>min_gap) indicate column boundaries.
    
    Args:
        rows: List of table rows
        min_gap: Minimum gap between columns in points (default 20.0)
        
    Returns:
        List of column center X-positions (sorted left to right)
        
    Edge cases:
        - No gaps found → single column (returns median X-position)
        - Too many gaps → uses adaptive threshold (median gap × 1.5)
        - Empty rows → returns empty list
    """
    if not rows:
        return []
    
    # Collect all token X-positions (centers, not left edges)
    x_positions = []
    for row in rows:
        if not row.tokens:
            continue
        for token in row.tokens:
            x_center = token.x + (token.width / 2)
            x_positions.append(x_center)
    
    if not x_positions:
        return []
    
    # Sort X-positions
    x_positions.sort()
    
    # Find gaps (large spaces between consecutive X-positions)
    gaps = []
    for i in range(len(x_positions) - 1):
        gap = x_positions[i + 1] - x_positions[i]
        if gap > min_gap:
            gaps.append((x_positions[i], x_positions[i + 1], gap))
    
    # Adaptive threshold: if too many gaps, use median gap × 1.5
    # This handles cases with variable spacing (over-clustering prevention)
    if len(gaps) > 10:  # Too many gaps - likely over-clustering
        gap_sizes = [g[2] for g in gaps]
        median_gap = statistics.median(gap_sizes)
        adaptive_threshold = median_gap * 1.5
        gaps = [g for g in gaps if g[2] > adaptive_threshold]
        logger.debug(
            f"Applied adaptive threshold {adaptive_threshold:.1f}pt "
            f"(median gap {median_gap:.1f}pt) to reduce {len(gap_sizes)} gaps"
        )
    
    # Column boundaries are midpoints of large gaps
    column_boundaries = []
    for left_x, right_x, gap_size in gaps:
        boundary = (left_x + right_x) / 2
        column_boundaries.append(boundary)
    
    # Column centers are midpoints between boundaries
    column_centers = []
    if column_boundaries:
        # First column: from 0 to first boundary
        column_centers.append(column_boundaries[0] / 2)
        
        # Middle columns: between boundaries
        for i in range(len(column_boundaries) - 1):
            center = (column_boundaries[i] + column_boundaries[i + 1]) / 2
            column_centers.append(center)
        
        # Last column: from last boundary to page width
        page_width = rows[0].page.width if rows and rows[0].page else 595.0
        last_center = (column_boundaries[-1] + page_width) / 2
        column_centers.append(last_center)
    else:
        # No gaps found - single column (description only)
        # Return median X-position as single column center
        column_centers.append(statistics.median(x_positions))
        logger.debug(
            f"No gaps found (min_gap={min_gap:.1f}pt), "
            f"treating as single column at {column_centers[0]:.1f}pt"
        )
    
    return sorted(column_centers)


def map_columns_from_header(
    header_row: Row,
    column_centers: List[float]
) -> Optional[Dict[str, int]]:
    """Map columns to fields using header row keywords.
    
    Identifies which column contains which field (description, quantity, unit, etc.)
    by matching header row tokens against field keywords.
    
    Args:
        header_row: Table header row (e.g., "Artikelnr Benämning Antal Enhet Pris Moms% Nettobelopp")
        column_centers: List of column center X-positions
        
    Returns:
        Dict mapping field names to column indices: {'description': 1, 'quantity': 2, ...}
        Returns None if header row is empty or no matches found
        
    Field keywords:
        - description: benämning, beskrivning, artikel, produkt, text
        - quantity: antal, kvantitet, qty, st, mängd
        - unit: enhet, unit, st, kg, tim
        - unit_price: pris, á-pris, a-pris, enhetspris, price
        - vat_percent: moms, moms%, vat, vat%
        - netto: nettobelopp, netto, belopp, total, summa
    """
    if not header_row.tokens or not column_centers:
        return None
    
    field_keywords = {
        'description': ['benämning', 'beskrivning', 'artikel', 'produkt', 'text'],
        'quantity': ['antal', 'kvantitet', 'qty', 'st', 'mängd'],
        'unit': ['enhet', 'unit', 'st', 'kg', 'tim'],
        'unit_price': ['pris', 'á-pris', 'a-pris', 'enhetspris', 'price'],
        'vat_percent': ['moms', 'moms%', 'vat', 'vat%'],
        'netto': ['nettobelopp', 'netto', 'belopp', 'total', 'summa']
    }
    
    column_map = {}
    
    # For each token in header, find which column it belongs to
    for token in header_row.tokens:
        token_center = token.x + (token.width / 2)
        token_text_lower = token.text.lower()
        
        # Find nearest column
        nearest_col_idx = min(
            range(len(column_centers)),
            key=lambda i: abs(column_centers[i] - token_center)
        )
        
        # Check if token matches any field keywords
        for field_name, keywords in field_keywords.items():
            if any(keyword in token_text_lower for keyword in keywords):
                # Only map if not already mapped (first match wins)
                if field_name not in column_map:
                    column_map[field_name] = nearest_col_idx
                break
    
    # Return None if no mappings found
    if not column_map:
        return None
    
    return column_map


def assign_tokens_to_columns(
    row: Row,
    column_centers: List[float]
) -> Dict[int, List[Token]]:
    """Assign tokens to columns based on X-position.
    
    Uses nearest-neighbor assignment: each token is assigned to the column
    whose center is closest to the token's center.
    
    Args:
        row: Row to process
        column_centers: List of column center X-positions (sorted left to right)
        
    Returns:
        Dict mapping column index to list of tokens in that column:
        {0: [token1, token2], 1: [token3], ...}
        
    Note:
        Uses token center (x + width/2) for better precision than left edge.
    """
    if not column_centers:
        return {}
    
    # Initialize column token lists
    column_tokens = {i: [] for i in range(len(column_centers))}
    
    if not row.tokens:
        return column_tokens
    
    for token in row.tokens:
        token_center = token.x + (token.width / 2)
        
        # Find nearest column (nearest-neighbor assignment)
        nearest_col_idx = min(
            range(len(column_centers)),
            key=lambda i: abs(column_centers[i] - token_center)
        )
        
        column_tokens[nearest_col_idx].append(token)
    
    return column_tokens

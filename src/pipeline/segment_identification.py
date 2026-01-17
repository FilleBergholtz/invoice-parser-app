"""Row-to-segment identification (header, items, footer)."""

from typing import List

from ..models.page import Page
from ..models.row import Row
from ..models.segment import Segment


def identify_segments(rows: List[Row], page: Page) -> List[Segment]:
    """Identify document segments (header, items, footer) from rows.
    
    Args:
        rows: List of Row objects (ordered top-to-bottom)
        page: Page object for dimension reference
        
    Returns:
        List of Segment objects (header, items, footer)
        
    Algorithm:
    - Position-based segmentation:
      - Header: top 20-30% of page (rows with y < 0.3 * page.height)
      - Footer: bottom 20-30% of page (rows with y > 0.7 * page.height)
      - Items: middle section (rows between header and footer)
    - Create Segment objects with appropriate rows
    - Set y_min, y_max from row positions
    """
    if not rows:
        return []
    
    if not page:
        raise ValueError("Page reference required for segment identification")
    
    # Calculate page regions based on height
    page_height = page.height
    header_threshold = 0.3 * page_height  # Top 30%
    footer_threshold = 0.7 * page_height  # Bottom 30% (y > 70% of height)
    
    header_rows = []
    items_rows = []
    footer_rows = []
    
    # Classify rows into segments based on Y-position
    for row in rows:
        if row.y < header_threshold:
            header_rows.append(row)
        elif row.y > footer_threshold:
            footer_rows.append(row)
        else:
            items_rows.append(row)
    
    segments = []
    
    # Create header segment
    if header_rows:
        y_min = min(r.y for r in header_rows)
        y_max = max(r.y for r in header_rows)
        segments.append(Segment(
            segment_type="header",
            rows=header_rows,
            y_min=y_min,
            y_max=y_max,
            page=page
        ))
    
    # Create items segment
    if items_rows:
        y_min = min(r.y for r in items_rows)
        y_max = max(r.y for r in items_rows)
        segments.append(Segment(
            segment_type="items",
            rows=items_rows,
            y_min=y_min,
            y_max=y_max,
            page=page
        ))
    
    # Create footer segment (if exists)
    if footer_rows:
        y_min = min(r.y for r in footer_rows)
        y_max = max(r.y for r in footer_rows)
        segments.append(Segment(
            segment_type="footer",
            rows=footer_rows,
            y_min=y_min,
            y_max=y_max,
            page=page
        ))
    
    # Ensure at least header and items segments exist
    # If no header/items were found, assign all rows to items
    if not segments:
        # Edge case: very short invoice or no clear segments
        # Assign all rows to items
        y_min = min(r.y for r in rows)
        y_max = max(r.y for r in rows)
        segments.append(Segment(
            segment_type="items",
            rows=rows,
            y_min=y_min,
            y_max=y_max,
            page=page
        ))
    elif not any(s.segment_type == "header" for s in segments) and not any(s.segment_type == "items" for s in segments):
        # Only footer found - assign all to items
        all_rows = header_rows + items_rows + footer_rows
        y_min = min(r.y for r in all_rows)
        y_max = max(r.y for r in all_rows)
        segments.insert(0, Segment(
            segment_type="items",
            rows=all_rows,
            y_min=y_min,
            y_max=y_max,
            page=page
        ))
    
    return segments

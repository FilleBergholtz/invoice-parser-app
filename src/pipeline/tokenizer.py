"""Token extraction from pdfplumber (searchable PDFs)."""

import statistics
from typing import List, TYPE_CHECKING

import pdfplumber

from ..models.page import Page
from ..models.token import Token

if TYPE_CHECKING:
    from pdfplumber.page import Page as PDFPlumberPage
else:
    PDFPlumberPage = object  # type: ignore

# extra_attrs can cause edge cases on some PDFs; we try with them first and fall back.
_EXTRA_ATTRS = ["fontname", "size"]


def _tokens_reading_order(tokens: List[Token]) -> List[Token]:
    """Sort tokens by reading order using line clustering.
    Groups tokens with similar y (within a line threshold), sorts lines by y,
    tokens within each line by x. Avoids mixing lines when vertical spacing is uneven.
    """
    if not tokens:
        return []
    if len(tokens) == 1:
        return list(tokens)
    # Line threshold: fraction of median token height; clamp to sensible range
    heights = [t.height for t in tokens if t.height > 0]
    if heights:
        line_threshold = max(2.0, min(0.5 * statistics.median(heights), 15.0))
    else:
        line_threshold = 5.0
    # Sort by y then x for grouping
    by_xy = sorted(tokens, key=lambda t: (t.y, t.x))
    lines: List[List[Token]] = []
    current_line: List[Token] = [by_xy[0]]
    for t in by_xy[1:]:
        if abs(t.y - current_line[0].y) <= line_threshold:
            current_line.append(t)
        else:
            current_line.sort(key=lambda o: o.x)
            lines.append(current_line)
            current_line = [t]
    current_line.sort(key=lambda o: o.x)
    lines.append(current_line)
    out: List[Token] = []
    for line in lines:
        out.extend(line)
    return out


def extract_tokens_from_page(page: Page, pdfplumber_page: PDFPlumberPage) -> List[Token]:
    """Extract tokens from pdfplumber page object with spatial information.
    
    Args:
        page: Page object to populate with tokens
        pdfplumber_page: pdfplumber Page object with text objects
        
    Returns:
        List of Token objects with spatial information
        
    Note:
        Tokens are added to page.tokens list for traceability.
        Reading order is preserved (top-to-bottom, left-to-right).
    """
    tokens = []
    
    try:
        # extract_words: use_text_flow=True improves reading order for multi-column/complex layouts.
        # extra_attrs=["fontname","size"] can trigger edge cases on some PDFs — try first, fall back.
        kwargs: dict = {
            "x_tolerance": 3,
            "y_tolerance": 3,
            "use_text_flow": True,
        }
        try:
            words = pdfplumber_page.extract_words(**kwargs, extra_attrs=_EXTRA_ATTRS)
        except Exception:
            words = pdfplumber_page.extract_words(**kwargs)
        if not words and _EXTRA_ATTRS:
            # some PDFs return empty when extra_attrs is used
            words = pdfplumber_page.extract_words(**kwargs)
        
        for word in words:
            # Extract text content
            text = word.get('text', '').strip()
            
            # Skip empty text
            if not text:
                continue
            
            # Extract bounding box
            x0 = float(word.get('x0', 0))
            y0 = float(word.get('top', 0))  # pdfplumber uses 'top' for Y
            x1 = float(word.get('x1', 0))
            bottom = float(word.get('bottom', 0))  # pdfplumber uses 'bottom' for bottom Y
            
            # Calculate width and height
            width = x1 - x0
            height = bottom - y0
            
            # Validate bbox
            if width <= 0 or height <= 0:
                continue  # Skip invalid tokens
            
            # Get font information if available
            font_size = word.get('size')
            font_name = word.get('fontname')
            
            # Create Token object
            token = Token(
                text=text,
                x=x0,
                y=y0,  # Top-left Y coordinate
                width=width,
                height=height,
                page=page,
                font_size=float(font_size) if font_size is not None else None,
                font_name=str(font_name) if font_name is not None else None
            )
            
            tokens.append(token)
        
        # Reading order via line clustering (avoids mixing lines when spacing is uneven)
        tokens = _tokens_reading_order(tokens)
        
        # Add tokens to page for traceability
        page.tokens.extend(tokens)
        
        return tokens
        
    except Exception as e:
        # If extraction fails, return empty list but don't crash
        # Caller can handle empty token list
        return []

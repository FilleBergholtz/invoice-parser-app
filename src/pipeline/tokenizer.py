"""Token extraction from pdfplumber (searchable PDFs)."""

from typing import List

import pdfplumber

from ..models.page import Page
from ..models.token import Token


def extract_tokens_from_page(page: Page, pdfplumber_page: pdfplumber.Page) -> List[Token]:
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
        # Extract words/characters with their bounding boxes
        # Using chars gives more granular control over position
        chars = pdfplumber_page.chars
        
        # Group characters into tokens (words)
        # A token is typically a word or number, but we'll use pdfplumber's word grouping
        words = pdfplumber_page.extract_words(
            x_tolerance=3,  # Tolerance for grouping characters into words
            y_tolerance=3
        )
        
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
        
        # Sort tokens by reading order (top-to-bottom, left-to-right)
        # First by Y (top), then by X (left)
        tokens.sort(key=lambda t: (t.y, t.x))
        
        # Add tokens to page for traceability
        page.tokens.extend(tokens)
        
        return tokens
        
    except Exception as e:
        # If extraction fails, return empty list but don't crash
        # Caller can handle empty token list
        return []

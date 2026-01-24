"""Pattern matching for new invoices against learned patterns."""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from .database import LearningDatabase
from .pattern_extractor import PatternExtractor

logger = logging.getLogger(__name__)


class PatternMatcher:
    """Matches new invoices against learned patterns for confidence boosting.
    
    Performs supplier-specific pattern matching and calculates similarity scores.
    """
    
    def __init__(self, database: LearningDatabase):
        """Initialize pattern matcher.
        
        Args:
            database: LearningDatabase instance
        """
        self.database = database
    
    def calculate_similarity(
        self,
        pattern: Dict[str, Any],
        layout_hash: Optional[str] = None,
        position: Optional[Dict[str, float]] = None
    ) -> float:
        """Calculate similarity score between pattern and invoice.
        
        Args:
            pattern: Pattern dict from database
            layout_hash: Invoice layout hash (optional)
            position: Invoice position dict with x, y, width, height (optional)
            
        Returns:
            Similarity score (0.0-1.0)
        """
        layout_match = 0.0
        position_similarity = 0.0
        
        # Layout hash matching
        if layout_hash and pattern.get('layout_hash'):
            if layout_hash == pattern['layout_hash']:
                layout_match = 1.0
        
        # Position similarity
        if position and pattern.get('position_x') is not None:
            pattern_x = pattern.get('position_x', 0.0)
            pattern_y = pattern.get('position_y', 0.0)
            invoice_x = position.get('x', 0.0)
            invoice_y = position.get('y', 0.0)
            
            # Calculate distance
            x_diff = pattern_x - invoice_x
            y_diff = pattern_y - invoice_y
            distance = math.sqrt(x_diff * x_diff + y_diff * y_diff)
            
            # Normalize: 100 points distance = 0.5 similarity
            # Formula: similarity = 1.0 / (1.0 + distance / 100.0)
            position_similarity = 1.0 / (1.0 + distance / 100.0)
        elif not position and pattern.get('position_x') is None:
            # Both missing position - neutral (0.5)
            position_similarity = 0.5
        
        # Combined similarity: weighted average
        # Layout: 0.5 weight, Position: 0.5 weight
        combined = (layout_match * 0.5) + (position_similarity * 0.5)
        
        return combined
    
    def match_patterns(
        self,
        supplier_name: str,
        layout_hash: Optional[str] = None,
        position: Optional[Dict[str, float]] = None,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Match patterns for supplier.
        
        Args:
            supplier_name: Supplier name (will be normalized)
            layout_hash: Optional layout hash for matching
            position: Optional position dict with x, y, width, height
            similarity_threshold: Minimum similarity to return (default 0.5)
            
        Returns:
            List of matched patterns with similarity scores, sorted by similarity (highest first)
        """
        if not supplier_name:
            logger.warning("No supplier name provided for pattern matching")
            return []
        
        # Normalize supplier name
        normalized_supplier = PatternExtractor.normalize_supplier(supplier_name)
        
        # Query patterns for supplier (supplier-specific only)
        patterns = self.database.get_patterns(supplier=normalized_supplier)
        
        if not patterns:
            logger.debug(f"No patterns found for supplier: {normalized_supplier}")
            return []
        
        # Calculate similarity for each pattern
        matched_patterns = []
        for pattern in patterns:
            similarity = self.calculate_similarity(pattern, layout_hash, position)
            
            if similarity >= similarity_threshold:
                # Add similarity to pattern dict
                pattern_with_similarity = dict(pattern)
                pattern_with_similarity['similarity'] = similarity
                matched_patterns.append(pattern_with_similarity)
        
        # Sort by similarity (highest first)
        matched_patterns.sort(key=lambda p: p.get('similarity', 0.0), reverse=True)
        
        logger.debug(
            f"Matched {len(matched_patterns)} patterns for supplier {normalized_supplier} "
            f"(threshold: {similarity_threshold})"
        )
        
        return matched_patterns


def match_patterns(
    supplier_name: str,
    database: LearningDatabase,
    layout_hash: Optional[str] = None,
    position: Optional[Dict[str, float]] = None,
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """Convenience function to match patterns.
    
    Args:
        supplier_name: Supplier name
        database: LearningDatabase instance
        layout_hash: Optional layout hash
        position: Optional position dict
        similarity_threshold: Minimum similarity threshold
        
    Returns:
        List of matched patterns with similarity scores
    """
    matcher = PatternMatcher(database)
    return matcher.match_patterns(supplier_name, layout_hash, position, similarity_threshold)

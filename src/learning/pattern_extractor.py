"""Pattern extraction from corrections for learning system."""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..models.invoice_header import InvoiceHeader

logger = logging.getLogger(__name__)


class PatternExtractor:
    """Extracts patterns from corrections for learning system.
    
    Patterns include supplier, layout hash, position, and correct total amount.
    """
    
    @staticmethod
    def normalize_supplier(supplier_name: str) -> str:
        """Normalize supplier name.
        
        Args:
            supplier_name: Raw supplier name
            
        Returns:
            Normalized supplier name (lowercase, trimmed)
        """
        if not supplier_name:
            return "Unknown"
        return supplier_name.strip().lower()
    
    @staticmethod
    def calculate_layout_hash(supplier_name: str) -> str:
        """Calculate layout hash for pattern matching.
        
        Simplified implementation: hash of supplier + "footer"
        Future: Can be enhanced with actual footer structure analysis.
        
        Args:
            supplier_name: Supplier name
            
        Returns:
            Layout hash string
        """
        normalized = PatternExtractor.normalize_supplier(supplier_name)
        hash_input = f"{normalized}footer"
        return hashlib.md5(hash_input.encode('utf-8')).hexdigest()
    
    @classmethod
    def extract(
        cls,
        correction: Dict[str, Any],
        invoice_header: Optional[InvoiceHeader] = None
    ) -> Dict[str, Any]:
        """Extract single pattern from correction.
        
        Args:
            correction: Correction dict from JSON
            invoice_header: Optional InvoiceHeader for traceability data
            
        Returns:
            Pattern dict with supplier, layout_hash, position, correct_total, etc.
        """
        # Normalize supplier
        supplier_name = cls.normalize_supplier(
            correction.get('supplier_name', 'Unknown')
        )
        
        # Calculate layout hash
        layout_hash = cls.calculate_layout_hash(supplier_name)
        
        # Get position from traceability if available
        position_x = None
        position_y = None
        position_width = None
        position_height = None
        
        if invoice_header and invoice_header.total_traceability:
            bbox = invoice_header.total_traceability.evidence.get('bbox')
            if bbox and len(bbox) == 4:
                position_x = bbox[0]
                position_y = bbox[1]
                position_width = bbox[2]
                position_height = bbox[3]
        
        # Get correct total
        correct_total = correction.get('corrected_total')
        if correct_total is None:
            raise ValueError("correction must have corrected_total")
        
        # Create pattern
        pattern = {
            'supplier_name': supplier_name,
            'layout_hash': layout_hash,
            'position_x': position_x,
            'position_y': position_y,
            'position_width': position_width,
            'position_height': position_height,
            'correct_total': correct_total,
            'confidence_boost': 0.1,  # Default boost, can be calculated from accuracy later
            'usage_count': 1,
            'created_at': correction.get('timestamp', ''),
            'last_used': correction.get('timestamp', '')
        }
        
        return pattern


def extract_patterns_from_corrections(
    corrections: List[Dict[str, Any]],
    invoice_headers: Optional[List[InvoiceHeader]] = None
) -> List[Dict[str, Any]]:
    """Extract patterns from correction list.
    
    Args:
        corrections: List of correction dicts
        invoice_headers: Optional list of InvoiceHeader objects for traceability data
            (should match corrections by invoice_id if available)
        
    Returns:
        List of extracted pattern dicts
    """
    patterns = []
    extractor = PatternExtractor()
    
    # Create invoice_header lookup if provided
    header_lookup = {}
    if invoice_headers:
        # Would need invoice_id mapping - for now, use index if available
        # This is a limitation that can be enhanced later
        pass
    
    for correction in corrections:
        try:
            # Try to find matching invoice_header
            invoice_header = None
            # TODO: Match by invoice_id when we have better integration
            
            pattern = extractor.extract(correction, invoice_header)
            patterns.append(pattern)
            
        except Exception as e:
            logger.warning(f"Failed to extract pattern from correction {correction.get('invoice_id')}: {e}")
            continue
    
    logger.info(f"Extracted {len(patterns)} patterns from {len(corrections)} corrections")
    return patterns

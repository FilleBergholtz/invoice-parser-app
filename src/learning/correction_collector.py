"""Correction collection and storage for learning system."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..models.invoice_header import InvoiceHeader

logger = logging.getLogger(__name__)


class CorrectionCollector:
    """Manages correction storage for learning system.
    
    Stores user corrections in JSON format for Phase 7 learning system
    to consume and improve confidence scoring.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize correction collector.
        
        Args:
            storage_path: Path to corrections JSON file. Defaults to data/corrections.json
        """
        if storage_path is None:
            # Default to data/corrections.json in project root
            project_root = Path(__file__).parent.parent.parent
            storage_path = project_root / "data" / "corrections.json"
        
        self.storage_path = Path(storage_path)
        
        # Ensure data directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
    
    def save_correction(self, correction: Dict[str, Any]) -> None:
        """Save single correction to JSON file.
        
        Args:
            correction: Correction dict with all required fields
            
        Raises:
            ValueError: If correction data is invalid
            IOError: If file write fails
        """
        # Validate correction data
        required_fields = [
            'invoice_id', 'supplier_name', 'original_total',
            'original_confidence', 'corrected_total', 'corrected_confidence',
            'timestamp', 'correction_type'
        ]
        
        for field in required_fields:
            if field not in correction:
                raise ValueError(f"Missing required field: {field}")
        
        # Load existing corrections
        corrections = self.get_corrections()
        
        # Append new correction
        corrections.append(correction)
        
        # Save to file
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(corrections, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved correction for invoice {correction.get('invoice_id')}")
            
        except Exception as e:
            logger.error(f"Failed to save correction: {e}")
            raise IOError(f"Failed to save correction to {self.storage_path}: {e}") from e
    
    def get_corrections(self) -> List[Dict[str, Any]]:
        """Get all corrections from storage.
        
        Returns:
            List of correction dicts, empty list if file doesn't exist
        """
        if not self.storage_path.exists():
            return []
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                corrections = json.load(f)
            
            if not isinstance(corrections, list):
                logger.warning(f"Corrections file is not a list, resetting: {self.storage_path}")
                return []
            
            return corrections
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in corrections file: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to load corrections: {e}")
            return []
    
    def clear_corrections(self) -> None:
        """Clear all corrections from storage.
        
        Warning: This will delete all stored corrections!
        """
        if self.storage_path.exists():
            self.storage_path.unlink()
            logger.info("Cleared all corrections")


def save_correction(
    invoice_id: str,
    invoice_header: InvoiceHeader,
    selected_amount: float,
    selected_index: int,
    candidate_score: Optional[float] = None,
    raw_confidence: Optional[float] = None,
    storage_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Create and save correction for user-selected candidate.
    
    Args:
        invoice_id: Invoice identifier (filename or hash)
        invoice_header: InvoiceHeader object with original extraction data
        selected_amount: User-selected total amount
        selected_index: Index of selected candidate (0-based)
        candidate_score: Confidence score of selected candidate (from candidate dict)
        raw_confidence: Original raw confidence score (before calibration, if available)
        storage_path: Optional path to corrections file
        
    Returns:
        Correction dict that was saved
        
    Raises:
        ValueError: If correction data is invalid
        IOError: If save fails
    """
    # Get candidate score if not provided
    if candidate_score is None and invoice_header.total_candidates:
        if selected_index < len(invoice_header.total_candidates):
            candidate_score = invoice_header.total_candidates[selected_index].get('score', 0.0)
        else:
            candidate_score = 0.0
    
    # Create correction dict
    correction = {
        'invoice_id': invoice_id,
        'supplier_name': invoice_header.supplier_name or 'Unknown',
        'original_total': invoice_header.total_amount,
        'original_confidence': invoice_header.total_confidence,
        'corrected_total': selected_amount,
        'corrected_confidence': candidate_score or 0.0,
        'raw_confidence': raw_confidence,  # May be None if not available
        'candidate_index': selected_index,
        'timestamp': datetime.now().isoformat(),
        'correction_type': 'total_amount'  # For future extensibility
    }
    
    # Save using collector
    collector = CorrectionCollector(storage_path)
    collector.save_correction(correction)
    
    return correction

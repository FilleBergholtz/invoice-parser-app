"""Confidence score calibration using isotonic regression.

This module provides calibration of confidence scores to map raw scores
to calibrated scores that reflect actual accuracy. A confidence of 0.95
should mean 95% of predictions with that confidence are correct.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import joblib
from sklearn.isotonic import IsotonicRegression

logger = logging.getLogger(__name__)


class CalibrationModel:
    """Calibration model for confidence scores using isotonic regression.
    
    Isotonic regression ensures monotonic mapping: higher raw scores
    always map to higher calibrated scores.
    """
    
    def __init__(self, model: IsotonicRegression):
        """Initialize calibration model.
        
        Args:
            model: Trained isotonic regression model
        """
        self.model = model
    
    def calibrate(self, raw_score: float) -> float:
        """Apply calibration to raw confidence score.
        
        Args:
            raw_score: Raw confidence score (0.0-1.0)
            
        Returns:
            Calibrated confidence score (0.0-1.0)
        """
        # Ensure input is in valid range
        raw_score = max(0.0, min(1.0, raw_score))
        
        # Apply calibration (model expects 2D array)
        calibrated = self.model.predict([[raw_score]])[0]
        
        # Ensure output is in valid range (should be handled by out_of_bounds='clip')
        return max(0.0, min(1.0, calibrated))
    
    def save(self, path: str | Path) -> None:
        """Save calibration model to file.
        
        Args:
            path: Path to save model (will use .joblib extension if not provided)
        """
        path = Path(path)
        # Ensure .joblib extension
        if path.suffix not in ['.joblib', '.pkl']:
            path = path.with_suffix('.joblib')
        
        # Create parent directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save model using joblib
        joblib.dump(self.model, path)
        logger.info(f"Calibration model saved to {path}")
    
    @classmethod
    def load(cls, path: str | Path) -> Optional[CalibrationModel]:
        """Load calibration model from file.
        
        Args:
            path: Path to model file (.joblib or .pkl)
            
        Returns:
            CalibrationModel instance, or None if file not found or invalid
        """
        path = Path(path)
        
        # Try .joblib first, then .pkl
        if not path.exists():
            # Try alternative extension
            alt_path = path.with_suffix('.joblib' if path.suffix == '.pkl' else '.pkl')
            if alt_path.exists():
                path = alt_path
            else:
                logger.warning(f"Calibration model not found at {path} or {alt_path}")
                return None
        
        try:
            model = joblib.load(path)
            if not isinstance(model, IsotonicRegression):
                logger.error(f"Loaded model is not IsotonicRegression: {type(model)}")
                return None
            return cls(model)
        except Exception as e:
            logger.error(f"Failed to load calibration model from {path}: {e}")
            return None


def train_calibration_model(
    raw_scores: List[float],
    actual_correct: List[bool]
) -> CalibrationModel:
    """Train calibration model on (raw_score, actual_correct) pairs.
    
    Args:
        raw_scores: List of raw confidence scores (0.0-1.0)
        actual_correct: List of bools (True if prediction was correct, False otherwise)
        
    Returns:
        Trained CalibrationModel
        
    Raises:
        ValueError: If lists have different lengths or are empty
    """
    if len(raw_scores) != len(actual_correct):
        raise ValueError(
            f"raw_scores and actual_correct must have same length: "
            f"{len(raw_scores)} != {len(actual_correct)}"
        )
    
    if not raw_scores:
        raise ValueError("Cannot train calibration model on empty data")
    
    # Convert bools to floats (1.0 for True, 0.0 for False)
    y = [1.0 if correct else 0.0 for correct in actual_correct]
    
    # Ensure scores are in valid range
    X = [[max(0.0, min(1.0, score))] for score in raw_scores]
    
    # Train isotonic regression
    # out_of_bounds='clip' ensures predictions stay in [0, 1]
    model = IsotonicRegression(out_of_bounds='clip')
    model.fit(X, y)
    
    logger.info(f"Trained calibration model on {len(raw_scores)} samples")
    
    return CalibrationModel(model)


def calibrate_confidence(
    raw_score: float,
    model: Optional[CalibrationModel] = None
) -> float:
    """Apply calibration to raw confidence score.
    
    Args:
        raw_score: Raw confidence score (0.0-1.0)
        model: Optional CalibrationModel to use. If None, returns raw_score unchanged.
        
    Returns:
        Calibrated confidence score (0.0-1.0), or raw_score if model is None
    """
    if model is None:
        return raw_score
    
    return model.calibrate(raw_score)

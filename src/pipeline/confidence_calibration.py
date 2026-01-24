"""Confidence score calibration using isotonic regression.

This module provides calibration of confidence scores to map raw scores
to calibrated scores that reflect actual accuracy. A confidence of 0.95
should mean 95% of predictions with that confidence are correct.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def load_ground_truth_data(path: str | Path) -> Tuple[List[float], List[bool]]:
    """Load ground truth data from JSON or CSV file.
    
    Args:
        path: Path to ground truth file (JSON or CSV)
        
    Returns:
        Tuple of (raw_scores, actual_correct) lists
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid or missing required fields
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Ground truth file not found: {path}")
    
    raw_scores: List[float] = []
    actual_correct: List[bool] = []
    
    if path.suffix.lower() == '.json':
        # Load JSON format: [{"raw_confidence": 0.95, "actual_correct": true}, ...]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise ValueError(f"JSON file must contain a list, got {type(data)}")
        
        for item in data:
            if not isinstance(item, dict):
                raise ValueError(f"Each item must be a dict, got {type(item)}")
            
            if 'raw_confidence' not in item or 'actual_correct' not in item:
                raise ValueError(
                    "Each item must have 'raw_confidence' and 'actual_correct' fields"
                )
            
            raw_score = float(item['raw_confidence'])
            actual = bool(item['actual_correct'])
            
            # Validate score range
            if not 0.0 <= raw_score <= 1.0:
                raise ValueError(
                    f"raw_confidence must be between 0.0 and 1.0, got {raw_score}"
                )
            
            raw_scores.append(raw_score)
            actual_correct.append(actual)
    
    elif path.suffix.lower() == '.csv':
        # Load CSV format: raw_confidence,actual_correct (with header)
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check required columns
            if 'raw_confidence' not in reader.fieldnames or 'actual_correct' not in reader.fieldnames:
                raise ValueError(
                    "CSV must have 'raw_confidence' and 'actual_correct' columns"
                )
            
            for row in reader:
                try:
                    raw_score = float(row['raw_confidence'])
                    # Handle boolean strings: "true", "True", "1", etc.
                    actual_str = row['actual_correct'].lower().strip()
                    actual = actual_str in ['true', '1', 'yes', 'y']
                    
                    # Validate score range
                    if not 0.0 <= raw_score <= 1.0:
                        logger.warning(
                            f"Skipping invalid raw_confidence {raw_score} (must be 0.0-1.0)"
                        )
                        continue
                    
                    raw_scores.append(raw_score)
                    actual_correct.append(actual)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid row: {e}")
                    continue
    
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}. Use .json or .csv")
    
    if not raw_scores:
        raise ValueError(f"No valid data found in {path}")
    
    logger.info(f"Loaded {len(raw_scores)} ground truth samples from {path}")
    
    return raw_scores, actual_correct


def validate_calibration(
    model: Optional[CalibrationModel],
    raw_scores: List[float],
    actual_correct: List[bool]
) -> Dict[str, Any]:
    """Validate calibration model against ground truth data.
    
    Args:
        model: Optional CalibrationModel to validate. If None, validates raw scores.
        raw_scores: List of raw confidence scores
        actual_correct: List of bools indicating if prediction was correct
        
    Returns:
        Validation report dict with:
        - overall_accuracy: float
        - per_bin_drift: Dict[str, float] (bins: "0.0-0.1", "0.1-0.2", etc.)
        - max_drift: float
        - suggest_recalibration: bool (True if max_drift > 0.05)
    """
    if len(raw_scores) != len(actual_correct):
        raise ValueError(
            f"raw_scores and actual_correct must have same length: "
            f"{len(raw_scores)} != {len(actual_correct)}"
        )
    
    # Apply calibration if model exists
    calibrated_scores = [
        calibrate_confidence(score, model) for score in raw_scores
    ]
    
    # Calculate overall accuracy
    overall_accuracy = sum(actual_correct) / len(actual_correct) if actual_correct else 0.0
    
    # Group by confidence bins (0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
    bins: Dict[str, Dict[str, List[float]]] = {}
    for i in range(10):
        bin_key = f"{i*0.1:.1f}-{(i+1)*0.1:.1f}"
        bins[bin_key] = {'scores': [], 'correct': []}
    
    # Also handle 1.0 separately (edge case)
    bins['1.0'] = {'scores': [], 'correct': []}
    
    for calibrated, correct in zip(calibrated_scores, actual_correct):
        # Find bin
        bin_idx = int(calibrated * 10)
        if bin_idx >= 10:
            bin_key = '1.0'
        else:
            bin_key = f"{bin_idx*0.1:.1f}-{(bin_idx+1)*0.1:.1f}"
        
        bins[bin_key]['scores'].append(calibrated)
        bins[bin_key]['correct'].append(1.0 if correct else 0.0)
    
    # Calculate per-bin drift
    per_bin_drift: Dict[str, float] = {}
    max_drift = 0.0
    
    for bin_key, bin_data in bins.items():
        if not bin_data['scores']:
            per_bin_drift[bin_key] = 0.0
            continue
        
        predicted_accuracy = sum(bin_data['scores']) / len(bin_data['scores'])
        actual_accuracy = sum(bin_data['correct']) / len(bin_data['correct'])
        drift = abs(predicted_accuracy - actual_accuracy)
        
        per_bin_drift[bin_key] = drift
        max_drift = max(max_drift, drift)
    
    suggest_recalibration = max_drift > 0.05
    
    return {
        'overall_accuracy': overall_accuracy,
        'per_bin_drift': per_bin_drift,
        'max_drift': max_drift,
        'suggest_recalibration': suggest_recalibration,
        'total_samples': len(raw_scores),
        'bins_with_data': sum(1 for v in bins.values() if v['scores'])
    }


def format_validation_report(report: Dict[str, Any]) -> str:
    """Format validation report as human-readable string.
    
    Args:
        report: Validation report dict from validate_calibration()
        
    Returns:
        Formatted report string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("Confidence Calibration Validation Report")
    lines.append("=" * 60)
    lines.append("")
    
    lines.append(f"Total samples: {report['total_samples']}")
    lines.append(f"Overall accuracy: {report['overall_accuracy']:.2%}")
    lines.append(f"Max drift: {report['max_drift']:.2%}")
    lines.append(f"Bins with data: {report['bins_with_data']}/11")
    lines.append("")
    
    lines.append("Per-bin drift (predicted vs actual accuracy):")
    lines.append("-" * 60)
    
    # Sort bins by key
    sorted_bins = sorted(report['per_bin_drift'].items())
    
    for bin_key, drift in sorted_bins:
        if drift > 0.0:  # Only show bins with data
            lines.append(f"  {bin_key:>8}: {drift:>6.2%} drift")
    
    lines.append("")
    
    if report['suggest_recalibration']:
        lines.append("⚠️  WARNING: Max drift > 5% - Recalibration recommended")
        lines.append("   Run with --train flag to train new calibration model")
    else:
        lines.append("✓ Calibration is well-calibrated (max drift ≤ 5%)")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)

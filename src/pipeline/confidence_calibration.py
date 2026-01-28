"""Confidence score calibration using isotonic regression.

This module provides calibration of confidence scores to map raw scores
to calibrated scores that reflect actual accuracy. A confidence of 0.95
should mean 95% of predictions with that confidence are correct.

Key features:
- Robust isotonic regression with 1D input (sklearn-compliant)
- Segmented calibration (field/supplier) with fallback chain
- Min-samples guard to prevent overfitting
- Proper validation metrics (ECE, MCE, Brier score)
- Equal-frequency binning for stable drift metrics
"""

from __future__ import annotations

import csv
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
from sklearn.isotonic import IsotonicRegression

logger = logging.getLogger(__name__)


# ----------------------------
# Constants
# ----------------------------

MIN_SAMPLES_FOR_CALIBRATION = 50  # Minimum samples to train a calibration model
MIN_SAMPLES_PER_FIELD = 30  # Minimum samples for field-specific calibration


# ----------------------------
# Calibration Model
# ----------------------------

@dataclass
class CalibrationMetadata:
    """Metadata for a calibration model."""
    field_type: str  # "invoice_no", "total", "date", "*" (global)
    supplier_fingerprint: str  # supplier ID or "*" (global)
    n_samples: int
    brier_score: float
    ece: float


class CalibrationModel:
    """Calibration model for confidence scores using isotonic regression.
    
    Isotonic regression ensures monotonic mapping: higher raw scores
    always map to higher calibrated scores.
    
    IMPORTANT: Uses 1D arrays for sklearn compatibility.
    """
    
    def __init__(
        self,
        model: IsotonicRegression,
        metadata: Optional[CalibrationMetadata] = None
    ):
        """Initialize calibration model.
        
        Args:
            model: Trained isotonic regression model
            metadata: Optional metadata about training
        """
        self.model = model
        self.metadata = metadata
    
    def calibrate(self, raw_score: float) -> float:
        """Apply calibration to raw confidence score.
        
        Args:
            raw_score: Raw confidence score (0.0-1.0)
            
        Returns:
            Calibrated confidence score (0.0-1.0)
        """
        # Ensure input is in valid range
        raw_score = max(0.0, min(1.0, float(raw_score)))
        
        # Apply calibration - sklearn isotonic expects 1D array
        # predict() with a scalar or 1D array works correctly
        calibrated = self.model.predict([raw_score])[0]
        
        # Ensure output is in valid range
        return float(max(0.0, min(1.0, calibrated)))
    
    def save(self, path: str | Path) -> None:
        """Save calibration model to file."""
        path = Path(path)
        if path.suffix not in ['.joblib', '.pkl']:
            path = path.with_suffix('.joblib')
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save both model and metadata
        data = {
            'model': self.model,
            'metadata': self.metadata
        }
        joblib.dump(data, path)
        logger.info(f"Calibration model saved to {path}")
    
    @classmethod
    def load(cls, path: str | Path) -> Optional[CalibrationModel]:
        """Load calibration model from file."""
        path = Path(path)
        
        if not path.exists():
            alt_path = path.with_suffix('.joblib' if path.suffix == '.pkl' else '.pkl')
            if alt_path.exists():
                path = alt_path
            else:
                logger.warning(f"Calibration model not found at {path}")
                return None
        
        try:
            data = joblib.load(path)
            
            # Handle both old format (just model) and new format (dict with metadata)
            if isinstance(data, IsotonicRegression):
                return cls(data, None)
            elif isinstance(data, dict) and 'model' in data:
                model = data['model']
                metadata = data.get('metadata')
                if not isinstance(model, IsotonicRegression):
                    logger.error(f"Loaded model is not IsotonicRegression: {type(model)}")
                    return None
                return cls(model, metadata)
            else:
                logger.error(f"Invalid calibration model format")
                return None
        except Exception as e:
            logger.error(f"Failed to load calibration model from {path}: {e}")
            return None


# ----------------------------
# Calibration Registry (Segmented)
# ----------------------------

class CalibrationRegistry:
    """Registry for segmented calibration models with fallback chain.
    
    Calibration lookup order:
    1. (supplier_fingerprint, field_type) - most specific
    2. (supplier_fingerprint, "*") - supplier global
    3. ("*", field_type) - field global
    4. ("*", "*") - global fallback
    """
    
    def __init__(self):
        self.models: Dict[Tuple[str, str], CalibrationModel] = {}
    
    def register(
        self,
        model: CalibrationModel,
        field_type: str = "*",
        supplier_fingerprint: str = "*"
    ) -> None:
        """Register a calibration model for a specific segment."""
        key = (supplier_fingerprint, field_type)
        self.models[key] = model
        logger.debug(f"Registered calibration model for {key}")
    
    def get(
        self,
        field_type: str = "*",
        supplier_fingerprint: str = "*"
    ) -> Optional[CalibrationModel]:
        """Get calibration model using fallback chain."""
        # Try in order of specificity
        keys_to_try = [
            (supplier_fingerprint, field_type),  # Most specific
            (supplier_fingerprint, "*"),         # Supplier global
            ("*", field_type),                   # Field global
            ("*", "*"),                          # Global fallback
        ]
        
        for key in keys_to_try:
            if key in self.models:
                logger.debug(f"Using calibration model: {key}")
                return self.models[key]
        
        return None
    
    def calibrate(
        self,
        raw_score: float,
        field_type: str = "*",
        supplier_fingerprint: str = "*"
    ) -> float:
        """Calibrate score using best available model."""
        model = self.get(field_type, supplier_fingerprint)
        if model is None:
            return raw_score
        return model.calibrate(raw_score)
    
    def save(self, directory: str | Path) -> None:
        """Save all models to a directory."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        
        manifest = {}
        for (supplier, field), model in self.models.items():
            filename = f"calibration_{supplier}_{field}.joblib"
            model.save(directory / filename)
            manifest[f"{supplier}:{field}"] = filename
        
        # Save manifest
        with open(directory / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
    
    @classmethod
    def load(cls, directory: str | Path) -> CalibrationRegistry:
        """Load registry from directory."""
        directory = Path(directory)
        registry = cls()
        
        manifest_path = directory / "manifest.json"
        if not manifest_path.exists():
            logger.warning(f"No calibration manifest found at {directory}")
            return registry
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        for key_str, filename in manifest.items():
            supplier, field = key_str.split(":", 1)
            model = CalibrationModel.load(directory / filename)
            if model:
                registry.register(model, field, supplier)
        
        return registry


# ----------------------------
# Training Functions
# ----------------------------

def _aggregate_by_score(
    raw_scores: List[float],
    correct: List[float]
) -> Tuple[List[float], List[float]]:
    """Aggregate samples by raw score (reduce noise for isotonic).
    
    Groups identical raw scores and takes mean of correctness.
    This stabilizes isotonic regression.
    """
    score_groups: Dict[float, List[float]] = defaultdict(list)
    
    for score, c in zip(raw_scores, correct):
        # Round to avoid floating point noise
        rounded = round(score, 4)
        score_groups[rounded].append(c)
    
    agg_scores = []
    agg_correct = []
    
    for score in sorted(score_groups.keys()):
        agg_scores.append(score)
        agg_correct.append(sum(score_groups[score]) / len(score_groups[score]))
    
    return agg_scores, agg_correct


def train_calibration_model(
    raw_scores: List[float],
    actual_correct: List[bool],
    field_type: str = "*",
    supplier_fingerprint: str = "*",
    min_samples: int = MIN_SAMPLES_FOR_CALIBRATION
) -> Optional[CalibrationModel]:
    """Train calibration model on (raw_score, actual_correct) pairs.
    
    FIXES:
    - Uses 1D arrays (sklearn-compliant)
    - Aggregates duplicate scores for stability
    - Enforces minimum samples
    - Calculates quality metrics
    
    Args:
        raw_scores: List of raw confidence scores (0.0-1.0)
        actual_correct: List of bools (True if prediction was correct)
        field_type: Field type for metadata
        supplier_fingerprint: Supplier ID for metadata
        min_samples: Minimum samples required
        
    Returns:
        Trained CalibrationModel, or None if insufficient data
    """
    if len(raw_scores) != len(actual_correct):
        raise ValueError(
            f"raw_scores and actual_correct must have same length: "
            f"{len(raw_scores)} != {len(actual_correct)}"
        )
    
    if len(raw_scores) < min_samples:
        logger.warning(
            f"Insufficient samples for calibration ({len(raw_scores)} < {min_samples}). "
            f"Returning None (use identity or global fallback)."
        )
        return None
    
    # Convert bools to floats
    y = [1.0 if correct else 0.0 for correct in actual_correct]
    
    # Clip scores to valid range
    X = [max(0.0, min(1.0, float(score))) for score in raw_scores]
    
    # Aggregate by score for stability
    X_agg, y_agg = _aggregate_by_score(X, y)
    
    if len(X_agg) < 5:
        logger.warning(f"Too few unique scores ({len(X_agg)}) for isotonic regression")
        return None
    
    # Train isotonic regression with 1D arrays
    model = IsotonicRegression(out_of_bounds='clip', increasing=True)
    model.fit(X_agg, y_agg)
    
    # Calculate quality metrics
    y_pred = model.predict(X)
    brier = sum((p - c) ** 2 for p, c in zip(y_pred, y)) / len(y)
    ece = _calculate_ece(X, y_pred, y)
    
    metadata = CalibrationMetadata(
        field_type=field_type,
        supplier_fingerprint=supplier_fingerprint,
        n_samples=len(raw_scores),
        brier_score=brier,
        ece=ece
    )
    
    logger.info(
        f"Trained calibration model: {field_type}/{supplier_fingerprint}, "
        f"n={len(raw_scores)}, Brier={brier:.4f}, ECE={ece:.4f}"
    )
    
    return CalibrationModel(model, metadata)


def train_segmented_calibration(
    data: List[Dict[str, Any]],
    min_samples_per_segment: int = MIN_SAMPLES_PER_FIELD
) -> CalibrationRegistry:
    """Train segmented calibration models from labeled data.
    
    Args:
        data: List of dicts with keys:
            - raw_confidence: float
            - actual_correct: bool
            - field_type: str (optional, default "*")
            - supplier_fingerprint: str (optional, default "*")
        min_samples_per_segment: Minimum samples per segment
        
    Returns:
        CalibrationRegistry with trained models
    """
    registry = CalibrationRegistry()
    
    # Group data by segment
    segments: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    
    for item in data:
        supplier = item.get('supplier_fingerprint', '*')
        field = item.get('field_type', '*')
        segments[(supplier, field)].append(item)
    
    # Also collect for global aggregations
    all_data = []
    per_field: Dict[str, List[Dict]] = defaultdict(list)
    per_supplier: Dict[str, List[Dict]] = defaultdict(list)
    
    for (supplier, field), items in segments.items():
        all_data.extend(items)
        per_field[field].extend(items)
        per_supplier[supplier].extend(items)
    
    # Train segment-specific models
    for (supplier, field), items in segments.items():
        if len(items) >= min_samples_per_segment:
            model = train_calibration_model(
                [x['raw_confidence'] for x in items],
                [x['actual_correct'] for x in items],
                field_type=field,
                supplier_fingerprint=supplier
            )
            if model:
                registry.register(model, field, supplier)
    
    # Train field-global models
    for field, items in per_field.items():
        if field == "*":
            continue
        key = ("*", field)
        if key not in registry.models and len(items) >= min_samples_per_segment:
            model = train_calibration_model(
                [x['raw_confidence'] for x in items],
                [x['actual_correct'] for x in items],
                field_type=field,
                supplier_fingerprint="*"
            )
            if model:
                registry.register(model, field, "*")
    
    # Train global fallback
    if ("*", "*") not in registry.models and len(all_data) >= MIN_SAMPLES_FOR_CALIBRATION:
        model = train_calibration_model(
            [x['raw_confidence'] for x in all_data],
            [x['actual_correct'] for x in all_data],
            field_type="*",
            supplier_fingerprint="*"
        )
        if model:
            registry.register(model, "*", "*")
    
    return registry


# ----------------------------
# Validation Metrics
# ----------------------------

def _calculate_ece(
    raw_scores: List[float],
    calibrated_scores: List[float],
    correct: List[float],
    n_bins: int = 10
) -> float:
    """Calculate Expected Calibration Error (ECE).
    
    ECE = sum(|bin_accuracy - bin_confidence| * bin_count / total)
    
    Uses equal-width bins on RAW scores (not calibrated) for proper evaluation.
    """
    if not raw_scores:
        return 0.0
    
    # Bin by RAW score (not calibrated - this is the fix)
    bins = [[] for _ in range(n_bins)]
    
    for raw, cal, c in zip(raw_scores, calibrated_scores, correct):
        bin_idx = min(int(raw * n_bins), n_bins - 1)
        bins[bin_idx].append((cal, c))
    
    total = len(raw_scores)
    ece = 0.0
    
    for bin_data in bins:
        if not bin_data:
            continue
        
        bin_conf = sum(cal for cal, _ in bin_data) / len(bin_data)
        bin_acc = sum(c for _, c in bin_data) / len(bin_data)
        ece += abs(bin_conf - bin_acc) * len(bin_data) / total
    
    return ece


def _calculate_mce(
    raw_scores: List[float],
    calibrated_scores: List[float],
    correct: List[float],
    n_bins: int = 10
) -> float:
    """Calculate Maximum Calibration Error (MCE).
    
    MCE = max(|bin_accuracy - bin_confidence|) across all bins
    """
    if not raw_scores:
        return 0.0
    
    # Bin by RAW score
    bins = [[] for _ in range(n_bins)]
    
    for raw, cal, c in zip(raw_scores, calibrated_scores, correct):
        bin_idx = min(int(raw * n_bins), n_bins - 1)
        bins[bin_idx].append((cal, c))
    
    mce = 0.0
    
    for bin_data in bins:
        if not bin_data:
            continue
        
        bin_conf = sum(cal for cal, _ in bin_data) / len(bin_data)
        bin_acc = sum(c for _, c in bin_data) / len(bin_data)
        mce = max(mce, abs(bin_conf - bin_acc))
    
    return mce


def _calculate_brier(
    calibrated_scores: List[float],
    correct: List[float]
) -> float:
    """Calculate Brier score (mean squared error).
    
    Brier = mean((predicted - actual)^2)
    Lower is better. Range [0, 1].
    """
    if not calibrated_scores:
        return 0.0
    
    return sum((p - c) ** 2 for p, c in zip(calibrated_scores, correct)) / len(calibrated_scores)


def validate_calibration(
    model: Optional[CalibrationModel],
    raw_scores: List[float],
    actual_correct: List[bool],
    n_bins: int = 10
) -> Dict[str, Any]:
    """Validate calibration model against ground truth data.
    
    FIXES:
    - Bins by RAW score, not calibrated score
    - Includes ECE, MCE, Brier metrics
    - Reports both raw-binned and calibrated metrics
    
    Args:
        model: Optional CalibrationModel to validate. If None, validates raw scores.
        raw_scores: List of raw confidence scores
        actual_correct: List of bools indicating if prediction was correct
        n_bins: Number of bins for drift calculation
        
    Returns:
        Comprehensive validation report
    """
    if len(raw_scores) != len(actual_correct):
        raise ValueError("raw_scores and actual_correct must have same length")
    
    # Convert to floats
    correct = [1.0 if c else 0.0 for c in actual_correct]
    raw = [max(0.0, min(1.0, float(s))) for s in raw_scores]
    
    # Apply calibration
    if model:
        calibrated = [model.calibrate(s) for s in raw]
    else:
        calibrated = raw.copy()
    
    # Overall metrics
    overall_accuracy = sum(correct) / len(correct) if correct else 0.0
    
    # Calibration metrics
    ece = _calculate_ece(raw, calibrated, correct, n_bins)
    mce = _calculate_mce(raw, calibrated, correct, n_bins)
    brier = _calculate_brier(calibrated, correct)
    
    # Per-bin drift (binned by RAW score - this is the fix)
    bins_raw: Dict[str, Dict[str, List[float]]] = {}
    for i in range(n_bins):
        lo = i / n_bins
        hi = (i + 1) / n_bins
        bin_key = f"{lo:.1f}-{hi:.1f}"
        bins_raw[bin_key] = {'raw': [], 'calibrated': [], 'correct': []}
    
    for r, c, corr in zip(raw, calibrated, correct):
        bin_idx = min(int(r * n_bins), n_bins - 1)
        lo = bin_idx / n_bins
        hi = (bin_idx + 1) / n_bins
        bin_key = f"{lo:.1f}-{hi:.1f}"
        bins_raw[bin_key]['raw'].append(r)
        bins_raw[bin_key]['calibrated'].append(c)
        bins_raw[bin_key]['correct'].append(corr)
    
    per_bin_drift: Dict[str, Dict[str, float]] = {}
    max_drift = 0.0
    
    for bin_key, bin_data in bins_raw.items():
        if not bin_data['calibrated']:
            per_bin_drift[bin_key] = {
                'n': 0,
                'mean_raw': 0.0,
                'mean_calibrated': 0.0,
                'accuracy': 0.0,
                'drift': 0.0
            }
            continue
        
        n = len(bin_data['calibrated'])
        mean_raw = sum(bin_data['raw']) / n
        mean_cal = sum(bin_data['calibrated']) / n
        accuracy = sum(bin_data['correct']) / n
        drift = abs(mean_cal - accuracy)
        
        per_bin_drift[bin_key] = {
            'n': n,
            'mean_raw': mean_raw,
            'mean_calibrated': mean_cal,
            'accuracy': accuracy,
            'drift': drift
        }
        max_drift = max(max_drift, drift)
    
    # Recalibration threshold
    suggest_recalibration = ece > 0.05 or mce > 0.10
    
    return {
        'overall_accuracy': overall_accuracy,
        'ece': ece,
        'mce': mce,
        'brier_score': brier,
        'max_drift': max_drift,
        'per_bin_drift': per_bin_drift,
        'suggest_recalibration': suggest_recalibration,
        'total_samples': len(raw_scores),
        'bins_with_data': sum(1 for v in per_bin_drift.values() if v['n'] > 0),
        'model_metadata': model.metadata if model and model.metadata else None
    }


# ----------------------------
# Helper Functions
# ----------------------------

def calibrate_confidence(
    raw_score: float,
    model: Optional[CalibrationModel] = None
) -> float:
    """Apply calibration to raw confidence score.
    
    Args:
        raw_score: Raw confidence score (0.0-1.0)
        model: Optional CalibrationModel to use. If None, returns raw_score unchanged.
        
    Returns:
        Calibrated confidence score (0.0-1.0)
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
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Ground truth file not found: {path}")
    
    raw_scores: List[float] = []
    actual_correct: List[bool] = []
    
    if path.suffix.lower() == '.json':
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
            
            if not 0.0 <= raw_score <= 1.0:
                raise ValueError(
                    f"raw_confidence must be between 0.0 and 1.0, got {raw_score}"
                )
            
            raw_scores.append(raw_score)
            actual_correct.append(actual)
    
    elif path.suffix.lower() == '.csv':
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            fieldnames = reader.fieldnames or ()
            if 'raw_confidence' not in fieldnames or 'actual_correct' not in fieldnames:
                raise ValueError(
                    "CSV must have 'raw_confidence' and 'actual_correct' columns"
                )
            
            for row in reader:
                try:
                    raw_score = float(row['raw_confidence'])
                    actual_str = row['actual_correct'].lower().strip()
                    actual = actual_str in ['true', '1', 'yes', 'y']
                    
                    if not 0.0 <= raw_score <= 1.0:
                        logger.warning(f"Skipping invalid raw_confidence {raw_score}")
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


def format_validation_report(report: Dict[str, Any]) -> str:
    """Format validation report as human-readable string."""
    lines = []
    lines.append("=" * 65)
    lines.append("Confidence Calibration Validation Report")
    lines.append("=" * 65)
    lines.append("")
    
    lines.append(f"Total samples: {report['total_samples']}")
    lines.append(f"Overall accuracy: {report['overall_accuracy']:.2%}")
    lines.append("")
    
    lines.append("Calibration Metrics:")
    lines.append(f"  ECE (Expected Calibration Error): {report['ece']:.4f}")
    lines.append(f"  MCE (Maximum Calibration Error):  {report['mce']:.4f}")
    lines.append(f"  Brier Score:                      {report['brier_score']:.4f}")
    lines.append(f"  Max Bin Drift:                    {report['max_drift']:.2%}")
    lines.append(f"  Bins with data:                   {report['bins_with_data']}/10")
    lines.append("")
    
    if report.get('model_metadata'):
        meta = report['model_metadata']
        lines.append("Model Metadata:")
        lines.append(f"  Field type:      {meta.field_type}")
        lines.append(f"  Supplier:        {meta.supplier_fingerprint}")
        lines.append(f"  Training samples: {meta.n_samples}")
        lines.append("")
    
    lines.append("Per-bin Analysis (binned by raw score):")
    lines.append("-" * 65)
    lines.append(f"{'Bin':<12} {'N':>6} {'Raw':>8} {'Cal':>8} {'Acc':>8} {'Drift':>8}")
    lines.append("-" * 65)
    
    for bin_key, data in sorted(report['per_bin_drift'].items()):
        if data['n'] > 0:
            lines.append(
                f"{bin_key:<12} {data['n']:>6} "
                f"{data['mean_raw']:>7.2%} {data['mean_calibrated']:>7.2%} "
                f"{data['accuracy']:>7.2%} {data['drift']:>7.2%}"
            )
    
    lines.append("")
    
    if report['suggest_recalibration']:
        lines.append("⚠️  WARNING: Calibration drift detected (ECE > 5% or MCE > 10%)")
        lines.append("   Run with --train flag to retrain calibration model")
    else:
        lines.append("✓ Calibration is well-calibrated")
    
    lines.append("")
    lines.append("=" * 65)
    
    return "\n".join(lines)

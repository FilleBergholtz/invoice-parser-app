"""Confidence score calibration using isotonic regression.

This module provides calibration of confidence scores to map raw scores
to calibrated scores that reflect actual accuracy. A confidence of 0.95
should mean 95% of predictions with that confidence are correct.

Key features:
- Robust isotonic regression with 1D input (sklearn-compliant)
- Sample weights for aggregated training (avoids "steppy" curves)
- Segmented calibration (field/supplier) with full fallback chain
- Segment-adaptive min-samples thresholds
- Equal-frequency (quantile) binning for stable ECE/MCE
- Volume-aware recalibration thresholds
"""

from __future__ import annotations

import csv
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.isotonic import IsotonicRegression

logger = logging.getLogger(__name__)


# ----------------------------
# Constants (CAL-05: Segment-adaptive min-samples)
# ----------------------------

# Most specific: (supplier, field) - needs most data
MIN_SAMPLES_SUPPLIER_FIELD = 200

# Supplier aggregate: (supplier, "*")
MIN_SAMPLES_SUPPLIER_GLOBAL = 150

# Field aggregate: ("*", field)
MIN_SAMPLES_FIELD_GLOBAL = 100

# Least specific: ("*", "*") - global fallback
MIN_SAMPLES_GLOBAL = 50

# Minimum unique scores for isotonic regression
MIN_UNIQUE_SCORES = 8


# ----------------------------
# Utility Functions
# ----------------------------

def _safe_key(s: str, max_length: int = 120) -> str:
    """Sanitize string for use in filename (CAL-04).
    
    Prevents path traversal and invalid characters.
    """
    if not s:
        return "unknown"
    # Replace anything not alphanumeric, dot, underscore, or hyphen
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    # Collapse multiple underscores
    safe = re.sub(r"_+", "_", safe)
    # Strip leading/trailing underscores
    safe = safe.strip("_")
    # Enforce max length
    return safe[:max_length] if safe else "unknown"


def min_samples_for_segment(supplier: str, field: str) -> int:
    """Get appropriate min-samples threshold for segment specificity (CAL-05).
    
    More specific segments need more samples for reliable calibration.
    """
    if supplier != "*" and field != "*":
        return MIN_SAMPLES_SUPPLIER_FIELD
    elif supplier != "*":
        return MIN_SAMPLES_SUPPLIER_GLOBAL
    elif field != "*":
        return MIN_SAMPLES_FIELD_GLOBAL
    else:
        return MIN_SAMPLES_GLOBAL


def _quantile_bin_edges(values: List[float], n_bins: int) -> np.ndarray:
    """Compute bin edges using quantiles for equal-frequency binning (CAL-01).
    
    Each bin will contain approximately equal number of samples,
    which stabilizes ECE/MCE for skewed probability distributions.
    
    Args:
        values: List of values to compute quantiles from (usually raw scores)
        n_bins: Number of bins (edges = n_bins + 1)
        
    Returns:
        Array of bin edges [0.0, ..., 1.0] with n_bins + 1 elements
    """
    if len(values) < n_bins:
        # Not enough samples for requested bins
        return np.array([0.0, 1.0])
    
    # Use numpy.quantile with linear interpolation
    quantiles = np.linspace(0, 1, n_bins + 1)
    edges = np.quantile(values, quantiles)
    
    # Ensure strictly increasing (handle ties)
    for i in range(1, len(edges)):
        if edges[i] <= edges[i-1]:
            edges[i] = edges[i-1] + 1e-9
    
    # Clamp to [0, 1] for probability values
    edges[0] = 0.0
    edges[-1] = 1.0
    
    return edges


def _get_bin_index(value: float, edges: np.ndarray) -> int:
    """Get bin index for a value given edges (CAL-01).
    
    Uses binary search for efficiency.
    """
    # np.searchsorted finds insertion point; -1 for bin index
    # clip to valid range
    idx = int(np.searchsorted(edges, value, side='right')) - 1
    return max(0, min(idx, len(edges) - 2))


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
        """Save all models to a directory (CAL-04: safe filenames)."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        
        manifest = {}
        for (supplier, field), model in self.models.items():
            # CAL-04: Sanitize keys for safe filenames
            safe_supplier = _safe_key(supplier)
            safe_field = _safe_key(field)
            filename = f"calibration_{safe_supplier}_{safe_field}.joblib"
            model.save(directory / filename)
            # Store original keys as JSON array to preserve exact values
            manifest_key = json.dumps([supplier, field])
            manifest[manifest_key] = filename
        
        # Save manifest
        with open(directory / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Saved {len(self.models)} calibration models to {directory}")
    
    @classmethod
    def load(cls, directory: str | Path) -> CalibrationRegistry:
        """Load registry from directory (handles both old and new manifest formats)."""
        directory = Path(directory)
        registry = cls()
        
        manifest_path = directory / "manifest.json"
        if not manifest_path.exists():
            logger.warning(f"No calibration manifest found at {directory}")
            return registry
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        for key_str, filename in manifest.items():
            # Handle both old format ("supplier:field") and new format (JSON array)
            if key_str.startswith('['):
                # New format: JSON array
                try:
                    supplier, field = json.loads(key_str)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid manifest key: {key_str}")
                    continue
            else:
                # Old format: "supplier:field"
                supplier, field = key_str.split(":", 1)
            
            model = CalibrationModel.load(directory / filename)
            if model:
                registry.register(model, field, supplier)
        
        logger.info(f"Loaded {len(registry.models)} calibration models from {directory}")
        return registry


# ----------------------------
# Training Functions
# ----------------------------

def _aggregate_by_score_with_weights(
    raw_scores: List[float],
    correct: List[float]
) -> Tuple[List[float], List[float], List[float]]:
    """Aggregate samples by raw score, returning weights (CAL-02).
    
    Groups identical raw scores and takes mean of correctness.
    Returns counts as sample weights for isotonic regression.
    
    This is critical for avoiding "steppy" calibration curves:
    without weights, isotonic treats one aggregated point at 0.85
    the same as one at 0.90, even if 0.85 represents 100 samples
    and 0.90 represents 5.
    
    Returns:
        Tuple of (aggregated_scores, mean_correctness, counts_as_weights)
    """
    score_groups: Dict[float, List[float]] = defaultdict(list)
    
    for score, c in zip(raw_scores, correct):
        # Round to avoid floating point noise
        rounded = round(score, 4)
        score_groups[rounded].append(c)
    
    agg_scores = []
    agg_correct = []
    agg_weights = []
    
    for score in sorted(score_groups.keys()):
        vals = score_groups[score]
        agg_scores.append(score)
        agg_correct.append(sum(vals) / len(vals))
        agg_weights.append(float(len(vals)))  # Count as weight
    
    return agg_scores, agg_correct, agg_weights


def train_calibration_model(
    raw_scores: List[float],
    actual_correct: List[bool],
    field_type: str = "*",
    supplier_fingerprint: str = "*",
    min_samples: Optional[int] = None
) -> Optional[CalibrationModel]:
    """Train calibration model on (raw_score, actual_correct) pairs.
    
    Features:
    - Uses 1D arrays (sklearn-compliant)
    - Aggregates duplicate scores with sample weights (CAL-02)
    - Segment-adaptive min-samples thresholds (CAL-05)
    - Calculates quality metrics
    
    Args:
        raw_scores: List of raw confidence scores (0.0-1.0)
        actual_correct: List of bools (True if prediction was correct)
        field_type: Field type for metadata
        supplier_fingerprint: Supplier ID for metadata
        min_samples: Minimum samples required (auto-calculated if None)
        
    Returns:
        Trained CalibrationModel, or None if insufficient data
    """
    if len(raw_scores) != len(actual_correct):
        raise ValueError(
            f"raw_scores and actual_correct must have same length: "
            f"{len(raw_scores)} != {len(actual_correct)}"
        )
    
    # CAL-05: Use segment-adaptive threshold if not specified
    if min_samples is None:
        min_samples = min_samples_for_segment(supplier_fingerprint, field_type)
    
    if len(raw_scores) < min_samples:
        logger.debug(
            f"Insufficient samples for calibration ({len(raw_scores)} < {min_samples}) "
            f"for {supplier_fingerprint}/{field_type}. Returning None."
        )
        return None
    
    # Convert bools to floats
    y = [1.0 if correct else 0.0 for correct in actual_correct]
    
    # Clip scores to valid range
    X = [max(0.0, min(1.0, float(score))) for score in raw_scores]
    
    # CAL-02: Aggregate by score with weights
    X_agg, y_agg, w_agg = _aggregate_by_score_with_weights(X, y)
    
    if len(X_agg) < MIN_UNIQUE_SCORES:
        logger.debug(
            f"Too few unique scores ({len(X_agg)}) for isotonic regression "
            f"for {supplier_fingerprint}/{field_type}"
        )
        return None
    
    # CAL-02: Train isotonic regression with sample weights
    model = IsotonicRegression(out_of_bounds='clip', increasing=True)
    model.fit(X_agg, y_agg, sample_weight=w_agg)
    
    # Calculate quality metrics using quantile bins
    y_pred = model.predict(X)
    brier = sum((p - c) ** 2 for p, c in zip(y_pred, y)) / len(y)
    ece = _calculate_ece(X, list(y_pred), y)
    
    metadata = CalibrationMetadata(
        field_type=field_type,
        supplier_fingerprint=supplier_fingerprint,
        n_samples=len(raw_scores),
        brier_score=brier,
        ece=ece
    )
    
    logger.info(
        f"Trained calibration model: {field_type}/{supplier_fingerprint}, "
        f"n={len(raw_scores)}, unique={len(X_agg)}, Brier={brier:.4f}, ECE={ece:.4f}"
    )
    
    return CalibrationModel(model, metadata)


def train_segmented_calibration(
    data: List[Dict[str, Any]]
) -> CalibrationRegistry:
    """Train segmented calibration models from labeled data (CAL-03, CAL-05).
    
    Creates models at all levels of the fallback chain:
    1. (supplier, field) - most specific
    2. (supplier, "*") - supplier global (CAL-03: this was missing!)
    3. ("*", field) - field global
    4. ("*", "*") - global fallback
    
    Uses segment-adaptive min-samples thresholds (CAL-05).
    
    Args:
        data: List of dicts with keys:
            - raw_confidence: float
            - actual_correct: bool
            - field_type: str (optional, default "*")
            - supplier_fingerprint: str (optional, default "*")
        
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
    all_data: List[Dict] = []
    per_field: Dict[str, List[Dict]] = defaultdict(list)
    per_supplier: Dict[str, List[Dict]] = defaultdict(list)
    
    for (supplier, field), items in segments.items():
        all_data.extend(items)
        if field != "*":
            per_field[field].extend(items)
        if supplier != "*":
            per_supplier[supplier].extend(items)
    
    # 1. Train segment-specific models (supplier, field)
    for (supplier, field), items in segments.items():
        if supplier == "*" or field == "*":
            continue  # Skip aggregates, handle separately
        
        min_samples = min_samples_for_segment(supplier, field)
        if len(items) >= min_samples:
            model = train_calibration_model(
                [x['raw_confidence'] for x in items],
                [x['actual_correct'] for x in items],
                field_type=field,
                supplier_fingerprint=supplier,
                min_samples=min_samples
            )
            if model:
                registry.register(model, field, supplier)
    
    # 2. CAL-03: Train supplier-global models (supplier, "*")
    for supplier, items in per_supplier.items():
        if supplier == "*":
            continue
        
        key = (supplier, "*")
        if key not in registry.models:
            min_samples = min_samples_for_segment(supplier, "*")
            if len(items) >= min_samples:
                model = train_calibration_model(
                    [x['raw_confidence'] for x in items],
                    [x['actual_correct'] for x in items],
                    field_type="*",
                    supplier_fingerprint=supplier,
                    min_samples=min_samples
                )
                if model:
                    registry.register(model, "*", supplier)
    
    # 3. Train field-global models ("*", field)
    for field, items in per_field.items():
        if field == "*":
            continue
        
        key = ("*", field)
        if key not in registry.models:
            min_samples = min_samples_for_segment("*", field)
            if len(items) >= min_samples:
                model = train_calibration_model(
                    [x['raw_confidence'] for x in items],
                    [x['actual_correct'] for x in items],
                    field_type=field,
                    supplier_fingerprint="*",
                    min_samples=min_samples
                )
                if model:
                    registry.register(model, field, "*")
    
    # 4. Train global fallback ("*", "*")
    if ("*", "*") not in registry.models:
        min_samples = min_samples_for_segment("*", "*")
        if len(all_data) >= min_samples:
            model = train_calibration_model(
                [x['raw_confidence'] for x in all_data],
                [x['actual_correct'] for x in all_data],
                field_type="*",
                supplier_fingerprint="*",
                min_samples=min_samples
            )
            if model:
                registry.register(model, "*", "*")
    
    logger.info(
        f"Trained {len(registry.models)} calibration models from {len(data)} samples"
    )
    
    return registry


# ----------------------------
# Validation Metrics
# ----------------------------

def _calculate_ece(
    raw_scores: List[float],
    calibrated_scores: List[float],
    correct: List[float],
    n_bins: int = 10,
    use_quantile_bins: bool = True
) -> float:
    """Calculate Expected Calibration Error (ECE) (CAL-01).
    
    ECE = sum(|bin_accuracy - bin_confidence| * bin_count / total)
    
    Uses equal-frequency (quantile) bins on RAW scores for stable metrics
    with skewed probability distributions.
    
    Args:
        raw_scores: Raw confidence scores (used for binning)
        calibrated_scores: Calibrated scores (used for confidence comparison)
        correct: Ground truth (0.0 or 1.0)
        n_bins: Number of bins
        use_quantile_bins: If True, use equal-frequency binning (CAL-01)
    """
    if not raw_scores:
        return 0.0
    
    total = len(raw_scores)
    
    # CAL-01: Use quantile bins for stability
    if use_quantile_bins:
        edges = _quantile_bin_edges(raw_scores, n_bins)
        bins: List[List[Tuple[float, float]]] = [[] for _ in range(n_bins)]
        
        for raw, cal, c in zip(raw_scores, calibrated_scores, correct):
            bin_idx = _get_bin_index(raw, edges)
            bins[bin_idx].append((cal, c))
    else:
        # Fallback to equal-width bins
        bins = [[] for _ in range(n_bins)]
        for raw, cal, c in zip(raw_scores, calibrated_scores, correct):
            bin_idx = min(int(raw * n_bins), n_bins - 1)
            bins[bin_idx].append((cal, c))
    
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
    n_bins: int = 10,
    use_quantile_bins: bool = True
) -> float:
    """Calculate Maximum Calibration Error (MCE) (CAL-01).
    
    MCE = max(|bin_accuracy - bin_confidence|) across all bins
    
    Uses equal-frequency (quantile) bins for stability.
    """
    if not raw_scores:
        return 0.0
    
    # CAL-01: Use quantile bins for stability
    if use_quantile_bins:
        edges = _quantile_bin_edges(raw_scores, n_bins)
        bins: List[List[Tuple[float, float]]] = [[] for _ in range(n_bins)]
        
        for raw, cal, c in zip(raw_scores, calibrated_scores, correct):
            bin_idx = _get_bin_index(raw, edges)
            bins[bin_idx].append((cal, c))
    else:
        # Fallback to equal-width bins
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


def _suggest_recalibration(
    ece: float,
    mce: float,
    total_samples: int,
    bins_with_data: int
) -> bool:
    """Determine if recalibration is suggested (CAL-06: volume-aware).
    
    Uses adaptive thresholds based on data volume to avoid
    false positives from small-sample variance.
    """
    # Insufficient bin coverage = unreliable metrics
    if bins_with_data < 5:
        return False  # Can't trust metrics with sparse data
    
    # CAL-06: Volume-adaptive thresholds
    if total_samples < 200:
        ece_threshold, mce_threshold = 0.08, 0.15
    elif total_samples < 500:
        ece_threshold, mce_threshold = 0.06, 0.12
    else:
        ece_threshold, mce_threshold = 0.05, 0.10
    
    return ece > ece_threshold or mce > mce_threshold


def validate_calibration(
    model: Optional[CalibrationModel],
    raw_scores: List[float],
    actual_correct: List[bool],
    n_bins: int = 10
) -> Dict[str, Any]:
    """Validate calibration model against ground truth data.
    
    Features:
    - Equal-frequency (quantile) binning for ECE/MCE (CAL-01)
    - Equal-width binning for per-bin report (human readable)
    - Volume-aware recalibration thresholds (CAL-06)
    
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
    
    # CAL-01: Calibration metrics using quantile bins for stability
    ece = _calculate_ece(raw, calibrated, correct, n_bins, use_quantile_bins=True)
    mce = _calculate_mce(raw, calibrated, correct, n_bins, use_quantile_bins=True)
    brier = _calculate_brier(calibrated, correct)
    
    # Also calculate ECE with equal-width bins for comparison
    ece_equal_width = _calculate_ece(raw, calibrated, correct, n_bins, use_quantile_bins=False)
    
    # Per-bin drift using EQUAL-WIDTH bins for human-readable report
    # (quantile bin edges would vary and be confusing in reports)
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
    
    per_bin_drift: Dict[str, Dict[str, Any]] = {}
    max_drift = 0.0
    bins_with_data = 0
    
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
        
        bins_with_data += 1
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
    
    # CAL-06: Volume-aware recalibration suggestion
    suggest_recalibration = _suggest_recalibration(
        ece, mce, len(raw_scores), bins_with_data
    )
    
    return {
        'overall_accuracy': overall_accuracy,
        'ece': ece,  # Quantile-binned (stable)
        'ece_equal_width': ece_equal_width,  # For comparison
        'mce': mce,  # Quantile-binned (stable)
        'brier_score': brier,
        'max_drift': max_drift,
        'per_bin_drift': per_bin_drift,
        'suggest_recalibration': suggest_recalibration,
        'total_samples': len(raw_scores),
        'bins_with_data': bins_with_data,
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
    lines.append(f"  ECE (quantile bins):    {report['ece']:.4f}")
    if 'ece_equal_width' in report:
        lines.append(f"  ECE (equal-width bins): {report['ece_equal_width']:.4f}")
    lines.append(f"  MCE (quantile bins):    {report['mce']:.4f}")
    lines.append(f"  Brier Score:            {report['brier_score']:.4f}")
    lines.append(f"  Max Bin Drift:          {report['max_drift']:.2%}")
    lines.append(f"  Bins with data:         {report['bins_with_data']}/10")
    lines.append("")
    
    if report.get('model_metadata'):
        meta = report['model_metadata']
        lines.append("Model Metadata:")
        lines.append(f"  Field type:       {meta.field_type}")
        lines.append(f"  Supplier:         {meta.supplier_fingerprint}")
        lines.append(f"  Training samples: {meta.n_samples}")
        lines.append(f"  Training ECE:     {meta.ece:.4f}")
        lines.append(f"  Training Brier:   {meta.brier_score:.4f}")
        lines.append("")
    
    lines.append("Per-bin Analysis (equal-width bins for readability):")
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
        # CAL-06: Explain volume-aware thresholds
        n = report['total_samples']
        if n < 200:
            threshold_info = "ECE > 8% or MCE > 15% (small-data threshold)"
        elif n < 500:
            threshold_info = "ECE > 6% or MCE > 12% (medium-data threshold)"
        else:
            threshold_info = "ECE > 5% or MCE > 10% (standard threshold)"
        lines.append(f"⚠️  WARNING: Calibration drift detected ({threshold_info})")
        lines.append("   Run with --train flag to retrain calibration model")
    else:
        lines.append("✓ Calibration is well-calibrated")
    
    lines.append("")
    lines.append("=" * 65)
    
    return "\n".join(lines)

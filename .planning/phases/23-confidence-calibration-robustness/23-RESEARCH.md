# Phase 23: Confidence Calibration Robustness - Research

**Researched:** 2026-01-28
**Domain:** Probability calibration, isotonic regression, calibration metrics
**Confidence:** HIGH

## Summary

This research covers robust implementation approaches for probability calibration improvements: equal-frequency binning for stable ECE/MCE calculation, sample weights in isotonic regression to handle clustered data, and secure filename handling. The key finding is that sklearn provides all necessary primitives—`IsotonicRegression.fit(sample_weight=...)` and `calibration_curve(strategy='quantile')`—making this a straightforward integration task rather than a complex implementation challenge.

The established pattern is: aggregate duplicate scores with their counts as weights, train isotonic regression with those weights, and evaluate using quantile-binned ECE/MCE. This produces smooth calibration curves even with clustered data and stable drift metrics even with skewed probability distributions.

**Primary recommendation:** Use sklearn's existing `sample_weight` parameter and numpy's `quantile` function rather than hand-rolling weighted fitting or custom binning logic.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sklearn.isotonic.IsotonicRegression | 1.8+ | Monotonic calibration function | De facto standard for probability calibration; supports sample_weight |
| numpy.quantile | 2.0+ | Equal-frequency bin edge calculation | Optimized, handles edge cases correctly |
| sklearn.calibration.calibration_curve | 1.8+ | Reference implementation | strategy='quantile' for equal-frequency binning |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathvalidate | 3.0+ | Filename sanitization | When needing cross-platform safe filenames |
| re (stdlib) | - | Simple character filtering | When pathvalidate is overkill (internal-only filenames) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| numpy.quantile | Manual percentile calculation | numpy is optimized and handles edge cases; never hand-roll |
| pathvalidate | Simple regex | Regex is lighter but misses edge cases (reserved names, max length) |
| sklearn CalibrationDisplay | Custom plotting | sklearn is standard for visualization |

**Installation:**
```bash
# Already in requirements (sklearn, numpy)
pip install pathvalidate  # Optional: if robust sanitization needed
```

## Architecture Patterns

### Recommended Project Structure

No structural changes needed. All changes are in `src/pipeline/confidence_calibration.py`:

```
src/pipeline/
├── confidence_calibration.py  # All calibration logic (modified)
└── ...
```

### Pattern 1: Weighted Isotonic Regression

**What:** Pass sample counts as weights to `IsotonicRegression.fit()` when training on aggregated data.

**When to use:** Always, when aggregating duplicate X values (raw scores) before fitting.

**Why:** Raw scores often cluster (e.g., many predictions at 0.85, 0.90). Without weights, isotonic regression treats one aggregated point at 0.85 the same as one aggregated point at 0.90, even if the former represents 100 samples and the latter represents 5. Weights correct this.

**Example:**
```python
from sklearn.isotonic import IsotonicRegression
from collections import defaultdict
from typing import List, Tuple

def _aggregate_with_weights(
    raw_scores: List[float], 
    correct: List[float]
) -> Tuple[List[float], List[float], List[float]]:
    """Aggregate samples by rounded score, returning weights."""
    groups: dict[float, list[float]] = defaultdict(list)
    for score, c in zip(raw_scores, correct):
        rounded = round(score, 4)
        groups[rounded].append(c)
    
    xs, ys, ws = [], [], []
    for score in sorted(groups.keys()):
        vals = groups[score]
        xs.append(score)
        ys.append(sum(vals) / len(vals))  # Mean correctness
        ws.append(float(len(vals)))        # Count as weight
    return xs, ys, ws

# Training:
X_agg, y_agg, weights = _aggregate_with_weights(raw_scores, correct)
model = IsotonicRegression(out_of_bounds='clip', increasing=True)
model.fit(X_agg, y_agg, sample_weight=weights)  # Pass weights!
```

**Source:** sklearn 1.8 documentation - IsotonicRegression.fit() accepts `sample_weight` array-like of shape (n_samples,) where weights must be strictly positive.

### Pattern 2: Equal-Frequency (Quantile) Binning for ECE/MCE

**What:** Compute bin edges using quantiles so each bin contains approximately equal samples.

**When to use:** Always for ECE/MCE calculation. Equal-width bins produce unstable metrics when probability distributions are skewed (common in practice).

**Why:** With equal-width bins, low-probability bins may have very few samples (or none), making drift estimates noisy. Equal-frequency ensures each bin has statistical support.

**Example:**
```python
import numpy as np
from typing import List

def _quantile_bin_edges(values: List[float], n_bins: int) -> np.ndarray:
    """Compute bin edges using quantiles for equal-frequency binning."""
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
    """Get bin index for a value given edges."""
    # np.searchsorted finds insertion point; -1 for bin index
    # clip to valid range
    idx = np.searchsorted(edges, value, side='right') - 1
    return max(0, min(idx, len(edges) - 2))
```

**Source:** sklearn's `calibration_curve(strategy='quantile')` implements this pattern. numpy.quantile documentation (v2.4) provides the underlying computation.

### Pattern 3: Segment-Adaptive Min-Samples Thresholds

**What:** Use different minimum sample thresholds based on segment specificity.

**When to use:** When training hierarchical/segmented calibration models.

**Why:** More specific segments (supplier+field) need more samples for reliable calibration than generic segments (global). This reflects the statistical principle that more specific models have higher variance and need more data to stabilize.

**Example:**
```python
# Thresholds based on segment level
MIN_SAMPLES_SUPPLIER_FIELD = 200   # Most specific: (supplier, field)
MIN_SAMPLES_SUPPLIER_GLOBAL = 150  # Supplier aggregate: (supplier, "*")
MIN_SAMPLES_FIELD_GLOBAL = 100     # Field aggregate: ("*", field)
MIN_SAMPLES_GLOBAL = 50            # Least specific: ("*", "*")

def get_min_samples(supplier: str, field: str) -> int:
    """Get appropriate min-samples threshold for segment specificity."""
    if supplier != "*" and field != "*":
        return MIN_SAMPLES_SUPPLIER_FIELD
    elif supplier != "*":
        return MIN_SAMPLES_SUPPLIER_GLOBAL
    elif field != "*":
        return MIN_SAMPLES_FIELD_GLOBAL
    else:
        return MIN_SAMPLES_GLOBAL
```

**Source:** Hierarchical calibration literature recommends moderate calibration as practical target; thresholds are domain-specific but the principle of higher requirements for more specific segments is established.

### Pattern 4: Volume-Aware Recalibration Thresholds

**What:** Adjust ECE/MCE thresholds for triggering recalibration based on data volume.

**When to use:** When deciding whether current calibration needs retraining.

**Why:** With small samples, ECE/MCE estimates have high variance. A strict threshold (ECE > 0.05) may trigger false positives. Relaxing thresholds for small N avoids unnecessary recalibration.

**Example:**
```python
def suggest_recalibration(
    ece: float, 
    mce: float, 
    total_samples: int, 
    bins_with_data: int
) -> bool:
    """Suggest recalibration with volume-aware thresholds."""
    # Insufficient bin coverage = unreliable metrics
    if bins_with_data < 5:
        return False  # Can't trust metrics with sparse data
    
    # Volume-adaptive thresholds
    if total_samples < 200:
        ece_threshold, mce_threshold = 0.08, 0.15
    elif total_samples < 500:
        ece_threshold, mce_threshold = 0.06, 0.12
    else:
        ece_threshold, mce_threshold = 0.05, 0.10
    
    return ece > ece_threshold or mce > mce_threshold
```

**Source:** Calibration literature notes ECE estimator bias depends on sample size and bin formation method. Adaptive thresholds are a practical response.

### Pattern 5: Safe Filename Generation

**What:** Sanitize user-controlled strings before using in filenames.

**When to use:** When constructing filenames from supplier IDs, field names, or other potentially unsafe strings.

**Why:** Prevents path traversal attacks (../../../etc/passwd) and filesystem errors from invalid characters.

**Example:**
```python
import re

def _safe_key(s: str, max_length: int = 120) -> str:
    """Sanitize string for use in filename."""
    # Replace anything not alphanumeric, dot, underscore, or hyphen
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    # Collapse multiple underscores
    safe = re.sub(r"_+", "_", safe)
    # Strip leading/trailing underscores
    safe = safe.strip("_")
    # Enforce max length
    return safe[:max_length] if safe else "unknown"

# Usage in registry:
def _make_filename(supplier: str, field: str) -> str:
    return f"calibration_{_safe_key(supplier)}_{_safe_key(field)}.joblib"
```

**Source:** OWASP path traversal prevention guidelines; pathvalidate library documentation for cross-platform safety patterns.

### Anti-Patterns to Avoid

- **Training without weights on aggregated data:** Results in "steppy" calibration curves that don't reflect true data distribution
- **Equal-width bins for skewed distributions:** Produces unstable ECE/MCE with empty or near-empty bins
- **Fixed recalibration threshold regardless of N:** Triggers false positives with small datasets
- **Trusting user input in filenames:** Path traversal vulnerability
- **Using string formatting for filenames without sanitization:** Risk of filesystem errors or security issues

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Quantile calculation | Manual percentile indexing | `numpy.quantile()` | Handles interpolation methods, edge cases, ties correctly |
| Isotonic regression | Custom PAVA implementation | `sklearn.isotonic.IsotonicRegression` | Optimized C implementation, sample_weight support, tested |
| Equal-frequency binning | Custom bin edge calculation | `numpy.quantile(values, np.linspace(0, 1, n_bins+1))` | One line, correct |
| Calibration curve plotting | Manual matplotlib code | `sklearn.calibration.CalibrationDisplay` | Standard visualization |
| Complex filename sanitization | Custom regex for all platforms | `pathvalidate.sanitize_filename()` | Handles reserved names, max lengths, platform differences |

**Key insight:** sklearn's calibration tooling (`IsotonicRegression`, `calibration_curve`, `CalibrationDisplay`) covers 95% of calibration needs. The task is integration, not invention.

## Common Pitfalls

### Pitfall 1: Forgetting sample_weight When Aggregating

**What goes wrong:** Aggregating duplicate scores, then fitting isotonic without weights treats all aggregated points equally regardless of how many samples they represent.

**Why it happens:** The aggregation step is correct (reduces noise), but developers forget to propagate counts as weights.

**How to avoid:** Always return weights from aggregation function and pass to `fit()`.

**Warning signs:** Calibration curve has pronounced "steps" or "plateaus" despite large training data.

### Pitfall 2: Equal-Width Bins with Skewed Probabilities

**What goes wrong:** ECE/MCE become unstable, changing dramatically between runs or with small data changes.

**Why it happens:** Many models produce skewed probability distributions (e.g., 80% of predictions between 0.7-1.0). Equal-width bins 0.0-0.1, 0.1-0.2, etc. have very few samples in low bins.

**How to avoid:** Use quantile-based binning (strategy='quantile' in sklearn terms).

**Warning signs:** Per-bin reports show 0 or <5 samples in multiple bins; ECE/MCE vary significantly between similar datasets.

### Pitfall 3: Path Traversal in Registry Filenames

**What goes wrong:** Malicious or malformed supplier IDs like `../../etc/passwd` become part of filenames.

**Why it happens:** Direct string interpolation without sanitization.

**How to avoid:** Always sanitize user-controlled strings with `_safe_key()` or `pathvalidate`.

**Warning signs:** Filenames containing `..`, `/`, `\`, or other special characters.

### Pitfall 4: Triggering Recalibration on Small Data Noise

**What goes wrong:** Recalibration suggested after every run due to ECE variance from small samples.

**Why it happens:** Fixed ECE threshold (0.05) without considering sample size.

**How to avoid:** Use volume-aware thresholds; require minimum bin coverage.

**Warning signs:** Constant "recalibration needed" warnings; ECE fluctuates 50%+ between identical-sized datasets.

### Pitfall 5: Missing Supplier-Global Models in Fallback Chain

**What goes wrong:** Fallback jumps from (supplier, field) directly to (*, field), missing useful intermediate (supplier, *) models.

**Why it happens:** Training loop only considers per-field and global aggregations.

**How to avoid:** Explicitly loop over per_supplier aggregations and train (supplier, "*") models.

**Warning signs:** Fallback chain logs show no (supplier, "*") hits; new field types for known suppliers use global instead of supplier-specific calibration.

## Code Examples

Verified patterns from official sources:

### IsotonicRegression with sample_weight
```python
# Source: sklearn 1.8 documentation
from sklearn.isotonic import IsotonicRegression

# X, y can be 1D arrays or (n, 1) shaped
# sample_weight must be positive floats
model = IsotonicRegression(out_of_bounds='clip', increasing=True)
model.fit(X, y, sample_weight=weights)

# Prediction
y_pred = model.predict(X_new)  # Always returns 1D array
```

### numpy.quantile for Bin Edges
```python
# Source: numpy 2.4 documentation
import numpy as np

# 10 bins = 11 edges
quantiles = np.linspace(0, 1, 11)
edges = np.quantile(scores, quantiles)  # Default method='linear'

# For tied data, 'lower' or 'higher' may be more appropriate
edges = np.quantile(scores, quantiles, method='lower')
```

### sklearn calibration_curve Reference
```python
# Source: sklearn 1.8 documentation
from sklearn.calibration import calibration_curve

# strategy='quantile' for equal-frequency binning
prob_true, prob_pred = calibration_curve(
    y_true, y_prob, 
    n_bins=10, 
    strategy='quantile'  # Equal-frequency!
)
```

### Simple Filename Sanitization
```python
import re

def sanitize_filename(s: str) -> str:
    """Remove/replace unsafe characters."""
    # Keep only safe chars
    safe = re.sub(r'[^a-zA-Z0-9._-]', '_', s)
    # No leading dots (hidden files) or multiple underscores
    safe = re.sub(r'^\.+', '', safe)
    safe = re.sub(r'_+', '_', safe)
    return safe.strip('_')[:255] or 'unnamed'
```

## State of the Art (2025-2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Equal-width binning for ECE | Equal-frequency (quantile) binning | ~2020 onwards | Stable metrics for skewed distributions |
| Unweighted isotonic on raw data | Weighted isotonic on aggregated data | Best practice | Smooth calibration curves |
| Fixed ECE thresholds | Volume-aware adaptive thresholds | Recent practice | Fewer false recalibration triggers |
| Temperature scaling only | Histogram binning + scaling combo | 2019 paper | Better calibration guarantees |

**New tools/patterns to consider:**
- `CalibrationDisplay` for standardized visualization (sklearn 1.0+)
- Debiased ECE estimators for small samples (academic; not yet in sklearn)

**Deprecated/outdated:**
- Platt scaling alone (use isotonic or combined approaches)
- Equal-width binning for ECE (use quantile)
- Fixed min-samples regardless of segment (use adaptive)

## Open Questions

Things that couldn't be fully resolved:

1. **Exact min-samples thresholds**
   - What we know: More specific segments need more samples; literature doesn't give exact numbers
   - What's unclear: Whether 200/150/100/50 are optimal for this domain
   - Recommendation: Start with context-specified values, adjust based on observed calibration quality

2. **Debiased ECE estimators**
   - What we know: Academic literature proposes debiased estimators that reduce small-sample bias
   - What's unclear: Not available in sklearn; implementation complexity vs benefit
   - Recommendation: Use quantile binning (major improvement); defer debiasing to future iteration

3. **Hierarchical shrinkage (α blending)**
   - What we know: Blending segment predictions with global predictions can reduce variance
   - What's unclear: Optimal α selection method for this domain
   - Recommendation: Marked out of scope (CAL-07 LOW priority); implement fallback chain first

## Sources

### Primary (HIGH confidence)
- sklearn 1.8 documentation: `IsotonicRegression.fit(sample_weight=...)` - verified accepts weight parameter
- sklearn 1.8 documentation: `calibration_curve(strategy='quantile')` - verified equal-frequency binning support
- numpy 2.4 documentation: `numpy.quantile()` - verified interpolation methods and edge handling

### Secondary (MEDIUM confidence)
- sklearn isotonic module user guide - pattern for probability calibration
- JMLR "Metrics of Calibration for Probabilistic Predictions" (2022) - ECE limitations and alternatives
- Stack Overflow verified answers on quantile binning edge cases

### Tertiary (LOW confidence)
- General calibration threshold recommendations (0.05/0.10) - common practice but not formally standardized
- Exact min-samples thresholds for hierarchical calibration - domain-dependent, start with proposed values

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - sklearn documentation verified
- Architecture patterns: HIGH - patterns from official docs and established practice
- Pitfalls: MEDIUM - based on common issues in calibration literature
- Min-samples thresholds: LOW - domain-specific, proposed values need validation

**Research date:** 2026-01-28
**Valid until:** 2026-04-28 (90 days - stable domain, sklearn API unlikely to change)

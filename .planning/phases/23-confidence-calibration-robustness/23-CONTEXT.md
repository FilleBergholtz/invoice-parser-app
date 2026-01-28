# Phase 23: Confidence Calibration Robustness - Context

**Phase:** 23-confidence-calibration-robustness  
**Milestone:** v2.1 Parsing robustness / EDI  
**Status:** Not started  
**Created:** 2026-01-28

---

## Problem Statement

Den nuvarande `confidence_calibration.py` har flera brister som påverkar kalibreringsnoggranhet och stabilitet:

1. **Equal-width binning** används för ECE/MCE, vilket ger instabila driftmått vid skev data
2. **Isotonic regression utan sample weights** kan ge "trappiga" kurvor vid klustrad data
3. **Supplier-global modeller saknas** i träningsflödet (hål i fallback-kedjan)
4. **Osäkra filnamn** i registry (path traversal risk)
5. **Fasta min-samples thresholds** oavsett segment-nivå
6. **Recalibration threshold ignorerar datavolym**

---

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| CAL-01 | Equal-frequency binning för ECE/MCE (quantile bins) | HIGH |
| CAL-02 | Sample weights i isotonic regression baserat på count per score | HIGH |
| CAL-03 | Träna supplier-global modeller (supplier, "*") i registry | HIGH |
| CAL-04 | Sanitize filnamn i registry (säkra tecken) | MEDIUM |
| CAL-05 | Adaptiva min-samples: supplier+field 200+, supplier-global 150+, field-global 100+, global 50+ | MEDIUM |
| CAL-06 | Recalibration threshold justeras för låg datavolym (ECE>0.08 om N<200) | MEDIUM |

### Optional/Future

| ID | Requirement | Priority |
|----|-------------|----------|
| CAL-07 | Hierarkisk shrinkage (α*pred_segment + (1-α)*pred_global) | LOW |
| CAL-08 | ECE_raw vs ECE_cal i rapport för att se kalibreringsförbättring | LOW |
| CAL-09 | Cachea quantile edges för hastighet vid stora dataset | LOW |

---

## Technical Details

### 1. Equal-Frequency Binning

```python
def _quantile_bin_edges(values: List[float], n_bins: int) -> List[float]:
    if not values:
        return [0.0, 1.0]
    v = sorted(values)
    edges = [v[0]]
    for i in range(1, n_bins):
        q_idx = int(round(i * (len(v) - 1) / n_bins))
        edges.append(v[q_idx])
    edges.append(v[-1])
    # ensure strictly increasing edges (dedupe)
    out = [edges[0]]
    for e in edges[1:]:
        if e <= out[-1]:
            e = min(1.0, out[-1] + 1e-6)
        out.append(e)
    out[0] = 0.0
    out[-1] = 1.0
    return out

def _bin_index(x: float, edges: List[float]) -> int:
    for i in range(len(edges) - 1):
        if i == len(edges) - 2:
            if edges[i] <= x <= edges[i + 1]:
                return i
        if edges[i] <= x < edges[i + 1]:
            return i
    return len(edges) - 2
```

### 2. Sample Weights i Isotonic

```python
def _aggregate_by_score_with_weights(
    raw_scores: List[float], 
    correct: List[float]
) -> Tuple[List[float], List[float], List[float]]:
    groups: Dict[float, List[float]] = defaultdict(list)
    for s, c in zip(raw_scores, correct):
        groups[round(s, 4)].append(c)

    xs, ys, ws = [], [], []
    for s in sorted(groups.keys()):
        vals = groups[s]
        xs.append(s)
        ys.append(sum(vals) / len(vals))
        ws.append(float(len(vals)))
    return xs, ys, ws

# Användning:
X_agg, y_agg, w_agg = _aggregate_by_score_with_weights(X, y)
model.fit(X_agg, y_agg, sample_weight=w_agg)
```

### 3. Supplier-Global Modeller

```python
# Train supplier-global models
for supplier, items in per_supplier.items():
    if supplier == "*":
        continue
    key = (supplier, "*")
    if key not in registry.models and len(items) >= MIN_SAMPLES_SUPPLIER_GLOBAL:
        model = train_calibration_model(
            [x["raw_confidence"] for x in items],
            [x["actual_correct"] for x in items],
            field_type="*",
            supplier_fingerprint=supplier,
            min_samples=MIN_SAMPLES_SUPPLIER_GLOBAL,
        )
        if model:
            registry.register(model, "*", supplier)
```

### 4. Säkra Filnamn

```python
import re

def _safe_key(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s)[:120]

# Användning:
filename = f"calibration_{_safe_key(supplier)}_{_safe_key(field)}.joblib"
```

### 5. Adaptiva Min-Samples

```python
MIN_SAMPLES_SUPPLIER_FIELD = 200   # (supplier, field)
MIN_SAMPLES_SUPPLIER_GLOBAL = 150  # (supplier, "*")
MIN_SAMPLES_FIELD_GLOBAL = 100     # ("*", field)
MIN_SAMPLES_GLOBAL = 50            # ("*", "*")
```

### 6. Datavolym-Aware Recalibration

```python
def _suggest_recalibration(ece: float, mce: float, total_samples: int, bins_with_data: int) -> bool:
    # Adjust thresholds for small data
    if total_samples < 200:
        ece_threshold = 0.08
        mce_threshold = 0.15
    elif total_samples < 500:
        ece_threshold = 0.06
        mce_threshold = 0.12
    else:
        ece_threshold = 0.05
        mce_threshold = 0.10
    
    # Also consider bin coverage
    if bins_with_data < 5:
        # Too little support to trust metrics
        return False  # Don't trigger recalibration based on unreliable metrics
    
    return ece > ece_threshold or mce > mce_threshold
```

---

## Dependencies

- Phase 22: Valideringsdriven om-extraktion (complete)
- `sklearn.isotonic.IsotonicRegression` (already in use)

---

## Affected Files

| File | Changes |
|------|---------|
| `src/pipeline/confidence_calibration.py` | All changes |
| `tests/test_confidence_calibration.py` | New test file |

---

## Test Strategy

1. **Unit tests for quantile binning**
   - Empty input
   - Single value
   - Skewed distribution
   - Uniform distribution

2. **Unit tests for sample weights**
   - Verify weights are passed to isotonic
   - Verify aggregation is correct

3. **Integration tests for registry**
   - Supplier-global models created
   - Fallback chain works correctly
   - Safe filenames for special characters

4. **Validation tests**
   - ECE/MCE calculated correctly with equal-frequency bins
   - Recalibration threshold adapts to data size

---

## Success Criteria

1. ECE/MCE uses equal-frequency binning (quantile bins)
2. Isotonic regression uses sample weights
3. Supplier-global models are trained and accessible via fallback
4. Filenames are safe for all inputs (no path traversal)
5. Min-samples thresholds are segment-adaptive
6. Recalibration suggestion considers data volume

---

## Out of Scope

- Hierarkisk shrinkage (can be added in future plan)
- ECE_raw vs ECE_cal comparison (nice-to-have)
- Performance caching (optimize later if needed)

---

*Context created: 2026-01-28*

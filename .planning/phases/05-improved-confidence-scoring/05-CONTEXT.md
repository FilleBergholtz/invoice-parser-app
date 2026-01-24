# Phase 5: Improved Confidence Scoring - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve confidence scoring for total amount extraction to reduce REVIEW status. Add enhanced multi-factor scoring with additional signals, calibration against actual accuracy, multiple candidate extraction/scoring, and regular validation workflow.

**Core Problem:** Too many invoices receive REVIEW status due to low confidence (< 0.95) on total amount extraction.

**Goal:** Fewer invoices with REVIEW status due to low confidence (measurable improvement).

</domain>

<decisions>
## Implementation Decisions

### 1. Enhanced Multi-Factor Scoring

**Current Implementation:**
- Keyword match (0.35 weight)
- Position (0.20 weight)
- Mathematical validation (0.35 weight)
- Relative size (0.10 weight)

**Additional Signals to Add:**
- **Font size/weight** (0.05 weight): Total amount often in larger/bolder font
- **Proximity to VAT breakdown** (0.05 weight): Total often near VAT amount rows
- **Currency symbol presence** (0.03 weight): SEK/kr/:- symbols increase confidence
- **Row isolation** (0.02 weight): Total often on separate row or in box

**Total weights should still sum to 1.0** (adjust existing weights slightly to accommodate new signals).

### 2. Confidence Calibration

**Requirement:** Confidence 0.95 = 95% correct in validation.

**Approach:**
- Collect ground truth data (user corrections from Phase 6, or manual validation)
- Build calibration curve mapping raw scores to calibrated scores
- Use isotonic regression or Platt scaling (scikit-learn) for calibration
- Store calibration model in config or database

**Calibration Process:**
1. Collect (raw_score, actual_correct) pairs from validation data
2. Train calibration model (isotonic regression recommended for monotonicity)
3. Apply calibration to all confidence scores
4. Validate calibration regularly (monthly/quarterly)

### 3. Multiple Candidate Extraction

**Current:** Extracts multiple candidates but only scores top 10.

**Improvements:**
- Extract ALL candidates (no limit during extraction)
- Score ALL candidates independently (not just top 10)
- Store top N candidates (e.g., top 5) with scores for UI display
- Use candidate ranking for better selection logic

### 4. Regular Validation Workflow

**Requirement:** System validates confidence calibration regularly against ground truth data.

**Approach:**
- CLI command: `python -m src.cli.main --validate-confidence`
- Reads ground truth data (from learning database or manual validation file)
- Compares predicted confidence vs actual accuracy
- Reports calibration drift
- Suggests recalibration if drift > 5%

</decisions>

<current_state>
## Current Implementation

**Files:**
- `src/pipeline/confidence_scoring.py`: Multi-factor scoring algorithms
- `src/pipeline/footer_extractor.py`: Total amount extraction with candidate scoring

**Current Scoring:**
- `score_total_amount_candidate()`: 4-factor scoring (keyword 0.35, position 0.20, validation 0.35, size 0.10)
- `validate_total_against_line_items()`: Mathematical validation with tolerance

**Limitations:**
- No calibration (raw scores may not reflect actual accuracy)
- Limited signals (only 4 factors)
- Candidate extraction limited to top 10 for scoring
- No validation workflow

</current_state>

<requirements>
## Phase Requirements

- **CONF-01**: Enhanced multi-factor confidence scoring (additional signals)
- **CONF-02**: Calibration against actual accuracy (confidence 0.95 = 95% correct)
- **CONF-03**: Display improvements (already exists, needs enhancement)
- **CONF-04**: Multiple candidates scored independently (improve extraction/scoring)
- **CONF-05**: Regular validation against ground truth data

</requirements>

<research>
## Research References

- `.planning/research/SUMMARY.md`: Recommended approach (calibration from start, avoid score inflation)
- `.planning/research/STACK.md`: scikit-learn for calibration models
- `.planning/research/PITFALLS.md`: Confidence score inflation (calibrate from start)

</research>

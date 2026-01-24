---
phase: 05-improved-confidence-scoring
plan: 01
subsystem: confidence-scoring
tags: [confidence-scoring, multi-factor-scoring, candidate-extraction]

# Dependency graph
requires:
  - phase: 04-web-ui
    provides: v1.0 complete, foundation for v2.0 improvements
provides:
  - Enhanced multi-factor confidence scoring with 4 additional signals
  - All candidate extraction (no limit) and independent scoring
  - Top 5 candidates storage in InvoiceHeader for UI display
affects: [05-02 - calibration will use enhanced scoring, 06 - manual validation UI will use total_candidates]

# Tech tracking
tech-stack:
  added: []
  patterns: [Enhanced multi-factor scoring with font/VAT/currency/isolation signals, all-candidate extraction pattern]

key-files:
  created: []
  modified:
    - src/pipeline/confidence_scoring.py (enhanced scoring with 4 new signals)
    - src/pipeline/footer_extractor.py (all-candidate extraction, top 5 storage)
    - src/models/invoice_header.py (added total_candidates field)

key-decisions:
  - "Adjusted existing weights to accommodate new signals (keyword 0.32, position 0.18, validation 0.32, size 0.08)"
  - "Removed candidate limit - score ALL candidates independently for better accuracy"
  - "Store top 5 candidates in InvoiceHeader for UI display (Phase 6 will use this)"

patterns-established:
  - "Enhanced scoring pattern: 8-factor scoring (4 original + 4 new signals) summing to 1.0"
  - "All-candidate extraction pattern: Extract all, score all, store top N for UI"

# Metrics
duration: ~20min
completed: 2026-01-24
---

# Phase 05: Improved Confidence Scoring - Plan 01 Summary

**Enhanced multi-factor confidence scoring with font size, VAT proximity, currency symbols, and row isolation signals, plus all-candidate extraction with top 5 storage**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-01-24
- **Completed:** 2026-01-24
- **Tasks:** 2 completed
- **Files modified:** 3

## Accomplishments

- Enhanced `score_total_amount_candidate()` with 4 additional signals (font size/weight, VAT proximity, currency symbols, row isolation)
- Adjusted existing weights to sum to 1.0 (keyword 0.32, position 0.18, validation 0.32, size 0.08)
- Removed candidate limit - extract and score ALL candidates independently
- Added `total_candidates` field to InvoiceHeader storing top 5 candidates with scores
- Updated `extract_total_amount()` to score all candidates and store top 5 for UI

## Task Commits

Each task was committed atomically:

1. **Task 1: Enhance confidence scoring with additional signals** - Enhanced scoring function with 4 new signals, adjusted weights
2. **Task 2: Improve candidate extraction and scoring** - Removed limit, score all candidates, store top 5 in InvoiceHeader

**Plan metadata:** Committed together as single implementation

## Files Created/Modified

- `src/pipeline/confidence_scoring.py` - Enhanced `score_total_amount_candidate()` with font size (0.05), VAT proximity (0.05), currency symbols (0.03), row isolation (0.02) signals
- `src/pipeline/footer_extractor.py` - Removed candidate limit, score all candidates, store top 5 in `InvoiceHeader.total_candidates`
- `src/models/invoice_header.py` - Added `total_candidates: Optional[List[Dict[str, Any]]] = None` field

## Decisions Made

- **Weight adjustment:** Reduced existing weights proportionally to accommodate new signals while maintaining sum of 1.0
- **Font size heuristic:** Compare candidate row font size to average footer row font size (10% larger threshold for full score)
- **VAT proximity:** Check within 2-3 rows for "moms" keywords (full score within 1 row, partial within 2 rows)
- **Currency symbols:** Simple presence check for SEK/kr/:- symbols
- **Row isolation:** Check vertical spacing > 18.0 (1.5x typical row height) to adjacent rows
- **All-candidate extraction:** Removed performance limit - accuracy more important than speed for this use case
- **Top 5 storage:** Store top 5 candidates (not all) to balance UI needs with data size

## Deviations from Plan

None - plan executed exactly as written

## Issues Encountered

None

## Next Phase Readiness

- Enhanced scoring ready for calibration (Phase 5 Plan 02)
- Top 5 candidates available for manual validation UI (Phase 6)
- All candidates scored independently - ready for calibration training data collection

---
*Phase: 05-improved-confidence-scoring*
*Completed: 2026-01-24*

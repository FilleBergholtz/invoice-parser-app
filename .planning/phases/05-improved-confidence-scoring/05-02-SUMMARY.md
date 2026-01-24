---
phase: 05-improved-confidence-scoring
plan: 02
subsystem: confidence-calibration
tags: [confidence-calibration, isotonic-regression, scikit-learn, joblib]

# Dependency graph
requires:
  - phase: 05-01
    provides: Enhanced confidence scoring with all candidates extracted
provides:
  - Confidence score calibration using isotonic regression
  - Calibration model storage and loading
  - Integration with confidence scoring pipeline
affects: [05-03 - validation CLI will use calibration functions, 06 - manual validation will use calibrated scores]

# Tech tracking
tech-stack:
  added: [scikit-learn>=1.3.0, joblib>=1.3.0]
  patterns: [Isotonic regression calibration, model caching pattern, optional calibration fallback]

key-files:
  created:
    - src/pipeline/confidence_calibration.py
  modified:
    - src/pipeline/footer_extractor.py (integrated calibration)
    - src/config.py (added calibration config functions)
    - src/config/__init__.py (exported new config functions)

key-decisions:
  - "Use isotonic regression for monotonic calibration (higher raw = higher calibrated)"
  - "Cache calibration model in memory to avoid reloading for each invoice"
  - "Calibration is optional - fallback to raw scores if model not found (graceful degradation)"
  - "Apply calibration to all candidate scores before final selection"

patterns-established:
  - "Calibration pattern: Load model once, cache, apply to all scores before selection"
  - "Optional calibration pattern: Check enabled flag, load model, fallback gracefully"

# Metrics
duration: ~25min
completed: 2026-01-24
---

# Phase 05: Improved Confidence Scoring - Plan 02 Summary

**Confidence score calibration system implemented using isotonic regression with model storage and optional integration**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-01-24
- **Completed:** 2026-01-24
- **Tasks:** 2 completed
- **Files modified:** 3 created, 2 modified

## Accomplishments

- Created `confidence_calibration.py` module with `CalibrationModel` class
- Implemented `train_calibration_model()` using isotonic regression
- Implemented `calibrate_confidence()` function for applying calibration
- Integrated calibration into `extract_total_amount()` pipeline
- Added calibration model caching to avoid reloading for each invoice
- Added config functions for calibration enable/disable and model path
- Calibration is optional - gracefully falls back to raw scores if model not found

## Task Commits

Each task was committed atomically:

1. **Task 1: Create confidence calibration module** - Created calibration module with IsotonicRegression
2. **Task 2: Integrate calibration into confidence scoring** - Integrated calibration with caching and config

**Plan metadata:** Committed together as single implementation

## Files Created/Modified

- `src/pipeline/confidence_calibration.py` - NEW: CalibrationModel class, train_calibration_model(), calibrate_confidence()
- `src/pipeline/footer_extractor.py` - Integrated calibration: load model, apply to all candidates, cache model
- `src/config.py` - Added get_calibration_enabled() and get_calibration_model_path()
- `src/config/__init__.py` - Exported new calibration config functions

## Decisions Made

- **Isotonic regression:** Chosen for monotonic mapping (higher raw = higher calibrated), ensures scores stay in [0, 1] with out_of_bounds='clip'
- **Model caching:** Cache loaded model in module-level variable to avoid reloading for each invoice (performance optimization)
- **Optional calibration:** Calibration is optional - if model not found, use raw scores (graceful degradation, no failures)
- **Calibration timing:** Apply calibration to all candidate scores after scoring but before final selection (ensures calibrated scores used for selection)
- **Config approach:** Use environment variables (CALIBRATION_ENABLED, CALIBRATION_MODEL_PATH) with defaults (enabled=True, default path)
- **Model storage:** Use joblib for serialization (more efficient than pickle for sklearn models), default path: configs/calibration_model.joblib

## Deviations from Plan

None - plan executed exactly as written

## Issues Encountered

- **Import path issue:** Initially tried to import from `src.config` but config is in `src/config/__init__.py` which re-exports from `src/config.py`. Fixed by updating `__init__.py` to export new functions.

## Next Phase Readiness

- Calibration system ready for training (Phase 5 Plan 03 will add CLI command)
- Calibration model can be trained from ground truth data
- Calibrated scores are applied to all confidence scores in pipeline
- Ready for validation workflow (Plan 03)

---
*Phase: 05-improved-confidence-scoring*
*Completed: 2026-01-24*

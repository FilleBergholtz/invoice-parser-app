---
phase: 16-text-layer-routing-ocr-skip
plan: 16-01
subsystem: pipeline
tags: [ocr, pdfplumber, routing, pytesseract, text-quality]

# Dependency graph
requires:
  - phase: Phase 15
    provides: existing OCR pipeline and compare-extraction flow
provides:
  - per-page text-layer routing configuration
  - routing helper with debug reasons
  - pipeline integration for mixed text/OCR pages
  - stabilized OCR output parsing
  - routing tests
affects: [phase-17, phase-20, phase-22]

# Tech tracking
tech-stack:
  added: []
  patterns: [per-page routing with anchors + quality override, OCR fallback only]

key-files:
  created: [src/pipeline/ocr_routing.py, tests/test_ocr_routing.py]
  modified: [configs/profiles/default.yaml, src/config/profile_loader.py, src/cli/main.py, src/pipeline/invoice_boundary_detection.py, src/pipeline/ocr_abstraction.py]

key-decisions:
  - "Per-page routing uses required + extra anchors with optional quality override."
  - "OCR fallback uses pytesseract DICT/STRING output to avoid TSV enum errors."

patterns-established:
  - "Routing decisions provide debug reasons and page-level metadata."
  - "OCR only runs on pages with insufficient text layer."

# Metrics
duration: 13min
completed: 2026-01-26
---

# Phase 16 Plan 01: Text-layer routing (OCR-skip) Summary

**Per-page text-layer routing with anchor/quality thresholds and OCR fallback-only extraction, plus stabilized OCR parsing.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-01-26T15:54:25Z
- **Completed:** 2026-01-26T16:06:55Z
- **Tasks:** 5
- **Files modified:** 7

## Accomplishments
- Added configurable OCR routing defaults (anchors, thresholds, override)
- Implemented per-page routing across invoice processing and boundary detection
- Hardened OCR output parsing and added routing unit tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Konfigurationsnycklar för OCR‑routing** - `999521a` (feat)
2. **Task 2: Implementera per‑sida text‑layer check** - `df07a5d` (feat)
3. **Task 3: Integrera routing i pipeline** - `2a52ae7` (feat)
4. **Task 4: Fixa KeyError: 4 i OCR compare‑path** - `36d7f26` (fix)
5. **Task 5: Tester för routing och regression** - `55ef946` (test)

**Plan metadata:** pending

_Note: TDD tasks may have multiple commits (test → feat → refactor)_

## Files Created/Modified
- `configs/profiles/default.yaml` - adds default ocr_routing configuration
- `src/config/profile_loader.py` - exposes ocr_routing on ProfileConfig
- `src/pipeline/ocr_routing.py` - routing defaults and decision helper
- `src/cli/main.py` - per-page routing in invoice processing and compare flow
- `src/pipeline/invoice_boundary_detection.py` - mixed text/OCR token extraction for boundaries
- `src/pipeline/ocr_abstraction.py` - robust OCR output parsing
- `tests/test_ocr_routing.py` - routing decision tests

## Decisions Made
None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
Per-page routing and OCR fallback are in place, ready for AI-policy adjustments and downstream extraction phases.

---
*Phase: 16-text-layer-routing-ocr-skip*
*Completed: 2026-01-26*

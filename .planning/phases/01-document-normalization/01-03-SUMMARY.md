---
phase: 01-document-normalization
plan: 03
subsystem: layout-analysis
tags: [row-grouping, segment-identification, layout-driven]

# Dependency graph
requires:
  - phase: 01-02
    provides: Token model and token extraction
provides:
  - Row model (tokens grouped by Y-position)
  - Segment model (header, items, footer identification)
  - Row grouping logic (tokens→rows)
  - Segment identification logic (rows→segments)
affects: [01-04 - line item extraction needs segments]

# Tech tracking
tech-stack:
  added: []
  patterns: [Layout-driven approach: tokens→rows→segments, position-based segmentation]

key-files:
  created:
    - src/models/row.py
    - src/models/segment.py
    - src/pipeline/row_grouping.py
    - src/pipeline/segment_identification.py
    - tests/test_row_grouping.py
    - tests/test_segment_identification.py
  modified: []

key-decisions:
  - "Position-based segmentation (simpler, more robust) - content-based heuristics can be refined later"
  - "Row.tokens is KÄLLSANING (source of truth), Row.text is CONVENIENCE only"
  - "Y-position tolerance: 5 points or 2% of page height (whichever is smaller)"

patterns-established:
  - "Layout-driven pattern: tokens→rows→segments (not table-extractor-driven)"
  - "Traceability pattern: Row.tokens maintains Token references, Segment.rows maintains Row references"

# Metrics
duration: ~15min
completed: 2026-01-17
---

# Phase 01: Document Normalization - Plan 03 Summary

**Layout analysis implemented: tokens grouped into rows by Y-position, rows identified into segments (header/items/footer)**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-01-17 14:13
- **Completed:** 2026-01-17 14:28
- **Tasks:** 4 completed
- **Files modified:** 6 created

## Accomplishments

- Row and Segment data models created with full traceability
- Row grouping logic (tokens→rows by Y-position with tolerance)
- Segment identification (position-based: header 30%, items middle, footer 30%)
- Unit tests created for row grouping and segment identification

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Row and Segment data models** - Current commit (feat)
2. **Task 2: Implement row grouping from tokens** - Current commit (feat)
3. **Task 3: Implement segment identification from rows** - Current commit (feat)
4. **Task 4: Write unit tests** - Current commit (test)

## Files Created/Modified

- `src/models/row.py` - Row model with tokens (KÄLLSANING), y, x_min, x_max, text (CONVENIENCE)
- `src/models/segment.py` - Segment model with segment_type, rows, y_min, y_max
- `src/pipeline/row_grouping.py` - Token-to-row grouping by Y-position with tolerance
- `src/pipeline/segment_identification.py` - Row-to-segment identification (header/items/footer)
- `tests/test_row_grouping.py` - Unit tests for row grouping
- `tests/test_segment_identification.py` - Unit tests for segment identification

## Decisions Made

- **Position-based segmentation:** Used simple position-based approach (top 30% = header, middle = items, bottom 30% = footer) instead of content-based heuristics initially. This is simpler and more robust. Content-based refinement can be added later.

- **Y-position tolerance:** Used dynamic tolerance: 5 points or 2% of page height (whichever is smaller). This handles slight variations in token positioning while maintaining accuracy.

- **Traceability emphasis:** Row.tokens and Segment.rows are the source of truth. Row.text is convenience only for quick access. Downstream code should use tokens/bbox for exact positioning.

- **Edge case handling:** Edge cases handled (empty tokens, missing footer, very short invoices) to ensure robust segmentation even for unusual layouts.

## Deviations from Plan

None - plan executed exactly as written. All tasks completed as specified.

## Verification Status

- ✅ Row and Segment models match docs/02_data-model.md specification
- ✅ Row grouping correctly groups tokens by Y-position with tolerance
- ✅ Segment identification correctly identifies header/items/footer based on position
- ✅ Reading order preserved throughout (top-to-bottom)
- ✅ Full traceability: Row→Token→Page, Segment→Row→Token→Page
- ✅ Unit tests created (basic structure tests, integration tests require actual PDFs)

## Next Steps

Plan 01-04 depends on this plan - will use segments (items segment) for line item extraction.

---

*Plan completed: 2026-01-17*

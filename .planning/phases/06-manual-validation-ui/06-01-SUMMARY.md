---
phase: 06-manual-validation-ui
plan: 01
subsystem: ui
tags: [pyside6, pdf-viewer, pymupdf, click-detection]

# Dependency graph
requires:
  - phase: 05-improved-confidence-scoring
    provides: InvoiceHeader.total_candidates and total_traceability for candidate detection
provides:
  - Clickable PDF viewer component with PyMuPDF rendering
  - Click detection on candidate bounding boxes
  - Visual highlighting of candidates in PDF
  - Integration with main window validation workflow
affects: [06-02 - candidate selector will use PDF viewer signals, 06-03 - correction collection will use validation UI]

# Tech tracking
tech-stack:
  added: [pymupdf>=1.23.0]
  patterns: [PDF viewer with click detection, coordinate mapping pattern, visual highlighting pattern]

key-files:
  created:
    - src/ui/views/pdf_viewer.py
  modified:
    - src/ui/views/main_window.py (integrated PDF viewer in validation section)

key-decisions:
  - "Use PyMuPDF (fitz) for PDF rendering - reliable, well-documented, already used in codebase"
  - "QGraphicsView for PDF display - standard Qt pattern, supports click detection"
  - "Coordinate mapping: viewport → scene → PDF coordinates with scale factor"
  - "Click tolerance: 5 points for easier clicking on candidates"
  - "Show validation UI when review_count > 0 or status == REVIEW"

patterns-established:
  - "PDF viewer pattern: QGraphicsView + PyMuPDF rendering + click detection"
  - "Coordinate mapping pattern: Account for scale factor and viewport transformation"

# Metrics
duration: ~35min
completed: 2026-01-24
---

# Phase 06: Manual Validation UI - Plan 01 Summary

**Clickable PDF viewer component created with PyMuPDF rendering, click detection, and candidate highlighting**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-01-24
- **Completed:** 2026-01-24
- **Tasks:** 2 completed
- **Files modified:** 2 created, 1 modified

## Accomplishments

- Created `PDFViewer` component using PySide6 QGraphicsView and PyMuPDF
- Implemented PDF rendering with page navigation support
- Implemented click detection on candidate bounding boxes (from traceability evidence)
- Implemented visual highlighting of selected candidate (blue for selected, yellow for main)
- Integrated PDF viewer into main window validation section
- Added validation UI that shows when review_count > 0 or status == REVIEW

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PDF viewer component with PyMuPDF** - Created PDFViewer with rendering, click detection, highlighting
2. **Task 2: Integrate PDF viewer into main window** - Added validation section with PDF viewer

**Plan metadata:** Committed together as single implementation

## Files Created/Modified

- `src/ui/views/pdf_viewer.py` - NEW: PDFViewer class with PyMuPDF rendering, click detection, candidate highlighting
- `src/ui/views/main_window.py` - Added validation section with PDF viewer, shows when validation needed

## Decisions Made

- **PDF rendering library:** PyMuPDF (fitz) - already used in codebase, reliable, well-documented
- **Qt component:** QGraphicsView - standard Qt pattern for custom graphics, supports click detection
- **Coordinate mapping:** Map viewport → scene → PDF coordinates, account for scale factor from rendering
- **Click tolerance:** 5 points tolerance for easier clicking on candidate bounding boxes
- **Highlighting colors:** Blue for selected candidate, yellow for main candidate (from traceability)
- **Validation trigger:** Show validation UI when review_count > 0 or status == REVIEW
- **Page navigation:** Support for switching pages (set_page method), but currently shows first page
- **Integration approach:** Validation section initially hidden, shown when needed after processing

## Deviations from Plan

None - plan executed exactly as written

## Issues Encountered

- **Coordinate mapping complexity:** Needed to account for scale factor from PyMuPDF rendering (2x zoom) and viewport transformation. Solved by calculating scale_factor = pixmap_width / page_width.
- **Click detection accuracy:** Added 5-point tolerance to make clicking easier on candidate bounding boxes.

## Next Phase Readiness

- PDF viewer ready for candidate selector integration (Plan 06-02)
- Click detection working - emits candidate_clicked signal
- Visual highlighting working - can highlight selected candidate
- Ready for candidate selector to connect to PDF viewer signals

---
*Phase: 06-manual-validation-ui*
*Completed: 2026-01-24*

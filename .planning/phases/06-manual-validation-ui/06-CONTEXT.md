# Phase 6: Manual Validation UI - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Add manual validation UI to PySide6 GUI where users can click on total amount in PDF viewer, see candidate alternatives with confidence scores, select correct candidate, and save corrections for learning.

**Core Problem:** Users need to validate/correct total amount when confidence is low (< 0.95), and system needs to learn from these corrections.

**Goal:** Users can manually validate total amount in <10 seconds per invoice via clickable PDF viewer with candidate selection.

</domain>

<decisions>
## Implementation Decisions

### 1. PDF Viewer Component

**Approach:**
- Use PySide6 QGraphicsView with PyMuPDF (fitz) for PDF rendering
- Alternative: QPdfView (Qt 6.5+) if available, but PyMuPDF is more reliable
- Render PDF pages as QGraphicsPixmapItem or QGraphicsScene
- Support click detection on PDF coordinates

**Click Detection:**
- Map mouse click coordinates to PDF page coordinates
- Check if click is within bounding box of any candidate total amount
- Show candidate list when click detected

### 2. Candidate Display

**UI Component:**
- Dialog or side panel showing top 5 candidates from `InvoiceHeader.total_candidates`
- Display: amount, confidence score, row index, keyword type
- One-click selection (click candidate = select)
- Keyboard shortcuts: Arrow keys to navigate, Enter to select

### 3. Visual Highlighting

**PDF Highlighting:**
- Highlight selected candidate in PDF viewer (yellow/blue rectangle)
- Show bounding box from traceability evidence
- Optional: Highlight all candidates with different colors

### 4. Correction Collection

**Data Structure:**
- Store correction: (invoice_id, original_total, corrected_total, raw_confidence, corrected_confidence)
- Save to temporary file or in-memory structure (Phase 7 will add SQLite)
- Format: JSON for easy integration with Phase 7 learning system

**Correction Metadata:**
- Invoice ID (filename or hash)
- Supplier name (from InvoiceHeader)
- Original extraction result
- User-selected correction
- Timestamp

### 5. Integration with Existing GUI

**Current GUI:**
- `src/ui/views/main_window.py` - Basic processing UI
- `src/ui/services/engine_runner.py` - Runs CLI engine

**Enhancement:**
- Add validation view/mode after processing
- Show results with validation UI
- Integrate PDF viewer and candidate selector

</decisions>

<current_state>
## Current Implementation

**Files:**
- `src/ui/app.py` - Entry point
- `src/ui/views/main_window.py` - Basic main window (file selection, processing, logs)
- `src/ui/services/engine_runner.py` - Runs CLI engine in background thread

**Current Features:**
- File selection (drag & drop or browse)
- Processing with progress bar
- Log display
- Result summary

**Missing:**
- PDF viewer
- Candidate display
- Click detection
- Validation workflow
- Correction collection

</current_state>

<requirements>
## Phase Requirements

- **VALID-UI-01**: User can click on total amount in PDF viewer to see candidate alternatives
- **VALID-UI-02**: System displays multiple total amount candidates with confidence scores in UI
- **VALID-UI-03**: User can select correct total amount from candidate list
- **VALID-UI-04**: System highlights candidate totals visually in PDF viewer
- **VALID-UI-05**: User can validate total amount with keyboard shortcuts (arrow keys, Enter)
- **VALID-UI-06**: System collects user corrections and saves them for learning

</requirements>

<research>
## Research References

- `.planning/research/SUMMARY.md`: One-click selection, keyboard shortcuts, visual highlighting
- `.planning/research/ARCHITECTURE.md`: PDF Viewer (Clickable) component, Candidate Selector component
- `.planning/research/PITFALLS.md`: Manual validation UX friction (avoid with one-click, shortcuts, highlighting)

</research>

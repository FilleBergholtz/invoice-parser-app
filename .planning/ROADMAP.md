# Roadmap: Invoice Parser App

## Overview

This roadmap delivers a Swedish invoice parsing system that transforms PDF invoices into structured Excel tables with 100% accuracy on critical fields (invoice number and total) or explicit REVIEW status. The journey progresses through three phases: first establishing a stable document representation with full traceability, then extracting critical fields with confidence scoring, and finally validating and exporting with hard gates that guarantee correctness.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Document Normalization** - Establish stable PDF representation with spatial traceability
- [x] **Phase 2: Header + Wrap** - Extract critical fields (invoice number, total) with confidence scoring and handle multi-line items
- [x] **Phase 3: Validation** - Mathematical validation, hard gates, and Excel export with status columns
- [ ] **Phase 4: Web UI** - Web-based interface for invoice processing, review workflow, and API integration

## Phase Details

### Phase 1: Document Normalization

**Goal**: System can process PDF invoices (searchable or scanned) and create a stable document representation with full spatial traceability, enabling downstream field extraction.

**Depends on**: Nothing (first phase)

**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, LAYOUT-01, LAYOUT-02, LAYOUT-03, LINES-01, LINES-03, LINES-04, EXPORT-01, EXPORT-02, CLI-01, CLI-02, CLI-03

**Success Criteria** (what must be TRUE):
1. System can take a PDF invoice (searchable or scanned) as input and detect which type it is, routing to appropriate extraction path
2. System extracts all text as tokens with bounding boxes (x, y, width, height) preserving spatial information, whether from pdfplumber (searchable) or OCR (scanned)
3. System groups tokens into rows based on Y-position alignment, maintaining reading order
4. System identifies document segments (header, items/body, footer) based on position and content
5. System extracts line items using layout-driven approach (tokens→rows→segments) and produces basic Excel output (one row per line item) with invoice metadata repeated per row
6. System provides CLI interface that accepts input directory or file list, processes invoices in batch, and outputs status per invoice

**Plans**: 5 plans (all complete)

Plans:
- [x] 01-01: PDF Reading & Type Detection (Document/Page models, PDF reader, type detection)
- [x] 01-02: Token Extraction (Token model, pdfplumber tokenizer, OCR abstraction)
- [x] 01-03: Layout Analysis (Row/Segment models, row grouping, segment identification)
- [x] 01-04: Line Item Extraction (InvoiceLine model, layout-driven parser)
- [x] 01-05: Excel Export & CLI (Excel exporter, CLI interface, batch processing)

### Phase 2: Header + Wrap

**Goal**: System can extract invoice number and total amount with high confidence scoring, extract vendor and date, handle multi-line items, and store traceability for critical fields.

**Depends on**: Phase 1

**Requirements**: LAYOUT-04, EXTRACT-01, EXTRACT-02, EXTRACT-03, EXTRACT-04, EXTRACT-05, LINES-02, VALID-03

**Success Criteria** (what must be TRUE):
1. System extracts invoice number with confidence scoring (evaluates multiple candidates, scores based on position in header, proximity to "Faktura" keywords, uniqueness), stores exact value or marks as uncertain
2. System extracts total amount with confidence scoring (identifies "Att betala / Total / Summa att betala / Totalt", validates against sum excl + VAT + rounding), stores exact value or marks as uncertain
3. System extracts vendor name and invoice date from header
4. System handles multi-line items (wrapped text) by grouping continuation lines to the same line item
5. System stores traceability (page number + bbox + evidence/source text) for invoice number and total, enabling verification and trust

**Plans**: 5 plans (all complete)

Plans:
- [x] 02-01: InvoiceHeader & Traceability Models (foundation for field extraction)
- [x] 02-02: Total Amount Extraction (Priority 1: strongest signal via mathematical validation)
- [x] 02-03: Invoice Number Extraction (Priority 2: multi-factor scoring, tie-breaking)
- [x] 02-04: Vendor & Date Extraction (no hard gate, ISO date normalization)
- [x] 02-05: Wrap Detection (Priority 4: multi-line item handling)

### Phase 3: Validation

**Goal**: System validates extracted data mathematically, assigns status (OK/PARTIAL/REVIEW) based on hard gates, and exports final Excel with control columns and review reports.

**Depends on**: Phase 2

**Requirements**: VALID-01, VALID-02, VALID-04, VALID-05, EXPORT-03, EXPORT-04

**Success Criteria** (what must be TRUE):
1. System performs mathematical validation: calculates lines_sum = SUM(all line item totals), compares with extracted total, calculates diff = total - lines_sum, applies ±1 SEK tolerance for rounding
2. System implements hard gates: assigns OK status ONLY when both invoice number AND total are certain (high confidence ≥0.95). Otherwise assigns REVIEW (no silent guessing)
3. System assigns appropriate status: OK (high confidence + validation pass), PARTIAL (sum mismatch but header OK), or REVIEW (low confidence or validation failure)
4. System exports Excel with control columns: Status, LinesSum, Diff, InvoiceNoConfidence, TotalConfidence, enabling batch review of invoice quality
5. System creates review reports (review folder with PDF + metadata/annotations and JSON/CSV report with page + bbox + text excerpt) for invoices requiring manual verification

**Plans**: 4 plans (all complete)

Plans:
- [x] 03-01: ValidationResult Model & Status Assignment (foundation for validation)
- [x] 03-02: Excel Control Columns (extend export with validation data)
- [x] 03-03: Review Report Generation (JSON + PDF for REVIEW invoices)
- [x] 03-04: CLI Integration (connect all components in pipeline)

### Phase 4: Web UI

**Goal**: System provides web-based interface for invoice processing, review workflow with clickable PDF links, and API for external system integration.

**Depends on**: Phase 3

**Requirements**: UI-01, UI-02, UI-03

**Success Criteria** (what must be TRUE):
1. Users can upload PDF invoices via web browser
2. System shows processing status in real-time
3. Users can view list of processed invoices with status (OK/PARTIAL/REVIEW)
4. Users can filter and sort invoices by status
5. Users can click on invoices to see detailed information
6. Review workflow: Clickable links open PDF at correct page/position for verification
7. Users can download Excel files and review reports
8. API available for external system integration

**Plans**: 3 plans

Plans:
- [ ] 04-01: Streamlit MVP - Grundläggande UI och Filuppladdning
- [ ] 04-02: Streamlit MVP - Detaljvy och Review Workflow
- [ ] 04-03: API Endpoints för Extern Integration

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Document Normalization | 5/5 | Complete | 2026-01-17 |
| 2. Header + Wrap | 5/5 | Complete | 2026-01-17 |
| 3. Validation | 4/4 | Complete | 2026-01-17 |
| 4. Web UI | 0/0 | Planning | — |

**Note:** Phase 3 implementation is complete. Phase 4 (Web UI) is in planning phase.

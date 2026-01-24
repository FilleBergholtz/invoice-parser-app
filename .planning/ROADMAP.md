# Roadmap: Invoice Parser App

## Overview

This roadmap delivers a Swedish invoice parsing system that transforms PDF invoices into structured Excel tables with 100% accuracy on critical fields (invoice number and total) or explicit REVIEW status. v1.0 established the core pipeline. v2.0 focuses on improving confidence scoring, adding manual validation with learning, and integrating AI to reduce REVIEW status and handle unusual patterns.

## Milestones

- ✅ **v1.0 MVP** - Phases 1-4 (shipped 2026-01-17)
- 📋 **v2.0 Features** - Phases 5-9 (planned)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

<details>
<summary>✅ v1.0 MVP (Phases 1-4) - SHIPPED 2026-01-17</summary>

- [x] **Phase 1: Document Normalization** - Establish stable PDF representation with spatial traceability
- [x] **Phase 2: Header + Wrap** - Extract critical fields (invoice number, total) with confidence scoring and handle multi-line items
- [x] **Phase 3: Validation** - Mathematical validation, hard gates, and Excel export with status columns
- [x] **Phase 4: Web UI** - Web-based interface for invoice processing, review workflow, and API integration

</details>

### 📋 v2.0 Features (Planned)

**Milestone Goal:** Förbättra totalsumma-confidence, lägga till manuell validering med inlärning, och integrera AI för att minska REVIEW-status och hantera ovanliga mönster.

- [ ] **Phase 5: Improved Confidence Scoring** - Enhanced multi-factor confidence scoring for total amount to reduce REVIEW status
- [ ] **Phase 6: Manual Validation UI** - Clickable PDF viewer with candidate selection for user corrections
- [ ] **Phase 7: Learning System** - SQLite database and pattern matching to learn from user corrections
- [ ] **Phase 8: AI Integration** - AI fallback when confidence < 0.95 to improve extraction for edge cases
- [ ] **Phase 9: AI Data Analysis** (Optional) - Natural language queries and data analysis over processed invoices

## Phase Details

<details>
<summary>✅ v1.0 MVP Phases (1-4) - SHIPPED 2026-01-17</summary>

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

**Plans**: 3 plans (all complete)

Plans:
- [x] 04-01: Streamlit MVP - Grundläggande UI och Filuppladdning
- [x] 04-02: Streamlit MVP - Detaljvy och Review Workflow
- [x] 04-03: API Endpoints för Extern Integration

</details>

### 📋 v2.0 Features Phases

### Phase 5: Improved Confidence Scoring

**Goal**: System has improved confidence scoring for total amount extraction, resulting in fewer invoices with REVIEW status due to low confidence.

**Depends on**: Phase 4 (v1.0 complete)

**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04, CONF-05

**Success Criteria** (what must be TRUE):
1. System uses enhanced multi-factor confidence scoring with additional signals beyond current implementation
2. System calibrates confidence scores against actual accuracy (confidence 0.95 = 95% correct in validation)
3. System extracts multiple total amount candidates and scores each independently
4. System displays improved confidence scores clearly in UI
5. System validates confidence calibration regularly against ground truth data
6. Fewer invoices receive REVIEW status due to low confidence (measurable improvement)

**Plans**: TBD (to be planned)

---

### Phase 6: Manual Validation UI

**Goal**: Users can manually validate total amount when confidence is low by clicking on PDF and selecting correct candidate from alternatives.

**Depends on**: Phase 5

**Requirements**: VALID-UI-01, VALID-UI-02, VALID-UI-03, VALID-UI-04, VALID-UI-05, VALID-UI-06

**Success Criteria** (what must be TRUE):
1. User can click on total amount in PDF viewer to see candidate alternatives
2. System displays multiple total amount candidates with confidence scores in UI
3. User can select correct total amount from candidate list (one-click selection)
4. System highlights candidate totals visually in PDF viewer
5. User can validate total amount with keyboard shortcuts (arrow keys, Enter)
6. System collects user corrections and saves them for learning
7. Average validation time is <10 seconds per invoice

**Plans**: TBD (to be planned)

---

### Phase 7: Learning System

**Goal**: System learns from user corrections and uses learned patterns to improve confidence scoring for similar invoices in the future.

**Depends on**: Phase 6

**Requirements**: LEARN-01, LEARN-02, LEARN-03, LEARN-04, LEARN-05, LEARN-06, LEARN-07

**Success Criteria** (what must be TRUE):
1. System stores user corrections in SQLite learning database
2. System extracts patterns from corrected invoices (supplier, layout, position)
3. System matches new invoices to learned patterns (supplier-specific matching only)
4. System uses learned patterns to improve confidence scoring for similar invoices
5. System consolidates similar patterns to prevent database bloat
6. System performs regular cleanup of old or conflicting patterns
7. System accuracy improves over time as more corrections are collected (measurable improvement)

**Plans**: TBD (to be planned)

---

### Phase 8: AI Integration

**Goal**: System uses AI as fallback when confidence < 0.95 to improve total amount extraction for edge cases, reducing REVIEW status further.

**Depends on**: Phase 5 (can partially parallel with Phase 7)

**Requirements**: AI-01, AI-02, AI-03, AI-04, AI-05, AI-06, AI-07

**Success Criteria** (what must be TRUE):
1. System activates AI fallback when total amount confidence < 0.95
2. System uses AI (OpenAI/Claude) to extract total amount when heuristics fail
3. System uses structured outputs (Pydantic) for AI responses
4. System handles AI errors gracefully (timeouts, API errors, invalid responses)
5. System validates AI responses before using them
6. System can boost confidence score if AI validation succeeds
7. System abstracts AI provider (can switch between OpenAI/Claude)
8. AI usage is <20% of invoices (most handled by improved heuristics)

**Plans**: TBD (to be planned)

---

### Phase 9: AI Data Analysis (Optional)

**Goal**: Users can ask natural language questions about processed invoice data and receive structured answers.

**Depends on**: Phase 8

**Requirements**: ANALYSIS-01, ANALYSIS-02, ANALYSIS-03, ANALYSIS-04

**Success Criteria** (what must be TRUE):
1. User can ask natural language questions about processed invoice data
2. System retrieves relevant invoice information based on queries
3. System presents query results in structured format
4. System can summarize invoice data according to user requests

**Plans**: TBD (to be planned)

**Note:** This phase is optional and can be deferred to v3.0 if not critical.

---

## Progress

**Execution Order:**
Phases execute in numeric order: 5 → 6 → 7 → 8 → 9

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Document Normalization | v1.0 | 5/5 | Complete | 2026-01-17 |
| 2. Header + Wrap | v1.0 | 5/5 | Complete | 2026-01-17 |
| 3. Validation | v1.0 | 4/4 | Complete | 2026-01-17 |
| 4. Web UI | v1.0 | 3/3 | Complete | 2026-01-17 |
| 5. Improved Confidence Scoring | v2.0 | 0/3 | Not started | - |
| 6. Manual Validation UI | v2.0 | 0/TBD | Not started | - |
| 7. Learning System | v2.0 | 0/TBD | Not started | - |
| 8. AI Integration | v2.0 | 0/TBD | Not started | - |
| 9. AI Data Analysis | v2.0 | 0/TBD | Not started | - |

**Note:** v1.0 phases complete. v2.0 phases ready for planning.

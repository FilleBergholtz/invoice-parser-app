# Roadmap: Invoice Parser App

## Var vi är nu (2026-01-25)

| Status | Beskrivning |
|--------|-------------|
| **v1.0 MVP** | Klar (Phase 1–3). Shipped 2026-01-17. |
| **v2.0 Features** | Faser 5–13 klara. **Phase 14 tillagd:** Extraction fallback optimization (pdfplumber → OCR → AI → vision). |
| **Nästa steg** | Phase 14 tillagd. Kör `/gsd:plan-phase 14` för att bryta ner fasen. |

**Progress:** Phases 1–3 (v1) + 5–13 (v2) klara. **Phase 14** tillagd (oplanerad).

---

## Overview

This roadmap delivers a Swedish invoice parsing system that transforms PDF invoices into structured Excel tables with 100% accuracy on critical fields (invoice number and total) or explicit REVIEW status. v1.0 established the core pipeline. v2.0 focuses on improving confidence scoring, adding manual validation with learning, and integrating AI to reduce REVIEW status and handle unusual patterns.

## Milestones

- ✅ **v1.0 MVP** - Phases 1-3 (shipped 2026-01-17). *Phase 4 (Web UI) är borttagen – desktop-GUI (Phase 6) används i stället.*
- ✅ **v2.0 Features** - Phases 5-13 (alla klara 2026-01-25)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

<details>
<summary>✅ v1.0 MVP (Phases 1-3) - SHIPPED 2026-01-17</summary>

- [x] **Phase 1: Document Normalization** - Establish stable PDF representation with spatial traceability
- [x] **Phase 2: Header + Wrap** - Extract critical fields (invoice number, total) with confidence scoring and handle multi-line items
- [x] **Phase 3: Validation** - Mathematical validation, hard gates, and Excel export with status columns
- ~~**Phase 4: Web UI**~~ **Borttagen** – används inte. Desktop-GUI (Phase 6) används i stället.

</details>

### ✅ v2.0 Features (Complete 2026-01-25)

**Milestone Goal:** Förbättra totalsumma-confidence, manuell validering med inlärning, AI-integration, dual extraction, UI polish, About + ikoner. **Uppnådd.**

- [x] **Phase 5: Improved Confidence Scoring** - Enhanced multi-factor confidence scoring for total amount to reduce REVIEW status ✅
- [x] **Phase 6: Manual Validation UI** - Clickable PDF viewer with candidate selection for user corrections ✅
- [x] **Phase 7: Learning System** - SQLite database and pattern matching to learn from user corrections ✅
- [x] **Phase 8: AI Integration** - AI fallback when confidence < 0.95 to improve extraction for edge cases ✅
- [x] **Phase 9: AI Data Analysis** (Optional) - Natural language queries and data analysis over processed invoices ✅
- [x] **Phase 10: AI Fallback Fixes and Verification** - Document fixes, address gaps, and verify AI fallback works well ✅
- [x] **Phase 11: Pdfplumber och OCR: kör båda, jämför, använd bästa** - Dual extraction; compare results; use best ✅
- [x] **Phase 12: UI Polish (PySide6)** - Theme + layout + engine states för desktop-GUI ✅
- [x] **Phase 13: About page + app icons (branding & help)** - Om-dialog, Hjälp-meny, fönsterikoner ✅ 2026-01-25
- [ ] **Phase 14: Extraction fallback optimization (pdfplumber → OCR → AI → vision)** — [To be planned]

## Phase Details

<details>
<summary>✅ v1.0 MVP Phases (1-3) - SHIPPED 2026-01-17</summary>

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

### ~~Phase 4: Web UI~~ (Borttagen – används inte)

Phase 4 (Web UI) är borttagen. Vi använder inte webbgränssnitt; validerings- och review-UI levereras via **Phase 6: Manual Validation UI** (desktop-GUI med run_gui.py). Planerna under `.planning/phases/04-web-ui/` är arkiv och används inte i roadmapen.

</details>

### 📋 v2.0 Features Phases

### Phase 5: Improved Confidence Scoring

**Goal**: System has improved confidence scoring for total amount extraction, resulting in fewer invoices with REVIEW status due to low confidence.

**Depends on**: Phase 3 (v1.0 complete). *Phase 4 är borttagen.*

**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04, CONF-05

**Success Criteria** (what must be TRUE):
1. System uses enhanced multi-factor confidence scoring with additional signals beyond current implementation
2. System calibrates confidence scores against actual accuracy (confidence 0.95 = 95% correct in validation)
3. System extracts multiple total amount candidates and scores each independently
4. System displays improved confidence scores clearly in UI
5. System validates confidence calibration regularly against ground truth data
6. Fewer invoices receive REVIEW status due to low confidence (measurable improvement)

**Plans**: 3 plans

Plans:
- [x] 05-01: Enhanced Multi-Factor Scoring - Add additional signals (font size, VAT proximity, currency symbols, row isolation) and improve candidate extraction
- [x] 05-02: Confidence Calibration - Implement isotonic regression calibration to map raw scores to actual accuracy
- [x] 05-03: Calibration Validation CLI - Add CLI command for regular validation and training of calibration models

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

**Plans**: 3 plans

Plans:
- [ ] 09-01: Invoice Data Loading - Create data loader to read invoices from Excel files for querying
- [ ] 09-02: Natural Language Query Processing - Create AI-based query processor to parse natural language queries
- [ ] 09-03: Query Execution & CLI - Create query executor and add CLI --query command

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

**Plans**: 3 plans

Plans:
- [ ] 09-01: Invoice Data Loading - Create data loader to read invoices from Excel files for querying
- [ ] 09-02: Natural Language Query Processing - Create AI-based query processor to parse natural language queries
- [ ] 09-03: Query Execution & CLI - Create query executor and add CLI --query command

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

**Plans**: 3 plans

Plans:
- [ ] 09-01: Invoice Data Loading - Create data loader to read invoices from Excel files for querying
- [ ] 09-02: Natural Language Query Processing - Create AI-based query processor to parse natural language queries
- [ ] 09-03: Query Execution & CLI - Create query executor and add CLI --query command

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

**Plans**: 3 plans

Plans:
- [ ] 09-01: Invoice Data Loading - Create data loader to read invoices from Excel files for querying
- [ ] 09-02: Natural Language Query Processing - Create AI-based query processor to parse natural language queries
- [ ] 09-03: Query Execution & CLI - Create query executor and add CLI --query command

**Note:** This phase is optional and can be deferred to v3.0 if not critical.

---

### Phase 10: AI Fallback Fixes and Verification

**Goal:** Document what we have fixed/improved regarding AI fallback and ensure it works well in practice.

**Depends on:** Phase 9

**Plans:** 2 plans

Plans:
- [x] 10-01: Document AI fallback — 10-CONTEXT.md (trigger, context, prompts, config, UI, errors)
- [x] 10-02: Verification — 10-VERIFICATION.md, link from context, run tests

**Details:**

Dokumentera vad vi åtgärdat gällande AI fallback (t.ex. full sidkontext till AI, kandidater, prompt-förbättringar, UI-status/aktivera-inaktivera) och säkerställa att AI fallback fungerar bra i praktiken. Se `.planning/phases/10-ai-fallback-fixes/10-01-PLAN.md` och `10-02-PLAN.md`.

---

### Phase 11: Pdfplumber och OCR: kör båda, jämför, använd bästa

**Goal:** System runs both pdfplumber and OCR extraction when configured, compares results (validation_passed, total_confidence), and uses the best source per invoice for export, review, and AI.

**Depends on:** Phase 10

**Plans:** 3 plans

Plans:
- [x] 11-01: OCR path wiring — coordinate scaling, render→OCR in pipeline, pytesseract/pillow deps
- [x] 11-02: Dual-run and comparison — --compare-extraction, run both, compare, pick best
- [x] 11-03: Use best result downstream — export/review use chosen source; optional extraction_source metadata

**Details:**
Implementera både pdfplumber- och OCR-extraktion, köra båda per faktura/PDF, jämföra resultat (t.ex. validation_passed, confidence), och använda den bästa källan vidare i pipelinen. Se `.planning/phases/11-pdfplumber-ocr-compare/11-CONTEXT.md` och 11-01/11-02/11-03 PLAN-filer.

---

### Phase 12: UI Polish (PySide6) – theme + layout + engine states

**Goal:** Förbättra desktop-GUI (run_gui.py, PySide6) med enhetlig tema/styling, tydligare layout, och tydlig visning av engine-tillstånd (t.ex. Idle / Kör / Klar / Fel).

**Depends on:** Phase 6 (Manual Validation UI), Phase 11

**Scope:**
- **Theme:** Konsistent utseende (färger, teckensnitt, dark/light eller system), styrd via stylesheet eller QPalette.
- **Layout:** Tydligare uppdelning av paneler (input/output, PDF-viewer, validering), resizable/QLayout, möjligtvis sparad layout.
- **Engine states:** UI visar tydligt pipeline-tillstånd: t.ex. “Redo”, “Kör …”, “Klar”, “Fel” med ev. progress eller spinner; knappar och fält disable/enable per tillstånd så att användaren inte triggar dubbelkörningar eller missar feedback.

**Plans:** 6 plans (see 12-DISCUSS.md + 12-01 … 12-06)

Plans:
- [x] 12-01: Global theme – src/ui/theme/ (tokens, app_style.qss, apply_theme), apply in app.py
- [x] 12-02: MainWindow layout – toolbar, QSplitter, status bar, empty state, Ctrl+O/R/E
- [x] 12-03: Engine runner UX – states/signals, progress, log panel, error dialog "Show details"
- [x] 12-04: PDF viewer polish – zoom/fit/prev/next, page indicator, theme
- [x] 12-05: AI settings dialog – grouped settings, help text, Test connection stub, theme
- [ ] 12-06: UI fixes – candidate selector height, single Settings, AI settings edit, PDF placeholder, Run near Open

**Details:** `.planning/phases/12-ui-polish-pyside6/12-CONTEXT.md`, `12-DISCUSS.md`, `12-01-PLAN.md` … `12-06-PLAN.md`.

---

### Phase 14: Extraction fallback optimization (pdfplumber → OCR → AI → vision)

**Goal:** Robust, cost-efficient extraction with per-page fallback: pdfplumber → OCR → AI text → AI vision; text quality scoring and only-needed-pages fallback.

**Depends on:** Phase 13

**Plans:** 6 plans

Plans:
- [x] 14-01: Token model + OCR confidence (Token.confidence, exclude conf&lt;0, mean/median/low_conf_fraction)
- [x] 14-02: pdfplumber tokenizer (use_text_flow, extra_attrs safe fallback, line clustering)
- [x] 14-03: Text quality module (score_text_quality, score_ocr_quality [0..1])
- [x] 14-04: Rendering DPI (300 baseline, 400 retry when mean_conf&lt;55)
- [x] 14-05: AI vision + retry (image input, 4096px/20MB, 1 retry on invalid JSON)
- [x] 14-06: Orchestration + run_summary (page-level routing, vision_reason, artifacts)

**Details:**
Se `.planning/phases/14-extraction-fallback-optimization-pdfplumber-ocr-ai-vision/14-DISCUSS.md`, `14-CONTEXT.md`, `14-RESEARCH.md`. Planer: `14-01-PLAN.md` … `14-06-PLAN.md`.

---

## Progress

**Senast uppdaterad:** 2026-01-25

**Execution order:** 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Document Normalization | v1.0 | 5/5 | Complete | 2026-01-17 |
| 2. Header + Wrap | v1.0 | 5/5 | Complete | 2026-01-17 |
| 3. Validation | v1.0 | 4/4 | Complete | 2026-01-17 |
| 4. Web UI | v1.0 | 3/3 | (borttagen) | – |
| 5. Improved Confidence Scoring | v2.0 | 3/3 | Complete | 2026-01-24 |
| 6. Manual Validation UI | v2.0 | 4/4 | Complete | 2026-01-24 |
| 7. Learning System | v2.0 | 6/6 | Complete | 2026-01-24 |
| 8. AI Integration | v2.0 | 3/3 | Complete | 2026-01-24 |
| 9. AI Data Analysis | v2.0 | 3/3 | Complete | 2026-01-24 |
| 10. AI Fallback Fixes and Verification | v2.0 | 2/2 | Complete | 2026-01-24 |
| 11. Pdfplumber och OCR: kör båda, jämför, använd bästa | v2.0 | 3/3 | Complete | 2026-01-24 |
| 12. UI Polish (PySide6) – theme + layout + engine states | v2.0 | 5/5 | Complete | 2026-01-24 |
| 13. About page + app icons (branding & help) | v2.0 | 3/3 | Complete | 2026-01-25 |
| 14. Extraction fallback optimization (pdfplumber → OCR → AI → vision) | v2.0 | 2/6 | In progress | – |

**Sammanfattning:** v1.0 (Phase 1–3) klar. v2.0 phases 5–13 klara. **Phase 14 tillagd, oplanerad.**

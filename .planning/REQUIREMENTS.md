# Requirements: Invoice Parser App

**Defined:** 2025-01-27  
**Core Value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

**Status 2026-01-25:** v1 + v2 (Phase 1–3, 5–13) genomförda. Verifiering Phase 9, 10, 11 körd. Se `.planning/ROADMAP.md` och `.planning/STATE.md` för “var vi är”.

---

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Document Processing

- [x] **DOC-01**: System can detect PDF type (searchable vs scanned) and route to appropriate extraction path
- [x] **DOC-02**: System can extract text and spatial information (tokens with bbox) from searchable PDFs using pdfplumber
- [x] **DOC-03**: System can convert PDF pages to images with standardized DPI (300) and consistent coordinate system using pymupdf or pdf2image
- [x] **DOC-04**: System can perform OCR on scanned PDFs using Tesseract with Swedish language data (swe), returning tokens + bbox + confidence (not just raw text) via TSV/HOCR
- [x] **DOC-05**: OCR abstraction layer allows switching engines (e.g., PaddleOCR/EasyOCR) without changing pipeline
- [x] **DOC-06**: System handles multi-page documents, maintaining context across pages and preserving reading order

### Layout Analysis

- [x] **LAYOUT-01**: System extracts spatial text with bounding boxes (x, y, width, height) preserving document structure
- [x] **LAYOUT-02**: System groups tokens into rows based on Y-position alignment
- [x] **LAYOUT-03**: System identifies document segments (header, items/body, footer) based on position and content
- [x] **LAYOUT-04**: System creates spatial zones for contextual analysis (e.g., header zone, total zone)

### Field Extraction

- [x] **EXTRACT-01**: System extracts invoice number with confidence scoring (multiple candidates evaluated, scoring based on position in header, proximity to "Faktura" keywords, uniqueness)
- [x] **EXTRACT-02**: System extracts total amount with confidence scoring (identifies "Att betala / Total / Summa att betala / Totalt", validates against sum excl + VAT + rounding)
- [x] **EXTRACT-03**: System extracts vendor name from header
- [x] **EXTRACT-04**: System extracts invoice date from header
- [x] **EXTRACT-05**: System stores traceability (page number + bbox + evidence/source text) for invoice number and total (absolute requirement for hard gates)

### Line Item Extraction

- [x] **LINES-01**: System extracts line items using layout-driven approach (tokens→rows→segments), not table-extractor-driven (pdfplumber table detection is helper, not single point of failure)
- [x] **LINES-02**: System handles multi-line items (wrapped text) by grouping continuation lines to same line item
- [x] **LINES-03**: System extracts line item fields: description, quantity, unit price, total amount (best effort extraction)
- [x] **LINES-04**: System handles line items spanning multiple pages (table continuation)

### Validation & Quality Control

- [x] **VALID-01**: System performs mathematical validation: calculates lines_sum = SUM(all line item totals), compares with extracted total, calculates diff = total - lines_sum
- [x] **VALID-02**: System applies tolerance-based validation (±1 SEK) for rounding differences and shipping/discount rows
- [x] **VALID-03**: System assigns confidence scores to all critical fields (invoice number, total)
- [x] **VALID-04**: System implements hard gates: OK status ONLY when both invoice number AND total are certain (high confidence ≥0.95). Otherwise REVIEW (no silent guessing)
- [x] **VALID-05**: System assigns status: OK (high confidence + validation pass), PARTIAL (sum mismatch but header OK), or REVIEW (low confidence or validation failure)

### Export & Output

- [x] **EXPORT-01**: System exports primary output as Excel file (one row per line item/product row)
- [x] **EXPORT-02**: Excel includes invoice metadata repeated per row: Fakturanummer, Fakturadatum, Företag, Totalsumma
- [x] **EXPORT-03**: Excel includes control columns: Status, LinesSum, Diff, InvoiceNoConfidence, TotalConfidence (or HeaderConfidence if combined)
- [x] **EXPORT-04**: System creates review reports: review folder with PDF + metadata/annotations and JSON/CSV report with page + bbox + text excerpt for debugging

### Interface & Processing

- [x] **CLI-01**: System provides CLI interface for batch processing of multiple PDF invoices
- [x] **CLI-02**: System outputs status per invoice (OK/PARTIAL/REVIEW) during batch processing
- [x] **CLI-03**: System accepts input directory or file list and outputs to specified directory

## v2.0 Requirements

Requirements for v2.0 milestone. Focus: Improved confidence scoring, manual validation, learning system, and AI integration.

### Confidence Scoring Improvements

- [ ] **CONF-01**: System uses enhanced multi-factor confidence scoring for total amount extraction (additional signals beyond current implementation)
- [ ] **CONF-02**: System calibrates confidence scores against actual accuracy (confidence 0.95 = 95% correct in validation)
- [ ] **CONF-03**: System displays improved confidence scores clearly in UI (already exists, needs enhancement)
- [ ] **CONF-04**: System extracts multiple total amount candidates and scores each independently
- [ ] **CONF-05**: System validates confidence calibration regularly against ground truth data

### Manual Validation & User Interaction

- [x] **VALID-UI-01**: User can click on total amount in PDF viewer to see candidate alternatives
- [x] **VALID-UI-02**: System displays multiple total amount candidates with confidence scores in UI
- [x] **VALID-UI-03**: User can select correct total amount from candidate list
- [x] **VALID-UI-04**: System highlights candidate totals visually in PDF viewer
- [x] **VALID-UI-05**: User can validate total amount with keyboard shortcuts (arrow keys, Enter)
- [x] **VALID-UI-06**: System collects user corrections and saves them for learning

### Learning System

- [x] **LEARN-01**: System stores user corrections in SQLite learning database
- [x] **LEARN-02**: System extracts patterns from corrected invoices (supplier, layout, position)
- [x] **LEARN-03**: System matches new invoices to learned patterns (supplier-specific matching)
- [x] **LEARN-04**: System uses learned patterns to improve confidence scoring for similar invoices
- [x] **LEARN-05**: System consolidates similar patterns to prevent database bloat
- [x] **LEARN-06**: System performs regular cleanup of old or conflicting patterns
- [x] **LEARN-07**: System isolates patterns by supplier (no cross-supplier pattern matching)

### AI Integration

- [x] **AI-01**: System activates AI fallback when total amount confidence < 0.95
- [x] **AI-02**: System uses AI (OpenAI/Claude) to extract total amount when heuristics fail
- [x] **AI-03**: System uses structured outputs (Pydantic) for AI responses
- [x] **AI-04**: System handles AI errors gracefully (timeouts, API errors, invalid responses)
- [x] **AI-05**: System validates AI responses before using them
- [x] **AI-06**: System can boost confidence score if AI validation succeeds
- [x] **AI-07**: System abstracts AI provider (can switch between OpenAI/Claude)

### AI Data Analysis (Optional - v2.1+)

- [x] **ANALYSIS-01**: User can ask natural language questions about processed invoice data
- [x] **ANALYSIS-02**: System retrieves relevant invoice information based on queries
- [x] **ANALYSIS-03**: System presents query results in structured format
- [x] **ANALYSIS-04**: System can summarize invoice data according to user requests

## v3.0 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Processing

- **PROC-01**: Enhanced OCR preprocessing (deskew, denoise, contrast enhancement) for better accuracy on poor-quality scans
- **PROC-02**: Multi-language support (beyond Swedish)

### Advanced Features

- **ADV-01**: Real-time processing (single invoice processing on demand)
- **ADV-02**: Cloud deployment option
- **ADV-03**: Template learning system for vendor-specific optimizations
- **ADV-04**: Confidence prediction model (ML model predicts confidence before extraction)
- **ADV-05**: Batch learning (learn from multiple corrections at once)
- **ADV-06**: AI-powered pattern discovery (AI finds unusual patterns automatically)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Web UI / Phase 4 | **Borttagen – används inte.** Phase 4 (Web UI) är borttagen från roadmapen. Vi använder desktop-GUI (Phase 6, run_gui.py) för validering och review. CLI räcker för batch; GUI levereras som desktop-app. |
| Real-time processing | v1 dimensioned for batch processing (some to hundreds per week). Real-time adds unnecessary complexity. |
| Generic PDF parser | Focus is invoice-specific parsing with domain optimizations. Generic parser loses accuracy and Swedish-specific features. |
| Automatic correction of low-confidence fields | Violates 100% accuracy guarantee. Would introduce false positives. Hard gate with REVIEW status is the correct approach. |
| Template management system | Template-free approach with layout analysis is the design. Template system would create maintenance burden and break with vendor format changes. |
| API in v1 | CLI sufficient for v1. API can be added later if external systems need integration. |
| AI for all invoices | Expensive, slow, unnecessary. Use AI only as fallback when confidence < 0.95. |
| Override hard gates | Users cannot override hard gates. Would break core value (100% accuracy guarantee). Improve confidence instead. |
| Cloud-based learning | Privacy concerns, data ownership. Use local SQLite database per user. |
| Real-time AI for all | Expensive, slow. AI only when confidence < 0.95 (fallback pattern). |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

### v1.0 Requirements (Complete)

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOC-01 | Phase 1 | Complete |
| DOC-02 | Phase 1 | Complete |
| DOC-03 | Phase 1 | Complete |
| DOC-04 | Phase 1 | Complete |
| DOC-05 | Phase 1 | Complete |
| DOC-06 | Phase 1 | Complete |
| LAYOUT-01 | Phase 1 | Complete |
| LAYOUT-02 | Phase 1 | Complete |
| LAYOUT-03 | Phase 1 | Complete |
| LAYOUT-04 | Phase 2 | Complete |
| EXTRACT-01 | Phase 2 | Complete |
| EXTRACT-02 | Phase 2 | Complete |
| EXTRACT-03 | Phase 2 | Complete |
| EXTRACT-04 | Phase 2 | Complete |
| EXTRACT-05 | Phase 2 | Complete |
| LINES-01 | Phase 1 | Complete |
| LINES-02 | Phase 2 | Complete |
| LINES-03 | Phase 1 | Complete |
| LINES-04 | Phase 1 | Complete |
| VALID-01 | Phase 3 | Complete |
| VALID-02 | Phase 3 | Complete |
| VALID-03 | Phase 2 | Complete |
| VALID-04 | Phase 3 | Complete |
| VALID-05 | Phase 3 | Complete |
| EXPORT-01 | Phase 1 | Complete |
| EXPORT-02 | Phase 1 | Complete |
| EXPORT-03 | Phase 3 | Complete |
| EXPORT-04 | Phase 3 | Complete |
| CLI-01 | Phase 1 | Complete |
| CLI-02 | Phase 1 | Complete |
| CLI-03 | Phase 1 | Complete |

### v2.0 Requirements

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | Phase 5 | Pending |
| CONF-02 | Phase 5 | Pending |
| CONF-03 | Phase 5 | Pending |
| CONF-04 | Phase 5 | Pending |
| CONF-05 | Phase 5 | Pending |
| VALID-UI-01 | Phase 6 | Pending |
| VALID-UI-02 | Phase 6 | Pending |
| VALID-UI-03 | Phase 6 | Pending |
| VALID-UI-04 | Phase 6 | Pending |
| VALID-UI-05 | Phase 6 | Pending |
| VALID-UI-06 | Phase 6 | Pending |
| LEARN-01 | Phase 7 | Pending |
| LEARN-02 | Phase 7 | Pending |
| LEARN-03 | Phase 7 | Pending |
| LEARN-04 | Phase 7 | Pending |
| LEARN-05 | Phase 7 | Pending |
| LEARN-06 | Phase 7 | Pending |
| LEARN-07 | Phase 7 | Pending |
| AI-01 | Phase 8 | Pending |
| AI-02 | Phase 8 | Pending |
| AI-03 | Phase 8 | Pending |
| AI-04 | Phase 8 | Pending |
| AI-05 | Phase 8 | Pending |
| AI-06 | Phase 8 | Pending |
| AI-07 | Phase 8 | Pending |
| ANALYSIS-01 | Phase 9 | Pending |
| ANALYSIS-02 | Phase 9 | Pending |
| ANALYSIS-03 | Phase 9 | Pending |
| ANALYSIS-04 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 35 total (all complete)
- v2.0 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 ✓

### Backlog / användarrapporterade förbättringar

- [x] **INV-ID-01** (2026-01-25): I corrections.json och learning.db ska vi spara **extraherade fakturanummer** som identifierare när dessa finns, inte bara PDF-filnamn. En PDF kan innehålla flera fakturor med olika fakturanummer – varje ska identifieras med sitt fakturanummer. **Implementerat:** validation-blob innehåller `invoice_number`; GUI använder det vid "Bekräfta val" som `invoice_id` när det finns.
- [ ] **MULTIPAGE-01**: Fakturor som sträcker sig över flera sidor ska kunna lokaliseras och slås ihop: (a) hitta samma fakturanummer på flera sidor, (b) använd sidnummer i hörn (oftast övre högra) för att veta vilka sidor som hör ihop, (c) flera line items kan ligga på flera sidor för samma faktura – dessa ska behandlas som en logisk faktura.
- [x] **INV-NUM-02** (2026-01-25): Fakturanumret saknar första siffran vid extraktion. Korrekt är t.ex. 40615472 men vi får 0615472. I run_summary syns källtoken "4061547206" – undersök header_extractor (regex/kandidatval) så att hela numret eller rätt del (40615472) används, inte bara avklippt 0615472. **Implementerat:** Efter val av bästa kandidat söker header_extractor bland tokens efter en längre sifferseqvens som innehåller det valda numret; vid 10 tecken med årsuffix (06/24/25/26) används första 8 tecken (t.ex. 4061547206 → 40615472).
- [x] **REF-01** (2026-01-25): Referens/fakturareferens ska extraheras från headern och sparas i Excel. Kolumnen "Referenser" finns idag men fylls inte från extraktion. Sök i headern efter etiketter som "fakturareferens", "betalningsreferens", "referens", "reference" etc. och spara värdet så att det hamnar i Excel-kolumnen Referenser. **Implementerat:** extract_reference() i header_extractor, InvoiceHeader.reference, invoice_metadata["referenser"] i CLI, Excel använder meta.get("referenser").

---
*Requirements defined: 2025-01-27*
*Last updated: 2026-01-25 — INV-NUM-02, REF-01 implementerade*

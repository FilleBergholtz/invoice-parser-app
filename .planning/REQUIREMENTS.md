# Requirements: Invoice Parser App

**Defined:** 2025-01-27
**Core Value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

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

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Processing

- **PROC-01**: Enhanced OCR preprocessing (deskew, denoise, contrast enhancement) for better accuracy on poor-quality scans
- **PROC-02**: Vendor-specific heuristics learning to reduce REVIEW rate over time
- **PROC-03**: Multi-language support (beyond Swedish)

### User Interface

- **UI-01**: Review workflow with clickable PDF links (opens PDF at specific page/bbox for verification)
- **UI-02**: Web UI for invoice processing and review
- **UI-03**: API for external system integration

### Advanced Features

- **ADV-01**: Real-time processing (single invoice processing on demand)
- **ADV-02**: Cloud deployment option
- **ADV-03**: Template learning system for vendor-specific optimizations

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Web UI in v1 | CLI sufficient for batch processing. Web UI adds complexity and delays core functionality. Add later once pipeline is stable. |
| Real-time processing | v1 dimensioned for batch processing (some to hundreds per week). Real-time adds unnecessary complexity. |
| Generic PDF parser | Focus is invoice-specific parsing with domain optimizations. Generic parser loses accuracy and Swedish-specific features. |
| Automatic correction of low-confidence fields | Violates 100% accuracy guarantee. Would introduce false positives. Hard gate with REVIEW status is the correct approach. |
| Template management system | Template-free approach with layout analysis is the design. Template system would create maintenance burden and break with vendor format changes. |
| API in v1 | CLI sufficient for v1. API can be added later if external systems need integration. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

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
| VALID-01 | Phase 3 | Pending |
| VALID-02 | Phase 3 | Pending |
| VALID-03 | Phase 2 | Complete |
| VALID-04 | Phase 3 | Pending |
| VALID-05 | Phase 3 | Pending |
| EXPORT-01 | Phase 1 | Complete |
| EXPORT-02 | Phase 1 | Complete |
| EXPORT-03 | Phase 3 | Pending |
| EXPORT-04 | Phase 3 | Pending |
| CLI-01 | Phase 1 | Complete |
| CLI-02 | Phase 1 | Complete |
| CLI-03 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0 ✓

---
*Requirements defined: 2025-01-27*
*Last updated: 2026-01-17 after Phase 3 completion*

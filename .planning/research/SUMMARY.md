# Project Research Summary

**Project:** Invoice Parser App
**Domain:** Invoice parsing system (OCR + layout analysis + structured data extraction)
**Researched:** 2025-01-27
**Confidence:** HIGH

## Executive Summary

Invoice parsing systems combine OCR, layout analysis, and semantic extraction to transform PDF invoices into structured data. The standard approach uses a multi-stage pipeline: document input detection (searchable vs scanned PDFs), layout analysis for spatial understanding, field extraction for headers and line items, validation for mathematical consistency, and structured export. Modern systems prioritize template-free parsing with layout-aware extraction over brittle template-based approaches.

For this project (Swedish invoice parser with 100% accuracy on critical fields), the recommended approach is: pdfplumber for searchable PDFs (fast path) with pytesseract OCR fallback (scanned PDFs), spatial layout analysis for field identification, confidence scoring with hard gates (OK/PARTIAL/REVIEW status), and traceability back to PDF source. The critical risk is over-reliance on OCR accuracy - mitigated through confidence thresholds, mathematical validation, and explicit REVIEW status for uncertain extractions.

Key architectural decision: Modular pipeline (12 stages) with hard gate validation. This enables 100% accuracy guarantee for OK status while flagging uncertain cases for manual review. Unlike commercial SaaS (cost, vendor lock-in) or template-based systems (maintenance burden), this open-source approach provides flexibility and accuracy control at the cost of initial implementation complexity.

## Key Findings

### Recommended Stack

Python 3.11+ with pdfplumber (≥0.10.0) for searchable PDF extraction and layout analysis, pandas (≥2.0.0) for data processing and Excel export, pytesseract for OCR fallback on scanned PDFs, and pytest for testing. Supporting libraries: pdf2image for PDF-to-image conversion, opencv-python for image preprocessing, openpyxl for Excel formatting.

**Core technologies:**
- **pdfplumber**: PDF text extraction with spatial information (x,y,width,height) — essential for layout-aware extraction, preserves reading order and table structure
- **pandas**: Data processing and Excel export — industry standard for structured data manipulation, excellent Excel integration
- **pytesseract**: OCR engine for scanned PDFs — free, open-source, supports Swedish language, fallback when PDF has no text layer

### Expected Features

**Must have (table stakes):**
- High-accuracy OCR/text extraction (searchable PDFs via pdfplumber, scanned via OCR)
- Field-level extraction (invoice number, date, vendor, totals) with layout awareness
- Line item extraction from tables (complex but essential for validation)
- Mathematical validation (sum of line items vs total) with ±1 SEK tolerance
- Confidence scoring and exception handling (hard gates: OK/PARTIAL/REVIEW)
- Export to Excel with status columns and traceability

**Should have (competitive):**
- Hard gates on critical fields (100% or REVIEW) — differentiator for trust
- Template-free parsing — adapts to vendor changes without maintenance
- Batch processing with status tracking — handles volume efficiently
- Review workflow with clickable PDF links — fast human verification

**Defer (v2+):**
- Web UI — CLI sufficient for v1, add UI later
- API integration — only if external systems need direct access
- Real-time processing — batch is sufficient for invoice volumes

### Architecture Approach

Modular 12-stage pipeline matching project specification: Input detection → Layout analysis → Field extraction → Table parsing → Validation → Status assignment → Export. Each stage transforms data and passes to next, enabling independent testing and debugging. Key architectural patterns: Pipeline architecture (sequential stages), Hard gate validation (100% or REVIEW), Spatial traceability (bbox/page references for verification).

**Major components:**
1. **PDF Reader** — Detects PDF type (searchable/scanned), routes to appropriate extraction path
2. **Layout Analyzer** — Spatial text extraction with bounding boxes, document structure understanding
3. **Field Extractor** — Invoice number and total extraction with confidence scoring
4. **Table Parser** — Line item extraction from tables, multi-line item handling
5. **Validator** — Mathematical reconciliation, confidence assessment, status assignment
6. **Exporter** — Excel generation with status columns, review reports with PDF links

### Critical Pitfalls

1. **Over-reliance on OCR accuracy** — OCR misreads characters, causing incorrect extractions. Prevention: Confidence scoring, hard gates, preprocessing, validation checks
2. **Template-based extraction** — Breaks when vendor changes layout. Prevention: Layout analysis, semantic extraction, template-free approach
3. **Ignoring multi-page context** — Tables/fields split across pages lost. Prevention: Document-level context, table continuation detection
4. **Silent failure on low confidence** — Returns best guess, violates 100% accuracy. Prevention: Hard gates, explicit REVIEW status, never OK for uncertain extractions
5. **Poor table/line item extraction** — Header OK but line items missing/misaligned. Prevention: Robust table detection, multi-line handling, validation requirement

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Document Normalization

**Rationale:** Foundation - stable document representation with full traceability before attempting field extraction. Prevents pitfalls #3 (multi-page context) and #6 (traceability).

**Delivers:** PDF → Page → Tokens → Rows → Segments pipeline with spatial information preserved at every step. Each InvoiceLine traceable back to Page/Row/Token.

**Addresses:** Table stakes (OCR/text extraction, layout understanding), differentiator (traceability)

**Avoids:** Pitfall #3 (multi-page context), Pitfall #6 (traceability)

**Uses:** pdfplumber for spatial extraction, basic tokenization and row grouping

### Phase 2: Header + Wrap

**Rationale:** Build on stable foundation - extract critical fields (invoice number, total) with layout-aware approach. Handles multi-line items.

**Delivers:** Header extraction with confidence scoring, line item extraction with wrapped text handling. Spatial zonering for context.

**Addresses:** Table stakes (field extraction, line items), differentiator (hard gates, template-free)

**Avoids:** Pitfall #2 (template-based extraction), Pitfall #5 (poor table extraction)

**Implements:** Layout-aware field extraction, header scoring, multi-line item grouping

### Phase 3: Validation

**Rationale:** Quality control layer - mathematical validation, confidence assessment, hard gates. Ensures 100% accuracy on OK status.

**Delivers:** Reconciliation (sum validation), status assignment (OK/PARTIAL/REVIEW), Excel export with status columns, review reports.

**Addresses:** Table stakes (validation, confidence scoring), differentiator (hard gates)

**Avoids:** Pitfall #1 (OCR accuracy), Pitfall #4 (silent failure)

**Implements:** Hard gate logic, tolerance-based validation (±1 SEK), status system

### Phase Ordering Rationale

- **Phase 1 before Phase 2:** Must have stable document representation (tokens, rows, segments) before attempting field extraction. Layout analysis depends on spatial information.
- **Phase 2 before Phase 3:** Must extract fields and line items before validation. Validation compares extracted values, assigns status.
- **Dependencies:** Field extraction requires layout analysis (Phase 1 → Phase 2). Validation requires field extraction (Phase 2 → Phase 3).

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Header scoring algorithms, confidence threshold calibration (what is "high confidence"?)
- **Phase 2:** Multi-line item handling strategies (how to group wrapped text?)

Phases with standard patterns (skip research-phase):
- **Phase 1:** Document normalization patterns well-established (pdfplumber standard usage)
- **Phase 3:** Validation patterns straightforward (sum reconciliation, status assignment)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | pdfplumber, pandas are industry standard. Versions verified, well-documented. |
| Features | HIGH | Feature landscape well-researched from industry sources. Table stakes vs differentiators clear. |
| Architecture | HIGH | Pipeline architecture is standard pattern. 12-stage design matches project specification. |
| Pitfalls | HIGH | Common pitfalls well-documented from industry sources and academic papers. Prevention strategies clear. |

**Overall confidence:** HIGH

### Gaps to Address

- **Confidence threshold calibration:** What confidence score (0.95?) constitutes "high confidence" for hard gates? Need validation with test corpus.
- **Swedish-specific heuristics:** Field name variations in Swedish ("Fakturanummer", "Faktura nr", etc.) - need comprehensive keyword list.
- **Tolerance tuning:** ±1 SEK tolerance for sum validation - verify this handles all rounding cases in Swedish invoices.

## Sources

### Primary (HIGH confidence)
- WebSearch 2025 — "invoice parsing PDF OCR Python 2025 best libraries pdfplumber pytesseract"
- WebSearch 2025 — "invoice parser features requirements table stakes OCR document extraction 2025"
- WebSearch 2025 — "invoice parsing architecture pipeline OCR layout analysis 2025 design patterns"
- WebSearch 2025 — "invoice parsing common mistakes pitfalls OCR PDF extraction problems 2025"
- Project specification: specs/invoice_pipeline_v1.md (12-stage pipeline)
- Project requirements: .planning/PROJECT.md (hard gates, 100% accuracy)

### Secondary (MEDIUM confidence)
- Industry analysis: Commercial SaaS feature comparisons
- Academic papers: Document parsing architecture patterns

---
*Research completed: 2025-01-27*
*Ready for roadmap: yes*

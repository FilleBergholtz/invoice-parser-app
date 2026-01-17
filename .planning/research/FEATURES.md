# Feature Research

**Domain:** Invoice parsing system (OCR + layout analysis + structured extraction)
**Researched:** 2025-01-27
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| High-accuracy OCR/text extraction | Invoices contain critical financial data; errors are costly | MEDIUM | Must handle both searchable PDFs (fast path) and scanned (OCR path) |
| Field-level extraction (invoice number, date, vendor, totals) | Core requirement for any invoice parser | MEDIUM | Requires layout analysis + semantic understanding |
| Line item extraction | Users need detailed product/service breakdowns, not just totals | HIGH | **Layout-driven approach:** tokens→rows→segments (not "table extractor"-driven). pdfplumber table detection is helper, not single point of failure. Complex due to table variations, multi-line items, wrapped text |
| Multi-page document support | Real invoices span multiple pages | MEDIUM | Must maintain context across pages, handle page breaks in tables |
| Mathematical validation (totals check) | Detects extraction errors, builds user trust | LOW | Critical for 100% accuracy requirement on totals |
| Confidence scoring & exception handling | Users need to know when extraction is uncertain | MEDIUM | Enables hard gates - REVIEW status for low confidence |
| **Primary output: Excel (one row per line item)** | Core requirement - structured tabular format | LOW | pandas + openpyxl. One row = one product/service line. Invoice metadata (number, date, vendor, total) repeated per row. **Critical:** Must include control columns: Status, LinesSum, Diff |
| Spatial traceability (link back to PDF) | Users must verify extracted values against source | MEDIUM | **Absolute requirement for hard gates:** Store page + bbox + evidence (source text) for invoice number and total. Enables verification and trust |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Hard gates on critical fields (100% or REVIEW) | Guarantees no false positives - critical for trust | LOW | **Definition:** OK status ONLY when invoice number + total are both certain (high confidence). Otherwise REVIEW (no silent guessing). This is the definition of "100% correct" - 100% accurate for all OK exports. Requires traceability (page+bbox+evidence) for both critical fields |
| Template-free parsing | Adapts to vendor layout changes without maintenance | HIGH | Requires robust layout analysis + semantic understanding |
| Batch processing with status tracking | Handles volume efficiently, clear visibility into issues | MEDIUM | CLI + status output per invoice |
| Review workflow with clickable PDF links | Fast human verification of flagged invoices | MEDIUM | PDF viewer integration or metadata for navigation |
| Swedish language optimization | Better accuracy on Swedish invoices vs generic OCR | LOW | pytesseract Swedish language pack, Swedish field name patterns |
| Tolerance-based validation (±1 SEK) | Reduces false positives from rounding | LOW | Simple but effective for Swedish currency |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Automatic correction of low-confidence fields | Would increase "success rate" | Violates 100% accuracy guarantee - introduces false positives | Hard gate: REVIEW instead of guess |
| Real-time processing | Feels modern | Adds complexity, latency concerns, not needed for batch | Batch processing is sufficient for invoice volumes |
| Web UI in v1 | More accessible | Delays core functionality, adds tech stack complexity | CLI first, add UI later once pipeline is stable |
| Template management system | Seems organized | Creates maintenance burden, breaks with vendor changes | Template-free approach with layout analysis |
| Generic PDF parser (not invoice-specific) | Broader use case | Loses domain-specific optimizations and accuracy | Invoice-specific heuristics and validation |

## Feature Dependencies

```
PDF Input Detection
    └──requires──> Text Layer Check
                       ├──requires──> pdfplumber (searchable PDF path)
                       └──requires──> OCR Pipeline (scanned PDF path)
                                         └──requires──> Image Preprocessing

Layout Analysis
    └──requires──> Spatial Text Extraction (pdfplumber or OCR with bbox)
                       └──requires──> Page Segmentation

Field Extraction (Invoice Number, Total)
    └──requires──> Layout Analysis
                       └──requires──> Semantic Understanding (rules/heuristics)

Line Item Extraction
    └──requires──> Layout Analysis
                       └──requires──> Table Detection
                            └──requires──> Multi-line Item Handling

Validation
    └──requires──> Field Extraction
    └──requires──> Line Item Extraction
                       └──requires──> Mathematical Reconciliation

Status Assignment (OK/PARTIAL/REVIEW)
    └──requires──> Validation
    └──requires──> Confidence Scoring

Export to Excel
    └──requires──> Structured Data (from all extraction steps)
    └──requires──> Status Information
```

### Dependency Notes

- **Field Extraction requires Layout Analysis:** Spatial understanding is critical to distinguish invoice number from other numbers, totals from line items
- **Line Item Extraction enhances Validation:** Line items enable sum validation against total
- **Status Assignment conflicts with Auto-correction:** Cannot have both hard gates and automatic fixes

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [x] PDF text extraction (pdfplumber for searchable, OCR for scanned) — Essential input
- [x] Layout analysis (spatial text extraction with bbox) — Required for field identification
- [x] Invoice number extraction with confidence scoring — Critical field, hard gate requirement
- [x] Total extraction with confidence scoring — Critical field, hard gate requirement
- [x] Line item extraction (best effort) — Needed for validation
- [x] Mathematical validation (sum of line items vs total) — Core quality check
- [x] Status assignment (OK/PARTIAL/REVIEW) — Required for hard gates
- [x] Excel export (primary output: one row per line item) with control columns (Status, LinesSum, Diff) — Required output format
- [x] CLI interface for batch processing — Required user interface for v1

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Review workflow UI (clickable PDF links) — Improves manual review speed
- [ ] Enhanced OCR preprocessing (deskew, denoise) — Improves scanned PDF accuracy
- [ ] Vendor-specific heuristics learning — Reduces REVIEW rate over time
- [ ] Multi-language support (beyond Swedish) — Expands market

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Web UI — Only if CLI usage becomes barrier
- [ ] API for integration — Only if external systems need direct access
- [ ] Cloud deployment — Only if users need hosted solution
- [ ] Real-time processing — Only if batch becomes bottleneck
- [ ] Template learning system — Only if vendor-specific optimizations needed

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Invoice number extraction (100%) | HIGH | MEDIUM | P1 |
| Total extraction (100%) | HIGH | MEDIUM | P1 |
| Line item extraction | HIGH | HIGH | P1 |
| Status assignment (OK/PARTIAL/REVIEW) | HIGH | LOW | P1 |
| Excel export | HIGH | LOW | P1 |
| Batch processing CLI | MEDIUM | LOW | P1 |
| PDF traceability | MEDIUM | MEDIUM | P2 |
| Review workflow UI | MEDIUM | HIGH | P2 |
| Enhanced OCR preprocessing | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch (v1)
- P2: Should have, add when possible (v1.x)
- P3: Nice to have, future consideration (v2+)

## Competitor Feature Analysis

| Feature | Commercial SaaS (Textract, DocAI) | Open Source (invoice2data) | Our Approach |
|---------|----------------------------------|----------------------------|--------------|
| Accuracy | HIGH (95%+ on header, 80-90% on line items) | MEDIUM (template-dependent) | Focus on 100% for critical fields (hard gates) |
| Template handling | AI-based, template-free | Template-based (brittle) | Template-free with layout analysis |
| Line items | Good but not perfect | Varies by template quality | Best effort with validation |
| Cost | $$ per document | Free but requires maintenance | Free (open source stack) |
| Swedish support | Good (multilingual) | Limited | Optimized for Swedish |
| Traceability | Limited | None | Core feature (critical for trust) |

## Sources

- WebSearch 2025 — "invoice parser features requirements table stakes OCR document extraction 2025"
- Industry analysis: Commercial SaaS feature comparisons
- Project requirements: PROJECT.md (100% accuracy on invoice number/total)
- Research: Common invoice parsing user expectations

---
*Feature research for: Invoice Parser App (Swedish invoices, hard gates on critical fields)*
*Researched: 2025-01-27*

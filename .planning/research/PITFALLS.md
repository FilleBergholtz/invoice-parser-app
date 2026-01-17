# Pitfalls Research

**Domain:** Invoice parsing system (OCR + PDF extraction)
**Researched:** 2025-01-27
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Over-Reliance on OCR Accuracy

**What goes wrong:**
OCR misreads characters (0→O, 8→$, 1→I) leading to incorrect invoice numbers or totals. System exports incorrect data marked as OK.

**Why it happens:**
Developers assume OCR is accurate enough, don't implement confidence thresholds or validation.

**How to avoid:**
- Implement confidence scoring for all OCR extractions
- Hard gate on critical fields: invoice number and total require high confidence (≥0.95) or REVIEW status
- Post-OCR validation: cross-check totals with sum of line items
- Preprocessing: improve image quality (deskew, denoise) before OCR

**Warning signs:**
- High "success" rate but users report errors
- No confidence scores in output
- No validation checks (sum of line items vs total)

**Phase to address:**
Phase 1 (Document Normalization) - implement confidence scoring from start
Phase 3 (Validation) - hard gate implementation

---

### Pitfall 2: Template-Based Extraction

**What goes wrong:**
System works for known invoice formats but breaks when vendor changes layout. Requires constant template maintenance.

**Why it happens:**
Regex or position-based extraction assumes fixed layout. Vendor updates invoice design, extraction fails.

**How to avoid:**
- Use layout analysis (spatial understanding) instead of fixed templates
- Semantic extraction: look for keywords ("Faktura", "Total") + context, not fixed positions
- Vendor-agnostic heuristics: header scoring based on position + content patterns
- Template-free approach: adapt to layout changes automatically

**Warning signs:**
- Separate template/config file for each vendor
- Frequent template updates needed
- Extraction fails when invoice layout changes slightly

**Phase to address:**
Phase 2 (Header + Wrap) - implement layout-aware extraction

---

### Pitfall 3: Ignoring Multi-Page Context

**What goes wrong:**
Tables or fields split across pages are treated as separate documents. Line items lost, totals incorrect.

**Why it happens:**
Processing each page independently, losing context between pages.

**How to avoid:**
- Maintain document-level context across pages
- Table continuation detection: identify when table header repeats, merge rows
- Field extraction considers all pages (invoice number might be on page 2)
- Multi-page table reconstruction

**Warning signs:**
- Processing stops at page 1
- Tables truncated at page breaks
- Missing line items on later pages

**Phase to address:**
Phase 1 (Document Normalization) - page-aware processing from start

---

### Pitfall 4: Silent Failure on Low Confidence

**What goes wrong:**
System returns "best guess" for uncertain extractions, exports as OK. Users discover errors later, lose trust.

**Why it happens:**
Trying to maximize "success" rate, treating low confidence as acceptable.

**How to avoid:**
- Hard gates: uncertain extractions → REVIEW status, never OK
- Explicit status system: OK (high confidence + validation pass), PARTIAL (sum mismatch but header OK), REVIEW (low confidence)
- Never export as OK unless both invoice number and total are high confidence
- Clear distinction: 100% accurate for OK status vs uncertain for REVIEW

**Warning signs:**
- All invoices marked OK
- No REVIEW status in output
- Users report errors in "successful" extractions

**Phase to address:**
Phase 3 (Validation) - status assignment with hard gates

---

### Pitfall 5: Poor Table/Line Item Extraction

**What goes wrong:**
Header fields (invoice number, total) extracted correctly but line items missing or misaligned. Cannot validate totals.

**Why it happens:**
Table detection fails on borderless tables, multi-line items, wrapped text. Focus on "easy" header extraction, ignore complex tables.

**How to avoid:**
- Robust table detection: handle borderless tables, detect columns by alignment
- Multi-line item handling: group wrapped text to same line item
- Fallback strategies: if table detection fails, use row-based extraction with heuristics
- Validation requirement: sum of line items must match total (enforces extraction quality)

**Warning signs:**
- Header extracted but no line items
- Line item count doesn't match visible rows
- Sum of line items never matches total

**Phase to address:**
Phase 1 (Document Normalization) - robust row/segment identification
Phase 2 (Header + Wrap) - multi-line item handling

---

### Pitfall 6: Lack of Traceability

**What goes wrong:**
User questions extracted value, cannot verify against source PDF. Trust erodes, manual verification required.

**Why it happens:**
Only storing extracted values, not spatial references (where in PDF).

**How to avoid:**
- Store bounding boxes (bbox) for all critical fields
- Page number + bbox enables clickable links to PDF source
- Source text snippet: show original OCR/extracted text for verification
- Review reports: include PDF with annotations/markings

**Warning signs:**
- No page/position info in output
- Cannot locate extracted value in PDF
- No way to verify "where did this come from?"

**Phase to address:**
Phase 1 (Document Normalization) - spatial info from start
Phase 3 (Validation) - traceability in review reports

---

## Moderate Pitfalls

### Pitfall 7: No Mathematical Validation

**What goes wrong:**
Extracted totals don't match sum of line items, errors go undetected.

**Prevention:**
- Reconciliation step: sum all line items, compare to total
- Tolerance handling: ±1 SEK for rounding differences
- Status assignment: PARTIAL if sum mismatch (but header OK), REVIEW if header uncertain

**Phase to address:** Phase 3 (Validation)

### Pitfall 8: Poor Image Preprocessing

**What goes wrong:**
OCR accuracy low on scanned PDFs due to skew, noise, low resolution.

**Prevention:**
- Image preprocessing pipeline: deskew, denoise, contrast enhancement
- Resolution check: warn if image quality too low
- Preprocessing before OCR improves accuracy significantly

**Phase to address:** Phase 1 (if OCR needed early) or Phase 2

### Pitfall 9: Inconsistent Field Naming

**What goes wrong:**
Swedish invoices use various terms ("Fakturanummer", "Faktura nr", "Nr"). Simple keyword matching fails.

**Prevention:**
- Comprehensive keyword lists for Swedish invoice terms
- Fuzzy matching for variations
- Context-aware extraction: position + keyword + pattern

**Phase to address:** Phase 2 (Header + Wrap)

## Minor Pitfalls

### Pitfall 10: Export Format Issues

**What goes wrong:**
Excel export loses formatting, numbers as text, dates incorrect.

**Prevention:**
- Use openpyxl for proper Excel formatting
- Type detection: numbers as numbers, dates as dates
- Column width auto-adjust

**Phase to address:** Phase 3 (Export)

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip preprocessing for OCR | Faster initial development | Lower OCR accuracy, more REVIEW cases | Never - accuracy critical |
| Hardcode Swedish keywords | Quick field extraction | Breaks with vendor variations | MVP only, generalize in v1.x |
| No confidence scoring | Simpler code | Cannot implement hard gates | Never - required for 100% accuracy |
| Single-page processing | Simpler architecture | Breaks multi-page invoices | Never - real invoices are multi-page |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Tesseract OCR | Not installing system Tesseract | Install Tesseract separately, use pytesseract wrapper |
| pdfplumber | Assuming all PDFs are searchable | Check text layer first, fallback to OCR |
| pandas Excel export | Using to_excel without openpyxl | Install openpyxl, use engine='openpyxl' |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential processing | Slow batch processing | Parallel workers for I/O-bound PDF reading | 100+ invoices/batch |
| No OCR caching | Re-OCR same PDFs | Cache OCR results for repeat processing | Repeated processing |
| Memory leaks in pipeline | Memory grows with batch size | Proper cleanup, generator patterns | Large batches (1000+) |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing sensitive invoice data unencrypted | Data breach | Encrypt at rest, secure file handling |
| No access control on review reports | Unauthorized access | File permissions, user authentication (if web UI added) |
| Logging full invoice content | Information leakage | Log only metadata, not PII |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No status visibility | Users don't know which invoices need review | Clear status column (OK/PARTIAL/REVIEW) in Excel |
| Unclear error messages | Users can't fix issues | Descriptive errors, traceability to PDF source |
| No batch summary | Users don't know overall success rate | Summary stats: X OK, Y PARTIAL, Z REVIEW |

## "Looks Done But Isn't" Checklist

- [ ] **Invoice number extraction:** Often missing confidence scoring — verify confidence ≥0.95 or REVIEW
- [ ] **Total extraction:** Often missing validation — verify sum of line items matches total
- [ ] **Line items:** Often missing multi-line handling — verify wrapped text grouped correctly
- [ ] **Status assignment:** Often all marked OK — verify hard gates working (some REVIEW status)
- [ ] **Traceability:** Often missing spatial references — verify bbox/page stored for critical fields
- [ ] **Excel export:** Often missing status columns — verify LinesSum, Diff, Status columns present

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Template-based extraction | HIGH | Refactor to layout analysis, rebuild extraction logic |
| No confidence scoring | MEDIUM | Add confidence to existing extractors, update validation |
| Missing traceability | MEDIUM | Re-process PDFs with traceability, or add in next version |
| Poor OCR accuracy | LOW | Improve preprocessing, retrain/configure OCR |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Over-reliance on OCR accuracy | Phase 1 + Phase 3 | Confidence scores present, hard gates working |
| Template-based extraction | Phase 2 | Extraction works on unseen invoice formats |
| Multi-page context | Phase 1 | Multi-page invoices process correctly |
| Silent failure | Phase 3 | REVIEW status assigned for low confidence |
| Poor table extraction | Phase 1 + Phase 2 | Line items extracted, sum validation passes |
| Lack of traceability | Phase 1 + Phase 3 | bbox/page stored, review reports include links |

## Sources

- WebSearch 2025 — "invoice parsing common mistakes pitfalls OCR PDF extraction problems 2025"
- Industry post-mortems: Commercial invoice parsing system failures
- Academic papers: Common OCR/document extraction errors
- Project requirements: Hard gates and 100% accuracy requirement

---
*Pitfalls research for: Invoice Parser App (Swedish invoices, hard gates, 100% accuracy)*
*Researched: 2025-01-27*

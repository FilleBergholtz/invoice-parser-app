# Phase 3: Validation - Context & Decisions

**Created:** 2026-01-17  
**Status:** Discussion phase  
**Purpose:** Identify gray areas and gather implementation decisions for Phase 3 validation and export features.

---

## Phase 3 Scope

**Goal**: System validates extracted data mathematically, assigns status (OK/PARTIAL/REVIEW) based on hard gates, and exports final Excel with control columns and review reports.

**Requirements to implement:**
- VALID-01: Mathematical validation (lines_sum vs total)
- VALID-02: Tolerance-based validation (±1 SEK)
- VALID-04: Hard gates (OK only when both invoice number AND total are ≥0.95)
- VALID-05: Status assignment (OK/PARTIAL/REVIEW)
- EXPORT-03: Excel control columns (Status, LinesSum, Diff, confidence scores)
- EXPORT-04: Review reports (review folder with PDF + metadata, JSON/CSV report)

---

## Gray Areas - Questions for Discussion

### 1. Status System: PARTIAL vs WARNING

**Conflict identified:**
- `ROADMAP.md` uses: **OK / PARTIAL / REVIEW**
- `docs/05_validation.md` uses: **OK / Warning / Review**

**Question 1.1:** Which status system should we use? PARTIAL or WARNING?

**Current understanding:**
- **PARTIAL**: Sum mismatch but header OK (confidence ≥0.95 for invoice number and total, but mathematical validation fails or diff > ±1 SEK)
- **WARNING**: Same as PARTIAL? Or different?

**Recommendation:** Use **OK / PARTIAL / REVIEW** to match ROADMAP and requirements. PARTIAL = "header data is confident but line items don't sum correctly" (actionable: review line items). WARNING suggests less severity than PARTIAL.

**Decision needed:** Confirm PARTIAL vs WARNING terminology.

---

### 2. Status Assignment Logic

**Current state:**
- `InvoiceHeader.meets_hard_gate()` exists and checks: `invoice_number_confidence >= 0.95 AND total_confidence >= 0.95`
- Status currently set in CLI as: `"OK" if all_invoice_lines else "PARTIAL"` (simplified)
- Mathematical validation exists in `validate_total_against_line_items()` (Phase 2)

**Question 2.1:** What is the exact logic for status assignment?

**Proposed logic (from ROADMAP):**
```
IF hard_gate_passes AND sum_diff <= ±1 SEK:
    Status = OK
ELIF hard_gate_passes AND sum_diff > ±1 SEK:
    Status = PARTIAL  # Header confident, but line items don't sum
ELSE:
    Status = REVIEW  # Hard gate failed (low confidence)
```

**Edge cases to clarify:**
- What if invoice_number_confidence >= 0.95 but total_confidence < 0.95? → REVIEW
- What if total_confidence >= 0.95 but invoice_number_confidence < 0.95? → REVIEW
- What if no invoice_lines extracted but header OK? → PARTIAL or REVIEW?
- What if invoice_lines exist but total_amount is None (not extracted)? → REVIEW

**Decision needed:** Confirm status assignment logic with all edge cases.

---

### 3. Mathematical Validation Integration

**Current state:**
- `validate_total_against_line_items()` exists in `confidence_scoring.py` (used during total extraction)
- Calculation: `lines_sum = SUM(line.total_amount)`, `diff = |total - lines_sum|`, check `diff <= tolerance`

**Question 3.1:** Where should mathematical validation happen?
- Option A: During extraction (Phase 2) - already done for confidence scoring
- Option B: As separate validation step (Phase 3) - for status assignment and reporting
- Option C: Both - extraction uses it for confidence, validation step uses it for status

**Question 3.2:** What values should be stored for Excel control columns?
- `lines_sum`: SUM of all InvoiceLine.total_amount
- `diff`: `total_amount - lines_sum` (signed difference, not absolute)
- `total_amount`: From InvoiceHeader.total_amount (extracted from footer)
- All three needed for Excel export?

**Question 3.3:** What if `total_amount` is None (not extracted, confidence < 0.95)?
- Calculate `lines_sum` anyway? (Yes - shows what we have)
- Set `diff = None` or `diff = "N/A"`? (Prefer "N/A" in Excel)
- Status = REVIEW regardless? (Yes - hard gate failed)

**Decision needed:** Confirm validation step structure and what values to calculate/store.

---

### 4. Excel Control Columns Format

**Current Excel columns (Phase 1):**
- Fakturanummer, Referenser, Företag, Fakturadatum, Beskrivning, Antal, Enhet, Á-pris, Rabatt, Summa, Hela summan

**Required control columns (from requirements):**
- Status, LinesSum, Diff, InvoiceNoConfidence, TotalConfidence

**Question 4.1:** Where should control columns be placed?
- Option A: **After** existing columns (at the end) - keeps existing columns first
- Option B: **Before** existing columns (at the start) - control columns most visible
- Option C: **Mixed** - Status first, confidence columns at end

**Question 4.2:** Exact column names (Swedish or English)?
- Status → "Status" (OK/PARTIAL/REVIEW)
- LinesSum → "Radsumma" or "LinesSum"?
- Diff → "Diff" or "Avvikelse"?
- InvoiceNoConfidence → "Fakturanummer-konfidens" or "InvoiceNoConfidence"?
- TotalConfidence → "Totalsumma-konfidens" or "TotalConfidence"?

**Recommendation:** Swedish for consistency: "Status", "Radsumma", "Avvikelse", "Fakturanummer-konfidens", "Totalsumma-konfidens"

**Question 4.3:** Excel formatting for control columns?
- Status: Text (OK/PARTIAL/REVIEW)
- LinesSum: Number with 2 decimals (currency format)
- Diff: Number with 2 decimals (signed, can be negative)
- Confidence scores: Percentage (0.95 → 95%) or decimal (0.95)? Recommendation: Percentage (95%)

**Decision needed:** Confirm column order, names, and formatting.

---

### 5. Review Reports Structure

**Requirement:** Create review reports for invoices with REVIEW status (or all invoices?).

**Question 5.1:** Which invoices get review reports?
- Option A: **Only REVIEW status** - saves space, focuses on issues
- Option B: **All invoices** - comprehensive traceability, easier debugging
- Option C: **REVIEW + PARTIAL** - covers all uncertain cases

**Recommendation:** Only REVIEW (most useful, saves space).

**Question 5.2:** Review folder structure?
```
output_dir/
  ├── invoices_2026-01-17.xlsx  (consolidated Excel)
  ├── errors/                    (corrupt PDFs - already exists)
  └── review/                    (NEW - review reports)
      ├── invoice_12345/
      │   ├── invoice_12345.pdf  (copy of original PDF)
      │   ├── metadata.json      (InvoiceHeader + Traceability)
      │   └── report.csv         (optional - same data as JSON, CSV format)
      └── invoice_67890/
          ├── invoice_67890.pdf
          └── metadata.json
```

**Alternative:** Flat structure with prefixes?
```
review/
  ├── invoice_12345.pdf
  ├── invoice_12345_metadata.json
  ├── invoice_67890.pdf
  └── invoice_67890_metadata.json
```

**Recommendation:** Folder per invoice (organized, scales better).

**Question 5.3:** What metadata should be in review report?
- InvoiceHeader data (invoice_number, total_amount, confidence scores, etc.)
- Traceability evidence for invoice_number and total (JSON structure)
- Validation results (status, lines_sum, diff, errors)
- Line items count and summary?

**Question 5.4:** JSON vs CSV format?
- JSON: Structured, includes nested Traceability evidence, easier to parse programmatically
- CSV: Human-readable in Excel, but loses nested structure
- Both: JSON for programmatic access, CSV for manual review?

**Recommendation:** JSON only (structured, preserves traceability). CSV can be generated later if needed.

**Question 5.5:** PDF copy vs reference?
- Copy PDF to review folder? (Takes space but self-contained)
- Reference original path? (Saves space but requires original to stay)
- Configurable option? (User choice)

**Recommendation:** Copy PDF (self-contained, safe to move/archive review folder).

**Decision needed:** Confirm review folder structure, metadata content, and formats.

---

### 6. Status Integration with Existing Code

**Current state:**
- `process_invoice()` returns dict with `status` field (currently simplified: "OK" if lines exist, else "PARTIAL")
- `InvoiceHeader.meets_hard_gate()` exists but not used in status assignment
- Mathematical validation exists but not used for status

**Question 6.1:** Where should status assignment logic live?
- Option A: **New module** `src/pipeline/status_assignment.py` - dedicated validation module
- Option B: **InvoiceHeader method** - `InvoiceHeader.assign_status(line_items)` - keeps logic with data
- Option C: **CLI function** - `assign_invoice_status(invoice_header, line_items)` - simple function

**Recommendation:** Option A - new `validation.py` module (separation of concerns, reusable).

**Question 6.2:** What should status assignment function return?
```python
# Option A: Just status string
status = assign_status(invoice_header, line_items)  # "OK" | "PARTIAL" | "REVIEW"

# Option B: Validation result object
validation_result = validate_invoice(invoice_header, line_items)
# validation_result.status
# validation_result.lines_sum
# validation_result.diff
# validation_result.errors
# validation_result.warnings

# Option C: Update InvoiceHeader with status
invoice_header.status = assign_status(invoice_header, line_items)
```

**Recommendation:** Option B - ValidationResult object (carries all validation data for Excel export).

**Decision needed:** Confirm validation module structure and return type.

---

### 7. Excel Export Integration

**Current state:**
- `export_to_excel()` takes `invoice_lines` and `invoice_metadata` dict
- Does not include validation data (status, lines_sum, diff, confidence)

**Question 7.1:** How to pass validation data to Excel export?
- Option A: Extend `invoice_metadata` dict with validation fields
- Option B: Create `InvoiceResult` object that contains InvoiceHeader + validation + line items
- Option C: Pass separate `validation_result` parameter

**Question 7.2:** Multi-invoice batch export?
- Current: One Excel file with all invoices (one row per line item)
- Control columns: Should Status/Diff be per-invoice or per-line-item?
  - Per-line-item: Status column repeats same value for all rows of same invoice
  - Per-invoice: Only one row per invoice (summary row)
  
**Current design:** One row per line item (from Phase 1). Control columns should repeat per row (same value for all rows of same invoice).

**Question 7.3:** How to handle invoices with different statuses in batch?
- All invoices go to same Excel file (with their Status in control column)
- Or separate Excel files per status? (OK.xlsx, PARTIAL.xlsx, REVIEW.xlsx)

**Recommendation:** One consolidated Excel file with Status column (user can filter/sort by Status).

**Decision needed:** Confirm Excel export API and batch handling.

---

## Summary of Decisions Needed

1. **Status terminology:** PARTIAL vs WARNING? → Use PARTIAL
2. **Status assignment logic:** Exact rules for OK/PARTIAL/REVIEW with all edge cases
3. **Mathematical validation:** Where it happens, what values to store
4. **Excel control columns:** Order, names (Swedish), formatting (percentage for confidence)
5. **Review reports:** Which invoices (REVIEW only?), folder structure, metadata content, JSON vs CSV
6. **Validation module structure:** Where status logic lives, what it returns
7. **Excel export integration:** How to pass validation data, batch handling

---

## Recommended Defaults (if user confirms)

- **Status system:** OK / PARTIAL / REVIEW (matches ROADMAP)
- **Status logic:** Hard gate + sum_diff <= ±1 SEK = OK; Hard gate pass + sum_diff > ±1 SEK = PARTIAL; Hard gate fail = REVIEW
- **Control columns:** After existing columns, Swedish names, percentage for confidence
- **Review reports:** REVIEW status only, folder per invoice, JSON metadata with Traceability, copy PDF
- **Validation module:** New `validation.py` with `ValidationResult` object
- **Excel export:** Extend `invoice_metadata` dict with validation fields, one consolidated file

---

*Context document created: 2026-01-17*  
*Awaiting user decisions on gray areas*

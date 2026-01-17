# Phase 2: Header + Wrap - Context

**Gathered:** 2026-01-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract invoice number and total amount with high confidence scoring, extract vendor name and date from header, handle multi-line items (wrapped text), and store traceability for critical fields. This phase adds field extraction and confidence scoring to the document normalization foundation from Phase 1.

</domain>

<decisions>
## Implementation Decisions

### 1. Confidence Scoring - Fakturanummer (Invoice Number)

**Kandidatgenerering:**
- Extract **all matches**, but limit scoring to **top 10 candidates** (performance + robustness balance)
- Use regex + keyword proximity according to Heuristik 5 (docs/04_heuristics.md)

**Score Components (normalized to 0.0-1.0):**
- **Position (0.30 weight):** In header zone (y < 0.30 * page_height) → high score
- **Keyword proximity (0.35 weight):** "fakturanummer / invoice number / nr / no" on same row or within 1 row above → high score
- **Format validation (0.20 weight):** Alphanumeric, reasonable length (3-25 characters), not just date/amount/org number
- **Uniqueness (0.10 weight):** Appears once in document (or clearly most likely instance)
- **OCR/Token confidence (0.05 weight):** Average confidence of tokens in candidate area

**High Confidence Threshold:**
- Default: **≥ 0.95 = OK candidate**, otherwise REVIEW (hard gate requirement)

**Final Value Selection:**
- Choose candidate with **highest score**
- If top-2 candidates are within **0.03 score difference** and have different values → **REVIEW** (avoid silent guessing)

**Priority:** Second priority in Phase 2 (after totalsumma)

---

### 2. Confidence Scoring - Totalsumma (Total Amount)

**Kandidatgenerering:**
- Search in footer zone (y > 0.80 * page_height) + keywords: "Att betala", "Total", "Totalt", "Summa att betala", etc. (Heuristik 11)
- Extract all amounts that can be linked to these keywords, score top 10

**Score Components (normalized to 0.0-1.0):**
- **Keyword match (0.35 weight):** "Att betala" strongest, "Total/Totalt" next strongest
- **Position (0.20 weight):** Footer zone + right-aligned amount column
- **Mathematical validation (0.35 weight):**
  - If subtotal + VAT (+ rounding) exist and match → full score
  - If only total exists → neutral (not penalized, but lower than validated)
- **Relative size (0.10 weight):** Total should normally be largest amount among summation rows (with exceptions)

**Mathematical Validation (Formula):**
- Default: `subtotal_ex_vat + vat_total + rounding ≈ total`
- Tolerance: **±1 SEK** (matches Phase 1 context decision)

**High Confidence Threshold:**
- Default: **≥ 0.95 = OK**, otherwise REVIEW

**Final Amount Selection:**
- Choose candidate with **highest score**
- If two totals compete but only one passes validation → choose the validated one
- If none pass validation and multiple exist → REVIEW

**Priority:** **First priority in Phase 2** (hard gate + mathematical validation provides strongest early signal)

---

### 3. Traceability Format for Critical Fields

For **fakturanummer** and **totalsumma**, always store:

**JSON Structure:**
```json
{
  "field": "invoice_no|total",
  "value": "...",
  "confidence": 0.0,
  "evidence": {
    "page_number": 1,
    "bbox": [x, y, w, h],
    "row_index": 12,
    "text_excerpt": "max 120 characters (full row if shorter)",
    "tokens": [
      {"text":"...", "bbox":[...], "conf":0.0}
    ]
  }
}
```

**Specifications:**
- **Text excerpt length:** Default **120 characters**, or full row if shorter
- **BBox:** For **entire match** (union of all tokens included in match)
- **Storage:** JSON format (dataclass internally OK for code, but always write JSON to review folder)

**Priority:** Third priority in Phase 2

---

### 4. Wrap Detection (Multi-line Items)

**Candidate Wrap Row Criteria:**
- Lies directly below a product row
- Contains **no amount** (Heuristik 9)
- Starts at approximately same X as description column start

**X-Position Tolerance:**
- Default: `±0.02 * page_width` (≈ 2% of page width)
  - More robust than "5 pixels" across different DPI/resolutions

**Stop Conditions:**
- Next row contains amount → stop (new product row)
- X-start deviates > tolerance → stop
- **Max 3 wrap rows per line item** (default limit)

**Edge Case - Wrap Row Contains Partial Amount:**
- Then it is **not** a wrap: treat as new row/fee row and flag for uncertainty

**Consolidation:**
- Default: Append wrap text with **space separator** (not newline) for Excel readability

**Priority:** Fourth priority in Phase 2

---

### 5. Vendor Name and Date Extraction (Default Decisions)

**Robustness:**
- Always attempt extraction, but low confidence values are acceptable (no hard gate like invoice number/total)
- If not found, leave as None (no placeholder) - affects Excel export

**Date Format:**
- Normalize to ISO format (YYYY-MM-DD) for consistency
- Support Swedish formats per Heuristik 6 (docs/04_heuristics.md)

**Vendor Name:**
- Extract company name only (address out of scope for Phase 2)
- Use heuristics from docs/04_heuristics.md

**Integration:**
- Store in InvoiceHeader model (per docs/02_data-model.md)
- Link to InvoiceLines via document reference

---

### 6. Pipeline Integration

**Execution Order:**
1. After segment identification (Phase 1)
2. Extract header fields (invoice number, vendor, date) from header segment
3. Extract total amount from footer segment
4. Handle wrap detection during/after line item extraction
5. Store traceability for invoice number and total

**Data Models:**
- Use InvoiceHeader model (docs/02_data-model.md) for header data
- Link InvoiceHeader to Document
- InvoiceLines already reference segments (via InvoiceLine.segment)
- Add traceability JSON structure to InvoiceHeader or separate Traceability model

**Confidence Storage:**
- Store confidence scores in InvoiceHeader fields (invoice_number_confidence, total_confidence)
- Use for hard gate evaluation (≥0.95 threshold)

</decisions>

<specifics>
## Specific Ideas

- Confidence scoring weights prioritized: keyword proximity/validation (0.35 each) for highest signal
- Top-10 candidate limit balances performance with coverage
- Mathematical validation provides strongest signal for totalsumma (hence first priority)
- X-tolerance as percentage of page width more robust than absolute pixels
- Max 3 wraps per line item prevents runaway wrapping
- Space separator for wrap text maintains Excel readability
- 120-character text excerpt sufficient for review context

</specifics>

<deferred>
## Deferred Ideas

- Vendor address extraction (company name only in Phase 2)
- Advanced OCR confidence integration (basic token confidence only)
- Multiple invoice number formats in single document (handled as uniqueness check)
- Wrap detection across page boundaries (Phase 2 scope: within-page only)

</deferred>

---
*Phase: 02-header-wrap*
*Context gathered: 2026-01-17*
